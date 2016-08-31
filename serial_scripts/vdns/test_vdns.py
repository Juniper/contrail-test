# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run vdns_tests'. To run specific tests,
# You can do 'python -m testtools.run -l vdns_tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
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
from common.vdns.base import BasevDNSTest 
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
                        project_obj=self.project, ipamtype=ipam_mgmt_obj))
        assert ipam_fixt.verify_on_setup()
        vn_fixt = self.useFixture(VNFixture(self.connections, self.inputs,vn_name=vn_name,
                subnets=[vn_ip], ipam_fq_name=ipam_fixt.fq_name, option='contrail'))
        assert vn_fixt.verify_on_setup()
        self.logger.info("All configuration complete.")
        # restarting contrail-named on all control nodes
        self.inputs.stop_service('contrail-named', self.inputs.bgp_ips)
        sleep(10)
        self.inputs.start_service('contrail-named', self.inputs.bgp_ips)
        for ip in self.inputs.bgp_ips:
            assert self.inputs.confirm_service_active('contrail-named', ip)
        zoneFile = vn_fixt.vn_fq_name.split(':')[0] +'-' + dns_server_name + '.' + domain_name + '.zone.jnl'
        cmd = "ls -al /etc/contrail/dns/%s" % zoneFile
        for node in self.inputs.bgp_ips:
            output = self.inputs.run_cmd_on_server(node,cmd)
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
                    output = self.inputs.run_cmd_on_server(node,cmd)
                    outputList = output.split()
                    if outputList[4] == fileSize:
                        self.logger.debug("Size of zone file is constant now. File update completed.")
                        break
                    fileSize = outputList[4]
            # Command to Sync the jnl file with zone file.
            newcmd = "contrail-rndc -c /etc/contrail/dns/contrail-rndc.conf sync"
            self.inputs.run_cmd_on_server(node,newcmd)
            readFileCmd = "cat /etc/contrail/dns/%s" % zoneFile.rstrip('.jnl')
            fileContent = self.inputs.run_cmd_on_server(node, readFileCmd)
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
            5. Search for all DNS servers assigned to vrouter agents by discovery
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
                project_obj=self.project, ipamtype=ipam_mgmt_obj))
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
        # Getting the list of DNS servers in use by every Compute node as per discovery server assignment
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
                    inspect_h.get_vna_discovered_dns_server())
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
            self.inputs.stop_service("contrail-named",[self.inputs.bgp_ips[index]])
            self.addCleanup(self.inputs.start_service,'contrail-named',\
                             [self.inputs.bgp_ips[index]])
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
                    inspect_h.get_vna_discovered_dns_server())
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

if __name__ == '__main__':
    unittest.main()
# end of TestVdnsFixture
