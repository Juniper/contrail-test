from base import HABaseTest 
from common import isolated_creds
import time
from tcutils.wrappers import preposttest_wrapper

class TestHANode(HABaseTest):

    @classmethod
    def setUpClass(cls):
        super(TestHANode, cls).setUpClass()

    @preposttest_wrapper
    def test_ha_reboot(self):
        time.sleep(120)
        ret = self.ha_reboot_test([self.inputs.cfgm_ips[1],self.inputs.cfgm_ips[2]])
        self.ha_service_restart('contrail-vrouter-agent', self.inputs.compute_ips)
        return ret

    @preposttest_wrapper
    def test_ha_cold_reboot(self):
        time.sleep(120)
        ret = self.ha_cold_reboot_test([self.inputs.cfgm_ips[1],self.inputs.cfgm_ips[2]])
        self.ha_service_restart('contrail-vrouter-agent', self.inputs.compute_ips)
        return ret

    @preposttest_wrapper
    def test_ha_cold_shutdown(self):
        time.sleep(120)
        ret = self.ha_cold_shutdown_test([self.inputs.cfgm_ips[1],self.inputs.cfgm_ips[2]])
        self.ha_service_restart('contrail-vrouter-agent', self.inputs.compute_ips)
        return ret

#    @preposttest_wrapper
#    def test_ha_isolate(self):
#        ret = self.ha_isolate_test([self.inputs.cfgm_ips[1],self.inputs.cfgm_ips[2]])
#        time.sleep(120)
#        return ret

#end HA node failure tests



