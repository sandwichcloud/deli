from typing import Dict

import github
from github.NamedUser import NamedUser
from simple_settings import settings

from deli.counter.auth.driver import AuthDriver
from deli.counter.auth.drivers.github.router import GithubAuthRouter


class GithubAuthDriver(AuthDriver):
    def __init__(self):
        super().__init__('github')

    def auth_router(self) -> GithubAuthRouter:
        return GithubAuthRouter(self)

    def discover_options(self) -> Dict:  # pragma: no cover
        return {}

    def check_in_org(self, github_user) -> bool:
        for org in github_user.get_orgs():
            if org.login == settings.GITHUB_ORG:
                return True

        return False

    def health(self):
        health = {
            'healthy': False,
            'valid_credentials': False
        }
        try:
            client = github.Github(client_id=settings.GITHUB_CLIENT_ID, client_secret=settings.GITHUB_CLIENT_SECRET,
                                   base_url=settings.GITHUB_URL)
            remaining, limit = client.rate_limiting
            health['valid_credentials'] = True
            health['rate'] = {
                'limit': limit,
                'remaining': remaining
            }
            if remaining > 10:
                health['healthy'] = True
        except Exception:
            self.logger.exception("Error getting auth driver health")
        finally:
            return health

    def find_roles(self, github_user):
        roles = []

        org = None
        for org in github_user.get_orgs():
            if org.login == settings.GITHUB_ORG:
                break

        for team in org.get_teams():

            if team.has_in_members(NamedUser(None, [], {"login": github_user.login}, completed=True)) is False:
                continue

            if team.name in settings.GITHUB_TEAM_ROLES:
                roles.append(settings.GITHUB_TEAM_ROLES[team.name])
                continue

            if team.name.startswith(settings.GITHUB_TEAM_ROLES_PREFIX):
                roles.append(team.name.replace(settings.GITHUB_TEAM_ROLES_PREFIX, ""))
                continue

        return roles
