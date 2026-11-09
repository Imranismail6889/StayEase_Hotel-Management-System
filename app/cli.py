"""Database setup, seed, and reset commands."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import os
import secrets
import click
from app.extensions import db
from app.models import (
    Amenity,
    Booking,
    LoyaltyTransaction,
    PromoCode,
    Review,
    Room,
    Setting,
    User,
)
from app.services.payment_service import create_payment


def register_cli(app):
    @app.cli.command("seed")
    def seed_command():
        """Create tables and insert demo data."""
        production = _is_deployment_environment()
        admin_password = os.getenv("STAYEASE_ADMIN_PASSWORD")
        if production and (not admin_password or len(admin_password) < 16):
            raise click.ClickException(
                "Set STAYEASE_ADMIN_PASSWORD to a unique value of at least 16 characters before production seeding."
            )
        db.create_all()
        _seed(
            admin_password=admin_password if production else None,
            guest_password=(
                (os.getenv("STAYEASE_GUEST_PASSWORD") or secrets.token_urlsafe(32))
                if production
                else None
            ),
            randomize_customer_passwords=production,
        )
        click.echo("StayEase demo data is ready.")

    @app.cli.command("reset-db")
    def reset_db_command():
        """Drop tables, recreate the schema, and seed demo data."""
        if _is_deployment_environment():
            raise click.ClickException(
                "reset-db is disabled in production and preview deployments."
            )
        db.drop_all()
        db.create_all()
        _seed()
        click.echo("StayEase database reset and seeded.")


def _is_deployment_environment():
    return os.getenv(
        "APP_ENV", os.getenv("VERCEL_ENV", os.getenv("FLASK_ENV", "development"))
    ).lower() in {"production", "preview"}


def _seed(admin_password=None, guest_password=None, randomize_customer_passwords=False):
    if User.query.first():
        return
    admin = User(
        name="Avery Chen",
        email="admin@stayease.com",
        phone="+1 (415) 555-0100",
        role="admin",
    )
    admin.set_password(admin_password or "Admin@123")
    demo = User(
        name="Olivia Martin", email="guest@stayease.com", phone="+1 (415) 555-0128"
    )
    demo.set_password(guest_password or "Guest@123")
    db.session.add_all([admin, demo])
    names = [
        ("James Wilson", "james.wilson@example.com"),
        ("Aisha Patel", "aisha.patel@example.com"),
        ("Noah Kim", "noah.kim@example.com"),
        ("Sofia Ramirez", "sofia.ramirez@example.com"),
        ("Maya Robinson", "maya.robinson@example.com"),
        ("Daniel Cooper", "daniel.cooper@example.com"),
        ("Priya Shah", "priya.shah@example.com"),
        ("Ethan Brooks", "ethan.brooks@example.com"),
        ("Lena Fischer", "lena.fischer@example.com"),
        ("Mateo Garcia", "mateo.garcia@example.com"),
    ]
    customers = [demo]
    for name, email in names:
        user = User(name=name, email=email)
        user.set_password(
            secrets.token_urlsafe(32) if randomize_customer_passwords else "Guest@123"
        )
        db.session.add(user)
        customers.append(user)
    amenity_names = [
        "WiFi",
        "AC",
        "TV",
        "Mini-bar",
        "Jacuzzi",
        "Sea View",
        "Balcony",
        "Breakfast",
        "Butler",
    ]
    amenity_icons = ["⌁", "❄", "▣", "♢", "♨", "🌊", "⌂", "☕", "♧"]
    amenities = {}
    for name, icon in zip(amenity_names, amenity_icons):
        item = Amenity(name=name, icon=icon)
        db.session.add(item)
        amenities[name] = item
    specs = [
        ("101", "Courtyard King", "Standard", 79, 2, 1, ["WiFi", "AC", "TV"]),
        ("102", "Willow Twin", "Standard", 89, 2, 1, ["WiFi", "AC", "TV", "Breakfast"]),
        ("103", "Garden Queen", "Standard", 99, 2, 1, ["WiFi", "AC", "Balcony"]),
        ("104", "Harbor Single", "Standard", 109, 1, 1, ["WiFi", "AC", "Sea View"]),
        (
            "105",
            "Cedar Double",
            "Standard",
            119,
            2,
            1,
            ["WiFi", "AC", "TV", "Mini-bar"],
        ),
        (
            "201",
            "The Atelier Room",
            "Deluxe",
            149,
            2,
            2,
            ["WiFi", "AC", "TV", "Mini-bar", "Breakfast"],
        ),
        (
            "202",
            "Ocean Terrace",
            "Deluxe",
            179,
            2,
            2,
            ["WiFi", "AC", "Sea View", "Balcony"],
        ),
        (
            "203",
            "Palm Residence",
            "Deluxe",
            199,
            3,
            2,
            ["WiFi", "AC", "Balcony", "Breakfast"],
        ),
        (
            "204",
            "Saffron Family",
            "Deluxe",
            219,
            4,
            2,
            ["WiFi", "AC", "TV", "Mini-bar"],
        ),
        (
            "205",
            "The Heritage Loft",
            "Deluxe",
            239,
            3,
            2,
            ["WiFi", "AC", "TV", "Balcony"],
        ),
        (
            "301",
            "The Garden Suite",
            "Suite",
            269,
            2,
            3,
            ["WiFi", "AC", "TV", "Mini-bar", "Breakfast", "Butler"],
        ),
        (
            "302",
            "Skyline Suite",
            "Suite",
            289,
            3,
            3,
            ["WiFi", "AC", "TV", "Sea View", "Balcony"],
        ),
        (
            "303",
            "Jacuzzi Suite",
            "Suite",
            319,
            2,
            3,
            ["WiFi", "AC", "Jacuzzi", "Mini-bar"],
        ),
        (
            "304",
            "Ocean Grand Suite",
            "Suite",
            339,
            4,
            3,
            ["WiFi", "AC", "Sea View", "Balcony", "Butler"],
        ),
        (
            "305",
            "Willow Penthouse",
            "Suite",
            359,
            4,
            3,
            ["WiFi", "AC", "Jacuzzi", "Balcony", "Breakfast", "Butler"],
        ),
        (
            "401",
            "Coastal Penthouse",
            "Suite",
            379,
            4,
            4,
            ["WiFi", "AC", "Sea View", "Balcony", "Butler"],
        ),
        (
            "402",
            "Presidential Suite",
            "Suite",
            399,
            5,
            4,
            ["WiFi", "AC", "TV", "Mini-bar", "Jacuzzi", "Butler"],
        ),
        (
            "403",
            "Sunset Suite",
            "Suite",
            329,
            3,
            4,
            ["WiFi", "AC", "Sea View", "Breakfast"],
        ),
        (
            "404",
            "Garden Spa Suite",
            "Suite",
            309,
            2,
            4,
            ["WiFi", "AC", "Jacuzzi", "Breakfast"],
        ),
        (
            "405",
            "Family Panorama",
            "Suite",
            349,
            5,
            4,
            ["WiFi", "AC", "TV", "Sea View", "Balcony"],
        ),
    ]
    rooms = []
    descriptions = [
        "A considered retreat with warm natural finishes, soft linens, and the comforts you need to feel at home.",
        "A calm, light-filled room with thoughtful details and space to unwind after a day of exploring.",
        "Settle into generous comfort, attentive service, and a quiet view across the hotel grounds.",
    ]
    icons = ["🛏️", "🌊", "🌿", "✨", "🪟"]
    for index, spec in enumerate(specs):
        number, name, room_type, price, capacity, floor, amenity_list = spec
        room = Room(
            room_number=number,
            name=name,
            room_type=room_type,
            price_per_night=Decimal(str(price)),
            capacity=capacity,
            floor=floor,
            status="maintenance" if number == "104" else "available",
            description=descriptions[index % 3],
            image_urls=[icons[index % 5]],
        )
        room.amenities = [amenities[item] for item in amenity_list]
        rooms.append(room)
        db.session.add(room)
    now = datetime.now(timezone.utc)
    for code, discount, minimum, valid_to in [
        ("STAY15", 15, 3, now + timedelta(days=365)),
        ("WELCOME10", 10, 1, now + timedelta(days=365)),
        ("LONGSTAY20", 20, 5, now + timedelta(days=365)),
        ("EXPIRED5", 5, 1, now - timedelta(days=3)),
    ]:
        db.session.add(
            PromoCode(
                code=code,
                discount_percent=Decimal(discount),
                min_nights=minimum,
                valid_from=now - timedelta(days=30),
                valid_to=valid_to,
                max_uses=500,
            )
        )
    db.session.add_all(
        [
            Setting(key="tax_rate", value="12"),
            Setting(key="currency", value="USD"),
            Setting(key="hotel_name", value="StayEase Hotel"),
        ]
    )
    db.session.flush()
    today = date.today()
    for index in range(32):
        customer, room = customers[index % len(customers)], rooms[index % len(rooms)]
        check_in = today - timedelta(days=20 + index * 5)
        nights = 1 + index % 4
        subtotal = Decimal(room.price_per_night) * nights
        booking = Booking(
            booking_ref="BK-SEED-" + str(index + 1).zfill(4),
            user=customer,
            room=room,
            check_in_date=check_in,
            check_out_date=check_in + timedelta(days=nights),
            guests=min(room.capacity, 1 + index % min(room.capacity, 3)),
            nights=nights,
            subtotal=subtotal,
            tax_amount=(subtotal * Decimal("0.12")).quantize(Decimal("0.01")),
            discount_amount=Decimal("0.00"),
            total_amount=(subtotal * Decimal("1.12")).quantize(Decimal("0.01")),
            status="checked_out",
            special_requests="",
        )
        db.session.add(booking)
        db.session.flush()
        db.session.add(
            create_payment(booking, booking.total_amount, "credit_card", "4242", "Visa")
        )
        points = int(booking.total_amount)
        customer.loyalty_points += points
        db.session.add(
            LoyaltyTransaction(
                user_id=customer.id,
                points=points,
                reason="Historical checkout",
                booking_id=booking.id,
            )
        )
        if index % 3 == 0:
            db.session.add(
                Review(
                    user=customer,
                    room=room,
                    booking=booking,
                    rating=4 + (index % 2),
                    comment="A welcoming stay from start to finish. We would happily return.",
                )
            )
    for customer in customers:
        customer.loyalty_tier = (
            "Platinum"
            if customer.loyalty_points >= 5000
            else "Gold" if customer.loyalty_points >= 1000 else "Silver"
        )
    db.session.commit()
