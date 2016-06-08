import unittest
from tcutils.wrappers import preposttest_wrapper
from vnc_api.vnc_api import NoIdError
from vnc_api.vnc_api import VncApi
from scripts.securitygroup.verify import VerifySecGroup
from policy_test import PolicyFixture
from vn_test import MultipleVNFixture
from vm_test import MultipleVMFixture
from base import Md5Base
from common.policy.config import ConfigPolicy
from security_group import SecurityGroupFixture,get_secgrp_id_from_name
from vn_test import VNFixture
from vm_test import VMFixture
from tcutils.topo.topo_helper import *
import os
import sys
from tcutils.topo.sdn_topo_setup import *
import test
from tcutils.tcpdump_utils import *
from time import sleep
from tcutils.util import get_random_name
from tcutils.contrail_status_check import *

class TestMd5tests(Md5Base, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(TestMd5tests, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestMd5tests, cls).tearDownClass()

    def is_test_applicable(self):
        if len(self.inputs.ext_routers) < 1:            
            return (False, 'Atleast 1 mx is needed for different md5 keys checking')
        if not self.inputs.use_devicemanager_for_md5:
            return (False, 'Testbed is not enabled to test with Device Manager')
        return (True, None)

    def setUp(self):
        super(TestMd5tests, self).setUp()
        result = self.is_test_applicable()
        if result[0]:
            self.is_mx_present=True
            self.config_basic(self.is_mx_present)
            uuid = self.vnc_lib.bgp_routers_list()
            self.uuid = str(uuid)
            self.list_uuid = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', self.uuid)
        else:
            return

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_create_md5(self):
        """
        Description: Verify md5 with allow specific protocol on all ports and policy with allow all between VN's
        """
        assert self.test_create_MD5()
    #end create_md5

    @preposttest_wrapper
    def test_add_delete_md5(self):
        """
        Description: Verify md5 with add,delete and specific protocol on all ports and policy with allow all between VN's
        """
        assert self.test_add_delete_MD5()
    #end add_delete_md5

    @preposttest_wrapper
    def test_different_keys_md5(self):
        """
        Description: Verify md5 with add,delete and specific protocol on all ports and policy with allow all between VN's
        """
        assert self.test_different_keys_MD5()
    #end different_keys_md5

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_check_per_peer(self):
        """
        Description: Verify per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """

        assert self.test_check_per_peer_md5()
    #end check_per_peer   

    @preposttest_wrapper
    def test_add_delete_per_peer(self):
        """
        Description: Verify add delete per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        assert self.test_add_delete_per_peer_md5()    
    #end add_delete_per_peer

    @preposttest_wrapper
    def test_diff_keys_per_peer(self):
        """
        Description: Verify different keys per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        assert self.test_diff_keys_per_peer_md5()
    #end diff_keys_per_peer
       
    @preposttest_wrapper
    def test_precedence_per_peer(self):
        """
        Description: Verify precedence per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        assert self.test_precedence_per_peer_md5()
    #end precedence_per_peer
    @preposttest_wrapper

    def test_iter_keys_per_peer(self):
        """
        Description: Verify iteration of same keys per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        assert self.test_iter_keys_per_peer_md5()
    #end test_iter_keys_per_peer

#end class md5tests


class TestMd5testsOnControl(TestMd5tests):

    @classmethod
    def setUpClass(cls):
        super(TestMd5testsOnControl, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestMd5testsOnControl, cls).tearDownClass()

    def is_test_applicable(self):
        if (len(self.inputs.bgp_control_ips) == 1 and len(self.inputs.ext_routers) < 1):
            return (False, 'Cluster needs 2 BGP peers to configure md5. There are no peers here')
        return (True, None)

    def setUp(self):
        super(TestMd5testsOnControl, self).setUp()
        result = self.is_test_applicable()
        if result[0]:
            self.is_mx_present=False
            self.config_basic(self.is_mx_present)
        else:
            return

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_create_md5_on_control(self):
        """
        Description: Verify md5 with allow specific protocol on all ports and policy with allow all between VN's
        """
        assert self.test_create_MD5()
    #end create_md5

    @preposttest_wrapper
    def test_add_delete_md5_on_control(self):
        """
        Description: Verify md5 with add,delete and specific protocol on all ports and policy with allow all between VN's
        """
        assert self.test_add_delete_MD5()
    #end add_delete_md5

    @preposttest_wrapper
    def test_different_keys_md5_on_control(self):
        """
        Description: Verify md5 with add,delete and specific protocol on all ports and policy with allow all between VN's
        """
        assert self.test_different_keys_MD5()
    #end different_keys_md5

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_check_per_peer_on_control(self):
        """
        Description: Verify per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """

        assert self.test_check_per_peer_md5()
    #end check_per_peer   

    @preposttest_wrapper
    def test_add_delete_per_peer_on_control(self):
        """
        Description: Verify add delete per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        assert self.test_add_delete_per_peer_md5()
    #end add_delete_per_peer

    @preposttest_wrapper
    def test_diff_keys_per_peer_on_control(self):
        """
        Description: Verify different keys per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        assert self.test_diff_keys_per_peer_md5()
    #end diff_keys_per_peer

    @preposttest_wrapper
    def test_precedence_per_peer_on_control(self):
        """
        Description: Verify precedence per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        assert self.test_precedence_per_peer_md5()
    #end precedence_per_peer
    @preposttest_wrapper

    def test_iter_keys_per_peer_on_control(self):
        """
        Description: Verify iteration of same keys per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        assert self.test_iter_keys_per_peer_md5()
    #end test_iter_keys_per_peer

#end class TestMd5testsonControl 
