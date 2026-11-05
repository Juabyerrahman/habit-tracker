import os
import secrets
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: str) -> list[str]:
    return [v.strip() for v in os.getenv(name, default).split(",") if v.strip()]


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///habit_tracker.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Secrets come from the environment only. Validated in create_app().
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv("ACCESS_TOKEN_MINUTES", "15")))

    REFRESH_TOKEN_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "30"))
    REFRESH_COOKIE_NAME = "refresh_token"
    REFRESH_COOKIE_PATH = "/api/auth"
    COOKIE_SECURE = _env_bool("COOKIE_SECURE", False)
    COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "Lax")

    CORS_ORIGINS = _env_list("CORS_ORIGINS", "http://localhost:5173")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID") or None
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET") or None  # server-side only, never sent to the browser
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000/auth/google/callback")
    GOOGLE_SUCCESS_URL = os.getenv("GOOGLE_SUCCESS_URL", "http://localhost:5173/auth/callback")
    GOOGLE_ERROR_URL = os.getenv("GOOGLE_ERROR_URL", "http://localhost:5173/login")
    ENABLE_DEV_TOOLS = False  # /dev/auth-test page; only enabled in development

    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_ENABLED = True
    MAX_CONTENT_LENGTH = 1024 * 1024  # 1 MB


class DevelopmentConfig(Config):
    ENABLE_DEV_TOOLS = _env_bool("ENABLE_DEV_TOOLS", True)


class ProductionConfig(Config):
    COOKIE_SECURE = _env_bool("COOKIE_SECURE", True)


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = secrets.token_hex(32)  # random per test run, never a literal
    RATELIMIT_ENABLED = False
    GOOGLE_CLIENT_ID = None
    GOOGLE_CLIENT_SECRET = None
    GOOGLE_REDIRECT_URI = "http://localhost:5000/auth/google/callback"
    GOOGLE_SUCCESS_URL = "http://localhost:5173/auth/callback"
    GOOGLE_ERROR_URL = "http://localhost:5173/login"
    COOKIE_SECURE = False
    COOKIE_SAMESITE = "Lax"


_CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config(name: str | None = None):
    name = (name or os.getenv("APP_ENV", "development")).lower()
    try:
        return _CONFIGS[name]
    except KeyError:
        raise RuntimeError(f"Unknown APP_ENV '{name}'. Use one of: {', '.join(_CONFIGS)}") from None
