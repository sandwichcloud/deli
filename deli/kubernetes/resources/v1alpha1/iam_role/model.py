from deli.counter.auth.permission import SYSTEM_PERMISSIONS, PROJECT_PERMISSIONS
from deli.kubernetes.resources.model import SystemResourceModel, ProjectResourceModel
from deli.kubernetes.resources.project import Project


class IAMSystemRole(SystemResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['spec'] = {
                'permissions': []
            }

    @property
    def permissions(self):
        return self._raw['spec']['permissions']

    @permissions.setter
    def permissions(self, value):
        self._raw['spec']['permissions'] = value

    @classmethod
    def create_default_roles(cls):
        admin_role = cls()
        admin_role.name = "admin"
        admin_role.permissions = [permission['name'] for permission in SYSTEM_PERMISSIONS]
        if cls.get(admin_role.name) is None:
            admin_role.create()


class IAMProjectRole(ProjectResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['spec'] = {
                'permissions': []
            }

    @property
    def permissions(self):
        return self._raw['spec']['permissions']

    @permissions.setter
    def permissions(self, value):
        self._raw['spec']['permissions'] = value

    @classmethod
    def create_default_roles(cls, project: Project):
        viewer_role = cls()
        viewer_role.name = "viewer"
        viewer_role.project = project
        viewer_role.permissions = [permission['name'] for permission in PROJECT_PERMISSIONS if
                                   'viewer' in permission.get('tag', [])]
        viewer_role.create()

        editor_role = cls()
        editor_role.name = "editor"
        editor_role.project = project
        editor_role.permissions = [permission['name'] for permission in PROJECT_PERMISSIONS if
                                   'editor' in permission.get('tag', [])]
        editor_role.create()

        owner_role = cls()
        owner_role.name = "owner"
        owner_role.project = project
        owner_role.permissions = [permission['name'] for permission in PROJECT_PERMISSIONS]
        owner_role.create()
