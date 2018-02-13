import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.http.mounts.root.routes.v1.validation_models.regions import ResponseRegion, RequestCreateRegion, \
    ParamsRegion, ParamsListRegion, RequestRegionSchedule
from deli.counter.http.router import SandwichRouter
from deli.kubernetes.resources.const import NAME_LABEL
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.region.model import Region


class RegionsRouter(SandwichRouter):
    def __init__(self):
        super().__init__(uri_base='regions')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateRegion)
    @cherrypy.tools.model_out(cls=ResponseRegion)
    @cherrypy.tools.enforce_policy(policy_name="regions:create")
    def create(self):
        request: RequestCreateRegion = cherrypy.request.model

        region = Region.get_by_name(request.name)
        if region is not None:
            raise cherrypy.HTTPError(409, 'A region with the requested name already exists.')

        region = Region()
        region.name = request.name
        region.datacenter = request.datacenter
        region.image_datastore = request.image_datastore
        region.schedulable = False

        if request.image_folder is not None:
            region.image_folder = request.image_folder

        region.create()

        return ResponseRegion.from_database(region)

    @Route(route='{region_id}')
    @cherrypy.tools.model_params(cls=ParamsRegion)
    @cherrypy.tools.model_out(cls=ResponseRegion)
    @cherrypy.tools.resource_object(id_param="region_id", cls=Region)
    @cherrypy.tools.enforce_policy(policy_name="regions:get")
    def get(self, **_):
        return ResponseRegion.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListRegion)
    @cherrypy.tools.model_out_pagination(cls=ResponseRegion)
    @cherrypy.tools.enforce_policy(policy_name="regions:list")
    def list(self, name, limit, marker):
        kwargs = {
            'label_selector': []
        }

        if name is not None:
            kwargs['label_selector'].append(NAME_LABEL + '=' + name)

        if len(kwargs['label_selector']) > 0:
            kwargs['label_selector'] = ",".join(kwargs['label_selector'])
        else:
            del kwargs['label_selector']
        return self.paginate(Region, ResponseRegion, limit, marker, **kwargs)

    @Route(route='{region_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsRegion)
    @cherrypy.tools.resource_object(id_param="region_id", cls=Region)
    @cherrypy.tools.enforce_policy(policy_name="regions:delete")
    def delete(self, **_):
        cherrypy.response.status = 204

        region: Region = cherrypy.request.resource_object

        if region.state == ResourceState.ToDelete or region.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Region is already being deleting")

        if region.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Region has already been deleted")

        if region.schedulable:
            raise cherrypy.HTTPError(400, 'Region must not be schedulable.')

        region.delete()

    @Route(route='{region_id}/action/schedule', methods=[RequestMethods.PUT])
    @cherrypy.tools.model_params(cls=ParamsRegion)
    @cherrypy.tools.model_in(cls=RequestRegionSchedule)
    @cherrypy.tools.resource_object(id_param="region_id", cls=Region)
    @cherrypy.tools.enforce_policy(policy_name="regions:action:schedule")
    def action_schedule(self, **_):
        cherrypy.response.status = 204

        request: RequestRegionSchedule = cherrypy.request.model
        region: Region = cherrypy.request.resource_object

        if region.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, "Cannot change schedulability while in the current state.")

        region.schedulable = request.schedulable
        region.save()
