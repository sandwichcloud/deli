from deli.kubernetes.controller import ModelController
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.instance.model import Instance
from deli.kubernetes.resources.v1alpha1.project_quota.model import ProjectQuota
from deli.kubernetes.resources.v1alpha1.volume.model import Volume


class ProjectQuotaController(ModelController):
    def __init__(self, worker_count, resync_seconds):
        super().__init__(worker_count, resync_seconds, ProjectQuota, None)

    def sync_model_handler(self, model):
        state_funcs = {
            ResourceState.Created: self.created,
            ResourceState.ToDelete: self.to_delete,
            ResourceState.Deleting: self.deleting,
            ResourceState.Deleted: self.deleted
        }

        if model.state not in state_funcs:
            return

        state_funcs[model.state](model)

    def created(self, model: ProjectQuota):
        model.used_vcpu = 0
        model.used_ram = 0
        model.used_disk = 0

        instances = Instance.list(model.project)
        for instance in instances:
            model.used_vcpu += instance.vcpus
            model.used_ram += instance.ram
            model.used_disk += instance.disk

        volumes = Volume.list(model.project)
        for volume in volumes:
            model.used_disk += volume.size

        model.save()

    def to_delete(self, model):
        model.state = ResourceState.Deleting
        model.save()

    def deleting(self, model):
        model.state = ResourceState.Deleted
        model.save()

    def deleted(self, model: ProjectQuota):
        model.delete(force=True)
