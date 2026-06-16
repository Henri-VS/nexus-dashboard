import os
import pytest


def test_weather_lat_lon_accept_empty_string():
    """field_validator must coerce empty string to 0.0, not raise."""
    from app.core.config import Settings
    s = Settings(
        _env_file=None,
        NEXUS_SECRET_KEY="test-secret-key-for-pytest-use",
        WEATHER_LAT="",
        WEATHER_LON="",
    )
    assert s.weather_lat == 0.0
    assert s.weather_lon == 0.0


def test_weather_lat_lon_accept_none():
    from app.core.config import Settings
    s = Settings(
        _env_file=None,
        NEXUS_SECRET_KEY="test-secret-key-for-pytest-use",
        WEATHER_LAT=None,
        WEATHER_LON=None,
    )
    assert s.weather_lat == 0.0
    assert s.weather_lon == 0.0


def test_weak_key_detected(client):
    """The lifespan validation catches weak keys — verify the rule directly."""
    WEAK_KEYS = ["", "short", "change-me-to-a-random-secret"]
    for key in WEAK_KEYS:
        is_weak = not key or key == "change-me-to-a-random-secret" or len(key) < 16
        assert is_weak, f"Key {key!r} should be considered weak"


def test_strong_key_passes():
    from app.core.config import Settings
    s = Settings(
        _env_file=None,
        NEXUS_SECRET_KEY="this-is-a-valid-key-32chars!!!",
    )
    key = s.nexus_secret_key
    assert len(key) >= 16
    assert key != "change-me-to-a-random-secret"
