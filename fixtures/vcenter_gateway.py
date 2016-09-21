from vcenter import *
from vnc_api.vnc_api import  *
from lif_fixture import LogicalInterfaceFixture
from physical_device_fixture import PhysicalDeviceFixture
from pif_fixture import PhysicalInterfaceFixture
from port_fixture import PortFixture
from openstack import OpenstackAuth, OpenstackOrchestrator
from contrailapi import ContrailVncApi

class VcenterGatewayOrch(VcenterOrchestrator):

    def __init__(self, inputs, host, port, user, pwd, dc_name, vnc, logger):
        super(VcenterGatewayOrch, self).__init__(inputs, host, port, user, pwd, dc_name, vnc, logger)
        self.plug_api = ContrailPlugApi(inputs,vnc,logger)

    def create_vn(self, name, subnets, **kwargs):
        vn_obj = super(VcenterGatewayOrch, self).create_vn(name, subnets, **kwargs)
        self.plug_api.create_network_in_contrail_cluster(name,subnets,**kwargs)
        return vn_obj
    
    def delete_vn(self, vn_obj, **kwargs):
        super(VcenterGatewayOrch, self).delete_vn(vn_obj, **kwargs)
        self.plug_api.delete_network_from_contrail_cluster(vn_obj.name,**kwargs)

    def create_vm(self, vm_name, image_name, vn_objs, count=1, zone=None, node_name=None, **kwargs):
        vm_objs = super(VcenterGatewayOrch, self).create_vm(vm_name, image_name, vn_objs, count=1, zone=None, node_name=None, **kwargs)
        retry_vms = []
        retry_vms = vm_objs[:]
        for vm in retry_vms:
            if self.get_vm_detail(vm):
                retry_vms.remove(vm) 
            else:
                continue    
        for vm in vm_objs:
            for network in vm.networks:
                vlanId = network.config.defaultPortConfig.vlan.vlanId
                net_name = network.name
                if net_name in vm.macs:
                    mac = vm.macs[net_name]
                else:
                    mac = None  
                self.plug_api.create_vmi_lif_and_attach_vmi_to_lif(vn_name=net_name,mac_address=mac,vlan=vlanId,vm=vm)
 
        for vm in vm_objs:
            vm.bring_up_interfaces(self,vm,intfs=['eth0'])
        for vm in vm_objs:
            vm.get()
            self.plug_api.create_vmobj_in_api_server(vm)
        return vm_objs
    
    def create_vn_vmi_for_stp_bpdu_to_be_flooded(self,**kwargs):
        self.plug_api.create_network_in_contrail_cluster(name='stp_vn',subnet=[{'cidr':'122.121.123.0/24'}],**kwargs)
       	#The below code is needed for not to 
        #create the stp vmi port if already exists 
        #		
        interfaces = self._vnc.virtual_machine_interfaces_list()
        for intf in interfaces['virtual-machine-interfaces']:
            uuid = intf['uuid']
            intf_obj = self._vnc.virtual_machine_interface_read(id=uuid)
            mac_obj = intf_obj.get_virtual_machine_interface_mac_addresses()
            macs = mac_obj.mac_address 
            if macs: 
                for mac in macs:
                    if mac == '02:02:03:04:05:06':
                        return
        self.plug_api.create_vmi_lif_and_attach_vmi_to_lif(vn_name='stp_vn',mac_address='02:02:03:04:05:06',vlan='0')

    def delete_vm(self, vm, **kwargs):
        super(VcenterGatewayOrch, self).delete_vm(vm, **kwargs)
        self.plug_api.delete_vmi_and_detach_vmi_to_lif(vm)
        self.plug_api.delete_vmobj_in_api_server(vm)

