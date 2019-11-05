from builtins import str
from builtins import next
from builtins import range
import test_v1
from common.device_connection import NetconfConnection
import physical_device_fixture
from physical_router_fixture import PhysicalRouterFixture
from tcutils.contrail_status_check import *
from fabric.api import run, hide, settings
from common.servicechain.verify import VerifySvcChain
from vn_test import VNFixture
from vm_test import VMFixture
from vnc_api.vnc_api import *
from tcutils.util import get_random_name
from common.securitygroup.verify import VerifySecGroup
from common import isolated_creds, create_public_vn
from time import sleep
import os
import re

class BaseDM(VerifySecGroup):

    @classmethod
    def setUpClass(cls):
        super(BaseDM, cls).setUpClass()
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
        if cls.inputs.admin_username:
            public_creds = cls.admin_isolated_creds
        else:
            public_creds = cls.isolated_creds
        cls.public_vn_obj = create_public_vn.PublicVn(
            public_creds,
            cls.inputs,
            input_file=cls.input_file,
            logger=cls.logger)
        cls.public_vn_obj.configure_control_nodes()

    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseDM, cls).tearDownClass()
    # end tearDownClass

    def setUp(self):
        super(BaseDM, self).setUp()

    def tearDown(self):
        super(BaseDM, self).tearDown()

    def config_basic(self):

        self.create_physical_dev()
        self.create_vn()
  
    def create_physical_dev(self):

        #mx config using device manager
        self.phy_router_fixture = {}
        if self.inputs.ext_routers:
            if self.inputs.use_devicemanager_for_md5:
                j = 0
                self.mx_handle = {}
                for i in range(len(list(self.inputs.dm_mx.values()))):
                    router_params = list(self.inputs.dm_mx.values())[i]
                    if router_params['model'] == 'mx':
                        self.phy_router_fixture[j] = self.useFixture(PhysicalRouterFixture(
                            router_params['name'], router_params['control_ip'],
                            model=router_params['model'],
                            vendor=router_params['vendor'],
                            asn=router_params['asn'],
                            ssh_username=router_params['ssh_username'],
                            ssh_password=router_params['ssh_password'],
                            mgmt_ip=router_params['control_ip'],
                            connections=self.connections,
                            dm_managed=True))
                        physical_dev = self.vnc_lib.physical_router_read(id = self.phy_router_fixture[j].phy_device.uuid)
                        physical_dev.set_physical_router_management_ip(router_params['mgmt_ip'])
                        physical_dev.set_physical_router_dataplane_ip(router_params['mgmt_ip'])
                        physical_dev._pending_field_updates
                        self.vnc_lib.physical_router_update(physical_dev)
                        self.mx_handle[j] = self.phy_router_fixture[j].get_connection_obj('juniper',
                            host=router_params['control_ip'],
                            username=router_params['ssh_username'],
                            password=router_params['ssh_password'],
                            logger=[self.logger])

                        j += 1

    def create_vn(self):
        #Script has run till now with the same name and subnets. Lets change it!
        self.vn1_name = "test_DM_v4_only"
        self.vn1_net = ['12.6.2.0/24']
        #router external tag will cause DM ip allocation problem. Changing it to false
        self.vn1_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=self.vn1_name, inputs=self.inputs, subnets=self.vn1_net, router_external=False, shared = False))
        #assert self.vn1_fixture.verify_on_setup()
        self.add_RT_basic_traffic()

        self.vn2_name = "test_DM_dual_stack"
        self.vn2_net = ['2001::101:0/120']
        self.vn2_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=self.vn2_name, inputs=self.inputs, subnets=self.vn2_net))
        #assert self.vn2_fixture.verify_on_setup()

        self.vm1_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=self.vn1_fixture.obj, vm_name='sender', node_name=None,
            image_name='cirros', flavor='m1.tiny'))

    def add_multiple_vns(self):
        self.vn3_name = "test_vn3"
        self.vn3_net = ['2.1.1.0/24']
        self.vn3_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=self.vn3_name, inputs=self.inputs, subnets=self.vn3_net, router_external=True))
        assert self.vn3_fixture.verify_on_setup()
        self.vm3_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=self.vn3_fixture.obj, vm_name='receiver', node_name=None,
            image_name='cirros', flavor='m1.tiny'))

    def send_traffic_between_vms(self):
        self.change_global_vn_config('l3')
        sleep(90)
        cmd = 'show configuration groups __contrail__ interfaces lo0 unit 10%s family inet' % self.vn_index
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()
        lo_ip = re.findall('address (.+)\/32', self.output_from_mx[0])[0]
        assert self.vm1_fixture.ping_with_certainty(lo_ip), 'Ping to lo0 ip not passing'

        self.change_global_vn_config('l2_l3')
        sleep(90)
        cmd = 'show configuration groups __contrail__ interfaces irb unit %s family inet' % self.vn_index
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()
        irb_ip = re.findall('address (.+)\/24', self.output_from_mx[0])[0]
        assert self.vm1_fixture.ping_with_certainty(irb_ip), 'Ping to irb ip not passing'

    def send_traffic_with_multiple_vns(self):
        self.change_global_vn_config('l3')
        sleep(90)
        new_vn_index = self.vnc_lib.virtual_network_read(id = self.vn3_fixture.uuid).virtual_network_network_id
        cmd = 'show configuration groups __contrail__ interfaces lo0 unit 10%s family inet' % new_vn_index
        self.does_mx_have_config(cmd)
        self.is_dm_going_through()
        lo_ip = re.findall('address (.+)\/32', self.output_from_mx[0])[0]
        self.change_global_vn_config('l2_l3')
        assert self.vm3_fixture.ping_with_certainty(lo_ip), 'Ping to lo0 ip not passing'

    def remove_iptable_config(self):
        for i in range(len(list(self.inputs.physical_routers_data.values()))):
            router_params = list(self.inputs.physical_routers_data.values())[i]

            cmd = '/sbin/iptables -D OUTPUT -d %s -j DROP' % router_params['mgmt_ip']
            for node in self.inputs.cfgm_ips:
                dm_status = self.inputs.run_cmd_on_server(node, cmd)

    def get_output_from_node(self, cmd):
        i = 0
        self.output_from_mx = {}
        for dev_handle in list(self.mx_handle.values()):
            self.output_from_mx[i] = dev_handle.handle.cli(cmd)
            i += 1

    def check_mx_output(self, cmd):
        self.get_output_from_node(cmd)
        i = 0
        for i in range(len(self.output_from_mx)):
            if 'invalid command' in self.output_from_mx[i]:
                return False, str(self.phy_router_fixture[i].name)
        return True, 'all mx have correct output' 

    def delete_vn_from_devices(self):

        for dev_fixture in list(self.phy_router_fixture.values()):
            dev_fixture.delete_virtual_network(str(self.vn1_fixture.uuid))
            dev_fixture.delete_virtual_network(str(self.vn2_fixture.uuid))

    def delete_physical_devices(self):

        for dev_fixture in list(self.phy_router_fixture.values()):
            dev_fixture.delete_device()

    def unbind_dev_from_router(self):

        for dev_fixture in list(self.phy_router_fixture.values()):
            bgp_fq_name = ['default-domain', 'default-project','ip-fabric', '__default__', str(dev_fixture.name)]
            bgp_router = self.vnc_lib.bgp_router_read(fq_name=bgp_fq_name)
            dev_fixture.unbind_bgp_router(bgp_router)

    def does_mx_have_config(self, cmd):

        for i in range(1,13):
            self.op, self.bad_mx = self.check_mx_output(cmd)
            if not self.op:
                sleep(10)
            else:
                break
        self.iteration = i

    def is_dm_going_through(self):

        assert not (self.iteration == 12), "DM VN config not pushed even after 120 sec"
        assert self.op, "DM config on %s not going through. Check the MX" % self.bad_mx

    def is_dm_removed(self):

        assert not (self.iteration == 12), "DM VN config not removed even after 120 sec"
        assert self.op, "DM config on %s not removed. Check the MX" % self.bad_mx

    def remove_nc_config(self):
        for dev_fixture in list(self.phy_router_fixture.values()):
            physical_dev = self.vnc_lib.physical_router_read(id = dev_fixture.phy_device.uuid)
            physical_dev.set_physical_router_vnc_managed(False)
            physical_dev._pending_field_updates
            self.vnc_lib.physical_router_update(physical_dev)

    def add_nc_config(self):

        for dev_fixture in list(self.phy_router_fixture.values()):
            physical_dev = self.vnc_lib.physical_router_read(id = dev_fixture.phy_device.uuid)
            physical_dev.set_physical_router_vnc_managed(True)
            physical_dev._pending_field_updates
            self.vnc_lib.physical_router_update(physical_dev)

    def bind_dev_to_router(self):

        for dev_fixture in list(self.phy_router_fixture.values()):
            bgp_fq_name = ['default-domain', 'default-project','ip-fabric', '__default__', str(dev_fixture.name)]
            bgp_router = self.vnc_lib.bgp_router_read(fq_name=bgp_fq_name)
            dev_fixture.add_bgp_router(bgp_router)

    def add_vn_to_device(self):

        for dev_fixture in list(self.phy_router_fixture.values()):
            dev_fixture.add_virtual_network(str(self.vn1_fixture.uuid))
            dev_fixture.add_virtual_network(str(self.vn2_fixture.uuid))

    def change_vtep(self):

        for dev_fixture in list(self.phy_router_fixture.values()):
            physical_dev = self.vnc_lib.physical_router_read(id = dev_fixture.phy_device.uuid)
            physical_dev.set_physical_router_dataplane_ip(str('10.20.30.40'))
            physical_dev._pending_field_updates
            self.vnc_lib.physical_router_update(physical_dev)

    def change_vn_forwarding_mode(self, mode):

        self.vn1_fixture.add_forwarding_mode(project_fq_name=self.inputs.project_fq_name, vn_name=self.vn1_name, forwarding_mode = mode)
        self.vn2_fixture.add_forwarding_mode(project_fq_name=self.inputs.project_fq_name, vn_name=self.vn2_name, forwarding_mode = mode) 

    def change_global_vn_config(self, mode):

        global_vrouter_id = self.vnc_lib.get_default_global_vrouter_config_id()
        global_config = self.vnc_lib.global_vrouter_config_read(id=global_vrouter_id)
        global_config.set_forwarding_mode(mode)
        self.vnc_lib.global_vrouter_config_update(global_config)

    def remove_global_vn_config(self):

        global_vrouter_id = self.vnc_lib.get_default_global_vrouter_config_id()
        global_config = self.vnc_lib.global_vrouter_config_read(id=global_vrouter_id)
        global_config.set_forwarding_mode('l2_l3')
        self.vnc_lib.global_vrouter_config_update(global_config)

    def add_RT_basic_traffic(self):

        self.vn1_fixture.add_route_target(self.vn1_fixture.ri_name, self.inputs.router_asn, '98765')

    def add_vn_RT(self, value, mode='both'):
        rtgt_val = "target:%s:%s" % (self.inputs.router_asn, value)
        route_targets = RouteTargetList([rtgt_val])
        if mode == 'import':
            vn_handle = self.vnc_lib.virtual_network_read(id=self.vn1_fixture.uuid)
            vn_handle.set_import_route_target_list(route_targets)
            self.vnc_lib.virtual_network_update(vn_handle)
        if mode == 'export':
            vn_handle = self.vnc_lib.virtual_network_read(id=self.vn1_fixture.uuid)
            vn_handle.set_export_route_target_list(route_targets)
            self.vnc_lib.virtual_network_update(vn_handle)
        if mode == 'both':
            self.vn1_fixture.add_route_target(self.vn1_fixture.ri_name, self.inputs.router_asn, value)

    def del_vn_RT(self, value, mode = 'both'):
        route_targets = RouteTargetList([])
        if mode == 'import':
            vn_handle = self.vnc_lib.virtual_network_read(id=self.vn1_fixture.uuid)
            vn_handle.set_import_route_target_list(route_targets)
            self.vnc_lib.virtual_network_update(vn_handle)
        if mode == 'export':
            vn_handle = self.vnc_lib.virtual_network_read(id=self.vn1_fixture.uuid)
            vn_handle.set_export_route_target_list(route_targets)
            self.vnc_lib.virtual_network_update(vn_handle)
        if mode == 'both':
            self.vn1_fixture.del_route_target(self.vn1_fixture.ri_name, self.inputs.router_asn, value)

    def check_policy_added_on_mx(self, cmd, rt_value):

        for i in range(len(self.output_from_mx)):
            for j in range(1,13):
                self.does_mx_have_config(cmd)
                self.is_dm_going_through()
                if not rt_value in self.output_from_mx[i]:
                    sleep(10)
                else:
                    break
            if j == 12:
                assert False, "Policy not added after 120 sec" 
        return True

    def check_policy_removed_on_mx(self, cmd, rt_value):

        for i in range(len(self.output_from_mx)):
            for j in range(1,13):
                self.does_mx_have_config(cmd)
                self.is_dm_removed()
                if rt_value in self.output_from_mx[i]:
                    sleep(10)
                else:
                    break
            if j == 12:
                assert False, "Policy not deleted after 120 sec"    
        return True

    def get_old_as(self):

        global_system_id = self.vnc_lib.get_default_global_system_config_id()
        global_system_config = self.vnc_lib.global_system_config_read(id=global_system_id)
        self.old_as = global_system_config.get_autonomous_system()
        return self.old_as

    def change_global_AS(self, value):

        global_system_id = self.vnc_lib.get_default_global_system_config_id()
        global_system_config = self.vnc_lib.global_system_config_read(id=global_system_id)
        global_system_config.set_autonomous_system(value)
        self.vnc_lib.global_system_config_update(global_system_config)

    def change_mx_AS(self, value):

        for host in self.list_uuid:
            rparam = self.vnc_lib.bgp_router_read(id=host).bgp_router_parameters
            bgp_uuid = self.vnc_lib.bgp_router_read(id=host)
            rparam.set_autonomous_system(value)
            bgp_uuid.set_bgp_router_parameters(rparam)
            self.vnc_lib.bgp_router_update(bgp_uuid)

    def verify_mx_AS_different(self):
        cmd = 'show configuration groups __contrail__ routing-options autonomous-system'
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        global_as = re.findall('\d+', self.output_from_mx[0])[0]
        cmd = 'show configuration groups __contrail__ protocols bgp group __contrail_external__ neighbor %s peer-as' % self.inputs.bgp_ips[0] 
        self.does_mx_have_config(cmd)

        self.is_dm_going_through()
        local_auto = re.findall('\d+', self.output_from_mx[0])[0]
        assert not (global_as == local_auto), "Global and local AS should not be same"

    def scale_vns(self):

        generator = iter_iprange('111.1.1.0', '111.255.255.0', step=256)
        for i in range(1,2000):
            vn_scale_name = "test_%s_vn" % i
            vn_scale_net = (str(next(generator))+str('/24')).split()
            vn_scale_fixture = self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections, option='contrail',
                vn_name=vn_scale_name, inputs=self.inputs, subnets=vn_scale_net, router_external=True))
            #assert vn_scale_fixture.verify_on_setup()
            for dev_fixture in list(self.phy_router_fixture.values()):
                dev_fixture.add_virtual_network(str(vn_scale_fixture.uuid))

