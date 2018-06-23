import re

from ingredients_http.schematics.types import ArrowType
from schematics import Model
from schematics.exceptions import ValidationError
from schematics.types import UUIDType, IntType, StringType

from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.project_quota.model import ProjectQuota


class ProjectName(StringType):

    def __init__(self, **kwargs):
        super().__init__(max_length=54, **kwargs)
        self.k8s_reg = re.compile('^(([A-Za-z0-9][-A-Za-z0-9_]*)?[A-Za-z0-9])?$')

    def validate_kube(self, value, context=None):
        if self.k8s_reg.match(value) is None:
            raise ValidationError(
                "must consist of lower case alphanumeric characters, the optional character '-', and must start and "
                "end with an alphanumeric character (e.g. 'example', regex used for validation "
                "is '(([A-Za-z0-9][-A-Za-z0-9_]*)?[A-Za-z0-9])?')")


class RequestCreateProject(Model):
    name = ProjectName(required=True, min_length=3)


class ParamsProject(Model):
    project_name = ProjectName(required=True)


class ParamsListProject(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class ResponseProject(Model):
    name = ProjectName(required=True, min_length=3)
    created_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, project: Project):
        project_model = cls()
        project_model.name = project.name
        project_model.created_at = project.created_at

        return project_model


class RequestProjectModifyQuota(Model):
    vcpu = IntType(required=True, min_value=-1)
    ram = IntType(required=True, min_value=-1)
    disk = IntType(required=True, min_value=-1)


class ResponseProjectQuota(Model):
    vcpu = IntType(required=True)
    ram = IntType(required=True)
    disk = IntType(required=True)
    used_vcpu = IntType(required=True)
    used_ram = IntType(required=True)
    used_disk = IntType(required=True)

    @classmethod
    def from_database(cls, quota: ProjectQuota):
        model = cls()
        model.vcpu = quota.vcpu
        model.ram = quota.ram
        model.disk = quota.disk
        model.used_vcpu = quota.used_vcpu
        model.used_ram = quota.used_ram
        model.used_disk = quota.used_disk

        return model
