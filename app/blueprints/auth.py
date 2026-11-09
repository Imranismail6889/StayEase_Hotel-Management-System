"""Registration, login, and profile management."""

from flask import Blueprint, current_app, g
from flask_jwt_extended import create_access_token
from sqlalchemy.exc import IntegrityError

from app.extensions import db, limiter
from app.models import User
from app.schemas import (
    EmailSchema,
    LoginSchema,
    PasswordSchema,
    ProfileSchema,
    RegisterSchema,
)
from app.utils.decorators import authenticated, validate_with
from app.utils.errors import APIError
from app.utils.responses import success

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/register")
@limiter.limit("10 per 15 minutes")
@validate_with(RegisterSchema)
def register():
    data = g.validated
    email = data["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        raise APIError("conflict", "An account with this email already exists.", 409)
    user = User(name=data["name"].strip(), email=email, phone=data.get("phone", ""))
    user.set_password(data["password"])
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError as exc:
        db.session.rollback()
        raise APIError(
            "conflict", "An account with this email already exists.", 409
        ) from exc
    return success(
        {"user": user.to_dict(), "token": create_access_token(identity=str(user.id))},
        201,
    )


@bp.post("/login")
@limiter.limit("10 per 15 minutes")
@validate_with(LoginSchema)
def login():
    data = g.validated
    user = User.query.filter_by(email=data["email"].strip().lower()).first()
    if not user or not user.check_password(data["password"]) or not user.is_active:
        raise APIError("invalid_credentials", "Email or password is incorrect.", 401)
    return success(
        {"user": user.to_dict(), "token": create_access_token(identity=str(user.id))}
    )


@bp.get("/me")
@authenticated
def me():
    return success(g.current_user.to_dict())


@bp.put("/me")
@authenticated
@validate_with(ProfileSchema)
def update_me():
    data = g.validated
    for key in ("name", "phone"):
        if key in data:
            setattr(g.current_user, key, data[key].strip())
    db.session.commit()
    return success(g.current_user.to_dict())


@bp.put("/password")
@authenticated
@validate_with(PasswordSchema)
def change_password():
    data = g.validated
    if not g.current_user.check_password(data["current_password"]):
        raise APIError("invalid_credentials", "Current password is incorrect.", 401)
    g.current_user.set_password(data["new_password"])
    db.session.commit()
    return success({"message": "Password updated."})


@bp.post("/forgot-password")
@limiter.limit("10 per 15 minutes")
@validate_with(EmailSchema)
def forgot_password():
    email = g.validated["email"]
    current_app.logger.info("Mock password reset requested for %s", email)
    return success(
        {"message": "If that address has an account, a reset link has been sent."}
    )
