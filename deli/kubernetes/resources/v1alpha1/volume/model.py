import enum

from deli.kubernetes.resources.const import REGION_LABEL, ZONE_LABEL, ATTACHED_TO_LABEL
from deli.kubernetes.resources.model import ProjectResourceModel
from deli.kubernetes.resources.v1alpha1.instance.model import Instance
from deli.kubernetes.resources.v1alpha1.region.model import Region
from deli.kubernetes.resources.v1alpha1.zone.model import Zone


class VolumeTask(enum.Enum):
    CLONING = 'CLONING'
    GROWING = 'GROWING'
    ATTACHING = 'ATTACHING'
    DETACHING = 'DETACHING'


class Volume(ProjectResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['metadata']['labels'][REGION_LABEL] = ''
            self._raw['metadata']['labels'][ZONE_LABEL] = ''
            self._raw['metadata']['labels'][ATTACHED_TO_LABEL] = ''
            self._raw['spec'] = {
                'size': 0,
                'clonedFrom': None,
                'backingId': None,
            }
            self._raw['status']['task'] = {
                'name': None,
                'kwargs': {}
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

    @property
    def zone_name(self):
        zone_name = self._raw['metadata']['labels'][ZONE_LABEL]
        if zone_name == "":
            return None
        return zone_name

    @property
    def zone(self):
        zone_name = self.zone_name
        if zone_name is None:
            return None
        return Zone.get(zone_name)

    @zone.setter
    def zone(self, value):
        self._raw['metadata']['labels'][REGION_LABEL] = str(value.region.name)
        self._raw['metadata']['labels'][ZONE_LABEL] = str(value.name)

    @property
    def size(self):
        return self._raw['spec']['size']

    @size.setter
    def size(self, value):
        self._raw['spec']['size'] = value

    @property
    def backing_id(self):
        return self._raw['spec']['backingId']

    @backing_id.setter
    def backing_id(self, value):
        self._raw['spec']['backingId'] = value

    @property
    def cloned_from_name(self):
        if self._raw['spec']['clonedFrom'] is None:
            return None
        return self._raw['spec']['clonedFrom']

    @property
    def cloned_from(self):
        if self.cloned_from_name is not None:
            return Volume.get(self.project, str(self.cloned_from_name))
        return None

    @cloned_from.setter
    def cloned_from(self, value):
        if value is None:
            self._raw['spec']['clonedFrom'] = None
        else:
            self._raw['spec']['clonedFrom'] = str(value.name)

    @property
    def attached_to_name(self):
        instance_name = self._raw['metadata']['labels'][ATTACHED_TO_LABEL]
        if instance_name == "":
            return None
        return instance_name

    @property
    def attached_to(self):
        instance_name = self.attached_to_name
        if instance_name is None:
            return None
        return Instance.get(self.project, instance_name)

    @attached_to.setter
    def attached_to(self, value):
        if value is None:
            self._raw['metadata']['labels'][ATTACHED_TO_LABEL] = ""
        else:
            self._raw['metadata']['labels'][ATTACHED_TO_LABEL] = str(value.name)

    @property
    def task(self):
        if self._raw['status']['task']['name'] is None:
            return None
        return VolumeTask(self._raw['status']['task']['name'])

    @task.setter
    def task(self, value):
        if value is None:
            self._raw['status']['task']['name'] = None
            self.task_kwargs = {}
        else:
            self._raw['status']['task']['name'] = value.value

    @property
    def task_kwargs(self):
        return self._raw['status']['task']['kwargs']

    @task_kwargs.setter
    def task_kwargs(self, value):
        self._raw['status']['task']['kwargs'] = value

    def attach(self, instance: Instance):
        self.task = VolumeTask.ATTACHING
        self.task_kwargs = {
            'to': str(instance.name)
        }
