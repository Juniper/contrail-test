from vn_test import *
from vm_test import *
from floating_ip import *
from policy_test import *
from tcutils.wrappers import preposttest_wrapper
from base import BaseVnVmTest
from common import isolated_creds
import test

class TestBasicESXKVM(BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicESXKVM, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBasicESXKVM, cls).tearDownClass()

    def is_test_applicable(self):
        if not self.inputs.orchestrator == 'openstack':
            return (False, 'Skipping Test. Openstack required')
        zones = self.connections.nova_h.get_zones()
        if 'nova' not in zones or 'esx' not in zones:
            return (False, 'Skipping Test. Both nova and esx zones required')
        if not len(self.connections.nova_h.get_hosts('nova')) and not len(self.connections.nova_h.get_hosts('esx')):
            return (False, 'Skipping Test. Either or both nova and esx zones are empty')
        return (True, None)

    @test.attr(type=['quick_sanity'])
    @preposttest_wrapper
    def test_ping_within_vn(self):
        '''
        Description:  Validate Ping between 2 VMs in the same VN.
        Test steps:
               1. Create a VN and launch 2 VMs in it.
        Pass criteria: Ping between the VMs should go thru fine.
        '''
        vn1_fixture = self.create_vn(vn_name=get_random_name('vnEsx1'))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=get_random_name('vm1'), zone='nova')
        vm2_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=get_random_name('vm2'), zone='esx')
        vm3_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=get_random_name('vm3'), zone='esx')
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm3_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        vm3_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
            "Ping from %s to %s failed" % (vm1_fixture.vm_name, vm2_fixture.vm_name)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
            "Ping from %s to %s failed" % (vm2_fixture.vm_name, vm1_fixture.vm_name)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm3_fixture),\
            "Ping from %s to %s failed" % (vm2_fixture.vm_name, vm3_fixture.vm_name)
        return True
    # end test_ping_within_vn

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_ping_within_2_vn(self):
        '''
        Description:  Validate Ping between 2 VMs in the same VN.
        Test steps:
               1. Create a VN and launch 2 VMs in it.
               2. Create a VN and launch 2 VMs in it.
        Pass criteria: Ping between the VMs in the same VN should go thru fine, across VN should fail
        '''
        vn1_fixture = self.create_vn(vn_name=get_random_name('vnEsx1'))
        vn2_fixture = self.create_vn(vn_name=get_random_name('vnEsx2'))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        vn1_vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=get_random_name('vm1'), zone='nova')
        vn1_vm2_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=get_random_name('vm2'), zone='esx')
        vn2_vm1_fixture = self.create_vm(vn_fixture=vn2_fixture, vm_name=get_random_name('vm1'), zone='nova')
        vn2_vm2_fixture = self.create_vm(vn_fixture=vn2_fixture, vm_name=get_random_name('vm2'), zone='esx')
        vn1_vm1_fixture.wait_till_vm_is_up()
        vn1_vm2_fixture.wait_till_vm_is_up()
        vn2_vm1_fixture.wait_till_vm_is_up()
        vn2_vm2_fixture.wait_till_vm_is_up()
        assert vn1_vm1_fixture.ping_with_certainty(dst_vm_fixture=vn1_vm2_fixture),\
            "Ping from %s to %s failed" % (vn1_vm1_fixture.vm_name, vn1_vm2_fixture.vm_name)
        assert vn2_vm1_fixture.ping_with_certainty(dst_vm_fixture=vn2_vm2_fixture),\
            "Ping from %s to %s failed" % (vn2_vm1_fixture.vm_name, vn2_vm2_fixture.vm_name)
        assert vn1_vm1_fixture.ping_with_certainty(dst_vm_fixture=vn2_vm2_fixture, expectation=False),\
            "Ping from %s to %s should fail" % (vn1_vm1_fixture.vm_name, vn2_vm2_fixture.vm_name)
        assert vn1_vm2_fixture.ping_with_certainty(dst_vm_fixture=vn2_vm1_fixture, expectation=False),\
            "Ping from %s to %s should fail" % (vn1_vm2_fixture.vm_name, vn2_vm1_fixture.vm_name)
        assert vn1_vm2_fixture.ping_with_certainty(dst_vm_fixture=vn2_vm2_fixture, expectation=False),\
            "Ping from %s to %s should fail" % (vn1_vm2_fixture.vm_name, vn2_vm2_fixture.vm_name)
        return True
    # end test_ping_within_2_vn

    @test.attr(type=['sanity','quick_sanity'])
    @preposttest_wrapper
    def test_ping_with_policy(self):
        '''
        Description:  Validate Ping across VN with policy set to allow.
        Test steps:
               1. Create 2 VNs and set policy to allow ping traffic.
               2. Launch 2 VMs in the 1st VN. 
               3. Launch 1 VMs in the 2nd VN. 
        Pass criteria: Ping across VN should go thru fine
        '''
        vn1_name = get_random_name('vnEsx1')
        vn2_name = get_random_name('vnEsx2')
        rules = [{
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': vn1_name,
                'dest_network': vn2_name,
                }]
        policy_fixture = self.useFixture(PolicyFixture(
                                          policy_name=get_random_name('policyEsx'),
                                          rules_list=rules,
                                          inputs=self.inputs,
                                          connections=self.connections))
        vn1_fixture = self.create_vn(vn_name=vn1_name, policy_objs=[policy_fixture.policy_obj])
        vn2_fixture = self.create_vn(vn_name=vn2_name, policy_objs=[policy_fixture.policy_obj])
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        vn1_vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=get_random_name('vm1'), zone='nova')
        vn1_vm2_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=get_random_name('vm2'), zone='esx')
        vn2_vm1_fixture = self.create_vm(vn_fixture=vn2_fixture, vm_name=get_random_name('vm3'), zone='esx')
        vn1_vm1_fixture.wait_till_vm_is_up()
        vn1_vm2_fixture.wait_till_vm_is_up()
        vn2_vm1_fixture.wait_till_vm_is_up()
        assert vn1_vm1_fixture.ping_with_certainty(dst_vm_fixture=vn2_vm1_fixture),\
            "Ping from %s to %s failed" % (vn1_vm1_fixture.vm_name, vn2_vm1_fixture.vm_name)
        assert vn1_vm2_fixture.ping_with_certainty(dst_vm_fixture=vn2_vm1_fixture),\
            "Ping from %s to %s should fail" % (vn1_vm2_fixture.vm_name, vn2_vm1_fixture.vm_name)
        return True
    # end test_ping_with_policy

    def file_trf_tests(self, mode):
        '''
        Description: Test to validate File Transfer using specified mode between VMs. Files of different sizes.
        Test steps:
                1. Create a VN and launch 3 VMs in it
                2. Transfer files between the VMs 
                3. file sizes - 1000,1101,1202,1303,1373, 1374,2210, 2845, 3000, 10000 
        Pass criteria: Transfered file sizes should match the original file size
        '''
        vn1_fixture = self.create_vn(vn_name=get_random_name('vnEsx1'))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=get_random_name('vm1'), zone='nova')
        vm2_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=get_random_name('vm2'), zone='esx')
        vm3_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=get_random_name('vm3'), zone='esx')
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        vm3_fixture.wait_till_vm_is_up()
        vm1_fixture.put_pub_key_to_vm()
        vm2_fixture.put_pub_key_to_vm()
        vm3_fixture.put_pub_key_to_vm()

        test_file_sizes = ['1303'] if os.environ.has_key('ci_image') else \
                              ['1000', '1101', '1202', '1303', '1373', '1374',
                               '2210', '2845', '3000', '10000']
        transfer_result = True

        for size in test_file_sizes:
            self.logger.info("-" * 80)
            self.logger.info("FILE SIZE = %sB" % size)
            self.logger.info("-" * 80)

            self.logger.info('Transferring the file from %s to %s using %s' %
                             (vm1_fixture.vm_name, vm2_fixture.vm_name, mode))
            if os.environ.has_key('ci_image') and self.inputs.get_af() == 'v4' and mode == 'scp':
                file_transfer_result = vm1_fixture.scp_file_transfer_cirros(vm2_fixture, size=size)
            else:
                file_transfer_result = vm1_fixture.check_file_transfer(vm2_fixture,
                                                                   size=size, mode=mode)
            if file_transfer_result:
                self.logger.info(
                    'File of size %sB transferred properly' % size)
            else:
                transfer_result = False
                self.logger.error(
                    'File of size %sB not transferred ' % size)
                break

        for size in test_file_sizes:
            self.logger.info("-" * 80)
            self.logger.info("FILE SIZE = %sB" % size)
            self.logger.info("-" * 80)

            self.logger.info('Transferring the file from %s to %s using %s' %
                             (vm2_fixture.vm_name, vm3_fixture.vm_name, mode))
            if os.environ.has_key('ci_image') and self.inputs.get_af() == 'v4' and mode == 'scp':
                file_transfer_result = vm2_fixture.scp_file_transfer_cirros(vm3_fixture, size=size)
            else:
                file_transfer_result = vm2_fixture.check_file_transfer(vm3_fixture,
                                                                   size=size, mode=mode)
            if file_transfer_result:
                self.logger.info(
                    'File of size %sB transferred properly' % size)
            else:
                transfer_result = False
                self.logger.error(
                    'File of size %sB not transferred ' % size)
                break

        assert transfer_result, 'File not transferred via scp '
        return transfer_result
    # end test_vm_file_trf_scp_tests

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_vm_file_trf_scp_tests(self):
         return self.file_trf_tests('scp')

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_vm_file_trf_tftp_tests(self):
        return self.file_trf_tests('tftp')


# IPv6 classes follow
class TestBasicIPv6ESXKVM(TestBasicESXKVM):

    @classmethod
    def setUpClass(cls):
        super(TestBasicIPv6ESXKVM, cls).setUpClass()
        cls.inputs.set_af('v6')

