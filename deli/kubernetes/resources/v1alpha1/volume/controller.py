from go_defer import with_defer, defer

from deli.kubernetes.controller import ModelController
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.region.model import Region
from deli.kubernetes.resources.v1alpha1.volume.model import Volume, VolumeTask
from deli.kubernetes.resources.v1alpha1.zone.model import Zone


class VolumeController(ModelController):
    def __init__(self, worker_count, resync_seconds, vmware):
        super().__init__(worker_count, resync_seconds, Volume, vmware)

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
    def creating(self, model: Volume):
        defer(model.save)

        region: Region = model.region
        if region.schedulable is False:
            model.error_message = "Region is not currently schedulable"
            return

        zone: Zone = model.zone
        if zone.schedulable is False:
            model.error_message = "Zone is not currently schedulable"
            return

        with self.vmware.client_session() as vmware_client:
            datacenter = self.vmware.get_datacenter(vmware_client, region.datacenter)
            datastore = self.vmware.get_datastore(vmware_client, zone.vm_datastore, datacenter)
            cloned_from: Volume = model.cloned_from
            if cloned_from is None:
                if model.cloned_from_id:
                    model.error_message = "Could not clone volume, parent diapered."
                    return
                model.backing_id = self.vmware.create_disk(vmware_client, str(model.id), model.size, datastore)
                model.task = None
                model.state = ResourceState.Created
                return
            else:
                if 'task_key' not in model.task_kwargs:
                    task = self.vmware.clone_disk(vmware_client, str(model.id), str(cloned_from.backing_id), datastore)
                    model.task_kwargs = {"task_key": task.info.key}
                else:
                    task = self.vmware.get_task(vmware_client, model.task_kwargs['task_key'])
                    done, error = self.vmware.is_task_done(task)
                    if done:
                        if error is not None:
                            model.error_message = error
                            return

                        model.backing_id = task.info.result.config.id.id
                        model.task = None
                        model.state = ResourceState.Created

    @with_defer
    def created(self, model: Volume):
        defer(model.save)

        zone = model.zone
        if zone.state == ResourceState.Deleting:
            model.state = ResourceState.ToDelete

        with self.vmware.client_session() as vmware_client:
            datacenter = self.vmware.get_datacenter(vmware_client, model.region.datacenter)
            datastore = self.vmware.get_datastore(vmware_client, zone.vm_datastore, datacenter)
            if model.task == VolumeTask.ATTACHING:
                vm = self.vmware.get_vm(vmware_client, str(model.attached_to_id), datacenter)
                self.vmware.attach_disk(vmware_client, model.backing_id, datastore, vm)
                model.task = None
            elif model.task == VolumeTask.DETACHING:
                self.detach_disk(vmware_client, datacenter, model)
                model.task = None
            elif model.task == VolumeTask.GROWING:
                self.vmware.grow_disk(vmware_client, model.backing_id, model.task_kwargs['size'], datastore)
                model.size = model.task_kwargs['size']
                model.task = None
            elif model.task == VolumeTask.CLONING:
                # Check new volume
                # If it's none, created or errored then we are done cloning
                new_volume = Volume.get(model.project, model.task_kwargs['volume_id'])
                if new_volume is None or new_volume.state in [ResourceState.Created, ResourceState.Error]:
                    model.task = None

            if model.attached_to_id is not None:
                if model.attached_to is None:
                    model.attached_to = None

            if model.cloned_from_id is not None:
                if model.cloned_from is None:
                    model.cloned_from = None

    def detach_disk(self, vmware_client, datacenter, model):
        vm = self.vmware.get_vm(vmware_client, str(model.attached_to_id), datacenter)
        if vm is not None:
            self.vmware.detach_disk(vmware_client, model.backing_id, vm)
        model.attached_to = None

    def to_delete(self, model):
        if model.attached_to is not None:
            # If we are still attached so we need to detach before deleting
            with self.vmware.client_session() as vmware_client:
                datacenter = self.vmware.get_datacenter(vmware_client, model.region.datacenter)
                self.detach_disk(vmware_client, datacenter, model)
        model.state = ResourceState.Deleting
        model.save()

    @with_defer
    def deleting(self, model: Volume):
        defer(model.save)
        if model.backing_id is not None:
            with self.vmware.client_session() as vmware_client:
                datacenter = self.vmware.get_datacenter(vmware_client, model.region.datacenter)
                datastore = self.vmware.get_datastore(vmware_client, model.zone.vm_datastore, datacenter)
                self.vmware.delete_disk(vmware_client, model.backing_id, datastore)
        model.state = ResourceState.Deleted

    def deleted(self, model):
        model.delete(force=True)
