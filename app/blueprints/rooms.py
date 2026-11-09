"""Public room discovery and reviews."""

from flask import Blueprint, g

from app.extensions import db
from app.models import Amenity, Booking, Review, Room
from app.schemas import DateRangeSchema, RoomQuerySchema
from app.services.booking_service import is_available
from app.utils.decorators import validate_with
from app.utils.errors import APIError
from app.utils.responses import success

bp = Blueprint("rooms", __name__, url_prefix="/api/rooms")


@bp.get("")
@bp.get("/")
@validate_with(RoomQuerySchema, source="query")
def list_rooms():
    data = g.validated
    query = Room.query
    if data.get("type"):
        query = query.filter(Room.room_type == data["type"])
    if data.get("status"):
        status = data["status"].lower()
        query = query.filter(Room.status == status)
    if data.get("min_price") is not None:
        query = query.filter(Room.price_per_night >= data["min_price"])
    if data.get("max_price") is not None:
        query = query.filter(Room.price_per_night <= data["max_price"])
    if data.get("capacity"):
        query = query.filter(Room.capacity >= data["capacity"])
    amenity_names = [
        name.strip() for name in data.get("amenities", "").split(",") if name.strip()
    ]
    for name in amenity_names:
        query = query.filter(Room.amenities.any(Amenity.name.ilike("%" + name + "%")))
    rows = query.all()
    if data.get("check_in") or data.get("check_out"):
        if (
            not data.get("check_in")
            or not data.get("check_out")
            or data["check_out"] <= data["check_in"]
        ):
            raise APIError(
                "validation_error",
                "Both valid check_in and check_out dates are required.",
                422,
            )
        rows = [
            room
            for room in rows
            if room.status == "available"
            and is_available(room.id, data["check_in"], data["check_out"])
        ]
    sort = data.get("sort")
    if sort == "price_asc":
        rows.sort(key=lambda r: r.price_per_night)
    elif sort == "price_desc":
        rows.sort(key=lambda r: r.price_per_night, reverse=True)
    elif sort == "capacity":
        rows.sort(key=lambda r: r.capacity, reverse=True)
    elif sort == "rating":
        rows.sort(key=lambda r: r.to_dict()["rating"], reverse=True)
    total = len(rows)
    start = (data["page"] - 1) * data["per_page"]
    page_items = rows[start : start + data["per_page"]]
    return success(
        {
            "items": [r.to_dict() for r in page_items],
            "page": data["page"],
            "per_page": data["per_page"],
            "total": total,
            "pages": (total + data["per_page"] - 1) // data["per_page"],
        }
    )


@bp.get("/<int:room_id>")
def room_detail(room_id):
    room = db.session.get(Room, room_id)
    if not room:
        raise APIError("not_found", "Room not found.", 404)
    data = room.to_dict()
    data["reviews_list"] = [
        review.to_dict()
        for review in Review.query.filter_by(room_id=room_id)
        .order_by(Review.created_at.desc())
        .limit(20)
    ]
    return success(data)


@bp.get("/<int:room_id>/availability")
@validate_with(DateRangeSchema, source="query")
def room_availability(room_id):
    room = db.session.get(Room, room_id)
    if not room:
        raise APIError("not_found", "Room not found.", 404)
    dates = g.validated
    if dates["to_date"] <= dates["from_date"]:
        raise APIError(
            "validation_error", "The end date must follow the start date.", 422
        )
    bookings = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.status != "cancelled",
        Booking.check_in_date < dates["to_date"],
        Booking.check_out_date > dates["from_date"],
    ).all()
    return success(
        {
            "room_id": room_id,
            "booked_ranges": [
                {
                    "from": b.check_in_date.isoformat(),
                    "to": b.check_out_date.isoformat(),
                }
                for b in bookings
            ],
        }
    )


@bp.get("/<int:room_id>/reviews")
def room_reviews(room_id):
    room = db.session.get(Room, room_id)
    if not room:
        raise APIError("not_found", "Room not found.", 404)
    reviews = (
        Review.query.filter_by(room_id=room_id).order_by(Review.created_at.desc()).all()
    )
    breakdown = {
        rating: sum(1 for review in reviews if review.rating == rating)
        for rating in range(1, 6)
    }
    return success(
        {"items": [review.to_dict() for review in reviews], "breakdown": breakdown}
    )
