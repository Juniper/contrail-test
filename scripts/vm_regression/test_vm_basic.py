from __future__ import absolute_import, unicode_literals
from .base import BaseVnVmTest
from builtins import str
from builtins import range
import traffic_tests
from vn_test import *
from vm_test import *
from floating_ip import *
from policy_test import *
from user_test import UserFixture
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from common import isolated_creds
import inspect
import time
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from tcutils.util import get_subnet_broadcast
from tcutils.util import skip_because
import test

class TestBasicVMVN(BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicVMVN, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBasicVMVN, cls).tearDownClass()

    def runTest(self):
        pass
    #end runTes

    @skip_because(orchestrator = 'vcenter', hypervisor='docker',msg='Bug 1455944:VM image with cloud-init package needed')
    # Removing ci_sanity tag till microservice provisioning supports the same
    @test.attr(type=['cb_sanity', 'sanity', 'suite1'])
    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter')
    def test_metadata_service(self):
        '''
        Description: Test to validate metadata service on VM creation.

               1.Verify from global-vrouter-config if metadata configures or not - fails otherwise
               2.Create a shell script which writes  'hello world ' in a file in /tmp and save the script on the nova api node
               3.Create a vm with userdata pointing to that script - script should get executed during vm boot up
               4.Go to the vm and verify if the file with 'hello world ' written saved in /tmp of the vm - fails otherwise
            Maintainer: sandipd@juniper.net
        '''
        result = False
        mtries = 3
        gvrouter_cfg_obj = self.api_s_inspect.get_global_vrouter_config()
        ln_svc = gvrouter_cfg_obj.get_link_local_service()
        assert ln_svc, "Metadata NOT configured in global_vrouter_config"

        text = """#!/bin/sh
echo "Hello World.  The time is now $(date -R)!" | tee /tmp/output.txt
               """
        with open("/tmp/metadata_script.txt", "w") as f:
            f.write(text)

        vn_fixture = self.create_vn(af='v4')
        vm1_fixture = self.create_vm(vn_fixture=vn_fixture,
                                     image_name='cirros',
                                     userdata='/tmp/metadata_script.txt')
        assert vm1_fixture.wait_till_vm_is_up()

        cmd = 'cat /tmp/output.txt'
        for i in range(mtries):
            ret = vm1_fixture.run_cmd_on_vm(cmds=[cmd])
            self.logger.debug("ret : %s" % (ret))
            output = ret[cmd]
            if 'Hello World' in output:
                self.logger.info("metadata_script.txt got executed in the vm")
                return True
            else:
                self.logger.warn("metadata_script.txt did not get executed in the vm")
                if i+1 < mtries:
                    time.sleep(2)
        assert result

    @test.attr(type=['suite1'])
    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter', address_family = 'v6')
    def test_ipam_add_delete(self):
        '''
         Description: Test to validate IPAM creation, association of a VN and creating VMs in the VN. Ping b/w the VMs should be successful.
         Test steps:
                1. Create a IPAM.
                2. Use this IPAM to create a VN.
                3. Launch 2 VMs in the VN.
         Pass criteria: Ping between the VMs should PASS.
         Maintainer : ganeshahv@juniper.net
        '''
        ipam_obj = self.useFixture(
            IPAMFixture(connections=self.connections, name=get_random_name('my-ipam')))
        assert ipam_obj.verify_on_setup()
        vn_fixture = self.create_vn(ipam_fq_name=ipam_obj.fq_name)
        assert vn_fixture.verify_on_setup()

        vm1_fixture = self.create_vm(vn_fixture= vn_fixture, vm_name=get_random_name('vm1'))
        vm2_fixture = self.create_vm(vn_fixture= vn_fixture, vm_name=get_random_name('vm2'))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_to_vn(dst_vm_fixture=vm2_fixture,
                                      vn_fq_name=vn_fixture.get_vn_fq_name())

        return True


    @test.attr(type=['sanity', 'suite1', 'ci_sanity', 'vcenter_compute', 'ci_contrail_go_kolla_ocata_sanity'])
    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter',address_family = 'v6',
        hypervisor='docker',msg='Bug 1461423:Need privileged access')
    def test_ping_within_vn_two_vms_two_different_subnets(self):
        '''
        Description:  Validate Ping between 2 VMs in the same VN, 2 VMs in different VN
        subnets.
        Test steps:
                1. Create 1 IPAM's.
                2. Create 1 VN with 2 subnets and launch 2 VMs in them.
                3. Ping between the VMs in the same VN should go thru fine.
                4. Ping to the subnet broadcast and all-broadcast address.
        Pass criteria: VM in the same subnet will respond to both the pings, while the VM in a different VN should respond only to the
                        all-broadcast address.
        Maintainer : ganeshahv@juniper.net
        '''
        subnet1 = '31.1.1.0/29'
        subnet2 = '31.1.2.0/29'
        fixed_ip1 = '31.1.1.4'
        fixed_ip2 = '31.1.2.4'
        vn1_subnets = [subnet1, subnet2]

        ipam_obj = self.create_ipam()
        vn1_fixture = self.create_vn(vn_subnets=vn1_subnets,
                                     ipam_fq_name=ipam_obj.fq_name)

        subnet_objects = vn1_fixture.get_subnets()
        ports = {}

        for subnet in subnet_objects:
            if subnet['cidr'] == subnet1:
                ports['subnet1'] = vn1_fixture.create_port(vn1_fixture.vn_id,
                    subnet_id=subnet['id'], ip_address=fixed_ip1)
            elif subnet['cidr'] == subnet2:
                ports['subnet2'] = vn1_fixture.create_port(vn1_fixture.vn_id,
                    subnet_id=subnet['id'],ip_address=fixed_ip2)

        vm1 = self.create_vm(image_name='cirros', vn_fixture=vn1_fixture,
                             port_ids=[ports['subnet1']['id']])
        vm2 = self.create_vm(image_name='cirros', vn_fixture=vn1_fixture,
                             port_ids=[ports['subnet2']['id']])
        vm3 = self.create_vm(image_name='cirros', vn_fixture=vn1_fixture)
        assert ipam_obj.verify_on_setup()
        assert vn1_fixture.verify_on_setup()
        assert vm1.wait_till_vm_is_up()
        assert vm2.wait_till_vm_is_up()
        assert vm3.wait_till_vm_is_up()
        assert vm1.ping_to_ip(vm2.vm_ip)
        assert vm2.ping_to_ip(vm1.vm_ip)
        # Geting the VM ips
        vm1_ip = vm1.vm_ip
        vm2_ip = vm2.vm_ip
        vm3_ip = vm3.vm_ip
        ip_list = [vm1_ip, vm2_ip, vm3_ip]

        ip_broadcast = get_subnet_broadcast('%s/%s'%(vm1_ip, '29'))
        list_of_ip_to_ping = [ip_broadcast, '224.0.0.1', '255.255.255.255']
        cmd_list_to_pass_vm = [
            'echo 0 > /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts']

        vm1.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm2.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm3.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)

        for dst_ip in list_of_ip_to_ping:
            ping_output = vm1.ping_to_ip(
                dst_ip, return_output=True)
            expected_result = ' 0% packet loss'
            assert (expected_result in ping_output)
            string_count_dict = get_string_match_count(ip_list, ping_output)
            if (dst_ip == ip_broadcast):
                assert (string_count_dict[vm2_ip] == 0)
                assert (string_count_dict[vm3_ip] > 0)
            if (dst_ip == '224.0.0.1' or dst_ip == '255.255.255.255'):
                assert (string_count_dict[vm2_ip] > 0)
                assert (string_count_dict[vm3_ip] > 0)
    #test_ping_within_vn_two_vms_two_different_subnets

    @test.attr(type=[ 'suite1'])
    @preposttest_wrapper
    def test_vn_add_delete(self):
        '''
        Description: Test to validate VN creation and deletion.
        Test steps:
               1. Create a VN.
        Pass criteria: VN creation and deletion should go thru fine.
        Maintainer : ganeshahv@juniper.net
        '''
        vn_obj = self.create_vn()
        assert vn_obj.verify_on_setup()
        return True
    #end test_vn_add_delete

    @test.attr(type=[ 'suite1'])
    @preposttest_wrapper
    def test_vm_add_delete(self):
        '''
        Description:  Test to validate VM creation and deletion.
        Test steps:
                1. Create VM in a VN.
        Pass criteria: Creation and deletion of the VM should go thru fine.
        Maintainer : ganeshahv@juniper.net
        '''
        vn_fixture = self.create_vn()
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.create_vm(vn_fixture=vn_fixture,
                                     vm_name=get_random_name('vm_add_delete'))
        assert vm1_fixture.verify_on_setup()
        return True
    # end test_vm_add_delete

    @test.attr(type=['suite1', 'upgrade','vrouter_gw', 'vcenter_compute', 'ci_contrail_go_kolla_ocata_sanity'])
    @preposttest_wrapper
    def test_ping_within_vn(self):
        '''
        Description:  Validate Ping between 3 VMs in the same VN.
        Test steps:
               1. Create a VN and launch 3 VMs in it.
        Pass criteria: Ping between the VMs should go thru fine.
        Maintainer : ganeshahv@juniper.net
        '''
        vn1_name = get_random_name('vn30')
        vn1_vm1_name = get_random_name('vm1')
        vn1_vm2_name = get_random_name('vm2')
        vn1_vm3_name = get_random_name('vm3')
        vn1_fixture = self.create_vn(vn_name=vn1_name,orch=self.orchestrator)
        vn1_fixture.read()
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture,
            image_name='cirros-traffic', vm_name=vn1_vm1_name, orch=self.orchestrator)
        vm2_fixture = self.create_vm(vn_ids=[vn1_fixture.uuid],
            image_name='cirros-traffic', vm_name=vn1_vm2_name)
        vm3_fixture = self.create_vm(vn_ids=[vn1_fixture.uuid],
            image_name='cirros-traffic', vm_name=vn1_vm3_name)
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        assert vm3_fixture.wait_till_vm_is_up()

        def validate():
            assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
                "Ping from %s to %s failed" % (vn1_vm1_name, vn1_vm2_name)
            assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
                "Ping from %s to %s failed" % (vn1_vm2_name, vn1_vm1_name)
            assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm3_fixture),\
                "Ping from %s to %s failed" % (vn1_vm1_name, vn1_vm3_name)
            assert vm3_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
                "Ping from %s to %s failed" % (vn1_vm3_name, vn1_vm1_name)
        validate()
        self.validate_post_upgrade = validate
        return True
    # end test_ping_within_vn

    @test.attr(type=['cb_sanity', 'sanity', 'ci_sanity', 'vcenter',
                     'suite1', 'vcenter_compute', 'ci_contrail_go_kolla_ocata_sanity'])
    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter',address_family = 'v6')
    def test_generic_link_local_service(self):
        '''
        Description: Test to validate generic linklocal service - running nova list from vm.
            1.Create generic link local service to be able to wget to jenkins
            2.Create a vm
            3.Try wget to jenkins - passes if successful else fails

        Maintainer: sandipd@juniper.net
        '''

        result = True
        vn_name = get_random_name('vn2_metadata')
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        vn_obj = vn_fixture.obj
        vm1_fixture = self.create_vm(vn_ids=[vn_fixture.uuid], image_name='cirros')

        lls_service_name = 'introspect'
        introspect_port = '8083'
        service_ip = self.inputs.bgp_control_ips[0]
        fabric_service_name = self.inputs.bgp_names[0]
        host_new_name = fabric_service_name + '-test'
        self.orch.vnc_h.add_link_local_service(lls_service_name,
             '169.254.1.2', '8083', introspect_port,
             ipfabric_service_dns_name=host_new_name,
             ipfabric_service_ip=service_ip)
        self.addCleanup(self.orch.vnc_h.delete_link_local_service,
                        lls_service_name)
        compute_user = self.inputs.host_data[vm1_fixture.vm_node_ip]['username']
        compute_password = self.inputs.host_data[vm1_fixture.vm_node_ip]['password']

        update_hosts_cmd = 'echo "%s %s" >> /etc/hosts' % (service_ip,
            host_new_name)
        self.inputs.run_cmd_on_server(vm1_fixture.vm_node_ip,
                                      update_hosts_cmd,
                                      compute_user,
                                      compute_password,
                                      container='agent')
        # Remove the hosts entry which was added earlier
        update_hosts_cmd = "sed -i '$ d' /etc/hosts"
        self.addCleanup(self.inputs.run_cmd_on_server,
                        vm1_fixture.vm_node_ip,
                        update_hosts_cmd,
                        compute_user,
                        compute_password,
                        container='agent')

        assert vm1_fixture.wait_till_vm_is_up()
        cmd = 'wget http://169.254.1.2:8083 --spider && echo "Successful"'

        ret = None
        for i in range(3):
            try:
                self.logger.info("Retry %s" % (i))
                ret = vm1_fixture.run_cmd_on_vm(cmds=[cmd])
                if not ret[cmd]:
                    raise Exception('wget of http://169.254.1.2:8083 returned None')
            except Exception as e:
                time.sleep(3)
                self.logger.exception("Got exception as %s" % (e))
            else:
                break
        if ret[cmd]:
            if 'Connection timed out' in str(ret):
                self.logger.warn("Generic metadata did NOT work")
                result = False
            if 'Successful' in str(ret):
                self.logger.info("Generic metadata worked")
                result = True
        else:
            self.logger.error('Generic metadata check failed')
            result = False

        assert result, "Generic Link local verification failed "
    # end test_generic_link_local_service
