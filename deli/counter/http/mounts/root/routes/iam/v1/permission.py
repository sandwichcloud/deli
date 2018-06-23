import uuid

import cherrypy
from ingredients_http.route import Route

from deli.counter.auth.permission import SYSTEM_PERMISSIONS, PROJECT_PERMISSIONS
from deli.counter.http.mounts.root.routes.iam.v1.validation_models.permission import ParamsPermission, \
    ResponsePermission, \
    ParamsListPermission
from deli.counter.http.router import SandwichProjectRouter, SandwichSystemRouter


class IAMSystemPermissionRouter(SandwichSystemRouter):
    def __init__(self):
        super().__init__('permissions')

    @Route(route='{permission_name}')
    @cherrypy.tools.model_params(cls=ParamsPermission)
    @cherrypy.tools.model_out(cls=ResponsePermission)
    def get(self, permission_name):
        """Get a system permission
        ---
        get:
            description: Get a system permission
            tags:
                - iam
                - permission
            responses:
                200:
                    description: The permission
        """
        permission = None

        for p in SYSTEM_PERMISSIONS:
            if p['name'] == permission_name:
                permission = p
                break

        if permission is None:
            raise cherrypy.HTTPError(404, "The resource could not be found.")

        return ResponsePermission(permission)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListPermission)
    @cherrypy.tools.model_out_pagination(cls=ResponsePermission)
    def list(self, limit: int, marker: uuid.UUID):
        """List system permissions
        ---
        get:
            description: List system permissions
            tags:
                - iam
                - permission
            responses:
                200:
                    description: List of system permissions
        """
        permissions = []

        for p in SYSTEM_PERMISSIONS:
            permissions.append(ResponsePermission(p))

        return permissions, False


class IAMProjectPermissionRouter(SandwichProjectRouter):
    def __init__(self):
        super().__init__('permissions')

    @Route(route='{permission_name}')
    @cherrypy.tools.model_params(cls=ParamsPermission)
    @cherrypy.tools.model_out(cls=ResponsePermission)
    def get(self, permission_name):
        """Get a project permission
        ---
        get:
            description: Get a project permission
            tags:
                - iam
                - permission
            responses:
                200:
                    description: The permission
        """

        permission = None

        for p in PROJECT_PERMISSIONS:
            if p['name'] == permission_name:
                permission = p
                break

        if permission is None:
            raise cherrypy.HTTPError(404, "The resource could not be found.")

        return ResponsePermission(permission)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListPermission)
    @cherrypy.tools.model_out_pagination(cls=ResponsePermission)
    def list(self, limit: int, marker: uuid.UUID):
        """List project permissions
        ---
        get:
            description: List project permissions
            tags:
                - iam
                - permission
            responses:
                200:
                    description: List of project permissions
        """
        permissions = []

        for p in PROJECT_PERMISSIONS:
            permissions.append(ResponsePermission(p))

        return permissions, False
