import enum
import re
import time
import uuid

import arrow
from kubernetes import client
from kubernetes.client import V1DeleteOptions
from kubernetes.client.rest import ApiException

from deli.kubernetes.resources.const import GROUP, NAME_LABEL
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
                    "name": str(uuid.uuid4()),
                    "labels": {
                        NAME_LABEL: None
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
    def id(self):
        return uuid.UUID(self._raw['metadata']['name'])

    @property
    def name(self):
        return self._raw['metadata']['labels'][NAME_LABEL]

    @name.setter
    def name(self, value):
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
                "scope": "Cluster" if issubclass(cls, GlobalResourceModel) else "Namespaced",
                "names": {
                    "plural": cls.name_plural(),
                    "singular": cls.name_singular(),
                    "kind": cls.kind(),
                    "listKind": cls.list_kind(),
                }
            }
        }
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


class GlobalResourceModel(ResourceModel):
    def create(self):
        crd_api = client.CustomObjectsApi()
        self._raw = crd_api.create_cluster_custom_object(GROUP, self.version(), self.name_plural(), self._raw)

    @classmethod
    def get(cls, id, safe=True):
        crd_api = client.CustomObjectsApi()
        try:
            resp = crd_api.get_cluster_custom_object(GROUP, cls.version(), cls.name_plural(), str(id))
            if resp is None:
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

    def save(self):
        crd_api = client.CustomObjectsApi()
        self._raw = crd_api.replace_cluster_custom_object(GROUP, self.version(), self.name_plural(), str(self.id),
                                                          self._raw)

    @classmethod
    def list_sig(cls):
        return [GROUP, cls.version(), cls.name_plural()], {}

    @classmethod
    def list(cls, **kwargs):
        crd_api = client.CustomObjectsApi()
        args, sig_kwargs = cls.list_sig()
        raw_list = crd_api.list_cluster_custom_object(*args, **{**sig_kwargs, **kwargs})
        items = []
        for item in raw_list['items']:
            items.append(cls(item))
        return items

    def delete(self, force=False):
        if force:
            if 'delete.sandwichcloud.com' in self._raw['metadata']['finalizers']:
                self._raw['metadata']['finalizers'].remove('delete.sandwichcloud.com')
                self.save()
            crd_api = client.CustomObjectsApi()
            try:
                crd_api.delete_cluster_custom_object(GROUP, self.version(), self.name_plural(), str(self.id),
                                                     V1DeleteOptions())
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
    def project_id(self):
        return uuid.UUID(self._raw['metadata']['namespace'])

    @property
    def project(self):
        return Project.get(self._raw['metadata']['namespace'])

    @project.setter
    def project(self, value):
        self._raw['metadata']['namespace'] = str(value.id)

    def create(self):
        if self.project is None:
            raise ValueError("Project must be set to create %s".format(self.__class__.__name__))

        crd_api = client.CustomObjectsApi()
        self._raw = crd_api.create_namespaced_custom_object(GROUP, self.version(), str(self.project.id),
                                                            self.name_plural(), self._raw)

    @classmethod
    def get(cls, project, id, safe=True):
        crd_api = client.CustomObjectsApi()
        try:
            resp = crd_api.get_namespaced_custom_object(GROUP, cls.version(), str(project.id), cls.name_plural(),
                                                        str(id))
            if resp is None:
                return None
        except ApiException as e:
            if e.status == 404 and safe:
                return None
            raise
        return cls(resp)

    @classmethod
    def get_by_name(cls, project, name):
        objs = cls.list(project, label_selector=NAME_LABEL + "=" + name)
        if len(objs) == 0:
            return None
        return objs[0]

    def save(self):
        crd_api = client.CustomObjectsApi()
        self._raw = crd_api.replace_namespaced_custom_object(GROUP, self.version(), str(self.project.id),
                                                             self.name_plural(),
                                                             str(self.id), self._raw)

    @classmethod
    def list_sig(cls):
        return [GROUP, cls.version()], {"plural": cls.name_plural()}

    @classmethod
    def list_all(cls, **kwargs):
        crd_api = client.CustomObjectsApi()
        args, sig_kwargs = cls.list_sig()
        # We use this to query all namespaces
        raw_list = crd_api.list_cluster_custom_object(*args, **{**sig_kwargs, **kwargs})
        items = []
        for item in raw_list['items']:
            items.append(cls(item))
        return items

    @classmethod
    def list(cls, project, **kwargs):
        crd_api = client.CustomObjectsApi()
        args, sig_kwargs = cls.list_sig()
        args.append(str(project.id))
        raw_list = crd_api.list_namespaced_custom_object(*args, **{**sig_kwargs, **kwargs})
        items = []
        for item in raw_list['items']:
            items.append(cls(item))
        return items

    def delete(self, force=False):
        if force:
            if 'delete.sandwichcloud.com' in self._raw['metadata']['finalizers']:
                self._raw['metadata']['finalizers'].remove('delete.sandwichcloud.com')
                self.save()
            crd_api = client.CustomObjectsApi()
            try:
                crd_api.delete_namespaced_custom_object(GROUP, self.version(), str(self.project.id),
                                                        self.name_plural(), str(self.id), V1DeleteOptions())
            except ApiException as e:
                if e.status != 404:
                    raise
        else:
            self.state = ResourceState.ToDelete
            self.save()
