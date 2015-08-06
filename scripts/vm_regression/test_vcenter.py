from fixtures import Fixture
from vn_test import *
from vm_test import *
from user_test import UserFixture
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
from common import isolated_creds
from common.connections import *
import time
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
#from tcutils.util import get_subnet_broadcast
from tcutils.util import *
from base import *
from vcenter import *
from pyVim import  connect
from pyVmomi import vim
import test

class TestVcenter(BaseVnVmTest, VcenterOrchestrator):
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
        sleep(10)
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

    @test.attr(type=['vcenter'])
    @preposttest_wrapper
    def test_vcenter_vm_moveout_and_backin(self):
        '''
        Description:
        Test steps:
               1. Launch VN and couple of VMs
               2. Remove network-intf from VM
               3. Verify VM is removed from contrail-components
               4. Add network-intf back to VM
               5. Verify VM info in contrail-components
        Pass criteria: Ping between the VMs should work before move out and after backin.
        Maintainer : sunilbasker@juniper.net
        '''
        vn1_fixture = self.create_vn(vn_name=get_random_name('vnmb'))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=get_random_name('vm1mb'))
        vm2_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=get_random_name('vm2mb'))
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
            "Ping from %s to %s failed" % (vm1_fixture.vm_name, vm2_fixture.vm_name)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
            "Ping from %s to %s failed" % (vm2_fixture.vm_name, vm1_fixture.vm_name)

        vm1_fixture.orch.delete_networks_from_vm(vm1_fixture.vm_obj, [vn1_fixture.obj])
        sleep(2)
        assert vm1_fixture.verify_cleared_from_setup(check_orch=False)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture, expectation=False),\
            "Ping from %s to %s is expected to fail" % (vm2_fixture.vm_name, vm1_fixture.vm_name)
        vm1_fixture.orch.add_networks_to_vm(vm1_fixture.vm_obj, [vn1_fixture.obj])
        sleep(2)
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm1_fixture.verify_on_setup()
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
            "Ping from %s to %s failed" % (vm1_fixture.vm_name, vm2_fixture.vm_name)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
            "Ping from %s to %s failed" % (vm2_fixture.vm_name, vm1_fixture.vm_name)
        return True


