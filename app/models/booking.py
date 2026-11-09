"""Reservations and selected extras."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class Booking(db.Model):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','confirmed','checked_in','checked_out','cancelled')",
            name="ck_bookings_status",
        ),
        CheckConstraint("guests > 0 AND nights > 0", name="ck_bookings_stay"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_ref: Mapped[str] = mapped_column(
        String(24), unique=True, nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    room_id: Mapped[int | None] = mapped_column(
        ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True, index=True
    )
    check_in_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    check_out_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    guests: Mapped[int] = mapped_column(Integer, nullable=False)
    nights: Mapped[int] = mapped_column(Integer, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=0, nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    promo_code: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="confirmed", nullable=False, index=True
    )
    special_requests: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="bookings")
    room = relationship("Room", back_populates="bookings")
    extras = relationship(
        "BookingExtra", back_populates="booking", cascade="all, delete-orphan"
    )
    payments = relationship(
        "Payment", back_populates="booking", cascade="all, delete-orphan"
    )
    reviews = relationship(
        "Review", back_populates="booking", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.booking_ref,
            "booking_ref": self.booking_ref,
            "numeric_id": self.id,
            "room_id": self.room_id,
            "room": self.room.name if self.room else "Removed room",
            "user_id": self.user_id,
            "guest": self.user.name if self.user else "",
            "email": self.user.email if self.user else "",
            "checkin": self.check_in_date.isoformat(),
            "checkout": self.check_out_date.isoformat(),
            "check_in_date": self.check_in_date.isoformat(),
            "check_out_date": self.check_out_date.isoformat(),
            "dates": self.check_in_date.strftime("%b %d")
            + " – "
            + self.check_out_date.strftime("%b %d, %Y"),
            "guests": self.guests,
            "nights": self.nights,
            "subtotal": float(self.subtotal),
            "tax_amount": float(self.tax_amount),
            "discount_amount": float(self.discount_amount),
            "total": float(self.total_amount),
            "total_amount": float(self.total_amount),
            "promo_code": self.promo_code,
            "status": self.status.replace("_", " ").title(),
            "status_code": self.status,
            "special_requests": self.special_requests,
            "extras": [
                {"name": e.extra_name, "price": float(e.price)} for e in self.extras
            ],
        }


class BookingExtra(db.Model):
    __tablename__ = "booking_extras"
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    extra_name: Mapped[str] = mapped_column(String(80), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    booking = relationship("Booking", back_populates="extras")
