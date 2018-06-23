import enum
import json
import re
import time

import arrow
from kubernetes import client
from kubernetes.client import V1DeleteOptions, V1beta1CustomResourceDefinitionStatus
from kubernetes.client.rest import ApiException

from deli.cache import cache_client
from deli.kubernetes.resources.const import GROUP, UPDATED_AT_ANNOTATION, NAME_LABEL
from deli.kubernetes.resources.project import Project


class ResourceState(enum.Enum):
    ToCreate = 'ToCreate'
    Creating = 'Creating'
    Created = 'Created'
    ToDelete = 'ToDelete'
    Deleting = 'Deleting'
    Deleted = 'Deleted'
    Error = 'Error'


class ResourceModel(object):
    def __init__(self, raw=None):
        if raw is None:
            raw = {
                "apiVersion": GROUP + "/" + self.version(),
                "kind": self.kind(),
                "metadata": {
                    "name": '',
                    "labels": {
                        NAME_LABEL: ''
                    },
                    'annotations': {
                        UPDATED_AT_ANNOTATION: arrow.now('UTC').isoformat(),
                    },
                    "finalizers": [
                        'delete.sandwichcloud.com'
                    ]
                },
                "spec": {},
                "status": {
                    "state": ResourceState.ToCreate.value,
                    "errorMessage": ""
                }
            }
        self._raw = raw

    @property
    def name(self):
        return self._raw['metadata']['name']

    @name.setter
    def name(self, value):
        self._raw['metadata']['name'] = value
        self._raw['metadata']['labels'][NAME_LABEL] = value

    @property
    def state(self):
        return ResourceState(self._raw['status']["state"])

    @state.setter
    def state(self, value):
        self._raw['status']['state'] = value.value
        self._raw['status']['errorMessage'] = ""

    @property
    def error_message(self):
        return self._raw['status']['errorMessage']

    @error_message.setter
    def error_message(self, value):
        self.state = ResourceState.Error
        self._raw['status']['errorMessage'] = value

    @property
    def created_at(self):
        return arrow.get(self._raw['metadata']['creationTimestamp'])

    @property
    def resource_version(self):
        return self._raw['resourceVersion']

    @property
    def updated_at(self):
        return arrow.get(self._raw['metadata']['annotations'][UPDATED_AT_ANNOTATION])

    @updated_at.setter
    def updated_at(self, value):
        self._raw['metadata']['annotations'][UPDATED_AT_ANNOTATION] = value.isoformat()

    @classmethod
    def name_plural(cls):
        return cls.name_singular() + "s"

    @classmethod
    def name_singular(cls):
        name = '-'.join(re.findall('[A-Z][^A-Z]*', cls.kind()))
        return name.lower()

    @classmethod
    def version(cls):
        return cls.__module__.split(".")[-3]

    @classmethod
    def kind(cls):
        return cls.__name__

    @classmethod
    def list_kind(cls):
        return cls.kind() + "List"

    @classmethod
    def create_crd(cls):
        api_extensions_api = client.ApiextensionsV1beta1Api()
        crd = {
            "apiVersion": "apiextensions.k8s.io/v1beta1",
            "kind": "CustomResourceDefinition",
            "metadata": {
                "name": cls.name_plural() + "." + GROUP
            },
            "spec": {
                "group": GROUP,
                "version": cls.version(),
                "scope": "Cluster" if issubclass(cls, SystemResourceModel) else "Namespaced",
                "names": {
                    "plural": cls.name_plural(),
                    "singular": cls.name_singular(),
                    "kind": cls.kind(),
                    "listKind": cls.list_kind(),
                }
            }
        }

        # Patching the client to get around this issue:
        # https://github.com/kubernetes-incubator/client-python/issues/415
        @property
        def accepted_names(self):
            return self._accepted_names

        @accepted_names.setter
        def accepted_names(self, accepted_names):
            self._accepted_names = accepted_names

        @property
        def conditions(self):
            return self._conditions

        @conditions.setter
        def conditions(self, conditions):
            self._conditions = conditions

        V1beta1CustomResourceDefinitionStatus.accepted_names = accepted_names
        V1beta1CustomResourceDefinitionStatus.conditions = conditions
        try:
            api_extensions_api.create_custom_resource_definition(crd)
        except ApiException as e:
            # If it already exists don't error
            if e.status != 409:
                raise

    @classmethod
    def wait_for_crd(cls):
        name = cls.name_plural() + "." + GROUP
        api_extensions_api = client.ApiextensionsV1beta1Api()
        while True:
            try:
                crd = api_extensions_api.read_custom_resource_definition(name)
                for cond in crd.status.conditions:
                    if cond.type == "Established":
                        return
                    if cond.type == "NamesAccepted":
                        if cond.status == "False":
                            raise ValueError(
                                "Failed to create CRD %s: name conflict: %s".format(name, cond.message))
            except ApiException as e:
                # If it doesn't exist just wait, k8s may be slow
                if e.status != 404:
                    raise
            time.sleep(1)


