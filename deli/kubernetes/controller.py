import concurrent.futures
import logging
from abc import ABC, abstractmethod

from go_defer import with_defer, defer
from kubernetes import client

from deli.kubernetes.informer import Informer
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.workqueue import WorkQueue


class Controller(ABC):
    def __init__(self, worker_count, resync_seconds, list_func, *list_args, **list_kwargs):
        super().__init__()
        self.logger = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))
        self.worker_count = worker_count

        self.informer = Informer(resync_seconds, list_func, *list_args, **list_kwargs)
        self.informer.add_event_funcs(self.__add_func, self.__update_func, None)

        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.worker_count)

        self.workqueue = WorkQueue()

    def __add_func(self, obj):
        metadata = obj.get("metadata")
        key = metadata.get("namespace") + "/" + metadata.get("name") if metadata.get(
            "namespace") != "" else metadata.get("name")
        # Add the key to the queue
        # This allows us to pull the item from cache
        self.workqueue.add(key)

    def __update_func(self, _, obj):
        return self.__add_func(obj)

    def start(self):
        self.informer.start()
        self.informer.wait_for_cache()

        # Run a worker for each thread
        for _ in range(0, self.worker_count):
            self.executor.submit(self.run_worker)

    def run_worker(self):
        while self.process_next_item():
            pass

    def process_next_item(self):
        obj, shutdown = self.workqueue.get()
        if shutdown:
            # If the queue is shutdown we should stop working
            return False

        @with_defer
        def _process_item(key):
            # Remove from workqueue because we are done with the object
            defer(self.workqueue.done, key)
            self.sync_handler(key)

        # noinspection PyBroadException
        try:
            _process_item(obj)
        except (SystemExit, KeyboardInterrupt, GeneratorExit):
            # Ignore these exceptions, exiting will be handled via signals
            pass
        except Exception:
            # Catch all errors and just log them so the loop doesn't break
            self.logger.exception("Error processing item: " + obj)

        return True

    def stop(self):
        self.informer.stop()
        self.workqueue.shutdown()
        self.executor.shutdown()

    @abstractmethod
    def sync_handler(self, key):
        raise NotImplementedError


class ModelController(Controller):
    def __init__(self, worker_count, resync_seconds, model_cls, vmware=None):
        self.model_cls = model_cls
        self.vmware = vmware

        # We use this to query all namespaces
        crd_api = client.CustomObjectsApi()
        list_func = crd_api.list_cluster_custom_object

        list_args, list_kwargs = self.model_cls.list_sig()

        super().__init__(worker_count, resync_seconds, list_func, *list_args, **list_kwargs)

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
