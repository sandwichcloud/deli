from deli.kubernetes.resources.model import SystemResourceModel


class ProjectQuota(SystemResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['spec'] = {
                'vcpu': 0,
                'ram': 0,
                'disk': 0,
            }
            self._raw['status'].update({
                'usedVCPU': 0,
                'usedRam': 0,
                'usedDisk': 0
            })

    @property
    def vcpu(self):
        return self._raw['spec']['vcpu']

    @vcpu.setter
    def vcpu(self, value):
        self._raw['spec']['vcpu'] = value

    @property
    def ram(self):
        return self._raw['spec']['ram']

    @ram.setter
    def ram(self, value):
        self._raw['spec']['ram'] = value

    @property
    def disk(self):
        return self._raw['spec']['disk']

    @disk.setter
    def disk(self, value):
        self._raw['spec']['disk'] = value

    @property
    def used_vcpu(self):
        return self._raw['status']['usedVCPU']

    @used_vcpu.setter
    def used_vcpu(self, value):
        self._raw['status']['usedVCPU'] = value

    @property
    def used_ram(self):
        return self._raw['status']['usedRam']

    @used_ram.setter
    def used_ram(self, value):
        self._raw['status']['usedRam'] = value

    @property
    def used_disk(self):
        return self._raw['status']['usedDisk']

    @used_disk.setter
    def used_disk(self, value):
        self._raw['status']['usedDisk'] = value
