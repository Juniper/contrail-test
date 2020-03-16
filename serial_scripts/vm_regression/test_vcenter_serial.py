from __future__ import print_function
from __future__ import absolute_import
from .base import *
from fixtures import Fixture
from user_test import UserFixture
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
from common import isolated_creds
from common.connections import *
import time
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from tcutils.util import *
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
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm1_name, image_name='vcenter_tiny_vm')
        vm2_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm2_name, image_name='vcenter_tiny_vm')
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
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm1_name, image_name='vcenter_tiny_vm')
        vm2_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm2_name, image_name='vcenter_tiny_vm')
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        self.vm_host1 = vm1_fixture.vm_obj.host
        self.vm_host2 = vm2_fixture.vm_obj.host
        cluster_status, error_nodes = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        assert cluster_status, 'Cluster is not stable...'
        for compute_vm in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_vm, 'reboot')
        sleep(60)
        for compute_vm in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_vm, 'ifconfig ens192 up')
        cluster_status, error_nodes = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
            "Ping from %s to %s failed" % (vn1_vm1_name, vn1_vm2_name)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
            "Ping from %s to %s failed" % (vn1_vm2_name, vn1_vm1_name)
       
        vn1_vm1_name = get_random_name('vm1_after_reboot')
        vn1_vm2_name = get_random_name('vm2_after_reboot')
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm1_name, image_name='vcenter_tiny_vm')
        vm2_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm2_name, image_name='vcenter_tiny_vm')
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
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm1_name, image_name='vcenter_tiny_vm')
        vm2_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm2_name, image_name='vcenter_tiny_vm')
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
        cluster_status, error_nodes = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
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
                print(compute_vm_ip)
                return compute_vm_ip

class TestVcenterEAM(BaseVnVmTest):
    @classmethod
    def setUpClass(cls):
        super(TestVcenterEAM, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestVcenterEAM, cls).tearDownClass()

    def is_test_applicable(self):
        if self.inputs.orchestrator != 'vcenter':
            return(False, 'Skipping Test. Require %s setup' % 'vcenter')
        return (True, None)

    @test.attr(type=['vcenter'])
    @preposttest_wrapper
    def test_vcenter_eam_basic(self):
        '''1)Check contrail-agency created or not
           2)check contrail-vms managed by eam
           3)power off contrail-vm
           4)check agency issues
           5)Resolve issue
           6)check contrail-vm status'''

        eam_conn = self.orch.ConnectEAM()
        agency_name = 'ContrailVM-Agency'
        assert self.orch.verify_eam_agency(eam_conn,agency_name),'ContrailVM-agency not found'
        assert self.orch.verify_contrail_vms_managed_by_eam()
        agency = self.orch.get_eam_agency(eam_conn, agency_name)
        contrail_vm = self.orch.get_contrail_vms()[0]
        self.orch.manage_contrail_vm(contrail_vm,operation='poweroff')
        assert self.orch.verify_eam_agency_status(agency, expected='red')
        if self.orch.get_eam_issues(agency):
            self.orch.eam_resolve_issue(agency)
            assert self.orch.verify_eam_agency_status(agency),'Issues not got resolved'
            assert self.orch.verify_contrail_vm_state(contrail_vm),'Eam failed to power on contrail-vm'    
        else:
            assert False,'agency Issues not got generated'
    
    @preposttest_wrapper
    def test_vcenter_eam_maintenance_mode(self):
        '''1)put host in maintenance mode
           2)Check issues in eam agency
           3)resolve issue and verify
           4)check host exited from maintenace mode'''

        eam_conn = self.orch.ConnectEAM()
        agency_name = 'ContrailVM-Agency'
        agency = self.orch.get_eam_agency(eam_conn, agency_name)
        host = self.orch.get_hosts_obj()[0]
        self.orch.manage_esxi_host(host.name,operation='enter_maintenance_mode')
        assert self.orch.verify_eam_agency_status(agency, expected='red')
        if self.orch.get_eam_issues(agency):
            self.orch.eam_resolve_issue(agency)
            assert self.orch.verify_eam_agency_status(agency),'Issues not got resolved'
            assert self.orch.verify_host_state(host,expected='exit_maintenance_mode'),'Eam failed to exit host from maintenace_mode'    
        else:
            self.orch.manage_esxi_host(host.name,operation='exit_maintenance_mode')
            assert False,'agency Issues not got generated'

    @preposttest_wrapper
    def test_vcenter_eam_standby(self):
        '''1)put host in standby mode
           2)Check issues in eam agency
           3)resolve issue and verify
           4)check host exited from standby mode'''

        eam_conn = self.orch.ConnectEAM()
        agency_name = 'ContrailVM-Agency'
        agency = self.orch.get_eam_agency(eam_conn, agency_name)
        host = self.orch.get_hosts_obj()[0]
        self.orch.manage_esxi_host(host.name,operation='enter_standby_mode')
        assert self.orch.verify_eam_agency_status(agency, expected='red')
        if self.orch.get_eam_issues(agency):
            self.orch.eam_resolve_issue(agency)
            assert self.orch.verify_eam_agency_status(agency),'Issues not got resolved'
            assert self.orch.verify_host_state(host,expected='exit_standby_mode'),'Eam failed to exit host from standby_mode'    
        else:
            self.orch.manage_esxi_host(host.name,operation='exit_standby_mode')
            assert False,'agency Issues not got generated'
