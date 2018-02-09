import enum
import uuid

from deli.kubernetes.resources.const import TAG_LABEL, REGION_LABEL, ZONE_LABEL, IMAGE_LABEL, NETWORK_LABEL, \
    NETWORK_PORT_LABEL, SERVICE_ACCOUNT_LABEL
from deli.kubernetes.resources.model import ProjectResourceModel
from deli.kubernetes.resources.v1alpha1.flavor.model import Flavor
from deli.kubernetes.resources.v1alpha1.image.model import Image
from deli.kubernetes.resources.v1alpha1.keypair.keypair import Keypair
from deli.kubernetes.resources.v1alpha1.network.model import NetworkPort
from deli.kubernetes.resources.v1alpha1.region.model import Region
from deli.kubernetes.resources.v1alpha1.service_account.model import ServiceAccount
from deli.kubernetes.resources.v1alpha1.zone.model import Zone


class VMPowerState(enum.Enum):
    POWERED_ON = 'POWERED_ON'
    POWERED_OFF = 'POWERED_OFF'


class VMTask(enum.Enum):
    BUILDING = 'BUILDING'
    STARTING = 'STARTING'
    RESTARTING = 'RESTARTING'
    STOPPING = 'STOPPING'
    IMAGING = 'IMAGING'


class Instance(ProjectResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['metadata']['labels'][REGION_LABEL] = ''
            self._raw['metadata']['labels'][ZONE_LABEL] = ''
            self._raw['metadata']['labels'][IMAGE_LABEL] = ''
            self._raw['metadata']['labels'][NETWORK_LABEL] = ''
            self._raw['metadata']['labels'][NETWORK_PORT_LABEL] = ''
            self._raw['metadata']['labels'][SERVICE_ACCOUNT_LABEL] = ''
            self._raw['spec'] = {
                'flavor': {
                    'id': None,
                    'vcpus': 1,
                    'ram': 1024,
                    'disk': 20,
                },
                'keypairs': [],
                'userData': '#cloud-config\n{}',
                'initialVolumes': [
                    # {
                    #     "size": 5, size of the volume
                    #     "auto_delete": True delete the volume if still attached during instance delete
                    # }
                ],
            }
            self._raw['status']['initialVolumes'] = [
                # UUID of volumes with index matched to spec initialVolumes
            ]
            self._raw['status']['task'] = {
                'name': None,
                'kwargs': {}
            }
            self._raw['status']['vm'] = {
                'powerState': VMPowerState.POWERED_OFF.value
            }

    @property
    def region_id(self):
        region_id = self._raw['metadata']['labels'][REGION_LABEL]
        if region_id == "":
            return None
        return uuid.UUID(region_id)

    @property
    def region(self):
        region_id = self.region_id
        if region_id is None:
            return None
        return Region.get(region_id)

    @region.setter
    def region(self, value):
        self._raw['metadata']['labels'][REGION_LABEL] = str(value.id)

    @property
    def zone_id(self):
        zone_id = self._raw['metadata']['labels'][ZONE_LABEL]
        if zone_id == "":
            return None
        return uuid.UUID(zone_id)

    @property
    def zone(self):
        zone_id = self.zone_id
        if zone_id is None:
            return None
        return Zone.get(zone_id)

    @zone.setter
    def zone(self, value):
        self._raw['metadata']['labels'][ZONE_LABEL] = str(value.id)

    @property
    def image_id(self):
        image_id = self._raw['metadata']['labels'][IMAGE_LABEL]
        if image_id == "":
            return None
        return uuid.UUID(image_id)

    @property
    def image(self):
        image_id = self.image_id
        if image_id is None:
            return None
        return Image.get(image_id)

    @image.setter
    def image(self, value):
        self._raw['metadata']['labels'][IMAGE_LABEL] = str(value.id)

    @property
    def network_port_id(self):
        network_port_id = self._raw['metadata']['labels'][NETWORK_PORT_LABEL]
        if network_port_id == "":
            return None
        return uuid.UUID(network_port_id)

    @property
    def network_port(self):
        network_port_id = self.network_port_id
        if network_port_id is None:
            return None
        return NetworkPort.get(self.project, network_port_id)

    @network_port.setter
    def network_port(self, value):
        self._raw['metadata']['labels'][NETWORK_LABEL] = str(value.network.id)
        self._raw['metadata']['labels'][NETWORK_PORT_LABEL] = str(value.id)

    @property
    def service_account_id(self):
        service_account_id = self._raw['metadata']['labels'][SERVICE_ACCOUNT_LABEL]
        if service_account_id == "":
            return None
        return uuid.UUID(service_account_id)

    @property
    def service_account(self):
        service_account_id = self.service_account_id
        if service_account_id is None:
            return None
        return ServiceAccount.get(self.project, service_account_id)

    @service_account.setter
    def service_account(self, value):
        self._raw['metadata']['labels'][SERVICE_ACCOUNT_LABEL] = str(value.id)

    @property
    def user_data(self):
        return self._raw['spec']['userData']

    @user_data.setter
    def user_data(self, value):
        self._raw['spec']['userData'] = value

    @property
    def power_state(self):
        return VMPowerState(self._raw['status']['vm']['powerState'])

    @power_state.setter
    def power_state(self, value):
        self._raw['status']['vm']['powerState'] = value.value

    @property
    def task(self):
        if self._raw['status']['task']['name'] is None:
            return None
        return VMTask(self._raw['status']['task']['name'])

    @task.setter
    def task(self, value):
        if value is None:
            self._raw['status']['task']['name'] = None
            self.task_kwargs = {}
        else:
            self._raw['status']['task']['name'] = value.value

    @property
    def task_kwargs(self):
        return self._raw['status']['task']['kwargs']

    @task_kwargs.setter
    def task_kwargs(self, value):
        self._raw['status']['task']['kwargs'] = value

    @property
    def tags(self):
        tags = {}
        for label, v in self._raw['metadata']['labels'].items():
            if label.startswith(TAG_LABEL):
                tags[label.split("/")[1]] = v

        return tags

    def add_tag(self, tag, value):
        self._raw['metadata']['labels'][TAG_LABEL + '/' + tag] = value

    def remove_tag(self, tag):
        del self._raw['metadata']['labels'][TAG_LABEL + '/' + tag]

    @property
    def flavor_id(self):
        if self._raw['spec']['flavor']['id'] is None:
            return None
        return uuid.UUID(self._raw['spec']['flavor']['id'])

    @property
    def flavor(self):
        if self._raw['spec']['flavor']['id'] is None:
            return None
        return Flavor.get(self._raw['spec']['flavor']['id'])

    @flavor.setter
    def flavor(self, value):
        self._raw['spec']['flavor']['id'] = str(value.id)
        self.vcpus = value.vcpus
        self.ram = value.ram
        self.disk = value.disk

    @property
    def vcpus(self):
        return self._raw['spec']['flavor']['vcpus']

    @vcpus.setter
    def vcpus(self, value):
        self._raw['spec']['flavor']['vcpus'] = value

    @property
    def ram(self):
        return self._raw['spec']['flavor']['ram']

    @ram.setter
    def ram(self, value):
        self._raw['spec']['flavor']['ram'] = value

    @property
    def disk(self):
        return self._raw['spec']['flavor']['disk']

    @disk.setter
    def disk(self, value):
        self._raw['spec']['flavor']['disk'] = value

    @property
    def keypair_ids(self):
        keypair_ids = []
        for keypair_id in self._raw['spec']['keypairs']:
            keypair_ids.append(uuid.UUID(keypair_id))
        return keypair_ids

    @property
    def keypairs(self):
        keypairs = []
        for keypair_id in self._raw['spec']['keypairs']:
            keypair = Keypair.get(self.project, keypair_id)
            if keypair is not None:
                keypairs.append(keypair)
        return keypairs

    @keypairs.setter
    def keypairs(self, value):
        for keypair in value:
            self._raw['spec']['keypairs'].append(str(keypair.id))

    def action_start(self):
        self.task = VMTask.STARTING
        self.save()

    def action_stop(self, hard=False, timeout=300):
        self.task = VMTask.STOPPING
        self.task_kwargs = {
            'hard': hard,
            'timeout': timeout
        }
        self.save()

    def action_restart(self, hard=False, timeout=300):
        self.task = VMTask.RESTARTING
        self.task_kwargs = {
            'hard': hard,
            'timeout': timeout
        }
        self.save()

    def action_image(self, image_name):
        image = Image()
        image.project = self.project
        image.region = self.region
        image.name = image_name
        image.file_name = None
        image.create()

        self.task = VMTask.IMAGING
        self.task_kwargs = {
            'image_id': str(image.id)
        }
        self.save()

        return image

    @property
    def initial_volumes(self):
        return self._raw['spec']['initialVolumes']

    @initial_volumes.setter
    def initial_volumes(self, value):
        self._raw['spec']['initialVolumes'] = value

    @property
    def initial_volumes_status(self):
        return self._raw['status']['initialVolumes']

    @initial_volumes_status.setter
    def initial_volumes_status(self, value):
        self._raw['status']['initialVolumes'] = value
