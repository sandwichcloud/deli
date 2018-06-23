from ingredients_http.schematics.types import KubeName, KubeString, EnumType, ArrowType
from schematics import Model
from schematics.types import UUIDType, IntType, DictType, ListType, BooleanType, StringType, ModelType

from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.instance.model import Instance, VMPowerState, VMTask


class RequestInitialVolumes(Model):
    size = IntType(required=True, min_value=5)
    auto_delete = BooleanType(default=False)


class RequestCreateInstance(Model):
    name = KubeName(required=True, min_length=3)
    image_name = KubeName(required=True)
    service_account_name = KubeName()
    network_name = KubeName(required=True)
    region_name = KubeName(required=True)
    zone_name = KubeName()
    keypair_names = ListType(KubeName, default=list)
    tags = DictType(KubeString, default=dict)
    user_data = StringType()

    flavor_name = KubeName(required=True)
    disk = IntType()
    initial_volumes = ListType(ModelType(RequestInitialVolumes), default=list)

    def validate_disk(self, data, value):
        if value is not None and value != 0:
            IntType(min_value=5).validate_range(value)


class ResponseInstance(Model):
    name = KubeName(required=True, min_length=3)
    image_name = KubeName()
    network_port_id = KubeName(required=True)
    region_name = KubeName(required=True)
    zone_name = KubeName()
    service_account_name = KubeName()
    keypair_names = ListType(KubeName, default=list)
    state = EnumType(ResourceState, required=True)
    power_state = EnumType(VMPowerState, required=True)

    flavor_name = KubeName(required=True)
    vcpus = IntType(required=True)
    ram = IntType(required=True)
    disk = IntType(required=True)

    task = EnumType(VMTask)
    tags = DictType(KubeString, default=dict)
    user_data = StringType()
    error_message = StringType()
    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, instance: Instance):
        instance_model = cls()
        instance_model.name = instance.name
        instance_model.image_name = instance.image_name

        instance_model.network_port_id = instance.network_port_id
        instance_model.service_account_name = instance.service_account_name

        instance_model.region_name = instance.region_name
        if instance.zone_name is not None:
            instance_model.zone_name = instance.zone_name

        for keypair_name in instance.keypair_names:
            instance_model.keypair_names.append(keypair_name)

        instance_model.state = instance.state
        if instance.error_message != "":
            instance_model.error_message = instance.error_message

        instance_model.power_state = instance.power_state

        if instance.flavor_name is not None:
            instance_model.flavor_name = instance.flavor_name

        instance_model.vcpus = instance.vcpus
        instance_model.ram = instance.ram
        instance_model.disk = instance.disk

        instance_model.task = instance.task

        instance_model.tags = instance.tags
        instance_model.user_data = instance.user_data
        instance_model.created_at = instance.created_at
        instance_model.updated_at = instance.updated_at
        return instance_model


class ParamsInstance(Model):
    instance_name = KubeName(required=True)


class ParamsListInstance(Model):
    image_name = KubeName()
    zone_name = KubeName()
    region_name = KubeName()
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestInstanceImage(Model):
    name = KubeName(required=True)


class RequestInstancePowerOffRestart(Model):
    hard = BooleanType(default=False)
    timeout = IntType(default=60, min_value=60, max_value=300)
