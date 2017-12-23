from clify.app import Application
from pbr.version import VersionInfo
from simple_settings import settings


class CounterApplication(Application):
    def __init__(self):
        super().__init__('deli_counter', 'CLI for Deli Counter')

    @property
    def version(self):
        return VersionInfo('deli').semantic_version().release_string()

    def logging_config(self, log_level: int) -> dict:
        return settings.LOGGING_CONFIG
