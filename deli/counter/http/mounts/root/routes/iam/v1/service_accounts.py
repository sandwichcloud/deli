from typing import Optional

import arrow
import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.auth.token import Token
from deli.counter.http.mounts.root.routes.auth.v1.validation_models.oauth import ResponseOAuthToken
from deli.counter.http.mounts.root.routes.iam.v1.validation_models.service_accounts import ResponseServiceAccount, \
    RequestCreateServiceAccount, ParamsServiceAccount, ParamsListServiceAccount, RequestCreateServiceAccountKey, \
    ParamsServiceAccountKey
from deli.counter.http.router import SandwichProjectRouter, SandwichSystemRouter
from deli.kubernetes.resources.const import SERVICE_ACCOUNT_LABEL
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.iam_service_account.model import ProjectServiceAccount, SystemServiceAccount
from deli.kubernetes.resources.v1alpha1.instance.model import Instance


class ServiceAccountHelper(object):

    def helper_create(self, project: Optional[Project]):
        request: RequestCreateServiceAccount = cherrypy.request.model

        if project is None:
            service_account = SystemServiceAccount.get(request.name)
            if service_account is not None:
                raise cherrypy.HTTPError(400, 'A system service account with the requested name already exists.')
            service_account = SystemServiceAccount()
        else:
            service_account = ProjectServiceAccount.get(project, request.name)
            if service_account is not None:
                raise cherrypy.HTTPError(400, 'A project service account with the requested name already exists.')
            service_account = ProjectServiceAccount()
            service_account.project = project
            service_account.roles = []

        service_account.name = request.name
        service_account.create()
        return ResponseServiceAccount.from_database(service_account)

    def helper_get(self):
        return ResponseServiceAccount.from_database(cherrypy.request.resource_object)

    def helper_list(self, project: Optional[Project], limit, marker):
        if project is None:
            return self.paginate(SystemServiceAccount, ResponseServiceAccount, limit, marker)
        else:
            return self.paginate(ProjectServiceAccount, ResponseServiceAccount, limit, marker, project=project)

    def helper_delete(self, project: Optional[Project]):
        cherrypy.response.status = 204
        service_account = cherrypy.request.resource_object

        if project is not None and service_account.name == "default":
            raise cherrypy.HTTPError(409, 'Cannot delete the default service account.')

        if project is None and service_account.name == "admin":
            raise cherrypy.HTTPError(409, 'Cannot delete the admin service account.')

        if service_account.state == ResourceState.ToDelete or service_account.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Service Account is already being deleting")

        if service_account.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Service Account has already been deleted")

        if project is not None:
            instances = Instance.list(project, label_selector=SERVICE_ACCOUNT_LABEL + "=" + str(service_account.name))
            if len(instances) > 0:
                raise cherrypy.HTTPError(409, 'Cannot delete a service account while it is in use by an instance')

        service_account.delete()

    def helper_create_key(self, project: Optional[Project]):
        request: RequestCreateServiceAccountKey = cherrypy.request.model
        service_account = cherrypy.request.resource_object

        if project is None and service_account.name == "admin":
            raise cherrypy.HTTPError(409, 'Cannot create keys for the admin service account.')

        if request.name in service_account.keys:
            raise cherrypy.HTTPError(400, 'Service account %s already has a key with the name of %s'
                                     % (service_account.name, request.name))

        if service_account.state != ResourceState.Created:
            raise cherrypy.HTTPError(400,
                                     'Service Account member is not in the following state: '
                                     + ResourceState.Created.value)

        keys = service_account.keys
        keys[request.name] = arrow.now('UTC').shift(years=+10)
        service_account.keys = keys
        service_account.save()

        token = Token()
        token.email = service_account.email
        token.metadata['key'] = request.name

        response = ResponseOAuthToken()
        response.access_token = token.marshal(self.mount.fernet)
        response.expiry = keys[request.name]
        return response

    def helper_delete_key(self, name, project: Optional[Project]):
        cherrypy.response.status = 204
        service_account = cherrypy.request.resource_object

        if service_account.state != ResourceState.Created:
            raise cherrypy.HTTPError(400,
                                     'Service Account member is not in the following state: '
                                     + ResourceState.Created.value)

        if project is None and service_account.name == "admin":
            raise cherrypy.HTTPError(409, 'Cannot delete keys for the admin service account.')

        keys = service_account.keys
        del keys[name]
        service_account.keys = keys
        service_account.save()


