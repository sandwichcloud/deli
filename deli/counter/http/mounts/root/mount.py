import cherrypy
from cryptography.fernet import Fernet, MultiFernet
from ingredients_http.app import HTTPApplication
from ingredients_http.app_mount import ApplicationMount
from kubernetes import config
from kubernetes.client import Configuration
from simple_settings import settings

from deli.counter.auth.manager import load_drivers
from deli.counter.auth.token import Token
from deli.kubernetes.resources.model import ProjectResourceModel


class RootMount(ApplicationMount):
    def __init__(self, app: HTTPApplication):
        super().__init__(app=app, mount_point='/')
        self.fernet = MultiFernet([Fernet(key) for key in settings.AUTH_FERNET_KEYS])

    def validate_token(self):
        authorization_header = cherrypy.request.headers.get('Authorization', None)
        if authorization_header is None:
            raise cherrypy.HTTPError(400, 'Missing Authorization header.')

        method, fernet_token, *_ = authorization_header.split(" ")

        if method != 'Bearer':
            raise cherrypy.HTTPError(400, 'Only Bearer tokens are allowed.')

        token = Token.unmarshal(fernet_token, self.fernet)
        cherrypy.request.token = token
        cherrypy.request.project = token.project()

    def validate_project_scope(self):
        if cherrypy.request.project is None:
            raise cherrypy.HTTPError(403, "Token not scoped for a project")

    def enforce_policy(self, policy_name):
        cherrypy.request.token.enforce_policy(policy_name)

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
        load_drivers()

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
