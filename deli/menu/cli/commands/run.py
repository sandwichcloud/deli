import argparse
import enum
import ipaddress
import json
import os
import uuid

import arrow
from clify.daemon import Daemon
from dotenv import load_dotenv
from kubernetes import config

from deli.menu.vspc.server import VSPCServer


class EnvDefault(argparse.Action):
    def __init__(self, envvar, required=True, default=None, help=None, **kwargs):
        if envvar in os.environ:
            default = os.environ.get(envvar, default)
        if required and default:
            required = False
        if help is not None:
            help += " [Environment Variable: $" + envvar + "]"

        if default is None:
            default = argparse.SUPPRESS

        super(EnvDefault, self).__init__(default=default, required=required, help=help, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):  # pragma: no cover
        setattr(namespace, self.dest, values)


class RunMetadata(Daemon):
    def __init__(self):
        super().__init__('run', 'Run the Sandwich Cloud Metadata Server')
        self.vspc_server = None

    def setup_arguments(self, parser):
        load_dotenv(os.path.join(os.getcwd(), '.env'))
        parser.add_argument("--kube-config", action=EnvDefault, envvar="KUBECONFIG",
                            help="Path to a kubeconfig. Only required if out-of-cluster.")
        parser.add_argument("--fernet-key", action=EnvDefault, envvar="FERNET_KEY", required=True,
                            help="The fernet key to use to hand out tokens.")

    def run(self, args) -> int:
        if args.kube_config is None:
            self.logger.info("Using in-cluster configuration")
            config.load_incluster_config()
        else:
            self.logger.info("Using kube-config configuration")
            config.load_kube_config(config_file=args.kube_config)

        os.environ['FERNET_KEY'] = args.fernet_key

        old_json_encoder = json.JSONEncoder.default

        def json_encoder(self, o):  # pragma: no cover
            if isinstance(o, uuid.UUID):
                return str(o)
            if isinstance(o, arrow.Arrow):
                return o.isoformat()
            if isinstance(o, ipaddress.IPv4Network):
                return str(o)
            if isinstance(o, ipaddress.IPv4Address):
                return str(o)
            if isinstance(o, enum.Enum):
                return o.value

            return old_json_encoder(self, o)

        json.JSONEncoder.default = json_encoder

        self.vspc_server = VSPCServer('sandwich')
        self.vspc_server.start()

        return 0

    def on_shutdown(self, signum=None, frame=None):
        self.logger.info("Shutting down the Metadata Server")
        self.vspc_server.stop()
