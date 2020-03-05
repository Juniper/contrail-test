# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
from common.neutron.base import BaseNeutronTest
from tcutils.wrappers import preposttest_wrapper
import test
from tcutils.util import *
from vn_test import *

class TestRoutersBasic(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(TestRoutersBasic, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestRoutersBasic, cls).tearDownClass()

    @test.attr(type=['ci_sanity', 'sanity', 'suite1'])
    @preposttest_wrapper
    def test_basic_snat_behavior_without_external_connectivity(self):
        '''Create an external network, a router
        set router-gateway to external network
        launch a private network and attach it to router
        validate left vm pinging right vm through Snat
       '''

        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name)
        self.allow_all_on_default_fwaas_policy()
        vn1_fixture = self.create_vn()
        ext_vn_name = get_random_name('ext_vn')
        ext_vn_fixture = self.create_vn(vn_name=ext_vn_name,
            router_external=True)

        vm1_fixture = self.create_vm(vn1_fixture, image_name='cirros')
        vm2_fixture = self.create_vm(ext_vn_fixture, image_name='cirros')
        router_name = get_random_name('router1')
        router_dict = self.create_router(router_name)
        router_rsp = self.quantum_h.router_gateway_set(
                router_dict['id'],
                ext_vn_fixture.vn_id)
        self.add_vn_to_router(router_dict['id'], vn1_fixture)

        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(
         vm2_fixture.vm_ip), 'Ping from vm_left to vm_right through snat failed'
        return True
