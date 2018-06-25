import re

from ingredients_http.schematics.types import KubeName, ArrowType
from schematics import Model
from schematics.exceptions import ValidationError
from schematics.types import ListType, ModelType, StringType

from deli.kubernetes.resources.v1alpha1.iam_policy.model import IAMPolicy


class BindingMemberType(StringType):
    MESSAGES = {
        'split': "Member must be in the following format: 'serviceAccount/user/group:{emailId}'",
        'kind': "Member kind must be serviceAccount, user or group",
        'email': "Not a well-formed email address.",
        'user-invalid': "sandwich.local email Ids cannot be used for a user",
        'group-invalid': 'group email must have the domain of group.system.sandwich.local',
        'sa-invalid':
            "service account email domain must match the following regex '^service-account\.[a-z]+\.sandwich\.local$'"
    }

    EMAIL_REGEX = re.compile(r"""^(
        ( ( [%(atext)s]+ (\.[%(atext)s]+)* ) | ("( [%(qtext)s\s] | \\[%(vchar)s\s] )*") )
        @((?!-)[A-Z0-9-]{1,63}(?<!-)\.)+[A-Z]{2,63})$"""
                             % {
                                 'atext': '-A-Z0-9!#$%&\'*+/=?^_`{|}~',
                                 'qtext': '\x21\x23-\x5B\\\x5D-\x7E',
                                 'vchar': '\x21-\x7E'
                             },
                             re.I + re.X)

    SA_DOMAIN_REGEX = re.compile("^service-account\.[a-z]+\.sandwich\.local$")

    def validate_member(self, value, context=None):
        if ':' not in value:
            raise ValidationError(self.MESSAGES['split'])
        kind, email, *junk = value.split(":")

        if len(junk) > 0:
            raise ValidationError(self.MESSAGES['split'])

        if kind not in ['serviceAccount', 'user', 'group']:
            raise ValidationError(self.MESSAGES['kind'])

        if not self.EMAIL_REGEX.match(email):
            raise ValidationError(self.MESSAGES['email'])

        domain = email.split('@')[1]

        if kind == 'user':
            if email.endswith('sandwich.local'):
                raise ValidationError(self.MESSAGES['user-invalid'])

        if kind == 'group':
            if domain != 'group.system.sandwich.local':
                raise ValidationError(self.MESSAGES['group-invalid'])

        if kind == 'serviceAccount':
            if not self.SA_DOMAIN_REGEX.match(domain):
                raise ValidationError(self.MESSAGES['sa-invalid'])


class PolicyBinding(Model):
    role = KubeName(required=True)
    members = ListType(BindingMemberType, required=True)

    def validate_members(self, data, value):
        for member in value:
            if value.count(member) > 1:
                raise ValidationError(member + " appears multiple times in the binding")

        return value


class ResponsePolicy(Model):
    resource_version = StringType(required=True)
    bindings = ListType(ModelType(PolicyBinding), required=True)
    created_at = ArrowType(required=True)
    updated_at = ArrowType(required=True)

    @classmethod
    def from_database(cls, policy: IAMPolicy):
        model = cls()
        model.resource_version = policy.resource_version

        model.bindings = []

        for binding in policy.bindings:
            binding_model = PolicyBinding()
            binding_model.role = binding['role']
            binding_model.members = binding['members']
            model.bindings.append(binding_model)

        model.created_at = policy.created_at
        model.updated_at = policy.updated_at
        return model


class RequestSetPolicy(Model):
    resource_version = StringType(required=True)
    bindings = ListType(ModelType(PolicyBinding), required=True)
