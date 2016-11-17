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
from base import BaseVnVmTest
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
    @test.attr(type=['sanity', 'ci_sanity', 'suite1'])
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

        gvrouter_cfg_obj = self.api_s_inspect.get_global_vrouter_config()
        ln_svc = gvrouter_cfg_obj.get_link_local_service()
        if ln_svc:
            self.logger.info(
                "Metadata configured in global_vrouter_config as %s" %
                (str(ln_svc)))
        else:
            self.logger.warn(
                "Metadata NOT configured in global_vrouter_config")
            result = False
            assert result
            return True

        text = """#!/bin/sh
echo "Hello World.  The time is now $(date -R)!" | tee /tmp/output.txt
               """
        try:
            with open("/tmp/metadata_script.txt", "w") as f:
                f.write(text)
        except Exception as e:
            self.logger.exception(
                "Got exception while creating /tmp/metadata_script.txt as %s" % (e))

        if os.environ.has_key('ci_image'):
            img_name = os.environ['ci_image']
        else:
            img_name = 'ubuntu'
        vn_name = get_random_name('vn2_metadata')
        vm1_name = get_random_name('vm_in_vn2_metadata')
        vn_fixture = self.create_vn(vn_name=vn_name, af='v4')
        assert vn_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn_fixture=vn_fixture, vm_name=vm1_name,
                                     image_name=img_name,
                                     userdata='/tmp/metadata_script.txt')
        assert vm1_fixture.verify_on_setup()
        assert vm1_fixture.wait_till_vm_is_up()

        cmd = 'ls /tmp/'
        result = False
        for i in range(3):
            self.logger.debug("Retry %s" % (i))
            ret = vm1_fixture.run_cmd_on_vm(cmds=[cmd])
            self.logger.debug("ret : %s" % (ret))
            for elem in ret.values():
                if 'output.txt' in elem:
                    result = True
                    break
            if result:
                break
            time.sleep(2)
        if not result:
            self.logger.warn(
                "metadata_script.txt did not get executed in the vm")
            self.logger.debug('%s' %vm1_fixture.get_console_output())
        else:
            self.logger.debug("Printing the output.txt :")
            cmd = 'cat /tmp/output.txt'
            ret = vm1_fixture.run_cmd_on_vm(cmds=[cmd])
            self.logger.info("%s" % (ret.values()))
            for elem in ret.values():
                if 'Hello World' in elem:
                    result = True
                else:
                    self.logger.warn(
                        "metadata_script.txt did not get executed in the vm...output.txt does not contain proper output")
                    result = False
        assert result
        return True

    @test.attr(type=['sanity','ci_sanity','quick_sanity','suite1'])
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


    @test.attr(type=['sanity', 'suite1', 'ci_sanity'])
    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter',address_family = 'v6')
    def test_ping_within_vn_two_vms_two_different_subnets(self):
        '''
        Description:  Validate Ping between 2 VMs in the same VN, 2 VMs in different VNs.
        Test steps:
                1. Create 2 VNs and launch 2 VMs in them.
                2. Ping between the VMs in the same VN should go thru fine.
                3. Ping to the subnet broadcast and all-broadcast address.
        Pass criteria: VM in the same subnet will respond to both the pings, while the VM in a different VN should respond only to the
                        all-broadcast address.
        Maintainer : ganeshahv@juniper.net
        '''
        vn1_name = get_random_name('vn030')
        vn1_subnets = ['31.1.1.0/29', '31.1.2.0/29']
        subnet1 = '31.1.1.0/29'
        subnet2 = '31.1.2.0/29'
        fixed_ip1 = '31.1.1.4'
        fixed_ip2 = '31.1.2.4'
        subnet_objects = []
        # vn1_subnets=['30.1.1.0/24']
        vn1_vm1_name = get_random_name('vm1')
        vn1_vm2_name = get_random_name('vm2')
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()

        subnet_objects = vn1_fixture.get_subnets()
        ports = {}

        for subnet in subnet_objects:
            if subnet['cidr'] == subnet1:
                ports['subnet1'] = vn1_fixture.create_port(vn1_fixture.vn_id,
                    subnet_id=subnet['id'], ip_address=fixed_ip1)
            elif subnet['cidr'] == subnet2:
                ports['subnet2'] = vn1_fixture.create_port(vn1_fixture.vn_id,
                    subnet_id=subnet['id'],ip_address=fixed_ip2)

        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm1_name, port_ids = [ports['subnet1']['id']]))
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm2_name,port_ids = [ports['subnet2']['id']]))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)
        assert vm2_fixture.ping_to_ip(vm1_fixture.vm_ip)
        # Geting the VM ips
        vm1_ip = vm1_fixture.vm_ip
        vm2_ip = vm2_fixture.vm_ip
        ip_list = [vm1_ip, vm2_ip]
