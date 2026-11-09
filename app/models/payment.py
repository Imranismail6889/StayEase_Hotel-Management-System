"""Payment records, without storing card numbers."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Payment(db.Model):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "method IN ('credit_card','debit_card','upi','net_banking')",
            name="ck_payment_method",
        ),
        CheckConstraint(
            "status IN ('pending','paid','failed','refunded')", name="ck_payment_status"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="paid", nullable=False)
    transaction_ref: Mapped[str] = mapped_column(
        String(80), unique=True, nullable=False
    )
    card_last4: Mapped[str] = mapped_column(String(4), default="", nullable=False)
    card_brand: Mapped[str] = mapped_column(String(24), default="", nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    booking = relationship("Booking", back_populates="payments")
