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
from common.servicechain.verify import VerifySvcChain

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

        @test.attr(type=['sanity'])
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
            svc_template = self.config_svc_template(stack_name='st', mode='in-network')
            svc_instance, si_hs_obj = self.config_svc_instance(
                'si', svc_template, vn_list)
            si_fq_name = (':').join(svc_instance.si_fq_name)
            svc_rules = []
            svc_rules.append(self.config_svc_rule(si_fq_names=[si_fq_name], src_vns=[left_net_fix], dst_vns=[right_net_fix]))
            if self.inputs.get_af() == 'v6':
                svc_rules.append(self.config_svc_rule(proto='icmp6', si_fq_names=[si_fq_name], src_vns=[left_net_fix], dst_vns=[right_net_fix]))
            svc_chain = self.config_svc_chain(svc_rules, vn_list, [l_h_obj, r_hs_obj])
            assert vms[0].ping_with_certainty(vms[1].vm_ip, expectation=True)
        # end test_svc_creation_with_heat

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
            for i, mode in enumerate(set(left_svcs + right_svcs)):
                tmpl = self.config_svc_template(stack_name='st_%d' % i,
                                    mode=mode)
                svc_tmpls[mode] = {}
                svc_tmpls[mode]['tmpl'] = tmpl
                svc_tmpls[mode]['obj'] = tmpl.st_obj
                svc_tmpls[mode]['fq_name'] = ':'.join(tmpl.st_fq_name)

            left_sis = []
            for i, svc in enumerate(left_svcs):
                left_sis.append(self.config_svc_instance(
                    'sil_%d' % i, svc_tmpls[svc]['tmpl'], vn_list1))
            right_sis = []
            for i, svc in enumerate(right_svcs):
                right_sis.append(self.config_svc_instance(
                    'sir_%d' % i, svc_tmpls[svc]['tmpl'], vn_list2))
            left_si_names = [(':').join(si[0].si_fq_name) for si in left_sis]
            right_si_names = [(':').join(si[0].si_fq_name) for si in right_sis]
            left_rules = []
            left_rules.append(self.config_svc_rule(si_fq_names=left_si_names, src_vns=[left_net_fix], dst_vns=[transit_net_fix]))
            right_rules = []
            right_rules.append(self.config_svc_rule(si_fq_names=right_si_names, src_vns=[transit_net_fix], dst_vns=[right_net_fix]))
            if self.inputs.get_af() == 'v6':
                left_rules.append(self.config_svc_rule(proto='icmp6', si_fq_names=left_si_names, src_vns=[left_net_fix], dst_vns=[transit_net_fix]))
                right_rules.append(self.config_svc_rule(proto='icmp6', si_fq_names=right_si_names, src_vns=[transit_net_fix], dst_vns=[right_net_fix]))
            left_chain = self.config_svc_chain(left_rules, vn_list1, [l_hs_obj, t_hs_obj], 'left_chain')
            right_chain = self.config_svc_chain(right_rules, vn_list2, [t_hs_obj, r_hs_obj], 'right_chain')
            assert vms[0].ping_with_certainty(vms[1].vm_ip, expectation=True)
        # end transit_vn_with_left_right_svc

        @preposttest_wrapper
        @skip_because(address_family='v6')
        def test_transit_vn_sym_1_innetnat(self):
            svcs= ['in-network-nat']
            self.transit_vn_with_left_right_svc(svcs, svcs)
            return True

        @test.attr(type=['sanity'])
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
        @skip_because(address_family='v6')
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
        @skip_because(address_family='v6')
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
        @skip_because(address_family='v6')
        def test_transit_vn_sym_innet_nat(self):
            svcs= ['in-network', 'in-network-nat']
            self.transit_vn_with_left_right_svc(svcs, svcs)
            return True

        @preposttest_wrapper
        @skip_because(address_family='v6')
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
                stack_name='st', scaling=True, mode='in-network-nat')
            svc_instance, si_hs_obj = self.config_svc_instance(
                'si', svc_template, vn_list, max_inst=3)
            si_fq_name = (':').join(svc_instance.si_fq_name)
            svc_rules = []
            svc_rules.append(self.config_svc_rule(si_fq_names=[si_fq_name], src_vns=[left_net_fix], dst_vns=[right_net_fix]))
            if self.inputs.get_af() == 'v6':
                svc_rules.append(self.config_svc_rule(proto='icmp6', si_fq_names=[si_fq_name], src_vns=[left_net_fix], dst_vns=[right_net_fix]))
            svc_chain = self.config_svc_chain(svc_rules, vn_list, [l_h_obj, r_hs_obj])
            assert vms[0].ping_with_certainty(vms[1].vm_ip, expectation=True)
            dst_vm_list = [vms[1]]
            self.verify_traffic_flow(
                vms[0], dst_vm_list, svc_instance, left_net_fix)
            self.logger.info(
                '***** Will increase the SVMs in the SI to 4 *****')
            self.update_stack(
                si_hs_obj, change_set=[('max_instances', '4')])
            time.sleep(10)
            svc_instance.verify_on_setup()
            self.verify_svm_count(si_hs_obj, 'si', '4')
            assert vms[0].ping_with_certainty(vms[1].vm_ip, expectation=True)
            self.verify_traffic_flow(
                vms[0], dst_vm_list, svc_instance, left_net_fix)
            self.logger.info(
                '***** Will decrease the SVMs in the SI to 2 *****')
            self.update_stack(
                si_hs_obj, change_set=[('max_instances', '2')])
            time.sleep(10)
            svc_instance.verify_on_setup()
            self.verify_svm_count(si_hs_obj, 'si', '2')
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
                stack_name='st', scaling=True, mode='in-network-nat')
            svc_instance, si_hs_obj = self.config_svc_instance(
                'si', svc_template, vn_list, max_inst=3)
            si_fq_name = (':').join(svc_instance.si_fq_name)
            svc_rules = []
            svc_rules.append(self.config_svc_rule(si_fq_names=[si_fq_name], src_vns=[left_net_fix], dst_vns=[right_net_fix]))
            if self.inputs.get_af() == 'v6':
                svc_rules.append(self.config_svc_rule(proto='icmp6', si_fq_names=[si_fq_name], src_vns=[left_net_fix], dst_vns=[right_net_fix]))
            svc_chain = self.config_svc_chain(svc_rules, vn_list, [l_h_obj, r_hs_obj])
            assert vms[0].ping_with_certainty(vms[1].vm_ip, expectation=True)
            dst_vm_list = [vms[1]]
            self.verify_traffic_flow(
                vms[0], dst_vm_list, svc_instance, left_net_fix)
        # end test_ecmp_svc_creation_with_heat

        def multi_svc_chain(self, policys, svcs):
            '''
            Validate multi service chain using heat
            '''
            right_net_fix, r_hs_obj = self.config_vn(stack_name='right_net')
            left_net_fix, l_hs_obj = self.config_vn(stack_name='left_net')
            vn_list = [left_net_fix, right_net_fix]
            vms = []
            vms = self.config_vms(vn_list)
            svc_tmpls = {}
            for i, mode in enumerate(set(svcs.values())):
                tmpl = self.config_svc_template(stack_name='st_%d' % i,
                                    mode=mode)
                svc_tmpls[mode] = {}
                svc_tmpls[mode]['tmpl'] = tmpl
                svc_tmpls[mode]['obj'] = tmpl.st_obj
                svc_tmpls[mode]['fq_name'] = ':'.join(tmpl.st_fq_name)
            sis = {}
            i = 1
            for svc, mode in svcs.items():
                sis[svc] = self.config_svc_instance(
                    'sil_%d' % i, svc_tmpls[mode]['tmpl'], vn_list)
                i += 1
            rules = []
            test_ping = False
            for policy in policys:
                if (policy['proto'] == 'icmp') or (policy['proto'] == 'icmp6'):
                    test_ping = True
                rules.append(self.config_svc_rule(direction=policy['direction'],
                        proto=policy['proto'],
                        src_ports=policy.get('src_ports',None),
                        dst_ports=policy.get('dst_ports',None),
                        src_vns=[left_net_fix], dst_vns=[right_net_fix],
                        si_fq_names=[(':').join(sis[policy['svc']][0].si_fq_name)]))
            chain = self.config_svc_chain(rules, vn_list, [l_hs_obj, r_hs_obj], 'svc_chain')
            if test_ping:
                assert vms[0].ping_with_certainty(vms[1].vm_ip, expectation=True)
            for policy in policys:
                if policy['proto'] == 'icmp':
                    continue
                proto = policy['proto'] if policy['proto'] != 'any' else 'udp'
                sport = policy.get('src_ports', 8000)
                dport = policy.get('dst_ports', 8000)
                if type(sport) == type([]):
                    sport = sport[0][0]
                    dport = dport[0][0]
                sent, recv = self.verify_traffic(vms[0], vms[1], proto, sport, dport)
                assert sent == recv, "%s Traffic with src port %d, dst port %d failed" % (proto, sport, dport)
            return True
        # end multi_svc_chain

        @preposttest_wrapper
        def  test_proto_based_multi_sc(self):
            svcs = {'svc1' : 'in-network', 'svc2' : 'in-network'}
            policys = [{'direction':'<>', 'proto':'icmp', 'svc':'svc1'},
                       {'direction':'<>', 'proto':'tcp', 'svc':'svc2'}]
            if self.inputs.get_af() == 'v6':
                policys.append({'direction': '<>', 'proto': 'icmp6', 'svc':'svc1'})
            return self.multi_svc_chain(policys, svcs)

        @preposttest_wrapper
        def  test_port_based_multi_sc(self):
            svcs = {'svc1' : 'in-network', 'svc2' : 'in-network'}
            policys = [{'direction':'<>', 'proto':'tcp', 'svc':'svc1', 'src_ports':[(8000,8000)], 'dst_ports':[(8000,8000)]},
                       {'direction':'<>', 'proto':'tcp', 'svc':'svc2', 'src_ports':[(8001,8001)], 'dst_ports':[(8001,8001)]}]
            return self.multi_svc_chain(policys, svcs)

    # end TestHeat

    class TestHeatIPv6(TestHeat):

        @classmethod
        def setUpClass(cls):
            super(TestHeatIPv6, cls).setUpClass()
            cls.inputs.set_af('v6')

    class TestHeatv2(TestHeat):

        @classmethod
        def setUpClass(cls):
            super(TestHeatv2, cls).setUpClass()
            cls.heat_api_version = 2

    class TestHeatv2IPv6(TestHeat):

        @classmethod
        def setUpClass(cls):
            super(TestHeatv2IPv6, cls).setUpClass()
            cls.inputs.set_af('v6')
            cls.heat_api_version = 2

    class TestHeatPortTupleSvc(TestHeat):

        @classmethod
        def setUpClass(cls):
            super(TestHeatPortTupleSvc, cls).setUpClass()
            cls.heat_api_version = 2
            cls.pt_based_svc = True

    class TestHeatPortTupleSvcIPv6(TestHeat):

        @classmethod
        def setUpClass(cls):
            super(TestHeatPortTupleSvcIPv6, cls).setUpClass()
            cls.inputs.set_af('v6')
            cls.heat_api_version = 2
            cls.pt_based_svc = True

except ImportError:
    print 'Missing Heat Client. Will skip tests'