#       gettig broadcast ip for vm1_ip
        ip_broadcast = get_subnet_broadcast('%s/%s'%(vm1_ip, '29'))
        list_of_ip_to_ping = [ip_broadcast, '224.0.0.1', '255.255.255.255']
        # passing command to vms so that they respond to subnet broadcast
        cmd_list_to_pass_vm = [
            'echo 0 > /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts']

        vm1_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm2_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)

        for dst_ip in list_of_ip_to_ping:
            print 'pinging from %s to %s' % (vm1_ip, dst_ip)
# pinging from Vm1 to subnet broadcast
            if os.environ.has_key('ci_image'):
                ping_output = vm1_fixture.ping_to_ip(
                    dst_ip, return_output=True)
            else:
                ping_output = vm1_fixture.ping_to_ip(
                    dst_ip, return_output=True, other_opt='-b')
            expected_result = ' 0% packet loss'
            assert (expected_result in ping_output)
# getting count of ping response from each vm
            string_count_dict = {}
            string_count_dict = get_string_match_count(ip_list, ping_output)
            print string_count_dict
            if (dst_ip == ip_broadcast):
                assert (string_count_dict[vm2_ip] == 0)
            if (dst_ip == '224.0.0.1' or dst_ip == '255.255.255.255'):
                assert (string_count_dict[vm2_ip] > 0) or ('DUP!' in ping_output)
        return True
    #test_ping_within_vn_two_vms_two_different_subnets

    @test.attr(type=['sanity','ci_sanity', 'quick_sanity', 'vcenter', 'suite1'])
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

    @test.attr(type=['sanity','ci_sanity','vcenter', 'suite1'])
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

    @test.attr(type=['sanity','ci_sanity','quick_sanity', 'suite1', 'vcenter','vrouter_gw'])
    @preposttest_wrapper
    def test_ping_within_vn(self):
        '''
        Description:  Validate Ping between 2 VMs in the same VN.
        Test steps:
               1. Create a VN and launch 2 VMs in it.
        Pass criteria: Ping between the VMs should go thru fine.
        Maintainer : ganeshahv@juniper.net
        '''
        vn1_name = get_random_name('vn30')
        vn1_vm1_name = get_random_name('vm1')
        vn1_vm2_name = get_random_name('vm2')
        vn1_fixture = self.create_vn(vn_name=vn1_name,orch=self.orchestrator)
        assert vn1_fixture.verify_on_setup()
        vn1_fixture.read()
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm1_name,orch=self.orchestrator)
        vm2_fixture = self.create_vm(vn_ids=[vn1_fixture.uuid], vm_name=vn1_vm2_name)
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
            "Ping from %s to %s failed" % (vn1_vm1_name, vn1_vm2_name)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
            "Ping from %s to %s failed" % (vn1_vm2_name, vn1_vm1_name)
        return True
    # end test_ping_within_vn

    @test.attr(type=['sanity', 'ci_sanity', 'vcenter', 'suite1'])
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
        vm1_name = get_random_name('nova_client_vm')
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        #assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        img_name = os.environ['ci_image'] if os.environ.has_key('ci_image') else 'ubuntu-traffic'
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name,
                                                image_name=img_name))

        time.sleep(30)
        assert vm1_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()

        cfgm_hostname = self.inputs.host_data[self.inputs.cfgm_ip]['name']
        cfgm_control_ip = self.inputs.host_data[cfgm_hostname]['host_control_ip']
        compute_user = self.inputs.host_data[vm1_fixture.vm_node_ip]['username']
        compute_password = self.inputs.host_data[vm1_fixture.vm_node_ip]['password']
        cfgm_host_new_name = cfgm_hostname + '-test'
        cfgm_ip = self.inputs.api_server_ip or \
                  self.inputs.contrail_external_vip or self.inputs.cfgm_ip
        cfgm_intro_port = '8084'
        link_local_args = "--api_server_ip %s --api_server_port %s \
         --admin_user %s --admin_password %s \
         --linklocal_service_name cfgmintrospect\
         --linklocal_service_ip 169.254.1.2\
         --linklocal_service_port 8084\
         --ipfabric_dns_service_name %s\
         --ipfabric_service_port %s\
         --admin_tenant_name %s\
         " % (cfgm_ip, self.inputs.api_server_port,
              self.inputs.stack_user, self.inputs.stack_password,
              cfgm_host_new_name, cfgm_intro_port,
              self.inputs.project_name)
        if not self.inputs.devstack:
            cmd = "python /usr/share/contrail-utils/provision_linklocal.py --oper add %s" % (link_local_args)
        else:
            cmd = "python /opt/stack/contrail/controller/src/config/utils/provision_linklocal.py  --oper add %s" % (
                link_local_args)

        update_hosts_cmd = 'echo "%s %s" >> /etc/hosts' % (cfgm_control_ip,
            cfgm_host_new_name)
        self.inputs.run_cmd_on_server(vm1_fixture.vm_node_ip,
                                      update_hosts_cmd,
                                      compute_user,
                                      compute_password)

        args = shlex.split(cmd.encode('UTF-8'))
        process = Popen(args, stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = process.communicate()
        if stderr:
            self.logger.warn(
                "Linklocal service could not be created, err : \n %s" % (stderr))
        else:
            self.logger.info("%s" % (stdout))
        cmd = 'wget http://169.254.1.2:8084'

        ret = None
        for i in range(3):
            try:
                self.logger.info("Retry %s" % (i))
                ret = vm1_fixture.run_cmd_on_vm(cmds=[cmd])
                if not ret[cmd]:
                    raise Exception('wget of http://169.254.1.2:8084 returned None')
            except Exception as e:
                time.sleep(5)
                self.logger.exception("Got exception as %s" % (e))
            else:
                break
        if ret[cmd]:
            if 'Connection timed out' in str(ret):
                self.logger.warn("Generic metadata did NOT work")
                result = False
            if '200 OK' in str(ret) or '100%' in str(ret):
                self.logger.info("Generic metadata worked")
                result = True
        else:
            self.logger.error('Generic metadata check failed')
            result = False

        if not self.inputs.devstack:
            cmd = "python /usr/share/contrail-utils/provision_linklocal.py --oper delete %s" % (link_local_args)
        else:
            cmd = "python /opt/stack/contrail/controller/src/config/utils/provision_linklocal.py --oper delete %s" % (
                link_local_args)

        args = shlex.split(cmd.encode('UTF-8'))
        self.logger.info('Deleting the link local service')
        process = Popen(args, stdout=PIPE)
        stdout, stderr = process.communicate()
        if stderr:
            self.logger.warn(
                "Linklocal service could not be deleted, err : \n %s" % (stderr))
            result = result and False
        else:
            self.logger.info("%s" % (stdout))

        # Remove the hosts entry which was added earlier
        update_hosts_cmd = "sed -i '$ d' /etc/hosts"
        self.inputs.run_cmd_on_server(vm1_fixture.vm_node_ip,
                                      update_hosts_cmd,
                                      compute_user,
                                      compute_password)
        assert result, "Generic Link local verification failed"
        return True
    # end test_generic_link_local_service
