import ipaddress

from ingredients_http.schematics.types import IPv4NetworkType, IPv4AddressType
from schematics import Model
from schematics.exceptions import ValidationError
from schematics.types import StringType, ModelType, DictType, ListType


class OutOfBandNetwork(Model):
    cidr = IPv4NetworkType(required=True)
    gateway = IPv4AddressType(required=True)
    ip_address = IPv4AddressType(required=True)
    dns_servers = ListType(IPv4AddressType, required=True, min_size=1)

    def validate_gateway(self, data, value):
        cidr: ipaddress.IPv4Network = data['cidr']

        if value not in cidr:
            raise ValidationError('is not an address within ' + str(cidr))

        return value


class OutOfBandInstance(Model):
    region_name = StringType(required=True)
    zone_name = StringType(required=True)
    network = ModelType(OutOfBandNetwork, required=True)
    keypairs = ListType(StringType, default=list)
    tags = DictType(StringType, default=dict)
    user_data = StringType(default="#cloud-config\n{}")
