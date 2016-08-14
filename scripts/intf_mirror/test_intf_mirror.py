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

    @test.attr(type=['ci_sanity_WIP', 'sanity', 'quick_sanity'])
    @preposttest_wrapper
    def test_intf_mirroring_src_on_cn1_dst_on_cn2_analyzer_on_cn3(self):
        """Validate the intf mirroring
        src vm, dst vm and analyzer vm on different CNs
        """
        return self.verify_intf_mirroring_1()

    @preposttest_wrapper
    def test_intf_mirroring_src_on_cn1_dst_on_cn1_analyzer_on_cn1(self):
        """Validate the intf mirroring
        src vm, dst vm and analyzer vm on same CN
        """
        return self.verify_intf_mirroring_2()

    @preposttest_wrapper
    def test_intf_mirroring_src_on_cn1_dst_on_cn1_analyzer_on_cn2(self):
        """Validate the intf mirroring
        src vm, dst vm on same CN and analyzer vm on different CN
        """
        return self.verify_intf_mirroring_3()

    @preposttest_wrapper
    def test_intf_mirroring_src_on_cn1_dst_on_cn2_analyzer_on_cn1(self):
        """Validate the intf mirroring
        src vm, analyzer on same CN and dst vm on different CN
        """
        return self.verify_intf_mirroring_4()

    @preposttest_wrapper
    def test_intf_mirroring_src_on_cn2_dst_on_cn1_analyzer_on_cn1(self):
        """Validate the intf mirroring
        dst vm, analyzer vm on same CN and src vm on different CN
        """
        return self.verify_intf_mirroring_5()

if __name__ == '__main__':
    unittest.main()
