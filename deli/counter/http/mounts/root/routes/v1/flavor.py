import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.http.mounts.root.routes.v1.validation_models.flavor import RequestCreateFlavor, ResponseFlavor, \
    ParamsFlavor, ParamsListFlavor
from deli.counter.http.router import SandwichRouter
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.flavor.model import Flavor


class FlavorRouter(SandwichRouter):
    def __init__(self):
        super().__init__(uri_base='flavors')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateFlavor)
    @cherrypy.tools.model_out(cls=ResponseFlavor)
    @cherrypy.tools.enforce_policy(policy_name="flavors:create")
    def create(self):
        request: RequestCreateFlavor = cherrypy.request.model

        flavor = Flavor.get_by_name(request.name)
        if flavor is not None:
            raise cherrypy.HTTPError(400, 'A flavor with the requested name already exists.')

        flavor = Flavor()
        flavor.name = request.name
        flavor.vcpus = request.vcpus
        flavor.ram = request.ram
        flavor.disk = request.disk
        flavor.create()

        return ResponseFlavor.from_database(flavor)

    @Route(route='{flavor_id}')
    @cherrypy.tools.model_params(cls=ParamsFlavor)
    @cherrypy.tools.model_out(cls=ResponseFlavor)
    @cherrypy.tools.resource_object(id_param="flavor_id", cls=Flavor)
    @cherrypy.tools.enforce_policy(policy_name="flavors:get")
    def get(self, **_):
        return ResponseFlavor.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsListFlavor)
    @cherrypy.tools.model_out_pagination(cls=ResponseFlavor)
    @cherrypy.tools.enforce_policy(policy_name="flavors:list")
    def list(self, limit, marker):
        return self.paginate(Flavor, ResponseFlavor, limit, marker)

    @Route(route='{flavor_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsFlavor)
    @cherrypy.tools.resource_object(id_param="flavor_id", cls=Flavor)
    @cherrypy.tools.enforce_policy(policy_name="flavors:delete")
    def delete(self, **_):
        cherrypy.response.status = 204
        flavor: Flavor = cherrypy.request.resource_object

        if flavor.state == ResourceState.ToDelete or flavor.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Flavor is already being deleting")

        if flavor.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Flavor has already been deleted")

        flavor.delete()
