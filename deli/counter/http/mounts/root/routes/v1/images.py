import uuid

import cherrypy

from deli.counter.http.mounts.root.routes.v1.validation_models.images import RequestCreateImage, ResponseImage, \
    ParamsImage, ParamsListImage
from deli.http.request_methods import RequestMethods
from deli.http.route import Route
from deli.http.router import Router
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.image.model import Image
from deli.kubernetes.resources.v1alpha1.region.model import Region


class ImageRouter(Router):
    def __init__(self):
        super().__init__(uri_base='images')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_in(cls=RequestCreateImage)
    @cherrypy.tools.model_out(cls=ResponseImage)
    @cherrypy.tools.enforce_policy(policy_name="images:create")
    def create(self):
        request: RequestCreateImage = cherrypy.request.model
        project: Project = cherrypy.request.project

        image = Image.get_by_name(project, request.name)
        if image is not None:
            raise cherrypy.HTTPError(400, 'An image with the requested name already exists.')

        region = Region.get(request.region_id)
        if region is None:
            raise cherrypy.HTTPError(404, 'A region with the requested id does not exist.')

        if region.state != ResourceState.Created:
            raise cherrypy.HTTPError(409, 'Can only create a network with a region in the following state: %s'.format(
                ResourceState.Created))

        # TODO: check duplicate file name

        image = Image()
        image.name = request.name
        image.file_name = request.file_name
        image.project = project
        image.region = region
        image.create()

        return ResponseImage.from_database(image)

    @Route(route='{image_id}')
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsImage)
    @cherrypy.tools.model_out(cls=ResponseImage)
    @cherrypy.tools.resource_object(id_param="image_id", cls=Image)
    @cherrypy.tools.enforce_policy(policy_name="images:get")
    def get(self, **_):
        return ResponseImage.from_database(cherrypy.request.resource_object)

    @Route()
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsListImage)
    @cherrypy.tools.model_out_pagination(cls=ResponseImage)
    @cherrypy.tools.enforce_policy(policy_name="images:list")
    def list(self, region_id, limit: int, marker: uuid.UUID):
        kwargs = {
            'project': cherrypy.request.project
        }
        if region_id is not None:
            region: Region = Region.get(region_id)
            if region is None:
                raise cherrypy.HTTPError(404, "A region with the requested id does not exist.")

            kwargs['label_selector'] = 'sandwichcloud.io/region=' + region.id

        return self.paginate(Image, ResponseImage, limit, marker, **kwargs)

    @Route(route='{image_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsImage)
    @cherrypy.tools.resource_object(id_param="image_id", cls=Image)
    @cherrypy.tools.enforce_policy(policy_name="images:delete")
    def delete(self, **_):
        cherrypy.response.status = 204
        image: Image = cherrypy.request.resource_object

        if image.state == ResourceState.ToDelete or image.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Image is already being deleting")

        if image.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Image has already been deleted")

        image.delete()
