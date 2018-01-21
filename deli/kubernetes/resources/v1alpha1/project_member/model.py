import uuid

from deli.kubernetes.resources.model import ProjectResourceModel


class ProjectMember(ProjectResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['spec'] = {
                'username': None,
                'driver': None,
                'roles': [],
            }

    @property
    def username(self):
        return self._raw['spec']['username']

    @username.setter
    def username(self, value):
        self._raw['spec']['username'] = value

    @property
    def driver(self):
        return self._raw['spec']['driver']

    @driver.setter
    def driver(self, value):
        self._raw['spec']['driver'] = value

    @property
    def roles(self):
        roles = []
        for role_id in self._raw['spec']['roles']:
            roles.append(uuid.UUID(role_id))
        return roles

    @roles.setter
    def roles(self, value):
        role_ids = []
        for role in value:
            role_ids.append(str(role.id))
        self._raw['spec']['roles'] = role_ids