class ContrailPlugApi(object):
    def __init__(self, inputs, vnc, logger):
        self._inputs = inputs
        self._vnc = vnc
        self.logger = logger
        self._proj_obj = self._get_project_object()
        self._ipam_obj = self._get_ipam_object()
        self._gw = self._process_vcenter_gateway_info()
        self.vnc_h = ContrailVncApi(self._vnc, self.logger)

    def _get_project_object(self):
        return self._vnc.project_read(fq_name = self._inputs.project_fq_name)

    def _get_ipam_object(self):
        return self._vnc.network_ipam_read(
                fq_name=['default-domain', 'default-project', 'default-network-ipam'])

    def create_network_in_contrail_cluster(self,name,subnet,**kwargs):
        self.vn_uuid = self._create_vn(name,subnet)
        pass

    def delete_network_from_contrail_cluster(self,vn_name,**kwargs):
        self._delete_vn(vn_name)
        pass

    def delete_vmi_and_detach_vmi_to_lif(self,vm):
        self.delete_lif(vm)        
        self._delete_vmi(vm) 

    def delete_lif(self,vm):
        self._delete_lif(vm)

    def create_vmobj_in_api_server(self,vm_obj):
        vm_uuid = vm_obj.id 
        try:
            self.vnc_h.create_virtual_machine(vm_uuid=vm_uuid)
        except Exception as e:
            self.logger.error("VM object create in api failed for vm id %s"%(vm_uuid)) 
            raise
        vm_api_obj = self._vnc.virtual_machine_read(id=vm_obj.id)
        for port in vm_obj.ports:
            port_uuid = port.uuid
            port_obj = self._vnc.virtual_machine_interface_read(id=port_uuid)
            port_obj.set_virtual_machine(vm_api_obj)
            self._vnc.virtual_machine_interface_update(port_obj)
    
    def delete_vmobj_in_api_server(self,vm_obj):
        vm_uuid = vm_obj.id 
        try:
            self.vnc_h.delete_virtual_machine(vm_uuid=vm_uuid)
        except Exception as e:
            self.logger.error("VM object delete in api failed for vm id %s"%(vm_uuid)) 

    def create_vmi_lif_and_attach_vmi_to_lif(self,vn_name,mac_address,vlan,vm=None):
        vn_obj = self._read_vn(vn_name) 
        vn_id = vn_obj.uuid
        #create vmi
        port = self._create_vmi(vn_id=vn_id,mac_address=mac_address,
                    vm=vm )
        #for each vrouter gateway port , create lif 
        for gw in self._gw:
            for phy_port in gw.ports:
                lif_name = phy_port + '.' + str(vlan)
                pif_id = gw.get_port_uuid(phy_port)  
                self._create_lif(lif_name,vlan,pif_id,vm=vm,vmi_ids = [port.uuid])

    def _create_vn(self, vn_name, vn_subnet):

        vn_obj = VirtualNetwork(vn_name, parent_obj=self._proj_obj)
        for pfx in vn_subnet:
            px = pfx['cidr'].split('/')[0]
            pfx_len = int(pfx['cidr'].split('/')[1])
            subnet_vnc = IpamSubnetType(subnet=SubnetType(px, pfx_len))
            vnsn_data = VnSubnetsType([subnet_vnc])
            vn_obj.add_network_ipam(self._ipam_obj, vnsn_data)
        try:
            self._vnc.virtual_network_create(vn_obj)
        except RefsExistError:
            pass

    def _delete_vn(self, vn_name):
        vn_fq_name = VirtualNetwork(vn_name, self._proj_obj).get_fq_name()
        try:
            self._vnc.virtual_network_delete(fq_name=vn_fq_name)
        except cfgm_common.exceptions.NoIdError:
            pass
    # end _delete_vn
 
    def _read_vn(self,vn_name):
        vn_fq_name = VirtualNetwork(vn_name, self._proj_obj).get_fq_name()
        try:
            vn_obj = self._vnc.virtual_network_read(fq_name=vn_fq_name)
        except cfgm_common.exceptions.NoIdError:
            pass
        return vn_obj

    def _create_lif(self,name,vlan,pif_id,vmi_ids=[],vm=None):
        lif_obj = LogicalInterfaceFixture(
        name, pif_id=pif_id, vlan_id=vlan,vmi_ids=vmi_ids)
        lif_obj.setUp()
        if vm:
            vm.lifs.append(lif_obj)

    def _delete_lif(self,vm):
        for lif in vm.lifs:
            lif.cleanUp()

    def _create_vmi(self,vn_id,mac_address,
                     fixed_ips=[],security_groups=[],
                     extra_dhcp_opts=[],
                     project_obj=None,vm=None):
        port = PortFixture(vn_id,
                                api_type='contrail',
                                mac_address=mac_address,
                                fixed_ips=fixed_ips,
                                extra_dhcp_opts=extra_dhcp_opts,
                                project_obj=self._proj_obj,
                                security_groups=security_groups)
        port.setUp()
        if vm:
            vm.ports.append(port)
        return port

    def _delete_vmi(self,vm):
        for port in vm.ports:
            port.cleanUp()

    def _process_vcenter_gateway_info(self):
        return [VcenterGateway(gw) for gw in self._inputs.vcenter_gateway]


class VcenterGateway:
    """Represents one vcenter gateway."""

    def __init__(self,gateway):
        self.gateway = gateway

    @property
    def name(self):
        return self.gateway['name']
    
    @property
    def mgmt_ip(self):
        return self.gateway['mgmt_ip']
 
    @property
    def ports(self):
        return self.gateway['ports']
        
    def get_port_uuid(self,port):
        phy_device_fixture=PhysicalDeviceFixture(self.name,self.mgmt_ip)
        phy_device_fixture.setUp()
        phy_device_uuid = phy_device_fixture.phy_device.uuid
        pif_fixture=PhysicalInterfaceFixture(port,device_id=phy_device_uuid)
        pif_fixture.setUp()
        return pif_fixture.uuid
