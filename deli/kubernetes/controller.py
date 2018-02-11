from abc import abstractmethod

from k8scontroller.controller import Controller
from kubernetes import client

from deli.kubernetes.resources.model import ResourceState


class ModelController(Controller):
    def __init__(self, worker_count, resync_seconds, model_cls, vmware=None):
        self.model_cls = model_cls
        self.vmware = vmware

        # We use this to query all namespaces
        crd_api = client.CustomObjectsApi()
        list_func = crd_api.list_cluster_custom_object

        list_args, list_kwargs = self.model_cls.list_sig()

        super().__init__(self.model_cls.__name__, worker_count, resync_seconds, list_func, *list_args, **list_kwargs)

    def sync_handler(self, key):
        obj = self.informer.cache.get(key)
        model = self.model_cls(obj)

        # If the model has deletionTimestamp and it's not already deleting change the state to 'ToDelete'
        if model._raw['metadata'].get('deletionTimestamp', None) is not None:
            if model.state not in [ResourceState.ToDelete, ResourceState.Deleting, ResourceState.Deleted]:
                model.state = ResourceState.ToDelete
                model.save()
                return

        return self.sync_model_handler(model)

    @abstractmethod
    def sync_model_handler(self, model):
        raise NotImplementedError
