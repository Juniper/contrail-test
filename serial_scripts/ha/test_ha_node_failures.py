from base import HABaseTest 
from common import isolated_creds
import time
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because
import test

class TestHANode(HABaseTest):

    @classmethod
    def setUpClass(cls):
        super(TestHANode, cls).setUpClass()

    @test.attr(type=['ha', 'vcenter'])
    @preposttest_wrapper
    @skip_because(ha_setup = 'False')
    def test_ha_reboot(self):
        time.sleep(120)
        ret = self.ha_reboot_test([self.inputs.cfgm_ips[1],self.inputs.cfgm_ips[2]])
        time.sleep(30)
        return ret

    @test.attr(type=['vcenter'])
    @preposttest_wrapper
    @skip_because(ha_setup = 'False')
    def test_ha_cold_reboot(self):
        time.sleep(120)
        ret = self.ha_cold_reboot_test([self.inputs.cfgm_ips[1],self.inputs.cfgm_ips[2]])
        time.sleep(30)
        return ret

    @test.attr(type=['vcenter'])
    @preposttest_wrapper
    @skip_because(ha_setup = 'False')
    def test_ha_cold_shutdown(self):
        time.sleep(120)
        ret = self.ha_cold_shutdown_test([self.inputs.cfgm_ips[1],self.inputs.cfgm_ips[2]])
        time.sleep(30)
        return ret

    @test.attr(type=['vcenter'])
    @preposttest_wrapper
    @skip_because(ha_setup = 'False')
    def test_ha_isolate(self):
        ret = self.ha_isolate_test([self.inputs.cfgm_control_ips[1],self.inputs.cfgm_control_ips[2]])
        time.sleep(120)
        return ret

    @preposttest_wrapper
    def test_ha_cold_reboot_computes(self):
        time.sleep(120)
        ret = self.ha_reboot_all_test(self.inputs.compute_ips,mode='ipmi')
        time.sleep(30)
        return ret

    @preposttest_wrapper
    def test_ha_reboot_computes(self):
        time.sleep(120)
        ret = self.ha_reboot_all_test(self.inputs.compute_ips,mode='reboot')
        time.sleep(30)
        return ret

#    @preposttest_wrapper
#    def test_ha_cold_reboot_all(self):
#        time.sleep(120)
#        ips = self.inputs.compute_ips + [self.inputs.cfgm_ips[1],self.inputs.cfgm_ips[2]]
#        ret = self.ha_reboot_all_test(ips,mode='ipmi')
#        return ret

#    @preposttest_wrapper
#    def test_ha_reboot_all(self):
#        time.sleep(120)
#        ips = self.inputs.compute_ips + [self.inputs.cfgm_ips[1],self.inputs.cfgm_ips[2]]
#        ret = self.ha_reboot_all_test(ips,mode='reboot')
#        return ret

#end HA node failure tests

