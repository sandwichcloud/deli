import cherrypy

from deli.counter.http.mounts.root.routes.v1.validation_models.network_ports import ResponseNetworkPort, \
    ParamsNetworkPort, ParamsListNetworkPort
from deli.http.route import Route
from deli.http.router import Router
from deli.kubernetes.resources.v1alpha1.network.model import NetworkPort


class NetworkPortsRouter(Router):
    def __init__(self):
        super().__init__(uri_base='network-ports')

    @Route(route='{network_port_id}')
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsNetworkPort)
    @cherrypy.tools.model_out(cls=ResponseNetworkPort)
    @cherrypy.tools.resource_object(id_param="network_port_id", cls=NetworkPort)
    @cherrypy.tools.enforce_policy(policy_name="network_ports:get")
    def get(self, **_):
        return ResponseNetworkPort.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsListNetworkPort)
    @cherrypy.tools.model_out_pagination(cls=ResponseNetworkPort)
    @cherrypy.tools.enforce_policy(policy_name="network_ports:list")
    def list(self, limit, marker):
        kwargs = {
            'project': cherrypy.request.project
        }
        return self.paginate(NetworkPort, ResponseNetworkPort, limit, marker, **kwargs)
