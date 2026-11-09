"""Administrator operations."""

import csv
import io
from datetime import date
from flask import Blueprint, Response, g, request
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Amenity, Booking, Notification, PromoCode, Room, Setting, User
from app.schemas import (
    BookingStatusSchema,
    PaginationSchema,
    PromoWriteSchema,
    RoomStatusSchema,
    RoomWriteSchema,
    SettingSchema,
)
from app.services.booking_service import cancel_booking
from app.services.loyalty_service import award_checkout_points
from app.services.stats_service import dashboard_stats
from app.utils.decorators import admin_required, validate_with
from app.utils.errors import APIError
from app.utils.responses import success

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@bp.get("/stats")
@admin_required
def stats():
    return success(dashboard_stats())


@bp.get("/today")
@admin_required
def today_board():
    today = date.today()
    arrivals = Booking.query.filter_by(check_in_date=today, status="confirmed").all()
    departures = Booking.query.filter_by(
        check_out_date=today, status="checked_in"
    ).all()
    in_house = Booking.query.filter_by(status="checked_in").all()
    return success(
        {
            "arrivals": [booking.to_dict() for booking in arrivals],
            "departures": [booking.to_dict() for booking in departures],
            "in_house": [booking.to_dict() for booking in in_house],
            "arrival_count": len(arrivals),
            "departure_count": len(departures),
            "in_house_count": len(in_house),
        }
    )


@bp.get("/activity")
@admin_required
def activity():
    rows = Booking.query.order_by(Booking.created_at.desc()).limit(20).all()
    return success(
        [
            {
                "id": b.id,
                "booking_ref": b.booking_ref,
                "guest": b.user.name,
                "room": b.room.name,
                "status": b.status,
                "created_at": b.created_at.isoformat(),
            }
            for b in rows
        ]
    )


@bp.post("/rooms")
@admin_required
@validate_with(RoomWriteSchema)
def create_room():
    data = g.validated
    room = Room(
        **{
            key: data[key]
            for key in (
                "room_number",
                "name",
                "room_type",
                "description",
                "price_per_night",
                "capacity",
                "floor",
                "status",
                "image_urls",
            )
        }
    )
    room.amenities = _amenities(data["amenities"])
    db.session.add(room)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise APIError("conflict", "Room number is already in use.", 409) from exc
    return success(room.to_dict(), 201)


@bp.put("/rooms/<int:room_id>")
@admin_required
@validate_with(RoomWriteSchema)
def update_room(room_id):
    room = db.session.get(Room, room_id)
    if not room:
        raise APIError("not_found", "Room not found.", 404)
    for key in (
        "room_number",
        "name",
        "room_type",
        "description",
        "price_per_night",
        "capacity",
        "floor",
        "status",
        "image_urls",
    ):
        setattr(room, key, g.validated[key])
    room.amenities = _amenities(g.validated["amenities"])
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise APIError("conflict", "Room number is already in use.", 409) from exc
    return success(room.to_dict())


@bp.delete("/rooms/<int:room_id>")
@admin_required
def delete_room(room_id):
    room = db.session.get(Room, room_id)
    if not room:
        raise APIError("not_found", "Room not found.", 404)
    future = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.status != "cancelled",
        Booking.check_out_date > date.today(),
    ).first()
    if future:
        raise APIError(
            "conflict",
            "This room has an upcoming reservation and cannot be removed.",
            409,
        )
    db.session.delete(room)
    db.session.commit()
    return success({"deleted": True})


@bp.patch("/rooms/<int:room_id>/status")
@admin_required
@validate_with(RoomStatusSchema)
def set_room_status(room_id):
    room = db.session.get(Room, room_id)
    if not room:
        raise APIError("not_found", "Room not found.", 404)
    room.status = g.validated["status"]
    db.session.commit()
    return success(room.to_dict())


@bp.get("/bookings")
@admin_required
@validate_with(PaginationSchema, source="query")
def list_bookings():
    data = g.validated
    query = Booking.query.join(User).join(Room)
    if data["status"]:
        query = query.filter(Booking.status == data["status"].lower().replace(" ", "_"))
    if data["search"]:
        term = "%" + data["search"] + "%"
        query = query.filter(
            or_(
                Booking.booking_ref.ilike(term),
                User.name.ilike(term),
                User.email.ilike(term),
                Room.name.ilike(term),
            )
        )
    if data.get("from_date"):
        query = query.filter(Booking.check_in_date >= data["from_date"])
    if data.get("to_date"):
        query = query.filter(Booking.check_out_date <= data["to_date"])
    total = query.count()
    rows = (
        query.order_by(Booking.created_at.desc())
        .offset((data["page"] - 1) * data["per_page"])
        .limit(data["per_page"])
        .all()
    )
    return success(
        {
            "items": [b.to_dict() for b in rows],
            "total": total,
            "page": data["page"],
            "per_page": data["per_page"],
        }
    )


@bp.patch("/bookings/<string:booking_id>/status")
@admin_required
@validate_with(BookingStatusSchema)
def set_booking_status(booking_id):
    booking = (
        db.session.get(Booking, int(booking_id))
        if booking_id.isdigit()
        else Booking.query.filter_by(booking_ref=booking_id).first()
    )
    if not booking:
        raise APIError("not_found", "Reservation not found.", 404)
    status = g.validated["status"]
    if status == "cancelled":
        refund = cancel_booking(booking)
        return success({"booking": booking.to_dict(), **refund})
    allowed = {
        "pending": {"confirmed", "cancelled"},
        "confirmed": {"checked_in", "cancelled"},
        "checked_in": {"checked_out"},
        "checked_out": set(),
        "cancelled": set(),
    }
    if status != booking.status and status not in allowed.get(booking.status, set()):
        raise APIError(
            "conflict", "That reservation status transition is not allowed.", 409
        )
    booking.status = status
    if status == "checked_out":
        award_checkout_points(booking)
        db.session.add(
            Notification(
                user_id=booking.user_id,
                title="Thank you for staying",
                message="Your checkout is complete. Loyalty points have been added to your account.",
            )
        )
    elif status in ("confirmed", "checked_in"):
        db.session.add(
            Notification(
                user_id=booking.user_id,
                title="Reservation update",
                message="Your reservation is now " + status.replace("_", " ") + ".",
            )
        )
    db.session.commit()
    return success(booking.to_dict())


