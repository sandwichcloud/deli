import json
from typing import Optional

import arrow
import cherrypy
from cryptography.fernet import InvalidToken

from deli.counter.auth import manager
from deli.counter.auth.driver import AuthDriver
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.role.model import GlobalRole, ProjectRole
from deli.kubernetes.resources.v1alpha1.service_account.model import GlobalServiceAccount, ProjectServiceAccount


class Token(object):

    def __init__(self):
        self.expires_at = arrow.now().shift(days=+1)
        self.driver_name = None
        self.project_id = None
        self.global_role_ids = []
        self.project_role_ids = []
        self.username = None
        self.service_account_id = None
        self.service_account_key = None

    @classmethod
    def unmarshal(cls, token_string, fernet):
        try:
            token_data_bytes = fernet.decrypt(token_string.encode())
        except InvalidToken:
            raise cherrypy.HTTPError(401, 'Invalid authorization token.')

        token_json = json.loads(token_data_bytes.decode())
        token = cls()
        token.expires_at = arrow.get(token_json['expires_at'])
        token.driver_name = token_json['driver']
        token.project_id = token_json['project']
        token.global_role_ids = token_json['global_role_ids']
        token.project_role_ids = token_json['project_role_ids']
        token.username = token_json['username']
        token.service_account_id = token_json['service_account_id']
        token.service_account_key = token_json['service_account_key']

        if token.expires_at is not None and token.expires_at <= arrow.now():
            # Token is expired so it is invalid
            # Tokens with expires_at of None are static keys
            raise cherrypy.HTTPError(401, 'Invalid Authorization Token.')

        if token.driver_name != "metadata" and token.driver() is None:
            raise cherrypy.HTTPError(500,
                                     "Auth driver '%s' is not loaded, cannot validate token." % token.driver_name)

        project = token.project()
        if token.project_id is not None:
            if project is None:
                raise cherrypy.HTTPError(400, 'Current scoped project does not exist.')

        if token.service_account_id is not None:
            if project is not None:
                service_account = ProjectServiceAccount.get(project, token.service_account_id)
                if service_account is None:
                    service_account = GlobalServiceAccount.get(token.service_account_id)
            else:
                service_account = GlobalServiceAccount.get(token.service_account_id)

            if service_account is None:
                raise cherrypy.HTTPError(401, 'Invalid Authorization Token.')

            if token.service_account_key:
                if token.service_account_key not in service_account.keys:
                    raise cherrypy.HTTPError(401, 'Invalid Authorization Token.')

                # Key is set which means token is static
                # Static keys do not have roles set in the key so we set them here
                role_ids = service_account.role_ids
                if project is None:
                    token.global_role_ids = role_ids
                else:
                    token.project_role_ids = role_ids

        return token

    def marshal(self, fernet):
        token_data = {
            'expires_at': self.expires_at,
            'driver': self.driver_name,
            'project': self.project_id,
            'global_role_ids': self.global_role_ids,
            'project_role_ids': self.project_role_ids,
            'username': self.username,
            'service_account_id': self.service_account_id,
            'service_account_key': self.service_account_key
        }

        return fernet.encrypt(json.dumps(token_data).encode())

    def driver(self) -> Optional[AuthDriver]:
        return manager.DRIVERS.get(self.driver_name)

    def project(self) -> Optional[Project]:
        return Project.get(self.project_id)

    def set_global_roles(self, role_names):
        self.global_role_ids = []
        for role_name in role_names:
            role = GlobalRole.get_by_name(role_name)
            if role is not None:
                self.global_role_ids.append(role.id)

    def enforce_policy(self, policy):
        project = self.project()
        if project is not None:
            for role_id in self.project_role_ids:
                role = ProjectRole.get(project, role_id)
                if role is None:
                    continue
                if policy in role.policies:
                    return

        for role_id in self.global_role_ids:
            role = GlobalRole.get(role_id)
            if role is None:
                continue
            if policy in role.policies:
                return

        raise cherrypy.HTTPError(403, "Insufficient permissions to perform the requested action.")