class SystemServiceAccountsRouter(SandwichSystemRouter, ServiceAccountHelper):
    def __init__(self):
        super().__init__(uri_base='service-accounts')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateServiceAccount)
    @cherrypy.tools.model_out(cls=ResponseServiceAccount)
    @cherrypy.tools.enforce_permission(permission_name="service_accounts:system:create")
    def create(self):
        """Create a system service account
        ---
        post:
            description: Create a system service account
            tags:
                - iam
                - service-account
            requestBody:
                description: Service Account to create
            responses:
                200:
                    description: The created service account
        """
        return self.helper_create(None)

    @Route(route='{service_account_name}')
    @cherrypy.tools.model_params(cls=ParamsServiceAccount)
    @cherrypy.tools.model_out(cls=ResponseServiceAccount)
    @cherrypy.tools.resource_object(id_param="service_account_name", cls=SystemServiceAccount)
    @cherrypy.tools.enforce_permission(permission_name="service_accounts:system:get")
    def get(self, **_):
        """Get a system service account
        ---
        get:
            description: Get a system service account
            tags:
                - iam
                - service-account
            responses:
                200:
                    description: The service account
        """
        return self.helper_get()

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListServiceAccount)
    @cherrypy.tools.model_out_pagination(cls=ResponseServiceAccount)
    @cherrypy.tools.enforce_permission(permission_name="service_accounts:system:list")
    def list(self, limit, marker):
        """List system service accounts
        ---
        get:
            description: List system service accounts
            tags:
                - iam
                - service-account
            responses:
                200:
                    description: List of service accounts
        """
        return self.helper_list(None, limit, marker)

    @Route(route='{service_account_name}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsServiceAccount)
    @cherrypy.tools.resource_object(id_param="service_account_name", cls=SystemServiceAccount)
    @cherrypy.tools.enforce_permission(permission_name="service_accounts:system:delete")
    def delete(self, **_):
        """Delete a system service account
        ---
        delete:
            description: Delete a system service account
            tags:
                - iam
                - service-account
            responses:
                204:
                    description: Service Account deleted
        """
        self.helper_delete(None)

    @Route(route='{service_account_name}/keys', methods=[RequestMethods.POST])
    @cherrypy.tools.model_params(cls=ParamsServiceAccount)
    @cherrypy.tools.model_in(cls=RequestCreateServiceAccountKey)
    @cherrypy.tools.model_out(cls=ResponseOAuthToken)
    @cherrypy.tools.resource_object(id_param="service_account_name", cls=SystemServiceAccount)
    @cherrypy.tools.enforce_permission(permission_name="service_accounts:system:key:create")
    def create_key(self, **_):
        """Create a system service account key
        ---
        post:
            description: Create a system service account key
            tags:
                - iam
                - service-account
            requestBody:
                description: Service Account to create
            responses:
                200:
                    description: The created key
        """
        return self.helper_create_key(None)

    @Route(route='{service_account_name}/keys/{name}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsServiceAccountKey)
    @cherrypy.tools.resource_object(id_param="service_account_name", cls=SystemServiceAccount)
    @cherrypy.tools.enforce_permission(permission_name="service_accounts:system:key:delete")
    def delete_key(self, **kwargs):
        """Delete a system service account key
        ---
        delete:
            description: Delete a system service account key
            tags:
                - iam
                - service-account
            responses:
                204:
                    description: Service Account key deleted
        """
        return self.helper_delete_key(name=kwargs['name'], project=None)


class ProjectServiceAccountsRouter(SandwichProjectRouter, ServiceAccountHelper):
    def __init__(self):
        super().__init__(uri_base='service-accounts')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateServiceAccount)
    @cherrypy.tools.model_out(cls=ResponseServiceAccount)
    @cherrypy.tools.enforce_permission(permission_name="service_accounts:project:create")
    def create(self):
        """Create a project service account
        ---
        post:
            description: Create a project service account
            tags:
                - iam
                - service-account
            requestBody:
                description: Service Account to create
            responses:
                200:
                    description: The created service account
        """
        return self.helper_create(cherrypy.request.project)

    @Route(route='{service_account_name}')
    @cherrypy.tools.model_params(cls=ParamsServiceAccount)
    @cherrypy.tools.model_out(cls=ResponseServiceAccount)
    @cherrypy.tools.resource_object(id_param="service_account_name", cls=ProjectServiceAccount)
    @cherrypy.tools.enforce_permission(permission_name="service_accounts:project:get")
    def get(self, **_):
        """Get a project service account
        ---
        get:
            description: Get a project service account
            tags:
                - iam
                - service-account
            responses:
                200:
                    description: The service account
        """
        return self.helper_get()

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListServiceAccount)
    @cherrypy.tools.model_out_pagination(cls=ResponseServiceAccount)
    @cherrypy.tools.enforce_permission(permission_name="service_accounts:project:list")
    def list(self, limit, marker):
        """List project service accounts
        ---
        get:
            description: List project service accounts
            tags:
                - iam
                - service-account
            responses:
                200:
                    description: List of service accounts
        """
        return self.helper_list(cherrypy.request.project, limit, marker)

    @Route(route='{service_account_name}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsServiceAccount)
    @cherrypy.tools.resource_object(id_param="service_account_name", cls=ProjectServiceAccount)
    @cherrypy.tools.enforce_permission(permission_name="service_accounts:project:delete")
    def delete(self, **_):
        """Delete a project service account
        ---
        delete:
            description: Delete a project service account
            tags:
                - iam
                - service-account
            responses:
                204:
                    description: Service Account deleted
        """
        self.helper_delete(cherrypy.request.project)

    @Route(route='{service_account_name}/keys', methods=[RequestMethods.POST])
    @cherrypy.tools.model_params(cls=ParamsServiceAccount)
    @cherrypy.tools.model_in(cls=RequestCreateServiceAccountKey)
    @cherrypy.tools.model_out(cls=ResponseOAuthToken)
    @cherrypy.tools.resource_object(id_param="service_account_name", cls=ProjectServiceAccount)
    @cherrypy.tools.enforce_permission(permission_name="service_accounts:project:key:create")
    def create_key(self, **_):
        """Create a project service account key
        ---
        post:
            description: Create a project service account key
            tags:
                - iam
                - service-account
            requestBody:
                description: Service Account to create
            responses:
                200:
                    description: The created key
        """
        return self.helper_create_key(cherrypy.request.project)

    @Route(route='{service_account_name}/keys/{name}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsServiceAccountKey)
    @cherrypy.tools.resource_object(id_param="service_account_name", cls=ProjectServiceAccount)
    @cherrypy.tools.enforce_permission(permission_name="service_accounts:project:key:delete")
    def delete_key(self, **kwargs):
        """Delete a project service account key
        ---
        delete:
            description: Delete a project service account key
            tags:
                - iam
                - service-account
            responses:
                204:
                    description: Service Account key deleted
        """
        return self.helper_delete_key(name=kwargs['name'], project=cherrypy.request.project)
