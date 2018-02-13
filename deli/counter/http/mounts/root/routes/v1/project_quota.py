import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.http.mounts.root.routes.v1.validation_models.projects import ResponseProjectQuota, \
    RequestProjectModifyQuota
from deli.counter.http.router import SandwichRouter
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.project_quota.model import ProjectQuota


class ProjectQuotaRouter(SandwichRouter):
    def __init__(self):
        super().__init__(uri_base='project-quota')

    @Route(methods=[RequestMethods.GET])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_out(cls=ResponseProjectQuota)
    @cherrypy.tools.enforce_policy(policy_name="projects:quota:get")
    def get(self):
        project: Project = cherrypy.request.project
        quota = ProjectQuota.get(project, project.id)
        return ResponseProjectQuota.from_database(quota)

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_in(cls=RequestProjectModifyQuota)
    @cherrypy.tools.enforce_policy(policy_name="projects:quota:modify")
    def modify(self):
        cherrypy.response.status = 204
        request: RequestProjectModifyQuota = cherrypy.request.model
        project: Project = cherrypy.request.project
        quota: ProjectQuota = ProjectQuota.get(project, project.id)

        quota.vcpu = request.vcpu
        quota.ram = request.ram
        quota.disk = request.disk
        quota.save()
