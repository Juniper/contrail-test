from __future__ import print_function
# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run vdns_tests'. To run specific tests,
# You can do 'python -m testtools.run -l vdns_tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
from common.vdns.base import BasevDNSTest 
from builtins import str
from builtins import range
from builtins import object
import os
import unittest
import fixtures
import testtools
import traceback
import difflib

from policy_test import *
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.pkgs.Traffic.traffic.core.stream import Stream
from tcutils.pkgs.Traffic.traffic.core.profile import create, ContinuousProfile
from tcutils.pkgs.Traffic.traffic.core.helpers import Host
from tcutils.pkgs.Traffic.traffic.core.helpers import Sender, Receiver
from common import isolated_creds
import inspect
from vnc_api import vnc_api
from vnc_api.gen.resource_test import *
from vdns_fixture import *
from floating_ip import *
from policy_test import *
from control_node import *
from user_test import UserFixture
import test
from common.contrail_test_init import ContrailTestInit
from tcutils.contrail_status_check import ContrailStatusChecker


class TestvDNS0(BasevDNSTest):

    @classmethod
    def setUpClass(cls):
        super(TestvDNS0, cls).setUpClass()

    def runTest(self):
        pass
    #end runTest

    # until Bug #1866 is resolved this test is going to run for 1000 records.
    @preposttest_wrapper
    def test_vdns_zrecord_scaling(self):
        '''This test tests vdns fixed record scaling
            1. Create VDNS server object
            2. Associate VDNS with IPAM
            3. Launch VN with IPAM and launch VM in VN
            4. Create 1000 records
            5. Pic some random records for nslookup verification and it should pass
        Pass criteria: Step 5 should pass
        Maintainer: cf-test@juniper.net'''

        record_order = 'random'
        test_type = 'recordscaling'
        record_num = 1000
        self.verify_dns_record_order(record_order, test_type, record_num)
        return True



