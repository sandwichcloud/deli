import importlib
import inspect
import json
import logging
import os
import os.path
import pkgutil
from typing import List, Dict

import cherrypy
from simple_settings import settings

from deli.http.router import Router


class ApplicationMount(object):
    def __init__(self, app, mount_point: str, routers_location: str = 'routes'):
        self.logger = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))
        self.app = app
        self.mount_point = mount_point
        self._dispatcher = cherrypy.dispatch.RoutesDispatcher()
        self.routers_location = routers_location

    def __import_routers(self, package) -> List[Router]:
        routers = []
        for _, name, is_pkg in pkgutil.walk_packages(package.__path__):
            full_name = package.__name__ + '.' + name
            module = importlib.import_module(full_name)
            if is_pkg:
                routers.extend(self.__import_routers(importlib.import_module(full_name)))
            else:
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, Router) and obj is not Router:
                        self.logger.debug("Found Router Object: " + obj.__name__)
                        router = obj()
                        routers.append(router)

        return routers

    def __setup_routers(self):
        try:
            # Import routes_location
            routes_module = importlib.import_module(".." + self.routers_location, self.__module__)
        except ImportError:
            self.logger.exception("Could not import routes location: " + self.routers_location)
            raise

        routers = self.__import_routers(routes_module)
        for router in routers:
            self.logger.debug("Setting up routes for " + router.__module__ + "." + router.__class__.__name__)
            router.mount = self
            module_path = importlib.import_module(router.__module__).__file__
            common_prefix = os.path.commonpath([routes_module.__file__, module_path])
            rel_path = os.path.dirname(os.path.relpath(module_path, common_prefix))
            if os.name == 'nt':
                # Fix paths when running on windows
                rel_path = rel_path.replace('\\', '/')
            if not rel_path:
                router.setup_routes(self._dispatcher, self.mount_point)
            else:
                if self.mount_point == '/':
                    router.setup_routes(self._dispatcher, self.mount_point + rel_path)
                else:
                    router.setup_routes(self._dispatcher, self.mount_point + "/" + rel_path)

    def setup(self):
        self.__setup_routers()

    def mount_config(self) -> Dict:
        return {
            'request.dispatch': self._dispatcher,
            'error_page.default': self.__jsonify_error,
            'tools.response_headers.on': True,
            'tools.response_headers.headers': [('Access-Control-Allow-Origin', '*'),
                                               ('Access-Control-Allow-Headers', 'Content-Type')],
        }

    def __jsonify_error(self, status, message, traceback, version) -> str:
        cherrypy.response.headers['Content-Type'] = 'application/json'
        data = {'status': status, 'message': message, 'method': cherrypy.request.method}

        if settings.DEBUG and status.startswith('5'):
            # Only show traceback when debugging and during a 5xx error. All other errors are considered intentional.
            data['traceback'] = traceback

        return json.dumps(data)
