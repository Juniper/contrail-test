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


class TestSanity_MX(base.FloatingIpBaseTest):

    @classmethod
    def setUpClass(cls):
        super(TestSanity_MX, cls).setUpClass()
    
    @classmethod
    def tearDownClass(cls):
        super(TestSanity_MX, cls).tearDownClass()

    def is_test_applicable(self):
        if os.environ.get('MX_GW_TEST') != '1':
            return (False, 'Skipping Test. Env variable MX_GW_TEST is not set')
        return (True, None)

    @test.attr(type=['mx_test', 'sanity', 'vcenter'])
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
        result = True
        fip_pool_name = self.inputs.fip_pool_name
        fvn_name = 'public'
        fip_subnets = [self.inputs.fip_pool]
        vm1_name = 'vm200'
        vn1_name = 'vn200'
        vn1_subnets = ['11.1.1.0/24']
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

        vm1_fixture.wait_till_vm_up()

        self.logger.info(
            "BGP Peer configuration done and trying to outside the VN cluster")
        self.logger.info("Now trying to ping %s" % (self.inputs.public_host))
        if not vm1_fixture.ping_with_certainty(self.inputs.public_host):
            result = result and False

        if not result:
            self.logger.error(
                'Test  ping outside VN cluster from VM %s failed' %
                (vm1_name))
            assert result

        # Removing further projects from floating IP pool. For cleanup
        self.logger.info('Removing project %s to FIP pool %s' %
                    (self.inputs.project_name, fip_pool_name))
        project_obj = self.public_vn_obj.fip_fixture.deassoc_project\
                    (self.inputs.project_name)

        return True
    # end test_mx_gateway

    @test.attr(type='mx_test')
    @preposttest_wrapper
    def test_apply_policy_fip_on_same_vn(self):
        '''A particular VN is configure with policy to talk accross VN's and FIP to access outside'''

        result = True
        fip_pool_name = self.inputs.fip_pool_name
        vm1_name = 'vm200'
        vn1_name = 'vn200'
        vn1_subnets = ['11.1.1.0/24']
        vm2_name = 'vm300'
        vn2_name = 'vn300'
        vn2_subnets = ['22.1.1.0/24']
        mx_rt = self.inputs.mx_rt

        # Get all compute host
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
           compute_1 = host_list[0]
           compute_2 = host_list[1]

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
                node_name=compute_1))
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
                node_name=compute_2))
        assert vm2_fixture.verify_on_setup()

        # Fip
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
        routing_instance = self.public_vn_obj.public_vn_fixture.ri_name

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
     
        vm1_fixture.wait_till_vm_up()
        vm2_fixture.wait_till_vm_up()

        self.logger.info(
            'Checking connectivity within VNS cluster through Policy')
        self.logger.info('Ping from %s to %s' % (vm1_name, vm2_name))
        if not vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip):
            result = result and False

        self.logger.info(
            'Checking connectivity outside VNS cluster through FIP')
        self.logger.info("Now trying to ping %s" %(self.inputs.public_host))
        if not vm1_fixture.ping_with_certainty(self.inputs.public_host):
            result = result and False

        if not result:
            self.logger.error(
                'Test to verify the Traffic to Inside and Outside Virtual network cluster simultaneously failed')
            assert result
        # Removing further projects from floating IP pool. For cleanup
        self.logger.info('Removing project %s to FIP pool %s' %
            (self.inputs.project_name, fip_pool_name))
        project_obj = self.public_vn_obj.fip_fixture.deassoc_project\
                    (self.inputs.project_name)

        return True
    # end test_apply_policy_fip_on_same_vn

    @test.attr(type='mx_test')
    @preposttest_wrapper
    def test_ftp_http_with_public_ip(self):
        '''Test FTP and HTTP traffic from public network.'''

        result = True
        fip_pool_name = self.inputs.fip_pool_name
        fip_subnets = [self.inputs.fip_pool]
        fvn_name = self.inputs.public_vn
        vm1_name = 'vm200'
        vn1_name = 'vn200'
        vn1_subnets = ['11.1.1.0/24']
        mx_rt = self.inputs.mx_rt

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
        # Adding further projects to floating IP.
        self.logger.info('Adding project %s to FIP pool %s' %
                         (self.inputs.project_name, fip_pool_name))
        project_obj = self.public_vn_obj.fip_fixture.assoc_project\
                        (self.inputs.project_name)

        fip_id = self.public_vn_obj.fip_fixture.create_and_assoc_fip(
            self.public_vn_obj.public_vn_fixture.vn_id, vm1_fixture.vm_id,project_obj)

        assert self.public_vn_obj.fip_fixture.verify_fip(fip_id, \
                vm1_fixture, self.public_vn_obj.public_vn_fixture)
        self.addCleanup(self.public_vn_obj.fip_fixture.disassoc_and_delete_fip, fip_id)
        vm1_fixture.wait_till_vm_up()
        self.logger.info(
            "BGP Peer configuration done and trying to ping outside the VN cluster")
        self.logger.info("Now trying to ping %s" %(self.inputs.public_host))
        if not vm1_fixture.ping_with_certainty(self.inputs.public_host):
            result = result and False

        self.logger.info('Testing FTP...Installing VIM In the VM via FTP')
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
        # Removing further projects from floating IP pool. For cleanup
        self.logger.info('Removing project %s to FIP pool %s' %
            (self.inputs.project_name, fip_pool_name))
        project_obj = self.public_vn_obj.fip_fixture.deassoc_project\
                    (self.inputs.project_name)

        return True
    # end test_ftp_http_with_public_ip

    @test.attr(type='mx_test')
    @preposttest_wrapper
    def test_fip_with_vm_in_2_vns(self):
        ''' Test to validate that awhen  VM is associated two VN and and diffrent floating IP allocated to them.
        '''
        fip_pool_name = self.inputs.fip_pool_name
        fip_subnets = [self.inputs.fip_pool]
        fip_pool_internal = 'some_pool2'
        fvn_name = self.inputs.public_vn
        router_name = self.inputs.ext_routers[0][0]
        router_ip = self.inputs.ext_routers[0][1]
        mx_rt = self.inputs.mx_rt
        vm1_name = 'vm_mine1'
        vn1_name = 'vn222'
        vn1_subnets = ['11.1.1.0/24']
        vn2_name = 'vn223'
        vn2_subnets = ['22.1.1.0/24']
        vn3_name = 'vn224'
        vn3_gateway = '22.1.1.1'
        vn3_subnets = ['33.1.1.0/24']
        vm2_name = 'vm_vn222'
        vm3_name = 'vm_vn223'
        vm4_name = 'vm_vn224'
        list_of_ips = []
        publicip_list = (self.inputs.fip_pool.split('/')[0].split('.'))
        publicip_list[3] = str(int(publicip_list[3]) + 6)
        publicip = ".".join(publicip_list)

        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn1_name,
                inputs=self.inputs,
                subnets=vn1_subnets))
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn2_name,
                inputs=self.inputs,
                subnets=vn2_subnets))
        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn3_name,
                inputs=self.inputs,
                subnets=vn3_subnets))

        host_rt = ['33.1.1.0/24', '0.0.0.0/0']
        vn2_fixture.add_host_routes(host_rt)

        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        assert vn3_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_objs=[
                    vn1_fixture.obj,
                    vn2_fixture.obj],
                vm_name=vm1_name,
                project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        vm2_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                vm_name=vm2_name,
                project_name=self.inputs.project_name))
        assert vm2_fixture.verify_on_setup()
        vm3_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_obj=vn2_fixture.obj,
                vm_name=vm3_name,
                project_name=self.inputs.project_name))
        assert vm3_fixture.verify_on_setup()
        vm4_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_obj=vn3_fixture.obj,
                vm_name=vm4_name,
                project_name=self.inputs.project_name))
        assert vm4_fixture.verify_on_setup()

        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        vm3_fixture.wait_till_vm_is_up()
        vm4_fixture.wait_till_vm_is_up()

        list_of_ips = vm1_fixture.vm_ips

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
        # Adding further projects to floating IP.
        self.logger.info('Adding project %s to FIP pool %s' %
                         (self.inputs.project_name, fip_pool_name))
        project_obj = self.public_vn_obj.fip_fixture.assoc_project\
                        (self.inputs.project_name)

        # FIP public
        self.logger.info(
            "Configuring FLoating IP in VM %s to communicate public network" %
            (vm1_name))
        vmi1_id = vm1_fixture.tap_intf[vn1_fixture.vn_fq_name]['uuid']
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name,
                vn_id=self.public_vn_obj.public_vn_fixture.vn_id))
        #assert fip_fixture.verify_on_setup()
        my_fip_name = 'fip'
        fvn_obj = self.vnc_lib.virtual_network_read(id=self.public_vn_obj.public_vn_fixture.vn_id)
        fip_pool_obj = FloatingIpPool(fip_pool_name, fvn_obj)
        fip_obj = FloatingIp(my_fip_name, fip_pool_obj, publicip, True)
        vm1_intf = self.vnc_lib.virtual_machine_interface_read(id=vmi1_id)
        # Read the project obj and set to the floating ip object.
        fip_obj.set_project(project_obj)
        fip_obj.add_virtual_machine_interface(vm1_intf)
        self.vnc_lib.floating_ip_create(fip_obj)
        self.addCleanup(self.vnc_lib.floating_ip_delete, fip_obj.fq_name)
        # TODO Need to add verify_fip()

        # FIP internal
        self.logger.info(
            "Configuring FLoating IP in VM %s to communicate inside VNS to other network" %
            (vm1_name))
        vmi2_id = vm1_fixture.tap_intf[vn2_fixture.vn_fq_name]['uuid']
        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_internal,
                vn_id=vn3_fixture.vn_id))
        assert fip_fixture1.verify_on_setup()
        my_fip_name1 = 'fip1'
        vn3_obj = self.vnc_lib.virtual_network_read(id=vn3_fixture.vn_id)
        fip_pool_obj1 = FloatingIpPool(fip_pool_internal, vn3_obj)
        fip_obj1 = FloatingIp(my_fip_name1, fip_pool_obj1, '33.1.1.241', True)
        # Read the project obj and set to the floating ip object.
        fip_obj1.set_project(project_obj)
        vm2_intf = self.vnc_lib.virtual_machine_interface_read(id=vmi2_id)
        fip_obj1.add_virtual_machine_interface(vm2_intf)
        self.vnc_lib.floating_ip_create(fip_obj1)
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
                if ((rec['sip'] == list_of_ips[1]) and (
                        rec['dip'] == vm4_fixture.vm_ip) and (rec['protocol'] == '1')):
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
        self.logger.info("Now trying to ping %s" % (self.inputs.public_host))
        if not vm1_fixture.ping_with_certainty(self.inputs.public_host):
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
                if ((rec['sip'] == list_of_ips[0]) and (
                        rec['dip'] == '10.206.255.2') and (rec['protocol'] == '1')):
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

        # Removing further projects from floating IP pool. For cleanup
        self.logger.info('Removing project %s to FIP pool %s' %
            (self.inputs.project_name, fip_pool_name))
        project_obj = self.public_vn_obj.fip_fixture.deassoc_project\
                    (self.inputs.project_name)

        if not result:
            self.logger.error(
                'Test test_fip_with_vm_in_2_vns Failed')
            assert result
        return True
    # end test_vm_add_delete_in_2_vns_chk_ping
