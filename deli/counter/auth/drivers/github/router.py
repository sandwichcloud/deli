import arrow
import cherrypy
import github
import github.AuthenticatedUser
import requests
import requests.exceptions
from github.GithubException import TwoFactorException, GithubException, BadCredentialsException
from ingredients_http.request_methods import RequestMethods
from ingredients_http.route import Route
from simple_settings import settings
from sqlalchemy_utils.types.json import json

from deli.counter.auth.validation_models.github import RequestGithubAuthorization, RequestGithubToken
from deli.counter.http.mounts.root.routes.v1.auth.validation_models.tokens import ResponseOAuthToken
from deli.counter.http.router import SandwichRouter


class GithubAuthRouter(SandwichRouter):
    def __init__(self, driver):
        super().__init__(uri_base='github')
        self.driver = driver

    def generate_token(self, token_github_client):
        github_user = token_github_client.get_user()
        if self.driver.check_in_org(github_user) is False:
            raise cherrypy.HTTPError(403, "User not a member of GitHub organization: '" + settings.GITHUB_ORG + "'")

        expiry = arrow.now().shift(days=+1)
        token = self.driver.generate_user_token(expiry, github_user.login, self.driver.find_roles(github_user))

        response = ResponseOAuthToken()
        response.access_token = token
        response.expiry = expiry
        return response

    @Route(route='authorization', methods=[RequestMethods.POST])
    @cherrypy.config(**{'tools.authentication.on': False})
    @cherrypy.tools.model_in(cls=RequestGithubAuthorization)
    @cherrypy.tools.model_out(cls=ResponseOAuthToken)
    def authorization(self):  # Used to get token via API (username and password Auth Flow)
        request: RequestGithubAuthorization = cherrypy.request.model

        user_github_client = github.Github(request.username, request.password, base_url=settings.GITHUB_URL)
        github_user: github.AuthenticatedUser.AuthenticatedUser = user_github_client.get_user()

        try:
            authorization = github_user.create_authorization(
                scopes=['user:email', 'read:org'],
                note='Sandwich Cloud Authorization',
                client_id=settings.GITHUB_CLIENT_ID,
                client_secret=settings.GITHUB_CLIENT_SECRET,
                onetime_password=request.otp_code
            )
        except TwoFactorException:
            cherrypy.response.headers['X-GitHub-OTP'] = '2fa'
            raise cherrypy.HTTPError(401, "OTP Code Required")
        except BadCredentialsException:
            raise cherrypy.HTTPError(404, "Invalid credentials")
        except GithubException as e:
            self.logger.exception("Error while validating GitHub authorization")
            raise cherrypy.HTTPError(424, "Backend error while talking with GitHub: " + json.dumps(e.data))

        return self.generate_token(github.Github(authorization.token, base_url=settings.GITHUB_URL))

    @Route(route='token', methods=[RequestMethods.OPTIONS])
    @cherrypy.config(**{'tools.authentication.on': False})
    @cherrypy.tools.json_out()
    def token_options(self):  # pragma: no cover
        # This is required for EmberJS for some reason?
        return {}

    @Route(route='token', methods=[RequestMethods.POST])
    @cherrypy.config(**{'tools.authentication.on': False})
    @cherrypy.tools.model_in(cls=RequestGithubToken)
    @cherrypy.tools.model_out(cls=ResponseOAuthToken)
    def token(self):  # Used to get token via Web UI (Authorization Code Auth Flow)
        request: RequestGithubToken = cherrypy.request.model

        # TODO: how to get this url since the settings only has the api url?
        r = requests.post('https://github.com/login/oauth/access_token', json={
            'client_id': settings.GITHUB_CLIENT_ID,
            'client_secret': settings.GITHUB_CLIENT_SECRET,
            'code': request.authorizationCode
        }, headers={'Accept': 'application/json'})

        if r.status_code == 404:
            raise cherrypy.HTTPError(404, "Unknown Authorization Code")
        elif r.status_code != 200:
            try:
                r.raise_for_status()
            except request.exceptions.RequestException as e:
                self.logger.exception("Error while validating GitHub access token")
                raise cherrypy.HTTPError(424, "Backend error while talking with GitHub: " + e.response.text)

        access_token_data = r.json()
        return self.generate_token(github.Github(access_token_data['access_token'], base_url=settings.GITHUB_URL))
