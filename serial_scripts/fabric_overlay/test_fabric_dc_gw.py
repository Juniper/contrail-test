from tcutils.wrappers import preposttest_wrapper
from common.contrail_fabric.base import BaseFabricTest
from tcutils.util import skip_because
import test
import time

class TestFabricDcGw(BaseFabricTest):
    def is_test_applicable(self):
        result, msg = super(TestFabricDcGw, self).is_test_applicable()
        if result:
            msg = 'No spines in the provided fabric topology'
            for device in self.inputs.physical_routers_data.iterkeys():
                if self.get_role_from_inputs(device) == 'spine':
                    break
            else:
                return False, msg
            msg = 'No public subnets specified in test inputs yaml'
            if self.inputs.public_subnets:
                return (True, None)
        return False, msg

    def setUp(self):
        for device_name, device_dict in self.inputs.physical_routers_data.items():
            if device_dict['role'] == 'spine':
#                self.rb_roles[device['name']] = ['CRB-Gateway', 'DC-Gateway']
                self.rb_roles[device_name] = ['DC-Gateway','Route-Reflector']
        super(TestFabricDcGw, self).setUp()

    @preposttest_wrapper
    def itest_floating_ip(self):
        fip_ips = dict()
        bms_fixtures = list()
        public_vn = self.create_vn(vn_subnets=self.inputs.public_subnets[:1])
        fip_pool = self.create_fip_pool(public_vn.uuid)
        private_vn = self.create_vn()

        for spine in self.spines:
            spine.add_virtual_network(public_vn.uuid)
        vm = self.create_vm(vn_fixture=vn, image_name='cirros')

        fip_ips[vm.uuid], fip_id = self.create_and_assoc_fip(fip_pool, vm)
        for bms in self.inputs.bms_data.keys():
            bms_fixture = self.create_bms(bms_name=bms, vn_fixture=vn,
                security_groups=[self.default_sg.uuid])
            bms_fixtures.append(bms_fixture)
            fip_ips[bms_fixture.uuid], fip_id = self.create_and_assoc_fip(
                fip_pool, vm_fixture=None, vmi_id=bms_fixture.port_fixture.uuid)

        for fixture in bms_fixtures + [vm]:
            msg = 'ping from %s to %s failed'%(fixture.name,
                                               self.inputs.public_host)
            assert fixture.ping_with_certainty(self.inputs.public_host)

    @preposttest_wrapper
    def test_instance_on_public_network(self):
        bms_fixtures = list()
        vn = self.create_vn(vn_subnets=self.inputs.public_subnets[:1])
        lr_fixtures = self.create_logical_router([vn], is_public_lr=True)
        vm = self.create_vm(vn_fixture=vn, image_name='cirros')
        for bms in self.inputs.bms_data.keys():
            bms_fixtures.append(self.create_bms(
                bms_name=bms,
                vn_fixture=vn,
                security_groups=[self.default_sg.uuid]))
        self.check_vms_booted([vm])

        for fixture in bms_fixtures + [vm]:
            msg = 'ping from %s to %s failed'%(fixture.name,
                                               self.inputs.public_host)
            assert fixture.ping_with_certainty(self.inputs.public_host)
        self.do_ping_mesh(bms_fixtures + [vm])
