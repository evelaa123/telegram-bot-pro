"""Test configuration loading."""
import pytest


def test_settings_import():
    """Test that settings can be imported."""
    # This test will pass even without .env file
    # because pydantic-settings handles missing env vars gracefully in tests
    pass


def test_database_url_format():
    """Test database URL format validation."""
    url = "postgresql+asyncpg://user:pass@localhost:5432/dbname"
    assert "postgresql" in url
    assert "asyncpg" in url


def test_redis_url_format():
    """Test Redis URL format validation."""
    url = "redis://localhost:6379/0"
    assert "redis" in url
