from deli.counter.auth.policy import SYSTEM_POLICIES, PROJECT_POLICIES
from deli.kubernetes.resources.model import SystemResourceModel, ProjectResourceModel
from deli.kubernetes.resources.project import Project


class IAMSystemRole(SystemResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['spec'] = {
                'policies': []
            }

    @property
    def policies(self):
        return self._raw['spec']['policies']

    @policies.setter
    def policies(self, value):
        self._raw['spec']['policies'] = value

    @classmethod
    def create_default_roles(cls):
        admin_role = cls()
        admin_role.name = "admin"
        admin_role.policies = [policy['name'] for policy in SYSTEM_POLICIES]
        if cls.get(admin_role.name) is None:
            admin_role.create()


class IAMProjectRole(ProjectResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['spec'] = {
                'policies': []
            }

    @property
    def policies(self):
        return self._raw['spec']['policies']

    @policies.setter
    def policies(self, value):
        self._raw['spec']['policies'] = value

    @classmethod
    def create_default_roles(cls, project: Project):
        viewer_role = cls()
        viewer_role.name = "viewer"
        viewer_role.project = project
        viewer_role.policies = [policy['name'] for policy in PROJECT_POLICIES if 'viewer' in policy.get('tag', [])]
        viewer_role.create()

        editor_role = cls()
        editor_role.name = "editor"
        editor_role.project = project
        editor_role.policies = [policy['name'] for policy in PROJECT_POLICIES if 'editor' in policy.get('tag', [])]
        editor_role.create()

        owner_role = cls()
        owner_role.name = "owner"
        owner_role.project = project
        owner_role.policies = [policy['name'] for policy in PROJECT_POLICIES]
        owner_role.create()
