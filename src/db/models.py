from tortoise import fields
from tortoise.contrib.postgres.fields import ArrayField
from tortoise.models import Model


class IdMixin:
    id = fields.IntField(pk=True)


class TimestampMixin:
    created_at = fields.DatetimeField(null=True)
    updated_at = fields.DatetimeField(null=True)


class Users(Model, TimestampMixin, IdMixin):
    firstname = fields.CharField(max_length=255, null=True)
    lastname = fields.CharField(max_length=255, null=True)
    username = fields.CharField(max_length=255, null=True)
    chat_id = fields.BigIntField()
    user_id = fields.BigIntField(unique=True)
    role = fields.IntField(null=True)
    blocked = fields.BooleanField(default=False)
    announce_allowed = fields.BooleanField(default=True)
    last_announced = fields.DatetimeField(null=True)
    utm = ArrayField(element_type="text", null=True)
    utm_created_at = fields.DatetimeField(null=True)
    paid_requests_count = fields.BigIntField(default=0)

    class Meta:
        table = 'users'