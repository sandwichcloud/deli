from threading import Condition

from go_defer import with_defer, defer


class WorkQueue(object):
    def __init__(self):
        self.queue = []
        self.dirty = []
        self.processing = []
        self.condition = Condition()
        self.__shutting_down = False

    @with_defer
    def add(self, item):
        self.condition.acquire()
        defer(self.condition.release)
        if self.__shutting_down:
            return
        if item in self.dirty:
            return

        self.dirty.append(item)
        if item in self.processing:
            return
        self.queue.append(item)
        self.condition.notify()

    @with_defer
    def len(self):
        self.condition.acquire()
        defer(self.condition.release)
        return len(self.queue)

    @with_defer
    def get(self):
        self.condition.acquire()
        defer(self.condition.release)
        while len(self.queue) == 0 and self.__shutting_down is False:
            self.condition.wait()
        if len(self.queue) == 0:
            return None, True

        item, self.queue = self.queue[0], self.queue[1:]

        self.processing.append(item)
        self.dirty.remove(item)

        return item, False

    @with_defer
    def done(self, item):
        self.condition.acquire()
        defer(self.condition.release)

        self.processing.remove(item)
        if item in self.dirty:
            self.queue.append(item)
            self.condition.notify()

    @with_defer
    def shutdown(self):
        self.condition.acquire()
        defer(self.condition.release)
        self.__shutting_down = True
        self.condition.notify_all()

    @property
    @with_defer
    def shutting_down(self):
        self.condition.acquire()
        defer(self.condition.release)
        return self.__shutting_down
