from schematics import Model
from schematics.types import StringType, ListType, UUIDType, IntType


class ParamsPermission(Model):
    permission_name = StringType(required=True)


class ParamsListPermission(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class ResponsePermission(Model):
    name = StringType(required=True)
    description = StringType(required=True)
    tags = ListType(StringType)
