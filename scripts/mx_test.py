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


class TestMxSanityFixture(testtools.TestCase, fixtures.TestWithFixtures):

#    @classmethod
    def setUp(self):
        super(TestMxSanityFixture, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.quantum_fixture = self.connections.quantum_fixture
        self.nova_fixture = self.connections.nova_fixture
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.analytics_obj = self.connections.analytics_obj
        self.agent_inspect = self.connections.agent_inspect
    # end setUpClass

    def cleanUp(self):
        super(TestMxSanityFixture, self).cleanUp()
    # end cleanUp

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_mx_gateway(self):
        '''
         Test to validate floating-ip from a public pool  assignment to a VM. It creates a VM, assigns a FIP to it and pings to outside the cluster.
             1.Check env variable MX_GW_TEST is set to 1. This confirm the MX present in Setup.
             2.Create 2 Vns. One public100 and other vn200. VN public100 created with IP pool accessible from outside network.
             3.VM vm200 launched under vn200.
             4.VM vm200 get floating ip from public100 network
             5.Configure the control with MX peering if not present.
             6.Try to ping outside network and check connecivity

         Pass criteria:  Step 6 should pass
         Maintainer: chhandak@juniper.net
        '''
        if (('MX_GW_TEST' in os.environ) and (os.environ.get('MX_GW_TEST') == '1')):

            result = True
            fip_pool_name = self.inputs.fip_pool_name
            fvn_name = 'public100'
            fip_subnets = [self.inputs.fip_pool]
            vm1_name = 'vm200'
            vn1_name = 'vn200'
            vn1_subnets = ['11.1.1.0/24']
            api_server_port = self.inputs.api_server_port
            api_server_ip = self.inputs.cfgm_ip
            mx_rt = self.inputs.mx_rt
            router_name = self.inputs.ext_routers[0][0]
            router_ip = self.inputs.ext_routers[0][1]

            self.project_fixture = self.useFixture(ProjectFixture(
                vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
            self.logger.info(
                'Default SG to be edited for allow all on project: %s' %
                self.inputs.project_name)
            self.project_fixture.set_sec_group_for_allow_all(
                self.inputs.project_name, 'default')

            fvn_fixture = self.useFixture(
                VNFixture(
                    project_name=self.inputs.project_name, connections=self.connections,
                    vn_name=fvn_name, inputs=self.inputs, subnets=fip_subnets, router_asn=self.inputs.router_asn, rt_number=mx_rt))
            assert fvn_fixture.verify_on_setup()
            vn1_fixture = self.useFixture(
                VNFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
            assert vn1_fixture.verify_on_setup()
            vm1_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn1_fixture.obj, vm_name=vm1_name))
            vm1_fixture.wait_till_vm_is_up()
            assert vm1_fixture.verify_on_setup()

            fip_fixture = self.useFixture(
                FloatingIPFixture(
                    project_name=self.inputs.project_name, inputs=self.inputs,
                    connections=self.connections, pool_name=fip_pool_name, vn_id=fvn_fixture.vn_id))
            assert fip_fixture.verify_on_setup()
            fip_id = fip_fixture.create_and_assoc_fip(
                fvn_fixture.vn_id, vm1_fixture.vm_id)
            self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)
            assert fip_fixture.verify_fip(fip_id, vm1_fixture, fvn_fixture)
            routing_instance = fvn_fixture.ri_name

            # Configuring all control nodes here
            for entry in self.inputs.bgp_ips:
                hostname = self.inputs.host_data[entry]['name']
                entry_control_ip = self.inputs.host_data[
                    entry]['host_control_ip']
                cn_fixture1 = self.useFixture(
                    CNFixture(connections=self.connections,
                              router_name=hostname, router_ip=entry_control_ip, router_type='contrail', inputs=self.inputs))
            cn_fixturemx = self.useFixture(
                CNFixture(connections=self.connections,
                          router_name=router_name, router_ip=router_ip, router_type='mx', inputs=self.inputs))
            sleep(10)
            assert cn_fixturemx.verify_on_setup()
            # TODO Configure MX. Doing Manually For Now
            self.logger.info(
                "BGP Peer configuraion done and trying to outside the VN cluster")
            self.logger.info(
                "Checking the basic routing. Pinging known local IP bng2-core-gw1.jnpr.net")
            assert vm1_fixture.ping_with_certainty('10.206.255.2')
            self.logger.info("Now trying to ping www-int.juniper.net")
            if not vm1_fixture.ping_with_certainty('www-int.juniper.net'):
                result = result and False

            if not result:
                self.logger.error(
                    'Test  ping outside VN cluster from VM %s failed' % (vm1_name))
                assert result
        else:
            self.logger.info(
                "Skiping Test. Env variable MX_TEST is not set. Skiping th test")
            raise self.skipTest(
                "Skiping Test. Env variable MX_TEST is not set. Skiping th test")

        return True
    # end test_mx_gateway

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
        if (('MX_GW_TEST' in os.environ) and (os.environ.get('MX_GW_TEST') == '1')):

            result = True
            fip_pool_name = self.inputs.fip_pool_name
            fip_subnets = [self.inputs.fip_pool]
            fvn_name = 'public100'
            vm1_name = 'vm200'
            vn1_name = 'vn200'
            vn1_subnets = ['11.1.1.0/24']
            api_server_port = self.inputs.api_server_port
            api_server_ip = self.inputs.cfgm_ip
            mx_rt = self.inputs.mx_rt
            router_name = self.inputs.ext_routers[0][0]
            router_ip = self.inputs.ext_routers[0][1]
            mx_rt_wrong = '11111'

            self.project_fixture = self.useFixture(ProjectFixture(
                vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
            self.logger.info(
                'Default SG to be edited for allow all on project: %s' %
                self.inputs.project_name)
            self.project_fixture.set_sec_group_for_allow_all(
                self.inputs.project_name, 'default')

            fvn_fixture = self.useFixture(
                VNFixture(
                    project_name=self.inputs.project_name, connections=self.connections,
                    vn_name=fvn_name, inputs=self.inputs, subnets=fip_subnets, router_asn=self.inputs.router_asn, rt_number=mx_rt_wrong))
            assert fvn_fixture.verify_on_setup()
            vn1_fixture = self.useFixture(
                VNFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
            assert vn1_fixture.verify_on_setup()
            vm1_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn1_fixture.obj, vm_name=vm1_name))
            vm1_fixture.wait_till_vm_is_up()
            assert vm1_fixture.verify_on_setup()

            fip_fixture = self.useFixture(
                FloatingIPFixture(
                    project_name=self.inputs.project_name, inputs=self.inputs,
                    connections=self.connections, pool_name=fip_pool_name, vn_id=fvn_fixture.vn_id))
            assert fip_fixture.verify_on_setup()
            fip_id = fip_fixture.create_and_assoc_fip(
                fvn_fixture.vn_id, vm1_fixture.vm_id)
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
                    CNFixture(connections=self.connections,
                              router_name=hostname, router_ip=entry_control_ip, router_type='contrail', inputs=self.inputs))
            cn_fixturemx = self.useFixture(
                CNFixture(connections=self.connections,
                          router_name=router_name, router_ip=router_ip, router_type='mx', inputs=self.inputs))
            sleep(10)
            assert cn_fixturemx.verify_on_setup()
            self.logger.info(
                "BGP Peer configuraion done and trying to outside the VN cluster")

            if not vm1_fixture.ping_to_ip('www-int.juniper.net'):
                self.logger.info(
                    "Here ping should fail as VN %s is configured with wrong RT values" % fvn_name)
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
                    'Test  ping outside VN cluster from VM %s failed' % (vm1_name))
                assert result
        else:
            self.logger.info(
                "Skiping Test. Env variable MX_TEST is not set. Skiping the test")
            raise self.skipTest(
                "Skiping Test. Env variable MX_TEST is not set. Skiping th test")

        return True
    # end test_change_of_rt_in_vn

    @preposttest_wrapper
    def test_apply_policy_fip_on_same_vn(self):
        '''A particular VN is configure with policy to talk accross VN's and FIP to access outside'''

        if (('MX_GW_TEST' in os.environ) and (os.environ.get('MX_GW_TEST') == '1')):

            result = True
            fip_pool_name = self.inputs.fip_pool_name
            fip_subnets = [self.inputs.fip_pool]
            fvn_name = 'public100'
            vm1_name = 'vm200'
            vn1_name = 'vn200'
            vn1_subnets = ['11.1.1.0/24']
            vm2_name = 'vm300'
            vn2_name = 'vn300'
            vn2_subnets = ['22.1.1.0/24']
            api_server_port = self.inputs.api_server_port
            api_server_ip = self.inputs.cfgm_ip
            mx_rt = self.inputs.mx_rt
            router_name = self.inputs.ext_routers[0][0]
            router_ip = self.inputs.ext_routers[0][1]

            self.project_fixture = self.useFixture(ProjectFixture(
                vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
            self.logger.info(
                'Default SG to be edited for allow all on project: %s' %
                self.inputs.project_name)
            self.project_fixture.set_sec_group_for_allow_all(
                self.inputs.project_name, 'default')

            # Get all compute host
            host_list = []
            for host in self.inputs.compute_ips:
                host_list.append(self.inputs.host_data[host]['name'])

            fvn_fixture = self.useFixture(
                VNFixture(
                    project_name=self.inputs.project_name, connections=self.connections,
                    vn_name=fvn_name, inputs=self.inputs, subnets=fip_subnets, router_asn=self.inputs.router_asn, rt_number=mx_rt))
            assert fvn_fixture.verify_on_setup()
            vn1_fixture = self.useFixture(
                VNFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
            assert vn1_fixture.verify_on_setup()
            vm1_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn1_fixture.obj, vm_name=vm1_name, node_name=host_list[0]))
            vm1_fixture.wait_till_vm_is_up()
            assert vm1_fixture.verify_on_setup()

            vn2_fixture = self.useFixture(
                VNFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_name=vn2_name, inputs=self.inputs, subnets=vn2_subnets))
            assert vn2_fixture.verify_on_setup()
            vm2_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn2_fixture.obj, vm_name=vm2_name, node_name=host_list[1]))
            vm2_fixture.wait_till_vm_is_up()
            assert vm2_fixture.verify_on_setup()

            # Fip
            fip_fixture = self.useFixture(
                FloatingIPFixture(
                    project_name=self.inputs.project_name, inputs=self.inputs,
                    connections=self.connections, pool_name=fip_pool_name, vn_id=fvn_fixture.vn_id))
            assert fip_fixture.verify_on_setup()
            fip_id = fip_fixture.create_and_assoc_fip(
                fvn_fixture.vn_id, vm1_fixture.vm_id)
            self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)
            assert fip_fixture.verify_fip(fip_id, vm1_fixture, fvn_fixture)
            routing_instance = fvn_fixture.ri_name

            # Configuring all control nodes here
            for entry in self.inputs.bgp_ips:
                hostname = self.inputs.host_data[entry]['name']
                entry_control_ip = self.inputs.host_data[
                    entry]['host_control_ip']
                cn_fixture1 = self.useFixture(
                    CNFixture(connections=self.connections,
                              router_name=hostname, router_ip=entry_control_ip, router_type='contrail', inputs=self.inputs))
            cn_fixturemx = self.useFixture(
                CNFixture(connections=self.connections,
                          router_name=router_name, router_ip=router_ip, router_type='mx', inputs=self.inputs))
            sleep(10)
            assert cn_fixturemx.verify_on_setup()

            # Policy
            # Apply policy in between VN
            policy1_name = 'policy1'
            policy2_name = 'policy2'
            rules = [
                {
                    'direction': '<>', 'simple_action': 'pass',
                    'protocol': 'icmp',
                    'source_network': vn1_name,
                    'dest_network': vn2_name,
                },
            ]
            rev_rules = [
                {
                    'direction': '<>', 'simple_action': 'pass',
                    'protocol': 'icmp',
                    'source_network': vn2_name,
                    'dest_network': vn1_name,
                },
            ]

            policy1_fixture = self.useFixture(PolicyFixture(
                policy_name=policy1_name, rules_list=rules, inputs=self.inputs, connections=self.connections))
            policy2_fixture = self.useFixture(PolicyFixture(
                policy_name=policy2_name, rules_list=rev_rules, inputs=self.inputs, connections=self.connections))

            self.logger.info('Apply policy between VN %s and %s' %
                             (vn1_name, vn2_name))
            vn1_fixture.bind_policies(
                [policy1_fixture.policy_fq_name], vn1_fixture.vn_id)
            self.addCleanup(vn1_fixture.unbind_policies,
                            vn1_fixture.vn_id, [policy1_fixture.policy_fq_name])
            vn2_fixture.bind_policies(
                [policy2_fixture.policy_fq_name], vn2_fixture.vn_id)
            self.addCleanup(vn2_fixture.unbind_policies,
                            vn2_fixture.vn_id, [policy2_fixture.policy_fq_name])

            self.logger.info(
                'Checking connectivity within VNS cluster through Policy')
            self.logger.info('Ping from %s to %s' % (vm1_name, vm2_name))
            if not vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip):
                result = result and False

            self.logger.info(
                'Checking connectivity outside VNS cluster through FIP')
            self.logger.info(
                "Checking the basic routing. Pinging known local IP bng2-core-gw1.jnpr.net")
            assert vm1_fixture.ping_with_certainty('10.206.255.2')
            self.logger.info("Now trying to ping www-int.juniper.net")
            if not vm1_fixture.ping_with_certainty('www-int.juniper.net'):
                result = result and False

            if not result:
                self.logger.error(
                    'Test to verify the Traffic to Inside and Outside Virtual network cluster simaltaneiously failed')
                assert result
        else:
            self.logger.info(
                "Skiping Test. Env variable MX_TEST is not set. Skiping the test")
            raise self.skipTest(
                "Skiping Test. Env variable MX_TEST is not set. Skiping the test")
        return True
    # end test_apply_policy_fip_on_same_vn

    @preposttest_wrapper
    def test_ftp_http_with_public_ip(self):
        '''Test FTP and HTTP traffic from public network.'''

        if (('MX_GW_TEST' in os.environ) and (os.environ.get('MX_GW_TEST') == '1')):

            result = True
            fip_pool_name = self.inputs.fip_pool_name
            fip_subnets = [self.inputs.fip_pool]
            fvn_name = 'public100'
            vm1_name = 'vm200'
            vn1_name = 'vn200'
            vn1_subnets = ['11.1.1.0/24']
            api_server_port = self.inputs.api_server_port
            api_server_ip = self.inputs.cfgm_ip
            mx_rt = self.inputs.mx_rt
            router_name = self.inputs.ext_routers[0][0]
            router_ip = self.inputs.ext_routers[0][1]

            self.project_fixture = self.useFixture(ProjectFixture(
                vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
            self.logger.info(
                'Default SG to be edited for allow all on project: %s' %
                self.inputs.project_name)
            self.project_fixture.set_sec_group_for_allow_all(
                self.inputs.project_name, 'default')

            fvn_fixture = self.useFixture(
                VNFixture(
                    project_name=self.inputs.project_name, connections=self.connections,
                    vn_name=fvn_name, inputs=self.inputs, subnets=fip_subnets, router_asn=self.inputs.router_asn, rt_number=mx_rt))
            assert fvn_fixture.verify_on_setup()
            vn1_fixture = self.useFixture(
                VNFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
            assert vn1_fixture.verify_on_setup()
            vm1_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn1_fixture.obj, vm_name=vm1_name))
            vm1_fixture.wait_till_vm_is_up()
            assert vm1_fixture.verify_on_setup()
            fip_fixture = self.useFixture(
                FloatingIPFixture(
                    project_name=self.inputs.project_name, inputs=self.inputs,
                    connections=self.connections, pool_name=fip_pool_name, vn_id=fvn_fixture.vn_id))
            assert fip_fixture.verify_on_setup()
            fip_id = fip_fixture.create_and_assoc_fip(
                fvn_fixture.vn_id, vm1_fixture.vm_id)
            assert fip_fixture.verify_fip(fip_id, vm1_fixture, fvn_fixture)
            self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)
            routing_instance = fvn_fixture.ri_name

            # Configuring all control nodes here
            for entry in self.inputs.bgp_ips:
                hostname = self.inputs.host_data[entry]['name']
                entry_control_ip = self.inputs.host_data[
                    entry]['host_control_ip']
                cn_fixture1 = self.useFixture(
                    CNFixture(connections=self.connections,
                              router_name=hostname, router_ip=entry_control_ip, router_type='contrail', inputs=self.inputs))
            cn_fixturemx = self.useFixture(
                CNFixture(connections=self.connections,
                          router_name=router_name, router_ip=router_ip, router_type='mx', inputs=self.inputs))
            sleep(10)
            assert cn_fixturemx.verify_on_setup()
            self.logger.info(
                "BGP Peer configuraion done and trying to outside the VN cluster")
            self.logger.info(
                "Checking the basic routing. Pinging known local IP bng2-core-gw1.jnpr.net")
            assert vm1_fixture.ping_with_certainty('10.206.255.2')
            self.logger.info("Now trying to ping www-int.juniper.net")
            if not vm1_fixture.ping_with_certainty('www-int.juniper.net'):
                result = result and False

            self.logger.info('Testing FTP...Intsalling VIM In the VM via FTP')
            run_cmd = "wget ftp://ftp.vim.org/pub/vim/unix/vim-7.3.tar.bz2"
            vm1_fixture.run_cmd_on_vm(cmds=[run_cmd])
            output = vm1_fixture.return_output_values_list[0]
            if 'saved' not in output:
                self.logger.error("FTP failed from VM %s" %
                                  (vm1_fixture.vm_name))
                result = result and False
            else:
                self.logger.info("FTP successful from VM %s via FIP" %
                                 (vm1_fixture.vm_name))

            self.logger.info(
                'Testing HTTP...Trying to access www-int.juniper.net')
            run_cmd = "wget http://www-int.juniper.net"
            vm1_fixture.run_cmd_on_vm(cmds=[run_cmd])
            output = vm1_fixture.return_output_values_list[0]
            if 'saved' not in output:
                self.logger.error("HTTP failed from VM %s" %
                                  (vm1_fixture.vm_name))
                result = result and False
            else:
                self.logger.info("HTTP successful from VM %s via FIP" %
                                 (vm1_fixture.vm_name))

            self.logger.info(
                'Testing bug 1336. Trying wget with www.google.com')
            run_cmd = "wget http://www.google.com --timeout 5 --tries 12"
            output = None
            vm1_fixture.run_cmd_on_vm(cmds=[run_cmd])
            output = vm1_fixture.return_output_values_list[0]
            if 'saved' not in output:
                self.logger.error(
                    "HTTP failed from VM %s to google.com. Bug 1336" %
                    (vm1_fixture.vm_name))
                result = result and False
                assert result, "wget failed to google.com. Bug 1336"
            else:
                self.logger.info("HTTP successful from VM %s via FIP" %
                                 (vm1_fixture.vm_name))

            if not result:
                self.logger.error(
                    'Test FTP and HTTP traffic from public network Failed.')
                assert result
        else:
            self.logger.info(
                "Skiping Test. Env variable MX_TEST is not set. Skiping the test")
            raise self.skipTest(
                "Skiping Test. Env variable MX_TEST is not set. Skiping the test")

        return True
    # end test_ftp_http_with_public_ip

    @preposttest_wrapper
    def test_fip_with_vm_in_2_vns(self):
        ''' Test to validate that awhen  VM is associated two VN and and diffrent floating IP allocated to them.
        '''
        fip_pool_name = self.inputs.fip_pool_name
        fip_subnets = [self.inputs.fip_pool]
        fip_pool_internal = 'some_pool2'
        fvn_name = 'public100'
        router_name = self.inputs.ext_routers[0][0]
        router_ip = self.inputs.ext_routers[0][1]
        mx_rt = self.inputs.mx_rt
        vm1_name = 'vm_mine1'
        vn1_name = 'vn222'
        vn1_subnets = ['11.1.1.0/24']
        vn2_name = 'vn223'
        vn2_subnets = ['22.1.1.0/24']
        vn3_name = 'vn224'
        vn3_gateway = '22.1.1.254'
        vn3_subnets = ['33.1.1.0/24']
        vm2_name = 'vm_vn222'
        vm3_name = 'vm_vn223'
        vm4_name = 'vm_vn224'
        list_of_ips = []
        publicip_list = (self.inputs.fip_pool.split('/')[0].split('.'))
        publicip_list[3] = str(int(publicip_list[3]) + 2)
        publicip = ".".join(publicip_list)

        self.project_fixture = self.useFixture(ProjectFixture(
            vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
        self.logger.info(
            'Default SG to be edited for allow all on project: %s' %
            self.inputs.project_name)
        self.project_fixture.set_sec_group_for_allow_all(
            self.inputs.project_name, 'default')

        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn2_name, inputs=self.inputs, subnets=vn2_subnets))
        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn3_name, inputs=self.inputs, subnets=vn3_subnets))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        assert vn3_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_objs=[vn1_fixture.obj, vn2_fixture.obj], vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn1_fixture.obj, vm_name=vm2_name, project_name=self.inputs.project_name))

        vm2_fixture.wait_till_vm_is_up()
        assert vm2_fixture.verify_on_setup()
        vm3_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn2_fixture.obj, vm_name=vm3_name, project_name=self.inputs.project_name))
        assert vm3_fixture.verify_on_setup()
        vm4_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn3_fixture.obj, vm_name=vm4_name, project_name=self.inputs.project_name))
        assert vm4_fixture.verify_on_setup()
        list_of_ips = vm1_fixture.vm_ips
        i = 'ifconfig eth1 %s netmask 255.255.255.0' % list_of_ips[1]
        cmd_to_output = [i]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_output, as_sudo=True)
        output = vm1_fixture.return_output_cmd_dict[i]
        print output

        j = 'ifconfig -a'
        cmd_to_output1 = [j]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_output1)
        output1 = vm1_fixture.return_output_cmd_dict[j]
        print output1

        for ips in list_of_ips:
            if ips not in output1:
                result = False
                self.logger.error("IP %s not assigned to any eth intf of %s" %
                                  (ips, vm1_fixture.vm_name))
                assert result, "PR 1018"
            else:
                self.logger.info("IP %s is assigned to eth intf of %s" %
                                 (ips, vm1_fixture.vm_name))

        self.logger.info('-' * 80)
        self.logger.info('Will ping to the two VMs from the Multi-NIC VM')
        self.logger.info('-' * 80)
        result = True
        if not vm1_fixture.ping_to_ip(vm2_fixture.vm_ip):
            result = False
            assert result, "Ping to %s Fail" % vm2_fixture.vm_ip
        else:
            self.logger.info('Ping to %s Pass' % vm2_fixture.vm_ip)
        if not vm1_fixture.ping_to_ip(vm3_fixture.vm_ip):
            result = False
            assert result, "Ping to %s Fail" % vm3_fixture.vm_ip
        else:
            self.logger.info('Ping to %s Pass' % vm3_fixture.vm_ip)

        self.logger.info('-' * 80)
        # Configuring all control nodes here
        for entry in self.inputs.bgp_ips:
            hostname = self.inputs.host_data[entry]['name']
            entry_control_ip = self.inputs.host_data[entry]['host_control_ip']
            cn_fixture1 = self.useFixture(
                CNFixture(connections=self.connections,
                          router_name=hostname, router_ip=entry_control_ip, router_type='contrail', inputs=self.inputs))
        cn_fixturemx = self.useFixture(CNFixture(connections=self.connections,
                                                 router_name=router_name, router_ip=router_ip, router_type='mx', inputs=self.inputs))
        sleep(10)
        assert cn_fixturemx.verify_on_setup()

        fvn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=fvn_name, inputs=self.inputs, subnets=fip_subnets, router_asn=self.inputs.router_asn, rt_number=mx_rt))
        assert fvn_fixture.verify_on_setup()

        # FIP public
        self.logger.info(
            "Configuring FLoating IP in VM %s to communicate public network" % (vm1_name))
        vmi1_id = vm1_fixture.tap_intf[vn1_fixture.vn_fq_name]['uuid']
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name, vn_id=fvn_fixture.vn_id))
        assert fip_fixture.verify_on_setup()
        my_fip_name = 'fip'
        fvn_obj = self.vnc_lib.virtual_network_read(id=fvn_fixture.vn_id)
        fip_pool_obj = FloatingIpPool(fip_pool_name, fvn_obj)
        fip_obj = FloatingIp(my_fip_name, fip_pool_obj, publicip, True)
        vm1_intf = self.vnc_lib.virtual_machine_interface_read(id=vmi1_id)
        # Read the project obj and set to the floating ip object.
        fip_obj.set_project(self.project_fixture.project_obj)
        fip_obj.add_virtual_machine_interface(vm1_intf)
        self.vnc_lib.floating_ip_create(fip_obj)
        self.addCleanup(self.vnc_lib.floating_ip_delete, fip_obj.fq_name)
        # TODO Need to add verify_fip()

        # FIP internal
        self.logger.info(
            "Configuring FLoating IP in VM %s to communicate inside VNS to other network" % (vm1_name))
        vmi2_id = vm1_fixture.tap_intf[vn2_fixture.vn_fq_name]['uuid']
        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_internal, vn_id=vn3_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()
        my_fip_name1 = 'fip1'
        vn3_obj = self.vnc_lib.virtual_network_read(id=vn3_fixture.vn_id)
        fip_pool_obj1 = FloatingIpPool(fip_pool_internal, vn3_obj)
        fip_obj1 = FloatingIp(my_fip_name1, fip_pool_obj1, '33.1.1.241', True)
        # Read the project obj and set to the floating ip object.
        fip_obj1.set_project(self.project_fixture.project_obj)
        vm2_intf = self.vnc_lib.virtual_machine_interface_read(id=vmi2_id)
        fip_obj1.add_virtual_machine_interface(vm2_intf)
        self.vnc_lib.floating_ip_create(fip_obj1)
        # Need to add route in the host explictly for non default VMI
        i = ' route add -net %s netmask 255.255.255.0 gw %s dev eth1' % (
            vn3_subnets[0].split('/')[0], vn3_gateway)
        self.logger.info("Configuring explicit route %s in host VM" % (i))
        cmd_to_output = [i]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_output, as_sudo=True)
        output = vm1_fixture.return_output_cmd_dict[i]
        print output

        self.addCleanup(self.vnc_lib.floating_ip_delete, fip_obj1.fq_name)
        # TODO Need to add verify_fip()

        # Checking communication to other network in VNS cluster
        self.logger.info('Checking connectivity other network using FIP')
        if not vm1_fixture.ping_with_certainty(vm4_fixture.vm_ip):
            result = result and False
        self.logger.info(
            'Checking flow records is created with proper src IP while reaching other network inside VNS')
        # Verify Flow records here
        inspect_h1 = self.agent_inspect[vm1_fixture.vm_node_ip]
        flow_rec1_result = False
        flow_rec1_direction = False
        flow_rec1_nat = False
        for iter in range(25):
            self.logger.debug('**** Iteration %s *****' % iter)
            flow_rec1 = None
            flow_rec1 = inspect_h1.get_vna_fetchallflowrecords()
            for rec in flow_rec1:
                if ((rec['sip'] == list_of_ips[1]) and (rec['dip'] == vm4_fixture.vm_ip) and (rec['protocol'] == '1')):
                    flow_rec1_result = True
                    self.logger.info('Verifying NAT in flow records')
                    if rec['nat'] == 'enabled':
                        flow_rec1_nat = True
                    self.logger.info(
                        'Verifying traffic direction in flow records')
                    if rec['direction'] == 'ingress':
                        flow_rec1_direction = True
                    break
                else:
                    flow_rec1_result = False
            if flow_rec1_result:
                break
            else:
                iter += 1
                sleep(10)
        assert flow_rec1_result, 'Test Failed. Required ingress Traffic flow not found'
        assert flow_rec1_nat, 'Test Failed. NAT is not enabled in given flow'
        assert flow_rec1_direction, 'Test Failed. Traffic direction is wrong should be ingress'

        # Checking communication to outside VNS cluster
        self.logger.info(
            'Checking connectivity outside VNS cluster through FIP')
        self.logger.info(
            "Checking the basic routing. Pinging known local IP bng2-core-gw1.jnpr.net")
        assert vm1_fixture.ping_with_certainty('10.206.255.2')
        self.logger.info("Now trying to ping www-int.juniper.net")
        if not vm1_fixture.ping_with_certainty('www-int.juniper.net'):
            result = result and False

        inspect_h1 = self.agent_inspect[vm1_fixture.vm_node_ip]
        flow_rec2_result = False
        flow_rec2_direction = False
        flow_rec2_nat = False
        for iter in range(25):
            self.logger.debug('**** Iteration %s *****' % iter)
            flow_rec2 = None
            flow_rec2 = inspect_h1.get_vna_fetchallflowrecords()
            for rec in flow_rec2:
                if ((rec['sip'] == list_of_ips[0]) and (rec['dip'] == '10.206.255.2') and (rec['protocol'] == '1')):
                    flow_rec2_result = True
                    self.logger.info('Verifying NAT in flow records')
                    if rec['nat'] == 'enabled':
                        flow_rec2_nat = True
                    self.logger.info(
                        'Verifying traffic direction in flow records')
                    if rec['direction'] == 'ingress':
                        flow_rec2_direction = True
                    break
                else:
                    flow_rec2_result = False
            if flow_rec2_result:
                break
            else:
                iter += 1
                sleep(10)
        assert flow_rec2_result, 'Test Failed. Required ingress Traffic flow for the VN with public access not found'
        assert flow_rec2_nat, 'Test Failed. NAT is not enabled in given flow for the VN with public access'
        assert flow_rec2_direction, 'Test Failed. Traffic direction is wrong should be ingress for the VN with public access'

        # Delete and dis-associte FIP
        # self.vnc_lib.floating_ip_delete(fip_obj.fq_name)
        # self.vnc_lib.floating_ip_delete(fip_obj1.fq_name)
        return result
    # end test_vm_add_delete_in_2_vns_chk_ping
# end TestMxSanityFixture
