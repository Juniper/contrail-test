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
from tcutils.contrail_status_check import ContrailStatusChecker
import re

class TestVcenterSerial(BaseVnVmTest):
    @classmethod
    def setUpClass(cls):
        super(TestVcenterSerial, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestVcenterSerial, cls).tearDownClass()

    def is_test_applicable(self):
        if self.inputs.orchestrator != 'vcenter':
            return(False, 'Skipping Test. Require %s setup' % 'vcenter')
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
        vn1_fixture = self.create_vn(vn1_name, [get_random_cidr()])
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm1_name)
        vm2_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm2_name)
        assert vm1_fixture.wait_till_vm_is_up(refresh=True)
        assert vm2_fixture.wait_till_vm_is_up(refresh=True)
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
            "Ping from %s to %s failed" % (vn1_vm1_name, vn1_vm2_name)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
            "Ping from %s to %s failed" % (vn1_vm2_name, vn1_vm1_name)
        for cfgm in self.inputs.cfgm_ips:
            cmd = 'docker restart vcenterplugin_vcenter-plugin_1'
            plugin_mstr = self.inputs.run_cmd_on_server(cfgm, cmd
                              )
            time.sleep(12)
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
               1. Create two vms and ping between them
               2. reboot contrail-compute VM's
               3. Verify contrail-status
               4. ping between existing vms
               5. Create two more guest VM's
               6. ping between the vm after compute VM reboot
        Pass criteria: Contrail status should be active after reboot and ping between the VM has to work.
        Maintainer : shajuvk@juniper.net
        '''

        vn1_name = get_random_name('vn50')
        vn1_vm1_name = get_random_name('vm1_reboot')
        vn1_vm2_name = get_random_name('vm2_reboot')
        vn1_fixture = self.create_vn(vn1_name, [get_random_cidr()])
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm1_name)
        vm2_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm2_name)
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        self.vm_host1 = vm1_fixture.vm_obj.host
        self.vm_host2 = vm2_fixture.vm_obj.host
        cluster_status, error_nodes = ContrailStatusChecker().wait_till_contrail_cluster_stable()
        assert cluster_status, 'Cluster is not stable...'
        for compute_vm in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_vm, 'reboot')
        sleep(60)
        for compute_vm in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_vm, 'ifconfig ens192 up')
        cluster_status, error_nodes = ContrailStatusChecker().wait_till_contrail_cluster_stable()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
            "Ping from %s to %s failed" % (vn1_vm1_name, vn1_vm2_name)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
            "Ping from %s to %s failed" % (vn1_vm2_name, vn1_vm1_name)
       
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

    @test.attr(type=['vcenter'])
    @preposttest_wrapper
    def test_vcenter_vrouter_agent_restart(self):
        ''' Test steps:
               1. Create two guest VM's
               2. ping between the vms
               3. restart agents on Contrail VM'
               4. Verify contrail-status
               5. ping between the vms
        Pass criteria: Contrail status should be active after restart  and ping between the VM has to work.'''
 
        vn1_name = get_random_name('vn50')
        vn1_vm1_name = get_random_name('vm1')
        vn1_vm2_name = get_random_name('vm2')
        vn1_fixture = self.create_vn(vn1_name, [get_random_cidr()])
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm1_name)
        vm2_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm2_name)
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
            "Ping from %s to %s failed" % (vn1_vm1_name, vn1_vm2_name)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
            "Ping from %s to %s failed" % (vn1_vm2_name, vn1_vm1_name)
        contrail_vms = self.inputs.compute_ips
        self.inputs.restart_service('contrail-vrouter-agent', contrail_vms,
                                 container='agent',
                                 verify_service=True)
        cluster_status, error_nodes = ContrailStatusChecker().wait_till_contrail_cluster_stable()
        assert cluster_status, 'Cluster is not stable after restart...'
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
            "Ping from %s to %s failed" % (vn1_vm1_name, vn1_vm2_name)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
            "Ping from %s to %s failed" % (vn1_vm2_name, vn1_vm1_name)

    def get_compute_vm(self, host):
        for esxi_host in self.inputs.esxi_vm_ips:
            compute_vm_host = esxi_host['ip']
            if compute_vm_host == host:
                compute_vm_ip = esxi_host['contrail_vm']
                print compute_vm_ip
                return compute_vm_ip
