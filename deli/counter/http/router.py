import inspect
from typing import Callable, List

import cherrypy
from ingredients_http.request_methods import RequestMethods
from ingredients_http.router import Router


class SandwichRouter(Router):
    def paginate(self, db_cls, response_cls, limit, marker, **kwargs):
        resp_models = []

        for obj in db_cls.list(**kwargs):
            resp_models.append(response_cls.from_database(obj))

        return resp_models, False

    def on_register(self, uri: str, action: Callable, methods: List[RequestMethods]):
        self.mount.api_spec.add_path(path=uri, router=self, func=action)


class SandwichSystemRouter(SandwichRouter):

    def __init__(self, uri_base=None):
        if uri_base is None:
            uri_base = 'system'
        else:
            uri_base = 'system/' + uri_base
        super().__init__(uri_base=uri_base)


class SandwichProjectRouter(SandwichRouter):

    def __init__(self, uri_base=None):
        if uri_base is None:
            uri_base = 'projects/{project_name}'
        else:
            uri_base = 'projects/{project_name}/' + uri_base
        super().__init__(uri_base=uri_base)

    def setup_routes(self, dispatcher: cherrypy.dispatch.RoutesDispatcher, uri_prefix: str):
        for member in [getattr(self, attr) for attr in dir(self)]:
            if inspect.ismethod(member) and hasattr(member, '_route'):
                # Enable project scope checking
                self.__class__.__dict__[member.__name__]._cp_config['tools.project_scope.on'] = True
                self.__class__.__dict__[member.__name__]._cp_config['tools.project_scope.delete_param'] = True

        super().setup_routes(dispatcher, uri_prefix)
