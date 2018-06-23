from deli.counter.auth.policy import SYSTEM_POLICIES, PROJECT_POLICIES
from deli.kubernetes.controller import ModelController
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.iam_role.model import IAMProjectRole, IAMSystemRole


class IAMSystemRoleController(ModelController):
    def __init__(self, worker_count, resync_seconds):
        super().__init__(worker_count, resync_seconds, IAMSystemRole, None)

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

    def created(self, model: IAMSystemRole):
        if model.name != 'admin':
            return

        policy_names = [p['name'] for p in SYSTEM_POLICIES]

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


class IAMProjectRoleController(ModelController):
    def __init__(self, worker_count, resync_seconds):
        super().__init__(worker_count, resync_seconds, IAMProjectRole, None)

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

    def created(self, model: IAMProjectRole):
        policies = {
            'viewer': [policy['name'] for policy in PROJECT_POLICIES if 'viewer' in policy.get('tag', [])],
            'editor': [policy['name'] for policy in PROJECT_POLICIES if 'editor' in policy.get('tag', [])],
            'owner': [policy['name'] for policy in PROJECT_POLICIES]
        }

        if model.name not in policies.keys():
            return

        policies = policies[model.name]
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

    def deleted(self, model: IAMProjectRole):
        model.delete(force=True)
