from marshmallow import ValidationError, fields, validate, validates_schema

from app.schemas.common import StrictSchema


class TaskCreateSchema(StrictSchema):
    title = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    notes = fields.Str(load_default="", validate=validate.Length(max=1000))
    date = fields.Date(required=True)


class TaskUpdateSchema(StrictSchema):
    title = fields.Str(validate=validate.Length(min=1, max=200))
    notes = fields.Str(validate=validate.Length(max=1000))
    date = fields.Date()
    is_completed = fields.Bool()

    @validates_schema
    def _not_empty(self, data, **kwargs):
        if not data:
            raise ValidationError("Provide at least one field to update.")


class TaskReorderSchema(StrictSchema):
    date = fields.Date(required=True)
    ordered_ids = fields.List(fields.Str(), required=True, validate=validate.Length(min=1, max=500))


class TaskCarrySchema(StrictSchema):
    date = fields.Date(required=True)