class TestvDNSRestart(BasevDNSTest):

    @classmethod
    def setUpClass(cls):
        super(TestvDNSRestart, cls).setUpClass()

    def runTest(self):
        pass
    #end runTest
 
    @preposttest_wrapper
    def test_vdns_controlnode_switchover(self):
        ''' This test tests control node switchover functionality
            1. Create VDNS server object
            2. Associate VDNS with IPAM
            3. Launch VN with IPAM
            4. Launch VM with VN Created above. This test verifies on launch of VM agent should update DNS 'A' and 'PTR' records
            5. Ping VMs using VM name
            6. Restart active control node
            7. Ping VMs using VM name
        Pass criteria: Step 4,5 and 7 should pass
        Maintainer: cf-test@juniper.net
        '''

        restart_process = 'ControlNodeRestart'
        self.vdns_with_cn_dns_agent_restart(restart_process)
        return True

    @preposttest_wrapper
    def test_vdns_dns_restart(self):
        ''' This test test dns process restart functionality
            1. Create VDNS server object
            2. Associate VDNS with IPAM
            3. Launch VN with IPAM
            4. Launch  VM with VN Created above. This test verifies on launch of VM agent should update DNS 'A' and 'PTR' records
            5. Ping VMs using VM name
            6. Restart the dns process in the active control node
            7. Ping VMs using VM name
        Pass criteria: Step 4, 5 and 7 should pass
        Maintainer: cf-test@juniper.net
        '''
        restart_process = 'DnsRestart'
        self.vdns_with_cn_dns_agent_restart(restart_process)
        return True

    @preposttest_wrapper
    def test_vdns_agent_restart(self):
        '''This test tests agent process restart functionality
            1. Create VDNS server object
            2. Associate VDNS with IPAM
            3. Launch VN with IPAM
            4. Launch VM with VN Created above. This test verifies on launch of VM agent should update DNS 'A' and 'PTR' records
            5. Ping VMs using VM name
            6. Restart the agent process in the compute node
            7. Ping VMs using VM name
        Pass criteria: Step 4, 5 and 7 should pass
        Maintainer: cf-test@juniper.net
        '''

        restart_process = 'AgentRestart'
        self.vdns_with_cn_dns_agent_restart(restart_process)
        return True

    @preposttest_wrapper
    def test_vdns_named_restart(self):
        '''This test tests named process restart functionality
            1. Create VDNS server object
            2. Associate VDNS with IPAM
            3. Launch VN with IPAM
            4. Launch VM with VN Created above. This test verifies on launch of VM agent should update DNS 'A' and 'PTR' records
            5. Ping VMs using VM name
            6. Restart the named process in the active control node
            7. Ping VMs using VM name
        Pass criteria: Step 4, 5 and 7 should pass
        Maintainer: cf-test@juniper.net
        '''

        restart_process = 'NamedRestart'
        self.vdns_with_cn_dns_agent_restart(restart_process)
        return True

    @preposttest_wrapper
    def scale_vdns_records_restart_named(self):
        ''' 
        This test verifies vdns record scaling as well as record update after named restart.
        This test case is specifically for bug verification of bug ID 1583566 : [vDNS]: Records lost on named restart if scaled configuration is present 
        Steps:
            1.  Create vDNS server
            2.  Create 5000 records for the server.
            3.  Create IPAM and VN objects.
            4.  Restart contrail-named process on all control nodes.
            5.  Wait for the zone.jnl file to restore all the 5000 VDNS records.
            6.  Verify that all 5000 records are present in the zone file
        Pass criteria: All records should get restored on all control nodes.
        Maintainer: pulkitt@juniper.net
        '''
        vn_name = 'vn-vdns'
        domain_name = 'juniper.net'
        ttl = 100
        dns_data = VirtualDnsType( domain_name=domain_name, dynamic_records_from_client=True,
                        default_ttl_seconds=ttl, record_order='random', reverse_resolution=True, 
                        external_visible = True)
        ipam_name = 'ipamTest'
        dns_server_name = "vdnsTest"
        # Create VDNS server object.
        vdns_fixt = self.useFixture(VdnsFixture(
                    self.inputs, self.connections, vdns_name=dns_server_name, dns_data=dns_data))
        result, msg = vdns_fixt.verify_on_setup()
        self.assertTrue(result, msg)
        # Create IPAM management object
        dns_server = IpamDnsAddressType(
                        virtual_dns_server_name=vdns_fixt.vdns_fq_name)
        # Subnetting 11.11.0.0/16 into maximum 1024 subnets and mask of /26
        vn_ip = '11.11.0.0/16'
        network, prefix = vn_ip.split('/')
        record_counter = 5000
        for x in range(0,record_counter):
            record_name = "vDNSrecForAliasVM%d" % x
            actual_vm_name = "VM%d" % x
            vdns_rec_data = VirtualDnsRecordType(record_name, 'CNAME', 'IN', actual_vm_name, ttl)
            vdns_rec_fix = self.useFixture(VdnsRecordFixture(
                        self.inputs, self.connections, record_name, vdns_fixt.fq_name, vdns_rec_data))
        ipam_mgmt_obj = IpamType(ipam_dns_method='virtual-dns-server', ipam_dns_server=dns_server)
        # Associate VDNS with IPAM.
        ipam_fixt = self.useFixture(IPAMFixture(ipam_name, vdns_obj= vdns_fixt.obj,
                        connections=self.connections, ipamtype=ipam_mgmt_obj))
        assert ipam_fixt.verify_on_setup()
        vn_fixt = self.useFixture(VNFixture(self.connections, self.inputs,vn_name=vn_name,
                subnets=[vn_ip], ipam_fq_name=ipam_fixt.fq_name, option='contrail'))
        assert vn_fixt.verify_on_setup()
        self.logger.info("All configuration complete.")
        # restarting contrail-named on all control nodes
        self.inputs.stop_service('contrail-named', self.inputs.bgp_ips,
                                 container='named')
        sleep(10)
        self.inputs.start_service('contrail-named', self.inputs.bgp_ips,
                                  container='named')
        for ip in self.inputs.bgp_ips:
            assert self.inputs.verify_service_state(service='named', host=ip)[0]
        zoneFile = vn_fixt.vn_fq_name.split(':')[0] +'-' + dns_server_name + '.' + domain_name + '.zone.jnl'
        cmd = "ls -al /etc/contrail/dns/%s" % zoneFile
        for node in self.inputs.bgp_ips:
            output = self.inputs.run_cmd_on_server(node,cmd,
                                                   container='dns')
            if "No such file or directory" in output:
                msg = "Zone file not found for the configured domain on control node %s" % node
                self.logger.error("Zone file not found for the configured domain on control node %s" % node)
                result = False
                assert result, msg
            else:
                outputList = output.split()
                fileSize = outputList[4]
                while 1:
                    self.logger.debug("Waiting till the record file get updated completely")
                    sleep(10)
                    output = self.inputs.run_cmd_on_server(node,cmd,
                                                           container='dns')
                    outputList = output.split()
                    if outputList[4] == fileSize:
                        self.logger.debug("Size of zone file is constant now. File update completed.")
                        break
                    fileSize = outputList[4]
            # Command to Sync the jnl file with zone file.
            newcmd = "contrail-rndc -c /etc/contrail/dns/contrail-rndc.conf sync"
            self.inputs.run_cmd_on_server(node,newcmd,
                                          container='named')
            readFileCmd = "cat /etc/contrail/dns/%s" % zoneFile.rstrip('.jnl')
            fileContent = self.inputs.run_cmd_on_server(node, readFileCmd,
                                                        container='named')
            lines = fileContent.split('\n')
            count = 0
            for lineNumber in range(0,len(lines)):
                line = lines[lineNumber].split()
                if len(line) > 1:
                    if  line[1] == 'CNAME':
                        count = count +1
            self.logger.debug("Number of records file on control node %s are %d." % (node, count))
            if count ==5000:
                self.logger.info("All records restored correctly on control node %s" % node )
            else : 
                self.logger.error("Records lost after named restart on control node %s" % node)
                msg = "records lost after restart of named."
                result = False
                assert result, msg
    # end scale_vdns_records_restart_named
    
    @preposttest_wrapper
    def test_agent_query_all_dns_servers_policy_fixed(self):
        '''Agent to request all available named servers from Disocvery Server while 
           connecting to two in the list to send DNS records, but querying all.
           This script is specifically written to test 
           Bug Id 1551987 : "Agent to query all available bind server for vDNS records"
           Also, this script assumes that DNS policy is *fixed* which is the default value.
           Steps:
            1. Create a VN with IPAM having Virtual DNS configured.
            2. Create 2 VMs each on both compute nodes.
            3. Check that ping between 2 VMs on same compute and across different compute
            4. Ping local records and verify in introspect logs that DNS query is sent to all control nodes in cluster
            5. Search for all DNS servers assigned to vrouter agents
            6. Stop the *contrail-named* processes on both assigned DNS servers to vrouter agent of compute 1.
            7. Verify all cases of nslookup during and after subscription TTL expiry.
        Pass criteria: DNS queries should reach every DNS server in network and any server can resolve it.
        Entry Criteria: Minimum 3 control nodes and 2 Compute nodes are required for this test case.
        Maintainer: pulkitt@juniper.net'''
        if len(self.inputs.bgp_ips) <2 or len(self.inputs.compute_ips) < 2:
            skip = True
            msg = "Skipping this test case as minimum control nodes required are 2"
            raise testtools.TestCase.skipException(msg)
        vm_list = ['vm1-agent1', 'vm2-agent1', 'vm1-agent2', 'vm2-agent2']
        vn_name = 'vn1'
        vn_nets = {'vn1' : '10.10.10.0/24'}
        dns_server_name = 'vdns1'
        domain_name = 'juniper.net'
        ttl = 100
        ipam_name = 'ipam1'
        dns_data = VirtualDnsType(
            domain_name=domain_name, dynamic_records_from_client=True,
            default_ttl_seconds=ttl, record_order='random', reverse_resolution=True)
        vdns_fixt1 = self.useFixture(VdnsFixture(self.inputs, self.connections, 
            vdns_name=dns_server_name, dns_data=dns_data))
        result, msg = vdns_fixt1.verify_on_setup()
        self.assertTrue(result, msg)
        dns_server = IpamDnsAddressType(
            virtual_dns_server_name=vdns_fixt1.vdns_fq_name)
        ipam_mgmt_obj = IpamType(
            ipam_dns_method='virtual-dns-server', ipam_dns_server=dns_server)
        # Associate IPAM with  VDNS server Object
        ipam_fixt1 = self.useFixture(IPAMFixture(ipam_name, vdns_obj=vdns_fixt1.obj, 
                connections=self.connections, ipamtype=ipam_mgmt_obj))
        # Launch  VM with VN Created above.
        vn_fixt = self.useFixture(VNFixture(self.connections, self.inputs,\
                     vn_name=vn_name, subnets=[vn_nets['vn1']], \
                     ipam_fq_name=ipam_fixt1.fq_name, option='contrail'))
        vm_fixture = {}
        for vm in vm_list:
            if 'agent1' in vm:
                vm_fixture[vm] = self.useFixture(VMFixture(project_name=
                    self.inputs.project_name, connections=self.connections, 
                    vn_obj=vn_fixt.obj,vm_name=vm, 
                    node_name = self.inputs.compute_names[0]))
            elif 'agent2' in vm:
                vm_fixture[vm] = self.useFixture(VMFixture(project_name=
                    self.inputs.project_name, connections=self.connections,
                    vn_obj=vn_fixt.obj, vm_name=vm, 
                    node_name = self.inputs.compute_names[1]))
        for vm in vm_list:
            assert vm_fixture[vm].wait_till_vm_is_up()
        # Verify connectivity between all Agents after configuration of VMs
        self.assertTrue(vm_fixture['vm1-agent1'].ping_to_ip(ip='vm1-agent2', count=2))
        self.assertTrue(vm_fixture['vm1-agent1'].ping_to_ip(ip='vm2-agent1', count=2))
        self.assertTrue(vm_fixture['vm1-agent2'].ping_to_ip(ip='vm1-agent1', count=2))
        self.assertTrue(vm_fixture['vm1-agent2'].ping_to_ip(ip='vm2-agent2', count=2))
        # Ping from vm of agent 1 to VM of agent 2 and verify query sent to all DNS servers
        inspect_h_agent1 = self.agent_inspect[vm_fixture['vm1-agent1'].vm_node_ip]
        output_1 = str(inspect_h_agent1.get_vna_dns_query_to_named())
        self.assertTrue(vm_fixture['vm1-agent1'].ping_to_ip(ip='vm1-agent2', count=2))
        output_2 = str(inspect_h_agent1.get_vna_dns_query_to_named())
        diff = difflib.ndiff(output_1,output_2)
        delta = ''.join(x[2:] for x in diff if x.startswith('+ '))
        # Getting the list of DNS servers in use by every Compute node
        for i in range(0,len(self.inputs.bgp_ips)):
            if "DNS query sent to named server : %s" % self.inputs.bgp_control_ips[i] in delta:
                self.logger.debug("DNS query sent successfully to DNS server on %s" % 
                                  self.inputs.bgp_control_ips[i])
            else:
                self.logger.error("DNS query not sent to DNS server running on %s" % 
                                  self.inputs.bgp_control_ips[i])
                errmsg = "DNS query not sent to all DNS servers in the network"
                self.logger.error(errmsg)
                assert False, errmsg
        dns_list_all_compute_nodes = []
        for entry in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[entry]
            dns_list_all_compute_nodes.append(
                    inspect_h.get_vna_dns_server())
            self.logger.debug("The compute node %s is connected to DNS servers: %s" 
                        %(entry,dns_list_all_compute_nodes[-1]))
        # Specifically for fixed policy, verifying that all agents connected to same set of DNS servers
        for i in range(0,(len(dns_list_all_compute_nodes)-1)):
            if set(dns_list_all_compute_nodes[i]) == set(dns_list_all_compute_nodes[i+1]):
               self.logger.info("All computes connected to same DNS server as expected")
            else:
                errmsg = "Computes connected to different DNS servers. This is not expected with policy as fixed"
                self.logger.error(errmsg)
                assert False, errmsg
        # Making the named down on Control nodes associated with 1st vrouter agent
        # Verifying that DNS resolve the queries as per the assigned DNS servers
        for nodes in dns_list_all_compute_nodes[0]:
            index = self.inputs.bgp_control_ips.index(nodes)
            self.inputs.stop_service("contrail-named",[self.inputs.bgp_ips[index]],
                                     container='named')
            self.addCleanup(self.inputs.start_service,'contrail-named',\
                             [self.inputs.bgp_ips[index]],
                             container='named')
        verify = "once"
        cmd_for_agent2 = 'nslookup -timeout=1 vm2-agent2' + '| grep ' +\
                       '\'' + vm_fixture['vm2-agent2'].vm_ip + '\''
        cmd_for_agent1 = 'nslookup -timeout=1 vm2-agent1' + '| grep ' +\
                       '\'' + vm_fixture['vm2-agent1'].vm_ip + '\''
        for i in range(0,360):
            new_dns_list = []
            for entry in self.inputs.compute_ips[0],self.inputs.compute_ips[1]:
                inspect_h = self.agent_inspect[entry]
                new_dns_list.append(
                    inspect_h.get_vna_dns_server())
                self.logger.debug("The compute node %s is connected to DNS servers: %s" 
                        %(entry,new_dns_list[-1]))
            if i == 0 and new_dns_list[0] == new_dns_list[1] and\
                new_dns_list[0]==dns_list_all_compute_nodes[0]:
                assert self.verify_ns_lookup_data(vm_fixture['vm1-agent1'],\
                                     cmd_for_agent2, vm_fixture['vm2-agent2'].vm_ip,
                                     expected_result = False)
                assert self.verify_ns_lookup_data(vm_fixture['vm1-agent1'],\
                                     cmd_for_agent1, vm_fixture['vm2-agent1'].vm_ip,
                                     expected_result = False)
                continue
            elif new_dns_list[0] != new_dns_list[1] and verify=="once" :
                if new_dns_list[0] == dns_list_all_compute_nodes[0] and \
                new_dns_list[1] != dns_list_all_compute_nodes[1]:
                    assert self.verify_ns_lookup_data(vm_fixture['vm1-agent1'],\
                                         cmd_for_agent1, vm_fixture['vm2-agent1'].vm_ip,
                                         expected_result = False)
                    assert self.verify_ns_lookup_data(vm_fixture['vm1-agent2'],\
                                         cmd_for_agent1, vm_fixture['vm2-agent1'].vm_ip,
                                         expected_result = False)
                    assert self.verify_ns_lookup_data(vm_fixture['vm1-agent2'],\
                                         cmd_for_agent2, vm_fixture['vm2-agent2'].vm_ip)
                    assert self.verify_ns_lookup_data(vm_fixture['vm1-agent1'],\
                                         cmd_for_agent2, vm_fixture['vm2-agent2'].vm_ip)
                elif new_dns_list[0] != dns_list_all_compute_nodes[0] and \
                new_dns_list[1] == dns_list_all_compute_nodes[1]:
                    assert self.verify_ns_lookup_data(vm_fixture['vm1-agent2'],\
                                         cmd_for_agent2, vm_fixture['vm2-agent2'].vm_ip,
                                         expected_result = False)
                    assert self.verify_ns_lookup_data(vm_fixture['vm1-agent1'],\
                                         cmd_for_agent2, vm_fixture['vm2-agent2'].vm_ip,
                                         expected_result = False)
                    assert self.verify_ns_lookup_data(vm_fixture['vm1-agent1'],\
                                        cmd_for_agent1, vm_fixture['vm2-agent1'].vm_ip)
                    assert self.verify_ns_lookup_data(vm_fixture['vm1-agent2'],\
                                         cmd_for_agent1, vm_fixture['vm2-agent1'].vm_ip)
                verify="done"
                continue
            elif new_dns_list[0] != dns_list_all_compute_nodes[0] and \
            new_dns_list[1] != dns_list_all_compute_nodes[1]:
                # Allowing some time for new DNS server to populate the records. 
                assert self.verify_ns_lookup_data(vm_fixture['vm1-agent1'],\
                                    cmd_for_agent2, vm_fixture['vm2-agent2'].vm_ip)
                assert self.verify_ns_lookup_data(vm_fixture['vm1-agent1'],\
                                     cmd_for_agent1, vm_fixture['vm2-agent1'].vm_ip)
                assert self.verify_ns_lookup_data(vm_fixture['vm1-agent2'],\
                                     cmd_for_agent2, vm_fixture['vm2-agent2'].vm_ip)
                assert self.verify_ns_lookup_data(vm_fixture['vm1-agent2'],\
                                     cmd_for_agent1, vm_fixture['vm2-agent1'].vm_ip)
                self.assertTrue(vm_fixture['vm1-agent1'].ping_to_ip(ip='vm2-agent2', count=2))
                self.assertTrue(vm_fixture['vm1-agent1'].ping_to_ip(ip='vm2-agent1', count=2))
                self.assertTrue(vm_fixture['vm1-agent2'].ping_to_ip(ip='vm2-agent2', count=2))
                self.assertTrue(vm_fixture['vm1-agent2'].ping_to_ip(ip='vm2-agent1', count=2))
                break
            else:
                self.logger.debug("Waiting till new DNS server assignment takes place for agent 1")
                sleep(5)
                continue

    class InitForZoneTests(object):
        '''
        Initialisation of variables to be used in 2 different test cases
        "test_vdns_with_same_zone" and "test_vdns_with_diff_zone"
        '''
        def __init__(self):
            self.project_list = ['project1',
                                 'project2',
                                 'project3',
                                 'project4',
                                 'project5',
                                 'project6']
            self.ipam_list = {'project1': 'ipam1',
                             'project2': 'ipam2',
                             'project3': 'ipam3',
                             'project4': 'ipam4',
                             'project5': 'ipam5',
                             'project6': 'ipam6'}
            self.vn_list = {'project1': 'vn1',
                   'project2': 'vn2',
                   'project3': 'vn3',
                   'project4': 'vn4',
                   'project5': 'vn5',
                   'project6': 'vn6'}
            self.vn_nets = {'project1': ['10.10.10.0/24'],
                   'project2': ['20.10.10.0/24'],
                   'project3': ['30.10.10.0/24'],
                   'project4': ['40.10.10.0/24'],
                   'project5': ['50.10.10.0/24'],
                   'project6': ['60.10.10.0/24']}
            self.vm_list = {'project1': 'vm1',
                   'project2': 'vm2',
                   'project3': 'vm3',
                   'project4': 'vm4',
                   'project5': 'vm5',
                   'project6': 'vm6'}
            self.proj_user = {'project1': 'user1',
                     'project2': 'user2',
                     'project3': 'user3',
                     'project4': 'user4',
                     'project5': 'user5',
                     'project6': 'user6'}
            self.proj_pass = {'project1': 'user1',
                     'project2': 'user2',
                     'project3': 'user3',
                     'project4': 'user4',
                     'project5': 'user5',
                     'project6': 'user6'}
            self.proj_vdns = {'project1': 'vdns1',
                     'project2': 'vdns2',
                     'project3': 'vdns3',
                     'project4': 'vdns4',
                     'project5': 'vdns5',
                     'project6': 'vdns6'}
    
    @preposttest_wrapper
    def test_vdns_with_same_zone(self):
        ''' Test vdns in same zone with multi projects/vdns-servers '''
        var_obj = self.InitForZoneTests()
        vdns_fixt1 = {}
        ipam_mgmt_obj = {}
        for project in var_obj.project_list:
            dns_server_name = var_obj.proj_vdns[project]
            self.logger.info(
                'Creating vdns server:%s in project:%s',
                dns_server_name,
                project)
            domain_name = 'juniper.net'
            ttl = 100
            # VDNS creation
            dns_data = VirtualDnsType(
                domain_name=domain_name, dynamic_records_from_client=True,
                default_ttl_seconds=ttl, record_order='random')
            vdns_fixt1[project] = self.useFixture(
                VdnsFixture(
                    self.inputs,
                    self.connections,
                    vdns_name=dns_server_name,
                    dns_data=dns_data))
            result, msg = vdns_fixt1[project].verify_on_setup()
            self.assertTrue(result, msg)
            dns_server = IpamDnsAddressType(
                virtual_dns_server_name=vdns_fixt1[project].vdns_fq_name)
            ipam_mgmt_obj[project] = IpamType(
                ipam_dns_method='virtual-dns-server',
                ipam_dns_server=dns_server)
        ipam_fixt = {}
        vn_fixt = {}
        vm_fix = {}
        pol_fixt = {}
        for proj in var_obj.project_list:
            # User creation
            user_fixture = self.useFixture(
                UserFixture(
                    connections=self.admin_connections,
                    username=var_obj.proj_user[proj],
                    password=var_obj.proj_pass[proj]))
            # Project creation
            project_fixture = self.useFixture(
                ProjectFixture(
                    project_name=proj,
                    username=var_obj.proj_user[proj],
                    password=var_obj.proj_pass[proj],
                    connections=self.admin_connections))
            user_fixture.add_user_to_tenant(proj, var_obj.proj_user[proj], 'admin')
            project_fixture.set_user_creds(var_obj.proj_user[proj], var_obj.proj_pass[proj])
            project_inputs = ContrailTestInit(
                    self.input_file,
                    stack_user=project_fixture.project_username,
                    stack_password=project_fixture.project_user_password,
                    stack_tenant=proj,
                    logger=self.logger)
            project_connections = ContrailConnections(project_inputs,
                                                      logger=self.logger)
            self.logger.info(
                'Default SG to be edited for allow all on project: %s' % proj)
            project_fixture.set_sec_group_for_allow_all(proj, 'default')
            # Ipam creation
            ipam_fixt[proj] = self.useFixture(IPAMFixture(var_obj.ipam_list[proj], vdns_obj= vdns_fixt1[proj].obj,
                        connections=project_connections, ipamtype=ipam_mgmt_obj[proj]))
            # VN Creation
            vn_fixt[proj] = self.useFixture(
                VNFixture(
                    project_name=proj,
                    connections=project_connections,
                    vn_name=var_obj.vn_list[proj],
                    inputs=project_inputs,
                    subnets=var_obj.vn_nets[proj],
                    ipam_fq_name=ipam_fixt[proj].getObj().get_fq_name()))
            vn_quantum_obj = self.orch.get_vn_obj_if_present(vn_name=var_obj.vn_list[proj], project_id=project_fixture.uuid)
            # VM creation
            vm_fix[proj] = self.useFixture(
                VMFixture(
                    project_name=proj,
                    connections=project_connections,
                    vn_obj=vn_quantum_obj,
                    vm_name=var_obj.vm_list[proj]))
            vm_fix[proj].verify_vm_launched()
            vm_fix[proj].verify_on_setup()
            vm_fix[proj].wait_till_vm_is_up()
            msg = "Ping by using name %s is failed. Dns server \
                  should resolve VM name to IP" % (var_obj.vm_list[proj])
            self.assertTrue(
                vm_fix[proj].ping_with_certainty(ip=var_obj.vm_list[proj]), msg)
            vm_ip = vm_fix[proj].get_vm_ip_from_vm(
                vn_fq_name=vm_fix[proj].vn_fq_name)
            vm_rev_ip = vm_ip.split('.')
            vm_rev_ip = '.'.join(
                (vm_rev_ip[3], vm_rev_ip[2], vm_rev_ip[1], vm_rev_ip[0]))
            vm_rev_ip = vm_rev_ip + '.in-addr.arpa'
            rev_zone = var_obj.vn_nets[proj][0].split('/')[0].split('.')
            rev_zone = '.'.join((rev_zone[0], rev_zone[1], rev_zone[2]))
            rev_zone = rev_zone + '.in-addr.arpa'
            # Frame the Expected DNS data for VM, one for 'A' record and
            # another 'PTR' record.
            rec_name = var_obj.vm_list[proj] + "." + domain_name
            agent_inspect_h = self.agent_inspect[vm_fix[proj].vm_node_ip]
            assigned_dns_ips = agent_inspect_h.get_vna_dns_server()
            vm_dns_exp_data = [{'rec_data': vm_ip,
                                'rec_type': 'A',
                                'rec_class': 'IN',
                                'rec_ttl': str(ttl),
                                'rec_name': rec_name,
                                'installed': 'yes',
                                'zone': domain_name},
                               {'rec_data': rec_name,
                                'rec_type': 'PTR',
                                'rec_class': 'IN',
                                'rec_ttl': str(ttl),
                                'rec_name': vm_rev_ip,
                                'installed': 'yes',
                                'zone': rev_zone}]
            self.verify_vm_dns_data(vm_dns_exp_data, assigned_dns_ips[0])
            vm_dns_exp_data = []
        self.logger.info(
            'Restart supervisor-config & supervisor-control and test ping')
        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('supervisor-control', [bgp_ip],
                                         container='dns')
            self.inputs.restart_service('supervisor-control', [bgp_ip],
                                         container='named')
            self.inputs.restart_service('supervisor-control', [bgp_ip],
                                         container='control')
        for cfgm_ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('supervisor-config', [cfgm_ip],
                                         container='api-server')
        status_checker = ContrailStatusChecker(self.inputs)
        self.logger.debug("Waiting for all the services to be UP")
        assert status_checker.wait_till_contrail_cluster_stable()[0],\
                "All services could not come UP after restart"
        for proj in var_obj.project_list:
            msg = "Ping by using name %s is failed. Dns server \
                  should resolve VM name to IP" % (var_obj.vm_list[proj])
            self.assertTrue(
                vm_fix[proj].ping_with_certainty(ip=var_obj.vm_list[proj]), msg)
        return True
    # end test_vdns_with_same_zone
    
    
    @preposttest_wrapper
    def test_vdns_with_diff_zone(self):
        ''' Test vdns in different zones with multi projects '''
        var_obj = self.InitForZoneTests()
        vdns_fixt1 = {}
        ipam_mgmt_obj = {}
        for project in var_obj.project_list:
            dns_server_name = var_obj.proj_vdns[project]
            self.logger.info(
                'Creating vdns server:%s in project:%s',
                dns_server_name,
                project)
            domain_name = '%s.net' % (project)
            ttl = 100
            # VDNS creation
            dns_data = VirtualDnsType(
                domain_name=domain_name, dynamic_records_from_client=True,
                default_ttl_seconds=ttl, record_order='random')
            vdns_fixt1[project] = self.useFixture(
                VdnsFixture(
                    self.inputs,
                    self.connections,
                    vdns_name=dns_server_name,
                    dns_data=dns_data))
            result, msg = vdns_fixt1[project].verify_on_setup()
            self.assertTrue(result, msg)
            dns_server = IpamDnsAddressType(
                virtual_dns_server_name=vdns_fixt1[project].vdns_fq_name)
            ipam_mgmt_obj[project] = IpamType(
                ipam_dns_method='virtual-dns-server',
                ipam_dns_server=dns_server)
        ipam_fixt = {}
        vn_fixt = {}
        vm_fix = {}
        pol_fixt = {}
        for proj in var_obj.project_list:
            # User creation
            user_fixture = self.useFixture(
                UserFixture(
                    connections=self.admin_connections,
                    username=var_obj.proj_user[proj],
                    password=var_obj.proj_pass[proj]))
            # Project creation
            project_fixture = self.useFixture(
                ProjectFixture(
                    project_name=proj,
                    username=var_obj.proj_user[proj],
                    password=var_obj.proj_pass[proj],
                    connections=self.admin_connections))
            user_fixture.add_user_to_tenant(proj, var_obj.proj_user[proj], 'admin')
            project_fixture.set_user_creds(var_obj.proj_user[proj], var_obj.proj_pass[proj])
            project_inputs = ContrailTestInit(
                    self.input_file,
                    stack_user=project_fixture.project_username,
                    stack_password=project_fixture.project_user_password,
                    stack_tenant=proj,
                    logger=self.logger)
            project_connections = ContrailConnections(project_inputs,
                                                      logger=self.logger)
            self.logger.info(
                'Default SG to be edited for allow all on project: %s' % proj)
            project_fixture.set_sec_group_for_allow_all(proj, 'default')
            # Ipam creation
            ipam_fixt[proj] = self.useFixture(IPAMFixture(var_obj.ipam_list[proj], vdns_obj= vdns_fixt1[proj].obj,
                        connections=project_connections, ipamtype=ipam_mgmt_obj[proj]))
            # VN Creation
            vn_fixt[proj] = self.useFixture(
                VNFixture(
                    project_name=proj,
                    connections=project_connections,
                    vn_name=var_obj.vn_list[proj],
                    inputs=project_inputs,
                    subnets=var_obj.vn_nets[proj],
                    ipam_fq_name=ipam_fixt[proj].getObj().get_fq_name()))
            vn_quantum_obj = self.orch.get_vn_obj_if_present(vn_name=var_obj.vn_list[proj], project_id=project_fixture.uuid)
            # VM creation
            vm_fix[proj] = self.useFixture(
                VMFixture(
                    project_name=proj,
                    connections=project_connections,
                    vn_obj=vn_quantum_obj,
                    vm_name=var_obj.vm_list[proj]))
            vm_fix[proj].verify_vm_launched()
            vm_fix[proj].verify_on_setup()
            vm_fix[proj].wait_till_vm_is_up()
            msg = "Ping by using name %s is failed. Dns server \
                  should resolve VM name to IP" % (var_obj.vm_list[proj])
            self.assertTrue(
                vm_fix[proj].ping_with_certainty(ip=var_obj.vm_list[proj]), msg)
            vm_ip = vm_fix[proj].get_vm_ip_from_vm(
                vn_fq_name=vm_fix[proj].vn_fq_name)
            vm_rev_ip = vm_ip.split('.')
            vm_rev_ip = '.'.join(
                (vm_rev_ip[3], vm_rev_ip[2], vm_rev_ip[1], vm_rev_ip[0]))
            vm_rev_ip = vm_rev_ip + '.in-addr.arpa'
            rev_zone = var_obj.vn_nets[proj][0].split('/')[0].split('.')
            rev_zone = '.'.join((rev_zone[0], rev_zone[1], rev_zone[2]))
            rev_zone = rev_zone + '.in-addr.arpa'
            # Frame the Expected DNS data for VM, one for 'A' record and
            # another 'PTR' record.
            domain_name = '%s.net' % (proj)
            rec_name = var_obj.vm_list[proj] + "." + domain_name
            agent_inspect_h = self.agent_inspect[vm_fix[proj].vm_node_ip]
            assigned_dns_ips = agent_inspect_h.get_vna_dns_server()
            vm_dns_exp_data = [{'rec_data': vm_ip,
                                'rec_type': 'A',
                                'rec_class': 'IN',
                                'rec_ttl': str(ttl),
                                'rec_name': rec_name,
                                'installed': 'yes',
                                'zone': domain_name},
                               {'rec_data': rec_name,
                                'rec_type': 'PTR',
                                'rec_class': 'IN',
                                'rec_ttl': str(ttl),
                                'rec_name': vm_rev_ip,
                                'installed': 'yes',
                                'zone': rev_zone}]
            self.verify_vm_dns_data(vm_dns_exp_data, assigned_dns_ips[0])
            vm_dns_exp_data = []
        self.logger.info(
            'Restart supervisor-config & supervisor-control and test ping')
        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('supervisor-control', [bgp_ip],
                                        container='control')
            self.inputs.restart_service('supervisor-control', [bgp_ip],
                                        container='dns')
            self.inputs.restart_service('supervisor-control', [bgp_ip],
                                        container='named')
        for cfgm_ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('supervisor-config', [cfgm_ip],
                                         container='api-server')
        status_checker = ContrailStatusChecker(self.inputs)
        self.logger.debug("Waiting for all the services to be UP")
        assert status_checker.wait_till_contrail_cluster_stable()[0],\
                "All services could not come UP after restart"
        for proj in var_obj.project_list:
            msg = "Ping by using name %s is failed. Dns server \
                  should resolve VM name to IP" % (var_obj.vm_list[proj])
            self.assertTrue(
                vm_fix[proj].ping_with_certainty(ip=var_obj.vm_list[proj]), msg)
        return True
    # end test_vdns_with_diff_zone
