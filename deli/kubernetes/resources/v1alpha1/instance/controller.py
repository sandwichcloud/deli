import math
import uuid

import arrow
from go_defer import with_defer, defer

from deli.kubernetes.controller import ModelController
from deli.kubernetes.resources.const import REGION_LABEL, ZONE_LABEL, ATTACHED_TO_LABEL
from deli.kubernetes.resources.model import ResourceState
from deli.kubernetes.resources.v1alpha1.image.model import Image
from deli.kubernetes.resources.v1alpha1.instance.model import Instance, VMTask, VMPowerState
from deli.kubernetes.resources.v1alpha1.network.model import NetworkPort
from deli.kubernetes.resources.v1alpha1.region.model import Region
from deli.kubernetes.resources.v1alpha1.volume.model import Volume, VolumeTask
from deli.kubernetes.resources.v1alpha1.zone.model import Zone


class InstanceController(ModelController):
    def __init__(self, worker_count, resync_seconds, vmware, vspc_url):
        super().__init__(worker_count, resync_seconds, Instance, vmware)
        self.vspc_url = vspc_url

    def sync_model_handler(self, model):
        state_funcs = {
            ResourceState.ToCreate: self.to_create,
            ResourceState.Creating: self.creating,
            ResourceState.Created: self.created,
            ResourceState.ToDelete: self.to_delete,
            ResourceState.Deleting: self.deleting,
            ResourceState.Deleted: self.deleted
        }

        if model.state not in state_funcs:
            return

        state_funcs[model.state](model)

    def to_create(self, model):
        model.state = ResourceState.Creating
        model.save()

    @with_defer
    def creating(self, model: Instance):
        defer(model.save)

        if model.task is None:
            region: Region = model.region
            if region.schedulable is False:
                model.error_message = "Region is not currently schedulable"
                return

            image = model.image
            if image is None:
                model.error_message = "Image does not exist"
                return

            network_port: NetworkPort = model.network_port
            if network_port.state == ResourceState.Error:
                model.error_message = "Network Port has returned an error"
                return

            if network_port.state != ResourceState.Created:
                # Wait for network port to be ready
                return

            with self.vmware.client_session() as vmware_client:
                datacenter = self.vmware.get_datacenter(vmware_client, region.datacenter)

                zone: Zone = model.zone
                if zone is None:
                    zone = self.find_best_zone(vmware_client, datacenter, region, model)

                    # If we cannot find a free zone error
                    if zone is None:
                        model.error_message = "Could not find an available zone to launch the instance"
                        return

                    model.zone = zone
                else:
                    if zone.schedulable is False:
                        model.error_message = "Zone is not currently schedulable"
                        return
                    if self.can_zone_host(vmware_client, datacenter, zone, model) is False:
                        model.error_message = "Requested zone does not have enough resources available."
                        return

                vmware_image = self.vmware.get_image(vmware_client, image.file_name, datacenter)

                image_size = math.ceil(self.vmware.get_disk_size(vmware_image) / (1024 ** 3))
                if image_size > model.disk:
                    model.error_message = "Requested image requires a disk size of at least %s GB" % image_size
                    return
                #
                # old_vm = self.vmware.get_vm(vmware_client, str(model.vm_id), datacenter)
                # if old_vm is not None:
                #     self.logger.info(
                #         "A backing for the vm %s / %s already exists so it is going to be deleted".format(
                #             model.project.name,
                #             model.name))
                #     self.vmware.power_off_vm(vmware_client, old_vm, hard=True)
                #     self.vmware.delete_vm(vmware_client, old_vm)

                port_group = self.vmware.get_port_group(vmware_client, network_port.network.port_group, datacenter)
                cluster = self.vmware.get_cluster(vmware_client, zone.vm_cluster, datacenter)
                datastore = self.vmware.get_datastore(vmware_client, zone.vm_datastore, datacenter)
                folder = None
                if zone.vm_folder is not None:
                    folder = self.vmware.get_folder(vmware_client, zone.vm_folder, datacenter)

                create_vm_task = self.vmware.create_vm_from_image(vm_name="sandwich-" + str(uuid.uuid4()),
                                                                  image=vmware_image,
                                                                  datacenter=datacenter,
                                                                  cluster=cluster,
                                                                  datastore=datastore,
                                                                  folder=folder,
                                                                  port_group=port_group,
                                                                  vcpus=model.vcpus,
                                                                  ram=model.ram)
                model.task = VMTask.BUILDING
                model.task_kwargs = {"task_key": create_vm_task.info.key}
        elif model.task == VMTask.BUILDING:
            with self.vmware.client_session() as vmware_client:
                task = self.vmware.get_task(vmware_client, model.task_kwargs['task_key'])
                done, error = self.vmware.is_task_done(task)
                if done:
                    if error is not None:
                        model.error_message = error
                        return
                    model.vm_id = task.info.result.config.instanceUuid
                    datacenter = self.vmware.get_datacenter(vmware_client, model.region.datacenter)
                    vmware_vm = self.vmware.get_vm(vmware_client, str(model.vm_id), datacenter)
                    self.vmware.resize_root_disk(vmware_client, model.disk, vmware_vm)
                    self.vmware.setup_serial_connection(vmware_client, self.vspc_url, vmware_vm)

                    if len(model.initial_volumes) > 0:
                        if len(model.initial_volumes_status) == 0:
                            initial_volume_names = []
                            for idx, volume_data in enumerate(model.initial_volumes):
                                volume = Volume()
                                volume.project = model.project
                                volume.name = model.name + "-" + str(idx)
                                volume.zone = model.zone
                                volume.size = volume_data['size']
                                volume.create()

                                initial_volume_names.append(volume.name)
                            model.initial_volumes_status = initial_volume_names
                            return
                        else:
                            attached_vols = 0
                            for volume_name in model.initial_volumes_status:
                                volume: Volume = Volume.get(model.project, volume_name)
                                if volume is None:
                                    model.error_message = "Volume " + volume.name + \
                                                          " has disappeared while trying to attach"
                                    return
                                if volume.state in [ResourceState.ToCreate, ResourceState.Creating]:
                                    continue
                                if volume.state != ResourceState.Created:
                                    model.error_message = "Cannot attach volume " + str(
                                        volume.name) + " while it is in the following state: " + volume.state.value
                                    return
                                if volume.attached_to_name == model.name:
                                    attached_vols += 1
                                    continue
                                if volume.attached_to_name is not None and volume.attached_to_name != model.name:
                                    model.error_message = "Volume " + str(
                                        volume.name) + " has been attached to another instance."
                                    return
                                if volume.task is None:
                                    volume.attach(model)
                                    volume.save()
                                else:
                                    model.error_message = "Cannot attach volume" + str(
                                        volume.name) + " while a task is running on it."
                                    return
                            if attached_vols != len(model.initial_volumes_status):
                                return

                    self.vmware.power_on_vm(vmware_client, vmware_vm)
                    model.task = None
                    model.power_state = VMPowerState.POWERED_ON
                    model.state = ResourceState.Created

    def created(self, model: Instance):
        region = model.region
        # Check our region, if it is not created we should be deleted
        if region.state == ResourceState.Deleting:
            model.delete()
            return

        zone = model.zone
        if zone.state == ResourceState.Deleting:
            model.delete()
            return

        # Network port is being deleted so we should delete
        if model.network_port.state == ResourceState.Deleting:
            model.delete()
            return
        # If the service account is gone we need to delete
        if model.service_account is None:
            model.delete()
            return

        # If the image doesn't exist we should clear it
        if model.image_name is not None:
            if model.image is None:
                model.image = None
                model.save()
                return

        with self.vmware.client_session() as vmware_client:
            datacenter = self.vmware.get_datacenter(vmware_client, region.datacenter)
            vmware_vm = self.vmware.get_vm(vmware_client, str(model.vm_id), datacenter)

            if vmware_vm is None:
                model.error_message = "Backing VM disappeared"
                model.save()
                return

            if model.task == VMTask.STARTING:
                self.vmware.power_on_vm(vmware_client, vmware_vm)
                model.power_state = VMPowerState.POWERED_ON
                model.task = None
                model.save()
                return
            elif model.task == VMTask.STOPPING or model.task == VMTask.RESTARTING:
                is_shutdown = self.shutdown_vm(vmware_client, vmware_vm, model)
                if is_shutdown:
                    if model.task == VMTask.RESTARTING:
                        self.vmware.power_on_vm(vmware_client, vmware_vm)
                    model.task = None
                    model.save()
                    return
            elif model.task == VMTask.IMAGING:
                if 'task_key' not in model.task_kwargs:
                    datastore = self.vmware.get_datastore(vmware_client, region.image_datastore, datacenter)
                    folder = None
                    if region.image_folder is not None:
                        folder = self.vmware.get_folder(vmware_client, region.image_folder, datacenter)
                    clone_vm_task, image_file_name = self.vmware.clone_and_template_vm(vmware_vm, datastore, folder)
                    model.task_kwargs["image_file_name"] = image_file_name
                    model.task_kwargs["task_key"] = clone_vm_task.info.key
                    model.save()
                    return
                else:
                    task = self.vmware.get_task(vmware_client, model.task_kwargs['task_key'])
                    done, error = self.vmware.is_task_done(task)
                    if done:
                        if error is not None:
                            model.error_message = error
                            return
                        image: Image = Image.get(model.project, model.task_kwargs['image_name'])
                        image.file_name = model.task_kwargs["image_file_name"]
                        image.save()
                        model.task = None
                        model.save()
                        return

            power_state = str(vmware_vm.runtime.powerState)
            if power_state == "poweredOn" and model.power_state != VMPowerState.POWERED_ON:
                model.power_state = VMPowerState.POWERED_ON
                model.save()
                return

            if power_state == "poweredOff" and model.power_state != VMPowerState.POWERED_OFF:
                model.power_state = VMPowerState.POWERED_OFF
                model.save()
                return

    def shutdown_vm(self, vmware_client, vmware_vm, model):
        if 'timeout_at' not in model.task_kwargs:
            hard = model.task_kwargs['hard']
            if hard:
                self.vmware.power_off_vm(vmware_client, vmware_vm, hard=True)
                return True
            self.vmware.power_off_vm(vmware_client, vmware_vm)
            model.task_kwargs["timeout_at"] = arrow.now('UTC').shift(seconds=+model.task_kwargs['timeout']).isoformat()
        else:
            power_state = str(vmware_vm.runtime.powerState)
            if power_state != 'poweredOn':
                return True
            timeout_at = arrow.get(model.task_kwargs['timeout_at'])
            if timeout_at <= arrow.now('UTC'):
                self.vmware.power_off_vm(vmware_client, vmware_vm, hard=True)
                return True

        return False

    def to_delete(self, model):
        model.state = ResourceState.Deleting
        model.task_kwargs = {
            'hard': False,
            'timeout': 300
        }
        model.save()

    @with_defer
    def deleting(self, model: Instance):
        defer(model.save)

        region = model.region
        if region is not None:
            with self.vmware.client_session() as vmware_client:
                datacenter = self.vmware.get_datacenter(vmware_client, region.datacenter)
                vmware_vm = self.vmware.get_vm(vmware_client, str(model.vm_id), datacenter)
                if vmware_vm is None:
                    self.logger.warning(
                        "Could not find backing vm for instance %s/%s when trying to delete" % (model.project.name,
                                                                                                model.name))
                else:
                    power_state = str(vmware_vm.runtime.powerState)
                    if power_state == 'poweredOn':
                        is_shutdown = self.shutdown_vm(vmware_client, vmware_vm, model)
                        if is_shutdown is False:
                            return

                    for idx, volume_name in enumerate(model.initial_volumes_status):
                        delete = model.initial_volumes[idx]['auto_delete']
                        if delete:
                            volume: Volume = Volume.get(model.project, volume_name)
                            if volume is None:
                                continue
                            if volume.state in [ResourceState.ToDelete, ResourceState.Deleting, ResourceState.Deleted]:
                                continue
                            if volume.attached_to_name == model.name:
                                volume.delete()

                    attached_volumes = Volume.list(model.project,
                                                   label_selector=ATTACHED_TO_LABEL + "=" + str(model.name))
                    if len(attached_volumes) > 0:
                        for volume in attached_volumes:
                            if volume.state in [ResourceState.ToDelete, ResourceState.Deleting, ResourceState.Deleted]:
                                continue
                            if volume.task != VolumeTask.DETACHING:
                                volume.task = VolumeTask.DETACHING
                                volume.save()
                        return

                    self.vmware.delete_vm(vmware_client, vmware_vm)
        else:
            # The region has poofed so we can't actually delete anything in vmware
            pass
        network_port = model.network_port
        if network_port is not None:
            network_port.delete()
        model.power_state = VMPowerState.POWERED_OFF
        model.state = ResourceState.Deleted

    def deleted(self, model):
        model.delete(force=True)

    def find_best_zone(self, vmware_client, datacenter, region, model):
        """
        Currently this just finds a zone that can host the instances and returns that.
        We may want a better way to balance instances across zones in the future
        """
        zones = Zone.list(label_selector=REGION_LABEL + '=' + str(region.name))

        for zone in zones:
            if zone.schedulable is False:
                continue
            if self.can_zone_host(vmware_client, datacenter, zone, model):
                return zone

        return None

    def can_zone_host(self, vmware_client, datacenter, zone, model):
        cluster = self.vmware.get_cluster(vmware_client, zone.vm_cluster, datacenter)
        instances = Instance.list_all(label_selector=ZONE_LABEL + '=' + str(zone.name))
        used_resources = {}
        for instance in instances:
            if instance.name == model.name:
                # Skip own instance
                continue
            vm = self.vmware.get_vm(vmware_client, str(instance.vm_id), datacenter)
            if vm is None:
                continue
            # If the  VM doesn't have a host we should reserve it on all hosts
            host = vm.runtime.host.name if vm.runtime.host is not None else None

            if host not in used_resources:
                used_resources[host] = (instance.vcpus, instance.ram)
            else:
                used_cores, used_ram = used_resources[host]
                used_cores += instance.vcpus
                used_ram += instance.ram
                used_resources[host] = (used_cores, used_ram)

        for host in cluster.host:
            total_cores = math.floor(host.hardware.cpuInfo.numCpuThreads * (zone.core_provision_percent / 100))
            total_ram = math.floor(host.hardware.memorySize * (zone.ram_provision_percent / 100))
            if host.name in used_resources:
                used_cores, used_ram = used_resources[host.name]
                available_cores = total_cores - used_cores
                available_ram = total_ram - used_ram
            else:
                available_cores = total_cores
                available_ram = total_ram

            if None in used_resources:
                used_cores, used_ram = used_resources[None]
                available_cores = available_cores - used_cores
                available_ram = available_ram - used_ram

            if available_cores >= model.vcpus and available_ram >= model.ram:
                return True

        return False
