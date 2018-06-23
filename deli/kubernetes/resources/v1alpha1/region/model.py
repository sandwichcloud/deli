from deli.kubernetes.resources.model import SystemResourceModel


class Region(SystemResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['spec'] = {
                'datacenter': None,
                'imageDatastore': None,
                'imageFolder': None,
                'schedulable': False
            }

    @property
    def datacenter(self):
        return self._raw['spec']['datacenter']

    @datacenter.setter
    def datacenter(self, value):
        self._raw['spec']['datacenter'] = value

    @property
    def image_datastore(self):
        return self._raw['spec']['imageDatastore']

    @image_datastore.setter
    def image_datastore(self, value):
        self._raw['spec']['imageDatastore'] = value

    @property
    def image_folder(self):
        return self._raw['spec'].get('imageFolder')

    @image_folder.setter
    def image_folder(self, value):
        self._raw['spec']['imageFolder'] = value

    @property
    def schedulable(self):
        return self._raw['spec']['schedulable']

    @schedulable.setter
    def schedulable(self, value):
        self._raw['spec']['schedulable'] = value
