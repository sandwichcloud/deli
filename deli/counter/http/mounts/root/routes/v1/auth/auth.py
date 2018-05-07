import cherrypy
from ingredients_http.route import Route

from deli.counter.auth.manager import DRIVERS
from deli.counter.http.router import SandwichRouter


class AuthRouter(SandwichRouter):
    def __init__(self):
        super().__init__()

    def setup_routes(self, dispatcher: cherrypy.dispatch.RoutesDispatcher, uri_prefix: str):
        for _, driver in DRIVERS.items():
            try:
                driver_router: SandwichRouter = driver.auth_router()
            except NotImplementedError:
                continue
            driver_router.mount = self.mount
            driver_router.setup_routes(dispatcher, uri_prefix)

        super().setup_routes(dispatcher, uri_prefix)

    @Route(route='discover')
    @cherrypy.config(**{'tools.authentication.on': False})
    @cherrypy.tools.json_out()
    def discover(self):
        data = {
            "default": list(DRIVERS.keys())[0]
        }

        for _, driver in DRIVERS.items():
            data[driver.name] = driver.discover_options()

        return data
