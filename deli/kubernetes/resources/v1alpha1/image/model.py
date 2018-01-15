import enum
import uuid

from deli.kubernetes.resources.const import REGION_LABEL, IMAGE_VISIBILITY_LABEL, PROJECT_LABEL, IMAGE_MEMBER_LABEL
from deli.kubernetes.resources.model import GlobalResourceModel
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.region.model import Region


class ImageVisibility(enum.Enum):
    PUBLIC = 'PUBLIC'
    PRIVATE = 'PRIVATE'
    SHARED = 'SHARED'


class Image(GlobalResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['metadata']['labels'][PROJECT_LABEL] = None
            self._raw['metadata']['labels'][REGION_LABEL] = None
            self._raw['metadata']['labels'][IMAGE_VISIBILITY_LABEL] = ImageVisibility.PRIVATE.value
            self._raw['spec'] = {
                'fileName': None
            }

    @property
    def project_id(self):
        return uuid.UUID(self._raw['metadata']['labels'][PROJECT_LABEL])

    @property
    def project(self):
        return Project.get(self._raw['metadata']['labels'][PROJECT_LABEL])

    @project.setter
    def project(self, value):
        self._raw['metadata']['labels'][PROJECT_LABEL] = str(value.id)

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

    @property
    def visibility(self):
        return ImageVisibility(self._raw['metadata']['labels'][IMAGE_VISIBILITY_LABEL])

    @visibility.setter
    def visibility(self, value):
        self._raw['metadata']['labels'][IMAGE_VISIBILITY_LABEL] = value.value

    def add_member(self, project_id):
        self._raw['metadata']['labels'][IMAGE_MEMBER_LABEL + "/" + str(project_id)] = "1"

    def remove_member(self, project_id):
        self._raw['metadata']['labels'].pop(IMAGE_MEMBER_LABEL + "/" + str(project_id), None)

    def member_ids(self):
        member_ids = []

        for label in self._raw['metadata']['labels']:
            if label.startswith(IMAGE_MEMBER_LABEL) is False:
                continue
            member_ids.append(label.split("/")[1])

        return member_ids

    def is_member(self, project_id):
        return IMAGE_MEMBER_LABEL + "/" + str(project_id) in self._raw['metadata']['labels']
