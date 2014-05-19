import traffic_tests
from vn_test import *
from vm_test import *
from floating_ip import *
from policy_test import *
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from base import BaseVnVmTest
from common import isolated_creds

class TestMetadata(BaseVnVmTest):
    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestMetadata, cls).setUpClass()

    def runTest(self):
        pass
    #end runTes 
    @preposttest_wrapper
    def test_multiple_metadata_service_scale(self):
        ''' Test to metadata service scale.
        '''

        vm1_name='vm_min'
        vn_name='vn1111'
        vn_subnets=['111.1.1.0/24']
        vn_fixture= self.useFixture(VNFixture(project_name= self.project.project_name, connections= self.connections,
                     vn_name=vn_name, inputs= self.inputs, subnets= vn_subnets))
        vn_obj= vn_fixture.obj
        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
                        vn_obj=vn_obj, vm_name= vm1_name, project_name= self.project.project_name ,
                        image_name='ubuntu'))

        text = """#!/bin/sh
echo "Hello World.  The time is now $(date -R)!" | tee /tmp/output.txt
               """
        try:
            with open ("/tmp/metadata_script.txt" , "w") as f:
                f.write(text)
        except Exception as e:
            self.logger.exception("Got exception while creating /tmp/metadata_script.txt as %s"%(e))


        vm1_name='vm_mine'
        vn_name='vn222'
        vn_subnets=['11.1.1.0/24']
        vn_count_for_test=20
        if (len(self.inputs.compute_ips) == 1):
            vn_count_for_test=2
        try:
            vm_fixture= self.useFixture(create_multiple_vn_and_multiple_vm_fixture (connections= self.connections,
                     vn_name=vn_name, vm_name=vm1_name, inputs= self.inputs, project_name= self.project.project_name,
                      subnets= vn_subnets,vn_count=vn_count_for_test,vm_count=1,subnet_count=1,userdata = '/tmp/metadata_script.txt',
                        image_name='ubuntu'))
            compute_ip=[]
            time.sleep(30)
        except Exception as e:
            self.logger.exception("Got exception as %s"%(e))
        try:
            assert vm_fixture.verify_vms_on_setup()
            assert vm_fixture.verify_vns_on_setup()
        except Exception as e:
            self.logger.exception("Got exception as %s"%(e))

        cmd = 'ls /tmp/'
        result = True
        for vmobj in vm_fixture.vm_obj_dict.values():
            ret = vmobj.run_cmd_on_vm(cmds = [cmd])
            for elem in ret.values():
                if 'output.txt' in elem:
                    result = result and True
                    break
            if not result:
                self.logger.warn("metadata_script.txt did not get executed in the vm")
                result = result and False
            else:
                self.logger.info("Printing the output.txt :")
                cmd = 'cat /tmp/output.txt'
                ret = vmobj.run_cmd_on_vm(cmds = [cmd])
                self.logger.info("%s" %(ret.values()))
                for elem in ret.values():
                    if 'Hello World' in elem:
                        result = result and True
                    else:
                        self.logger.warn("metadata_script.txt did not get executed in the vm...output.txt does not contain proper output")
                        result = result and False
        assert result
        return True

#end TestVMVN
class TestMetadataXML(TestMetadata):
    _interface = 'xml'
    pass
