from deli.counter.auth.policy import POLICIES
from deli.kubernetes.resources.model import GlobalResourceModel, ProjectResourceModel
from deli.kubernetes.resources.project import Project


class GlobalRole(GlobalResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['spec'] = {
                'policies': []
            }

    @classmethod
    def kind(cls):
        return "SandwichGlobalRole"

    @property
    def policies(self):
        return self._raw['spec']['policies']

    @policies.setter
    def policies(self, value):
        self._raw['spec']['policies'] = value

    @classmethod
    def create_default_roles(cls):
        admin_policies = []

        for policy in POLICIES:
            admin_policies.append(policy['name'])

        admin_role = cls()
        admin_role.name = "admin"
        admin_role.policies = admin_policies
        if cls.get_by_name(admin_role.name) is None:
            admin_role.create()


class ProjectRole(ProjectResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['spec'] = {
                'policies': []
            }

    @classmethod
    def kind(cls):
        return "SandwichProjectRole"

    @property
    def policies(self):
        return self._raw['spec']['policies']

    @policies.setter
    def policies(self, value):
        self._raw['spec']['policies'] = value

    @classmethod
    def create_default_roles(cls, project: Project):
        member_policies = []
        service_account_policies = []

        for policy in POLICIES:
            tags = policy.get('tags', [])
            if 'default_project_member' in tags:
                member_policies.append(policy['name'])
            if 'default_service_account' in tags:
                service_account_policies.append(policy['name'])

        member_role = cls()
        member_role.name = "default-member"
        member_role.project = project
        member_role.policies = member_policies
        member_role.create()

        sa_role = cls()
        sa_role.name = "default-service-account"
        sa_role.project = project
        sa_role.policies = service_account_policies
        sa_role.create()
