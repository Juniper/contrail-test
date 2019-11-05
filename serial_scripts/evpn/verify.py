from __future__ import print_function
from builtins import hex
from builtins import str
from builtins import range
from builtins import object
from time import sleep
import re
import os
from vn_test import *
from vm_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from policy_test import *
from contrail_fixtures import *
import random
import socket
from tcutils.tcpdump_utils import verify_tcpdump_count, search_in_pcap
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from fabric.operations import get, put
from string import Template


class VerifyEvpnCases(object):

    def verify_dns_disabled(self, encap):
        # Setting up default encapsulation
        self.logger.info('Setting new Encap before continuing')
        if (encap == 'gre'):
            self.update_encap_priority('gre')
        elif (encap == 'udp'):
            self.update_encap_priority('udp')
        elif (encap == 'vxlan'):
            self.update_encap_priority('vxlan')

        result = True
        host_list = self.connections.orch.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        compute_3 = host_list[0]

        if len(host_list) > 2:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
            compute_3 = host_list[2]

        elif len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
            compute_3 = host_list[1]

        (self.vn3_name, self.vn3_subnets) = ("EVPN-MGMT-VN", ["11.1.1.0/24"])
        (self.vn4_name, self.vn4_subnets) = ("EVPN-L2-VN", ["44.1.1.0/24"])

        dhcp_option_list = {'dhcp_option': [{'dhcp_option_value': '0.0.0.0', 'dhcp_option_name': '6'}]}

        vn3_fixture = self.useFixture(
                VNFixture(
                    project_name=self.inputs.project_name, connections=self.connections,
                    vn_name=self.vn3_name,option='contrail', inputs=self.inputs, subnets=self.vn3_subnets))

        vn4_fixture = self.useFixture(
                VNFixture(
                    project_name=self.inputs.project_name, connections=self.connections,
                    vn_name=self.vn4_name, option='contrail', inputs=self.inputs,
                    subnets=self.vn4_subnets, dhcp_option_list=dhcp_option_list,
                    enable_dhcp=False,forwarding_mode='l2'))
        assert vn3_fixture.verify_on_setup()
        assert vn4_fixture.verify_on_setup()
        self.connections.vnc_lib_fixture.set_rpf_mode(vn4_fixture.vn_fq_name, 'disable')

        vn_l2_vm1_name = 'testvm1'

        vm1_name = 'dhcp-server'
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu-dns-server',
                vm_name=vm1_name,
                node_name=compute_2))

        vm2_name = 'dnsserver'
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu-dns-server',
                vm_name=vm2_name,
                node_name=compute_3))

        vn_l2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm1_name,
                node_name=compute_1))

        # Wait till vm is up
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        assert vn_l2_vm1_fixture.wait_till_vm_is_up()

        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vn_l2_vm1_fixture.verify_on_setup()
        
        # Configure dhcp-server vm on eth1 and bring the intreface up
        # forcefully
        self.bringup_interface_forcefully(vm1_fixture)
        cmd_to_pass1 = ['ifconfig eth1 13.1.1.252 netmask 255.255.255.0']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)

        for i in range(3):
          cmd_to_pass2 = ['service isc-dhcp-server restart']
          vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True, timeout=60)
          output = vm1_fixture.return_output_cmd_dict['service isc-dhcp-server restart']
          if output and 'running' in output:
              break
          else:
              sleep(2)

        # Configure dns-server vm on eth1 and bring the intreface up
        # forcefully
        self.bringup_interface_forcefully(vm2_fixture)
        cmd_to_pass1 = ['ifconfig eth1 13.1.1.253 netmask 255.255.255.0']
        vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)

        for i in range(3):
          cmd_to_pass2 = ['service bind9 restart']
          vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True, timeout=60)
          output = vm2_fixture.return_output_cmd_dict['service bind9 restart']
          if output and 'Starting domain name service... bind9\r\n   ...done.' in output:
              break
          else:
              sleep(2)

        self.bringup_interface_forcefully(vn_l2_vm1_fixture)
        for i in range(2):
            self.logger.info("Retry %s for bringing up eth1 up" % (i))
            cmd_to_pass3 = ['dhclient eth1']
            vn_l2_vm1_fixture.run_cmd_on_vm(
                cmds=cmd_to_pass3, as_sudo=True, timeout=60)

            ret1 = self.verify_eth1_ip_from_vm(vn_l2_vm1_fixture)
            if ret1:
                break
            sleep(5)

        sleep(5)

        cmd_to_pass1 = ['dig @13.1.1.253 host1.test.com']
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        output = vn_l2_vm1_fixture.return_output_cmd_dict['dig @13.1.1.253 host1.test.com']
        if output and '13.1.1.251' in output:
           self.logger.info("Result for Dns Query is %s \n" %output)

        else:
           result = result and False
           self.logger.error('DNS Query for host1.test.com Failed Not Expected')

        cmd_to_pass1 = ['dig @13.1.1.253 juniper.net']
        for i in range(3):
            vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
            output = vn_l2_vm1_fixture.return_output_cmd_dict['dig @13.1.1.253 juniper.net']
            self.logger.info("Result for Dns Query is %s \n" %output)
            record = re.search(r'ANSWER SECTION:\r\njuniper.net.', output)
            if record is None:
               result = result and False
               self.logger.error('DNS Query for juniper.net Failed Not Expected')
               sleep(1)
            else:
               break

        cmd_to_pass1 = ['dig @13.1.1.253 www.google.com']
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        output = vn_l2_vm1_fixture.return_output_cmd_dict['dig @13.1.1.253 www.google.com']
        self.logger.info("Result for Dns Query is %s \n" %output)
        record = re.search(r'ANSWER SECTION:\r\nwww.google.com.', output)
        if record is None:
           result = result and False
           self.logger.error('DNS Query for www.google.com Failed Not Expected')

        cmd_to_pass1 = ['nslookup 13.1.1.251 13.1.1.253']
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        output = vn_l2_vm1_fixture.return_output_cmd_dict['nslookup 13.1.1.251 13.1.1.253']
        self.logger.info("Result for nslookup is %s \n" %output)
        if output and 'host1.test.com.1.1.13.in-addr.arpa.' in output:
           self.logger.info("nslookup for host1 succeeded %s \n"%output)

        else:
           result = result and False
           self.logger.error('nslookup for host1.test.com Failed Not Expected')

        return result


    def verify_l2_multicast_traffic(self, encap):
        '''Test ping to all hosts
        '''
        # Setting up default encapsulation
        self.logger.info('Setting new Encap before continuing')
        if (encap == 'gre'):
            self.update_encap_priority('gre')
        elif (encap == 'udp'):
            self.update_encap_priority('udp')
        elif (encap == 'vxlan'):
            self.update_encap_priority('vxlan')
        result = True
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        compute_3 = host_list[0]
        if len(host_list) > 2:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
            compute_3 = host_list[2]
        elif len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
            compute_3 = host_list[1]
             
        (self.vn3_name, self.vn3_subnets) = ("EVPN-MGMT-VN", ["33.1.1.0/24"])
        (self.vn4_name, self.vn4_subnets) = ("EVPN-L2-VN", ["44.1.1.0/24"])

        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn3_name,
                subnets=self.vn3_subnets))

        vn4_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn4_name,
                subnets=self.vn4_subnets,
                enable_dhcp=False,
                forwarding_mode='l2'))

        vn_l2_vm1_name = 'EVPN_VN_L2_VM1'
        vn_l2_vm2_name = 'EVPN_VN_L2_VM2'
        vn_l2_vm3_name = 'EVPN_VN_L2_VM3'

        vn_l2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm1_name,
                node_name=compute_1))
        vn_l2_vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm2_name,
                node_name=compute_2))
        vn_l2_vm3_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm3_name,
                node_name=compute_3))

        assert vn3_fixture.verify_on_setup()
        assert vn4_fixture.verify_on_setup()
        assert vn_l2_vm1_fixture.verify_on_setup()
        assert vn_l2_vm2_fixture.verify_on_setup()
        assert vn_l2_vm3_fixture.verify_on_setup()

        # Wait till vm is up
        assert vn_l2_vm1_fixture.wait_till_vm_is_up()
        assert vn_l2_vm2_fixture.wait_till_vm_is_up()
        assert vn_l2_vm3_fixture.wait_till_vm_is_up()
        assert not self.verify_eth1_ip_from_vm(vn_l2_vm1_fixture),'L2 VM got IP when dhcp is disabled'
        assert not self.verify_eth1_ip_from_vm(vn_l2_vm2_fixture),'L2 VM got IP when dhcp is disabled'
        assert not self.verify_eth1_ip_from_vm(vn_l2_vm3_fixture),'L2 VM got IP when dhcp is disabled'
        #send l2 multicast traffic
        self.mac1 = vn_l2_vm1_fixture.mac_addr[vn4_fixture.vn_fq_name]
        self.mac2 = '01:00:00:00:00:00'
        vm2_intf = vn_l2_vm2_fixture.tap_intf[vn4_fixture.vn_fq_name]['name']
        vm3_intf = vn_l2_vm3_fixture.tap_intf[vn4_fixture.vn_fq_name]['name']
        filters = 'ether src %s' %(self.mac1)
        session1,pcap1 = vn_l2_vm2_fixture.start_tcpdump(filters=filters,interface=vm2_intf)
        session2,pcap2 = vn_l2_vm3_fixture.start_tcpdump(filters=filters,interface=vm3_intf)
        self.logger.info('waiting to get tcpdump started')
        sleep(10)
        self.send_l2_traffic(vn_l2_vm1_fixture,iface='eth1')
        result1 = verify_tcpdump_count(self, session1, pcap1, exp_count=10,mac=self.mac2)
        result2 = verify_tcpdump_count(self, session2, pcap2, exp_count=10,mac=self.mac2)
        result = result1 and result2
        assert result,'Failed to send multicast traffic'
    # End verify_l2_multicast_traffic



    def verify_change_of_l2_vn_forwarding_mode(self, encap):
        '''Change the vn forwarding mode from l2 only to l2l3 and verify l2_l3 routes get updated
        '''
        # Setting up default encapsulation
        self.logger.info('Setting new Encap before continuing')
        if (encap == 'gre'):
            self.update_encap_priority('gre')
        elif (encap == 'udp'):
            self.update_encap_priority('udp')
        elif (encap == 'vxlan'):
            self.update_encap_priority('vxlan')

        result = True
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
        (self.vn3_name, self.vn3_subnets) = ("EVPN-MGMT-VN", ["33.1.1.0/24"])
        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn3_name,
                subnets=self.vn3_subnets))

        vn_l2_vm1_name = 'EVPN_VN_L2_VM1'
        vn_l2_vm2_name = 'EVPN_VN_L2_VM2'

        (self.vn1_name, self.vn1_subnets) = ("EVPN-Test-VN1", ["55.1.1.0/24"])

        self.vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn1_name,
                subnets=self.vn1_subnets,
                enable_dhcp=False,
                forwarding_mode='l2'))
        
        assert self.vn1_fixture.verify_on_setup()
        vn_l2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    self.vn1_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm1_name,
                node_name=compute_1))
        
        vn_l2_vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    self.vn1_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm2_name,
                node_name=compute_2))

        assert vn_l2_vm1_fixture.verify_on_setup()
        assert vn_l2_vm2_fixture.verify_on_setup()

        # Wait till vm is up
        assert vn_l2_vm1_fixture.wait_till_vm_is_up()
        assert vn_l2_vm2_fixture.wait_till_vm_is_up()
        assert not self.verify_eth1_ip_from_vm(vn_l2_vm1_fixture),'L2 VM got IP when dhcp is disabled'
        assert not self.verify_eth1_ip_from_vm(vn_l2_vm2_fixture),'L2 VM got IP when dhcp is disabled'
        vn1_subnet_id=self.vn1_fixture.get_subnets()[0]['id']
        vn1_dhcp_dict = {'enable_dhcp': True}
        self.vn1_fixture.update_subnet(vn1_subnet_id,vn1_dhcp_dict)
        self.logger.info(
            "Changing vn1 forwarding mode from l2 only to l2l3 followed by calling verify_on_setup for vms which checks if l3 routes are there or not ")
        self.vn1_fixture.add_forwarding_mode(
            project_fq_name=self.inputs.project_fq_name,
            vn_name=self.vn1_name,
            forwarding_mode='l2_l3')
        cmd='dhclient eth1'
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        assert self.verify_eth1_ip_from_vm(vn_l2_vm1_fixture),'VM did not got IP after enabling dhcp'
        assert self.verify_eth1_ip_from_vm(vn_l2_vm2_fixture),'VM did not got IP after enabling dhcp'
        assert self.vn1_fixture.verify_on_setup()
        assert vn_l2_vm1_fixture.verify_on_setup()
        assert vn_l2_vm2_fixture.verify_on_setup()
        #removing ipv6 verification
        #send l3 only traffic and verify
        self.vn_l2_vm1_ip = vn_l2_vm1_fixture.vm_ip_dict[self.vn1_fixture.vn_fq_name][0]
        self.vn_l2_vm2_ip =  vn_l2_vm2_fixture.vm_ip_dict[self.vn1_fixture.vn_fq_name][0]
        filters = '\'(src host %s and dst host %s and not arp)\'' \
                    % (self.vn_l2_vm1_ip, self.vn_l2_vm2_ip)
        tap_intf = vn_l2_vm2_fixture.tap_intf[self.vn1_fixture.vn_fq_name]['name']
        session, pcap = vn_l2_vm2_fixture.start_tcpdump(filters = filters,interface = tap_intf)
        sleep(20)
        self.send_l3_traffic(vn_l2_vm1_fixture)
        assert verify_tcpdump_count(self,session, pcap, raw_count=True, exp_count=10)
        
        #send l2 traffic and verify
        self.mac1=vn_l2_vm1_fixture.mac_addr[self.vn1_fixture.vn_fq_name]
        self.mac2=vn_l2_vm2_fixture.mac_addr[self.vn1_fixture.vn_fq_name]
        filters = 'ether src %s' %(self.mac1)
        tap_intf = vn_l2_vm2_fixture.tap_intf[self.vn1_fixture.vn_fq_name]['name']
        session,pcap = vn_l2_vm2_fixture.start_tcpdump(filters=filters,interface=tap_intf)
        sleep(20)
        self.send_l2_traffic(vn_l2_vm1_fixture,iface='eth1')
        result = verify_tcpdump_count(self, session, pcap, exp_count=10,mac=self.mac2)

        return result
    # End verify_change_of_l2_vn_forwarding_mode

    def verify_change_of_l2l3_vn_forwarding_mode(self, encap):
        '''Change the vn forwarding mode from l2l3 only to l2 and verify l3 routes gets deleted and check with l2 traffic
        '''
        # Setting up default encapsulation
        self.logger.info('Setting new Encap before continuing')
        if (encap == 'gre'):
            self.update_encap_priority('gre')
        elif (encap == 'udp'):
            self.update_encap_priority('udp')
        elif (encap == 'vxlan'):
            self.update_encap_priority('vxlan')

        result = True
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
        (self.vn3_name, self.vn3_subnets) = ("EVPN-MGMT-VN", ["33.1.1.0/24"])
        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn3_name,
                subnets=self.vn3_subnets))

        vn_l2_vm1_name = 'EVPN_VN_L2_VM1'
        vn_l2_vm2_name = 'EVPN_VN_L2_VM2'

        (self.vn1_name, self.vn1_subnets) = ("EVPN-Test-VN1", ["55.1.1.0/24"])

        self.vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn1_name,
                subnets=self.vn1_subnets))
        assert self.vn1_fixture.verify_on_setup()
        vn_l2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    self.vn1_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm1_name,
                node_name=compute_1))
        vn_l2_vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    self.vn1_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm2_name,
                node_name=compute_2))

        assert vn_l2_vm1_fixture.verify_on_setup()
        assert vn_l2_vm2_fixture.verify_on_setup()

        # Wait till vm is up
        assert vn_l2_vm1_fixture.wait_till_vm_is_up()
        assert vn_l2_vm2_fixture.wait_till_vm_is_up()
        vn1_subnet_id=self.vn1_fixture.get_subnets()[0]['id']
        cmd = 'ip addr flush dev eth1'
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True, timeout=60)
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True, timeout=60)
        vn1_dhcp_dict = {'enable_dhcp': False}
        self.vn1_fixture.update_subnet(vn1_subnet_id,vn1_dhcp_dict)
        self.logger.info(
            "Changing vn1 forwarding mode from l2l3 to l2 only  followed by calling verify_on_setup for vms which checks l2 routes and explicity check l3 routes are  removed  ")
        self.vn1_fixture.add_forwarding_mode(
            project_fq_name=self.inputs.project_fq_name,
            vn_name=self.vn1_name,
            forwarding_mode='l2')
        cmd = 'dhclient eth1'
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True, timeout=10)
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True, timeout=10)
        assert not self.verify_eth1_ip_from_vm(vn_l2_vm1_fixture),'L2 VM got IP when dhcp is disabled'
        assert not self.verify_eth1_ip_from_vm(vn_l2_vm2_fixture),'L2 VM got IP when dhcp is disabled'
        assert self.vn1_fixture.verify_on_setup()
        assert vn_l2_vm1_fixture.verify_on_setup()
        assert vn_l2_vm2_fixture.verify_on_setup()
                       
        #send l2 traffic and verify
        self.mac1=vn_l2_vm1_fixture.mac_addr[self.vn1_fixture.vn_fq_name]
        self.mac2=vn_l2_vm2_fixture.mac_addr[self.vn1_fixture.vn_fq_name]
        filters = 'ether src %s' %(self.mac1)
        tap_intf = vn_l2_vm2_fixture.tap_intf[self.vn1_fixture.vn_fq_name]['name']
        session,pcap = vn_l2_vm2_fixture.start_tcpdump(filters=filters,interface=tap_intf)
        self.logger.info('waiting to get tcpdump started')
        sleep(20)
        self.send_l2_traffic(vn_l2_vm1_fixture,iface='eth1')
        result = verify_tcpdump_count(self, session, pcap, exp_count=10,mac=self.mac2)
        
        #for bug-id 1514703
        #check ping working between l2 vms
        #assert vn_l2_vm1_fixture.ping_with_certainty(dst_vm_fixture=vn_l2_vm2_fixture, 
        #                                      vn_fq_name=self.vn1_fixture.vn_fq_name)
        
        return result
    # End verify_change_of_l2l3_vn_forwarding_mode

    def verify_change_of_l3_vn_forwarding_mode(self, encap):
        '''Change the vn forwarding mode from l2_l3  to l3_only and verify l3 mode 
        '''
        # Setting up default encapsulation
        self.logger.info('Setting new Encap before continuing')
        if (encap == 'gre'):
            self.update_encap_priority('gre')
        elif (encap == 'udp'):
            self.update_encap_priority('udp')
        elif (encap == 'vxlan'):
            self.update_encap_priority('vxlan')

        result = True
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
        (self.vn3_name, self.vn3_subnets) = ("EVPN-MGMT-VN", ["33.1.1.0/24"])
        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn3_name,
                subnets=self.vn3_subnets))

        vn_l2_vm1_name = 'EVPN_VN_L2_VM1'
        vn_l2_vm2_name = 'EVPN_VN_L2_VM2'

        (self.vn1_name, self.vn1_subnets) = ("EVPN-Test-VN1", ["55.1.1.0/24"])

        self.vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn1_name,
                subnets=self.vn1_subnets))
        assert self.vn1_fixture.verify_on_setup()
        vn_l2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    self.vn1_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm1_name,
                node_name=compute_1))
        vn_l2_vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    self.vn1_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm2_name,
                node_name=compute_2))

        assert vn_l2_vm1_fixture.verify_on_setup()
        assert vn_l2_vm2_fixture.verify_on_setup()

        # Wait till vm is up
        assert vn_l2_vm1_fixture.wait_till_vm_is_up()
        assert vn_l2_vm2_fixture.wait_till_vm_is_up()
        self.logger.info(
            "Changing vn1 forwarding mode from l2l3 to l3 only  followed by calling verify_on_setup ")
        self.vn1_fixture.add_forwarding_mode(
            project_fq_name=self.inputs.project_fq_name,
            vn_name=self.vn1_name,
            forwarding_mode='l3')
        assert self.vn1_fixture.verify_on_setup()
        assert vn_l2_vm1_fixture.verify_on_setup()
        assert vn_l2_vm2_fixture.verify_on_setup()
        
        #send l3 only traffic and verify
        self.vn_l2_vm1_ip = vn_l2_vm1_fixture.vm_ip_dict[self.vn1_fixture.vn_fq_name][0]
        self.vn_l2_vm2_ip =  vn_l2_vm2_fixture.vm_ip_dict[self.vn1_fixture.vn_fq_name][0]
        filters = '\'(src host %s and dst host %s and not arp)\'' \
                    % (self.vn_l2_vm1_ip, self.vn_l2_vm2_ip)
        tap_intf = vn_l2_vm2_fixture.tap_intf[self.vn1_fixture.vn_fq_name]['name']
        session, pcap = vn_l2_vm2_fixture.start_tcpdump(filters = filters,interface = tap_intf)
        sleep(10)
        output = self.send_l3_traffic(vn_l2_vm1_fixture)
        assert verify_tcpdump_count(self,session, pcap,raw_count=True, exp_count=10)
        
        return result
    
    # End verify_change_of_l3_vn_forwarding_mode

    def get_matching_vrf(self, vrf_objs, vrf_name):
        return [x for x in vrf_objs if x['name'] == vrf_name][0]

    def verify_vxlan_mode_with_configured_vxlan_id_l2_vn(self):
        ''' Configure vxlan_id explicitly with vn's forwarding mode as l2 and send traffic between vm's using this interface and check traffic is coming with
            configured vxlan_id
        '''
        encap = 'vxlan'
        # Setting up default encapsulation
        self.logger.info('Setting new Encap before continuing')
        self.update_encap_priority(encap)
        result = True
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
            
        (self.vn3_name, self.vn3_subnets) = ("EVPN-MGMT-VN", ["33.1.1.0/24"])
        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn3_name,
                subnets=self.vn3_subnets))

        vn_l2_vm1_name = 'EVPN_VN_L2_VM1'
        vn_l2_vm2_name = 'EVPN_VN_L2_VM2'

        (self.vn1_name, self.vn1_subnets) = ("EVPN-Test-VN1", ["55.1.1.0/24"])
        # Randomly choose a vxlan_id choosing between 1 and 255 for this test
        # case
        vxlan_random_id = random.randint(1, 255)
        vxlan_hex_id = hex(vxlan_random_id).split('x')[1]
        vxlan_hex_id = vxlan_hex_id + '00'
        self.vxlan_id = str(vxlan_random_id)

        self.connections.vnc_lib_fixture.set_vxlan_mode('configured')
        self.addCleanup(self.connections.vnc_lib_fixture.set_vxlan_mode,
            vxlan_mode='automatic')
        self.vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn1_name,
                subnets=self.vn1_subnets,
                vxlan_id=self.vxlan_id,
                enable_dhcp=False,
                forwarding_mode='l2'))
        assert self.vn1_fixture.verify_on_setup()

        vn_l2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    self.vn1_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm1_name,
                node_name=compute_1))
        vn_l2_vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    self.vn1_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm2_name,
                node_name=compute_2))

        assert vn3_fixture.verify_on_setup()
        assert vn_l2_vm1_fixture.verify_on_setup()
        assert vn_l2_vm2_fixture.verify_on_setup()
        
        # Verify that configured vxlan_id shows up in agent introspect
        for compute_ip in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[compute_ip]
            vn = inspect_h.get_vna_vn(vn_name=self.vn1_fixture.vn_name, project=self.inputs.project_name)
            if vn is None:
                continue
            agent_vrf_objs = inspect_h.get_vna_vrf_objs(
                vn_name=self.vn1_fixture.vn_name, project=self.inputs.project_name)
            agent_vrf_obj = self.get_matching_vrf(
                agent_vrf_objs['vrf_list'], self.vn1_fixture.vrf_name)
            agent_vrf_id = agent_vrf_obj['ucindex']
            agent_path_local_vm = inspect_h.get_vna_layer2_route(
                vrf_id=agent_vrf_id, mac='ff:ff:ff:ff:ff:ff')
            agent_path_vn_l2_vm1 = inspect_h.get_vna_layer2_route(
                vrf_id=agent_vrf_id,
                mac=vn_l2_vm1_fixture.mac_addr[
                    self.vn1_fixture.vn_fq_name])
            agent_path_vn_l2_vm2 = inspect_h.get_vna_layer2_route(
                vrf_id=agent_vrf_id,
                mac=vn_l2_vm2_fixture.mac_addr[
                    self.vn1_fixture.vn_fq_name])
            if agent_path_local_vm['routes'][0][
                    'path_list'][0]['vxlan_id'] != self.vxlan_id:
                result = False
                assert result, 'Failed to configure vxlan_id problem with local vm path'
            if agent_path_vn_l2_vm1['routes'][0][
                    'path_list'][0]['vxlan_id'] != self.vxlan_id:
                result = False
                assert result, 'Failed to configure vxlan_id problem with route for %s' + \
                    vn_l2_vm1_name
            if agent_path_vn_l2_vm2['routes'][0][
                    'path_list'][0]['vxlan_id'] != self.vxlan_id:
                result = False
                assert result, 'Failed to configure vxlan_id problem with route for %s' + \
                    vn_l2_vm1_name
            self.logger.info(
                'vxlan_id shown in agent introspect %s ' %
                (agent_path_local_vm['routes'][0]['path_list'][0]['vxlan_id']))

        # Wait till vm is up
        assert vn_l2_vm1_fixture.wait_till_vm_is_up()
        assert vn_l2_vm2_fixture.wait_till_vm_is_up()
        #send l2 traffic and verify
        self.mac1=vn_l2_vm1_fixture.mac_addr[self.vn1_fixture.vn_fq_name]
        self.mac2=vn_l2_vm2_fixture.mac_addr[self.vn1_fixture.vn_fq_name]
        filters = 'ether src %s' %(self.mac1)
        tap_intf = vn_l2_vm2_fixture.tap_intf[self.vn1_fixture.vn_fq_name]['name']
        self.tcpdump_start_on_all_compute()
        session,pcap = vn_l2_vm2_fixture.start_tcpdump(filters=filters,interface=tap_intf)
        self.logger.info('waiting to get tcpdump started')
        sleep(10)
        self.send_l2_traffic(vn_l2_vm1_fixture,iface='eth1')
        result = verify_tcpdump_count(self, session, pcap, exp_count=10,mac=self.mac2)
        comp_vm1_ip = vn_l2_vm1_fixture.vm_node_ip
        comp_vm2_ip = vn_l2_vm2_fixture.vm_node_ip

        # Pad vxlan_hex_id to length of 4 and grep it in tcpdump
        if vxlan_random_id < 15:
            vxlan_hex_id = '0' + vxlan_hex_id
        self.tcpdump_analyze_on_compute(
            comp_vm1_ip, encap.upper(), vxlan_id=vxlan_hex_id)
        self.tcpdump_analyze_on_compute(
            comp_vm2_ip, encap.upper(), vxlan_id=vxlan_hex_id)
        self.tcpdump_stop_on_all_compute()

        return result
    # End verify_vxlan_mode_with_configured_vxlan_id_l2_vn

    def verify_vxlan_mode_with_configured_vxlan_id_l2l3_vn(self):
        ''' Configure vxlan_id explicitly with vn's forwarding mode as l2l3, send traffic and check if traffic is coming with
            configured vxlan_id
        '''
        encap = 'vxlan'
        # Setting up default encapsulation
        self.update_encap_priority(encap)

        result = True
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]

        vn_l2_vm1_name = 'EVPN_VN_L2_VM1'
        vn_l2_vm2_name = 'EVPN_VN_L2_VM2'

        (self.vn1_name, self.vn1_subnets) = ("EVPN-Test-VN1", ["55.1.1.0/24"])
        # Randomly choose a vxlan_id choosing between 1 and 255 for this test
        # case
        vxlan_random_id = random.randint(1, 255)
        vxlan_hex_id = hex(vxlan_random_id).split('x')[1]
        vxlan_hex_id = vxlan_hex_id + '00'
        self.vxlan_id = str(vxlan_random_id)

        self.connections.vnc_lib_fixture.set_vxlan_mode('configured')
        self.addCleanup(self.connections.vnc_lib_fixture.set_vxlan_mode,
            vxlan_mode='automatic')
        self.vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn1_name,
                subnets=self.vn1_subnets,
                vxlan_id=self.vxlan_id))
        assert self.vn1_fixture.verify_on_setup()

        vn_l2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=self.vn1_fixture.obj,
                image_name='ubuntu',
                vm_name=vn_l2_vm1_name,
                node_name=compute_1))
        vn_l2_vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=self.vn1_fixture.obj,
                image_name='ubuntu',
                vm_name=vn_l2_vm2_name,
                node_name=compute_2))

        assert vn_l2_vm1_fixture.verify_on_setup()
        assert vn_l2_vm2_fixture.verify_on_setup()
        # Verify that configured vxlan_id shows up in agent introspect
        for compute_ip in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[compute_ip]
            vn = inspect_h.get_vna_vn(vn_name=self.vn1_fixture.vn_name, project=self.inputs.project_name)
            if vn is None:
                continue
            agent_vrf_objs = inspect_h.get_vna_vrf_objs(
                vn_name=self.vn1_fixture.vn_name, project=self.inputs.project_name)
            agent_vrf_obj = self.get_matching_vrf(
                agent_vrf_objs['vrf_list'], self.vn1_fixture.vrf_name)
            agent_vrf_id = agent_vrf_obj['ucindex']
            agent_path_local_vm = inspect_h.get_vna_layer2_route(
                vrf_id=agent_vrf_id, mac='ff:ff:ff:ff:ff:ff')
            agent_path_vn_l2_vm1 = inspect_h.get_vna_layer2_route(
                vrf_id=agent_vrf_id,
                mac=vn_l2_vm1_fixture.mac_addr[
                    self.vn1_fixture.vn_fq_name])
            agent_path_vn_l2_vm2 = inspect_h.get_vna_layer2_route(
                vrf_id=agent_vrf_id,
                mac=vn_l2_vm2_fixture.mac_addr[
                    self.vn1_fixture.vn_fq_name])
            if agent_path_local_vm['routes'][0][
                    'path_list'][0]['vxlan_id'] != self.vxlan_id:
                result = False
                assert result, 'Failed to configure vxlan_id problem with local vm path'
            if agent_path_vn_l2_vm1['routes'][0][
                    'path_list'][0]['vxlan_id'] != self.vxlan_id:
                result = False
                assert result, 'Failed to configure vxlan_id problem with route for %s' + \
                    vn_l2_vm1_name
            if agent_path_vn_l2_vm2['routes'][0][
                    'path_list'][0]['vxlan_id'] != self.vxlan_id:
                result = False
                assert result, 'Failed to configure vxlan_id problem with route for %s' + \
                    vn_l2_vm1_name
            self.logger.info(
                'vxlan_id shown in agent introspect %s ' %
                (agent_path_local_vm['routes'][0]['path_list'][0]['vxlan_id']))

        # Wait till vm is up
        assert vn_l2_vm1_fixture.wait_till_vm_is_up()
        assert vn_l2_vm2_fixture.wait_till_vm_is_up()
        #removing ipv6 verification
        #send l3 only traffic and verify
        self.vn_l2_vm1_ip = vn_l2_vm1_fixture.vm_ip_dict[self.vn1_fixture.vn_fq_name][0]
        self.vn_l2_vm2_ip =  vn_l2_vm2_fixture.vm_ip_dict[self.vn1_fixture.vn_fq_name][0]
        filters = '\'(src host %s and dst host %s and not arp)\'' \
                    % (self.vn_l2_vm1_ip, self.vn_l2_vm2_ip)
        tap_intf = vn_l2_vm2_fixture.tap_intf[self.vn1_fixture.vn_fq_name]['name']
        self.tcpdump_start_on_all_compute()
        session, pcap = vn_l2_vm2_fixture.start_tcpdump(filters = filters,interface = tap_intf)
        sleep(10)
        self.send_l3_traffic(vn_l2_vm1_fixture)
        assert verify_tcpdump_count(self,session, pcap, raw_count=True, exp_count=10)
        comp_vm1_ip = vn_l2_vm1_fixture.vm_node_ip
        comp_vm2_ip = vn_l2_vm2_fixture.vm_node_ip
        
        # Pad vxlan_hex_id to length of 4 and grep it in tcpdump
        if vxlan_random_id < 15:
           vxlan_hex_id = '0' + vxlan_hex_id
        self.tcpdump_analyze_on_compute(
            comp_vm1_ip, encap.upper(), vxlan_id=vxlan_hex_id)
        self.tcpdump_analyze_on_compute(
            comp_vm2_ip, encap.upper(), vxlan_id=vxlan_hex_id)
        self.tcpdump_stop_on_all_compute()

        return result
    # end verify_vxlan_mode_with_configured_vxlan_id_l2l3_vn

    def get_matching_vrf(self, vrf_objs, vrf_name):
        return [x for x in vrf_objs if x['name'] == vrf_name][0]
  
    def verify_l2_vm_file_trf_by_scp(self, encap):
        '''Description: Test to validate File Transfer using scp between VMs. Files of different sizes. L2 forwarding mode is used for scp.
        '''
        # Setting up default encapsulation
        self.logger.info('Setting new Encap before continuing')
        if (encap == 'gre'):
            self.update_encap_priority('gre')
        elif (encap == 'udp'):
            self.update_encap_priority('udp')
        elif (encap == 'vxlan'):
            self.update_encap_priority('vxlan')

        result = True
        host_list = self.connections.orch.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        compute_3 = host_list[0]
        if len(host_list) > 2:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
            compute_3 = host_list[2]
        elif len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
            compute_3 = host_list[1]

        (self.vn3_name, self.vn3_subnets) = ("EVPN-MGMT-VN", ["11.1.1.0/24"])
        (self.vn4_name, self.vn4_subnets) = ("EVPN-L2-VN", ["44.1.1.0/24"])

        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn3_name,
                subnets=self.vn3_subnets))

        vn4_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn4_name,
                subnets=self.vn4_subnets,
                enable_dhcp=False,
                forwarding_mode='l2'
                ))

        self.connections.vnc_lib_fixture.set_rpf_mode(vn4_fixture.vn_fq_name, 'disable')

        vn_l2_vm1_name = 'EVPN_VN_L2_VM1'
        vn_l2_vm2_name = 'EVPN_VN_L2_VM2'

        vm1_name = 'dhcp-server-vm'
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                flavor='contrail_flavor_large',
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu-dhcp-server',
                vm_name=vm1_name,
                node_name=compute_1))

        vn_l2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm1_name,
                node_name=compute_2))
        vn_l2_vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm2_name,
                node_name=compute_3))

        # Wait till vm is up
        assert vm1_fixture.wait_till_vm_is_up()
        assert vn_l2_vm1_fixture.wait_till_vm_is_up()
        assert vn_l2_vm2_fixture.wait_till_vm_is_up()

        assert vn3_fixture.verify_on_setup()
        assert vn4_fixture.verify_on_setup()
        assert vm1_fixture.verify_on_setup()
        assert vn_l2_vm1_fixture.verify_on_setup()
        assert vn_l2_vm2_fixture.verify_on_setup()
        
        # Configure dhcp-server vm on eth1 and bring the intreface up
        # forcefully
        self.bringup_interface_forcefully(vm1_fixture)
        cmd_to_pass1 = ['ifconfig eth1 13.1.1.253 netmask 255.255.255.0']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
       
        for i in range(3):
          cmd_to_pass2 = ['service isc-dhcp-server restart']
          vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True, timeout=60)
          output = vm1_fixture.return_output_cmd_dict['service isc-dhcp-server restart']
          if output and 'running' in output:
              break
          else:
              sleep(2)

        self.bringup_interface_forcefully(vn_l2_vm1_fixture)
        self.bringup_interface_forcefully(vn_l2_vm2_fixture)
        sleep(10)

        for i in range(2):
            self.logger.info("Retry %s for bringing up eth1 up" % (i))
            cmd_to_pass3 = ['dhclient eth1']
            vn_l2_vm1_fixture.run_cmd_on_vm(
                cmds=cmd_to_pass3, as_sudo=True, timeout=60)

            ret1 = self.verify_eth1_ip_from_vm(vn_l2_vm1_fixture)
            cmd_to_pass4 = ['dhclient eth1']
            vn_l2_vm2_fixture.run_cmd_on_vm(
                cmds=cmd_to_pass4, as_sudo=True, timeout=60)

            ret2 = self.verify_eth1_ip_from_vm(vn_l2_vm2_fixture)
            if ret1 and ret2:
                break
            sleep(5)
        i = 'ifconfig eth1'
        cmd_to_pass5 = [i]
        out = vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass5, as_sudo=True, timeout=60)
        output = vn_l2_vm2_fixture.return_output_cmd_dict[i]
        match = re.search('inet addr:(.+?)  Bcast:', output)

        if match:
            dest_vm_ip = match.group(1)
        valid_ip = re.search('13.1.1.(.*)', output)
        assert valid_ip, 'failed to get ip from 13.1.1.0 subnet as configured in dhcp vm'
        file_sizes = ['1350', '3000']
        for size in file_sizes:
            self.logger.info("-" * 80)
            self.logger.info("FILE SIZE = %sB" % size)
            self.logger.info("-" * 80)

            self.logger.info(
                'Transferring the file from %s to %s using scp' %
                (vn_l2_vm1_fixture.vm_name, vn_l2_vm2_fixture.vm_name))
            filename = 'testfile'

            # Create file
            cmd = 'dd bs=%s count=1 if=/dev/zero of=%s' % (size, filename)
            vn_l2_vm1_fixture.run_cmd_on_vm(cmds=[cmd], timeout=60)

            # Copy key
            vn_l2_vm2_fixture.run_cmd_on_vm(
                cmds=['cp -f ~root/.ssh/authorized_keys ~/.ssh/'],
                as_sudo=True, timeout=60)
            # Scp file from EVPN_VN_L2_VM1 to EVPN_VN_L2_VM2 using
            # EVPN_VN_L2_VM2 vm's eth1 interface ip
            vn_l2_vm1_fixture.scp_file_to_vm(filename, vm_ip=dest_vm_ip)
            vn_l2_vm1_fixture.run_cmd_on_vm(cmds=['sync'], as_sudo=True, timeout=60)
            # Verify if file size is same in destination vm
            out_dict = vn_l2_vm2_fixture.run_cmd_on_vm(
                cmds=['ls -l %s' % (filename)], timeout=60)
            if size in list(out_dict.values())[0]:
                self.logger.info('File of size %s is trasferred successfully to \
                    %s by scp ' % (size, dest_vm_ip))
            else:
                self.logger.warn('File of size %s is not trasferred fine to %s \
                    by scp !! Pls check logs' % (size, dest_vm_ip))
                result = False
                assert result
                
        self.tcpdump_stop_on_all_compute()
        return result
    
    @retry(delay=2, tries=5)
    def verify_eth1_ip_from_vm(self, vm_fix):
        i = 'ifconfig eth1'
        cmd_to_pass5 = [i]
        out = vm_fix.run_cmd_on_vm(cmds=cmd_to_pass5, as_sudo=True, timeout=60)
        output = vm_fix.return_output_cmd_dict[i]
        match = re.search('inet addr:(.+?)  Bcast:', output)
        if match:
           return True
        else:
           return False

    def verify_l2_vm_file_trf_by_tftp(self, encap):
        '''Description: Test to validate File Transfer using tftp between VMs. Files of different sizes. L2 forwarding mode is used for tftp.
        '''
        # Setting up default encapsulation
        self.logger.info('Setting new Encap before continuing')
        if (encap == 'gre'):
            self.update_encap_priority('gre')
        elif (encap == 'udp'):
            self.update_encap_priority('udp')
        elif (encap == 'vxlan'):
            self.update_encap_priority('vxlan')

        result = True
        host_list = self.connections.orch.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        compute_3 = host_list[0]
        if len(host_list) > 2:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
            compute_3 = host_list[2]
        elif len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
            compute_3 = host_list[1]

        (self.vn3_name, self.vn3_subnets) = ("EVPN-MGMT-VN", ["11.1.1.0/24"])
        (self.vn4_name, self.vn4_subnets) = ("EVPN-L2-VN", ["44.1.1.0/24"])
        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn3_name,
                subnets=self.vn3_subnets))

        vn4_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn4_name,
                subnets=self.vn4_subnets,
                enable_dhcp=False,
                forwarding_mode='l2'))

        self.connections.vnc_lib_fixture.set_rpf_mode(vn4_fixture.vn_fq_name, 'disable')

        vn_l2_vm1_name = 'EVPN_VN_L2_VM1'
        vn_l2_vm2_name = 'EVPN_VN_L2_VM2'

        file = 'testfile'
        y = 'ls -lrt /var/lib/tftpboot/%s' % file
        cmd_to_check_file = [y]
        z = 'ls -lrt /var/lib/tftpboot/%s' % file
        cmd_to_check_tftpboot_file = [z]
        file_sizes = ['1000', '1101', '1202', '1303', '1373',
                      '1374', '2210', '2845', '3000', '10000', '2000000']

        vm1_name = 'dhcp-server-vm'
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                flavor='contrail_flavor_large',
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu-dhcp-server',
                vm_name=vm1_name,
                node_name=compute_1))

        vn_l2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                flavor='contrail_flavor_small',
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu-traffic',
                vm_name=vn_l2_vm1_name,
                node_name=compute_2))
        vn_l2_vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                flavor='contrail_flavor_small',
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu-traffic',
                vm_name=vn_l2_vm2_name,
                node_name=compute_3))

        # Wait till vm is up
        assert vm1_fixture.wait_till_vm_is_up()
        assert vn_l2_vm1_fixture.wait_till_vm_is_up()
        assert vn_l2_vm2_fixture.wait_till_vm_is_up()
        assert vn3_fixture.verify_on_setup()
        assert vn4_fixture.verify_on_setup()
        assert vm1_fixture.verify_on_setup()
        assert vn_l2_vm1_fixture.verify_on_setup()
        assert vn_l2_vm2_fixture.verify_on_setup()
        
        # Configure dhcp-server vm on eth1 and bring the intreface up
        # forcefully
        self.bringup_interface_forcefully(vm1_fixture)
        cmd_to_pass1 = ['ifconfig eth1 13.1.1.253 netmask 255.255.255.0']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)

        for i in range(3):
          cmd_to_pass2 = ['service isc-dhcp-server restart']
          vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True, timeout=60)
          output = vm1_fixture.return_output_cmd_dict['service isc-dhcp-server restart']
          if output and 'running' in output:
              break
          else:
              sleep(2)

        self.bringup_interface_forcefully(vn_l2_vm1_fixture)
        self.bringup_interface_forcefully(vn_l2_vm2_fixture)
        sleep(10)

        for i in range(2):
            self.logger.info("Retry %s for bringing up eth1 up" % (i))
            cmd_to_pass3 = ['dhclient eth1']
            vn_l2_vm1_fixture.run_cmd_on_vm(
                cmds=cmd_to_pass3, as_sudo=True, timeout=60)

            ret1 = self.verify_eth1_ip_from_vm(vn_l2_vm1_fixture)
            cmd_to_pass4 = ['dhclient eth1']
            vn_l2_vm2_fixture.run_cmd_on_vm(
                cmds=cmd_to_pass4, as_sudo=True, timeout=60)

            ret2 = self.verify_eth1_ip_from_vm(vn_l2_vm2_fixture)
            if ret1 and ret2:
                break
            sleep(5)
        i = 'ifconfig eth1'
        cmd_to_pass5 = [i]
        out = vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass5, as_sudo=True, timeout=60)
        output = vn_l2_vm2_fixture.return_output_cmd_dict[i]
        match = re.search('inet addr:(.+?)  Bcast:', output)

        if match:
            dest_vm_ip = match.group(1)
        valid_ip = re.search('13.1.1.(.*)', output)
        assert valid_ip, 'failed to get ip from 13.1.1.0 subnet as configured in dhcp vm'

        for size in file_sizes:
            self.logger.info("-" * 80)
            self.logger.info("FILE SIZE = %sB" % size)
            self.logger.info("-" * 80)

            self.logger.info(
                'Transferring the file from %s to %s using tftp' %
                (vn_l2_vm1_fixture.vm_name, vn_l2_vm2_fixture.vm_name))
            filename = 'testfile'

            # Create file
            cmd = 'dd bs=%s count=1 if=/dev/zero of=%s' % (size, filename)
            vn_l2_vm1_fixture.run_cmd_on_vm(cmds=[cmd], timeout=60)

            # Create the file on the remote machine so that put can be done
            vn_l2_vm2_fixture.run_cmd_on_vm(
                cmds=['sudo touch /var/lib/tftpboot/%s' % (filename),
                      'sudo chmod 777 /var/lib/tftpboot/%s' % (filename)], timeout=60)
            # tftp file from EVPN_VN_L2_VM1 to EVPN_VN_L2_VM2 using
            # EVPN_VN_L2_VM2 vm's eth1 interface ip
            vn_l2_vm1_fixture.tftp_file_to_vm(filename, vm_ip=dest_vm_ip)
            vn_l2_vm1_fixture.run_cmd_on_vm(cmds=['sync'], as_sudo=True, timeout=60)

            # Verify if file size is same in destination vm
            self.logger.info('Checking if the file exists on %s' %
                             (vn_l2_vm2_fixture.vm_name))
            vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_check_file, timeout=60)
            output = vn_l2_vm2_fixture.return_output_cmd_dict[y]
            print(output)
            if size in output:
                self.logger.info(
                    'File of size %sB transferred via tftp properly' % size)
            else:
                result = False
                self.logger.error(
                    'File of size %sB not transferred via tftp ' % size)
                assert result, 'File of size %sB not transferred via tftp ' % size

        self.tcpdump_stop_on_all_compute()
        return result

    def verify_vlan_tagged_packets_for_l2_vn(self, encap):
        ''' Send traffic on tagged interfaces eth1.100 and eth1.200 respectively and verify configured  vlan tag in tcpdump
        '''
        # Setting up default encapsulation
        self.logger.info('Setting new Encap before continuing')
        if (encap == 'gre'):
            self.update_encap_priority('gre')
        elif (encap == 'udp'):
            self.update_encap_priority('udp')
        elif (encap == 'vxlan'):
            self.update_encap_priority('vxlan')

        result = True
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
        # Setup multi interface vms with eth1 as l2 interface
        (self.vn3_name, self.vn3_subnets) = ("EVPN-MGMT-VN", ["33.1.1.0/24"])
        (self.vn4_name, self.vn4_subnets) = ("EVPN-L2-VN", ["44.1.1.0/24"])
        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn3_name,
                subnets=self.vn3_subnets))

        vn4_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn4_name,
                subnets=self.vn4_subnets,
                enable_dhcp=False,
                forwarding_mode='l2'))

        vn_l2_vm1_name = 'EVPN_VN_L2_VM1'
        vn_l2_vm2_name = 'EVPN_VN_L2_VM2'

        vn_l2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu-traffic',
                vm_name=vn_l2_vm1_name,
                node_name=compute_1))
        vn_l2_vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu-traffic',
                vm_name=vn_l2_vm2_name,
                node_name=compute_2))

        assert vn3_fixture.verify_on_setup()
        assert vn4_fixture.verify_on_setup()
        assert vn_l2_vm1_fixture.verify_on_setup()
        assert vn_l2_vm2_fixture.verify_on_setup()

        # Wait till vm is up
        assert vn_l2_vm1_fixture.wait_till_vm_is_up()
        assert vn_l2_vm2_fixture.wait_till_vm_is_up()
        
        # Bring the intreface up forcefully
        self.bringup_interface_forcefully(vn_l2_vm1_fixture)
        self.bringup_interface_forcefully(vn_l2_vm2_fixture)
        
        # Configure 2 vlan's on eth1 with id 100 and 200 configure ips and
        # bring up the new interfaces,  first configure vlan 100
        cmd_to_pass1 = ['vconfig add eth1 100']
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        cmd_to_pass2 = ['vconfig add eth1 100']
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True, timeout=60)
        cmd_to_pass3 = ['ip addr add 10.0.0.1/24 dev eth1.100']
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass3, as_sudo=True, timeout=60)
        cmd_to_pass4 = ['ip addr add 10.0.0.2/24 dev eth1.100']
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass4, as_sudo=True, timeout=60)

        # Configure vlan with id 200 and give ip to new interface on both vms
        cmd_to_pass1 = ['vconfig add eth1 200']
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        cmd_to_pass2 = ['vconfig add eth1 200']
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True, timeout=60)
        cmd_to_pass3 = ['ip addr add 20.0.0.1/24 dev eth1.200']
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass3, as_sudo=True, timeout=60)
        cmd_to_pass4 = ['ip addr add 20.0.0.2/24 dev eth1.200']
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass4, as_sudo=True, timeout=60)

        # Bring the new interfaces eth1.100 and eth1.200 forcefully
        cmd_to_pass1 = ['ifconfig eth1.100 up']
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        cmd_to_pass2 = ['ifconfig eth1.100 up']
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True, timeout=60)
        cmd_to_pass3 = ['ifconfig eth1.200 up']
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass3, as_sudo=True, timeout=60)
        cmd_to_pass4 = ['ifconfig eth1.200 up']
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass4, as_sudo=True, timeout=60)
        sleep(30)

        i = 'ifconfig eth1.100'
        j = 'ifconfig eth1.200'
        cmd_to_pass1 = [i, j]
        out = vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        output = vn_l2_vm1_fixture.return_output_cmd_dict[i]
        match = re.search('inet addr:(.+?)  Bcast:', output)
        assert match, 'Failed to get configured ip'
        vn_l2_vm1_fixture_eth1_100_ip = match.group(1)
        output = vn_l2_vm1_fixture.return_output_cmd_dict[j]
        match = re.search('inet addr:(.+?)  Bcast:', output)
        assert match, 'Failed to get configured ip'
        vn_l2_vm1_fixture_eth1_200_ip = match.group(1)

        out = vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        output = vn_l2_vm2_fixture.return_output_cmd_dict[i]
        match = re.search('inet addr:(.+?)  Bcast:', output)
        assert match, 'Failed to get configured ip'
        vn_l2_vm2_fixture_eth1_100_ip = match.group(1)
        output = vn_l2_vm2_fixture.return_output_cmd_dict[j]
        match = re.search('inet addr:(.+?)  Bcast:', output)
        assert match, 'Failed to get configured ip'
        vn_l2_vm2_fixture_eth1_200_ip = match.group(1)

        # Analyze traffic and verify that configured vlan_id is seen
        vlan_id_pattern1 = '8100' + str('\ ') + '0064'
        vlan_id_pattern2 = '8100' + str('\ ') + '00c8'
        self.tcpdump_start_on_all_compute()
        assert vn_l2_vm1_fixture.ping_to_ip(
            vn_l2_vm2_fixture_eth1_100_ip, other_opt='-p 4231', count='15')
        comp_vm2_ip = vn_l2_vm2_fixture.vm_node_ip
        self.tcpdump_analyze_on_compute(
            comp_vm2_ip, encap.upper(), vlan_id=vlan_id_pattern1)
        self.tcpdump_start_on_all_compute()
        assert vn_l2_vm2_fixture.ping_to_ip(
            vn_l2_vm1_fixture_eth1_100_ip, other_opt='-p 4231', count='15')
        comp_vm1_ip = vn_l2_vm1_fixture.vm_node_ip
        self.tcpdump_analyze_on_compute(
            comp_vm1_ip, encap.upper(), vlan_id=vlan_id_pattern1)

        self.tcpdump_start_on_all_compute()
        assert vn_l2_vm1_fixture.ping_to_ip(
            vn_l2_vm2_fixture_eth1_200_ip, other_opt='-p 4231', count='15')
        comp_vm2_ip = vn_l2_vm2_fixture.vm_node_ip
        self.tcpdump_analyze_on_compute(
            comp_vm2_ip, encap.upper(), vlan_id=vlan_id_pattern2)
        self.tcpdump_start_on_all_compute()
        assert vn_l2_vm2_fixture.ping_to_ip(
            vn_l2_vm1_fixture_eth1_200_ip, other_opt='-p 4231', count='15')
        comp_vm1_ip = vn_l2_vm1_fixture.vm_node_ip
        self.tcpdump_analyze_on_compute(
            comp_vm1_ip, encap.upper(), vlan_id=vlan_id_pattern2)

        self.tcpdump_stop_on_all_compute()
        return True
    # end verify_vlan_tagged_packets_for_l2_vn

    def verify_vlan_qinq_tagged_packets_for_l2_vn(self, encap):
        ''' Send traffic on tagged interfaces eth1.100.1000 and eth1.200.2000 respectively on both vms and verify configured  vlan tag in tcpdump
        '''
        # Setting up default encapsulation
        self.logger.info('Setting new Encap before continuing')
        if (encap == 'vxlan'):
            self.update_encap_priority('vxlan')

        result = True
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
        # Setup multi interface vms with eth1 as l2 interface
        (self.vn3_name, self.vn3_subnets) = ("EVPN-MGMT-VN", ["33.1.1.0/24"])
        (self.vn4_name, self.vn4_subnets) = ("EVPN-L2-VN", ["44.1.1.0/24"])
        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn3_name,
                subnets=self.vn3_subnets))

        vn4_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn4_name,
                subnets=self.vn4_subnets,
                enable_dhcp=False,
                forwarding_mode='l2'))

        vn_l2_vm1_name = 'EVPN_VN_L2_VM1'
        vn_l2_vm2_name = 'EVPN_VN_L2_VM2'

        vn_l2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu-traffic',
                vm_name=vn_l2_vm1_name,
                node_name=compute_1))
        vn_l2_vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                flavor='contrail_flavor_large',
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu-traffic',
                vm_name=vn_l2_vm2_name,
                node_name=compute_2))
        assert vn3_fixture.verify_on_setup()
        assert vn4_fixture.verify_on_setup()
        assert vn_l2_vm1_fixture.verify_on_setup()
        assert vn_l2_vm2_fixture.verify_on_setup()

        # Wait till vm is up
        assert vn_l2_vm1_fixture.wait_till_vm_is_up()
        assert vn_l2_vm2_fixture.wait_till_vm_is_up()
        
        # Bring the intreface up forcefully
        self.bringup_interface_forcefully(vn_l2_vm1_fixture)
        self.bringup_interface_forcefully(vn_l2_vm2_fixture)

        # Configure 2 vlan's on eth1 with id 100 and 200 configure ips and
        # bring up the new interface forcefully
        vlan_id1 = '100'
        vlan_id2 = '200'
        i = 'vconfig add eth1 ' + vlan_id1
        j = 'ip addr add 10.0.0.1/24 dev eth1.' + vlan_id1
        k = 'vconfig add eth1 ' + vlan_id2
        l = 'ip addr add 20.0.0.1/24 dev eth1.' + vlan_id2
        cmd_to_pass1 = [i, j, k, l]
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        j = 'ip addr add 10.0.0.2/24 dev eth1.' + vlan_id1
        l = 'ip addr add 20.0.0.2/24 dev eth1.' + vlan_id2
        cmd_to_pass2 = [i, j, k, l]
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True, timeout=60)

        # Bring the new interfaces eth1.100 and eth1.200 forcefully
        cmd_to_pass1 = ['ifconfig eth1.100 up']
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        cmd_to_pass2 = ['ifconfig eth1.100 up']
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True, timeout=60)
        cmd_to_pass3 = ['ifconfig eth1.200 up']
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass3, as_sudo=True, timeout=60)
        cmd_to_pass4 = ['ifconfig eth1.200 up']
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass4, as_sudo=True, timeout=60)

        sleep(30)

        # Check if interface got ip assigned correctly
        i = 'ifconfig eth1.100'
        j = 'ifconfig eth1.200'
        cmd_to_pass1 = [i, j]
        out = vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        output = vn_l2_vm1_fixture.return_output_cmd_dict[i]
        match = re.search('inet addr:(.+?)  Bcast:', output)
        assert match, 'Failed to get configured ip'
        vn_l2_vm1_fixture_eth1_100_ip = match.group(1)
        output = vn_l2_vm1_fixture.return_output_cmd_dict[j]
        match = re.search('inet addr:(.+?)  Bcast:', output)
        assert match, 'Failed to get configured ip'
        vn_l2_vm1_fixture_eth1_200_ip = match.group(1)

        out = vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        output = vn_l2_vm2_fixture.return_output_cmd_dict[i]
        match = re.search('inet addr:(.+?)  Bcast:', output)
        assert match, 'Failed to get configured ip'
        vn_l2_vm2_fixture_eth1_100_ip = match.group(1)
        output = vn_l2_vm2_fixture.return_output_cmd_dict[j]
        match = re.search('inet addr:(.+?)  Bcast:', output)
        assert match, 'Failed to get configured ip'
        vn_l2_vm2_fixture_eth1_200_ip = match.group(1)

        # Configure new vlans on top of eth1.100 and eth1.200 vlans with
        # vlan_ids 1000 and 2000 respectively
        vlan_eth1_id1 = '1000'
        vlan_eth1_id2 = '2000'
        i = 'vconfig add eth1.100 ' + vlan_eth1_id1
        j = 'ip addr add 30.0.0.1/24 dev eth1.100.' + vlan_eth1_id1
        k = 'vconfig add eth1.100 ' + vlan_eth1_id2
        l = 'ip addr add 40.0.0.1/24 dev eth1.100.' + vlan_eth1_id2
        cmd_to_pass1 = [i, j, k, l]
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        j = 'ip addr add 30.0.0.2/24 dev eth1.100.' + vlan_eth1_id1
        l = 'ip addr add 40.0.0.2/24 dev eth1.100.' + vlan_eth1_id2
        cmd_to_pass2 = [i, j, k, l]
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True, timeout=60)

        i = 'vconfig add eth1.200 ' + vlan_eth1_id1
        j = 'ip addr add 50.0.0.1/24 dev eth1.200.' + vlan_eth1_id1
        k = 'vconfig add eth1.200 ' + vlan_eth1_id2
        l = 'ip addr add 60.0.0.1/24 dev eth1.200.' + vlan_eth1_id2
        cmd_to_pass1 = [i, j, k, l]
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        j = 'ip addr add 50.0.0.2/24 dev eth1.200.' + vlan_eth1_id1
        l = 'ip addr add 60.0.0.2/24 dev eth1.200.' + vlan_eth1_id2
        cmd_to_pass2 = [i, j, k, l]
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True, timeout=60)

        # Bring the new interfaces on eth1.100 and eth1.200 with tag 1000 and
        # 2000 up
        cmd_to_pass1 = ['ifconfig eth1.100.1000 up']
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        cmd_to_pass2 = ['ifconfig eth1.100.1000 up']
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True, timeout=60)
        sleep(1)
        cmd_to_pass3 = ['ifconfig eth1.100.2000 up']
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass3, as_sudo=True, timeout=60)
        cmd_to_pass4 = ['ifconfig eth1.100.2000 up']
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass4, as_sudo=True, timeout=60)
        sleep(1)
        cmd_to_pass1 = ['ifconfig eth1.200.1000 up']
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        cmd_to_pass2 = ['ifconfig eth1.200.1000 up']
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass2, as_sudo=True, timeout=60)
        sleep(1)
        cmd_to_pass3 = ['ifconfig eth1.200.2000 up']
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass3, as_sudo=True, timeout=60)
        cmd_to_pass4 = ['ifconfig eth1.200.2000 up']
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass4, as_sudo=True, timeout=60)
        sleep(1)

        # Check if interface got ip assigned correctly
        i = 'ifconfig eth1.100.1000'
        j = 'ifconfig eth1.100.2000'
        k = 'ifconfig eth1.200.1000'
        l = 'ifconfig eth1.200.2000'
        cmd_to_pass1 = [i, j, k, l]
        out = vn_l2_vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        output = vn_l2_vm1_fixture.return_output_cmd_dict[i]
        match = re.search('inet addr:(.+?)  Bcast:', output)
        assert match, 'Failed to get configured ip'
        vn_l2_vm1_fixture_eth1_100_1000_ip = match.group(1)
        output = vn_l2_vm1_fixture.return_output_cmd_dict[j]
        match = re.search('inet addr:(.+?)  Bcast:', output)
        assert match, 'Failed to get configured ip'
        vn_l2_vm1_fixture_eth1_100_2000_ip = match.group(1)
        output = vn_l2_vm1_fixture.return_output_cmd_dict[k]
        match = re.search('inet addr:(.+?)  Bcast:', output)
        assert match, 'Failed to get configured ip'
        vn_l2_vm1_fixture_eth1_200_1000_ip = match.group(1)
        output = vn_l2_vm1_fixture.return_output_cmd_dict[l]
        match = re.search('inet addr:(.+?)  Bcast:', output)
        assert match, 'Failed to get configured ip'
        vn_l2_vm1_fixture_eth1_200_2000_ip = match.group(1)

        out = vn_l2_vm2_fixture.run_cmd_on_vm(cmds=cmd_to_pass1, as_sudo=True, timeout=60)
        output = vn_l2_vm2_fixture.return_output_cmd_dict[i]
        match = re.search('inet addr:(.+?)  Bcast:', output)
        assert match, 'Failed to get configured ip'
        vn_l2_vm2_fixture_eth1_100_1000_ip = match.group(1)
        output = vn_l2_vm2_fixture.return_output_cmd_dict[j]
        match = re.search('inet addr:(.+?)  Bcast:', output)
        assert match, 'Failed to get configured ip'
        vn_l2_vm2_fixture_eth1_100_2000_ip = match.group(1)
        output = vn_l2_vm2_fixture.return_output_cmd_dict[k]
        match = re.search('inet addr:(.+?)  Bcast:', output)
        assert match, 'Failed to get configured ip'
        vn_l2_vm2_fixture_eth1_200_1000_ip = match.group(1)
        output = vn_l2_vm2_fixture.return_output_cmd_dict[l]
        match = re.search('inet addr:(.+?)  Bcast:', output)
        assert match, 'Failed to get configured ip'
        vn_l2_vm2_fixture_eth1_200_2000_ip = match.group(1)

        # Ping between the interface and verify that vlan id is seen in traffic
        vlan_id_pattern1 =  '8100' + \
            str('\ ') + '0064' + str('\ ') + '8100' + str('\ ') + '03e8'
        vlan_id_pattern2 =  '8100' + \
            str('\ ') + '00c8' + str('\ ') + '8100' + str('\ ') + '03e8'
        vlan_id_pattern3 =  '8100' + \
            str('\ ') + '0064' + str('\ ') + '8100' + str('\ ') + '07d0'
        vlan_id_pattern4 =  '8100' + \
            str('\ ') + '00c8' + str('\ ') + '8100' + str('\ ') + '07d0'
        self.tcpdump_start_on_all_compute()
        assert vn_l2_vm1_fixture.ping_to_ip(
            vn_l2_vm2_fixture_eth1_100_1000_ip,
            other_opt='-I eth1.100.1000  -p 4231',
            count='15')
        comp_vm2_ip = vn_l2_vm2_fixture.vm_node_ip
        self.tcpdump_analyze_on_compute(
            comp_vm2_ip, encap.upper(), vlan_id=vlan_id_pattern1)
        self.tcpdump_start_on_all_compute()
        assert vn_l2_vm2_fixture.ping_to_ip(
            vn_l2_vm1_fixture_eth1_100_1000_ip,
            other_opt='-I eth1.100.1000 -p 4231',
            count='15')
        comp_vm1_ip = vn_l2_vm1_fixture.vm_node_ip
        self.tcpdump_analyze_on_compute(
            comp_vm1_ip, encap.upper(), vlan_id=vlan_id_pattern1)

        self.tcpdump_start_on_all_compute()
        assert vn_l2_vm1_fixture.ping_to_ip(
            vn_l2_vm2_fixture_eth1_100_2000_ip,
            other_opt='-I eth1.100.2000 -p 4231',
            count='15')
        comp_vm2_ip = vn_l2_vm2_fixture.vm_node_ip
        self.tcpdump_analyze_on_compute(
            comp_vm2_ip, encap.upper(), vlan_id=vlan_id_pattern3)
        self.tcpdump_start_on_all_compute()
        assert vn_l2_vm2_fixture.ping_to_ip(
            vn_l2_vm1_fixture_eth1_100_2000_ip,
            other_opt='-I eth1.100.2000 -p 4231',
            count='15')
        comp_vm1_ip = vn_l2_vm1_fixture.vm_node_ip
        self.tcpdump_analyze_on_compute(
            comp_vm1_ip, encap.upper(), vlan_id=vlan_id_pattern3)

        self.tcpdump_start_on_all_compute()
        assert vn_l2_vm1_fixture.ping_to_ip(
            vn_l2_vm2_fixture_eth1_200_1000_ip,
            other_opt='-I eth1.200.1000 -p 4231',
            count='15')
        comp_vm2_ip = vn_l2_vm2_fixture.vm_node_ip
        self.tcpdump_analyze_on_compute(
            comp_vm2_ip, encap.upper(), vlan_id=vlan_id_pattern2)
        self.tcpdump_start_on_all_compute()
        assert vn_l2_vm2_fixture.ping_to_ip(
            vn_l2_vm1_fixture_eth1_200_1000_ip,
            other_opt='-I eth1.200.1000 -p 4231',
            count='15')
        comp_vm1_ip = vn_l2_vm1_fixture.vm_node_ip
        self.tcpdump_analyze_on_compute(
            comp_vm1_ip, encap.upper(), vlan_id=vlan_id_pattern2)

        self.tcpdump_start_on_all_compute()
        assert vn_l2_vm1_fixture.ping_to_ip(
            vn_l2_vm2_fixture_eth1_200_2000_ip,
            other_opt='-I eth1.200.2000 -p 4231',
            count='15')
        comp_vm2_ip = vn_l2_vm2_fixture.vm_node_ip
        self.tcpdump_analyze_on_compute(
            comp_vm2_ip, encap.upper(), vlan_id=vlan_id_pattern4)
        self.tcpdump_start_on_all_compute()
        assert vn_l2_vm2_fixture.ping_to_ip(
            vn_l2_vm1_fixture_eth1_200_2000_ip,
            other_opt='-I eth1.200.2000 -p 4231',
            count='15')
        comp_vm1_ip = vn_l2_vm1_fixture.vm_node_ip
        self.tcpdump_analyze_on_compute(
            comp_vm1_ip, encap.upper(), vlan_id=vlan_id_pattern4)

        # Ping between interfaces with different outer vlan tag and expect the
        # ping to fail
        self.logger.info(
            "Expecting the pings to fail as the outer vlan tag is different")
        assert not (
            vn_l2_vm1_fixture.ping_to_ip(vn_l2_vm2_fixture_eth1_200_1000_ip,
                                         other_opt='-I eth1.100.1000 -p 4231')), 'Failed in resolving outer vlan tag'
        assert not (
            vn_l2_vm1_fixture.ping_to_ip(vn_l2_vm2_fixture_eth1_200_2000_ip,
                                         other_opt='-I eth1.100.2000 -p 4231')), 'Failed in resolving outer vlan tag'
        assert not (
            vn_l2_vm2_fixture.ping_to_ip(vn_l2_vm1_fixture_eth1_100_1000_ip,
                                         other_opt='-I eth1.200.1000 -p 4231')), 'Failed in resolving outer vlan tag'
        assert not (
            vn_l2_vm2_fixture.ping_to_ip(vn_l2_vm1_fixture_eth1_100_2000_ip,
                                         other_opt='-I eth1.200.2000 -p 4231')), 'Failed in resolving outer vlan tag'

        self.tcpdump_stop_on_all_compute()
        return True
    # End verify_vlan_qinq_tagged_packets_for_l2_vn

    def verify_epvn_l2_mode_control_node_switchover(self, encap):
        '''Setup l2 evpn and do control node switch over verify ping before and after cn switch over
        '''
        if len(set(self.inputs.bgp_ips)) < 2:
            self.logger.info(
                "Skipping Test. At least 2 control node required to run the test")
            raise self.skipTest(
                "Skipping Test. At least 2 control node required to run the test")
        # Setting up default encapsulation
        self.logger.info('Setting new Encap before continuing')
        if (encap == 'gre'):
            self.update_encap_priority('gre')
        elif (encap == 'udp'):
            self.update_encap_priority('udp')
        elif (encap == 'vxlan'):
            self.update_encap_priority('vxlan')

        result = True
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]

        (self.vn3_name, self.vn3_subnets) = ("EVPN-MGMT-VN", ["33.1.1.0/24"])
        (self.vn4_name, self.vn4_subnets) = ("EVPN-L2-VN", ["44.1.1.0/24"])
        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn3_name,
                subnets=self.vn3_subnets))

        vn4_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn4_name,
                subnets=self.vn4_subnets,
                enable_dhcp=False,
                forwarding_mode='l2'))

        vn_l2_vm1_name = 'EVPN_VN_L2_VM1'
        vn_l2_vm2_name = 'EVPN_VN_L2_VM2'

        vn_l2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm1_name,
                node_name=compute_1))
        vn_l2_vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm2_name,
                node_name=compute_2))

        assert vn3_fixture.verify_on_setup()
        assert vn4_fixture.verify_on_setup()
        assert vn_l2_vm1_fixture.verify_on_setup()
        assert vn_l2_vm2_fixture.verify_on_setup()

        # Wait till vm is up
        assert vn_l2_vm1_fixture.wait_till_vm_is_up()
        assert vn_l2_vm2_fixture.wait_till_vm_is_up()

        #removed ipv6 verification
        self.tcpdump_start_on_all_compute()
        self.mac1=vn_l2_vm1_fixture.mac_addr[vn4_fixture.vn_fq_name]
        self.mac2=vn_l2_vm2_fixture.mac_addr[vn4_fixture.vn_fq_name]
        filters = 'ether src %s' %(self.mac1)
        tap_intf = vn_l2_vm2_fixture.tap_intf[vn4_fixture.vn_fq_name]['name']
        session,pcap = vn_l2_vm2_fixture.start_tcpdump(filters=filters,interface=tap_intf)
        self.logger.info('waiting to get tcpdump started')
        sleep(10)
        self.send_l2_traffic(vn_l2_vm1_fixture,iface='eth1')
        sleep(10)
        comp_vm1_ip = vn_l2_vm1_fixture.vm_node_ip
        comp_vm2_ip = vn_l2_vm2_fixture.vm_node_ip
        self.tcpdump_analyze_on_compute(comp_vm1_ip, encap.upper())
        self.tcpdump_analyze_on_compute(comp_vm2_ip, encap.upper())

        # Figuring the active control node
        active_controller = None
        self.agent_inspect = self.connections.agent_inspect
        inspect_h = self.agent_inspect[vn_l2_vm1_fixture.vm_node_ip]
        agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                active_controller = entry['controller_ip']
        active_controller_host_ip = self.inputs.host_data[
            active_controller]['host_ip']
        self.logger.info(
            'Active control node from the Agent %s is %s' %
            (vn_l2_vm1_fixture.vm_node_ip, active_controller_host_ip))

        # Stop on Active node
        self.logger.info('Stoping the Control service in  %s' %
                         (active_controller_host_ip))
        self.inputs.stop_service(
            'contrail-control', [active_controller_host_ip],
            container='control')
        sleep(5)

        # Check the control node shifted to other control node
        new_active_controller = None
        new_active_controller_state = None
        inspect_h = self.agent_inspect[vn_l2_vm1_fixture.vm_node_ip]
        agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                new_active_controller = entry['controller_ip']
                new_active_controller_state = entry['state']
        new_active_controller_host_ip = self.inputs.host_data[
            new_active_controller]['host_ip']
        self.logger.info(
            'Active control node from the Agent %s is %s' %
            (vn_l2_vm1_fixture.vm_node_ip, new_active_controller_host_ip))
        if new_active_controller_host_ip == active_controller_host_ip:
            self.logger.error(
                'Control node switchover fail. Old Active controlnode was %s and new active control node is %s' %
                (active_controller_host_ip, new_active_controller_host_ip))
            result = False

        if new_active_controller_state != 'Established':
            self.logger.error(
                'Agent does not have Established XMPP connection with Active control node')
            result = result and False

        # Start the control node service again
        self.logger.info('Starting the Control service in  %s' %
                         (active_controller_host_ip))
        self.inputs.start_service(
            'contrail-control', [active_controller_host_ip],
            container='control')

        # Check the BGP peering status from the currently active control node
        sleep(5)
        cn_bgp_entry = self.cn_inspect[
            new_active_controller_host_ip].get_cn_bgp_neigh_entry()
        sleep(5)
        for entry in cn_bgp_entry:
            if entry['state'] != 'Established':
                result = result and False
                self.logger.error(
                    'With Peer %s peering is not Established. Current State %s ' %
                    (entry['peer'], entry['state']))
        # Check ping
        #removed ipv6 verification
        #send l2_traffic
        self.tcpdump_start_on_all_compute()
        self.mac1=vn_l2_vm1_fixture.mac_addr[vn4_fixture.vn_fq_name]
        self.mac2=vn_l2_vm2_fixture.mac_addr[vn4_fixture.vn_fq_name]
        filters = 'ether src %s' %(self.mac1)
        tap_intf = vn_l2_vm2_fixture.tap_intf[vn4_fixture.vn_fq_name]['name']
        session,pcap = vn_l2_vm2_fixture.start_tcpdump(filters=filters,interface=tap_intf)
        self.logger.info('waiting to get tcpdump started')
        sleep(10)
        self.send_l2_traffic(vn_l2_vm1_fixture,iface='eth1')
        sleep(10)                                     
        comp_vm1_ip = vn_l2_vm1_fixture.vm_node_ip
        comp_vm2_ip = vn_l2_vm2_fixture.vm_node_ip
        self.tcpdump_analyze_on_compute(comp_vm1_ip, encap.upper())
        self.tcpdump_analyze_on_compute(comp_vm2_ip, encap.upper())
        self.tcpdump_stop_on_all_compute()
        
        return result
    # verify_epvn_l2_mode_control_node_switchover

    def verify_epvn_with_agent_restart(self, encap):
        '''Restart the vrouter service and verify the impact on L2 route
        '''
        # Setting up default encapsulation
        self.logger.info('Setting new Encap before continuing')
        if (encap == 'gre'):
            self.update_encap_priority('gre')
        elif (encap == 'udp'):
            self.update_encap_priority('udp')
        elif (encap == 'vxlan'):
            self.update_encap_priority('vxlan')

        result = True
        host_list = self.connections.orch.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]

        (self.vn1_name, self.vn1_subnets) = ("EVPN-VN1", ["11.1.1.0/24"])
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn1_name,
                subnets=self.vn1_subnets))
        vm1_name = 'EVPN_VN1_VM1'
        vm2_name = 'EVPN_VN1_VM2'
        vn1_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                image_name='ubuntu',
                vm_name=vm1_name,
                node_name=compute_1))
        vn1_vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn1_fixture.obj,
                image_name='ubuntu',
                vm_name=vm2_name,
                node_name=compute_2))
        assert vn1_fixture.verify_on_setup()
        assert vn1_vm1_fixture.verify_on_setup()
        assert vn1_vm2_fixture.verify_on_setup()
        assert vn1_vm1_fixture.wait_till_vm_is_up()
        assert vn1_vm2_fixture.wait_till_vm_is_up()
        
        #send l2 traffic and verify
        self.mac1=vn1_vm1_fixture.mac_addr[vn1_fixture.vn_fq_name]
        self.mac2=vn1_vm2_fixture.mac_addr[vn1_fixture.vn_fq_name]
        filters = 'ether src %s' %(self.mac1)
        tap_intf = vn1_vm2_fixture.tap_intf[vn1_fixture.vn_fq_name]['name']
        session,pcap = vn1_vm2_fixture.start_tcpdump(filters=filters,interface=tap_intf)
        self.logger.info('waiting to get tcpdump started')
        sleep(20)
        self.send_l2_traffic(vn1_vm1_fixture,iface='eth0')
        result = verify_tcpdump_count(self, session, pcap, exp_count=10,mac=self.mac2)
        self.logger.info('Will restart compute  services now')
        for compute_ip in self.inputs.compute_ips:
            if compute_ip in self.inputs.dpdk_ips:
                self.inputs.stop_service('contrail-vrouter-agent', [compute_ip],
                                         container='agent')
                self.inputs.restart_service('contrail-vrouter-agent-dpdk', [compute_ip],
                                            container='agent-dpdk')
                self.inputs.start_service('contrail-vrouter-agent', [compute_ip],
                                          container='agent')
            else:
                self.inputs.restart_service('contrail-vrouter', [compute_ip],
                                        container='agent')
        sleep(10)
        self.logger.info(
            'Verifying L2 route and other VM verification after restart')
        assert vn1_vm1_fixture.verify_on_setup(refresh=True)
        assert vn1_vm2_fixture.verify_on_setup(refresh=True)
        #send l2 traffic and verify
        self.mac1=vn1_vm1_fixture.mac_addr[vn1_fixture.vn_fq_name]
        self.mac2=vn1_vm2_fixture.mac_addr[vn1_fixture.vn_fq_name]
        filters = 'ether src %s' %(self.mac1)
        tap_intf = vn1_vm2_fixture.tap_intf[vn1_fixture.vn_fq_name]['name']
        session,pcap = vn1_vm2_fixture.start_tcpdump(filters=filters,interface=tap_intf)
        self.logger.info('waiting to get tcpdump started')
        sleep(20)
        self.send_l2_traffic(vn1_vm1_fixture,iface='eth0')
        result = verify_tcpdump_count(self, session, pcap, exp_count=10,mac=self.mac2)
        self.logger.info('Checking the communication between 2 VM after vrouter restart')
        assert vn1_vm1_fixture.ping_with_certainty(dst_vm_fixture=vn1_vm2_fixture, 
                                              vn_fq_name=vn1_fixture.vn_fq_name)

        return True
    # End test_epvn_with_agent_restart

    def verify_epvn_l2_mode(self, encap):
        '''verify the impact on L2 route with each encapsulation
        '''
        # Setting up default encapsulation
        self.logger.info('Setting new Encap before continuing')
        if (encap == 'gre'):
            self.update_encap_priority('gre')
        elif (encap == 'udp'):
            self.update_encap_priority('udp')
        elif (encap == 'vxlan'):
            self.update_encap_priority('vxlan')

        result = True
        host_list = self.connections.orch.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]

        (self.vn3_name, self.vn3_subnets) = ("EVPN-MGMT-VN", ["33.1.1.0/24"])
        (self.vn4_name, self.vn4_subnets) = ("EVPN-L2-VN", ["44.1.1.0/24"])

        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn3_name,
                subnets=self.vn3_subnets))

        vn4_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn4_name,
                subnets=self.vn4_subnets,
                enable_dhcp=False,
                forwarding_mode='l2'))

        vn_l2_vm1_name = 'EVPN_VN_L2_VM1'
        vn_l2_vm2_name = 'EVPN_VN_L2_VM2'

        vn_l2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm1_name,
                node_name=compute_1))
        vn_l2_vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    vn4_fixture.obj],
                image_name='ubuntu',
                vm_name=vn_l2_vm2_name,
                node_name=compute_2))
        assert vn3_fixture.verify_on_setup()
        assert vn4_fixture.verify_on_setup()
        assert vn_l2_vm1_fixture.verify_on_setup()
        assert vn_l2_vm2_fixture.verify_on_setup()

        # Wait till vm is up
        vn_l2_vm1_fixture.wait_till_vm_is_up()
        vn_l2_vm2_fixture.wait_till_vm_is_up()

        #send l2 traffic and verify
        self.mac1=vn_l2_vm1_fixture.mac_addr[vn4_fixture.vn_fq_name]
        self.mac2=vn_l2_vm2_fixture.mac_addr[vn4_fixture.vn_fq_name]
        filters = 'ether src %s' %(self.mac1)
        tap_intf = vn_l2_vm2_fixture.tap_intf[vn4_fixture.vn_fq_name]['name']
        self.tcpdump_start_on_all_compute()
        session,pcap = vn_l2_vm2_fixture.start_tcpdump(filters=filters,interface=tap_intf)
        self.logger.info('waiting to get tcpdump started')
        sleep(10)
        self.send_l2_traffic(vn_l2_vm1_fixture,iface='eth1')
        sleep(10)
        result = verify_tcpdump_count(self, session, pcap, exp_count=10,mac=self.mac2)

        comp_vm2_ip = vn_l2_vm2_fixture.vm_node_ip
        if len(self.connections.nova_h.get_hosts()) >= 2:
            self.tcpdump_analyze_on_compute(comp_vm2_ip, encap.upper())
        self.tcpdump_stop_on_all_compute()

        return True
    # End verify_epvn_l2_mode
    
    def verify_l2_only_and_l3_only_arp_resolution(self,encap):

        # Setting up default encapsulation
        self.logger.info('Setting new Encap before continuing')
        if (encap == 'gre'):
            self.update_encap_priority('gre')
        elif (encap == 'udp'):
            self.update_encap_priority('udp')
        elif (encap == 'vxlan'):
            self.update_encap_priority('vxlan')

        result = True
        host_list = self.connections.nova_h.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
        (self.vn3_name, self.vn3_subnets) = ("EVPN-MGMT-VN", ["33.1.1.0/24"])
        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn3_name,
                subnets=self.vn3_subnets))

        vn_l2_vm1_name = 'EVPN_VN_L2_VM1'
        vn_l2_vm2_name = 'EVPN_VN_L2_VM2'

        (self.vn1_name, self.vn1_subnets) = ("EVPN-Test-VN1", ["55.1.1.0/24"])

        self.vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                inputs=self.inputs,
                vn_name=self.vn1_name,
                subnets=self.vn1_subnets))
        assert self.vn1_fixture.verify_on_setup()
        vn_l2_vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    self.vn1_fixture.obj],
                image_name='ubuntu-traffic',
                vm_name=vn_l2_vm1_name,
                node_name=compute_1))
        vn_l2_vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[
                    vn3_fixture.obj,
                    self.vn1_fixture.obj],
                image_name='ubuntu-traffic',
                vm_name=vn_l2_vm2_name,
                node_name=compute_2))

        assert vn_l2_vm1_fixture.verify_on_setup()
        assert vn_l2_vm2_fixture.verify_on_setup()

        # Wait till vm is up
        assert vn_l2_vm1_fixture.wait_till_vm_is_up()
        assert vn_l2_vm2_fixture.wait_till_vm_is_up()
        self.bringup_interface_forcefully(vn_l2_vm1_fixture)
        cmd = 'dhclient eth1'
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        assert self.verify_eth1_ip_from_vm(vn_l2_vm1_fixture)
        
        self.bringup_interface_forcefully(vn_l2_vm2_fixture)
        cmd = 'dhclient eth1'
        vn_l2_vm2_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        assert self.verify_eth1_ip_from_vm(vn_l2_vm2_fixture)
        self.logger.info(
            "Changing vn1 forwarding mode from l2l3 to l2 only  followed by calling verify_on_setup for vms which checks l2 routes and explicity check l3 routes are  removed  ")
        self.vn1_fixture.add_forwarding_mode(
            project_fq_name=self.inputs.project_fq_name,
            vn_name=self.vn1_name,
            forwarding_mode='l2')
        assert self.vn1_fixture.verify_on_setup()
        assert vn_l2_vm1_fixture.verify_on_setup()
        assert vn_l2_vm2_fixture.verify_on_setup()
        cmd = 'ip -s -s neigh flush all'
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        mac1=vn_l2_vm1_fixture.mac_addr[self.vn1_fixture.vn_fq_name]
        mac2=vn_l2_vm2_fixture.mac_addr[self.vn1_fixture.vn_fq_name]
        self.logger.info('verify l2_only arp resolution')
        filters = 'arp'
        tap_intf = vn_l2_vm2_fixture.tap_intf[self.vn1_fixture.vn_fq_name]['name']
        session,pcap = vn_l2_vm2_fixture.start_tcpdump(filters=filters,interface=tap_intf)
        self.logger.info('waiting to get tcpdump started')
        sleep(20)
        
        self.vn_l2_vm1_ip = vn_l2_vm1_fixture.vm_ip_dict[self.vn1_fixture.vn_fq_name][0]
        self.vn_l2_vm2_ip = vn_l2_vm2_fixture.vm_ip_dict[self.vn1_fixture.vn_fq_name][0]
        intf_name = vn_l2_vm1_fixture.get_vm_interface_name(mac1)
        output,form_output = vn_l2_vm1_fixture.arping(self.vn_l2_vm2_ip,intf_name)
        search_string = self.vn_l2_vm1_ip
        status = search_in_pcap(session, pcap,search_string)
        vn_l2_vm2_fixture.stop_tcpdump(session,pcap)
        if status and mac2 in output:
            self.logger.info('arp resolution was done by end vm')
        else:
            assert status,'arp got proxied which is not expected in L2 mode'
            
        #for bug-id 1513718 
        #clear arps and do arping
        #check vrouter proxy arp request or not
        self.logger.info('Verifying l3_only arp resolution')
        self.logger.info(
            "Changing vn1 forwarding mode from l2l3 to l3 only  followed by calling verify_on_setup ")
        self.vn1_fixture.add_forwarding_mode(
            project_fq_name=self.inputs.project_fq_name,
            vn_name=self.vn1_name,
            forwarding_mode='l3')
        cmd = 'ip -s -s neigh flush all'
        vn_l2_vm1_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        filters = 'arp'
        session,pcap = vn_l2_vm2_fixture.start_tcpdump(filters=filters,interface=tap_intf)
        self.logger.info('waiting to get tcpdump started')
        sleep(20)
        intf_name = vn_l2_vm1_fixture.get_vm_interface_name(mac1)
        output,form_output = vn_l2_vm1_fixture.arping(self.vn_l2_vm2_ip,intf_name)
        vn_l2_vm2_fixture.stop_tcpdump(session, pcap)
        search_string = self.vn_l2_vm1_ip
        status = search_in_pcap(session, pcap,search_string)
        vn_l2_vm2_fixture.stop_tcpdump(session,pcap)
        if not status and ('00:00:5e:00:01:00' in output):
            self.logger.info('arp proxied by vrouter in L3 mode')
        else:
            assert status,'arp not proxied by vrouter'
            
        return result
    #end verify_l2_l3_and_l3_only_arp_resolution

        

    def bringup_interface_forcefully(self, vm_fixture, intf='eth1'):
        cmd = 'ifconfig %s up'%(intf)
        for i in range (5):
          cmd_to_pass = [cmd]
          vm_fixture.run_cmd_on_vm(cmds=cmd_to_pass, as_sudo=True, timeout=60)
          vm_fixture.run_cmd_on_vm(cmds=['ifconfig'], as_sudo=True, timeout=60)
          output = vm_fixture.return_output_cmd_dict['ifconfig']
          if output and 'eth1' in output:
              break
          else:
             sleep(3)
          
    # Encap functions here :

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
            cmd1 = 'tcpdump -ni %s -U udp port 6635 and \'((ether[100:4]==0x5a5a5a5a) or (ether[120:4]==0x42314231))\' -w %s -s 0' % (
                comp_intf, pcap1)
            cmd_udp = "nohup " + cmd1 + " >& /dev/null < /dev/null &"
            cmd2 = 'tcpdump -ni %s -U proto 47 and \'((ether[100:4]==0x5a5a5a5a) or (ether[120:4]==0x42314231))\' -w %s -s 0' % (comp_intf, pcap2)
            cmd_gre = "nohup " + cmd2 + " >& /dev/null < /dev/null &"
            cmd3 = 'tcpdump -ni %s -U dst port 4789 and \'((ether[100:4]==0x5a5a5a5a) or (ether[120:4]==0x42314231))\' -w %s -s 0' % (
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
            out3, err  = execute_cmd_out(session, cmd3, self.logger)
            count_1204 = int(out3.strip('\n'))
            cmd4 = 'tcpdump  -r %s | grep VXLAN |wc -l' % pcaps3
            out4, err = execute_cmd_out(session, cmd4, self.logger)
            count_1404 = int(out4.strip('\n'))
            if count_1204 != 0:
                count = count_1204
            elif count_1404 !=0 :
                count = count_1404
            else: 
                 count=0

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

                if count_vlan_id > count:
                    errmsg = "%s vxlan packet are seen with %s vlan_id . Not Expected . " % (
                        count, count_vlan_id)
                    self.logger.error(errmsg)
                    assert False, errmsg
                else:
                    self.logger.info(
                        "%s vxlan packets are seen with %s vlan_id as expexted . " %
                        (count, count_vlan_id))

        return True

    # end tcpdump_analyze_on_compute
    
    def send_l3_traffic(self,vm1_fixture):
        python_code = Template('''
from scapy.all import *
payload = 'ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ'
a=IP(src='$src_ip',dst='$dst_ip')/payload
send(a, count=10)
            ''')
        python_code = python_code.substitute(src_ip=self.vn_l2_vm1_ip, dst_ip=self.vn_l2_vm2_ip)
        return vm1_fixture.run_python_code(python_code)
    #end send_l3_traffic
    def send_l2_traffic(self,vm1_fixture,iface):
        
        python_code = Template('''
from scapy.all import *
payload = 'ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ'
a=Ether(src='$mac1',dst='$mac2')/payload
sendp(a, count=10, inter=0, iface='$iface')
            ''')
        python_code = python_code.substitute(mac1=self.mac1,mac2=self.mac2,iface=iface)
        return vm1_fixture.run_python_code(python_code)
    #end send_l2_traffic
    
