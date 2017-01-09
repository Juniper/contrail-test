from fixtures import Fixture
from user_test import UserFixture
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
from common import isolated_creds
from common.connections import *
import time
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from base import *

import test

class TestVcenter(BaseVnVmTest):
    @classmethod
    def setUpClass(cls):
        super(TestVcenter, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestVcenter, cls).tearDownClass()

    def is_test_applicable(self, orch='vcenter'):
        if self.inputs.orchestrator != orch:
            return(False, 'Skipping Test. Require %s setup' % orch)
        return (True, None)

    @test.attr(type=['vcenter'])
    @preposttest_wrapper
    def test_vcenter_plugin_restart(self):
        '''
        Description:  Restart the plugin and ping between the VN.
        Test steps:

               1. Create a VN and launch 2 VMs.
               2. ping between the vm
               3. find out plugin master with port 443
               3. restart the vcenter-plugin on master
               4. ping between the vm after plugin restart
               5. Plugin  status should be Active
        Pass criteria: Ping between the VMs should work after plugin restart and Plugin status should be Active.
        Maintainer : shajuvk@juniper.net
        '''
        vn1_name = get_random_name('vn40')
        vn1_vm1_name = get_random_name('vm1_plugin')
        vn1_vm2_name = get_random_name('vm2_plugin')
        vn1_fixture = self.create_vn(vn_name=vn1_name)
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm1_name)
        vm2_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm2_name)
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
            "Ping from %s to %s failed" % (vn1_vm1_name, vn1_vm2_name)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
            "Ping from %s to %s failed" % (vn1_vm2_name, vn1_vm1_name)
        for cfgm in self.inputs.cfgm_ips:
            cmd = 'netstat -nalp | grep :443 && service contrail-vcenter-plugin restart'
            plugin_mstr = self.inputs.run_cmd_on_server(cfgm, cmd)
            status = self.inputs.run_cmd_on_server(cfgm, 'contrail-status | grep vcenter')
            self.logger.info('Vcenter plugin status on cfgm %s is %s' % (cfgm, status))
            sleep(6)
            if 'active' not in status.split():
               self.logger.error('Plugin status is not ACTIVE')
               return False
            self.logger.info('Vcenter plugin status on cfgm %s is %s' % (cfgm, status))
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
            "Ping from %s to %s failed" % (vn1_vm1_name, vn1_vm2_name)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
            "Ping from %s to %s failed" % (vn1_vm2_name, vn1_vm1_name)
        return True

    # end of test test_vcenter_plugin_restart
