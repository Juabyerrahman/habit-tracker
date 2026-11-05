from marshmallow import ValidationError, fields, validate, validates_schema

from app.schemas.common import StrictSchema

_schedule = fields.List(
    fields.Int(validate=validate.Range(min=0, max=6)),
    validate=validate.Length(min=1, max=7),
)


class HabitCreateSchema(StrictSchema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    description = fields.Str(load_default="", validate=validate.Length(max=500))
    category = fields.Str(allow_none=True, load_default=None, validate=validate.Length(max=50))
    icon = fields.Str(allow_none=True, load_default=None, validate=validate.Length(max=16))
    start_date = fields.Date(allow_none=True, load_default=None)  # default: today in user's timezone
    schedule = fields.List(
        fields.Int(validate=validate.Range(min=0, max=6)),
        load_default=lambda: [0, 1, 2, 3, 4, 5, 6],
        validate=validate.Length(min=1, max=7),
    )


class HabitUpdateSchema(StrictSchema):
    name = fields.Str(validate=validate.Length(min=1, max=100))
    description = fields.Str(validate=validate.Length(max=500))
    category = fields.Str(allow_none=True, validate=validate.Length(max=50))
    icon = fields.Str(allow_none=True, validate=validate.Length(max=16))
    start_date = fields.Date()
    schedule = _schedule

    @validates_schema
    def _not_empty(self, data, **kwargs):
        if not data:
            raise ValidationError("Provide at least one field to update.")
