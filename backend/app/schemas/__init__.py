from app.errors import ApiError


def load(schema, payload):
    """Validate a JSON body. ValidationError is turned into a 422 by the global handler."""
    if not isinstance(payload, dict):
        raise ApiError(400, "invalid_json", "Request body must be a JSON object.")
    return schema.load(payload)
