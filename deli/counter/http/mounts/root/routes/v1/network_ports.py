import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.http.mounts.root.routes.v1.validation_models.network_ports import ResponseNetworkPort, \
    ParamsNetworkPort, ParamsListNetworkPort
from deli.counter.http.router import SandwichRouter
from deli.kubernetes.resources.const import NETWORK_PORT_LABEL
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.instance.model import Instance
from deli.kubernetes.resources.v1alpha1.network.model import NetworkPort


class NetworkPortsRouter(SandwichRouter):
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

    @Route(route='{network_port_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsNetworkPort)
    @cherrypy.tools.resource_object(id_param="network_port_id", cls=NetworkPort)
    @cherrypy.tools.enforce_policy(policy_name="network_ports:delete")
    def delete(self, **_):
        cherrypy.response.status = 204
        network_port: NetworkPort = cherrypy.request.resource_object

        if network_port.state == ResourceState.ToDelete or network_port.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Network Port is already being deleting")

        if network_port.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Network Port has already been deleted")

        instances = Instance.list_all(label_selector=NETWORK_PORT_LABEL + "=" + str(network_port.id))
        if len(instances) > 0:
            raise cherrypy.HTTPError(409, 'Cannot delete a network port while it is in use by an instance')

        network_port.delete()
