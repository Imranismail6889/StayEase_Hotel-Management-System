"""Verified-stay reviews."""

from datetime import datetime, timezone
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.extensions import db


class Review(db.Model):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_review_rating"),
        UniqueConstraint("user_id", "booking_id", name="uq_review_user_booking"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    user = relationship("User", back_populates="reviews")
    room = relationship("Room", back_populates="reviews")
    booking = relationship("Booking", back_populates="reviews")

    def to_dict(self):
        return {
            "id": self.id,
            "user": self.user.name if self.user else "Guest",
            "name": self.user.name if self.user else "Guest",
            "room_id": self.room_id,
            "booking_id": self.booking_id,
            "rating": self.rating,
            "comment": self.comment,
            "text": self.comment,
            "created_at": self.created_at.isoformat(),
        }
