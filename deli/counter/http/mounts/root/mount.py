import cherrypy
from apispec import APISpec
from cryptography.fernet import Fernet, MultiFernet
from ingredients_http.app import HTTPApplication
from ingredients_http.app_mount import ApplicationMount
from kubernetes import config
from kubernetes.client import Configuration
from pbr.version import VersionInfo
from simple_settings import settings

from deli.cache import cache_client
from deli.counter.auth.token import Token
from deli.kubernetes.resources.model import ProjectResourceModel
from deli.kubernetes.resources.project import Project


class RootMount(ApplicationMount):
    def __init__(self, app: HTTPApplication):
        super().__init__(app=app, mount_point='/')
        self.fernet = MultiFernet([Fernet(key) for key in settings.AUTH_FERNET_KEYS])
        self.api_spec = APISpec(
            title='Sandwich Cloud API',
            openapi_version='3.0.0',
            version=VersionInfo('sandwichcloud-deli').semantic_version().release_string(),
            plugins=[
                "deli.counter.http.spec.plugins.docstring",
            ]
        )

    def validate_token(self):
        authorization_header = cherrypy.request.headers.get('Authorization', None)
        if authorization_header is None:
            raise cherrypy.HTTPError(400, 'Missing Authorization header.')

        method, auth_token, *_ = authorization_header.split(" ")

        if method != 'Bearer':
            raise cherrypy.HTTPError(400, 'Only Bearer tokens are allowed.')

        token = Token.unmarshal(auth_token, self.fernet)
        cherrypy.request.token = token
        cherrypy.request.login = token.email  # This sets the userID field in cherrypy logs

        if 'instance' in token.metadata:
            # If the token is from an instance include the instance name
            # The email will contain the project
            cherrypy.request.login = token.email + '/' + token.metadata['instance']

    def enforce_permission(self, permission_name):
        project = None
        if hasattr(cherrypy.request, 'project'):
            project = cherrypy.request.project
        cherrypy.request.token.enforce_permission(permission_name, project=project)

    def validate_project_scope(self, delete_param=False):
        if 'project_name' in cherrypy.request.params:
            project_name = cherrypy.request.params['project_name']
            if delete_param:
                del cherrypy.request.params['project_name']
            project = Project.get(project_name)
            cherrypy.request.project = project
            if project is None:
                raise cherrypy.HTTPError(404, "The project (%s) could not be found." % project_name)
        else:
            raise cherrypy.HTTPError(500, "Could not infer project from resource URL")

    def resource_object(self, id_param, cls):
        resource_name = str(cherrypy.request.params[id_param])

        if issubclass(cls, ProjectResourceModel):
            resource = cls.get(cherrypy.request.project, resource_name)
        else:
            resource = cls.get(resource_name)

        if resource is None:
            raise cherrypy.HTTPError(404, "The resource could not be found.")

        cherrypy.request.resource_object = resource

    def __setup_tools(self):
        cherrypy.tools.authentication = cherrypy.Tool('on_start_resource', self.validate_token, priority=20)
        cherrypy.tools.project_scope = cherrypy.Tool('on_start_resource', self.validate_project_scope, priority=30)

        cherrypy.tools.resource_object = cherrypy.Tool('before_request_body', self.resource_object, priority=40)
        cherrypy.tools.enforce_permission = cherrypy.Tool('before_request_body', self.enforce_permission, priority=50)

    def __setup_kubernetes(self):
        if settings.KUBE_CONFIG is not None or settings.KUBE_MASTER is not None:
            Configuration.set_default(Configuration())
            if settings.KUBE_CONFIG is not None:
                config.load_kube_config(config_file=settings.KUBE_CONFIG)
            if settings.KUBE_MASTER is not None:
                Configuration._default.host = settings.KUBE_MASTER
        else:
            config.load_incluster_config()

    def __setup_redis(self):
        cache_client.connect(url=settings.REDIS_URL)

    def setup(self):
        self.__setup_tools()
        self.__setup_kubernetes()
        self.__setup_redis()
        super().setup()

    def mount_config(self):
        config = super().mount_config()
        config['tools.authentication.on'] = True
        return config
