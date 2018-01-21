from deli.kubernetes.controller import ModelController
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.project_member.model import ProjectMember


class ProjectMemberController(ModelController):
    def __init__(self, worker_count, resync_seconds):
        super().__init__(worker_count, resync_seconds, ProjectMember, None)

    def sync_model_handler(self, model):
        state_funcs = {
            ResourceState.ToDelete: self.to_delete,
            ResourceState.Deleting: self.deleting,
            ResourceState.Deleted: self.deleted
        }

        if model.state not in state_funcs:
            return

        state_funcs[model.state](model)

    def to_delete(self, model):
        model.state = ResourceState.Deleting
        model.save()

    def deleting(self, model):
        model.state = ResourceState.Deleted
        model.save()

    def deleted(self, model: ProjectMember):
        model.delete(force=True)
