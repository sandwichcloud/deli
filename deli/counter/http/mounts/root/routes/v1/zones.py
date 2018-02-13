import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.http.mounts.root.routes.v1.validation_models.zones import RequestCreateZone, ResponseZone, \
    ParamsZone, ParamsListZone, RequestZoneSchedule
from deli.counter.http.router import SandwichRouter
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.region.model import Region
from deli.kubernetes.resources.v1alpha1.zone.model import Zone


class ZoneRouter(SandwichRouter):
    def __init__(self):
        super().__init__(uri_base='zones')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateZone)
    @cherrypy.tools.model_out(cls=ResponseZone)
    @cherrypy.tools.enforce_policy(policy_name="zones:create")
    def create(self):
        request: RequestCreateZone = cherrypy.request.model

        zone = Zone.get_by_name(request.name)
        if zone is not None:
            raise cherrypy.HTTPError(409, 'A zone with the requested name already exists.')

        region = Region.get(request.region_id)
        if region is None:
            raise cherrypy.HTTPError(404, 'A region with the requested id does not exist.')

        if region.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Can only create a zone with a region in the following state: %s'.format(
                ResourceState.Created))

        zone = Zone()
        zone.name = request.name
        zone.region = region
        zone.vm_cluster = request.vm_cluster
        zone.vm_datastore = request.vm_datastore
        zone.core_provision_percent = request.core_provision_percent
        zone.ram_provision_percent = request.ram_provision_percent
        zone.schedulable = False

        if request.vm_folder is not None:
            zone.vm_folder = request.vm_folder

        zone.create()

        return ResponseZone.from_database(zone)

    @Route(route='{zone_id}')
    @cherrypy.tools.model_params(cls=ParamsZone)
    @cherrypy.tools.model_out(cls=ResponseZone)
    @cherrypy.tools.resource_object(id_param="zone_id", cls=Zone)
    @cherrypy.tools.enforce_policy(policy_name="zones:get")
    def get(self, **_):
        return ResponseZone.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListZone)
    @cherrypy.tools.model_out_pagination(cls=ResponseZone)
    @cherrypy.tools.enforce_policy(policy_name="zones:list")
    def list(self, region_id, limit, marker):

        kwargs = {}
        if region_id is not None:
            region: Region = Region.get(region_id)
            if region is None:
                raise cherrypy.HTTPError(404, "A region with the requested id does not exist.")

            kwargs['label_selector'] = 'sandwichcloud.io/region=' + region.name

        return self.paginate(Zone, ResponseZone, limit, marker, **kwargs)

    @Route(route='{zone_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsZone)
    @cherrypy.tools.resource_object(id_param="zone_id", cls=Zone)
    @cherrypy.tools.enforce_policy(policy_name="zones:delete")
    def delete(self, **_):
        cherrypy.response.status = 204

        zone: Zone = cherrypy.request.resource_object
        if zone.state == ResourceState.ToDelete or zone.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Zone is already being deleting")

        if zone.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Zone has already been deleted")

        if zone.schedulable:
            raise cherrypy.HTTPError(400, 'Zone must not be schedulable.')

        zone.delete()

    @Route(route='{zone_id}/action/schedule', methods=[RequestMethods.PUT])
    @cherrypy.tools.model_params(cls=ParamsZone)
    @cherrypy.tools.model_in(cls=RequestZoneSchedule)
    @cherrypy.tools.resource_object(id_param="zone_id", cls=Zone)
    @cherrypy.tools.enforce_policy(policy_name="zones:action:schedule")
    def action_schedule(self, **_):
        cherrypy.response.status = 204

        request: RequestZoneSchedule = cherrypy.request.model
        zone: Zone = cherrypy.request.resource_object

        if zone.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, "Cannot change schedulability while in the current state.")

        zone.schedulable = request.schedulable
        zone.save()
