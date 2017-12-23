import uuid

from deli.kubernetes.resources.const import REGION_LABEL
from deli.kubernetes.resources.model import ProjectResourceModel
from deli.kubernetes.resources.v1alpha1.region.model import Region


class Image(ProjectResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['metadata']['labels'][REGION_LABEL] = None
            self._raw['spec'] = {
                'fileName': None
            }

    @property
    def region_id(self):
        return uuid.UUID(self._raw['metadata']['labels'][REGION_LABEL])

    @property
    def region(self):
        return Region.get(self._raw['metadata']['labels'][REGION_LABEL])

    @region.setter
    def region(self, value):
        self._raw['metadata']['labels'][REGION_LABEL] = str(value.id)

    @property
    def file_name(self):
        return self._raw['spec']['fileName']

    @file_name.setter
    def file_name(self, value):
        self._raw['spec']['fileName'] = value
