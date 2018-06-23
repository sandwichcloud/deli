from typing import Optional

from deli.kubernetes.resources.const import VM_ID_LABEL
from deli.kubernetes.resources.v1alpha1.instance.model import Instance
from deli.kubernetes.resources.v1alpha1.network.model import Network
from deli.menu.metadata.vm_client import SandwichVMClient
from vmw_cloudinit_metadata.drivers.driver import Driver
from vmw_cloudinit_metadata.vspc.vm_client import InstanceData, InstanceMetadata, InstanceNetworkData


class SandwichDriver(Driver):

    def new_client(self, vm_name, writer):
        return SandwichVMClient(vm_name, writer, self)

    def parse_options(self, opts):
        pass

    def get_sandwich_instance(self, vm_client) -> Optional[Instance]:
        vm_uuid = vm_client.vm_vc_uuid
        instances = Instance.list_all(label_selector=VM_ID_LABEL + "=" + str(vm_uuid))
        if len(instances) == 0:
            self.logger.warning("Could not find any instances with the uuid of '%s'" % vm_uuid)
            return None
        if len(instances) > 1:
            self.logger.warning("Found multiple instances with the uuid of '%s'" % vm_uuid)
            return None
        return instances[0]

    def get_instance(self, vm_name) -> Optional[InstanceData]:
        instance = self.get_sandwich_instance(vm_name)
        if instance is None:
            return None
        network_port = instance.network_port
        network: Network = network_port.network

        keypairs = []
        for keypair in instance.keypairs:
            keypairs.append(keypair.public_key)

        instance_data = InstanceData()

        metadata = InstanceMetadata()
        metadata.ami_id = instance.image_name
        metadata.instance_id = instance.name
        metadata.region = instance.region.name
        metadata.availability_zone = instance.zone.name
        metadata.tags = instance.tags
        metadata.public_keys = keypairs
        metadata.hostname = 'ip-' + str(network_port.ip_address).replace(".", "-")
        instance_data.metadata = metadata

        network_data = InstanceNetworkData()
        network_data.address = str(network_port.ip_address)
        network_data.netmask = network.cidr.with_netmask.split("/")[1]
        network_data.gateway = str(network.gateway)
        network_data.search = ["sandwich.local"]
        network_data.nameservers = [str(ns) for ns in network.dns_servers]
        instance_data.network = network_data

        instance_data.userdata = instance.user_data

        instance_data.validate()
        return instance_data
