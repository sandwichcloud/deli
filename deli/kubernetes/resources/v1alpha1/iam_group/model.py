from deli.kubernetes.resources.model import SystemResourceModel


class IAMSystemGroup(SystemResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['spec'] = {}

    @property
    def email(self):
        return "%s@group.system.sandwich.local" % self.name

    @property
    def oauth_link(self):
        return self._raw['spec']['oauth_link']

    @oauth_link.setter
    def oauth_link(self, value):
        self._raw['spec']['oauth_link'] = value
