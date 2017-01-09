# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import fixtures
import testtools
import time

from vn_test import *
from vm_test import *
from common.connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper

from common.neutron.base import BaseNeutronTest
import test
from tcutils.util import get_an_ip


class TestVirtualNetwork(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(TestVirtualNetwork, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestVirtualNetwork, cls).tearDownClass()

    @preposttest_wrapper
    def test_virtual_network_rename(self):
        ''' Launch a vn , rename the vn
            verify in network response , api server
        '''
        result = True
        vn1_name = get_random_name('vn1')
        vn1_subnet_cidr = get_random_cidr()
        vn1_subnets = [{'cidr': vn1_subnet_cidr}]
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        body = {'name': "test_network"}
        net_dict = {'network': body}
        net_rsp = self.quantum_h.update_network(
            vn1_fixture.vn_id,
            net_dict)
        assert net_rsp['network'][
            'name'] == "test_network", 'Failed to update network name'
        vn_dict = self.api_s_inspect.get_cs_vn_by_id(
            vn_id=vn1_fixture.vn_id, refresh=True)
        assert vn_dict[
            'virtual-network']['display_name'] == "test_network", 'New name of VN is not reflected in API Server'

    @preposttest_wrapper
    def test_virtual_network_admin_state_up(self):
        '''
           Verify that with admin_state_up set as False vn does not forward packets
        '''
        result = True
        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vn1_vm1_name = get_random_name('vn1-vm1')
        vn1_vm2_name = get_random_name('vn1-vm2')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vn1_vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name,
                                         image_name='cirros-0.3.0-x86_64-uec')
        vn1_vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name,
                                         image_name='cirros-0.3.0-x86_64-uec')
        assert vn1_vm1_fixture.wait_till_vm_is_up()
        assert vn1_vm2_fixture.wait_till_vm_is_up()
        assert vn1_vm1_fixture.ping_with_certainty(vn1_vm2_fixture.vm_ip)
        body = {'admin_state_up': False}
        net_dict = {'network': body}
        net_rsp = self.quantum_h.update_network(
            vn1_fixture.vn_id,
            net_dict)
        assert net_rsp['network'][
            'admin_state_up'] == False, 'Failed to update admin_state_up'
        assert vn1_vm1_fixture.ping_with_certainty(vn1_vm2_fixture.vm_ip,
                                                   expectation=False)
        body = {'admin_state_up': True}
        net_dict = {'network': body}
        net_rsp = self.quantum_h.update_network(
            vn1_fixture.vn_id,
            net_dict)
        assert net_rsp['network'][
            'admin_state_up'], 'Failed to update admin_state_up'
        assert vn1_vm1_fixture.ping_with_certainty(vn1_vm2_fixture.vm_ip)
