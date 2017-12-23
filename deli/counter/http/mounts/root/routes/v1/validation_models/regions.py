from schematics import Model
from schematics.types import IntType, UUIDType, StringType, BooleanType

from deli.http.schematics.types import EnumType, ArrowType, KubeName
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.region.model import Region


class RequestCreateRegion(Model):
    name = KubeName(required=True, min_length=3)
    datacenter = StringType(required=True)
    image_datastore = StringType(required=True)
    image_folder = StringType()


class ParamsRegion(Model):
    region_id = UUIDType(required=True)


class ParamsListRegion(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestRegionSchedule(Model):
    schedulable = BooleanType(required=True)


class ResponseRegion(Model):
    id = UUIDType(required=True)
    name = KubeName(required=True, min_length=3)
    datacenter = StringType(required=True, )
    image_datastore = StringType(required=True)
    image_folder = StringType()
    schedulable = BooleanType(required=True)
    state = EnumType(ResourceState, required=True)
    error_message = StringType()
    created_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, region: Region):
        region_model = cls()
        region_model.id = region.id
        region_model.name = region.name
        region_model.datacenter = region.datacenter
        region_model.image_datastore = region.image_datastore
        region_model.image_folder = region.image_folder
        region_model.schedulable = region.schedulable

        region_model.state = region.state
        if region.error_message != "":
            region_model.error_message = region.error_message

        region_model.created_at = region.created_at

        return region_model
