import json
import uuid

import arrow
from clify.command import Command
from cryptography.fernet import Fernet
from kubernetes import config
from kubernetes.client import Configuration
from simple_settings import settings

from deli.counter.auth.token import Token
from deli.kubernetes.resources.v1alpha1.service_account.model import GlobalServiceAccount


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

        return 0

    def run(self, args) -> int:
        fernet = Fernet(settings.AUTH_FERNET_KEYS[0])

        service_account = GlobalServiceAccount.get_by_name('admin')
        if service_account is None:
            self.logger.error("Could not find admin service account. Is the manager running?")
            return 1

        key_name = str(uuid.uuid4())
        service_account.keys = [key_name]
        service_account.save()

        token = Token()
        token.driver_name = 'metadata'
        token.service_account_id = service_account.id
        token.service_account_key = key_name

        self.logger.info("Old admin keys are now invalid.")
        self.logger.info("Admin Key: " + token.marshal(fernet).decode())

        return 0
