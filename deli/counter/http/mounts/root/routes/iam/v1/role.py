from typing import Optional

import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.auth.permission import PROJECT_PERMISSIONS, SYSTEM_PERMISSIONS
from deli.counter.http.mounts.root.routes.iam.v1.validation_models.role import RequestCreateRole, ResponseRole, \
    RequestRoleUpdate, ParamsRole, ParamsListRoles
from deli.counter.http.router import SandwichProjectRouter, SandwichSystemRouter
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.iam_role.model import IAMSystemRole, IAMProjectRole


class RoleHelper(object):

    def helper_create(self, project: Optional[Project]):
        request: RequestCreateRole = cherrypy.request.model

        if project is None:
            if IAMSystemRole.get(request.name) is not None:
                raise cherrypy.HTTPError(400, 'A system role with the requested name already exists.')
            role = IAMSystemRole()
        else:
            if IAMProjectRole.get(project, request.name) is not None:
                raise cherrypy.HTTPError(400, 'A project role with the requested name already exists.')
            role = IAMProjectRole()
            role.project = project

        if project is not None:
            permission_names = [p['name'] for p in PROJECT_PERMISSIONS]
        else:
            permission_names = [p['name'] for p in SYSTEM_PERMISSIONS]

        for permission in request.permissions:
            if permission not in permission_names:
                raise cherrypy.HTTPError(404, 'Unknown permission %s' % permission)

        role.name = request.name
        role.permissions = request.permissions
        role.create()

        return ResponseRole.from_database(role)

    def helper_get(self):
        return ResponseRole.from_database(cherrypy.request.resource_object)

    def helper_list(self, project: Optional[Project], limit, marker):
        if project is None:
            return self.paginate(IAMSystemRole, ResponseRole, limit, marker)
        else:
            return self.paginate(IAMProjectRole, ResponseRole, limit, marker, project=project)

    def helper_update(self, project: Optional[Project]):
        cherrypy.response.status = 204
        request: RequestRoleUpdate = cherrypy.request.model
        role = cherrypy.request.resource_object

        if role.name in ['admin', 'viewer', 'editor', 'owner']:
            raise cherrypy.HTTPError(409, 'Cannot update the default roles')

        if role.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Role is not in the following state: ' + ResourceState.Created.value)

        if project is not None:
            permission_names = [p['name'] for p in PROJECT_PERMISSIONS]
        else:
            permission_names = [p['name'] for p in SYSTEM_PERMISSIONS]

        for permission in request.permissions:
            if permission not in permission_names:
                raise cherrypy.HTTPError(404, 'Unknown permission %s' % permission)

        role.permissions = request.permissions
        role.save()

    def helper_delete(self):
        cherrypy.response.status = 204
        role = cherrypy.request.resource_object

        if role.name in ['admin', 'viewer', 'editor', 'owner']:
            raise cherrypy.HTTPError(409, 'Cannot delete the default roles')

        if role.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Role is not in the following state: ' + ResourceState.Created.value)

        role.delete()


