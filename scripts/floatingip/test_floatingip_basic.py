# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import re
import os
from common.openstack_libs import nova_client as mynovaclient
from common.openstack_libs import nova_exception as novaException
from user_test import UserFixture
import fixtures
import testtools
import unittest
from common.contrail_test_init import ContrailTestInit
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from common.connections import ContrailConnections
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


class FloatingipBasicTestSanity(base.FloatingIpBaseTest):

    @classmethod
    def setUpClass(cls):
        super(FloatingipBasicTestSanity, cls).setUpClass()

    @test.attr(type=['sanity', 'ci_sanity', 'quick_sanity', 'vcenter'])
    @preposttest_wrapper
    def test_floating_ip(self):
        '''Test to validate floating-ip Assignment to a VM. It creates a VM, assigns a FIP to it and pings to a IP in the FIP VN.
        '''
        result = True
        fip_pool_name = get_random_name('some-pool')
        vn1_vm1_name = get_random_name('vn1_vm1_name')
        fvn_vm1_name = get_random_name('fvn_vm1_name')

        (vn1_name, vn1_subnets) = (
            get_random_name("vn1"), [get_random_cidr()])
        (fvn_name, fvn_subnets) = (
            get_random_name("fvn"), [get_random_cidr()])

        # Get all computes
        self.get_two_different_compute_hosts()

        fvn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=fvn_name,
                subnets=fvn_subnets))

        assert fvn_fixture.verify_on_setup()

        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=vn1_name,
                subnets=vn1_subnets))

        assert vn1_fixture.verify_on_setup()

        vn1_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                vm_name=vn1_vm1_name,
                node_name=self.compute_1
            ))

        fvn_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=fvn_fixture.obj,
                vm_name=fvn_vm1_name,
                node_name=self.compute_2
            ))

        assert vn1_vm1_fixture.verify_on_setup()
        assert fvn_vm1_fixture.verify_on_setup()

        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name,
                vn_id=fvn_fixture.vn_id))
        assert fip_fixture.verify_on_setup()
        fip_id = fip_fixture.create_and_assoc_fip(
            fvn_fixture.vn_id, vn1_vm1_fixture.vm_id)
        assert fip_fixture.verify_fip(fip_id, vn1_vm1_fixture, fvn_fixture)
        vn1_vm1_fixture.wait_till_vm_up()
        fvn_vm1_fixture.wait_till_vm_up()
        if not vn1_vm1_fixture.ping_with_certainty(fvn_vm1_fixture.vm_ip):
            result = result and False
        fip_fixture.disassoc_and_delete_fip(fip_id)

        if not result:
            self.logger.error('Test to ping between VMs %s and %s failed' %
                              (vn1_vm1_name, fvn_vm1_name))
            assert result

        return True
    # end test_floating_ip
