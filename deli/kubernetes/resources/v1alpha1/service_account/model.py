import uuid

from deli.kubernetes.resources.model import ProjectResourceModel, GlobalResourceModel
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.role.model import ProjectRole, GlobalRole


class GlobalServiceAccount(GlobalResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['spec'] = {
                'roles': [],
                'keys': []
            }

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
            role = GlobalRole.get(role_id)
            if role is not None:
                roles.append(role)
        return roles

    @roles.setter
    def roles(self, value):
        role_ids = []
        for role in value:
            role_ids.append(str(role.id))
        self._raw['spec']['roles'] = role_ids

    @property
    def keys(self):
        return self._raw['spec']['keys']

    @keys.setter
    def keys(self, value):
        self._raw['spec']['keys'] = value

    @classmethod
    def create_admin_sa(cls):
        admin_role = GlobalRole.get_by_name("admin")
        
        admin_sa = cls()
        admin_sa.name = "admin"
        admin_sa.roles = [admin_role]
        admin_sa.create()


class ProjectServiceAccount(ProjectResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['spec'] = {
                'roles': [],
                'keys': []
            }

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

    @property
    def keys(self):
        return self._raw['spec']['keys']

    @keys.setter
    def keys(self, value):
        self._raw['spec']['keys'] = value

    @classmethod
    def create_default_service_account(cls, project: Project):
        service_account = cls()
        service_account.name = "default"
        service_account.project = project
        service_account.roles = [ProjectRole.get_by_name(project, 'default-service-account')]
        service_account.create()
