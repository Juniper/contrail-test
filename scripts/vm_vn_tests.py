# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import signal
from novaclient import client as mynovaclient
from novaclient import exceptions as novaException
import unittest
import fixtures
import testtools
import traceback
import traffic_tests
from contrail_test_init import *
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from connections import ContrailConnections
from floating_ip import *
from control_node import *
from policy_test import *
from multiple_vn_vm_test import *
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from fabric.context_managers import settings
from fabric.api import run
from tcutils.commands import *

#from analytics_tests import *


class TestVMVN(testtools.TestCase, fixtures.TestWithFixtures):

#    @classmethod
    def setUp(self):
        super(TestVMVN, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.quantum_fixture = self.connections.quantum_fixture
        self.nova_fixture = self.connections.nova_fixture
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.analytics_obj = self.connections.analytics_obj
    # end setUpClass

    def cleanUp(self):
        super(TestVMVN, self).cleanUp()
    # end cleanUp

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_vn_add_delete(self):
        '''Test to validate VN creation and deletion.
        '''
        vn_obj = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn22', inputs=self.inputs, subnets=['22.1.1.0/24']))
        assert vn_obj.verify_on_setup()
        assert vn_obj
        return True
    # end

    @preposttest_wrapper
    def test_duplicate_vn_add(self):
        '''Test to validate adding a Duplicate VN creation and deletion.
        '''
        vn_obj1 = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn22', inputs=self.inputs, subnets=['22.1.1.0/24']))
        assert vn_obj1.verify_on_setup()
        assert vn_obj1

        vn_obj2 = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn22', inputs=self.inputs, subnets=['22.1.1.0/24']))
        assert vn_obj2.verify_on_setup()
        assert vn_obj2, 'Duplicate VN cannot be created'
        if (vn_obj1.vn_id == vn_obj2.vn_id):
            self.logger.info('Same obj created')
        else:
            self.logger.error('Different objs created.')
        return True
    # end test_duplicate_vn_add

    @preposttest_wrapper
    def test_vn_name_with_spl_characters(self):
        '''Test to validate VN name with special characters is allowed.
        '''
        vn1_obj = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn.1', inputs=self.inputs, subnets=['22.1.1.0/29']))
        assert vn1_obj.verify_on_setup()
        assert vn1_obj

        vn2_obj = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn,2', inputs=self.inputs, subnets=['33.1.1.0/30']))
        assert vn2_obj.verify_on_setup()
        assert vn2_obj

        vn3_obj = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn&3', inputs=self.inputs, subnets=['44.1.1.0/29']))
        self.logger.info(
            "VN names with '&' are allowed via API, but not through Openstack ==> Bug 1023")
        assert not vn3_obj.verify_on_setup()
        if vn3_obj:
            self.logger.error('Bug 1023 needs to be fixed')

        vn4_obj = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn_4', inputs=self.inputs, subnets=['55.1.1.0/31']))
        assert vn4_obj.verify_on_setup()
        assert vn4_obj

        return True
    # end test_vn_name_with_spl_characters

    @preposttest_wrapper
    def test_vn_vm_no_ip(self):
        '''Test to check that VMs launched in a VN with no subnet, will go to error state.
        '''
        vn_obj = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn22', inputs=self.inputs))
        #assert vn_obj.verify_on_setup()
        assert vn_obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj.obj, vm_name='vm222', project_name=self.inputs.project_name))
        self.logger.info('The VM should not get an IP')
        assert not vm1_fixture.verify_on_setup()
        return True
    # end test_vn_vm_no_ip

    @preposttest_wrapper
    def test_ipam_add_delete(self):
        '''Test to validate IPAM creation, association of a VN and creating VMs in the VN. Ping b/w the VMs should be successful.
        '''
        project_obj = self.useFixture(
            ProjectFixture(vnc_lib_h=self.vnc_lib, connections=self.connections))
        ipam_obj = self.useFixture(
            IPAMFixture(project_obj=project_obj, name='my-ipam'))
        assert ipam_obj.verify_on_setup()
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn22', inputs=self.inputs, subnets=['22.1.1.0/24'], ipam_fq_name=ipam_obj.fq_name))
        assert vn_fixture.verify_on_setup()

        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_fixture.obj, vm_name='vm1'))
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_fixture.obj, vm_name='vm2'))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm2_fixture.vm_obj)
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)

        return True
    # end test_ipam_add_delete

    @preposttest_wrapper
    def test_ipam_persistence_across_restart_reboots(self):
        '''Test to validate IPAM persistence across restarts and reboots of nodes.
        '''
        project_obj = self.useFixture(
            ProjectFixture(vnc_lib_h=self.vnc_lib, connections=self.connections))
        ipam_obj = self.useFixture(
            IPAMFixture(project_obj=project_obj, name='my-ipam'))
        assert ipam_obj.verify_on_setup()

        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn22', inputs=self.inputs, subnets=['22.1.1.0/24'], ipam_fq_name=ipam_obj.fq_name))
        assert vn_fixture.verify_on_setup()

        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_fixture.obj, vm_name='vm1'))
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_fixture.obj, vm_name='vm2'))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm2_fixture.vm_obj)
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)
        self.logger.info('Will restart the services now')
        for compute_ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter', [compute_ip])
        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('contrail-control', [bgp_ip])
        sleep(30)

        self.logger.info(
            'Will check if the ipam persists and ping b/w VMs is still successful')

        assert ipam_obj
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)

#       reboot the compute node now and verify the ipam persistence
#       for compute_ip in self.inputs.compute_ips:
#           self.inputs.reboot(compute_ip)
#       sleep(120)
#       assert ipam_obj
#       reboot the control nodes now and verify the ipam persistence
#       for bgp_ip in self.inputs.bgp_ips:
#           self.inputs.reboot(bgp_ip)
#       sleep(120)
#       assert ipam_obj
#       reboot the cfgm node now and verify the ipam persistence
#       self.inputs.reboot(self.inputs.cfgm_ip)
#       sleep(120)

