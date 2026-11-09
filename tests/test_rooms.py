"""Room filter and availability tests."""

from datetime import date, timedelta
from decimal import Decimal
from app.extensions import db
from app.models import Booking, User, Room


def test_room_filters_and_sorting(client):
    response = client.get(
        "/api/rooms?type=Deluxe&min_price=90&max_price=150&sort=price_asc"
    )
    assert response.status_code == 200
    items = response.get_json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Garden Room"


def test_availability_excludes_overlapping_booking(app, client):
    today = date.today()
    with app.app_context():
        guest = User.query.filter_by(email="guest@example.com").first()
        room = Room.query.filter_by(room_number="101").first()
        booking = Booking(
            booking_ref="BK-EXISTING",
            user=guest,
            room=room,
            check_in_date=today + timedelta(days=3),
            check_out_date=today + timedelta(days=5),
            guests=1,
            nights=2,
            subtotal=Decimal("200"),
            tax_amount=Decimal("24"),
            discount_amount=Decimal("0"),
            total_amount=Decimal("224"),
            status="confirmed",
        )
        db.session.add(booking)
        db.session.commit()
    response = client.get(
        "/api/rooms?check_in="
        + (today + timedelta(days=4)).isoformat()
        + "&check_out="
        + (today + timedelta(days=6)).isoformat()
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["items"] == []
