import uuid

import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.http.mounts.root.routes.v1.validation_models.projects import ResponseProjectMember, \
    RequestProjectAddMember, ParamsProjectMember, ParamsListProjectMember, RequestProjectUpdateMember
from deli.counter.http.router import SandwichRouter
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.project_member.model import ProjectMember
from deli.kubernetes.resources.v1alpha1.role.model import ProjectRole


class ProjectMemberRouter(SandwichRouter):
    def __init__(self):
        super().__init__(uri_base='project-members')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_in(cls=RequestProjectAddMember)
    @cherrypy.tools.model_out(cls=ResponseProjectMember)
    @cherrypy.tools.enforce_policy(policy_name="projects:members:add")
    def create(self):
        request: RequestProjectAddMember = cherrypy.request.model
        project: Project = cherrypy.request.project

        if project.is_member(request.username, request.driver):
            raise cherrypy.HTTPError(400, 'The requested user is already a member of the project.')

        default_role = ProjectRole.get_by_name(project, "default-member")

        member = ProjectMember()
        member.project = project
        member.username = request.username
        member.driver = request.driver
        member.roles = [default_role]
        member.create()

        project.add_member(member)
        project.save()

        return ResponseProjectMember.from_database(member)

    @Route(route='{member_id}')
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsProjectMember)
    @cherrypy.tools.model_out(cls=ResponseProjectMember)
    @cherrypy.tools.resource_object(id_param="member_id", cls=ProjectMember)
    @cherrypy.tools.enforce_policy(policy_name="projects:members:get")
    def get(self, **_):
        return ResponseProjectMember.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsListProjectMember)
    @cherrypy.tools.model_out_pagination(cls=ResponseProjectMember)
    @cherrypy.tools.enforce_policy(policy_name="projects:members:list")
    def list(self, limit: int, marker: uuid.UUID):
        return self.paginate(ProjectMember, ResponseProjectMember, limit, marker, project=cherrypy.request.project)

    @Route(route='{member_id}', methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsProjectMember)
    @cherrypy.tools.model_in(cls=RequestProjectUpdateMember)
    @cherrypy.tools.resource_object(id_param="member_id", cls=ProjectMember)
    @cherrypy.tools.enforce_policy(policy_name="projects:members:update")
    def update(self, **_):
        cherrypy.response.status = 204
        request: RequestProjectUpdateMember = cherrypy.request.model
        project: Project = cherrypy.request.project
        member: ProjectMember = cherrypy.request.resource_object

        roles = []

        for role_id in request.roles:
            role: ProjectRole = ProjectRole.get(project, str(role_id))
            if role is None:
                raise cherrypy.HTTPError(404,
                                         'A project role with the requested id of %s does not exist.' % role_id)
            roles.append(role)

        member.roles = roles
        member.save()

    @Route(route='{member_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsProjectMember)
    @cherrypy.tools.resource_object(id_param="member_id", cls=ProjectMember)
    @cherrypy.tools.enforce_policy(policy_name="projects:members:remove")
    def delete(self, **_):
        cherrypy.response.status = 204
        project: Project = cherrypy.request.project
        member: ProjectMember = cherrypy.request.resource_object

        project.remove_member(member)
        project.save()

        member.delete()
