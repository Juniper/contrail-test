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

from policy_test import *
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.pkgs.Traffic.traffic.core.stream import Stream
from tcutils.pkgs.Traffic.traffic.core.profile import create, ContinuousProfile
from tcutils.pkgs.Traffic.traffic.core.helpers import Host
from tcutils.pkgs.Traffic.traffic.core.helpers import Sender, Receiver
from base import BasevDNSRestartTest 
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

class TestvDNSRestart(BasevDNSRestartTest):

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
        proj_fixt = self.useFixture(ProjectFixture(
                        vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name,
                        connections=self.connections))
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
        record_counter = 500
        for x in range(0,record_counter):
            record_name = "vDNSrecForAliasVM%d" % x
            actual_vm_name = "VM%d" % x
            vdns_rec_data = VirtualDnsRecordType(record_name, 'CNAME', 'IN', actual_vm_name, ttl)
            vdns_rec_fix = self.useFixture(VdnsRecordFixture(
                        self.inputs, self.connections, record_name, vdns_fixt.fq_name, vdns_rec_data))
        ipam_mgmt_obj = IpamType(ipam_dns_method='virtual-dns-server', ipam_dns_server=dns_server)
        # Associate VDNS with IPAM.
        ipam_fixt = self.useFixture(IPAMFixture(ipam_name, vdns_obj= vdns_fixt.obj,
                        project_obj=proj_fixt, ipamtype=ipam_mgmt_obj))
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
            output = self.inputs.run_cmd_on_server(node,cmd, username = self.inputs.host_data[node]['username'], 
                                          password = self.inputs.host_data[node]['password'])
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
                    output = self.inputs.run_cmd_on_server(node,cmd, username = self.inputs.host_data[node]['username'], 
                                          password = self.inputs.host_data[node]['password'])
                    outputList = output.split()
                    if outputList[4] == fileSize:
                        self.logger.debug("Size of zone file is constant now. File update completed.")
                        break
                    fileSize = outputList[4]
            # Command to Sync the jnl file with zone file.
            newcmd = "contrail-rndc -c /etc/contrail/dns/contrail-rndc.conf sync"
            self.inputs.run_cmd_on_server(node,newcmd, username = self.inputs.host_data[node]['username'], 
                                          password = self.inputs.host_data[node]['password'])
            readFileCmd = "cat /etc/contrail/dns/%s" % zoneFile.rstrip('.jnl')
            fileContent = self.inputs.run_cmd_on_server(node, readFileCmd, username = self.inputs.host_data[node]['username'], 
                                        password = self.inputs.host_data[node]['password'])
            lines = fileContent.split('\n')
            count = 0
            for lineNumber in range(0,len(lines)):
                line = lines[lineNumber].split()
                if len(line) > 1:
                    if  line[1] == 'CNAME':
                        count = count +1
            self.logger.debug("Number of records file on control node %s are %d." % (node, count))
            if count ==500:
                self.logger.info("All records restored correctly on control node %s" % node )
            else : 
                self.logger.error("Records lost after named restart on control node %s" % node)
                msg = "records lost after restart of named."
                result = False
                assert result, msg
    # end scale_vdns_records_restart_named

if __name__ == '__main__':
    unittest.main()
# end of TestVdnsFixture