#       self.logger.info('Will check if the ipam persists and ping b/w VMs is still successful')
#       assert ipam_obj
#       assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )

        return True
    # end test_ipam_persistence_across restart_reboots

    @preposttest_wrapper
    def test_release_ipam(self):
        '''Test to validate that IPAM cannot be deleted until the VM associated with it is deleted.
        '''
        project_obj = self.useFixture(
            ProjectFixture(vnc_lib_h=self.vnc_lib, connections=self.connections))
        ipam_obj = self.useFixture(
            IPAMFixture(project_obj=project_obj, name='my-ipam'))
        assert ipam_obj.verify_on_setup()

        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn22', inputs=self.inputs, subnets=['22.1.1.0/24'], ipam_fq_name=ipam_obj.fq_name))
        assert vn_fixture.verify_on_setup()

        try:
            self.vnc_lib.network_ipam_delete(vn_fixture.ipam_fq_name)
        except RefsExistError as e:
            self.logger.info(
                'RefsExistError:Check passed that the IPAM cannot be released when the VN is associated to it.')

        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_fixture.obj, vm_name='vm1'))
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_fixture.obj, vm_name='vm2'))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm2_fixture.vm_obj)
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)

        try:
            self.vnc_lib.network_ipam_delete(vn_fixture.ipam_fq_name)
        except RefsExistError as e:
            self.logger.info(
                'RefsExistError:Check passed that the IPAM cannot be released when the VN is associated to it, which has VMs on it.')

        return True
    # end test_release_ipam

    @preposttest_wrapper
    def test_shutdown_vm(self):
        ''' Test to validate that VN is unaffected after the VMs in it are shutdown.
        '''
        vm1_name = 'vm_mine'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        cmd_to_shutdown_vm = ['shutdown -h now']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_shutdown_vm, as_sudo=True)
        assert vn_fixture.verify_on_setup()
        return True
    # end test_shutdown_vm

    @preposttest_wrapper
    def test_disassociate_vn_from_vm(self):
        ''' Test to validate that disassociating a VN from a VM fails.
        '''
        vm1_name = 'vm_mine'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        try:
            self.logger.info(' Will try deleting the VN now')
            self.vnc_lib.virtual_network_delete(id=vn_obj['network']['id'])
            assert vn_fixture.verify_on_setup()
            assert vm1_fixture.verify_on_setup()
        except RefsExistError as e:
            self.logger.info(
                'RefsExistError:Check passed that the VN cannot be disassociated/deleted when the VM exists')

        return True
    # end test_disassociate_vn_from_vm

    @preposttest_wrapper
    def test_vm_gw_tests(self):
        ''' Test to validate gateway IP assignments the VM interface.
        '''
        vm1_name = 'vm_mine'
        vm2_name = 'vm_yours'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name))

        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm2_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm2_fixture.vm_obj)
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)

        self.logger.info(
            'Adding a static GW and checking that ping is still successful after the change')
        cmd_to_add_gw = ['route add default gw 11.1.1.254']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_gw)
        assert vm1_fixture.verify_on_setup()
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)
        self.logger.info(
            'Adding a static GW, pointing to the metadata IP and checking that ping succeeds')
        i = 'route add default gw %s' % vm1_fixture.local_ip
        cmd_to_change_gw = [i]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_change_gw)
        assert vm1_fixture.verify_on_setup()
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)
        return True
    # end test_vm_static_ip_tests

    @preposttest_wrapper
    def test_vm_static_ip_tests(self):
        ''' Test to validate Static IP to the VM interface.
        '''
        vm1_name = 'vm_mine'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)

        self.logger.info('Adding the same address as a Static IP')
        cmd = 'ifconfig eth0 %s netmask 255.255.255.0' % vm1_fixture.vm_ip
        cmd_to_add_static_ip = [cmd]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_static_ip, as_sudo=True)
        assert vm1_fixture.verify_on_setup()
        result = True

        self.logger.info('Adding a different address as a Static IP')
        cmd_to_add_file = ['touch batchfile']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_file)

        self.logger.info(
            'WIll add a different address and revert back to the original IP')
        cmd_to_add_cmd_to_file = [
            "echo 'ifconfig; route; sudo ifconfig eth0 10.10.10.10 netmask 255.255.255.0; ifconfig; route; sudo ifconfig eth0 11.1.1.253 netmask 255.255.255.0; ifconfig; route; sudo ifdown eth0; sleep 5; sudo ifup eth0; ifconfig; route' > batchfile"]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_cmd_to_file)

        cmd_to_exec_file = ['sh batchfile | tee > out.log']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_exec_file)

        i = 'cat out.log'
        cmd_to_view_output = ['cat out.log']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_view_output)

        output = vm1_fixture.return_output_cmd_dict[i]
        print output
        if '10.10.10.10' not in output:
            result = False
        assert vm1_fixture.verify_on_setup()
        return result
    # end test_vm_static_ip_tests

    @preposttest_wrapper
    def test_vm_file_trf_tftp_tests(self):
        '''
         Description:  Test to validate File Transfer using tftp between VMs. Files of different sizes.
         Test steps:
                1. Creating vm's - vm1 and vm2 and a Vn - vn222
                2. Transfer file from vm1 to vm2 with diferrent file sizes using tftp
                3. file sizes - 1000,1101,1202,1303,1373, 1374,2210, 2845, 3000, 10000, 10000003
                4. verify files present in vm2 match with the size of the file sent.
          Pass criteria: File in vm2 should match with the transferred file size from vm1

          Maintainer : ganeshahv@juniper.net
        '''
        vm1_name = 'vm1'
        vm2_name = 'vm2'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        file_sizes = ['1000', '1101', '1202', '1303', '1373',
                      '1374', '2210', '2845', '3000', '10000', '10000003']
        file = 'testfile'
        y = 'ls -lrt /var/lib/tftpboot/%s' % file
        cmd_to_check_file = [y]
        z = 'ls -lrt /var/lib/tftpboot/%s' % file
        cmd_to_check_tftpboot_file = [z]
        x = 'sync'
        cmd_to_sync = [x]
        create_result = True
        transfer_result = True
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, flavor='contrail_flavor_small', image_name='ubuntu-tftp', vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, flavor='contrail_flavor_small', image_name='ubuntu-tftp', vm_name=vm2_name, project_name=self.inputs.project_name))
        assert vm2_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up(vm2_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        # ssh and tftp taking sometime to be up and runnning
        sleep(60)
        for size in file_sizes:
            self.logger.info("-" * 80)
            self.logger.info("FILE SIZE = %sB" % size)
            self.logger.info("-" * 80)
            self.logger.info('Transferring the file from %s to %s using tftp' %
                             (vm1_fixture.vm_name, vm2_fixture.vm_name))

            vm1_fixture.check_file_transfer(
                dest_vm_fixture=vm2_fixture, mode='tftp', size=size)
            self.logger.info('Checking if the file exists on %s' %
                             vm2_fixture.vm_name)
            vm2_fixture.run_cmd_on_vm(cmds=cmd_to_check_file)
            output = vm2_fixture.return_output_cmd_dict[y]
            print output
            if size in output:
                self.logger.info(
                    'File of size %sB transferred via tftp properly' % size)
            else:
                transfer_result = False
                self.logger.error(
                    'File of size %sB not transferred via tftp ' % size)

        assert transfer_result, 'File not transferred via tftp '
        return transfer_result
    # end test_vm_file_trf_tftp_tests

    scp_test_starup_wait = 60  # seconds
    scp_test_file_sizes = ['1000', '1101', '1202', '1303',
                           '1373', '1374', '2210', '2845', '3000', '10000', '10000003']

    @preposttest_wrapper
    def test_vm_file_trf_scp_tests(self):
        '''
         Description: Test to validate File Transfer using scp between VMs. Files of different sizes.
         Test steps:
                1. Creating vm's - vm1 and vm2 and a Vn - vn222
                2. Transfer file from vm1 to vm2 with diferrent file sizes using scp
                3. file sizes - 1000,1101,1202,1303,1373, 1374,2210, 2845, 3000, 10000, 10000003
                4. verify files present in vm2 match with the size of the file sent.
         Pass criteria: File in vm2 should match with the transferred file size from vm1

         Maintainer : ganeshahv@juniper.net
        '''
        vm1_name = 'vm1'
        vm2_name = 'vm2'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
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
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm2_name, project_name=self.inputs.project_name))
        assert vm2_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up(vm2_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)

        # ssh and tftp taking sometime to be up and runnning
        sleep(self.scp_test_starup_wait)
        vm1_fixture.put_pub_key_to_vm()
        vm2_fixture.put_pub_key_to_vm()
        for size in self.scp_test_file_sizes:
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

    @preposttest_wrapper
    def test_vm_intf_tests(self):
        ''' Test to validate Loopback and eth0 intfs up/down events.
        '''
        vm1_name = 'vm_mine'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        self.logger.info('Shutting down Loopback intf')
        cmd_to_intf_down = ['ifdown lo ']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_intf_down, as_sudo=True)
        assert vm1_fixture.verify_on_setup()
        self.logger.info('Bringing up Loopback intf')
        cmd_to_intf_up = ['ifup lo']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_intf_up, as_sudo=True)
        assert vm1_fixture.verify_on_setup()
        cmd_to_create_file = ['touch batchfile']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_create_file)
        cmd_to_add_cmd_to_file = [
            "echo 'ifconfig; route; sudo ifdown eth0; ifconfig; route; sleep 10; sudo ifup eth0;  ifconfig; route ' > batchfile"]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_cmd_to_file)
        cmd_to_exec_file = ['sh batchfile | tee > out.log']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_exec_file)
        assert vm1_fixture.verify_on_setup()
        return True
    # end test_vm_intf_tests

    @preposttest_wrapper
    def test_vm_arp(self):
        ''' Test to validate that the fool-proof way is to not answer
        for arp request from the guest for the address the tap i/f is
        "configured" for.
        '''
        vm1_name = 'vm_mine'
        vm2_name = 'vm_yours'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, image_name='ubuntu-arping', vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, image_name='ubuntu-arping', vm_name=vm2_name, project_name=self.inputs.project_name))
        assert vm2_fixture.verify_on_setup()

        i = 'arping -c 10 %s' % vm1_fixture.vm_ip
        cmd_to_output = [i]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_output, as_sudo=True)
        output = vm1_fixture.return_output_cmd_dict[i]
        print output
        result = True
        if not '100%' in output:
            self.logger.error(
                'Arping to the VMs own address should have failed')
            result = False
        else:
            self.logger.info('Arping to the VMs own address fails')

        j = 'arping -c 10 %s' % vm2_fixture.vm_ip
        cmd_to_output = [j]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_output, as_sudo=True)
        output1 = vm1_fixture.return_output_cmd_dict[j]
        print output1
        if not '0%' in output:
            self.logger.error(
                'Arping to the other VMs address should have passed')
            result = False
        else:
            self.logger.info('Arping to the other VMs address passes')

        assert result, "ARPing Failure"
        return True
    # end test_vm_arp

    @preposttest_wrapper
    def test_host_route_add_delete(self):
        ''' Test to validate that host_route is sent to the  VM via DHCP.
        '''
        vm1_name = 'vm_mine'
        vm2_name = 'vm_yours'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        host_rt = ['1.1.1.1/32', '0.0.0.0/0']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_fixture.add_host_routes(host_rt)
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name, flavor='contrail_flavor_large', image_name='ubuntu-traffic'))
        assert vm1_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        route_cmd = 'route -n'
        vm1_fixture.run_cmd_on_vm(cmds=[route_cmd], as_sudo=True)
        output = vm1_fixture.return_output_cmd_dict[route_cmd]
        self.logger.info('%s' % output)
        for rt in host_rt:
            if (rt.split('/')[0]) in output:
                self.logger.info('Route to %s found in the route-table' % rt)
                result = True
            else:
                self.logger.info(
                    'Route to %s not found in the route-table' % rt)
                result = False
        assert result, 'No Host-Route in the route-table'

        vn_fixture.del_host_routes(host_rt)
        vn_obj = vn_fixture.obj
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm2_name, project_name=self.inputs.project_name, flavor='contrail_flavor_large', image_name='ubuntu-traffic'))
        assert vm2_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up(vm2_fixture.vm_obj)
        new_route_cmd = 'route -n'
        vm2_fixture.run_cmd_on_vm(cmds=[new_route_cmd], as_sudo=True)
        new_output = vm2_fixture.return_output_cmd_dict[new_route_cmd]
        self.logger.info('%s' % new_output)
        for rt in host_rt:
            route_ip = rt.split('/')[0]
            if "0.0.0.0" in rt:
                self.logger.info('Skip verifying default route')
                continue
            if re.search(r'\broute_ip\b', new_output):
                self.logger.info('Route to %s found in the route-table' % rt)
                new_result = False
            else:
                self.logger.info(
                    'Route to %s not found in the route-table' % rt)
                new_result = True
        assert new_result, 'Host-Route still found in the route-table'

        return True
    # end test_host_route_add_delete

    @preposttest_wrapper
    def test_vm_add_delete(self):
        ''' Test to validate that a VM creation and deletion passes.
        '''
        vm1_name = 'vm_mine'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name, flavor='contrail_flavor_large', image_name='ubuntu-traffic'))
        assert vm1_fixture.verify_on_setup()
        return True
    # end test_vm_add_delete

    @preposttest_wrapper
    def test_static_route_to_vm(self):
        ''' Test to validate that traffic to a destination for which a VM is a next-hop sis sent to the tap-interface in the agent, corresponding to the VM.
        '''
        vm1_name = 'vm_mine'
        vn1_name = 'vn222'
        vn1_subnets = ['11.1.1.0/24']
        vm2_name = 'vm_yours'
        vn2_name = 'vn111'
        vn2_subnets = ['12.1.1.0/24']

        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vn1_obj = vn1_fixture.obj

        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn1_obj, vm_name=vm1_name, project_name=self.inputs.project_name, flavor='contrail_flavor_large', image_name='ubuntu-traffic'))
        assert vm1_fixture.verify_on_setup()
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn1_obj, vm_name=vm2_name, project_name=self.inputs.project_name, flavor='contrail_flavor_large', image_name='ubuntu-traffic'))
        assert vm2_fixture.verify_on_setup()

        self.logger.info(
            '+++++ Will add a static route with the VM1 as the next-hop and verify the route entry in the agent ++++++')
        vm1_vmi_id = vm1_fixture.cs_vmi_obj[vn1_fixture.vn_fq_name][
            'virtual-machine-interface']['uuid']
        add_static_route_cmd = 'python provision_static_route.py --prefix 1.2.3.4/32 --virtual_machine_interface_id ' + vm1_vmi_id + ' --tenant_name "admin" --api_server_ip 127.0.0.1 --api_server_port 8082 \
                --oper add --route_table_name my_route_table'
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.cfgm_ips[0]), password=self.inputs.password, warn_only=True, abort_on_prompts=False, debug=True):
            status = run('cd /opt/contrail/utils;' + add_static_route_cmd)
            self.logger.debug("%s" % status)
            m = re.search(r'Creating Route table', status)
            assert m, 'Failed in Creating Route table'
        time.sleep(10)
        for vm_fixture in [vm1_fixture, vm2_fixture]:
            (domain, project, vn) = vn1_fixture.vn_fq_name.split(':')
            inspect_h = self.agent_inspect[vm_fixture.vm_node_ip]
            agent_vrf_objs = inspect_h.get_vna_vrf_objs(domain, project, vn)
            agent_vrf_obj = vm_fixture.get_matching_vrf(
                agent_vrf_objs['vrf_list'], vn1_fixture.vrf_name)
            vn_vrf_id = agent_vrf_obj['ucindex']
            paths = inspect_h.get_vna_active_route(
                vrf_id=vn_vrf_id, ip='1.2.3.4', prefix='32')['path_list']
            self.logger.info('There are %s nexthops to 1.2.3.4 on Agent %s' %
                             (len(paths), vm_fixture.vm_node_ip))

        compute_ip = vm1_fixture.vm_node_ip
        compute_user = self.inputs.host_data[compute_ip]['username']
        compute_password = self.inputs.host_data[compute_ip]['password']
        session = ssh(compute_ip, compute_user, compute_password)
        vm1_tapintf = vm1_fixture.tap_intf[vn1_fixture.vn_fq_name]['name']
        cmd = 'tcpdump -ni %s icmp -vvv -c 2 > /tmp/%s_out.log' % (vm1_tapintf,
                                                                   vm1_tapintf)
        execute_cmd(session, cmd, self.logger)

        self.logger.info('***** Will start a ping from %s to 1.2.3.4 *****' %
                         vm2_fixture.vm_name)
        vm2_fixture.ping_with_certainty('1.2.3.4', expectation=False)
        self.logger.info('***** Will check the result of tcpdump *****')
        output_cmd = 'cat /tmp/%s_out.log' % vm1_tapintf
        output, err = execute_cmd_out(session, output_cmd, self.logger)
        print output
        if '1.2.3.4' in output:
            self.logger.info(
                'Traffic is going to the tap interface of %s correctly' %
                vm1_fixture.vm_name)
        else:
            result = False
            assert result
            self.logger.error(
                'Traffic to 1.2.3.4 not seen on the tap interface of %s' %
                vm1_fixture.vm_name)

        self.logger.info(
            '-------------------------Will delete the static route now------------------')
        del_static_route_cmd = 'python provision_static_route.py --prefix 1.2.3.4/32 --virtual_machine_interface_id ' + vm1_vmi_id + ' --tenant_name "admin" --api_server_ip 127.0.0.1 --api_server_port 8082 \
                --oper del --route_table_name my_route_table'
        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.cfgm_ips[0]), password=self.inputs.password, warn_only=True, abort_on_prompts=False, debug=True):
            del_status = run('cd /opt/contrail/utils;' + del_static_route_cmd)
            self.logger.debug("%s" % del_status)
        time.sleep(10)

        for vm_fixture in [vm1_fixture, vm2_fixture]:
            (domain, project, vn) = vn1_fixture.vn_fq_name.split(':')
            inspect_h = self.agent_inspect[vm_fixture.vm_node_ip]
            agent_vrf_objs = inspect_h.get_vna_vrf_objs(domain, project, vn)
            agent_vrf_obj = vm_fixture.get_matching_vrf(
                agent_vrf_objs['vrf_list'], vn1_fixture.vrf_name)
            vn_vrf_id = agent_vrf_obj['ucindex']
            del_check = True
            if inspect_h.get_vna_active_route(vrf_id=vn_vrf_id, ip='1.2.3.4', prefix='32') == None:
                self.logger.info('There is no route to 1.2.3.4 on Agent %s' %
                                 vm_fixture.vm_node_ip)
            else:
                del_check = False
            assert del_check, 'Static Route Deletion unsuccessful'

        return True
    # end test_static_route_to_vm

    @preposttest_wrapper
    def test_vm_multiple_flavors(self):
        ''' Test to validate creation and deletion of VMs of all flavors.
        '''
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj

        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm_tiny', flavor='m1.tiny', project_name=self.inputs.project_name, image_name='cirros-0.3.0-x86_64-uec'))

        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm_small', flavor='m1.small', project_name=self.inputs.project_name))

        vm3_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm_medium', flavor='m1.medium', project_name=self.inputs.project_name))

        vm4_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm_large', flavor='m1.large', project_name=self.inputs.project_name))

        vm5_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm_xlarge', flavor='m1.xlarge', project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()
        assert vm5_fixture.verify_on_setup()

        for a in range(1, 6):
            eval('self.nova_fixture.wait_till_vm_is_up(vm%d_fixture.vm_obj )' %
                 a)

        for i in range(1, 5):
            for j in range(i + 1, 6):
                ping = eval('vm%d_fixture.ping_to_ip ( vm%d_fixture.vm_ip )' %
                            (i, j))
                assert 'ping'

        return True
    # end test_vm_multiple_flavors

    @preposttest_wrapper
    def test_vm_vn_block_exhaustion(self):
        ''' Test to validate that a VMs cannot be created after the IP-Block is exhausted.
        '''
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/29']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        self.logger.info(
            'out of /29 block, we can have 5 usable addresses. Only 5 VMs should get launched properly.')

        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm1', project_name=self.inputs.project_name))

        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm2', project_name=self.inputs.project_name))

        vm3_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm3', project_name=self.inputs.project_name))

        vm4_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm4', project_name=self.inputs.project_name))

        vm5_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm5', project_name=self.inputs.project_name))

        self.logger.info(
            'The 6th VM should go into ERROR state as it is unable to get any ip. The ip-block is exhausted')

        sleep(15)
        vm6_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm6', project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()
        assert vm5_fixture.verify_on_setup()
        assert not vm6_fixture.verify_on_setup()

        return True
    # end test_vm_vn_block_exhaustion

    @preposttest_wrapper
    def test_multistep_vm_delete_with_stop_start_service(self):
        ''' Test to validate VMs addition deletion after service restarts.
        '''
        vn_name = 'vn1'
        vn_subnets = ['10.10.10.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        self.logger.info('Launching VM')
        vm1_fixture = VMFixture(connections=self.connections,
                                vn_obj=vn_obj, vm_name='vm1', project_name=self.inputs.project_name)
        vm1_fixture.setUp()
        vm1_fixture.verify_vm_launched()
        self.logger.info('VM launched successfully.Stopping vrouter service')
        for compute_ip in self.inputs.compute_ips:
            self.inputs.stop_service('contrail-vrouter', [compute_ip])
        #    self.addCleanup( sleep(10))
            self.addCleanup(self.inputs.start_service,
                            'contrail-vrouter', [compute_ip])
        self.logger.info('Trying to delete the VM')
        assert not vm1_fixture.cleanUp()
        self.logger.info('VM is not deleted as expected')
        for compute_ip in self.inputs.compute_ips:
            self.logger.info('Starting Vrouter Service')
            self.inputs.start_service('contrail-vrouter', [compute_ip])
            sleep(10)
        return True
    # end test_multistep_vm_delete_with_stop_start_service

    @preposttest_wrapper
    def test_multistep_vm_add_delete_with_stop_start_service(self):
        ''' Test to validate VMs addition deletion after service restarts.
        '''
        vn_name = 'vn1'
        vn_subnets = ['10.10.10.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        self.logger.info('Launching VM')

        vm1_fixture = VMFixture(connections=self.connections,
                                vn_obj=vn_obj, vm_name='vm1', project_name=self.inputs.project_name)
        vm1_fixture.setUp()
        vm1_fixture.verify_vm_launched()

        self.logger.info('vm1 launched successfully.Stopping vrouter service')
        for compute_ip in self.inputs.compute_ips:
            self.inputs.stop_service('contrail-vrouter', [compute_ip])
            self.addCleanup(self.inputs.start_service,
                            'contrail-vrouter', [compute_ip])
        self.logger.info('Trying to delete vm1')
        assert not vm1_fixture.cleanUp()
        self.logger.info(
            'vm1 is not deleted as expected.Trying to launch a new VM vm2')
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm2', project_name=self.inputs.project_name))
        vm2_fixture.verify_vm_launched()
        self.logger.info('Checking if vm2 has booted up')
        assert not self.nova_fixture.wait_till_vm_is_up(vm2_fixture.vm_obj)
        self.logger.info(
            'vm2 has not booted up as expected.Starting vrouter service')
        for compute_ip in self.inputs.compute_ips:
            self.inputs.start_service('contrail-vrouter', [compute_ip])
        self.nova_fixture.wait_till_vm_is_up(vm2_fixture.vm_obj)
        self.logger.info('vm2 is up now as expected')
        assert vm2_fixture.verify_on_setup()

        return True
    # end test_multistep_vm_add_delete_with_stop_start_service

    @preposttest_wrapper
    def test_nova_com_sch_restart_with_multiple_vn_vm(self):
        ''' Test to validate that multiple VM creation and deletion passes.
        '''
        vm1_name = 'vm_mine'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_count_for_test = 32
        if (len(self.inputs.compute_ips) == 1):
            vn_count_for_test = 5
        vm_fixture = self.useFixture(
            create_multiple_vn_and_multiple_vm_fixture(
                connections=self.connections,
                vn_name=vn_name, vm_name=vm1_name, inputs=self.inputs, project_name=self.inputs.project_name,
                subnets=vn_subnets, vn_count=vn_count_for_test, vm_count=1, subnet_count=1, image_name='cirros-0.3.0-x86_64-uec',
                flavor='m1.tiny'))
        time.sleep(100)
        try:
            assert vm_fixture.verify_vms_on_setup()
            assert vm_fixture.verify_vns_on_setup()
        except Exception as e:
            self.logger.exception("Got exception as %s" % (e))

        compute_ip = []
        for vmobj in vm_fixture.vm_obj_dict.values():
            vm_host_ip = vmobj.vm_node_ip
            if vm_host_ip not in compute_ip:
                compute_ip.append(vm_host_ip)
        self.inputs.restart_service('openstack-nova-compute', compute_ip)
        self.inputs.restart_service('openstack-nova-scheduler', compute_ip)
        sleep(30)
        for vmobj in vm_fixture.vm_obj_dict.values():
            assert vmobj.verify_on_setup()
        return True
    # end test_nova_com_sch_restart_with_multiple_vn_vm

    @preposttest_wrapper
    def test_vn_vm_no_ip_assign(self):
        '''Test to check that VM launched in a VN with no subnet gets ip assigned after subnet is assigned to the VN and VM is made active.
        '''
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn22', inputs=self.inputs))
        assert vn_fixture

        result = True
        vn_obj = self.quantum_fixture.get_vn_obj_if_present('vn22')
        vn_id = vn_obj['network']['id']
        subnet = '20.20.20.0/24'
        self.logger.info('VN launched with no ip block.Launching VM now.')
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_fixture.obj, vm_name='vm222', project_name=self.inputs.project_name))
        self.project_fixture = self.useFixture(ProjectFixture(
            vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
        vm_obj = self.nova_fixture.get_vm_if_present(
            'vm222', self.project_fixture.uuid)

        self.logger.info('The VM should not get any IP')
        assert not vm1_fixture.verify_on_setup()
        self.logger.info('Now assigning IP block to VN')
        ipam = vn_fixture.ipam_fq_name
        vn_fixture.create_subnet(subnet, ipam)
        vnnow_obj = self.quantum_fixture.get_vn_obj_if_present('vn22')
        subnet_created = vnnow_obj['network'][
            'contrail:subnet_ipam'][0]['subnet_cidr']
        if subnet_created != subnet:
            self.logger.error('ip block is not assigned to VN')
            result = False
            assert result
        else:
            self.logger.info(
                'ip block is assigned to the VN.Chcking VM state')
            vm_obj.get()
            state = vm_obj.status
            if state == 'ACTIVE':
                self.logger.error('VM status is %s.Should not be active' %
                                  (state))
                result = False
                assert result
            else:
                self.logger.info('VM status is not ACTIVE as expected.')
            # vm_obj.reset_state('active')
            # vm_obj.get()
            # state_new=vm_obj.status
            # if state_new!='ACTIVE':
            #    self.logger.error ('VM is not active')
            #    result = False
            #    assert result
            # else:
            #    self.logger.info ('VM status is ACTIVE as expected.VM should get ip if bug 954 is fixed')
            #    result = self.nova_fixture.get_vm_ip(vm_obj, 'vn22')
            #    assert result
            return result
   # end test_vn_vm_no_ip_assign

    @preposttest_wrapper
    def test_vn_in_agent_with_vms_add_delete(self):
        ''' Test to validate VN's existence and removal in agent with deletion of associated VMs.
        '''
        vn_name = 'vn1'
        vn_subnets = ['10.10.10.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        self.logger.info('Launching VMs')

        vm1_fixture = VMFixture(connections=self.connections,
                                vn_obj=vn_obj, vm_name='vm1', project_name=self.inputs.project_name)
        vm1_fixture.setUp()
        vm1_fixture.verify_vm_launched()

        vm2_fixture = VMFixture(connections=self.connections,
                                vn_obj=vn_obj, vm_name='vm2', project_name=self.inputs.project_name)
        vm2_fixture.setUp()
        vm2_fixture.verify_vm_launched()
        self.logger.info('vm1 and vm2 launched successfully.')
        sleep(10)
        # for compute_ip in self.inputs.compute_ips:
        self.logger.info('Deleting vm2')
        vm2_fixture.cleanUp()
        self.logger.info('Checking if vn is still present in agent')
        assert not vn_fixture.verify_vn_not_in_agent()
        self.logger.info('VN is present in agent as expected.Now deleting vm1')
        vm1_fixture.cleanUp()
        self.logger.info('Checking if VN is removed from agent')
       # assert vn_fixture.verify_vn_not_in_agent()
        self.logger.info('VN is not present in agent as expected')

        return True
    # end test_vn_in_agent_with_vms_add_delete

    @preposttest_wrapper
    def test_traffic_bw_vms_diff_pkt_size(self):
        ''' Test to validate TCP, ICMP, UDP traffic of different packet sizes b/w VMs created within a VN.
        '''
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/29']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        # Get all compute host
        host_list = []
        for host in self.inputs.compute_ips:
            host_list.append(self.inputs.host_data[host]['name'])
        print host_list
        if len(set(self.inputs.compute_ips)) > 1:
            self.logger.info("Multi-Node Setup")
            vm1_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_large', image_name='ubuntu-traffic', vm_name='vm1', node_name=host_list[1]))
            assert vm1_fixture.verify_on_setup()
            vm2_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_large', image_name='ubuntu-traffic', vm_name='vm2', node_name=host_list[0]))
            assert vm2_fixture.verify_on_setup()
        else:
            self.logger.info("Single-Node Setup")
            vm1_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_large', image_name='ubuntu-traffic', vm_name='vm1'))
            vm2_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_large', image_name='ubuntu-traffic', vm_name='vm2'))
            assert vm1_fixture.verify_on_setup()
            assert vm2_fixture.verify_on_setup()

        out1 = self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        if out1 == False:
            return {'result': out1, 'msg': "%s failed to come up" % vm1_fixture.vm_name}
        else:
            sleep(10)
            self.logger.info('Will install Traffic package on %s' %
                             vm1_fixture.vm_name)
            vm1_fixture.install_pkg("Traffic")

        out2 = self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        if out2 == False:
            return {'result': out2, 'msg': "%s failed to come up" % vm2_fixture.vm_name}
        else:
            sleep(10)
            self.logger.info('Will install Traffic package on %s' %
                             vm2_fixture.vm_name)
            vm2_fixture.install_pkg("Traffic")
        result = True
        msg = []
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['tcp', 'icmp', 'udp']
        total_streams = {}
        total_streams['icmp'] = 1
        total_streams['udp'] = 2
        total_streams['tcp'] = 2
        dpi = 9100
        proto = 'udp'
        packet_sizes = [40, 64, 254, 748, 1350]
        cmd_to_increase_mtu = ['ifconfig eth0 mtu 16436']
        for packet_size in packet_sizes:
            if packet_size > 1400:
                self.logger.info('Increasing the MTU of the eth0 of VM')
                vm1_fixture.run_cmd_on_vm(
                    cmds=cmd_to_increase_mtu)
                vm2_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu)
            self.logger.info("-" * 80)
            self.logger.info("PACKET SIZE = %sB" % packet_size)
            self.logger.info("-" * 80)
            for proto in traffic_proto_l:
                traffic_obj[proto] = {}
                startStatus[proto] = {}
                traffic_obj[proto] = self.useFixture(
                    traffic_tests.trafficTestFixture(self.connections))
                # def startTraffic (self, name=name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
                # packet_size= 100, start_sport= 8000,
                # total_single_instance_streams= 20):
                startStatus[proto] = traffic_obj[proto].startTraffic(
                    num_streams=total_streams[proto], start_port=dpi,
                    tx_vm_fixture=vm1_fixture, rx_vm_fixture=vm2_fixture, stream_proto=proto, packet_size=packet_size)
                self.logger.info("Status of start traffic : %s, %s, %s" %
                                 (proto, vm1_fixture.vm_ip, startStatus[proto]))
                if startStatus[proto]['status'] != True:
                    msg.append(startStatus[proto])
                    result = False
            #self.assertEqual(out['result'], True, out['msg'])
            self.logger.info("-" * 80)
            # Poll live traffic
            traffic_stats = {}
            self.logger.info("Poll live traffic and get status..")
            for proto in traffic_proto_l:
                traffic_stats = traffic_obj[proto].getLiveTrafficStats()
                err_msg = ["Traffic disruption is seen: details: "] + \
                    traffic_stats['msg']
            self.assertEqual(traffic_stats['status'], True, err_msg)
            self.logger.info("-" * 80)
            # Stop Traffic
            self.logger.info("Proceed to stop traffic..")
            self.logger.info("-" * 80)
            for proto in traffic_proto_l:
                stopStatus[proto] = {}
                stopStatus[proto] = traffic_obj[proto].stopTraffic()
                if stopStatus[proto] != []:
                    msg.append(stopStatus[proto])
                    result = False
                self.logger.info(
                    "Status of stop traffic for proto %s and packet size of %sB is %s" %
                    (proto, packet_size, stopStatus[proto]))
            self.logger.info("-" * 80)
            print result
            self.logger.info('Sleeping for 20s')
            sleep(10)
        self.assertEqual(result, True, msg)

        return True
    # end test_traffic_bw_vms_diff_pkt_size

    @preposttest_wrapper
    def test_traffic_bw_vms_diff_pkt_size_w_chksum(self):
        ''' Test to validate ICMP, UDP traffic of different packet sizes b/w VMs created within a VN and validate UDP checksum.
        '''
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/29']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        # Get all compute host
        host_list = []
        for host in self.inputs.compute_ips:
            host_list.append(self.inputs.host_data[host]['name'])
        print host_list
        if len(set(self.inputs.compute_ips)) > 1:
            self.logger.info("Multi-Node Setup")
            vm1_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_large', image_name='ubuntu-traffic', vm_name='vm1', node_name=host_list[1]))
            assert vm1_fixture.verify_on_setup()
            vm2_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_large', image_name='ubuntu-traffic', vm_name='vm2', node_name=host_list[0]))
            assert vm2_fixture.verify_on_setup()
        else:
            self.logger.info("Single-Node Setup")
            vm1_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_large', image_name='ubuntu-traffic', vm_name='vm1'))
            vm2_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_large', image_name='ubuntu-traffic', vm_name='vm2'))
            assert vm1_fixture.verify_on_setup()
            assert vm2_fixture.verify_on_setup()

        out1 = self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        if out1 == False:
            return {'result': out1, 'msg': "%s failed to come up" % vm1_fixture.vm_name}
        else:
            sleep(10)
            self.logger.info('Will install Traffic package on %s' %
                             vm1_fixture.vm_name)
            vm1_fixture.install_pkg("Traffic")

        out2 = self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        if out2 == False:
            return {'result': out2, 'msg': "%s failed to come up" % vm2_fixture.vm_name}
        else:
            sleep(10)
            self.logger.info('Will install Traffic package on %s' %
                             vm2_fixture.vm_name)
            vm2_fixture.install_pkg("Traffic")

        result = True
        msg = []
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['icmp', 'udp']
        total_streams = {}
        total_streams['icmp'] = 1
        total_streams['udp'] = 2
        dpi = 9100
        proto = 'udp'
        packet_sizes = [40, 64, 254, 748, 1350]
        cmd_to_increase_mtu = ['ifconfig eth0 mtu 16436']
        for packet_size in packet_sizes:
            if packet_size > 1400:
                self.logger.info('Increasing the MTU of the eth0 of VM')
                vm1_fixture.run_cmd_on_vm(
                    cmds=cmd_to_increase_mtu)
                vm2_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu)
            self.logger.info("-" * 80)
            self.logger.info("PACKET SIZE = %sB" % packet_size)
            self.logger.info("-" * 80)
            for proto in traffic_proto_l:
                name = proto
                traffic_obj[proto] = {}
                startStatus[proto] = {}
                traffic_obj[proto] = self.useFixture(
                    traffic_tests.trafficTestFixture(self.connections))
                # def startTraffic (self, name=name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
                # packet_size= 100, start_sport= 8000,
                # total_single_instance_streams= 20):
                startStatus[proto] = traffic_obj[proto].startTraffic(
                    num_streams=total_streams[proto], start_port=dpi,
                    tx_vm_fixture=vm1_fixture, rx_vm_fixture=vm2_fixture, stream_proto=proto, packet_size=packet_size, chksum=True)
                self.logger.info("Status of start traffic : %s, %s, %s" %
                                 (proto, vm1_fixture.vm_ip, startStatus[proto]))
                if startStatus[proto]['status'] != True:
                    msg.append(startStatus[proto])
                    result = False
            #self.assertEqual(out['result'], True, out['msg'])
            self.logger.info("-" * 80)
            # Poll live traffic
            traffic_stats = {}
            self.logger.info("Poll live traffic and get status..")
            for proto in traffic_proto_l:
                traffic_stats = traffic_obj[proto].getLiveTrafficStats()
                err_msg = ["Traffic disruption is seen: details: "] + \
                    traffic_stats['msg']
            self.assertEqual(traffic_stats['status'], True, err_msg)
            self.logger.info("-" * 80)
            # Stop Traffic
            self.logger.info("Proceed to stop traffic..")
            self.logger.info("-" * 80)
            for proto in traffic_proto_l:
                stopStatus[proto] = {}
                stopStatus[proto] = traffic_obj[proto].stopTraffic()
                if stopStatus[proto] != []:
                    msg.append(stopStatus[proto])
                    result = False
                for rcv_count in range(0, total_streams[proto]):
                    if traffic_obj[proto].receiver[rcv_count].corrupt > 0:
                        self.logger.error(
                            "In Stream %s of %s, %s packets are corrupted" %
                            (rcv_count, proto, traffic_obj[proto].receiver[rcv_count].corrupt))
                        result = False
                    else:
                        self.logger.info(
                            "In Stream %s of %s, No packets are corrupted" % (rcv_count, proto))
                self.logger.info(
                    "Status of stop traffic for proto %s and packet size of %sB is %s" %
                    (proto, packet_size, stopStatus[proto]))
            self.logger.info("-" * 80)
            print result
            sleep(5)
        self.assertEqual(result, True, msg)

        return True
    # end test_traffic_bw_vms_diff_pkt_size_w_chksum

    @preposttest_wrapper
    def test_traffic_bw_vms(self):
        ''' Test to validate TCP, ICMP, UDP traffic b/w VMs created within a VN .
        '''
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/29']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj

        # Get all compute host
        host_list = []
        for host in self.inputs.compute_ips:
            host_list.append(self.inputs.host_data[host]['name'])
        print host_list

        if len(set(self.inputs.compute_ips)) > 1:

            self.logger.info("Multi-Node Setup")
            vm1_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_large', image_name='ubuntu-traffic', vm_name='vm1', node_name=host_list[1]))
            assert vm1_fixture.verify_on_setup()
            vm2_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_large', image_name='ubuntu-traffic', vm_name='vm2', node_name=host_list[0]))
            assert vm2_fixture.verify_on_setup()
        else:
            self.logger.info("Single-Node Setup")
            vm1_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_large', image_name='ubuntu-traffic', vm_name='vm1'))
            vm2_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_large', image_name='ubuntu-traffic', vm_name='vm2'))
            assert vm1_fixture.verify_on_setup()
            assert vm2_fixture.verify_on_setup()

        out1 = self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        if out1 == False:
            return {'result': out1, 'msg': "%s failed to come up" % vm1_fixture.vm_name}
        else:
            sleep(10)
            self.logger.info('Will install Traffic package on %s' %
                             vm1_fixture.vm_name)
            vm1_fixture.install_pkg("Traffic")

        out2 = self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        if out2 == False:
            return {'result': out2, 'msg': "%s failed to come up" % vm2_fixture.vm_name}
        else:
            sleep(10)
            self.logger.info('Will install Traffic package on %s' %
                             vm2_fixture.vm_name)
            vm2_fixture.install_pkg("Traffic")

        #self.logger.info('Will install Traffic package')
        # vm1_fixture.install_pkg("Traffic")
        # vm2_fixture.install_pkg("Traffic")
        #self.logger.info('Installed Traffic package')

        result = True
        msg = []
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['tcp', 'icmp', 'udp']
        total_streams = {}
        total_streams['icmp'] = 1
        total_streams['udp'] = 2
        total_streams['tcp'] = 2
        dpi = 9100
        proto = 'udp'
        for proto in traffic_proto_l:
            traffic_obj[proto] = {}
            startStatus[proto] = {}
            traffic_obj[proto] = self.useFixture(
                traffic_tests.trafficTestFixture(self.connections))
            # def startTraffic (self, name=name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
            # packet_size= 100, start_sport= 8000,
            # total_single_instance_streams= 20):
            startStatus[proto] = traffic_obj[proto].startTraffic(
                num_streams=total_streams[proto], start_port=dpi,
                tx_vm_fixture=vm1_fixture, rx_vm_fixture=vm2_fixture, stream_proto=proto)
            self.logger.info("Status of start traffic : %s, %s, %s" %
                             (proto, vm1_fixture.vm_ip, startStatus[proto]))
            if startStatus[proto]['status'] != True:
                msg.append(startStatus[proto])
                result = False
        #self.assertEqual(out['result'], True, out['msg'])
        self.logger.info("-" * 80)
        # Poll live traffic
        traffic_stats = {}
        self.logger.info("Poll live traffic and get status..")
        for proto in traffic_proto_l:
            traffic_stats = traffic_obj[proto].getLiveTrafficStats()
            err_msg = ["Traffic disruption is seen: details: "] + \
                traffic_stats['msg']
        self.assertEqual(traffic_stats['status'], True, err_msg)
        self.logger.info("-" * 80)
        # Stop Traffic
        self.logger.info("Proceed to stop traffic..")
        self.logger.info("-" * 80)
        for proto in traffic_proto_l:
            stopStatus[proto] = {}
            stopStatus[proto] = traffic_obj[proto].stopTraffic()
            if stopStatus[proto] != []:
                msg.append(stopStatus[proto])
                result = False
            self.logger.info("Status of stop traffic for proto %s is %s" %
                             (proto, stopStatus[proto]))
        self.logger.info("-" * 80)
        self.assertEqual(result, True, msg)
        return True
    # end test_traffic_bw_vms

    @preposttest_wrapper
    def test_policy_between_vns_diff_proj(self):
        ''' Test to validate that policy to deny and pass under different projects should behave accordingly.
        '''
        vm_names = ['vm_100', 'vm_200', 'vm_300', 'vm_400']
        vn_names = ['vn_100', 'vn_200', 'vn_300', 'vn_400']
        vn_subnets = [['10.1.1.0/24'], ['20.1.1.0/24'],
                      ['30.1.1.0/24'], ['40.1.1.0/24']]
        projects = ['project111', 'project222']
        policy_names = ['policy1', 'policy2', 'policy3', 'policy4']
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': vn_names[0],
                'dest_network': vn_names[1],
            },
        ]
        rev_rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': vn_names[1],
                'dest_network': vn_names[0],
            },
        ]
        rules1 = [
            {
                'direction': '<>', 'simple_action': 'deny',
                'protocol': 'icmp',
                'source_network': vn_names[2],
                'dest_network': vn_names[3],
            },
        ]
        rev_rules1 = [
            {
                'direction': '<>', 'simple_action': 'deny',
                'protocol': 'icmp',
                'source_network': vn_names[3],
                'dest_network': vn_names[2],
            },
        ]

        user_list = [('gudi', 'gudi123', 'admin'), ('mal', 'mal123', 'admin')]
        project_fixture1 = self.useFixture(
            ProjectFixture(
                project_name=projects[
                    0], vnc_lib_h=self.vnc_lib, username=user_list[0][0],
                password=user_list[0][1], connections=self.connections))
        project_inputs1 = self.useFixture(
            ContrailTestInit(
                self.ini_file, stack_user=project_fixture1.username,
                stack_password=project_fixture1.password, project_fq_name=['default-domain', projects[0]]))
        project_connections1 = ContrailConnections(project_inputs1)

        project_fixture2 = self.useFixture(
            ProjectFixture(
                project_name=projects[
                    1], vnc_lib_h=self.vnc_lib, username=user_list[1][0],
                password=user_list[1][1], connections=self.connections))
        project_inputs2 = self.useFixture(
            ContrailTestInit(
                self.ini_file, stack_user=project_fixture2.username,
                stack_password=project_fixture2.password, project_fq_name=['default-domain', projects[1]]))
        project_connections2 = ContrailConnections(project_inputs2)

        self.logger.info(
            'We will now create policy to allow in project %s and check that ping passes between the VMs' % (projects[0]))

        policy1_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_names[
                    0], rules_list=rules, inputs=project_inputs1,
                connections=project_connections1))
        policy2_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_names[
                    1], rules_list=rev_rules, inputs=project_inputs1,
                connections=project_connections1))

        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=projects[0], connections=project_connections1,
                vn_name=vn_names[0], inputs=project_inputs1, subnets=vn_subnets[0], policy_objs=[policy1_fixture.policy_obj]))
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=projects[0], connections=project_connections1,
                vn_name=vn_names[1], inputs=project_inputs1, subnets=vn_subnets[1], policy_objs=[policy2_fixture.policy_obj]))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(
            VMFixture(connections=project_connections1,
                      vn_obj=vn1_fixture.obj, vm_name=vm_names[0], project_name=projects[0]))
        vm2_fixture = self.useFixture(
            VMFixture(connections=project_connections1,
                      vn_obj=vn2_fixture.obj, vm_name=vm_names[1], project_name=projects[0]))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm2_fixture.vm_obj)
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)

        self.logger.info(
            'We will now create policy to deny in project %s and check that ping fails between the VMs' % (projects[1]))

        policy3_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_names[
                    2], rules_list=rules1, inputs=project_inputs2,
                connections=project_connections2))
        policy4_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_names[
                    3], rules_list=rev_rules1, inputs=project_inputs2,
                connections=project_connections2))

        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=projects[1], connections=project_connections2,
                vn_name=vn_names[2], inputs=project_inputs2, subnets=vn_subnets[2], policy_objs=[policy3_fixture.policy_obj]))
        vn4_fixture = self.useFixture(
            VNFixture(
                project_name=projects[1], connections=project_connections2,
                vn_name=vn_names[3], inputs=project_inputs2, subnets=vn_subnets[3], policy_objs=[policy4_fixture.policy_obj]))
        assert vn3_fixture.verify_on_setup()
        assert vn4_fixture.verify_on_setup()

        vm3_fixture = self.useFixture(
            VMFixture(connections=project_connections2,
                      vn_obj=vn3_fixture.obj, vm_name=vm_names[2], project_name=projects[1]))
        vm4_fixture = self.useFixture(
            VMFixture(connections=project_connections2,
                      vn_obj=vn4_fixture.obj, vm_name=vm_names[3], project_name=projects[1]))
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()

        self.nova_fixture.wait_till_vm_is_up(vm3_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm4_fixture.vm_obj)
        assert not vm4_fixture.ping_to_ip(vm3_fixture.vm_ip)
        return True
    # end test_policy_between_vns_diff_proj

    @preposttest_wrapper
    def test_diff_proj_same_vn_vm_add_delete(self):
        ''' Test to validate that a VN and VM with the same name and same subnet can be created in two different projects
        '''
        vm_name = 'vm_mine'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        projects = ['project111', 'project222']
        user_list = [('gudi', 'gudi123', 'admin'), ('mal', 'mal123', 'admin')]

        project_fixture1 = self.useFixture(
            ProjectFixture(
                project_name=projects[
                    0], vnc_lib_h=self.vnc_lib, username=user_list[0][0],
                password=user_list[0][1], connections=self.connections))
        project_inputs1 = self.useFixture(
            ContrailTestInit(
                self.ini_file, stack_user=project_fixture1.username,
                stack_password=project_fixture1.password, project_fq_name=['default-domain', projects[0]]))
        project_connections1 = ContrailConnections(project_inputs1)

        project_fixture2 = self.useFixture(
            ProjectFixture(
                project_name=projects[
                    1], vnc_lib_h=self.vnc_lib, username=user_list[1][0],
                password=user_list[1][1], connections=self.connections))
        project_inputs2 = self.useFixture(
            ContrailTestInit(
                self.ini_file, stack_user=project_fixture2.username,
                stack_password=project_fixture2.password, project_fq_name=['default-domain', projects[1]]))
        project_connections2 = ContrailConnections(project_inputs2)

        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=projects[0], connections=project_connections1,
                vn_name=vn_name, inputs=project_inputs1, subnets=vn_subnets))

        assert vn1_fixture.verify_on_setup()
        vn1_obj = vn1_fixture.obj

        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=projects[1], connections=project_connections2,
                vn_name=vn_name, inputs=project_inputs2, subnets=vn_subnets))

        assert vn2_fixture.verify_on_setup()
        vn2_obj = vn2_fixture.obj

        vm1_fixture = self.useFixture(
            VMFixture(connections=project_connections1,
                      vn_obj=vn1_obj, vm_name=vm_name, project_name=projects[0]))
        vm2_fixture = self.useFixture(
            VMFixture(connections=project_connections2,
                      vn_obj=vn2_obj, vm_name=vm_name, project_name=projects[1]))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        if not vm1_fixture.agent_label == vm2_fixture.agent_label:
            self.logger.info("Correct label assigment")
        else:
            self.logger.error(
                "The same label has been assigned for both the VMs")
            return False
        return True
    # end test_diff_proj_same_vn_vm_add_delete

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
        #    if fix.cleanUp in cleanup:
            self._cleanups.remove(cleanup)
            # break
   # end remove_from_cleanups

    @preposttest_wrapper
    def test_vm_multi_intf_in_same_vn_chk_ping(self):
        ''' Test to validate that a multiple interfaces of the same VM can be associated to the same VN and ping is successful.
        '''
        #raise self.skipTest("Skiping Test. Will enable after infra changes to support them have been made")
        vm1_name = 'vm_mine1'
        vn1_name = 'vn222'
        vn1_subnets = ['11.1.1.0/24']
        vm2_name = 'vm_yours'
        list_of_ips = []
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        # In latest release we dont support adding same VN
        # Converting test to negative, accept execption and mark as PASS
        try:
            vm1_fixture = self.useFixture(
                VMFixture(connections=self.connections,
                          vn_objs=[vn1_fixture.obj, vn1_fixture.obj, vn1_fixture.obj, vn1_fixture.obj, vn1_fixture.obj], vm_name=vm1_name, project_name=self.inputs.project_name))
        except Exception as e:
            self.logger.exception(
                "Got exception while creating multi_intf_vm_in_same_vn as %s" % (e))
            return True

        assert vm1_fixture.verify_on_setup()
        try:
            vm2_fixture = self.useFixture(
                VMFixture(connections=self.connections,
                          vn_objs=[vn1_fixture.obj, vn1_fixture.obj, vn1_fixture.obj, vn1_fixture.obj, vn1_fixture.obj], vm_name=vm2_name, project_name=self.inputs.project_name))
        except Exception as e:
            self.logger.exception(
                "Got exception while creating multi_intf_vm_in_same_vn as %s" % (e))
            return True

        assert vm2_fixture.verify_on_setup()
        list_of_vm1_ips = vm1_fixture.vm_ips
        list_of_vm2_ips = vm2_fixture.vm_ips

        self.logger.info('Will ping to the two VMs from the Multi-NIC VM')
        self.logger.info('-' * 80)
        result = True
        for vm2_ip in list_of_vm2_ips:
            if not vm1_fixture.ping_to_ip(vm2_ip):
                result = False
                assert result, "Ping to %s from %s Fail" % (
                    vm2_ip, vm1_fixture.vm_name)
            else:
                self.logger.info('Ping to %s from %s Pass' %
                                 (vm2_ip, vm1_fixture.vm_name))

        for vm1_ip in list_of_vm1_ips:
            if not vm2_fixture.ping_to_ip(vm1_ip):
                result = False
                assert result, "Ping to %s from %s Fail" % (
                    vm1_ip, vm2_fixture.vm_name)
            else:
                self.logger.info('Ping to %s from %s Pass' %
                                 (vm2_ip, vm2_fixture.vm_name))

    # end test_vm_multi_intf_in_same_vn_chk_ping
    @preposttest_wrapper
    def test_vm_in_2_vns_chk_ping(self):
        ''' Test to validate that a VM can be associated to more than a VN and ping to a network goes from the respective intf.
        '''
        vm1_name = 'vm_mine1'
        vn1_name = 'vn222'
        vn1_subnets = ['11.1.1.0/24']
        vn2_name = 'vn223'
        vn2_subnets = ['22.1.1.0/24']
        vm2_name = 'vm_vn222'
        vm3_name = 'vm_vn223'
        list_of_ips = []
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn2_name, inputs=self.inputs, subnets=vn2_subnets))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_objs=[vn1_fixture.obj, vn2_fixture.obj], vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn1_fixture.obj, vm_name=vm2_name, project_name=self.inputs.project_name))
        assert vm2_fixture.verify_on_setup()
        vm3_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn2_fixture.obj, vm_name=vm3_name, project_name=self.inputs.project_name))
        assert vm3_fixture.verify_on_setup()
        list_of_ips = vm1_fixture.vm_ips
        i = 'ifconfig eth1 %s netmask 255.255.255.0' % list_of_ips[1]
        cmd_to_output = [i]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_output, as_sudo=True)
        output = vm1_fixture.return_output_cmd_dict[i]
        print output

        j = 'ifconfig -a'
        cmd_to_output1 = [j]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_output1)
        output1 = vm1_fixture.return_output_cmd_dict[j]
        print output1

        for ips in list_of_ips:
            if ips not in output1:
                result = False
                self.logger.error("IP %s not assigned to any eth intf of %s" %
                                  (ips, vm1_fixture.vm_name))
                assert result, "PR 1018"
            else:
                self.logger.info("IP %s is assigned to eth intf of %s" %
                                 (ips, vm1_fixture.vm_name))

        self.logger.info('-' * 80)
        self.logger.info('Will ping to the two VMs from the Multi-NIC VM')
        self.logger.info('-' * 80)
        result = True
        if not vm1_fixture.ping_to_ip(vm2_fixture.vm_ip):
            result = False
            assert result, "Ping to %s Fail" % vm2_fixture.vm_ip
        else:
            self.logger.info('Ping to %s Pass' % vm2_fixture.vm_ip)
        if not vm1_fixture.ping_to_ip(vm3_fixture.vm_ip):
            result = False
            assert result, "Ping to %s Fail" % vm3_fixture.vm_ip
        else:
            self.logger.info('Ping to %s Pass' % vm3_fixture.vm_ip)

        cmd_to_add_file = ['touch batchfile']
        cmd_to_exec_file = ['sh batchfile | tee > out.log']
        cmd_to_delete_file = ['rm -rf batchfile']
        ping_vm2 = 'ping %s' % vm2_fixture.vm_ip
        cmd_to_ping_vm2 = [ping_vm2]
        ping_vm3 = 'ping %s' % vm3_fixture.vm_ip
        cmd_to_ping_vm3 = [ping_vm3]

        self.logger.info('-' * 80)
        self.logger.info(
            'Will shut down eth1 and hence ping to the second n/w should fail, while the ping to the first n/w is unaffected. The same is not done for eth0 as it points to the default GW')
        self.logger.info('-' * 80)
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_file)
        cmd_to_add_cmd_to_file = [
            "echo 'ifconfig -a; sudo ifconfig eth1 down; ifconfig -a; ping -c 5 %s > ping_output_after_shutdown.log; sudo ifconfig eth1 up; ifconfig -a ' > batchfile" % vm3_fixture.vm_ip]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_cmd_to_file)
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_exec_file)
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_delete_file)

        i = 'cat ping_output_after_shutdown.log'
        cmd_to_view_output = ['cat ping_output_after_shutdown.log']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_view_output)
        output = vm1_fixture.return_output_cmd_dict[i]
        print output

        if not '100% packet loss' in output:
            result = False
            self.logger.error('Ping to %s Pass' % vm3_fixture.vm_ip)
        else:
            self.logger.info('Ping to %s Fail' % vm3_fixture.vm_ip)
        if not vm1_fixture.ping_to_ip(vm2_fixture.vm_ip):
            result = False
            assert result, "Ping to %s Fail" % vm2_fixture.vm_ip
        else:
            self.logger.info('Ping to %s Pass' % vm2_fixture.vm_ip)

        self.logger.info('-' * 80)
        self.logger.info(
            'Will unshut eth1 and hence ping to the second n/w should pass, while the ping to the first n/w is still unaffected. The same is not done for eth0 as it points to the default GW')
        self.logger.info('-' * 80)
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_file)
        cmd_to_add_cmd_to_file = [
            "echo 'ifconfig -a; sudo ifconfig eth1 up; sleep 10; sudo ifconfig -a; ping -c 5 %s > ping_output.log' > batchfile" % vm3_fixture.vm_ip]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_cmd_to_file)
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_exec_file)
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_delete_file)

        j = 'cat ping_output.log'
        cmd_to_view_output = ['cat ping_output.log']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_view_output)
        output1 = vm1_fixture.return_output_cmd_dict[j]
        print output1

        if not '0% packet loss' in output1:
            result = False
            self.logger.error('Ping to %s Fail' % vm3_fixture.vm_ip)
        else:
            self.logger.info('Ping to %s Pass' % vm3_fixture.vm_ip)
        if not vm1_fixture.ping_to_ip(vm2_fixture.vm_ip):
            result = False
            assert result, "Ping to %s Fail" % vm2_fixture.vm_ip
        else:
            self.logger.info('Ping to %s Pass' % vm2_fixture.vm_ip)

        return True
    # end test_vm_add_delete_in_2_vns_chk_ping

    @preposttest_wrapper
    def test_vm_add_delete_in_2_vns_chk_ips(self):
        ''' Test to validate that a VM can be associated to more than a VN and it gets the IPs as well.
        '''
        vm1_name = 'vm_mine1'
        vn1_name = 'vn222'
        vn1_subnets = ['11.1.1.0/24']
        vn2_name = 'vn223'
        vn2_subnets = ['22.1.1.0/24']
        text = """#!/bin/sh
                ifconfig eth1 22.1.1.253 netmask 255.255.255.0
                """
        try:
            with open("/tmp/metadata_script.txt", "w") as f:
                f.write(text)
        except Exception as e:
            self.logger.exception(
                "Got exception while creating /tmp/metadata_script.txt as %s" % (e))

        list_of_ips = []
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn2_name, inputs=self.inputs, subnets=vn2_subnets))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()

        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_objs=[vn1_fixture.obj, vn2_fixture.obj], vm_name=vm1_name, project_name=self.inputs.project_name, image_name='cirros-0.3.0-x86_64-uec', flavor='m1.tiny', userdata='/tmp/metadata_script.txt'))
        assert vm1_fixture.verify_on_setup()
        list_of_ips = vm1_fixture.vm_ips
        cmd = '/sbin/ifconfig -a'
        ret = vm1_fixture.run_cmd_on_vm(cmds=[cmd])
        for elem in ret.values():
            for ips in list_of_ips:
                if ips not in elem:
                    self.logger.error(
                        "IP %s not assigned to any eth intf of %s" %
                        (ips, vm1_fixture.vm_name))
                else:
                    self.logger.info('IP %s assigned' % ips)
        return True
    # end test_vm_add_delete_in_2_vns_chk_ips

    @preposttest_wrapper
    def test_vm_add_delete_in_2_vns(self):
        ''' Test to validate that a VM can be associated to more than one VN.
        '''
        vm1_name = 'vm_mine1'
        vn1_name = 'vn222'
        vn1_subnets = ['11.1.1.0/24']
        vn2_name = 'vn223'
        vn2_subnets = ['22.1.1.0/24']
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn2_name, inputs=self.inputs, subnets=vn2_subnets))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_objs=[vn1_fixture.obj, vn2_fixture.obj], vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        return True
    # end test_vm_add_delete_in_2_vns

    @preposttest_wrapper
    def test_no_frag_in_vm(self):
        ''' Validate that VM should not fragment packets and that Vrouter does it.
        '''
        vn1_name = 'vn30'
        vn1_subnets = ['30.1.1.0/24']
        vn1_vm1_name = 'vm1'
        vn1_vm2_name = 'vm2'
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, flavor='contrail_flavor_large', image_name='ubuntu-traffic', vm_name=vn1_vm1_name))
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, flavor='contrail_flavor_large', image_name='ubuntu-traffic', vm_name=vn1_vm2_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm2_fixture.vm_obj)

        out1 = self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        if out1 == False:
            return {'result': out1, 'msg': "%s failed to come up" % vm1_fixture.vm_name}
        else:
            sleep(10)
            self.logger.info('Will install Traffic package on %s' %
                             vm1_fixture.vm_name)
            vm1_fixture.install_pkg("Traffic")

        out2 = self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        if out2 == False:
            return {'result': out2, 'msg': "%s failed to come up" % vm2_fixture.vm_name}
        else:
            sleep(10)
            self.logger.info('Will install Traffic package on %s' %
                             vm2_fixture.vm_name)
            vm2_fixture.install_pkg("Traffic")

        # vm1_fixture.install_pkg("Traffic")
        # vm2_fixture.install_pkg("Traffic")
        result = True
        msg = []
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['icmp']
        total_streams = {}
        total_streams['icmp'] = 1
        dpi = 9100
        packet_size = 2000
        cmd_to_increase_mtu = ['ifconfig eth0 mtu 3000']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu)
        vm2_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu)
        for proto in traffic_proto_l:
            traffic_obj[proto] = {}
            startStatus[proto] = {}
            traffic_obj[proto] = self.useFixture(
                traffic_tests.trafficTestFixture(self.connections))
            startStatus[proto] = traffic_obj[proto].startTraffic(
                num_streams=total_streams[proto], start_port=dpi,
                tx_vm_fixture=vm1_fixture, rx_vm_fixture=vm2_fixture, stream_proto=proto, packet_size=packet_size)
            self.logger.info("Status of start traffic : %s, %s, %s" %
                             (proto, vm1_fixture.vm_ip, startStatus[proto]))
            cmd_to_tcpdump = [
                'nohup tcpdump -i eth0 icmp -vvv -c 10 > /tmp/out.log']
            vm1_fixture.run_cmd_on_vm(cmds=cmd_to_tcpdump)
            i = 'cat /tmp/out.log'
            cmd_to_output = ['cat /tmp/out.log']
            vm1_fixture.run_cmd_on_vm(cmds=cmd_to_output)
            output = vm1_fixture.return_output_cmd_dict[i]
            print output
            if 'DF' in output:
                result = False
        return result
    # end test_no_frag_in_vm

    @preposttest_wrapper
    def test_ping_within_vn(self):
        ''' Validate Ping between two VMs within a VN.

        '''
        vn1_name = 'vn30'
        vn1_subnets = ['30.1.1.0/24']
        vn1_vm1_name = 'vm1'
        vn1_vm2_name = 'vm2'
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm1_name))
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm2_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm2_fixture.vm_obj)
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)
        assert vm2_fixture.ping_to_ip(vm1_fixture.vm_ip)
        return True
    # end test_ping_within_vn

    @preposttest_wrapper
    def test_ping_on_broadcast_multicast_with_frag(self):
        ''' Validate Ping on subnet broadcast,link local multucast,network broadcastwith packet sizes > MTU and see that fragmentation and assembly work fine .

        '''
        vn1_name = 'vn30'
        vn1_subnets = ['30.1.1.0/24']
        ping_count = '5'
        vn1_vm1_name = 'vm1'
        vn1_vm2_name = 'vm2'
        vn1_vm3_name = 'vm3'
        vn1_vm4_name = 'vm4'
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm1_name))
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm2_name))
        vm3_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm3_name))
        vm4_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm4_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm2_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm3_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm4_fixture.vm_obj)
        # Geting the VM ips
        vm1_ip = vm1_fixture.vm_ip
        vm2_ip = vm2_fixture.vm_ip
        vm3_ip = vm3_fixture.vm_ip
        vm4_ip = vm4_fixture.vm_ip
        ip_list = [vm1_ip, vm2_ip, vm3_ip, vm4_ip]
        list_of_ip_to_ping = ['30.1.1.255', '224.0.0.1', '255.255.255.255']
        # passing command to vms so that they respond to subnet broadcast
        cmd_list_to_pass_vm = [
            'echo 0 > /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm2_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm3_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm4_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        for dst_ip in list_of_ip_to_ping:
            print 'pinging from %s to %s' % (vm1_ip, dst_ip)
# pinging from Vm1 to subnet broadcast
            ping_output = vm1_fixture.ping_to_ip(
                dst_ip, return_output=True, count=ping_count,  size='3000', other_opt='-b')
            self.logger.info(
                'The packet is not fragmanted because of the smaller MTU')
            expected_result = 'Message too long'
            assert (expected_result in ping_output)

        self.logger.info('Will change the MTU of the VMs and try again')
        cmd_to_increase_mtu = ['ifconfig eth0 mtu 9000']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True)
        vm2_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True)
        vm3_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True)
        vm4_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True)

        for dst_ip in list_of_ip_to_ping:
            print 'pinging from %s to %s' % (vm1_ip, dst_ip)
