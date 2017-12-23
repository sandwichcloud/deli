import argparse
import os

from clify.daemon import Daemon
from dotenv import load_dotenv
from kubernetes import config

from deli.kubernetes.resources.v1alpha1.image.controller import ImageController
from deli.kubernetes.resources.v1alpha1.image.model import Image
from deli.kubernetes.resources.v1alpha1.instance.controller import InstanceController
from deli.kubernetes.resources.v1alpha1.instance.model import Instance
from deli.kubernetes.resources.v1alpha1.keypair.controller import KeypairController
from deli.kubernetes.resources.v1alpha1.keypair.keypair import Keypair
from deli.kubernetes.resources.v1alpha1.network.controller import NetworkController, NetworkPortController
from deli.kubernetes.resources.v1alpha1.network.model import Network, NetworkPort
from deli.kubernetes.resources.v1alpha1.region.controller import RegionController
from deli.kubernetes.resources.v1alpha1.region.model import Region
from deli.kubernetes.resources.v1alpha1.role.controller import GlobalRoleController, ProjectRoleController
from deli.kubernetes.resources.v1alpha1.role.model import GlobalRole, ProjectRole
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
        self.controllers = []

    def setup_arguments(self, parser):
        load_dotenv(os.path.join(os.getcwd(), '.env'))
        parser.add_argument("--kube-config", action=EnvDefault, envvar="KUBE_CONFIG",
                            help="Path to a kubeconfig. Only required if out-of-cluster.")

        required_group = parser.add_argument_group("required named arguments")

        required_group.add_argument("--vcenter-host", action=EnvDefault, envvar="VCENTER_HOST", required=True,
                                    help="The address to use to connect to VCenter")
        required_group.add_argument("--vcenter-port", action=EnvDefault, envvar="VCENTER_PORT", default="443",
                                    help="The port to use to connect to VCenter")
        required_group.add_argument("--vcenter-username", action=EnvDefault, envvar="VCENTER_USERNAME", required=True,
                                    help="The username to use to connect to VCenter")
        required_group.add_argument("--vcenter-password", action=EnvDefault, envvar="VCENTER_PASSWORD", required=True,
                                    help="The password to use to connect to VCenter")

    def run(self, args) -> int:
        if args.kube_config is None:
            self.logger.info("Using in-cluster configuration")
            config.load_incluster_config()
        else:
            self.logger.info("Using kube-config configuration")
            config.load_kube_config(config_file=args.kube_config)

        self.logger.info("Creating CRDs")
        GlobalRole.create_crd()
        GlobalRole.wait_for_crd()
        GlobalRole.create_default_roles()
        ProjectRole.create_crd()
        ProjectRole.wait_for_crd()

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
        Instance.create_crd()
        Instance.wait_for_crd()
        Keypair.create_crd()
        Keypair.wait_for_crd()
        self.logger.info("CRDs have been created")

        vmware = VMWare(args.vcenter_host, args.vcenter_port, args.vcenter_username, args.vcenter_password)

        self.launch_controller(RegionController(1, 30, vmware))
        self.launch_controller(ZoneController(1, 30, vmware))
        self.launch_controller(GlobalRoleController(1, 30))
        self.launch_controller(ProjectRoleController(1, 30))
        self.launch_controller(NetworkController(1, 30, vmware))
        self.launch_controller(NetworkPortController(1, 30))
        self.launch_controller(ImageController(1, 30, vmware))
        self.launch_controller(InstanceController(1, 30, vmware))
        self.launch_controller(KeypairController(1, 30))
        return 0

    def launch_controller(self, controller):
        self.controllers.append(controller)
        controller.start()

    def on_shutdown(self, signum=None, frame=None):
        self.logger.info("Shutting down the Manager")
        for controller in self.controllers:
            controller.stop()
