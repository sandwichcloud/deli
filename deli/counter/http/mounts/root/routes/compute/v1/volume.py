import uuid

import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.http.mounts.root.errors.quota import QuotaError
from deli.counter.http.mounts.root.routes.compute.v1.validation_models.volume import RequestCreateVolume, \
    ResponseVolume, ParamsVolume, ParamsListVolume, RequestCloneVolume, RequestAttachVolume, RequestGrowVolume
from deli.counter.http.router import SandwichProjectRouter
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.instance.model import Instance
from deli.kubernetes.resources.v1alpha1.project_quota.model import ProjectQuota
from deli.kubernetes.resources.v1alpha1.volume.model import Volume, VolumeTask
from deli.kubernetes.resources.v1alpha1.zone.model import Zone


class VolumeRouter(SandwichProjectRouter):
    def __init__(self):
        super().__init__(uri_base='volumes')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateVolume)
    @cherrypy.tools.model_out(cls=ResponseVolume)
    @cherrypy.tools.enforce_policy(policy_name="volumes:create")
    def create(self):
        """Create a volume
        ---
        post:
            description: Create a volume
            tags:
                - compute
                - volume
            requestBody:
                description: Volume to create
            responses:
                200:
                    description: The created volume
        """
        request: RequestCreateVolume = cherrypy.request.model
        project: Project = cherrypy.request.project

        volume = Volume.get(project, request.name)
        if volume is not None:
            raise cherrypy.HTTPError(409, 'A volume with the requested name already exists.')

        zone = Zone.get(request.zone_name)
        if zone is None:
            raise cherrypy.HTTPError(404, 'A zone with the requested name does not exist.')
        if zone.state != ResourceState.Created:
            raise cherrypy.HTTPError(400,
                                     'Can only create a volume with a zone in the following state: %s'.format(
                                         ResourceState.Created))

        quota: ProjectQuota = ProjectQuota.get(project.name)
        used_disk = quota.used_disk + request.size
        if quota.disk != -1:
            if used_disk > quota.disk:
                raise QuotaError("Disk", request.size, quota.used_disk, quota.disk)

        quota.used_disk = used_disk
        quota.save()

        volume = Volume()
        volume.project = project
        volume.name = request.name
        volume.zone = zone
        volume.size = request.size
        volume.create()

        return ResponseVolume.from_database(volume)

    @Route(route='{volume_name}')
    @cherrypy.tools.model_params(cls=ParamsVolume)
    @cherrypy.tools.model_out(cls=ResponseVolume)
    @cherrypy.tools.resource_object(id_param="volume_name", cls=Volume)
    @cherrypy.tools.enforce_policy(policy_name="volumes:get")
    def get(self, **_):
        """Get a volume
        ---
        get:
            description: Get a volume
            tags:
                - compute
                - volume
            responses:
                200:
                    description: The volume
        """
        return ResponseVolume.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListVolume)
    @cherrypy.tools.model_out_pagination(cls=ResponseVolume)
    @cherrypy.tools.enforce_policy(policy_name="volumes:list")
    def list(self, limit: int, marker: uuid.UUID):
        """List volumes
        ---
        get:
            description: List volumes
            tags:
                - compute
                - volume
            responses:
                200:
                    description: List of volumes
        """
        kwargs = {
            'project': cherrypy.request.project,
            'label_selector': [],
        }
        if len(kwargs['label_selector']) > 0:
            kwargs['label_selector'] = ",".join(kwargs['label_selector'])
        else:
            del kwargs['label_selector']
        return self.paginate(Volume, ResponseVolume, limit, marker, **kwargs)

    @Route(route='{volume_name}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsVolume)
    @cherrypy.tools.resource_object(id_param="volume_name", cls=Volume)
    @cherrypy.tools.enforce_policy(policy_name="volumes:delete")
    def delete(self, **_):
        """Delete a volume
        ---
        delete:
            description: Delete a volume
            tags:
                - compute
                - volume
            responses:
                204:
                    description: Volume deleted
        """
        cherrypy.response.status = 204

        volume: Volume = cherrypy.request.resource_object
        if volume.task is not None and volume.state != ResourceState.Error:
            raise cherrypy.HTTPError(400, "Please wait for the current task to finish.")
        if volume.state == ResourceState.ToDelete or volume.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Volume is already being deleting")
        if volume.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Volume has already been deleted")

        if volume.attached_to_name is not None:
            raise cherrypy.HTTPError(409, 'Cannot delete when attached to an instance.')

        volume.delete()

    @Route(route='{volume_name}/action/attach', methods=[RequestMethods.POST])
    @cherrypy.tools.model_params(cls=ParamsVolume)
    @cherrypy.tools.model_in(cls=RequestAttachVolume)
    @cherrypy.tools.resource_object(id_param="volume_name", cls=Volume)
    @cherrypy.tools.enforce_policy(policy_name="volumes:action:attach")
    def action_attach(self, **_):
        """Attach a volume
        ---
        put:
            description: Attach a volume
            tags:
                - compute
                - volume
            requestBody:
                description: Attach options
            responses:
                204:
                    description: Volume attaching
        """
        request: RequestAttachVolume = cherrypy.request.model
        cherrypy.response.status = 204

        volume: Volume = cherrypy.request.resource_object
        if volume.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Volume is not in the following state: ' + ResourceState.Created.value)
        if volume.task is not None:
            raise cherrypy.HTTPError(400, "Please wait for the current task to finish.")

        if volume.attached_to_name is not None:
            raise cherrypy.HTTPError(409, 'Volume is already attached to an instance.')

        instance: Instance = Instance.get(cherrypy.request.project, request.instance_name)
        if instance is None:
            raise cherrypy.HTTPError(404, 'Could not find the requested instance.')
        if instance.state != ResourceState.Created:
            raise cherrypy.HTTPError(400,
                                     'The requested instance is not in the following state: ' +
                                     ResourceState.Created.value)
        if instance.region_name != volume.region_name:
            raise cherrypy.HTTPError(400, 'The requested instance is not in the same region as the volume.')
        if instance.zone_name != volume.zone_name:
            raise cherrypy.HTTPError(400, 'The requested instance is not in the same zone as the volume.')
        if instance.task is not None:
            raise cherrypy.HTTPError(400, 'Please wait for the current task on the instance to finish.')

        volume.attach(instance)
        volume.save()

    @Route(route='{volume_name}/action/detach', methods=[RequestMethods.PUT])
    @cherrypy.tools.model_params(cls=ParamsVolume)
    @cherrypy.tools.resource_object(id_param="volume_name", cls=Volume)
    @cherrypy.tools.enforce_policy(policy_name="volumes:action:detach")
    def action_detach(self, **_):
        """Detach a volume
        ---
        put:
            description: Detach a volume
            tags:
                - compute
                - volume
            responses:
                204:
                    description: Volume detaching
        """
        cherrypy.response.status = 204

        volume: Volume = cherrypy.request.resource_object
        if volume.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Volume is not in the following state: ' + ResourceState.Created.value)
        if volume.task is not None:
            raise cherrypy.HTTPError(400, "Please wait for the current task to finish.")

        if volume.attached_to_name is None:
            raise cherrypy.HTTPError(409, 'Volume is not attached to an instance.')

        volume.task = VolumeTask.DETACHING
        volume.save()

    @Route(route='{volume_name}/action/grow', methods=[RequestMethods.POST])
    @cherrypy.tools.model_params(cls=ParamsVolume)
    @cherrypy.tools.model_in(cls=RequestGrowVolume)
    @cherrypy.tools.resource_object(id_param="volume_name", cls=Volume)
    @cherrypy.tools.enforce_policy(policy_name="volumes:action:grow")
    def action_grow(self, **_):
        """Grow a volume
        ---
        put:
            description: Grow a volume
            tags:
                - compute
                - volume
            requestBody:
                description: Grow options
            responses:
                204:
                    description: Volume growing
        """
        project: Project = cherrypy.request.project
        request: RequestGrowVolume = cherrypy.request.model
        cherrypy.response.status = 204

        volume: Volume = cherrypy.request.resource_object
        if volume.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Volume is not in the following state: ' + ResourceState.Created.value)
        if volume.task is not None:
            raise cherrypy.HTTPError(400, "Please wait for the current task to finish.")

        if volume.attached_to_name is not None:
            raise cherrypy.HTTPError(409, 'Cannot grow while attached to an instance')

        if request.size <= volume.size:
            raise cherrypy.HTTPError(400, 'Size must be bigger than the current volume size.')

        quota: ProjectQuota = ProjectQuota.get(project.name)
        used_disk = quota.used_disk + request.size
        if quota.disk != -1:
            if used_disk > quota.disk:
                raise QuotaError("Disk", request.size, quota.used_disk, quota.disk)

        quota.used_disk = used_disk
        quota.save()

        volume.task = VolumeTask.GROWING
        volume.task_kwargs = {"size": request.size}
        volume.save()

    @Route(route='{volume_name}/action/clone', methods=[RequestMethods.POST])
    @cherrypy.tools.model_params(cls=ParamsVolume)
    @cherrypy.tools.model_in(cls=RequestCloneVolume)
    @cherrypy.tools.model_out(cls=ResponseVolume)
    @cherrypy.tools.resource_object(id_param="volume_name", cls=Volume)
    @cherrypy.tools.enforce_policy(policy_name="volumes:action:grow")
    def action_clone(self, **_):
        """Clone a volume
        ---
        put:
            description: Clone a volume
            tags:
                - compute
                - volume
            requestBody:
                description: Clone options
            responses:
                200:
                    description: The created volume
        """
        request: RequestCloneVolume = cherrypy.request.model
        project: Project = cherrypy.request.project
        volume: Volume = cherrypy.request.resource_object
        if volume.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Volume is not in the following state: ' + ResourceState.Created.value)
        if volume.task is not None:
            raise cherrypy.HTTPError(400, "Please wait for the current task to finish.")
        if volume.attached_to_name is not None:
            raise cherrypy.HTTPError(409, 'Cannot clone while attached to an instance')
        if Volume.get(cherrypy.request.project, request.name) is not None:
            raise cherrypy.HTTPError(409, 'A volume with the requested name already exists.')

        quota: ProjectQuota = ProjectQuota.get(project.name)
        used_disk = quota.used_disk + volume.size
        if quota.disk != -1:
            if used_disk > quota.disk:
                raise QuotaError("Disk", volume.size, quota.used_disk, quota.disk)

        quota.used_disk = used_disk
        quota.save()

        new_volume = Volume()
        new_volume.project = volume.project
        new_volume.name = request.name
        new_volume.zone = volume.zone
        new_volume.size = volume.size
        new_volume.cloned_from = volume
        new_volume.create()

        volume.task = VolumeTask.CLONING
        volume.task_kwargs = {'volume_name': str(new_volume.name)}
        volume.save()

        return ResponseVolume.from_database(new_volume)
