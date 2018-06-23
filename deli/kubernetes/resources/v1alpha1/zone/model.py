from deli.kubernetes.resources.const import REGION_LABEL
from deli.kubernetes.resources.model import SystemResourceModel
from deli.kubernetes.resources.v1alpha1.region.model import Region


class Zone(SystemResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['metadata']['labels'][REGION_LABEL] = ''
            self._raw['spec'] = {
                'vmCluster': None,
                'vmDatastore': None,
                'vmFolder': None,
                'provision': {
                    'core': 100,
                    'ram': 100
                }
            }

    @property
    def region_name(self):
        region_name = self._raw['metadata']['labels'][REGION_LABEL]
        if region_name == "":
            return None
        return region_name

    @property
    def region(self):
        region_name = self.region_name
        if region_name is None:
            return None
        return Region.get(region_name)

    @region.setter
    def region(self, value):
        self._raw['metadata']['labels'][REGION_LABEL] = value.name

    @property
    def vm_cluster(self):
        return self._raw['spec']['vmCluster']

    @vm_cluster.setter
    def vm_cluster(self, value):
        self._raw['spec']['vmCluster'] = value

    @property
    def vm_datastore(self):
        return self._raw['spec']['vmDatastore']

    @vm_datastore.setter
    def vm_datastore(self, value):
        self._raw['spec']['vmDatastore'] = value

    @property
    def vm_folder(self):
        return self._raw['spec'].get('vmFolder')

    @vm_folder.setter
    def vm_folder(self, value):
        self._raw['spec']['vmFolder'] = value

    @property
    def core_provision_percent(self):
        return self._raw['spec']['provision']['core']

    @core_provision_percent.setter
    def core_provision_percent(self, value):
        self._raw['spec']['provision']['core'] = value

    @property
    def ram_provision_percent(self):
        return self._raw['spec']['provision']['ram']

    @ram_provision_percent.setter
    def ram_provision_percent(self, value):
        self._raw['spec']['provision']['ram'] = value

    @property
    def schedulable(self):
        return self._raw['spec']['schedulable']

    @schedulable.setter
    def schedulable(self, value):
        self._raw['spec']['schedulable'] = value
