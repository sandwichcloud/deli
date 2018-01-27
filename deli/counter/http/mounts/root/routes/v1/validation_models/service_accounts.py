from schematics import Model
from schematics.types import UUIDType, ListType, StringType, IntType

from deli.http.schematics.types import KubeName, ArrowType
from deli.kubernetes.resources.v1alpha1.service_account.model import ServiceAccount


class RequestCreateServiceAccount(Model):
    name = KubeName(required=True, min_length=3)


class RequestUpdateServiceAccount(Model):
    roles = ListType(StringType, required=True, min_size=1)


class ParamsServiceAccount(Model):
    service_account_id = UUIDType(required=True)


class ParamsListServiceAccount(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class ResponseServiceAccount(Model):
    id = UUIDType(required=True)
    name = KubeName(required=True, min_length=3)
    roles = ListType(UUIDType, required=True, min_size=1)
    created_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, service_account: ServiceAccount):
        model = cls()
        model.id = service_account.id
        model.name = service_account.name
        model.roles = service_account.role_ids
        model.created_at = service_account.created_at

        return model
