from schematics import Model
from schematics.types import UUIDType, IntType, DictType, ListType, BooleanType, StringType

from deli.http.schematics.types import KubeString, EnumType, ArrowType, KubeName
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.instance.model import Instance, VMPowerState, VMTask


class RequestCreateInstance(Model):
    name = KubeName(required=True, min_length=3)
    image_id = UUIDType(required=True)
    service_account_id = UUIDType()
    network_id = UUIDType(required=True)
    region_id = UUIDType(required=True)
    zone_id = UUIDType()
    keypair_ids = ListType(UUIDType, default=list)
    tags = DictType(KubeString, default=dict)


class ResponseInstance(Model):
    # Simplified instance model, used to speed up list times
    id = UUIDType(required=True)
    name = KubeName(required=True, min_length=3)
    image_id = UUIDType()
    network_port_id = UUIDType(required=True)
    region_id = UUIDType(required=True)
    zone_id = UUIDType()
    service_account_id = UUIDType()
    keypair_ids = ListType(UUIDType, default=list)
    state = EnumType(ResourceState, required=True)
    power_state = EnumType(VMPowerState, required=True)
    task = EnumType(VMTask)
    tags = DictType(KubeString, default=dict)
    error_message = StringType()
    created_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, instance: Instance):
        instance_model = cls()
        instance_model.id = instance.id
        instance_model.name = instance.name
        instance_model.image_id = instance.image_id

        instance_model.network_port_id = instance.network_port_id
        instance_model.service_account_id = instance.service_account_id

        instance_model.region_id = instance.region_id
        if instance.zone_id is not None:
            instance_model.zone_id = instance.zone_id

        for keypair_id in instance.keypair_ids:
            instance_model.keypair_ids.append(keypair_id)

        instance_model.state = instance.state
        if instance.error_message != "":
            instance_model.error_message = instance.error_message

        instance_model.power_state = instance.power_state
        instance_model.task = instance.task

        instance_model.tags = instance.tags
        instance_model.created_at = instance.created_at
        return instance_model


class ParamsInstance(Model):
    instance_id = UUIDType(required=True)


class ParamsListInstance(Model):
    image_id = UUIDType()
    zone_id = UUIDType()
    region_id = UUIDType()
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestInstanceImage(Model):
    name = KubeName(required=True)


class RequestInstancePowerOffRestart(Model):
    hard = BooleanType(default=False)
    timeout = IntType(default=60, min_value=60, max_value=300)
