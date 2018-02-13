import cherrypy
from ingredients_http.route import Route
from kubernetes import client

from deli.counter.http.router import SandwichRouter


class HealthRouter(SandwichRouter):
    def __init__(self):
        super().__init__(uri_base='health')

    @Route()
    @cherrypy.config(**{'tools.authentication.on': False})
    @cherrypy.tools.json_out()
    def get(self):
        data = {
            'kubernetes_version': None,
            'auth': {}
        }

        try:
            version = client.VersionApi().get_code()
            data['kubernetes_version'] = version.git_version
        except Exception:
            cherrypy.response.status = 503
            self.logger.exception("Error getting kubernetes version")

        for driver in self.mount.auth_manager.drivers.values():
            driver_health = driver.health()
            if driver_health['healthy'] is False:
                cherrypy.response.status = 503
            data['auth'][driver.name] = driver_health

        return data
