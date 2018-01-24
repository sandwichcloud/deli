from typing import Optional

import cherrypy

from deli.counter.auth.policy import POLICIES
from deli.counter.http.mounts.root.routes.v1.auth.validation_models.role import RequestCreateRole, ResponseRole, \
    ParamsRole, ParamsListRoles, RequestRoleUpdate
from deli.http.request_methods import RequestMethods
from deli.http.route import Route
from deli.http.router import Router
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.role.model import GlobalRole, ProjectRole


class RoleHelper(object):

    def helper_create(self, project: Optional[Project]):
        request: RequestCreateRole = cherrypy.request.model

        if project is None:
            if GlobalRole.get_by_name(request.name) is not None:
                raise cherrypy.HTTPError(400, 'A global role with the requested name already exists.')
            role = GlobalRole()
        else:
            if ProjectRole.get_by_name(project, request.name) is not None:
                raise cherrypy.HTTPError(400, 'A project role with the requested name already exists.')
            role = ProjectRole()
            role.project = project

        policy_names = [p['name'] for p in POLICIES]

        for policy in request.policies:
            if policy not in policy_names:
                raise cherrypy.HTTPError(404, 'Unknown policy %s' % policy)

            if project is not None:
                i = policy_names.index(policy)
                if 'project' not in POLICIES[i].get('tags', []):
                    raise cherrypy.HTTPError(409, 'Cannot add non-project policy %s to project role' % policy)

        role.name = request.name
        role.policies = request.policies
        role.create()

        return ResponseRole.from_database(role)

    def helper_get(self):
        return ResponseRole.from_database(cherrypy.request.resource_object)

    def helper_list(self, project: Optional[Project], limit, marker):
        if project is None:
            return self.paginate(GlobalRole, ResponseRole, limit, marker)
        else:
            return self.paginate(ProjectRole, ResponseRole, limit, marker, project=project)

    def helper_update(self, project: Optional[Project]):
        cherrypy.response.status = 204
        request: RequestRoleUpdate = cherrypy.request.model
        role = cherrypy.request.resource_object

        if role.name in ['admin', 'default-member', 'default-service-account']:
            raise cherrypy.HTTPError(409, 'Cannot update the default roles')

        policy_names = [p['name'] for p in POLICIES]

        for policy in request.policies:
            if policy not in policy_names:
                raise cherrypy.HTTPError(404, 'Unknown policy %s' % policy)
            if project is not None:
                i = policy_names.index(policy)
                if 'project' not in POLICIES[i].get('tags', []):
                    raise cherrypy.HTTPError(409, 'Cannot add non-project policy %s to project role' % policy)

        role.policies = request.policies
        role.save()

    def helper_delete(self):
        cherrypy.response.status = 204
        role = cherrypy.request.resource_object

        if role.name in ['admin', 'default-member', 'default-service-account']:
            raise cherrypy.HTTPError(409, 'Cannot delete the default roles')

        role.delete()


class AuthGlobalRolesRouter(Router, RoleHelper):
    def __init__(self):
        super().__init__('global-roles')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateRole)
    @cherrypy.tools.model_out(cls=ResponseRole)
    @cherrypy.tools.enforce_policy(policy_name="roles:global:create")
    def create(self):
        return self.helper_create(None)

    @Route(route='{role_id}')
    @cherrypy.tools.model_params(cls=ParamsRole)
    @cherrypy.tools.model_out(cls=ResponseRole)
    @cherrypy.tools.resource_object(id_param="role_id", cls=GlobalRole)
    @cherrypy.tools.enforce_policy(policy_name="roles:global:get")
    def get(self, **_):
        return self.helper_get()

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListRoles)
    @cherrypy.tools.model_out_pagination(cls=ResponseRole)
    @cherrypy.tools.enforce_policy(policy_name="roles:global:list")
    def list(self, limit, marker):
        return self.helper_list(None, limit, marker)

    @Route(route='{role_id}', methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestRoleUpdate)
    @cherrypy.tools.resource_object(id_param="role_id", cls=GlobalRole)
    @cherrypy.tools.enforce_policy(policy_name="roles:global:update")
    def update(self, **_):
        return self.helper_update(None)

    @Route(route='{role_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsRole)
    @cherrypy.tools.resource_object(id_param="role_id", cls=GlobalRole)
    @cherrypy.tools.enforce_policy(policy_name="roles:global:delete")
    def delete(self, **_):
        return self.helper_delete()


class AuthProjectRolesRouter(Router, RoleHelper):
    def __init__(self):
        super().__init__('project-roles')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_in(cls=RequestCreateRole)
    @cherrypy.tools.model_out(cls=ResponseRole)
    @cherrypy.tools.enforce_policy(policy_name="roles:project:create")
    def create(self):
        return self.helper_create(cherrypy.request.project)

    @Route(route='{role_id}')
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsRole)
    @cherrypy.tools.model_out(cls=ResponseRole)
    @cherrypy.tools.resource_object(id_param="role_id", cls=ProjectRole)
    @cherrypy.tools.enforce_policy(policy_name="roles:project:get")
    def get(self, **_):
        return self.helper_get()

    @Route()
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsListRoles)
    @cherrypy.tools.model_out_pagination(cls=ResponseRole)
    @cherrypy.tools.enforce_policy(policy_name="roles:project:list")
    def list(self, limit, marker):
        return self.helper_list(cherrypy.request.project, limit, marker)

    @Route(route='{role_id}', methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_in(cls=RequestRoleUpdate)
    @cherrypy.tools.resource_object(id_param="role_id", cls=ProjectRole)
    @cherrypy.tools.enforce_policy(policy_name="roles:project:update")
    def update(self, **_):
        return self.helper_update(cherrypy.request.project)

    @Route(route='{role_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsRole)
    @cherrypy.tools.resource_object(id_param="role_id", cls=ProjectRole)
    @cherrypy.tools.enforce_policy(policy_name="roles:project:delete")
    def delete(self, **_):
        return self.helper_delete()
