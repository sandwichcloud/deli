import ipaddress

from deli.kubernetes.resources.const import REGION_LABEL, NETWORK_LABEL
from deli.kubernetes.resources.model import SystemResourceModel, ProjectResourceModel
from deli.kubernetes.resources.v1alpha1.region.model import Region


class Network(SystemResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['metadata']['labels'][REGION_LABEL] = ''
            self._raw['spec'] = {
                'portGroup': None,
                'ipam': {
                    'cidr': None,
                    'poolStart': None,
                    'poolEnd': None,
                    'gateway': None,
                    'dnsServers': [],
                }
            }

    @property
    def region_name(self):
        region_name = self._raw['metadata']['labels'][REGION_LABEL]
        if region_name == "":
            return None
        return region_name

    @property
    def region(self):
        region_name = self.region_name
        if region_name is None:
            return None
        return Region.get(region_name)

    @region.setter
    def region(self, value):
        self._raw['metadata']['labels'][REGION_LABEL] = value.name

    @property
    def port_group(self):
        return self._raw['spec']['portGroup']

    @port_group.setter
    def port_group(self, value):
        self._raw['spec']['portGroup'] = value

    @property
    def cidr(self):
        return ipaddress.IPv4Network(self._raw['spec']['ipam']['cidr'])

    @cidr.setter
    def cidr(self, value):
        self._raw['spec']['ipam']['cidr'] = str(value)

    @property
    def pool_start(self):
        return ipaddress.IPv4Address(self._raw['spec']['ipam']['poolStart'])

    @pool_start.setter
    def pool_start(self, value):
        self._raw['spec']['ipam']['poolStart'] = str(value)

    @property
    def pool_end(self):
        return ipaddress.IPv4Address(self._raw['spec']['ipam']['poolEnd'])

    @pool_end.setter
    def pool_end(self, value):
        self._raw['spec']['ipam']['poolEnd'] = str(value)

    @property
    def gateway(self):
        return ipaddress.IPv4Address(self._raw['spec']['ipam']['gateway'])

    @gateway.setter
    def gateway(self, value):
        self._raw['spec']['ipam']['gateway'] = str(value)

    @property
    def dns_servers(self):
        dns_servers = []
        for dns_server in self._raw['spec']['ipam']['dnsServers']:
            dns_servers.append(ipaddress.IPv4Address(dns_server))
        return dns_servers

    @dns_servers.setter
    def dns_servers(self, value):
        for dns_server in value:
            self._raw['spec']['ipam']['dnsServers'].append(str(dns_server))


class NetworkPort(ProjectResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['metadata']['labels'][NETWORK_LABEL] = None
            self._raw['spec'] = {
                'ipAddress': None
            }

    @property
    def network_name(self):
        return self._raw['metadata']['labels'][NETWORK_LABEL]

    @property
    def network(self):
        return Network.get(self._raw['metadata']['labels'][NETWORK_LABEL])

    @network.setter
    def network(self, value):
        self._raw['metadata']['labels'][NETWORK_LABEL] = str(value.name)

    @property
    def ip_address(self):
        ip_string = self._raw['spec']['ipAddress']
        if ip_string is None:
            return None
        return ipaddress.IPv4Address(ip_string)

    @ip_address.setter
    def ip_address(self, value):
        self._raw['spec']['ipAddress'] = str(value)
