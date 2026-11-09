"""Reservation, pricing, and authorization tests."""

from datetime import date, timedelta
from app.extensions import db
from app.models import Booking


def booking_payload(offset=10, nights=2, **extra):
    start = date.today() + timedelta(days=offset)
    end = start + timedelta(days=nights)
    return {
        "room_id": 1,
        "check_in": start.isoformat(),
        "check_out": end.isoformat(),
        "guests": 2,
        **extra,
    }


def test_booking_creation_and_overlap_conflict(client, customer_token, auth_headers):
    headers = auth_headers(customer_token)
    payload = booking_payload()
    response = client.post("/api/bookings", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.get_json()["data"]["total"] == 224.0
    assert (
        client.post("/api/bookings", json=payload, headers=headers).status_code == 409
    )


def test_quote_calculates_promo_and_tax(client, customer_token, auth_headers, app):
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal
    from app.models import PromoCode

    with app.app_context():
        db.session.add(
            PromoCode(
                code="SAVE15",
                discount_percent=Decimal("15"),
                min_nights=2,
                valid_from=datetime.now(timezone.utc) - timedelta(days=1),
                valid_to=datetime.now(timezone.utc) + timedelta(days=30),
                max_uses=5,
            )
        )
        db.session.commit()
    response = client.post(
        "/api/bookings/quote",
        json=booking_payload(extras=["Breakfast"], promo_code="SAVE15"),
        headers=auth_headers(customer_token),
    )
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["subtotal"] == 248.0
    assert data["discount_amount"] == 37.2
    assert data["tax_amount"] == 25.3
    assert data["total"] == 236.1


def test_user_cannot_read_another_customers_reservation(
    client, customer_token, auth_headers, app
):
    from decimal import Decimal
    from app.models import User, Room

    payload = booking_payload()
    first = client.post(
        "/api/bookings", json=payload, headers=auth_headers(customer_token)
    ).get_json()["data"]
    with app.app_context():
        other = User(name="Other Guest", email="other@example.com")
        other.set_password("Otherpass123!")
        db.session.add(other)
        db.session.flush()
        room = Room.query.filter_by(room_number="101").first()
        booking = Booking(
            booking_ref="BK-PRIVATE",
            user=other,
            room=room,
            check_in_date=date.today() + timedelta(days=20),
            check_out_date=date.today() + timedelta(days=21),
            guests=1,
            nights=1,
            subtotal=Decimal("100"),
            tax_amount=Decimal("12"),
            discount_amount=Decimal("0"),
            total_amount=Decimal("112"),
            status="confirmed",
        )
        db.session.add(booking)
        db.session.commit()
    assert (
        client.get(
            "/api/bookings/BK-PRIVATE", headers=auth_headers(customer_token)
        ).status_code
        == 404
    )
    assert first["booking_ref"].startswith("BK-")


def test_cancellation_refund(client, customer_token, auth_headers):
    headers = auth_headers(customer_token)
    payload = booking_payload(offset=1, nights=1)
    created = client.post("/api/bookings", json=payload, headers=headers).get_json()[
        "data"
    ]
    result = client.post("/api/bookings/" + created["id"] + "/cancel", headers=headers)
    assert result.status_code == 200
    assert result.get_json()["data"]["refund_percent"] == 50