class SystemResourceModel(ResourceModel):

    def create(self):
        crd_api = client.CustomObjectsApi()

        self._raw = crd_api.create_cluster_custom_object(GROUP, self.version(), self.name_plural(), self._raw)
        cache_client.set(self.name_plural() + "_" + self.name, self._raw)

    @classmethod
    def get(cls, name, safe=True, from_cache=True):
        resp = None
        if from_cache:
            resp = cache_client.get(cls.name_plural() + "_" + name)
        if resp is None:
            crd_api = client.CustomObjectsApi()
            try:
                resp = crd_api.get_cluster_custom_object(GROUP, cls.version(), cls.name_plural(), name)
                if resp is None:
                    return None
                o = cls(resp)
                cache_client.set(cls.name_plural() + "_" + o.name, o._raw)
            except ApiException as e:
                if e.status == 404:
                    cache_client.delete(cls.name_plural() + "_" + name)
                    if safe:
                        return None
                raise
        else:
            o = cls(resp)

        return o

    def save(self, ignore=False):
        crd_api = client.CustomObjectsApi()
        try:
            self.updated_at = arrow.now('UTC')
            self._raw = crd_api.replace_cluster_custom_object(GROUP, self.version(), self.name_plural(), self.name,
                                                              self._raw)
            cache_client.set(self.name_plural() + "_" + self.name, self._raw)
        except ApiException as e:
            cache_client.delete(self.name_plural() + "_" + self.name)
            if e.status == 409:
                if ignore:
                    return
            raise e

    @classmethod
    def list_sig(cls):
        return [GROUP, cls.version(), cls.name_plural()], {}

    @classmethod
    def list(cls, **kwargs):
        items = []

        crd_api = client.CustomObjectsApi()
        args, sig_kwargs = cls.list_sig()
        raw_list = crd_api.list_cluster_custom_object(*args, **{**sig_kwargs, **kwargs})
        pipe = cache_client.pipeline()
        for item in raw_list['items']:
            o = cls(item)
            items.append(o)
            pipe.set(cls.name_plural() + "_" + o.name, json.dumps(item), ex=cache_client.default_cache_time)
        pipe.execute()

        return items

    def delete(self, force=False):
        if force:
            if 'delete.sandwichcloud.com' in self._raw['metadata']['finalizers']:
                self._raw['metadata']['finalizers'].remove('delete.sandwichcloud.com')
                self.save()
                cache_client.delete(self.name_plural() + "_" + self.name)
            crd_api = client.CustomObjectsApi()
            try:
                crd_api.delete_cluster_custom_object(GROUP, self.version(), self.name_plural(), self.name,
                                                     V1DeleteOptions())
                cache_client.delete(self.name_plural() + "_" + self.name)
            except ApiException as e:
                if e.status != 404:
                    raise
        else:
            self.state = ResourceState.ToDelete
            self.save()


