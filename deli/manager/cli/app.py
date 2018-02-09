import logging

from clify.app import Application
from pbr.version import VersionInfo


class ManagerApplication(Application):
    def __init__(self):
        super().__init__('deli_manager', 'CLI for Deli Manager')

    @property
    def version(self):
        return VersionInfo('sandwichcloud-deli').semantic_version().release_string()

    def logging_config(self, log_level: int) -> dict:
        return {
            'version': 1,
            'formatters': {
                'default': {
                    'format': '[%(asctime)s][%(name)s][%(levelname)s] %(message)s',
                    'datefmt': '%Y-%m-%dT%H:%M:%S%z'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'default'
                }
            },
            'loggers': {
                '': {
                    'level': logging.getLevelName(log_level),
                    'handlers': ['console']
                },
                'deli': {
                    'level': logging.getLevelName(log_level),
                    'handlers': ['console'],
                    'propagate': False
                },
            }
        }
