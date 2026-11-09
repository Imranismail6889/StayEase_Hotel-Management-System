"""Admin dashboard aggregates."""

from datetime import date, timedelta
from sqlalchemy import func
from app.models import Booking, Room, User


def dashboard_stats():
    today = date.today()
    six_months_ago = today.replace(day=1) - timedelta(days=180)
    revenue = (
        Booking.query.filter(Booking.status == "checked_out")
        .with_entities(func.coalesce(func.sum(Booking.total_amount), 0))
        .scalar()
    )
    active = Booking.query.filter(
        Booking.status.in_(["confirmed", "checked_in"])
    ).count()
    customer_count = User.query.filter_by(role="customer").count()
    total_rooms = Room.query.count()
    in_house = Booking.query.filter(Booking.status == "checked_in").count()
    occupancy = round(100 * in_house / total_rooms, 1) if total_rooms else 0
    cancelled = Booking.query.filter_by(status="cancelled").count()
    all_bookings = Booking.query.count()
    rows = Booking.query.filter(
        Booking.status == "checked_out", Booking.check_out_date >= six_months_ago
    ).all()
    monthly = {}
    for booking in rows:
        key = booking.check_out_date.strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + float(booking.total_amount)
    status_counts = {
        status: Room.query.filter_by(status=status).count()
        for status in ["available", "occupied", "maintenance"]
    }
    type_perf = {}
    for room in Room.query.all():
        type_perf[room.room_type] = type_perf.get(room.room_type, 0) + sum(
            float(b.total_amount) for b in room.bookings if b.status == "checked_out"
        )
    return {
        "total_revenue": float(revenue or 0),
        "active_bookings": active,
        "occupancy_rate": occupancy,
        "total_customers": customer_count,
        "revenue_by_month": monthly,
        "room_status_counts": status_counts,
        "room_type_performance": type_perf,
        "cancellation_rate": (
            round(cancelled * 100 / all_bookings, 1) if all_bookings else 0
        ),
    }
