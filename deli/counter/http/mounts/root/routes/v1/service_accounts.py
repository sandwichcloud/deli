import cherrypy

from deli.counter.http.mounts.root.routes.v1.validation_models.service_accounts import ResponseServiceAccount, \
    RequestCreateServiceAccount, ParamsServiceAccount, ParamsListServiceAccount, RequestUpdateServiceAccount
from deli.http.request_methods import RequestMethods
from deli.http.route import Route
from deli.http.router import Router
from deli.kubernetes.resources.const import SERVICE_ACCOUNT_LABEL
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.instance.model import Instance
from deli.kubernetes.resources.v1alpha1.role.model import ProjectRole
from deli.kubernetes.resources.v1alpha1.service_account.model import ServiceAccount


class ServiceAccountsRouter(Router):
    def __init__(self):
        super().__init__(uri_base='service-accounts')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_in(cls=RequestCreateServiceAccount)
    @cherrypy.tools.model_out(cls=ResponseServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:create")
    def create(self):
        request: RequestCreateServiceAccount = cherrypy.request.model
        project: Project = cherrypy.request.project

        service_account = ServiceAccount.get_by_name(project, request.name)
        if service_account is not None:
            raise cherrypy.HTTPError(400, 'An service account with the requested name already exists.')

        service_account = ServiceAccount()
        service_account.project = project
        service_account.name = request.name
        service_account.roles = [ProjectRole.get_by_name(project, 'default-service-account')]
        service_account.create()

        return ResponseServiceAccount.from_database(service_account)

    @Route(route='{service_account_id}')
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsServiceAccount)
    @cherrypy.tools.model_out(cls=ResponseServiceAccount)
    @cherrypy.tools.resource_object(id_param="service_account_id", cls=ServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:get")
    def get(self, **_):
        return ResponseServiceAccount.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsListServiceAccount)
    @cherrypy.tools.model_out_pagination(cls=ResponseServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:list")
    def list(self, limit, marker):
        return self.paginate(ServiceAccount, ResponseServiceAccount, limit, marker, project=cherrypy.request.project)

    @Route(route='{service_account_id}', methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsServiceAccount)
    @cherrypy.tools.model_in(cls=RequestUpdateServiceAccount)
    @cherrypy.tools.resource_object(id_param="service_account_id", cls=ServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:update")
    def update(self, **_):
        cherrypy.response.status = 204
        request: RequestUpdateServiceAccount = cherrypy.request.model
        project: Project = cherrypy.request.project
        service_account: ServiceAccount = cherrypy.request.resource_object

        if service_account.name == "default":
            raise cherrypy.HTTPError(409, 'Cannot update the default service account.')

        roles = []
        for role_id in request.roles:
            role = ProjectRole.get(project, role_id)
            if role is None:
                raise cherrypy.HTTPError(404, 'A project role with the requested id of %s does not exist.' % role_id)
            roles.append(role)

        service_account.roles = roles
        service_account.save()

    @Route(route='{service_account_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsServiceAccount)
    @cherrypy.tools.resource_object(id_param="service_account_id", cls=ServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:delete")
    def delete(self, **_):
        cherrypy.response.status = 204
        service_account: ServiceAccount = cherrypy.request.resource_object

        if service_account.name == "default":
            raise cherrypy.HTTPError(409, 'Cannot delete the default service account.')

        if service_account.state == ResourceState.ToDelete or service_account.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Service Account is already being deleting")

        if service_account.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Service Account has already been deleted")

        instances = Instance.list_all(label_selector=SERVICE_ACCOUNT_LABEL + "=" + str(service_account.id))
        if len(instances) > 0:
            raise cherrypy.HTTPError(409, 'Cannot delete a service account while it is in use by an instance')

        service_account.delete()
