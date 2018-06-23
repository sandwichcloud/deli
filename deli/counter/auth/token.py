import json
import logging
from typing import List

import arrow
import cherrypy
import jose
import requests
from cryptography.fernet import InvalidToken
from jose import jwt
from simple_settings import settings

from deli.counter.auth.permission import SYSTEM_PERMISSIONS
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.iam_group.model import IAMSystemGroup
from deli.kubernetes.resources.v1alpha1.iam_policy.model import IAMPolicy
from deli.kubernetes.resources.v1alpha1.iam_role.model import IAMSystemRole, IAMProjectRole
from deli.kubernetes.resources.v1alpha1.iam_service_account.model import SystemServiceAccount, ProjectServiceAccount
from deli.kubernetes.resources.v1alpha1.instance.model import Instance


class Token(object):

    def __init__(self):
        self.email = None
        self.service_account = None
        self.metadata = {}  # Extra metadata the token contains, currently only used for service accounts
        self.expires_at = arrow.now('UTC').shift(days=+1)

        self.system_roles = []
        self.oauth_groups = []

        self.logger = logging.getLogger("%s.%s" % (self.__module__, self.__class__.__name__))

    def get_oauth_rsa_key(self, unverified_header):
        r = requests.get(settings.OPENID_ISSUER_URL + ".well-known/openid-configuration")
        if r.status_code != 200:
            try:
                r.raise_for_status()
            except requests.exceptions.RequestException as e:
                self.logger.exception("Backend error while discovering OAuth configuration from provider")
                raise cherrypy.HTTPError(424,
                                         "Backend error while discovering OAuth configuration from provider: "
                                         + e.response.text)

        well_known_data = r.json()
        r = requests.get(well_known_data['jwks_uri'])
        if r.status_code != 200:
            try:
                r.raise_for_status()
            except requests.exceptions.RequestException as e:
                self.logger.exception("Backend error while discovering OAuth keys")
                raise cherrypy.HTTPError(424,
                                         "Backend error while discovering OAuth keys from provider: " + e.response.text)

        rsa_key = {}
        for key in r.json()["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break

        if len(rsa_key) == 0:
            # Header has a invalid kid
            raise cherrypy.HTTPError(401, 'Invalid Authorization Token.')

        return rsa_key

    @classmethod
    def unmarshal(cls, token_string, fernet):
        token = cls()

        try:
            token_data_bytes = fernet.decrypt(token_string.encode())
            token_json = json.loads(token_data_bytes.decode())
            token.expires_at = arrow.get(token_json['expires_at']) if token_json['expires_at'] is not None else None
            if token.expires_at is not None and token.expires_at <= arrow.now('UTC'):
                raise cherrypy.HTTPError(401, 'Invalid Authorization Token.')
            token.metadata = token_json['metadata']
            token.email = token_json['email']
        except InvalidToken:
            try:
                token_payload = jwt.decode(token_string,
                                           token.get_oauth_rsa_key(jwt.get_unverified_header(token_string)),
                                           algorithms=['RS256'], audience=settings.OPENID_CLIENT_ID,
                                           issuer=settings.OPENID_ISSUER_URL)
                token.expires_at = arrow.get(token_payload['exp'])
                token.email = token_payload[settings.OPENID_EMAIL_CLAIM]
                token.oauth_groups = token_payload[settings.OPENID_GROUPS_CLAIM]
            except jose.JOSEError:
                # Unable to decode jwt
                raise cherrypy.HTTPError(401, 'Invalid Authorization Token.')

        username, domain, *_ = token.email.split("@")
        if domain.endswith('sandwich.local'):
            type, project_name, *_ = domain.split('.')
            system = True if project_name == 'system' else False
            project = None
            if system is False:
                project = Project.get(project_name)
                if project is None:
                    # Email domain contains invalid project
                    raise cherrypy.HTTPError(401, 'Invalid Authorization Token.')

            if type == 'service-account':
                if system:
                    service_account = SystemServiceAccount.get(username)
                else:
                    service_account = ProjectServiceAccount.get(project, username)

                if service_account is None:
                    raise cherrypy.HTTPError(401, 'Invalid Authorization Token.')

                if token.metadata['key'] not in service_account.keys:
                    if 'instance' in token.metadata:
                        if Instance.get(project, token.metadata['instance']) is None:
                            # Token says it's from an instance but we can't find it
                            raise cherrypy.HTTPError(401, 'Invalid Authorization Token.')
                    else:
                        # Token says it's a service account key but it doesn't exist
                        raise cherrypy.HTTPError(401, 'Invalid Authorization Token.')
                else:
                    expire_at = service_account.keys[token.metadata['key']]
                    if expire_at <= arrow.now('UTC'):
                        # Service account key is expired
                        raise cherrypy.HTTPError(401, 'Invalid Authorization Token.')

                token.service_account = service_account
            else:
                # Invalid email type
                raise cherrypy.HTTPError(401, 'Invalid Authorization Token.')

        system_policy = IAMPolicy.get("system")
        token.system_roles = token.find_roles(system_policy)

        return token

    def marshal(self, fernet):
        token_data = {
            'email': self.email,
            'metadata': self.metadata,
            'expires_at': self.expires_at,
        }

        return fernet.encrypt(json.dumps(token_data).encode())

    @property
    def identity(self):
        if self.service_account is not None:
            check_email = "serviceAccount:" + self.email
        else:
            check_email = "user:" + self.email

        return check_email

    def find_roles(self, policy: IAMPolicy) -> List[str]:
        roles = []

        for binding in policy.bindings:
            role_name = binding['role']
            members = binding['members']

            # Check if user is in the members list
            if self.identity in members:
                roles.append(role_name)

            # If the user has oauth groups
            # check for groups in the members listing
            # and see if the user is part of them
            if len(self.oauth_groups) > 0:
                for member in members:
                    if member.endswith("group.system.sandwich.local"):
                        group_name = member.split("@")[0]
                        iam_group: IAMSystemGroup = IAMSystemGroup.get(group_name)
                        if iam_group.oauth_link in self.oauth_groups:
                            roles.append(role_name)
                            continue

        return roles

    def get_projects(self) -> List[Project]:
        projects = []
        policies = IAMPolicy.list()
        for policy in policies:
            if policy.name == "system":
                continue
            if len(self.find_roles(policy)) > 0:
                project = Project.get(policy.name)
                if project is not None:
                    projects.append(project)

        return projects

    def enforce_permission(self, permission, project=None):
        if len(self.system_roles) > 0:
            if permission in [p['name'] for p in SYSTEM_PERMISSIONS]:
                for role_name in self.system_roles:
                    role = IAMSystemRole.get(role_name)
                    if role is not None and permission in role.permissions:
                        return
                raise cherrypy.HTTPError(403,
                                         "Insufficient permissions (%s) to perform the requested action." % permission)

        if project is not None:
            project_policy = IAMPolicy.get(project.name)
            if project_policy is None:
                raise cherrypy.HTTPError(500, "Could not find iam policy document for project %s" % project.name)
            project_roles = self.find_roles(project_policy)
            for role_name in project_roles:
                role = IAMProjectRole.get(project, role_name)
                if role is not None and permission in role.permissions:
                    return

            raise cherrypy.HTTPError(403, "Insufficient permissions (%s) to perform the "
                                          "requested action in the project %s." % (permission, project.name))

        raise cherrypy.HTTPError(403, "Insufficient permissions (%s) to perform the requested action." % permission)
