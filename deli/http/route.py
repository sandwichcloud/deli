from functools import wraps
from typing import List

from deli.http.request_methods import RequestMethods


class Route(object):
    def __init__(self, route: str = '', methods: List[RequestMethods] = None):
        self.route = route
        self.methods = methods

        if self.methods is None:
            self.methods = [RequestMethods.GET]

    def __call__(self, func):
        func._route = self.route
        func._methods = self.methods

        @wraps(func)
        def wrapped_func(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapped_func
