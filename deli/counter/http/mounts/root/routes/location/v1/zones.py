import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.http.mounts.root.routes.location.v1.validation_models.zones import RequestCreateZone, ResponseZone, \
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
    @cherrypy.tools.enforce_permission(permission_name="zones:create")
    def create(self):
        """Create a zone
        ---
        post:
            description: Create a zone
            tags:
                - location
                - zone
            requestBody:
                description: Zone to create
            responses:
                200:
                    description: The created zone
        """
        request: RequestCreateZone = cherrypy.request.model

        zone = Zone.get(request.name)
        if zone is not None:
            raise cherrypy.HTTPError(409, 'A zone with the requested name already exists.')

        region = Region.get(request.region_name)
        if region is None:
            raise cherrypy.HTTPError(404, 'A region with the requested name does not exist.')

        if region.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Can only create a zone with a region in the following state: {0}'.format(
                ResourceState.Created.value))

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

    @Route(route='{zone_name}')
    @cherrypy.tools.model_params(cls=ParamsZone)
    @cherrypy.tools.model_out(cls=ResponseZone)
    @cherrypy.tools.resource_object(id_param="zone_name", cls=Zone)
    def get(self, **_):
        """Get a zone
        ---
        get:
            description: Get a zone
            tags:
                - location
                - zone
            responses:
                200:
                    description: The zone
        """
        return ResponseZone.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListZone)
    @cherrypy.tools.model_out_pagination(cls=ResponseZone)
    def list(self, region_name, limit, marker):
        """List zones
        ---
        get:
            description: List zones
            tags:
                - location
                - zone
            responses:
                200:
                    description: List of zones
        """
        kwargs = {}
        if region_name is not None:
            region: Region = Region.get(region_name)
            if region is None:
                raise cherrypy.HTTPError(404, "A region with the requested name does not exist.")

            kwargs['label_selector'] = 'sandwichcloud.io/region=' + region.name

        return self.paginate(Zone, ResponseZone, limit, marker, **kwargs)

    @Route(route='{zone_name}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsZone)
    @cherrypy.tools.resource_object(id_param="zone_name", cls=Zone)
    @cherrypy.tools.enforce_permission(permission_name="zones:delete")
    def delete(self, **_):
        """Delete a zone
        ---
        delete:
            description: Delete a zone
            tags:
                - location
                - zone
            responses:
                204:
                    description: Zone deleted
        """
        cherrypy.response.status = 204

        zone: Zone = cherrypy.request.resource_object
        if zone.state == ResourceState.ToDelete or zone.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Zone is already being deleting")

        if zone.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Zone has already been deleted")

        if zone.schedulable:
            raise cherrypy.HTTPError(400, 'Zone must not be schedulable.')

        zone.delete()

    @Route(route='{zone_name}/action/schedule', methods=[RequestMethods.PUT])
    @cherrypy.tools.model_params(cls=ParamsZone)
    @cherrypy.tools.model_in(cls=RequestZoneSchedule)
    @cherrypy.tools.resource_object(id_param="zone_name", cls=Zone)
    @cherrypy.tools.enforce_permission(permission_name="zones:action:schedule")
    def action_schedule(self, **_):
        """Allow or disallow a zone to be scheduled
        ---
        put:
            description: Allow or disallow a zone to be scheduled
            tags:
                - location
                - zone
            requestBody:
                description: Zone schedule options
            responses:
                204:
                    description: Zone schedule changed
        """
        cherrypy.response.status = 204

        request: RequestZoneSchedule = cherrypy.request.model
        zone: Zone = cherrypy.request.resource_object

        if zone.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, "Cannot change schedulability while in the current state.")

        zone.schedulable = request.schedulable
        zone.save()
