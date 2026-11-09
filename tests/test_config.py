"""Database URL configuration for supported SQLAlchemy drivers."""

from config import database_url


def test_normalizes_postgresql_and_mysql_urls(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example/stayease")
    assert database_url() == "postgresql+psycopg://user:pass@db.example/stayease"

    monkeypatch.setenv("DATABASE_URL", "mysql://user:pass@db.example/stayease")
    assert database_url() == "mysql+pymysql://user:pass@db.example/stayease"


def test_defaults_to_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert database_url() == "sqlite:///stayease.db"
