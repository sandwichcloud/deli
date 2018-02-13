import uuid

import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route

from deli.counter.http.mounts.root.routes.v1.validation_models.images import RequestCreateImage, ResponseImage, \
    ParamsImage, ParamsListImage, ParamsImageMember, RequestAddMember, ResponseImageMember, RequestImageVisibility
from deli.counter.http.router import SandwichRouter
from deli.kubernetes.resources.const import REGION_LABEL, IMAGE_VISIBILITY_LABEL, \
    MEMBER_LABEL
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.image.model import Image, ImageVisibility
from deli.kubernetes.resources.v1alpha1.region.model import Region


class ImageRouter(SandwichRouter):
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

        image = Image.get_by_name(request.name, project=project)
        if image is not None:
            raise cherrypy.HTTPError(400, 'An image with the requested name already exists.')

        region = Region.get(request.region_id)
        if region is None:
            raise cherrypy.HTTPError(404, 'A region with the requested id does not exist.')

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

    @Route(route='{image_id}')
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsImage)
    @cherrypy.tools.model_out(cls=ResponseImage)
    @cherrypy.tools.resource_object(id_param="image_id", cls=Image)
    @cherrypy.tools.enforce_policy(policy_name="images:get")
    def get(self, **_):
        image: Image = cherrypy.request.resource_object

        if image.visibility == ImageVisibility.PRIVATE:
            if image.project_id != cherrypy.request.project.id:
                if image.is_member(cherrypy.request.project.id) is False:
                    raise cherrypy.HTTPError(404, "The resource could not be found.")

        return ResponseImage.from_database(image)

    @Route()
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsListImage)
    @cherrypy.tools.model_out_pagination(cls=ResponseImage)
    @cherrypy.tools.enforce_policy(policy_name="images:list")
    def list(self, region_id, visibility: ImageVisibility, limit: int, marker: uuid.UUID):
        kwargs = {
            'label_selector': []
        }

        if visibility == ImageVisibility.PRIVATE:
            kwargs['label_selector'].append(IMAGE_VISIBILITY_LABEL + '=' + ImageVisibility.PRIVATE.value)
            kwargs['label_selector'].append(MEMBER_LABEL + "/" + str(cherrypy.request.project.id) + "=1")
        else:
            kwargs['label_selector'].append(IMAGE_VISIBILITY_LABEL + '=' + ImageVisibility.PUBLIC.value)

        if region_id is not None:
            region: Region = Region.get(region_id)
            if region is None:
                raise cherrypy.HTTPError(404, "A region with the requested id does not exist.")

            kwargs['label_selector'].append(REGION_LABEL + '=' + region.id)

        kwargs['label_selector'] = ",".join(kwargs['label_selector'])

        return self.paginate(Image, ResponseImage, limit, marker, **kwargs)

    @Route(route='{image_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsImage)
    @cherrypy.tools.resource_object(id_param="image_id", cls=Image)
    @cherrypy.tools.enforce_policy(policy_name="images:delete")
    def delete(self, **_):
        cherrypy.response.status = 204
        image: Image = cherrypy.request.resource_object

        if image.project_id != cherrypy.request.project.id:
            raise cherrypy.HTTPError(404, "The resource could not be found.")
        if image.state == ResourceState.ToDelete or image.state == ResourceState.Deleting:
            raise cherrypy.HTTPError(400, "Image is already being deleting")
        if image.state == ResourceState.Deleted:
            raise cherrypy.HTTPError(400, "Image has already been deleted")
        if image.state not in [ResourceState.Created, ResourceState.Error]:
            raise cherrypy.HTTPError(400, 'Image cannot be deleted in the current state')

        image.delete()

    @Route(route='{image_id}/action/visibility', methods=[RequestMethods.PUT])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsImage)
    @cherrypy.tools.model_in(cls=RequestImageVisibility)
    @cherrypy.tools.resource_object(id_param="image_id", cls=Image)
    @cherrypy.tools.enforce_policy(policy_name="images:action:visibility")
    def action_visibility(self, **_):
        cherrypy.response.status = 204
        image: Image = cherrypy.request.resource_object
        request: RequestImageVisibility = cherrypy.request.model

        if image.project_id != cherrypy.request.project.id:
            raise cherrypy.HTTPError(404, "The resource could not be found.")

        if request.public:
            self.mount.enforce_policy("images:action:visibility:public")
            if image.visibility == ImageVisibility.PUBLIC:
                raise cherrypy.HTTPError(409, 'The requested image is already public')
        else:
            if image.visibility == ImageVisibility.PRIVATE:
                raise cherrypy.HTTPError(409, 'The requested image is already private')

        image.visibility = ImageVisibility.PUBLIC if request.public else ImageVisibility.PRIVATE
        image.save()

    @Route(route='{image_id}/members', methods=[RequestMethods.POST])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsImage)
    @cherrypy.tools.model_in(cls=RequestAddMember)
    @cherrypy.tools.resource_object(id_param="image_id", cls=Image)
    @cherrypy.tools.enforce_policy(policy_name="images:members:add")
    def add_member(self, **_):
        cherrypy.response.status = 204
        request: RequestAddMember = cherrypy.request.model
        image: Image = cherrypy.request.resource_object

        if image.project_id != cherrypy.request.project.id:
            raise cherrypy.HTTPError(404, "The resource could not be found.")

        if image.visibility == ImageVisibility.PUBLIC:
            raise cherrypy.HTTPError(409, 'Cannot add a member to a public image')

        project = Project.get(request.project_id)
        if project is None:
            raise cherrypy.HTTPError(404, 'A project with the requested id does not exist.')

        if image.project_id == project.id:
            raise cherrypy.HTTPError(409, 'Cannot add the owning project as a member.')

        if image.is_member(request.project_id):
            raise cherrypy.HTTPError(409, 'A project with the requested id is already a member.')

        image.add_member(request.project_id)
        image.save()

    @Route(route='{image_id}/members')
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsImage)
    @cherrypy.tools.model_out_pagination(cls=ResponseImageMember)
    @cherrypy.tools.resource_object(id_param="image_id", cls=Image)
    @cherrypy.tools.enforce_policy(policy_name="images:members:list")
    def list_members(self, **_):
        image: Image = cherrypy.request.resource_object

        if image.project_id != cherrypy.request.project.id:
            raise cherrypy.HTTPError(404, "The resource could not be found.")

        if image.visibility == ImageVisibility.PUBLIC:
            raise cherrypy.HTTPError(409, 'Cannot list members of a public image')

        members = []

        for member_id in image.member_ids():
            member = ResponseImageMember()
            member.project_id = member_id
            members.append(member)

        return members, False

    @Route(route='{image_id}/members/{project_id}', methods=[RequestMethods.DELETE])
    @cherrypy.tools.project_scope()
    @cherrypy.tools.model_params(cls=ParamsImageMember)
    @cherrypy.tools.resource_object(id_param="image_id", cls=Image)
    @cherrypy.tools.enforce_policy(policy_name="images:members:delete")
    def delete_member(self, project_id, **_):
        cherrypy.response.status = 204
        image: Image = cherrypy.request.resource_object

        if image.project_id != cherrypy.request.project.id:
            raise cherrypy.HTTPError(404, "The resource could not be found.")

        if image.visibility == ImageVisibility.PUBLIC:
            raise cherrypy.HTTPError(409, 'Cannot delete a member from a public image')

        project = Project.get(project_id)
        if project is None:
            raise cherrypy.HTTPError(404, 'A project with the requested id does not exist.')

        if image.is_member(project_id) is False:
            raise cherrypy.HTTPError(409, 'A project with the requested id is not a member.')

        image.remove_member(project_id)
        image.save()
