# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run mx_tests'. To run specific tests,
# You can do 'python -m testtools.run -l mx_test'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
# Set the env variable MX_GW_TESTto 1 to run the test
#
import os
from time import sleep
import socket
import xml.etree.ElementTree as ET
from tcutils.wrappers import preposttest_wrapper
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from fabric.operations import get, put
from tcutils.wrappers import preposttest_wrapper
from encap import base
from vn_test import *
from vm_test import *
from floating_ip import *
from control_node import *
from policy_test import *
import test


class TestEncapCases(base.BaseEncapTest):

    @classmethod
    def setUpClass(cls):
        super(TestEncapCases, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_encaps_mx_gateway(self):
        '''Test to validate floating-ip froma a public pool  assignment to a VM. It creates a VM, assigns a FIP to it and pings to outside the cluster.'''

        if (('MX_GW_TEST' in os.environ) and (
                os.environ.get('MX_GW_TEST') == '1')):
            if len(self.connections.nova_h.get_hosts()) < 2:
                raise self.skipTest(
                    'Skipping Test. At least 2 compute node required to run the test')
            self.logger.info("Read the existing encap priority")
            existing_encap = self.connections.read_vrouter_config_encap()
            self.logger.info('Setting new Encap before continuing')
            config_id = self.connections.update_vrouter_config_encap(
                'MPLSoUDP', 'MPLSoGRE', 'VXLAN')
            self.logger.info('Created.UUID is %s' % (config_id))

            configured_encap_list = [
                unicode('MPLSoUDP'), unicode('MPLSoGRE'), unicode('VXLAN')]
            if existing_encap != configured_encap_list :
                self.addCleanup(self.connections.update_vrouter_config_encap, existing_encap[0], existing_encap[1], existing_encap[2])
            encap_list = self.connections.read_vrouter_config_encap()
            if configured_encap_list != encap_list:

                self.logger.error(
                    "Configured Encap Priority order is NOT matching with expected order. Configured: %s ,Expected: %s" %
                    (configured_encap_list, encap_list))
                assert False
            else:
                self.logger.info(
                    "Configured Encap Priority order is matching with expected order. Configured: %s ,Expected: %s" %
                    (configured_encap_list, encap_list))

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
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_name=fvn_name,
                    inputs=self.inputs,
                    subnets=fip_subnets,
                    router_asn=self.inputs.router_asn,
                    rt_number=mx_rt))
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
                    project_name=self.inputs.project_name,
                    inputs=self.inputs,
                    connections=self.connections,
                    pool_name=fip_pool_name,
                    vn_id=fvn_fixture.vn_id))
            assert fip_fixture.verify_on_setup()
            fip_id = fip_fixture.create_and_assoc_fip(
                fvn_fixture.vn_id, vm1_fixture.vm_id)
            assert fip_fixture.verify_fip(fip_id, vm1_fixture, fvn_fixture)
            routing_instance = fvn_fixture.ri_name

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
            vm1_fixture.wait_till_vm_is_up()
            # TODO Configure MX. Doing Manually For Now
            self.logger.info(
                "BGP Peer configuraion done and trying to outside the VN cluster")
            self.logger.info("Now trying to ping %s" % (self.inputs.public_host))
            self.tcpdump_start_on_all_compute()
            if not vm1_fixture.ping_with_certainty(
                    self.inputs.public_host,
                    count='15'):
                result = result and False
            comp_vm1_ip = vm1_fixture.vm_node_ip
            self.tcpdump_analyze_on_compute(comp_vm1_ip, 'GRE')
            fip_fixture.disassoc_and_delete_fip(fip_id)
            if not result:
                self.logger.error(
                    'Test  ping outside VN cluster from VM %s failed' %
                    (vm1_name))
                assert result
        else:
            self.logger.info(
                "Skipping Test. Env variable MX_TEST is not set. Skipping the test")
            raise self.skipTest(
                "Skipping Test. Env variable MX_TEST is not set. Skipping the test")

        return True
    # end test_encaps_mx_gateway

    @test.attr(type=[ 'serial', 'sanity' ])
    @preposttest_wrapper
    def test_apply_policy_fip_on_same_vn_gw_mx(self):
        '''A particular VN is configure with policy to talk accross VN's and FIP to access outside'''

        if (('MX_GW_TEST' in os.environ) and (
                os.environ.get('MX_GW_TEST') == '1')):

            if len(self.connections.nova_h.get_hosts()) < 2:
                self.logger.info(
                    "Skipping Test. At least 2 compute node required to run the test")
                raise self.skipTest(
                    'Skipping Test. At least 2 compute node required to run the test')
            self.logger.info("Read the existing encap priority")
            existing_encap = self.connections.read_vrouter_config_encap()

            self.logger.info('Setting new Encap before continuing')            
            config_id = self.connections.update_vrouter_config_encap(
                'MPLSoUDP', 'MPLSoGRE', 'VXLAN')
            self.logger.info('Created.UUID is %s' % (config_id))

            configured_encap_list = [
                unicode('MPLSoUDP'), unicode('MPLSoGRE'), unicode('VXLAN')]
            if existing_encap != configured_encap_list :
                self.addCleanup(self.connections.update_vrouter_config_encap, existing_encap[0], existing_encap[1], existing_encap[2])

            encap_list = self.connections.read_vrouter_config_encap()
            if configured_encap_list != encap_list:

                self.logger.error(
                    "Configured Encap Priority order is NOT matching with expected order. Configured: %s ,Expected: %s" %
                    (configured_encap_list, encap_list))
                assert False
            else:
                self.logger.info(
                    "Configured Encap Priority order is matching with expected order. Configured: %s ,Expected: %s" %
                    (configured_encap_list, encap_list))

            result = True
            fip_pool_name = self.inputs.fip_pool_name
            fvn_name = 'public100'
            fip_subnets = [self.inputs.fip_pool]
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

            # Get all compute host
            host_list = self.connections.nova_h.get_hosts()

            fvn_fixture = self.useFixture(
                VNFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_name=fvn_name,
                    inputs=self.inputs,
                    subnets=fip_subnets,
                    router_asn=self.inputs.router_asn,
                    rt_number=mx_rt))
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
                    vm_name=vm1_name,
                    node_name=host_list[0]))
            assert vm1_fixture.verify_on_setup()

            vn2_fixture = self.useFixture(
                VNFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_name=vn2_name,
                    inputs=self.inputs,
                    subnets=vn2_subnets))
            assert vn2_fixture.verify_on_setup()
            vm2_fixture = self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_obj=vn2_fixture.obj,
                    vm_name=vm2_name,
                    node_name=host_list[1]))
            assert vm2_fixture.verify_on_setup()

            # Fip
            fip_fixture = self.useFixture(
                FloatingIPFixture(
                    project_name=self.inputs.project_name,
                    inputs=self.inputs,
                    connections=self.connections,
                    pool_name=fip_pool_name,
                    vn_id=fvn_fixture.vn_id))
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

            policy1_fixture = self.useFixture(
                PolicyFixture(
                    policy_name=policy1_name,
                    rules_list=rules,
                    inputs=self.inputs,
                    connections=self.connections))
            policy2_fixture = self.useFixture(
                PolicyFixture(
                    policy_name=policy2_name,
                    rules_list=rev_rules,
                    inputs=self.inputs,
                    connections=self.connections))

            self.logger.info('Apply policy between VN %s and %s' %
                             (vn1_name, vn2_name))
            vn1_fixture.bind_policies(
                [policy1_fixture.policy_fq_name], vn1_fixture.vn_id)
            self.addCleanup(
                vn1_fixture.unbind_policies, vn1_fixture.vn_id, [
                    policy1_fixture.policy_fq_name])
            vn2_fixture.bind_policies(
                [policy2_fixture.policy_fq_name], vn2_fixture.vn_id)
            self.addCleanup(
                vn2_fixture.unbind_policies, vn2_fixture.vn_id, [
                    policy2_fixture.policy_fq_name])
            vm1_fixture.wait_till_vm_is_up()
            vm2_fixture.wait_till_vm_is_up()
            self.logger.info(
                'Checking connectivity within VNS cluster through Policy')
            self.logger.info('Ping from %s to %s' % (vm1_name, vm2_name))
            self.tcpdump_start_on_all_compute()
            if not vm1_fixture.ping_with_certainty(
                    vm2_fixture.vm_ip,
                    count='15'):
                result = result and False
            comp_vm1_ip = vm1_fixture.vm_node_ip
            comp_vm2_ip = vm2_fixture.vm_node_ip
            self.tcpdump_analyze_on_compute(comp_vm1_ip, 'UDP')
            self.tcpdump_analyze_on_compute(comp_vm2_ip, 'UDP')

            self.logger.info(
                'Checking connectivity outside VNS cluster through FIP')
            self.logger.info("Now trying to ping %s" % (self.inputs.public_host))
            self.tcpdump_start_on_all_compute()
            if not vm1_fixture.ping_with_certainty(
                    self.inputs.public_host,
                    count='15'):
                result = result and False
            comp_vm1_ip = vm1_fixture.vm_node_ip
            self.tcpdump_analyze_on_compute(comp_vm1_ip, 'GRE')
            if not result:
                self.logger.error(
                    'Test to verify the Traffic to Inside and Outside Virtual network cluster simaltaneiously failed')
                assert result
        else:
            self.logger.info(
                "Skipping Test. Env variable MX_TEST is not set. Skipping the test")
            raise self.skipTest(
                "Skipping Test. Env variable MX_TEST is not set. Skipping the test")

        return True
    # end test_apply_policy_fip_on_same_vn_gw_mx

    @test.attr(type='serial')
    @preposttest_wrapper
    def test_apply_policy_fip_vn_with_encaps_change_gw_mx(self):
        '''A particular VN is configured with policy to talk across VN's and FIP to access outside.The encapsulation prioritis set at the start of testcase are changed and verified '''

        if (('MX_GW_TEST' in os.environ) and (
                os.environ.get('MX_GW_TEST') == '1')):

            if len(self.connections.nova_h.get_hosts()) < 2:
                self.logger.info(
                    "Skipping Test. At least 2 compute node required to run the test")
                raise self.skipTest(
                    'Skipping Test. At least 2 compute node required to run the test')
            self.logger.info("Read the existing encap priority")
            existing_encap = self.connections.read_vrouter_config_encap()

            self.logger.info('Setting new Encap before continuing')

            config_id = self.connections.update_vrouter_config_encap(
                'MPLSoUDP', 'MPLSoGRE', 'VXLAN')
            self.logger.info('Created.UUID is %s' % (config_id))

            configured_encap_list = [
                unicode('MPLSoUDP'), unicode('MPLSoGRE'), unicode('VXLAN')]
            if existing_encap != configured_encap_list :
                self.addCleanup(self.connections.update_vrouter_config_encap, existing_encap[0], existing_encap[1], existing_encap[2])

            encap_list = self.connections.read_vrouter_config_encap()
            if configured_encap_list != encap_list:

                self.logger.error(
                    "Configured Encap Priority order is NOT matching with expected order. Configured: %s ,Expected: %s" %
                    (configured_encap_list, encap_list))
                assert False
            else:
                self.logger.info(
                    "Configured Encap Priority order is matching with expected order. Configured: %s ,Expected: %s" %
                    (configured_encap_list, encap_list))

            result = True
            fip_pool_name = self.inputs.fip_pool_name
            fvn_name = 'public100'
            fip_subnets = [self.inputs.fip_pool]
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

            # Get all compute host
            host_list = self.connections.nova_h.get_hosts()

            fvn_fixture = self.useFixture(
                VNFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_name=fvn_name,
                    inputs=self.inputs,
                    subnets=fip_subnets,
                    router_asn=self.inputs.router_asn,
                    rt_number=mx_rt))
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
                    vm_name=vm1_name,
                    node_name=host_list[0]))
            assert vm1_fixture.verify_on_setup()

            vn2_fixture = self.useFixture(
                VNFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_name=vn2_name,
                    inputs=self.inputs,
                    subnets=vn2_subnets))
            assert vn2_fixture.verify_on_setup()
            vm2_fixture = self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_obj=vn2_fixture.obj,
                    vm_name=vm2_name,
                    node_name=host_list[1]))
            assert vm2_fixture.verify_on_setup()

            # Fip
            fip_fixture = self.useFixture(
                FloatingIPFixture(
                    project_name=self.inputs.project_name,
                    inputs=self.inputs,
                    connections=self.connections,
                    pool_name=fip_pool_name,
                    vn_id=fvn_fixture.vn_id))
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

            policy1_fixture = self.useFixture(
                PolicyFixture(
                    policy_name=policy1_name,
                    rules_list=rules,
                    inputs=self.inputs,
                    connections=self.connections))
            policy2_fixture = self.useFixture(
                PolicyFixture(
                    policy_name=policy2_name,
                    rules_list=rev_rules,
                    inputs=self.inputs,
                    connections=self.connections))

            self.logger.info('Apply policy between VN %s and %s' %
                             (vn1_name, vn2_name))
            vn1_fixture.bind_policies(
                [policy1_fixture.policy_fq_name], vn1_fixture.vn_id)
            self.addCleanup(
                vn1_fixture.unbind_policies, vn1_fixture.vn_id, [
                    policy1_fixture.policy_fq_name])
            vn2_fixture.bind_policies(
                [policy2_fixture.policy_fq_name], vn2_fixture.vn_id)
            self.addCleanup(
                vn2_fixture.unbind_policies, vn2_fixture.vn_id, [
                    policy2_fixture.policy_fq_name])
            vm1_fixture.wait_till_vm_is_up()
            vm2_fixture.wait_till_vm_is_up()
            self.logger.info(
                'Checking connectivity within VNS cluster through Policy')
            self.logger.info('Ping from %s to %s' % (vm1_name, vm2_name))
            self.tcpdump_start_on_all_compute()
            if not vm1_fixture.ping_with_certainty(
                    vm2_fixture.vm_ip,
                    count='15'):
                result = result and False
            comp_vm1_ip = vm1_fixture.vm_node_ip
            comp_vm2_ip = vm2_fixture.vm_node_ip
            self.tcpdump_analyze_on_compute(comp_vm1_ip, 'UDP')
            self.tcpdump_analyze_on_compute(comp_vm2_ip, 'UDP')

            self.logger.info(
                'Checking connectivity outside VNS cluster through FIP')
            self.logger.info("Now trying to ping %s" % (self.inputs.public_host))
            self.tcpdump_start_on_all_compute()
            if not vm1_fixture.ping_with_certainty(
                    self.inputs.public_host,
                    count='15'):
                result = result and False
            comp_vm1_ip = vm1_fixture.vm_node_ip
            self.tcpdump_analyze_on_compute(comp_vm1_ip, 'GRE')
            if not result:
                self.logger.error(
                    'Test to verify the Traffic to Inside and Outside Virtual network cluster simaltaneiously failed')
                assert result
            self.logger.info('Now changing the encapsulation priorities')
            self.logger.info(
                'The new encapsulation will take effect once bug 1422 is fixed')
            res = self.connections.update_vrouter_config_encap(
                'MPLSoGRE', 'MPLSoUDP', 'VXLAN')
            self.logger.info('Updated.%s' % (res))
            self.logger.info(
                'Checking connectivity within VNS cluster through Policy')
            self.logger.info('Ping from %s to %s' % (vm1_name, vm2_name))
            self.tcpdump_start_on_all_compute()
            if not vm1_fixture.ping_with_certainty(
                    vm2_fixture.vm_ip,
                    count='15'):
                result = result and False
            comp_vm1_ip = vm1_fixture.vm_node_ip
            comp_vm2_ip = vm2_fixture.vm_node_ip
            self.tcpdump_analyze_on_compute(comp_vm1_ip, 'GRE')
            self.tcpdump_analyze_on_compute(comp_vm2_ip, 'GRE')

            self.logger.info(
                'Checking connectivity outside VNS cluster through FIP')
            self.logger.info("Now trying to ping %s" % (self.inputs.public_host))
            self.tcpdump_start_on_all_compute()
            if not vm1_fixture.ping_with_certainty(
                    self.inputs.public_host,
                    count='15'):
                result = result and False
            comp_vm1_ip = vm1_fixture.vm_node_ip
            self.tcpdump_analyze_on_compute(comp_vm1_ip, 'GRE')
            if not result:
                self.logger.error(
                    'Test to verify the Traffic to Inside and Outside Virtual network cluster simaltaneiously failed after changing the encapsulation')
                assert result

        else:
            self.logger.info(
                "Skipping Test. Env variable MX_TEST is not set. Skipping the test")
            raise self.skipTest(
                "Skipping Test. Env variable MX_TEST is not set. Skipping the test")
        return True
    # end test_apply_policy_fip_vn_with_encaps_change_gw_mx

