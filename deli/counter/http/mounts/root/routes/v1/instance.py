import uuid

import cherrypy

from deli.counter.http.mounts.root.routes.v1.validation_models.images import ResponseImage
from deli.counter.http.mounts.root.routes.v1.validation_models.instances import RequestCreateInstance, ResponseInstance, \
    ParamsInstance, ParamsListInstance, RequestInstancePowerOffRestart, RequestInstanceImage
from deli.http.request_methods import RequestMethods
from deli.http.route import Route
from deli.http.router import Router
from deli.kubernetes.resources.const import REGION_LABEL, IMAGE_LABEL, ZONE_LABEL
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.image.model import Image
from deli.kubernetes.resources.v1alpha1.instance.model import Instance, VMPowerState
from deli.kubernetes.resources.v1alpha1.keypair.keypair import Keypair
from deli.kubernetes.resources.v1alpha1.network.model import NetworkPort, Network
from deli.kubernetes.resources.v1alpha1.region.model import Region
from deli.kubernetes.resources.v1alpha1.service_account.model import ServiceAccount
from deli.kubernetes.resources.v1alpha1.zone.model import Zone


class InstanceRouter(Router):
    def __init__(self):
        super().__init__(uri_base='instances')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_in(cls=RequestCreateInstance)
    @cherrypy.tools.model_out(cls=ResponseInstance)
    @cherrypy.tools.enforce_policy(policy_name="instances:create")
    def create(self):
        request: RequestCreateInstance = cherrypy.request.model
        project: Project = cherrypy.request.project

        # TODO: do we care about unique instance names in a project?
        # instance = Instance.get_by_name(project, request.name)
        # if instance is not None:
        #     raise cherrypy.HTTPError(409, 'An instance with the requested name already exists.')

        region = Region.get(request.region_id)
        if region is None:
            raise cherrypy.HTTPError(404, 'A region with the requested id does not exist.')

        zone = None
        if request.zone_id is not None:
            zone = Zone.get(request.zone_id)
            if zone is None:
                raise cherrypy.HTTPError(404, 'A zone with the requested id does not exist.')
            if zone.region.id != region.id:
                raise cherrypy.HTTPError(409, 'The requested zone is not within the requested region')

        network = Network.get(request.network_id)
        if network is None:
            raise cherrypy.HTTPError(404, 'A network with the requested id does not exist.')
        if network.region.id != region.id:
            raise cherrypy.HTTPError(409, 'The requested network is not within the requested region')

        image = Image.get(project, request.image_id)
        if image is None:
            raise cherrypy.HTTPError(404, 'An image with the requested id does not exist.')
        if image.region.id != region.id:
            raise cherrypy.HTTPError(409, 'The requested image is not within the requested region')

        keypairs = []
        for keypair_id in request.keypair_ids:
            keypair = Keypair.get(project, keypair_id)
            if keypair is None:
                raise cherrypy.HTTPError(404,
                                         'A keypair with the requested id of %s does not exist.'.format(keypair_id))
            keypairs.append(keypair)

        if request.service_account_id is not None:
            service_account = ServiceAccount.get(project, request.service_account_id)
            if service_account is None:
                raise cherrypy.HTTPError(404, 'A service account with the requested id of %s does not exist.'.format(
                    request.service_account_id))
        else:
            service_account = ServiceAccount.get_by_name(project, 'default')

        network_port = NetworkPort()
        network_port.project = project
        network_port.network = network
        network_port.create()

        instance = Instance()
        instance.name = request.name
        instance.project = project
        instance.region = region
        if zone is not None:
            instance.zone = zone
        instance.image = image
        instance.service_account = service_account
        instance.network_port = network_port
        instance.keypairs = keypairs
        for k, v in request.tags.items():
            instance.add_tag(k, v)
        instance.create()

        return ResponseInstance.from_database(instance)

    @Route(route='{instance_id}')
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsInstance)
    @cherrypy.tools.model_out(cls=ResponseInstance)
    @cherrypy.tools.resource_object(id_param="instance_id", cls=Instance)
    @cherrypy.tools.enforce_policy(policy_name="instances:get")
    def get(self, **_):
        return ResponseInstance.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsListInstance)
    @cherrypy.tools.model_out_pagination(cls=ResponseInstance)
    @cherrypy.tools.enforce_policy(policy_name="instances:list")
    def list(self, image_id, region_id, zone_id, limit: int, marker: uuid.UUID):
        kwargs = {
            'project': cherrypy.request.project,
            'label_selector': [],
        }

        if image_id is not None:
            image: Image = Image.get(cherrypy.request.project, image_id)
            if image is None:
                raise cherrypy.HTTPError(404, "An image with the requested id does not exist.")
            kwargs['label_selector'].append(IMAGE_LABEL + '=' + image.id)

        if region_id is not None:
            region: Region = Region.get(region_id)
            if region is None:
                raise cherrypy.HTTPError(404, "A region with the requested id does not exist.")
            kwargs['label_selector'].append(REGION_LABEL + '=' + region.id)

        if zone_id is not None:
            zone: Zone = Zone.get(zone_id)
            if zone is None:
                raise cherrypy.HTTPError(404, 'A zone with the requested id does not exist.')
            kwargs['label_selector'].append(ZONE_LABEL + '=' + zone.id)

        if len(kwargs['label_selector']) > 0:
            kwargs['label_selector'] = ",".join(kwargs['label_selector'])
        else:
            del kwargs['label_selector']

        return self.paginate(Instance, ResponseInstance, limit, marker, **kwargs)

    @Route(route='{instance_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsInstance)
    @cherrypy.tools.resource_object(id_param="instance_id", cls=Instance)
    @cherrypy.tools.enforce_policy(policy_name="instances:delete")
    def delete(self, **_):
        cherrypy.response.status = 204

        instance: Instance = cherrypy.request.resource_object
        if instance.state == ResourceState.ToDelete or instance.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Instance is already being deleting")

        if instance.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Instance has already been deleted")

        instance.delete()

    @Route(route='{instance_id}/action/start', methods=[RequestMethods.PUT])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsInstance)
    @cherrypy.tools.resource_object(id_param="instance_id", cls=Instance)
    @cherrypy.tools.enforce_policy(policy_name="instances:delete")
    def action_start(self, **_):
        cherrypy.response.status = 202

        instance: Instance = cherrypy.request.resource_object

        if instance.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Instance is not in the following state: ' + ResourceState.Created.value)
        if instance.task is not None:
            raise cherrypy.HTTPError(400, 'Please wait for the current task to finish.')
        if instance.power_state != VMPowerState.POWERED_OFF:
            raise cherrypy.HTTPError(400, 'Instance must be powered off.')

        instance.action_start()

    @Route(route='{instance_id}/action/stop', methods=[RequestMethods.PUT])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsInstance)
    @cherrypy.tools.model_in(cls=RequestInstancePowerOffRestart)
    @cherrypy.tools.resource_object(id_param="instance_id", cls=Instance)
    @cherrypy.tools.enforce_policy(policy_name="instances:delete")
    def action_stop(self, **_):
        request: RequestInstancePowerOffRestart = cherrypy.request.model
        cherrypy.response.status = 202

        instance: Instance = cherrypy.request.resource_object

        if instance.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Instance is not in the following state: ' + ResourceState.Created.value)
        if instance.task is not None:
            raise cherrypy.HTTPError(400, 'Please wait for the current task to finish.')
        if instance.power_state != VMPowerState.POWERED_ON:
            raise cherrypy.HTTPError(400, 'Instance must be powered on.')

        instance.action_stop(request.hard, request.timeout)

    @Route(route='{instance_id}/action/restart', methods=[RequestMethods.PUT])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsInstance)
    @cherrypy.tools.model_in(cls=RequestInstancePowerOffRestart)
    @cherrypy.tools.resource_object(id_param="instance_id", cls=Instance)
    @cherrypy.tools.enforce_policy(policy_name="instances:delete")
    def action_restart(self, **_):
        request: RequestInstancePowerOffRestart = cherrypy.request.model
        cherrypy.response.status = 202

        instance: Instance = cherrypy.request.resource_object

        if instance.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Instance is not in the following state: ' + ResourceState.Created.value)
        if instance.task is not None:
            raise cherrypy.HTTPError(400, 'Please wait for the current task to finish.')
        if instance.power_state != VMPowerState.POWERED_ON:
            raise cherrypy.HTTPError(400, 'Instance must be powered on.')

        instance.action_restart(request.hard, request.timeout)

    @Route(route='{instance_id}/action/image', methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsInstance)
    @cherrypy.tools.model_in(cls=RequestInstanceImage)
    @cherrypy.tools.model_out(cls=ResponseImage)
    @cherrypy.tools.resource_object(id_param="instance_id", cls=Instance)
    @cherrypy.tools.enforce_policy(policy_name="instances:delete")
    def action_image(self, **_):
        project: Project = cherrypy.request.project
        request: RequestInstanceImage = cherrypy.request.model

        instance: Instance = cherrypy.request.resource_object

        if instance.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Instance is not in the following state: ' + ResourceState.Created.value)
        if instance.task is not None:
            raise cherrypy.HTTPError(400, 'Please wait for the current task to finish.')
        if instance.power_state != VMPowerState.POWERED_OFF:
            raise cherrypy.HTTPError(400, 'Instance must be powered off.')

        if Image.get_by_name(project, request.name) is not None:
            raise cherrypy.HTTPError(400, 'An image with the requested name already exists.')

        image = instance.action_image(request.name)

        return ResponseImage.from_database(image)
