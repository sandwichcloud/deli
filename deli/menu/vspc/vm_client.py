import base64
import enum
import json
import logging
import os
import os.path
import uuid

import arrow
import yaml
from cryptography.fernet import Fernet

from deli.kubernetes.resources.const import ID_LABEL
from deli.kubernetes.resources.v1alpha1.image.model import Image
from deli.kubernetes.resources.v1alpha1.instance.model import Instance
from deli.kubernetes.resources.v1alpha1.keypair.keypair import Keypair
from deli.kubernetes.resources.v1alpha1.network.model import NetworkPort, Network
from deli.kubernetes.resources.v1alpha1.region.model import Region
from deli.kubernetes.resources.v1alpha1.service_account.model import ServiceAccount
from deli.kubernetes.resources.v1alpha1.zone.model import Zone
from deli.menu.models.out_of_band import OutOfBandInstance
from deli.menu.vspc.async_telnet import CR


class PacketCode(enum.Enum):
    # Incoming packets
    REQUEST_METADATA = 'REQUEST_METADATA'
    REQUEST_NETWORKDATA = 'REQUEST_NETWORKDATA'
    REQUEST_USERDATA = 'REQUEST_USERDATA'
    REQUEST_SECURITYDATA = 'REQUEST_SECURITYDATA'
    # Outgoing packets
    RESPONSE_METADATA = 'RESPONSE_METADATA'
    RESPONSE_NETWORKDATA = 'RESPONSE_NETWORKDATA'
    RESPONSE_USERDATA = 'RESPONSE_USERDATA'
    RESPONSE_SECURITYDATA = 'RESPONSE_SECURITYDATA'


