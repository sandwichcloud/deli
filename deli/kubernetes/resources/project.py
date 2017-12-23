import json
import uuid

import arrow
from kubernetes import client
from kubernetes.client import V1DeleteOptions, V1Namespace
from kubernetes.client.rest import ApiException

from deli.kubernetes.resources.const import NAME_LABEL


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
                        "sandwichcloud.com/project": "true"
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
        core_api.create_namespaced_config_map(str(self.id), {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": "project-members"
            },
            "data": {}
        })

    @classmethod
    def get(cls, id, safe=True):
        core_api = client.CoreV1Api()
        try:
            resp = core_api.read_namespace(str(id)).to_dict()
            if resp is None:
                return None
            if resp['metadata']['labels'] is None:
                return None
            if 'sandwichcloud.com/project' not in resp['metadata']['labels']:
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
    def list_sig(cls):
        return [], {"label_selector": "sandwichcloud.com/project"}

    @classmethod
    def list(cls, **kwargs):
        core_api = client.CoreV1Api()
        _, sig_kwargs = cls.list_sig()
        raw_list = core_api.list_namespace(**{**sig_kwargs, **kwargs})
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

    @property
    def members(self):
        core_api = client.CoreV1Api()
        member_data = core_api.read_namespaced_config_map("project-members", str(self.id)).to_dict()['data']
        for k, v in member_data:
            member_data[k] = json.loads(v)

        return member_data

    def is_member(self, username, driver):
        core_api = client.CoreV1Api()
        configmap = core_api.read_namespaced_config_map("project-members", str(self.id)).to_dict()
        if configmap['data'] is None:
            return False
        return username + '__' + driver in configmap['data']

    def get_member(self, username, driver):
        core_api = client.CoreV1Api()
        configmap = core_api.read_namespaced_config_map("project-members", str(self.id)).to_dict()
        return json.loads(configmap['data'][username + '__' + driver])

    def add_member(self, username, driver, role_ids):
        core_api = client.CoreV1Api()
        configmap = core_api.read_namespaced_config_map("project-members", str(self.id)).to_dict()
        configmap['data'][username + '__' + driver] = json.dumps(role_ids)
        core_api.replace_namespaced_config_map("project-members", str(self.id), configmap)

    def remove_member(self, username, driver):
        core_api = client.CoreV1Api()
        configmap = core_api.read_namespaced_config_map("project-members", str(self.id)).to_dict()
        del configmap['data'][username + '__' + driver]
        core_api.replace_namespaced_config_map("project-members", str(self.id), configmap)
