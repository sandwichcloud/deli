import uuid

from deli.kubernetes.resources.model import ProjectResourceModel
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.role.model import ProjectRole


class ServiceAccount(ProjectResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['spec'] = {
                'roles': []
            }

    @classmethod
    def kind(cls):
        return "SandwichServiceAccount"

    @property
    def role_ids(self):
        roles_ids = []
        for role_id in self._raw['spec']['roles']:
            roles_ids.append(uuid.UUID(role_id))
        return roles_ids

    @property
    def roles(self):
        roles = []
        for role_id in self._raw['spec']['roles']:
            role = ProjectRole.get(self.project, role_id)
            if role is not None:
                roles.append(role)
        return roles

    @roles.setter
    def roles(self, value):
        role_ids = []
        for role in value:
            role_ids.append(str(role.id))
        self._raw['spec']['roles'] = role_ids

    @classmethod
    def create_default_service_account(cls, project: Project):
        service_account = cls()
        service_account.name = "default"
        service_account.project = project
        service_account.roles = [ProjectRole.get_by_name(project, 'default-service-account')]
        service_account.create()
