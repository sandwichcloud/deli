from ingredients_http.schematics.types import EnumType, KubeName, ArrowType
from schematics import Model
from schematics.types import UUIDType, StringType, IntType

from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.image.model import Image, ImageVisibility


class ParamsImage(Model):
    image_name = StringType(required=True)


class ParamsListImage(Model):
    visibility = EnumType(ImageVisibility, default=ImageVisibility.PRIVATE)
    region_name = StringType()
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestCreateImage(Model):
    name = KubeName(required=True, min_length=3)
    file_name = StringType(required=True)
    region_name = KubeName(required=True)


class ResponseImage(Model):
    project_name = StringType(required=True)
    name = KubeName(required=True, min_length=3)
    file_name = StringType()
    region_name = StringType(required=True)
    state = EnumType(ResourceState, required=True)
    error_message = StringType()
    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, image: Image):
        image_model = cls()
        image_model.project_name = image.project_name
        image_model.name = image.name

        image_model.file_name = image.file_name
        image_model.region_name = image.region_name

        image_model.state = image.state
        if image.error_message != "":
            image_model.error_message = image.error_message
        image_model.created_at = image.created_at
        image_model.updated_at = image.updated_at

        return image_model
