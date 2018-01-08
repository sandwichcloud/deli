import uuid

from deli.kubernetes.resources.model import ProjectResourceModel
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.role.model import ProjectRole


class ServiceAccount(ProjectResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['spec'] = {
                'role': None
            }

    @classmethod
    def kind(cls):
        return "SandwichServiceAccount"

    @property
    def role_id(self):
        return uuid.UUID(self._raw['spec']['role'])

    @property
    def role(self):
        return ProjectRole.get(self.project, self._raw['spec']['role'])

    @role.setter
    def role(self, value):
        self._raw['spec']['role'] = str(value.id)

    @classmethod
    def create_default_service_account(cls, project: Project):
        service_account = cls()
        service_account.name = "default"
        service_account.project = project
        service_account.role = ProjectRole.get_by_name(project, 'default-service-account')
        service_account.create()
