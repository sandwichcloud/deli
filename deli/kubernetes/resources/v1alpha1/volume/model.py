import enum
import uuid

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
            self._raw['metadata']['labels'][REGION_LABEL] = None
            self._raw['metadata']['labels'][ZONE_LABEL] = None
            self._raw['metadata']['labels'][ATTACHED_TO_LABEL] = None
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
    def region_id(self):
        return uuid.UUID(self._raw['metadata']['labels'][REGION_LABEL])

    @property
    def region(self):
        return Region.get(self._raw['metadata']['labels'][REGION_LABEL])

    @property
    def zone_id(self):
        return uuid.UUID(self._raw['metadata']['labels'][ZONE_LABEL])

    @property
    def zone(self):
        return Zone.get(self._raw['metadata']['labels'][ZONE_LABEL])

    @zone.setter
    def zone(self, value):
        self._raw['metadata']['labels'][REGION_LABEL] = str(value.region.id)
        self._raw['metadata']['labels'][ZONE_LABEL] = str(value.id)

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
    def cloned_from_id(self):
        if self._raw['spec']['clonedFrom'] is None:
            return None
        return uuid.UUID(self._raw['spec']['clonedFrom'])

    @property
    def cloned_from(self):
        if self.cloned_from_id is not None:
            return Volume.get(self.project, str(self.cloned_from_id))
        return None

    @cloned_from.setter
    def cloned_from(self, value):
        if value is None:
            self._raw['spec']['clonedFrom'] = None
        else:
            self._raw['spec']['clonedFrom'] = str(value.id)

    @property
    def attached_to_id(self):
        instance_id = self._raw['metadata']['labels'][ATTACHED_TO_LABEL]
        if instance_id is None:
            return None
        return uuid.UUID(instance_id)

    @property
    def attached_to(self):
        instance_id = self.attached_to_id
        if instance_id is None:
            return None
        return Instance.get(self.project, instance_id)

    @attached_to.setter
    def attached_to(self, value):
        if value is None:
            self._raw['metadata']['labels'][ATTACHED_TO_LABEL] = None
        else:
            self._raw['metadata']['labels'][ATTACHED_TO_LABEL] = str(value.id)

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
