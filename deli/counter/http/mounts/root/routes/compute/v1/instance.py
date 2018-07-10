import uuid

import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.http.mounts.root.errors.quota import QuotaError
from deli.counter.http.mounts.root.routes.compute.v1.validation_models.images import ResponseImage
from deli.counter.http.mounts.root.routes.compute.v1.validation_models.instances import RequestCreateInstance, \
    ResponseInstance, ParamsInstance, ParamsListInstance, RequestInstancePowerOffRestart, RequestInstanceImage
from deli.counter.http.router import SandwichProjectRouter
from deli.kubernetes.resources.const import REGION_LABEL, IMAGE_LABEL, ZONE_LABEL, ATTACHED_TO_LABEL
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.flavor.model import Flavor
from deli.kubernetes.resources.v1alpha1.iam_service_account.model import ProjectServiceAccount
from deli.kubernetes.resources.v1alpha1.image.model import Image
from deli.kubernetes.resources.v1alpha1.instance.model import Instance, VMPowerState
from deli.kubernetes.resources.v1alpha1.keypair.keypair import Keypair
from deli.kubernetes.resources.v1alpha1.network.model import NetworkPort, Network
from deli.kubernetes.resources.v1alpha1.project_quota.model import ProjectQuota
from deli.kubernetes.resources.v1alpha1.region.model import Region
from deli.kubernetes.resources.v1alpha1.volume.model import Volume
from deli.kubernetes.resources.v1alpha1.zone.model import Zone


