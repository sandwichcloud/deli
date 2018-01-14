from schematics import Model
from schematics.types import UUIDType, IntType

from deli.http.schematics.types import IPv4AddressType, ArrowType, EnumType
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.network.model import NetworkPort


class ParamsNetworkPort(Model):
    network_port_id = UUIDType(required=True)


class ParamsListNetworkPort(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class ResponseNetworkPort(Model):
    id = UUIDType(required=True)
    network_id = UUIDType(required=True)
    ip_address = IPv4AddressType(required=True)
    state = EnumType(ResourceState, required=True)
    created_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, network_port: NetworkPort):
        model = cls()
        model.id = network_port.id
        model.network_id = network_port.network_id
        model.ip_address = network_port.ip_address
        model.state = network_port.state
        model.created_at = network_port.created_at

        return model
