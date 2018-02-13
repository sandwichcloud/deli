import uuid

import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from kubernetes.client.rest import ApiException

from deli.counter.http.mounts.root.routes.v1.validation_models.projects import ResponseProject, RequestCreateProject, \
    ParamsProject, ParamsListProject
from deli.counter.http.router import SandwichRouter
from deli.kubernetes.resources.const import MEMBER_LABEL
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.project_quota.model import ProjectQuota
from deli.kubernetes.resources.v1alpha1.role.model import ProjectRole
from deli.kubernetes.resources.v1alpha1.service_account.model import ServiceAccount


class ProjectRouter(SandwichRouter):
    def __init__(self):
        super().__init__(uri_base='projects')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateProject)
    @cherrypy.tools.model_out(cls=ResponseProject)
    @cherrypy.tools.enforce_policy(policy_name="projects:create")
    def create(self):
        request: RequestCreateProject = cherrypy.request.model

        project = Project.get_by_name(request.name)
        if project is not None:
            raise cherrypy.HTTPError(409, 'A project with the requested name already exists.')

        project = Project()
        project.name = request.name

        try:
            project.create()
        except ApiException as e:
            if e.status == 409:
                raise cherrypy.HTTPError(409, 'Cannot create a project with the requested name, it is reserved.')
            raise

        ProjectRole.create_default_roles(project)
        ServiceAccount.create_default_service_account(project)
        quota = ProjectQuota()
        # Set the quota id to the project id so we know how to get it back
        quota._raw['metadata']['name'] = str(project.id)
        quota.project = project
        quota.create()

        return ResponseProject.from_database(project)

    @Route(route='{project_id}')
    @cherrypy.tools.model_params(cls=ParamsProject)
    @cherrypy.tools.model_out(cls=ResponseProject)
    @cherrypy.tools.resource_object(id_param="project_id", cls=Project)
    @cherrypy.tools.enforce_policy(policy_name="projects:get")
    def get(self, **_):
        project: Project = cherrypy.request.resource_object

        if project.is_member(cherrypy.request.user['name'], cherrypy.request.user['driver']) is False:
            self.mount.enforce_policy("projects:get:all")

        return ResponseProject.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListProject)
    @cherrypy.tools.model_out_pagination(cls=ResponseProject)
    @cherrypy.tools.enforce_policy(policy_name="projects:list")
    def list(self, all: bool, limit: int, marker: uuid.UUID):
        kwargs = {
            "label_selector": []
        }

        if all is False:
            kwargs['label_selector'].append(
                cherrypy.request.user['driver'] + "." + MEMBER_LABEL + "/" + cherrypy.request.user['name'])
        else:
            self.mount.enforce_policy("projects:list:all")

        kwargs['label_selector'] = ",".join(kwargs['label_selector'])

        return self.paginate(Project, ResponseProject, limit, marker, **kwargs)

    @Route(route='{project_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsProject)
    @cherrypy.tools.resource_object(id_param="project_id", cls=Project)
    @cherrypy.tools.enforce_policy(policy_name="projects:delete")
    def delete(self, **_):
        cherrypy.response.status = 204

        project: Project = cherrypy.request.resource_object
        project.delete()
