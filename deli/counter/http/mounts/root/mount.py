import json

import arrow
import cherrypy
from cryptography.fernet import Fernet, MultiFernet, InvalidToken
from ingredients_http.app import HTTPApplication
from ingredients_http.app_mount import ApplicationMount
from kubernetes import config
from kubernetes.client import Configuration
from simple_settings import settings

from deli.counter.auth.manager import AuthManager
from deli.kubernetes.resources.model import ProjectResourceModel
from deli.kubernetes.resources.project import Project


class RootMount(ApplicationMount):
    def __init__(self, app: HTTPApplication):
        super().__init__(app=app, mount_point='/')
        self.auth_manager: AuthManager = None
        self.messaging = None

    def validate_token(self):
        authorization_header = cherrypy.request.headers.get('Authorization', None)
        if authorization_header is None:
            raise cherrypy.HTTPError(400, 'Missing Authorization header.')

        method, fernet_token, *_ = authorization_header.split(" ")

        if method != 'Bearer':
            raise cherrypy.HTTPError(400, 'Only Bearer tokens are allowed.')

        fernets = []
        for key in settings.AUTH_FERNET_KEYS:
            fernets.append(Fernet(key))
        fernet = MultiFernet(fernets)

        try:
            token_data_bytes = fernet.decrypt(fernet_token.encode())
        except InvalidToken:
            raise cherrypy.HTTPError(401, 'Invalid Authorization Token.')

        token_json = json.loads(token_data_bytes.decode())

        expires_at = arrow.get(token_json['expires_at'])

        if expires_at <= arrow.now():
            # Token is expired so it is invalid
            raise cherrypy.HTTPError(401, 'Invalid Authorization Token.')

        cherrypy.request.token = {
            'roles': token_json['roles']
        }
        cherrypy.request.user = token_json.get('user')
        cherrypy.request.service_account = token_json.get('service_account')
        cherrypy.request.project = None

        project_id = token_json.get('project')

        if project_id is not None:
            project = Project.get(project_id)
            if project is None:
                raise cherrypy.HTTPError(400, 'Current scoped project does not exist.')
            cherrypy.request.project = project

    def validate_project_scope(self):
        if cherrypy.request.project is None:
            raise cherrypy.HTTPError(403, "Token not scoped for a project")

    def enforce_policy(self, policy_name):
        self.auth_manager.enforce_policy(policy_name, cherrypy.request.token, cherrypy.request.project)

    def resource_object(self, id_param, cls):
        resource_id = cherrypy.request.params[id_param]

        if issubclass(cls, ProjectResourceModel):
            resource = cls.get(cherrypy.request.project, resource_id)
        else:
            resource = cls.get(resource_id)

        if resource is None:
            raise cherrypy.HTTPError(404, "The resource could not be found.")

        cherrypy.request.resource_object = resource

    def __setup_tools(self):
        cherrypy.tools.authentication = cherrypy.Tool('on_start_resource', self.validate_token, priority=20)
        cherrypy.tools.project_scope = cherrypy.Tool('on_start_resource', self.validate_project_scope, priority=30)

        cherrypy.tools.enforce_policy = cherrypy.Tool('before_request_body', self.enforce_policy, priority=40)
        cherrypy.tools.resource_object = cherrypy.Tool('before_request_body', self.resource_object, priority=50)

    def __setup_auth(self):
        self.auth_manager = AuthManager()
        self.auth_manager.load_drivers()

    def __setup_kubernetes(self):
        if settings.KUBE_CONFIG is not None or settings.KUBE_MASTER is not None:
            Configuration.set_default(Configuration())
            if settings.KUBE_CONFIG is not None:
                config.load_kube_config(config_file=settings.KUBE_CONFIG)
            if settings.KUBE_MASTER is not None:
                Configuration._default.host = settings.KUBE_MASTER
        else:
            config.load_incluster_config()

    def setup(self):
        self.__setup_tools()
        self.__setup_auth()
        self.__setup_kubernetes()
        super().setup()

    def mount_config(self):
        config = super().mount_config()
        config['tools.authentication.on'] = True
        return config
