import test_v1
from common.connections import ContrailConnections
from common import isolated_creds
from random import randint

import os
import unittest
import fixtures
import testtools
import traceback
import signal
import traffic_tests
from common.contrail_test_init import ContrailTestInit
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from common.connections import ContrailConnections
from floating_ip import *
from control_node import *
from policy_test import *
from multiple_vn_vm_test import *
from vdns_fixture import *
from contrail_fixtures import *
from vnc_api import vnc_api
from vnc_api.gen.resource_test import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import retry

class BasevDNSTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BasevDNSTest, cls).setUpClass()
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.orch = cls.connections.orch
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        cls.dnsagent_inspect = cls.connections.dnsagent_inspect
        cls.api_s_inspect = cls.connections.api_server_inspect
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BasevDNSTest, cls).tearDownClass()
    #end tearDownClass 

    def verify_dns_record_order(self, record_order, test_type='test_record_order', record_num=10):
        ''' This test tests DNS record order.
            Round-Robin/Fixed/Random
        '''
        random_number = randint(2500,5000)
        vn1_ip = '10.10.10.1/24'
        vn_name = get_random_name('vn')
        dns_server_name = get_random_name('vdns1')
        domain_name = 'juniper.net'
        ttl = 100
        ipam_name = get_random_name('ipam1')
        project_fixture = self.useFixture(ProjectFixture(
            vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
        project_connections = project_fixture.get_project_connections()
        dns_data = VirtualDnsType(
            domain_name=domain_name, dynamic_records_from_client=True,
            default_ttl_seconds=ttl, record_order=record_order)
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
        ipam_fixt1 = self.useFixture(IPAMFixture(ipam_name, vdns_obj=
                                     vdns_fixt1.obj, connections=project_connections, ipamtype=ipam_mgmt_obj))
        # Launch VN with IPAM
        vn_fixt = self.useFixture(
            VNFixture(
                self.connections, self.inputs, vn_name=vn_name,
                subnets=[vn1_ip], ipam_fq_name= ipam_fixt1.fq_name, option='contrail'))
        vn_quantum_obj = self.orch.get_vn_obj_if_present(
            vn_name=vn_name, project_id=project_fixture.uuid)
        vm_fixture = self.useFixture(
            VMFixture(project_name=self.inputs.project_name,
                      connections=self.connections, vn_obj=vn_quantum_obj, vm_name=get_random_name('vm1-test')))
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
                rec = 'test-rec-' + str(j) + '-' + str(i) + str(random_number)
                self.logger.info('Creating record %s', rec)
                recname = 'rec' + str(j) + '-' + str(i) + str(random_number)
                rec_ip = str(l) + '.' + str(k) + '.' + str(j) + '.' + str(i)
                vdns_rec_data = VirtualDnsRecordType(
                    recname, 'A', 'IN', rec_ip, ttl)
                vdns_rec_fix = self.useFixture(VdnsRecordFixture(
                    self.inputs, self.connections, rec, vdns_fixt1.get_fq_name(), vdns_rec_data))
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
            self.logger.debug('%%%%NSLook up verification%%%%')
            import re
            for rec in verify_rec_name_list:
                cmd = 'nslookup ' + rec
                vm_fixture.run_cmd_on_vm(cmds=[cmd])
                result = vm_fixture.return_output_cmd_dict[cmd]
                result = result.replace("\r", "")
                result = result.replace("\t", "")
                result = result.replace("\n", " ")
                m_obj = re.search(
                    r"Address:[0-9.]*#[0-9]*\s*.*Name:(.*\.juniper\.net)\s*Address:\s*([0-9.]*)", result)
                if not m_obj:
                    #import pdb; pdb.set_trace()
                    self.assertTrue(
                        False, 'record search is failed,please check syntax of the regular expression/NSlookup is failed')
                print ('vm_name is ---> %s \t ip-address is ---> %s' %
                       (m_obj.group(1), m_obj.group(2)))
        else:
            for num in range(1, record_num):
                rec = 'test-rec-' + str(j) + '-' + str(i) + str(random_number)
                rec_ip = '1.' + '1.' + str(j) + '.' + str(i)
                vdns_rec_data = VirtualDnsRecordType(
                    'test1', 'A', 'IN', rec_ip, ttl)
                vdns_rec_fix = self.useFixture(VdnsRecordFixture(
                    self.inputs, self.connections, rec, vdns_fixt1.get_fq_name(), vdns_rec_data))
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
                r"Address:[0-9.]*#[0-9]*\s*Name:test1.juniper.net\s*(Address:\s*[0-9.]*)", result)
            if not m_obj:
                self.assertTrue(
                    False, 'record search is failed,please check syntax of regular expression')
            print m_obj.group(1)
            dns_record = m_obj.group(1).split(':')
            dns_record_ip = dns_record[1].lstrip()
            next_ip = self.next_ip_in_list(rec_ip_list, dns_record_ip)
            round_robin_success_count = 0
            for rec in rec_ip_list:
                vm_fixture.run_cmd_on_vm(cmds=[cmd])
                result = vm_fixture.return_output_cmd_dict[cmd]
                result = result.replace("\r", "")
                result = result.replace("\t", "")
                result = result.replace("\n", " ")
                m_obj = re.search(
                    r"Address:[0-9.]*#[0-9]*\s*Name:test1.juniper.net\s*(Address:\s*[0-9.]*)", result)
                print m_obj.group(1)
                dns_record = m_obj.group(1).split(':')
                dns_record_ip1 = dns_record[1].lstrip()
                if record_order == 'round-robin':
                    if next_ip == dns_record_ip1:
                        round_robin_success_count += 1
                    else:
                        round_robin_success_count = 0
                    if round_robin_success_count == 3:
                        self.logger.debug("Consecutive 3 outputs are in round robin fashion")
                        self.logger.debug("This should be enough to confirm round robin behavior")
                        break
                    if rec == rec_ip_list[-1] and round_robin_success_count < 3:
                        self.logger.error("\n VDNS records are not sent in \
                            round-robin order")
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
                        print "\n VDNS records are not sent fixed in fixed order"
                        self.assertTrue(
                            False, 'VDNS records are not sent fixed in fixed order')
        return True
    # end test_dns_record_order

    # This Test test vdns functionality with control node restart
    def vdns_with_cn_dns_agent_restart(self, restart_process):
        '''
         This test test the functionality of controlnode/dns/agent restart with vdns feature.
        '''
        if restart_process == 'ControlNodeRestart':
            if len(set(self.inputs.bgp_ips)) < 2:
                raise self.skipTest(
                    "Skipping Test. At least 2 control nodes required to run the control node switchover test")
        vn1_ip = '10.10.10.1/24'
        vm_list = [get_random_name('vm1-test'), get_random_name('vm2-test')]
        vn_name = get_random_name('vn1')
        dns_server_name = get_random_name('vdns1')
        domain_name = 'juniper.net'
        ttl = 100
        ipam_name = get_random_name('ipam1')
        rev_zone = vn1_ip.split('.')
        rev_zone = '.'.join((rev_zone[0], rev_zone[1], rev_zone[2]))
        rev_zone = rev_zone + '.in-addr.arpa'
        project_fixture = self.useFixture(ProjectFixture(
            vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
        project_connections = project_fixture.get_project_connections()
        dns_data = VirtualDnsType(
            domain_name=domain_name, dynamic_records_from_client=True,
            default_ttl_seconds=ttl, record_order='random')
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
        ipam_fixt1 = self.useFixture(IPAMFixture(ipam_name, vdns_obj=
                                     vdns_fixt1.obj, connections=project_connections, ipamtype=ipam_mgmt_obj))
        # Launch VN with IPAM
        vn_fixt = self.useFixture(
            VNFixture(
                self.connections, self.inputs, vn_name=vn_name,
                subnets=[vn1_ip], ipam_fq_name= ipam_fixt1.fq_name, option='contrail'))
        vm_fixture = {}
        vm_dns_exp_data = {}
        # Launch  VM with VN Created above. This test verifies on launch of VM agent should updated DNS 'A' and 'PTR' records
        # The following code will verify the same. Also, we should be able ping
        # with VM name.
        for vm_name in vm_list:
            vn_quantum_obj = self.orch.get_vn_obj_if_present(
                vn_name=vn_name, project_id=project_fixture.uuid)
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
            # Frame the Expected DNS data for VM, one for 'A' record and
            # another 'PTR' record.
            agent_inspect_h = self.agent_inspect[vm_fixture[vm_name].vm_node_ip]
            assigned_dns_ips = agent_inspect_h.get_vna_discovered_dns_server()
            rec_name = vm_name + "." + domain_name
            vm_dns_exp_data[vm_name] = [{'rec_data': vm_ip, 'rec_type': 'A', 'rec_class': 'IN', 'rec_ttl': str(
                ttl), 'rec_name': rec_name, 'installed': 'yes', 'zone': domain_name}, {'rec_data': rec_name, 'rec_type': 'PTR', 'rec_class': 'IN', 'rec_ttl': str(ttl), 'rec_name': vm_rev_ip, 'installed': 'yes', 'zone': rev_zone}]
            self.verify_vm_dns_data(vm_dns_exp_data[vm_name], assigned_dns_ips[0])
        # ping between two vms which are in same subnets by using name.
        self.assertTrue(vm_fixture[vm_list[0]]
                        .ping_with_certainty(ip=vm_list[1]))
        active_controller = vm_fixture[vm_list[0]].get_active_controller()
        self.logger.debug('Active control node from the Agent %s is %s' %
                         (vm_fixture[vm_list[0]].vm_node_ip, active_controller))
        # Control node restart/switchover.
        if restart_process == 'ControlNodeRestart':
            # restart the Active control node
            self.logger.info('Restarting active control node')
            self.inputs.restart_service(
                'contrail-control', [active_controller])
            sleep(5)
            # Check the control node shifted to other control node
            new_active_controller = vm_fixture[
                vm_list[0]].get_active_controller()
            self.logger.info('Active control node from the Agent %s is %s' %
                             (vm_fixture[vm_list[0]].vm_node_ip, new_active_controller))
            if new_active_controller == active_controller:
                self.logger.error(
                    'Control node switchover fail. Old Active controlnode was %s and new active control node is %s' %
                    (active_controller, new_active_controller))
                return False
            self.inputs.restart_service(
                'contrail-control', [new_active_controller])
        if restart_process == 'DnsRestart':
            # restart the dns process in the active control node
            self.logger.info(
                'Restarting the dns process in the active control node')
            self.inputs.restart_service('contrail-dns', [active_controller])
        if restart_process == 'NamedRestart':
            # restart the named process in the active control node
            self.logger.info(
                'Restarting the named process in the active control node')
            self.inputs.restart_service('contrail-named', [active_controller])
        # restart the agent process in the compute node
        if restart_process == 'AgentRestart':
            self.logger.info('Restarting the agent process on compute nodes')
            for compute_ip in self.inputs.compute_ips:
                self.inputs.restart_service('contrail-vrouter', [compute_ip])
        if restart_process == 'scp':
            self.logger.debug('scp using name of vm')
            vm_fixture[vm_list[0]].put_pub_key_to_vm()
            vm_fixture[vm_list[1]].put_pub_key_to_vm()
            size = '1000'
            file = 'testfile'
            y = 'ls -lrt %s' % file
            cmd_to_check_file = [y]
            cmd_to_sync = ['sync']
            create_result = True
            transfer_result = True

            self.logger.debug("-" * 80)
            self.logger.debug("FILE SIZE = %sB" % size)
            self.logger.debug("-" * 80)
            self.logger.debug('Creating a file of the specified size on %s' %
                             vm_fixture[vm_list[0]].vm_name)

            self.logger.debug('Transferring the file from %s to %s using scp' %
                             (vm_fixture[vm_list[0]].vm_name, vm_fixture[vm_list[1]].vm_name))
            vm_fixture[
                vm_list[0]].check_file_transfer(dest_vm_fixture=vm_fixture[vm_list[1]], mode='scp', size=size)

            self.logger.debug('Checking if the file exists on %s' %
                             vm_fixture[vm_list[1]].vm_name)
            vm_fixture[vm_list[1]].run_cmd_on_vm(cmds=cmd_to_check_file)
            output = vm_fixture[vm_list[1]].return_output_cmd_dict[y]
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
            msg = "Ping by using name %s is failed after controlnode/dns/agent/named process restart. Dns server should resolve VM name to IP" % (
                vm_name)
            self.assertTrue(vm_fixture[vm_name]
                            .ping_with_certainty(ip=vm_name), msg)
            agent_inspect_h = self.agent_inspect[vm_fixture[vm_name].vm_node_ip]
            assigned_dns_ips = agent_inspect_h.get_vna_discovered_dns_server()
            self.verify_vm_dns_data(vm_dns_exp_data[vm_name], assigned_dns_ips[0])
        return True
    # end test_vdns_controlnode_switchover

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

    @retry(delay=1, tries=4)
    def verify_ns_lookup_data(self, vm_fix, cmd, expectd_data,
                              expected_result = True):
        self.logger.debug("Inside verify_ns_lookup_data")
        self.logger.debug(
            "cmd string is %s and  expected data %s for searching" %
            (cmd, expectd_data))
        vm_fix.run_cmd_on_vm(cmds=[cmd])
        result = vm_fix.return_output_cmd_dict[cmd]
        try:
            if (result.find(expectd_data) == -1):
                actual_result = False
            else:
                actual_result = True
        except AttributeError, e:
            self.logger.error('Unable to get any result of nslookup')
            self.logger.exception(e)
            actual_result = False
        if actual_result == expected_result:
            return True
        else:
            return False

    def verify_vm_dns_data(self, vm_dns_exp_data, dns_server_ip):
        result = True
        dns_data_list = []
        for bgp_ip in self.inputs.bgp_ips:
            dnsinspect_h = self.dnsagent_inspect[dns_server_ip]
            dns_data_list.append(dnsinspect_h.get_dnsa_config())

        # Traverse over expected record data
        for expected in vm_dns_exp_data:
            # Get te actual record data from introspect
            found_rec = False
            vm_dns_act_data = []
            msg = ''
            for dns_data in dns_data_list:
                for act in dns_data:
                    for rec in act['records'] or []:
                        if rec['rec_name'] in expected['rec_name']:
                            vm_dns_act_data = rec
                            found_rec = True
                            break
                    if found_rec:
                        break
                if found_rec:
                    break
            if not vm_dns_act_data:
                self.logger.info("DNS record match not found in dns agent %s"%bgp_ip)
                return False
            # Compare the DNS entries populated dynamically on VM Creation.
            self.logger.debug(
                "Actual record data %s ,\n Expected record data %s" %
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
            self.assertTrue(result, msg)
        return True
    # end verify_vm_dns_data
