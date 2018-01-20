from schematics import Model
from schematics.types import UUIDType, IntType, BooleanType

from deli.http.schematics.types import ArrowType, KubeName
from deli.kubernetes.resources.project import Project


class RequestCreateProject(Model):
    name = KubeName(required=True, min_length=3)


class ParamsProject(Model):
    project_id = UUIDType(required=True)


class ParamsListProject(Model):
    all = BooleanType(default=False)
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class ResponseProject(Model):
    id = UUIDType(required=True)
    name = KubeName(required=True, min_length=3)
    created_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, project: Project):
        project_model = cls()
        project_model.id = project.id
        project_model.name = project.name
        project_model.created_at = project.created_at

        return project_model
