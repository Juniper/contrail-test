from string import Template

from common.neutron.base import BaseNeutronTest
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because

class ExtendedFlowTests(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(ExtendedFlowTests, cls).setUpClass()
        cls.vnc_api_h = cls.vnc_lib
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(ExtendedFlowTests, cls).tearDownClass()
    # end tearDownClass

    @preposttest_wrapper
    @skip_because( bug='1530034')
    def test_with_fuzz_bug_1504710(self):
        '''
        This test makes sure that the vrouter doesnt misbehave
        with various IP protocols
        '''

        # TODO
        # Unable to figure out what scapy profile can fuzz
        # packets. Currently use raw scapy code itself
        python_code = Template('''
from scapy.all import *
a=fuzz(IP(dst='$dest_ip')/Raw(RandString(size=300)))
send(a, count=1000, inter=0, iface='eth0')
''')

        vn_fixture = self.create_vn()
        vm1_fixture = self.create_vm(vn_fixture)
        vm2_fixture = self.create_vm(vn_fixture)
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        python_code = python_code.substitute(dest_ip=vm2_fixture.vm_ip)
        vm1_fixture.run_python_code(python_code)

        # Now validate that later pings between vms work        
        self.do_ping_test(vm1_fixture, vm1_fixture.vm_ip, vm2_fixture.vm_ip)
    # end test_with_fuzz_bug_1504710

