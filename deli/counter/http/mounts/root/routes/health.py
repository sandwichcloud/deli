import cherrypy
from kubernetes import client

from deli.http.route import Route
from deli.http.router import Router


class HealthRouter(Router):
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