class TestvDNS1(BasevDNSTest):

    @classmethod
    def setUpClass(cls):
        super(TestvDNS1, cls).setUpClass()

    def runTest(self):
        pass
    #end runTest 

    # This test creates 16 levels of vdns servers vdns1,vdns2,vdns3...vdns16.
    #      The VDNS server are configured as shown below.
    #                         vdns1 (domain: juniper.net)
    #                        ^
    #                       /
    #                      /
    #                    vdns2(domain: one.juniper.net)
    #                    ^
    #                   /
    #                  /
    #                 vdns3(domain: two.one.juniper.net)
    #                ...
    #                vdns16
    #
    @preposttest_wrapper
    @skip_because(feature='multi-ipam')
    def test_vdns_tree_scaling(self):
        ''' 1. This test creates 16 levels of vdns servers vdns1,vdns2,vdns3...vdns16.
               The VDNS server are configured as shown below. 
                             vdns1 (domain: juniper.net)
                             ^     
                            /       
                           /         
                         vdns2(domain: one.juniper.net)
                         ^       
                        /
                       /
                      vdns3(domain: two.one.juniper.net)
                      ...
                     vdns16
            2. VDNS2,VDNS3...vdns16 needs to point next vdns server except for VDNS1 which is root
            3. Configure NS records for Next DNS server
            4. Associate IPAM with VDNS server Object at each level
            5. Configure VN in IPAM created and launch VM in VN at each level
            6. perform NS lookup for each level
        Pass criteria: Step 6 should pass
        Maintainer: cf-test@juniper.net  
        '''

        ttl = 1000
        raise self.skipTest("Skipping test case,till CEM-4604 is fixed.")
        project_fixture = self.useFixture(ProjectFixture(
            project_name=self.inputs.project_name, connections=self.connections))
        project_connections = project_fixture.get_project_connections()
        dns_server_name_list = [
            'vdns501', 'vdns502', 'vdns503', 'vdns504', 'vdns505', 'vdns506', 'vdns507',
            'vdns508', 'vdns509', 'vdns510', 'vdns511', 'vdns512', 'vdns513', 'vdns514', 'vdns515', 'vdns516']
        domain_name_list = {
            'vdns501': 'juniper.net',
            'vdns502': 'two.juniper.net',
            'vdns503': 'three.two.juniper.net',
            'vdns504': 'four.three.two.juniper.net',
            'vdns505': 'five.four.three.two.juniper.net',
            'vdns506': 'six.five.four.three.two.juniper.net',
            'vdns507': 'seven.six.five.four.three.two.juniper.net',
            'vdns508': 'eight.seven.six.five.four.three.two.juniper.net',
            'vdns509': 'nine.eight.seven.six.five.four.three.two.juniper.net',
            'vdns510': 'ten.nine.eight.seven.six.five.four.three.two.juniper.net',
            'vdns511': '11.ten.nine.eight.seven.six.five.four.three.two.juniper.net',
            'vdns512': '12.11.ten.nine.eight.seven.six.five.four.three.two.juniper.net',
            'vdns513': '13.12.11.ten.nine.eight.seven.six.five.four.three.two.juniper.net',
            'vdns514': '14.13.12.11.ten.nine.eight.seven.six.five.four.three.two.juniper.net',
            'vdns515': '15.14.13.12.11.ten.nine.eight.seven.six.five.four.three.two.juniper.net',
            'vdns516': '16.15.14.13.12.11.ten.nine.eight.seven.six.five.four.three.two.juniper.net'}
        next_vdns_list = {
            'vdns501': 'vdns502', 'vdns502': 'vdns503', 'vdns503': 'vdns504', 'vdns504': 'vdns505', 'vdns505': 'vdns506', 'vdns506': 'vdns507', 'vdns507': 'vdns508', 'vdns508': 'vdns509', 'vdns509': 'vdns510', 'vdns510': 'vdns511', 'vdns511': 'vdns512', 'vdns512': 'vdns513', 'vdns513': 'vdns514', 'vdns514': 'vdns515', 'vdns515': 'vdns516', 'vdns516': 'none'}
        rec_names = {
            'vdns501': 'test-rec501', 'vdns502': 'test-rec502', 'vdns503': 'test-rec503', 'vdns504': 'test-rec504', 'vdns505': 'test-rec505', 'vdns506': 'test-rec506', 'vdns507': 'test-rec507', 'vdns508': 'test-rec508', 'vdns509': 'test-rec509', 'vdns510': 'test-rec510', 'vdns511': 'test-rec511', 'vdns512': 'test-rec512', 'vdns513': 'test-rec513', 'vdns514': 'test-rec514', 'vdns515': 'test-rec515', 'vdns516': 'test-rec516'}
        ipam_dns_list = {
            'vdns501': 'ipam501', 'vdns502': 'ipam502', 'vdns503': 'ipam503', 'vdns504': 'ipam504', 'vdns505': 'ipam505', 'vdns506': 'ipam506', 'vdns507': 'ipam507', 'vdns508': 'ipam508','vdns509': 'ipam509', 'vdns510': 'ipam510', 'vdns511': 'ipam511', 'vdns512': 'ipam512', 'vdns513': 'ipam513', 'vdns514': 'ipam514', 'vdns515': 'ipam515', 'vdns516': 'ipam516'}
        vn_dns_list = {
            'vdns501': ['vn501', ['10.10.1.0/24']], 'vdns502': ['vn502', ['10.10.2.0/24']], 'vdns503': ['vn503', ['10.10.3.0/24']], 'vdns504': ['vn504', ['10.10.4.0/24']], 'vdns505': ['vn505', ['10.10.5.0/24']], 'vdns506': ['vn506', ['10.10.6.0/24']], 'vdns507': ['vn507', ['10.10.7.0/24']], 'vdns508': ['vn508', ['10.10.8.0/24']], 'vdns509': ['vn509', ['10.10.9.0/24']], 'vdns510': ['vn510', ['10.10.10.0/24']], 'vdns511': ['vn511', ['10.10.11.0/24']], 'vdns512': ['vn512', ['10.10.12.0/24']], 'vdns513': ['vn513', ['10.10.13.0/24']], 'vdns514': ['vn514', ['10.10.14.0/24']], 'vdns515': ['vn515', ['10.10.15.0/24']], 'vdns516': ['vn516', ['10.10.16.0/24']]}
        vm_dns_list = {
            'vdns501': 'vm501', 'vdns502': 'vm502', 'vdns503': 'vm503', 'vdns504': 'vm504', 'vdns505': 'vm505', 'vdns506': 'vm506', 'vdns507': 'vm507', 'vdns508': 'vm508',
            'vdns509': 'vm509', 'vdns510': 'vm510', 'vdns511': 'vm511', 'vdns512': 'vm512', 'vdns513': 'vm513', 'vdns514': 'vm514', 'vdns515': 'vm515', 'vdns516': 'vm516'}
        vm_ip_dns_list = {}
        vdns_fix = {}
        vdns_data = {}
        vdns_rec = {}
        next_dns = None
        # DNS configuration
        for dns_name in dns_server_name_list:
            # VNDS1 is root, so Next VDNS entry is not required.
            if dns_name == 'vdns501':
                vdns_data[dns_name] = VirtualDnsType(domain_name=domain_name_list[
                                                     dns_name], dynamic_records_from_client=True, default_ttl_seconds=ttl, record_order='random')
            else:
                # VDNS2,VDNS3...vdns16 needs to point next vdns server.
                vdns_data[dns_name] = VirtualDnsType(
                    domain_name=domain_name_list[
                        dns_name], dynamic_records_from_client=True,
                    default_ttl_seconds=ttl, record_order='random', next_virtual_DNS=next_dns.vdns_fq_name)
            vdns_fix[dns_name] = self.useFixture(VdnsFixture(
                self.inputs, self.connections, vdns_name=dns_name, dns_data=vdns_data[dns_name]))
            result, msg = vdns_fix[dns_name].verify_on_setup()
            self.assertTrue(result, msg)
            next_dns = vdns_fix[dns_name]

        #  Configure NS records for Next DNS server
        for dns_name in dns_server_name_list:
            if next_vdns_list[dns_name] != 'none':
                next_dns = next_vdns_list[dns_name]
                vdns_rec_data = VirtualDnsRecordType(
                    domain_name_list[next_dns], 'NS', 'IN', vdns_fix[next_dns].vdns_fq_name, ttl)
                vdns_rec[dns_name] = self.useFixture(VdnsRecordFixture(
                    self.inputs, self.connections, rec_names[dns_name], vdns_fix[dns_name].get_fq_name(), vdns_rec_data))
                result, msg = vdns_rec[dns_name].verify_on_setup()
                self.assertTrue(result, msg)
        vn_fixt = {}
        vm_fixture = {}
        ipam_fixt = {}

        dns_server_name_list1 = [ 'vdns501', 'vdns505', 'vdns516']

        for dns_name in dns_server_name_list1:
            dns_server = IpamDnsAddressType(
                virtual_dns_server_name=vdns_fix[dns_name].vdns_fq_name)
            ipam_mgmt_obj = IpamType(
                ipam_dns_method='virtual-dns-server', ipam_dns_server=dns_server)
            # Associate IPAM with VDNS server Object
            ipam_fixt[dns_name] = self.useFixture(IPAMFixture(ipam_dns_list[dns_name], vdns_obj=
                                                  vdns_fix[dns_name].obj, connections=project_connections, ipamtype=ipam_mgmt_obj))
            # Launch VN
            vn_fixt[dns_name] = self.useFixture(
                VNFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_name=vn_dns_list[dns_name][0], inputs=self.inputs, subnets=vn_dns_list[dns_name][1], ipam_fq_name=ipam_fixt[dns_name].getObj().get_fq_name()))
            # Launch VM
            vm_fixture[dns_name] = self.useFixture(VMFixture(
                project_name=self.inputs.project_name, connections=self.connections, vn_obj=vn_fixt[dns_name].obj, vm_name=vm_dns_list[dns_name]))
            vm_fixture[dns_name].verify_vm_launched()
            vm_fixture[dns_name].verify_on_setup()
            vm_fixture[dns_name].wait_till_vm_is_up()
            vm_ip_dns_list[dns_name] = vm_fixture[dns_name].vm_ip
        # perform NS lookup for each level
        import re
        sleep(300)
        sleep(300)
        sleep(120)

        for dns in dns_server_name_list1:
            for dns_name in dns_server_name_list1:
                cmd = 'nslookup ' + \
                    vm_dns_list[dns_name] + '.' + domain_name_list[dns_name]
                self.logger.info(
                    'VM Name is ---> %s\t cmd is---> %s', vm_dns_list[dns], cmd)
                vm_fixture[dns].run_cmd_on_vm(cmds=[cmd])
                result = vm_fixture[dns].return_output_cmd_dict[cmd]
                result = result.replace("\r", "")
                result = result.replace("\t", "")
                result = result.replace("\n", " ")
                m_obj = re.search(
                    r"Address:[0-9.]*#[0-9]*\s*.*Name:(.*\.juniper\.net)\s*Address:\s*([0-9.]*)", result)
                if not m_obj:
                    self.assertTrue(
                        False, 'record search is failed,please check syntax of the regular expression/NSlookup is failed')
                print ('vm_name is ---> %s \t ip-address is ---> %s' %
                       (m_obj.group(1), m_obj.group(2)))
                vm_name_to_verify = vm_dns_list[dns_name] + \
                    '.' + domain_name_list[dns_name]
                self.assertEqual(m_obj.group(1), vm_name_to_verify,
                                 'VM name is not matching with nslookup command output')
                self.assertEqual(m_obj.group(2), vm_ip_dns_list[
                                 dns_name], 'IP Address is not matching with nslookup command output')
        return True

