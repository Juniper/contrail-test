# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import re
import os
from novaclient import client as mynovaclient
from novaclient import exceptions as novaException
import fixtures
import testtools
import unittest

from contrail_test_init import *
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from connections import ContrailConnections
from floating_ip import *
from policy_test import *
from multiple_vn_vm_test import *
from contrail_fixtures import *
from user_test import UserFixture 
from tcutils.wrappers import preposttest_wrapper
from tcutils.commands import *
from testresources import ResourcedTestCase
from floating_ip_test_resource import SolnSetupResource
import traffic_tests
from fabric.context_managers import settings
from fabric.api import run
from floating_ip_shared_net import SharedNetExternalRouter

class TestFipCases(ResourcedTestCase, SharedNetExternalRouter, testtools.TestCase):

    resources = [('base_setup', SolnSetupResource)]

    def __init__(self, *args, **kwargs):
        testtools.TestCase.__init__(self, *args, **kwargs)
        self.res = SolnSetupResource.getResource()
        self.inputs = self.res.inputs
        self.connections = self.res.connections
        self.logger = self.res.logger
        self.nova_fixture = self.res.nova_fixture
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.analytics_obj = self.connections.analytics_obj
        self.vnc_lib = self.connections.vnc_lib

    def __del__(self):
        print "Deleting test_with_setup now"
        SolnSetupResource.finishedWith(self.res)

    def setUp(self):
        super(TestFipCases, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'

    def tearDown(self):
        print "Tearing down test"
        super(TestFipCases, self).tearDown()
        SolnSetupResource.finishedWith(self.res)

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_communication_across_borrower_vm(self):
        '''Test communication between the VMs who has borrowed the FIP from common FIP pool.
        '''
        result = True
        fip_pool_name = 'some-pool1'
        #fvn_name= self.res.fip_vn_name
        fvn_fixture = self.res.fvn1_fixture
        vn1_fixture = self.res.vn1_fixture
        vn2_fixture = self.res.vn2_fixture
        vn1_vm1_fixture = self.res.vn1_vm1_fixture
        vn2_vm1_fixture = self.res.vn2_vm1_fixture
        fvn_vm1_fixture = self.res.fvn1_vm1_fixture
        fvn_subnets = self.res.fvn1_subnets
        vm1_name = self.res.vn1_vm1_name
        vn1_name = self.res.vn1_name
        vn1_subnets = self.res.vn1_subnets
        vm2_name = self.res.vn2_vm1_name
        vn2_name = self.res.vn2_name
        vn2_subnets = self.res.vn2_subnets
        assert fvn_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        assert vn1_vm1_fixture.verify_on_setup()
        assert vn2_vm1_fixture.verify_on_setup()
        assert fvn_vm1_fixture.verify_on_setup()

        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name, vn_id=fvn_fixture.vn_id))
        assert fip_fixture.verify_on_setup()
        fip_id = fip_fixture.create_and_assoc_fip(
            fvn_fixture.vn_id, vn1_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)
        assert fip_fixture.verify_fip(fip_id, vn1_vm1_fixture, fvn_fixture)
        fip_id1 = fip_fixture.create_and_assoc_fip(
            fvn_fixture.vn_id, vn2_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture.verify_fip(fip_id1, vn2_vm1_fixture, fvn_fixture)
        if not vn1_vm1_fixture.ping_with_certainty(fip_fixture.fip[fip_id1]):
            result = result and False
        # fip_fixture.disassoc_and_delete_fip(fip_id)
        # fip_fixture.disassoc_and_delete_fip(fip_id1)
        if not result:
            self.logger.error('Test to ping between VMs %s and %s' %
                              (vm1_name, vm2_name))
            assert result
        return True
    # end test_communication_across_borrower_vm

    @preposttest_wrapper
    def test_mutual_floating_ip(self):
        '''Test communication when 2 VM in 2 diffrent VN borrowing FIP from each other.
        '''
        result = True
        fip_pool_name1 = 'some-pool1'
        fip_pool_name2 = 'some-pool2'
        #fvn_name= self.res.fip_vn_name
        fvn1_fixture = self.res.fvn1_fixture
        fvn2_fixture = self.res.fvn2_fixture
        fvn1_vm1_fixture = self.res.fvn1_vm1_fixture
        fvn1_subnets = self.res.fvn1_subnets
        fvn1_vm1_name = self.res.fvn1_vm1_name
        fvn2_vm1_fixture = self.res.fvn2_vm1_fixture
        fvn2_subnets = self.res.fvn2_subnets
        fvn2_vm1_name = self.res.fvn2_vm1_name
        assert fvn1_fixture.verify_on_setup()
        assert fvn2_fixture.verify_on_setup()
        assert fvn1_vm1_fixture.verify_on_setup()
        assert fvn2_vm1_fixture.verify_on_setup()

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name1, vn_id=fvn1_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()
        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn1_fixture.vn_id, fvn2_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture1.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture1.verify_fip(
            fip_id1, fvn2_vm1_fixture, fvn1_fixture)

        fip_fixture2 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name2, vn_id=fvn2_fixture.vn_id))
        assert fip_fixture2.verify_on_setup()
        fip_id2 = fip_fixture2.create_and_assoc_fip(
            fvn2_fixture.vn_id, fvn1_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture2.disassoc_and_delete_fip, fip_id2)
        assert fip_fixture2.verify_fip(fip_id2, fvn1_vm1_fixture, fvn2_fixture)

        if not fvn2_vm1_fixture.ping_with_certainty(fip_fixture2.fip[fip_id2]):
            result = result and False
        if not fvn1_vm1_fixture.ping_with_certainty(fip_fixture1.fip[fip_id1]):
            result = result and False
        # fip_fixture1.disassoc_and_delete_fip(fip_id1)
        # fip_fixture2.disassoc_and_delete_fip(fip_id2)
        if not result:
            self.logger.error('Test to ping between VMs %s and %s' %
                              (vm1_name, vm2_name))
            assert result
        return result
    # end test_mutual_floating_ip

    @preposttest_wrapper
    def test_exhust_Fip_pool_and_release_fip(self):
        '''Test exhaustion of FIP pool and release and reuse of FIP
        '''
        # This test case combine 2 test case from the test plan
        # 1. Test when FIP is released
        # 2. Test with all the available floating IP pool used/ allocated to
        # diffrent VMs
        result = True
        fip_pool_name1 = 'some-pool1'
        fvn1_fixture = self.res.fvn1_fixture
        fvn2_fixture = self.res.fvn2_fixture
        fvn3_fixture = self.res.fvn3_fixture
        vn1_fixture = self.res.vn1_fixture
        vn2_fixture = self.res.vn2_fixture

        fvn1_vm1_fixture = self.res.fvn1_vm1_fixture
        fvn1_subnets = self.res.fvn1_subnets
        fvn1_vm1_name = self.res.fvn1_vm1_name
        fvn2_vm1_fixture = self.res.fvn2_vm1_fixture
        fvn2_subnets = self.res.fvn2_subnets
        fvn2_vm1_name = self.res.fvn2_vm1_name
        fvn3_vm1_fixture = self.res.fvn3_vm1_fixture
        fvn3_subnets = self.res.fvn3_subnets
        fvn3_vm1_name = self.res.fvn3_vm1_name
        vn1_vm1_fixture = self.res.vn1_vm1_fixture
        vn1_vm2_fixture = self.res.vn1_vm2_fixture
        vn1_subnets = self.res.vn1_subnets
        vn1_vm1_name = self.res.vn1_vm1_name
        vn1_vm2_name = self.res.vn1_vm2_name
        vn2_vm1_fixture = self.res.vn2_vm1_fixture
        vn2_vm2_fixture = self.res.vn2_vm2_fixture
        vn2_subnets = self.res.vn2_subnets
        vn2_vm1_name = self.res.vn2_vm1_name
        vn2_vm2_name = self.res.vn2_vm2_name
        assert fvn1_fixture.verify_on_setup()
        assert fvn2_fixture.verify_on_setup()
        assert fvn3_fixture.verify_on_setup()
        assert fvn1_vm1_fixture.verify_on_setup()
        assert fvn2_vm1_fixture.verify_on_setup()
        assert fvn3_vm1_fixture.verify_on_setup()
        assert vn1_vm1_fixture.verify_on_setup()
        assert vn1_vm2_fixture.verify_on_setup()
        assert vn2_vm1_fixture.verify_on_setup()
        assert vn2_vm2_fixture.verify_on_setup()

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name1, vn_id=fvn3_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()

        # Allocate FIP to multiple IP to exhaust the pool of 5 address
        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn3_fixture.vn_id, vn1_vm1_fixture.vm_id)
        assert fip_fixture1.verify_fip(fip_id1, vn1_vm1_fixture, fvn3_fixture)
        fip_id2 = fip_fixture1.create_and_assoc_fip(
            fvn3_fixture.vn_id, vn1_vm2_fixture.vm_id)
        assert fip_fixture1.verify_fip(fip_id2, vn1_vm2_fixture, fvn3_fixture)
        fip_id3 = fip_fixture1.create_and_assoc_fip(
            fvn3_fixture.vn_id, vn2_vm1_fixture.vm_id)
        assert fip_fixture1.verify_fip(fip_id3, vn2_vm1_fixture, fvn3_fixture)
        fip_id4 = fip_fixture1.create_and_assoc_fip(
            fvn3_fixture.vn_id, vn2_vm2_fixture.vm_id)
        assert fip_fixture1.verify_fip(fip_id4, vn2_vm2_fixture, fvn3_fixture)

        self.logger.info(
            'Here Floating IP pool is alreadu exhausted. Should not allow to add futher.Quantum Exception expected')
        fip_id5 = fip_fixture1.create_and_assoc_fip(
            fvn3_fixture.vn_id, fvn1_vm1_fixture.vm_id)
        if fip_id5 != None:
            self.logger.error(
                'FIP should not get created/asscocited as pool is already exhusted')
            result = result and False
        self.logger.info('Releasing one FIP.')
        fip_fixture1.disassoc_and_delete_fip(fip_id1)

        if not vn1_vm1_fixture.ping_to_ip(fvn3_vm1_fixture.vm_ip):
            self.logger.info(
                "Here ping should fail from VM as FIP is removed ")
        else:
            self.logger.error(
                "Ping should fail. But ping is successful even after removal of FIP from VM %s" % (vn1_vm1_name))
            result = result and False

        self.logger.info('Now FIP should get created and asscociated with %s' %
                         (fvn1_vm1_name))
        fip_id5 = fip_fixture1.create_and_assoc_fip(
            fvn3_fixture.vn_id, fvn1_vm1_fixture.vm_id)
        assert fip_fixture1.verify_fip(
            fip_id5, fvn1_vm1_fixture, fvn3_fixture)
        if not fvn1_vm1_fixture.ping_with_certainty(fvn3_vm1_fixture.vm_ip):
            result = result and False

        fip_fixture1.disassoc_and_delete_fip(fip_id2)
        fip_fixture1.disassoc_and_delete_fip(fip_id3)
        fip_fixture1.disassoc_and_delete_fip(fip_id4)
        fip_fixture1.disassoc_and_delete_fip(fip_id5)
        if not result:
            self.logger.error(
                'Test Failed. Exhaustion of FIP pool test failed')
            assert result
        return result
    # end test_exhust_floating_ip_and_further_block_add

    @preposttest_wrapper
    def test_extend_fip_pool_runtime(self):
        '''Test addition of subnet in VN should extend FIP pool and communication from borrower VM to multiple subnet of allocating VNs
        '''
        # This test case combine 2 test case from the test plan
        # 1. Test when more IP block is added to existing FIP
        # 2. When the allocating VN has multiple subnet, borrower VM should
        # able to communicate all the subnet
        result = True
        fip_pool_name1 = 'some-pool1'
        additional_subnet = '180.1.1.0/24'
        fvn1_fixture = self.res.fvn1_fixture
        fvn2_fixture = self.res.fvn2_fixture
        fvn3_fixture = self.res.fvn3_fixture
        vn1_fixture = self.res.vn1_fixture
        vn2_fixture = self.res.vn2_fixture

        fvn1_vm1_fixture = self.res.fvn1_vm1_fixture
        fvn1_subnets = self.res.fvn1_subnets
        fvn1_vm1_name = self.res.fvn1_vm1_name
        fvn2_vm1_fixture = self.res.fvn2_vm1_fixture
        fvn2_subnets = self.res.fvn2_subnets
        fvn2_vm1_name = self.res.fvn2_vm1_name
        fvn3_vm1_fixture = self.res.fvn3_vm1_fixture
        fvn3_subnets = self.res.fvn3_subnets
        fvn3_vm1_name = self.res.fvn3_vm1_name
        vn1_vm1_fixture = self.res.vn1_vm1_fixture
        vn1_vm2_fixture = self.res.vn1_vm2_fixture
        vn1_subnets = self.res.vn1_subnets
        vn1_vm1_name = self.res.vn1_vm1_name
        vn1_vm2_name = self.res.vn1_vm2_name
        vn2_vm1_fixture = self.res.vn2_vm1_fixture
        vn2_vm2_fixture = self.res.vn2_vm2_fixture
        vn2_subnets = self.res.vn2_subnets
        vn2_vm1_name = self.res.vn2_vm1_name
        vn2_vm2_name = self.res.vn2_vm2_name
        assert fvn1_fixture.verify_on_setup()
        assert fvn2_fixture.verify_on_setup()
        assert fvn3_fixture.verify_on_setup()
        assert fvn1_vm1_fixture.verify_on_setup()
        assert fvn2_vm1_fixture.verify_on_setup()
        assert fvn3_vm1_fixture.verify_on_setup()
        assert vn1_vm1_fixture.verify_on_setup()
        assert vn1_vm2_fixture.verify_on_setup()
        assert vn2_vm1_fixture.verify_on_setup()
        assert vn2_vm2_fixture.verify_on_setup()

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name1, vn_id=fvn3_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()

        # Allocate FIP to multiple IP to exhaust the pool of 5 address
        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn3_fixture.vn_id, vn1_vm1_fixture.vm_id)
        assert fip_fixture1.verify_fip(fip_id1, vn1_vm1_fixture, fvn3_fixture)
        fip_id2 = fip_fixture1.create_and_assoc_fip(
            fvn3_fixture.vn_id, vn1_vm2_fixture.vm_id)
        assert fip_fixture1.verify_fip(fip_id2, vn1_vm2_fixture, fvn3_fixture)
        fip_id3 = fip_fixture1.create_and_assoc_fip(
            fvn3_fixture.vn_id, vn2_vm1_fixture.vm_id)
        assert fip_fixture1.verify_fip(fip_id3, vn2_vm1_fixture, fvn3_fixture)
        fip_id4 = fip_fixture1.create_and_assoc_fip(
            fvn3_fixture.vn_id, vn2_vm2_fixture.vm_id)
        assert fip_fixture1.verify_fip(fip_id4, vn2_vm2_fixture, fvn3_fixture)

        self.logger.info(
            'Here Floating IP pool is already exhausted. Should not allow to add futher.Quantum Exception expected')
        fip_id5 = fip_fixture1.create_and_assoc_fip(
            fvn3_fixture.vn_id, fvn1_vm1_fixture.vm_id)
        if fip_id5 != None:
            self.logger.error(
                'FIP should not get created/asscocited as pool is already exhusted')
            result = result and False

        # Here we need to add further Subnet to FVN3
        fvn3_fixture.add_subnet(additional_subnet)

        # Launching additional VM which should get IP from additional subnet
        additional_vm_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections, vn_obj=fvn3_fixture.obj, vm_name='additional_vm'))
        assert additional_vm_fixture.verify_on_setup()

        # Now verify floating pool is also getting extended and available
        fip_id5 = fip_fixture1.create_and_assoc_fip(
            fvn3_fixture.vn_id, fvn1_vm1_fixture.vm_id)
        assert fip_fixture1.verify_fip(
            fip_id5, fvn1_vm1_fixture, fvn3_fixture)

        # Verify from borrower VM we can ping all the subnet of giving VN
        if not fvn1_vm1_fixture.ping_with_certainty(fvn3_vm1_fixture.vm_ip):
            result = result and False
        if not fvn1_vm1_fixture.ping_with_certainty(additional_vm_fixture.vm_ip):
            result = result and False

        fip_fixture1.disassoc_and_delete_fip(fip_id1)
        fip_fixture1.disassoc_and_delete_fip(fip_id2)
        fip_fixture1.disassoc_and_delete_fip(fip_id3)
        fip_fixture1.disassoc_and_delete_fip(fip_id4)
        fip_fixture1.disassoc_and_delete_fip(fip_id5)
        if not result:
            self.logger.error(
                'Test Failed. Extension of FIP pool and communication multiple subnet test fail')
            assert result
        return result

    # end test_extend_fip_pool_runtime

    @preposttest_wrapper
    def test_service_restart_with_fip(self):
        '''Test restart of agent and control service with floating IP
        '''
        result = True
        fip_pool_name1 = 'some-pool1'
        fip_pool_name2 = 'some-pool2'
        #fvn_name= self.res.fip_vn_name
        fvn1_fixture = self.res.fvn1_fixture
        fvn2_fixture = self.res.fvn2_fixture
        fvn1_vm1_fixture = self.res.fvn1_vm1_fixture
        fvn1_subnets = self.res.fvn1_subnets
        fvn1_vm1_name = self.res.fvn1_vm1_name
        fvn2_vm1_fixture = self.res.fvn2_vm1_fixture
        fvn2_subnets = self.res.fvn2_subnets
        fvn2_vm1_name = self.res.fvn2_vm1_name
        assert fvn1_fixture.verify_on_setup()
        assert fvn2_fixture.verify_on_setup()
        assert fvn1_vm1_fixture.verify_on_setup()
        assert fvn2_vm1_fixture.verify_on_setup()

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name1, vn_id=fvn1_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()
        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn1_fixture.vn_id, fvn2_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture1.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture1.verify_fip(
            fip_id1, fvn2_vm1_fixture, fvn1_fixture)

        fip_fixture2 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name2, vn_id=fvn2_fixture.vn_id))
        assert fip_fixture2.verify_on_setup()
        fip_id2 = fip_fixture2.create_and_assoc_fip(
            fvn2_fixture.vn_id, fvn1_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture2.disassoc_and_delete_fip, fip_id2)
        assert fip_fixture2.verify_fip(fip_id2, fvn1_vm1_fixture, fvn2_fixture)

        if not fvn2_vm1_fixture.ping_with_certainty(fip_fixture2.fip[fip_id2]):
            result = result and False
        if not fvn1_vm1_fixture.ping_with_certainty(fip_fixture1.fip[fip_id1]):
            result = result and False

        self.logger.info('Will restart compute  services now')
        for compute_ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter', [compute_ip])
        sleep(10)
        assert fvn1_vm1_fixture.verify_on_setup()
        assert fvn2_vm1_fixture.verify_on_setup()
        if not fvn2_vm1_fixture.ping_with_certainty(fip_fixture2.fip[fip_id2]):
            result = result and False
        if not fvn1_vm1_fixture.ping_with_certainty(fip_fixture1.fip[fip_id1]):
            result = result and False

        self.logger.info('Will restart control services now')
        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('contrail-control', [bgp_ip])
        sleep(10)
        assert fvn1_vm1_fixture.verify_on_setup()
        assert fvn2_vm1_fixture.verify_on_setup()
        if not fvn2_vm1_fixture.ping_with_certainty(fip_fixture2.fip[fip_id2]):
            result = result and False
        if not fvn1_vm1_fixture.ping_with_certainty(fip_fixture1.fip[fip_id1]):
            result = result and False

        # fip_fixture1.disassoc_and_delete_fip(fip_id1)
        # fip_fixture2.disassoc_and_delete_fip(fip_id2)
        if not result:
            self.logger.error(
                'Test Failed for restart of agent and control node with floating IP')
            assert result
        return result
    # end test_service_restart_with_fip

    @preposttest_wrapper
    def test_fip_with_traffic(self):
        '''Testtraffic accross borrower and giving VN.
        '''
        result = True
        fip_pool_name1 = 'some-pool1'
        fvn1_fixture = self.res.fvn1_fixture
        fvn1_vm1_traffic_fixture = self.res.fvn1_vm1_traffic_fixture
        fvn1_subnets = self.res.fvn1_subnets
        fvn1_vm1_traffic_name = self.res.fvn1_vm1_traffic_name
        vn1_fixture = self.res.vn1_fixture
        vn1_vm1_traffic_fixture = self.res.vn1_vm1_traffic_fixture
        vn1_subnets = self.res.vn1_subnets
        vn1_vm1_traffic_name = self.res.vn1_vm1_traffic_name

        assert fvn1_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert fvn1_vm1_traffic_fixture.verify_on_setup()
        assert vn1_vm1_traffic_fixture.verify_on_setup()
        fvn1_vm1_traffic_fixture.wait_till_vm_is_up()
        vn1_vm1_traffic_fixture.wait_till_vm_is_up()

        # Install traffic pkg in VM
        vn1_vm1_traffic_fixture.install_pkg("Traffic")
        fvn1_vm1_traffic_fixture.install_pkg("Traffic")

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name1, vn_id=fvn1_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()

        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn1_fixture.vn_id, vn1_vm1_traffic_fixture.vm_id)
        self.addCleanup(fip_fixture1.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture1.verify_fip(
            fip_id1, vn1_vm1_traffic_fixture, fvn1_fixture)
        if not vn1_vm1_traffic_fixture.ping_with_certainty(fvn1_vm1_traffic_fixture.vm_ip):
            result = result and False

        # Send UDP traffic
        fvn1_vm1_traffic_fixture.install_pkg("Traffic")
        vn1_vm1_traffic_fixture.install_pkg("Traffic")

        # Verify Traffic ---
        # Start Traffic
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['udp']
        total_streams = {}
        total_streams['udp'] = 1
        dpi = 9100
        proto = 'udp'
        for proto in traffic_proto_l:
            traffic_obj[proto] = {}
            startStatus[proto] = {}
            traffic_obj[proto] = self.useFixture(
                traffic_tests.trafficTestFixture(self.connections))
            # def startTraffic (self, name=name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
            # packet_size= 100, start_sport= 8000,
            # total_single_instance_streams= 20):
            startStatus[proto] = traffic_obj[proto].startTraffic(
                num_streams=total_streams[proto], start_port=dpi,
                tx_vm_fixture=vn1_vm1_traffic_fixture, rx_vm_fixture=fvn1_vm1_traffic_fixture, stream_proto=proto)
            self.logger.info("Status of start traffic : %s, %s, %s" %
                             (proto, vn1_vm1_traffic_fixture.vm_ip, startStatus[proto]))
            if startStatus[proto]['status'] != True:
                result = False
        self.logger.info("-" * 80)

        # Poll live traffic
        traffic_stats = {}
        self.logger.info("Poll live traffic and get status..")
        for proto in traffic_proto_l:
            traffic_stats = traffic_obj[proto].getLiveTrafficStats()
            err_msg = "Traffic disruption is seen: details: "
        #self.assertEqual(traffic_stats['status'], True, err_msg)
        assert(traffic_stats['status'] == True), err_msg
        self.logger.info("-" * 80)

        # Verify Flow records here
        inspect_h1 = self.agent_inspect[vn1_vm1_traffic_fixture.vm_node_ip]
        inspect_h2 = self.agent_inspect[fvn1_vm1_traffic_fixture.vm_node_ip]
        flow_rec1 = None
        udp_src = unicode(8000)
        dpi = unicode(dpi)

        # Verify Ingress Traffic
        self.logger.info('Verifying Ingress Flow Record')
        flow_rec1 = inspect_h1.get_vna_fetchflowrecord(vrf=vn1_vm1_traffic_fixture.agent_vrf_objs['vrf_list'][0][
                                                       'ucindex'], sip=vn1_vm1_traffic_fixture.vm_ip, dip=fvn1_vm1_traffic_fixture.vm_ip, sport=udp_src, dport=dpi, protocol='17')

        if flow_rec1 is not None:
            self.logger.info('Verifying NAT in flow records')
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec1, 'nat', 'enabled')
            if match is False:
                self.logger.error(
                    'Test Failed. NAT is not enabled in given flow. Flow details %s' % (flow_rec1))
                result = result and False
            self.logger.info('Verifying traffic direction in flow records')
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec1, 'direction', 'ingress')
            if match is False:
                self.logger.error(
                    'Test Failed. Traffic direction is wrong should be ingress. Flow details %s' % (flow_rec1))
                result = result and False
        else:
            self.logger.error(
                'Test Failed. Required ingress Traffic flow not found')
            result = result and False

        # Verify Egress Traffic
        # Check VMs are in same agent or not. Need to compute source vrf
        # accordingly
        if vn1_vm1_traffic_fixture.vm_node_ip != fvn1_vm1_traffic_fixture.vm_node_ip:
            source_vrf = vn1_vm1_traffic_fixture.agent_vrf_objs[
                'vrf_list'][0]['ucindex']
        else:
            vrf_list = inspect_h1.get_vna_vrf_objs(
                vn_name=fvn1_vm1_traffic_fixture.vn_name)
            source_vrf = vrf_list['vrf_list'][0]['ucindex']
        self.logger.info('Verifying Egress Flow Records')
        flow_rec2 = inspect_h1.get_vna_fetchflowrecord(
            vrf=source_vrf, sip=fvn1_vm1_traffic_fixture.vm_ip, dip=fip_fixture1.fip[fip_id1], sport=dpi, dport=udp_src, protocol='17')
        if flow_rec2 is not None:
            self.logger.info('Verifying NAT in flow records')
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec2, 'nat', 'enabled')
            if match is False:
                self.logger.error(
                    'Test Failed. NAT is not enabled in given flow. Flow details %s' % (flow_rec2))
                result = result and False
            self.logger.info('Verifying traffic direction in flow records')
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec2, 'direction', 'egress')
            if match is False:
                self.logger.error(
                    'Test Failed. Traffic direction is wrong should be Egress. Flow details %s' % (flow_rec1))
                result = result and False
        else:
            self.logger.error(
                'Test Failed. Required Egress Traffic flow not found')
            result = result and False

        # Stop Traffic
        self.logger.info("Proceed to stop traffic..")
        self.logger.info("-" * 80)
        for proto in traffic_proto_l:
            stopStatus[proto] = {}
            stopStatus[proto] = traffic_obj[proto].stopTraffic()
            #if stopStatus[proto] != []: msg.append(stopStatus[proto]); result= False
            if stopStatus[proto] != []:
                result = False
            self.logger.info("Status of stop traffic for proto %s is %s" %
                             (proto, stopStatus[proto]))
        self.logger.info("-" * 80)
        if not result:
            self.logger.error(
                'Test Failed. Floating IP test with traffic failed')
            assert result
        return result
    # end test_fip_with_traffic

    @preposttest_wrapper
    def test_removal_of_fip_with_traffic(self):
        '''Test the removal of FIP with back ground traffic. Verify the impact on flow also.
        '''
        result = True
        fip_pool_name1 = 'some-pool1'
        fvn1_fixture = self.res.fvn1_fixture
        fvn1_vm1_traffic_fixture = self.res.fvn1_vm1_traffic_fixture
        fvn1_subnets = self.res.fvn1_subnets
        fvn1_vm1_traffic_name = self.res.fvn1_vm1_traffic_name
        vn1_fixture = self.res.vn1_fixture
        vn1_vm1_traffic_fixture = self.res.vn1_vm1_traffic_fixture
        vn1_subnets = self.res.vn1_subnets
        vn1_vm1_traffic_name = self.res.vn1_vm1_traffic_name

        assert fvn1_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert fvn1_vm1_traffic_fixture.verify_on_setup()
        assert vn1_vm1_traffic_fixture.verify_on_setup()

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name1, vn_id=fvn1_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()

        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn1_fixture.vn_id, vn1_vm1_traffic_fixture.vm_id)
        assert fip_fixture1.verify_fip(
            fip_id1, vn1_vm1_traffic_fixture, fvn1_fixture)
        if not vn1_vm1_traffic_fixture.ping_with_certainty(fvn1_vm1_traffic_fixture.vm_ip):
            result = result and False

        fvn1_vm1_traffic_fixture.wait_till_vm_is_up()
        vn1_vm1_traffic_fixture.wait_till_vm_is_up()
        # Install traffic pkg in VM
        vn1_vm1_traffic_fixture.install_pkg("Traffic")
        fvn1_vm1_traffic_fixture.install_pkg("Traffic")

        # Verify Traffic ---
        # Start Traffic
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['udp']
        total_streams = {}
        total_streams['udp'] = 1
        dpi = 9100
        proto = 'udp'
        for proto in traffic_proto_l:
            traffic_obj[proto] = {}
            startStatus[proto] = {}
            traffic_obj[proto] = self.useFixture(
                traffic_tests.trafficTestFixture(self.connections))
            # def startTraffic (self, name=name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
            # packet_size= 100, start_sport= 8000,
            # total_single_instance_streams= 20):
            startStatus[proto] = traffic_obj[proto].startTraffic(
                num_streams=total_streams[proto], start_port=dpi,
                tx_vm_fixture=vn1_vm1_traffic_fixture, rx_vm_fixture=fvn1_vm1_traffic_fixture, stream_proto=proto)
            self.logger.info("Status of start traffic : %s, %s, %s" %
                             (proto, vn1_vm1_traffic_fixture.vm_ip, startStatus[proto]))
            #if startStatus[proto] != None: msg.append(startStatus[proto]); result= False
            if startStatus[proto]['status'] != True:
                result = False
        self.logger.info("-" * 80)

        # Poll live traffic
        traffic_stats = {}
        self.logger.info("Poll live traffic and get status..")
        for proto in traffic_proto_l:
            traffic_stats = traffic_obj[proto].getLiveTrafficStats()
            err_msg = "Traffic disruption is seen: details: "
        #self.assertEqual(traffic_stats['status'], True, err_msg)
        assert(traffic_stats['status'] == True), err_msg
        self.logger.info("-" * 80)
        self.logger.info(
            "Removing/disassociating FIP here. Now Traffic should stopped")
        fip_fixture1.disassoc_and_delete_fip(fip_id1)
        sleep(2)

        # Poll live traffic
        traffic_stats = {}
        self.logger.info(
            "Traffic expected to stop flowing as FIP removed.Disruption expected.")
        for proto in traffic_proto_l:
            traffic_stats = traffic_obj[proto].getLiveTrafficStats()
            err_msg = "Traffic NOT stopped after FIP removal "
        #self.assertEqual(traffic_stats['status'], False, err_msg)
        assert(traffic_stats['status'] == False), err_msg
        self.logger.info("-" * 80)

        # Verify Flow records here
        inspect_h1 = self.agent_inspect[vn1_vm1_traffic_fixture.vm_node_ip]
        inspect_h2 = self.agent_inspect[fvn1_vm1_traffic_fixture.vm_node_ip]
        flow_rec1 = None
        udp_src = unicode(8000)
        dpi = unicode(dpi)

        # Verify Ingress Traffic
        self.logger.info('Verifying Ingress Flow Record')
        flow_rec1 = inspect_h1.get_vna_fetchflowrecord(vrf=vn1_vm1_traffic_fixture.agent_vrf_objs['vrf_list'][0][
                                                       'ucindex'], sip=vn1_vm1_traffic_fixture.vm_ip, dip=fvn1_vm1_traffic_fixture.vm_ip, sport=udp_src, dport=dpi, protocol='17')

        if flow_rec1 is not None:
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec1, 'short_flow', 'yes')
            if match is False:
                self.logger.error(
                    'Test Failed. After removal of FIP flow type should be short_flow. Flow details %s' % (flow_rec1))
                result = result and False
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec1, 'dst_vn', '__UNKNOWN__')
            if match is False:
                self.logger.error(
                    'Test Failed. After removal of FIP destination VN should be unkwown. Flow details %s' % (flow_rec1))
                result = result and False
        # Verify Egress Traffic
        self.logger.info('Verifying Egress Flow Records')
        # Check VMs are in same agent or not. Need to compute source vrf
        # accordingly
        if vn1_vm1_traffic_fixture.vm_node_ip != fvn1_vm1_traffic_fixture.vm_node_ip:
            source_vrf = vn1_vm1_traffic_fixture.agent_vrf_objs[
                'vrf_list'][0]['ucindex']
        else:
            vrf_list = inspect_h1.get_vna_vrf_objs(
                vn_name=fvn1_vm1_traffic_fixture.vn_name)
            source_vrf = vrf_list['vrf_list'][0]['ucindex']

        flow_rec2 = inspect_h1.get_vna_fetchflowrecord(
            vrf=source_vrf, sip=fvn1_vm1_traffic_fixture.vm_ip, dip=fip_fixture1.fip[fip_id1], sport=dpi, dport=udp_src, protocol='17')
        if flow_rec2 is not None:
            self.logger.error(
                'Test Failed. Egress Flow records entry should be removed after removal of FIP. It still exists.')
            self.logger.error('Flow record entry: %s' % (flow_rec2))
            result = result and False

        else:
            self.logger.info(
                'Verification successful. Egress flow records removed')

        flow_rec3 = inspect_h1.get_vna_fetchflowrecord(
            vrf=source_vrf, sip=fvn1_vm1_traffic_fixture.vm_ip, dip=vn1_vm1_traffic_fixture.vm_ip, sport=dpi, dport=udp_src, protocol='17')
        if flow_rec3 is not None:
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec3, 'short_flow', 'yes')
            if match is False:
                self.logger.error(
                    'Test Failed. After removal of FIP flow type should be short_flow. Flow details %s' % (flow_rec3))
                result = result and False
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec3, 'dst_vn', '__UNKNOWN__')
            if match is False:
                self.logger.error(
                    'Test Failed. After removal of FIP destination VN should be unkwown. Flow details %s' % (flow_rec3))
                result = result and False

        # Stop Traffic
        self.logger.info("Proceed to stop traffic..")
        self.logger.info("-" * 80)
        for proto in traffic_proto_l:
            stopStatus[proto] = {}
            stopStatus[proto] = traffic_obj[proto].stopTraffic()
        self.logger.info("-" * 80)

        if not result:
            self.logger.error(
                'Test Failed. Traffic not stopped/flow still exists after FIP removal')
            assert result
        return result
    # end test_removal_of_fip_with_traffic

    @preposttest_wrapper
    def test_traffic_with_control_node_switchover(self):
        ''' Stop the control node and check peering with agent fallback to other control node.

        '''
        if len(set(self.inputs.bgp_ips)) < 2:
            raise self.skipTest(
                "Skiping Test. At least 2 control node required to run the test")
        result = True
        fip_pool_name1 = 'some-pool1'
        fvn1_fixture = self.res.fvn1_fixture
        fvn1_vm1_traffic_fixture = self.res.fvn1_vm1_traffic_fixture
        fvn1_subnets = self.res.fvn1_subnets
        fvn1_vm1_traffic_name = self.res.fvn1_vm1_traffic_name
        vn1_fixture = self.res.vn1_fixture
        vn1_vm1_traffic_fixture = self.res.vn1_vm1_traffic_fixture
        vn1_subnets = self.res.vn1_subnets
        vn1_vm1_traffic_name = self.res.vn1_vm1_traffic_name

        assert fvn1_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert fvn1_vm1_traffic_fixture.verify_on_setup()
        assert vn1_vm1_traffic_fixture.verify_on_setup()

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name1, vn_id=fvn1_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()

        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn1_fixture.vn_id, vn1_vm1_traffic_fixture.vm_id)
        self.addCleanup(fip_fixture1.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture1.verify_fip(
            fip_id1, vn1_vm1_traffic_fixture, fvn1_fixture)
        if not vn1_vm1_traffic_fixture.ping_with_certainty(fvn1_vm1_traffic_fixture.vm_ip):
            result = result and False

        # Figuring the active control node
        active_controller = None
        inspect_h = self.agent_inspect[vn1_vm1_traffic_fixture.vm_node_ip]
        agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                active_controller = entry['controller_ip']
        self.logger.info('Active control node from the Agent %s is %s' %
                         (vn1_vm1_traffic_fixture.vm_node_ip, active_controller))

        fvn1_vm1_traffic_fixture.wait_till_vm_is_up()
        vn1_vm1_traffic_fixture.wait_till_vm_is_up()
        # Install traffic pkg in VM
        vn1_vm1_traffic_fixture.install_pkg("Traffic")
        fvn1_vm1_traffic_fixture.install_pkg("Traffic")
        # Start Traffic
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['icmp']
        total_streams = {}
        total_streams[
            'icmp'] = 1
        dpi = 9100
        proto = 'icmp'
        for proto in traffic_proto_l:
            traffic_obj[proto] = {}
            startStatus[proto] = {}
            traffic_obj[proto] = self.useFixture(
                traffic_tests.trafficTestFixture(self.connections))
            startStatus[proto] = traffic_obj[proto].startTraffic(
                num_streams=total_streams[proto], start_port=dpi,
                tx_vm_fixture=vn1_vm1_traffic_fixture, rx_vm_fixture=fvn1_vm1_traffic_fixture, stream_proto=proto)
            self.logger.info("Status of start traffic : %s, %s, %s" %
                             (proto, vn1_vm1_traffic_fixture.vm_ip, startStatus[proto]))
            if startStatus[proto]['status'] != True:
                result = False
        self.logger.info("-" * 80)

        # Poll live traffic
        traffic_stats = {}
        self.logger.info("Poll live traffic and get status..")
        for proto in traffic_proto_l:
            traffic_stats = traffic_obj[proto].getLiveTrafficStats()
            err_msg = "Traffic disruption is seen: details: "
        #self.assertEqual(traffic_stats['status'], True, err_msg)
        assert(traffic_stats['status'] == True), err_msg
        self.logger.info("-" * 80)

        # Stop on Active node
        self.logger.info('Stoping the Control service in  %s' %
                         (active_controller))
        self.inputs.stop_service('contrail-control', [active_controller])
        sleep(5)

        # Check the control node shifted to other control node
        new_active_controller = None
        new_active_controller_state = None
        inspect_h = self.agent_inspect[vn1_vm1_traffic_fixture.vm_node_ip]
        agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                new_active_controller = entry['controller_ip']
                new_active_controller_state = entry['state']
        self.logger.info('Active control node from the Agent %s is %s' %
                         (vn1_vm1_traffic_fixture.vm_node_ip, new_active_controller))
        if new_active_controller == active_controller:
            self.logger.error(
                'Control node switchover fail. Old Active controlnode was %s and new active control node is %s' %
                (active_controller, new_active_controller))
            result = False
        if new_active_controller_state != 'Established':
            self.logger.error(
                'Agent does not have Established XMPP connection with Active control node')
            result = result and False

        # Verify Flow records here
        inspect_h1 = self.agent_inspect[vn1_vm1_traffic_fixture.vm_node_ip]
        inspect_h2 = self.agent_inspect[fvn1_vm1_traffic_fixture.vm_node_ip]
        flow_rec1 = None
        udp_src = unicode(8000)
        dpi = unicode(dpi)

        # Verify Ingress Traffic
        self.logger.info('Verifying Ingress Flow Record')
        flow_rec1 = inspect_h1.get_vna_fetchflowrecord(vrf=vn1_vm1_traffic_fixture.agent_vrf_objs['vrf_list'][0][
                                                       'ucindex'], sip=vn1_vm1_traffic_fixture.vm_ip, dip=fvn1_vm1_traffic_fixture.vm_ip, sport='0', dport='0', protocol='1')

        if flow_rec1 is not None:
            self.logger.info('Verifying NAT in flow records')
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec1, 'nat', 'enabled')
            if match is False:
                self.logger.error(
                    'Test Failed. NAT is not enabled in given flow. Flow details %s' % (flow_rec1))
                result = result and False
            self.logger.info('Verifying traffic direction in flow records')
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec1, 'direction', 'ingress')
            if match is False:
                self.logger.error(
                    'Test Failed. Traffic direction is wrong should be ingress. Flow details %s' % (flow_rec1))
                result = result and False
        else:
            self.logger.error(
                'Test Failed. Required ingress Traffic flow not found')
            result = result and False

        # Verify Egress Traffic
        # Check VMs are in same agent or not. Need to compute source vrf
        # accordingly
        if vn1_vm1_traffic_fixture.vm_node_ip != fvn1_vm1_traffic_fixture.vm_node_ip:
            source_vrf = vn1_vm1_traffic_fixture.agent_vrf_objs[
                'vrf_list'][0]['ucindex']
        else:
            vrf_list = inspect_h1.get_vna_vrf_objs(
                vn_name=fvn1_vm1_traffic_fixture.vn_name)
            source_vrf = vrf_list['vrf_list'][0]['ucindex']
        self.logger.info('Verifying Egress Flow Records')
        flow_rec2 = inspect_h1.get_vna_fetchflowrecord(
            vrf=source_vrf, sip=fvn1_vm1_traffic_fixture.vm_ip, dip=fip_fixture1.fip[fip_id1], sport='0', dport='0', protocol='1')
        if flow_rec2 is not None:
            self.logger.info('Verifying NAT in flow records')
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec2, 'nat', 'enabled')
            if match is False:
                self.logger.error(
                    'Test Failed. NAT is not enabled in given flow. Flow details %s' % (flow_rec2))
                result = result and False
            self.logger.info('Verifying traffic direction in flow records')
            match = inspect_h1.match_item_in_flowrecord(
                flow_rec2, 'direction', 'egress')
            if match is False:
                self.logger.error(
                    'Test Failed. Traffic direction is wrong should be Egress. Flow details %s' % (flow_rec1))
                result = result and False
        else:
            self.logger.error(
                'Test Failed. Required Egress Traffic flow not found')
            result = result and False

        # Stop Traffic
        self.logger.info("Proceed to stop traffic..")
        self.logger.info("-" * 80)
        for proto in traffic_proto_l:
            stopStatus[proto] = {}
            stopStatus[proto] = traffic_obj[proto].stopTraffic()
            #if stopStatus[proto] != []: msg.append(stopStatus[proto]); result= False
            if stopStatus[proto] != []:
                result = False
            self.logger.info("Status of stop traffic for proto %s is %s" %
                             (proto, stopStatus[proto]))
        self.logger.info("-" * 80)

        # Start the control node service again
        self.logger.info('Starting the Control service in  %s' %
                         (active_controller))
        self.inputs.start_service('contrail-control', [active_controller])

        sleep(10)
        # Check the BGP peering status from the currently active control node
        self.logger.info(
            'Checking the BGP peering from new active controler  %s' %
            (new_active_controller))
        cn_bgp_entry = self.cn_inspect[
            new_active_controller].get_cn_bgp_neigh_entry()
        sleep(5)
        for entry in cn_bgp_entry:
            if entry['state'] != 'Established':
                result = result and False
                self.logger.error(
                    'With Peer %s peering is not Established. Current State %s ' %
                    (entry['peer'], entry['state']))

        # fip_fixture1.disassoc_and_delete_fip(fip_id1)
        if not result:
            self.logger.error('Switchover of control node failed')
            assert result
        return True
    # end test_traffic_with_control_node_switchover

    @preposttest_wrapper
    def test_fip_in_uve(self):
        '''Test analytics information for FIP
        '''
        result = True
        fip_pool_name = 'some-pool1'
        fvn_fixture = self.res.fvn1_fixture
        vn1_fixture = self.res.vn1_fixture
        vn1_vm1_fixture = self.res.vn1_vm1_fixture
        fvn_subnets = self.res.fvn1_subnets
        vm1_name = self.res.vn1_vm1_name
        vn1_name = self.res.vn1_name
        vn1_subnets = self.res.vn1_subnets
        assert fvn_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert vn1_vm1_fixture.verify_on_setup()

        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name, vn_id=fvn_fixture.vn_id))
        assert fip_fixture.verify_on_setup()
        fip_id = fip_fixture.create_and_assoc_fip(
            fvn_fixture.vn_id, vn1_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)
        assert fip_fixture.verify_fip(fip_id, vn1_vm1_fixture, fvn_fixture)

        # Verify FIP details in analytics UVE
        self.logger.info("Verifying FIP details in UVE")
        result = fip_fixture.verify_fip_in_uve(
            fip_fixture.fip[fip_id], vn1_vm1_fixture, fvn_fixture)
        # fip_fixture.disassoc_and_delete_fip(fip_id)
        if not result:
            self.logger.error('FIP verification in UVE has failed')
            assert result
        return True
    # end test_fip_in_uve

    @preposttest_wrapper
    def test_vm_restart_with_fip(self):
        '''Test restart of VM with Floating IP.
        '''
        result = True
        fip_pool_name1 = 'some-pool1'
        fvn1_fixture = self.res.fvn1_fixture
        fvn1_vm1_fixture = self.res.fvn1_vm1_fixture
        fvn1_subnets = self.res.fvn1_subnets
        fvn1_vm1_name = self.res.fvn1_vm1_name
        vn1_fixture = self.res.vn1_fixture
        vn1_vm1_fixture = self.res.vn1_vm1_fixture
        vn1_subnets = self.res.vn1_subnets
        vn1_vm1_name = self.res.vn1_vm1_name

        assert fvn1_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert fvn1_vm1_fixture.verify_on_setup()
        assert vn1_vm1_fixture.verify_on_setup()
        fvn1_vm1_fixture.wait_till_vm_is_up()
        vn1_vm1_fixture.wait_till_vm_is_up()

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name1, vn_id=fvn1_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()

        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn1_fixture.vn_id, vn1_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture1.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture1.verify_fip(fip_id1, vn1_vm1_fixture, fvn1_fixture)
        if not vn1_vm1_fixture.ping_with_certainty(fvn1_vm1_fixture.vm_ip):
            result = result and False

        # Restart the VM here
        self.logger.info('Rebooting the VM  %s' % (vn1_vm1_name))
        cmd_to_reboot_vm = ['reboot']
        vn1_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_reboot_vm)
        vn1_vm1_traffic_fixture.wait_till_vm_is_up()
        assert vn1_vm1_fixture.verify_on_setup()
        self.logger.info('Verify the connectivity to other VN via floating IP')
        if not vn1_vm1_fixture.ping_with_certainty(fvn1_vm1_fixture.vm_ip):
            result = result and False

        if not result:
            self.logger.error('Test VM restart with FIP failed')
            assert result
        return True
    # end test_vm_restart_with_fip

    @preposttest_wrapper
    def test_vn_info_in_agent_with_fip(self):
        '''Test VN information available in in agent when FIP allocated.
        '''
        result = True
        fip_pool_name1 = 'some-pool1'
        fvn1_fixture = self.res.fvn1_fixture
        fvn1_vm1_fixture = self.res.fvn1_vm1_fixture
        fvn1_subnets = self.res.fvn1_subnets
        fvn1_name = self.res.fvn1_name
        fvn1_vm1_name = self.res.fvn1_vm1_name
        vn1_fixture = self.res.vn1_fixture
        vn1_vm1_fixture = self.res.vn1_vm1_fixture
        vn1_subnets = self.res.vn1_subnets
        vn1_vm1_name = self.res.vn1_vm1_name

        assert fvn1_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert fvn1_vm1_fixture.verify_on_setup()
        assert vn1_vm1_fixture.verify_on_setup()
        fvn1_vm1_fixture.wait_till_vm_is_up()
        vn1_vm1_fixture.wait_till_vm_is_up()

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name1, vn_id=fvn1_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()

        # Checking the allocating VN info in borrower VM agent.
        self.logger.info(
            'Checking the VN informatiopn of FIP allocating VN is already present in agent of borrower VN or not')
        inspect_h1 = self.agent_inspect[vn1_vm1_fixture.vm_node_ip]
        vn_fq_name = inspect_h1.get_vna_vn(vn_name=fvn1_name)

        if vn_fq_name is None:
            self.logger.info('VN info for %s is not present in agent %s' %
                             (fvn1_name, vn1_vm1_fixture.vm_node_ip))
        else:
            self.logger.error(
                'VN info for %s is already present in agent %s. Setup problem. Existing the test here' %
                (fvn1_name, vn1_vm1_fixture.vm_node_ip))
            result = result & False
            assert result

        # Allocate the FIP here
        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn1_fixture.vn_id, vn1_vm1_fixture.vm_id)
        #self.addCleanup( fip_fixture1.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture1.verify_fip(fip_id1, vn1_vm1_fixture, fvn1_fixture)
        if not vn1_vm1_fixture.ping_with_certainty(fvn1_vm1_fixture.vm_ip):
            result = result and False

        # Checking the allocating VN info in borrower VM agent.
        vn_fq_name = inspect_h1.get_vna_vn(vn_name=fvn1_name)
        if vn_fq_name is None:
            self.logger.info(
                'FIP allocating VN  %s is not present in agent  %s' %
                (fvn1_name, vn1_vm1_fixture.vm_node_ip))
            result = result & False
            fip_fixture1.disassoc_and_delete_fip(fip_id1)
            assert result
        else:
            self.logger.info('VN info for %s is present in agent %s.' %
                             (fvn1_name, vn1_vm1_fixture.vm_node_ip))

        # Disasscotite the fixture here
        self.logger.info('Dis associating the FIP %s from VM  %s' %
                         (fip_fixture1.fip[fip_id1], vn1_vm1_name))
        fip_fixture1.disassoc_and_delete_fip(fip_id1)

        vn_fq_name = inspect_h1.get_vna_vn(vn_name=fvn1_name)

        if vn_fq_name is None:
            self.logger.info('VN info for %s is no more  present in agent %s' %
                             (fvn1_name, vn1_vm1_fixture.vm_node_ip))
        else:
            self.logger.error(
                'VN info for %s is still present in agent %s after removal of FIP' %
                (fvn1_name, vn1_vm1_fixture.vm_node_ip))
            result = result & False
        if not result:
            self.logger.error('Test VN info in agent with FIP failed')
            assert result
        return True
    # end test_vn_info_in_agent_with_fip

    @preposttest_wrapper
    def test_fip_with_policy(self):
        '''Test interation of FIP with policy .
        '''
        result = True
        fip_pool_name1 = 'some-pool1'
        fvn1_fixture = self.res.fvn1_fixture
        fvn1_vm1_fixture = self.res.fvn1_vm1_fixture
        fvn1_subnets = self.res.fvn1_subnets
        fvn1_name = self.res.fvn1_name
        fvn1_vm1_name = self.res.fvn1_vm1_name
        fvn2_fixture = self.res.fvn2_fixture
        fvn2_vm1_fixture = self.res.fvn2_vm1_fixture
        fvn2_subnets = self.res.fvn2_subnets
        fvn2_name = self.res.fvn2_name
        fvn2_vm1_name = self.res.fvn2_vm1_name
        vn1_fixture = self.res.vn1_fixture
        vn1_vm1_fixture = self.res.vn1_vm1_fixture
        vn1_subnets = self.res.vn1_subnets
        vn1_vm1_name = self.res.vn1_vm1_name
        vn2_fixture = self.res.vn2_fixture
        vn2_vm1_fixture = self.res.vn2_vm1_fixture
        vn2_subnets = self.res.vn2_subnets
        vn2_vm1_name = self.res.vn2_vm1_name

        assert fvn1_fixture.verify_on_setup()
        assert fvn2_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        assert fvn1_vm1_fixture.verify_on_setup()
        assert fvn2_vm1_fixture.verify_on_setup()
        assert vn1_vm1_fixture.verify_on_setup()
        assert vn2_vm1_fixture.verify_on_setup()

        # Apply policy in between VN
        policy1_name = 'policy1'
        policy2_name = 'policy2'
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': fvn1_name,
                'dest_network': fvn2_name,
            },
        ]
        rev_rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': fvn2_name,
                'dest_network': fvn1_name,
            },
        ]

        # Policy
        policy1_fixture = self.useFixture(PolicyFixture(
            policy_name=policy1_name, rules_list=rules, inputs=self.inputs, connections=self.connections))
        policy2_fixture = self.useFixture(PolicyFixture(
            policy_name=policy2_name, rules_list=rev_rules, inputs=self.inputs, connections=self.connections))

        self.logger.info('Apply policy between VN %s and %s' %
                         (fvn1_name, fvn2_name))
        fvn1_fixture.bind_policies(
            [policy1_fixture.policy_fq_name], fvn1_fixture.vn_id)
        self.addCleanup(fvn1_fixture.unbind_policies,
                        fvn1_fixture.vn_id, [policy1_fixture.policy_fq_name])
        fvn2_fixture.bind_policies(
            [policy2_fixture.policy_fq_name], fvn2_fixture.vn_id)
        self.addCleanup(fvn2_fixture.unbind_policies,
                        fvn2_fixture.vn_id, [policy2_fixture.policy_fq_name])
        self.logger.info('Ping from %s to %s' % (fvn1_vm1_name, fvn2_vm1_name))
        if not fvn1_vm1_fixture.ping_with_certainty(fvn2_vm1_fixture.vm_ip):
            result = result and False

        # FIP
        self.logger.info("Configuring floating IP now")
        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name1, vn_id=fvn1_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()

        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn1_fixture.vn_id, vn1_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture1.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture1.verify_fip(fip_id1, vn1_vm1_fixture, fvn1_fixture)

        fip_id2 = fip_fixture1.create_and_assoc_fip(
            fvn1_fixture.vn_id, vn2_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture1.disassoc_and_delete_fip, fip_id2)
        assert fip_fixture1.verify_fip(fip_id2, vn2_vm1_fixture, fvn1_fixture)

        self.logger.info(
            'Ping from from VM %s to Other VM in different network with FIP %s ' %
            (vn1_vm1_name, fip_fixture1.fip[fip_id2]))
        if not vn1_vm1_fixture.ping_with_certainty(fip_fixture1.fip[fip_id2]):
            result = result and False

        self.logger.info('Ping from from VM %s to IP  %s in VN %s' %
                         (vn1_vm1_name, fvn2_vm1_fixture.vm_ip, fvn2_vm1_name))
        if not vn1_vm1_fixture.ping_with_certainty(fvn2_vm1_fixture.vm_ip):
            result = result and False

        # Unbind
        fvn1_fixture.unbind_policies(
            fvn1_fixture.vn_id, [policy1_fixture.policy_fq_name])
        fvn2_fixture.unbind_policies(
            fvn2_fixture.vn_id, [policy2_fixture.policy_fq_name])

        sleep(2)

        if not vn1_vm1_fixture.ping_to_ip(fvn2_vm1_fixture.vm_ip):
            self.logger.info(
                "Here ping should fail from VM as Policy is removed from the VN")
        else:
            self.logger.error(
                "Ping should fail. But ping is successful even after removal of policy")
            result = result and False

        self.logger.info('Communication via FIP should still works ')
        self.logger.info(
            'Ping from from VM %s to Other VM in different network with FIP %s ' %
            (vn1_vm1_name, fip_fixture1.fip[fip_id2]))
        if not vn1_vm1_fixture.ping_with_certainty(fip_fixture1.fip[fip_id2]):
            result = result and False

        # Rebind the policy here for cleanup purpose.
        fvn1_fixture.bind_policies(
            [policy1_fixture.policy_fq_name], fvn1_fixture.vn_id)
        fvn2_fixture.bind_policies(
            [policy2_fixture.policy_fq_name], fvn2_fixture.vn_id)

        if not result:
            self.logger.error('Test VN info in agent with FIP failed')
            assert result
        return True
    # test_fip_with_policy

    @preposttest_wrapper
    def test_fip_pool_shared_across_project(self):
        ''' Verify FIP Pool is shared accorss diffrent projects.
        '''
        result = True
        fip_pool_name = 'small-pool1'
        fvn_name = 'floating-vn'
        fvm_name = 'floating-vm'
        fvn_subnets = ['121.1.1.0/30']
        vm1_name = 'vm400'
        vn1_name = 'vn400'
        vn1_subnets = ['131.1.1.0/24']
        vm2_name = 'vm500'
        vn2_name = 'vn500'
        vn2_subnets = ['141.1.1.0/24']

        self.demo_proj_inputs1 = self.useFixture(ContrailTestInit(
            self.ini_file, stack_user='admin', stack_password='contrail123', project_fq_name=['default-domain', 'demo']))
        self.demo_proj_connections1 = ContrailConnections(
            self.demo_proj_inputs1)

        # VN Fixture
        fvn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=fvn_name, inputs=self.inputs, subnets=fvn_subnets))
        assert fvn_fixture.verify_on_setup()
        fvn_fixture1 = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=fvn_name, inputs=self.inputs, subnets=fvn_subnets))
        assert fvn_fixture1.verify_on_setup()
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name='demo', connections=self.demo_proj_connections1,
                vn_name=vn2_name, inputs=self.demo_proj_inputs1, subnets=vn2_subnets))
        assert vn2_fixture.verify_on_setup()

        # VM Fixture
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vm1_name))
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name='demo', connections=self.demo_proj_connections1,
                vn_obj=vn2_fixture.obj, vm_name=vm2_name))
        # fvm_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
        #        vn_obj= fvn_fixture.obj, vm_name= fvm_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        #assert fvm_fixture.verify_on_setup()

        # Floating Ip Fixture
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name, vn_id=fvn_fixture.vn_id))
        assert fip_fixture.verify_on_setup()

        # Adding further projects to floating IP.
        self.logger.info('Adding project demo to FIP pool %s' %
                         (fip_pool_name))
        project_obj = fip_fixture.assoc_project(fip_fixture, 'demo')

        # Asscociating FIP to VM under demo project
        self.logger.info(
            'Allocating FIP to VM %s in Demo project from VN %s under admin project' %
            (vm2_name, fvn_name))
        fip_id = fip_fixture.create_and_assoc_fip(
            fvn_fixture.vn_id, vm2_fixture.vm_id, project_obj)
        assert fip_fixture.verify_fip(fip_id, vm2_fixture, fvn_fixture)

        self.logger.info(
            'FIP  pool is exhausted now. Trying to add FIP to VM under admin project. Should FAIL')
        fip_id1 = fip_fixture.create_and_assoc_fip(
            fvn_fixture.vn_id, vm1_fixture.vm_id)
        if fip_id1 != None:
            self.logger.error(
                'FIP should not get created/asscocited as pool is already exhusted')
            result = result and False
        self.logger.info(
            'Releasing FIP to VM %s in Demo project from VN %s under admin project' %
            (vm2_name, fvn_name))
        fip_fixture.disassoc_and_delete_fip(fip_id)

        if result is True:
            self.logger.info(
                'Allocating FIP to VM %s in admin  project from VN %s under admin project' %
                (vm1_name, fvn_name))
            fip_id2 = fip_fixture.create_and_assoc_fip(
                fvn_fixture.vn_id, vm1_fixture.vm_id)
            assert fip_fixture.verify_fip(fip_id2, vm1_fixture, fvn_fixture)

            fip_fixture.disassoc_and_delete_fip(fip_id2)

        # Removing further projects from floating IP pool. For cleanup
        self.logger.info('Removing project demo to FIP pool %s' %
                         (fip_pool_name))
        project_obj = fip_fixture.deassoc_project(fip_fixture, 'demo')

        if not result:
            self.logger.error(
                'Test Failed:Verify FIP Pool is shared accorss diffrent projects')
            assert result
        return True
    # end test_fip_pool_shared_across_project

    @preposttest_wrapper
    def test_communication_across__diff_proj(self):
        ''' Test communication across diffrent projects using Floating IP.
        '''
        result = True
        fip_pool_name = 'some-pool2'
        vm_names = ['Test_Vm_100', 'Test_VM_200']
        vn_names = ['Test_Vn_100', 'Test_Vn_200']
        vn_subnets = [['31.1.1.0/24'], ['41.1.1.0/24']]
        projects = ['project111', 'project222']

        user_list = [('test1', 'test123', 'admin'),
                     ('test2', 'test123', 'admin')]

        # Making sure VM falls on diffrent compute host
        host_list = []
        for host in self.inputs.compute_ips:
            host_list.append(self.inputs.host_data[host]['name'])
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]

        # Projects
        user1_fixture= self.useFixture(
            UserFixture(
                connections=self.connections, username=user_list[0][0], password=user_list[0][1]))
        project_fixture1 = self.useFixture(
            ProjectFixture(
                project_name=projects[0], username=user_list[0][0], password=user_list[0][1],
                    vnc_lib_h=self.vnc_lib, connections=self.connections))
        user1_fixture.add_user_to_tenant(projects[0], user_list[0][0] , user_list[0][2])
        project_inputs1 = self.useFixture(
            ContrailTestInit(
                self.ini_file, stack_user=project_fixture1.username,
                stack_password=project_fixture1.password, project_fq_name=['default-domain', projects[0]]))
        project_connections1 = ContrailConnections(project_inputs1)

        self.logger.info(
            'Default SG to be edited for allow all on project: %s' %
            projects[0])
        project_fixture1.set_sec_group_for_allow_all(projects[0], 'default')

        user2_fixture= self.useFixture(
            UserFixture(
                connections=self.connections, username=user_list[1][0], password=user_list[1][1]))
        project_fixture2 = self.useFixture(
            ProjectFixture(
                project_name=projects[1], username=user_list[0][0], password=user_list[0][1],
                    vnc_lib_h=self.vnc_lib, connections=self.connections))
        user2_fixture.add_user_to_tenant(projects[1], user_list[1][0] , user_list[1][2])
        project_inputs2 = self.useFixture(
            ContrailTestInit(
                self.ini_file, stack_user=user_list[1][0],
                stack_password=user_list[1][1], project_fq_name=['default-domain', projects[1]]))
        project_connections2 = ContrailConnections(project_inputs2)

        self.logger.info(
            'Default SG to be edited for allow all on project: %s' %
            projects[1])
        project_fixture2.set_sec_group_for_allow_all(projects[1], 'default')

        # VN
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=projects[0], connections=project_connections1,
                vn_name=vn_names[0], inputs=project_inputs1, subnets=vn_subnets[0]))
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=projects[1], connections=project_connections2,
                vn_name=vn_names[1], inputs=project_inputs2, subnets=vn_subnets[1]))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()

        # VM
        vm1_fixture = self.useFixture(
            VMFixture(connections=project_connections1,
                      vn_obj=vn1_fixture.obj, vm_name=vm_names[0], project_name=projects[0], node_name=compute_1))
        vm2_fixture = self.useFixture(
            VMFixture(connections=project_connections2,
                      vn_obj=vn2_fixture.obj, vm_name=vm_names[1], project_name=projects[1], node_name=compute_2))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()

        # Floating Ip Fixture
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=project_inputs1.project_name, inputs=project_inputs1,
                connections=project_connections1, pool_name=fip_pool_name, vn_id=vn1_fixture.vn_id))
        assert fip_fixture.verify_on_setup()

        # Adding further projects to floating IP.
        self.logger.info('Adding project demo to FIP pool %s' %
                         (fip_pool_name))
        project_obj = fip_fixture.assoc_project(fip_fixture, projects[0])

        self.logger.info(
            'Allocating FIP to VM %s in project %s from VN %s in project %s ' %
            (vm2_fixture.vm_name, projects[1], vn_names[0], projects[0]))
        fip_id = fip_fixture.create_and_assoc_fip(
            vn1_fixture.vn_id, vm2_fixture.vm_id, project_obj)
        assert fip_fixture.verify_fip(fip_id, vm2_fixture, vn1_fixture)

        if not vm1_fixture.ping_with_certainty(fip_fixture.fip[fip_id]):
            result = result and False
        fip_fixture.disassoc_and_delete_fip(fip_id)

        # Removing further projects from floating IP pool. For cleanup
        self.logger.info('Removing project %s from FIP pool %s' %
                         (projects[0], fip_pool_name))
        project_obj = fip_fixture.deassoc_project(fip_fixture, projects[0])

        if not result:
            self.logger.error(
                'Test Failed:Test communication across diffrent projects using Floating IP')
            assert result
        return result
    # end test_communication_across__diff_proj

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            self._cleanups.remove(cleanup)
    # end remove_from_cleanups

    @preposttest_wrapper
    def test_traffic_to_fip(self):
        '''Testtraffic accross borrower and giving VN.
        '''
        result = True
        fip_pool_name1 = 'some-pool1'
        fvn1_fixture = self.res.fvn1_fixture
        fvn1_vm1_traffic_fixture = self.res.fvn1_vm1_traffic_fixture
        fvn1_subnets = self.res.fvn1_subnets
        fvn1_vm1_traffic_name = self.res.fvn1_vm1_traffic_name
        vn1_fixture = self.res.vn1_fixture
        vn1_vm1_traffic_fixture = self.res.vn1_vm1_traffic_fixture
        vn1_subnets = self.res.vn1_subnets
        vn1_vm1_traffic_name = self.res.vn1_vm1_traffic_name

        assert fvn1_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert fvn1_vm1_traffic_fixture.verify_on_setup()
        assert vn1_vm1_traffic_fixture.verify_on_setup()
        fvn1_vm1_traffic_fixture.wait_till_vm_is_up()
        vn1_vm1_traffic_fixture.wait_till_vm_is_up()

        # Install traffic pkg in VM
        vn1_vm1_traffic_fixture.install_pkg("Traffic")
        fvn1_vm1_traffic_fixture.install_pkg("Traffic")

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name1, vn_id=fvn1_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()

        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn1_fixture.vn_id, vn1_vm1_traffic_fixture.vm_id)
        self.addCleanup(fip_fixture1.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture1.verify_fip(
            fip_id1, vn1_vm1_traffic_fixture, fvn1_fixture)
        if not fvn1_vm1_traffic_fixture.ping_with_certainty(fip_fixture1.fip[fip_id1]):
            result = result and False

        # Send UDP traffic
        fvn1_vm1_traffic_fixture.install_pkg("Traffic")
        vn1_vm1_traffic_fixture.install_pkg("Traffic")
        src_vn = 'default-domain' + ':' + \
            self.inputs.project_name + ':' + fvn1_fixture.vn_name
        dst_vn = 'default-domain' + ':' + \
            self.inputs.project_name + ':' + fvn1_fixture.vn_name
        query = {}
        query['udp'] = '(' + 'sourcevn=' + src_vn + ') AND (destvn=' + dst_vn + ') AND (protocol =17) AND (sourceip = ' + \
            fip_fixture1.fip[fip_id1] + \
            ') AND (destip = ' + \
            fvn1_vm1_traffic_fixture.vm_ip + ')'
        flow_record_data = {}
        flow_series_data = {}
        start_time = self.analytics_obj.getstarttime(
            fvn1_vm1_traffic_fixture.vm_node_ip)
        self.logger.info("start time= %s" % (start_time))
        sleep(5)

        # Verify Traffic ---
        # Start Traffic
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['udp']
        total_streams = {}
        total_streams['udp'] = 1
        dpi = 9100
        proto = 'udp'
        for proto in traffic_proto_l:
            traffic_obj[proto] = {}
            startStatus[proto] = {}
            traffic_obj[proto] = self.useFixture(
                traffic_tests.trafficTestFixture(self.connections))
            startStatus[proto] = traffic_obj[proto].startTraffic(
                num_streams=total_streams[proto], start_port=dpi,
                tx_vm_fixture=fvn1_vm1_traffic_fixture, rx_vm_fixture=vn1_vm1_traffic_fixture, stream_proto=proto, chksum=True, fip=fip_fixture1.fip[fip_id1])
            self.logger.info("Status of start traffic : %s, %s, %s" %
                             (proto, fvn1_vm1_traffic_fixture.vm_ip, startStatus[proto]))
            if startStatus[proto]['status'] != True:
                result = False
        self.logger.info("-" * 80)

        # Poll live traffic
        traffic_stats = {}
        self.logger.info("Poll live traffic and get status..")
        for proto in traffic_proto_l:
            traffic_stats = traffic_obj[proto].getLiveTrafficStats()
            err_msg = "Traffic disruption is seen: details: "
        #self.assertEqual(traffic_stats['status'], True, err_msg)
        assert(traffic_stats['status'] == True), err_msg
        self.logger.info("-" * 80)

        sleep(5)
        for proto in traffic_proto_l:
            flow_record_data[proto] = self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query('FlowRecordTable', dir=0, start_time=start_time, end_time='now', select_fields=[
                                                                                                              'sourcevn', 'sourceip', 'destvn', 'destip', 'setup_time', 'teardown_time', 'agg-packets', 'agg-bytes', 'protocol'], where_clause=query[proto])
            flow_series_data[proto] = self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query(
                'FlowSeriesTable', dir=0, start_time=start_time, end_time='now', select_fields=['sourcevn', 'sourceip', 'destvn', 'destip', 'sum(packets)', 'flow_count', 'sum(bytes)', 'sum(bytes)'], where_clause=query[proto])
            msg = proto + \
                " Flow count info is not matching with opserver flow series record"
            # self.assertEqual(flow_series_data[proto][0]['flow_count'],total_streams[proto],msg)
            assert(flow_series_data[proto][0]
                   ['flow_count'] == total_streams[proto]), msg

        # Stop Traffic
        self.logger.info("Proceed to stop traffic..")
        self.logger.info("-" * 80)
        for proto in traffic_proto_l:
            stopStatus[proto] = {}
            stopStatus[proto] = traffic_obj[proto].stopTraffic()
            if stopStatus[proto] != []:
                result = False
            self.logger.info("Status of stop traffic for proto %s is %s" %
                             (proto, stopStatus[proto]))
            for rcv_count in range(0, total_streams[proto]):
                if traffic_obj[proto].receiver[rcv_count].corrupt > 0:
                    self.logger.error(
                        "In Stream %s of %s, %s packets are corrupted" %
                        (rcv_count, proto, traffic_obj[proto].receiver[rcv_count].corrupt))
                    result = False
                else:
                    self.logger.info(
                        "In Stream %s of %s, No packets are corrupted" %
                        (rcv_count, proto))
        self.logger.info("-" * 80)

        # Get the traffic Stats for each protocol sent
        traffic_stats[proto] = traffic_obj[proto].returnStats()
        # Get the Opserver Flow series data
        flow_series_data[proto] = self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query(
            'FlowSeriesTable', dir=0, start_time=start_time, end_time='now', select_fields=['sourcevn', 'sourceip', 'destvn', 'destip', 'sum(packets)', 'flow_count', 'sum(bytes)', 'sum(bytes)'], where_clause=query[proto])
        self.logger.info("-" * 80)
        #self.assertEqual(result, True, msg)
        assert(result == True), msg
        for proto in traffic_proto_l:
            self.logger.info(
                " verify %s traffic status against to Analytics flow series data" % (proto))
            msg = proto + \
                " Traffic Stats is not matching with opServer flow series data"
            self.logger.info(
                "***Actual Traffic sent by agent %s \n\n stats shown by Analytics flow series%s" %
                (traffic_stats[proto], flow_series_data[proto]))
        print flow_series_data[proto]
        for i in xrange(len(flow_series_data[proto]) - 1):
            if flow_series_data[proto][i]['destip'] == fip_fixture1.fip[fip_id1]:
                # self.assertGreaterEqual(flow_series_data[proto][i]['sum(packets)'],traffic_stats[proto]['total_pkt_sent'],msg)
                assert(flow_series_data[proto][i]['sum(packets)']
                       >= traffic_stats[proto]['total_pkt_sent']), msg

        self.logger.info("-" * 80)
        self.logger.info(
            "***Let flows age out and verify analytics still shows the data in the history***")
        self.logger.info("-" * 80)
        time.sleep(180)
        for proto in traffic_proto_l:
            self.logger.info(
                " verify %s traffic status against Analytics flow series data after flow age out" % (proto))
            flow_series_data[proto] = self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query(
                'FlowSeriesTable', dir=0, start_time='now', end_time='now', select_fields=['sourcevn', 'sourceip', 'destvn', 'destip', 'sum(packets)', 'flow_count', 'sum(bytes)', 'sum(bytes)'], where_clause=query[proto])
            msg = proto + \
                " Flow count info is not matching with opserver flow series record after flow age out in kernel"
            # self.assertEqual(len(flow_series_data[proto]),0,msg)
            assert(len(flow_series_data[proto]) == 0), msg
            flow_series_data[proto] = self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query(
                'FlowSeriesTable', dir=0, start_time=start_time, end_time='now', select_fields=['sourcevn', 'sourceip', 'destvn', 'destip', 'sum(packets)', 'flow_count', 'sum(bytes)', 'sum(bytes)'], where_clause=query[proto])
            msg = proto + \
                " Traffic Stats is not matching with opServer flow series data after flow age out in kernel"
            # Historical data should be present in the Analytics, even if flows
            # age out in kernel
            for i in xrange(len(flow_series_data[proto]) - 1):
                if flow_series_data[proto][i]['destip'] == fip_fixture1.fip[fip_id1]:
                # self.assertGreaterEqual(flow_series_data[proto][i]['sum(packets)'],traffic_stats[proto]['total_pkt_sent'],msg)
                    assert(flow_series_data[proto][i]['sum(packets)']
                           >= traffic_stats[proto]['total_pkt_sent']), msg

        if not result:
            self.logger.error(
                'Test Failed. Floating IP test with traffic failed')
            assert result
        return result
    # end test_fip_with_traffic

    @preposttest_wrapper
    def test_ping_to_fip_using_diag(self):
        '''Test ping to floating IP using diag introspect.
        '''
        result = True
        fip_pool_name1 = 'some-pool1'
        fvn1_fixture = self.res.fvn1_fixture
        vn1_fixture = self.res.vn1_fixture
        fvn1_vm1_fixture = self.res.fvn1_vm1_fixture
        fvn1_subnets = self.res.fvn1_subnets
        fvn1_vm1_name = self.res.fvn1_vm1_name

        vn1_vm1_fixture = self.res.vn1_vm1_fixture
        vn1_subnets = self.res.vn1_subnets
        vn1_vm1_name = self.res.fvn1_vm1_name

        assert fvn1_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert vn1_vm1_fixture.verify_on_setup()
        assert fvn1_vm1_fixture.verify_on_setup()

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name1, vn_id=fvn1_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()

        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn1_fixture.vn_id, vn1_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture1.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture1.verify_fip(fip_id1, vn1_vm1_fixture, fvn1_fixture)

        if not fvn1_vm1_fixture.ping_with_certainty(fip_fixture1.fip[fip_id1]):
            result = result and False
        inspect_h1 = self.agent_inspect[fvn1_vm1_fixture.vm_node_ip]
        self.logger.info("Pinging using diag introspect from IP %s to IP %s" %
                         (fvn1_vm1_fixture.vm_ip, fip_fixture1.fip[fip_id1]))
        result = inspect_h1.get_vna_verify_diag_ping(src_ip=fvn1_vm1_fixture.vm_ip, dst_ip=fip_fixture1.fip[
                                                     fip_id1], vrf=fvn1_vm1_fixture.agent_vrf_objs['vrf_list'][0]['name'], proto='17')
        if not result:
            self.logger.error('Test to ping uding diag between VMs %s and %s' %
                              (fvn1_vm1_fixture.vm_ip, fip_fixture1.fip[fip_id1]))
            assert result
        return result
    # end test_ping_to_fip_using_diag

    @preposttest_wrapper
    def test_floating_ip(self):
        '''Test to validate floating-ip Assignment to a VM. It creates a VM, assigns a FIP to it and pings to a IP in the FIP VN.
        '''
        result = True
        fip_pool_name = 'some-pool1'
        fvn_name = self.res.fvn1_name
        fvn_fixture = self.res.fvn1_fixture
        vn1_fixture = self.res.vn1_fixture
        vn1_vm1_fixture = self.res.vn1_vm1_fixture
        fvn_vm1_fixture = self.res.fvn1_vm1_fixture
        fvn_subnets = self.res.fvn1_subnets
        vm1_name = self.res.vn1_vm1_name
        vn1_name = self.res.vn1_name
        vn1_subnets = self.res.vn1_subnets
        assert fvn_fixture.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert vn1_vm1_fixture.verify_on_setup()
        assert fvn_vm1_fixture.verify_on_setup()

        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name, vn_id=fvn_fixture.vn_id))
        assert fip_fixture.verify_on_setup()
        fip_id = fip_fixture.create_and_assoc_fip(
            fvn_fixture.vn_id, vn1_vm1_fixture.vm_id)
        assert fip_fixture.verify_fip(fip_id, vn1_vm1_fixture, fvn_fixture)
        if not vn1_vm1_fixture.ping_with_certainty(fvn_vm1_fixture.vm_ip):
            result = result and False
        fip_fixture.disassoc_and_delete_fip(fip_id)
        if not result:
            self.logger.error('Test to ping between VMs %s and %s' %
                              (vn1_vm1_name, fvn_vm1_name))
            assert result
        return True
    # end test_floating_ip

    @preposttest_wrapper
    def test_tcp_transfer_from_fip_vm(self):
        ''' Validate data transfer through floating ip.

        '''
        self.logger.info('Reading default encap priority  before continuing')
        default_encap_prior = self.connections.read_vrouter_config_encap()
        self.logger.info("Default encap priority is %s" % default_encap_prior)
        self.logger.info('Setting new Encap before continuing')
        config_id = self.connections.update_vrouter_config_encap(
            'MPLSoGRE', 'MPLSoUDP', 'VXLAN')
        self.logger.info(
            'Created.UUID is %s. MPLSoGRE is the highest priority encap' % (config_id))
        self.addCleanup(self.connections.update_vrouter_config_encap, encap1=default_encap_prior[
                        0], encap2=default_encap_prior[1], encap3=default_encap_prior[2])

        fip_pool_name = 'testpool'

        fvn_name = 'vn-public'
        fvm_name = 'fvm'
        fvn_subnets = ['100.1.1.0/24']

        vn1_name = 'vn-frontend'
        vm1_name = 'vm-fe'
        vn1_subnets = ['192.168.1.0/24']

        vn2_name = 'vn-backend'
        vm2_name = 'vm-be'
        vn2_subnets = ['192.168.2.0/24']

        # policy between frontend and backend
        policy_name = 'frontend-to-backend-policy'
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any',
                'source_network': vn1_name,
                'dest_network': vn2_name,
            },
        ]

        policy_fixture = self.useFixture(
            PolicyFixture(policy_name=policy_name,
                          rules_list=rules, inputs=self.inputs,
                          connections=self.connections))
        # frontend VN
        vn1_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets,
            policy_objs=[policy_fixture.policy_obj]))
        vn1_fixture.verify_on_setup()

        # backend VN
        vn2_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=vn2_name, inputs=self.inputs, subnets=vn2_subnets,
            policy_objs=[policy_fixture.policy_obj]))
        vn2_fixture.verify_on_setup()

        # public VN
        fvn_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=fvn_name, inputs=self.inputs, subnets=fvn_subnets))
        fvn_fixture.verify_on_setup()

        # frontend VM
        vm1_fixture = self.useFixture(VMFixture(image_name='redmine-fe',
                                                project_name=self.inputs.project_name, connections=self.connections,
                                                vn_obj=vn1_fixture.obj, vm_name=vm1_name, flavor='contrail_flavor_medium', fixed_ips=['192.168.1.253']))

        # backend VM
        vm2_fixture = self.useFixture(VMFixture(image_name='redmine-be',
                                                project_name=self.inputs.project_name, connections=self.connections,
                                                vn_obj=vn2_fixture.obj, vm_name=vm2_name, flavor='contrail_flavor_medium', fixed_ips=['192.168.2.253']))

        # public VM
        fvm_fixture = self.useFixture(VMFixture(image_name='ubuntu',
                                                project_name=self.inputs.project_name, connections=self.connections,
                                                vn_obj=fvn_fixture.obj, vm_name=fvm_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert fvm_fixture.verify_on_setup()

        fip_fixture = self.useFixture(FloatingIPFixture(
            project_name=self.inputs.project_name, inputs=self.inputs,
            connections=self.connections, pool_name=fip_pool_name,
            vn_id=fvn_fixture.vn_id))
        assert fip_fixture.verify_on_setup()

        fip_id = fip_fixture.create_and_assoc_fip(fvn_fixture.vn_id,
                                                  vm1_fixture.vm_id)
        assert fip_fixture.verify_fip(fip_id, vm1_fixture, fvn_fixture)
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)

        fip = vm1_fixture.vnc_lib_h.floating_ip_read(
            id=fip_id).get_floating_ip_address()
        assert fvm_fixture.ping_with_certainty(fip)
        result = fvm_fixture.tcp_data_transfer(vm1_fixture.local_ip, fip)
        assert result
        return result
    # end test_tcp_transfer_from_fip_vm

    @preposttest_wrapper
    def test_multiple_floating_ip_for_single_vm(self):
        '''Test to validate floating-ip Assignment to a VM. It creates a VM, assigns a FIP to it and pings to a IP in the FIP VN.
        '''
        result = True
        fip_pool_name = 'some-other-pool1'
        fvn_name = self.res.fvn1_name
        fvm_name = self.res.fvn1_vm1_name
        fvn_subnets = self.res.fvn1_subnets
        fip_pool_name1 = 'some-pool2'
        fvn_name1 = 'fvnn200'
        fvm_name1 = 'vm200'
        fvn_subnets1 = ['150.1.1.0/24']
        vm1_name = self.res.vn1_vm1_name
        vn1_name = self.res.vn1_name
        vn1_subnets = self.res.vn1_subnets

        # VN Fixture
#        fvn_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
# vn_name=fvn_name, inputs= self.inputs, subnets= fvn_subnets))
        fvn_fixture = self.res.fvn1_fixture
        assert fvn_fixture.verify_on_setup()
        fvn_fixture1 = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=fvn_name1, inputs=self.inputs, subnets=fvn_subnets1))
        assert fvn_fixture1.verify_on_setup()
