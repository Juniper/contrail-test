from tcutils.wrappers import preposttest_wrapper
from common.servicechain.firewall.verify import VerifySvcFirewall
from common.svc_health_check.base import BaseHC
import test
import time
from common import isolated_creds
from tcutils.wrappers import preposttest_wrapper
from common.bgpaas.base import BaseBGPaaS
from common.neutron.base import BaseNeutronTest
from tcutils.util import *
from tcutils.tcpdump_utils import *
#BaseBGPaaS,
from contrailapi import ContrailVncApi
from base import RPBase
 
class TestRP(RPBase, BaseBGPaaS, BaseHC, VerifySvcFirewall):

    @classmethod
    def setUpClass(cls):
        super(TestRP, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestRP, cls).tearDownClass()

    def is_test_applicable(self):
        return (True, None)

    def setUp(self):
        super(TestRP, self).setUp()
        result = self.is_test_applicable()

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_rp_interface(self):
        #ret_dict = self.verify_svc_chain(service_mode='in-network-nat',
        #                                 create_svms=True, max_inst=1)
        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='cirros')
        self.configure_term_routing_policy(vn_fixture = vn_fixture, from_term = 'protocol', sub_from = 'interface', to_term = 'community', sub_to = '64512:55555')
        self.verify_policy_in_control(vn_fixture, test_vm.vm_ip, '55555')

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_rp_interface_static(self):
        #ret_dict = self.verify_svc_chain(service_mode='in-network-nat',
        #                                 create_svms=True, max_inst=1)
        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='cirros')
        self.static_table_handle = ContrailVncApi(self.vnc_lib, self.logger)
        self.intf_table_to_right_obj = self.static_table_handle.create_route_table(
            prefixes=['14.15.16.17/32'],
            name="int_table_right",
            parent_obj=self.project.project_obj,
        )
        id_entry = self.inputs.project_fq_name[0] + ':' + \
            self.inputs.project_fq_name[1] + ':' + vn_fixture.vn_name
        self.static_table_handle.bind_vmi_to_interface_route_table(
            str(test_vm.get_vmi_ids()[id_entry]),
            self.intf_table_to_right_obj)

        self.configure_term_routing_policy(vn_fixture = vn_fixture, from_term = 'protocol', sub_from = 'interface-static', to_term = 'community', sub_to = '64512:55555')
        self.verify_policy_in_control(vn_fixture, '14.15.16.17/32', '55555')

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_rp_service_interface(self):
        ret_dict = self.verify_svc_chain(service_mode='in-network',
                                         create_svms=True, max_inst=1)
        #vn_name = get_random_name('bgpaas_vn')
        #vn_subnets = [get_random_cidr()]
        #vn_fixture = self.create_vn(vn_name, vn_subnets)
        #test_vm = self.create_vm(vn_fixture, 'test_vm',
        #                         image_name='cirros')
        si_fixture = ret_dict['si_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        left_vn_fixture = ret_dict['left_vn_fixture']
        self.configure_term_routing_policy(vn_fixture = si_fixture, from_term = 'protocol', sub_from = 'service-interface', to_term = 'community', sub_to = '64512:55555')
        self.verify_policy_in_control(vn_fixture, '0.255.255.250', '55555')

    @preposttest_wrapper
    def test_rp_interface_matrix(self):
        #ret_dict = self.verify_svc_chain(service_mode='in-network-nat',
        #                                 create_svms=True, max_inst=1)
        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='cirros')
        self.configure_term_routing_policy(vn_fixture = vn_fixture, from_term = 'protocol', sub_from = 'interface', to_term = 'med', sub_to = '444')
        self.verify_policy_in_control(vn_fixture, test_vm.vm_ip, '444')
        self.configure_term_routing_policy(vn_fixture = vn_fixture, from_term = 'protocol', sub_from = 'interface', to_term = 'local-preference', sub_to = '555')
        self.verify_policy_in_control(vn_fixture, test_vm.vm_ip, '555')

        self.configure_term_routing_policy(vn_fixture = vn_fixture, from_term = 'protocol', sub_from = 'interface', to_term = 'as-path', sub_to = '666')
        self.verify_policy_in_control(vn_fixture, test_vm.vm_ip, '666')

    @preposttest_wrapper
    def test_rp_interface_static_matrix(self):
        #ret_dict = self.verify_svc_chain(service_mode='in-network-nat',
        #                                 create_svms=True, max_inst=1)
        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='cirros')
        self.static_table_handle = ContrailVncApi(self.vnc_lib, self.logger)
        self.intf_table_to_right_obj = self.static_table_handle.create_route_table(
            prefixes=['14.15.16.17/32'],
            name="int_table_right",
            parent_obj=self.project.project_obj,
        )
        id_entry = self.inputs.project_fq_name[0] + ':' + \
            self.inputs.project_fq_name[1] + ':' + vn_fixture.vn_name
        self.static_table_handle.bind_vmi_to_interface_route_table(
            str(test_vm.get_vmi_ids()[id_entry]),
            self.intf_table_to_right_obj)

        self.configure_term_routing_policy(vn_fixture = vn_fixture, from_term = 'protocol', sub_from = 'interface-static', to_term = 'med', sub_to = '444')
        self.verify_policy_in_control(vn_fixture, '14.15.16.17/32', '444')
        self.configure_term_routing_policy(vn_fixture = vn_fixture, from_term = 'protocol', sub_from = 'interface-static', to_term = 'local-preference', sub_to = '555')
        self.verify_policy_in_control(vn_fixture, '14.15.16.17/32', '555')

        self.configure_term_routing_policy(vn_fixture = vn_fixture, from_term = 'protocol', sub_from = 'interface-static', to_term = 'as-path', sub_to = '666')
        self.verify_policy_in_control(vn_fixture, '14.15.16.17/32', '666')

    @preposttest_wrapper
    def test_rp_service_interface_matrix(self):

        ret_dict = self.verify_svc_chain(service_mode='in-network',
                                         create_svms=True, max_inst=1)
        si_fixture = ret_dict['si_fixture']
        left_vm_fixture = ret_dict['left_vm_fixture']
        right_vm_fixture = ret_dict['right_vm_fixture']
        left_vn_fixture = ret_dict['left_vn_fixture']

        self.configure_term_routing_policy(vn_fixture = si_fixture, from_term = 'protocol', sub_from = 'service-interface', to_term = 'med', sub_to = '444')
        self.verify_policy_in_control(vn_fixture, '0.255.255.250', '444')
        self.configure_term_routing_policy(vn_fixture = si_fixture, from_term = 'protocol', sub_from = 'service-interface', to_term = 'local-preference', sub_to = '555')
        self.verify_policy_in_control(vn_fixture, '0.255.255.250', '555')

        self.configure_term_routing_policy(vn_fixture = si_fixture, from_term = 'protocol', sub_from = 'service-interface', to_term = 'as-path', sub_to = '666')
        self.verify_policy_in_control(vn_fixture, '0.255.255.250', '666')


