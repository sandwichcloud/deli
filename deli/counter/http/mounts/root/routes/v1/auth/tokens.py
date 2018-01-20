import arrow
import cherrypy
from kubernetes.client.rest import ApiException

from deli.counter.http.mounts.root.routes.v1.auth.validation_models.tokens import ResponseVerifyToken, \
    RequestScopeToken, ResponseOAuthToken
from deli.http.request_methods import RequestMethods
from deli.http.route import Route
from deli.http.router import Router
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.role.model import GlobalRole, ProjectRole


class AuthNTokenRouter(Router):
    def __init__(self):
        super().__init__('tokens')

    @Route()
    @cherrypy.tools.model_out(cls=ResponseVerifyToken)
    def get(self):
        global_role_names = []
        for role_name in cherrypy.request.token['roles']['global']:
            try:
                role: GlobalRole = GlobalRole.get(role_name)
                global_role_names.append(role.name)
            except ApiException as e:
                if e.status != 404:
                    raise

        response = ResponseVerifyToken()

        if cherrypy.request.service_account is not None:
            response.service_account_id = cherrypy.request.service_account['id']
            response.service_account_name = cherrypy.request.service_account['name']
        else:
            response.username = cherrypy.request.user['name']
            response.driver = cherrypy.request.user['driver']

        if cherrypy.request.project is not None:
            project_role_names = []

            for role_name in cherrypy.request.token['roles']['project']:
                try:
                    role: ProjectRole = ProjectRole.get(cherrypy.request.project, role_name)
                    project_role_names.append(role.name)
                except ApiException as e:
                    if e.status != 404:
                        raise

            response.project_id = cherrypy.request.project.id
            response.project_roles = project_role_names
        response.global_roles = global_role_names
        return response

    @Route(methods=[RequestMethods.HEAD])
    def head(self):
        cherrypy.response.status = 204
        # Fix for https://github.com/cherrypy/cherrypy/issues/1657
        del cherrypy.response.headers['Content-Type']

    # Generate a new token scoped for the requested project
    @Route(route='scope', methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestScopeToken)
    @cherrypy.tools.model_out(cls=ResponseOAuthToken)
    @cherrypy.tools.enforce_policy(policy_name="projects:scope")
    def scope_token(self):

        if cherrypy.request.service_account is not None:
            raise cherrypy.HTTPError(403, "Service Accounts cannot scope tokens.")

        if cherrypy.request.project is not None:
            raise cherrypy.HTTPError(403, "Cannot scope an already scoped token.")

        request: RequestScopeToken = cherrypy.request.model

        project = Project.get(request.project_id)
        if project is None:
            raise cherrypy.HTTPError(404, 'A project with the requested id does not exist.')

        driver = self.mount.auth_manager.drivers.get(cherrypy.request.user['driver'])
        if driver is None:
            raise cherrypy.HTTPError(500, "Previous auth driver '%s' is not loaded. Cannot scope token."
                                     % cherrypy.request.user['driver'])

        global_role_names = []
        global_role_ids = cherrypy.request.token['roles']['global']
        for role_id in global_role_ids:
            role = GlobalRole.get(role_id)
            if role is not None:
                global_role_names.append(role.name)

        project_role_ids = []

        user = cherrypy.request.user
        if project.is_member(user['name'], user['driver']):
            project_role_ids.extend(project.get_member(user['name'], user['driver']))
        else:
            try:
                self.mount.enforce_policy("projects:scope:all")
            except cherrypy.HTTPError:
                raise cherrypy.HTTPError(400, "Only project members can scope to this project")

        expiry = arrow.now().shift(days=+1)
        token = driver.generate_user_token(expiry, cherrypy.request.user['name'],
                                           global_role_names, project=project,
                                           project_role_ids=project_role_ids)

        response = ResponseOAuthToken()
        response.access_token = token
        response.expiry = expiry
        return response
