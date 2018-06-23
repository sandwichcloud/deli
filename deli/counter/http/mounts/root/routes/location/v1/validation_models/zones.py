from ingredients_http.schematics.types import KubeName, EnumType, ArrowType
from schematics import Model
from schematics.types import IntType, UUIDType, StringType, BooleanType

from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.zone.model import Zone


class RequestCreateZone(Model):
    name = KubeName(required=True, min_length=3)
    region_name = KubeName(required=True)
    vm_cluster = StringType(required=True)
    vm_datastore = StringType(required=True)
    vm_folder = StringType()
    core_provision_percent = IntType(min_value=0, required=True)
    ram_provision_percent = IntType(min_value=0, required=True)


class ParamsZone(Model):
    zone_name = KubeName(required=True)


class ParamsListZone(Model):
    region_name = KubeName()
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestZoneSchedule(Model):
    schedulable = BooleanType(required=True)


class ResponseZone(Model):
    name = KubeName(required=True, min_length=3)
    region_name = KubeName()
    vm_cluster = StringType(required=True)
    vm_datastore = StringType(required=True)
    vm_folder = StringType()
    core_provision_percent = IntType(required=True)
    ram_provision_percent = IntType(required=True)
    schedulable = BooleanType(required=True)
    state = EnumType(ResourceState, required=True)
    error_message = StringType()
    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, zone: Zone):
        zone_model = cls()
        zone_model.name = zone.name
        zone_model.region_name = zone.region_name
        zone_model.vm_cluster = zone.vm_cluster
        zone_model.vm_datastore = zone.vm_datastore
        zone_model.vm_folder = zone.vm_folder
        zone_model.core_provision_percent = zone.core_provision_percent
        zone_model.ram_provision_percent = zone.ram_provision_percent
        zone_model.schedulable = zone.schedulable

        zone_model.state = zone.state
        if zone.error_message != "":
            zone_model.error_message = zone.error_message
        zone_model.created_at = zone.created_at
        zone_model.updated_at = zone.updated_at

        return zone_model
