from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_ssh_public_key
from ingredients_http.schematics.types import ArrowType, KubeName
from schematics import Model
from schematics.exceptions import ValidationError
from schematics.types import UUIDType, IntType, StringType

from deli.kubernetes.resources.v1alpha1.keypair.keypair import Keypair


class ParamsKeypair(Model):
    keypair_name = KubeName(required=True)


class ParamsListKeypair(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestCreateKeypair(Model):
    name = KubeName(required=True, min_length=3)
    public_key = StringType(required=True)

    def validate_public_key(self, data, value):
        try:
            load_ssh_public_key(value.encode(), default_backend())
        except ValueError:
            raise ValidationError("public_key could not be decoded or is not in the proper format")
        except UnsupportedAlgorithm:
            raise ValidationError("public_key serialization type is not supported")

        return value


class ResponseKeypair(Model):
    name = KubeName(required=True, min_length=3)
    public_key = StringType(required=True)
    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, keypair: Keypair):
        model = cls()
        model.name = keypair.name
        model.public_key = keypair.public_key
        model.created_at = keypair.created_at
        model.updated_at = keypair.updated_at

        return model
