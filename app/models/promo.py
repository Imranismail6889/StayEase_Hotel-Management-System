"""Discount codes."""

from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import Boolean, DateTime, Integer, String, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.extensions import db


class PromoCode(db.Model):
    __tablename__ = "promo_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(
        String(40), unique=True, nullable=False, index=True
    )
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    min_nights: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    valid_to: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_uses: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "discount_percent": float(self.discount_percent),
            "min_nights": self.min_nights,
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat(),
            "max_uses": self.max_uses,
            "used_count": self.used_count,
            "is_active": self.is_active,
        }
