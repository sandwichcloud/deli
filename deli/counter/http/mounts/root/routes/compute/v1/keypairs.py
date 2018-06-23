import uuid

import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.http.mounts.root.routes.compute.v1.validation_models.keypairs import RequestCreateKeypair, \
    ResponseKeypair, \
    ParamsKeypair, ParamsListKeypair
from deli.counter.http.router import SandwichProjectRouter
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.keypair.keypair import Keypair


class KeypairsRouter(SandwichProjectRouter):
    def __init__(self):
        super().__init__(uri_base='keypairs')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateKeypair)
    @cherrypy.tools.model_out(cls=ResponseKeypair)
    @cherrypy.tools.enforce_policy(policy_name="keypairs:create")
    def create(self):
        """Create a keypair
        ---
        post:
            description: Create a keypair
            tags:
                - compute
                - keypair
            requestBody:
                description: Keypair to create
            responses:
                200:
                    description: The created keypair
        """
        request: RequestCreateKeypair = cherrypy.request.model
        project = cherrypy.request.project

        keypair = Keypair.get(project, request.name)
        if keypair is not None:
            raise cherrypy.HTTPError(409, "A keypair with the requested name already exists.")

        keypair = Keypair()
        keypair.name = request.name
        keypair.public_key = request.public_key
        keypair.project = project
        keypair.create()
        return ResponseKeypair.from_database(keypair)

    @Route(route='{keypair_name}')
    @cherrypy.tools.model_params(cls=ParamsKeypair)
    @cherrypy.tools.model_out(cls=ResponseKeypair)
    @cherrypy.tools.resource_object(id_param="keypair_name", cls=Keypair)
    @cherrypy.tools.enforce_policy(policy_name="keypairs:get")
    def get(self, **_):
        """Get a keypair
        ---
        get:
            description: Get a keypair
            tags:
                - compute
                - keypair
            responses:
                200:
                    description: The keypair
        """
        return ResponseKeypair.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListKeypair)
    @cherrypy.tools.model_out_pagination(cls=ResponseKeypair)
    @cherrypy.tools.enforce_policy(policy_name="keypairs:list")
    def list(self, limit: int, marker: uuid.UUID):
        """List keypairs
        ---
        get:
            description: List keypairs
            tags:
                - compute
                - keypair
            responses:
                200:
                    description: List of keypairs
        """
        kwargs = {
            'project': cherrypy.request.project
        }
        return self.paginate(Keypair, ResponseKeypair, limit, marker, **kwargs)

    @Route(route='{keypair_name}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsKeypair)
    @cherrypy.tools.resource_object(id_param="keypair_name", cls=Keypair)
    @cherrypy.tools.enforce_policy(policy_name="keypairs:delete")
    def delete(self, **_):
        """Delete a keypair
        ---
        delete:
            description: Delete a keypair
            tags:
                - compute
                - keypair
            responses:
                204:
                    description: Keypair deleted
        """
        cherrypy.response.status = 204
        keypair: Keypair = cherrypy.request.resource_object

        if keypair.state == ResourceState.ToDelete or keypair.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Keypair is already being deleting")

        if keypair.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Keypair has already been deleted")

        keypair.delete()
