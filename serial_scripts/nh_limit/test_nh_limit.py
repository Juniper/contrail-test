from __future__ import absolute_import
from tcutils.wrappers import preposttest_wrapper
import os
import test
from .base import TestNHLimit
from common.base import *

class TestNHLimitKernel(TestNHLimit):
    subnet = '11.1.1.1/32'
    logicalsystem = ['nh_LS100', 'nh_LS200']
    table = ['_proj_LS100.inet.0', '_proj_LS200.inet.0']
    agent_mode = None
    vn_count = 10

    @preposttest_wrapper
    def test_nh_limit_one_million(self):
        '''
        Description: Change nhLimit to 1 million and verify the number of nh indexes on agent side.
        Test Steps: 
                   1. Pump routes on mx side
                   2. Set 1 million nh limit on agent side
                   3. Create 10 VNs with route target and 1 VM in each VN on any one compute
                   4. Verify 1 million nh_indexes on agent side
                   5. Verify ping between any two VMs
        Pass criteria: Nh limit should be properly set and nh indexes should be same in number as nh_limit
        Maintainer: rsetru@juniper.net
        '''
        nh_limit = '1000000'
        count = self.get_prefix_count(nh_limit, self.vn_count)
        nh_index_Range = []
        nh_index_Range.append(int(nh_limit) - 5)
        nh_index_Range.append(int(nh_limit))
        compute = self.get_compute()
        for i in range(len(self.logicalsystem)):
            self.add_routes_using_rtgen_mx_side(
                self.logicalsystem[i], self.table[i], self.subnet, count)
            self.addCleanup(self.remove_routes_mx_side, self.logicalsystem[i])
        self.set_nh_limit(nh_limit=nh_limit, compute=compute, modify=True)
        self.addCleanup(self.reset_nh_limit, compute=compute)
        self.create_vmvn_for_nhlimittest(compute, self.vn_count)
        self.verify_nh_indexes(compute, nh_index_Range)
        self.ping_after_nh_index()

    @preposttest_wrapper
    def test_nh_limit_change(self):
        '''
        Test Steps:
                   1. Pump routes 800000 on mx side
                   2. Set 600000 nh limit on agent side
                   3. Create 10 VNs with route target and 1 VM in each VN on any one compute
                   4. Verify that only 600000 nh_indexes are on agent side
                   5. Verify ping between any two VMs
                   6. Set 800000 nh limit on agent side
                   7. Verify that 800000 nh_indexes are on agent side
                   8. Verify ping between any two VMs
        Pass criteria: Nh limit should be properly set and nh indexes should be same in number as nh_limit
        Maintainer: rsetru@juniper.net
        '''
        nh_limit1 = '600000'
        nh_limit2 = '800000'
        count = self.get_prefix_count(nh_limit2, self.vn_count)
        nh_index_Range1 = []
        nh_index_Range1.append(int(nh_limit1) - 5)
        nh_index_Range1.append(int(nh_limit1))
        nh_index_Range2 = []
        nh_index_Range2.append(int(nh_limit2) - 5)
        nh_index_Range2.append(int(nh_limit2))
        compute = self.get_compute()
        for i in range(len(self.logicalsystem)):
            self.add_routes_using_rtgen_mx_side(
                self.logicalsystem[i], self.table[i], self.subnet, count)
            self.addCleanup(self.remove_routes_mx_side, self.logicalsystem[i])
        self.set_nh_limit(nh_limit=nh_limit1, compute=compute, modify=True)
        self.create_vmvn_for_nhlimittest(compute, self.vn_count)
        self.verify_nh_indexes(compute, nh_index_Range1)
        self.ping_after_nh_index()
        self.reset_nh_limit(compute=compute)
        self.set_nh_limit(nh_limit=nh_limit2, compute=compute, modify=True)
        self.addCleanup(self.reset_nh_limit, compute=compute)
        self.verify_nh_indexes(compute, nh_index_Range2)
        self.ping_after_nh_index()

    @test.attr(type=['nh_limit_test'])
    @preposttest_wrapper
    def test_nh_limit_change_with_mpls(self):
        '''
        Test Steps:
                   1. Pump routes 800000 on mx side
                   2. Set 600000 nh limit and 10000 mpls_limit on agent side
                   3. Create 10 VNs with route target and 1 VM in each VN on any one compute
                   4. Verify that only 600000 nh_indexes are on agent side
                   5. Verify ping between any two VMs
                   6. Set 800000 nh limit on agent side
                   7. Verify that 800000 nh_indexes are on agent side
                   8. Verify ping between any two VMs
        Pass criteria: Nh limit should be properly set and nh indexes should be same in number as nh_limit
        Maintainer: rsetru@juniper.net
        '''
        nh_limit1 = '600000'
        nh_limit2 = '800000'
        mpls_limit = '10000'
        count = self.get_prefix_count(nh_limit2, self.vn_count)
        nh_index_Range1 = []
        nh_index_Range1.append(int(nh_limit1) - 5)
        nh_index_Range1.append(int(nh_limit1))
        nh_index_Range2 = []
        nh_index_Range2.append(int(nh_limit2) - 5)
        nh_index_Range2.append(int(nh_limit2))
        compute = self.get_compute()
        for i in range(len(self.logicalsystem)):
            self.add_routes_using_rtgen_mx_side(
                self.logicalsystem[i], self.table[i], self.subnet, count)
            self.addCleanup(self.remove_routes_mx_side, self.logicalsystem[i])
        self.set_nh_limit(nh_limit=nh_limit1, compute=compute,
                          mpls_limit=mpls_limit, modify=True)
        self.create_vmvn_for_nhlimittest(compute, self.vn_count)
        self.verify_nh_indexes(compute, nh_index_Range1)
        self.ping_after_nh_index()
        self.reset_nh_limit(compute=compute)
        self.set_nh_limit(nh_limit=nh_limit2, compute=compute, mpls_limit=mpls_limit, modify=True)
        self.addCleanup(self.reset_nh_limit, compute=compute)
        self.verify_nh_indexes(compute, nh_index_Range2)
        self.ping_after_nh_index()

    @test.attr(type=['nh_limit_test'])
    @preposttest_wrapper
    def test_default_nh_limit(self):
        '''
        Description: Verify default nh_limit and verify the number of nh indexes on agent side.
        Test Steps:
                   1. Verify default nh_limit as 524288 and default mpls_limit on agent side
                   2. Pump routes on mx side
                   3. Create 10 VNs with route target and 1 VM in each VN on any one compute
                   4. Verify 524288 nh_indexes on agent side
                   5. Verify ping between any two VMs
        Pass criteria: Nh limit should be properly set and nh indexes should be same in number as nh_limit
        Maintainer: rsetru@juniper.net
        '''
        nh_limit = '524288'
        mpls_limit = '5120'
        count = self.get_prefix_count(nh_limit, self.vn_count)
        nh_index_Range = []
        nh_index_Range.append(int(nh_limit) - 10)
        nh_index_Range.append(int(nh_limit))
        compute = self.get_compute()
        self.verify_nh_limit(compute, nh_limit, mpls_limit)
        for i in range(len(self.logicalsystem)):
            self.add_routes_using_rtgen_mx_side(
                self.logicalsystem[i], self.table[i], self.subnet, count)
            self.addCleanup(self.remove_routes_mx_side, self.logicalsystem[i])
        self.create_vmvn_for_nhlimittest(compute, self.vn_count)
        self.verify_nh_indexes(compute, nh_index_Range)
        self.ping_after_nh_index()


