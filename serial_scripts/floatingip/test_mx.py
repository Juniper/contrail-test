# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run mx_tests'. To run specific tests,
# You can do 'python -m testtools.run -l mx_test'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
# Set the env variable MX_GW_TESTto 1 to run the test
#
import os
from novaclient import client as mynovaclient
from novaclient import exceptions as novaException
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


class TestSanity_MX(base.FloatingIpBaseTest):

    @classmethod
    def setUpClass(cls):
        super(TestSanity_MX, cls).setUpClass()

    @test.attr(type=['mx_test', 'sanity'])
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
        if (('MX_GW_TEST' in os.environ) and (
                os.environ.get('MX_GW_TEST') == '1')):

            result = True
            fip_pool_name = self.inputs.fip_pool_name
            fip_subnets = [self.inputs.fip_pool]
            fvn_name = 'public'
            vm1_name = 'vm200'
            vn1_name = 'vn200'
            vn1_subnets = ['11.1.1.0/24']
            api_server_port = self.inputs.api_server_port
            api_server_ip = self.inputs.cfgm_ip
            mx_rt = self.inputs.mx_rt
            router_name = self.inputs.ext_routers[0][0]
            router_ip = self.inputs.ext_routers[0][1]
            mx_rt_wrong = '11111'

            self.project_fixture = self.useFixture(
                ProjectFixture(
                    vnc_lib_h=self.vnc_lib,
                    project_name=self.inputs.project_name,
                    connections=self.connections))
            self.logger.info(
                'Default SG to be edited for allow all on project: %s' %
                self.inputs.project_name)
            self.project_fixture.set_sec_group_for_allow_all(
                self.inputs.project_name, 'default')

            fvn_fixture = self.useFixture(
                VNFixture(
                    project_name=self.inputs.stack_tenant,
                    connections=self.admin_connections,
                    vn_name=fvn_name,
                    inputs=self.admin_inputs,
                    subnets=fip_subnets,
                    router_asn=self.inputs.router_asn,
                    rt_number=mx_rt_wrong))
            assert fvn_fixture.verify_on_setup()
            vn1_fixture = self.useFixture(
                VNFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_name=vn1_name,
                    inputs=self.inputs,
                    subnets=vn1_subnets))
            assert vn1_fixture.verify_on_setup()
            vm1_fixture = self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_obj=vn1_fixture.obj,
                    vm_name=vm1_name))
            assert vm1_fixture.verify_on_setup()

            fip_fixture = self.useFixture(
                FloatingIPFixture(
                    project_name=self.inputs.stack_tenant,
                    inputs=self.admin_inputs,
                    connections=self.admin_connections,
                    pool_name=fip_pool_name,
                    vn_id=fvn_fixture.vn_id))
            assert fip_fixture.verify_on_setup()
            # Adding further projects to floating IP.
            self.logger.info('Adding project %s to FIP pool %s' %
                             (self.inputs.project_name, fip_pool_name))
            project_obj = fip_fixture.assoc_project(fip_fixture, self.inputs.project_name)

            fip_id = fip_fixture.create_and_assoc_fip(
                fvn_fixture.vn_id, vm1_fixture.vm_id, project_obj)
            self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)
            assert fip_fixture.verify_fip(fip_id, vm1_fixture, fvn_fixture)

            routing_instance = fvn_fixture.ri_name
            # TODO Configure MX. Doing Manually For Now
            # Configuring all control nodes here
            for entry in self.inputs.bgp_ips:
                hostname = self.inputs.host_data[entry]['name']
                entry_control_ip = self.inputs.host_data[
                    entry]['host_control_ip']
                cn_fixture1 = self.useFixture(
                    CNFixture(
                        connections=self.connections,
                        router_name=hostname,
                        router_ip=entry_control_ip,
                        router_type='contrail',
                        inputs=self.inputs))
            cn_fixturemx = self.useFixture(
                CNFixture(
                    connections=self.connections,
                    router_name=router_name,
                    router_ip=router_ip,
                    router_type='mx',
                    inputs=self.inputs))
            sleep(10)
            assert cn_fixturemx.verify_on_setup()
            self.logger.info(
                "BGP Peer configuraion done and trying to outside the VN cluster")

            if not vm1_fixture.ping_to_ip('www-int.juniper.net'):
                self.logger.info(
                    "Here ping should fail as VN %s is configured with wrong RT values" %
                    fvn_name)
            else:
                self.logger.error(
                    "Ping should fail. But ping is successful even with wrong RT values")
                result = result and False

            # Change the RT value to correct one.
            fvn_fixture.del_route_target(
                routing_instance, self.inputs.router_asn, mx_rt_wrong)
            sleep(2)
            fvn_fixture.add_route_target(
                routing_instance, self.inputs.router_asn, mx_rt)
            sleep(10)

            self.logger.info(
                "Checking the basic routing. Pinging known local IP bng2-core-gw1.jnpr.net")
            assert vm1_fixture.ping_with_certainty('10.206.255.2')
            self.logger.info("Now trying to ping www-int.juniper.net")
            if not vm1_fixture.ping_with_certainty('www-int.juniper.net'):
                result = result and False

            # Reverting the RT value for fixture cleanup.
            fvn_fixture.del_route_target(
                routing_instance, self.inputs.router_asn, mx_rt)
            sleep(2)
            fvn_fixture.add_route_target(
                routing_instance, self.inputs.router_asn, mx_rt_wrong)

            if not result:
                self.logger.error(
                    'Test  ping outside VN cluster from VM %s failed' %
                    (vm1_name))
                assert result
        else:
            self.logger.info(
                "Skiping Test. Env variable MX_TEST is not set. Skiping the test")
            raise self.skipTest(
                "Skiping Test. Env variable MX_TEST is not set. Skiping th test")

        # Removing further projects from floating IP pool. For cleanup
        self.logger.info('Removing project %s to FIP pool %s' %
            (self.inputs.project_name, fip_pool_name))
        project_obj = fip_fixture.deassoc_project(fip_fixture, self.inputs.project_name)

        return True
    # end test_change_of_rt_in_vn

