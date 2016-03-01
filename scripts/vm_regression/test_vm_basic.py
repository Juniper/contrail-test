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

