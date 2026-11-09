"""Loyalty point accrual."""

from app.extensions import db
from app.models import LoyaltyTransaction


def award_checkout_points(booking):
    points = int(booking.total_amount)
    user = booking.user
    user.loyalty_points += points
    user.loyalty_tier = (
        "Platinum"
        if user.loyalty_points >= 5000
        else "Gold" if user.loyalty_points >= 1000 else "Silver"
    )
    db.session.add(
        LoyaltyTransaction(
            user_id=user.id,
            points=points,
            reason="Reservation checkout",
            booking_id=booking.id,
        )
    )
