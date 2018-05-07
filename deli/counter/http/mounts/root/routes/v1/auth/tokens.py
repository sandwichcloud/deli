import arrow
import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from kubernetes.client.rest import ApiException

from deli.counter.http.mounts.root.routes.v1.auth.validation_models.tokens import ResponseVerifyToken, \
    RequestScopeToken, ResponseOAuthToken
from deli.counter.http.router import SandwichRouter
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.project_member.model import ProjectMember
from deli.kubernetes.resources.v1alpha1.role.model import GlobalRole, ProjectRole


class AuthTokenRouter(SandwichRouter):
    def __init__(self):
        super().__init__('tokens')

    @Route()
    @cherrypy.tools.model_out(cls=ResponseVerifyToken)
    def get(self):
        token = cherrypy.request.token
        project = token.project()

        response = ResponseVerifyToken()
        response.driver = token.driver_name

        global_role_names = []
        for role_id in token.global_role_ids:
            try:
                role: GlobalRole = GlobalRole.get(role_id)
                global_role_names.append(role.name)
            except ApiException as e:
                if e.status != 404:
                    raise
        response.global_roles = global_role_names

        if token.service_account_id is not None:
            response.service_account_id = token.service_account_id
        else:
            response.username = token.username

        if project is not None:
            response.project_id = project.id
            project_role_names = []

            for role_id in token.project_role_ids:
                try:
                    role: ProjectRole = ProjectRole.get(project, role_id)
                    project_role_names.append(role.name)
                except ApiException as e:
                    if e.status != 404:
                        raise
            response.project_roles = project_role_names

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
        token = cherrypy.request.token

        if token.service_account_id is not None:
            raise cherrypy.HTTPError(403, "Service Accounts cannot scope tokens.")

        if token.project() is not None:
            raise cherrypy.HTTPError(403, "Cannot scope an already scoped token.")

        request: RequestScopeToken = cherrypy.request.model

        project = Project.get(request.project_id)
        if project is None:
            raise cherrypy.HTTPError(404, 'A project with the requested id does not exist.')

        project_role_ids = []
        if project.is_member(token.username, token.driver_name):
            member_id = project.get_member_id(token.username, token.driver_name)
            project_member: ProjectMember = ProjectMember.get(project, member_id)
            project_role_ids.extend(project_member.roles)
        else:
            try:
                token.enforce_policy("projects:scope:all")
            except cherrypy.HTTPError:
                raise cherrypy.HTTPError(400, "Only project members can scope to this project")

        token.expires_at = arrow.now().shift(days=+1)
        token.project_id = project.id
        token.project_role_ids = project_role_ids

        response = ResponseOAuthToken()
        response.access_token = token.marshal(self.mount.fernet)
        response.expiry = token.expires_at
        return response
