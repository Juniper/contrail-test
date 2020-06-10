"""Intf mirroring IPv6 Regression tests."""
# Written by 	: ankitja@juniper.net
# Maintained by : ankitja@juniper.net

import os
import unittest
import fixtures
import testtools
import test

from common.connections import ContrailConnections
from common.contrail_test_init import ContrailTestInit
from tcutils.wrappers import preposttest_wrapper
from common.intf_mirroring.verify import VerifyIntfMirror
from .base import BaseIntfMirrorTest

class TestIntfMirror6(BaseIntfMirrorTest, VerifyIntfMirror):

    @classmethod
    def setUpClass(cls):
        super(TestIntfMirror6, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_juniper_header6(self):
        """Validate the presence of juniper header IPv6 cases
        1) Check pkts get mirrored from both sub intf and parent intf when enabled on both
        2) Verify if the juniper header is correct
        3) Verify if the inner header is correct

        Maintainer : ankitja@juniper.net
        """
        return self.verify_juniper_header_testcase(header=2, ipv6=True)
        
    @preposttest_wrapper
    def test_juniper_header6_ingress(self):
        """Validate the presence of juniper header with ingress IPv6 cases
        1) Check pkts get mirrored from both sub intf and parent intf when enabled on both
        2) Verify if the juniper header is correct
        3) Verify if the inner header is correct
        
        Maintainer : ankitja@juniper.net

        """
        return self.verify_juniper_header_testcase(header=2, direction='ingress', ipv6=True)

    @preposttest_wrapper
    def test_juniper_header6_egress(self):
        """Validate the presence of juniper header with egress IPv6 cases
        1) Check pkts get mirrored from both sub intf and parent intf when enabled on both
        2) Verify if the juniper header is correct
        3) Verify if the inner header is correct
        
        Maintainer : ankitja@juniper.net

        """
        return self.verify_juniper_header_testcase(header=2, direction='egress', ipv6=True)

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_juniper_header6_without_header_ingress(self):
        """Validate the presence of no juniper header IPv6 cases
        1) Check pkts get mirrored from both sub intf and parent intf when enabled on both
        2) Verify if the juniper header is absent
        3) Verify if the inner header is correct

        Maintainer : ankitja@juniper.net

        """
        return self.verify_juniper_header_testcase(header=3, direction='ingress', ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn1vn1_dst_cn2vn1_analyzer_cn3vn1(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm and analyzer vm on different CNs, all in same VN
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn3_vn1(ipv6=True)

    @test.attr(type=['cb_sanity', 'ci_sanity_WIP', 'sanity', 'quick_sanity'])
    @preposttest_wrapper
    def test_intf_mirror6_src_cn1vn1_dst_cn2vn2_analyzer_cn3vn3(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm and analyzer vm on different CNs, all in different VNs

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn3_vn3(ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn1vn1_dst_cn2vn1_analyzer_cn3vn2(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm and analyzer vm on different CNs, src and dst in vn1, analyzer in vn2

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn3_vn2(ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn1vn1_dst_cn2vn2_analyzer_cn3vn1(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm and analyzer vm on different CNs, src and analyzer in vn1, dst in vn2

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn3_vn1(ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn1vn1_dst_cn2vn2_analyzer_cn3vn2(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm and analyzer vm on different CNs, src in vn1, dst and analyzer in vn2

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn3_vn2(ipv6=True)


    @preposttest_wrapper
    def test_intf_mirror6_with_subintf_src_cn1vn1_dst_cn2vn1_analyzer_cn3vn1(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm and analyzer vm on different CNs, all in same VN
        when src vmi, dst vmi and analyzer vmi are sub interfaces

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn3_vn1(sub_intf=True,ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_with_subintf_src_cn1vn1_dst_cn2vn1_analyzer_cn3vn2(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm and analyzer vm on different CNs, src and dst in vn1, analyzer in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn3_vn2(sub_intf=True,ipv6=True)


    @preposttest_wrapper
    def test_intf_mirror6_src_cn1vn1_dst_cn1vn1_analyzer_cn1vn1(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm and analyzer vm on same CN, all in same VN

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn1(ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn1vn1_dst_cn1vn2_analyzer_cn1vn3(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm and analyzer vm on same CN, all in different VNs

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn3(ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn1vn1_dst_cn1vn1_analyzer_cn1vn2(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm and analyzer vm on same CN, src and dst in vn1, analyzer in vn2

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn2(ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn1vn1_dst_cn1vn2_analyzer_cn1vn1(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm and analyzer vm on same CN, src and analyzer in vn1, dst in vn2

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn1(ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn1vn1_dst_cn1vn2_analyzer_cn1vn2(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm and analyzer vm on same CN, src in vn1, dst and analyzer in vn2

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn2(ipv6=True)


    @preposttest_wrapper
    def test_intf_mirror6_with_subintf_src_cn1vn1_dst_cn1vn1_analyzer_cn1vn1(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm and analyzer vm on same CN, all in same VN
        when src vmi, dst vmi and analyzer vmi are sub interfaces

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn1(sub_intf=True,ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_with_subintf_src_cn1vn1_dst_cn1vn1_analyzer_cn1vn2(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm and analyzer vm on same CN, src and dst in vn1, analyzer in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn2(sub_intf=True,ipv6=True)


    @preposttest_wrapper
    def test_intf_mirror6_src_cn1vn1_dst_cn1vn1_analyzer_cn2vn1(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm on same CN and analyzer vm on different CN, all in same VN

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn2_vn1(ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn1vn1_dst_cn1vn2_analyzer_cn2vn3(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm on same CN and analyzer vm on different CN, all in different VNs

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn2_vn3(ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn1_vn1dst_cn1vn1_analyzer_cn2vn2(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm on same CN and analyzer vm on different CN, src and dst in vn1, analyzer in vn2

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn2_vn2(ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn1vn1_dst_cn1vn2_analyzer_cn2vn1(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm on same CN and analyzer vm on different CN, src and analyzer in vn1, dst in vn2

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn2_vn1(ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn1vn1_dst_cn1vn2_analyzer_cn2vn2(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm on same CN and analyzer vm on different CN, src in vn1, dst and analyzer in vn2

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn2_analyzer_on_cn2_vn2(ipv6=True)


    @preposttest_wrapper
    def test_intf_mirror6_with_subintf_src_cn1vn1_dst_cn1vn1_analyzer_cn2vn1(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm on same CN and analyzer vm on different CN, all in same VN
        when src vmi, dst vmi and analyzer vmi are sub interfaces

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn2_vn1(sub_intf=True,ipv6=True)


    @preposttest_wrapper
    def test_intf_mirror6_with_subintf_src_cn1vn1_dst_cn1vn1_analyzer_cn2vn2(self):
        """Validate the interface mirroring IPv6
        src vm, dst vm on same CN and analyzer vm on different CN, src and dst in vn1, analyzer in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn1_vn1_analyzer_on_cn2_vn2(sub_intf=True,ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn1vn1_dst_cn2vn1_analyzer_cn1vn1(self):
        """Validate the interface mirroring IPv6
        src vm, analyzer vm on same CN and dst vm on different CN, all in same VN
        
        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn1_vn1(ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn1vn1_dst_cn2vn2_analyzer_cn1vn3(self):
        """Validate the interface mirroring IPv6
        src vm, analyzer vm on same CN and dst vm on different CN, all in different VNs

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn1_vn3(ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn1vn1_dst_cn2vn1_analyzer_cn1vn2(self):
        """Validate the interface mirroring IPv6
        src vm, analyzer vm on same CN and dst vm on different CN, src and dst in vn1, analyzer in vn2

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn1_vn2(ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn1vn1_dst_cn2vn2_analyzer_cn1vn1(self):
        """Validate the interface mirroring IPv6
        src vm, analyzer vm on same CN and dst vm on different CN, src and analyzer in vn1, dst in vn2

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn1_vn1(ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn1vn1_dst_cn2vn2_analyzer_cn1vn2(self):
        """Validate the interface mirroring IPv6
        src vm, analyzer vm on same CN and dst vm on different CN, src in vn1, dst and analyzer in vn2

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn2_analyzer_on_cn1_vn2(ipv6=True)



    @preposttest_wrapper
    def test_intf_mirror6_with_subintf_src_cn1vn1_dst_cn2vn1_analyzer_cn1vn1(self):
        """Validate the interface mirroring IPv6
        src vm, analyzer vm on same CN and dst vm on different CN, all in same VN
        when src vmi, dst vmi and analyzer vmi are sub interfaces

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn1_vn1(sub_intf=True,ipv6=True)


    @preposttest_wrapper
    def test_intf_mirror6_with_subintf_src_cn1vn1_dst_cn2vn1_analyzer_cn1vn2(self):
        """Validate the interface mirroring IPv6
        src vm, analyzer vm on same CN and dst vm on different CN, src and dst in vn1, analyzer in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn1_vn2(sub_intf=True,ipv6=True)


    @preposttest_wrapper
    def test_intf_mirror6_src_cn2vn1_dst_cn1vn1_analyzer_cn1vn1(self):
        """Validate the interface mirroring IPv6
        dst vm, analyzer vm on same CN and src vm on different CN, all in same VN

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn1(ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn2vn1_dst_cn1vn2_analyzer_cn1vn3(self):
        """Validate the interface mirroring IPv6
        dst vm, analyzer vm on same CN and src vm on different CN, all in different VNs

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn3(ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn2vn1_dst_cn1vn1_analyzer_cn1vn2(self):
        """Validate the interface mirroring IPv6
        dst vm, analyzer vm on same CN and src vm on different CN, src and dst in vn1, analyzer in vn2

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn2(ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn2vn1_dst_cn1vn2_analyzer_cn1vn1(self):
        """Validate the interface mirroring IPv6
        dst vm, analyzer vm on same CN and src vm on different CN, src and analyzer in vn1, dst in vn2

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn1(ipv6=True)

    @preposttest_wrapper
    def test_intf_mirror6_src_cn2vn1_dst_cn1vn2_analyzer_cn1vn2(self):
        """Validate the interface mirroring IPv6
        dst vm, analyzer vm on same CN and src vm on different CN, src in vn1, dst and analyzer in vn2

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn2_analyzer_on_cn1_vn2(ipv6=True)


    @preposttest_wrapper
    def test_intf_mirror6_with_subintf_src_cn2vn1_dst_cn1vn1_analyzer_cn1vn1(self):
        """Validate the interface mirroring IPv6
        dst vm, analyzer vm on same CN and src vm on different CN, all in same VN
        when src vmi, dst vmi and analyzer vmi are sub interfaces

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn1(sub_intf=True,ipv6=True)


    @preposttest_wrapper
    def test_intf_mirror6_with_subintf_src_cn2vn1_dst_cn1vn1_analyzer_cn1vn2(self):
        """Validate the interface mirroring IPv6
        dst vm, analyzer vm on same CN and src vm on different CN, src and dst in vn1, analyzer in vn2
        when src vmi, dst vmi and analyzer vmi are sub interfaces

        Maintainer : ankitja@juniper.net

        """
        return self.verify_intf_mirroring_src_on_cn2_vn1_dst_on_cn1_vn1_analyzer_on_cn1_vn2(sub_intf=True,ipv6=True)

if __name__ == '__main__':
    unittest.main()