@bp.get("/bookings/export.csv")
@admin_required
def export_bookings():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Reservation",
            "Guest",
            "Email",
            "Room",
            "Check in",
            "Check out",
            "Total",
            "Status",
        ]
    )
    for b in Booking.query.order_by(Booking.created_at.desc()).all():
        writer.writerow(
            [
                b.booking_ref,
                b.user.name,
                b.user.email,
                b.room.name,
                b.check_in_date,
                b.check_out_date,
                b.total_amount,
                b.status,
            ]
        )
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": 'attachment; filename="stayease-bookings.csv"'},
    )


@bp.get("/customers")
@admin_required
@validate_with(PaginationSchema, source="query")
def customers():
    data = g.validated
    query = User.query.filter_by(role="customer")
    if data["search"]:
        term = "%" + data["search"] + "%"
        query = query.filter(or_(User.name.ilike(term), User.email.ilike(term)))
    total = query.count()
    rows = (
        query.order_by(User.created_at.desc())
        .offset((data["page"] - 1) * data["per_page"])
        .limit(data["per_page"])
        .all()
    )
    items = []
    for user in rows:
        record = user.to_dict()
        record["bookings_count"] = len(user.bookings)
        record["total_spent"] = round(
            sum(
                float(b.total_amount)
                for b in user.bookings
                if b.status == "checked_out"
            ),
            2,
        )
        items.append(record)
    return success(
        {
            "items": items,
            "total": total,
            "page": data["page"],
            "per_page": data["per_page"],
        }
    )


@bp.get("/customers/<int:user_id>")
@admin_required
def customer_detail(user_id):
    user = db.session.get(User, user_id)
    if not user or user.role != "customer":
        raise APIError("not_found", "Customer not found.", 404)
    return success(
        {
            "user": user.to_dict(),
            "bookings": [
                b.to_dict()
                for b in Booking.query.filter_by(user_id=user.id)
                .order_by(Booking.created_at.desc())
                .all()
            ],
        }
    )


@bp.patch("/customers/<int:user_id>/active")
@admin_required
def set_customer_active(user_id):
    user = db.session.get(User, user_id)
    if not user or user.role != "customer":
        raise APIError("not_found", "Customer not found.", 404)
    active = request.get_json(silent=True)
    if not isinstance(active, dict) or not isinstance(active.get("is_active"), bool):
        raise APIError("validation_error", "is_active must be a boolean.", 422)
    user.is_active = active["is_active"]
    db.session.commit()
    return success(user.to_dict())


@bp.route("/promos", methods=["GET", "POST"])
@admin_required
def promos_collection():
    if request.method == "GET":
        return success(
            [promo.to_dict() for promo in PromoCode.query.order_by(PromoCode.id).all()]
        )
    from marshmallow import ValidationError

    try:
        data = PromoWriteSchema().load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        raise APIError(
            "validation_error", "Request validation failed.", 422, exc.messages
        ) from exc
    promo = PromoCode(
        code=data["code"].upper(),
        discount_percent=data["discount_percent"],
        min_nights=data["min_nights"],
        valid_to=data["valid_to"],
        max_uses=data["max_uses"],
        is_active=data["is_active"],
    )
    db.session.add(promo)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise APIError("conflict", "Promo code already exists.", 409) from exc
    return success(promo.to_dict(), 201)


@bp.route("/promos/<int:promo_id>", methods=["PUT", "DELETE"])
@admin_required
def promo_item(promo_id):
    promo = db.session.get(PromoCode, promo_id)
    if not promo:
        raise APIError("not_found", "Promo code not found.", 404)
    if request.method == "DELETE":
        db.session.delete(promo)
        db.session.commit()
        return success({"deleted": True})
    from marshmallow import ValidationError

    try:
        data = PromoWriteSchema().load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        raise APIError(
            "validation_error", "Request validation failed.", 422, exc.messages
        ) from exc
    for key in (
        "code",
        "discount_percent",
        "min_nights",
        "valid_to",
        "max_uses",
        "is_active",
    ):
        setattr(promo, key, data[key])
    promo.code = promo.code.upper()
    db.session.commit()
    return success(promo.to_dict())


@bp.route("/settings", methods=["GET", "PUT"])
@admin_required
def settings():
    if request.method == "GET":
        return success({item.key: item.value for item in Setting.query.all()})
    from marshmallow import ValidationError

    try:
        data = SettingSchema().load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        raise APIError(
            "validation_error", "Request validation failed.", 422, exc.messages
        ) from exc
    for key, value in data["settings"].items():
        item = db.session.get(Setting, key)
        if item:
            item.value = value
        else:
            db.session.add(Setting(key=key, value=value))
    db.session.commit()
    return success({item.key: item.value for item in Setting.query.all()})


def _amenities(names):
    result = []
    for name in names:
        item = Amenity.query.filter_by(name=name).first()
        if not item:
            item = Amenity(name=name)
            db.session.add(item)
            db.session.flush()
        result.append(item)
    return result
