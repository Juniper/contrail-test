from base import HABaseTest 
from common import isolated_creds
import time
from tcutils.wrappers import preposttest_wrapper
import test

class TestHANode(HABaseTest):

    @classmethod
    def setUpClass(cls):
        super(TestHANode, cls).setUpClass()

    @test.attr(type=['ha'])
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

    @preposttest_wrapper
    def test_ha_isolate(self):
        ret = self.ha_isolate_test([self.inputs.cfgm_control_ips[2],self.inputs.cfgm_control_ips[2]])
        time.sleep(120)
        return ret

    @preposttest_wrapper
    def test_ha_cold_reboot_computes(self):
        time.sleep(120)
        ret = self.ha_reboot_all_test(self.inputs.compute_ips,mode='power')
        return ret

    @preposttest_wrapper
    def test_ha_reboot_computes(self):
        time.sleep(120)
        ret = self.ha_reboot_all_test(self.inputs.compute_ips,mode='reboot')
        return ret

#    @preposttest_wrapper
#    def test_ha_cold_reboot_all(self):
#        time.sleep(120)
#        ips = self.inputs.compute_ips + [self.inputs.cfgm_ips[1],self.inputs.cfgm_ips[2]]
#        ret = self.ha_reboot_all_test(ips,mode='power')
#        return ret

#    @preposttest_wrapper
#    def test_ha_reboot_all(self):
#        time.sleep(120)
#        ips = self.inputs.compute_ips + [self.inputs.cfgm_ips[1],self.inputs.cfgm_ips[2]]
#        ret = self.ha_reboot_all_test(ips,mode='reboot')
#        return ret

#end HA node failure tests

