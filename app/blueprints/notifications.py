"""User notification inbox."""

from flask import Blueprint, g
from app.extensions import db
from app.models import Notification
from app.utils.decorators import authenticated
from app.utils.errors import APIError
from app.utils.responses import success

bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@bp.get("")
@authenticated
def list_notifications():
    rows = (
        Notification.query.filter_by(user_id=g.current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(100)
    )
    items = rows.all()
    return success(
        {
            "items": [item.to_dict() for item in items],
            "unread_count": sum(not item.is_read for item in items),
        }
    )


@bp.put("/<int:notification_id>/read")
@authenticated
def mark_read(notification_id):
    item = Notification.query.filter_by(
        id=notification_id, user_id=g.current_user.id
    ).first()
    if not item:
        raise APIError("not_found", "Notification not found.", 404)
    item.is_read = True
    db.session.commit()
    return success(item.to_dict())


@bp.put("/read-all")
@authenticated
def mark_all_read():
    Notification.query.filter_by(user_id=g.current_user.id, is_read=False).update(
        {"is_read": True}
    )
    db.session.commit()
    return success({"updated": True})
