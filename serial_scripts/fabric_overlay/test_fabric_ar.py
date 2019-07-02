from tcutils.wrappers import preposttest_wrapper
from common.contrail_fabric.base import BaseFabricTest
from tcutils.util import skip_because
import test
import time

class TestFabricAR(BaseFabricTest):
    def is_test_applicable(self):
        result, msg = super(TestFabricAR, self).is_test_applicable()
        if result:
            msg = 'No spines in the provided fabric topology'
            for device in self.inputs.physical_routers_data.iterkeys():
                if self.get_role_from_inputs(device) == 'spine':
                    break
            else:
                return False, msg
        msg = 'No devices configured with ar_replicator rb_role'
        for device, device_dict in self.inputs.physical_routers_data.items():
            if 'ar_replicator' in (device_dict.get('rb_roles') or []):
                return True, None
        return False, msg

    def setUp(self):
        for device, device_dict in self.inputs.physical_routers_data.items():
            if 'ar_replicator' in (device_dict.get('rb_roles') or []):
                if device_dict['role'] == 'spine':
                    self.rb_roles[device] = ['AR-Replicator',
                        'CRB-Gateway', 'Route-Reflector']
                elif device_dict['role'] == 'leaf':
                    self.rb_roles[device] = ['AR-Replicator', 'CRB-Access']
            if 'ar_client' in (device_dict.get('rb_roles') or []):
                if device_dict['role'] == 'spine':
                    self.rb_roles[device] = ['AR-Client',
                        'CRB-Gateway', 'Route-Reflector']
                elif device_dict['role'] == 'leaf':
                    self.rb_roles[device] = ['AR-Client', 'CRB-Access']
        super(TestFabricAR, self).setUp()

    @preposttest_wrapper
    def test_intra_ar(self):
        import pdb; pdb.set_trace()
        bms_fixtures = list()
        vn = self.create_vn()
        lr = self.create_logical_router([vn])
#        for bms in self.inputs.bms_data.keys():
#            bms_fixture = self.create_bms(bms_name=bms, vn_fixture=vn,
#                security_groups=[self.default_sg.uuid])
#            bms_fixtures.append(bms_fixture)

        for bms in self.inputs.bms_data.keys():
            bms_fixtures.append(self.create_bms(
                bms_name=bms,
                tor_port_vlan_tag=10,
                vn_fixture=vn))
        self.do_ping_mesh(bms_fixtures)