class InstanceRouter(SandwichProjectRouter):
    def __init__(self):
        super().__init__(uri_base='instances')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateInstance)
    @cherrypy.tools.model_out(cls=ResponseInstance)
    @cherrypy.tools.enforce_permission(permission_name="instances:create")
    def create(self):
        """Create an instance
        ---
        post:
            description: Create an instance
            tags:
                - compute
                - instance
            requestBody:
                description: Instance to create
            responses:
                200:
                    description: The created instance
        """
        request: RequestCreateInstance = cherrypy.request.model
        project: Project = cherrypy.request.project

        instance = Instance.get(project, request.name)
        if instance is not None:
            raise cherrypy.HTTPError(409, 'An instance with the requested name already exists.')

        region = Region.get(request.region_name)
        if region is None:
            raise cherrypy.HTTPError(404, 'A region with the requested name does not exist.')
        if region.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Can only create a instance with a region in the following state: {0}'.format(
                ResourceState.Created.value))

        zone = None
        if request.zone_name is not None:
            zone = Zone.get(request.zone_name)
            if zone is None:
                raise cherrypy.HTTPError(404, 'A zone with the requested name does not exist.')
            if zone.region.name != region.name:
                raise cherrypy.HTTPError(409, 'The requested zone is not within the requested region')
            if zone.state != ResourceState.Created:
                raise cherrypy.HTTPError(400,
                                         'Can only create a instance with a zone in the following state: {0}'.format(
                                             ResourceState.Created.value))

        network = Network.get(request.network_name)
        if network is None:
            raise cherrypy.HTTPError(404, 'A network with the requested name does not exist.')
        if network.region.name != region.name:
            raise cherrypy.HTTPError(409, 'The requested network is not within the requested region')
        if network.state != ResourceState.Created:
            raise cherrypy.HTTPError(400,
                                     'Can only create a instance with a network in the following state: {0}'.format(
                                         ResourceState.Created.value))

        # TODO: User inputs image url instead of id
        # projectId/imageId
        image: Image = Image.get(project, request.image_name)
        if image is None:
            raise cherrypy.HTTPError(404, 'An image with the requested name does not exist.')
        if image.region.name != region.name:
            raise cherrypy.HTTPError(409, 'The requested image is not within the requested region')
        if image.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Can only create a instance with a image in the following state: {0}'.format(
                ResourceState.Created.value))

        flavor: Flavor = Flavor.get(request.flavor_name)
        if flavor is None:
            raise cherrypy.HTTPError(404, 'A flavor with the requested name does not exist.')

        keypairs = []
        for keypair_name in request.keypair_names:
            keypair = Keypair.get(project, keypair_name)
            if keypair is None:
                raise cherrypy.HTTPError(404,
                                         'A keypair with the requested name of {0} does not exist.'.format(
                                             keypair_name))
            keypairs.append(keypair)

        # TODO: User inputs service account email instead of id
        # Only project service accounts are allowed
        if request.service_account_name is not None:
            service_account = ProjectServiceAccount.get(project, request.service_account_name)
            if service_account is None:
                raise cherrypy.HTTPError(404, 'A service account with the requested name of {0} does not exist.'.format(
                    request.service_account_name))
        else:
            service_account = ProjectServiceAccount.get(project, 'default')
            if service_account is None:
                raise cherrypy.HTTPError(500, 'Could not find a default service account to attach to the instance.')

        quota: ProjectQuota = ProjectQuota.get(project.name)
        used_vcpu = quota.used_vcpu + flavor.vcpus
        used_ram = quota.used_ram + flavor.ram
        requested_disk = flavor.disk
        if request.disk is not None:
            requested_disk = request.disk
        used_disk = quota.used_disk + requested_disk

        if quota.vcpu != -1:
            if used_vcpu > quota.vcpu:
                raise QuotaError("VCPU", flavor.vcpus, quota.used_vcpu, quota.vcpu)

        if quota.ram != -1:
            if used_ram > quota.ram:
                raise QuotaError("Ram", flavor.ram, quota.used_ram, quota.ram)

        if quota.disk != -1:
            if used_disk > quota.disk:
                raise QuotaError("Disk", requested_disk, quota.used_disk, quota.disk)

        quota.used_vcpu = used_vcpu
        quota.used_ram = used_ram
        quota.used_disk = used_disk
        quota.save()

        network_port = NetworkPort()
        network_port.name = str(uuid.uuid4())  # We don't care about the network port's name, just that it's unique
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
        if request.user_data is not None:
            if len(request.user_data) > 0:
                instance.user_data = request.user_data
        for k, v in request.tags.items():
            instance.add_tag(k, v)

        instance.flavor = flavor
        if request.disk is not None:
            instance.disk = request.disk
        if request.initial_volumes is not None:
            initial_volumes = []
            for initial_volume in request.initial_volumes:
                initial_volumes.append(initial_volume.to_native())
            instance.initial_volumes = initial_volumes

        instance.create()

        return ResponseInstance.from_database(instance)

    @Route(route='{instance_name}')
    @cherrypy.tools.model_params(cls=ParamsInstance)
    @cherrypy.tools.model_out(cls=ResponseInstance)
    @cherrypy.tools.resource_object(id_param="instance_name", cls=Instance)
    @cherrypy.tools.enforce_permission(permission_name="instances:get")
    def get(self, **_):
        """Get an instance
        ---
        get:
            description: Get an instance
            tags:
                - compute
                - instance
            responses:
                200:
                    description: The instance
        """
        return ResponseInstance.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListInstance)
    @cherrypy.tools.model_out_pagination(cls=ResponseInstance)
    @cherrypy.tools.enforce_permission(permission_name="instances:list")
    def list(self, image_name, region_name, zone_name, limit: int, marker: uuid.UUID):
        """List instances
        ---
        get:
            description: List instances
            tags:
                - compute
                - instance
            responses:
                200:
                    description: List of instances
        """
        kwargs = {
            'project': cherrypy.request.project,
            'label_selector': [],
        }

        if image_name is not None:
            image: Image = Image.get(cherrypy.request.project, image_name)
            if image is None:
                raise cherrypy.HTTPError(404, "An image with the requested name does not exist.")
            kwargs['label_selector'].append(IMAGE_LABEL + '=' + image.name)

        if region_name is not None:
            region: Region = Region.get(region_name)
            if region is None:
                raise cherrypy.HTTPError(404, "A region with the requested name does not exist.")
            kwargs['label_selector'].append(REGION_LABEL + '=' + region.name)

        if zone_name is not None:
            zone: Zone = Zone.get(zone_name)
            if zone is None:
                raise cherrypy.HTTPError(404, 'A zone with the requested name does not exist.')
            kwargs['label_selector'].append(ZONE_LABEL + '=' + zone.name)

        if len(kwargs['label_selector']) > 0:
            kwargs['label_selector'] = ",".join(kwargs['label_selector'])
        else:
            del kwargs['label_selector']

        return self.paginate(Instance, ResponseInstance, limit, marker, **kwargs)

    @Route(route='{instance_name}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsInstance)
    @cherrypy.tools.resource_object(id_param="instance_name", cls=Instance)
    @cherrypy.tools.enforce_permission(permission_name="instances:delete")
    def delete(self, **_):
        """Delete an instance
        ---
        delete:
            description: Delete an instance
            tags:
                - compute
                - instance
            responses:
                204:
                    description: Instance deleted
        """
        cherrypy.response.status = 204

        instance: Instance = cherrypy.request.resource_object
        if instance.task is not None and instance.state != ResourceState.Error:
            raise cherrypy.HTTPError(400, "Please wait for the current task to finish.")
        if instance.state == ResourceState.ToDelete or instance.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Instance is already being deleting")
        if instance.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Instance has already been deleted")

        instance.delete()

    @Route(route='{instance_name}/action/start', methods=[RequestMethods.PUT])
    @cherrypy.tools.model_params(cls=ParamsInstance)
    @cherrypy.tools.resource_object(id_param="instance_name", cls=Instance)
    @cherrypy.tools.enforce_permission(permission_name="instances:action:stop")
    def action_start(self, **_):
        """Start an instance
        ---
        put:
            description: Start an instance
            tags:
                - compute
                - instance
            responses:
                204:
                    description: Instance starting
        """
        cherrypy.response.status = 202

        instance: Instance = cherrypy.request.resource_object

        if instance.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Instance is not in the following state: ' + ResourceState.Created.value)
        if instance.task is not None:
            raise cherrypy.HTTPError(400, 'Please wait for the current task to finish.')
        if instance.power_state != VMPowerState.POWERED_OFF:
            raise cherrypy.HTTPError(400, 'Instance must be powered off.')

        instance.action_start()

    @Route(route='{instance_name}/action/stop', methods=[RequestMethods.PUT])
    @cherrypy.tools.model_params(cls=ParamsInstance)
    @cherrypy.tools.model_in(cls=RequestInstancePowerOffRestart)
    @cherrypy.tools.resource_object(id_param="instance_name", cls=Instance)
    @cherrypy.tools.enforce_permission(permission_name="instances:action:start")
    def action_stop(self, **_):
        """Stop an instance
        ---
        put:
            description: Stop an instance
            tags:
                - compute
                - instance
            requestBody:
                description: Stop options
            responses:
                204:
                    description: Instance stopping
        """
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

    @Route(route='{instance_name}/action/restart', methods=[RequestMethods.PUT])
    @cherrypy.tools.model_params(cls=ParamsInstance)
    @cherrypy.tools.model_in(cls=RequestInstancePowerOffRestart)
    @cherrypy.tools.resource_object(id_param="instance_name", cls=Instance)
    @cherrypy.tools.enforce_permission(permission_name="instances:action:restart")
    def action_restart(self, **_):
        """Restart an instance
        ---
        put:
            description: Restart an instance
            tags:
                - compute
                - instance
            requestBody:
                description: Restart options
            responses:
                204:
                    description: Instance restarting
        """
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

    @Route(route='{instance_name}/action/image', methods=[RequestMethods.POST])
    @cherrypy.tools.model_params(cls=ParamsInstance)
    @cherrypy.tools.model_in(cls=RequestInstanceImage)
    @cherrypy.tools.model_out(cls=ResponseImage)
    @cherrypy.tools.resource_object(id_param="instance_name", cls=Instance)
    @cherrypy.tools.enforce_permission(permission_name="instances:action:image")
    def action_image(self, **_):
        """Image an instance
        ---
        put:
            description: Image an instance
            tags:
                - compute
                - instance
            requestBody:
                description: Image to create
            responses:
                200:
                    description: The created image
        """
        project: Project = cherrypy.request.project
        request: RequestInstanceImage = cherrypy.request.model

        instance: Instance = cherrypy.request.resource_object

        if instance.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Instance is not in the following state: ' + ResourceState.Created.value)
        if instance.task is not None:
            raise cherrypy.HTTPError(400, 'Please wait for the current task to finish.')
        if instance.power_state != VMPowerState.POWERED_OFF:
            raise cherrypy.HTTPError(400, 'Instance must be powered off.')

        if Image.get(project, request.name) is not None:
            raise cherrypy.HTTPError(400, 'An image with the requested name already exists.')

        attached_volumes = Volume.list(project, label_selector=ATTACHED_TO_LABEL + "=" + str(instance.name))
        if len(attached_volumes) > 0:
            raise cherrypy.HTTPError(409, 'Cannot create an image while volumes are attached.')

        image = instance.action_image(request.name)

        return ResponseImage.from_database(image)
