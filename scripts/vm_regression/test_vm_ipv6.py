import traffic_tests
from vn_test import *
from vm_test import *
from floating_ip import *
from policy_test import *
from user_test import UserFixture
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.pkgs.Traffic.traffic.core.stream import Stream
from tcutils.pkgs.Traffic.traffic.core.profile import create, ContinuousProfile
from tcutils.pkgs.Traffic.traffic.core.helpers import Host
from tcutils.pkgs.Traffic.traffic.core.helpers import Sender, Receiver
from base import BaseVnVmTest
from common import isolated_creds
import inspect
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from time import sleep
import test

class TestBasicVMVN0(BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicVMVN0, cls).setUpClass()

    @test.attr(type=['sanity','ipv6'])
    @preposttest_wrapper
    def test_ipv6_vn_add_delete(self):
        '''Test to validate IPV6 VN creation and deletion.
           and verify VN  fixture for ipv4 network for following introspec
               (i) API
                (ii)control node
                (iii) opserver
                (iv) Agent
        '''
        vn_obj = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn22', inputs=self.inputs, subnets=['22.1.1.0/24']))
        assert vn_obj.verify_on_setup()
        ipv6_subnet= ['2ffe::/64']
        ipam = vn_obj.ipam_fq_name
        for ipv6 in ipv6_subnet:
            cidr = {'cidr':ipv6}
            vn_obj.create_subnet(cidr,ipam,ip_version=6)
        return True
    #end test_ipv6_vn_add_delete
