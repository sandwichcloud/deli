from deli.counter.auth.policy import POLICIES
from deli.kubernetes.controller import ModelController
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.role.model import ProjectRole, GlobalRole


class GlobalRoleController(ModelController):
    def __init__(self, worker_count, resync_seconds):
        super().__init__(worker_count, resync_seconds, GlobalRole, None)

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

    def created(self, model: GlobalRole):
        if model.name != 'admin':
            return

        policy_names = [p['name'] for p in POLICIES]

        if model.policies == policy_names:
            return

        model.policies = policy_names
        model.save(ignore=True)

    def to_delete(self, model):
        model.state = ResourceState.Deleting
        model.save()

    def deleting(self, model):
        model.state = ResourceState.Deleted
        model.save()

    def deleted(self, model):
        model.delete(force=True)


class ProjectRoleController(ModelController):
    def __init__(self, worker_count, resync_seconds):
        super().__init__(worker_count, resync_seconds, ProjectRole, None)

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

    def created(self, model: ProjectRole):
        if model.name not in ['default-member', 'default-service-account']:
            return

        member_policies = []
        service_account_policies = []

        for p in POLICIES:
            tags = p.get('tags', [])
            if 'default_project_member' in tags:
                member_policies.append(p['name'])
            if 'default_service_account' in tags:
                service_account_policies.append(p['name'])

        if model.name == 'default-member':
            policies = member_policies
        else:
            policies = service_account_policies

        if model.policies == policies:
            return

        model.policies = policies
        model.save()

    def to_delete(self, model):
        model.state = ResourceState.Deleting
        model.save()

    def deleting(self, model):
        model.state = ResourceState.Deleted
        model.save()

    def deleted(self, model: ProjectRole):
        model.delete(force=True)
