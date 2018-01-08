import logging
import time
from queue import Queue, Empty
from threading import Thread, RLock, Event

from go_defer import with_defer, defer
from kubernetes import watch


class Informer(object):
    def __init__(self, name, resync_seconds, list_func, *list_args, **list_kwargs):
        self.logger = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))
        self.queue = Queue()
        self.name = name
        self.list_func = list_func
        self.list_args = list_args
        self.list_kwargs = list_kwargs
        self.resync_seconds = resync_seconds

        self.add_funcs = []
        self.update_funcs = []
        self.delete_funcs = []

        self.cache = InformerCache()
        self.processor = None
        self.watcher = None
        self.lister = None

    def add_event_funcs(self, add_func, update_func, delete_func):
        if add_func is not None:
            self.add_funcs.append(add_func)
        if update_func is not None:
            self.update_funcs.append(update_func)
        if delete_func is not None:
            self.delete_funcs.append(delete_func)

    def start(self):

        if self.processor is not None:
            raise Exception("Informer already running.")

        self.processor = InformerProcessQueue(self.queue, self.add_funcs, self.update_funcs, self.delete_funcs)
        self.watcher = InformerWatch(self.name, self.queue, self.cache, self.list_func, self.list_args,
                                     self.list_kwargs)
        self.lister = InformerList(self.name, self.queue, self.cache, self.resync_seconds, self.list_func,
                                   self.list_args, self.list_kwargs)

        self.processor.start()
        self.watcher.start()
        self.lister.start()

    # Wait until the cache is filled with the initial objects
    def wait_for_cache(self):
        while self.lister.first_run:
            time.sleep(1)

    def stop(self):
        self.lister.shutdown()
        self.watcher.shutdown()
        self.queue.join()
        # Shutdown the processor last so all remaining items can be processes
        self.processor.shutdown()


class InformerProcessQueue(Thread):
    def __init__(self, queue, add_funcs, update_funcs, delete_funcs):
        super().__init__()
        self.logger = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))
        self.queue = queue
        self.funcs = {
            'ADDED': add_funcs,
            'MODIFIED': update_funcs,
            'DELETED': delete_funcs
        }
        self.shutting_down = False

    def run(self):
        while self.shutting_down is False:
            try:
                event, item = self.queue.get(timeout=1)
                try:
                    for func in self.funcs[event]:
                        if event == 'MODIFIED':
                            func(None, item)
                        else:
                            func(item)
                except (SystemExit, KeyboardInterrupt, GeneratorExit):
                    # Ignore these exceptions, exiting will be handled via signals
                    pass
                except Exception:
                    # Catch all errors and just log them so the loop doesn't break
                    # self.logger.exception("Error running function for event " + event + " and item " + item)
                    pass
                self.queue.task_done()
            except Empty:
                continue

    def shutdown(self):
        self.shutting_down = True


class InformerWatch(Thread):
    def __init__(self, name, queue, cache, list_func, list_args, list_kwargs):
        super().__init__()
        self.logger = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))
        self.name = name
        self.queue = queue
        self.cache = cache
        self.list_func = list_func
        self.list_args = list_args
        self.list_kwargs = list_kwargs
        self.watcher = watch.Watch()
        self.shutting_down = False

    def run(self):
        resource_version = None
        while self.shutting_down is False:
            try:
                if resource_version is None:
                    # List first so we can get the resourceVersion to start at
                    # if we don't do this we get all events from the beginning of history
                    ret = self.list_func(*self.list_args, **self.list_kwargs)
                    resource_version = ret['metadata']['resourceVersion']
                stream = self.watcher.stream(self.list_func, *self.list_args,
                                             **{**self.list_kwargs, 'resource_version': resource_version})
                # If there is nothing to stream this will hang for as long as the api server
                # allows it. Any idea on how to break out sooner as it prevents a quick shutdown?
                for event in stream:
                    operation = event['type']
                    obj = event['object']

                    metadata = obj.get("metadata")
                    resource_version = metadata['resourceVersion']

                    cache_key = metadata.get("namespace") + "/" + metadata.get(
                        "name") if metadata.get("namespace") != "" else metadata.get("name")

                    self.cache.add(cache_key, obj)
                    self.queue.put((operation, obj))
            except Exception as e:
                self.logger.error(
                    "Caught Exception while watching " + self.name +
                    " sleeping for 30 seconds before trying again. Enable debug logging to see exception")
                self.logger.debug("Exception: ", exc_info=True)
                time.sleep(30)

    def shutdown(self):
        self.watcher.stop()
        self.shutting_down = True


class InformerList(Thread):
    def __init__(self, name, queue, cache, resync_seconds, list_func, list_args, list_kwargs):
        super().__init__()
        self.logger = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))
        self.name = name
        self.queue = queue
        self.cache = cache
        self.list_func = list_func
        self.list_args = list_args
        self.list_kwargs = list_kwargs
        self.resync_seconds = resync_seconds
        self.shutting_down = Event()
        self.first_run = True

    @with_defer
    def run(self):
        while True:
            try:
                new_cache = {}
                ret = self.list_func(*self.list_args, **self.list_kwargs)
                for obj in ret['items']:
                    if self.shutting_down.is_set():
                        break
                    metadata = obj.get("metadata")

                    cache_key = metadata.get("namespace") + "/" + metadata.get(
                        "name") if metadata.get("namespace") != "" else metadata.get("name")

                    new_cache[cache_key] = obj
                self.cache.reset(new_cache)
                for _, obj in new_cache.items():
                    self.queue.put(("MODIFIED", obj))
                self.first_run = False
            except:
                self.logger.error(
                    "Caught Exception while listing " + self.name +
                    " sleeping for 30 seconds before trying again. Enable debug logging to see exception")
                self.logger.debug("Exception: ", exc_info=True)
                time.sleep(30)
            if self.shutting_down.wait(timeout=self.resync_seconds):
                break

    def shutdown(self):
        self.shutting_down.set()


class InformerCache(object):
    def __init__(self):
        self.cache = {}
        self.lock = RLock()

    @with_defer
    def get(self, key):
        self.lock.acquire()
        defer(self.lock.release)
        return self.cache.get(key)

    @with_defer
    def add(self, key, item):
        self.lock.acquire()
        defer(self.lock.release)
        self.cache[key] = item

    @with_defer
    def delete(self, key):
        self.lock.acquire()
        defer(self.lock.release)
        self.cache.pop(key, None)

    @with_defer
    def reset(self, new_cache):
        self.lock.acquire()
        defer(self.lock.release)
        self.cache = new_cache
