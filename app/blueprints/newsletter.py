"""Newsletter subscription."""

from flask import Blueprint, g
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import NewsletterSubscriber
from app.schemas import NewsletterSchema
from app.utils.decorators import validate_with
from app.utils.responses import success

bp = Blueprint("newsletter", __name__, url_prefix="/api/newsletter")


@bp.post("/subscribe")
@validate_with(NewsletterSchema)
def subscribe():
    email = g.validated["email"].lower()
    if not NewsletterSubscriber.query.filter_by(email=email).first():
        db.session.add(NewsletterSubscriber(email=email))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
    return success(
        {"subscribed": True, "message": "You are on the StayEase list."}, 201
    )
