import logging
import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.getcwd(), '.env'))

####################
# CORE             #
####################

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
        '': {
            'level': LOGGING_LEVEL,
            'handlers': ['console']
        },
        'deli': {
            'level': LOGGING_LEVEL,
            'handlers': ['console'],
            'propagate': False
        },
        'cherrypy.access': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False
        },
        'cherrypy.error': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False
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

KUBE_CONFIG = os.environ.get("KUBECONFIG")
KUBE_MASTER = os.environ.get("KUBEMASTER")

####################
# REDIS            #
####################

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

####################
# Auth             #
####################

AUTH_DRIVERS = os.environ.get('AUTH_DRIVERS', "").split(",")
AUTH_FERNET_KEYS = os.environ['AUTH_FERNET_KEYS'].split(",")

# URL of the OpenID Provider
OPENID_ISSUER_URL = os.environ['OPENID_ISSUER_URL']

# Client crendentials to auth with the OpenID Prover
OPENID_CLIENT_ID = os.environ['OPENID_CLIENT_ID']
OPENID_CLIENT_SECRET = os.environ['OPENID_CLIENT_SECRET']

# JWT Claim to use as the user's email
OPENID_EMAIL_CLAIM = os.environ.get('OPENID_EMAIL_CLAIM', 'email')

# JWT claim to use as the user's groups
OPENID_GROUPS_CLAIM = os.environ.get('OPENID_GROUPS_CLAIM', 'groups')
