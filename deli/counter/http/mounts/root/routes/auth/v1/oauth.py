import arrow
import cherrypy
import requests
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from simple_settings import settings

from deli.counter.http.mounts.root.routes.auth.v1.validation_models.oauth import ResponseOAuthToken, RequestOAuthToken
from deli.counter.http.router import SandwichRouter


class AuthRouter(SandwichRouter):
    def __init__(self):
        super().__init__(uri_base='oauth')

    def get_token_url(self):
        r = requests.get(settings.OPENID_ISSUER_URL + ".well-known/openid-configuration")
        if r.status_code != 200:
            try:
                r.raise_for_status()
            except requests.exceptions.RequestException as e:
                self.logger.exception("Backend error while discovering OAuth configuration from provider")
                raise cherrypy.HTTPError(424,
                                         "Backend error while discovering OAuth configuration from provider: "
                                         + e.response.text)

        well_known_data = r.json()
        return well_known_data['token_endpoint']

    @Route(route='token', methods=[RequestMethods.POST])
    @cherrypy.config(**{'tools.authentication.on': False})
    @cherrypy.tools.model_in(cls=RequestOAuthToken)
    @cherrypy.tools.model_out(cls=ResponseOAuthToken)
    def token(self):  # Used to get token via API (username and password Auth Flow)
        """Auth to the API
        ---
        post:
            description: Auth to the API
            tags:
                - auth
            requestBody:
                description: User credentials
            responses:
                200:
                    description: An API Token
        """
        request: RequestOAuthToken = cherrypy.request.model

        r = requests.post(self.get_token_url(), json={
            'grant_type': 'password',
            'username': request.email,
            'password': request.password,
            'client_id': settings.OPENID_CLIENT_ID,
            'client_secret': settings.OPENID_CLIENT_SECRET,
            'scope': 'openid profile email'
        }, headers={'Accept': 'application/json'})

        if r.status_code == 403:
            raise cherrypy.HTTPError(403, 'Wrong email or password')
        elif r.status_code != 200:
            try:
                r.raise_for_status()
            except requests.exceptions.RequestException as e:
                self.logger.exception("Error while validating OAuth access token")
                raise cherrypy.HTTPError(424, "Backend error while talking with OAuth Provider: " + e.response.text)

        token_json = r.json()
        token_model = ResponseOAuthToken()
        token_model.access_token = token_json['id_token']
        token_model.expiry = arrow.now('UTC').shift(seconds=+token_json['expires_in'])
        return token_model
