import argparse
import enum
import ipaddress
import json
import os
import os.path
import time
import uuid

import arrow
import urllib3
from clify.daemon import Daemon
from dotenv import load_dotenv
from kubernetes import config, client
from kubernetes.client import Configuration

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
        parser.add_argument("--kube-config", action=EnvDefault, envvar="KUBECONFIG", required=False, default="",
                            help="Path to a kubeconfig. Only required if out-of-cluster.")
        parser.add_argument('--kube-master', action=EnvDefault, envvar="KUBEMASTER", required=False, default="",
                            help="The address of the Kubernetes API server (overrides any value in kubeconfig)")
        parser.add_argument('--out-of-band', action=EnvDefault, envvar="OUT_OF_BAND", required=False, default=None,
                            help="Path to .yaml (.yml) files to use for metadata")
        parser.add_argument("--fernet-key", action=EnvDefault, envvar="FERNET_KEY", required=True,
                            help="The fernet key to use to hand out tokens.")

    def run(self, args) -> int:

        if hasattr(args, "out_of_band"):
            self.logger.info("Using out of band configuration for metadata")
            if os.path.isdir(args.out_of_band) is False:
                self.logger.error("Could not find directory for out of band configuration " + args.out_of_band)
                return 1
            os.environ['OUT_OF_BAND'] = args.out_of_band
        else:
            self.logger.info("Using Kubernetes configuration for metadata")
            if args.kube_config != "" or args.kube_master != "":
                self.logger.info("Using kube-config configuration")
                Configuration.set_default(Configuration())
                if args.kube_config != "":
                    config.load_kube_config(config_file=args.kube_config)
                if args.kube_master != "":
                    Configuration._default.host = args.kube_master

            else:
                self.logger.info("Using in-cluster configuration")
                config.load_incluster_config()

            while True:
                try:
                    client.CoreV1Api().list_namespace()
                    break
                except urllib3.exceptions.HTTPError as e:
                    self.logger.error(
                        "Error connecting to the Kubernetes API. Trying again in 5 seconds. Error: " + str(e))
                    time.sleep(5)

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
        if self.vspc_server is not None:
            self.vspc_server.stop()
