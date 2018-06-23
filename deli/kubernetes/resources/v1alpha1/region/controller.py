from go_defer import with_defer, defer

from deli.kubernetes.controller import ModelController
from deli.kubernetes.resources.const import REGION_LABEL
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.image.model import Image
from deli.kubernetes.resources.v1alpha1.instance.model import Instance
from deli.kubernetes.resources.v1alpha1.region.model import Region
from deli.kubernetes.resources.v1alpha1.zone.model import Zone


class RegionController(ModelController):
    def __init__(self, worker_count, resync_seconds, vmware):
        super().__init__(worker_count, resync_seconds, Region, vmware)

    def sync_model_handler(self, model: Region):
        state_funcs = {
            ResourceState.ToCreate: self.to_create,
            ResourceState.Creating: self.creating,
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
    def creating(self, model):
        defer(model.save)

        with self.vmware.client_session() as vmware_client:
            datacenter = self.vmware.get_datacenter(vmware_client, model.datacenter)
            if datacenter is None:
                model.error_message = "Could not find VMWare Datacenter"
                return

            datastore = self.vmware.get_datastore(vmware_client, model.image_datastore, datacenter)
            if datastore is None:
                model.error_message = "Could not find VMWare Datastore"
                return

            if model.image_folder is not None:
                folder = self.vmware.get_folder(vmware_client, model.image_folder, datacenter)
                if folder is None:
                    model.error_message = "Could not find VMWare VM & Templates folder."
                    return

        model.state = ResourceState.Created

    def to_delete(self, model):
        model.state = ResourceState.Deleting
        model.save()

    def deleting(self, model):
        if self.can_delete(model):
            model.state = ResourceState.Deleted
            model.save()

    def deleted(self, model):
        if self.can_delete(model):
            model.delete(force=True)

    def can_delete(self, model):
        # These resources need the region to exist to successfully delete
        zones = Zone.list(label_selector=REGION_LABEL + "=" + model.name)
        if len(zones) > 0:
            return False

        images = Image.list_all(label_selector=REGION_LABEL + "=" + model.name)
        if len(images) > 0:
            return False

        instances = Instance.list_all(label_selector=REGION_LABEL + "=" + model.name)
        if len(instances) > 0:
            return False

        return True