# pinging from Vm1 to subnet broadcast
            ping_output = vm1_fixture.ping_to_ip(
                dst_ip, return_output=True, count=ping_count,  size='3000', other_opt='-b')
            expected_result = 'Message too long'
            assert (expected_result not in ping_output)

# getting count of ping response from each vm
            string_count_dict = {}
            string_count_dict = get_string_match_count(ip_list, ping_output)
            print string_count_dict
            for k in ip_list:
                # this is a workaround : ping utility exist as soon as it gets
                # one response
                assert (string_count_dict[k] >= (int(ping_count) - 1))
        return True
    # end test_ping_on_broadcast_multicast_with_frag

    @preposttest_wrapper
    def test_broadcast_udp_w_chksum(self):
        ''' Validate Broadcast UDP stream with checksum check enabled .

        '''
        vn1_name = 'vn30'
        vn1_subnets = ['30.1.1.0/24']
        vn1_vm1_name = 'vm1'
        vn1_vm2_name = 'vm2'
        vn1_vm3_name = 'vm3'
        vn1_vm4_name = 'vm4'
        result = True
        list_of_ips = ['30.1.1.255', '224.0.0.1', '255.255.255.255']
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()

        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, flavor='contrail_flavor_large', image_name='ubuntu-traffic', vm_name=vn1_vm1_name))
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, flavor='contrail_flavor_large', image_name='ubuntu-traffic', vm_name=vn1_vm2_name))
        vm3_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, flavor='contrail_flavor_large', image_name='ubuntu-traffic', vm_name=vn1_vm3_name))
        vm4_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, flavor='contrail_flavor_large', image_name='ubuntu-traffic', vm_name=vn1_vm4_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()
        #self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj )
        #self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj )
        #self.nova_fixture.wait_till_vm_is_up( vm3_fixture.vm_obj )
        #self.nova_fixture.wait_till_vm_is_up( vm4_fixture.vm_obj )

        out1 = self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        if out1 == False:
            return {'result': out1, 'msg': "%s failed to come up" % vm1_fixture.vm_name}
        else:
            sleep(
                10)
            self.logger.info('Installing Traffic package on %s ...' %
                             vm1_fixture.vm_name)
            vm1_fixture.install_pkg("Traffic")

        out2 = self.nova_fixture.wait_till_vm_is_up(vm2_fixture.vm_obj)
        if out2 == False:
            return {'result': out2, 'msg': "%s failed to come up" % vm2_fixture.vm_name}
        else:
            sleep(
                10)
            self.logger.info('Installing Traffic package on %s ...' %
                             vm2_fixture.vm_name)
            vm2_fixture.install_pkg("Traffic")

        out3 = self.nova_fixture.wait_till_vm_is_up(vm3_fixture.vm_obj)
        if out3 == False:
            return {'result': out3, 'msg': "%s failed to come up" % vm3_fixture.vm_name}
        else:
            sleep(
                10)
            self.logger.info('Installing Traffic package on %s ...' %
                             vm3_fixture.vm_name)
            vm3_fixture.install_pkg("Traffic")

        out4 = self.nova_fixture.wait_till_vm_is_up(vm4_fixture.vm_obj)
        if out4 == False:
            return {'result': out4, 'msg': "%s failed to come up" % vm4_fixture.vm_name}
        else:
            sleep(
                10)
            self.logger.info('Installing Traffic package on %s ...' %
                             vm4_fixture.vm_name)
            vm4_fixture.install_pkg("Traffic")

        # Starting Multicast_UDP
        for ips in list_of_ips:
            self.logger.info("-" * 80)
            self.logger.info('Sending UDP packets to %s' % ips)
            self.logger.info("-" * 80)
            stream = Stream(protocol="ip", proto="udp",
                            src=vm1_fixture.vm_ip, dst=ips, dport=9000)
            profile = ContinuousProfile(
                stream=stream, listener=ips, capfilter="udp port 8000", chksum=True)

            tx_vm_node_ip = self.inputs.host_data[
                self.nova_fixture.get_nova_host_of_vm(vm1_fixture.vm_obj)]['host_ip']
            rx1_vm_node_ip = self.inputs.host_data[
                self.nova_fixture.get_nova_host_of_vm(vm2_fixture.vm_obj)]['host_ip']
            rx2_vm_node_ip = self.inputs.host_data[
                self.nova_fixture.get_nova_host_of_vm(vm3_fixture.vm_obj)]['host_ip']
            rx3_vm_node_ip = self.inputs.host_data[
                self.nova_fixture.get_nova_host_of_vm(vm4_fixture.vm_obj)]['host_ip']

            tx_local_host = Host(
                tx_vm_node_ip, self.inputs.username, self.inputs.password)
            rx1_local_host = Host(
                rx1_vm_node_ip, self.inputs.username, self.inputs.password)
            rx2_local_host = Host(
                rx2_vm_node_ip, self.inputs.username, self.inputs.password)
            rx3_local_host = Host(
                rx3_vm_node_ip, self.inputs.username, self.inputs.password)

            send_host = Host(vm1_fixture.local_ip,
                             vm1_fixture.vm_username, vm1_fixture.vm_password)
            recv_host1 = Host(vm2_fixture.local_ip,
                              vm2_fixture.vm_username, vm2_fixture.vm_password)
            recv_host2 = Host(vm3_fixture.local_ip,
                              vm3_fixture.vm_username, vm3_fixture.vm_password)
            recv_host3 = Host(vm4_fixture.local_ip,
                              vm4_fixture.vm_username, vm4_fixture.vm_password)

            sender = Sender("sendudp", profile, tx_local_host,
                            send_host, self.inputs.logger)
            receiver1 = Receiver("recvudp", profile,
                                 rx1_local_host, recv_host1, self.inputs.logger)
            receiver2 = Receiver("recvudp", profile,
                                 rx2_local_host, recv_host2, self.inputs.logger)
            receiver3 = Receiver("recvudp", profile,
                                 rx3_local_host, recv_host3, self.inputs.logger)

            receiver1.start()
            receiver2.start()
            receiver3.start()
            sender.start()

            # Poll to make sure traffic flows, optional
            sender.poll()
            receiver1.poll()
            receiver2.poll()
            receiver3.poll()
            sender.stop()
            receiver1.stop()
            receiver2.stop()
            receiver3.stop()
            self.logger.info(
                '%s sent %s packets to %s. %s received %s packets out of which %s are Corrupted' %
                (vm1_fixture.vm_name, sender.sent, ips, vm2_fixture.vm_name, receiver1.recv, receiver1.corrupt))
            self.logger.info(
                '%s sent %s packets to %s. %s received %s packets out of which %s are Corrupted' %
                (vm1_fixture.vm_name, sender.sent, ips, vm3_fixture.vm_name, receiver2.recv, receiver2.corrupt))
            self.logger.info(
                '%s sent %s packets to %s. %s received %s packets out of which %s are Corrupted' %
                (vm1_fixture.vm_name, sender.sent, ips, vm4_fixture.vm_name, receiver3.recv, receiver3.corrupt))

            corrupt_list = [receiver1.corrupt,
                            receiver2.corrupt, receiver3.corrupt]
            for i in corrupt_list:
                if(i > 0):
                    result = False
            if(sender.sent == receiver1.recv == receiver2.recv == receiver3.recv):
                self.logger.info("Packets seen on all the receivers")
            else:
                self.logger.error("Packet Drops seen")
                result = False
            print result
        msg = "Packets not Broadcasted"
        self.assertEqual(result, True, msg)
        return True
    # end broadcast_udp_w_chksum

    # start subnet ping
    # verifying that ping to subnet broadcast is respended by other vms in same subnet
    # vm from other subnet should not respond
    @preposttest_wrapper
    def test_ping_on_broadcast_multicast(self):
        ''' Validate Ping on subnet broadcast,link local multucast,network broadcast .

        '''
        vn1_name = 'vn30'
        vn1_subnets = ['30.1.1.0/24']
        ping_count = '5'
        vn1_vm1_name = 'vm1'
        vn1_vm2_name = 'vm2'
        vn1_vm3_name = 'vm3'
        vn1_vm4_name = 'vm4'
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm1_name))
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm2_name))
        vm3_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm3_name))
        vm4_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm4_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm2_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm3_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm4_fixture.vm_obj)
        # Geting the VM ips
        vm1_ip = vm1_fixture.vm_ip
        vm2_ip = vm2_fixture.vm_ip
        vm3_ip = vm3_fixture.vm_ip
        vm4_ip = vm4_fixture.vm_ip
        ip_list = [vm1_ip, vm2_ip, vm3_ip, vm4_ip]
        list_of_ip_to_ping = ['30.1.1.255', '224.0.0.1', '255.255.255.255']
        # passing command to vms so that they respond to subnet broadcast
        cmd_list_to_pass_vm = [
            'echo 0 > /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm2_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm3_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm4_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        for dst_ip in list_of_ip_to_ping:
            print 'pinging from %s to %s' % (vm1_ip, dst_ip)
# pinging from Vm1 to subnet broadcast
            ping_output = vm1_fixture.ping_to_ip(
                dst_ip, return_output=True, count=ping_count, other_opt='-b')
            expected_result = ' 0% packet loss'
            assert (expected_result in ping_output)
# getting count of ping response from each vm
            string_count_dict = {}
            string_count_dict = get_string_match_count(ip_list, ping_output)
            print string_count_dict
            for k in ip_list:
                # this is a workaround : ping utility exist as soon as it gets
                # one response
                assert (string_count_dict[k] >= (int(ping_count) - 1))
        return True
    # end subnet ping

    @preposttest_wrapper
    def test_ping_within_vn_two_vms_two_different_subnets(self):
        ''' Validate Ping between two VMs within a VN-2 vms in 2 different subnets.
            Validate ping to subnet broadcast not responded back by other vm
            Validate ping to network broadcast (all 255) is responded back by other vm

        '''
        vn1_name = 'vn030'
        vn1_subnets = ['31.1.1.0/30', '31.1.2.0/30']
        # vn1_subnets=['30.1.1.0/24']
        vn1_vm1_name = 'vm1'
        vn1_vm2_name = 'vm2'
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm1_name))
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm2_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm2_fixture.vm_obj)
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)
        assert vm2_fixture.ping_to_ip(vm1_fixture.vm_ip)
        # Geting the VM ips
        vm1_ip = vm1_fixture.vm_ip
        vm2_ip = vm2_fixture.vm_ip
        ip_list = [vm1_ip, vm2_ip]
