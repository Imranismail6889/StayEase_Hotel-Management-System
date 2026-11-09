"""Availability, pricing, and reservation transactions."""

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP


from app.extensions import db
from app.models import Booking, BookingExtra, Notification, PromoCode, Setting
from app.services.payment_service import create_payment, refund_payment
from app.utils.errors import APIError

EXTRAS = {
    "Breakfast": Decimal("24.00"),
    "Airport pickup": Decimal("48.00"),
    "Late checkout": Decimal("35.00"),
    "Spa package": Decimal("95.00"),
}
CENT = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def is_available(
    room_id: int, check_in: date, check_out: date, exclude_booking_id=None
) -> bool:
    query = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.status != "cancelled",
        Booking.check_in_date < check_out,
        Booking.check_out_date > check_in,
    )
    if exclude_booking_id:
        query = query.filter(Booking.id != exclude_booking_id)
    return query.first() is None


def _valid_promo(code: str, nights: int) -> PromoCode | None:
    if not code:
        return None
    promo = PromoCode.query.filter_by(code=code.upper()).first()
    today = datetime.now(timezone.utc)
    if not promo or not promo.is_active:
        raise APIError("invalid_promo", "This promo code is not active.", 422)
    valid_from = promo.valid_from
    valid_to = promo.valid_to
    if valid_from.tzinfo is None:
        valid_from = valid_from.replace(tzinfo=timezone.utc)
    if valid_to.tzinfo is None:
        valid_to = valid_to.replace(tzinfo=timezone.utc)
    if not valid_from <= today <= valid_to or promo.used_count >= promo.max_uses:
        raise APIError(
            "invalid_promo",
            "This promo code has expired or reached its usage limit.",
            422,
        )
    if nights < promo.min_nights:
        raise APIError(
            "invalid_promo",
            "This stay does not meet the minimum nights for this code.",
            422,
            {"min_nights": promo.min_nights},
        )
    return promo


def quote(user, data: dict, check_availability=True) -> dict:
    from app.models import Room

    room = db.session.get(Room, data["room_id"])
    if not room:
        raise APIError("not_found", "Room not found.", 404)
    check_in, check_out = data["check_in"], data["check_out"]
    if check_in < date.today():
        raise APIError("validation_error", "Check-in cannot be in the past.", 422)
    if check_out <= check_in:
        raise APIError("validation_error", "Check-out must be after check-in.", 422)
    if data.get("guests", 1) > room.capacity:
        raise APIError(
            "validation_error",
            "Guest count exceeds room capacity.",
            422,
            {"capacity": room.capacity},
        )
    if room.status == "maintenance":
        raise APIError("conflict", "This room is under maintenance.", 409)
    if check_availability and not is_available(room.id, check_in, check_out):
        raise APIError("conflict", "This room is already booked for those dates.", 409)
    nights = (check_out - check_in).days
    extras = data.get("extras", [])
    unknown = sorted(set(extras) - set(EXTRAS))
    if unknown:
        raise APIError(
            "validation_error",
            "One or more selected extras are invalid.",
            422,
            {"extras": unknown},
        )
    room_total = Decimal(room.price_per_night) * nights
    extras_total = sum((EXTRAS[name] * nights for name in extras), Decimal("0.00"))
    subtotal = _money(room_total + extras_total)
    promo = _valid_promo(data.get("promo_code", ""), nights)
    promo_discount = (
        _money(subtotal * Decimal(promo.discount_percent) / Decimal(100))
        if promo
        else Decimal("0.00")
    )
    tier_discount_rate = {"Gold": Decimal("0.05"), "Platinum": Decimal("0.10")}.get(
        user.loyalty_tier, Decimal("0")
    )
    tier_discount = _money((subtotal - promo_discount) * tier_discount_rate)
    discount = min(subtotal, promo_discount + tier_discount)
    tax_rate = Decimal(
        Setting.query.filter_by(key="tax_rate").first().value
        if Setting.query.filter_by(key="tax_rate").first()
        else "12"
    )
    tax = _money((subtotal - discount) * tax_rate / Decimal(100))
    total = _money(subtotal - discount + tax)
    return {
        "room": room.to_dict(),
        "room_id": room.id,
        "nights": nights,
        "guests": data.get("guests", 1),
        "extras": [
            {"name": name, "price": float(EXTRAS[name] * nights)} for name in extras
        ],
        "subtotal": float(subtotal),
        "discount_amount": float(discount),
        "promo_discount": float(promo_discount),
        "loyalty_discount": float(tier_discount),
        "tax_rate": float(tax_rate),
        "tax_amount": float(tax),
        "total": float(total),
        "promo_code": promo.code if promo else "",
        "currency": (
            Setting.query.filter_by(key="currency").first().value
            if Setting.query.filter_by(key="currency").first()
            else "USD"
        ),
    }


def create_booking(user, data: dict) -> Booking:
    from app.models import Room

    room = db.session.get(Room, data["room_id"])
    priced = quote(user, data)
    ref = (
        "BK-"
        + datetime.now(timezone.utc).strftime("%y%m%d")
        + "-"
        + str(int(datetime.now(timezone.utc).timestamp() * 1000))[-6:]
    )
    booking = Booking(
        booking_ref=ref,
        user=user,
        room=room,
        check_in_date=data["check_in"],
        check_out_date=data["check_out"],
        guests=data.get("guests", 1),
        nights=priced["nights"],
        subtotal=Decimal(str(priced["subtotal"])),
        tax_amount=Decimal(str(priced["tax_amount"])),
        discount_amount=Decimal(str(priced["discount_amount"])),
        total_amount=Decimal(str(priced["total"])),
        promo_code=priced["promo_code"],
        status="confirmed",
        special_requests=data.get("special_requests", ""),
    )
    try:
        for extra in data.get("extras", []):
            booking.extras.append(
                BookingExtra(extra_name=extra, price=EXTRAS[extra] * priced["nights"])
            )
        db.session.add(booking)
        db.session.flush()
        payment = create_payment(
            booking,
            Decimal(str(priced["total"])),
            data.get("method", "credit_card"),
            data.get("card_last4", ""),
            data.get("card_brand", ""),
        )
        db.session.add(payment)
        promo = (
            PromoCode.query.filter_by(code=priced["promo_code"]).first()
            if priced["promo_code"]
            else None
        )
        if promo:
            promo.used_count += 1
        db.session.add(
            Notification(
                user_id=user.id,
                title="Stay confirmed",
                message="Your reservation " + ref + " is confirmed.",
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return booking


def cancel_booking(booking: Booking) -> dict:
    if booking.status in ("cancelled", "checked_out"):
        raise APIError("conflict", "This reservation cannot be cancelled.", 409)
    now = datetime.now(timezone.utc)
    check_in = datetime.combine(
        booking.check_in_date, datetime.min.time(), tzinfo=timezone.utc
    )
    hours = (check_in - now).total_seconds() / 3600
    fraction = (
        Decimal("1.00")
        if hours >= 48
        else Decimal("0.50") if hours > 0 else Decimal("0.00")
    )
    refund = _money(Decimal(booking.total_amount) * fraction)
    booking.status = "cancelled"
    for payment in booking.payments:
        if payment.status == "paid" and refund:
            payment.transaction_ref = refund_payment(payment, refund)
    db.session.add(
        Notification(
            user_id=booking.user_id,
            title="Reservation cancelled",
            message="Your reservation "
            + booking.booking_ref
            + " has been cancelled. Refund: $"
            + str(refund)
            + ".",
        )
    )
    db.session.commit()
    return {"refund_amount": float(refund), "refund_percent": int(fraction * 100)}
