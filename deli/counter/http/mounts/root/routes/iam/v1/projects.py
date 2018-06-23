import uuid

import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.auth.token import Token
from deli.counter.http.mounts.root.routes.iam.v1.validation_models.projects import ResponseProject, \
    RequestCreateProject, \
    ParamsProject, ParamsListProject
from deli.counter.http.router import SandwichRouter
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.iam_policy.model import IAMPolicy
from deli.kubernetes.resources.v1alpha1.iam_role.model import IAMProjectRole
from deli.kubernetes.resources.v1alpha1.iam_service_account.model import ProjectServiceAccount
from deli.kubernetes.resources.v1alpha1.project_quota.model import ProjectQuota


class ProjectRouter(SandwichRouter):
    def __init__(self):
        super().__init__(uri_base='projects')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateProject)
    @cherrypy.tools.model_out(cls=ResponseProject)
    @cherrypy.tools.enforce_permission(permission_name="projects:create")
    def create(self):
        """Create a project
        ---
        post:
            description: Create a project
            tags:
                - iam
                - project
            requestBody:
                description: Project to create
            responses:
                200:
                    description: The created project
        """
        request: RequestCreateProject = cherrypy.request.model

        project = Project.get(request.name)
        if project is not None:
            raise cherrypy.HTTPError(409, 'A project with the requested name already exists.')

        if request.name == "system":
            raise cherrypy.HTTPError(409, 'Cannot use a reserved name as the project name')

        project = Project()
        project.name = request.name
        project.create()

        IAMProjectRole.create_default_roles(project)
        ProjectServiceAccount.create_default_service_account(project)

        quota = ProjectQuota()
        quota.name = project.name
        quota.create()

        IAMPolicy.create_project_policy(project, cherrypy.request.token)

        return ResponseProject.from_database(project)

    @Route(route='{project_name}')
    @cherrypy.tools.model_params(cls=ParamsProject)
    @cherrypy.tools.model_out(cls=ResponseProject)
    @cherrypy.tools.project_scope()
    @cherrypy.tools.resource_object(id_param="project_name", cls=Project)
    @cherrypy.tools.enforce_permission(permission_name="projects:get")
    def get(self, **_):
        """Get a project
        ---
        get:
            description: Get a project
            tags:
                - iam
                - project
            responses:
                200:
                    description: The project
        """
        project: Project = cherrypy.request.resource_object
        return ResponseProject.from_database(project)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListProject)
    @cherrypy.tools.model_out_pagination(cls=ResponseProject)
    def list(self, limit: int, marker: uuid.UUID):
        """List projects
        ---
        get:
            description: List projects
            tags:
                - iam
                - project
            responses:
                200:
                    description: List of projects
        """
        token: Token = cherrypy.request.token

        resp_models = []
        for project in token.get_projects():
            resp_models.append(ResponseProject.from_database(project))
        return resp_models, False

    @Route(route='{project_name}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsProject)
    @cherrypy.tools.project_scope()
    @cherrypy.tools.resource_object(id_param="project_name", cls=Project)
    @cherrypy.tools.enforce_permission(permission_name="projects:delete")
    def delete(self, **_):
        """Delete a project
        ---
        delete:
            description: Delete a project
            tags:
                - iam
                - project
            responses:
                204:
                    description: Project deleted
        """
        cherrypy.response.status = 204

        project: Project = cherrypy.request.resource_object
        project.delete()
