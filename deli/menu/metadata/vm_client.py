import enum
import os

import arrow
from cryptography.fernet import Fernet
from vmw_cloudinit_metadata.vspc.vm_client import VMClient

from deli.counter.auth.token import Token
from deli.kubernetes.resources.v1alpha1.instance.model import Instance


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


class SandwichVMClient(VMClient):

    def __init__(self, vm_name, writer, driver):
        self.fernet = Fernet(os.environ['FERNET_KEY'])
        super().__init__(vm_name, writer, driver)

    async def write_security_data(self):

        instance: Instance = self.driver.get_sandwich_instance(self)
        if instance is None:
            return

        token = Token()
        token.email = instance.service_account.email
        token.metadata['instance'] = instance.name
        token.expires_at = arrow.now('UTC').shift(minutes=+30)

        await self.write(PacketCode.RESPONSE_SECURITYDATA, token.marshal(self.fernet).decode())

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
        elif packet_code == PacketCode.REQUEST_NETWORKDATA:
            await self.write_networkdata()
        elif packet_code == PacketCode.REQUEST_SECURITYDATA:
            await self.write_security_data()
