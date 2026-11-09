"""Customer reservation lifecycle."""

from flask import Blueprint, Response, g

from app.extensions import db
from app.models import Booking
from app.schemas import BookingSchema, ModifyBookingSchema, QuoteSchema
from app.services.booking_service import (
    cancel_booking,
    create_booking,
    EXTRAS,
    is_available,
    quote,
)
from app.services.ics_service import make_ics
from app.services.invoice_service import render_invoice
from app.utils.decorators import authenticated, validate_with
from app.utils.errors import APIError
from app.utils.responses import success

bp = Blueprint("bookings", __name__, url_prefix="/api/bookings")


def _find_booking(booking_id):
    if str(booking_id).isdigit():
        return db.session.get(Booking, int(booking_id))
    return Booking.query.filter_by(booking_ref=booking_id).first()


def _owned(booking_id):
    booking = _find_booking(booking_id)
    if not booking:
        raise APIError("not_found", "Reservation not found.", 404)
    if booking.user_id != g.current_user.id and g.current_user.role != "admin":
        raise APIError("not_found", "Reservation not found.", 404)
    return booking


@bp.post("/quote")
@authenticated
@validate_with(QuoteSchema)
def booking_quote():
    return success(quote(g.current_user, g.validated))


@bp.post("")
@bp.post("/")
@authenticated
@validate_with(BookingSchema)
def create():
    booking = create_booking(g.current_user, g.validated)
    return success(booking.to_dict(), 201)


@bp.get("")
@bp.get("/")
@authenticated
def list_mine():
    status = __import__("flask").request.args.get("status")
    query = Booking.query.filter_by(user_id=g.current_user.id)
    if status:
        query = query.filter_by(status=status.lower().replace(" ", "_"))
    return success(
        [b.to_dict() for b in query.order_by(Booking.check_in_date.desc()).all()]
    )


@bp.get("/<string:booking_id>")
@authenticated
def detail(booking_id):
    return success(_owned(booking_id).to_dict())


@bp.put("/<string:booking_id>/modify")
@authenticated
@validate_with(ModifyBookingSchema)
def modify(booking_id):
    booking = _owned(booking_id)
    data = g.validated
    if booking.status != "confirmed":
        raise APIError("conflict", "Only confirmed reservations can be modified.", 409)
    if not is_available(
        booking.room_id, data["check_in"], data["check_out"], booking.id
    ):
        raise APIError(
            "conflict", "The room is no longer available for those dates.", 409
        )
    pricing = quote(
        g.current_user,
        {
            "room_id": booking.room_id,
            "check_in": data["check_in"],
            "check_out": data["check_out"],
            "guests": data.get("guests") or booking.guests,
            "extras": [e.extra_name for e in booking.extras],
            "promo_code": booking.promo_code,
        },
        check_availability=False,
    )
    booking.check_in_date, booking.check_out_date = data["check_in"], data["check_out"]
    booking.guests, booking.nights = (
        data.get("guests") or booking.guests,
        pricing["nights"],
    )
    booking.subtotal, booking.tax_amount = pricing["subtotal"], pricing["tax_amount"]
    booking.discount_amount, booking.total_amount = (
        pricing["discount_amount"],
        pricing["total"],
    )
    for extra in booking.extras:
        extra.price = EXTRAS[extra.extra_name] * pricing["nights"]
    db.session.commit()
    return success(booking.to_dict())


@bp.post("/<string:booking_id>/cancel")
@authenticated
def cancel(booking_id):
    return success(cancel_booking(_owned(booking_id)))


@bp.get("/<string:booking_id>/invoice")
@authenticated
def invoice(booking_id):
    booking = _owned(booking_id)
    return Response(render_invoice(booking), mimetype="text/html")


@bp.get("/<string:booking_id>/calendar.ics")
@authenticated
def calendar(booking_id):
    booking = _owned(booking_id)
    return Response(
        make_ics(booking),
        mimetype="text/calendar",
        headers={
            "Content-Disposition": 'attachment; filename="'
            + booking.booking_ref
            + '.ics"'
        },
    )
