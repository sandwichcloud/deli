from schematics import Model
from schematics.types import StringType, ListType, UUIDType, IntType


class ParamsPolicy(Model):
    policy_name = StringType(required=True)


class ParamsListPolicy(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class ResponsePolicy(Model):
    name = StringType(required=True)
    description = StringType(required=True)
    tags = ListType(StringType)