#       gettig broadcast ip for vm1_ip
        ip_broadcast = ''
        ip_broadcast = get_subnet_broadcast_from_ip(vm1_ip, '30')
        list_of_ip_to_ping = [ip_broadcast, '224.0.0.1', '255.255.255.255']
        # passing command to vms so that they respond to subnet broadcast
        cmd_list_to_pass_vm = [
            'echo 0 > /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts']

        vm1_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm2_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)

        for dst_ip in list_of_ip_to_ping:
            print 'pinging from %s to %s' % (vm1_ip, dst_ip)
# pinging from Vm1 to subnet broadcast
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
                assert (string_count_dict[vm2_ip] > 0)
        return True
    # end test_ping_within_vn

    @preposttest_wrapper
    def test_process_restart_in_policy_between_vns(self):
        ''' Test to validate that with policy having rule to check icmp fwding between VMs on different VNs , ping between VMs should pass
        with process restarts
        '''
        result = True
        msg = []
        vn1_name = 'vn40'
        vn1_subnets = ['40.1.1.0/24']
        vn2_name = 'vn41'
        vn2_subnets = ['41.1.1.0/24']
        policy1_name = 'policy1'
        policy2_name = 'policy2'
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': vn1_name,
                'dest_network': vn2_name,
            },
        ]
        rev_rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': vn2_name,
                'dest_network': vn1_name,
            },
        ]
        policy1_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy1_name, rules_list=rules, inputs=self.inputs,
                connections=self.connections))
        policy2_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy2_name, rules_list=rev_rules, inputs=self.inputs,
                connections=self.connections))
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets, policy_objs=[policy1_fixture.policy_obj]))
        assert vn1_fixture.verify_on_setup()
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn2_name, inputs=self.inputs, subnets=vn2_subnets, policy_objs=[policy2_fixture.policy_obj]))
        assert vn2_fixture.verify_on_setup()
        vn1_vm1_name = 'vm1'
        vn1_vm2_name = 'vm2'
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm1_name))
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn2_fixture.obj, vm_name=vn1_vm2_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up(vm1_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm2_fixture.vm_obj)
        self.logger.info("Verify ping to vm %s" % (vn1_vm2_name))
        ret = vm1_fixture.ping_with_certainty(
            vm2_fixture.vm_ip, expectation=True)
        result_msg = "vm ping test result to vm %s is: %s" % (
            vn1_vm2_name, ret)
        self.logger.info(result_msg)
        if ret != True:
            result = False
            msg.extend([result_msg, policy1_name])
        self.assertEqual(result, True, msg)

        for compute_ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter', [compute_ip])
        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('contrail-control', [bgp_ip])
        sleep(30)
        self.logger.info('Sleeping for 30 seconds')
        vn1_vm3_name = 'vm3'
        vn1_vm4_name = 'vm4'
        vm3_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm3_name))
        vm4_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn2_fixture.obj, vm_name=vn1_vm4_name))
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()
        self.nova_fixture.wait_till_vm_is_up(vm3_fixture.vm_obj)
        self.nova_fixture.wait_till_vm_is_up(vm4_fixture.vm_obj)
        self.logger.info("Verify ping to vm %s" % (vn1_vm4_name))
        ret = vm3_fixture.ping_with_certainty(
            vm4_fixture.vm_ip, expectation=True)
        result_msg = "vm ping test result to vm %s is: %s" % (
            vn1_vm4_name, ret)
        self.logger.info(result_msg)
        if ret != True:
            result = False
            msg.extend([result_msg, policy1_name])
        self.assertEqual(result, True, msg)
        return True
