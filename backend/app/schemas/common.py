from zoneinfo import ZoneInfo

from marshmallow import RAISE, Schema, ValidationError, pre_load


def valid_timezone(value: str) -> None:
    try:
        ZoneInfo(value)
    except Exception:
        raise ValidationError("Must be a valid IANA timezone, e.g. 'Asia/Dhaka'.") from None


class StrictSchema(Schema):
    """Rejects unknown fields and trims whitespace on string inputs."""

    class Meta:
        unknown = RAISE

    no_strip: tuple = ()  # fields that must be kept verbatim (passwords)

    @pre_load
    def _strip_strings(self, data, **kwargs):
        return {k: (v.strip() if isinstance(v, str) and k not in self.no_strip else v) for k, v in data.items()}
