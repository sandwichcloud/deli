from schematics import Model
from schematics.types import UUIDType, StringType, IntType

from deli.http.schematics.types import KubeName, EnumType, ArrowType
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.image.model import Image


class ParamsImage(Model):
    image_id = UUIDType(required=True)


class ParamsListImage(Model):
    region_id = UUIDType()
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestCreateImage(Model):
    name = KubeName(required=True, min_length=3)
    file_name = StringType(required=True)
    region_id = KubeName(required=True)


class ResponseImage(Model):
    id = UUIDType(required=True)
    name = KubeName(required=True, min_length=3)
    file_name = StringType()
    region_id = UUIDType(required=True)
    state = EnumType(ResourceState, required=True)
    error_message = StringType()
    created_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, image: Image):
        image_model = cls()
        image_model.id = image.id
        image_model.name = image.name

        image_model.file_name = image.file_name
        image_model.region_id = image.region_id

        image_model.state = image.state
        if image.error_message != "":
            image_model.error_message = image.error_message
        image_model.created_at = image.created_at

        return image_model
