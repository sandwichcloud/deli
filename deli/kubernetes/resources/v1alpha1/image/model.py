import enum
import uuid

from deli.kubernetes.resources.const import REGION_LABEL, IMAGE_VISIBILITY_LABEL, PROJECT_LABEL, MEMBER_LABEL, \
    NAME_LABEL
from deli.kubernetes.resources.model import GlobalResourceModel
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.region.model import Region


class ImageVisibility(enum.Enum):
    PUBLIC = 'PUBLIC'
    PRIVATE = 'PRIVATE'


class Image(GlobalResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['metadata']['labels'][PROJECT_LABEL] = ''
            self._raw['metadata']['labels'][REGION_LABEL] = ''
            self._raw['metadata']['labels'][IMAGE_VISIBILITY_LABEL] = ImageVisibility.PRIVATE.value
            self._raw['spec'] = {
                'fileName': None
            }

    @classmethod
    def get_by_name(cls, name, project=None):
        label_selector = [NAME_LABEL + "=" + name]
        if project is not None:
            label_selector.append(PROJECT_LABEL + "=" + str(project.id))
        objs = cls.list(label_selector=",".join(label_selector))
        if len(objs) == 0:
            return None
        return objs[0]

    @property
    def project_id(self):
        project_id = self._raw['metadata']['labels'][PROJECT_LABEL]
        if project_id == "":
            return None
        return uuid.UUID(project_id)

    @property
    def project(self):
        project_id = self.project_id
        if project_id is None:
            return None
        return Project.get(project_id)

    @project.setter
    def project(self, value):
        self._raw['metadata']['labels'][PROJECT_LABEL] = str(value.id)
        self.add_member(value.id)

    @property
    def region_id(self):
        region_id = self._raw['metadata']['labels'][REGION_LABEL]
        if region_id == "":
            return None
        return uuid.UUID(region_id)

    @property
    def region(self):
        region_id = self.region_id
        if region_id is None:
            return None
        return Region.get(region_id)

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

        if value == ImageVisibility.PUBLIC:
            # We are now public so clear members
            for label in list(self._raw['metadata']['labels']):
                if label.startswith(MEMBER_LABEL) is False:
                    continue
                del self._raw['metadata']['labels'][label]
        elif value == ImageVisibility.PRIVATE:
            # We are now private so add our project back as a member
            self.add_member(self.project_id)

        self._raw['metadata']['labels'][IMAGE_VISIBILITY_LABEL] = value.value

    def add_member(self, project_id):
        self._raw['metadata']['labels'][MEMBER_LABEL + "/" + str(project_id)] = "1"

    def remove_member(self, project_id):
        self._raw['metadata']['labels'].pop(MEMBER_LABEL + "/" + str(project_id), None)

    def member_ids(self):
        member_ids = []

        for label in self._raw['metadata']['labels']:
            if label.startswith(MEMBER_LABEL) is False:
                continue
            member_id = label.split("/")[1]
            if member_id == self.project_id:
                continue
            member_ids.append(member_id)

        return member_ids

    def is_member(self, project_id):
        return MEMBER_LABEL + "/" + str(project_id) in self._raw['metadata']['labels']
