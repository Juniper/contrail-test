import time
from vm_test import *
from policy_test import *
import test
from bgpaas_test import *
from tcutils.wrappers import preposttest_wrapper
from base import BaseBGPTest
from common import isolated_creds
from tcutils.wrappers import preposttest_wrapper

class TestBasicBGP(BaseBGPTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicBGP, cls).setUpClass()

    def create_vn(self,policy_obj, *args, **kwargs):

        return self.useFixture(
                VNFixture(project_name=self.inputs.project_name,
                          connections=self.connections,
                          inputs=self.inputs,policy_objs=[policy_obj],
                          *args, **kwargs
                          ))

    @classmethod
    def tearDownClass(cls):
        super(TestBasicBGP, cls).tearDownClass()
   
    def create_bgpaas(self):
        return self.useFixture(
            BGPaasFixture(project_name=self.inputs.project_name,
                      connections=self.connections,
                      inputs=self.inputs,
                      service_name="bgpaas.router",
                      asn="652"))

    @test.attr(type=['sanity','ci_sanity', 'quick_sanity', 'vcenter'])
    @preposttest_wrapper
    def test_bgpaas_add_delete(self):
        '''
        Description: Test to validate bgpaas creation and deletion.
        '''

        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any',
                'source_network': 'any',
                'dest_network': 'any'
            },
        ]

        policy_fixture = self.useFixture(PolicyFixture(
                                          policy_name="test.policy",
                                          rules_list=rules,
                                          inputs=self.inputs,
                                          connections=self.connections))


        vn1_name = "vsrx_mx_vn1"
        vn1_subnets = ['2.3.0.0/16']
        #vn1_name = get_random_name(vn1_name)
        mgmt_vn_fixture = self.create_vn(policy_fixture.policy_obj,vn_name="MGMT",disable_gateway=True)
        vn1_fixture = self.create_vn(policy_fixture.policy_obj,vn_name= vn1_name,subnets=vn1_subnets,disable_gateway=True)
        vn2_name = "bgp_vn2"
        #vn2_name = get_random_name(vn2_name)
        vn2_subnets = ['1.3.0.0/16','fd66::0/96']
        vn2_fixture = self.create_vn(policy_fixture.policy_obj,vn_name= vn2_name,subnets=vn2_subnets)
        #assert vn1_fixture.verify_on_setup(), "Verification of VN %s failed" % (vn1_name)
        #assert vn2_fixture.verify_on_setup(), "Verification of VN %s failed" % (vn2_name)
        #vn1_vm1_name = get_random_name("srx-vm")
        #vn2_vm1_name = get_random_name("bgp-vm")
        vn1_vm1_name = "srx.bgp.vm"
        vn2_vm1_name = "bgp.vm"
        vm1_fixture= self.useFixture(VMFixture(connections=self.connections,
                                     vn_objs=[mgmt_vn_fixture.obj,vn1_fixture.obj,vn2_fixture.obj],
                                     vm_name=vn1_vm1_name,
                                     project_name=self.inputs.project_name,
                                     image_name = 'vSRX',flavor='m1.medium'))
        vm2_fixture= self.useFixture(VMFixture(connections=self.connections,
                                     vn_objs=[vn2_fixture.obj,mgmt_vn_fixture.obj],
                                    vm_name=vn2_vm1_name,
                                    project_name=self.inputs.project_name,
                                    image_name = 'bgpass-v6-vm',flavor='m1.small'))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        #vm1_fixture.wait_till_vm_is_up()
        #vm2_fixture.wait_till_vm_is_up()
        bgpaas_obj = self.create_bgpaas()
        #assert bgpaas_obj.verify_on_setup()
        time.sleep(300)
        expected_result = ' 0% packet loss'
        test_result = True

        dst_ip = '3.1.1.5'
        ping_count = 5
        ping_output = vm2_fixture.ping_to_ip(
                dst_ip, return_output=True, count=ping_count)
        self.logger.info("ping output : \n %s" % (ping_output))
        ret = re.search(expected_result,ping_output)
        if ret:
           test_result = test_result and True
        else:
           test_result = test_result and False

        dst_ip = '2001:0db8:0:f101::1'
        ping_count = 5
        ping_output = vm2_fixture.ping_to_ipv6(
                dst_ip, return_output=True, count=ping_count)
        self.logger.info("ping output : \n %s" % (ping_output))
        ret = re.search(expected_result,ping_output)
        if ret:
           test_result = test_result and True
        else:
           test_result = test_result and False

        dst_ip = '2001:0db8:0:f102::1'
        ping_count = 5
        ping_output = vm2_fixture.ping_to_ip(
                dst_ip, return_output=True, count=ping_count)
        self.logger.info("ping output : \n %s" % (ping_output))
        ret = re.search(expected_result,ping_output)
        if ret:
           test_result = test_result and True
        else:
           test_result = test_result and False

        return test_result
