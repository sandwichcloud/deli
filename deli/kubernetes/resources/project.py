import uuid

import arrow
from kubernetes import client
from kubernetes.client import V1DeleteOptions, V1Namespace
from kubernetes.client.rest import ApiException

from deli.kubernetes.resources.const import NAME_LABEL, MEMBER_LABEL, PROJECT_LABEL


class Project(object):
    # A project is really a Namespace so we can't just subclass ResourceModel
    def __init__(self, raw=None):
        if raw is None:
            raw = {
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {
                    "name": str(uuid.uuid4()),
                    "labels": {
                        NAME_LABEL: None,
                        PROJECT_LABEL: "true"
                    }
                }
            }
        if isinstance(raw, V1Namespace):
            self._raw = raw.to_dict()
        else:
            self._raw = raw

    @property
    def id(self):
        return uuid.UUID(self._raw['metadata']['name'])

    @property
    def name(self):
        return self._raw['metadata']['labels'][NAME_LABEL]

    @name.setter
    def name(self, value):
        self._raw['metadata']['labels'][NAME_LABEL] = value

    def create(self):
        core_api = client.CoreV1Api()
        self._raw = core_api.create_namespace(self._raw).to_dict()

    @classmethod
    def get(cls, id, safe=True):
        core_api = client.CoreV1Api()
        try:
            resp = core_api.read_namespace(str(id)).to_dict()
            if resp is None:
                return None
            if resp['metadata']['labels'] is None:
                return None
            if PROJECT_LABEL not in resp['metadata']['labels']:
                return None
        except ApiException as e:
            if e.status == 404 and safe:
                return None
            raise
        return cls(resp)

    @classmethod
    def get_by_name(cls, name):
        objs = cls.list(label_selector=NAME_LABEL + "=" + name)
        if len(objs) == 0:
            return None
        return objs[0]

    @classmethod
    def list(cls, **kwargs):
        if 'label_selector' in kwargs:
            label_selector = kwargs['label_selector']
            if len(label_selector) > 0:
                kwargs['label_selector'] += "," + PROJECT_LABEL
            else:
                kwargs['label_selector'] += PROJECT_LABEL
        else:
            kwargs['label_selector'] = PROJECT_LABEL
        core_api = client.CoreV1Api()
        raw_list = core_api.list_namespace(**kwargs)
        items = []
        for item in raw_list.items:
            items.append(cls(item))
        return items

    @property
    def created_at(self):
        return arrow.get(self._raw['metadata']['creation_timestamp'])

    @property
    def resource_version(self):
        return self._raw['resourceVersion']

    def delete(self):
        core_api = client.CoreV1Api()
        core_api.delete_namespace(str(self.id), V1DeleteOptions())

    def save(self):
        core_api = client.CoreV1Api()
        self._raw = core_api.replace_namespace(str(self.id), self._raw)

    def is_member(self, username, driver):
        label = driver + "." + MEMBER_LABEL + "/" + username
        return label in self._raw['metadata']['labels']

    def get_member_id(self, username, driver):
        return self._raw['metadata']['labels'][driver + "." + MEMBER_LABEL + "/" + username]

    def add_member(self, project_member):
        label = project_member.driver + "." + MEMBER_LABEL + "/" + project_member.username
        self._raw['metadata']['labels'][label] = str(project_member.id)

    def remove_member(self, project_member):
        label = project_member.driver + "." + MEMBER_LABEL + "/" + project_member.username
        del self._raw['metadata']['labels'][label]
