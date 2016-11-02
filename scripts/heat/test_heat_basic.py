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

from common.heat.base import BaseHeatTest

class TestBasicHeat(BaseHeatTest, ECMPTraffic, ECMPVerify):

    @classmethod
    def setUpClass(cls):
        super(TestBasicHeat, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBasicHeat, cls).tearDownClass()

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_svc_creation_with_heat(self):
        '''
        Validate creation of a in-network-nat service chain using heat
        '''
        vn_list = []
        if self.pt_based_svc:
            mgmt_net_fix, m_hs_obj = self.config_vn(stack_name='mgmt_net')
        else:
            mgmt_net_fix=None
            m_hs_obj=None
        right_net_fix, r_hs_obj = self.config_vn(stack_name='right_net')
        left_net_fix, l_h_obj = self.config_vn(stack_name='left_net')
        vn_list = [mgmt_net_fix, left_net_fix, right_net_fix]
        vms = []
        vms = self.config_vms([left_net_fix, right_net_fix])
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
# end TestHeat

class TestBasicHeatv2(TestBasicHeat):
    @classmethod
    def setUpClass(cls):
        super(TestBasicHeatv2, cls).setUpClass()
        cls.heat_api_version = 2
        cls.pt_based_svc = True

    @test.attr(type=['sanity', 'suite1'])
    @preposttest_wrapper
    def test_svc_creation_with_heat(self):
        super(TestBasicHeatv2, self).test_svc_creation_with_heat()

class TestBasicHeatIPv6(TestBasicHeat):
    @classmethod
    def setUpClass(cls):
        super(TestBasicHeatIPv6, cls).setUpClass()
        cls.inputs.set_af('v6')

class TestBasicHeatv2IPv6(TestBasicHeatv2):
    @classmethod
    def setUpClass(cls):
        super(TestBasicHeatv2IPv6, cls).setUpClass()
        cls.inputs.set_af('v6')

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_svc_creation_with_heat(self):
        super(TestBasicHeatv2, self).test_svc_creation_with_heat()
