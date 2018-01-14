from deli.kubernetes.resources.model import GlobalResourceModel


class Flavor(GlobalResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['spec'] = {
                'vcpus': 0,
                'ram': 0,
                'disk': 0
            }

    @property
    def vcpus(self):
        return self._raw['status']["vcpus"]

    @vcpus.setter
    def vcpus(self, value):
        self._raw['status']["vcpus"] = value

    @property
    def ram(self):
        return self._raw['status']["ram"]

    @ram.setter
    def ram(self, value):
        self._raw['status']["ram"] = value

    @property
    def disk(self):
        return self._raw['status']["disk"]

    @disk.setter
    def disk(self, value):
        self._raw['status']["disk"] = value
