from apispec import Path
from apispec.utils import load_operations_from_docstring
from ingredients_http.schematics.types import KubeName, ArrowType, IPv4AddressType, IPv4NetworkType, EnumType, \
    KubeString
from schematics.models import FieldDescriptor
from schematics.types import IntType, StringType, BooleanType, UUIDType, EmailType, ListType, DictType, ModelType

from deli.counter.http.mounts.root.routes.iam.v1.validation_models.policy import BindingMemberType
from deli.counter.http.mounts.root.routes.iam.v1.validation_models.projects import ProjectName
from deli.counter.http.router import SandwichProjectRouter


def docstring_path_helper(spec, path, router, func, **kwargs):
    operations = load_operations_from_docstring(func.__doc__)

    cp_config = func._cp_config

    if operations is not None:
        for method, data in operations.items():

            if cp_config.get('tools.authentication.on', True):
                data['security'] = [
                    {'Bearer': []}
                ]

            if 'tools.model_in.cls' in cp_config:
                model_cls = cp_config['tools.model_in.cls']
                spec.definition(model_cls.__name__, **parse_model(spec, model_cls))

                data['requestBody']['required'] = True
                data['requestBody']['content'] = {
                    'application/json': {
                        'schema': {'$ref': '#/components/schemas/' + model_cls.__name__}
                    }
                }

            if 'tools.model_params.cls' in cp_config:
                model_cls = cp_config['tools.model_params.cls']
                data['parameters'] = data.get('parameters', [])

                # In query vs in path
                for key, obj in model_cls.__dict__.items():
                    inn = 'query'
                    if '{' + key + '}' in path.path:
                        inn = 'path'
                    if isinstance(obj, FieldDescriptor):
                        data['parameters'].append({
                            'name': key,
                            'in': inn,
                            'required': model_cls._fields[key].required,
                            'schema': parse_model_type(spec, model_cls._fields[key])
                        })

            if 'tools.model_out.cls' in cp_config:
                model_cls = cp_config['tools.model_out.cls']
                spec.definition(model_cls.__name__, **parse_model(spec, model_cls))
                data['responses'][200]['content'] = {
                    'application/json': {
                        'schema': {'$ref': '#/components/schemas/' + model_cls.__name__}
                    }
                }

            if 'tools.model_out_pagination.cls' in cp_config:
                model_cls = cp_config['tools.model_out_pagination.cls']
                spec.definition(model_cls.__name__, **parse_model(spec, model_cls))
                data['responses'][200]['content'] = {
                    'application/json': {
                        'schema': {
                            'type': 'array',
                            'items': {'$ref': '#/components/schemas/' + model_cls.__name__}
                        }
                    }
                }

            if isinstance(router, SandwichProjectRouter):
                data['parameters'] = data.get('parameters', [])
                data['parameters'].append({
                    'name': 'project_name',
                    'in': 'path',
                    'required': True,
                    'schema': {
                        'type': 'string'
                    }
                })

            if 'tools.enforce_permission.permission_name' in cp_config:
                data['x-required-permission'] = cp_config['tools.enforce_permission.permission_name']

    return Path(path=path.path, operations=operations)


def setup(spec):
    spec.register_path_helper(docstring_path_helper)


def parse_model(spec, model_cls):
    kwargs = {
        'properties': {},
        'extra_fields': {
            'type': 'object',
            'required': []
        }
    }
    for key, obj in model_cls.__dict__.items():
        if isinstance(obj, FieldDescriptor):
            kwargs['properties'][key] = parse_model_type(spec, model_cls._fields[key])
            if model_cls._fields[key].required:
                kwargs['extra_fields']['required'].append(key)

    if len(kwargs['extra_fields']['required']) == 0:
        del kwargs['extra_fields']['required']

    return kwargs


def parse_model_type(spec, model_type):
    swagger_types = {
        StringType: 'string',
        KubeName: 'string',
        KubeString: 'string',
        ProjectName: 'string',
        UUIDType: 'string',
        EmailType: 'string',
        EnumType: 'string',
        IPv4AddressType: 'string',
        IPv4NetworkType: 'string',
        ArrowType: 'string',
        BindingMemberType: 'string',
        IntType: 'integer',
        BooleanType: 'boolean',
        ListType: 'array',
        DictType: 'object',
        ModelType: 'object',
    }

    data = {
        # Find the swagger type, if not found default to string
        # It would be nice to have complex types like uuid, emails, ect...
        # But swagger doesn't support it
        "type": swagger_types.get(model_type.__class__, "string")
    }

    if model_type.__class__ == EnumType:
        data['enum'] = [x.value for x in model_type.enum_class]

    if model_type.__class__ == ListType:
        if model_type.field.__class__ == ModelType:
            spec.definition(model_type.field.model_class.__name__, **parse_model(spec, model_type.field.model_class))
            data['items'] = {
                '$ref': '#/components/schemas/' + model_type.field.model_class.__name__
            }
        else:
            data['items'] = parse_model_type(spec, model_type.field)

    if model_type.__class__ == DictType:
        data['additionalProperties'] = parse_model_type(spec, model_type.field)

    if model_type.__class__ == ModelType:
        spec.definition(model_type.model_class.__name__, **parse_model(spec, model_type.model_class))
        data['additionalProperties'] = {
            '$ref': '#/components/schemas/' + model_type.model_class.__name__
        }

    return data
