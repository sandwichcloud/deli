import uuid

import cherrypy

from deli.counter.http.mounts.root.routes.v1.validation_models.networks import RequestCreateNetwork, ResponseNetwork, \
    ParamsNetwork, ParamsListNetwork
from deli.http.request_methods import RequestMethods
from deli.http.route import Route
from deli.http.router import Router
from deli.kubernetes.resources.const import REGION_LABEL
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.network.model import Network
from deli.kubernetes.resources.v1alpha1.region.model import Region


class NetworkRouter(Router):
    def __init__(self):
        super().__init__(uri_base='networks')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateNetwork)
    @cherrypy.tools.model_out(cls=ResponseNetwork)
    @cherrypy.tools.enforce_policy(policy_name="networks:create")
    def create(self):
        request: RequestCreateNetwork = cherrypy.request.model

        network = Network.get_by_name(request.name)
        if network is not None:
            raise cherrypy.HTTPError(409, 'A network with the requested name does already exists.')

        region = Region.get(request.region_id)
        if region is None:
            raise cherrypy.HTTPError(404, 'A region with the requested id does not exist.')

        if region.state != ResourceState.Created:
            raise cherrypy.HTTPError(409, 'Can only create a network with a region in the following state: %s'.format(
                ResourceState.Created))

        # TODO: check duplicate (or overlapping) cidr

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

    @Route(route='{network_id}')
    @cherrypy.tools.model_params(cls=ParamsNetwork)
    @cherrypy.tools.model_out(cls=ResponseNetwork)
    @cherrypy.tools.resource_object(id_param="network_id", cls=Network)
    @cherrypy.tools.enforce_policy(policy_name="networks:get")
    def get(self, **_):
        return ResponseNetwork.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListNetwork)
    @cherrypy.tools.model_out_pagination(cls=ResponseNetwork)
    @cherrypy.tools.enforce_policy(policy_name="networks:list")
    def list(self, region_name, limit: int, marker: uuid.UUID):
        kwargs = {}
        if region_name is not None:
            region: Region = Region.get(region_name)
            if region is None:
                raise cherrypy.HTTPError(404, "A region with the requested name does not exist.")

            kwargs['label_selector'] = REGION_LABEL + '=' + region.name

        return self.paginate(Network, ResponseNetwork, limit, marker, **kwargs)

    @Route(route='{network_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsNetwork)
    @cherrypy.tools.resource_object(id_param="network_id", cls=Network)
    @cherrypy.tools.enforce_policy(policy_name="networks:delete")
    def delete(self, **_):
        cherrypy.response.status = 204
        network: Network = cherrypy.request.resource_object

        if network.state == ResourceState.ToDelete or network.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Network is already being deleting")

        if network.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Network has already been deleted")

        network.delete()
