from marshmallow import ValidationError, fields, post_load, validate, validates_schema

from app.schemas.common import StrictSchema, valid_timezone


class RegisterSchema(StrictSchema):
    no_strip = ("password",)
    email = fields.Email(required=True, validate=validate.Length(max=254))
    password = fields.Str(required=True, validate=validate.Length(min=10, max=128))
    name = fields.Str(load_default="", validate=validate.Length(max=100))
    timezone = fields.Str(load_default="UTC", validate=valid_timezone)

    @post_load
    def _normalise(self, data, **kwargs):
        data["email"] = data["email"].lower()
        return data


class LoginSchema(StrictSchema):
    no_strip = ("password",)
    email = fields.Str(required=True, validate=validate.Length(min=1, max=254))
    password = fields.Str(required=True, validate=validate.Length(min=1, max=128))

    @post_load
    def _normalise(self, data, **kwargs):
        data["email"] = data["email"].lower()
        return data


class OAuthSchema(StrictSchema):
    no_strip = ("credential",)
    credential = fields.Str(required=True, validate=validate.Length(min=1, max=4096))
    timezone = fields.Str(validate=valid_timezone)  # optional; only used when a new account is created


class ProfileUpdateSchema(StrictSchema):
    name = fields.Str(validate=validate.Length(max=100))
    timezone = fields.Str(validate=valid_timezone)
    week_starts_on = fields.Int(validate=validate.Range(min=0, max=6))

    @validates_schema
    def _not_empty(self, data, **kwargs):
        if not data:
            raise ValidationError("Provide at least one field to update.")
