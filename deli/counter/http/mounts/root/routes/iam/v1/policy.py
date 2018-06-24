import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.http.mounts.root.routes.iam.v1.validation_models.policy import ResponsePolicy, RequestSetPolicy
from deli.counter.http.router import SandwichSystemRouter, SandwichProjectRouter
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.iam_group.model import IAMSystemGroup
from deli.kubernetes.resources.v1alpha1.iam_policy.model import IAMPolicy
from deli.kubernetes.resources.v1alpha1.iam_role.model import IAMSystemRole, IAMProjectRole
from deli.kubernetes.resources.v1alpha1.iam_service_account.model import SystemServiceAccount, ProjectServiceAccount


class IAMSystemPolicyRouter(SandwichSystemRouter):
    def __init__(self):
        super().__init__('policy')

    @Route()
    @cherrypy.tools.model_out(cls=ResponsePolicy)
    @cherrypy.tools.enforce_permission(permission_name="policy:system:get")
    def get(self):
        """Get a system policy
        ---
        get:
            description: Get a system policy
            tags:
                - iam
                - policy
            responses:
                200:
                    description: The policy
        """
        return ResponsePolicy.from_database(IAMPolicy.get("system"))

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestSetPolicy)
    @cherrypy.tools.enforce_permission(permission_name="policy:system:set")
    def set(self):
        """Set a system policy
        ---
        post:
            description: Set a system policy
            tags:
                - iam
                - policy
            requestBody:
                description: The policy
            responses:
                200:
                    description: The policy
        """
        cherrypy.response.status = 204
        policy = IAMPolicy.get("system")
        bindings = []
        request: RequestSetPolicy = cherrypy.request.model

        if request.resource_version != policy.resource_version:
            raise cherrypy.HTTPError(400, 'The policy has a newer resource version than requested')

        has_one_admin = False

        for binding in request.bindings:
            role = IAMSystemRole.get(binding.role)
            if role is None:
                raise cherrypy.HTTPError(404, 'Unknown system role ' + binding.role)

            if role.name == 'admin':
                if len(binding.members) > 0:
                    has_one_admin = True

            for member in binding.members:
                kind, email = member.split(":")
                user, domain = email.split('@')

                if kind == 'group':
                    group = IAMSystemGroup.get(user)
                    if group is None:
                        raise cherrypy.HTTPError(404, 'Unknown Group ' + email)

                if kind == 'serviceAccount':
                    _, project, *__ = domain.split('.')
                    if project != 'system':
                        raise cherrypy.HTTPError(400, 'Can only add system service accounts to a system policy.')

                    sa = SystemServiceAccount.get(user)
                    if sa is None:
                        raise cherrypy.HTTPError(404, 'Unknown service account ' + email)

            bindings.append(binding.to_native())

        if has_one_admin is False:
            raise cherrypy.HTTPError(400, 'Must have an admin binding with at least one member')

        policy.bindings = bindings
        policy.save()


class IAMProjectPolicyRouter(SandwichProjectRouter):
    def __init__(self):
        super().__init__('policy')

    @Route()
    @cherrypy.tools.model_out(cls=ResponsePolicy)
    @cherrypy.tools.enforce_permission(permission_name="policy:project:get")
    def get(self):
        """Get a project policy
        ---
        get:
            description: Get a project policy
            tags:
                - iam
                - policy
            responses:
                200:
                    description: The policy
        """
        return ResponsePolicy.from_database(IAMPolicy.get(cherrypy.request.project.name))

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestSetPolicy)
    @cherrypy.tools.enforce_permission(permission_name="policy:project:set")
    def set(self):
        """Set a project policy
        ---
        post:
            description: Set a project policy
            tags:
                - iam
                - policy
            requestBody:
                description: The policy
            responses:
                200:
                    description: The policy
        """
        cherrypy.response.status = 204
        project: Project = cherrypy.request.project
        policy = IAMPolicy.get(project)
        bindings = []
        request: RequestSetPolicy = cherrypy.request.model

        if request.resource_version != policy.resource_version:
            raise cherrypy.HTTPError(400, 'The policy has a newer resource version than requested')

        has_one_owner = False

        for binding in request.bindings:
            role = IAMProjectRole.get(project, binding.role)
            if role is None:
                raise cherrypy.HTTPError(404, 'Unknown project role ' + binding.role)

            if role.name == "owner":
                if len(binding.members) > 0:
                    has_one_owner = True

            for member in binding.members:
                kind, email = member.split(":")
                user, domain = email.split('@')

                if kind == 'group':
                    group = IAMSystemGroup.get(user)
                    if group is None:
                        raise cherrypy.HTTPError(404, 'Unknown Group ' + email)

                if kind == 'serviceAccount':
                    _, sa_project_name, *__ = domain.split('.')

                    if sa_project_name == 'system':
                        sa = SystemServiceAccount.get(user)
                    else:
                        sa_project = Project.get(sa_project_name)
                        if sa_project is None:
                            raise cherrypy.HTTPError(404, 'Unknown service account ' + email)
                        sa = ProjectServiceAccount.get(sa_project, user)

                    if sa is None:
                        raise cherrypy.HTTPError(404, 'Unknown service account ' + email)

            bindings.append(binding.to_native())

        if has_one_owner is False:
            raise cherrypy.HTTPError(400, 'Must have a owner binding with at least one member')

        policy.bindings = bindings
        policy.save()