class TestvDNS2(BasevDNSTest):

    @classmethod
    def setUpClass(cls):
        super(TestvDNS2, cls).setUpClass()

    def runTest(self):
        pass
    #end runTest 

    @preposttest_wrapper
    @skip_because(feature='multi-ipam')
    def test_vdns_server_scaling(self):
        ''' This Test tests vdns server scaling
            1. Launch 1000 VDNS server objects
            2. Associate IPAM with each VDNS server Object
            3. Launch one VN in using each IPAM also launch one VM per VN
            4. nslookup for vm_name for all VMs should pass
        Pass criteria: Step 6 should pass
        Maintainer: cf-test@juniper.net'''

        ttl = 100
        # Number of VDNS servers
        raise self.skipTest("Skipping test case,till CEM-4604 is fixed.")
        vdns_scale = 1000
        # Number of records per server
        record_num = 1
        project_fixture = self.useFixture(ProjectFixture(
            project_name=self.inputs.project_name, connections=self.connections))
        project_connections = project_fixture.get_project_connections()
        vdns_fixt = {}
        vdns_verify = []
        i = 1
        j = 1
        for num in range(1, vdns_scale + 1):
            self.logger.info('Creating %s vdns server', num)
            domain_name = 'vdns1111' + str(num) + '.net'
            vdnsName = 'vdns1111' + str(num)
            dns_data = VirtualDnsType(
                domain_name=domain_name, dynamic_records_from_client=True,
                default_ttl_seconds=ttl, record_order='random')
            vdns_fixt[vdnsName] = self.useFixture(
                VdnsFixture(self.inputs, self.connections, vdns_name=vdnsName, dns_data=dns_data))
            for rec_num in range(1, record_num + 1):
                self.logger.info(
                    'Creating %s record for vdns server %s', rec_num, num)
                rec = 'test-rec-' + str(j) + '-' + str(i)
                rec_ip = '1.' + '1.' + str(j) + '.' + str(i)
                rec_name = 'rec' + str(j) + '-' + str(i)
                vdns_rec_data = VirtualDnsRecordType(
                    rec_name, 'A', 'IN', rec_ip, ttl)
                vdns_rec_fix = self.useFixture(VdnsRecordFixture(
                    self.inputs, self.connections, rec, vdns_fixt[vdnsName].get_fq_name(), vdns_rec_data))
                sleep(1)
                i = i + 1
                if i > 253:
                    j = j + 1
                    i = 1
            if num % 200 == 0:
                vdns_verify.append(vdnsName)

        vm_fixture = {}
        i = 1
        # Sleep for some time - DNS takes some time to sync with BIND server
        self.logger.info(
            'Sleep for 180sec to sync vdns server with bind server')
        sleep(180)
        for vdns in vdns_verify:
            ipam_name = 'ipam1111-' + str(i)
            vn_name = 'vn1111-' + str(i)
            subnet = '10.10.' + str(i) + '.0/24'
            vm_name = 'vm1111' + str(i)
            vm_domain_name = vm_name + '.' + vdns + '.net'
            dns_server = IpamDnsAddressType(
                virtual_dns_server_name=vdns_fixt[vdns].vdns_fq_name)
            ipam_mgmt_obj = IpamType(
                ipam_dns_method='virtual-dns-server', ipam_dns_server=dns_server)
            # Associate IPAM with VDNS server Object
            ipam_fixt = self.useFixture(IPAMFixture(ipam_name, vdns_obj= vdns_fixt[vdns].obj, connections=project_connections, ipamtype=ipam_mgmt_obj))
            # Launch VN
            vn_fixt = self.useFixture(
                VNFixture(
                    project_name=self.inputs.project_name, connections=self.connections,
                    vn_name=vn_name, inputs=self.inputs, subnets=[subnet], ipam_fq_name=ipam_fixt.getObj().get_fq_name()))
            # Launch VM
            vm_fixture[vdns] = self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name, connections=self.connections,
                    vn_obj=vn_fixt.obj, vm_name=vm_name))
            vm_fixture[vdns].verify_vm_launched()
            vm_fixture[vdns].verify_on_setup()
            vm_fixture[vdns].wait_till_vm_is_up()
            # get vm IP from nova
            vm_ip = vm_fixture[vdns].vm_ip
            i = i + 1
            cmd = 'nslookup ' + vm_name
            self.logger.info(
                'VM Name is ---> %s\t cmd is---> %s', vm_name, cmd)
            vm_fixture[vdns].run_cmd_on_vm(cmds=[cmd])
            result = vm_fixture[vdns].return_output_cmd_dict[cmd]
            result = result.replace("\r", "")
            result = result.replace("\t", "")
            result = result.replace("\n", " ")
            m_obj = re.search(
                r"Address:[0-9.]*#[0-9]*\s*.*Name:(.*\.vdns[0-9]*\.net)\s*Address:\s*([0-9.]*)", result)
            if not m_obj:
                self.assertTrue(
                    False, 'record search is failed,please check syntax of the regular expression/NSlookup is failed')
            print ('vm_name is ---> %s \t ip-address is ---> %s' %
                   (m_obj.group(1), m_obj.group(2)))
            self.assertEqual(m_obj.group(1), vm_domain_name,
                             'VM name is not matching with nslookup command output')
            self.assertEqual(m_obj.group(2), vm_ip,
                             'IP Address is not matching with nslookup command output')
        return True
     # End of test_vdns_server_scaling

if __name__ == '__main__':
    unittest.main()
# end of TestVdnsFixture