#        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
# vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        vn1_fixture = self.res.vn1_fixture
        assert vn1_fixture.verify_on_setup()

        # VM Fixture
#        vm1_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
#                vn_obj= vn1_fixture.obj, vm_name= vm1_name))
        vm1_fixture = self.res.vn1_vm1_fixture
        assert vm1_fixture.verify_on_setup()
#        fvm_fixture= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,
#                vn_obj= fvn_fixture.obj, vm_name= fvm_name))
        fvm_fixture = self.res.fvn1_vm1_fixture
        assert fvm_fixture.verify_on_setup()
        fvm_fixture1 = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=fvn_fixture1.obj, vm_name=fvm_name1))
        assert fvm_fixture1.verify_on_setup()
        # Floating Ip Fixture
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name, vn_id=fvn_fixture.vn_id))
        assert fip_fixture.verify_on_setup()
        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name1, vn_id=fvn_fixture1.vn_id))
        assert fip_fixture1.verify_on_setup()
        fip_id = fip_fixture.create_and_assoc_fip(
            fvn_fixture.vn_id, vm1_fixture.vm_id)
        assert fip_fixture.verify_fip(fip_id, vm1_fixture, fvn_fixture)
        fip_id1 = fip_fixture.create_and_assoc_fip(
            fvn_fixture1.vn_id, vm1_fixture.vm_id)
        assert fip_fixture1.verify_fip(fip_id1, vm1_fixture, fvn_fixture1)

        # Check the communication from borrower VM to all 2 networks
        if not vm1_fixture.ping_with_certainty(fvm_fixture.vm_ip):
            result = result and False
        if not vm1_fixture.ping_with_certainty(fvm_fixture1.vm_ip):
            result = result and False

        # Check the floating IP provider VNs should commmunicate with each
        # other
        self.logger.info(
            'Ping should fail here. %s and %s should not able to communicate with each oether' %
            (fvm_name1, fvm_name))
        if fvm_fixture1.ping_to_ip(fvm_fixture.vm_ip):
            result = result and False
        # Check after disscocition of floating ip communication should and only
        # should stop from that network
        fip_fixture.disassoc_and_delete_fip(fip_id)
        self.logger.info(
            'Ping should fail here as floating IP pool is already released')
        if vm1_fixture.ping_to_ip(fvm_fixture.vm_ip):
            result = result and False
        if not vm1_fixture.ping_with_certainty(fvm_fixture1.vm_ip):
            result = result and False
        fip_fixture1.disassoc_and_delete_fip(fip_id1)
        if not result:
            self.logger.error(
                'Test to check multiple floating ip for single VM has failed')
            assert result
        return True
    # end test_floating_ip

    @preposttest_wrapper
    def test_longest_prefix_match_with_fip_and_staticroute(self):
        '''1. Create vn1 and vn2 launch vm1, vm2 in vn1 and vm3 in vn2
           2. Create static ip with vn2 subnet pointing to vm2
           3. Allocate fip vn2 to vm1
           4. Expect ping from vm1 to vm3 to pass, following longest prefix match
        '''
        result = True
        vn1_name = 'vn111'
        vn1_subnets = ['1.1.1.0/24']
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vn1_obj = vn1_fixture.obj

        vn2_name = 'vn222'
        vn2_subnets = ['2.2.2.0/24']
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn2_name, inputs=self.inputs, subnets=vn2_subnets))
        assert vn2_fixture.verify_on_setup()
        vn2_obj = vn2_fixture.obj

        vm1_name = 'vm111'
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn1_obj, vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()

        vm2_name = 'vm222'
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn1_obj, vm_name=vm2_name, project_name=self.inputs.project_name))
        assert vm2_fixture.verify_on_setup()

        vm3_name = 'vm333'
        vm3_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn2_obj, vm_name=vm3_name, project_name=self.inputs.project_name))
        assert vm3_fixture.verify_on_setup()

        vm2_vmi_id = vm2_fixture.cs_vmi_obj[vn1_fixture.vn_fq_name][
            'virtual-machine-interface']['uuid']

        add_static_route_cmd = 'python provision_static_route.py --prefix 2.2.2.0/24 --virtual_machine_interface_id ' + vm2_vmi_id + \
            ' --tenant_name "admin" --api_server_ip 127.0.0.1 --api_server_port 8082 --oper add --route_table_name my_route_table'
        self.logger.info("Create static IP for 2.2.2.0/24 pointing to vm2 ")
        with settings(
            host_string='%s@%s' % (
                self.inputs.username, self.inputs.cfgm_ips[0]),
                password=self.inputs.password, warn_only=True, abort_on_prompts=False, debug=True):

            status = run('cd /opt/contrail/utils;' + add_static_route_cmd)
            self.logger.debug("%s" % status)
            m = re.search(r'Creating Route table', status)
            assert m, 'Failed in Creating Route table'

        compute_ip = vm2_fixture.vm_node_ip
        compute_user = self.inputs.host_data[compute_ip]['username']
        compute_password = self.inputs.host_data[compute_ip]['password']
        session = ssh(compute_ip, compute_user, compute_password)
        vm2_tapintf = vm2_fixture.tap_intf[vn1_fixture.vn_fq_name]['name']
        cmd = 'tcpdump -ni %s icmp -vvv -c 2 > /tmp/%s_out.log' % (vm2_tapintf,
                                                                   vm2_tapintf)
        execute_cmd(session, cmd, self.logger)
        assert not(vm1_fixture.ping_to_ip(vm3_fixture.vm_ip, count='20'))
        self.logger.info('***** Will check the result of tcpdump *****')
        output_cmd = 'cat /tmp/%s_out.log' % vm2_tapintf
        output, err = execute_cmd_out(session, output_cmd, self.logger)
        print output
        if vm1_fixture.vm_ip in output:
            self.logger.info(
                'Traffic is going to vm222 static ip is configured correctly')
        else:
            result = False
            self.logger.error(
                'Static ip with subnet 2.2.2.0/24 is not configured correctly')

        fip_pool_name = 'test-floating-pool1'
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name, vn_id=vn2_fixture.vn_id))

        fip_id = fip_fixture.create_and_assoc_fip(
            vn2_fixture.vn_id, vm1_fixture.vm_id)
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)
        assert fip_fixture.verify_fip(fip_id, vm1_fixture, vn2_fixture)

        execute_cmd(session, cmd, self.logger)
        if not (vm1_fixture.ping_with_certainty(vm3_fixture.vm_ip)):
            result = result and False
            self.logger.error(
                'Longest prefix matched route is not taken floating ip ping is failing')
        self.logger.info('***** Will check the result of tcpdump *****')
        output_cmd = 'cat /tmp/%s_out.log' % vm2_tapintf
        output, err = execute_cmd_out(session, output_cmd, self.logger)
        print output
        if vm1_fixture.vm_ip in output:
            self.logger.error(
                'Ping is still going to vm222 due to static route added not expected')
            result = False
        else:
            self.logger.info(
                'Route with longest prefix match is followed as expected')

        del_static_route_cmd = 'python provision_static_route.py --prefix 2.2.2.0/24 --virtual_machine_interface_id ' + vm2_vmi_id + \
            ' --tenant_name "admin" --api_server_ip 127.0.0.1 --api_server_port 8082 --oper del --route_table_name my_route_table'
        self.logger.info("Delete static IP for 2.2.2.0/24 pointing to vm2 ")
        with settings(
            host_string='%s@%s' % (
                self.inputs.username, self.inputs.cfgm_ips[0]),
                password=self.inputs.password, warn_only=True, abort_on_prompts=False, debug=True):

            status = run('cd /opt/contrail/utils;' + del_static_route_cmd)
            self.logger.debug("%s" % status)
        assert result
        return True

    # end test_longest_prefix_match_with_fip_and_staticroute

    @preposttest_wrapper
    def test_longest_prefix_match_with_fip_and_policy(self):
        '''1. Create vn1 and vn2 launch vm1 in vn1  vm2 in vn2
           2. Create policy between vn1 and vn2 to allow all protocols except ICMP, expect ping to fail & scp to pass from vm1 to vm2 to verify policy
           3. Allocate fip from vn2 to vm1
           4. Expect ping from vm1 to vm2 to pass, following longest prefix match
        '''
        result = True
        vn1_name = 'vn111'
        vn1_subnets = ['1.1.1.0/24']
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vn1_obj = vn1_fixture.obj

        vn2_name = 'vn222'
        vn2_subnets = ['2.2.2.0/24']
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn2_name, inputs=self.inputs, subnets=vn2_subnets))
        assert vn2_fixture.verify_on_setup()
        vn2_obj = vn2_fixture.obj

        vm1_name = 'vm111'
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn1_obj, vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()

        vm2_name = 'vm222'
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn2_obj, vm_name=vm2_name, project_name=self.inputs.project_name))
        assert vm2_fixture.verify_on_setup()

        self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm2_fixture.vm_obj)

        rules = [
            {
                'direction': '<>', 'simple_action': 'deny',
                'protocol': 'icmp',
                'src_ports': 'any',
                'dst_ports': 'any',
                'source_network': vn1_name,
                'dest_network': vn2_name,
            },

            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any',
                'src_ports': 'any',
                'source_network': vn1_name,
                'dest_network': vn2_name,
                'dst_ports': 'any',
            },
        ]

        policy_name = 'policy_no_icmp'

        policy_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name, rules_list=rules, inputs=self.inputs,
                connections=self.connections))

        policy_fq_name = [policy_fixture.policy_fq_name]
        vn1_fixture.bind_policies(policy_fq_name, vn1_fixture.vn_id)
        self.addCleanup(vn1_fixture.unbind_policies,
                        vn1_fixture.vn_id, [policy_fixture.policy_fq_name])
        vn2_fixture.bind_policies(policy_fq_name, vn2_fixture.vn_id)
        self.addCleanup(vn2_fixture.unbind_policies,
                        vn2_fixture.vn_id, [policy_fixture.policy_fq_name])
        vn1_fixture.verify_on_setup()
        vn2_fixture.verify_on_setup()

        for i in range(3):
            self.logger.info("Expecting the ping to fail")
            assert not (vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)
                        ), 'Failed in applying policy ping should fail as icmp is denied'
        assert self.scp_files_to_vm(
            vm1_fixture, vm2_fixture), 'Failed to scp file to vm '

        fip_pool_name = 'test-floating-pool'
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name, vn_id=vn2_fixture.vn_id))

        fip_id = fip_fixture.create_and_assoc_fip(
            vn2_fixture.vn_id, vm1_fixture.vm_id)
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)
        assert fip_fixture.verify_fip(fip_id, vm1_fixture, vn2_fixture)

        if not (vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip)):
            self.logger.error(
                'Route with longest prefix match is not followed fip ping should have passed')
            result = False
            assert result, 'Ping by floating ip failed'
        assert self.scp_files_to_vm(
            vm1_fixture, vm2_fixture), 'Failed to scp file to vm '

        return True

    # end test_longest_prefix_match_with_fip_and_policy

    def scp_files_to_vm(self, src_vm, dst_vm):
        result = True
        src_vm.put_pub_key_to_vm()
        dst_vm.put_pub_key_to_vm()
        dest_vm_ip = dst_vm.vm_ip
        file_sizes = ['1000', '1101', '1202']
        for size in file_sizes:
            self.logger.info("-" * 80)
            self.logger.info("FILE SIZE = %sB" % size)
            self.logger.info("-" * 80)

            self.logger.info('Transferring the file from %s to %s using scp' %
                             (src_vm.vm_name, dst_vm.vm_name))
            filename = 'testfile'

            # Create file
            cmd = 'dd bs=%s count=1 if=/dev/zero of=%s' % (size, filename)
            src_vm.run_cmd_on_vm(cmds=[cmd])

            # Copy key
            dst_vm.run_cmd_on_vm(
                cmds=['cp -f ~root/.ssh/authorized_keys ~/.ssh/'], as_sudo=True)
            # Scp file from EVPN_VN_L2_VM1 to EVPN_VN_L2_VM2 using
            # EVPN_VN_L2_VM2 vm's eth1 interface ip
            src_vm.scp_file_to_vm(filename, vm_ip=dst_vm.vm_ip)
            src_vm.run_cmd_on_vm(cmds=['sync'])
            # Verify if file size is same in destination vm
            out_dict = dst_vm.run_cmd_on_vm(
                cmds=['ls -l %s' % (filename)])
            if size in out_dict.values()[0]:
                self.logger.info('File of size %s is trasferred successfully to \
                    %s by scp ' % (size, dest_vm_ip))
            else:
                self.logger.warn('File of size %s is not trasferred fine to %s \
                    by scp !! Pls check logs' % (size, dest_vm_ip))
                result = result and False
        return result

    @preposttest_wrapper
    def test_longest_prefix_match_with_fip_and_native_staticroute(self):
        ''' Test Longest prefix match when native VRF  has longer prefix than FIP VRF
        '''
        result= True
        vn1_name='vn111'
        vn1_subnets=['1.1.1.0/24']
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vn1_obj= vn1_fixture.obj

        vn2_name='vn222'
        vn2_subnets=['2.2.2.0/24']
        vn2_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn2_name, inputs= self.inputs, subnets= vn2_subnets))
        assert vn2_fixture.verify_on_setup()
        vn2_obj= vn2_fixture.obj

        vn3_name='vn333'
        vn3_subnets=['10.1.1.0/24']
        vn3_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn3_name, inputs= self.inputs, subnets= vn3_subnets))
        assert vn3_fixture.verify_on_setup()
        vn3_obj= vn3_fixture.obj

        vm1_name='vm111'
        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn1_obj, vm_name= vm1_name, project_name= self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()

        vm2_name='vm222'
        vm2_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_objs=[vn1_obj, vn2_obj], vm_name= vm2_name, project_name= self.inputs.project_name))
        assert vm2_fixture.verify_on_setup()

        vm3_name='vm333'
        vm3_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn3_obj, vm_name= vm3_name, project_name= self.inputs.project_name))
        assert vm3_fixture.verify_on_setup()

        self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up( vm3_fixture.vm_obj)

        cmd_to_pass1=['ifconfig eth1 up']
        vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True)
        sleep(10)
        cmd_to_pass2=['dhclient eth1']
        output=vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True)
        sleep(30)
        self.logger.info("%s"%output)
        vm2_eth1_ip = vm2_fixture.vm_ips[1]

        vm3_vmi_id = vm3_fixture.cs_vmi_obj[vn3_fixture.vn_fq_name]['virtual-machine-interface']['uuid']
        vm2_vmi_id = vm2_fixture.cs_vmi_obj[vn1_fixture.vn_fq_name]['virtual-machine-interface']['uuid']

        add_static_route_cmd = 'python provision_static_route.py --prefix 2.2.2.0/24 --virtual_machine_interface_id ' +vm3_vmi_id+' --tenant_name "admin" --api_server_ip 127.0.0.1 --api_server_port 8082 --oper add --route_table_name my_route_table'
        self.logger.info("Create static route 2.2.2.0/24 pointing to vm3 \n")
        with settings(host_string= '%s@%s' %(self.inputs.username, self.inputs.cfgm_ips[0]),
                        password= self.inputs.password,warn_only=True,abort_on_prompts=False,debug=True):

                status= run('cd /opt/contrail/utils;'+add_static_route_cmd)
                self.logger.debug("%s"%status)
                m = re.search(r'Creating Route table',status)
                assert m , 'Failed in Creating Route table'

        fip_pool_name= 'test-floating-pool'
        fip_fixture= self.useFixture(FloatingIPFixture( project_name= self.inputs.project_name, inputs = self.inputs,
                    connections= self.connections, pool_name = fip_pool_name, vn_id= vn3_fixture.vn_id ))
        fip_id= fip_fixture.create_and_assoc_fip(vn3_fixture.vn_id, vm1_fixture.vm_id)
        self.addCleanup( fip_fixture.disassoc_and_delete_fip, fip_id)
        assert fip_fixture.verify_fip( fip_id, vm1_fixture, vn3_fixture)

        vm1_fip = vm1_fixture.vnc_lib_h.floating_ip_read(
            id=fip_id).get_floating_ip_address()

        compute_ip = vm3_fixture.vm_node_ip
        compute_user = self.inputs.host_data[compute_ip]['username']
        compute_password = self.inputs.host_data[compute_ip]['password']
        session = ssh(compute_ip,compute_user,compute_password)
        vm3_tapintf = vm3_fixture.tap_intf[vn3_fixture.vn_fq_name]['name']
        cmd = 'tcpdump -ni %s icmp -vvv -c 2 > /tmp/%s_out.log'%(vm3_tapintf, vm3_tapintf)
        execute_cmd(session, cmd, self.logger)
        assert not(vm1_fixture.ping_to_ip(vm2_eth1_ip, count='20'))
        self.logger.info('***** Will check the result of tcpdump *****\n')
        output_cmd= 'cat /tmp/%s_out.log'%vm3_tapintf
        output, err = execute_cmd_out(session, output_cmd, self.logger)
        print output

        if vm1_fip  in output:
           self.logger.info('Traffic is going to vm333 static ip is configured correctly \n')
        else:
           result= result and False
           self.logger.error('Static ip with subnet 2.2.2.0/24 is not configured correctly \n')

        static_route_vm2= vm2_fixture.vm_ips[1] + '/' + '32'

        add_static_route_cmd = 'python provision_static_route.py --prefix ' + static_route_vm2 + ' --virtual_machine_interface_id ' +vm2_vmi_id+' --tenant_name "admin" --api_server_ip 127.0.0.1 --api_server_port 8082 --oper add --route_table_name my_route_table'
        self.logger.info("Create static route %s pointing to vm111 eth0 interface \n"%static_route_vm2)
        with settings(host_string= '%s@%s' %(self.inputs.username, self.inputs.cfgm_ips[0]),
                        password= self.inputs.password,warn_only=True,abort_on_prompts=False,debug=True):

                status= run('cd /opt/contrail/utils;'+add_static_route_cmd)
                self.logger.debug("%s"%status)

        execute_cmd(session, cmd, self.logger)
        if not (vm1_fixture.ping_with_certainty( vm2_eth1_ip )):
           result = result and False
           self.logger.error('Longest prefix matched route is not taken ping using native static route is failing \n')
        self.logger.info('***** Will check the result of tcpdump *****')
        output_cmd= 'cat /tmp/%s_out.log'%vm3_tapintf
        output, err = execute_cmd_out(session, output_cmd, self.logger)
        print output

        if vm1_fip  in output:
           self.logger.error('Ping is still going to vm333 problem with static route %s Longest prefix route not followed \n'%static_route_vm2)
           result= result and False
        else:
           self.logger.info('Ping not going to vm333  as expected \n')

        del_static_route_cmd1 = 'python provision_static_route.py --prefix 2.2.2.0/24 --virtual_machine_interface_id ' +vm3_vmi_id+' --tenant_name "admin" --api_server_ip 127.0.0.1 --api_server_port 8082 --oper del --route_table_name my_route_table'
        del_static_route_cmd2 = 'python provision_static_route.py --prefix ' + static_route_vm2 + ' --virtual_machine_interface_id ' +vm2_vmi_id+' --tenant_name "admin" --api_server_ip 127.0.0.1 --api_server_port 8082 --oper del --route_table_name my_route_table'

        self.logger.info("Delete static IP for 2.2.2.0/24 pointing to vm333 \n")
        self.logger.info("Delete static IP for %s pointing to vm111 \n"%static_route_vm2)

        with settings(host_string= '%s@%s' %(self.inputs.username, self.inputs.cfgm_ips[0]),
                        password= self.inputs.password,warn_only=True,abort_on_prompts=False,debug=True):

                status= run('cd /opt/contrail/utils;'+del_static_route_cmd1)
                self.logger.debug("%s"%status)
                status= run('cd /opt/contrail/utils;'+del_static_route_cmd2)
                self.logger.debug("%s"%status)

        assert result , 'Failed to take route with longest prefix'
        return True
    #end test_longest_prefix_match_with_fip_and_native_staticroute

    @preposttest_wrapper
    def test_longest_prefix_match_with_2fip_different_vn_name(self):
        ''' Allocate 2 FIP from different VN. Both the Floating VN should push same route. VM should take the route for the VN based on destination vn name (smaller dict name)
            FIP is allocated from vnaaa and vnbbb and both push same route so traffic is expected on interface associated with vnaaa
        '''
        result= True
        vn1_name='vn111'
        vn1_subnets=['1.1.1.0/24']
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vn1_obj= vn1_fixture.obj

        vn2_name='vnaaa'
        vn2_subnets=['2.2.2.0/24']
        vn2_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn2_name, inputs= self.inputs, subnets= vn2_subnets))
        assert vn2_fixture.verify_on_setup()
        vn2_obj= vn2_fixture.obj

        vn3_name='vnbbb'
        vn3_subnets=['3.3.3.0/24']
        vn3_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn3_name, inputs= self.inputs, subnets= vn3_subnets))
        assert vn3_fixture.verify_on_setup()
        vn3_obj= vn3_fixture.obj

        vn4_name='vn444'
        vn4_subnets=['4.4.4.0/24']
        vn4_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn4_name, inputs= self.inputs, subnets= vn4_subnets))
        assert vn4_fixture.verify_on_setup()
        vn4_obj= vn4_fixture.obj

        vm1_name='vm111'
        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_objs=[vn1_obj, vn2_obj, vn3_obj], vm_name= vm1_name, project_name= self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()

        vm2_name='vm222'
        vm2_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn4_obj, vm_name= vm2_name, project_name= self.inputs.project_name))
        assert vm2_fixture.verify_on_setup()

        self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj)

        cmd_to_pass1=['ifconfig eth1 up']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True)
        sleep(10)
        cmd_to_pass2=['ifconfig eth2 up']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True)
        sleep(10)

        cmd_list= 'dhclient eth1;dhclient eth2'
        cmd_to_pass=[cmd_list]
        output=vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass, as_sudo=True)
        sleep(30)

        vm1_eth1_vmi_id = vm1_fixture.cs_vmi_obj[vn2_fixture.vn_fq_name]['virtual-machine-interface']['uuid']
        vm1_eth2_vmi_id = vm1_fixture.cs_vmi_obj[vn3_fixture.vn_fq_name]['virtual-machine-interface']['uuid']

        static_route_vm1_eth0 = vm1_fixture.vm_ip + '/' + '32'
        add_static_route_cmd1 = 'python provision_static_route.py --prefix ' + static_route_vm1_eth0 + ' --virtual_machine_interface_id ' +vm1_eth1_vmi_id+' --tenant_name "admin" --api_server_ip 127.0.0.1 --api_server_port 8082 --oper add --route_table_name my_route_table1'
        add_static_route_cmd2 = 'python provision_static_route.py --prefix ' + static_route_vm1_eth0 + ' --virtual_machine_interface_id ' +vm1_eth2_vmi_id+' --tenant_name "admin" --api_server_ip 127.0.0.1 --api_server_port 8082 --oper add --route_table_name my_route_table2'
        self.logger.info("Create static route %s pointing to eth0 of vm1 \n"%static_route_vm1_eth0)
        with settings(host_string= '%s@%s' %(self.inputs.username, self.inputs.cfgm_ips[0]),
                        password= self.inputs.password,warn_only=True,abort_on_prompts=False,debug=True):

                status1= run('cd /opt/contrail/utils;'+add_static_route_cmd1)
                self.logger.debug("%s"%status1)
                m = re.search(r'Creating Route table',status1)
                assert m , 'Failed in Creating Route table'

                status2= run('cd /opt/contrail/utils;'+add_static_route_cmd2)
                self.logger.debug("%s"%status2)
                m = re.search(r'Creating Route table',status2)
                assert m , 'Failed in Creating Route table'

        fip_pool_name1= 'test-floating-pool1'
        fip_fixture1= self.useFixture(FloatingIPFixture( project_name= self.inputs.project_name, inputs = self.inputs,
                    connections= self.connections, pool_name = fip_pool_name1, vn_id= vn2_fixture.vn_id ))
        fip_id1= fip_fixture1.create_and_assoc_fip(vn2_fixture.vn_id, vm2_fixture.vm_id)
        self.addCleanup( fip_fixture1.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture1.verify_fip( fip_id1, vm2_fixture, vn2_fixture)

        vm2_fip1 = vm2_fixture.vnc_lib_h.floating_ip_read(
            id=fip_id1).get_floating_ip_address()

        fip_pool_name2= 'test-floating-pool2'
        fip_fixture2= self.useFixture(FloatingIPFixture( project_name= self.inputs.project_name, inputs = self.inputs,
                    connections= self.connections, pool_name = fip_pool_name2, vn_id= vn3_fixture.vn_id ))
        fip_id2= fip_fixture2.create_and_assoc_fip(vn3_fixture.vn_id, vm2_fixture.vm_id)
        self.addCleanup( fip_fixture2.disassoc_and_delete_fip, fip_id2)
        assert fip_fixture2.verify_fip( fip_id2, vm2_fixture, vn3_fixture)

        vm2_fip2 = vm2_fixture.vnc_lib_h.floating_ip_read(
            id=fip_id2).get_floating_ip_address()

        compute_ip = vm1_fixture.vm_node_ip
        compute_user = self.inputs.host_data[compute_ip]['username']
        compute_password = self.inputs.host_data[compute_ip]['password']
        session = ssh(compute_ip,compute_user,compute_password)
        vm1_tapintf_eth1 = vm1_fixture.tap_intf[vn2_fixture.vn_fq_name]['name']
        vm1_tapintf_eth2 = vm1_fixture.tap_intf[vn3_fixture.vn_fq_name]['name']
        cmd1 = 'tcpdump -ni %s icmp -vvv -c 2 > /tmp/%s_out.log'%(vm1_tapintf_eth1, vm1_tapintf_eth1)
        cmd2 = 'tcpdump -ni %s icmp -vvv -c 2 > /tmp/%s_out.log'%(vm1_tapintf_eth2, vm1_tapintf_eth2)
        execute_cmd(session, cmd1, self.logger)
        execute_cmd(session, cmd2, self.logger)
        if not (vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip, count='20' )):
           result = result and False
           self.logger.error("Ping from vm222 to vm111 failed not expected")

        self.logger.info('***** Will check the result of tcpdump *****\n')
        output_cmd1= 'cat /tmp/%s_out.log'%vm1_tapintf_eth1
        output_cmd2= 'cat /tmp/%s_out.log'%vm1_tapintf_eth2
        output1, err = execute_cmd_out(session, output_cmd1, self.logger)
        output2, err = execute_cmd_out(session, output_cmd2, self.logger)
        print output1
        print output2

        if vm2_fip1  in output1:
           self.logger.info('Traffic is going through vm111 eth1 interface as the vn name (vnaaa) is smaller here, longest prefix match is followed \n')
        else:
           result= result and False
           self.logger.error('Traffic is not going through vm111 eth1 interface though vn name is smaller here, not expected \n \n')

        if vm2_fip2  in output2:
           self.logger.error('Traffic is going through vm111 eth2 interface not  expected \n')
           result= result and False
        else:
           self.logger.info('Traffic is not going through vm111 eth2 interface since associated vn name (vnbbb) is greater than vnaaa, longest prefix match followed \n')

        del_static_route_cmd1 = 'python provision_static_route.py --prefix ' + static_route_vm1_eth0  + ' --virtual_machine_interface_id ' +vm1_eth1_vmi_id+' --tenant_name "admin" --api_server_ip 127.0.0.1 --api_server_port 8082 --oper del --route_table_name my_route_table1'
        del_static_route_cmd2 = 'python provision_static_route.py --prefix ' + static_route_vm1_eth0  + ' --virtual_machine_interface_id ' +vm1_eth2_vmi_id+' --tenant_name "admin" --api_server_ip 127.0.0.1 --api_server_port 8082 --oper del --route_table_name my_route_table2'
        self.logger.info("Delete static route %s pointing to eth0 of vm1 \n"%static_route_vm1_eth0)

        with settings(host_string= '%s@%s' %(self.inputs.username, self.inputs.cfgm_ips[0]),
                        password= self.inputs.password,warn_only=True,abort_on_prompts=False,debug=True):

                status1= run('cd /opt/contrail/utils;'+del_static_route_cmd1)
                self.logger.debug("%s"%status1)
                status2= run('cd /opt/contrail/utils;'+del_static_route_cmd2)
                self.logger.debug("%s"%status2)

        assert result , 'Longest prefix match rule not followed'
        return True
    # end test_longest_prefix_match_with_2fip_different_vn_name

    @preposttest_wrapper
    def test_longest_prefix_match_with_two_fips_from_same_vn(self):
        ''' Allocate 2 FIP from same Vn. VM should choose the path with lower IP address.
        '''
        result= True
        vn1_name='vn111'
        vn1_subnets=['1.1.1.0/24']
        vn1_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vn1_obj= vn1_fixture.obj

        vn2_name='vn222'
        vn2_subnets=['2.2.2.0/24']
        vn2_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn2_name, inputs= self.inputs, subnets= vn2_subnets))
        assert vn2_fixture.verify_on_setup()
        vn2_obj= vn2_fixture.obj

        vm1_name='vm111'
        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn1_obj, vm_name= vm1_name, project_name= self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()

        vm2_name='vm222'
        vm2_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn2_obj, vm_name= vm2_name, project_name= self.inputs.project_name))
        assert vm2_fixture.verify_on_setup()

        fip_pool_name= 'test-floating-pool'
        fip_fixture= self.useFixture(FloatingIPFixture( project_name= self.inputs.project_name, inputs = self.inputs,
                    connections= self.connections, pool_name = fip_pool_name, vn_id= vn1_fixture.vn_id ))
        fip_id1= fip_fixture.create_and_assoc_fip(vn1_fixture.vn_id, vm2_fixture.vm_id)
        fip_id2= fip_fixture.create_and_assoc_fip(vn1_fixture.vn_id, vm2_fixture.vm_id)

        self.addCleanup( fip_fixture.disassoc_and_delete_fip, fip_id2)
        assert fip_fixture.verify_fip( fip_id1, vm2_fixture, vn1_fixture)
        assert fip_fixture.verify_fip( fip_id2, vm2_fixture, vn1_fixture)

        vm2_fip1 = vm2_fixture.vnc_lib_h.floating_ip_read(
            id=fip_id1).get_floating_ip_address()

        vm2_fip2 = vm2_fixture.vnc_lib_h.floating_ip_read(
            id=fip_id2).get_floating_ip_address()

        compute_ip = vm1_fixture.vm_node_ip
        compute_user = self.inputs.host_data[compute_ip]['username']
        compute_password = self.inputs.host_data[compute_ip]['password']
        session = ssh(compute_ip,compute_user,compute_password)
        vm1_tapintf = vm1_fixture.tap_intf[vn1_fixture.vn_fq_name]['name']
        cmd = 'tcpdump -ni %s icmp -vvv -c 2 > /tmp/%s_out.log'%(vm1_tapintf, vm1_tapintf)
        execute_cmd(session, cmd, self.logger)
        if not (vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip, count='20' )):
           result = result and False
           self.logger.error("Ping from vm222 to vm111 failed not expected")

        self.logger.info('***** Will check the result of tcpdump *****\n')
        output_cmd= 'cat /tmp/%s_out.log'%vm1_tapintf
        output, err = execute_cmd_out(session, output_cmd, self.logger)
        print output

        if vm2_fip1 > vm2_fip2:
           smaller_fip = vm2_fip2
        else:
           smaller_fip = vm2_fip1

        if smaller_fip  in output:
           self.logger.info('Traffic is send using smaller fip when 2 fips are allocated from same vn as expected \n')
        else:
           result= result and False
           self.logger.error('Traffic is not send using smaller fip when 2 fips are allocated from same vn, not expected \n')

        fip_id3= fip_fixture.create_and_assoc_fip(vn1_fixture.vn_id, vm2_fixture.vm_id)
        self.addCleanup( fip_fixture.disassoc_and_delete_fip, fip_id3)
        assert fip_fixture.verify_fip( fip_id3, vm2_fixture, vn1_fixture)
        vm2_fip3 = vm2_fixture.vnc_lib_h.floating_ip_read(
            id=fip_id3).get_floating_ip_address()
        fip_fixture.disassoc_and_delete_fip(fip_id1)

        execute_cmd(session, cmd, self.logger)
        if not (vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip, count='20' )):
           result = result and False
           self.logger.error("Ping from vm222 to vm111 failed not expected")
        self.logger.info('***** Will check the result of tcpdump *****')
        output_cmd= 'cat /tmp/%s_out.log'%vm1_tapintf
        output, err = execute_cmd_out(session, output_cmd, self.logger)
        print output

        if vm2_fip2 > vm2_fip3:
           smaller_fip = vm2_fip3
        else:
           smaller_fip = vm2_fip2

        if smaller_fip  in output:
           self.logger.info('Traffic is send using smaller fip when 2 fips are allocated from same vn as expected \n')
        else:
           result= result and False
           self.logger.error('Traffic is not send using smaller fip when 2 fips are allocated from same vn, not expected \n')

        assert result, 'Longest prefix match rule is not followed'

        return True
    #end test_longest_prefix_match_with_two_fips_from_same_vn

    @preposttest_wrapper
    def test_fip_from_shared_network_in_demo_project(self):
        ''' Allocate fip to vm launched in demo project from shared network using neutron api
            Maintainer: hkumar@juniper.net
        '''
        return self.verify_fip_from_shared_network_in_demo_project()
