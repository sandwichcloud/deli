from ingredients_http.schematics.types import KubeName, ArrowType, EnumType
from schematics import Model
from schematics.types import UUIDType, StringType, IntType, EmailType, DictType

from deli.kubernetes.resources.model import ResourceState


class RequestCreateServiceAccount(Model):
    name = KubeName(required=True, min_length=3)


class ParamsServiceAccount(Model):
    service_account_name = KubeName(required=True)


class ParamsListServiceAccount(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class ResponseServiceAccount(Model):
    name = KubeName(required=True, min_length=3)
    email = EmailType(required=True)
    keys = DictType(ArrowType, required=True)
    state = EnumType(ResourceState, required=True)
    created_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, service_account):
        model = cls()
        model.name = service_account.name
        model.email = service_account.email
        model.keys = service_account.keys
        model.state = service_account.state
        model.created_at = service_account.created_at

        return model


class RequestCreateServiceAccountKey(Model):
    name = StringType(required=True, min_length=3)


class ParamsServiceAccountKey(Model):
    service_account_name = KubeName(required=True)
    name = StringType(required=True, min_length=3)
