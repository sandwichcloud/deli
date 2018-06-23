from go_defer import with_defer, defer

from deli.kubernetes.controller import ModelController
from deli.kubernetes.resources.const import ZONE_LABEL
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.instance.model import Instance
from deli.kubernetes.resources.v1alpha1.volume.model import Volume
from deli.kubernetes.resources.v1alpha1.zone.model import Zone


class ZoneController(ModelController):
    def __init__(self, worker_count, resync_seconds, vmware):
        super().__init__(worker_count, resync_seconds, Zone, vmware)

    def sync_model_handler(self, model: Zone):
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
    def creating(self, model: Zone):
        defer(model.save)

        with self.vmware.client_session() as vmware_client:
            datacenter = self.vmware.get_datacenter(vmware_client, model.region.datacenter)

            datastore = self.vmware.get_datastore(vmware_client, model.vm_datastore, datacenter)
            if datastore is None:
                model.error_message = "Could not find VMWare datastore."
                return

            cluster = self.vmware.get_cluster(vmware_client, model.vm_cluster, datacenter)
            if cluster is None:
                model.error_message = "Could not find VMWare cluster."
                return

            if model.vm_folder is not None:
                folder = self.vmware.get_folder(vmware_client, model.vm_folder, datacenter)
                if folder is None:
                    model.error_message = "Could not find VMWare VM & Templates folder."
                    return

        model.state = ResourceState.Created

    def created(self, model: Zone):
        region = model.region
        if region.state == ResourceState.Deleting:
            model.delete()
            return

    def to_delete(self, model):
        model.state = ResourceState.Deleting
        model.save()

    def deleting(self, model):
        if self.can_delete(model):
            model.state = ResourceState.Deleted
            model.save()

    def deleted(self, model):
        model.delete(force=True)

    def can_delete(self, model):
        # These resources need the zone to exist to successfully delete
        instances = Instance.list_all(label_selector=ZONE_LABEL + "=" + str(model.name))
        if len(instances) > 0:
            return False

        volumes = Volume.list_all(label_selector=ZONE_LABEL + "=" + str(model.name))
        if len(volumes) > 0:
            return False

        return True
