from flask import current_app


def set_refresh_cookie(resp, raw: str) -> None:
    cfg = current_app.config
    resp.set_cookie(
        cfg["REFRESH_COOKIE_NAME"],
        raw,
        max_age=cfg["REFRESH_TOKEN_DAYS"] * 86400,
        httponly=True,
        secure=cfg["COOKIE_SECURE"],
        samesite=cfg["COOKIE_SAMESITE"],
        path=cfg["REFRESH_COOKIE_PATH"],
    )


def clear_refresh_cookie(resp) -> None:
    cfg = current_app.config
    resp.delete_cookie(cfg["REFRESH_COOKIE_NAME"], path=cfg["REFRESH_COOKIE_PATH"])
