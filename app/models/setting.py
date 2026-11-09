"""Key/value hotel settings."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.extensions import db


class Setting(db.Model):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
