"""Promo validation endpoint."""

from flask import Blueprint, g
from app.models import PromoCode
from app.schemas import PromoValidateSchema
from app.utils.decorators import validate_with
from app.utils.responses import success

bp = Blueprint("promos", __name__, url_prefix="/api/promos")


@bp.post("/validate")
@validate_with(PromoValidateSchema)
def validate():
    data = g.validated
    promo = PromoCode.query.filter_by(code=data["code"].upper()).first()
    valid = bool(
        promo
        and promo.is_active
        and promo.used_count < promo.max_uses
        and promo.min_nights <= data["nights"]
    )
    if valid:
        from datetime import datetime, timezone

        start, end = promo.valid_from, promo.valid_to
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        valid = start <= now <= end
    return success(
        {
            "valid": valid,
            "code": promo.code if valid else data["code"].upper(),
            "discount_percent": float(promo.discount_percent) if valid else 0,
            "reason": (
                ""
                if valid
                else "The code is invalid, expired, or does not meet its minimum stay."
            ),
        }
    )
