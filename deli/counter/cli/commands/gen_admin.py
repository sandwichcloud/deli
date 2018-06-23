import json
import uuid

import arrow
from clify.command import Command
from cryptography.fernet import Fernet
from kubernetes import config
from kubernetes.client import Configuration
from simple_settings import settings

from deli.cache import cache_client
from deli.counter.auth.token import Token
from deli.kubernetes.resources.v1alpha1.iam_service_account.model import SystemServiceAccount


class GenAdmin(Command):
    def __init__(self):
        super().__init__('gen-admin', 'Generate Token for admin service account')

    def setup_arguments(self, parser):
        pass

    def setup(self, args):
        old_json_encoder = json.JSONEncoder.default

        def json_encoder(self, o):  # pragma: no cover
            if isinstance(o, uuid.UUID):
                return str(o)
            if isinstance(o, arrow.Arrow):
                return o.isoformat()

            return old_json_encoder(self, o)

        json.JSONEncoder.default = json_encoder

        if settings.KUBE_CONFIG is not None or settings.KUBE_MASTER is not None:
            Configuration.set_default(Configuration())
            if settings.KUBE_CONFIG is not None:
                config.load_kube_config(config_file=settings.KUBE_CONFIG)
            if settings.KUBE_MASTER is not None:
                Configuration._default.host = settings.KUBE_MASTER
        else:
            config.load_incluster_config()

        cache_client.connect(url=settings.REDIS_URL)
        return 0

    def run(self, args) -> int:
        fernet = Fernet(settings.AUTH_FERNET_KEYS[0])

        service_account = SystemServiceAccount.get('admin')
        if service_account is None:
            self.logger.error("Could not find admin service account. Is the manager running?")
            return 1

        service_account.keys = {"admin": arrow.now('UTC').shift(years=+10)}
        service_account.save()

        token = Token()
        token.email = service_account.email
        token.metadata['key'] = 'admin'

        self.logger.info("Old admin keys are now invalid.")
        self.logger.info("Admin Key: " + token.marshal(fernet).decode())

        return 0
