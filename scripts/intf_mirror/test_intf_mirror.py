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
    def test_intf_mirroring(self):
        """Validate the intf mirroring"""
        return self.verify_intf_mirroring()

if __name__ == '__main__':
    unittest.main()
