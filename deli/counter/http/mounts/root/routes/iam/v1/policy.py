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
    @cherrypy.tools.model_out(cls=ResponsePolicy)
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
        policy = IAMPolicy.get("system")
        bindings = []
        request: RequestSetPolicy = cherrypy.request.model

        if request.resource_version != policy.resource_version:
            raise cherrypy.HTTPError(400, 'The policy has a newer reosurce version than requested')

        for binding in request.bindings:
            role = IAMSystemRole.get(binding.role)
            if role is None:
                raise cherrypy.HTTPError(404, 'Unknown system role ' + binding.role)
            for member in binding.members:
                if member.contains(':') is False:
                    raise cherrypy.HTTPError(400, 'Member must be in the following format: '
                                                  '{user/serviceAccount/group}:{email}')

                kind, email, *junk = member.split(":")

                if len(junk) > 0:
                    raise cherrypy.HTTPError(400, 'Member must be in the following format: '
                                                  '{user/serviceAccount/group}:{email}')

                username, domain, *_ = email.split("@")

                if kind not in ['user', 'serviceAccount', 'group']:
                    raise cherrypy.HTTPError(400, 'Member must be in the following format: '
                                                  '{user/serviceAccount/group}:{email}')

                if kind == 'serviceAccount':
                    if domain != 'service-account.system.sandwich.local':
                        raise cherrypy.HTTPError(400, 'Can only add system service accounts to a system policy')

                    sa = SystemServiceAccount.get(username)
                    if sa is None:
                        raise cherrypy.HTTPError(404, 'Unknown System Service Account ' + email)

                if kind == 'group':
                    if domain != 'group.system.sandwich.local':
                        raise cherrypy.HTTPError(400, 'Invalid email for group ' + email)
                    group = IAMSystemGroup.get(username)
                    if group is None:
                        raise cherrypy.HTTPError(404, 'Unknown Group ' + username)

                if kind == 'user':
                    if domain.endswith('sandwich.local'):
                        raise cherrypy.HTTPError(400, 'Cannot add ' + email + " has a user")

            bindings.append(binding.to_native())

        policy.bindings = bindings
        policy.save()
        return ResponsePolicy.from_database(policy)


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
    @cherrypy.tools.model_out(cls=ResponsePolicy)
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
        project: Project = cherrypy.request.project
        policy = IAMPolicy.get(project)
        bindings = []
        request: RequestSetPolicy = cherrypy.request.model

        if request.resource_version != policy.resource_version:
            raise cherrypy.HTTPError(400, 'The policy has a newer reosurce version than requested')

        for binding in request.bindings:
            role = IAMProjectRole.get(project, binding.role)
            if role is None:
                raise cherrypy.HTTPError(404, 'Unknown project role ' + binding.role)
            for member in binding.members:
                if member.contains(':') is False:
                    raise cherrypy.HTTPError(400, 'Member must be in the following format: '
                                                  '{user/serviceAccount/group}:{email}')

                kind, email, *junk = member.split(":")

                if len(junk) > 0:
                    raise cherrypy.HTTPError(400, 'Member must be in the following format: '
                                                  '{user/serviceAccount/group}:{email}')

                username, domain, *_ = email.split("@")

                if kind not in ['user', 'serviceAccount', 'group']:
                    raise cherrypy.HTTPError(400, 'Member must be in the following format: '
                                                  '{user/serviceAccount/group}:{email}')

                if kind == 'serviceAccount':
                    saKind, project_name, *suffix = domain.split(".")
                    suffix = ".".join(suffix)

                    if saKind != 'service-account' or suffix != 'sandwich.local':
                        raise cherrypy.HTTPError(400, 'Service account emails must be in the following format: '
                                                      'service-account.{project_name/system}.sandwich.local')

                    if project_name == 'system':
                        sa = SystemServiceAccount.get(username)
                        if sa is None:
                            raise cherrypy.HTTPError(404, 'Unknown System Service Account ' + email)
                    else:
                        sa_project = Project.get(project_name)
                        if sa_project is None:
                            raise cherrypy.HTTPError(404, 'Unknown System Project Account ' + email)

                        sa = ProjectServiceAccount.get(sa_project, username)
                        if sa is None:
                            raise cherrypy.HTTPError(404, 'Unknown System Project Account ' + email)

                if kind == 'group':
                    if domain != 'group.system.sandwich.local':
                        raise cherrypy.HTTPError(400, 'Invalid email for group ' + email)
                    group = IAMSystemGroup.get(username)
                    if group is None:
                        raise cherrypy.HTTPError(404, 'Unknown Group ' + username)

                if kind == 'user':
                    if domain.endswith('sandwich.local'):
                        raise cherrypy.HTTPError(400, 'Cannot add ' + email + " has a user")

            bindings.append(binding.to_native())

        policy.bindings = bindings
        policy.save()
        return ResponsePolicy.from_database(policy)
