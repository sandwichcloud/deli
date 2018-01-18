from threading import RLock

from go_defer import with_defer, defer

from deli.kubernetes.controller import ModelController
from deli.kubernetes.resources.const import NETWORK_LABEL, NETWORK_PORT_LABEL
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.instance.model import Instance
from deli.kubernetes.resources.v1alpha1.network.model import Network, NetworkPort


class NetworkController(ModelController):
    def __init__(self, worker_count, resync_seconds, vmware):
        super().__init__(worker_count, resync_seconds, Network, vmware)

    def sync_model_handler(self, model: Network):
        state_funcs = {
            ResourceState.ToCreate: self.to_create,
            ResourceState.Creating: self.creating,
            ResourceState.Created: self.created,
            ResourceState.ToDelete: self.to_delete,
            ResourceState.Deleting: self.deleting,
            ResourceState.Deleted: self.deleted
        }

        if model.state not in state_funcs:
            return

        state_funcs[model.state](model)

    def to_create(self, model):
        model.state = ResourceState.Creating
        model.save()

    @with_defer
    def creating(self, model: Network):
        defer(model.save)

        region = model.region
        if region is None:
            model.state = ResourceState.ToDelete
            return

        with self.vmware.client_session() as vmware_client:
            datacenter = self.vmware.get_datacenter(vmware_client, region.datacenter)
            if datacenter is None:
                model.error_message = "Could not find VMWare Datacenter for region %s " % str(region.id)
                return

            port_group = self.vmware.get_port_group(vmware_client, model.port_group, datacenter)
            if port_group is None:
                model.error_message = "Could not find port group"
                return

        model.state = ResourceState.Created

    def created(self, model: Network):
        # Check our region, if it is gone we should be deleted
        region = model.region
        if region is None:
            model.delete()
            return

    def to_delete(self, model):
        model.state = ResourceState.Deleting
        model.save()

    def deleting(self, model):
        # Resources that depend on the network will be auto deleted during their sync
        model.state = ResourceState.Deleted
        model.save()

    def deleted(self, model):
        model.delete(force=True)


class NetworkPortController(ModelController):

    def __init__(self, worker_count, resync_seconds):
        super().__init__(worker_count, resync_seconds, NetworkPort, None)
        self.lock = RLock()

    def sync_model_handler(self, model):
        state_funcs = {
            ResourceState.ToCreate: self.to_create,
            ResourceState.Creating: self.creating,
            ResourceState.Created: self.created,
            ResourceState.ToDelete: self.to_delete,
            ResourceState.Deleting: self.deleting,
            ResourceState.Deleted: self.deleted
        }

        if model.state not in state_funcs:
            return

        state_funcs[model.state](model)

    def to_create(self, model):
        model.state = ResourceState.Creating
        model.save()

    @with_defer
    def creating(self, model: NetworkPort):
        network: Network = model.network
        if network is None:
            model.delete()
            return

        defer(model.save)

        usable_addresses = []
        start_host = network.pool_start
        end_host = network.pool_end
        for host in network.cidr:

            if host == network.gateway:
                # Skip gateway
                continue

            if host in network.dns_servers:
                # Skip dns servers if in range
                continue

            if start_host <= host <= end_host:
                usable_addresses.append(host)

        self.lock.acquire()
        defer(self.lock.release)

        network_ports = NetworkPort.list_all(label_selector=NETWORK_LABEL + "=" + str(network.id))
        for network_port in network_ports:
            if network_port.ip_address is not None:
                usable_addresses.remove(network_port.ip_address)

        if len(usable_addresses) == 0:
            model.error_message = "No usable ip addresses found."
            return

        model.ip_address = usable_addresses[0]
        model.state = ResourceState.Created
        # We need to save before the lock is released
        model.save()

    def created(self, model: NetworkPort):
        # Check our network, if it is gone we should be deleted
        network = model.network
        if network is None:
            model.state = ResourceState.ToDelete
            return

    def to_delete(self, model):
        model.state = ResourceState.Deleting
        model.save()

    def deleting(self, model):
        instances = Instance.list_all(label_selector=NETWORK_PORT_LABEL + "=" + str(model.id))
        if len(instances) > 0:
            # There is still an instance with the network port so lets wait
            return

        model.state = ResourceState.Deleted
        model.save()

    def deleted(self, model):
        model.delete(force=True)
