import logging
import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

####################
# CORE             #
####################

DEBUG = True if os.environ.get('PRODUCTION') is None else False

LOGGING_LEVEL = logging.getLevelName(logging.INFO)
LOGGING_CONFIG = {
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
        'deli': {
            'level': LOGGING_LEVEL,
            'handlers': ['console']
        },
        'cherrypy.access': {
            'level': 'INFO',
            'handlers': ['console']
        },
        'cherrypy.error': {
            'level': 'INFO',
            'handlers': ['console']
        },
        'sqlalchemy': {
            'level': 'WARN',
            'handlers': ['console']
        },
    }
}

if os.environ.get('CLI'):
    LOGGING_CONFIG['formatters']['default'] = {
        'format': '[%(levelname)s] %(message)s',
        'datefmt': '%Y-%m-%dT%H:%M:%S%z'
    }
    LOGGING_CONFIG['loggers']['alembic'] = {
        'level': LOGGING_LEVEL,
        'handlers': ['console']
    }

####################
# Kubernetes       #
####################

KUBE_CONFIG = os.environ.get("KUBE_CONFIG")

####################
# Auth             #
####################

AUTH_DRIVERS = os.environ.get('AUTH_DRIVERS', "deli.counter.auth.drivers.database.driver:DatabaseAuthDriver").split(",")
AUTH_FERNET_KEYS = os.environ['AUTH_FERNET_KEYS'].split(",")

####################
# Database AUTH    #
####################
# Does database auth need any params?

####################
# GITHUB AUTH      #
####################

GITHUB_URL = os.environ.get('GITHUB_URL', 'https://api.github.com')
GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')
GITHUB_ORG = os.environ.get('GITHUB_ORG')
GITHUB_TEAM_ROLES_PREFIX = os.environ.get("GITHUB_TEAM_ROLES_PREFIX", "sandwich-")

# Split the env var into a dict because it is faster to search
_github_team_roles = os.environ.get('GITHUB_TEAM_ROLES', 'sandwich-admin:admin')
GITHUB_TEAM_ROLES = dict(item.split(":") for item in _github_team_roles.split(","))