class TestNHLimitDpdk(TestNHLimit):
    subnet = '11.1.1.1/32'
    logicalsystem = ['nh_LS100', 'nh_LS200']
    table = ['_proj_LS100.inet.0', '_proj_LS200.inet.0']
    agent_mode = 'dpdk'
    vn_count = 10

    @test.attr(type=['nh_limit_test'])
    @preposttest_wrapper
    def test_nh_limit_one_million(self):
        '''
        Description: Change nhLimit to 1 million and verify the number of nh indexes on agent side.
        Test Steps:
                   1. Pump routes on mx side
                   2. Set 1 million nh limit on agent side
                   3. Create 10 VNs with route target and 1 VM in each VN on any one compute
                   4. Verify 1 million nh_indexes on agent side
                   5. Verify ping between any two VMs
        Pass criteria: Nh limit should be properly set and nh indexes should be same in number as nh_limit
        Maintainer: rsetru@juniper.net
        '''
        nh_limit = '1000000'
        count = self.get_prefix_count(nh_limit, self.vn_count)
        nh_index_Range = []
        nh_index_Range.append(int(nh_limit) - 5)
        nh_index_Range.append(int(nh_limit))
        compute = self.get_compute(self.agent_mode)
        for i in range(len(self.logicalsystem)):
            self.add_routes_using_rtgen_mx_side(
                self.logicalsystem[i], self.table[i], self.subnet, count)
            self.addCleanup(self.remove_routes_mx_side, self.logicalsystem[i])
        self.set_nh_limit(nh_limit=nh_limit, compute=compute,
                          agent_mode=self.agent_mode, modify=True)
        self.addCleanup(self.reset_nh_limit, compute=compute,
                        agent_mode=self.agent_mode)
        self.create_vmvn_for_nhlimittest(compute, self.vn_count)
        self.verify_nh_indexes(compute, nh_index_Range)
        self.ping_after_nh_index()

    @test.attr(type=['nh_limit_test'])
    @preposttest_wrapper
    def test_nh_limit_change(self):
        '''
        Test Steps:
                   1. Pump routes 800000 on mx side
                   2. Set 600000 nh limit on agent side
                   3. Create 10 VNs with route target and 1 VM in each VN on any one compute
                   4. Verify that only 600000 nh_indexes are on agent side
                   5. Verify ping between any two VMs
                   6. Set 800000 nh limit on agent side
                   7. Verify that 800000 nh_indexes are on agent side
                   8. Verify ping between any two VMs
        Pass criteria: Nh limit should be properly set and nh indexes should be same in number as nh_limit
        Maintainer: rsetru@juniper.net
        '''
        nh_limit1 = '600000'
        nh_limit2 = '800000'
        count = self.get_prefix_count(nh_limit2, self.vn_count)
        nh_index_Range1 = []
        nh_index_Range1.append(int(nh_limit1) - 5)
        nh_index_Range1.append(int(nh_limit1))
        nh_index_Range2 = []
        nh_index_Range2.append(int(nh_limit2) - 5)
        nh_index_Range2.append(int(nh_limit2))
        compute = self.get_compute(self.agent_mode)
        for i in range(len(self.logicalsystem)):
            self.add_routes_using_rtgen_mx_side(
                self.logicalsystem[i], self.table[i], self.subnet, count)
            self.addCleanup(self.remove_routes_mx_side, self.logicalsystem[i])
        self.set_nh_limit(nh_limit=nh_limit1, compute=compute,
                          agent_mode=self.agent_mode, modify=True)
        self.create_vmvn_for_nhlimittest(compute, self.vn_count)
        self.verify_nh_indexes(compute, nh_index_Range1)
        self.ping_after_nh_index()
        self.reset_nh_limit(compute=compute, agent_mode=self.agent_mode)
        self.set_nh_limit(nh_limit=nh_limit2, compute=compute,
                          agent_mode=self.agent_mode, modify=True)
        self.addCleanup(self.reset_nh_limit, compute=compute,
                        agent_mode=self.agent_mode)
        self.verify_nh_indexes(compute, nh_index_Range2)
        self.ping_after_nh_index()

    @test.attr(type=['nh_limit_test'])
    @preposttest_wrapper
    def test_nh_limit_change_with_mpls(self):
        '''
        Test Steps:
                   1. Pump routes 800000 on mx side
                   2. Set 600000 nh limit and 10000 mpls_limit on agent side
                   3. Create 10 VNs with route target and 1 VM in each VN on any one compute
                   4. Verify that only 600000 nh_indexes are on agent side
                   5. Verify ping between any two VMs
                   6. Set 800000 nh limit on agent side
                   7. Verify that 800000 nh_indexes are on agent side
                   8. Verify ping between any two VMs
        Pass criteria: Nh limit should be properly set and nh indexes should be same in number as nh_limit
        Maintainer: rsetru@juniper.net
        '''
        nh_limit1 = '600000'
        nh_limit2 = '800000'
        mpls_limit = '10000'
        count = self.get_prefix_count(nh_limit2, self.vn_count)
        nh_index_Range1 = []
        nh_index_Range1.append(int(nh_limit1) - 5)
        nh_index_Range1.append(int(nh_limit1))
        nh_index_Range2 = []
        nh_index_Range2.append(int(nh_limit2) - 5)
        nh_index_Range2.append(int(nh_limit2))
        compute = self.get_compute(self.agent_mode)
        for i in range(len(self.logicalsystem)):
            self.add_routes_using_rtgen_mx_side(
                self.logicalsystem[i], self.table[i], self.subnet, count)
            self.addCleanup(self.remove_routes_mx_side, self.logicalsystem[i])
        self.set_nh_limit(nh_limit=nh_limit1, compute=compute,
                          agent_mode=self.agent_mode, mpls_limit=mpls_limit, modify=True)
        self.create_vmvn_for_nhlimittest(compute, self.vn_count)
        self.verify_nh_indexes(compute, nh_index_Range1)
        self.ping_after_nh_index()
        self.reset_nh_limit(compute=compute, agent_mode=self.agent_mode)
        self.set_nh_limit(nh_limit=nh_limit2, compute=compute,
                          agent_mode=self.agent_mode, mpls_limit=mpls_limit, modify=True)
        self.addCleanup(self.reset_nh_limit, compute=compute,
                        agent_mode=self.agent_mode)
        self.verify_nh_indexes(compute, nh_index_Range2)
        self.ping_after_nh_index()

    @test.attr(type=['nh_limit_test'])
    @preposttest_wrapper
    def test_default_nh_limit(self):
        '''
        Description: Verify default nh_limit and verify the number of nh indexes on agent side.
        Test Steps:
                   1. Verify default nh_limit as 524288 and default mpls_limit on agent side
                   2. Pump routes on mx side
                   3. Create 10 VNs with route target and 1 VM in each VN on any one compute
                   4. Verify 524288 nh_indexes on agent side
                   5. Verify ping between any two VMs
        Pass criteria: Nh limit should be properly set and nh indexes should be same in number as nh_limit
        Maintainer: rsetru@juniper.net
        '''
        nh_limit = '524288'
        mpls_limit = '5120'
        count = self.get_prefix_count(nh_limit, self.vn_count)
        nh_index_Range = []
        nh_index_Range.append(int(nh_limit) - 10)
        nh_index_Range.append(int(nh_limit))
        compute = self.get_compute(self.agent_mode)
        self.verify_nh_limit(compute, nh_limit, mpls_limit)
        for i in range(len(self.logicalsystem)):
            self.add_routes_using_rtgen_mx_side(
                self.logicalsystem[i], self.table[i], self.subnet, count)
            self.addCleanup(self.remove_routes_mx_side, self.logicalsystem[i])
        self.create_vmvn_for_nhlimittest(compute, self.vn_count)
        self.verify_nh_indexes(compute, nh_index_Range)
        self.ping_after_nh_index()
