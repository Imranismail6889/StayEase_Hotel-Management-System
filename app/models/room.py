"""Rooms, amenities, and their association."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Table,
    Column,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db

room_amenities = Table(
    "room_amenities",
    db.metadata,
    Column(
        "room_id",
        ForeignKey("rooms.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
    Column(
        "amenity_id",
        ForeignKey("amenities.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    ),
)


class Amenity(db.Model):
    __tablename__ = "amenities"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    icon: Mapped[str] = mapped_column(String(24), default="✧", nullable=False)


class Room(db.Model):
    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint(
            "room_type IN ('Standard','Deluxe','Suite')", name="ck_rooms_type"
        ),
        CheckConstraint(
            "status IN ('available','occupied','maintenance')", name="ck_rooms_status"
        ),
        CheckConstraint("price_per_night >= 0", name="ck_rooms_price"),
        CheckConstraint("capacity > 0", name="ck_rooms_capacity"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    room_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    room_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(1200), default="", nullable=False)
    price_per_night: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    floor: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="available", nullable=False, index=True
    )
    image_urls: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    amenities = relationship("Amenity", secondary=room_amenities, lazy="selectin")
    bookings = relationship("Booking", back_populates="room")
    reviews = relationship("Review", back_populates="room")

    @property
    def type(self):
        return self.room_type

    def to_dict(self) -> dict:
        ratings = [review.rating for review in self.reviews]
        average = round(sum(ratings) / len(ratings), 1) if ratings else 0.0
        return {
            "id": self.id,
            "room_number": self.room_number,
            "name": self.name,
            "room": self.name,
            "type": self.room_type,
            "room_type": self.room_type,
            "description": self.description,
            "price": float(self.price_per_night),
            "price_per_night": float(self.price_per_night),
            "capacity": self.capacity,
            "floor": self.floor,
            "status": self.status.title(),
            "status_code": self.status,
            "image_urls": self.image_urls or [],
            "amenities": [a.name for a in self.amenities],
            "rating": average,
            "reviews": len(ratings),
            "emoji": (self.image_urls or ["🛏️"])[0] if self.image_urls else "🛏️",
            "art": "linear-gradient(135deg,#d9c6a7,#998365)",
            "booked": [],
        }
