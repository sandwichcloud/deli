from schematics import Model
from schematics.types import UUIDType, IntType

from deli.http.schematics.types import IPv4AddressType
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

    @classmethod
    def from_database(cls, network_port: NetworkPort):
        model = cls()
        model.id = network_port.id
        model.network_id = network_port.network_id
        model.ip_address = network_port.ip_address

        return model
