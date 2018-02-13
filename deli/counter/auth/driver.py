import json
import logging
from abc import ABCMeta, abstractmethod
from typing import Dict

from cryptography.fernet import Fernet
from simple_settings import settings

from deli.counter.http.router import SandwichRouter
from deli.kubernetes.resources.v1alpha1.role.model import GlobalRole


class AuthDriver(object):
    __metaclass__ = ABCMeta

    def __init__(self, name):
        self.name = name
        self.logger = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))

    @abstractmethod
    def discover_options(self) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def auth_router(self) -> SandwichRouter:
        raise NotImplementedError

    @abstractmethod
    def health(self):
        return None

    def generate_user_token(self, expires_at, username, global_role_names, project=None, project_role_ids=None):
        fernet = Fernet(settings.AUTH_FERNET_KEYS[0])

        global_role_ids = []

        for role_name in global_role_names:
            role = GlobalRole.get_by_name(role_name)
            if role is not None:
                global_role_ids.append(role.id)

        token_data = {
            'expires_at': expires_at,
            'user': {
                'name': username,
                'driver': self.name
            },
            'roles': {
                'global': global_role_ids,
                'project': []
            }
        }

        if project is not None:
            token_data['project'] = project.id
            token_data['roles']['project'] = project_role_ids if project_role_ids is not None else []

        return fernet.encrypt(json.dumps(token_data).encode())