#
    @test.attr(type=['sanity','ipv6'])
    @preposttest_wrapper
    def test_ipv6_vm_add_delete(self):
        ''' Test to validate that a VM creation and deletion passes for ipv6 network.
            and verify VM fixture for following introspec
                (i) API 
                (ii)control node
                (iii) opserver 
                (iv) Agent   
        '''
        vm1_name = 'vm_ipv6'
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn22', inputs=self.inputs, subnets=['22.1.1.0/24']))
        assert vn_fixture.verify_on_setup()
        ipv6_subnet= ['2ff1::/64']
        ipam = vn_fixture.ipam_fq_name
        for ipv6 in ipv6_subnet:
            cidr = {'cidr':ipv6}
            vn_fixture.create_subnet(cidr,ipam,ip_version=6)
        vn_obj=vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name, flavor='contrail_flavor_small', image_name='centos65-ipv6'))
        assert vm1_fixture.verify_on_setup()
        return True
    # end test_ipv6_vm_add_delete

    @test.attr(type=['sanity','ipv6'])
    @preposttest_wrapper
    def test_ping6_within_vn(self):
        ''' Validate Ping between two VMs within a VN for ipv6 network. 
            and verify VM fixture for following introspec
                (i) API
                (ii)control node
                (iii) opserver
                (iv) Agent
        '''
        vn1_name = get_random_name('vn30')
        vn1_subnets = ['10.1.1.0/24']
        vn1_vm1_name = get_random_name('vm1')
        vn1_vm2_name = get_random_name('vm2')
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        ipv6_subnet= ['2001::/64']
        ipam = vn1_fixture.ipam_fq_name
        for ipv6 in ipv6_subnet:
            cidr = {'cidr':ipv6}
            vn1_fixture.create_subnet(cidr,ipam,ip_version=6)
        vn_obj=vn1_fixture.obj
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj,flavor='contrail_flavor_small', vm_name=vn1_vm1_name, image_name='centos65-ipv6'))
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, flavor='contrail_flavor_small',vm_name=vn1_vm2_name, image_name='centos65-ipv6'))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        for vm_ipv6 in vm2_fixture.vm_ips :
            if ':' in vm_ipv6 :
                vm2_ipv6= vm_ipv6 
        for vm_ipv6 in vm1_fixture.vm_ips :
            if ':' in vm_ipv6 :
                vm1_ipv6= vm_ipv6
        assert vm1_fixture.ping_to_ipv6(vm2_ipv6)
        assert vm2_fixture.ping_to_ipv6(vm1_ipv6)
        return True
    # end test_ping_within_vn


    @test.attr(type=['sanity','ipv6'])
    @preposttest_wrapper
    def test_ipv6_vm_file_trf_scp_tests(self):
        '''
         Description: Test to validate File Transfer using scp between VMs using ipv6 addresses . Files of different sizes.
         Test steps:
                1. Creating vm's - vm1 and vm2 and a Vn - vn222
                2. Transfer file from vm1 to vm2 with diferrent file sizes using scp
                3. file sizes - 1000,1101,1202,1303,1373, 1374,2210, 2845, 3000, 10000, 10000003
                4. verify files present in vm2 match with the size of the file sent.
         Pass criteria: File in vm2 should match with the transferred file size from vm1

        '''
        vm1_name = 'vm1'
        vm2_name = 'vm2'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        scp_test_file_sizes = ['1000', '1101', '1202', '1303',
            '1373', '1374', '2210', '2845', '3000', '10000', '10000003']
        file = 'somefile'
        y = 'ls -lrt %s' % file
        cmd_to_check_file = [y]
        x = 'sync'
        cmd_to_sync = [x]
        create_result = True
        transfer_result = True
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        ipv6_subnet= ['2011::/64']
        ipam = vn_fixture.ipam_fq_name
        for ipv6 in ipv6_subnet:
            cidr = {'cidr':ipv6}
            vn_fixture.create_subnet(cidr,ipam,ip_version=6)
        vn_obj=vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name,flavor='contrail_flavor_small', image_name='centos65-ipv6'))
        assert vm1_fixture.wait_till_vm_is_up()
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm2_name, project_name=self.inputs.project_name,flavor='contrail_flavor_small', image_name='centos65-ipv6'))
        assert vm2_fixture.wait_till_vm_is_up()

        # ssh and tftp taking sometime to be up and runnning
        #sleep(self.scp_test_starup_wait)
        vm1_fixture.put_pub_key_to_vm()
        vm2_fixture.put_pub_key_to_vm()
        for size in scp_test_file_sizes:
            self.logger.info("-" * 80)
            self.logger.info("FILE SIZE = %sB" % size)
            self.logger.info("-" * 80)

            self.logger.info('Transferring the file from %s to %s using scp' %
                             (vm1_fixture.vm_name, vm2_fixture.vm_name))
            file_transfer_result = vm1_fixture.check_file_transfer(vm2_fixture,
                                                                   size=size)

            if file_transfer_result:
                self.logger.info(
                    'File of size %sB transferred via scp properly' % size)
            else:
                transfer_result = False
                self.logger.error(
                    'File of size %sB not transferred via scp ' % size)
                break

        assert transfer_result, 'File not transferred via scp '
        return transfer_result
    # end test_vm_file_trf_scp_tests

    @test.attr(type=['sanity','ipv6'])
    @preposttest_wrapper
    def test_ipv6_vm_file_trf_tftp_tests(self):
        '''
         Description:  Test to validate File Transfer using tftp between VMs using ipv6 addresses. Files of different sizes .
         Test steps:
                1. Creating vm's - vm1 and vm2 and a Vn - vn222
                2. Transfer file from vm1 to vm2 with diferrent file sizes using tftp
                3. file sizes - 1000,1101,1202,1303,1373, 1374,2210, 2845, 3000, 10000, 10000003
                4. verify files present in vm2 match with the size of the file sent.
          Pass criteria: File in vm2 should match with the transferred file size from vm1

        '''
        vm1_name='vm1'
        vm2_name='vm2'
        vn_name='vn222'
        ts = time.time()
        vn_name = '%s_%s'%(inspect.stack()[0][3],str(ts))
        vn_subnets=['11.1.1.0/24']
        file_sizes=['1000', '1101', '1202', '1303', '1373', '1374', '2210', '2845', '3000', '10000', '10000003']
        file= 'testfile'
        y = 'ls -lrt /var/lib/tftpboot/%s'%file
        cmd_to_check_file = [y]
        z = 'ls -lrt /var/lib/tftpboot/%s'%file
        cmd_to_check_tftpboot_file = [z]
        x = 'sync'
        cmd_to_sync = [x]
        create_result= True
        transfer_result= True
        vn_fixture= self.useFixture(VNFixture(project_name= self.project.project_name, connections= self.connections,
                     vn_name=vn_name, inputs= self.inputs, subnets= vn_subnets))
        assert vn_fixture.verify_on_setup()
        ipv6_subnet= ['2012::/64']
        ipam = vn_fixture.ipam_fq_name
        for ipv6 in ipv6_subnet:
            cidr = {'cidr':ipv6}
            vn_fixture.create_subnet(cidr,ipam,ip_version=6)
        vn_obj= vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                            vn_obj=vn_obj, flavor='contrail_flavor_small',
                            image_name='centos65-ipv6', vm_name=vm1_name,
                            project_name=self.inputs.project_name))
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                            vn_obj=vn_obj, flavor='contrail_flavor_small',
                            image_name='centos65-ipv6', vm_name=vm2_name,
                            project_name=self.inputs.project_name))
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        #ssh and tftp taking sometime to be up and runnning
        for size in file_sizes:
            self.logger.info ("-"*80)
            self.logger.info("FILE SIZE = %sB"%size)
            self.logger.info ("-"*80)
            self.logger.info('Transferring the file from %s to %s using tftp'%(vm1_fixture.vm_name, vm2_fixture.vm_name))

            vm1_fixture.check_file_transfer(dest_vm_fixture = vm2_fixture, mode = 'tftp', size= size )
            self.logger.info('Checking if the file exists on %s'%vm2_fixture.vm_name)
            vm2_fixture.run_cmd_on_vm( cmds= cmd_to_check_file );
            output= vm2_fixture.return_output_cmd_dict[y]
            print output
            if size in output:
                self.logger.info('File of size %sB transferred via tftp properly'%size)
            else:
                transfer_result= False
                self.logger.error('File of size %sB not transferred via tftp '%size)
                break

        if not transfer_result:
            self.logger.error('Tftp transfer failed, lets verify basic things')
            assert vm1_fixture.verify_on_setup()
            assert vm2_fixture.verify_on_setup()
            assert transfer_result
        return transfer_result
    #end test_vm_file_trf_tftp_tests
      
    @test.attr(type=['sanity','ipv6'])
    @preposttest_wrapper
    def test_ping6_across_vn_two_vms_two_different_subnets(self):
        ''' Validate Ping between two VMs across  VNs in 2 different subnets.

        '''
        vn_names = ['vn030','vn031']
        vn_subnets = [['31.1.1.0/30'], ['31.1.2.0/30']]
        # vn1_subnets=['30.1.1.0/24']
        vn1_vm1_name = 'vm1'
        vn1_vm2_name = 'vm2'
        policy_names = ['policy1']
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any',
                'source_network': vn_names[0],
                'dest_network': vn_names[1],
            },
        ]
        policy_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_names[
                    0], rules_list=rules, inputs=self.inputs,
                connections=self.connections))
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_names[0], inputs=self.inputs, subnets=vn_subnets[0],policy_objs=[policy_fixture.policy_obj]))
        assert vn1_fixture.verify_on_setup()
        ipv6_subnet= ['2021::/64']
        ipam = vn1_fixture.ipam_fq_name
        for ipv6 in ipv6_subnet:
            cidr = {'cidr':ipv6}
            vn1_fixture.create_subnet(cidr,ipam,ip_version=6)
        vn1_obj=vn1_fixture.obj
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_names[1], inputs=self.inputs, subnets=vn_subnets[1],policy_objs=[policy_fixture.policy_obj]))
        assert vn2_fixture.verify_on_setup()
        ipv6_subnet= ['2022::/64']
        ipam = vn2_fixture.ipam_fq_name
        for ipv6 in ipv6_subnet:
            cidr = {'cidr':ipv6}
            vn2_fixture.create_subnet(cidr,ipam,ip_version=6)
        vn2_obj=vn2_fixture.obj
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_obj, vm_name=vn1_vm1_name,flavor='contrail_flavor_small', image_name='centos65-ipv6'))
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn2_obj, vm_name=vn1_vm2_name,flavor='contrail_flavor_small', image_name='centos65-ipv6'))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        for vm_ipv6 in vm2_fixture.vm_ips :
            if ':' in vm_ipv6 :
                vm2_ipv6= vm_ipv6
        for vm_ipv6 in vm1_fixture.vm_ips :
            if ':' in vm_ipv6 :
                vm1_ipv6= vm_ipv6
        sleep(10)
        assert vm1_fixture.ping_to_ipv6(vm2_ipv6)
        sleep(30)
        assert vm2_fixture.ping_to_ipv6(vm1_ipv6)
        return True
    #test_ping6_across_vn_two_vms_two_different_subnets

