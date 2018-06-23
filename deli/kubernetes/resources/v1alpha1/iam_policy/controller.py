from deli.kubernetes.controller import ModelController
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.iam_policy.model import IAMPolicy
from deli.kubernetes.resources.v1alpha1.iam_role.model import IAMProjectRole, IAMSystemRole


class IAMPolicyController(ModelController):
    def __init__(self, worker_count, resync_seconds):
        super().__init__(worker_count, resync_seconds, IAMPolicy, None)

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

    def created(self, model: IAMPolicy):
        if model.name == "system":
            return

        project = Project.get(model.name)
        if project is None:
            model.delete()
            return

        needs_save = False
        for binding in list(model.bindings):
            role_name = binding['role']
            if project is not None:
                role = IAMProjectRole.get(project, role_name)
            else:
                role = IAMSystemRole.get(role_name)
            if role is None:
                needs_save = True
                model.bindings.remove(binding)

        if needs_save:
            model.save()

    def to_delete(self, model):
        model.state = ResourceState.Deleting
        model.save()

    def deleting(self, model):
        model.state = ResourceState.Deleted
        model.save()

    def deleted(self, model):
        model.delete(force=True)
