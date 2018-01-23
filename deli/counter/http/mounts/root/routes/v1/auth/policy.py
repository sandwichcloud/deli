import uuid

import cherrypy

from deli.counter.auth.policy import POLICIES
from deli.counter.http.mounts.root.routes.v1.auth.validation_models.policy import ParamsPolicy, ResponsePolicy, \
    ParamsListPolicy
from deli.http.route import Route
from deli.http.router import Router


class AuthPolicyRouter(Router):
    def __init__(self):
        super().__init__('policies')

    @Route(route='{policy_name}')
    @cherrypy.tools.model_params(cls=ParamsPolicy)
    @cherrypy.tools.model_out(cls=ResponsePolicy)
    @cherrypy.tools.enforce_policy(policy_name="policies:get")
    def get(self, policy_name):

        policy = None

        for p in POLICIES:
            if p['name'] == policy_name:
                policy = p
                break

        if policy is None:
            raise cherrypy.HTTPError(404, "The resource could not be found.")

        return ResponsePolicy(policy)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListPolicy)
    @cherrypy.tools.model_out_pagination(cls=ResponsePolicy)
    @cherrypy.tools.enforce_policy(policy_name="policies:list")
    def list(self, limit: int, marker: uuid.UUID):
        policies = []

        for p in POLICIES:
            policies.append(ResponsePolicy(p))

        return policies, False
