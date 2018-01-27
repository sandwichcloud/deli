from schematics import Model
from schematics.types import StringType, ListType, IntType

from deli.counter.auth.drivers.database.models.user import User
from deli.http.schematics.types import ArrowType


class ParamsDatabaseUser(Model):
    user_id = IntType(required=True)


class ParamsListDatabaseUser(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = IntType()


class RequestDatabaseLogin(Model):
    username = StringType(required=True)
    password = StringType(required=True)


class RequestDatabaseCreateUser(Model):
    username = StringType(required=True)
    password = StringType(required=True)


class ResponseDatabaseUser(Model):
    id = IntType(required=True)
    username = StringType(required=True)
    roles = ListType(StringType(), default=list)
    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, user: User):
        model = cls()
        model.id = user.id
        model.username = user.username

        for role in user.roles:
            model.roles = role.role

        model.created_at = user.created_at
        model.updated_at = user.updated_at

        return model


class RequestDatabaseChangePassword(Model):
    password = StringType(required=True)


class RequestDatabaseUserRole(Model):
    roles = ListType(StringType, required=True, min_size=1)
