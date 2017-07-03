"""Intf mirroring Regression tests."""
import os
import unittest
import fixtures
import testtools
import test

from common.connections import ContrailConnections
from common.contrail_test_init import ContrailTestInit
from tcutils.wrappers import preposttest_wrapper
from common.intf_mirroring.verify import VerifyIntfMirror
from base import BaseIntfMirrorTest

class TestIntfMirror(BaseIntfMirrorTest, VerifyIntfMirror):

    @classmethod
    def setUpClass(cls):
        super(TestIntfMirror, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_intf_mirror_src_cn1vn1_dst_cn2vn1_analyzer_cn3vn1(self):
        """Validate the interface mirroring
        src vm, dst vm and analyzer vm on different CNs, all in same VN
        """
        return self.verify_intf_mirroring_src_on_cn1_vn1_dst_on_cn2_vn1_analyzer_on_cn3_vn1()

    @test.attr(type=['ci_sanity_WIP', 'sanity', 'quick_sanity'])
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
