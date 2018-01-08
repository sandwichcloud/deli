import importlib
import logging

import cherrypy
from kubernetes.client.rest import ApiException
from simple_settings import settings

from deli.counter.auth.driver import AuthDriver
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.role.model import GlobalRole, ProjectRole


class AuthManager(object):
    def __init__(self):
        self.logger = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))
        self.drivers = {}

    def load_drivers(self):
        for driver_string in settings.AUTH_DRIVERS:
            if ':' not in driver_string:
                raise ValueError("AUTH_DRIVER does not contain a module and class. "
                                 "Must be in the following format: 'my.module:MyClass'")

            auth_module, auth_class, *_ = driver_string.split(":")
            try:
                auth_module = importlib.import_module(auth_module)
            except ImportError:
                self.logger.exception("Could not import auth driver's module: " + auth_module)
                raise
            try:
                driver_klass = getattr(auth_module, auth_class)
            except AttributeError:
                self.logger.exception("Could not get driver's module class: " + auth_class)
                raise

            if not issubclass(driver_klass, AuthDriver):
                raise ValueError("AUTH_DRIVER class is not a subclass of '" + AuthDriver.__module__ + ".AuthDriver'")

            driver: AuthDriver = driver_klass()
            self.drivers[driver.name] = driver

        if len(self.drivers) == 0:
            raise ValueError("No auth drivers loaded")

    def enforce_policy(self, policy_name, token_data: dict, project: Project):

        # Check project first because it probably will have less things
        # to loop through
        if project is not None:
            for role_id in token_data['roles']['project']:
                try:
                    role: ProjectRole = ProjectRole.get(project, role_id)
                    if role is None:
                        continue
                    if policy_name in role.policies:
                        return
                except ApiException as e:
                    if e.status != 404:
                        raise

        for role_id in token_data['roles']['global']:
            try:
                role: GlobalRole = GlobalRole.get(role_id)
                if role is None:
                    continue
                if policy_name in role.policies:
                    return
            except ApiException as e:
                if e.status != 404:
                    raise

        raise cherrypy.HTTPError(403, "Insufficient permissions to perform the requested action.")
