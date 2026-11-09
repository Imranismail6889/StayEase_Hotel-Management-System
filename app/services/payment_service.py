"""Mock payment gateway interface."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from app.models import Payment


def create_payment(
    booking, amount: Decimal, method: str, card_last4: str = "", card_brand: str = ""
) -> Payment:
    """Create a simulated payment record; raw card data is never accepted or stored."""
    return Payment(
        booking=booking,
        amount=amount,
        method=method,
        status="paid",
        transaction_ref="MOCK-" + uuid4().hex[:16].upper(),
        card_last4=card_last4,
        card_brand=card_brand,
        paid_at=datetime.now(timezone.utc),
    )


def confirm_payment(payment: Payment) -> Payment:
    """Confirm a mock transaction."""
    payment.status = "paid"
    payment.paid_at = datetime.now(timezone.utc)
    return payment


def refund_payment(payment: Payment, amount: Decimal) -> str:
    """Record a mock refund and return its reference."""
    payment.status = "refunded"
    payment.amount = amount
    return "REF-" + uuid4().hex[:16].upper()
