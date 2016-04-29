# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import fixtures
import testtools
import time
import sys
from common.connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper
import time
import test
from tcutils.util import *
from netaddr import IPNetwork, IPAddress
from common.ecmp.ecmp_traffic import ECMPTraffic
from common.ecmp.ecmp_verify import ECMPVerify
try:
    from heat_test import *
    from base import BaseHeatTest

    class TestHeat(BaseHeatTest, ECMPTraffic, ECMPVerify):

        @classmethod
        def setUpClass(cls):
            super(TestHeat, cls).setUpClass()

        @classmethod
        def tearDownClass(cls):
            super(TestHeat, cls).tearDownClass()

        @test.attr(type=['sanity', 'ci_sanity'])
        @preposttest_wrapper
        def test_heat_stacks_list(self):
            '''
            Validate installation of heat
            This issues a command to list all the heat-stacks
            '''
            stacks_list = []
            self.stacks = self.useFixture(
                HeatFixture(connections=self.connections, username=self.inputs.username, password=self.inputs.password,
                            project_fq_name=self.inputs.project_fq_name, inputs=self.inputs, cfgm_ip=self.inputs.cfgm_ip, openstack_ip=self.inputs.openstack_ip))
            stacks_list = self.stacks.list_stacks()
            self.logger.info(
                'The following are the stacks currently : %s' % stacks_list)
        # end test_heat_stacks_list

        @preposttest_wrapper
        def test_svc_creation_with_heat(self):
            '''
            Validate creation of a in-network-nat service chain using heat
            '''
            vn_list = []
            right_net_fix, r_hs_obj = self.config_vn(stack_name='right_net')
            left_net_fix, l_h_obj = self.config_vn(stack_name='left_net')
            vn_list = [left_net_fix, right_net_fix]
            vms = []
            vms = self.config_vms(vn_list)
            svc_template = self.config_svc_template(stack_name='svc_template')
            st_fq_name = ':'.join(svc_template.st_fq_name)
            st_obj = svc_template.st_obj
            svc_instance, si_hs_obj = self.config_svc_instance(
                'svc_instance', st_fq_name, st_obj, vn_list)
            si_fq_name = (':').join(svc_instance.si_fq_name)
            svc_chain = self.config_svc_chain(si_fq_name, vn_list)
            assert vms[0].ping_with_certainty(vms[1].vm_ip, expectation=True)
        # end test_svc_creation_with_heat

        @test.attr(type=['sanity'])
        @preposttest_wrapper
        def test_transit_vn_with_svc(self):
            '''
            Validate Transit VN with in-network-nat service chain using heat
            '''
            vn_list = []
            right_net_fix, r_hs_obj = self.config_vn(stack_name='right_net')
            transit_net_fix, t_hs_obj = self.config_vn(
                stack_name='transit_net')
            left_net_fix, l_hs_obj = self.config_vn(stack_name='left_net')
            vn_list1 = [left_net_fix, transit_net_fix]
            vn_list2 = [transit_net_fix, right_net_fix]
            end_vn_list = [left_net_fix, right_net_fix]
            vms = []
            vms = self.config_vms(end_vn_list)
            svc_template = self.config_svc_template(stack_name='svc_template')
            st_fq_name = ':'.join(svc_template.st_fq_name)
            st_obj = svc_template.st_obj
            svc_instance1, si_hs_obj1 = self.config_svc_instance(
                'svc_instance1', st_fq_name, st_obj, vn_list1)
            svc_instance2, si_hs_obj2 = self.config_svc_instance(
                'svc_instance2', st_fq_name, st_obj, vn_list2)
            si1_fq_name = (':').join(svc_instance1.si_fq_name)
            si2_fq_name = (':').join(svc_instance2.si_fq_name)
            svc_chain1 = self.config_svc_chain(
                si1_fq_name, vn_list1, 'svc_chain1')
            svc_chain2 = self.config_svc_chain(
                si2_fq_name, vn_list2, 'svc_chain2')
            assert vms[0].ping_with_certainty(vms[1].vm_ip, expectation=True)
            self.logger.info(
                'Changing the VN %s to non-transitive' % transit_net_fix.vn_name)
            self.update_stack(
                t_hs_obj, stack_name='transit_net', change_set=['allow_transit', 'False'])
            assert vms[0].ping_with_certainty(vms[1].vm_ip, expectation=False)
        # end test_transit_vn_with_svc

        def transit_vn_with_left_right_svc(self, left_svcs, right_svcs):
            '''
            Validate Transit VN with multi transparent service chain using heat
            '''
            vn_list = []
            right_net_fix, r_hs_obj = self.config_vn(stack_name='right_net')
            transit_net_fix, t_hs_obj = self.config_vn(stack_name='transit_net')
            left_net_fix, l_hs_obj = self.config_vn(stack_name='left_net')
            vn_list1 = [left_net_fix, transit_net_fix]
            vn_list2 = [transit_net_fix, right_net_fix]
            end_vn_list = [left_net_fix, right_net_fix]
            vms = []
            vms = self.config_vms(end_vn_list)
            svc_tmpls = {}
            for mode in set(left_svcs + right_svcs):
                tmpl = self.config_svc_template(stack_name='st_%s' % mode,
                                    mode=mode)
                svc_tmpls[mode] = {}
                svc_tmpls[mode]['tmpl'] = tmpl
                svc_tmpls[mode]['obj'] = tmpl.st_obj
                svc_tmpls[mode]['fq_name'] = ':'.join(tmpl.st_fq_name)

            left_sis = []
            for i, svc in enumerate(left_svcs):
                left_sis.append(self.config_svc_instance(
                    'svc_left_%d' % i, svc_tmpls[svc]['fq_name'],
                    svc_tmpls[svc]['obj'], vn_list1, svc_mode=svc))
            right_sis = []
            for i, svc in enumerate(right_svcs):
                right_sis.append(self.config_svc_instance(
                    'svc_right_%d' % i, svc_tmpls[svc]['fq_name'],
                    svc_tmpls[svc]['obj'], vn_list2, svc_mode=svc))
            left_si_names = ','.join([(':').join(si[0].si_fq_name) for si in left_sis])
            right_si_names = ','.join([(':').join(si[0].si_fq_name) for si in right_sis])
            left_chain = self.config_svc_chain(
                left_si_names, vn_list1, 'left_chain')
            right_chain = self.config_svc_chain(
                right_si_names, vn_list2, 'right_chain')
            assert vms[0].ping_with_certainty(vms[1].vm_ip, expectation=True)
        # end transit_vn_with_left_right_svc

        @preposttest_wrapper
        def test_transit_vn_sym_1_innetnat(self):
            svcs= ['in-network-nat']
            self.transit_vn_with_left_right_svc(svcs, svcs)
            return True

        @preposttest_wrapper
        def test_transit_vn_sym_1_innet(self):
            svcs= ['in-network']
            self.transit_vn_with_left_right_svc(svcs, svcs)
            return True

        @preposttest_wrapper
        def test_transit_vn_sym_1_trans(self):
            svcs= ['transparent']
            self.transit_vn_with_left_right_svc(svcs, svcs)
            return True

        @preposttest_wrapper
        def test_transit_vn_asym_innetnat_trans(self):
            left= ['in-network-nat']
            right= ['transparent']
            self.transit_vn_with_left_right_svc(left, right)
            return True

        @preposttest_wrapper
        def test_transit_vn_asym_innet_trans(self):
            left= ['in-network']
            right= ['transparent']
            self.transit_vn_with_left_right_svc(left, right)
            return True

        @preposttest_wrapper
        def test_transit_vn_asym_innet_nat(self):
            left= ['in-network']
            right= ['in-network-nat']
            self.transit_vn_with_left_right_svc(left, right)
            return True

        @preposttest_wrapper
        def test_transit_vn_sym_2_innet_svc(self):
            svcs= ['in-network', 'in-network']
            self.transit_vn_with_left_right_svc(svcs, svcs)
            return True

        @preposttest_wrapper
        def test_transit_vn_sym_2_trans_svc(self):
            svcs= ['transparent', 'transparent']
            self.transit_vn_with_left_right_svc(svcs, svcs)
            return True

        @preposttest_wrapper
        def test_transit_vn_sym_innet_nat(self):
            svcs= ['in-network', 'in-network-nat']
            self.transit_vn_with_left_right_svc(svcs, svcs)
            return True

        @preposttest_wrapper
        def test_transit_vn_sym_trans_nat(self):
            svcs= ['transparent', 'in-network-nat']
            self.transit_vn_with_left_right_svc(svcs, svcs)
            return True

        @preposttest_wrapper
        def test_transit_vn_sym_trans_innet(self):
            svcs= ['transparent', 'in-network']
            self.transit_vn_with_left_right_svc(svcs, svcs)
            return True

        @preposttest_wrapper
        def test_max_inst_change_in_ecmp_svc(self):
            '''
            Validate creation of a in-network-nat service chain with 3 Service VMs using heat
            '''
            vn_list = []
            right_net_fix, r_hs_obj = self.config_vn(stack_name='right_net')
            left_net_fix, l_h_obj = self.config_vn(stack_name='left_net')
            vn_list = [left_net_fix, right_net_fix]
            vms = []
            vms = self.config_vms(vn_list)
            svc_template = self.config_svc_template(
                stack_name='svc_template', scaling=True, mode='in-network-nat')
            st_fq_name = ':'.join(svc_template.st_fq_name)
            st_obj = svc_template.st_obj
            svc_instance, si_hs_obj = self.config_svc_instance(
                'svc_inst', st_fq_name, st_obj, vn_list, max_inst='3', svc_mode='in-network-nat')
            si_fq_name = (':').join(svc_instance.si_fq_name)
            svc_chain = self.config_svc_chain(si_fq_name, vn_list)
            assert vms[0].ping_with_certainty(vms[1].vm_ip, expectation=True)
            dst_vm_list = [vms[1]]
            self.verify_traffic_flow(
                vms[0], dst_vm_list, svc_instance, left_net_fix)
            self.logger.info(
                '***** Will increase the SVMs in the SI to 4 *****')
            self.update_stack(
                si_hs_obj, stack_name='svc_inst', change_set=['max_instances', '4'])
            time.sleep(10)
            svc_instance.verify_on_setup()
            self.verify_svm_count(si_hs_obj, 'svc_inst', '4')
            assert vms[0].ping_with_certainty(vms[1].vm_ip, expectation=True)
            self.verify_traffic_flow(
                vms[0], dst_vm_list, svc_instance, left_net_fix)
            self.logger.info(
                '***** Will decrease the SVMs in the SI to 2 *****')
            self.update_stack(
                si_hs_obj, stack_name='svc_inst', change_set=['max_instances', '2'])
            time.sleep(10)
            svc_instance.verify_on_setup()
            self.verify_svm_count(si_hs_obj, 'svc_inst', '2')
            assert vms[0].ping_with_certainty(vms[1].vm_ip, expectation=True)
            self.verify_traffic_flow(
                vms[0], dst_vm_list, svc_instance, left_net_fix)
    # end test_max_inst_change_in_ecmp_svc

        @preposttest_wrapper
        def test_ecmp_svc_creation_with_heat(self):
            '''
            Validate creation of a in-network-nat service chain with 3 Service VMs using heat
            '''
            vn_list = []
            right_net_fix, r_hs_obj = self.config_vn(stack_name='right_net')
            left_net_fix, l_h_obj = self.config_vn(stack_name='left_net')
            vn_list = [left_net_fix, right_net_fix]
            vms = []
            vms = self.config_vms(vn_list)
            svc_template = self.config_svc_template(
                stack_name='svc_template', scaling=True, mode='in-network-nat')
            st_fq_name = ':'.join(svc_template.st_fq_name)
            st_obj = svc_template.st_obj
            svc_instance, si_hs_obj = self.config_svc_instance(
                'svc_instance', st_fq_name, st_obj, vn_list, max_inst='3', svc_mode='in-network-nat')
            si_fq_name = (':').join(svc_instance.si_fq_name)
            svc_chain = self.config_svc_chain(si_fq_name, vn_list)
            assert vms[0].ping_with_certainty(vms[1].vm_ip, expectation=True)
            dst_vm_list = [vms[1]]
            self.verify_traffic_flow(
                vms[0], dst_vm_list, svc_instance, left_net_fix)
        # end test_ecmp_svc_creation_with_heat

    # end TestHeat

except ImportError:
    print 'Missing Heat Client. Will skip tests'