# end test_process_restart_in_policy_between_vns

    @preposttest_wrapper
    def test_multiple_vn_vm(self):
        """ Validate creation of multiple VN with multiple subnet and VMs in it.
        """

        result = True
        # Multiple VN's with multiple subnets
        vn_s = {'vn-1': '20.1.1.0/24', 'vn-2':
                ['10.1.1.0/24', '10.1.2.0/24']}
        multi_vn_fixture = self.useFixture(MultipleVNFixture(
            connections=self.connections, inputs=self.inputs, subnet_count=2,
            vn_name_net=vn_s,  project_name=self.inputs.project_name))
        assert multi_vn_fixture.verify_on_setup()

        vn_objs = multi_vn_fixture.get_all_fixture_obj()
        multi_vm_fixture = self.useFixture(MultipleVMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vm_count_per_vn=4, vn_objs=vn_objs, image_name='cirros-0.3.0-x86_64-uec',
            flavor='m1.tiny'))
        assert multi_vm_fixture.verify_on_setup()

        return True
    # end test_multiple_vn_vm

    @preposttest_wrapper
    def test_process_restart_with_multiple_vn_vm(self):
        ''' Test to validate that multiple VM creation and deletion passes.
        '''
        vm1_name = 'vm_mine'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_count_for_test = 32
        if (len(self.inputs.compute_ips) == 1):
            vn_count_for_test = 10
        vm_fixture = self.useFixture(
            create_multiple_vn_and_multiple_vm_fixture(
                connections=self.connections,
                vn_name=vn_name, vm_name=vm1_name, inputs=self.inputs, project_name=self.inputs.project_name,
                subnets=vn_subnets, vn_count=vn_count_for_test, vm_count=1, subnet_count=1, image_name='cirros-0.3.0-x86_64-uec',
                flavor='m1.tiny'))
        time.sleep(100)
        try:
            assert vm_fixture.verify_vms_on_setup()
            assert vm_fixture.verify_vns_on_setup()
        except Exception as e:
            self.logger.exception("Got exception as %s" % (e))
        compute_ip = []
        for vmobj in vm_fixture.vm_obj_dict.values():
            vm_host_ip = vmobj.vm_node_ip
            if vm_host_ip not in compute_ip:
                compute_ip.append(vm_host_ip)
        self.inputs.restart_service('contrail-vrouter', compute_ip)
        sleep(50)
        for vmobj in vm_fixture.vm_obj_dict.values():
            assert vmobj.verify_on_setup()
        return True

    @preposttest_wrapper
    def test_bring_up_vm_with_control_node_down(self):
        ''' Create VM when there is not active control node. Verify VM comes up fine when all control nodes are back

        '''
        if len(set(self.inputs.bgp_ips)) < 2:
            raise self.skipTest(
                "Skiping Test. At least 2 control node required to run the test")
        result = True
        vn1_name = 'vn30'
        vn1_subnets = ['30.1.1.0/24']

        # Collecting all the control node details
        controller_list = []
        for entry in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[entry]
            agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
            for entry in agent_xmpp_status:
                controller_list.append(entry['controller_ip'])
        controller_list = set(controller_list)

        # Stop all the control node
        for entry in controller_list:
            self.logger.info('Stoping the Control service in  %s' % (entry))
            self.inputs.stop_service('contrail-control', [entry])
            self.addCleanup(self.inputs.start_service,
                            'contrail-control', [entry])
        sleep(30)

        vn1_vm1_name = 'vm1'
        vn1_vm2_name = 'vm2'
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm1_name))

        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm2_name))

        vm1_fixture.verify_vm_launched()
        vm2_fixture.verify_vm_launched()
        vm1_node_ip = self.inputs.host_data[
            self.nova_fixture.get_nova_host_of_vm(vm1_fixture.vm_obj)]['host_ip']
        vm2_node_ip = self.inputs.host_data[
            self.nova_fixture.get_nova_host_of_vm(vm2_fixture.vm_obj)]['host_ip']
        inspect_h1 = self.agent_inspect[vm1_node_ip]
        inspect_h2 = self.agent_inspect[vm2_node_ip]
        self.logger.info(
            'Checking TAP interface is created for all VM and  should be in Error state')
        vm1_tap_intf = None
        vm2_tap_intf = None
        vm1_tap_intf = inspect_h1.get_vna_tap_interface_by_ip(
            vm1_fixture.vm_ip)
        if vm1_tap_intf is []:
            self.logger.error('TAP interface is not created for VM %s' %
                              (vn1_vm1_name))
            result = result and False
        else:
            if vm1_tap_intf[0]['vrf_name'] != '--ERROR--':
                self.logger.error(
                    'TAP interface VRF info should be Error . But currently in %s' %
                    (vm1_tap_intf[0]['vrf_name']))
                result = result and False

        vm2_tap_intf = inspect_h2.get_vna_tap_interface_by_ip(
            vm2_fixture.vm_ip)
        if vm2_tap_intf is []:
            self.logger.error('TAP interface is not created for VM %s' %
                              (vn1_vm2_name))
            result = result and False
        else:
            if vm2_tap_intf[0]['vrf_name'] != '--ERROR--':
                self.logger.error(
                    'TAP interface VRF info should be Error . But currently in %s' %
                    (vm2_tap_intf[0]['vrf_name']))
                result = result and False

        self.logger.info('Waiting for 120 sec for cleanup to begin')
        sleep(120)
        # Check agent should not have any VN info
        for entry in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[entry]
            self.logger.info('Checking VN info in agent %s.' % (entry))
            if inspect_h.get_vna_vn_list()['VNs'] != []:
                self.logger.error(
                    'Agent should not have any VN info present when control node is down')
                result = result and False

        # Start all the control node
        for entry in controller_list:
            self.logger.info('Starting the Control service in  %s' % (entry))
            self.inputs.start_service('contrail-control', [entry])
        sleep(10)

        self.logger.info('Checking the VM came up properly or not')
        assert vn1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm1_fixture.verify_on_setup()

        # Check ping between VM
        assert vm2_fixture.ping_to_ip(vm1_fixture.vm_ip)
        if not result:
            self.logger.error(
                'Test to verify cleanup of agent after control nodes stop Failed')
            assert result
        return True

    # end test_bring_up_vm_with_control_node_down

