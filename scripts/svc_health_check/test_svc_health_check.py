from tcutils.wrappers import preposttest_wrapper
from common.servicechain.firewall.verify import VerifySvcFirewall
from base import BaseHC
import test

class TestSvcHC(BaseHC, VerifySvcFirewall):

    @preposttest_wrapper
    def test_svc_hc_basic(self):
        ret_dict = self.verify_svc_in_network_datapath(svc_img_name='tiny_nat_fw', st_version=2)
        hc_fixture = self.create_hc()
        si_fixture = ret_dict['si_fixtures'][0]
        si_fixture.associate_hc(hc_fixture.uuid, 'left')
        assert si_fixture.verify_hc_in_agent()
        assert si_fixture.verify_hc_is_active()

