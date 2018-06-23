from ingredients_http.schematics.types import KubeName, EnumType, ArrowType
from schematics import Model
from schematics.types import IntType, UUIDType, StringType, BooleanType

from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.region.model import Region


class RequestCreateRegion(Model):
    name = KubeName(required=True, min_length=3)
    datacenter = StringType(required=True)
    image_datastore = StringType(required=True)
    image_folder = StringType()


class ParamsRegion(Model):
    region_name = KubeName(required=True)


class ParamsListRegion(Model):
    region_name = KubeName()
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestRegionSchedule(Model):
    schedulable = BooleanType(required=True)


class ResponseRegion(Model):
    name = KubeName(required=True, min_length=3)
    datacenter = StringType(required=True, )
    image_datastore = StringType(required=True)
    image_folder = StringType()
    schedulable = BooleanType(required=True)
    state = EnumType(ResourceState, required=True)
    error_message = StringType()
    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, region: Region):
        region_model = cls()
        region_model.name = region.name
        region_model.datacenter = region.datacenter
        region_model.image_datastore = region.image_datastore
        region_model.image_folder = region.image_folder
        region_model.schedulable = region.schedulable

        region_model.state = region.state
        if region.error_message != "":
            region_model.error_message = region.error_message

        region_model.created_at = region.created_at
        region_model.updated_at = region.updated_at

        return region_model
