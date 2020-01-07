from common.contrail_fabric.ztp_base import ZtpBaseTest
from tcutils.wrappers import preposttest_wrapper
import time

class TestZtp(ZtpBaseTest):

    def setUp(self):
        for device, device_dict in list(self.inputs.physical_routers_data.items()):
            if 'dc_gw' in (device_dict.get('rb_roles') or []):
                if device_dict['role'] == 'spine':
                    self.rb_roles[device] = ['DC-Gateway', 'Route-Reflector']
        super(TestZtp, self).setUp()

    @preposttest_wrapper
    def test_ztp_basic(self):
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')
        bms_fixtures = list()
        # Test Leafs
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='cirros-0.4.0')
        for bms in self.get_bms_nodes():
            bms_fixtures.append(self.create_bms(bms_name=bms, vlan_id=10,
                vn_fixture=vn))
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures + [vm1])

        # Test Spines
        vn2 = self.create_vn()
        self.create_logical_router([vn, vn2])
        vm2 = self.create_vm(vn_fixture=vn2, image_name='cirros-0.4.0')
        for bms in list(bms_fixtures):
            bms_fixtures.append(self.create_bms(bms_name=bms.name, vlan_id=20,
                vn_fixture=vn2, bond_name=bms.bond_name,
                port_group_name=bms.port_group_name))
        vm2.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures + [vm1, vm2])

    @preposttest_wrapper
    def test_ztp_public_connectivity_from_vm_bms(self):
        '''
        1)on board fabric with dc_gateway role to mx
        2)Add bms to leaf
        3)create public vn,ping to 8.8.8.8 from bms
        4)Create Vm,associate fip to vm
        5)ping to 8.8.8.8 from vm
        '''
        bms_fixtures = list()
        public_vn = self.create_vn(vn_subnets=self.inputs.public_subnets[:1],
                                   router_external=True)
        private_vn = self.create_vn()
        fip_pool = self.create_fip_pool(public_vn.uuid)
        for bms in list(self.inputs.bms_data.keys()):
            bms_fixture = self.create_bms(bms_name=bms, vn_fixture=public_vn)
            bms_fixtures.append(bms_fixture)
        for spine in self.spines:
            prouter_details = self.inputs.physical_routers_data[spine.name]
            if prouter_details.get('model', '').startswith('mx'):
                spine.add_virtual_network(public_vn.uuid)
                self.addCleanup(spine.delete_virtual_network, public_vn.uuid)
        vm = self.create_vm(vn_fixture=private_vn, image_name='cirros-0.4.0')
        self.check_vms_booted([vm])
        self.create_and_assoc_fip(fip_pool, vm)
        for fixture in bms_fixtures + [vm]:
            msg = 'ping from %s to %s failed'%(fixture.name,
                                               self.inputs.public_host)
            assert fixture.ping_with_certainty(self.inputs.public_host),msg

    @preposttest_wrapper
    def test_ztp_restart_dm_api_server(self):
        '''
        1)on board fabric with dc_gateway role to mx
        2)Create Vm
        3)ping to 8.8.8.8 from vm
        4)restart api container
        5)ping should pass to 8.8.8.8
        6)restart dm
        7)ping should pass to 8.8.8.8
        8)stop dm, make some config,start dm,
        9)verify config changes pushed by dm
        '''
        public_vn = self.create_vn(vn_subnets=self.inputs.public_subnets[:1],
                                   router_external=True)
        fip_pool = self.create_fip_pool(public_vn.uuid)
        private_vn = self.create_vn()
        for spine in self.spines:
            spine.add_virtual_network(public_vn.uuid)
            self.addCleanup(spine.delete_virtual_network, public_vn.uuid)
        vm = self.create_vm(vn_fixture=private_vn, image_name='cirros-0.4.0')
        self.check_vms_booted([vm])
        self.create_and_assoc_fip(fip_pool, vm)
        assert vm.ping_with_certainty(self.inputs.public_host)
        self.logger.debug('restart dm and api-server and verify ping')
        self.inputs.restart_container(self.inputs.cfgm_ips, 'device-manager')
        self.inputs.restart_container(self.inputs.cfgm_ips, 'api-server')
        time.sleep(10)
        assert vm.ping_with_certainty(self.inputs.public_host)
        self.logger.debug('stop dm make some config and start dm and verify')
        self.inputs.stop_container(self.inputs.cfgm_ips, 'device-manager')
        #do some config changes
        for spine in self.spines:
            spine.delete_virtual_network(public_vn.uuid)
        self.inputs.start_container(self.inputs.cfgm_ips, 'device-manager')
        time.sleep(30)
        assert vm.ping_with_certainty(self.inputs.public_host,expectation=False)
        for spine in self.spines:
            spine.add_virtual_network(public_vn.uuid)
        time.sleep(10)
        assert vm.ping_with_certainty(self.inputs.public_host)