class VMClient(object):

    def __init__(self, vm_name, writer):
        self.logger = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))
        self.vm_name = vm_name
        self.writer = writer

        self.fernet = Fernet(os.environ['FERNET_KEY'])
        self.out_of_band = os.environ.get('OUT_OF_BAND')

    def get_instance(self):
        if self.out_of_band is not None:

            instance_file = None
            if os.path.isfile(os.path.join(self.out_of_band, self.vm_name + ".yaml")):
                instance_file = os.path.join(self.out_of_band, self.vm_name + ".yaml")
            elif os.path.isfile(os.path.join(self.out_of_band, self.vm_name + ".yml")):
                instance_file = os.path.join(self.out_of_band, self.vm_name + ".yml")

            if instance_file is None:
                self.logger.error("Could not find metadata file for instance " + self.vm_name)
                return None

            with open(instance_file) as f:
                instance_yaml = yaml.load(f)
                try:
                    instance_model = OutOfBandInstance(instance_yaml)
                    instance_model.validate()
                except Exception:
                    self.logger.exception("Error loading metadata for instance " + self.vm_name)
                    return None

            # Override instance properties
            @property
            def image_id(self):
                return self._image.id

            @property
            def project_id(self):
                return uuid.uuid4()

            @property
            def image(self):
                return self._image

            @image.setter
            def image(self, value):
                self._image = value

            @property
            def region(self):
                return self._region

            @region.setter
            def region(self, value):
                self._region = value

            @property
            def zone(self):
                return self._zone

            @zone.setter
            def zone(self, value):
                self._zone = value

            @property
            def keypairs(self):
                return self._keypairs

            @keypairs.setter
            def keypairs(self, value):
                self._keypairs = value

            @property
            def network_port(self):
                return self._network_port

            @network_port.setter
            def network_port(self, value):
                self._network_port = value

            @property
            def service_account(self):
                return self._service_account

            @service_account.setter
            def service_account(self, value):
                self._service_account = value

            Instance.image_id = image_id
            Instance.project_id = project_id
            Instance.image = image
            Instance.region = region
            Instance.zone = zone
            Instance.keypairs = keypairs
            Instance.network_port = network_port
            Instance.service_account = service_account

            # Override network port properties
            @property
            def network(self):
                return self._network

            @network.setter
            def network(self, value):
                self._network = value

            NetworkPort.network = network

            network = Network()
            network.cidr = instance_model.network.cidr
            network.gateway = instance_model.network.gateway
            network.dns_servers = instance_model.network.dns_servers

            network_port = NetworkPort()
            network_port.ip_address = instance_model.network.ip_address
            network_port.network = network

            region = Region()
            region.name = instance_model.region_name

            zone = Zone()
            zone.name = instance_model.zone_name

            service_account = ServiceAccount()
            service_account.name = "None"

            instance = Instance()
            instance.image = Image()
            instance.region = region
            instance.zone = zone
            instance.service_account = service_account

            for k, v in instance_model.tags.items():
                instance.add_tag(k, v)

            keypairs = []
            for public_key in instance_model.keypairs:
                keypair = Keypair()
                keypair.public_key = public_key
                keypairs.append(keypair)
                
            instance.keypairs = keypairs
            instance.network_port = network_port
            instance.user_data = instance_model.user_data

            return instance
        else:
            instances = Instance.list_all(label_selector=ID_LABEL + "=" + self.vm_name)
            if len(instances) == 0:
                self.logger.warning("Could not find any instances with the id of '%s'" % self.vm_name)
                return None
            if len(instances) > 1:
                self.logger.warning("Found multiple instances with the id of '%s'" % self.vm_name)
                return None
            return instances[0]

    async def write_metadata(self):

        instance: Instance = self.get_instance()
        if instance is None:
            return

        keypairs = []
        for keypair in instance.keypairs:
            keypairs.append(keypair.public_key)

        network_port = instance.network_port

        metadata = {
            'ami-id': instance.image_id,
            'instance-id': instance.id,
            'region': instance.region.name,
            'availability-zone': instance.zone.name,
            'tags': instance.tags,
            'public-keys': keypairs,
            'hostname': 'ip-' + str(network_port.ip_address).replace(".", "-"),
            'local-hostname': 'ip-' + str(network_port.ip_address).replace(".", "-"),
        }

        await self.write(PacketCode.RESPONSE_METADATA, json.dumps(metadata))

    async def write_networkdata(self):

        instance: Instance = self.get_instance()
        if instance is None:
            return

        network_port = instance.network_port
        network = network_port.network

        networkdata = {
            'version': 1,
            'config': [
                {
                    "type": "physical",
                    "name": "eth0",
                    "subnets": [
                        {
                            "type": "static",
                            "address": str(network_port.ip_address),
                            "netmask": network.cidr.with_netmask.split("/")[1],
                            "gateway": str(network.gateway),
                            "dns_search": ["sandwich.local"],
                            "dns_nameservers": [str(ns) for ns in network.dns_servers]
                        }
                    ]
                }
            ]
        }

        await self.write(PacketCode.RESPONSE_NETWORKDATA, yaml.safe_dump(networkdata, default_flow_style=False))

    async def write_userdata(self):
        instance: Instance = self.get_instance()
        if instance is None:
            return

        await self.write(PacketCode.RESPONSE_USERDATA, instance.user_data)

    async def write_security_data(self):

        instance: Instance = self.get_instance()
        if instance is None:
            return

        service_account = instance.service_account

        token_data = {
            # Token only lasts 30 minutes. This should be more than enough
            'expires_at': arrow.now().shift(minutes=+30),
            'service_account': {
                'id': service_account.id,
                'name': service_account.name,
            },
            'project': instance.project_id,
            'roles': {
                'global': [],
                'project': service_account.role_ids
            }
        }

        await self.write(PacketCode.RESPONSE_SECURITYDATA,
                         self.fernet.encrypt(json.dumps(token_data).encode()).decode())

    async def write(self, packet_code, data):
        b64data = base64.b64encode(data.encode()).decode('ascii')
        packet_data = "!!" + packet_code.value + "#" + b64data + '\n'
        self.writer.write(packet_data.encode() + CR)
        await self.writer.drain()

    async def process_packets(self, packet_code, data):
        try:
            packet_code = PacketCode(packet_code)
        except ValueError:
            self.logger.error("Received unknown packet code '%s' from vm '%s'" % (packet_code, self.vm_name))
            return

        self.logger.debug("Received packet code '%s' from vm '%s'" % (packet_code, self.vm_name))

        if packet_code == PacketCode.REQUEST_METADATA:
            await self.write_metadata()
        elif packet_code == PacketCode.REQUEST_USERDATA:
            await self.write_userdata()
        elif packet_code == PacketCode.REQUEST_SECURITYDATA:
            await self.write_security_data()
        elif packet_code == PacketCode.REQUEST_NETWORKDATA:
            await self.write_networkdata()
