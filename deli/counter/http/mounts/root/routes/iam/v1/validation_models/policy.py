from ingredients_http.schematics.types import KubeName
from schematics import Model
from schematics.types import ListType, ModelType, StringType

from deli.kubernetes.resources.v1alpha1.iam_policy.model import IAMPolicy


class PolicyBinding(Model):
    role = KubeName(required=True)
    members = ListType(StringType)


class ResponsePolicy(Model):
    resource_version = StringType(required=True)
    bindings = ListType(ModelType(PolicyBinding), required=True)

    @classmethod
    def from_database(cls, policy: IAMPolicy):
        model = cls()
        model.resource_version = policy.resource_version

        model.bindings = []

        for binding in policy.bindings:
            binding_model = PolicyBinding()
            binding_model.role = binding['role']
            binding_model.members = binding_model['members']
            model.bindings.append(binding_model)

        return model


class RequestSetPolicy(Model):
    resource_version = StringType(required=True)
    bindings = ListType(ModelType(PolicyBinding), required=True)
