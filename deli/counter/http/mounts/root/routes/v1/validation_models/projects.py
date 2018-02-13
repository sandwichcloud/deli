from ingredients_http.schematics.types import KubeName, ArrowType
from schematics import Model
from schematics.types import UUIDType, IntType, BooleanType, ListType, StringType

from deli.kubernetes.resources.project import Project
from deli.kubernetes.resources.v1alpha1.project_member.model import ProjectMember
from deli.kubernetes.resources.v1alpha1.project_quota.model import ProjectQuota


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


class RequestProjectAddMember(Model):
    username = StringType(required=True)
    driver = StringType(required=True, choices=['github', 'database'])


class ParamsProjectMember(Model):
    member_id = UUIDType(required=True)


class ParamsListProjectMember(Model):
    limit = IntType(default=100, max_value=100, min_value=1)
    marker = UUIDType()


class RequestProjectUpdateMember(Model):
    roles = ListType(UUIDType, required=True, min_size=1)


class ResponseProjectMember(Model):
    id = UUIDType(required=True)
    username = StringType(required=True)
    driver = StringType(required=True)
    roles = ListType(UUIDType, default=list)
    created_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, project_member: ProjectMember):
        model = cls()
        model.id = project_member.id
        model.username = project_member.username
        model.driver = project_member.driver
        model.roles = project_member.roles
        model.created_at = project_member.created_at

        return model
