"""Application configuration profiles."""

import os

from dotenv import load_dotenv

load_dotenv()


def database_url():
    """Normalize common connection URLs to the installed DB-API drivers."""
    value = os.getenv("DATABASE_URL", "sqlite:///stayease.db")
    if value.startswith(("postgres://", "postgresql://")):
        return "postgresql+psycopg://" + value.split("://", 1)[1]
    if value.startswith("mysql://"):
        return "mysql+pymysql://" + value.split("://", 1)[1]
    return value


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-only-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = 60 * 60 * 24 * 7
    SQLALCHEMY_DATABASE_URI = database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CLIENT_ORIGIN = os.getenv("CLIENT_ORIGIN", "http://localhost:5000")
    RATELIMIT_DEFAULT = "200 per hour"
    RATELIMIT_STORAGE_URI = "memory://"
    JSON_SORT_KEYS = False


class DevConfig(Config):
    DEBUG = True


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    JWT_SECRET_KEY = "test-jwt-secret-long-enough-for-sha256-signing"
    SECRET_KEY = "test-secret-long-enough-for-signing"
    RATELIMIT_ENABLED = False


class ProdConfig(Config):
    DEBUG = False
    TESTING = False
