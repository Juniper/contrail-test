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
import os
import unittest
import fixtures
import testtools
import traceback

from policy_test import *
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because
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
from tcutils.tcpdump_utils import *

sys.path.append(os.path.realpath('tcutils/traffic_utils'))
from base_traffic import *
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.helpers import Host, Sender, Receiver
from traffic.core.profile import StandardProfile,ContinuousProfile
from string import Template

class TestvDNS0(BasevDNSTest):

    @classmethod
    def setUpClass(cls):
        super(TestvDNS0, cls).setUpClass()

    def runTest(self):
        pass
    #end runTest 

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
            project_name=self.inputs.project_name, connections=self.connections))
        project_connections = project_fixture.get_project_connections()
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
        ipam_fixt1 = self.useFixture(IPAMFixture(ipam_name, vdns_obj=vdns_fixt1.obj, connections=project_connections, ipamtype=ipam_mgmt_obj))
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
            agent_inspect_h = self.agent_inspect[vm_fixture[vm_name].vm_node_ip]
            assigned_dns_ips = agent_inspect_h.get_vna_dns_server()
            rec_name = vm_name + "." + domain_name
            vm_dns_exp_data = [{'rec_data': vm_ip, 'rec_type': 'A', 'rec_class': 'IN', 'rec_ttl': str(
                ttl), 'rec_name': rec_name, 'installed': 'yes', 'zone': domain_name}, {'rec_data': rec_name, 'rec_type': 'PTR', 'rec_class': 'IN', 'rec_ttl': str(ttl), 'rec_name': vm_rev_ip, 'installed': 'yes', 'zone': rev_zone}]
            self.verify_vm_dns_data(vm_dns_exp_data, assigned_dns_ips[0])
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
            vm_updated = False
            for i in range(0,4):
                vm_fixture['vm1-test'].run_cmd_on_vm(cmds=[cmd])
                result = vm_fixture['vm1-test'].return_output_cmd_dict[cmd]
                if result:
                    result = result.replace("\t", " ")
                    m_obj = re.search(r"rec1.juniper.net\.*\s*([0-9.]*)\s*IN\s*A\s*([0-9.]*)",
                                      result)
                    if not m_obj:
                        self.assertTrue(False,
                        'record search is failed,please check syntax of regular expression')
                    if int(m_obj.group(1)) != ttl_mod:
                        sleep(1)
                    else:
                        vm_updated = True
                        break
                else:
                    sleep(1)
            assert vm_updated, "Record not updated on VM "
            print(("\nTTL VALUE is %s ", m_obj.group(1)))
            print(("\nrecord ip address is %s", m_obj.group(2)))
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
            project_name=self.inputs.project_name, connections=self.connections))
        project_connections = project_fixture.get_project_connections()
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
        except Exception as msg:
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
            ipam_fixt[ipam] = self.useFixture(IPAMFixture(ipam_dns_list[ipam],
                                              vdns_obj=vdns_fix[ipam],
                                              connections=project_connections,
                                              ipamtype=ipam_mgmt_obj))

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
        except Exception as msg:
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
            project_name=self.inputs.project_name, connections=self.connections))
        project_connections = project_fixture.get_project_connections()
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
        ipam_fixt1 = self.useFixture(IPAMFixture(ipam_name, vdns_obj=vdns_fixt1.obj, connections=project_connections, ipamtype=ipam_mgmt_obj))

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
                    project_name=proj, username=self.inputs.admin_username,
                    password=self.inputs.admin_password, connections=admin_con))
            user_fixture.add_user_to_tenant(proj, proj_user[proj] , 'admin')
            project_fixture.set_user_creds(proj_user[proj], proj_pass[proj])
            project_inputs = ContrailTestInit(
                self.input_file, stack_user=project_fixture.project_username,
                stack_password=project_fixture.project_user_password,
                stack_tenant=proj, logger=self.logger)
            project_connections = ContrailConnections(project_inputs, logger= self.logger)
            self.logger.info(
                'Default SG to be edited for allow all on project: %s' % proj)
            project_fixture.set_sec_group_for_allow_all(proj, 'default')
            # policy creation
            pol_fixt[proj] = self.useFixture(PolicyFixture(policy_name=policy_list[
                                             proj], inputs=project_inputs, connections=project_connections, rules_list=rules[proj]))
            # Ipam creation
            ipam_fixt[proj] = self.useFixture(
                            IPAMFixture(ipam_list[proj], vdns_obj=vdns_fixt1.obj, \
                            connections=project_connections, ipamtype=ipam_mgmt_obj))
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
            agent_inspect_h = self.agent_inspect[vm_fix[proj].vm_node_ip]
            assigned_dns_ips = agent_inspect_h.get_vna_dns_server()
            rec_name = vm_list[proj] + "." + domain_name
            vm_dns_exp_data = [{'rec_data': vm_ip, 'rec_type': 'A', 'rec_class': 'IN', 'rec_ttl': str(
                ttl), 'rec_name': rec_name, 'installed': 'yes', 'zone': domain_name}, {'rec_data': rec_name, 'rec_type': 'PTR', 'rec_class': 'IN', 'rec_ttl': str(ttl), 'rec_name': vm_rev_ip, 'installed': 'yes', 'zone': rev_zone}]
            self.verify_vm_dns_data(vm_dns_exp_data, assigned_dns_ips[0])
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
            project_name=self.inputs.project_name, connections=self.connections))
        project_connections = project_fixture.get_project_connections()
        # VN Creation
        fvn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=fvn_name, inputs=self.inputs, subnets=fip_subnets, router_asn=self.inputs.router_asn, rt_number=mx_rt))
        assert fvn_fixture.verify_on_setup()
        # Default DNS server
        ipam_mgmt_obj = IpamType(ipam_dns_method='default-dns-server')
        # Associate VDNS with IPAM.
        ipam_fixt1 = self.useFixture(IPAMFixture(ipam_name, connections=project_connections, ipamtype=ipam_mgmt_obj))
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
        cmd = 'nslookup salesforce.com'
        vm_fix.run_cmd_on_vm(cmds=[cmd])
        result = vm_fix.return_output_cmd_dict[cmd]
        import re
        m_obj = re.search(r"(salesforce.com)", result)
        if not m_obj:
            self.assertTrue(
                False, 'record search is failed,please check syntax of the regular expression/NSlookup is failed')
        print(m_obj.group(1))
        # Ipam DNS mentod is set to default, so DNS resolution to external
        # world needs to be resolved.
        self.assertTrue(vm_fix.ping_with_certainty(ip='salesforce.com'),
                        "DNS name resolution failed when vdns set to default DNS method")
        # Modify Ipam with DNS Method to none.
        ipam_mgmt_obj = IpamType(ipam_dns_method='none')
        update_ipam = ipam_fixt1.getObj()
        update_ipam.set_network_ipam_mgmt(ipam_mgmt_obj)
        self.vnc_lib.network_ipam_update(update_ipam)
        vm_fix.run_cmd_on_vm(cmds=[cmd])
        result1 = vm_fix.return_output_cmd_dict[cmd]
        # changes as per CEM-4607
        m_obj1 = re.search(r"(salesforce.com)", result1)
        if not m_obj1:
            self.assertTrue(
                False, 'record search is failed,please check syntax of the regular expression/NSlookup is failed')
        print(m_obj1.group(1))
        return True

    @preposttest_wrapper
    def test_agent_crash_dns_malformed_received(self):
        '''Verify that Agent do not crash on sending a malformed DNS packet.
           This Test case specifically test following Bug
           Bug Id 1566067 : "Agent crash at BindUtil::DnsClass"
           Steps:
            1. Create a VN with IPAM having Virtual DNS configured.
            2. Create a VM and send a DNS query from VM to DNS server. DNS server should 
               have the Qclass field as any value other than "01"
            3. Verify that no crash happens when this malformed DNS packet reaches the server
        Pass criteria: Vrouter agent should not crash on receiving a malformed DNS packet
        Maintainer: pulkitt@juniper.net'''
        vm_list = ['vm1', 'vm2']
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
        vn_fixt = self.useFixture(VNFixture(self.connections, self.inputs, vn_name=vn_name,
                     subnets=[vn_nets['vn1']], ipam_fq_name=ipam_fixt1.fq_name, option='contrail'))
        vm_fixture1 = self.useFixture(VMFixture(project_name=self.inputs.project_name, 
                    connections=self.connections, vn_obj=vn_fixt.obj, vm_name=vm_list[0],
                    image_name = "ubuntu-traffic"))
        assert vm_fixture1.verify_vm_launched()
        assert vm_fixture1.verify_on_setup()
        assert vm_fixture1.wait_till_vm_is_up()
        # DNS payload with 1 query and qclass as "04" instead of "01"
        filters = '\'(src host %s and dst host %s and port 1234)\'' \
                    % (vm_fixture1.vm_ip,vn_fixt.get_dns_ip(ipam_fq_name = ipam_fixt1.fq_name))
        session, pcap = start_tcpdump_for_vm_intf(self, vm_fixture1, vn_fixt.vn_fq_name, filters = filters)


        srcip = vm_fixture1.vm_ip
        dstip = vn_fixt.get_dns_ip(ipam_fq_name =ipam_fixt1.fq_name)

        python_code = Template('''
from scapy.all import *
a=IP(dst='$dip',src='$sip')/UDP(dport=53,sport=1234)/str('\\x12\\x34\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x01\\x00\\x04')
send(a, iface='eth0',inter=1.000000,count=10)
           ''')
        python_code = python_code.substitute(dip=dstip,sip=srcip)
        vm_fixture1.run_python_code(python_code)

        sleep(2)
        stop_tcpdump_for_vm_intf(self, session, pcap)
        sleep(2)
        # grep in pcap file with source port (1234) 
        assert verify_tcpdump_count(self, session, pcap, grep_string="1234", exp_count=10)

if __name__ == '__main__':
    unittest.main()
# end of TestVdnsFixture
