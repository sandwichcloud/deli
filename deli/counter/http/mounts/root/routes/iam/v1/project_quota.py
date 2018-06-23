import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.http.mounts.root.routes.iam.v1.validation_models.projects import ResponseProjectQuota, \
    RequestProjectModifyQuota
from deli.counter.http.router import SandwichProjectRouter
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.project_quota.model import ProjectQuota


class ProjectQuotaRouter(SandwichProjectRouter):
    def __init__(self):
        super().__init__(uri_base='quota')

    @Route(methods=[RequestMethods.GET])
    @cherrypy.tools.model_out(cls=ResponseProjectQuota)
    @cherrypy.tools.enforce_permission(permission_name="projects:quota:get")
    def get(self):
        """Get a project's quota
        ---
        get:
            description: Get a project's quota
            tags:
                - iam
                - project
            responses:
                200:
                    description: The project's quota
        """
        project: Project = cherrypy.request.project
        quota = ProjectQuota.get(project.name)
        return ResponseProjectQuota.from_database(quota)

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestProjectModifyQuota)
    @cherrypy.tools.enforce_permission(permission_name="projects:quota:modify")
    def modify(self):
        """Modify a project's quota
        ---
        post:
            description: Modify a project's quota
            tags:
                - iam
                - project
            requestBody:
                description: Quota options
            responses:
                204:
                    description: Quota set
        """
        cherrypy.response.status = 204
        request: RequestProjectModifyQuota = cherrypy.request.model
        project: Project = cherrypy.request.project
        quota: ProjectQuota = ProjectQuota.get(project.name)

        quota.vcpu = request.vcpu
        quota.ram = request.ram
        quota.disk = request.disk
        quota.save()
