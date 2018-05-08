from ingredients_http.schematics.types import KubeName, ArrowType, EnumType
from schematics import Model
from schematics.types import ListType, UUIDType, IntType, StringType

from deli.kubernetes.resources.model import ResourceState


class RequestCreateRole(Model):
    name = KubeName(required=True, min_length=3)
    policies = ListType(StringType, default=list)


class ParamsRole(Model):
    role_id = UUIDType(required=True)


class ParamsListRoles(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestRoleUpdate(Model):
    policies = ListType(StringType, min_size=1)


class ResponseRole(Model):
    id = UUIDType(required=True)
    name = KubeName(required=True, min_length=3)
    policies = ListType(StringType, default=list)
    state = EnumType(ResourceState, required=True)
    created_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, role):
        model = cls()
        model.id = role.id
        model.name = role.name
        model.policies = role.policies
        model.state = role.state
        model.created_at = role.created_at

        return model
