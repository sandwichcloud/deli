import base64
import enum
import json
import logging
import os

import arrow
import yaml
from cryptography.fernet import Fernet

from deli.kubernetes.resources.const import ID_LABEL
from deli.kubernetes.resources.v1alpha1.instance.model import Instance
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

    def get_instance(self):
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

        fernet = Fernet(os.environ['FERNET_KEY'])

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
                'project': [service_account.role_id]
            }
        }

        await self.write(PacketCode.RESPONSE_SECURITYDATA, fernet.encrypt(json.dumps(token_data).encode()).decode())

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
