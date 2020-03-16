"""Intf mirroring Regression tests."""
from __future__ import absolute_import
from .base import BaseIntfMirrorTest
import os
import unittest
import fixtures
import testtools
import test

from common.connections import ContrailConnections
from common.contrail_test_init import ContrailTestInit
from tcutils.wrappers import preposttest_wrapper
from common.intf_mirroring.verify import VerifyIntfMirror

class TestIntfMirror(BaseIntfMirrorTest, VerifyIntfMirror):

    @classmethod
    def setUpClass(cls):
        super(TestIntfMirror, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @test.attr(type=['ci_sanity_WIP', 'sanity', 'quick_sanity'])
    @preposttest_wrapper
    def test_intf_mirroring_disable_enable_scenarios(self):
        """Validate the interface mirroring
        Validate enable/disable combinations on parent/sub interface
        1) Check pkts get mirrored from both sub intf and parent intf when enabled on both
        2) Disable on sub intf and check pkts from parent still get mirrored
        3) Enable on sub intf and verify step 1
        4) Disable on parent and check pkts from sub intf still get mirrored
        5) Enable on parent and verify step 1
        """
        return self.verify_intf_mirroring_disable_enable_scenarios()

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_juniper_header(self):
        """Validate the presence of juniper header
        1) Check pkts get mirrored from both sub intf and parent intf when enabled on both
        2) Verify if the juniper header is correct
        3) Verify if the inner header is correct
        """
        return self.verify_juniper_header_testcase(header = 2)

    @preposttest_wrapper
    def test_juniper_header_ingress(self, direction = 'ingress'):
        """Validate the presence of juniper header with ingress
        1) Check pkts get mirrored from both sub intf and parent intf when enabled on both
        2) Verify if the juniper header is correct
        3) Verify if the inner header is correct
        """
        return self.verify_juniper_header_testcase(header = 2, direction = direction)

    @preposttest_wrapper
    def test_juniper_header_egress(self, direction = 'egress'):
        """Validate the presence of juniper header with egress
        1) Check pkts get mirrored from both sub intf and parent intf when enabled on both
        2) Verify if the juniper header is correct
        3) Verify if the inner header is correct
        """
        return self.verify_juniper_header_testcase(header = 2, direction = direction)

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_juniper_header_without_header_ingress(self, direction = 'ingress'):
        """Validate the presence of no juniper header
        1) Check pkts get mirrored from both sub intf and parent intf when enabled on both
        2) Verify if the juniper header is absent
        3) Verify if the inner header is correct
        """
        return self.verify_juniper_header_testcase(header = 3, direction = direction)

    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn2vn1_analyzer_cn3vn1(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on different CNs, all in same VN
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn3_vn1()

    @test.attr(type=['cb_sanity', 'ci_sanity_WIP', 'sanity', 'quick_sanity'])
    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn2vn2_analyzer_cn3vn3(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on different CNs, all in different VNs
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn3_vn3()

    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn2vn1_analyzer_cn3vn2(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on different CNs, src and dst in vn1, analyzer in vn2
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn3_vn2()

    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn2vn2_analyzer_cn3vn1(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on different CNs, src and analyzer in vn1, dst in vn2
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn3_vn1()

    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn2vn2_analyzer_cn3vn2(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on different CNs, src in vn1, dst and analyzer in vn2
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn3_vn2()


    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn2vn1_analyzer_cn3vn1(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on different CNs, all in same VN
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn3_vn1(sub_intf=True)

    @test.attr(type=['ci_sanity_WIP', 'sanity', 'quick_sanity'])
    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn2vn2_analyzer_cn3vn3(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on different CNs, all in different VNs
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn3_vn3(sub_intf=True)

    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn2vn1_analyzer_cn3vn2(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on different CNs, src and dst in vn1, analyzer in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn3_vn2(sub_intf=True)

    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn2vn2_analyzer_cn3vn1(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on different CNs, src and analyzer in vn1, dst in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn3_vn1(sub_intf=True)

    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn2vn2_analyzer_cn3vn2(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on different CNs, src in vn1, dst and analyzer in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn3_vn2(sub_intf=True)



    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn1vn1_analyzer_cn1vn1(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on same CN, all in same VN
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn1()

    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn1vn2_analyzer_cn1vn3(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on same CN, all in different VNs
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn3()

    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn1vn1_analyzer_cn1vn2(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on same CN, src and dst in vn1, analyzer in vn2
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn2()

    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn1vn2_analyzer_cn1vn1(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on same CN, src and analyzer in vn1, dst in vn2
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn1()

    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn1vn2_analyzer_cn1vn2(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on same CN, src in vn1, dst and analyzer in vn2
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn2()


    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn1vn1_analyzer_cn1vn1(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on same CN, all in same VN
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn1(sub_intf=True)

    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn1vn2_analyzer_cn1vn3(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on same CN, all in different VNs
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn3(sub_intf=True)

    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn1vn1_analyzer_cn1vn2(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on same CN, src and dst in vn1, analyzer in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn2(sub_intf=True)

    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn1vn2_analyzer_cn1vn1(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on same CN, src and analyzer in vn1, dst in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn1(sub_intf=True)

    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn1vn2_analyzer_cn1vn2(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on same CN, src in vn1, dst and analyzer in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn2(sub_intf=True)



    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn1vn1_analyzer_cn2vn1(self):
        """Validate the interface mirroring
        src vm, dst vm on same CN and analyzer vm on different CN, all in same VN
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn2_vn1()

    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn1vn2_analyzer_cn2vn3(self):
        """Validate the interface mirroring
        src vm, dst vm on same CN and analyzer vm on different CN, all in different VNs
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn2_vn3()

    @preposttest_wrapper
    def test_intf_mirror_src_cn1_vn1dst_cn1vn1_analyzer_cn2vn2(self):
        """Validate the interface mirroring
        src vm, dst vm on same CN and analyzer vm on different CN, src and dst in vn1, analyzer in vn2
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn2_vn2()

    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn1vn2_analyzer_cn2vn1(self):
        """Validate the interface mirroring
        src vm, dst vm on same CN and analyzer vm on different CN, src and analyzer in vn1, dst in vn2
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn2_vn1()

    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn1vn2_analyzer_cn2vn2(self):
        """Validate the interface mirroring
        src vm, dst vm on same CN and analyzer vm on different CN, src in vn1, dst and analyzer in vn2
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn2_vn2()


    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn1vn1_analyzer_cn2vn1(self):
        """Validate the interface mirroring
        src vm, dst vm on same CN and analyzer vm on different CN, all in same VN
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn2_vn1(sub_intf=True)

    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn1vn2_analyzer_cn2vn3(self):
        """Validate the interface mirroring
        src vm, dst vm on same CN and analyzer vm on different CN, all in different VNs
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn2_vn3(sub_intf=True)

    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn1vn1_analyzer_cn2vn2(self):
        """Validate the interface mirroring
        src vm, dst vm on same CN and analyzer vm on different CN, src and dst in vn1, analyzer in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn2_vn2(sub_intf=True)

    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn1vn2_analyzer_cn2vn1(self):
        """Validate the interface mirroring
        src vm, dst vm on same CN and analyzer vm on different CN, src and analyzer in vn1, dst in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn2_vn1(sub_intf=True)

    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn1vn2_analyzer_cn2vn2(self):
        """Validate the interface mirroring
        src vm, dst vm on same CN and analyzer vm on different CN, src in vn1, dst and analyzer in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn2_vn2(sub_intf=True)




    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn2vn1_analyzer_cn1vn1(self):
        """Validate the interface mirroring
        src vm, analyzer vm on same CN and dst vm on different CN, all in same VN
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn1_vn1()

    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn2vn2_analyzer_cn1vn3(self):
        """Validate the interface mirroring
        src vm, analyzer vm on same CN and dst vm on different CN, all in different VNs
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn1_vn3()

    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn2vn1_analyzer_cn1vn2(self):
        """Validate the interface mirroring
        src vm, analyzer vm on same CN and dst vm on different CN, src and dst in vn1, analyzer in vn2
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn1_vn2()

    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn2vn2_analyzer_cn1vn1(self):
        """Validate the interface mirroring
        src vm, analyzer vm on same CN and dst vm on different CN, src and analyzer in vn1, dst in vn2
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn1_vn1()

    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn2vn2_analyzer_cn1vn2(self):
        """Validate the interface mirroring
        src vm, analyzer vm on same CN and dst vm on different CN, src in vn1, dst and analyzer in vn2
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn1_vn2()



    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn2vn1_analyzer_cn1vn1(self):
        """Validate the interface mirroring
        src vm, analyzer vm on same CN and dst vm on different CN, all in same VN
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn1_vn1(sub_intf=True)

    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn2vn2_analyzer_cn1vn3(self):
        """Validate the interface mirroring
        src vm, analyzer vm on same CN and dst vm on different CN, all in different VNs
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn1_vn3(sub_intf=True)

    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn2vn1_analyzer_cn1vn2(self):
        """Validate the interface mirroring
        src vm, analyzer vm on same CN and dst vm on different CN, src and dst in vn1, analyzer in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn1_vn2(sub_intf=True)

    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn2vn2_analyzer_cn1vn1(self):
        """Validate the interface mirroring
        src vm, analyzer vm on same CN and dst vm on different CN, src and analyzer in vn1, dst in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn1_vn1(sub_intf=True)

    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn1vn1_dst_cn2vn2_analyzer_cn1vn2(self):
        """Validate the interface mirroring
        src vm, analyzer vm on same CN and dst vm on different CN, src in vn1, dst and analyzer in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn1_vn2(sub_intf=True)



    @preposttest_wrapper
    def test_intf_mirror_src_cn2vn1_dst_cn1vn1_analyzer_cn1vn1(self):
        """Validate the interface mirroring
        dst vm, analyzer vm on same CN and src vm on different CN, all in same VN
        """
        return self.verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn1()

    @preposttest_wrapper
    def test_intf_mirror_src_cn2vn1_dst_cn1vn2_analyzer_cn1vn3(self):
        """Validate the interface mirroring
        dst vm, analyzer vm on same CN and src vm on different CN, all in different VNs
        """
        return self.verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn3()

    @preposttest_wrapper
    def test_intf_mirror_src_cn2vn1_dst_cn1vn1_analyzer_cn1vn2(self):
        """Validate the interface mirroring
        dst vm, analyzer vm on same CN and src vm on different CN, src and dst in vn1, analyzer in vn2
        """
        return self.verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn2()

    @preposttest_wrapper
    def test_intf_mirror_src_cn2vn1_dst_cn1vn2_analyzer_cn1vn1(self):
        """Validate the interface mirroring
        dst vm, analyzer vm on same CN and src vm on different CN, src and analyzer in vn1, dst in vn2
        """
        return self.verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn1()

    @preposttest_wrapper
    def test_intf_mirror_src_cn2vn1_dst_cn1vn2_analyzer_cn1vn2(self):
        """Validate the interface mirroring
        dst vm, analyzer vm on same CN and src vm on different CN, src in vn1, dst and analyzer in vn2
        """
        return self.verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn2()


    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn2vn1_dst_cn1vn1_analyzer_cn1vn1(self):
        """Validate the interface mirroring
        dst vm, analyzer vm on same CN and src vm on different CN, all in same VN
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn1(sub_intf=True)

    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn2vn1_dst_cn1vn2_analyzer_cn1vn3(self):
        """Validate the interface mirroring
        dst vm, analyzer vm on same CN and src vm on different CN, all in different VNs
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn3(sub_intf=True)

    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn2vn1_dst_cn1vn1_analyzer_cn1vn2(self):
        """Validate the interface mirroring
        dst vm, analyzer vm on same CN and src vm on different CN, src and dst in vn1, analyzer in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn2(sub_intf=True)

    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn2vn1_dst_cn1vn2_analyzer_cn1vn1(self):
        """Validate the interface mirroring
        dst vm, analyzer vm on same CN and src vm on different CN, src and analyzer in vn1, dst in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn1(sub_intf=True)

    @preposttest_wrapper
    def test_intf_mirror_with_subintf_src_cn2vn1_dst_cn1vn2_analyzer_cn1vn2(self):
        """Validate the interface mirroring
        dst vm, analyzer vm on same CN and src vm on different CN, src in vn1, dst and analyzer in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces
        """
        return self.verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn2(sub_intf=True)


if __name__ == '__main__':
    unittest.main()
