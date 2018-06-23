import uuid

import cherrypy
from ingredients_http.route import Route

from deli.counter.auth.policy import SYSTEM_POLICIES, PROJECT_POLICIES
from deli.counter.http.mounts.root.routes.iam.v1.validation_models.policy import ParamsPolicy, ResponsePolicy, \
    ParamsListPolicy
from deli.counter.http.router import SandwichProjectRouter, SandwichSystemRouter


class IAMSystemPolicyRouter(SandwichSystemRouter):
    def __init__(self):
        super().__init__('policies')

    @Route(route='{policy_name}')
    @cherrypy.tools.model_params(cls=ParamsPolicy)
    @cherrypy.tools.model_out(cls=ResponsePolicy)
    def get(self, policy_name):
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
        policy = None

        for p in SYSTEM_POLICIES:
            if p['name'] == policy_name:
                policy = p
                break

        if policy is None:
            raise cherrypy.HTTPError(404, "The resource could not be found.")

        return ResponsePolicy(policy)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListPolicy)
    @cherrypy.tools.model_out_pagination(cls=ResponsePolicy)
    def list(self, limit: int, marker: uuid.UUID):
        """List system policies
        ---
        get:
            description: List system policies
            tags:
                - iam
                - policy
            responses:
                200:
                    description: List of system policies
        """
        policies = []

        for p in SYSTEM_POLICIES:
            policies.append(ResponsePolicy(p))

        return policies, False


class IAMProjectPolicyRouter(SandwichProjectRouter):
    def __init__(self):
        super().__init__('policies')

    @Route(route='{policy_name}')
    @cherrypy.tools.model_params(cls=ParamsPolicy)
    @cherrypy.tools.model_out(cls=ResponsePolicy)
    def get(self, policy_name):
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

        policy = None

        for p in PROJECT_POLICIES:
            if p['name'] == policy_name:
                policy = p
                break

        if policy is None:
            raise cherrypy.HTTPError(404, "The resource could not be found.")

        return ResponsePolicy(policy)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListPolicy)
    @cherrypy.tools.model_out_pagination(cls=ResponsePolicy)
    def list(self, limit: int, marker: uuid.UUID):
        """List projectpolicies
        ---
        get:
            description: List project policies
            tags:
                - iam
                - policy
            responses:
                200:
                    description: List of project policies
        """
        policies = []

        for p in PROJECT_POLICIES:
            policies.append(ResponsePolicy(p))

        return policies, False
