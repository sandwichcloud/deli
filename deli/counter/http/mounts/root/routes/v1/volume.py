import uuid

import cherrypy

from deli.counter.http.mounts.root.routes.v1.errors.quota import QuotaError
from deli.counter.http.mounts.root.routes.v1.validation_models.volume import RequestCreateVolume, ResponseVolume, \
    ParamsVolume, ParamsListVolume, RequestCloneVolume, RequestAttachVolume, RequestGrowVolume
from deli.http.request_methods import RequestMethods
from deli.http.route import Route
from deli.http.router import Router
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.instance.model import Instance
from deli.kubernetes.resources.v1alpha1.project_quota.model import ProjectQuota
from deli.kubernetes.resources.v1alpha1.volume.model import Volume, VolumeTask
from deli.kubernetes.resources.v1alpha1.zone.model import Zone


class VolumeRouter(Router):
    def __init__(self):
        super().__init__(uri_base='volumes')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_in(cls=RequestCreateVolume)
    @cherrypy.tools.model_out(cls=ResponseVolume)
    @cherrypy.tools.enforce_policy(policy_name="volumes:create")
    def create(self):
        request: RequestCreateVolume = cherrypy.request.model
        project: Project = cherrypy.request.project

        volume = Volume.get_by_name(project, request.name)
        if volume is not None:
            raise cherrypy.HTTPError(409, 'A volume with the requested name already exists.')

        zone = Zone.get(request.zone_id)
        if zone is None:
            raise cherrypy.HTTPError(404, 'A zone with the requested id does not exist.')
        if zone.state != ResourceState.Created:
            raise cherrypy.HTTPError(400,
                                     'Can only create a volume with a zone in the following state: %s'.format(
                                         ResourceState.Created))

        quota: ProjectQuota = ProjectQuota.list(project)[0]
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

    @Route(route='{volume_id}')
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsVolume)
    @cherrypy.tools.model_out(cls=ResponseVolume)
    @cherrypy.tools.resource_object(id_param="volume_id", cls=Volume)
    @cherrypy.tools.enforce_policy(policy_name="volumes:get")
    def get(self, **_):
        return ResponseVolume.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsListVolume)
    @cherrypy.tools.model_out_pagination(cls=ResponseVolume)
    @cherrypy.tools.enforce_policy(policy_name="volumes:list")
    def list(self, limit: int, marker: uuid.UUID):
        kwargs = {
            'project': cherrypy.request.project,
            'label_selector': [],
        }
        if len(kwargs['label_selector']) > 0:
            kwargs['label_selector'] = ",".join(kwargs['label_selector'])
        else:
            del kwargs['label_selector']
        return self.paginate(Volume, ResponseVolume, limit, marker, **kwargs)

    @Route(route='{volume_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsVolume)
    @cherrypy.tools.resource_object(id_param="volume_id", cls=Volume)
    @cherrypy.tools.enforce_policy(policy_name="volumes:delete")
    def delete(self, **_):
        cherrypy.response.status = 204

        volume: Volume = cherrypy.request.resource_object
        if volume.task is not None:
            raise cherrypy.HTTPError(400, "Please wait for the current task to finish.")
        if volume.state == ResourceState.ToDelete or volume.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Volume is already being deleting")
        if volume.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Volume has already been deleted")

        if volume.attached_to_id is not None:
            raise cherrypy.HTTPError(409, 'Cannot delete when attached to an instance.')

        volume.delete()

    @Route(route='{volume_id}/action/attach', methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsVolume)
    @cherrypy.tools.model_in(cls=RequestAttachVolume)
    @cherrypy.tools.resource_object(id_param="volume_id", cls=Volume)
    @cherrypy.tools.enforce_policy(policy_name="volumes:action:attach")
    def action_attach(self, **_):
        request: RequestAttachVolume = cherrypy.request.model
        cherrypy.response.status = 204

        volume: Volume = cherrypy.request.resource_object
        if volume.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Volume is not in the following state: ' + ResourceState.Created.value)
        if volume.task is not None:
            raise cherrypy.HTTPError(400, "Please wait for the current task to finish.")

        if volume.attached_to_id is not None:
            raise cherrypy.HTTPError(409, 'Volume is already attached to an instance.')

        instance: Instance = Instance.get(cherrypy.request.project, request.instance_id)
        if instance is None:
            raise cherrypy.HTTPError(404, 'Could not find the requested instance.')
        if instance.state != ResourceState.Created:
            raise cherrypy.HTTPError(400,
                                     'The requested instance is not in the following state: ' +
                                     ResourceState.Created.value)
        if instance.region_id != volume.region_id:
            raise cherrypy.HTTPError(400, 'The requested instance is not in the same region as the volume.')
        if instance.zone_id != volume.zone_id:
            raise cherrypy.HTTPError(400, 'The requested instance is not in the same zone as the volume.')

        volume.task = VolumeTask.ATTACHING
        volume.attached_to = instance
        volume.save()

    @Route(route='{volume_id}/action/detach', methods=[RequestMethods.PUT])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsVolume)
    @cherrypy.tools.resource_object(id_param="volume_id", cls=Volume)
    @cherrypy.tools.enforce_policy(policy_name="volumes:action:detach")
    def action_detach(self, **_):
        cherrypy.response.status = 204

        volume: Volume = cherrypy.request.resource_object
        if volume.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Volume is not in the following state: ' + ResourceState.Created.value)
        if volume.task is not None:
            raise cherrypy.HTTPError(400, "Please wait for the current task to finish.")

        if volume.attached_to_id is None:
            raise cherrypy.HTTPError(409, 'Volume is not attached to an instance.')

        volume.task = VolumeTask.DETACHING
        volume.save()

    @Route(route='{volume_id}/action/grow', methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsVolume)
    @cherrypy.tools.model_in(cls=RequestGrowVolume)
    @cherrypy.tools.resource_object(id_param="volume_id", cls=Volume)
    @cherrypy.tools.enforce_policy(policy_name="volumes:action:grow")
    def action_grow(self, **_):
        project: Project = cherrypy.request.project
        request: RequestGrowVolume = cherrypy.request.model
        cherrypy.response.status = 204

        volume: Volume = cherrypy.request.resource_object
        if volume.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Volume is not in the following state: ' + ResourceState.Created.value)
        if volume.task is not None:
            raise cherrypy.HTTPError(400, "Please wait for the current task to finish.")

        if volume.attached_to_id is not None:
            raise cherrypy.HTTPError(409, 'Cannot grow while attached to an instance')

        if request.size <= volume.size:
            raise cherrypy.HTTPError(400, 'Size must be bigger than the current volume size.')

        quota: ProjectQuota = ProjectQuota.list(project)[0]
        used_disk = quota.used_disk + request.size
        if quota.disk != -1:
            if used_disk > quota.disk:
                raise QuotaError("Disk", request.size, quota.used_disk, quota.disk)

        quota.used_disk = used_disk
        quota.save()

        volume.task = VolumeTask.GROWING
        volume.task_kwargs = {"size": request.size}
        volume.save()

    @Route(route='{volume_id}/action/clone', methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsVolume)
    @cherrypy.tools.model_in(cls=RequestCloneVolume)
    @cherrypy.tools.model_out(cls=ResponseVolume)
    @cherrypy.tools.resource_object(id_param="volume_id", cls=Volume)
    @cherrypy.tools.enforce_policy(policy_name="volumes:action:grow")
    def action_clone(self, **_):
        request: RequestCloneVolume = cherrypy.request.model
        volume: Volume = cherrypy.request.resource_object
        if volume.state != ResourceState.Created:
            raise cherrypy.HTTPError(400, 'Volume is not in the following state: ' + ResourceState.Created.value)
        if volume.task is not None:
            raise cherrypy.HTTPError(400, "Please wait for the current task to finish.")
        if volume.attached_to_id is not None:
            raise cherrypy.HTTPError(409, 'Cannot clone while attached to an instance')
        if Volume.get_by_name(cherrypy.request.project, request.name) is not None:
            raise cherrypy.HTTPError(409, 'A volume with the requested name already exists.')

        new_volume = Volume()
        new_volume.project = volume.project
        new_volume.name = request.name
        new_volume.zone = volume.zone
        new_volume.size = volume.size
        new_volume.cloned_from = volume
        new_volume.create()

        volume.task = VolumeTask.CLONING
        volume.task_kwargs = {'volume_id': str(new_volume.id)}
        volume.save()

        return ResponseVolume.from_database(new_volume)
