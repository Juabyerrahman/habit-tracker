import sqlite3

from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.config import get_config
from app.errors import register_error_handlers
from app.extensions import cors, db, jwt, limiter, migrate


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _validate_config(app: Flask) -> None:
    key = app.config.get("JWT_SECRET_KEY")
    if not key or len(key) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY is missing or shorter than 32 characters. Generate one with:\n"
            '  python -c "import secrets; print(secrets.token_hex(32))"\n'
            "and set it in backend/.env (see .env.example)."
        )
    samesite = str(app.config["COOKIE_SAMESITE"]).lower()
    if samesite not in {"lax", "strict", "none"}:
        raise RuntimeError("COOKIE_SAMESITE must be Lax, Strict or None.")
    if samesite == "none" and not app.config["COOKIE_SECURE"]:
        raise RuntimeError("COOKIE_SAMESITE=None requires COOKIE_SECURE=true.")


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))
    _validate_config(app)
    app.url_map.strict_slashes = False

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
    )

    from app import models  # noqa: F401  (registers tables for migrations)
    from app.auth.jwt_callbacks import register_jwt_callbacks
    from app.auth.providers import init_providers
    from app.routes import register_blueprints

    init_providers(app)
    register_jwt_callbacks(jwt)
    register_error_handlers(app)
    register_blueprints(app)

    @app.after_request
    def _security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("Cache-Control", "no-store")
        return resp

    return app
