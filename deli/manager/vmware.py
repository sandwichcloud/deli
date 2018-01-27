import uuid
from contextlib import contextmanager

from pyVim import connect
from pyVmomi import vim, vmodl


class VMWare(object):
    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def connect(self):
        return connect.SmartConnectNoSSL(
            host=self.host,
            user=self.username,
            pwd=self.password,
            port=self.port
        )

    def get_datacenter(self, vmware_client, datacenter_name):
        return self.get_obj(vmware_client, vim.Datacenter, datacenter_name)

    def get_folder(self, vmware_client, folder_name, datacenter):
        # TODO: find folder in DC
        return self.get_obj(vmware_client, vim.Folder, folder_name)

    def get_image(self, vmware_client, image_name, datacenter):
        return self.get_obj(vmware_client, vim.VirtualMachine, image_name, folder=datacenter.vmFolder)

    def get_vm(self, vmware_client, vm_name, datacenter):
        return self.get_obj(vmware_client, vim.VirtualMachine, vm_name, folder=datacenter.vmFolder)

    def get_cluster(self, vmware_client, cluster_name, datacenter):
        return self.get_obj(vmware_client, vim.ClusterComputeResource, cluster_name, folder=datacenter.hostFolder)

    def get_datastore(self, vmware_client, datastore_name, datacenter):
        return self.get_obj(vmware_client, vim.Datastore, datastore_name, folder=datacenter.datastoreFolder)

    def get_port_group(self, vmware_client, port_group_name, datacenter):
        return self.get_obj(vmware_client, vim.dvs.DistributedVirtualPortgroup, port_group_name,
                            folder=datacenter.networkFolder)

    def get_disk(self, vmware_client, disk_id, datastore):
        vStorageManager = vmware_client.RetrieveContent().vStorageObjectManager
        return vStorageManager.RetrieveVStorageObject(id=disk_id, datastore=datastore)

    def create_disk(self, vmware_client, disk_name, size, datastore):
        vStorageManager = vmware_client.RetrieveContent().vStorageObjectManager

        spec = vim.vslm.CreateSpec()
        spec.name = disk_name
        spec.capacityInMB = size * 1024
        spec.backingSpec = vim.vslm.CreateSpec.DiskFileBackingSpec()
        spec.backingSpec.provisioningType = "thin"
        spec.backingSpec.datastore = datastore

        task = vStorageManager.CreateDisk_Task(spec)
        self.wait_for_tasks(vmware_client, [task])
        vStorageObject = task.info.result

        return vStorageObject.config.id.id

    def clone_disk(self, vmware_client, disk_name, disk_id, datastore):
        vStorageManager = vmware_client.RetrieveContent().vStorageObjectManager

        spec = vim.vslm.CloneSpec()
        spec.name = disk_name
        spec.backingSpec = vim.vslm.CreateSpec.DiskFileBackingSpec()
        spec.backingSpec.datastore = datastore
        spec.backingSpec.provisioningType = "thin"
        task = vStorageManager.CloneVStorageObject_Task(id=vim.vslm.ID(id=disk_id), datastore=datastore, spec=spec)
        return task

    def delete_disk(self, vmware_client, disk_id, datastore):
        vStorageManager = vmware_client.RetrieveContent().vStorageObjectManager
        task = vStorageManager.DeleteVStorageObject_Task(id=vim.vslm.ID(id=disk_id), datastore=datastore)
        self.wait_for_tasks(vmware_client, [task])

    def grow_disk(self, vmware_client, disk_id, size, datastore):
        vStorageManager = vmware_client.RetrieveContent().vStorageObjectManager
        task = vStorageManager.ExtendDisk_Task(id=vim.vslm.ID(id=disk_id), datastore=datastore,
                                               newCapacityInMB=size * 1024)
        self.wait_for_tasks(vmware_client, [task])

    def attach_disk(self, vmware_client, disk_id, datastore, vm):
        task = vm.AttachDisk_Task(diskId=vim.vslm.ID(id=disk_id), datastore=datastore)
        self.wait_for_tasks(vmware_client, [task])

    def detach_disk(self, vmware_client, disk_id, vm):
        task = vm.DetachDisk_Task(diskId=vim.vslm.ID(id=disk_id))
        try:
            self.wait_for_tasks(vmware_client, [task])
        except vim.fault.NotFound:
            # Ignore error if the disk is already detached
            pass

    def create_vm_from_image(self, vm_name, image, cluster, datastore, folder, port_group, vcpus, ram):

        relospec = vim.vm.RelocateSpec()
        relospec.datastore = datastore
        relospec.pool = cluster.resourcePool

        clonespec = vim.vm.CloneSpec()
        clonespec.location = relospec
        clonespec.powerOn = False

        dvs_port_connection = vim.dvs.PortConnection()
        dvs_port_connection.portgroupKey = port_group.key
        dvs_port_connection.switchUuid = (
            port_group.config.distributedVirtualSwitch.uuid
        )

        nic = vim.vm.device.VirtualDeviceSpec()
        nic.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        nic.device = vim.vm.device.VirtualVmxnet3()
        nic.device.addressType = 'assigned'
        nic.device.key = 4000
        nic.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
        nic.device.backing.port = dvs_port_connection
        nic.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        nic.device.connectable.startConnected = True
        nic.device.connectable.allowGuestControl = True

        vmconf = vim.vm.ConfigSpec()
        vmconf.numCPUs = vcpus
        vmconf.memoryMB = ram
        vmconf.deviceChange = [nic]

        enable_uuid_opt = vim.option.OptionValue()
        enable_uuid_opt.key = 'disk.enableUUID'  # Allow the guest to easily mount extra disks
        enable_uuid_opt.value = '1'
        vmconf.extraConfig = [enable_uuid_opt]

        clonespec.config = vmconf

        if folder is not None:
            task = image.Clone(folder=folder, name=vm_name, spec=clonespec)
        else:
            task = image.Clone(name=vm_name, spec=clonespec)

        return task

    def get_disk_size(self, vm):
        for dev in vm.config.hardware.device:
            if isinstance(dev, vim.vm.device.VirtualDisk) and dev.deviceInfo.label == "Hard disk 1":
                return dev.capacityInBytes

        return 0

    def resize_root_disk(self, vmware_client, new_size, vm):
        virtual_disk_device = None

        # Find the disk device
        for dev in vm.config.hardware.device:
            if isinstance(dev, vim.vm.device.VirtualDisk) and dev.deviceInfo.label == "Hard disk 1":
                virtual_disk_device = dev
                break

        virtual_disk_spec = vim.vm.device.VirtualDeviceSpec()
        virtual_disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        virtual_disk_spec.device = virtual_disk_device
        virtual_disk_spec.device.capacityInBytes = new_size * (1024 ** 3)

        spec = vim.vm.ConfigSpec()
        spec.deviceChange = [virtual_disk_spec]
        task = vm.ReconfigVM_Task(spec=spec)
        self.wait_for_tasks(vmware_client, [task])

    def setup_serial_connection(self, vmware_client, vspc_address, vm):
        serial_device = None
        # Find the serial device
        for dev in vm.config.hardware.device:
            # Label may change if we add another port (i.e for logging)
            if isinstance(dev, vim.vm.device.VirtualSerialPort) and dev.deviceInfo.label == "Serial port 1":
                serial_device = dev
                break

        serial_device_spec = vim.vm.device.VirtualDeviceSpec()
        serial_device_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit

        if serial_device is None:
            serial_device_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
            serial_device_spec.device = vim.vm.device.VirtualSerialPort()
        else:
            serial_device_spec.device = serial_device

        serial_device_spec.device.backing = vim.vm.device.VirtualSerialPort.URIBackingInfo()
        serial_device_spec.device.backing.serviceURI = 'sandwich'
        serial_device_spec.device.backing.direction = 'client'
        serial_device_spec.device.backing.proxyURI = vspc_address
        serial_device_spec.device.yieldOnPoll = True

        spec = vim.vm.ConfigSpec()
        spec.deviceChange = [serial_device_spec]
        task = vm.ReconfigVM_Task(spec=spec)
        self.wait_for_tasks(vmware_client, [task])

    def power_on_vm(self, vmware_client, vm):
        if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOff:
            task = vm.PowerOn()
            self.wait_for_tasks(vmware_client, [task])

    def power_off_vm(self, vmware_client, vm, hard=False):
        if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
            if hard is False:
                try:
                    vm.ShutdownGuest()
                except vim.fault.ToolsUnavailable:
                    # Guest tools was not running so hard power off instead
                    return self.power_off_vm(vmware_client, vm, hard=True)
                return
            task = vm.PowerOff()
            self.wait_for_tasks(vmware_client, [task])

    def delete_vm(self, vmware_client, vm):
        task = vm.Destroy()
        self.wait_for_tasks(vmware_client, [task])

    def delete_image(self, vmware_client, image):
        task = image.Destroy_Task()
        self.wait_for_tasks(vmware_client, [task])

    def clone_and_template_vm(self, vm, datastore, folder):
        reloSpec = vim.vm.RelocateSpec()
        reloSpec.datastore = datastore
        # the vm template stays on the host
        # if the host is down any clone will fail

        if folder is not None:
            reloSpec.folder = folder

        # Configure the new vm to be super small because why not
        # We may want to remove it from the vswitch as well
        vmconf = vim.vm.ConfigSpec()
        vmconf.numCPUs = 1
        vmconf.memoryMB = 128
        vmconf.deviceChange = []

        # We don't want additional disks to be cloned with the VM so remove them
        for dev in vm.config.hardware.device:
            if isinstance(dev, vim.vm.device.VirtualDisk) and dev.deviceInfo.label.startswith("Hard disk") \
                    and dev.deviceInfo.label.endswith("1") is False:
                virtual_disk_spec = vim.vm.device.VirtualDeviceSpec()
                virtual_disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
                virtual_disk_spec.device = dev
                vmconf.deviceChange.append(virtual_disk_spec)

        # If the vm starts with a large disk there is no way to shrink it.
        # Hopefully it is thin provisioned...
        # We should be smart when we create instances that will be converted to images
        # they should have as small a disk as possible
        # storage is cheap but cloning is expensive

        clonespec = vim.vm.CloneSpec()
        clonespec.location = reloSpec
        clonespec.config = vmconf
        clonespec.powerOn = False
        clonespec.template = True

        file_name = str(uuid.uuid4())

        task = vm.Clone(folder=folder, name=file_name, spec=clonespec)
        return task, file_name

    def get_obj(self, vmware_client, vimtype, name, folder=None):
        """
        Return an object by name, if name is None the
        first found object is returned
        """
        obj = None
        content = vmware_client.RetrieveContent()

        if folder is None:
            folder = content.rootFolder

        container = content.viewManager.CreateContainerView(folder, [vimtype], True)
        for c in container.view:
            if c.name == name:
                obj = c
                break

        container.Destroy()
        return obj

    def get_task(self, vmware_client, task_key):
        task = vim.Task(task_key)
        task._stub = vmware_client._stub
        return task

    def is_task_done(self, task):
        state = task.info.state
        if state == vim.TaskInfo.State.success:
            return True, None

        if state == vim.TaskInfo.State.error:
            return True, str(task.info.error.msg)

        return False, None

    def wait_for_tasks(self, vmware_client, tasks):
        """Given the service instance si and tasks, it returns after all the
       tasks are complete
       """
        property_collector = vmware_client.RetrieveContent().propertyCollector
        task_list = [str(task) for task in tasks]
        # Create filter
        obj_specs = [vmodl.query.PropertyCollector.ObjectSpec(obj=task)
                     for task in tasks]
        property_spec = vmodl.query.PropertyCollector.PropertySpec(type=vim.Task,
                                                                   pathSet=[],
                                                                   all=True)
        filter_spec = vmodl.query.PropertyCollector.FilterSpec()
        filter_spec.objectSet = obj_specs
        filter_spec.propSet = [property_spec]
        pcfilter = property_collector.CreateFilter(filter_spec, True)
        try:
            version, state = None, None
            # Loop looking for updates till the state moves to a completed state.
            while len(task_list):
                update = property_collector.WaitForUpdates(version)
                for filter_set in update.filterSet:
                    for obj_set in filter_set.objectSet:
                        task = obj_set.obj
                        for change in obj_set.changeSet:
                            if change.name == 'info':
                                state = change.val.state
                            elif change.name == 'info.state':
                                state = change.val
                            else:
                                continue

                            if not str(task) in task_list:
                                continue

                            if state == vim.TaskInfo.State.success:
                                # Remove task from taskList
                                task_list.remove(str(task))
                            elif state == vim.TaskInfo.State.error:
                                raise task.info.error
                # Move to next version
                version = update.version
        finally:
            if pcfilter:
                pcfilter.Destroy()

    @contextmanager
    def client_session(self):
        vmware_client = self.connect()
        try:
            yield vmware_client
        finally:
            connect.Disconnect(vmware_client)
