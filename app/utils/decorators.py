"""Authentication, authorization, and request validation helpers."""

from functools import wraps

from flask import g, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from marshmallow import ValidationError

from app.extensions import db
from app.models import User
from app.utils.errors import APIError


def validate_with(schema, source="json"):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            raw = (
                request.get_json(silent=True) or {}
                if source == "json"
                else request.args.to_dict(flat=True)
            )
            try:
                g.validated = schema().load(raw)
            except ValidationError as exc:
                raise APIError(
                    "validation_error", "Request validation failed.", 422, exc.messages
                ) from exc
            return fn(*args, **kwargs)

        return wrapped

    return decorator


def authenticated(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        verify_jwt_in_request()
        try:
            user_id = int(get_jwt_identity())
        except (ValueError, TypeError) as exc:
            raise APIError(
                "unauthorized", "A valid access token is required.", 401
            ) from exc
        user = db.session.get(User, user_id)
        if not user or not user.is_active:
            raise APIError("unauthorized", "This account is unavailable.", 401)
        g.current_user = user
        return fn(*args, **kwargs)

    return wrapped


def admin_required(fn):
    @wraps(fn)
    @authenticated
    def wrapped(*args, **kwargs):
        if g.current_user.role != "admin":
            raise APIError("forbidden", "Administrator access is required.", 403)
        return fn(*args, **kwargs)

    return wrapped
