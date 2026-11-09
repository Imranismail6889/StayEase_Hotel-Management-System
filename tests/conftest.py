"""Shared app and authentication fixtures."""

from decimal import Decimal
import pytest
from app import create_app
from app.extensions import db
from app.models import Room, Setting, User


@pytest.fixture()
def app():
    app = create_app("config.TestConfig")
    with app.app_context():
        db.create_all()
        db.session.add_all(
            [Setting(key="tax_rate", value="12"), Setting(key="currency", value="USD")]
        )
        guest = User(name="Test Guest", email="guest@example.com")
        guest.set_password("Guestpass123!")
        admin = User(name="Test Admin", email="admin@example.com", role="admin")
        admin.set_password("Adminpass123!")
        room = Room(
            room_number="101",
            name="Garden Room",
            room_type="Deluxe",
            description="A quiet room.",
            price_per_night=Decimal("100.00"),
            capacity=2,
            floor=1,
            status="available",
            image_urls=["🛏️"],
        )
        db.session.add_all([guest, admin, room])
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def customer_token(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "guest@example.com", "password": "Guestpass123!"},
    )
    return response.get_json()["data"]["token"]


@pytest.fixture()
def admin_token(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "Adminpass123!"},
    )
    return response.get_json()["data"]["token"]


@pytest.fixture()
def auth_headers():
    def make(token):
        return {"Authorization": "Bearer " + token}

    return make
