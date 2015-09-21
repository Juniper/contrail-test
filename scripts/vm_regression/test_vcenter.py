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

class TestVcenter(BaseVnVmTest):
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
    def test_vcenter_static_ip(self):
        '''
        Description: Statically assign ip for VM
        Test steps:
               1. Create a VN with dhcp disabled
               2. launch two VMs and assign IP
               2. ping between the vm
        Pass criteria: Ping between the VMs should work
        Maintainer : sunilbasker@juniper.net
        '''
        vn_name = get_random_name('vn')
        vn_sub = '12.11.10.0/24'
        vn_fixture = self.create_vn(vn_name=vn_name, subnets=[vn_sub], enable_dhcp=False)
        assert vn_fixture.verify_on_setup()

        vm1 = self.create_vm(vn_fixture=vn_fixture, vm_name=get_random_name('vm'))
        vm1.vm_obj.assign_ip('eth0', '12.11.10.101', '12.11.10.1', '255.255.255.0')
        assert vm1.wait_till_vm_is_up()
        vm2 = self.create_vm(vn_fixture=vn_fixture, vm_name=get_random_name('vm'))
        vm2.vm_obj.assign_ip('eth0', '12.11.10.102')
        assert vm2.wait_till_vm_is_up()

        assert vm1.ping_with_certainty(dst_vm_fixture=\
                       vm2), "Ping from %s to %s failed" % \
                       (vm1.vm_name, vm2.vn_name)
        assert vm2.ping_with_certainty(dst_vm_fixture=\
                       vm1), "Ping from %s to %s failed" % \
                       (vm2.vm_name, vm1.vn_name)
        return True

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
        host3 = esxs[1]
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
