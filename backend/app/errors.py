from flask import jsonify
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    """Raise anywhere to return a clean JSON error."""

    def __init__(self, status: int, code: str, message: str, details=None):
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details


def error_response(status: int, code: str, message: str, details=None):
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return jsonify(body), status


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def _api_error(e):
        return error_response(e.status, e.code, e.message, e.details)

    @app.errorhandler(ValidationError)
    def _validation_error(e):
        return error_response(422, "validation_error", "Request validation failed.", e.normalized_messages())

    @app.errorhandler(HTTPException)
    def _http_error(e):
        if e.code == 429:
            return error_response(429, "too_many_requests", "Too many attempts. Please wait a minute and try again.")
        return error_response(e.code or 500, (e.name or "error").lower().replace(" ", "_"), e.description)

    @app.errorhandler(Exception)
    def _unexpected(e):
        app.logger.exception("Unhandled error")
        return error_response(500, "internal_error", "Something went wrong.")
