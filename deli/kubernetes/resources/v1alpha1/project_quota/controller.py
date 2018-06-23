from deli.kubernetes.controller import ModelController
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.instance.model import Instance
from deli.kubernetes.resources.v1alpha1.project_quota.model import ProjectQuota
from deli.kubernetes.resources.v1alpha1.volume.model import Volume


class ProjectQuotaController(ModelController):
    def __init__(self, worker_count, resync_seconds):
        super().__init__(worker_count, resync_seconds, ProjectQuota, None)

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

    def creating(self, model):
        model.state = ResourceState.Created
        model.save()

    def created(self, model: ProjectQuota):
        used_vcpu = 0
        used_ram = 0
        used_disk = 0

        project = Project.get(model.name)
        if project is None:
            model.delete()
            return

        instances = Instance.list(project)
        for instance in instances:
            used_vcpu += instance.vcpus
            used_ram += instance.ram
            used_disk += instance.disk

        volumes = Volume.list(project)
        for volume in volumes:
            used_disk += volume.size

        if used_vcpu != model.used_vcpu or used_ram != model.used_ram or used_disk != model.used_disk:
            model.used_vcpu = used_vcpu
            model.used_ram = used_ram
            model.used_disk = used_disk
            model.save(ignore=True)

    def to_delete(self, model):
        model.state = ResourceState.Deleting
        model.save()

    def deleting(self, model):
        model.state = ResourceState.Deleted
        model.save()

    def deleted(self, model: ProjectQuota):
        model.delete(force=True)
