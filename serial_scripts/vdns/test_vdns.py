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
from common.contrail_test_init import ContrailTestInit
from tcutils.contrail_status_check import ContrailStatusChecker

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

    class InitForZoneTests:
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
                    vnc_lib_h=self.vnc_lib,
                    username=var_obj.proj_user[proj],
                    password=var_obj.proj_pass[proj],
                    connections=self.admin_connections))
            user_fixture.add_user_to_tenant(proj, var_obj.proj_user[proj], 'admin')
            project_fixture.set_user_creds(var_obj.proj_user[proj], var_obj.proj_pass[proj])
            project_inputs = ContrailTestInit(
                    self.ini_file,
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
                        project_obj=project_fixture, ipamtype=ipam_mgmt_obj[proj]))
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
            assigned_dns_ips = agent_inspect_h.get_vna_discovered_dns_server()
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
            self.inputs.restart_service('supervisor-control', [bgp_ip])
        for cfgm_ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('supervisor-config', [cfgm_ip])
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
                    vnc_lib_h=self.vnc_lib,
                    username=var_obj.proj_user[proj],
                    password=var_obj.proj_pass[proj],
                    connections=self.admin_connections))
            user_fixture.add_user_to_tenant(proj, var_obj.proj_user[proj], 'admin')
            project_fixture.set_user_creds(var_obj.proj_user[proj], var_obj.proj_pass[proj])
            project_inputs = ContrailTestInit(
                    self.ini_file,
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
                        project_obj=project_fixture, ipamtype=ipam_mgmt_obj[proj]))
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
            assigned_dns_ips = agent_inspect_h.get_vna_discovered_dns_server()
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
            self.inputs.restart_service('supervisor-control', [bgp_ip])
        for cfgm_ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('supervisor-config', [cfgm_ip])
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

if __name__ == '__main__':
    unittest.main()
# end of TestVdnsFixture