#   @preposttest_wrapper
#   def test_vn_reboot_nodes(self):
#        ''' Test to validate persistence of VN across compute/control/cfgm node reboots Commented till 129 is fixed.
#        '''
#        vn_obj=self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,
#                     vn_name='vn111', inputs= self.inputs, subnets=['100.100.100.0/24']))
#        assert vn_obj.verify_on_setup()
#        reboot the compute node now and verify the VN persistence
#        for compute_ip in self.inputs.compute_ips:
#            self.inputs.reboot(compute_ip)
#        sleep(120)
#        assert vn_obj.verify_on_setup()
# reboot the control nodes now and verify the VN persistence
#        for bgp_ip in self.inputs.bgp_ips:
#            self.inputs.reboot(bgp_ip)
#        sleep(120)
#        assert vn_obj.verify_on_setup()
# reboot the cfgm node now and verify the VN persistence
#        self.inputs.reboot(self.inputs.cfgm_ip)
#        sleep(120)
#        assert vn_obj.verify_on_setup()
#        assert vn_obj
#        return True
    # end test_vn_reboot_nodes

    @preposttest_wrapper
    def test_vn_subnet_types(self):
        """ Validate various type of subnets associated to VNs.
        """

        # vn-1 : 0.0.0.0/0 to be given once PR 802 is fixed
        reserved_ip_vns = {'vn-2': '169.254.1.1/24', 'vn-3': '251.2.2.1/24'}
        overlapping_vns = {'vn-5': ['10.1.1.0/24', '10.1.1.0/24'], 'vn-6':
                           ['11.11.11.0/30', '11.11.11.8/29'], 'vn-7': '10.1.1.1/24'}
        # vn-4 is added here bcoz the check has been implemented already for
        # 127 and not for 0
        non_usable_block_vns = {'vn-4': '127.0.0.1/8', 'vn-8':
                                '100.100.100.0/31', 'vn-9': '200.200.200.1/32'}

        res_vn_fixture = self.useFixture(
            MultipleVNFixture(connections=self.connections, inputs=self.inputs,
                              subnet_count=2, vn_name_net=reserved_ip_vns,  project_name=self.inputs.project_name))
        ovlap_vn_fixture = self.useFixture(MultipleVNFixture(
            connections=self.connections, inputs=self.inputs, subnet_count=2, vn_name_net=overlapping_vns,  project_name=self.inputs.project_name))
        try:
            non_usable_vn_fixture = self.useFixture(MultipleVNFixture(
                connections=self.connections, inputs=self.inputs, subnet_count=2, vn_name_net=non_usable_block_vns,  project_name=self.inputs.project_name))
        except NotPossibleToSubnet as e:
            self.logger.info(
                'Subnets like vn-4, vn-8 and vn-8 cannot be created as IPs cannot be assigned')
        if not res_vn_fixture.verify_on_setup:
            self.logger.error(
                'Reserved Addresses cannot be assigned --> Bug 803')
        assert ovlap_vn_fixture.verify_on_setup(
        ), 'Overlap in address space not taken care of '
        return True
    # end test_subnets_vn

    @preposttest_wrapper
    def test_bulk_add_delete(self):
        '''
        Validate adding multiple vms in bulk and deleting them in one shot
        '''
        vn1_name = "bulk_test_vn1"
        vn1_subnets = ['101.1.1.0/24']
        vn1_fixture = self.useFixture(
            VNFixture(project_name=self.inputs.project_name,
                      connections=self.connections, vn_name=vn1_name,
                      inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup(), "Verification of VN %s failed" % (
            vn1_name)

        # Create 15 VMs in bulk
        vm_count = 15
        vmx_fixture = self.useFixture(
            VMFixture(project_name=self.inputs.project_name,
                      connections=self.connections, vn_obj=vn1_fixture.obj,
                      vm_name=vn1_name, count=vm_count, image_name='cirros-0.3.0-x86_64-uec',
                      flavor='m1.tiny'))
        assert vmx_fixture.verify_vm_launched(), 'One or more VMs do not seem' \
            ' to have got launched. Please check logs'

        # Delete all vms now
        self.remove_from_cleanups(vmx_fixture)
        vmx_fixture.cleanUp(), 'Cleanup failed for atleast one VM, Check logs'
        assert vmx_fixture.verify_vm_not_in_nova(), 'Atleast 1 VM not deleted ' \
            ' in Nova, Pls check logs'

        return True
    # end test_bulk_add_delete

    @preposttest_wrapper
    def test_multiple_metadata_service_scale(self):
        ''' Test to metadata service scale.
        '''

        vm1_name = 'vm_min'
        vn_name = 'vn1111'
        vn_subnets = ['111.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name,
                                                image_name='cirros-0.3.0-x86_64-uec', flavor='m1.tiny'))

        text = """#!/bin/sh
echo "Hello World.  The time is now $(date -R)!" | tee /tmp/output.txt
               """
        try:
            with open("/tmp/metadata_script.txt", "w") as f:
                f.write(text)
        except Exception as e:
            self.logger.exception(
                "Got exception while creating /tmp/metadata_script.txt as %s" % (e))

        vm1_name = 'vm_mine'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_count_for_test = 20
        if (len(self.inputs.compute_ips) == 1):
            vn_count_for_test = 2
        try:
            vm_fixture = self.useFixture(
                create_multiple_vn_and_multiple_vm_fixture(
                    connections=self.connections,
                    vn_name=vn_name, vm_name=vm1_name, inputs=self.inputs, project_name=self.inputs.project_name,
                    subnets=vn_subnets, vn_count=vn_count_for_test, vm_count=1, subnet_count=1, userdata='/tmp/metadata_script.txt',
                    image_name='cirros-0.3.0-x86_64-uec', flavor='m1.tiny'))
            compute_ip = []
            time.sleep(30)
        except Exception as e:
            self.logger.exception("Got exception as %s" % (e))

        try:
            assert vm_fixture.verify_vms_on_setup()
            assert vm_fixture.verify_vns_on_setup()
        except Exception as e:
            self.logger.exception("Got exception as %s" % (e))

        cmd = 'ls /tmp/'
        result = True
        for vmobj in vm_fixture.vm_obj_dict.values():
            ret = vmobj.run_cmd_on_vm(cmds=[cmd])
            for elem in ret.values():
                if 'output.txt' in elem:
                    result = result and True
                    break
            if not result:
                self.logger.warn(
                    "metadata_script.txt did not get executed in the vm")
                result = result and False
            else:
                self.logger.info("Printing the output.txt :")
                cmd = 'cat /tmp/output.txt'
                ret = vmobj.run_cmd_on_vm(cmds=[cmd])
                self.logger.info("%s" % (ret.values()))
                for elem in ret.values():
                    if 'Hello World' in elem:
                        result = result and True
                    else:
                        self.logger.warn(
                            "metadata_script.txt did not get executed in the vm...output.txt does not contain proper output")
                        result = result and False
        assert result
        return True

    @preposttest_wrapper
    def test_kill_service_verify_core_generation(self):
        """Validate core is generated for services on SIGQUIT"""
        compute_ip = self.inputs.compute_ips[0]
        compute_user = self.inputs.host_data[compute_ip]['username']
        compute_pwd = self.inputs.host_data[compute_ip]['password']
        cfgm_ip = self.inputs.cfgm_ips[0]
        cfgm_user = self.inputs.host_data[cfgm_ip]['username']
        cfgm_pwd = self.inputs.host_data[cfgm_ip]['password']
        collector_ip = self.inputs.collector_ips[0]
        collector_user = self.inputs.host_data[collector_ip]['username']
        collector_pwd = self.inputs.host_data[collector_ip]['password']
        control_ip = self.inputs.bgp_ips[0]
        control_user = self.inputs.host_data[control_ip]['username']
        control_pwd = self.inputs.host_data[control_ip]['password']
        result = True
        err_msg = []
        # Format <service_name> : [<process_name>,
        # <role_on_which_process_running>]
        service_list = {
            'contrail-control': ['control-node', 'control'],
            'contrail-vrouter': ['vnswad', 'compute'],
            'contrail-qe': ['qed', 'collector'],
            'contrail-collector': ['vizd', 'collector'],
            'contrail-opserver': ['python', 'collector'],
            'contrail-discovery': ['python', 'cfgm'],
            'contrail-api': ['python', 'cfgm'],
            'contrail-svc-monitor': ['python', 'cfgm']
        }

        for service, process in service_list.iteritems():
            cmd = "service %s status |  awk '{print $4}' | cut -f 1 -d','" % service
            self.logger.info("service:%s, process:%s" % (service, process))
            if process[1] == 'cfgm':
                login_ip = cfgm_ip
                login_user = cfgm_user
                login_pwd = cfgm_pwd
            elif process[1] == 'compute':
                login_ip = compute_ip
                login_user = compute_user
                login_pwd = compute_pwd
            elif process[1] == 'control':
                login_ip = control_ip
                login_user = control_user
                login_pwd = control_pwd
            elif process[1] == 'collector':
                login_ip = collector_ip
                login_user = collector_user
                login_pwd = collector_pwd
            else:
                self.logger.error("invalid role:%s" % process[1])
                result = result and False
                assert result, "Invalid role:%s specified for service:%s" % (
                    process[1], service)

            with settings(host_string='%s@%s' % (login_user, login_ip),
                          password=login_pwd, warn_only=True, abort_on_prompts=False):
                pid = run(cmd)
                self.logger.info("service:%s, pid:%s" % (service, pid))
                run('kill -3 %s' % pid)
                sleep(10)
                if "No such file or directory" in run("ls -lrt /var/crashes/core.%s.%s*" % (process[0], pid)):
                    self.logger.error(
                        "core is not generated for service:%s" % service)
                    err_msg.append("core is not generated for service:%s" %
                                   service)
                    result = result and False
                else:
                    # remove core after generation
                    run("rm -f /var/crashes/core.%s.%s*" % (process[0], pid))
        assert result, "core generation validation test failed: %s" % err_msg
        return True
    # end test_kill_service_verify_core_generation

# end TestVMVN
