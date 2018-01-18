from schematics import Model
from schematics.types import UUIDType, IntType, StringType

from deli.http.schematics.types import KubeName, EnumType, ArrowType
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.volume.model import Volume, VolumeTask


class ParamsVolume(Model):
    volume_id = UUIDType(required=True)


class ParamsListVolume(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestCreateVolume(Model):
    name = KubeName(required=True, min_length=3)
    zone_id = UUIDType(required=True)
    size = IntType(required=True, min_value=5)


class RequestCloneVolume(Model):
    name = KubeName(required=True, min_length=3)


class RequestAttachVolume(Model):
    instance_id = UUIDType(required=True)


class RequestGrowVolume(Model):
    size = IntType(required=True, min_value=5)


class ResponseVolume(Model):
    id = UUIDType(required=True)
    name = KubeName(required=True, min_length=3)
    zone_id = UUIDType(required=True)
    size = IntType(required=True)
    attached_to = UUIDType()
    state = EnumType(ResourceState, required=True)
    task = EnumType(VolumeTask)
    error_message = StringType()
    created_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, volume: Volume):
        model = cls()
        model.id = volume.id
        model.name = volume.name
        model.zone_id = volume.zone_id
        model.size = volume.size
        model.state = volume.state
        model.attached_to = volume.attached_to_id
        model.task = volume.task
        model.error_message = volume.error_message
        model.created_at = volume.created_at

        return model
