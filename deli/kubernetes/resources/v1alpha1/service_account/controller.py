from deli.kubernetes.controller import ModelController
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.role.model import ProjectRole, GlobalRole
from deli.kubernetes.resources.v1alpha1.service_account.model import ProjectServiceAccount, GlobalServiceAccount


class GlobalServiceAccountController(ModelController):
    def __init__(self, worker_count, resync_seconds):
        super().__init__(worker_count, resync_seconds, GlobalServiceAccount, None)

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

    def created(self, model: GlobalServiceAccount):
        roles = []
        for role_id in list(model.role_ids):
            role = GlobalRole.get(role_id)
            if role is not None:
                roles.append(role)

        if len(roles) == len(model.role_ids):
            return

        # Some roles no longer exist so we need to fix that
        model.roles = roles
        model.save(ignore=True)

    def to_delete(self, model):
        model.state = ResourceState.Deleting
        model.save()

    def deleting(self, model):
        model.state = ResourceState.Deleted
        model.save()

    def deleted(self, model: GlobalServiceAccount):
        model.delete(force=True)


class ProjectServiceAccountController(ModelController):
    def __init__(self, worker_count, resync_seconds):
        super().__init__(worker_count, resync_seconds, ProjectServiceAccount, None)

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

    def created(self, model: ProjectServiceAccount):
        if model.name == "default":
            return

        roles = []
        for role_id in list(model.role_ids):
            role = ProjectRole.get(model.project, role_id)
            if role is not None:
                roles.append(role)

        if len(roles) == len(model.role_ids):
            return

        # Some roles no longer exist so we need to fix that
        model.roles = roles
        model.save(ignore=True)

    def to_delete(self, model):
        model.state = ResourceState.Deleting
        model.save()

    def deleting(self, model):
        model.state = ResourceState.Deleted
        model.save()

    def deleted(self, model: ProjectServiceAccount):
        model.delete(force=True)
