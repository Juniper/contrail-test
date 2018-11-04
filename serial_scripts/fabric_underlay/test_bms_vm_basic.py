import traffic_tests
from vn_test import *
from vm_test import *
from vm_regression.base import BaseVnVmTest
from bms_fixture import BMSFixture
from floating_ip import *
from policy_test import *
from user_test import UserFixture
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from common import isolated_creds
import inspect
import time
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from tcutils.util import get_subnet_broadcast
from tcutils.util import skip_because
import test
from common.contrail_fabric.base import BaseFabricTest
from physical_router_fixture import PhysicalRouterFixture
from physical_device_fixture import PhysicalDeviceFixture

class TestBasicBMSVMVN(BaseFabricTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicBMSVMVN, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBasicBMSVMVN, cls).tearDownClass()

    def setUp(self):
       super(TestBasicBMSVMVN, self).setUp()
       self.create_ironic_provision_vn()

    def runTest(self):
        pass

    def tearDown(self):
       super(TestBasicBMSVMVN, self).tearDown()

    #end runTes

    def create_ironic_provision_vn(self):

        '''
        Description: Create ironic-provision VN and attach to MX and QFXs
        Maintainer: vageesant@juniper.net
        '''

        for host_data in self.inputs.host_data.iteritems():
          for static_route in host_data[1]['static_routes']:
            self.inputs.run_cmd_on_server(host_data[1]['host_ip'],static_route)

        bms_lcm_config = self.inputs.bms_lcm_config
        self.vn1_name = bms_lcm_config["ironic_provision_vn"]["name"]
        self.vn1_net = [bms_lcm_config["ironic_provision_vn"]["subnet"]]

        self.inputs.project_name = "admin"
        self.ironic_vn_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=self.vn1_name, inputs=self.inputs, subnets=self.vn1_net, router_external=True, shared = True,dns_nameservers_list=[self.inputs.internal_vip]))
        self.ironic_vn_fixture.setUp()

        self.inputs.restart_container([self.inputs.openstack_ip],'ironic_conductor')

        for device in self.fabric.fetch_associated_devices():
            device_fixture = PhysicalDeviceFixture(connections=self.connections,
                                                       name=device)
            device_fixture.read()
            device_fixture.add_virtual_network(self.ironic_vn_fixture.vn_id)
            self.addCleanup(device_fixture.delete_virtual_network, self.ironic_vn_fixture.vn_id)

    def reconfigure_block_size_tftp(self):

        node_ip = self.inputs.openstack_ip
        bms_lcm_config = self.inputs.bms_lcm_config
        tftp_config_file_url = bms_lcm_config["tftp"]["config_url"]
        cmd = "wget %s -O /etc/kolla/ironic-pxe/config.json" %(tftp_config_file_url)
        output = self.inputs.run_cmd_on_server(node_ip, cmd)

        self.inputs.restart_container([self.inputs.openstack_ip],'ironic_pxe')

        mtu_conf_cmd = bms_lcm_config["tftp"]["mtu"]
        output = self.inputs.run_cmd_on_server(node_ip, cmd)

    def check_ping_from_mx(self):
        internal_vip = self.inputs.internal_vip
        devices = self.inputs.physical_routers_data.keys()
        for device in self.inputs.physical_routers_data.iteritems():
            router_params = device[1]
            if router_params['role'] == 'spine':
               phy_router_fixture = self.useFixture(PhysicalRouterFixture(
                            router_params['name'], router_params['control_ip'],
                            model="mx",
                            vendor=router_params['vendor'],
                            asn=router_params['asn'],
                            ssh_username=router_params['ssh_username'],
                            ssh_password=router_params['ssh_password'],
                            mgmt_ip=router_params['control_ip'],
                            do_cleanup=False,
                            connections=self.connections))

               mx_handle = phy_router_fixture.get_connection_obj('juniper',
                    host=router_params['control_ip'],
                    username=router_params['ssh_username'],
                    password=router_params['ssh_password'],
                    logger=[self.logger])
               cmd = "ping %s wait 1"%internal_vip
               output = mx_handle.handle.cli(cmd)
               self.logger.debug(output)
               cmd = "run show bgp summary | display xml rpc"
               output = mx_handle.handle.cli(cmd)
               self.logger.debug(output)

    def update_project_nova_quota(self):
        project_id = self.connections.project_id
        ram_quota = -1
        cores     = -1
        self.connections.nova_h.obj.quotas.update(re.sub("-","",project_id),ram=ram_quota)
        self.connections.nova_h.obj.quotas.update(re.sub("-","",project_id),cores=cores)

    def bms_delete_nodes(self,bms_name=None,all_bms=False):
        node_list = self.connections.ironic_h.obj.node.list()
        for node in node_list:
            self.connections.ironic_h.obj.node.delete(node.uuid)

    @preposttest_wrapper
    def bms_node_add_delete(self,bms_type=None):
        '''
          Description: Create BMS ironic node
          Test steps:

          Maintainer: vageesant@juniper.net
        '''
        bms_lcm_config = self.inputs.bms_lcm_config
        bms_nodes = self.inputs.bms_data
        base_kernel_image = bms_lcm_config["deploy_kernel"]
        base_ramdisk_image = bms_lcm_config["deploy_ramdisk"]

        if bms_type == "all":
          bms_nodes_filtered = []
          for k,v in bms_nodes.iteritems():
              v['node_name'] = k
              bms_nodes_filtered.append(v)
        else:
          bms_nodes_filtered = []
          for k,v in bms_nodes.iteritems():
              if v['bms_type'] == bms_type:
                 v['node_name'] = k
                 bms_nodes_filtered.append(v)

        if len(bms_nodes_filtered) == 0:
           return

        self.bms_fixture = self.useFixture(BMSFixture(self.connections,bms_nodes_filtered[0]['node_name'],is_ironic_node=True))
        base_kernel_uuid  = self.bms_fixture.connections.nova_h.get_image(base_kernel_image)['id']
        base_ramdisk_uuid = self.bms_fixture.connections.nova_h.get_image(base_ramdisk_image)['id']

        for bms_node in bms_nodes_filtered:
            self.bms_fixture = self.useFixture(BMSFixture(self.connections,bms_node['node_name'],is_ironic_node=True))
            driver_info = bms_node["driver_info"]
            properties  = bms_node['properties']
            driver_info['deploy_ramdisk']     = base_ramdisk_uuid
            driver_info['deploy_kernel']      = base_kernel_uuid

            interfaces = bms_node['interfaces']
            port_list = []
            for interface in interfaces:
                local_link_connection = {}
                local_link_connection['mac_addr']    = interface['host_mac']
                local_link_connection['switch_info'] = interface['tor']
                local_link_connection['switch_id']   = interface['switch_id']
                local_link_connection['pxe_enabled'] = interface['pxe_enabled']
                local_link_connection['port_id']     = interface['tor_port']
                port_list.append(local_link_connection)

            self.bms_fixture.create_bms_node(ironic_node_name=bms_node['node_name'],port_list=port_list,driver_info=driver_info,properties=properties)
            self.bms_fixture.set_bms_node_state("available")

        self.logger.debug(self.bms_fixture.connections.ironic_h.obj.node.list())
        #self.bms_fixture.delete_ironic_node()
        #print self.bms_fixture.ironic_h.obj.node.list()

    @preposttest_wrapper
    def test_bms_single_interface(self):
        '''
        Description: Test BMS LCM scenario for single interface BMS node
        Test Steps:
           1. Delete all existing BMS nodes and create only one ironic node - the host which has single interface
           2. Update SG to allow ping/traffic between BMS VM and regular VM
           3. Reconfigure TFTP Block size and ip link MTU
           4. Bringup one BMS LCM instance and one VM.Verify ping between VM and BMS VM instance works.
        Maintainer: vageesant@juniper.net
        '''

        self.project.set_sec_group_for_allow_all()
        self.bms_delete_nodes()
        self.bms_node_add_delete(bms_type="single_interface")
        time.sleep(60)
        self.update_project_nova_quota()
        self.reconfigure_block_size_tftp()
        self.bms_vm_add_delete(bms_count=1)

    @preposttest_wrapper
    def test_bms_multi_homing(self):
        '''
        Description: Test BMS LCM scenario for multi homing - BMS node with two interface.interface1 in qfx1 and interface2 in qfx2
        Test Steps:
           1. Delete all existing BMS nodes and create only one ironic node - the host which has two interface- interface1 in qfx1 and interace2 in qfx2
           2. Update SG to allow ping/traffic between BMS VM and regular VM
           3. Reconfigure TFTP Block size and ip link MTU
           4. Bringup one BMS LCM instance and one VM.Verify ping between VM and BMS VM instance works.
        Maintainer: vageesant@juniper.net
        '''

        self.project.set_sec_group_for_allow_all()
        self.bms_delete_nodes()
        self.bms_node_add_delete(bms_type="multi_homing")
        time.sleep(60)
        self.update_project_nova_quota()
        self.reconfigure_block_size_tftp()
        self.bms_vm_add_delete(bms_count=1)

    @preposttest_wrapper
    def test_bms_lag(self):
        '''
        Description: Test BMS LCM scenario for LAG - Link Aggregation - BMS node with two interface.interface1 and interface2 both in the same qfx
        Test Steps:
           1. Delete all existing BMS nodes and create only one ironic node - the host which has two interface- interface1 interface2 both in the same qfx.
           2. Update SG to allow ping/traffic between BMS VM and regular VM
           3. Reconfigure TFTP Block size and ip link MTU
           4. Bringup one BMS LCM instance and one VM.Verify ping between VM and BMS VM instance works.
        Maintainer: vageesant@juniper.net
        '''

        self.project.set_sec_group_for_allow_all()
        self.bms_delete_nodes()
        self.bms_node_add_delete(bms_type="link_aggregation")
        time.sleep(60)
        self.update_project_nova_quota()
        self.reconfigure_block_size_tftp()
        self.bms_vm_add_delete(bms_count=1)

    @preposttest_wrapper
    def test_bms_all(self):
        '''
        Description: SuperSet testcase for Single Interface BMS,LAG Scenario and Multi-homing scenario
        Test Steps:
           1. Delete all existing BMS nodes and create only one ironic node - the host which has two interface- interface1 interface2 both in the same qfx.
           2. Update SG to allow ping/traffic between BMS VM and regular VM
           3. Reconfigure TFTP Block size and ip link MTU
           4. Bringup one BMS LCM instance and one VM.Verify ping between VM and BMS VM instance works.
        Maintainer: vageesant@juniper.net
        '''

        self.bms_delete_nodes()
        self.bms_node_add_delete("all")
        self.update_project_nova_quota()
        self.reconfigure_block_size_tftp()
        self.bms_vm_add_delete(bms_count=3)

    def bms_vm_add_delete(self,bms_count=1):
        '''
        Not run as separate test.
        Will be called by test_bms_single_interface or  test_bms_multi_homing or test_bms_lag
        Test Step:
            1. Create tenant VN
            2. Create N BMS instance.
            3. Create regular VM and verify ping from VM to BMS VM instance works.

        Maintainer : vageesant@juniper.net
        '''

        bms_lcm_config = self.inputs.bms_lcm_config
        bms_nodes = self.inputs.bms_data
        bms_image = bms_lcm_config['bms_image']
        vm_image  = bms_lcm_config['vm']['glance_image']
        bms_availability_zone = bms_lcm_config['availability_zone']
        bms_availability_host = bms_lcm_config['availability_host']

        vn_fixture = self.create_vn()
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj

        vm_fixture = self.create_vm(vn_fixture=vn_fixture,image_name='ubuntu-traffic',zone="nova",vm_name=get_random_name('vm_add_delete'))

        bms_fixtures_list = []
        for i in xrange(bms_count):
            bms_vm_name = get_random_name('bms_vm_add_delete')
            bms_fixtures_list.append(self.create_vm(vn_fixture=vn_fixture,image_name=bms_image,zone=bms_availability_zone,node_name=bms_availability_host, vm_name=bms_vm_name,instance_type="baremetal"))

        for bms_fixture in bms_fixtures_list:
            assert bms_fixture.verify_on_setup()

        assert vm_fixture.verify_on_setup()

        for bms_fixture in bms_fixtures_list:
            for i in xrange(5):
               ping_result = vm_fixture.ping_with_certainty(bms_fixture.vm_ip)
               if ping_result:
                  break
        assert ping_result
        return True


