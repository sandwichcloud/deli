import cherrypy
from ingredients_http.route import Route

from deli.counter.http.router import SandwichRouter


class AuthRouter(SandwichRouter):
    def __init__(self):
        super().__init__()
        self.drivers = {}

    def setup_routes(self, dispatcher: cherrypy.dispatch.RoutesDispatcher, uri_prefix: str):
        self.drivers = self.mount.auth_manager.drivers

        for _, driver in self.drivers.items():
            driver_router: SandwichRouter = driver.auth_router()
            driver_router.setup_routes(dispatcher, uri_prefix)

        super().setup_routes(dispatcher, uri_prefix)

    @Route(route='discover')
    @cherrypy.config(**{'tools.authentication.on': False})
    @cherrypy.tools.json_out()
    def discover(self):
        data = {
            "default": list(self.drivers.keys())[0]
        }

        for _, driver in self.drivers.items():
            data[driver.name] = driver.discover_options()

        return data
