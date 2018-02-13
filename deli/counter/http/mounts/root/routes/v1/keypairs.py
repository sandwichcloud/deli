import uuid

import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.http.mounts.root.routes.v1.validation_models.keypairs import RequestCreateKeypair, ResponseKeypair, \
    ParamsKeypair, ParamsListKeypair
from deli.counter.http.router import SandwichRouter
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.keypair.keypair import Keypair


class KeypairsRouter(SandwichRouter):
    def __init__(self):
        super().__init__(uri_base='keypairs')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_in(cls=RequestCreateKeypair)
    @cherrypy.tools.model_out(cls=ResponseKeypair)
    @cherrypy.tools.enforce_policy(policy_name="keypairs:create")
    def create(self):
        request: RequestCreateKeypair = cherrypy.request.model
        project = cherrypy.request.project

        keypair = Keypair.get_by_name(project, request.name)
        if keypair is not None:
            raise cherrypy.HTTPError(409, "A keypair with the requested name already exists.")

        keypair = Keypair()
        keypair.name = request.name
        keypair.public_key = request.public_key
        keypair.project = project
        keypair.create()
        return ResponseKeypair.from_database(keypair)

    @Route(route='{keypair_id}')
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsKeypair)
    @cherrypy.tools.model_out(cls=ResponseKeypair)
    @cherrypy.tools.resource_object(id_param="keypair_id", cls=Keypair)
    @cherrypy.tools.enforce_policy(policy_name="keypairs:get")
    def get(self, **_):
        return ResponseKeypair.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsListKeypair)
    @cherrypy.tools.model_out_pagination(cls=ResponseKeypair)
    @cherrypy.tools.enforce_policy(policy_name="keypairs:list")
    def list(self, limit: int, marker: uuid.UUID):
        kwargs = {
            'project': cherrypy.request.project
        }
        return self.paginate(Keypair, ResponseKeypair, limit, marker, **kwargs)

    @Route(route='{keypair_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsKeypair)
    @cherrypy.tools.resource_object(id_param="keypair_id", cls=Keypair)
    @cherrypy.tools.enforce_policy(policy_name="keypairs:delete")
    def delete(self, **_):
        cherrypy.response.status = 204
        keypair: Keypair = cherrypy.request.resource_object

        if keypair.state == ResourceState.ToDelete or keypair.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Keypair is already being deleting")

        if keypair.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Keypair has already been deleted")

        keypair.delete()
