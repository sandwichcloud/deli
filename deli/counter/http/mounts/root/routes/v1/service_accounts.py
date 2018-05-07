from typing import Optional

import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.auth.token import Token
from deli.counter.http.mounts.root.routes.v1.auth.validation_models.tokens import ResponseOAuthToken
from deli.counter.http.mounts.root.routes.v1.validation_models.service_accounts import ResponseServiceAccount, \
    RequestCreateServiceAccount, ParamsServiceAccount, ParamsListServiceAccount, RequestUpdateServiceAccount, \
    RequestCreateServiceAccountKey, ParamsServiceAccountKey
from deli.counter.http.router import SandwichRouter
from deli.kubernetes.resources.const import SERVICE_ACCOUNT_LABEL
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.instance.model import Instance
from deli.kubernetes.resources.v1alpha1.role.model import ProjectRole, GlobalRole
from deli.kubernetes.resources.v1alpha1.service_account.model import ProjectServiceAccount, GlobalServiceAccount


class ServiceAccountHelper(object):

    def helper_create(self, project: Optional[Project]):
        request: RequestCreateServiceAccount = cherrypy.request.model

        if project is None:
            service_account = GlobalServiceAccount.get_by_name(request.name)
            if service_account is not None:
                raise cherrypy.HTTPError(400, 'A global service account with the requested name already exists.')
        else:
            service_account = ProjectServiceAccount.get_by_name(project, request.name)
            if service_account is not None:
                raise cherrypy.HTTPError(400, 'A project service account with the requested name already exists.')
            service_account = ProjectServiceAccount()
            service_account.project = project
            service_account.roles = [ProjectRole.get_by_name(project, 'default-service-account')]

        service_account.name = request.name
        service_account.create()
        return ResponseServiceAccount.from_database(service_account)

    def helper_get(self):
        return ResponseServiceAccount.from_database(cherrypy.request.resource_object)

    def helper_list(self, project: Optional[Project], limit, marker):
        if project is None:
            return self.paginate(GlobalServiceAccount, ResponseServiceAccount, limit, marker)
        else:
            return self.paginate(ProjectServiceAccount, ResponseServiceAccount, limit, marker, project=project)

    def helper_update(self, project: Optional[Project]):
        cherrypy.response.status = 204
        request: RequestUpdateServiceAccount = cherrypy.request.model
        service_account = cherrypy.request.resource_object

        if project is not None and service_account.name == "default":
            raise cherrypy.HTTPError(409, 'Cannot update the default service account.')

        roles = []
        for role_id in request.roles:
            if project is None:
                role = GlobalRole.get(project, role_id)
                if role is None:
                    raise cherrypy.HTTPError(404, 'A global role with the requested id of %s does not exist.' % role_id)
            else:
                role = ProjectRole.get(project, role_id)
                if role is None:
                    raise cherrypy.HTTPError(404,
                                             'A project role with the requested id of %s does not exist.' % role_id)
            roles.append(role)

        service_account.roles = roles
        service_account.save()

    def helper_delete(self, project: Optional[Project]):
        cherrypy.response.status = 204
        service_account = cherrypy.request.resource_object

        if project is not None and service_account.name == "default":
            raise cherrypy.HTTPError(409, 'Cannot delete the default service account.')

        if service_account.state == ResourceState.ToDelete or service_account.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Service Account is already being deleting")

        if service_account.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Service Account has already been deleted")

        if project is not None:
            instances = Instance.list_all(label_selector=SERVICE_ACCOUNT_LABEL + "=" + str(service_account.id))
            if len(instances) > 0:
                raise cherrypy.HTTPError(409, 'Cannot delete a service account while it is in use by an instance')

        service_account.delete()

    def helper_create_key(self, project: Optional[Project]):
        request: RequestCreateServiceAccountKey = cherrypy.request.model
        service_account = cherrypy.request.resource_object

        if request.name in service_account.keys:
            raise cherrypy.HTTPError(400, 'Service account %s already has a key with the name of %s'
                                     % (service_account.name, request.name))

        service_account.keys = service_account.keys + [request.name]
        service_account.save()

        token = Token()
        token.driver_name = 'metadata'
        token.service_account_id = service_account.id
        token.service_account_key = request.name
        if project is not None:
            token.project_id = project.id

        response = ResponseOAuthToken()
        response.access_token = token.marshal(self.mount.fernet)
        response.expiry = None
        return response

    def helper_delete_key(self, name):
        cherrypy.response.status = 204
        service_account = cherrypy.request.resource_object
        keys = service_account.keys
        keys.remove(name)
        service_account.keys = keys
        service_account.save()


