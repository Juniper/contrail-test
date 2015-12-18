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
from tcutils.util import skip_because
from base import BasevDNSTest
from common import isolated_creds
import inspect
from vnc_api import vnc_api
from vnc_api.gen.resource_test import *
from vdns_fixture import *
from floating_ip import *
from policy_test import *
from control_node import *
from user_test import UserFixture
from ipam_test import IPAMFixture
from vn_test import VNFixture
import test

class TestvDNS0(BasevDNSTest):

    @classmethod
    def setUpClass(cls):
        super(TestvDNS0, cls).setUpClass()

    def runTest(self):
        pass
    #end runTest 

    # This Test test vdns functionality-- On VM launch agent should dynamically update dns records to dns agent.
    # This test verifies the same functionality and should able to refer VM by
    # a name.
    @test.attr(type=['sanity', 'ci_sanity', 'vcenter'])
    @preposttest_wrapper
    def test_vdns_ping_same_vn(self):
        ''' 
        Test:- Test vdns functionality. On VM launch agent should dynamically update dns records to dns agent
            1.  Create vDNS server 
            2.  Create IPAM using above vDNS data 
            3.  Create VN using above IPAM and launch 2 VM's within it 
            4.  Ping between these 2 VM's using dns name 
            5.  Try to delete vDNS server which has IPAM back-reference[Negative case] 
            6.  Add CNAME VDNS record for vm1-test and verify we able to ping by alias name 
        Pass criteria: Step 4,5 and 6 should pass
         
        Maintainer: cf-test@juniper.net
        '''
        vn1_ip = '10.10.10.0/24'
        vm_list = ['vm1-test', 'vm2-test']
        vn_name = 'vn1-vdns'
        dns_server_name = 'vdns1'
        domain_name = 'juniper.net'
        cname_rec = 'vm1-test-alias'
        ttl = 100
        ipam_name = 'ipam1'
        rev_zone = vn1_ip.split('.')
        rev_zone = '.'.join((rev_zone[0], rev_zone[1], rev_zone[2]))
        rev_zone = rev_zone + '.in-addr.arpa'
        proj_fixt = self.useFixture(ProjectFixture(
            vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
        dns_data = VirtualDnsType(
            domain_name=domain_name, dynamic_records_from_client=True,
            default_ttl_seconds=ttl, record_order='random', reverse_resolution=True)
        # Create VDNS server object.
        vdns_fixt1 = self.useFixture(VdnsFixture(
            self.inputs, self.connections, vdns_name=dns_server_name, dns_data=dns_data))
        result, msg = vdns_fixt1.verify_on_setup()
        self.assertTrue(result, msg)
        dns_server = IpamDnsAddressType(
            virtual_dns_server_name=vdns_fixt1.vdns_fq_name)
        ipam_mgmt_obj = IpamType(
            ipam_dns_method='virtual-dns-server', ipam_dns_server=dns_server)
        # Associate VDNS with IPAM.
        ipam_fixt1 = self.useFixture(IPAMFixture(ipam_name, vdns_obj= vdns_fixt1.obj, project_obj=proj_fixt, ipamtype=ipam_mgmt_obj))
        vn_fixt = self.useFixture(
            VNFixture(
                self.connections, self.inputs,
                vn_name=vn_name, subnets=[vn1_ip], ipam_fq_name=ipam_fixt1.fq_name, option='contrail'))
        vm_fixture = {}
        # Launch  VM with VN Created above. This test verifies on launch of VM agent should updated DNS 'A' and 'PTR' records
        # The following code will verify the same. Also, we should be able ping
        # with VM name.
        for vm_name in vm_list:
            vn_quantum_obj = self.orch.get_vn_obj_if_present(
                vn_name=vn_fixt.vn_name, project_id=proj_fixt.uuid)
            vm_fixture[vm_name] = self.useFixture(
                VMFixture(project_name=self.inputs.project_name, connections=self.connections, vn_obj=vn_quantum_obj, vm_name=vm_name))
            vm_fixture[vm_name].verify_vm_launched()
            vm_fixture[vm_name].verify_on_setup()
            vm_fixture[vm_name].wait_till_vm_is_up()
            vm_ip = vm_fixture[vm_name].get_vm_ip_from_vm(
                vn_fq_name=vm_fixture[vm_name].vn_fq_name)
            vm_rev_ip = vm_ip.split('.')
            vm_rev_ip = '.'.join(
                (vm_rev_ip[3], vm_rev_ip[2], vm_rev_ip[1], vm_rev_ip[0]))
            vm_rev_ip = vm_rev_ip + '.in-addr.arpa'
            msg = "Ping by using name %s is failed. Dns server should resolve VM name to IP" % (
                vm_name)
            self.assertTrue(vm_fixture[vm_name]
                            .ping_with_certainty(ip=vm_name), msg)
            # Frame the Expected DNS data for VM, one for 'A' record and
            # another 'PTR' record.
            rec_name = vm_name + "." + domain_name
            vm_dns_exp_data = [{'rec_data': vm_ip, 'rec_type': 'A', 'rec_class': 'IN', 'rec_ttl': str(
                ttl), 'rec_name': rec_name, 'installed': 'yes', 'zone': domain_name}, {'rec_data': rec_name, 'rec_type': 'PTR', 'rec_class': 'IN', 'rec_ttl': str(ttl), 'rec_name': vm_rev_ip, 'installed': 'yes', 'zone': rev_zone}]
            self.verify_vm_dns_data(vm_dns_exp_data)
            vm_dns_exp_data = []
        # ping between two vms which are in same subnets by using name.
        self.assertTrue(vm_fixture['vm1-test']
                        .ping_with_certainty(ip=vm_list[1]))
        # delete VDNS with ipam as back refrence.
        self.logger.info(
            "Try deleting the VDNS entry %s with back ref of ipam.", dns_server_name)
        try:
            self.vnc_lib.virtual_DNS_delete(
                fq_name=vdns_fixt1.obj.get_fq_name())
            errmsg = "VDNS entry deleted which is not expected, when it has back refrence of ipam."
            self.logger.error(errmsg)
            assert False, errmsg
        except Exception, msg:
            self.logger.info(msg)
            self.logger.info(
                "Deletion of the vdns entry failed with back ref of ipam as expected")
        # Add VDNS record 'CNAME' and add it to VDNS and ping with alias for
        # vm1-test
        self.logger.info(
            'Add CNAME VDNS record for vm1-test and verify we able to ping by alias name')
        vdns_rec_data = VirtualDnsRecordType(
            cname_rec, 'CNAME', 'IN', 'vm1-test', ttl)
        vdns_rec_fix = self.useFixture(VdnsRecordFixture(
            self.inputs, self.connections, 'test-rec', vdns_fixt1.get_fq_name(), vdns_rec_data))
        result, msg = vdns_rec_fix.verify_on_setup()
        self.assertTrue(result, msg)
        self.assertTrue(vm_fixture['vm1-test']
                        .ping_with_certainty(ip=cname_rec))
        return True
    # end test_vdns_ping_same_vn

    @preposttest_wrapper
    def test_vdns_ping_diff_vn(self):
        '''This Test tests vdns functionality-- test vms on different subnets and we should able to refer each by name.
          We should be able to ping each of vms by using name
            1.  Create vDNS server
            2.  Create IPAM using above vDNS data with 2 subnets
            3.  Create VN using above IPAM  with one vn in each subnet and launch 1 VM within each VN
            4.  Ping between these 2 VM's using dns name expecting it to pass as VNs have attached policy to allow icmp
            5.  Frame the Expected DNS data for VM, one for 'A' record and another 'PTR' record and verify it also verify nslookup for VM's
            6.  Add VDNS record and verify TTL value correctly
            7.  Modify the record TTL and address values and verify
        Pass criteria: Step 4,5,6 and 7  should pass

        Maintainer: cf-test@juniper.net'''

        vm_list = ['vm1-test', 'vm2-test']
        vn_list = ['vn1', 'vn2']
        vn_nets = {'vn1' : '10.10.10.0/24', 'vn2' : '20.20.20.0/24'}
        vm_vn_list = {'vm1-test': 'vn1', 'vm2-test': 'vn2'}
        dns_server_name = 'vdns1'
        domain_name = 'juniper.net'
        ttl = 100
        ipam_name = 'ipam1'
        rev_zone = vn_nets['vn1'].split('.')
        rev_zone = '.'.join((rev_zone[0], rev_zone[1], rev_zone[2]))
        rev_zone = rev_zone + '.in-addr.arpa'
        policy_name = 'policy1'
        project_fixture = self.useFixture(ProjectFixture(
            vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
        dns_data = VirtualDnsType(
            domain_name=domain_name, dynamic_records_from_client=True,
            default_ttl_seconds=ttl, record_order='random', reverse_resolution=True)
        vdns_fixt1 = self.useFixture(VdnsFixture(
            self.inputs, self.connections, vdns_name=dns_server_name, dns_data=dns_data))
        result, msg = vdns_fixt1.verify_on_setup()
        self.assertTrue(result, msg)
        dns_server = IpamDnsAddressType(
            virtual_dns_server_name=vdns_fixt1.vdns_fq_name)
        ipam_mgmt_obj = IpamType(
            ipam_dns_method='virtual-dns-server', ipam_dns_server=dns_server)
        # Associate IPAM with  VDNS server Object
        ipam_fixt1 = self.useFixture(IPAMFixture(ipam_name, vdns_obj=vdns_fixt1.obj, project_obj=project_fixture, ipamtype=ipam_mgmt_obj))
        # create policy
        rules = {}
        rules[policy_name] = [PolicyRuleType(direction='<>', protocol='icmp', dst_addresses=[AddressType(virtual_network='any')], src_addresses=[AddressType(
            virtual_network='local')], action_list=ActionListType(simple_action='pass'), src_ports=[PortType(-1, -1)], dst_ports=[PortType(-1, -1)])]
        policy_fixt = self.useFixture(
            NetworkPolicyTestFixtureGen(
                self.vnc_lib, network_policy_name=policy_name,
                parent_fixt=project_fixture, network_policy_entries=PolicyEntriesType(rules[policy_name])))

        vn_fixt = {}
        vm_fixture = {}
        # Launch  VM with VN Created above. This test verifies on launch of VM agent should updated DNS 'A' and 'PTR' records
        # The following code will verify the same. Also, we should be able ping
        # with VM name.
        for vm_name in vm_list:
            vn = vm_vn_list[vm_name]
            vn_fixt[vm_name] = self.useFixture(VNFixture(self.connections, self.inputs, vn_name=vm_vn_list[vm_name], subnets=[vn_nets[vn]], policy_objs=[policy_fixt.getObj()], ipam_fq_name=ipam_fixt1.fq_name, option='contrail'))
            vn_quantum_obj = self.orch.get_vn_obj_if_present(vn_name=vn, project_id=project_fixture.uuid)
            vm_fixture[vm_name] = self.useFixture(
                VMFixture(project_name=self.inputs.project_name, connections=self.connections, vn_obj=vn_quantum_obj, vm_name=vm_name))
            vm_fixture[vm_name].verify_vm_launched()
            vm_fixture[vm_name].verify_on_setup()
            vm_fixture[vm_name].wait_till_vm_is_up()
            msg = "Ping by using name %s is failed. Dns server should resolve VM name to IP" % (
                vm_name)
            self.assertTrue(vm_fixture[vm_name]
                            .ping_with_certainty(ip=vm_name), msg)
            vm_ip = vm_fixture[vm_name].get_vm_ip_from_vm(
                vn_fq_name=vm_fixture[vm_name].vn_fq_name)
            vm_rev_ip = vm_ip.split('.')
            vm_rev_ip = '.'.join(
                (vm_rev_ip[3], vm_rev_ip[2], vm_rev_ip[1], vm_rev_ip[0]))
            vm_rev_ip = vm_rev_ip + '.in-addr.arpa'
            # Frame the Expected DNS data for VM, one for 'A' record and
            # another 'PTR' record.
            rec_name = vm_name + "." + domain_name
            vm_dns_exp_data = [{'rec_data': vm_ip, 'rec_type': 'A', 'rec_class': 'IN', 'rec_ttl': str(
                ttl), 'rec_name': rec_name, 'installed': 'yes', 'zone': domain_name}, {'rec_data': rec_name, 'rec_type': 'PTR', 'rec_class': 'IN', 'rec_ttl': str(ttl), 'rec_name': vm_rev_ip, 'installed': 'yes', 'zone': rev_zone}]
            self.verify_vm_dns_data(vm_dns_exp_data)
            vm_dns_exp_data = []
            # for test
            add = 'Address:.*' + vm_ip
            exp_data = vm_ip
            cmd = 'nslookup ' + vm_name + '|' + ' grep ' + '\'' + add + '\''
            msg = 'nslookup failed for VM  ' + vm_name
            self.assertTrue(
                self.verify_ns_lookup_data(vm_fixture[vm_name], cmd, exp_data), msg)
            cmd = 'nslookup ' + vm_ip + '|' + ' grep ' + '\'' + vm_name + '\''
            exp_data = vm_name + '.' + domain_name
            msg = 'reverse nslookup failed for VM  ' + vm_name
            self.assertTrue(
                self.verify_ns_lookup_data(vm_fixture[vm_name], cmd, exp_data), msg)
        # ping between two vms which are in different subnets by using name.
        self.assertTrue(vm_fixture['vm1-test']
                        .ping_with_certainty(ip=vm_list[1]))
        # Add VDNS record and verify TTL value correctly
        self.logger.info(
            'Add VDNS record and verify TTL value is set correctly using with dig command')
        vdns_rec_data = VirtualDnsRecordType('rec1', 'A', 'IN', '1.1.1.1', ttl)
        vdns_rec_fix = self.useFixture(VdnsRecordFixture(
            self.inputs, self.connections, 'test-rec', vdns_fixt1.get_fq_name(), vdns_rec_data))
        result, msg = vdns_rec_fix.verify_on_setup()
        self.assertTrue(result, msg)
        cmd = 'dig +nocmd ' + 'rec1.' + domain_name + ' +noall +answer'
        import re
        vdns_record_obj = vdns_rec_fix.obj
        ttl_list = [100, 2000, 0, 86400, 2147483647, -1, 2147483648]
        i = 1
        # modify the record TTL and address values and verify
        for ttl_mod in ttl_list:
            ip_add = '1.1.1.' + str(i)
            # Already configured TTL as a 100, so not configuring TTL value for
            # first time
            if ttl_mod != 100:
                vdns_rec_data = VirtualDnsRecordType(
                    'rec1', 'A', 'IN', ip_add, ttl_mod)
                vdns_record_obj.set_virtual_DNS_record_data(vdns_rec_data)
                try:
                    self.vnc_lib.virtual_DNS_record_update(vdns_record_obj)
                except Exception as e:
                    if (ttl_mod == -1 or ttl_mod == 2147483648):
                        self.logger.info(
                            'Failed to configure invalid TTL values as expected')
                        continue
                    else:
                        self.assertTrue(False, 'Failed to Modify TTL values')
            vm_fixture['vm1-test'].run_cmd_on_vm(cmds=[cmd])
            result = vm_fixture['vm1-test'].return_output_cmd_dict[cmd]
            result = result.replace("\t", " ")
            #m_obj = re.search(r"rec1.juniper.net\.*\s*([0-9.]*)",result)
            m_obj = re.search(
                r"rec1.juniper.net\.*\s*([0-9.]*)\s*IN\s*A\s*([0-9.]*)", result)
            if not m_obj:
                self.assertTrue(
                    False, 'record search is failed,please check syntax of regular expression')
            print ("\nTTL VALUE is %s ", m_obj.group(1))
            print ("\nrecord ip address is %s", m_obj.group(2))
            self.assertEqual(int(m_obj.group(1)), ttl_mod,
                             'TTL value is not matching for static record after record modification')
            self.assertEqual(m_obj.group(2), ip_add,
                             'IP Address is not matching for static record after record modification')
            i = i + 1
        return True
    # end of test_vdns_ping_diff_vn

    # This test creates 3 vnds servers vdns1,vdns2 and vdns3. For vdns2 and vdns3, vdns1 act a next vdns nerver.
    # The VDNS server are configured as shown below.
    #                         vdns1 (domain: juniper.net)
    #                        ^     ^
    #                       /       \
    #                      /         \
    #   (bng.juniper.net) vdns2        vdns3(eng.juniper.net)
    #
    #
    @preposttest_wrapper
    @skip_because(feature='multi-ipam')
    def test_vdns_with_next_vdns(self):
        ''' This test creates 3 vnds servers vdns1,vdns2 and vdns3. For vdns2 and vdns3, vdns1 act a next vdns nerver.
            The VDNS server are configured as shown below.
                                vdns1 (domain: juniper.net)
                               ^     ^
                              /       \
                             /         \
            (bng.juniper.net) vdns2        vdns3(eng.juniper.net)
            1. Try to delete vdns entry which was referenced in other vdns entry expecting it to fail
            2. In VDNS1 need to be added 'NS' records to delegate a subdomain to VDNS2 and VDNS3
            3. Create IPAM entries with VDNS servers as shown above and launch VN's using these IPAMS
            4. Launch 1 VM each in VN's Created above. This test verifies on launch of VM agent should update DNS 'A' and 'PTR' records for VM
            5. Ping with VM name should pass as policy is attached between VNs to allow icmp
            6. Verify DNS entries are resolved for sub domains
            7. Try to delete vdns entry which was referenced in other vdns entry expect it to fail
        Pass criteria: Step 5,6 and 7  should pass

        Maintainer: cf-test@juniper.net
        '''
        vm_list = ['vm1-test', 'vm2-test', 'vm3-test']
        vm_vn_list = {'vm1-test': 'vn1', 'vm2-test': 'vn2', 'vm3-test': 'vn3'}
        vn_nets = {'vn1' : '10.10.10.0/24', 'vn2' : '20.20.20.0/24', 'vn3' : '30.30.30.0/24'}
        policy_name = 'policy1'
        dns_server_name1 = 'vdns1'
        dns_server_name2 = 'vdns2'
        dns_server_name3 = 'vdns3'
        domain_name1 = 'juniper.net'
        domain_name2 = 'bng.juniper.net'
        domain_name3 = 'eng.juniper.net'
        ttl = 100
        vm1_ping_list = [vm_list[0] + "." + domain_name1, vm_list[1]
                         + "." + domain_name2, vm_list[2] + "." + domain_name3]
        vm2_ping_list = [vm_list[1] + "." + domain_name2,
                         vm_list[0] + "." + domain_name1]
        vm3_ping_list = [vm_list[2] + "." + domain_name3,
                         vm_list[0] + "." + domain_name1]
        vm_domain_list = {vm_list[0]: vm1_ping_list,
                          vm_list[1]: vm2_ping_list, vm_list[2]: vm3_ping_list}

        project_fixture = self.useFixture(ProjectFixture(
            vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
        dns_server_name_list = ['vdns1', 'vdns2', 'vdns3']
        domain_name_list = {'vdns1': 'juniper.net', 'vdns2':
                            'bng.juniper.net', 'vdns3': 'eng.juniper.net'}
        rec_names = {'vdns2': 'test-rec1', 'vdns3': 'test-rec2'}
        ipam_dns_list = {'vdns1': 'ipam1', 'vdns2': 'ipam2', 'vdns3': 'ipam3'}

        vdns_fix = {}
        vdns_data = {}
        vdns_rec = {}
        for dns_name in dns_server_name_list:
            # VDNS1
            if dns_name == 'vdns1':
                vdns_data[dns_name] = VirtualDnsType(domain_name=domain_name_list[
                                                     dns_name], dynamic_records_from_client=True, default_ttl_seconds=ttl, record_order='random')
            else:
                # VDNS2 and VDNS3 need to point VDNS1 as next vdns server.
                vdns_data[dns_name] = VirtualDnsType(
                    domain_name=domain_name_list[
                        dns_name], dynamic_records_from_client=True,
                    default_ttl_seconds=ttl, record_order='random', next_virtual_DNS=vdns_fix['vdns1'].vdns_fq_name)
            vdns_fix[dns_name] = self.useFixture(VdnsFixture(
                self.inputs, self.connections, vdns_name=dns_name, dns_data=vdns_data[dns_name]))
            result, msg = vdns_fix[dns_name].verify_on_setup()
            self.assertTrue(result, msg)

        # Try to delete vdns entry which was referenced in other vdns entry,
        # deletion should fail.
        self.logger.info(
            "Try deleting the VDNS entry %s with back ref.", dns_server_name1)
        try:
            self.vnc_lib.virtual_DNS_delete(
                fq_name=vdns_fix[dns_server_name1].obj.get_fq_name())
            errmsg = "VDNS entry deleted which is not expected, when it is attached to a other vdns servers."
            self.logger.error(errmsg)
            assert False, errmsg
        except Exception, msg:
            self.logger.info(msg)
            self.logger.info(
                "Not able to delete the vdns entry with back ref as expected")
        # In VDNS1 need to be added 'NS' records to delegate a subdomain to
        # VDNS2 and VDNS3.
        for dns_name in dns_server_name_list:
            if dns_name != 'vdns1':
                vdns_rec_data = VirtualDnsRecordType(
                    domain_name_list[dns_name], 'NS', 'IN', vdns_fix[dns_name].vdns_fq_name, ttl)
                vdns_rec[dns_name] = self.useFixture(VdnsRecordFixture(
                    self.inputs, self.connections, rec_names[dns_name], vdns_fix['vdns1'].get_fq_name(), vdns_rec_data))
                result, msg = vdns_rec[dns_name].verify_on_setup()
                self.assertTrue(result, msg)

        ipam_fixt = {}
        # Create IPAM entrys with VDNS servers
        for ipam in ipam_dns_list:
            dns_server = IpamDnsAddressType(
                virtual_dns_server_name=vdns_fix[ipam].vdns_fq_name)
            ipam_mgmt_obj = IpamType(
                ipam_dns_method='virtual-dns-server', ipam_dns_server=dns_server)
            ipam_fixt[ipam] = self.useFixture(IPAMFixture(ipam_dns_list[ipam], vdns_obj=vdns_fix[ipam], project_obj=project_fixture, ipamtype=ipam_mgmt_obj)) 

        rules = {}
        rules[policy_name] = [PolicyRuleType(direction='<>', protocol='icmp', dst_addresses=[AddressType(virtual_network='any')], src_addresses=[AddressType(
            virtual_network='any')], action_list=ActionListType(simple_action='pass'), src_ports=[PortType(-1, -1)], dst_ports=[PortType(-1, -1)])]
        policy_fixt = self.useFixture(
            NetworkPolicyTestFixtureGen(
                self.vnc_lib, network_policy_name=policy_name,
                parent_fixt=project_fixture, network_policy_entries=PolicyEntriesType(rules[policy_name])))

        ipam_dns = { 'vn1': ipam_fixt['vdns1'].getObj(),
                     'vn2': ipam_fixt['vdns2'].getObj(),
                     'vn3': ipam_fixt['vdns3'].getObj() }

        vn_fixt = {}
        vm_fixture = {}
        # Launch  VM with VN Created above. This test verifies on launch of VM agent should updated DNS 'A' and 'PTR' records
        # The following code will verify the same. Also, we should be able ping
        # with VM name.
        for vm_name in vm_list:
            vn = vm_vn_list[vm_name]
            vn_fixt[vm_name] = self.useFixture(VNFixture(self.connections, self.inputs, vn_name=vn, subnets=[vn_nets[vn]], policy_objs=[policy_fixt.getObj()], ipam_fq_name=ipam_dns[vn].get_fq_name(), option='contrail'))
            vn_quantum_obj = self.orch.get_vn_obj_if_present(vn_name=vn, project_id=project_fixture.uuid)
            vm_fixture[vm_name] = self.useFixture(
                VMFixture(project_name=self.inputs.project_name, connections=self.connections, vn_obj=vn_quantum_obj, vm_name=vm_name))
            vm_fixture[vm_name].verify_vm_launched()
            vm_fixture[vm_name].verify_on_setup()
            vm_fixture[vm_name].wait_till_vm_is_up()

        # Verify DNS entries are resolved for sub domains.
        for vm_name in vm_list:
            vm_ping_list = vm_domain_list[vm_name]
            for cmd in vm_ping_list:
                self.assertTrue(vm_fixture[vm_name]
                                .ping_with_certainty(ip=cmd))

        # Try to delete vdns entry which was referenced in other vdns entry,
        # deletion should fail.
        self.logger.info(
            "Try deleting the VDNS entry %s with back ref of vdns records.", dns_server_name1)
        try:
            self.vnc_lib.virtual_DNS_delete(
                fq_name=vdns_fix[dns_server_name1].obj.get_fq_name())
            errmsg = "VDNS entry deleted which is not expected, when it had vdns records."
            self.logger.error(errmsg)
            assert False, errmsg
        except Exception, msg:
            self.logger.info(msg)
            self.logger.info(
                "Not able to delete the vdns entry with back ref of vdns records")
        return True

    @preposttest_wrapper
    def test_vdns_roundrobin_rec_order(self):
        ''' This test tests vdns round-robin record order
            1. Create VDNS server object
            2. Associate VDNS with IPAM
            3. Launch VN with IPAM and launch VM in VN
            4. Get the NS look up record and verify round-robin record order
        Pass criteria: Step 4 should pass
        Maintainer: cf-test@juniper.net'''


        record_order = 'round-robin'
        self.verify_dns_record_order(record_order)
        return True

    @preposttest_wrapper
    def test_vdns_random_rec_order(self):
        ''' This test tests vdns random record order
            1. Create VDNS server object
            2. Associate VDNS with IPAM
            3. Launch VN with IPAM and launch VM in VN
            4. Get the NS look up record and verify random record order
        Pass criteria: Step 4 should pass
        Maintainer: cf-test@juniper.net'''

        record_order = 'random'
        self.verify_dns_record_order(record_order)
        return True

    @preposttest_wrapper
    def test_vdns_fixed_rec_order(self):
        '''This test tests vdns fixed record order
            1. Create VDNS server object
            2. Associate VDNS with IPAM
            3. Launch VN with IPAM and launch VM in VN
            4. Get the NS look up record and verify fixed record order
        Pass criteria: Step 4 should pass
        Maintainer: cf-test@juniper.net'''

        record_order = 'fixed'
        self.verify_dns_record_order(record_order)
        return True

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

    @preposttest_wrapper
    def test_vdns_with_fip(self):
        ''' This Test test vdns functionality with floating ip
            1. Create VDNS server object
            2. Associate VDNS with IPAM
            3. Launch VN with IPAM and launch VM in VN
            4. Verify on launch of VM agent should updated DNS 'A' and 'PTR' records for VM
            5. Ping with VM name should pass
            6. Associate floating ip to VM from another subnet and ping using VM name
        Pass criteria: Step 4,5 and 6 should pass
        Maintainer: cf-test@juniper.net '''

        vn_nets = {'vn1': ['10.10.10.0/24'], 'vn2': ['20.20.20.0/24']}
        vm_list = ['vm1-test', 'vm2-test']
        vm_vn_list = {'vm1-test': 'vn1', 'vm2-test': 'vn2'}
        dns_server_name = 'vdns1'
        domain_name = 'juniper.net'
        ttl = 100
        ipam_name = 'ipam1'
        fip_pool_name1 = 'some-pool1'
        project_fixture = self.useFixture(ProjectFixture(
            vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
        # VDNS
        dns_data = VirtualDnsType(
            domain_name=domain_name, dynamic_records_from_client=True,
            default_ttl_seconds=ttl, record_order='random')
        vdns_fixt1 = self.useFixture(VdnsFixture(
            self.inputs, self.connections, vdns_name=dns_server_name, dns_data=dns_data))
        result, msg = vdns_fixt1.verify_on_setup()
        self.assertTrue(result, msg)
        dns_server = IpamDnsAddressType(
            virtual_dns_server_name=vdns_fixt1.vdns_fq_name)
        # IPAM
        ipam_mgmt_obj = IpamType(
            ipam_dns_method='virtual-dns-server', ipam_dns_server=dns_server)
        # Associate IPAM with  VDNS server Object
        ipam_fixt1 = self.useFixture(IPAMFixture(ipam_name, vdns_obj=vdns_fixt1.obj, project_obj=project_fixture, ipamtype=ipam_mgmt_obj))

        vn_fixt = {}
        vm_fixture = {}
        # Launch  VM with VN Created above. This test verifies on launch of VM agent should updated DNS 'A' and 'PTR' records
        # The following code will verify the same. Also, we should be able ping
        # with VM name.
        for vm_name in vm_list:
            vn = vm_vn_list[vm_name]
            vn_fixt[vm_name] = self.useFixture(
                VNFixture(
                    project_name=self.inputs.project_name, connections=self.connections,
                    vn_name=vm_vn_list[vm_name], inputs=self.inputs, subnets=vn_nets[vn], ipam_fq_name=ipam_fixt1.getObj().get_fq_name()))
            vm_fixture[vm_name] = self.useFixture(
                VMFixture(project_name=self.inputs.project_name, connections=self.connections, vn_obj=vn_fixt[vm_name].obj, vm_name=vm_name))
            vm_fixture[vm_name].verify_vm_launched()
            vm_fixture[vm_name].verify_on_setup()
            vm_fixture[vm_name].wait_till_vm_is_up()

        # FIP
        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name1, vn_id=vn_fixt['vm2-test'].vn_id))
        assert fip_fixture1.verify_on_setup()
        fip_id1 = fip_fixture1.create_and_assoc_fip(
            vn_fixt['vm2-test'].vn_id, vm_fixture['vm1-test'].vm_id)
        self.addCleanup(fip_fixture1.disassoc_and_delete_fip, fip_id1)
        assert fip_fixture1.verify_fip(
            fip_id1, vm_fixture['vm1-test'], vn_fixt['vm2-test'])
        # ping between two vms which are in different subnets by using name.
        self.assertTrue(
            vm_fixture['vm1-test'].ping_with_certainty(ip=vm_list[1]),
            "Ping with VM name failed for VDNS with floating ip")
        return True

    @preposttest_wrapper
    @skip_because(feature='multi-tenant')
    def test_vdns_with_diff_projs(self):
        ''' Test vdns with different projects
            1. Create VDNS server object
            2. Create two projects
            3. Launch one IPAM using the VDNS server and launch one VN in each IPAM with policy to allow traffic betwwen VN's
            4. Launch one VM in each VN, frame the expected DNS data for VM, one for 'A' record and another 'PTR' record and verify
            5. Ping with VM name should pass
            6. Ping between two VM's which are in different subnets by using name
        Pass criteria: Step 4,5 and 6 should pass
        Maintainer: cf-test@juniper.net '''

        project_list = ['project1', 'project2']
        ipam_list = {'project1': 'ipam1', 'project2': 'ipam2'}
        policy_list = {'project1': 'policy1', 'project2': 'policy2'}
        vn_list = {'project1': 'vn1', 'project2': 'vn2'}
        vn_nets = {'project1': ['10.10.10.0/24'],
                   'project2': ['20.20.20.0/24']}
        vn_nets_woutsub = {'project1': '10.10.10.0', 'project2': '20.20.20.0'}
        vm_list = {'project1': 'vm1', 'project2': 'vm2'}
        proj_user = {'project1': 'user1', 'project2': 'user2'}
        proj_pass = {'project1': 'user123', 'project2': 'user134'}
        dns_server_name = 'vdns1'
        domain_name = 'juniper.net'
        ttl = 100
        # VDNS creation
        dns_data = VirtualDnsType(
            domain_name=domain_name, dynamic_records_from_client=True,
            default_ttl_seconds=ttl, record_order='random')
        vdns_fixt1 = self.useFixture(VdnsFixture(
            self.inputs, self.connections, vdns_name=dns_server_name, dns_data=dns_data))
        result, msg = vdns_fixt1.verify_on_setup()
        self.assertTrue(result, msg)
        dns_server = IpamDnsAddressType(
            virtual_dns_server_name=vdns_fixt1.vdns_fq_name)
        ipam_mgmt_obj = IpamType(
            ipam_dns_method='virtual-dns-server', ipam_dns_server=dns_server)
        ipam_fixt = {}
        vn_fixt = {}
        vm_fix = {}
        pol_fixt = {}
        rules = {
            'project1': [{'direction': '<>', 'protocol': 'any', 'dest_network': 'default-domain:project2:vn2', 'source_network': 'any', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}],
            'project2': [{'direction': '<>', 'protocol': 'any', 'dest_network': 'default-domain:project1:vn1', 'source_network': 'any', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]}
        admin_ip = self.inputs
        admin_con = self.connections
        for proj in project_list:
            # Project creation
            user_fixture= self.useFixture(
                UserFixture(
                    connections=self.connections, username=proj_user[proj], password=proj_pass[proj]))
            project_fixture = self.useFixture(
                ProjectFixture(
                    project_name=proj, vnc_lib_h=self.vnc_lib, username=proj_user[
                        proj],
                    password=proj_pass[proj], connections=admin_con))
            user_fixture.add_user_to_tenant(proj, proj_user[proj] , 'admin')
            project_inputs = ContrailTestInit(
                    self.ini_file, stack_user=project_fixture.username,
                    stack_password=project_fixture.password, project_fq_name=['default-domain', proj], logger=self.logger)
            project_connections = ContrailConnections(project_inputs, logger= self.logger)
            proj_fixt = self.useFixture(
                ProjectTestFixtureGen(self.vnc_lib, project_name=proj))
            self.logger.info(
                'Default SG to be edited for allow all on project: %s' % proj)
            project_fixture.set_sec_group_for_allow_all(proj, 'default')
            # policy creation
            pol_fixt[proj] = self.useFixture(PolicyFixture(policy_name=policy_list[
                                             proj], inputs=project_inputs, connections=project_connections, rules_list=rules[proj]))
            # Ipam creation
            ipam_fixt[proj] = self.useFixture(
                NetworkIpamTestFixtureGen(
                    self.vnc_lib, virtual_DNS_refs=[vdns_fixt1.obj],
                    parent_fixt=proj_fixt, network_ipam_name=ipam_list[proj], network_ipam_mgmt=ipam_mgmt_obj))
            # VN Creation
            vn_fixt[proj] = self.useFixture(
                VNFixture(project_name=proj, connections=project_connections,
                          vn_name=vn_list[proj], inputs=project_inputs, subnets=vn_nets[proj], ipam_fq_name=ipam_fixt[proj].getObj().get_fq_name(), policy_objs=[pol_fixt[proj].policy_obj]))
            # VM creation
            vm_fix[proj] = self.useFixture(
                VMFixture(
                    project_name=proj, connections=project_connections, vn_obj=vn_fixt[
                        proj].obj,
                    vm_name=vm_list[proj]))
            vm_fix[proj].verify_vm_launched()
            vm_fix[proj].verify_on_setup()
            vm_fix[proj].wait_till_vm_is_up()
            msg = "Ping by using name %s is failed. Dns server should resolve VM name to IP" % (
                vm_list[proj])
            self.assertTrue(
                vm_fix[proj].ping_with_certainty(ip=vm_list[proj]), msg)
            vm_ip = vm_fix[proj].get_vm_ip_from_vm(
                vn_fq_name=vm_fix[proj].vn_fq_name)
            vm_rev_ip = vm_ip.split('.')
            vm_rev_ip = '.'.join(
                (vm_rev_ip[3], vm_rev_ip[2], vm_rev_ip[1], vm_rev_ip[0]))
            vm_rev_ip = vm_rev_ip + '.in-addr.arpa'
            rev_zone = vn_nets_woutsub[proj].split('.')
            rev_zone = '.'.join((rev_zone[0], rev_zone[1], rev_zone[2]))
            rev_zone = rev_zone + '.in-addr.arpa'
            # Frame the Expected DNS data for VM, one for 'A' record and
            # another 'PTR' record.
            rec_name = vm_list[proj] + "." + domain_name
            vm_dns_exp_data = [{'rec_data': vm_ip, 'rec_type': 'A', 'rec_class': 'IN', 'rec_ttl': str(
                ttl), 'rec_name': rec_name, 'installed': 'yes', 'zone': domain_name}, {'rec_data': rec_name, 'rec_type': 'PTR', 'rec_class': 'IN', 'rec_ttl': str(ttl), 'rec_name': vm_rev_ip, 'installed': 'yes', 'zone': rev_zone}]
            self.verify_vm_dns_data(vm_dns_exp_data)
            vm_dns_exp_data = []
        # ping between two vms which are in different subnets by using name.
        self.assertTrue(vm_fix['project1'].ping_with_certainty(
            ip=vm_list['project2']), "Ping with VM name failed for VDNS across the projects")
        return True

    @preposttest_wrapper
    def test_vdns_default_mode(self):
        ''' Test vdns with default and None DNS Methods
            1. Create VDNS server object as default-dns-server
            2. Associate VDNS with IPAM
            3. Launch VN with IPAM and launch VM in VN
            4. Configure public ip pool and allocate fip to VM
            5. From VM do nslookup juniper.net,DNS method configued is default, DNS should resolve for external DNS
            6. Ping juniper.net from VM verify DNS resolution to external world
            7. Modify Ipam with DNS Method to none and nslookup juniper.net should pass
        Pass criteria: Step 5,6 and 7 should pass
        Maintainer: cf-test@juniper.net'''

        vn_nets = {'vn1': ['10.10.10.0/24']}
        vm_name = 'vm1-test'
        vn_name = 'vn1'
        ipam_name = 'ipam1'
        fip_pool_name = self.inputs.fip_pool_name
        fvn_name = 'public100'
        mx_rt = self.inputs.mx_rt
        router_name = self.inputs.ext_routers[0][0]
        router_ip = self.inputs.ext_routers[0][1]
        fip_subnets = [self.inputs.fip_pool]

        project_fixture = self.useFixture(ProjectFixture(
            vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
        # VN Creation
        fvn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=fvn_name, inputs=self.inputs, subnets=fip_subnets, router_asn=self.inputs.router_asn, rt_number=mx_rt))
        assert fvn_fixture.verify_on_setup()
        # Default DNS server
        ipam_mgmt_obj = IpamType(ipam_dns_method='default-dns-server')
        # Associate VDNS with IPAM.
        ipam_fixt1 = self.useFixture(IPAMFixture(ipam_name, project_obj=project_fixture, ipamtype=ipam_mgmt_obj))
        vn_fixt = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_nets[vn_name], ipam_fq_name=ipam_fixt1.getObj().get_fq_name()))
        vm_fix = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections, vn_obj=vn_fixt.obj,
                vm_name=vm_name))
        vm_fix.verify_vm_launched()
        vm_fix.verify_on_setup()
        vm_fix.wait_till_vm_is_up()
        # FIP creation
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name, vn_id=fvn_fixture.vn_id))
        assert fip_fixture.verify_on_setup()
        fip_id = fip_fixture.create_and_assoc_fip(
            fvn_fixture.vn_id, vm_fix.vm_id)
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)
        assert fip_fixture.verify_fip(fip_id, vm_fix, fvn_fixture)
        routing_instance = fvn_fixture.ri_name
        # Configuring all control nodes here
        for entry in self.inputs.bgp_ips:
            hostname = self.inputs.host_data[entry]['name']
            cn_fixturemx = self.useFixture(CNFixture(
                connections=self.connections, router_name=router_name, router_ip=router_ip, router_type='mx', inputs=self.inputs))
        sleep(5)
        assert cn_fixturemx.verify_on_setup()
        # DNS methos configued is default, DNS should resolve for external DNS
        # lookups.
        cmd = 'nslookup juniper.net'
        vm_fix.run_cmd_on_vm(cmds=[cmd])
        result = vm_fix.return_output_cmd_dict[cmd]
        import re
        m_obj = re.search(r"(juniper.net)", result)
        if not m_obj:
            self.assertTrue(
                False, 'record search is failed,please check syntax of the regular expression/NSlookup is failed')
        print m_obj.group(1)
        # Ipam DNS mentod is set to default, so DNS resolution to external
        # world needs to be resolved.
        self.assertTrue(vm_fix.ping_with_certainty(ip='juniper.net'),
                        "DNS name resolution failed when vdns set to default DNS method")
        # Modify Ipam with DNS Method to none.
        ipam_mgmt_obj = IpamType(ipam_dns_method='none')
        update_ipam = ipam_fixt1.getObj()
        update_ipam.set_network_ipam_mgmt(ipam_mgmt_obj)
        self.vnc_lib.network_ipam_update(update_ipam)
        vm_fix.run_cmd_on_vm(cmds=[cmd])
        result1 = vm_fix.return_output_cmd_dict[cmd]
        m_obj1 = re.search(r"(no\s*servers\s*could\s*be\s*reached)", result1)
        if not m_obj1:
            self.assertTrue(
                False, 'record search is failed,please check syntax of the regular expression/NSlookup is failed')
        print m_obj1.group(1)
        return True

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
        project_fixture = self.useFixture(ProjectFixture(
            vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
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

        for dns_name in dns_server_name_list:
            dns_server = IpamDnsAddressType(
                virtual_dns_server_name=vdns_fix[dns_name].vdns_fq_name)
            ipam_mgmt_obj = IpamType(
                ipam_dns_method='virtual-dns-server', ipam_dns_server=dns_server)
            # Associate IPAM with VDNS server Object
            ipam_fixt[dns_name] = self.useFixture(IPAMFixture(ipam_dns_list[dns_name], vdns_obj=
                                                  vdns_fix[dns_name].obj, project_obj=project_fixture, ipamtype=ipam_mgmt_obj))
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
        for dns in dns_server_name_list:
            for dns_name in dns_server_name_list:
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
        vdns_scale = 1000
        # Number of records per server
        record_num = 1
        project_fixture = self.useFixture(ProjectFixture(
            vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
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
            if num % 100 == 0:
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
            ipam_fixt = self.useFixture(IPAMFixture(ipam_name, vdns_obj= vdns_fixt[vdns].obj, project_obj=project_fixture, ipamtype=ipam_mgmt_obj))
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