# end TestEncapsulation
#
    def start_tcpdump(self, session, cmd):
        self.logger.info("Starting tcpdump to capture the packets.")
        result = execute_cmd(session, cmd, self.logger)
   # end start_tcpdump

    def stop_tcpdump(self, session):
        self.logger.info("Stopping any tcpdump process running")
        cmd = 'kill $(pidof tcpdump)'
        execute_cmd(session, cmd, self.logger)
        self.logger.info("Removing any encap-pcap files in /tmp")
        cmd = 'rm -f /tmp/encap*pcap'
        execute_cmd(session, cmd, self.logger)
    # end stop_tcpdump

    def tcpdump_start_on_all_compute(self):
        for compute_ip in self.inputs.compute_ips:
            compute_user = self.inputs.host_data[compute_ip]['username']
            compute_password = self.inputs.host_data[compute_ip]['password']
            session = ssh(compute_ip, compute_user, compute_password)
            self.stop_tcpdump(session)
            inspect_h = self.agent_inspect[compute_ip]
            comp_intf = inspect_h.get_vna_interface_by_type('eth')
            if len(comp_intf) == 1:
                comp_intf = comp_intf[0]
            self.logger.info('Agent interface name: %s' % comp_intf)
            pcap1 = '/tmp/encap-udp.pcap'
            pcap2 = '/tmp/encap-gre.pcap'
            pcap3 = '/tmp/encap-vxlan.pcap'
            cmd1 = 'tcpdump -ni %s udp port 51234 -w %s -s 0' % (
                comp_intf, pcap1)
            cmd_udp = "nohup " + cmd1 + " >& /dev/null < /dev/null &"
            cmd2 = 'tcpdump -ni %s proto 47 -w %s -s 0' % (comp_intf, pcap2)
            cmd_gre = "nohup " + cmd2 + " >& /dev/null < /dev/null &"
            cmd3 = 'tcpdump -ni %s dst port 4789 -w %s -s 0' % (
                comp_intf, pcap3)
            cmd_vxlan = "nohup " + cmd3 + " >& /dev/null < /dev/null &"

            self.start_tcpdump(session, cmd_udp)
            self.start_tcpdump(session, cmd_gre)
            self.start_tcpdump(session, cmd_vxlan)

    # end tcpdump_on_all_compute

    def tcpdump_stop_on_all_compute(self):
        sessions = {}
        for compute_ip in self.inputs.compute_ips:
            compute_user = self.inputs.host_data[compute_ip]['username']
            compute_password = self.inputs.host_data[compute_ip]['password']
            session = ssh(compute_ip, compute_user, compute_password)
            self.stop_tcpdump(session)

    # end tcpdump_on_all_compute

    def tcpdump_stop_on_compute(self, compute_ip):
        sessions = {}
        compute_user = self.inputs.host_data[compute_ip]['username']
        compute_password = self.inputs.host_data[compute_ip]['password']
        session = ssh(compute_ip, compute_user, compute_password)
        self.stop_tcpdump(session)

    def tcpdump_analyze_on_compute(
            self,
            comp_ip,
            pcaptype,
            vxlan_id=None,
            vlan_id=None):
        sleep(2)
        sessions = {}
        compute_user = self.inputs.host_data[comp_ip]['username']
        compute_password = self.inputs.host_data[comp_ip]['password']
        session = ssh(comp_ip, compute_user, compute_password)
        self.logger.info("Analyzing on compute node %s" % comp_ip)
        if pcaptype == 'UDP':
            pcaps1 = '/tmp/encap-udp.pcap'
            pcaps2 = '/tmp/encap-gre.pcap'
            cmd2 = 'tcpdump  -r %s | grep UDP |wc -l' % pcaps1
            out2, err = execute_cmd_out(session, cmd2, self.logger)
            cmd3 = 'tcpdump  -r %s | grep GRE | wc -l' % pcaps2
            out3, err = execute_cmd_out(session, cmd3, self.logger)
            count2 = int(out2.strip('\n'))
            count3 = int(out3.strip('\n'))
            if count2 != 0 and count3 == 0:
                self.logger.info(
                    "%s UDP encapsulated packets are seen and %s GRE encapsulated packets are seen as expected" %
                    (count2, count3))
                return True
            else:
                errmsg = "%s UDP encapsulated packets are seen and %s GRE encapsulated packets are seen.Not expected" % (
                    count2, count3)
                self.logger.error(errmsg)
                assert False, errmsg
        elif pcaptype == 'GRE':
            pcaps1 = '/tmp/encap-udp.pcap'
            pcaps2 = '/tmp/encap-gre.pcap'
            cmd2 = 'tcpdump  -r %s | grep UDP |wc -l' % pcaps1
            out2, err = execute_cmd_out(session, cmd2, self.logger)
            cmd3 = 'tcpdump  -r %s | grep GRE | wc -l' % pcaps2
            out3, err = execute_cmd_out(session, cmd3, self.logger)
            count2 = int(out2.strip('\n'))
            count3 = int(out3.strip('\n'))
            if count2 == 0 and count3 != 0:
                self.logger.info(
                    "%s GRE encapsulated packets are seen and %s UDP encapsulated packets are seen as expected" %
                    (count3, count2))
                # self.tcpdump_stop_on_all_compute()
                self.tcpdump_stop_on_compute(comp_ip)
                return True
            else:
                errmsg = "%s UDP encapsulated packets are seen and %s GRE encapsulated packets are seen.Not expected" % (
                    count2, count3)
                self.logger.error(errmsg)
                # self.tcpdump_stop_on_all_compute()
                self.tcpdump_stop_on_compute(comp_ip)
                assert False, errmsg

        elif pcaptype == 'VXLAN':
            pcaps1 = '/tmp/encap-udp.pcap'
            pcaps2 = '/tmp/encap-gre.pcap'
            pcaps3 = '/tmp/encap-vxlan.pcap'
            cmd2 = 'tcpdump  -r %s | grep UDP |wc -l' % pcaps1
            out2, err = execute_cmd_out(session, cmd2, self.logger)
            cmd3 = 'tcpdump  -r %s | grep GRE | wc -l' % pcaps2
            out3, err = execute_cmd_out(session, cmd3, self.logger)
            count2 = int(out2.strip('\n'))
            count3 = int(out3.strip('\n'))

            cmd3 = 'tcpdump  -r %s | grep UDP |wc -l' % pcaps3
            out3, err = execute_cmd_out(session, cmd3, self.logger)
            count = int(out3.strip('\n'))

            if count2 == 0 and count3 == 0 and count != 0:
                self.logger.info(
                    "%s GRE encapsulated packets are seen and %s UDP encapsulated packets are seen and %s vxlan packets are seen  as expected" %
                    (count3, count2, count))
                # self.tcpdump_stop_on_all_compute()
                if vxlan_id is not None:
                    cmd4 = 'tcpdump -AX -r %s | grep ' % pcaps3 + \
                        vxlan_id + ' |wc -l'
                    out4, err = execute_cmd_out(session, cmd4, self.logger)
                    count_vxlan_id = int(out4.strip('\n'))

                    if count_vxlan_id < count:
                        errmsg = "%s vxlan packet are seen with %s vxlan_id . Not Expected . " % (
                            count, count_vxlan_id)
                        self.tcpdump_stop_on_compute(comp_ip)
                        self.logger.error(errmsg)
                        assert False, errmsg
                    else:
                        self.logger.info(
                            "%s vxlan packets are seen with %s vxlan_id as expexted . " %
                            (count, count_vxlan_id))
                        self.tcpdump_stop_on_compute(comp_ip)
            else:
                errmsg = "%s UDP encapsulated packets are seen and %s GRE encapsulated packets are seen.Not expected, %s vxlan packet seen" % (
                    count2, count3, count)
                self.logger.error(errmsg)
                # self.tcpdump_stop_on_all_compute()
                self.tcpdump_stop_on_compute(comp_ip)
                assert False, errmsg
            if vlan_id is not None:
                cmd5 = 'tcpdump -AX -r %s | grep %s |wc -l' % (pcaps3, vlan_id)
                out5, err = execute_cmd_out(session, cmd5, self.logger)
                count_vlan_id = int(out5.strip('\n'))

                if count_vlan_id < count:
                    errmsg = "%s vxlan packet are seen with %s vlan_id . Not Expected . " % (
                        count, count_vlan_id)
                    self.logger.error(errmsg)
                    assert False, errmsg
                else:
                    self.logger.info(
                        "%s vxlan packets are seen with %s vlan_id as expexted . " %
                        (count, count_vlan_id))
        return True

#       return True
    # end tcpdump_analyze_on_compute
#
