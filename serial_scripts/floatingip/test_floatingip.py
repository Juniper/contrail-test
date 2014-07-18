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
from tcutils.wrappers import preposttest_wrapper
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from tcutils.commands import *
from testresources import ResourcedTestCase
import traffic_tests
from fabric.context_managers import settings
from fabric.api import run
import base
import test


class FloatingipTestSanity_restart(base.FloatingIpBaseTest):

    @classmethod
    def setUpClass(cls):
        super(FloatingipTestSanity_restart, cls).setUpClass()

    @test.attr(type='serial')	
    @preposttest_wrapper
    def test_service_restart_with_fip(self):
        '''Test restart of agent and control service with floating IP
        '''
        result = True
        fip_pool_name = get_random_name('some-pool1')
        (self.vn1_name, self.vn1_subnets) = (
            get_random_name("vn1"), ["11.1.1.0/24"])
        (self.vn2_name, self.vn2_subnets) = (
            get_random_name("vn2"), ["22.1.1.0/24"])
        (self.fvn_public_name, self.fvn_public_subnets) = (
            get_random_name("fip_vn_public"), ['10.204.219.16/28'])
        (self.fvn1_name, self.fvn1_subnets) = (
            get_random_name("fip_vn1"), ['100.1.1.0/24'])
        (self.fvn2_name, self.fvn2_subnets) = (
            get_random_name("fip_vn2"), ['200.1.1.0/24'])
        (self.fvn3_name, self.fvn3_subnets) = (
            get_random_name("fip_vn3"), ['170.1.1.0/29'])
        (self.vn1_vm1_name, self.vn1_vm2_name) = (
            get_random_name('vn1_vm1'), get_random_name('vn1_vm2'))
        (self.vn2_vm1_name, self.vn2_vm2_name) = (
            get_random_name('vn2_vm1'), get_random_name('vn2_vm2'))
        (self.fvn_public_vm1_name) = (get_random_name('fvn_public_vm1'))
        (self.fvn1_vm1_name) = (get_random_name('fvn1_vm1'))
        (self.fvn2_vm1_name) = (get_random_name('fvn2_vm1'))
        (self.fvn3_vm1_name) = (get_random_name('fvn3_vm1'))
        (self.vn1_vm1_traffic_name) = get_random_name('VN1_VM1_traffic')
        (self.fvn1_vm1_traffic_name) = get_random_name('FVN1_VM1_traffic')
        # Get all compute host
        host_list = []
        for host in self.inputs.compute_ips:
            host_list.append(self.inputs.host_data[host]['name'])
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
        fip_pool_name1 = get_random_name('some-pool1')
        fip_pool_name2 = get_random_name('some-pool2')

        self.fvn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.fvn1_name,
                subnets=self.fvn1_subnets))
        self.fvn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.fvn2_name,
                subnets=self.fvn2_subnets))
        self.fvn1_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=self.fvn1_fixture.obj,
                vm_name=self.fvn1_vm1_name,
                node_name=compute_2))

        self.fvn2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=self.fvn2_fixture.obj,
                vm_name=self.fvn2_vm1_name,
                node_name=compute_1))

        #fvn_name= self.res.fip_vn_name
        fvn1_fixture = self.fvn1_fixture
        fvn2_fixture = self.fvn2_fixture
        fvn1_vm1_fixture = self.fvn1_vm1_fixture
        fvn1_subnets = self.fvn1_subnets
        fvn1_vm1_name = self.fvn1_vm1_name
        fvn2_vm1_fixture = self.fvn2_vm1_fixture
        fvn2_subnets = self.fvn2_subnets
        fvn2_vm1_name = self.fvn2_vm1_name
        assert fvn1_fixture.verify_on_setup()
        assert fvn2_fixture.verify_on_setup()
        assert fvn1_vm1_fixture.verify_on_setup()
        assert fvn2_vm1_fixture.verify_on_setup()

        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name1,
                vn_id=fvn1_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()
        fip_id1 = fip_fixture1.create_and_assoc_fip(
            fvn1_fixture.vn_id, fvn2_vm1_fixture.vm_id)
        self.addCleanup(fip_fixture1.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture1.verify_fip(
            fip_id1, fvn2_vm1_fixture, fvn1_fixture)

        fip_fixture2 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name2,
                vn_id=fvn2_fixture.vn_id))
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

        if not result:
            self.logger.error(
                'Test Failed for restart of agent and control node with floating IP')
            assert result
        return result
    # end test_service_restart_with_fip