class GlobalServiceAccountsRouter(SandwichRouter, ServiceAccountHelper):
    def __init__(self):
        super().__init__(uri_base='global-service-accounts')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateServiceAccount)
    @cherrypy.tools.model_out(cls=ResponseServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:global:create")
    def create(self):
        return self.helper_create(None)

    @Route(route='{service_account_id}')
    @cherrypy.tools.model_params(cls=ParamsServiceAccount)
    @cherrypy.tools.model_out(cls=ResponseServiceAccount)
    @cherrypy.tools.resource_object(id_param="service_account_id", cls=GlobalServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:global:get")
    def get(self, **_):
        return self.helper_get()

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListServiceAccount)
    @cherrypy.tools.model_out_pagination(cls=ResponseServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:global:list")
    def list(self, limit, marker):
        return self.helper_list(None, limit, marker)

    @Route(route='{service_account_id}', methods=[RequestMethods.POST])
    @cherrypy.tools.model_params(cls=ParamsServiceAccount)
    @cherrypy.tools.model_in(cls=RequestUpdateServiceAccount)
    @cherrypy.tools.resource_object(id_param="service_account_id", cls=GlobalServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:global:update")
    def update(self, **_):
        self.helper_update(None)

    @Route(route='{service_account_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsServiceAccount)
    @cherrypy.tools.resource_object(id_param="service_account_id", cls=GlobalServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:global:delete")
    def delete(self, **_):
        self.helper_delete(None)

    @Route(route='{service_account_id}/keys', methods=[RequestMethods.POST])
    @cherrypy.tools.model_params(cls=ParamsServiceAccount)
    @cherrypy.tools.model_in(cls=RequestCreateServiceAccountKey)
    @cherrypy.tools.model_out(cls=ResponseOAuthToken)
    @cherrypy.tools.resource_object(id_param="service_account_id", cls=GlobalServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:global:key:create")
    def create_key(self, **_):
        return self.helper_create_key(None)

    @Route(route='{service_account_id}/keys/{name}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsServiceAccountKey)
    @cherrypy.tools.resource_object(id_param="service_account_id", cls=GlobalServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:global:key:delete")
    def delete_key(self, **kwargs):
        return self.helper_delete_key(name=kwargs['name'])


class ProjectServiceAccountsRouter(SandwichRouter, ServiceAccountHelper):
    def __init__(self):
        super().__init__(uri_base='project-service-accounts')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_in(cls=RequestCreateServiceAccount)
    @cherrypy.tools.model_out(cls=ResponseServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:project:create")
    def create(self):
        return self.helper_create(cherrypy.request.project)

    @Route(route='{service_account_id}')
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsServiceAccount)
    @cherrypy.tools.model_out(cls=ResponseServiceAccount)
    @cherrypy.tools.resource_object(id_param="service_account_id", cls=ProjectServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:project:get")
    def get(self, **_):
        return self.helper_get()

    @Route()
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsListServiceAccount)
    @cherrypy.tools.model_out_pagination(cls=ResponseServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:project:list")
    def list(self, limit, marker):
        return self.helper_list(cherrypy.request.project, limit, marker)

    @Route(route='{service_account_id}', methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsServiceAccount)
    @cherrypy.tools.model_in(cls=RequestUpdateServiceAccount)
    @cherrypy.tools.resource_object(id_param="service_account_id", cls=ProjectServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:project:update")
    def update(self, **_):
        self.helper_update(cherrypy.request.project)

    @Route(route='{service_account_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsServiceAccount)
    @cherrypy.tools.resource_object(id_param="service_account_id", cls=ProjectServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:project:delete")
    def delete(self, **_):
        self.helper_delete(cherrypy.request.project)

    @Route(route='{service_account_id}/keys', methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsServiceAccount)
    @cherrypy.tools.model_in(cls=RequestCreateServiceAccountKey)
    @cherrypy.tools.model_out(cls=ResponseOAuthToken)
    @cherrypy.tools.resource_object(id_param="service_account_id", cls=ProjectServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:project:key:create")
    def create_key(self, **_):
        return self.helper_create_key(cherrypy.request.project)

    @Route(route='{service_account_id}/keys/{name}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsServiceAccountKey)
    @cherrypy.tools.resource_object(id_param="service_account_id", cls=ProjectServiceAccount)
    @cherrypy.tools.enforce_policy(policy_name="service_accounts:project:key:delete")
    def delete_key(self, **kwargs):
        return self.helper_delete_key(name=kwargs['name'])
