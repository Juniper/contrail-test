# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run vdns_tests'.
# To run specific tests, You can do 'python -m testtools.run -l vdns_tests'
# Set the env variable PARAMS_FILE to point to your ini file.
# Else it will try to pick params.ini in PWD
#
import os
import unittest
import fixtures
import testtools
import traceback

from common.contrail_test_init import ContrailTestInit
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from vm_test import *
from common.connections import ContrailConnections
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
from vnc_api import vnc_api
from vnc_api.gen.resource_test import *
from vdns_fixture import *
from floating_ip import *
from policy_test import *
from control_node import *
from user_test import UserFixture


class TestVdnsFixture(testtools.TestCase, VdnsFixture):

    #    @classmethod

    def setUp(self):
        super(TestVdnsFixture, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.quantum_h = self.connections.quantum_h
        self.nova_h = self.connections.nova_h
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.agent_inspect = self.connections.agent_inspect
        self.dnsagent_inspect = self.connections.dnsagent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.project_fq_name = None
        self.api_s_inspect = self.connections.api_server_inspect
        self.analytics_obj = self.connections.analytics_obj

    # end setUpClass

    def cleanUp(self):
        super(TestVdnsFixture, self).cleanUp()
    # end cleanUp

    def runTest(self):
        pass
    # end runTest

    # This Test test vdns functionality-- On VM launch agent should dynamically
    # update dns records to dns agent.
    # This test verifies the same functionality and should able to refer VM by
    # a name.
    @preposttest_wrapper
    def test_vdns_ping_same_vn(self):
        '''
        Test:- Test vdns functionality. On VM launch agent should dynamically
                  update dns records to dns agent
        1.  Create vDNS server
        2.  Create IPAM using above vDNS data
        3.  Create VN using above IPAM and launch 2 VM's within it
        4.  Ping between these 2 VM's using dns name
        5.  Try to delete vDNS server which has IPAM back-ref[Negative case]
        6.  Add CNAME VDNS record for vm1-test and
                verify we able to ping by alias name
        Pass criteria: Step 4,5 and 6 should pass

        Maintainer: cf-test@juniper.net
        '''
        vn1_ip = '10.10.10.1'
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
        project_fixture = self.useFixture(
            ProjectFixture(
                vnc_lib_h=self.vnc_lib,
                project_name=self.inputs.project_name,
                connections=self.connections))
        proj_fixt = self.useFixture(
            ProjectTestFixtureGen(self.vnc_lib, project_name=self.inputs.project_name))
        dns_data = VirtualDnsType(
            domain_name=domain_name, dynamic_records_from_client=True,
            default_ttl_seconds=ttl, record_order='random')
        # Create VDNS server object.
        vdns_fixt1 = self.useFixture(
            VdnsFixture(
                self.inputs,
                self.connections,
                vdns_name=dns_server_name,
                dns_data=dns_data))
        result, msg = vdns_fixt1.verify_on_setup()
        self.assertTrue(result, msg)
        dns_server = IpamDnsAddressType(
            virtual_dns_server_name=vdns_fixt1.vdns_fq_name)
        ipam_mgmt_obj = IpamType(
            ipam_dns_method='virtual-dns-server', ipam_dns_server=dns_server)
        # Associate VDNS with IPAM.
        ipam_fixt1 = self.useFixture(
            NetworkIpamTestFixtureGen(
                self.vnc_lib,
                virtual_DNS_refs=[
                    vdns_fixt1.obj],
                parent_fixt=proj_fixt,
                network_ipam_name=ipam_name,
                network_ipam_mgmt=ipam_mgmt_obj))
        vn_nets = {
            'vn1-vdns': [(ipam_fixt1.getObj(), VnSubnetsType(
                [IpamSubnetType(subnet=SubnetType(vn1_ip, 24))]))],
        }
        # Launch VN with IPAM
        vn_fixt = self.useFixture(
            VirtualNetworkTestFixtureGen(
                self.vnc_lib,
                virtual_network_name=vn_name,
                network_ipam_ref_infos=vn_nets[vn_name],
                parent_fixt=proj_fixt,
                id_perms=IdPermsType(
                    enable=True)))
        vm_fixture = {}
        # Launch  VM with VN Created above. This test verifies on
        # launch of VM agent should updated DNS 'A' and 'PTR' records
        # The following code will verify the same. Also, we should be able ping
        # with VM name.
        for vm_name in vm_list:
            vn_quantum_obj = self.quantum_h.get_vn_obj_if_present(
                vn_fixt._name)
            vm_fixture[vm_name] = self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_obj=vn_quantum_obj,
                    vm_name=vm_name))
            vm_fixture[vm_name].verify_vm_launched()
            vm_fixture[vm_name].verify_on_setup()
            vm_fixture[vm_name].wait_till_vm_is_up()
            vm_ip = vm_fixture[vm_name].get_vm_ip_from_vm(
                vn_fq_name=vm_fixture[vm_name].vn_fq_name)
            vm_rev_ip = vm_ip.split('.')
            vm_rev_ip = '.'.join(
                (vm_rev_ip[3], vm_rev_ip[2], vm_rev_ip[1], vm_rev_ip[0]))
            vm_rev_ip = vm_rev_ip + '.in-addr.arpa'
            msg = "Ping by using name %s is failed. Dns server \
                      should resolve VM name to IP" % (vm_name)
            self.assertTrue(vm_fixture[vm_name]
                            .ping_with_certainty(ip=vm_name), msg)
            # Frame the Expected DNS data for VM, one for 'A' record and
            # another 'PTR' record.
            rec_name = vm_name + "." + domain_name
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
            self.verify_vm_dns_data(vm_dns_exp_data)
            vm_dns_exp_data = []
        # ping between two vms which are in same subnets by using name.
        self.assertTrue(vm_fixture['vm1-test']
                        .ping_with_certainty(ip=vm_list[1]))
        # delete VDNS with ipam as back refrence.
        self.logger.info(
            "Try deleting the VDNS entry %s with back ref of ipam.",
            dns_server_name)
        try:
            self.vnc_lib.virtual_DNS_delete(
                fq_name=vdns_fixt1.obj.get_fq_name())
            errmsg = 'VDNS entry deleted which is not expected, \
                     when it has back refrence of ipam.'
            self.logger.error(errmsg)
            assert False, errmsg
        except Exception as msg:
            self.logger.info(msg)
            self.logger.info('Deletion of the vdns entry failed '
                             'with back ref of ipam as expected')
        # Add VDNS record 'CNAME' and add it to VDNS and ping with alias for
        # vm1-test
        self.logger.info('Add CNAME VDNS record for vm1-test and '
                         'verify we able to ping by alias name')
        vdns_rec_data = VirtualDnsRecordType(
            cname_rec, 'CNAME', 'IN', 'vm1-test', ttl)
        vdns_rec_fix = self.useFixture(
            VdnsRecordFixture(
                self.inputs,
                self.connections,
                'test-rec',
                vdns_fixt1.vdns_fix,
                vdns_rec_data))
        result, msg = vdns_rec_fix.verify_on_setup()
        self.assertTrue(result, msg)
        self.assertTrue(vm_fixture['vm1-test']
                        .ping_with_certainty(ip=cname_rec))
        return True
    # end test_vdns_ping_same_vn

    @preposttest_wrapper
    def test_vdns_ping_diff_vn(self):
        ''' This Test test vdns functionality-- test vms on different subnets
            and we should able to refer each by name.We should be able to
            ping each of vms by using name
        '''
        vn1_ip = '10.10.10.0'
        vn2_ip = '20.20.20.0'
        vm_list = ['vm1-test', 'vm2-test']
        vn_list = ['vn1', 'vn2']
        vm_vn_list = {'vm1-test': 'vn1', 'vm2-test': 'vn2'}
        dns_server_name = 'vdns1'
        domain_name = 'juniper.net'
        ttl = 100
        ipam_name = 'ipam1'
        rev_zone = vn1_ip.split('.')
        rev_zone = '.'.join((rev_zone[0], rev_zone[1], rev_zone[2]))
        rev_zone = rev_zone + '.in-addr.arpa'
        policy_name = 'policy1'
        project_fixture = self.useFixture(
            ProjectFixture(
                vnc_lib_h=self.vnc_lib,
                project_name=self.inputs.project_name,
                connections=self.connections))
        proj_fixt = self.useFixture(
            ProjectTestFixtureGen(self.vnc_lib, project_name=self.inputs.project_name))
        dns_data = VirtualDnsType(
            domain_name=domain_name, dynamic_records_from_client=True,
            default_ttl_seconds=ttl, record_order='random')
        vdns_fixt1 = self.useFixture(
            VdnsFixture(
                self.inputs,
                self.connections,
                vdns_name=dns_server_name,
                dns_data=dns_data))
        result, msg = vdns_fixt1.verify_on_setup()
        self.assertTrue(result, msg)
        dns_server = IpamDnsAddressType(
            virtual_dns_server_name=vdns_fixt1.vdns_fq_name)
        ipam_mgmt_obj = IpamType(
            ipam_dns_method='virtual-dns-server', ipam_dns_server=dns_server)
        # Associate IPAM with  VDNS server Object
        ipam_fixt1 = self.useFixture(
            NetworkIpamTestFixtureGen(
                self.vnc_lib,
                virtual_DNS_refs=[
                    vdns_fixt1.obj],
                parent_fixt=proj_fixt,
                network_ipam_name=ipam_name,
                network_ipam_mgmt=ipam_mgmt_obj))
        vn_nets = {
            'vn1': [(ipam_fixt1.getObj(),
                     VnSubnetsType([
                         IpamSubnetType(subnet=SubnetType(vn1_ip, 24))]))],
            'vn2': [(ipam_fixt1.getObj(),
                     VnSubnetsType([
                         IpamSubnetType(subnet=SubnetType(vn2_ip, 24))]))],
        }
        # create policy
        rules = {}
        rules[policy_name] = [
            PolicyRuleType(
                direction='<>', protocol='icmp', dst_addresses=[
                    AddressType(
                        virtual_network='any')], src_addresses=[
                    AddressType(
                        virtual_network='local')], action_list=ActionListType(
                            simple_action='pass'), src_ports=[
                                PortType(
                                    -1, -1)], dst_ports=[
                                        PortType(
                                            -1, -1)])]
        policy_fixt = self.useFixture(
            NetworkPolicyTestFixtureGen(
                self.vnc_lib,
                network_policy_name=policy_name,
                parent_fixt=proj_fixt,
                network_policy_entries=PolicyEntriesType(
                    rules[policy_name])))
        policy_ref = [
            (policy_fixt.getObj(),
             VirtualNetworkPolicyType(
                sequence=SequenceType(
                    major=0,
                    minor=0)))]

        vn_fixt = {}
        vm_fixture = {}
        # Launch  VM with VN Created above. This test verifies
        # on launch of VM agent should updated DNS 'A' and 'PTR' records
        # The following code will verify the same. Also, we should be able ping
        # with VM name.
        for vm_name in vm_list:
            vn = vm_vn_list[vm_name]
            vn_fixt[vm_name] = self.useFixture(
                VirtualNetworkTestFixtureGen(
                    self.vnc_lib,
                    virtual_network_name=vm_vn_list[vm_name],
                    network_ipam_ref_infos=vn_nets[vn],
                    parent_fixt=proj_fixt,
                    id_perms=IdPermsType(
                        enable=True),
                    network_policy_ref_infos=policy_ref))
            vn_quantum_obj = self.quantum_h.get_vn_obj_if_present(vn)
            vm_fixture[vm_name] = self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_obj=vn_quantum_obj,
                    vm_name=vm_name))
            vm_fixture[vm_name].verify_vm_launched()
            vm_fixture[vm_name].verify_on_setup()
            vm_fixture[vm_name].wait_till_vm_is_up()
            msg = "Ping by using name %s is failed." % (vm_name)
            msg += "Dns server should resolve VM name to IP"
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
            self.verify_vm_dns_data(vm_dns_exp_data)
            vm_dns_exp_data = []
            # for test
            add = 'Address:.*' + vm_ip
            exp_data = vm_ip
            cmd = 'nslookup ' + vm_name + '|' + ' grep ' + '\'' + add + '\''
            msg = 'nslookup failed for VM  ' + vm_name
            self.assertTrue(
                self.verify_ns_lookup_data(
                    vm_fixture[vm_name],
                    cmd,
                    exp_data),
                msg)
            cmd = 'nslookup ' + vm_ip + '|' + ' grep ' + '\'' + vm_name + '\''
            exp_data = vm_name + '.' + domain_name
            msg = 'reverse nslookup failed for VM  ' + vm_name
            self.assertTrue(
                self.verify_ns_lookup_data(
                    vm_fixture[vm_name],
                    cmd,
                    exp_data),
                msg)
        # ping between two vms which are in different subnets by using name.
        self.assertTrue(vm_fixture['vm1-test']
                        .ping_with_certainty(ip=vm_list[1]))
        # Add VDNS record and verify TTL value correctly
        self.logger.info(
            'Add VDNS record and verify TTL value is set'
            ' correctly using with dig command')
        vdns_rec_data = VirtualDnsRecordType('rec1', 'A', 'IN', '1.1.1.1', ttl)
        vdns_rec_fix = self.useFixture(
            VdnsRecordFixture(
                self.inputs,
                self.connections,
                'test-rec',
                vdns_fixt1.vdns_fix,
                vdns_rec_data))
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
                            'Failed to configure invalid TTL as expected')
                        continue
                    else:
                        self.assertTrue(False, 'Failed to Modify TTL values')
            vm_fixture['vm1-test'].run_cmd_on_vm(cmds=[cmd])
            result = vm_fixture['vm1-test'].return_output_cmd_dict[cmd]
            result = result.replace("\t", " ")
            m_obj = re.search(
                r"rec1.juniper.net\.*\s*([0-9.]*)\s*IN\s*A\s*([0-9.]*)",
                result)
            if not m_obj:
                self.assertTrue(
                    False,
                    'record search is failed,please check '
                    'syntax of regular expression')
            print ("\nTTL VALUE is %s ", m_obj.group(1))
            print ("\nrecord ip address is %s", m_obj.group(2))
            self.assertEqual(int(m_obj.group(
                1)), ttl_mod, 'TTL value is not matching for '
                'static record after record modification')
            self.assertEqual(
                m_obj.group(2),
                ip_add,
                'IP Address is not matching for static record '
                'after record modification')
            i = i + 1
        return True
    # end of test_vdns_ping_diff_vn

    # This test creates 3 vnds servers vdns1,vdns2 and vdns3.
    # For vdns2 and vdns3, vdns1 act a next vdns nerver.
    # The VDNS server are configured as shown below.
    #                         vdns1 (domain: juniper.net)
    #                        ^     ^
    #                       /       \
    #                      /         \
    #   (bng.juniper.net) vdns2        vdns3(eng.juniper.net)
    #
    #
    @preposttest_wrapper
    def test_vdns_with_next_vdns(self):
        ''' This test creates 3 vnds servers vdns1,vdns2 and vdns3.
            For vdns2 and vdns3, vdns1 act a next vdns nerver.
        '''
        vn1_ip = '10.10.10.0'
        vn2_ip = '20.20.20.0'
        vn3_ip = '30.30.30.0'
        vm_list = ['vm1-test', 'vm2-test', 'vm3-test']
        vm_vn_list = {'vm1-test': 'vn1', 'vm2-test': 'vn2', 'vm3-test': 'vn3'}
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

        project_fixture = self.useFixture(
            ProjectFixture(
                vnc_lib_h=self.vnc_lib,
                project_name=self.inputs.project_name,
                connections=self.connections))
        proj_fixt = self.useFixture(
            ProjectTestFixtureGen(self.vnc_lib, project_name=self.inputs.project_name))
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
                vdns_data[dns_name] = VirtualDnsType(
                    domain_name=domain_name_list[dns_name],
                    dynamic_records_from_client=True,
                    default_ttl_seconds=ttl,
                    record_order='random')
            else:
                # VDNS2 and VDNS3 need to point VDNS1 as next vdns server.
                vdns_data[dns_name] = VirtualDnsType(
                    domain_name=domain_name_list[dns_name],
                    dynamic_records_from_client=True,
                    default_ttl_seconds=ttl,
                    record_order='random',
                    next_virtual_DNS=vdns_fix['vdns1'].vdns_fq_name)
            vdns_fix[dns_name] = self.useFixture(
                VdnsFixture(
                    self.inputs,
                    self.connections,
                    vdns_name=dns_name,
                    dns_data=vdns_data[dns_name]))
            result, msg = vdns_fix[dns_name].verify_on_setup()
            self.assertTrue(result, msg)

        # Try to delete vdns entry which was referenced in other vdns entry,
        # deletion should fail.
        self.logger.info(
            "Try deleting the VDNS entry %s with back ref.", dns_server_name1)
        try:
            self.vnc_lib.virtual_DNS_delete(
                fq_name=vdns_fix[dns_server_name1].obj.get_fq_name())
            errmsg = "VDNS entry deleted which is not expected, "
            errmsg += "when it is attached to a other vdns servers."
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
                    domain_name_list[dns_name],
                    'NS',
                    'IN',
                    vdns_fix[dns_name].vdns_fq_name,
                    ttl)
                vdns_rec[dns_name] = self.useFixture(
                    VdnsRecordFixture(
                        self.inputs,
                        self.connections,
                        rec_names[dns_name],
                        vdns_fix['vdns1'].vdns_fix,
                        vdns_rec_data))
                result, msg = vdns_rec[dns_name].verify_on_setup()
                self.assertTrue(result, msg)

        ipam_fixt = {}
        # Create IPAM entrys with VDNS servers
        for ipam in ipam_dns_list:
            dns_server = IpamDnsAddressType(
                virtual_dns_server_name=vdns_fix[ipam].vdns_fq_name)
            ipam_mgmt_obj = IpamType(
                ipam_dns_method='virtual-dns-server',
                ipam_dns_server=dns_server)
            ipam_fixt[ipam] = self.useFixture(
                NetworkIpamTestFixtureGen(
                    self.vnc_lib,
                    virtual_DNS_refs=[
                        vdns_fix[ipam].obj],
                    parent_fixt=proj_fixt,
                    network_ipam_name=ipam_dns_list[ipam],
                    network_ipam_mgmt=ipam_mgmt_obj))

        rules = {}
        rules[policy_name] = [
            PolicyRuleType(
                direction='<>', protocol='icmp', dst_addresses=[
                    AddressType(
                        virtual_network='any')], src_addresses=[
                    AddressType(
                        virtual_network='any')], action_list=ActionListType(
                            simple_action='pass'), src_ports=[
                                PortType(
                                    -1, -1)], dst_ports=[
                                        PortType(
                                            -1, -1)])]
        policy_fixt = self.useFixture(
            NetworkPolicyTestFixtureGen(
                self.vnc_lib,
                network_policy_name=policy_name,
                parent_fixt=proj_fixt,
                network_policy_entries=PolicyEntriesType(
                    rules[policy_name])))
        policy_ref = [
            (policy_fixt.getObj(),
             VirtualNetworkPolicyType(
                sequence=SequenceType(
                    major=0,
                    minor=0)))]

        vn_nets = {
            'vn1': [(ipam_fixt['vdns1'].getObj(), VnSubnetsType([
                IpamSubnetType(subnet=SubnetType(vn1_ip, 24))]))],
            'vn2': [(ipam_fixt['vdns2'].getObj(), VnSubnetsType([
                IpamSubnetType(subnet=SubnetType(vn2_ip, 24))]))],
            'vn3': [(ipam_fixt['vdns3'].getObj(), VnSubnetsType([
                IpamSubnetType(subnet=SubnetType(vn3_ip, 24))]))],
        }

        vn_fixt = {}
        vm_fixture = {}
        # Launch  VM with VN Created above. This test verifies
        # on launch of VM agent should updated DNS 'A' and 'PTR' records
        # The following code will verify the same. Also, we should be able ping
        # with VM name.
        for vm_name in vm_list:
            vn = vm_vn_list[vm_name]
            vn_fixt[vm_name] = self.useFixture(
                VirtualNetworkTestFixtureGen(
                    self.vnc_lib,
                    virtual_network_name=vm_vn_list[vm_name],
                    network_ipam_ref_infos=vn_nets[vn],
                    parent_fixt=proj_fixt,
                    id_perms=IdPermsType(
                        enable=True),
                    network_policy_ref_infos=policy_ref))
            vn_quantum_obj = self.quantum_h.get_vn_obj_if_present(vn)
            vm_fixture[vm_name] = self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_obj=vn_quantum_obj,
                    vm_name=vm_name))
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
            "Try deleting the VDNS entry %s with back ref of vdns records.",
            dns_server_name1)
        try:
            self.vnc_lib.virtual_DNS_delete(
                fq_name=vdns_fix[dns_server_name1].obj.get_fq_name())
            errmsg = "VDNS entry deleted which is not "
            errmsg += "expected, when it had vdns records."
            self.logger.error(errmsg)
            assert False, errmsg
        except Exception as msg:
            self.logger.info(msg)
            self.logger.info(
                'Not able to delete the vdns entry'
                'with back ref of vdns records')
        return True

    @preposttest_wrapper
    def test_vdns_controlnode_switchover(self):
        ''' This test test control node switchover functionality'''
        restart_process = 'ControlNodeRestart'
        self.vdns_with_cn_dns_agent_restart(restart_process)
        return True

    @preposttest_wrapper
    def test_vdns_dns_restart(self):
        ''' This test test dns process restart functionality'''
        restart_process = 'DnsRestart'
        self.vdns_with_cn_dns_agent_restart(restart_process)
        return True

    @preposttest_wrapper
    def test_vdns_agent_restart(self):
        '''This test tests agent process restart functionality'''
        restart_process = 'AgentRestart'
        self.vdns_with_cn_dns_agent_restart(restart_process)
        return True

    @preposttest_wrapper
    def test_vdns_named_restart(self):
        '''This test tests named process restart functionality'''
        restart_process = 'NamedRestart'
        self.vdns_with_cn_dns_agent_restart(restart_process)
        return True

    @preposttest_wrapper
    def test_vdns_scp(self):
        '''This test tests scp with VDNS functionality'''
        restart_process = 'scp'
        self.vdns_with_cn_dns_agent_restart(restart_process)
        return True

    # This Test test vdns functionality with control node restart
    def vdns_with_cn_dns_agent_restart(self, restart_process):
        '''
         This test test the functionality of controlnode/dns/agent
         restart with vdns feature.
        '''
        if restart_process == 'ControlNodeRestart':
            if len(set(self.inputs.bgp_ips)) < 2:
                raise self.skipTest(
                    "Skipping Test. At least 2 control nodes required"
                    " to run the control node switchover test")
        vn1_ip = '10.10.10.1'
        vm_list = ['vm1-test', 'vm2-test']
        vn_name = 'vn1'
        dns_server_name = 'vdns1'
        domain_name = 'juniper.net'
        ttl = 100
        ipam_name = 'ipam1'
        rev_zone = vn1_ip.split('.')
        rev_zone = '.'.join((rev_zone[0], rev_zone[1], rev_zone[2]))
        rev_zone = rev_zone + '.in-addr.arpa'
        project_fixture = self.useFixture(
            ProjectFixture(
                vnc_lib_h=self.vnc_lib,
                project_name=self.inputs.project_name,
                connections=self.connections))
        proj_fixt = self.useFixture(
            ProjectTestFixtureGen(self.vnc_lib, project_name=self.inputs.project_name))
        dns_data = VirtualDnsType(
            domain_name=domain_name, dynamic_records_from_client=True,
            default_ttl_seconds=ttl, record_order='random')
        # Create VDNS server object.
        vdns_fixt1 = self.useFixture(
            VdnsFixture(
                self.inputs,
                self.connections,
                vdns_name=dns_server_name,
                dns_data=dns_data))
        result, msg = vdns_fixt1.verify_on_setup()
        self.assertTrue(result, msg)
        dns_server = IpamDnsAddressType(
            virtual_dns_server_name=vdns_fixt1.vdns_fq_name)
        ipam_mgmt_obj = IpamType(
            ipam_dns_method='virtual-dns-server', ipam_dns_server=dns_server)
        # Associate VDNS with IPAM.
        ipam_fixt1 = self.useFixture(
            NetworkIpamTestFixtureGen(
                self.vnc_lib,
                virtual_DNS_refs=[
                    vdns_fixt1.obj],
                parent_fixt=proj_fixt,
                network_ipam_name=ipam_name,
                network_ipam_mgmt=ipam_mgmt_obj))
        vn_nets = {'vn1': [(ipam_fixt1.getObj(), VnSubnetsType(
            [IpamSubnetType(subnet=SubnetType(vn1_ip, 24))]))], }
        # Launch VN with IPAM
        vn_fixt = self.useFixture(
            VirtualNetworkTestFixtureGen(
                self.vnc_lib,
                virtual_network_name=vn_name,
                network_ipam_ref_infos=vn_nets[vn_name],
                parent_fixt=proj_fixt,
                id_perms=IdPermsType(
                    enable=True)))
        vm_fixture = {}
        vm_dns_exp_data = {}
        # Launch  VM with VN Created above. This test verifies on
        # launch of VM agent should updated DNS 'A' and 'PTR' records
        # The following code will verify the same. Also, we should be able ping
        # with VM name.
        for vm_name in vm_list:
            vn_quantum_obj = self.quantum_h.get_vn_obj_if_present(
                vn_fixt._name)
            vm_fixture[vm_name] = self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_obj=vn_quantum_obj,
                    vm_name=vm_name))
            vm_fixture[vm_name].verify_vm_launched()
            vm_fixture[vm_name].verify_on_setup()
            vm_fixture[vm_name].wait_till_vm_is_up()
            vm_ip = vm_fixture[vm_name].get_vm_ip_from_vm(
                vn_fq_name=vm_fixture[vm_name].vn_fq_name)
            vm_rev_ip = vm_ip.split('.')
            vm_rev_ip = '.'.join(
                (vm_rev_ip[3], vm_rev_ip[2], vm_rev_ip[1], vm_rev_ip[0]))
            vm_rev_ip = vm_rev_ip + '.in-addr.arpa'
            # Frame the Expected DNS data for VM, one for 'A' record and
            # another 'PTR' record.
            rec_name = vm_name + "." + domain_name
            vm_dns_exp_data[vm_name] = [{'rec_data': vm_ip,
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
            self.verify_vm_dns_data(vm_dns_exp_data[vm_name])
        # ping between two vms which are in same subnets by using name.
        self.assertTrue(vm_fixture['vm1-test']
                        .ping_with_certainty(ip=vm_list[1]))
        active_controller = vm_fixture['vm1-test'].get_active_controller()
        self.logger.info(
            'Active control node from the Agent %s is %s' %
            (vm_fixture['vm1-test'].vm_node_ip, active_controller))
        # Control node restart/switchover.
        if restart_process == 'ControlNodeRestart':
            # restart the Active control node
            self.logger.info('restarting active control node')
            self.inputs.restart_service(
                'contrail-control', [active_controller])
            sleep(5)
            # Check the control node shifted to other control node
            new_active_controller = vm_fixture[
                'vm1-test'].get_active_controller()
            self.logger.info(
                'Active control node from the Agent %s is %s' %
                (vm_fixture['vm1-test'].vm_node_ip, new_active_controller))
            if new_active_controller == active_controller:
                self.logger.error(
                    'Control node switchover fail. Old Active controlnode '
                    'was %s and new active control node is %s' %
                    (active_controller, new_active_controller))
                return False
            self.inputs.restart_service(
                'contrail-control', [new_active_controller])
        if restart_process == 'DnsRestart':
            # restart the dns process in the active control node
            self.logger.info(
                'restart the dns process in the active control node')
            self.inputs.restart_service('contrail-dns', [active_controller])
        if restart_process == 'NamedRestart':
            # restart the named process in the active control node
            self.logger.info(
                'restart the named process in the active control node')
            self.inputs.restart_service('contrail-named', [active_controller])
        # restart the agent process in the compute node
        if restart_process == 'AgentRestart':
            self.logger.info('restart the agent process')
            for compute_ip in self.inputs.compute_ips:
                self.inputs.restart_service('contrail-vrouter-agent', [compute_ip])
        if restart_process == 'scp':
            self.logger.info('scp using name of vm')
            vm_fixture['vm1-test'].put_pub_key_to_vm()
            vm_fixture['vm2-test'].put_pub_key_to_vm()
            size = '1000'
            file = 'testfile'
            y = 'ls -lrt %s' % file
            cmd_to_check_file = [y]
            cmd_to_sync = ['sync']
            create_result = True
            transfer_result = True

            self.logger.info("-" * 80)
            self.logger.info("FILE SIZE = %sB" % size)
            self.logger.info("-" * 80)
            self.logger.info('Creating a file of the specified size on %s' %
                             vm_fixture['vm1-test'].vm_name)

            self.logger.info(
                'Transferring the file from %s to %s using scp' %
                (vm_fixture['vm1-test'].vm_name,
                    vm_fixture['vm2-test'].vm_name))
            vm_fixture['vm1-test'].check_file_transfer(
                dest_vm_fixture=vm_fixture['vm2-test'],
                mode='scp',
                size=size)

            self.logger.info('Checking if the file exists on %s' %
                             vm_fixture['vm2-test'].vm_name)
            vm_fixture['vm2-test'].run_cmd_on_vm(cmds=cmd_to_check_file)
            output = vm_fixture['vm2-test'].return_output_cmd_dict[y]
            print output
            if size in output:
                self.logger.info(
                    'File of size %sB transferred via scp properly' % size)
            else:
                transfer_result = False
                self.logger.error(
                    'File of size %sB not transferred via scp ' % size)
            assert transfer_result, 'File not transferred via scp'
        # Verify after controlnode/dns/agent/named process restart ping vm's by
        # using name.
        for vm_name in vm_list:
            msg = "Ping by using name %s is failed after controlnode/dns/"\
                  "agent/named process restart. Dns server should resolve "\
                  "VM name to IP" % (vm_name)
            self.assertTrue(vm_fixture[vm_name]
                            .ping_with_certainty(ip=vm_name), msg)
            self.verify_vm_dns_data(vm_dns_exp_data[vm_name])
        return True
    # end test_vdns_controlnode_switchover

    @preposttest_wrapper
    def test_vdns_roundrobin_rec_order(self):
        ''' This test tests vdns round-robin record order'''
        record_order = 'round-robin'
        self.verify_dns_record_order(record_order)
        return True

    @preposttest_wrapper
    def test_vdns_random_rec_order(self):
        ''' This test tests vdns random record order'''
        record_order = 'random'
        self.verify_dns_record_order(record_order)
        return True

    @preposttest_wrapper
    def test_vdns_fixed_rec_order(self):
        '''This test tests vdns fixed record order'''
        record_order = 'fixed'
        self.verify_dns_record_order(record_order)
        return True

    # until Bug #1866 is resolved this test is going to run for 1000 records.
    @preposttest_wrapper
    def test_vdns_zrecord_scaling(self):
        '''This test tests vdns fixed record order'''
        record_order = 'random'
        test_type = 'recordscaling'
        record_num = 1000
        self.verify_dns_record_order(record_order, test_type, record_num)
        return True

    def verify_dns_record_order(
            self,
            record_order,
            test_type='test_record_order',
            record_num=10):
        ''' This test tests DNS record order.
            Round-Robin/Fixed/Random
        '''
        vn1_ip = '10.10.10.1'
        vn_name = 'vn1'
        dns_server_name = 'vdns1'
        domain_name = 'juniper.net'
        ttl = 100
        ipam_name = 'ipam1'
        project_fixture = self.useFixture(
            ProjectFixture(
                vnc_lib_h=self.vnc_lib,
                project_name=self.inputs.project_name,
                connections=self.connections))
        proj_fixt = self.useFixture(
            ProjectTestFixtureGen(self.vnc_lib, project_name=self.inputs.project_name))
        dns_data = VirtualDnsType(
            domain_name=domain_name, dynamic_records_from_client=True,
            default_ttl_seconds=ttl, record_order=record_order)
        # Create VDNS server object.
        vdns_fixt1 = self.useFixture(
            VdnsFixture(
                self.inputs,
                self.connections,
                vdns_name=dns_server_name,
                dns_data=dns_data))
        result, msg = vdns_fixt1.verify_on_setup()
        self.assertTrue(result, msg)
        dns_server = IpamDnsAddressType(
            virtual_dns_server_name=vdns_fixt1.vdns_fq_name)
        ipam_mgmt_obj = IpamType(
            ipam_dns_method='virtual-dns-server', ipam_dns_server=dns_server)
        # Associate VDNS with IPAM.
        ipam_fixt1 = self.useFixture(
            NetworkIpamTestFixtureGen(
                self.vnc_lib,
                virtual_DNS_refs=[
                    vdns_fixt1.obj],
                parent_fixt=proj_fixt,
                network_ipam_name=ipam_name,
                network_ipam_mgmt=ipam_mgmt_obj))
        vn_nets = {'vn1': [(ipam_fixt1.getObj(), VnSubnetsType(
            [IpamSubnetType(subnet=SubnetType(vn1_ip, 24))]))], }
        # Launch VN with IPAM
        vn_fixt = self.useFixture(
            VirtualNetworkTestFixtureGen(
                self.vnc_lib,
                virtual_network_name=vn_name,
                network_ipam_ref_infos=vn_nets[vn_name],
                parent_fixt=proj_fixt,
                id_perms=IdPermsType(
                    enable=True)))
        vn_quantum_obj = self.quantum_h.get_vn_obj_if_present(
            vn_fixt._name)
        vm_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn_quantum_obj,
                vm_name='vm1-test'))
        vm_fixture.verify_vm_launched()
        vm_fixture.verify_on_setup()
        vm_fixture.wait_till_vm_is_up()

        rec_ip_list = []
        i = 1
        j = 1
        k = 1
        l = 1
        verify_rec_name_list = []
        verify_rec_name_ip = {}
        if test_type == 'recordscaling':
            self.logger.info('Creating %s number of records', record_num)
            for num in range(1, record_num):
                rec = 'test-rec-' + str(j) + '-' + str(i)
                self.logger.info('Creating record %s', rec)
                recname = 'rec' + str(j) + '-' + str(i)
                rec_ip = str(l) + '.' + str(k) + '.' + str(j) + '.' + str(i)
                vdns_rec_data = VirtualDnsRecordType(
                    recname, 'A', 'IN', rec_ip, ttl)
                vdns_rec_fix = self.useFixture(
                    VdnsRecordFixture(
                        self.inputs,
                        self.connections,
                        rec,
                        vdns_fixt1.vdns_fix,
                        vdns_rec_data))
                sleep(1)
                i = i + 1
                if i > 253:
                    j = j + 1
                    i = 1
                if j > 253:
                    k = k + 1
                    j = 1
                    i = 1
                # sleep for some time after configuring 10 records.
                if num % 10 == 0:
                    sleep(0.5)
                # pic some random records for nslookup verification
                if num % 100 == 0:
                    verify_rec_name_list.append(recname)
                    verify_rec_name_ip[recname] = rec_ip
            # Sleep for some time - DNS takes some time to sync with BIND
            # server
            self.logger.info(
                'Sleep for 180sec to sync vdns server with vdns record entry')
            sleep(180)
            # Verify NS look up works for some random records values
            self.logger.info('****NSLook up verification****')
            import re
            for rec in verify_rec_name_list:
                cmd = 'nslookup ' + rec
                vm_fixture.run_cmd_on_vm(cmds=[cmd])
                result = vm_fixture.return_output_cmd_dict[cmd]
                result = result.replace("\r", "")
                result = result.replace("\t", "")
                result = result.replace("\n", " ")
                m_obj = re.search(
                    r"Address:[0-9.]*#[0-9]*\s*.*Name:(.*\.juniper\.net)\s*Address:\s*([0-9.]*)",
                    result)
                if not m_obj:
                    self.assertTrue(
                        False,
                        'record search is failed,please check syntax of the '
                        'regular expression/NSlookup is failed')
                print ('vm_name is ---> %s \t ip-address is ---> %s' %
                       (m_obj.group(1), m_obj.group(2)))
        else:
            for num in range(1, record_num):
                rec = 'test-rec-' + str(j) + '-' + str(i)
                rec_ip = '1.' + '1.' + str(j) + '.' + str(i)
                vdns_rec_data = VirtualDnsRecordType(
                    'test1', 'A', 'IN', rec_ip, ttl)
                vdns_rec_fix = self.useFixture(
                    VdnsRecordFixture(
                        self.inputs,
                        self.connections,
                        rec,
                        vdns_fixt1.vdns_fix,
                        vdns_rec_data))
                result, msg = vdns_rec_fix.verify_on_setup()
                i = i + 1
                if i > 253:
                    j = j + 1
                    i = 1
                rec_ip_list.append(rec_ip)
                sleep(2)
            # Get the NS look up record Verify record order
            cmd = 'nslookup test1'
            vm_fixture.run_cmd_on_vm(cmds=[cmd])
            result = vm_fixture.return_output_cmd_dict[cmd]
            result = result.replace("\r", "")
            result = result.replace("\t", "")
            result = result.replace("\n", " ")
            import re
            m_obj = re.search(
                r"Address:[0-9.]*#[0-9]*\s*Name:test1.juniper.net\s*(Address:\s*[0-9.]*)",
                result)
            if not m_obj:
                self.assertTrue(
                    False,
                    'record search is failed,please check '
                    'syntax of regular expression')
            print m_obj.group(1)
            dns_record = m_obj.group(1).split(':')
            dns_record_ip = dns_record[1].lstrip()
            next_ip = self.next_ip_in_list(rec_ip_list, dns_record_ip)
            for rec in rec_ip_list:
                vm_fixture.run_cmd_on_vm(cmds=[cmd])
                result = vm_fixture.return_output_cmd_dict[cmd]
                result = result.replace("\r", "")
                result = result.replace("\t", "")
                result = result.replace("\n", " ")
                m_obj = re.search(
                    r"Address:[0-9.]*#[0-9]*\s*Name:test1.juniper.net\s*(Address:\s*[0-9.]*)",
                    result)
                print m_obj.group(1)
                dns_record = m_obj.group(1).split(':')
                dns_record_ip1 = dns_record[1].lstrip()
                if record_order == 'round-robin':
                    if next_ip != dns_record_ip1:
                        print "\n VDNS records are not sent in \
                            round-robin order"
                        self.assertTrue(
                            False,
                            'VDNS records are not sent in round-robin order')
                    next_ip = self.next_ip_in_list(rec_ip_list, dns_record_ip1)
                if record_order == 'random':
                    if dns_record_ip1 not in rec_ip_list:
                        print "\n VDNS records are not sent in random order"
                        self.assertTrue(
                            False, 'VDNS records are not sent random order')
                if record_order == 'fixed':
                    if dns_record_ip != dns_record_ip1:
                        print "\n VDNS records are not sent \
                            fixed in fixed order"
                        self.assertTrue(
                            False,
                            'VDNS records are not sent fixed in fixed order')
        return True
    # end test_dns_record_order

    @preposttest_wrapper
    def test_vdns_with_fip(self):
        ''' This Test test vdns functionality with floating ip.
        '''
        vn_nets = {'vn1': ['10.10.10.0/24'], 'vn2': ['20.20.20.0/24']}
        vm_list = ['vm1-test', 'vm2-test']
        vm_vn_list = {'vm1-test': 'vn1', 'vm2-test': 'vn2'}
        dns_server_name = 'vdns1'
        domain_name = 'juniper.net'
        ttl = 100
        ipam_name = 'ipam1'
        fip_pool_name1 = 'some-pool1'
        project_fixture = self.useFixture(
            ProjectFixture(
                vnc_lib_h=self.vnc_lib,
                project_name=self.inputs.project_name,
                connections=self.connections))
        proj_fixt = self.useFixture(
            ProjectTestFixtureGen(self.vnc_lib, project_name=self.inputs.project_name))
        # VDNS
        dns_data = VirtualDnsType(
            domain_name=domain_name, dynamic_records_from_client=True,
            default_ttl_seconds=ttl, record_order='random')
        vdns_fixt1 = self.useFixture(
            VdnsFixture(
                self.inputs,
                self.connections,
                vdns_name=dns_server_name,
                dns_data=dns_data))
        result, msg = vdns_fixt1.verify_on_setup()
        self.assertTrue(result, msg)
        dns_server = IpamDnsAddressType(
            virtual_dns_server_name=vdns_fixt1.vdns_fq_name)
        # IPAM
        ipam_mgmt_obj = IpamType(
            ipam_dns_method='virtual-dns-server', ipam_dns_server=dns_server)
        # Associate IPAM with  VDNS server Object
        ipam_fixt1 = self.useFixture(
            NetworkIpamTestFixtureGen(
                self.vnc_lib,
                virtual_DNS_refs=[
                    vdns_fixt1.obj],
                parent_fixt=proj_fixt,
                network_ipam_name=ipam_name,
                network_ipam_mgmt=ipam_mgmt_obj))

        vn_fixt = {}
        vm_fixture = {}
        # Launch  VM with VN Created above. This test verifies
        # on launch of VM agent should updated DNS 'A' and 'PTR' records
        # The following code will verify the same. Also, we should be able ping
        # with VM name.
        for vm_name in vm_list:
            vn = vm_vn_list[vm_name]
            vn_fixt[vm_name] = self.useFixture(
                VNFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_name=vm_vn_list[vm_name],
                    inputs=self.inputs,
                    subnets=vn_nets[vn],
                    ipam_fq_name=ipam_fixt1.getObj().get_fq_name()))
            vm_fixture[vm_name] = self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_obj=vn_fixt[vm_name].obj,
                    vm_name=vm_name))
            vm_fixture[vm_name].verify_vm_launched()
            vm_fixture[vm_name].verify_on_setup()
            vm_fixture[vm_name].wait_till_vm_is_up()

        # FIP
        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name1,
                vn_id=vn_fixt['vm2-test'].vn_id))
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
    def test_vdns_with_diff_projs(self):
        ''' Test vdns with different projects '''
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
        vdns_fixt1 = self.useFixture(
            VdnsFixture(
                self.inputs,
                self.connections,
                vdns_name=dns_server_name,
                dns_data=dns_data))
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
        rules = {'project1': [{'direction': '<>',
                               'protocol': 'any',
                               'dest_network': 'default-domain:project2:vn2',
                               'source_network': 'any',
                               'dst_ports': 'any',
                               'simple_action': 'pass',
                               'src_ports': 'any'}],
                 'project2': [{'direction': '<>',
                               'protocol': 'any',
                               'dest_network': 'default-domain:project1:vn1',
                               'source_network': 'any',
                               'dst_ports': 'any',
                               'simple_action': 'pass',
                               'src_ports': 'any'}]}
        admin_ip = self.inputs
        admin_con = self.connections
        for proj in project_list:
            # Project creation
            user_fixture = self.useFixture(
                UserFixture(
                    connections=self.connections,
                    username=proj_user[proj],
                    password=proj_pass[proj]))
            project_fixture = self.useFixture(
                ProjectFixture(
                    project_name=proj,
                    username=proj_user[proj],
                    password=proj_pass[proj],
                    vnc_lib_h=self.vnc_lib,
                    connections=admin_con))
            user_fixture.add_user_to_tenant(proj, proj_user[proj], 'admin')
            project_inputs = self.useFixture(
                ContrailTestInit(
                    self.ini_file,
                    stack_user=project_fixture.username,
                    stack_password=project_fixture.password,
                    project_fq_name=[
                        'default-domain',
                        proj]))
            project_connections = ContrailConnections(project_inputs)
            proj_fixt = self.useFixture(
                ProjectTestFixtureGen(self.vnc_lib, project_name=proj))
            self.logger.info(
                'Default SG to be edited for allow all on project: %s' % proj)
            project_fixture.set_sec_group_for_allow_all(proj, 'default')
            # policy creation
            pol_fixt[proj] = self.useFixture(
                PolicyFixture(
                    policy_name=policy_list[proj],
                    inputs=project_inputs,
                    connections=project_connections,
                    rules_list=rules[proj]))
            # Ipam creation
            ipam_fixt[proj] = self.useFixture(
                NetworkIpamTestFixtureGen(
                    self.vnc_lib,
                    virtual_DNS_refs=[
                        vdns_fixt1.obj],
                    parent_fixt=proj_fixt,
                    network_ipam_name=ipam_list[proj],
                    network_ipam_mgmt=ipam_mgmt_obj))
            # VN Creation
            vn_fixt[proj] = self.useFixture(
                VNFixture(
                    project_name=proj,
                    connections=project_connections,
                    vn_name=vn_list[proj],
                    inputs=project_inputs,
                    subnets=vn_nets[proj],
                    ipam_fq_name=ipam_fixt[proj].getObj().get_fq_name(),
                    policy_objs=[
                        pol_fixt[proj].policy_obj]))
            # VM creation
            vm_fix[proj] = self.useFixture(
                VMFixture(
                    project_name=proj,
                    connections=project_connections,
                    vn_obj=vn_fixt[proj].obj,
                    vm_name=vm_list[proj]))
            vm_fix[proj].verify_vm_launched()
            vm_fix[proj].verify_on_setup()
            vm_fix[proj].wait_till_vm_is_up()
            msg = "Ping by using name %s is failed. Dns server should \
                  resolve VM name to IP" % (vm_list[proj])
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
            self.verify_vm_dns_data(vm_dns_exp_data)
            vm_dns_exp_data = []
        # ping between two vms which are in different subnets by using name.
        self.assertTrue(
            vm_fix['project1'].ping_with_certainty(
                ip=vm_list['project2']),
            "Ping with VM name failed for VDNS across the projects")
        return True

    @preposttest_wrapper
    def test_vdns_default_mode(self):
        ''' Test vdns with default and None DNS Methods'''
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

        project_fixture = self.useFixture(
            ProjectFixture(
                vnc_lib_h=self.vnc_lib,
                project_name=self.inputs.project_name,
                connections=self.connections))
        proj_fixt = self.useFixture(
            ProjectTestFixtureGen(self.vnc_lib, project_name=self.inputs.project_name))
        # VN Creation
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
        # Default DNS server
        ipam_mgmt_obj = IpamType(ipam_dns_method='default-dns-server')
        # Associate VDNS with IPAM.
        ipam_fixt1 = self.useFixture(
            NetworkIpamTestFixtureGen(
                self.vnc_lib,
                parent_fixt=proj_fixt,
                network_ipam_name=ipam_name,
                network_ipam_mgmt=ipam_mgmt_obj))
        vn_fixt = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn_name,
                inputs=self.inputs,
                subnets=vn_nets[vn_name],
                ipam_fq_name=ipam_fixt1.getObj().get_fq_name()))
        vm_fix = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn_fixt.obj,
                vm_name=vm_name))
        vm_fix.verify_vm_launched()
        vm_fix.verify_on_setup()
        vm_fix.wait_till_vm_is_up()
        # FIP creation
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name,
                vn_id=fvn_fixture.vn_id))
        assert fip_fixture.verify_on_setup()
        fip_id = fip_fixture.create_and_assoc_fip(
            fvn_fixture.vn_id, vm_fix.vm_id)
        self.addCleanup(fip_fixture.disassoc_and_delete_fip, fip_id)
        assert fip_fixture.verify_fip(fip_id, vm_fix, fvn_fixture)
        routing_instance = fvn_fixture.ri_name
        # Configuring all control nodes here
        for entry in self.inputs.bgp_ips:
            hostname = self.inputs.host_data[entry]['name']
            cn_fixture1 = self.useFixture(
                CNFixture(
                    connections=self.connections,
                    router_name=hostname,
                    router_ip=entry,
                    router_type='contrail',
                    inputs=self.inputs))
            cn_fixturemx = self.useFixture(
                CNFixture(
                    connections=self.connections,
                    router_name=router_name,
                    router_ip=router_ip,
                    router_type='mx',
                    inputs=self.inputs))
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
                False,
                'record search is failed,please check '
                'syntax of the regular expression/NSlookup is failed')
        print m_obj.group(1)
        # Ipam DNS mentod is set to default, so DNS resolution to external
        # world needs to be resolved.
        self.assertTrue(
            vm_fix.ping_with_certainty(
                ip='juniper.net'),
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
                False,
                'record search is failed,please check syntax of '
                'the regular expression/NSlookup is failed')
        print m_obj1.group(1)
        return True

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
    def test_vdns_tree_scaling(self):
        ''' This test creates 16 levels of vdns servers vdns1,vdns2,vdns3...vdns16.
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
        '''
        ttl = 1000
        project_fixture = self.useFixture(
            ProjectFixture(
                vnc_lib_h=self.vnc_lib,
                project_name=self.inputs.project_name,
                connections=self.connections))
        proj_fixt = self.useFixture(
            ProjectTestFixtureGen(self.vnc_lib, project_name=self.inputs.project_name))
        dns_server_name_list = [
            'vdns1',
            'vdns2',
            'vdns3',
            'vdns4',
            'vdns5',
            'vdns6',
            'vdns7',
            'vdns8',
            'vdns9',
            'vdns10',
            'vdns11',
            'vdns12',
            'vdns13',
            'vdns14',
            'vdns15',
            'vdns16']
        domain_name_list = {
            'vdns1': 'juniper.net',
            'vdns2': 'two.juniper.net',
            'vdns3': 'three.two.juniper.net',
            'vdns4': 'four.three.two.juniper.net',
            'vdns5': 'five.four.three.two.juniper.net',
            'vdns6': 'six.five.four.three.two.juniper.net',
            'vdns7': 'seven.six.five.four.three.two.juniper.net',
            'vdns8': 'eight.seven.six.five.four.three.two.juniper.net',
            'vdns9': 'nine.eight.seven.six.five.four.three.two.juniper.net',
            'vdns10': 'ten.nine.eight.seven.six.five.four.three.two.juniper.net',
            'vdns11': '11.ten.nine.eight.seven.six.five.four.three.two.juniper.net',
            'vdns12': '12.11.ten.nine.eight.seven.six.five.four.three.two.juniper.net',
            'vdns13': '13.12.11.ten.nine.eight.seven.six.five.four.three.two.juniper.net',
            'vdns14': '14.13.12.11.ten.nine.eight.seven.six.five.four.three.two.juniper.net',
            'vdns15': '15.14.13.12.11.ten.nine.eight.seven.six.five.four.three.two.juniper.net',
            'vdns16': '16.15.14.13.12.11.ten.nine.eight.seven.six.five.four.three.two.juniper.net'}
        next_vdns_list = {
            'vdns1': 'vdns2',
            'vdns2': 'vdns3',
            'vdns3': 'vdns4',
            'vdns4': 'vdns5',
            'vdns5': 'vdns6',
            'vdns6': 'vdns7',
            'vdns7': 'vdns8',
            'vdns8': 'vdns9',
            'vdns9': 'vdns10',
            'vdns10': 'vdns11',
            'vdns11': 'vdns12',
            'vdns12': 'vdns13',
            'vdns13': 'vdns14',
            'vdns14': 'vdns15',
            'vdns15': 'vdns16',
            'vdns16': 'none'}
        rec_names = {
            'vdns1': 'test-rec1',
            'vdns2': 'test-rec2',
            'vdns3': 'test-rec3',
            'vdns4': 'test-rec4',
            'vdns5': 'test-rec5',
            'vdns6': 'test-rec6',
            'vdns7': 'test-rec7',
            'vdns8': 'test-rec8',
            'vdns9': 'test-rec9',
            'vdns10': 'test-rec10',
            'vdns11': 'test-rec11',
            'vdns12': 'test-rec12',
            'vdns13': 'test-rec13',
            'vdns14': 'test-rec14',
            'vdns15': 'test-rec15',
            'vdns16': 'test-rec16'}
        ipam_dns_list = {
            'vdns1': 'ipam1',
            'vdns2': 'ipam2',
            'vdns3': 'ipam3',
            'vdns4': 'ipam4',
            'vdns5': 'ipam5',
            'vdns6': 'ipam6',
            'vdns7': 'ipam7',
            'vdns8': 'ipam8',
            'vdns9': 'ipam9',
            'vdns10': 'ipam10',
            'vdns11': 'ipam11',
            'vdns12': 'ipam12',
            'vdns13': 'ipam13',
            'vdns14': 'ipam14',
            'vdns15': 'ipam15',
            'vdns16': 'ipam16'}
        vn_dns_list = {
            'vdns1': [
                'vn1',
                ['10.10.1.0/24']],
            'vdns2': [
                'vn2',
                ['10.10.2.0/24']],
            'vdns3': [
                'vn3',
                ['10.10.3.0/24']],
            'vdns4': [
                'vn4',
                ['10.10.4.0/24']],
            'vdns5': [
                'vn5',
                ['10.10.5.0/24']],
            'vdns6': [
                'vn6',
                ['10.10.6.0/24']],
            'vdns7': [
                'vn7',
                ['10.10.7.0/24']],
            'vdns8': [
                'vn8',
                ['10.10.8.0/24']],
            'vdns9': [
                'vn9',
                ['10.10.9.0/24']],
            'vdns10': [
                'vn10',
                ['10.10.10.0/24']],
            'vdns11': [
                'vn11',
                ['10.10.11.0/24']],
            'vdns12': [
                'vn12',
                ['10.10.12.0/24']],
            'vdns13': [
                'vn13',
                ['10.10.13.0/24']],
            'vdns14': [
                'vn14',
                ['10.10.14.0/24']],
            'vdns15': [
                'vn15',
                ['10.10.15.0/24']],
            'vdns16': [
                'vn16',
                ['10.10.16.0/24']]}
        vm_dns_list = {
            'vdns1': 'vm1',
            'vdns2': 'vm2',
            'vdns3': 'vm3',
            'vdns4': 'vm4',
            'vdns5': 'vm5',
            'vdns6': 'vm6',
            'vdns7': 'vm7',
            'vdns8': 'vm8',
            'vdns9': 'vm9',
            'vdns10': 'vm10',
            'vdns11': 'vm11',
            'vdns12': 'vm12',
            'vdns13': 'vm13',
            'vdns14': 'vm14',
            'vdns15': 'vm15',
            'vdns16': 'vm16'}
        vm_ip_dns_list = {}
        vdns_fix = {}
        vdns_data = {}
        vdns_rec = {}
        next_dns = None
        # DNS configuration
        for dns_name in dns_server_name_list:
            # VNDS1 is root, so Next VDNS entry is not required.
            if dns_name == 'vdns1':
                vdns_data[dns_name] = VirtualDnsType(
                    domain_name=domain_name_list[dns_name],
                    dynamic_records_from_client=True,
                    default_ttl_seconds=ttl,
                    record_order='random')
            else:
                # VDNS2,VDNS3...vdns16 needs to point next vdns server.
                vdns_data[dns_name] = VirtualDnsType(
                    domain_name=domain_name_list[dns_name],
                    dynamic_records_from_client=True,
                    default_ttl_seconds=ttl,
                    record_order='random',
                    next_virtual_DNS=next_dns.vdns_fq_name)
            vdns_fix[dns_name] = self.useFixture(
                VdnsFixture(
                    self.inputs,
                    self.connections,
                    vdns_name=dns_name,
                    dns_data=vdns_data[dns_name]))
            result, msg = vdns_fix[dns_name].verify_on_setup()
            self.assertTrue(result, msg)
            next_dns = vdns_fix[dns_name]

        #  Configure NS records for Next DNS server
        for dns_name in dns_server_name_list:
            if next_vdns_list[dns_name] != 'none':
                next_dns = next_vdns_list[dns_name]
                vdns_rec_data = VirtualDnsRecordType(
                    domain_name_list[next_dns],
                    'NS',
                    'IN',
                    vdns_fix[next_dns].vdns_fq_name,
                    ttl)
                vdns_rec[dns_name] = self.useFixture(
                    VdnsRecordFixture(
                        self.inputs,
                        self.connections,
                        rec_names[dns_name],
                        vdns_fix[dns_name].vdns_fix,
                        vdns_rec_data))
                result, msg = vdns_rec[dns_name].verify_on_setup()
                self.assertTrue(result, msg)
        vn_fixt = {}
        vm_fixture = {}
        ipam_fixt = {}

        for dns_name in dns_server_name_list:
            dns_server = IpamDnsAddressType(
                virtual_dns_server_name=vdns_fix[dns_name].vdns_fq_name)
            ipam_mgmt_obj = IpamType(
                ipam_dns_method='virtual-dns-server',
                ipam_dns_server=dns_server)
            # Associate IPAM with VDNS server Object
            ipam_fixt[dns_name] = self.useFixture(
                NetworkIpamTestFixtureGen(
                    self.vnc_lib,
                    virtual_DNS_refs=[
                        vdns_fix[dns_name].obj],
                    parent_fixt=proj_fixt,
                    network_ipam_name=ipam_dns_list[dns_name],
                    network_ipam_mgmt=ipam_mgmt_obj))
            # Launch VN
            vn_fixt[dns_name] = self.useFixture(
                VNFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_name=vn_dns_list[dns_name][0],
                    inputs=self.inputs,
                    subnets=vn_dns_list[dns_name][1],
                    ipam_fq_name=ipam_fixt[dns_name].getObj().get_fq_name()))
            # Launch VM
            vm_fixture[dns_name] = self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_obj=vn_fixt[dns_name].obj,
                    vm_name=vm_dns_list[dns_name]))
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
                    'VM Name is ---> %s\t cmd is---> %s',
                    vm_dns_list[dns],
                    cmd)
                vm_fixture[dns].run_cmd_on_vm(cmds=[cmd])
                result = vm_fixture[dns].return_output_cmd_dict[cmd]
                result = result.replace("\r", "")
                result = result.replace("\t", "")
                result = result.replace("\n", " ")
                m_obj = re.search(
                    r"Address:[0-9.]*#[0-9]*\s*.*Name:(.*\.juniper\.net)\s*Address:\s*([0-9.]*)",
                    result)
                if not m_obj:
                    self.assertTrue(
                        False,
                        'record search is failed,please check syntax of '
                        'the regular expression/NSlookup is failed')
                print ('vm_name is ---> %s \t ip-address is ---> %s' %
                       (m_obj.group(1), m_obj.group(2)))
                vm_name_to_verify = vm_dns_list[dns_name] + \
                    '.' + domain_name_list[dns_name]
                self.assertEqual(
                    m_obj.group(1),
                    vm_name_to_verify,
                    'VM name is not matching with nslookup command output')
                self.assertEqual(
                    m_obj.group(2),
                    vm_ip_dns_list[dns_name],
                    'IP Address is not matching with nslookup command output')
        return True

    @preposttest_wrapper
    def test_vdns_server_scaling(self):
        ''' This Test tests vdns server scaling '''
        ttl = 100
        # Number of VDNS servers
        vdns_scale = 1000
        # Number of records per server
        record_num = 1
        project_fixture = self.useFixture(
            ProjectFixture(
                vnc_lib_h=self.vnc_lib,
                project_name=self.inputs.project_name,
                connections=self.connections))
        proj_fixt = self.useFixture(
            ProjectTestFixtureGen(self.vnc_lib, project_name=self.inputs.project_name))
        vdns_fixt = {}
        vdns_verify = []
        i = 1
        j = 1
        for num in range(1, vdns_scale + 1):
            self.logger.info('Creating %s vdns server', num)
            domain_name = 'vdns' + str(num) + '.net'
            vdnsName = 'vdns' + str(num)
            dns_data = VirtualDnsType(
                domain_name=domain_name, dynamic_records_from_client=True,
                default_ttl_seconds=ttl, record_order='random')
            vdns_fixt[vdnsName] = self.useFixture(
                VdnsFixture(
                    self.inputs,
                    self.connections,
                    vdns_name=vdnsName,
                    dns_data=dns_data))
            for rec_num in range(1, record_num + 1):
                self.logger.info(
                    'Creating %s record for vdns server %s', rec_num, num)
                rec = 'test-rec-' + str(j) + '-' + str(i)
                rec_ip = '1.' + '1.' + str(j) + '.' + str(i)
                rec_name = 'rec' + str(j) + '-' + str(i)
                vdns_rec_data = VirtualDnsRecordType(
                    rec_name, 'A', 'IN', rec_ip, ttl)
                vdns_rec_fix = self.useFixture(
                    VdnsRecordFixture(
                        self.inputs,
                        self.connections,
                        rec,
                        vdns_fixt[vdnsName].vdns_fix,
                        vdns_rec_data))
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
            ipam_name = 'ipam-' + str(i)
            vn_name = 'vn-' + str(i)
            subnet = '10.10.' + str(i) + '.0/24'
            vm_name = 'vm' + str(i)
            vm_domain_name = vm_name + '.' + vdns + '.net'
            dns_server = IpamDnsAddressType(
                virtual_dns_server_name=vdns_fixt[vdns].vdns_fq_name)
            ipam_mgmt_obj = IpamType(
                ipam_dns_method='virtual-dns-server',
                ipam_dns_server=dns_server)
            # Associate IPAM with VDNS server Object
            ipam_fixt = self.useFixture(
                NetworkIpamTestFixtureGen(
                    self.vnc_lib,
                    virtual_DNS_refs=[
                        vdns_fixt[vdns].obj],
                    parent_fixt=proj_fixt,
                    network_ipam_name=ipam_name,
                    network_ipam_mgmt=ipam_mgmt_obj))
            # Launch VN
            vn_fixt = self.useFixture(
                VNFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_name=vn_name,
                    inputs=self.inputs,
                    subnets=[subnet],
                    ipam_fq_name=ipam_fixt.getObj().get_fq_name()))
            # Launch VM
            vm_fixture[vdns] = self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_obj=vn_fixt.obj,
                    vm_name=vm_name))
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
                r"Address:[0-9.]*#[0-9]*\s*.*Name:(.*\.vdns[0-9]*\.net)\s*Address:\s*([0-9.]*)",
                result)
            if not m_obj:
                self.assertTrue(
                    False,
                    'record search is failed,please check syntax of '
                    'the regular expression/NSlookup is failed')
            print ('vm_name is ---> %s \t ip-address is ---> %s' %
                   (m_obj.group(1), m_obj.group(2)))
            self.assertEqual(
                m_obj.group(1),
                vm_domain_name,
                'VM name is not matching with nslookup command output')
            self.assertEqual(
                m_obj.group(2),
                vm_ip,
                'IP Address is not matching with nslookup command output')
        return True
    #end test_vdns_server_scaling

    @preposttest_wrapper
    def test_vdns_with_same_zone(self):
        ''' Test vdns in same zone with multi projects/vdns-servers '''
        project_list = ['project1',
                        'project2',
                        'project3',
                        'project4',
                        'project5',
                        'project6']
        ipam_list = {'project1': 'ipam1',
                     'project2': 'ipam2',
                     'project3': 'ipam3',
                     'project4': 'ipam4',
                     'project5': 'ipam5',
                     'project6': 'ipam6'}
        vn_list = {'project1': 'vn1',
                   'project2': 'vn2',
                   'project3': 'vn3',
                   'project4': 'vn4',
                   'project5': 'vn5',
                   'project6': 'vn6'}
        vn_nets = {'project1': ['10.10.10.0/24'],
                   'project2': ['20.10.10.0/24'],
                   'project3': ['30.10.10.0/24'],
                   'project4': ['10.10.10.0/24'],
                   'project5': ['20.10.10.0/24'],
                   'project6': ['30.10.10.0/24']}
        vm_list = {'project1': 'vm1',
                   'project2': 'vm2',
                   'project3': 'vm3',
                   'project4': 'vm4',
                   'project5': 'vm5',
                   'project6': 'vm6'}
        proj_user = {'project1': 'user1',
                     'project2': 'user2',
                     'project3': 'user3',
                     'project4': 'user4',
                     'project5': 'user5',
                     'project6': 'user6'}
        proj_pass = {'project1': 'user1',
                     'project2': 'user2',
                     'project3': 'user3',
                     'project4': 'user4',
                     'project5': 'user5',
                     'project6': 'user6'}
        proj_vdns = {'project1': 'vdns1',
                     'project2': 'vdns2',
                     'project3': 'vdns3',
                     'project4': 'vdns4',
                     'project5': 'vdns5',
                     'project6': 'vdns6'}
        vdns_fixt1 = {}
        ipam_mgmt_obj = {}
        for project in project_list:
            dns_server_name = proj_vdns[project]
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
        admin_ip = self.inputs
        admin_con = self.connections
        for proj in project_list:
            # User creation
            user_fixture = self.useFixture(
                UserFixture(
                    connections=self.connections,
                    username=proj_user[proj],
                    password=proj_pass[proj]))
            # Project creation
            project_fixture = self.useFixture(
                ProjectFixture(
                    project_name=proj,
                    vnc_lib_h=self.vnc_lib,
                    username=proj_user[proj],
                    password=proj_pass[proj],
                    connections=admin_con))
            user_fixture.add_user_to_tenant(proj, proj_user[proj], 'admin')
            project_inputs = self.useFixture(
                ContrailTestInit(
                    self.ini_file,
                    stack_user=project_fixture.username,
                    stack_password=project_fixture.password,
                    project_fq_name=[
                        'default-domain',
                        proj]))
            project_connections = ContrailConnections(project_inputs)
            proj_fixt = self.useFixture(
                ProjectTestFixtureGen(self.vnc_lib, project_name=proj))
            self.logger.info(
                'Default SG to be edited for allow all on project: %s' % proj)
            project_fixture.set_sec_group_for_allow_all(proj, 'default')
            # Ipam creation
            ipam_fixt[proj] = self.useFixture(
                NetworkIpamTestFixtureGen(
                    self.vnc_lib,
                    virtual_DNS_refs=[
                        vdns_fixt1[proj].obj],
                    parent_fixt=proj_fixt,
                    network_ipam_name=ipam_list[proj],
                    network_ipam_mgmt=ipam_mgmt_obj[proj]))
            # VN Creation
            vn_fixt[proj] = self.useFixture(
                VNFixture(
                    project_name=proj,
                    connections=project_connections,
                    vn_name=vn_list[proj],
                    inputs=project_inputs,
                    subnets=vn_nets[proj],
                    ipam_fq_name=ipam_fixt[proj].getObj().get_fq_name()))
            # VM creation
            vm_fix[proj] = self.useFixture(
                VMFixture(
                    project_name=proj,
                    connections=project_connections,
                    vn_obj=vn_fixt[proj].obj,
                    vm_name=vm_list[proj]))
            vm_fix[proj].verify_vm_launched()
            vm_fix[proj].verify_on_setup()
            vm_fix[proj].wait_till_vm_is_up()
            msg = "Ping by using name %s is failed. Dns server \
                  should resolve VM name to IP" % (vm_list[proj])
            self.assertTrue(
                vm_fix[proj].ping_with_certainty(ip=vm_list[proj]), msg)
            vm_ip = vm_fix[proj].get_vm_ip_from_vm(
                vn_fq_name=vm_fix[proj].vn_fq_name)
            vm_rev_ip = vm_ip.split('.')
            vm_rev_ip = '.'.join(
                (vm_rev_ip[3], vm_rev_ip[2], vm_rev_ip[1], vm_rev_ip[0]))
            vm_rev_ip = vm_rev_ip + '.in-addr.arpa'
            rev_zone = vn_nets[proj][0].split('/')[0].split('.')
            rev_zone = '.'.join((rev_zone[0], rev_zone[1], rev_zone[2]))
            rev_zone = rev_zone + '.in-addr.arpa'
            # Frame the Expected DNS data for VM, one for 'A' record and
            # another 'PTR' record.
            rec_name = vm_list[proj] + "." + domain_name
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
            self.verify_vm_dns_data(vm_dns_exp_data)
            vm_dns_exp_data = []
        self.logger.info(
            'Restart supervisor-config & supervisor-control and test ping')
        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('supervisor-control', [bgp_ip])
        sleep(30)
        for cfgm_ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('supervisor-config', [cfgm_ip])
        sleep(60)
        for proj in project_list:
            msg = "Ping by using name %s is failed. Dns server \
                  should resolve VM name to IP" % (vm_list[proj])
            self.assertTrue(
                vm_fix[proj].ping_with_certainty(ip=vm_list[proj]), msg)
        return True
    # end test_vdns_with_same_zone

    @preposttest_wrapper
    def test_vdns_with_diff_zone(self):
        ''' Test vdns in different zones with multi projects '''
        project_list = [
            'project1',
            'project2',
            'project3',
            'project4',
            'project5',
            'project6']
        ipam_list = {
            'project1': 'ipam1',
            'project2': 'ipam2',
            'project3': 'ipam3',
            'project4': 'ipam4',
            'project5': 'ipam5',
            'project6': 'ipam6'}
        vn_list = {
            'project1': 'vn1',
            'project2': 'vn2',
            'project3': 'vn3',
            'project4': 'vn4',
            'project5': 'vn5',
            'project6': 'vn6'}
        vn_nets = {'project1': ['10.10.10.0/24'],
                   'project2': ['20.10.10.0/24'],
                   'project3': ['30.10.10.0/24'],
                   'project4': ['10.10.10.0/24'],
                   'project5': ['20.10.10.0/24'],
                   'project6': ['30.10.10.0/24'], }
        vm_list = {
            'project1': 'vm1',
            'project2': 'vm2',
            'project3': 'vm3',
            'project4': 'vm4',
            'project5': 'vm5',
            'project6': 'vm6'}
        proj_user = {
            'project1': 'user1',
            'project2': 'user2',
            'project3': 'user3',
            'project4': 'user4',
            'project5': 'user5',
            'project6': 'user6'}
        proj_pass = {
            'project1': 'user1',
            'project2': 'user2',
            'project3': 'user3',
            'project4': 'user4',
            'project5': 'user5',
            'project6': 'user6'}
        proj_vdns = {
            'project1': 'vdns1',
            'project2': 'vdns2',
            'project3': 'vdns3',
            'project4': 'vdns4',
            'project5': 'vdns5',
            'project6': 'vdns6'}
        vdns_fixt1 = {}
        ipam_mgmt_obj = {}
        for project in project_list:
            dns_server_name = proj_vdns[project]
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
        admin_ip = self.inputs
        admin_con = self.connections
        for proj in project_list:
            # User creation
            user_fixture = self.useFixture(
                UserFixture(
                    connections=self.connections,
                    username=proj_user[proj],
                    password=proj_pass[proj]))
            # Project creation
            project_fixture = self.useFixture(
                ProjectFixture(
                    project_name=proj,
                    vnc_lib_h=self.vnc_lib,
                    username=proj_user[proj],
                    password=proj_pass[proj],
                    connections=admin_con))
            user_fixture.add_user_to_tenant(proj, proj_user[proj], 'admin')
            project_inputs = self.useFixture(
                ContrailTestInit(
                    self.ini_file,
                    stack_user=project_fixture.username,
                    stack_password=project_fixture.password,
                    project_fq_name=[
                        'default-domain',
                        proj]))
            project_connections = ContrailConnections(project_inputs)
            proj_fixt = self.useFixture(
                ProjectTestFixtureGen(self.vnc_lib, project_name=proj))
            self.logger.info(
                'Default SG to be edited for allow all on project: %s' % proj)
            project_fixture.set_sec_group_for_allow_all(proj, 'default')
            # Ipam creation
            ipam_fixt[proj] = self.useFixture(
                NetworkIpamTestFixtureGen(
                    self.vnc_lib,
                    virtual_DNS_refs=[
                        vdns_fixt1[proj].obj],
                    parent_fixt=proj_fixt,
                    network_ipam_name=ipam_list[proj],
                    network_ipam_mgmt=ipam_mgmt_obj[proj]))
            # VN Creation
            vn_fixt[proj] = self.useFixture(
                VNFixture(
                    project_name=proj,
                    connections=project_connections,
                    vn_name=vn_list[proj],
                    inputs=project_inputs,
                    subnets=vn_nets[proj],
                    ipam_fq_name=ipam_fixt[proj].getObj().get_fq_name()))
            # VM creation
            vm_fix[proj] = self.useFixture(
                VMFixture(
                    project_name=proj,
                    connections=project_connections,
                    vn_obj=vn_fixt[proj].obj,
                    vm_name=vm_list[proj]))
            vm_fix[proj].verify_vm_launched()
            vm_fix[proj].verify_on_setup()
            vm_fix[proj].wait_till_vm_is_up()
            msg = "Ping by using name %s is failed. Dns server \
                  should resolve VM name to IP" % (vm_list[proj])
            self.assertTrue(
                vm_fix[proj].ping_with_certainty(ip=vm_list[proj]), msg)
            vm_ip = vm_fix[proj].get_vm_ip_from_vm(
                vn_fq_name=vm_fix[proj].vn_fq_name)
            vm_rev_ip = vm_ip.split('.')
            vm_rev_ip = '.'.join(
                (vm_rev_ip[3], vm_rev_ip[2], vm_rev_ip[1], vm_rev_ip[0]))
            vm_rev_ip = vm_rev_ip + '.in-addr.arpa'
            rev_zone = vn_nets[proj][0].split('/')[0].split('.')
            rev_zone = '.'.join((rev_zone[0], rev_zone[1], rev_zone[2]))
            rev_zone = rev_zone + '.in-addr.arpa'
            # Frame the Expected DNS data for VM, one for 'A' record and
            # another 'PTR' record.
            domain_name = '%s.net' % (proj)
            rec_name = vm_list[proj] + "." + domain_name
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
            self.verify_vm_dns_data(vm_dns_exp_data)
            vm_dns_exp_data = []
        self.logger.info(
            'Restart supervisor-config & supervisor-control and test ping')
        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('supervisor-control', [bgp_ip])
        sleep(30)
        for cfgm_ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('supervisor-config', [cfgm_ip])
        sleep(60)
        for proj in project_list:
            msg = "Ping by using name %s is failed. Dns server \
                  should resolve VM name to IP" % (vm_list[proj])
            self.assertTrue(
                vm_fix[proj].ping_with_certainty(ip=vm_list[proj]), msg)
        return True
    # end test_vdns_with_diff_zone

    def next_ip_in_list(self, iplist, item):
        item_index = iplist.index(item)
        next_item = None
        # if it not end of list, return next element in the list
        if item_index != (len(iplist) - 1):
            next_item = iplist[item_index + 1]
        # if the item is on end of list, the next element will be first element
        # in the list
        else:
            next_item = iplist[0]
        return next_item

    def verify_ns_lookup_data(self, vm_fix, cmd, expectd_data):
        self.logger.info("Inside verify_ns_lookup_data")
        self.logger.info(
            "cmd string is %s and  expected data %s for searching" %
            (cmd, expectd_data))
        vm_fix.run_cmd_on_vm(cmds=[cmd])
        result = vm_fix.return_output_cmd_dict[cmd]
        print ('\n result %s' % result)
        if (result.find(expectd_data) == -1):
            return False
        return True

    def verify_vm_dns_data(self, vm_dns_exp_data):
        self.logger.info("Inside verify_vm_dns_data")
        result = True
        dnsinspect_h = self.dnsagent_inspect[self.inputs.bgp_ips[0]]
        dns_data = dnsinspect_h.get_dnsa_config()
        vm_dns_act_data = []
        msg = ''

        # Traverse over expected record data
        found_rec = False
        for expected in vm_dns_exp_data:
            # Get te actual record data from introspect
            for act in dns_data:
                for rec in act['records']:
                    if (rec['rec_name'] in expected['rec_name']) and (
                            rec['rec_data'] in expected['rec_data']):
                        vm_dns_act_data = rec
                        found_rec = True
                        break
                if found_rec:
                    break
            if not vm_dns_act_data:
                self.logger.info("DNS record match not found in dns agent")
                return False
            found_rec = False
            # Compare the DNS entries populated dynamically on VM Creation.
            self.logger.info(
                "actual record data %s ,\n expected record data %s" %
                (vm_dns_act_data, expected))
            if(vm_dns_act_data['rec_name'] not in expected['rec_name']):
                result = result and False
            if (vm_dns_act_data['rec_data'] not in expected['rec_data']):
                msg = 'DNS record data info is not matching\n'
                result = result and False
            if(vm_dns_act_data['rec_type'] != expected['rec_type']):
                msg = msg + 'DNS record_type info is not matching\n'
                result = result and False
            if(vm_dns_act_data['rec_ttl'] != expected['rec_ttl']):
                msg = msg + 'DNS record ttl info is not matching\n'
                result = result and False
            if(vm_dns_act_data['rec_class'] != expected['rec_class']):
                msg = msg + 'DNS record calss info is not matching\n'
                result = result and False
            vm_dns_act_data = []
            self.assertTrue(result, msg)
        self.logger.info("Out of verify_vm_dns_data")
        return True
    # end verify_vm_dns_data
if __name__ == '__main__':
    unittest.main()
# end of TestVdnsFixture