class IAMSystemRolesRouter(SandwichSystemRouter, RoleHelper):
    def __init__(self):
        super().__init__('roles')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateRole)
    @cherrypy.tools.model_out(cls=ResponseRole)
    @cherrypy.tools.enforce_permission(permission_name="roles:system:create")
    def create(self):
        """Create a system role
        ---
        post:
            description: Create a system role
            tags:
                - iam
                - role
            requestBody:
                description: Role to create
            responses:
                200:
                    description: The created role
        """
        return self.helper_create(None)

    @Route(route='{role_name}')
    @cherrypy.tools.model_params(cls=ParamsRole)
    @cherrypy.tools.model_out(cls=ResponseRole)
    @cherrypy.tools.resource_object(id_param="role_name", cls=IAMSystemRole)
    @cherrypy.tools.enforce_permission(permission_name="roles:system:get")
    def get(self, **_):
        """Get a system role
        ---
        get:
            description: Get a system role
            tags:
                - iam
                - role
            responses:
                200:
                    description: The role
        """
        return self.helper_get()

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListRoles)
    @cherrypy.tools.model_out_pagination(cls=ResponseRole)
    @cherrypy.tools.enforce_permission(permission_name="roles:system:list")
    def list(self, limit, marker):
        """List system roles
        ---
        get:
            description: List system roles
            tags:
                - iam
                - role
            responses:
                200:
                    description: List of system roles
        """
        return self.helper_list(None, limit, marker)

    @Route(route='{role_name}', methods=[RequestMethods.POST])
    @cherrypy.tools.model_params(cls=ParamsRole)
    @cherrypy.tools.model_in(cls=RequestRoleUpdate)
    @cherrypy.tools.resource_object(id_param="role_name", cls=IAMSystemRole)
    @cherrypy.tools.enforce_permission(permission_name="roles:system:update")
    def update(self, **_):
        """Update a system role
        ---
        post:
            description: Update a system role
            tags:
                - iam
                - role
            requestBody:
                description: Role options
            responses:
                204:
                    description: Role updated
        """
        return self.helper_update(None)

    @Route(route='{role_name}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsRole)
    @cherrypy.tools.resource_object(id_param="role_name", cls=IAMSystemRole)
    @cherrypy.tools.enforce_permission(permission_name="roles:system:delete")
    def delete(self, **_):
        """Delete a system role
        ---
        delete:
            description: Delete a system role
            tags:
                - iam
                - role
            responses:
                204:
                    description: Role deleted
        """
        return self.helper_delete()


class IAMProjectRolesRouter(SandwichProjectRouter, RoleHelper):
    def __init__(self):
        super().__init__('roles')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateRole)
    @cherrypy.tools.model_out(cls=ResponseRole)
    @cherrypy.tools.enforce_permission(permission_name="roles:project:create")
    def create(self):
        """Create a project role
        ---
        post:
            description: Create a project role
            tags:
                - iam
                - role
            requestBody:
                description: Role to create
            responses:
                200:
                    description: The created role
        """
        return self.helper_create(cherrypy.request.project)

    @Route(route='{role_name}')
    @cherrypy.tools.model_params(cls=ParamsRole)
    @cherrypy.tools.model_out(cls=ResponseRole)
    @cherrypy.tools.resource_object(id_param="role_name", cls=IAMProjectRole)
    @cherrypy.tools.enforce_permission(permission_name="roles:project:get")
    def get(self, **_):
        """Get a project role
        ---
        get:
            description: Get a project role
            tags:
                - iam
                - role
            responses:
                200:
                    description: The role
        """
        return self.helper_get()

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListRoles)
    @cherrypy.tools.model_out_pagination(cls=ResponseRole)
    @cherrypy.tools.enforce_permission(permission_name="roles:project:list")
    def list(self, limit, marker):
        """List project roles
        ---
        get:
            description: List project roles
            tags:
                - iam
                - role
            responses:
                200:
                    description: List of project roles
        """
        return self.helper_list(cherrypy.request.project, limit, marker)

    @Route(route='{role_name}', methods=[RequestMethods.POST])
    @cherrypy.tools.model_params(cls=ParamsRole)
    @cherrypy.tools.model_in(cls=RequestRoleUpdate)
    @cherrypy.tools.resource_object(id_param="role_name", cls=IAMProjectRole)
    @cherrypy.tools.enforce_permission(permission_name="roles:project:update")
    def update(self, **_):
        """Update a project role
        ---
        post:
            description: Update a project role
            tags:
                - iam
                - role
            requestBody:
                description: Role options
            responses:
                204:
                    description: Role updated
        """
        return self.helper_update(cherrypy.request.project)

    @Route(route='{role_name}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsRole)
    @cherrypy.tools.resource_object(id_param="role_name", cls=IAMProjectRole)
    @cherrypy.tools.enforce_permission(permission_name="roles:project:delete")
    def delete(self, **_):
        """Delete a project role
        ---
        delete:
            description: Delete a project role
            tags:
                - iam
                - role
            responses:
                204:
                    description: Role deleted
        """
        return self.helper_delete()
