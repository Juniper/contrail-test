# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run mx_tests'. To run specific tests,
# You can do 'python -m testtools.run -l mx_test'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
# Set the env variable MX_GW_TESTto 1 to run the test
#
import os
from common.openstack_libs import nova_client as mynovaclient
from common.openstack_libs import nova_exception as novaException
import unittest
import fixtures
import testtools
import socket
import test
import base
from common.contrail_test_init import ContrailTestInit
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from common.connections import ContrailConnections
from floating_ip import *
from policy_test import *
from contrail_fixtures import *
from control_node import *
from tcutils.wrappers import preposttest_wrapper


class TestSerialSanity_MX(base.FloatingIpBaseTest):

    @classmethod
    def setUpClass(cls):
        super(TestSerialSanity_MX, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestSerialSanity_MX, cls).tearDownClass()

    def is_test_applicable(self):
        if os.environ.get('MX_GW_TEST') != '1':
            return (False, 'Skipping Test. Env variable MX_GW_TEST is not set')
        return (True, None)

    @test.attr(type=['mx_test', 'serial', 'sanity', 'vcenter'])
    @preposttest_wrapper
    def test_change_of_rt_in_vn(self):
        '''
         Verify the impact of change in route target of a vn
         Test Steps:
           1.Test configuration is simillar with (test_mx_gateway)
           2.In this test, first configure the public100 VN with wrong route target value (Mismatch with MX)
           3.Check the communication outside virtual network cluster fails
           4.Modify the route target value(Matching with MX)
           5.Communication should pass
         Pass criteria:  Step 3 and 5 should pass.
         Maintainer: chhandak@juniper.net
        '''

        result = True
        fip_pool_name = self.inputs.fip_pool_name 
        vm1_name = 'vm200'
        vn1_name = 'vn200'
        vn1_subnets = ['12.1.1.0/24']
        mx_rt = self.inputs.mx_rt
        mx_rt_wrong = '11111'

        vn1_fixture = self.useFixture(
	    VNFixture(project_name=self.inputs.project_name,
	    	  connections=self.connections, vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()

        vm1_fixture = self.useFixture(
	    VMFixture(project_name=self.inputs.project_name,
	    	  connections=self.connections, vn_obj=vn1_fixture.obj, vm_name=vm1_name))
        vm1_fixture.wait_till_vm_is_up()
        assert vm1_fixture.verify_on_setup()

        # Delete the correct RT value and add the wrong one.
        routing_instance = self.public_vn_obj.public_vn_fixture.ri_name
        self.public_vn_obj.public_vn_fixture.del_route_target(
            routing_instance, self.inputs.router_asn, mx_rt)
        sleep(2)

        self.public_vn_obj.public_vn_fixture.add_route_target(
            routing_instance, self.inputs.router_asn, mx_rt_wrong)
        sleep(10)

        # Adding further projects to floating IP.
        self.logger.info('Adding project %s to FIP pool %s' %
                         (self.inputs.project_name, fip_pool_name))
        project_obj = self.public_vn_obj.fip_fixture.assoc_project\
                        (self.inputs.project_name)

        fip_id = self.public_vn_obj.fip_fixture.create_and_assoc_fip(
            self.public_vn_obj.public_vn_fixture.vn_id, vm1_fixture.vm_id, project_obj)
        self.addCleanup(self.public_vn_obj.fip_fixture.disassoc_and_delete_fip, fip_id)

        assert self.public_vn_obj.fip_fixture.verify_fip(fip_id, vm1_fixture,
                self.public_vn_obj.public_vn_fixture)

        self.logger.info(
	    "BGP Peer configuraion done and trying to outside the VN cluster")

        if not vm1_fixture.ping_to_ip('www-int.juniper.net'):
	    self.logger.info(
	        "Here ping should fail as VN  is configured with wrong RT values" )
        else:
	    self.logger.error(
	        "Ping should fail. But ping is successful even with wrong RT values")
	    result = result and False

        # Change the RT value to correct one.
        routing_instance = self.public_vn_obj.public_vn_fixture.ri_name
        self.public_vn_obj.public_vn_fixture.del_route_target(
	    routing_instance, self.inputs.router_asn, mx_rt_wrong)
        sleep(2)
        self.public_vn_obj.public_vn_fixture.add_route_target(
	    routing_instance, self.inputs.router_asn, mx_rt)
        sleep(10)

        self.logger.info("Now trying to ping %s" % (self.inputs.public_host))
        if not vm1_fixture.ping_with_certainty(self.inputs.public_host):
	    result = result and False

        # Reverting the RT value for fixture cleanup.
        self.public_vn_obj.public_vn_fixture.del_route_target(
	    routing_instance, self.inputs.router_asn, mx_rt)
        sleep(2)
        self.public_vn_obj.public_vn_fixture.add_route_target(
	    routing_instance, self.inputs.router_asn, mx_rt_wrong)

        # Removing further projects from floating IP pool. For cleanup
        self.logger.info('Removing project %s to FIP pool %s' %
                    (self.inputs.project_name, fip_pool_name))
        project_obj = self.public_vn_obj.fip_fixture.deassoc_project\
                    (self.inputs.project_name)

        if not result:
	    self.logger.error(
	        'Test  ping outside VN cluster from VM %s failed' % (vm1_name))
	    assert result

        return True

    # end test_change_of_rt_in_vn
