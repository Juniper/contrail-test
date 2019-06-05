from ztp_base import ZtpBaseTest
from tcutils.wrappers import preposttest_wrapper

class TestZtp(ZtpBaseTest):
    @preposttest_wrapper
    def test_ztp_workflow(self):
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')
        bms_fixtures = list()
        vn = self.create_vn()
        for bms in self.get_bms_nodes():
            bms_fixtures.append(self.create_bms(bms_name=bms, vlan_id=10,
                vn_fixture=vn))
        self.do_ping_mesh(bms_fixtures)
