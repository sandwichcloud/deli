import json

import arrow
from kubernetes import client
from kubernetes.client import V1DeleteOptions, V1Namespace
from kubernetes.client.rest import ApiException

from deli.cache import cache_client
from deli.kubernetes.resources.const import PROJECT_LABEL


class Project(object):
    # A project is really a Namespace so we can't just subclass ResourceModel
    def __init__(self, raw=None):
        if raw is None:
            raw = {
                "apiVersion": "v1",
                "kind": "Namespace",
                "metadata": {
                    "name": '',
                    "labels": {
                        PROJECT_LABEL: "true"
                    }
                }
            }
        if isinstance(raw, V1Namespace):
            self._raw = raw.to_dict()
        else:
            self._raw = raw

    @property
    def name(self):
        return self._raw['metadata']['name'].replace("sandwich-", "")

    @name.setter
    def name(self, value):
        self._raw['metadata']['name'] = "sandwich-" + value

    def create(self):
        core_api = client.CoreV1Api()
        self._raw = core_api.create_namespace(self._raw).to_dict()
        cache_client.set('project_' + self.name, self._raw)

    @property
    def state(self):
        return self._raw['status']["phase"]

    @classmethod
    def get(cls, name, safe=True, from_cache=True):
        resp = None
        if from_cache:
            resp = cache_client.get("project_" + name)
        if resp is None:
            core_api = client.CoreV1Api()
            try:
                resp = core_api.read_namespace("sandwich-" + name).to_dict()
                if resp is None:
                    return None
                if resp['metadata']['labels'] is None:
                    return None
                if PROJECT_LABEL not in resp['metadata']['labels']:
                    return None
                o = cls(resp)
                if o.state != 'Terminating':  # Only cache if not terminating
                    cache_client.set('project_' + o.name, o._raw)
            except ApiException as e:
                if e.status == 404:
                    cache_client.delete('project_' + name)
                    if safe:
                        return None
                raise
        else:
            o = cls(resp)

        return o

    @classmethod
    def list(cls, **kwargs):
        items = []

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
        pipe = cache_client.pipeline()
        for item in raw_list.items:
            o = cls(item)
            items.append(o)
            if o.state != 'Terminating':  # Only cache if not terminating
                pipe.set("project_" + o.name, json.dumps(o._raw), ex=cache_client.default_cache_time)
        pipe.execute()
        return items

    @property
    def created_at(self):
        return arrow.get(self._raw['metadata']['creation_timestamp'])

    @property
    def resource_version(self):
        return self._raw['resourceVersion']

    def delete(self):
        core_api = client.CoreV1Api()
        core_api.delete_namespace(self._raw['metadata']['name'], V1DeleteOptions())
        # TODO: Does this cause any side effects since the k8s object isn't deleted right away
        cache_client.delete('project_' + self.name)

    def save(self):
        core_api = client.CoreV1Api()
        try:
            self._raw = core_api.replace_namespace(self._raw['metadata']['name'], self._raw)
            cache_client.set('project_' + self.name, self._raw)
        except ApiException:
            cache_client.delete('project_' + self.name)
            raise
