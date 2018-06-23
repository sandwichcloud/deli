import enum

from deli.kubernetes.resources.const import REGION_LABEL
from deli.kubernetes.resources.model import ProjectResourceModel
from deli.kubernetes.resources.v1alpha1.region.model import Region


class ImageVisibility(enum.Enum):
    PUBLIC = 'PUBLIC'
    PRIVATE = 'PRIVATE'


class ImageTask(enum.Enum):
    IMAGING_INSTANCE = 'IMAGING_INSTANCE'


class Image(ProjectResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['metadata']['labels'][REGION_LABEL] = ''
            self._raw['spec'] = {
                'fileName': None
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

    @region.setter
    def region(self, value):
        self._raw['metadata']['labels'][REGION_LABEL] = value.name

    @property
    def file_name(self):
        return self._raw['spec']['fileName']

    @file_name.setter
    def file_name(self, value):
        self._raw['spec']['fileName'] = value

    @property
    def task(self):
        if self._raw['status']['task']['name'] is None:
            return None
        return ImageTask(self._raw['status']['task']['name'])

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
