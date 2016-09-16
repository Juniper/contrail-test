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
from base import BaseVcenterGateway
from common import isolated_creds
import inspect
import time
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from tcutils.util import get_subnet_broadcast
from tcutils.util import skip_because
import test
from tcutils.tcpdump_utils import *



class TestBasicVcenterGateway(BaseVcenterGateway):

    @classmethod
    def setUpClass(cls):
        super(TestBasicVcenterGateway, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBasicVcenterGateway, cls).tearDownClass()


    @test.attr(type=['vcenter_gateway'])
    @preposttest_wrapper
    def test_vm_add_delete(self):
        '''
        Description:  Test to validate VM creation and deletion.
        Test steps:
                1. Create VM in a VN.
        Pass criteria: Creation and deletion of the VM should go thru fine.
        Maintainer : ganeshahv@juniper.net
        '''
        vn_fixture = self.create_vn(orch=self.vcenter_orch)
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vn_name = vn_fixture.vn_name
        vm1_fixture = self.create_vm(vn_fixture=vn_fixture,
                                     vm_name=get_random_name('vm_add_delete'),orch=self.vcenter_orch)
        assert vm1_fixture.verify_on_setup()
        return True
    # end test_vm_add_delete

    @test.attr(type=['vcenter_gateway'])
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
        vn1_fixture = self.create_vn(vn_name=vn1_name,orch=self.vcenter_orch)
        assert vn1_fixture.verify_on_setup()
        vn1_fixture.read()
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm1_name,orch=self.vcenter_orch)
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

    @test.attr(type=['vcenter_gateway'])
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
        vm1_name = get_random_name('vm1')
        vm2_name = get_random_name('vm2')
        vn_name = get_random_name('vn222')
        scp_test_file_sizes = ['1303'] if os.environ.has_key('ci_image') else \
                              ['1000', '1101', '1202', '1303', '1373', '1374',
                               '2210', '2845', '3000', '10000', '10000003']
        file = 'somefile'
        y = 'ls -lrt %s' % file
        cmd_to_check_file = [y]
        x = 'sync'
        cmd_to_sync = [x]
        create_result = True
        transfer_result = True
        vn_fixture = self.create_vn(vn_name=vn_name,orch=self.vcenter_orch)
        assert vn_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn_fixture=vn_fixture,vm_name=vm1_name
                                     ,orch=self.vcenter_orch)
        vm2_fixture = self.create_vm(vn_fixture=vn_fixture,vm_name=vm2_name
                                     )
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()

        for size in scp_test_file_sizes:
            self.logger.debug("-" * 80)
            self.logger.debug("FILE SIZE = %sB" % size)
            self.logger.debug("-" * 80)

            self.logger.debug('Transferring the file from %s to %s using scp' %
                             (vm1_fixture.vm_name, vm2_fixture.vm_name))
            if os.environ.has_key('ci_image') and self.inputs.get_af() == 'v4':
                file_transfer_result = vm1_fixture.scp_file_transfer_cirros(vm2_fixture, size=size)
            else:
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

    @test.attr(type=['vcenter_gateway'])
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
        vm1_name = get_random_name('vm1')
        vm2_name = get_random_name('vm2')
        ts = time.time()
        vn_name = '%s_%s'%(inspect.stack()[0][3],str(ts))
        file_sizes=['1000'] if os.environ.has_key('ci_image') else \
                            ['1000', '1101', '1202', '1303', '1373', '1374',
                             '2210', '2845', '3000', '10000', '10000003']
        file= 'testfile'
        y = 'ls -lrt /var/lib/tftpboot/%s'%file
        cmd_to_check_file = [y]
        z = 'ls -lrt /var/lib/tftpboot/%s'%file
        cmd_to_check_tftpboot_file = [z]
        x = 'sync'
        cmd_to_sync = [x]
        create_result= True
        transfer_result= True
        vn_fixture= self.create_vn(vn_name=vn_name,orch=self.vcenter_orch)
        assert vn_fixture.verify_on_setup()
        img_name=os.environ['ci_image'] if os.environ.has_key('ci_image')\
                                        else 'ubuntu'
        flavor='m1.tiny' if os.environ.has_key('ci_image')\
                         else 'contrail_flavor_small'
        vm1_fixture = self.create_vm(vn_fixture= vn_fixture, vm_name=vm1_name,orch=self.vcenter_orch)
        vm2_fixture = self.create_vm(vn_fixture= vn_fixture, vm_name=vm2_name,
                                     image_name=img_name, flavor=flavor)
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        for size in file_sizes:
            self.logger.debug ("-"*80)
            self.logger.debug("FILE SIZE = %sB"%size)
            self.logger.debug ("-"*80)
            self.logger.info('Transferring the file from %s to %s using tftp'%(
                                      vm1_fixture.vm_name, vm2_fixture.vm_name))
            vm1_fixture.check_file_transfer(dest_vm_fixture = vm2_fixture,
                                            mode = 'tftp', size= size)
            self.logger.debug('Checking if the file exists on %s'%vm2_name)
            vm2_fixture.run_cmd_on_vm( cmds= cmd_to_check_file )
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

