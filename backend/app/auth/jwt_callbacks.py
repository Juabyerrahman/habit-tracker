from app.errors import error_response


def register_jwt_callbacks(jwt):
    @jwt.unauthorized_loader
    def _missing(reason):
        return error_response(401, "missing_token", "Authentication required.")

    @jwt.invalid_token_loader
    def _invalid(reason):
        return error_response(401, "invalid_token", "Invalid access token.")

    @jwt.expired_token_loader
    def _expired(header, data):
        return error_response(401, "token_expired", "Access token expired.")
