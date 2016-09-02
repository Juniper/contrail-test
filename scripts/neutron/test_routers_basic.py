# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
from tcutils.wrappers import preposttest_wrapper
from common.neutron.base import BaseNeutronTest
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

    @test.attr(type=['ci_sanity', 'suite1'])
    @preposttest_wrapper
    def test_basic_snat_behavior_without_external_connectivity(self):
        '''Create an external network, a router
        set router-gateway to external network
        launch a private network and attach it to router
        validate left vm pinging right vm through Snat
       '''

        vm1_name = get_random_name('vm_left')
        vn1_name = get_random_name('vn_private')
        vn1_subnets = [get_random_cidr()]
        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name)
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn1_fixture, vm1_name,
                                         image_name='cirros-0.3.0-x86_64-uec')
        vm1_fixture.wait_till_vm_is_up()

        ext_vn_name = get_random_name('ext_vn')
        ext_subnets = [get_random_cidr()]

        ext_vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=ext_vn_name,
                inputs=self.inputs,
                subnets=ext_subnets,
                router_external=True))

        ext_vn_fixture.verify_on_setup()

        vm2_name = get_random_name('vm_right')
        vm2_fixture = self.create_vm(ext_vn_fixture, vm2_name,
                                         image_name='cirros-0.3.0-x86_64-uec')
        vm2_fixture.wait_till_vm_is_up()

        router_name = get_random_name('router1')
        router_dict = self.create_router(router_name)
        router_rsp = self.quantum_h.router_gateway_set(
                router_dict['id'],
                ext_vn_fixture.vn_id)
        self.add_vn_to_router(router_dict['id'], vn1_fixture)
        assert vm1_fixture.ping_with_certainty(
         vm2_fixture.vm_ip), 'Ping from vm_left to vm_right through snat failed'
        return True