class TestVcenter2(BaseVnVmTest):
    @classmethod
    def setUpClass(cls):
        super(TestVcenter2, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestVcenter2, cls).tearDownClass()

    def is_test_applicable(self):
        if self.inputs.orchestrator != 'vcenter':
            return (False, 'Skipping Test. Require vcenter setup')
        if len(self.orch.get_hosts()) <= 1:
            return (False, 'Skipping Test. Require more than one ESX server')
        return (True, None)

    @test.attr(type=['vcenter'])
    @preposttest_wrapper
    def test_vcenter_vm_on_diff_host(self):
        '''
        Description: Launch VM on diff ESX hosts
        Test steps:
               1. Create a VN
               2. launch one VM on each ESX server
               2. ping between the vms
        Pass criteria: Ping between the VMs should work
        Maintainer : sunilbasker@juniper.net
        '''
        esxs = self.orch.get_hosts()
        vn_name = get_random_name('vn')
        vn_fixture = self.create_vn(vn_name=vn_name)
        assert vn_fixture.verify_on_setup()

        vm_fixtures = {}
        for i in range(len(esxs)):
           vm_name = get_random_name('vm')
           vm_fixtures[vm_name] = self.create_vm(vn_fixture=vn_fixture, vm_name=vm_name, node_name=esxs[i])
           assert vm_fixtures[vm_name].wait_till_vm_is_up()

        for src_vm_fix in vm_fixtures.values():
            for dst_vm_fix in vm_fixtures.values():
                if dst_vm_fix is src_vm_fix:
                    continue
                assert src_vm_fix.ping_with_certainty(dst_vm_fixture=\
                       dst_vm_fix), "Ping from %s to %s failed" % \
                       (src_vm_fix.vm_name, dst_vm_fix.vn_name)

    @test.attr(type=['vcenter'])
    @preposttest_wrapper
    def test_vcenter_host_maintenance(self):
        '''
        Description: Moving ESX server to maintenance mode
        Test steps:
               1. Create a VN and launch 2 VMs on the first ESX server.
               2. ping between the vm
               3. launch 1 VMs on the second ESX server and ping
               4. Move the first server to maintenance mode
               5. launch 1 more VMs and ping all
               6. Restore the first server out of maintenance mode
               7. ping all
        Pass criteria: Ping between the VMs should work during & after one of host moves to maintenance mode
        Maintainer : sunilbasker@juniper.net
        '''
        esxs = self.orch.get_hosts()
        host1 = esxs[0]
        host2 = esxs[1]
        if len(esxs) > 2:
            host3 = esxs[2]
        vn_name = get_random_name('vn_mm')
        vm_fixtures = {}
        for _ in range(4):
           vm_fixtures[get_random_name('vm_mm')] = None
        vn_fixture = self.create_vn(vn_name=vn_name)
        assert vn_fixture.verify_on_setup()
        vms = vm_fixtures.keys()
        vm_fixtures[vms[0]] = self.create_vm(vn_fixture=vn_fixture, vm_name=vms[0], node_name=host1)
        vm_fixtures[vms[1]] = self.create_vm(vn_fixture=vn_fixture, vm_name=vms[1], node_name=host1)
        vm_fixtures[vms[2]] = self.create_vm(vn_fixture=vn_fixture, vm_name=vms[2], node_name=host2)
        for vm_fix in vm_fixtures.values():
            if vm_fix:
                assert vm_fix.wait_till_vm_is_up()

        for src_vm_fix in vm_fixtures.values():
            if not src_vm_fix:
                continue
            for dst_vm_fix in vm_fixtures.values():
                if not dst_vm_fix or dst_vm_fix is src_vm_fix:
                    continue
                assert src_vm_fix.ping_with_certainty(dst_vm_fixture=\
                       dst_vm_fix), "Ping from %s to %s failed" % \
                       (src_vm_fix.vm_name, dst_vm_fix.vn_name)

        self.orch.enter_maintenance_mode(host1)
        vm_fixtures[vms[3]] = self.create_vm(vn_fixture=vn_fixture, vm_name=vms[3], node_name=host3)
        assert vm_fixtures[vms[3]].wait_till_vm_is_up()
        src_vm_fix = vm_fixtures[vms[2]]
        dst_vm_fix = vm_fixtures[vms[3]]
        assert src_vm_fix.ping_with_certainty(dst_vm_fixture=dst_vm_fix),\
            "Ping from %s to %s failed" % (src_vm_fix.vm_name, dst_vm_fix.vm_name)
        src_vm_fix, dst_vm_fix = dst_vm_fix, src_vm_fix
        assert src_vm_fix.ping_with_certainty(dst_vm_fixture=dst_vm_fix),\
            "Ping from %s to %s failed" % (src_vm_fix.vm_name, dst_vm_fix.vm_name)

        self.orch.exit_maintenance_mode(host1)
        for vm_fix in vm_fixtures.values():
            if vm_fix:
                assert vm_fix.wait_till_vm_is_up()
        for src_vm_fix in vm_fixtures.values():
            if not src_vm_fix:
                continue
            for dst_vm_fix in vm_fixtures.values():
                if not dst_vm_fix or dst_vm_fix is src_vm_fix:
                    continue
                assert src_vm_fix.ping_with_certainty(dst_vm_fixture=\
                       dst_vm_fix), "Ping from %s to %s failed" % \
                       (src_vm_fix.vm_name, dst_vm_fix.vn_name)
        return True

    @test.attr(type=['vcenter'])
    @preposttest_wrapper
    def test_vcenter_vm_migrate(self):
        '''
        Description: Migrate VM between ESX servers
        Test steps:
               1. Create a VN
               2. launch two VMs on diff ESX servers
               3. ping between the vm
               4. Migrate VM to a diff ESX server
               5. ping between the vm
        Pass criteria: Ping between the VMs should work
        Maintainer : sunilbasker@juniper.net
        '''
        esxs = self.orch.get_hosts()
        vn_fixture = self.create_vn(vn_name=get_random_name('vn_mig'))
        assert vn_fixture.verify_on_setup()

        vm1_fixture = self.create_vm(vn_fixture=vn_fixture,
                                     vm_name=get_random_name('vm_mig'),
                                     node_name=esxs[0])
        vm2_fixture = self.create_vm(vn_fixture=vn_fixture,
                                     vm_name=get_random_name('vm_mig'),
                                     node_name=esxs[1])
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=\
                       vm2_fixture), "Ping from %s to %s failed" % \
                       (vm1_fixture.vm_name, vm2_fixture.vn_name)

        vm2_fixture.migrate(esxs[0])
        vm2_fixture.verify_on_setup()
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=\
                       vm2_fixture), "Ping from %s to %s failed" % \
                       (vm1_fixture.vm_name, vm2_fixture.vn_name)
        return True

class TestVcenter3(BaseVnVmTest):
    @classmethod
    def setUpClass(cls):
        super(TestVcenter3, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestVcenter3, cls).tearDownClass()

    def is_test_applicable(self):
        if self.inputs.orchestrator != 'vcenter':
            return (False, 'Skipping Test. Require vcenter setup')
        if len(self.orch.get_zones()) <= 1:
            return (False, 'Skipping Test. Require more than cluster in the setup')
        return (True, None)

    @test.attr(type=['vcenter'])
    @preposttest_wrapper
    def test_vcenter_vm_on_diff_cluster(self):
        '''
        Description: Launch VM on diff ESX clusters
        Test steps:
               1. Create a VN
               2. launch one VM on each ESX cluster
               2. ping between the vm
        Pass criteria: Ping between the VMs should work
        Maintainer : sunilbasker@juniper.net
        '''
        clus = self.orch.get_zones()
        vn_name = get_random_name('vn_')
        vn_fixture = self.create_vn(vn_name=vn_name)
        assert vn_fixture.verify_on_setup()

        vm_fixtures = {}
        for i in range(len(clus)):
           vm_name = get_random_name('vm_')
           vm_fixtures[vm_name] = self.create_vm(vn_fixture=vn_fixture, vm_name=vm_name, zone=clus[i])
           assert vm_fixtures[vm_name].wait_till_vm_is_up()

        for src_vm_fix in vm_fixtures.values():
            for dst_vm_fix in vm_fixtures.values():
                if dst_vm_fix is src_vm_fix:
                    continue
                assert src_vm_fix.ping_with_certainty(dst_vm_fixture=\
                       dst_vm_fix), "Ping from %s to %s failed" % \
                       (src_vm_fix.vm_name, dst_vm_fix.vn_name)
