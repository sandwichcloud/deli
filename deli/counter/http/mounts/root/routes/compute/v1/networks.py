import uuid

import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.http.mounts.root.routes.compute.v1.validation_models.networks import RequestCreateNetwork, \
    ResponseNetwork, \
    ParamsNetwork, ParamsListNetwork
from deli.counter.http.router import SandwichRouter
from deli.kubernetes.resources.const import REGION_LABEL
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.network.model import Network
from deli.kubernetes.resources.v1alpha1.region.model import Region


class NetworkRouter(SandwichRouter):
    def __init__(self):
        super().__init__(uri_base='networks')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateNetwork)
    @cherrypy.tools.model_out(cls=ResponseNetwork)
    @cherrypy.tools.enforce_permission(permission_name="networks:create")
    def create(self):
        """Create a network
        ---
        post:
            description: Create a network
            tags:
                - compute
                - network
            requestBody:
                description: Network to create
            responses:
                200:
                    description: The created network
        """
        request: RequestCreateNetwork = cherrypy.request.model

        network = Network.get(request.name)
        if network is not None:
            raise cherrypy.HTTPError(409, 'A network with the requested name does already exists.')

        region = Region.get(request.region_name)
        if region is None:
            raise cherrypy.HTTPError(404, 'A region with the requested name does not exist.')

        if region.state != ResourceState.Created:
            raise cherrypy.HTTPError(409, 'Can only create a network with a region in the following state: %s'.format(
                ResourceState.Created))

        network = Network()
        network.name = request.name
        network.port_group = request.port_group
        network.cidr = request.cidr
        network.gateway = request.gateway
        network.dns_servers = request.dns_servers
        network.pool_start = request.pool_start
        network.pool_end = request.pool_end
        network.region = region
        network.create()

        return ResponseNetwork.from_database(network)

    @Route(route='{network_name}')
    @cherrypy.tools.model_params(cls=ParamsNetwork)
    @cherrypy.tools.model_out(cls=ResponseNetwork)
    @cherrypy.tools.resource_object(id_param="network_name", cls=Network)
    def get(self, **_):
        """Get a network
        ---
        get:
            description: Get a network
            tags:
                - compute
                - network
            responses:
                200:
                    description: The network
        """
        return ResponseNetwork.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListNetwork)
    @cherrypy.tools.model_out_pagination(cls=ResponseNetwork)
    def list(self, region, limit: int, marker: uuid.UUID):
        """List networks
        ---
        get:
            description: List networks
            tags:
                - compute
                - network
            responses:
                200:
                    description: List of networks
        """
        kwargs = {
            'label_selector': []
        }
        if region is not None:
            region: Region = Region.get(region)
            if region is None:
                raise cherrypy.HTTPError(404, "A region with the requested name does not exist.")

            kwargs['label_selector'].append(REGION_LABEL + '=' + region.name)

        if len(kwargs['label_selector']) > 0:
            kwargs['label_selector'] = ",".join(kwargs['label_selector'])
        else:
            del kwargs['label_selector']

        return self.paginate(Network, ResponseNetwork, limit, marker, **kwargs)

    @Route(route='{network_name}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsNetwork)
    @cherrypy.tools.resource_object(id_param="network_name", cls=Network)
    @cherrypy.tools.enforce_permission(permission_name="networks:delete")
    def delete(self, **_):
        """Delete a network
        ---
        delete:
            description: Delete a network
            tags:
                - compute
                - network
            responses:
                204:
                    description: Network deleted
        """
        cherrypy.response.status = 204
        network: Network = cherrypy.request.resource_object

        if network.state == ResourceState.ToDelete or network.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Network is already being deleting")

        if network.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Network has already been deleted")

        network.delete()
