from ingredients_http.schematics.types import KubeName, ArrowType, EnumType
from schematics import Model
from schematics.types import UUIDType, ListType, StringType, IntType

from deli.kubernetes.resources.model import ResourceState


class RequestCreateServiceAccount(Model):
    name = KubeName(required=True, min_length=3)


class RequestUpdateServiceAccount(Model):
    roles = ListType(StringType, required=True)


class ParamsServiceAccount(Model):
    service_account_id = UUIDType(required=True)


class ParamsListServiceAccount(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class ResponseServiceAccount(Model):
    id = UUIDType(required=True)
    name = KubeName(required=True, min_length=3)
    roles = ListType(UUIDType, required=True)
    keys = ListType(StringType, required=True)
    state = EnumType(ResourceState, required=True)
    created_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, service_account):
        model = cls()
        model.id = service_account.id
        model.name = service_account.name
        model.roles = service_account.role_ids
        model.keys = service_account.keys
        model.state = service_account.state
        model.created_at = service_account.created_at

        return model


class RequestCreateServiceAccountKey(Model):
    name = StringType(required=True, min_length=3)


class ParamsServiceAccountKey(Model):
    service_account_id = UUIDType(required=True)
    name = StringType(required=True, min_length=3)
