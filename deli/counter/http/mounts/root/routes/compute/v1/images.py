import uuid

import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.http.mounts.root.routes.compute.v1.validation_models.images import RequestCreateImage, \
    ResponseImage, ParamsImage, ParamsListImage
from deli.counter.http.router import SandwichProjectRouter
from deli.kubernetes.resources.const import REGION_LABEL
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.image.model import Image, ImageVisibility
from deli.kubernetes.resources.v1alpha1.region.model import Region


class ImageRouter(SandwichProjectRouter):
    def __init__(self):
        super().__init__(uri_base='images')

    @Route(methods=[RequestMethods.POST])
    @cherrypy.tools.model_in(cls=RequestCreateImage)
    @cherrypy.tools.model_out(cls=ResponseImage)
    @cherrypy.tools.enforce_permission(permission_name="images:create")
    def create(self):
        """Create an image
        ---
        post:
            description: Create an image
            tags:
                - compute
                - image
            requestBody:
                description: Image to create
            responses:
                200:
                    description: The created image
        """
        request: RequestCreateImage = cherrypy.request.model
        project: Project = cherrypy.request.project

        image = Image.get(project, request.name)
        if image is not None:
            raise cherrypy.HTTPError(400, 'An image with the requested name already exists.')

        region = Region.get(request.region_name)
        if region is None:
            raise cherrypy.HTTPError(404, 'A region with the requested name does not exist.')

        if region.state != ResourceState.Created:
            raise cherrypy.HTTPError(409, 'Can only create a image with a region in the following state: %s'.format(
                ResourceState.Created))

        # TODO: check duplicate file name

        image = Image()
        image.name = request.name
        image.file_name = request.file_name
        image.project = project
        image.region = region
        image.create()

        return ResponseImage.from_database(image)

    @Route(route='{image_name}')
    @cherrypy.tools.model_params(cls=ParamsImage)
    @cherrypy.tools.model_out(cls=ResponseImage)
    @cherrypy.tools.resource_object(id_param="image_name", cls=Image)
    @cherrypy.tools.enforce_permission(permission_name="images:get")
    def get(self, **_):
        """Get an image
        ---
        get:
            description: Get an image
            tags:
                - compute
                - image
            responses:
                200:
                    description: The image
        """
        image: Image = cherrypy.request.resource_object

        return ResponseImage.from_database(image)

    @Route()
    @cherrypy.tools.model_params(cls=ParamsListImage)
    @cherrypy.tools.model_out_pagination(cls=ResponseImage)
    @cherrypy.tools.enforce_permission(permission_name="images:list")
    def list(self, region_name, visibility: ImageVisibility, limit: int, marker: uuid.UUID):
        """List images
        ---
        get:
            description: List images
            tags:
                - compute
                - image
            responses:
                200:
                    description: List of images
        """
        kwargs = {
            'project': cherrypy.request.project,
            'label_selector': []
        }

        if region_name is not None:
            region: Region = Region.get(region_name)
            if region is None:
                raise cherrypy.HTTPError(404, "A region with the requested name does not exist.")

            kwargs['label_selector'].append(REGION_LABEL + '=' + region.name)

        kwargs['label_selector'] = ",".join(kwargs['label_selector'])

        return self.paginate(Image, ResponseImage, limit, marker, **kwargs)

    @Route(route='{image_name}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.model_params(cls=ParamsImage)
    @cherrypy.tools.resource_object(id_param="image_name", cls=Image)
    @cherrypy.tools.enforce_permission(permission_name="images:delete")
    def delete(self, **_):
        """Delete an image
        ---
        delete:
            description: Delete an image
            tags:
                - compute
                - image
            responses:
                204:
                    description: Image deleted
        """
        cherrypy.response.status = 204
        image: Image = cherrypy.request.resource_object

        if image.project_name != cherrypy.request.project.name:
            raise cherrypy.HTTPError(404, "The resource could not be found.")
        if image.state == ResourceState.ToDelete or image.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Image is already being deleting")
        if image.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Image has already been deleted")
        if image.state not in [ResourceState.Created, ResourceState.Error]:
            raise cherrypy.HTTPError(400, 'Image cannot be deleted in the current state')

        image.delete()
