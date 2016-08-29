# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import fixtures
from vm_test import VMFixture
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
    from common.heat.base import BaseHeatTest

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
        @skip_because(address_family='v6')
        def test_public_access_thru_svc_w_fip(self):
            '''
            Validate creation of a in-network-nat service chain using heat.
            Create a end VN.
            Associate FIPs to the end VM and the right intf of the SVM.
            Create a static route entry to point 0/0 to the left intf of the SVM.
            The end VM should be able to access internet.
            '''
            if ('MX_GW_TEST' not in os.environ) or (('MX_GW_TEST' in os.environ) and (os.environ.get('MX_GW_TEST') != '1')):
                self.logger.info(
                    "Skipping Test. Env variable MX_GW_TEST is not set. Skipping the test")
                raise self.skipTest(
                    "Skipping Test. Env variable MX_GW_TEST is not set. Skipping the test")
                return True
            public_vn_fixture = self.public_vn_obj.public_vn_fixture
            public_vn_subnet = self.public_vn_obj.public_vn_fixture.vn_subnets[
                0]['cidr']
            # Since the ping is across projects, enabling allow_all in the SG
            self.project.set_sec_group_for_allow_all(
                self.inputs.project_name, 'default')
            vn_list = []
            right_net_fix, r_hs_obj = self.config_vn(stack_name='right_net')
            left_net_fix, l_h_obj = self.config_vn(stack_name='left_net')
            mgmt_net_fix, m_h_obj = self.config_vn(stack_name='mgmt_net')
            end_net_fix, end_h_obj = self.config_vn(stack_name='end_net')
            vn_list = [left_net_fix, right_net_fix]
            svc_vn_list = [mgmt_net_fix, left_net_fix, right_net_fix]
            vms = []
            vms = self.config_vms(vn_list)
            end_vm, end_vm_fix = self.config_vm(end_net_fix)
            end_vm_vmi = self.get_stack_output(end_vm, 'port_id')
            left_vn_fip_pool = self.config_fip_pool(left_net_fix)
            left_vn_fip_pool_op = self.get_stack_output(
                left_vn_fip_pool, 'fip_pool_name')
            fip_pool_fqdn = (':').join(left_vn_fip_pool_op)
            left_vn_fip = self.config_fip(fip_pool_fqdn, end_vm_vmi)
            svc_template = self.config_svc_template(
                stack_name='st', mode='in-network-nat')
            pt_si_hs_obj = self.config_pt_si(
                'pt_si', svc_template, svc_vn_list)
            pt_si_hs_obj_op = self.get_stack_output(
                pt_si_hs_obj, 'service_instance_fq_name')
            si_fqdn = (':').join(pt_si_hs_obj_op)
            prefix = '8.8.8.8/32'
            si_intf_type = 'left'
            intf_route_table = self.config_intf_rt_table(
                prefix, si_fqdn, si_intf_type)
            intf_route_table_op = self.get_stack_output(
                intf_route_table, 'intf_rt_tbl_name')
            intf_rt_table_fqdn = (':').join(intf_route_table_op)
            pt_svm, pt_svm_fix = self.config_pt_svm(
                'pt_svm', si_fqdn, svc_vn_list, intf_rt_table_fqdn)
            svm_right_vmi_id = self.get_stack_output(
                pt_svm, 'svm_right_vmi_id')
            public_vn_fip = self.config_fip(
                public_vn_fixture.vn_fq_name, svm_right_vmi_id)
            assert end_vm_fix.ping_with_certainty('8.8.8.8', expectation=True)
        # end test_public_access_thru_svc_w_fip

        def transit_vn_with_left_right_svc(self, left_svcs, right_svcs):
            '''
            Validate Transit VN with multi transparent service chain using heat
            '''
            vn_list = []
            right_net_fix, r_hs_obj = self.config_vn(stack_name='right_net')
            transit_net_fix, t_hs_obj = self.config_vn(stack_name='transit_net', transit=True)
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
                si = self.config_svc_instance('sil_%d' % i, svc_tmpls[svc]['tmpl'], vn_list1)
                left_sis.append(si)
                if svc == 'in-network' and (self.inputs.get_af() == 'v6' or self.pt_based_svc):
                    self.add_route_in_svm(si[0], [right_net_fix, 'eth1'])
            right_sis = []
            for i, svc in enumerate(right_svcs):
                si = self.config_svc_instance('sir_%d' % i, svc_tmpls[svc]['tmpl'], vn_list2)
                right_sis.append(si)
                if svc == 'in-network' and (self.inputs.get_af() == 'v6' or self.pt_based_svc):
                    self.add_route_in_svm(si[0], [left_net_fix, 'eth0'])
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
            time.sleep(10)
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
            svc_rules.append(self.config_svc_rule(proto='any', si_fq_names=[si_fq_name], src_vns=[left_net_fix], dst_vns=[right_net_fix]))
            svc_chain = self.config_svc_chain(svc_rules, vn_list, [l_h_obj, r_hs_obj])
            time.sleep(10)
            assert vms[0].ping_with_certainty(vms[1].vm_ip, expectation=True)
            dst_vm_list = [vms[1]]
            self.verify_traffic_flow(
                vms[0], dst_vm_list, svc_instance, left_net_fix)
            self.logger.info(
                '%%%%% Will increase the SVMs in the SI to 4 %%%%%')
            self.update_stack(
                si_hs_obj, change_sets=[('max_instances', '4')])
            time.sleep(10)
            svc_instance.verify_on_setup()
            self.verify_svm_count(si_hs_obj, 'si', '4')
            assert vms[0].ping_with_certainty(vms[1].vm_ip, expectation=True)
            self.verify_traffic_flow(
                vms[0], dst_vm_list, svc_instance, left_net_fix)
            self.logger.info(
                '%%%%% Will decrease the SVMs in the SI to 2 %%%%%')
            self.update_stack(
                si_hs_obj, change_sets=[('max_instances', '2')])
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
            svc_rules.append(self.config_svc_rule(proto='any', si_fq_names=[si_fq_name], src_vns=[left_net_fix], dst_vns=[right_net_fix]))
            svc_chain = self.config_svc_chain(svc_rules, vn_list, [l_h_obj, r_hs_obj])
            time.sleep(10)
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
            time.sleep(10)
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
            cls.pt_based_svc = True

        @preposttest_wrapper
        def test_ecmp_svc_creation_with_heat(self):
            '''
            Validate creation of a in-network-nat ECMP service chain using port-tuple
            '''
            stack_name = 'ecmp_pt'
            self.config_v2_svc_chain(stack_name)
        # end test_ecmp_v2_creation_with_heat

        @preposttest_wrapper
        def test_pt_multi_inline_v2_svc_creation_with_heat(self):
            '''
            Validate creation of a multi-inline SVC using port-tuple
            '''
            stack_name = 'pt_multi_inline'
            self.config_v2_svc_chain(stack_name)
        # end test_pt_multi_inline_v2_svc_creation_with_heat

        @preposttest_wrapper
        def test_src_cidr_svc_creation_with_heat(self):
            '''
            Validate Source CIDR based policy with service chaining

            At high level service chain template consists of following resources
                1. Two VNs (left_vn:10.10.10.0/24 and right_vn: 20.20.20.0/24
                2. Two VMs in left_vn (left_vm1: 10.10.10.3/24 and left_vm2: 10.10.10.4/24)
                3. One VM in right_vn (right_vm: 20.20.20.3/24)
                4. Service chain with version 2 template and in-network, having CIDR based policy with left_vm1 IP for source

            Validation steps
                1. Ping right_vm from left_vm1 and ping should pass, since policy is based upon left_vm1 CIDR
                2. Ping right_vm from left_vm2 and ping should fail, as polciy does not match for left_vm2 IP address

            '''
            stack_name = 'src_cidr_svc'
            self.config_v2_svc_chain(stack_name)
        # end test_cidr_based_sc

    class TestHeatv2IPv6(TestHeatv2):

        @classmethod
        def setUpClass(cls):
            super(TestHeatv2IPv6, cls).setUpClass()
            cls.inputs.set_af('v6')

except ImportError:
    print 'Missing Heat Client. Will skip tests'
