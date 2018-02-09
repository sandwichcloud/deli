import argparse
import enum
import ipaddress
import json
import os
import time
import uuid

import arrow
import urllib3
from clify.daemon import Daemon
from dotenv import load_dotenv
from kubernetes import config, client
from kubernetes.client import Configuration

from deli.kubernetes.election.elector import LeaderElector
from deli.kubernetes.resources.v1alpha1.flavor.controller import FlavorController
from deli.kubernetes.resources.v1alpha1.flavor.model import Flavor
from deli.kubernetes.resources.v1alpha1.image.controller import ImageController
from deli.kubernetes.resources.v1alpha1.image.model import Image
from deli.kubernetes.resources.v1alpha1.instance.controller import InstanceController
from deli.kubernetes.resources.v1alpha1.instance.model import Instance
from deli.kubernetes.resources.v1alpha1.keypair.controller import KeypairController
from deli.kubernetes.resources.v1alpha1.keypair.keypair import Keypair
from deli.kubernetes.resources.v1alpha1.network.controller import NetworkController, NetworkPortController
from deli.kubernetes.resources.v1alpha1.network.model import Network, NetworkPort
from deli.kubernetes.resources.v1alpha1.project_member.controller import ProjectMemberController
from deli.kubernetes.resources.v1alpha1.project_member.model import ProjectMember
from deli.kubernetes.resources.v1alpha1.project_quota.controller import ProjectQuotaController
from deli.kubernetes.resources.v1alpha1.project_quota.model import ProjectQuota
from deli.kubernetes.resources.v1alpha1.region.controller import RegionController
from deli.kubernetes.resources.v1alpha1.region.model import Region
from deli.kubernetes.resources.v1alpha1.role.controller import GlobalRoleController, ProjectRoleController
from deli.kubernetes.resources.v1alpha1.role.model import GlobalRole, ProjectRole
from deli.kubernetes.resources.v1alpha1.service_account.controller import ServiceAccountController
from deli.kubernetes.resources.v1alpha1.service_account.model import ServiceAccount
from deli.kubernetes.resources.v1alpha1.volume.controller import VolumeController
from deli.kubernetes.resources.v1alpha1.volume.model import Volume
from deli.kubernetes.resources.v1alpha1.zone.controller import ZoneController
from deli.kubernetes.resources.v1alpha1.zone.model import Zone
from deli.manager.vmware import VMWare


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


class RunManager(Daemon):
    def __init__(self):
        super().__init__('run', 'Run the Sandwich Cloud Manager')
        self.menu_url = None
        self.vmware = None
        self.leader_elector = None
        self.controllers = []

    def setup_arguments(self, parser):
        load_dotenv(os.path.join(os.getcwd(), '.env'))
        parser.add_argument("--kube-config", action=EnvDefault, envvar="KUBECONFIG", required=False, default="",
                            help="Path to a kubeconfig. Only required if out-of-cluster.")
        parser.add_argument('--kube-master', action=EnvDefault, envvar="KUBEMASTER", required=False, default="",
                            help="The address of the Kubernetes API server (overrides any value in kubeconfig)")

        required_group = parser.add_argument_group("required named arguments")

        required_group.add_argument("--vcenter-host", action=EnvDefault, envvar="VCENTER_HOST", required=True,
                                    help="The address to use to connect to VCenter")
        required_group.add_argument("--vcenter-port", action=EnvDefault, envvar="VCENTER_PORT", default="443",
                                    help="The port to use to connect to VCenter")
        required_group.add_argument("--vcenter-username", action=EnvDefault, envvar="VCENTER_USERNAME", required=True,
                                    help="The username to use to connect to VCenter")
        required_group.add_argument("--vcenter-password", action=EnvDefault, envvar="VCENTER_PASSWORD", required=True,
                                    help="The password to use to connect to VCenter")

        required_group.add_argument("--menu-url", action=EnvDefault, envvar="MENU_URL", required=True,
                                    help="Telnet URL to the menu server")

    def run(self, args) -> int:
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
                self.logger.error("Error connecting to the Kubernetes API. Trying again in 5 seconds. Error: " + str(e))
                time.sleep(5)

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

        self.logger.info("Creating CRDs")
        GlobalRole.create_crd()
        GlobalRole.wait_for_crd()
        GlobalRole.create_default_roles()
        ProjectRole.create_crd()
        ProjectRole.wait_for_crd()
        ProjectMember.create_crd()
        ProjectMember.wait_for_crd()
        ProjectQuota.create_crd()
        ProjectQuota.wait_for_crd()

        Region.create_crd()
        Region.wait_for_crd()
        Zone.create_crd()
        Zone.wait_for_crd()
        Network.create_crd()
        Network.wait_for_crd()
        NetworkPort.create_crd()
        NetworkPort.wait_for_crd()
        Image.create_crd()
        Image.wait_for_crd()
        ServiceAccount.create_crd()
        ServiceAccount.wait_for_crd()
        Flavor.create_crd()
        Flavor.wait_for_crd()
        Volume.create_crd()
        Volume.wait_for_crd()
        Instance.create_crd()
        Instance.wait_for_crd()
        Keypair.create_crd()
        Keypair.wait_for_crd()
        self.logger.info("CRDs have been created")

        self.menu_url = args.menu_url
        self.vmware = VMWare(args.vcenter_host, args.vcenter_port, args.vcenter_username, args.vcenter_password)

        self.leader_elector = LeaderElector(self.on_started_leading, self.on_stopped_leading)
        self.leader_elector.start()

        return 0

    def launch_controller(self, controller):
        self.controllers.append(controller)
        controller.start()

    def on_started_leading(self):
        if self.leader_elector.shutting_down:
            return
        self.logger.info("Started leading... starting controllers")
        self.launch_controller(RegionController(1, 30, self.vmware))
        self.launch_controller(ZoneController(1, 30, self.vmware))
        self.launch_controller(GlobalRoleController(1, 30))
        self.launch_controller(ProjectRoleController(1, 30))
        self.launch_controller(ProjectMemberController(1, 30))
        self.launch_controller(ProjectQuotaController(1, 30))
        self.launch_controller(NetworkController(1, 30, self.vmware))
        self.launch_controller(NetworkPortController(1, 30))
        self.launch_controller(ImageController(4, 30, self.vmware))
        self.launch_controller(ServiceAccountController(1, 30))
        self.launch_controller(FlavorController(1, 30))
        self.launch_controller(VolumeController(4, 30, self.vmware))
        self.launch_controller(InstanceController(4, 30, self.vmware, self.menu_url))
        self.launch_controller(KeypairController(4, 30))

    def on_stopped_leading(self):
        self.logger.info("Stopped leading... stopping controllers")
        for controller in self.controllers:
            controller.stop()
        self.controllers = []

    def on_shutdown(self, signum=None, frame=None):
        self.logger.info("Shutting down the Manager")
        if self.leader_elector is not None:
            self.leader_elector.shutdown()
