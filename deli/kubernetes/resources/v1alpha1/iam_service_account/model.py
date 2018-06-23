import arrow

from deli.kubernetes.resources.model import ProjectResourceModel, SystemResourceModel
from deli.kubernetes.resources.project import Project


class SystemServiceAccount(SystemResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['spec'] = {
                'keys': {}
            }

    @property
    def email(self):
        return "%s@service-account.system.sandwich.local" % self.name

    @property
    def keys(self):
        keys = {}
        for key, date in self._raw['spec']['keys'].items():
            keys[key] = arrow.get(date)

        return keys

    @keys.setter
    def keys(self, value):
        keys = {}
        for key, date in value.items():
            keys[key] = date.isoformat()

        self._raw['spec']['keys'] = keys

    @classmethod
    def create_admin_sa(cls):
        if SystemServiceAccount.get("admin") is None:
            admin_sa = cls()
            admin_sa.name = "admin"
            admin_sa.create()


class ProjectServiceAccount(ProjectResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['spec'] = {
                'keys': {}
            }

    @property
    def email(self):
        return "%s@service-account.%s.sandwich.local" % (self.name, self.project_name)

    @property
    def keys(self):
        keys = {}
        for key, date in self._raw['spec']['keys'].items():
            keys[key] = arrow.get(date)

        return keys

    @keys.setter
    def keys(self, value):
        keys = {}
        for key, date in value.items():
            keys[key] = date.isoformat()

        self._raw['spec']['keys'] = keys

    @classmethod
    def create_default_service_account(cls, project: Project):
        service_account = cls()
        service_account.name = "default"
        service_account.project = project
        service_account.create()
