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
from ipam_test import IPAMFixture
from vn_test import VNFixture
import test

class TestvDNSBasic0(BasevDNSTest):

    @classmethod
    def setUpClass(cls):
        super(TestvDNSBasic0, cls).setUpClass()

    def runTest(self):
        pass
    #end runTest 

    # This Test test vdns functionality-- On VM launch agent should dynamically update dns records to dns agent.
    # This test verifies the same functionality and should able to refer VM by
    # a name.
    @skip_because(hypervisor='docker',msg='Bug 1458794:DNS configuration issue in docker container')
    @test.attr(type=['sanity', 'ci_sanity', 'vcenter', 'suite1'])
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
        vm1_name = get_random_name('vm1-test')
        vm2_name = get_random_name('vm2-test')
        vm_list = [vm1_name, vm2_name]
        vn_name = get_random_name('vn1-vdns')
        dns_server_name = get_random_name('vdns1')
        domain_name = 'juniper.net'
        cname_rec = 'vm1-test-alias'
        ttl = 100
        ipam_name = 'ipam1'
        rev_zone = vn1_ip.split('.')
        rev_zone = '.'.join((rev_zone[0], rev_zone[1], rev_zone[2]))
        rev_zone = rev_zone + '.in-addr.arpa'
        proj_fixt = self.useFixture(ProjectFixture(
            project_name=self.inputs.project_name, connections=self.connections))
        proj_connections = proj_fixt.get_project_connections()
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
        ipam_fixt1 = self.useFixture(IPAMFixture(ipam_name, vdns_obj= vdns_fixt1.obj, connections=proj_connections, ipamtype=ipam_mgmt_obj))
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
            assert vm_fixture[vm_name].verify_vm_launched(), ('VM %s does not'
                'seem to have launched correctly' % (vm_name))
            assert vm_fixture[vm_name].verify_on_setup(), ('VM %s verification'
                'failed' % (vm_name))
            assert vm_fixture[vm_name].wait_till_vm_is_up(), ('VM %s'
                ' failed to come up' % (vm_name))
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
            agent_inspect_h = self.agent_inspect[vm_fixture[vm_name].vm_node_ip]
            assigned_dns_ips = agent_inspect_h.get_vna_discovered_dns_server()
            vm_dns_exp_data = [{'rec_data': vm_ip, 'rec_type': 'A', 'rec_class': 'IN', 'rec_ttl': str(
                ttl), 'rec_name': rec_name, 'installed': 'yes', 'zone': domain_name}, {'rec_data': rec_name, 'rec_type': 'PTR', 'rec_class': 'IN', 'rec_ttl': str(ttl), 'rec_name': vm_rev_ip, 'installed': 'yes', 'zone': rev_zone}]
            self.verify_vm_dns_data(vm_dns_exp_data, assigned_dns_ips[0])
            vm_dns_exp_data = []
        # ping between two vms which are in same subnets by using name.
        self.assertTrue(vm_fixture[vm1_name]
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
            self.logger.debug(msg)
            self.logger.info(
                "Deletion of the vdns entry failed with back ref of ipam as expected")
        # Add VDNS record 'CNAME' and add it to VDNS and ping with alias for
        # vm1-test
        self.logger.info(
            'Add CNAME VDNS record for %s and verify we able to ping by alias name' % vm1_name)
        vdns_rec_data = VirtualDnsRecordType(
            cname_rec, 'CNAME', 'IN', vm1_name, ttl)
        vdns_rec_fix = self.useFixture(VdnsRecordFixture(
            self.inputs, self.connections, 'test-rec', vdns_fixt1.get_fq_name(), vdns_rec_data))
        result, msg = vdns_rec_fix.verify_on_setup()
        self.assertTrue(result, msg)
        self.assertTrue(vm_fixture[vm1_name]
                        .ping_with_certainty(ip=cname_rec))
        return True
    # end test_vdns_ping_same_vn
