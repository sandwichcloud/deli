from go_defer import with_defer, defer

from deli.kubernetes.controller import ModelController
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.image.model import Image


class ImageController(ModelController):
    def __init__(self, worker_count, resync_seconds, vmware):
        super().__init__(worker_count, resync_seconds, Image, vmware)

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
    def creating(self, model: Image):
        region = model.region
        if region is None:
            # The region is gone so lets just delete
            model.delete(force=True)
            return

        if model.file_name is None:
            # Image was created via instance so lets wait until the file is ready
            return

        defer(model.save)

        with self.vmware.client_session() as vmware_client:
            datacenter = self.vmware.get_datacenter(vmware_client, region.datacenter)
            vmware_image = self.vmware.get_image(vmware_client, model.file_name, datacenter)
            if vmware_image is None:
                model.error_message = "Could not find image file"
                return

        model.state = ResourceState.Created

    def created(self, model: Image):
        region = model.region

        # If the region is None we need to error
        if region is None:
            model.error_message = "Region disappeared"
            model.save()
            return

        # Check our region, if it is not created we should be deleted
        if region.state != ResourceState.Created:
            model.delete()
            return

        project = model.project
        if project is None:
            model.delete()
            return

        for member_id in model.member_ids():
            if Project.get(member_id) is None:
                model.remove_member(member_id)
                model.save()

    def to_delete(self, model):
        model.state = ResourceState.Deleting
        model.save()

    @with_defer
    def deleting(self, model):
        defer(model.save)

        if model.file_name is not None:
            # Only try and delete if we have a file

            region = model.region
            if region is not None:
                with self.vmware.client_session() as vmware_client:
                    datacenter = self.vmware.get_datacenter(vmware_client, region.datacenter)
                    vmware_image = self.vmware.get_image(vmware_client, model.file_name, datacenter)
                    if vmware_image is not None:
                        self.vmware.delete_image(vmware_client, vmware_image)
                    else:
                        self.logger.warning(
                            "Tried to delete image %s but couldn't find its backing file" % str(model.id))
            else:
                # The region has poofed so we can't actually delete anything in vmware
                pass

        model.state = ResourceState.Deleted

    def deleted(self, model):
        model.delete(force=True)
