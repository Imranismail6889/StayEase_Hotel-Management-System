"""Verified booking review submission."""

from flask import Blueprint, g
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Booking, Review
from app.schemas import ReviewSchema
from app.utils.decorators import authenticated, validate_with
from app.utils.errors import APIError
from app.utils.responses import success

bp = Blueprint("reviews", __name__, url_prefix="/api/reviews")


@bp.get("")
@authenticated
def list_reviews():
    items = (
        Review.query.filter_by(user_id=g.current_user.id)
        .order_by(Review.created_at.desc())
        .limit(100)
        .all()
    )
    return success({"items": [item.to_dict() for item in items]})


@bp.post("")
@bp.post("/")
@authenticated
@validate_with(ReviewSchema)
def create_review():
    data = g.validated
    booking = Booking.query.filter_by(
        id=data["booking_id"], user_id=g.current_user.id
    ).first()
    if not booking:
        raise APIError("not_found", "Completed reservation not found.", 404)
    if booking.status != "checked_out":
        raise APIError("forbidden", "Reviews are available after checkout.", 403)
    review = Review(
        user_id=g.current_user.id,
        room_id=booking.room_id,
        booking_id=booking.id,
        rating=data["rating"],
        comment=data.get("comment", ""),
    )
    db.session.add(review)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise APIError(
            "conflict", "A review has already been submitted for this stay.", 409
        ) from exc
    return success(review.to_dict(), 201)
