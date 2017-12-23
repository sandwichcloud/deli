from schematics import Model
from schematics.types import StringType, ListType, UUIDType, IntType

from ingredients_db.models.builtin import BuiltInUser
from ingredients_http.schematics.types import ArrowType


class ParamsBuiltInUser(Model):
    user_id = UUIDType(required=True)


class ParamsListBuiltInUser(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestBuiltInLogin(Model):
    username = StringType(required=True)
    password = StringType(required=True)


class RequestBuiltInCreateUser(Model):
    username = StringType(required=True)
    password = StringType(required=True)


class ResponseBuiltInUser(Model):
    id = UUIDType(required=True)
    username = StringType(required=True)
    roles = ListType(StringType())
    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, user: BuiltInUser):
        model = cls()
        model.id = user.id
        model.username = user.username
        model.roles = user.roles
        model.created_at = user.created_at
        model.updated_at = user.updated_at

        return model


class RequestBuiltInChangePassword(Model):
    password = StringType(required=True)


class RequestBuiltInUserRole(Model):
    role = StringType(required=True)
