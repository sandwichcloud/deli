from apispec import Path
from apispec.utils import load_operations_from_docstring
from schematics.models import FieldDescriptor

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
                spec.definition(model_cls.__name__, **parse_model(model_cls))

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
                            'schema': {
                                'type': 'string'
                            }
                        })

            if 'tools.model_out.cls' in cp_config:
                model_cls = cp_config['tools.model_out.cls']
                spec.definition(model_cls.__name__, **parse_model(model_cls))
                data['responses'][200]['content'] = {
                    'application/json': {
                        'schema': {'$ref': '#/components/schemas/' + model_cls.__name__}
                    }
                }

            if 'tools.model_out_pagination.cls' in cp_config:
                model_cls = cp_config['tools.model_out_pagination.cls']
                spec.definition(model_cls.__name__, **parse_model(model_cls))
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


def parse_model(model_cls):
    kwargs = {
        'properties': {},
        'extra_fields': {
            'type': 'object',
            'required': []
        }
    }
    for key, obj in model_cls.__dict__.items():
        if isinstance(obj, FieldDescriptor):
            kwargs['properties'][key] = {
                "type": "string"
            }
            if model_cls._fields[key].required:
                kwargs['extra_fields']['required'].append(key)

    if len(kwargs['extra_fields']['required']) == 0:
        del kwargs['extra_fields']['required']

    return kwargs
