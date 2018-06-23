import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.http.mounts.root.routes.location.v1.validation_models.regions import ResponseRegion, \
    RequestCreateRegion, \
    ParamsRegion, ParamsListRegion, RequestRegionSchedule
from deli.counter.http.router import SandwichRouter
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
        """Create a region
        ---
        post:
            description: Create a region
            tags:
                - location
                - region
            requestBody:
                description: Region to create
            responses:
                200:
                    description: The created region
        """
        request: RequestCreateRegion = cherrypy.request.model

        region = Region.get(request.name)
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

    @Route(route='{region_name}')
    @cherrypy.tools.model_params(cls=ParamsRegion)
    @cherrypy.tools.model_out(cls=ResponseRegion)
    @cherrypy.tools.resource_object(id_param="region_name", cls=Region)
    def get(self, **_):
        """Get a region
        ---
        get:
            description: Get a region
            tags:
                - location
                - region
            responses:
                200:
                    description: The region
        """
        return ResponseRegion.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListRegion)
    @cherrypy.tools.model_out_pagination(cls=ResponseRegion)
    def list(self, limit, marker):
        """List regions
        ---
        get:
            description: List regions
            tags:
                - location
                - region
            responses:
                200:
                    description: List of regions
        """
        kwargs = {
            'label_selector': []
        }

        if len(kwargs['label_selector']) > 0:
            kwargs['label_selector'] = ",".join(kwargs['label_selector'])
        else:
            del kwargs['label_selector']
        return self.paginate(Region, ResponseRegion, limit, marker, **kwargs)

    @Route(route='{region_name}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsRegion)
    @cherrypy.tools.resource_object(id_param="region_name", cls=Region)
    @cherrypy.tools.enforce_policy(policy_name="regions:delete")
    def delete(self, **_):
        """Delete a region
        ---
        delete:
            description: Delete a region
            tags:
                - location
                - region
            responses:
                204:
                    description: Region deleted
        """
        cherrypy.response.status = 204

        region: Region = cherrypy.request.resource_object

        if region.state == ResourceState.ToDelete or region.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Region is already being deleting")

        if region.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Region has already been deleted")

        if region.schedulable:
            raise cherrypy.HTTPError(400, 'Region must not be schedulable.')

        region.delete()

    @Route(route='{region_name}/action/schedule', methods=[RequestMethods.PUT])
    @cherrypy.tools.model_params(cls=ParamsRegion)
    @cherrypy.tools.model_in(cls=RequestRegionSchedule)
    @cherrypy.tools.resource_object(id_param="region_name", cls=Region)
    @cherrypy.tools.enforce_policy(policy_name="regions:action:schedule")
    def action_schedule(self, **_):
        """Allow or disallow a region to be scheduled
        ---
        put:
            description: Allow or disallow a region to be scheduled
            tags:
                - location
                - region
            requestBody:
                description: Region schedule options
            responses:
                204:
                    description: Region schedule changed
        """
        cherrypy.response.status = 204

        request: RequestRegionSchedule = cherrypy.request.model
        region: Region = cherrypy.request.resource_object

        if region.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, "Cannot change schedulability while in the current state.")

        region.schedulable = request.schedulable
        region.save()
