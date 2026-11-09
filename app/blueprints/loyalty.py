"""Authenticated loyalty account and points history."""

from flask import Blueprint, g

from app.models import LoyaltyTransaction
from app.utils.decorators import authenticated
from app.utils.responses import success

bp = Blueprint("loyalty", __name__, url_prefix="/api/loyalty")


@bp.get("")
@authenticated
def list_transactions():
    transactions = (
        LoyaltyTransaction.query.filter_by(user_id=g.current_user.id)
        .order_by(LoyaltyTransaction.created_at.desc())
        .limit(100)
        .all()
    )
    return success(
        {
            "points": g.current_user.loyalty_points,
            "tier": g.current_user.loyalty_tier,
            "items": [
                {
                    "id": item.id,
                    "points": item.points,
                    "reason": item.reason,
                    "booking_id": item.booking_id,
                    "created_at": item.created_at.isoformat(),
                }
                for item in transactions
            ],
        }
    )