class ProjectResourceModel(ResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['metadata']['namespace'] = None

    @property
    def project_name(self):
        project_name = self._raw['metadata']['namespace']
        if project_name is None:
            return None

        return self._raw['metadata']['namespace'].replace("sandwich-", "")

    @property
    def project(self):
        if self.project_name is None:
            return None
        return Project.get(self.project_name)

    @project.setter
    def project(self, value):
        self._raw['metadata']['namespace'] = "sandwich-" + value.name

    def create(self):
        if self.project_name is None:
            raise ValueError("Project must be set to create %s".format(self.__class__.__name__))

        crd_api = client.CustomObjectsApi()
        self._raw = crd_api.create_namespaced_custom_object(GROUP, self.version(), "sandwich-" + self.project_name,
                                                            self.name_plural(), self._raw)
        cache_client.set(self.name_plural() + "_" + self.project_name + "_" + self.name, self._raw)

    @classmethod
    def get(cls, project, name, safe=True, from_cache=True):
        resp = None
        if from_cache:
            resp = cache_client.get(cls.name_plural() + "_" + project.name + "_" + name)
        if resp is None:
            crd_api = client.CustomObjectsApi()
            try:
                resp = crd_api.get_namespaced_custom_object(GROUP, cls.version(), "sandwich-" + project.name,
                                                            cls.name_plural(), name)
                if resp is None:
                    return None
                o = cls(resp)
                cache_client.set(cls.name_plural() + "_" + o.project_name + "_" + o.name, o._raw)
            except ApiException as e:
                if e.status == 404:
                    cache_client.delete(cls.name_plural() + "_" + project.name + "_" + name)
                    if safe:
                        return None
                raise
        else:
            o = cls(resp)

        return o

    def save(self, ignore=False):
        crd_api = client.CustomObjectsApi()
        try:
            self.updated_at = arrow.now('UTC')
            self._raw = crd_api.replace_namespaced_custom_object(GROUP, self.version(), "sandwich-" + self.project_name,
                                                                 self.name_plural(), self.name, self._raw)
            cache_client.set(self.name_plural() + "_" + self.project_name + "_" + self.name, self._raw)
        except ApiException as e:
            cache_client.delete(self.name_plural() + "_" + self.project.name + "_" + self.name)
            if e.status == 409:
                if ignore:
                    return
            raise e

    @classmethod
    def list_sig(cls):
        return [GROUP, cls.version()], {"plural": cls.name_plural()}

    @classmethod
    def list_all(cls, **kwargs):
        items = []

        crd_api = client.CustomObjectsApi()
        args, sig_kwargs = cls.list_sig()
        # We use this to query all namespaces
        raw_list = crd_api.list_cluster_custom_object(*args, **{**sig_kwargs, **kwargs})
        pipe = cache_client.pipeline()
        for item in raw_list['items']:
            o = cls(item)
            items.append(o)
            pipe.set(cls.name_plural() + "_" + o.project_name + "_" + o.name, json.dumps(item),
                     ex=cache_client.default_cache_time)
        pipe.execute()

        return items

    @classmethod
    def list(cls, project, **kwargs):
        items = []

        crd_api = client.CustomObjectsApi()
        args, sig_kwargs = cls.list_sig()
        args.append("sandwich-" + project.name)
        raw_list = crd_api.list_namespaced_custom_object(*args, **{**sig_kwargs, **kwargs})
        pipe = cache_client.pipeline()
        for item in raw_list['items']:
            o = cls(item)
            items.append(o)
            pipe.set(cls.name_plural() + "_" + project.name + "_" + o.name, json.dumps(item),
                     ex=cache_client.default_cache_time)
        pipe.execute()

        return items

    def delete(self, force=False):
        if force:
            if 'delete.sandwichcloud.com' in self._raw['metadata']['finalizers']:
                self._raw['metadata']['finalizers'].remove('delete.sandwichcloud.com')
                self.save()
                cache_client.delete(self.name_plural() + "_" + self.project.name + "_" + self.name)
            crd_api = client.CustomObjectsApi()
            try:
                crd_api.delete_namespaced_custom_object(GROUP, self.version(), "sandwich-" + self.project.name,
                                                        self.name_plural(), self.name, V1DeleteOptions())
                cache_client.delete(self.name_plural() + "_" + self.project.name + "_" + self.name)
            except ApiException as e:
                cache_client.delete(self.name_plural() + "_" + self.project.name + "_" + self.name)
                if e.status != 404:
                    raise
        else:
            self.state = ResourceState.ToDelete
            self.save()
