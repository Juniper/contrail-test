from fixtures import Fixture
from user_test import UserFixture
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
from common import isolated_creds
from common.connections import *
import time
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from tcutils.util import *
from base import *
from vcenter import *
import test

class TestVcenterSerial(BaseVnVmTest):
    @classmethod
    def setUpClass(cls):
        super(TestVcenter, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestVcenter, cls).tearDownClass()

    def is_test_applicable(self):
        if self.inputs.orchestrator != 'vcenter':
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

    @test.attr(type=['vcenter'])
    @preposttest_wrapper
    def test_vcenter_compute_vm_reboot(self):
        '''
        Description:  Rebooting ContrailVM and verify compute services.
        Test steps:

               1. reboot contrail-compute VM's
               2. Verify contrail-status
               3. Create two guest VM's
               4. ping between the vm after compute VM reboot
        Pass criteria: Contrail status should be active after reboot and ping between the VM has to work.
        Maintainer : shajuvk@juniper.net
        '''

        vn1_name = get_random_name('vn50')
        vn1_vm1_name = get_random_name('vm1_reboot')
        vn1_vm2_name = get_random_name('vm2_reboot')
        vn1_fixture = self.create_vn(vn_name=vn1_name)
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm1_name)
        vm2_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm2_name)
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        self.vm_host1 = vm1_fixture.vm_obj.host
        self.vm_host2 = vm2_fixture.vm_obj.host
        esxi_hosts = self.inputs.esxi_vm_ips
        for ip in self.inputs.compute_ips:
            status_before = self.inputs.run_cmd_on_server(ip, 'contrail-status').split()
            print status_before
            count = status_before.count('active')
            self.logger.info('compute VM status before rebooting VM %s is %s' % (ip, status_before))
            if count is not 3:
                assert "All the services are not Active on compute VM  %s" % ip
        self.vm1_compute_vm = self.get_compute_vm(self.vm_host1).split('@')[1]
        self.vm2_compute_vm = self.get_compute_vm(self.vm_host2).split('@')[1]
        self.inputs.run_cmd_on_server(self.vm1_compute_vm, 'reboot')
        self.inputs.run_cmd_on_server(self.vm2_compute_vm, 'reboot')
        sleep(20)
        for ip in self.inputs.compute_ips:
            status_after = self.inputs.run_cmd_on_server(ip, 'contrail-status').split()
            print status_after
            self.logger.info('compute VM status after rebooting VM %s is %s' % (ip, status_after))
            if status_before != status_after:
                assert self.logger.error('One or more contrail services on %s is not in ACTIVE state' % (ip))

        vn1_vm1_name = get_random_name('vm1_after_reboot')
        vn1_vm2_name = get_random_name('vm2_after_reboot')
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm1_name)
        vm2_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm2_name)
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
            "Ping from %s to %s failed" % (vn1_vm1_name, vn1_vm2_name)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
            "Ping from %s to %s failed" % (vn1_vm2_name, vn1_vm1_name)
        return True

     # end of test test_vcenter_compute_vm_reboot


    def get_compute_vm(self, host):
        for esxi_host in self.inputs.esxi_vm_ips:
            compute_vm_host = esxi_host['ip']
            if compute_vm_host == host:
                compute_vm_ip = esxi_host['contrail_vm']
                print compute_vm_ip
                return compute_vm_ip
