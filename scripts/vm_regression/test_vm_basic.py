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

import test


class TestBasicVMVN4(BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicVMVN4, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBasicVMVN4, cls).tearDownClass()

    @test.attr(type=['sanity', 'ci_sanity', 'vcenter', 'suite1'])
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

    @test.attr(type=['sanity','quick_sanity','ci_sanity', 'vcenter', 'suite1'])
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
        vn_fixture = self.create_vn(vn_name=vn_name)
        assert vn_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn_fixture=vn_fixture,vm_name=vm1_name,
                                     flavor='contrail_flavor_small')
        vm2_fixture = self.create_vm(vn_fixture=vn_fixture,vm_name=vm2_name,
                                     flavor='contrail_flavor_small')
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()

        vm1_fixture.put_pub_key_to_vm()
        vm2_fixture.put_pub_key_to_vm()
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
                self.logger.debug(
                    'File of size %sB transferred via scp properly' % size)
            else:
                transfer_result = False
                self.logger.error(
                    'File of size %sB not transferred via scp ' % size)
                break
        assert transfer_result, 'File not transferred via scp '
        return transfer_result
    # end test_vm_file_trf_scp_tests


class TestBasicVMVN6(BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicVMVN6, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBasicVMVN6, cls).tearDownClass()

    def runTest(self):
        pass
    #end runTes 

    @test.attr(type=['sanity', 'ci_sanity', 'suite1'])
    @preposttest_wrapper
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
                                     userdata='/tmp/metadata_script.txt',
                                     flavor='m1.tiny')
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

