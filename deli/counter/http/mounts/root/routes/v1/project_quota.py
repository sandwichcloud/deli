import cherrypy

from deli.counter.http.mounts.root.routes.v1.validation_models.projects import ResponseProjectQuota, \
    RequestProjectModifyQuota
from deli.http.request_methods import RequestMethods
from deli.http.route import Route
from deli.http.router import Router
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.project_quota.model import ProjectQuota


class ProjectQuotaRouter(Router):
    def __init__(self):
        super().__init__(uri_base='project-quota')

    @Route(methods=[RequestMethods.GET])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_out(cls=ResponseProjectQuota)
    @cherrypy.tools.enforce_policy(policy_name="projects:quota:get")
    def get(self):
        project: Project = cherrypy.request.project
        return ResponseProjectQuota.from_database(project)

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_in(cls=RequestProjectModifyQuota)
    @cherrypy.tools.enforce_policy(policy_name="projects:quota:modify")
    def modify(self):
        cherrypy.response.status = 204
        request: RequestProjectModifyQuota = cherrypy.request.model
        project: Project = cherrypy.request.project
        quota: ProjectQuota = ProjectQuota.list(project)[0]

        quota.vcpu = request.vcpu
        quota.ram = request.ram
        quota.disk = request.disk
        quota.save()
