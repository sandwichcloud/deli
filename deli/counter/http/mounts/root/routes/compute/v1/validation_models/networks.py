import ipaddress

from ingredients_http.schematics.types import KubeName, IPv4NetworkType, IPv4AddressType, EnumType, ArrowType
from schematics import Model
from schematics.exceptions import ValidationError
from schematics.types import UUIDType, IntType, StringType, ListType

from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.network.model import Network


class RequestCreateNetwork(Model):
    name = KubeName(required=True, min_length=3)
    port_group = StringType(required=True)
    cidr = IPv4NetworkType(required=True)
    gateway = IPv4AddressType(required=True)
    dns_servers = ListType(IPv4AddressType, min_size=1, required=True)
    pool_start = IPv4AddressType(required=True)
    pool_end = IPv4AddressType(required=True)
    region_name = KubeName(required=True)

    def validate_gateway(self, data, value):
        cidr: ipaddress.IPv4Network = data['cidr']

        if value not in cidr:
            raise ValidationError('is not an address within ' + str(cidr))

        return value

    def validate_pool_start(self, data, value):
        cidr: ipaddress.IPv4Network = data['cidr']

        if value not in cidr:
            raise ValidationError('is not an address within ' + str(cidr))

        return value

    def validate_pool_end(self, data, value):
        cidr: ipaddress.IPv4Network = data['cidr']

        if value not in cidr:
            raise ValidationError('is not an address within ' + str(cidr))

        if value < self.pool_start:
            raise ValidationError('needs to be larger than pool_start')

        return value


class ResponseNetwork(Model):
    name = KubeName(required=True, min_length=3)
    port_group = StringType(required=True)
    cidr = IPv4NetworkType(required=True)
    gateway = IPv4AddressType(required=True)
    dns_servers = ListType(IPv4AddressType, min_size=1, required=True)
    pool_start = IPv4AddressType(required=True)
    pool_end = IPv4AddressType(required=True)
    region_name = KubeName()
    state = EnumType(ResourceState, required=True)
    error_message = StringType()
    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, network: Network):
        network_model = cls()
        network_model.name = network.name

        network_model.port_group = network.port_group
        network_model.cidr = network.cidr
        network_model.gateway = network.gateway
        network_model.dns_servers = network.dns_servers
        network_model.pool_start = network.pool_start
        network_model.pool_end = network.pool_end
        network_model.region_name = network.region_name

        network_model.state = network.state
        if network.error_message != "":
            network_model.error_message = network.error_message
        network_model.created_at = network.created_at
        network_model.updated_at = network.updated_at

        return network_model


class ParamsNetwork(Model):
    network_name = KubeName(required=True)


class ParamsListNetwork(Model):
    name = KubeName()
    region = KubeName()
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()
