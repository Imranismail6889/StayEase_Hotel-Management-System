"""StayEase Flask application factory."""

import os
from datetime import timedelta
from tempfile import gettempdir

from flask import Flask, send_from_directory
from werkzeug.exceptions import HTTPException

from app.extensions import cors, db, jwt, limiter, migrate
from app.utils.errors import APIError
from app.utils.responses import error


def create_app(config_object=None):
    env_name = os.getenv(
        "APP_ENV", os.getenv("VERCEL_ENV", os.getenv("FLASK_ENV", "development"))
    ).lower()
    is_deployment = env_name in {"production", "preview"}
    instance_path = (
        os.path.join(gettempdir(), "stayease") if os.getenv("VERCEL_ENV") else None
    )
    app = Flask(
        __name__,
        instance_path=instance_path,
        instance_relative_config=True,
        static_folder="static",
        template_folder="templates",
    )
    app.config.from_object(
        config_object or ("config.ProdConfig" if is_deployment else "config.DevConfig")
    )
    if isinstance(config_object, dict):
        app.config.update(config_object)
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=7)
    os.makedirs(app.instance_path, exist_ok=True)
    if is_deployment or app.config.get("ENVIRONMENT") == "production":
        forbidden = {
            "dev-only-change-me",
            "dev-jwt-only-change-me",
            "replace-this-with-a-random-secret",
        }
        if (
            app.config.get("SECRET_KEY") in forbidden
            or app.config.get("JWT_SECRET_KEY") in forbidden
        ):
            raise RuntimeError(
                "Production requires non-default SECRET_KEY and JWT_SECRET_KEY values."
            )
        if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:"):
            raise RuntimeError(
                "Production and preview deployments require a persistent DATABASE_URL."
            )
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    cors.init_app(
        app,
        resources={
            r"/api/*": {
                "origins": app.config.get("CLIENT_ORIGIN", "http://localhost:5000")
            }
        },
    )
    from app import models  # noqa: F401
    from app.blueprints import (
        admin,
        auth,
        bookings,
        favorites,
        loyalty,
        newsletter,
        notifications,
        promos,
        reviews,
        rooms,
    )

    for blueprint in (
        auth.bp,
        rooms.bp,
        bookings.bp,
        reviews.bp,
        favorites.bp,
        loyalty.bp,
        promos.bp,
        notifications.bp,
        newsletter.bp,
        admin.bp,
    ):
        app.register_blueprint(blueprint)

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/<path:path>")
    def spa_fallback(path):
        if path.startswith("api/"):
            return error("not_found", "API endpoint not found.", 404)
        return send_from_directory(app.static_folder, "index.html")

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com; img-src 'self' data: https:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; script-src 'self' 'unsafe-inline'; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
        )
        return response

    @app.errorhandler(APIError)
    def handle_api_error(exc):
        return error(exc.code, exc.message, exc.status, exc.details)

    @app.errorhandler(HTTPException)
    def handle_http_error(exc):
        return error(
            exc.name.lower().replace(" ", "_"), exc.description, exc.code or 500
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc):
        db.session.rollback()
        app.logger.exception("Unhandled application error")
        message = (
            str(exc) if app.testing or app.debug else "An unexpected error occurred."
        )
        return error("internal_error", message, 500)

    @jwt.unauthorized_loader
    def missing_token(_reason):
        return error("unauthorized", "A valid access token is required.", 401)

    @jwt.invalid_token_loader
    def invalid_token(_reason):
        return error("unauthorized", "The access token is invalid.", 401)

    @jwt.expired_token_loader
    def expired_token(_header, _payload):
        return error("unauthorized", "The access token has expired.", 401)

    @jwt.revoked_token_loader
    def revoked_token(_header, _payload):
        return error("unauthorized", "The access token has been revoked.", 401)

    from app.cli import register_cli

    register_cli(app)
    return app
