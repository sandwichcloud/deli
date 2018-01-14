from schematics import Model
from schematics.types import UUIDType, IntType

from deli.http.schematics.types import KubeName, ArrowType
from deli.kubernetes.resources.v1alpha1.flavor.model import Flavor


class ParamsFlavor(Model):
    flavor_id = UUIDType(required=True)


class ParamsListFlavor(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestCreateFlavor(Model):
    name = KubeName(required=True, min_length=3)
    vcpus = IntType(required=True, min_value=1)
    ram = IntType(required=True, min_value=512)
    disk = IntType(required=True, min_value=5)


class ResponseFlavor(Model):
    id = UUIDType(required=True)
    name = KubeName(required=True, min_length=3)
    vcpus = IntType(required=True)
    ram = IntType(required=True)
    disk = IntType(required=True)
    created_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, flavor: Flavor):
        model = cls()
        model.id = flavor.id
        model.name = flavor.name
        model.vcpus = flavor.vcpus
        model.ram = flavor.ram
        model.disk = flavor.disk
        model.created_at = flavor.created_at

        return model
