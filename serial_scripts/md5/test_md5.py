from __future__ import absolute_import
from .base import Md5Base
from builtins import str
import unittest
from tcutils.wrappers import preposttest_wrapper
from vnc_api.vnc_api import NoIdError
from vnc_api.vnc_api import VncApi
from common.securitygroup.verify import VerifySecGroup
from policy_test import PolicyFixture
from vn_test import MultipleVNFixture
from vm_test import MultipleVMFixture
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
        if not list(self.inputs.dm_mx.values()):
           return (False, 'Physical routers data needs to be set in testbed.py to run this script')
        if len(self.inputs.ext_routers) < 1:            
            return (False, 'Atleast 1 mx is needed for different md5 keys checking')
        if not self.inputs.use_devicemanager_for_md5:
            return (False, 'Testbed is not enabled to test with Device Manager')
        return (True, None)

    def setUp(self):
        super(TestMd5tests, self).setUp()
        result = self.is_test_applicable()
        if result[0]:
            self.is_mx_present=False
            self.check_dm = True
            self.config_basic(self.check_dm)
            uuid = self.vnc_lib.bgp_routers_list()
            self.uuid = str(uuid)
            self.list_uuid = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', self.uuid)
            bgp_fq_name = ['default-domain', 'default-project','ip-fabric', '__default__', self.inputs.bgp_names[0]]
            self.only_control_host = self.vnc_lib.bgp_router_read(fq_name=bgp_fq_name).uuid
        else:
            return

    @preposttest_wrapper
    def create_md5(self):
        """
        Description: Verify md5 with allow specific protocol on all ports and policy with allow all between VN's
        """
        self.addCleanup(self.remove_configured_md5)
        assert self.create_md5_config()
    #end create_md5

    @preposttest_wrapper
    def add_delete_md5(self):
        """
        Description: Verify md5 with add,delete and specific protocol on all ports and policy with allow all between VN's
        """
        self.addCleanup(self.remove_configured_md5)
        assert self.add_delete_md5_config()
    #end add_delete_md5

    @preposttest_wrapper
    def different_keys_md5(self):
        """
        Description: Verify md5 with add,delete and specific protocol on all ports and policy with allow all between VN's
        """
        self.addCleanup(self.remove_configured_md5)
        assert self.different_keys_md5_config()
    #end different_keys_md5

    @preposttest_wrapper
    def check_per_peer(self):
        """
        Description: Verify per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        self.addCleanup(self.remove_configured_md5)
        assert self.check_per_peer_md5_config()
    #end check_per_peer   

    @preposttest_wrapper
    def add_delete_per_peer(self):
        """
        Description: Verify add delete per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        self.addCleanup(self.remove_configured_md5)
        assert self.add_delete_per_peer_md5_config()    
    #end add_delete_per_peer

    @preposttest_wrapper
    def diff_keys_per_peer(self):
        """
        Description: Verify different keys per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        self.addCleanup(self.remove_configured_md5)
        assert self.diff_keys_per_peer_md5_config()
    #end diff_keys_per_peer
       
    @preposttest_wrapper
    def precedence_per_peer(self):
        """
        Description: Verify precedence per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        self.addCleanup(self.remove_configured_md5)
        assert self.precedence_per_peer_md5_config()
    #end precedence_per_peer
    @preposttest_wrapper

    def iter_keys_per_peer(self):
        """
        Description: Verify iteration of same keys per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        self.addCleanup(self.remove_configured_md5)
        assert self.iter_keys_per_peer_md5_config()
    #end test_iter_keys_per_peer

#end class md5tests


class TestMd5testsOnControl(Md5Base, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(TestMd5testsOnControl, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestMd5testsOnControl, cls).tearDownClass()
        cls.remove_mx_group_config()

    def is_test_applicable(self):
        if (len(self.inputs.bgp_control_ips) == 1 and len(self.inputs.ext_routers) < 1):
            return (False, 'Cluster needs 2 BGP peers to configure md5. There are no peers here')
        return (True, None)

    def setUp(self):
        super(TestMd5testsOnControl, self).setUp()
        result = self.is_test_applicable()
        if result[0]:
            self.is_mx_present=False
            self.check_dm = False
            self.config_basic(self.check_dm)
            uuid = self.vnc_lib.bgp_routers_list()
            self.uuid = str(uuid)
            self.list_uuid = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', self.uuid)
            bgp_fq_name = ['default-domain', 'default-project','ip-fabric', '__default__', self.inputs.bgp_names[0]]
            self.only_control_host = self.vnc_lib.bgp_router_read(fq_name=bgp_fq_name).uuid
        else:
            return

    @test.attr(type=['sanity', 'vcenter_compute', 'vcenter'])
    @preposttest_wrapper
    def test_create_md5_on_control(self):
        """
        Description: Verify md5 with allow specific protocol on all ports and policy with allow all between VN's
        """
        self.addCleanup(self.remove_configured_md5)
        assert self.create_md5_config()
    #end create_md5

    @preposttest_wrapper
    def test_add_delete_md5_on_control(self):
        """
        Description: Verify md5 with add,delete and specific protocol on all ports and policy with allow all between VN's
        """
        self.addCleanup(self.remove_configured_md5)
        assert self.add_delete_md5_config()
    #end add_delete_md5

    @preposttest_wrapper
    def test_different_keys_md5_on_control(self):
        """
        Description: Verify md5 with add,delete and specific protocol on all ports and policy with allow all between VN's
        """
        self.addCleanup(self.remove_configured_md5)
        assert self.different_keys_md5_config()
    #end different_keys_md5

    @test.attr(type=['sanity', 'vcenter_compute' 'vcenter'])
    @preposttest_wrapper
    def test_check_per_peer_on_control(self):
        """
        Description: Verify per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        self.addCleanup(self.remove_configured_md5)
        assert self.check_per_peer_md5_config()
    #end check_per_peer   

    @preposttest_wrapper
    def test_add_delete_per_peer_on_control(self):
        """
        Description: Verify add delete per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        self.addCleanup(self.remove_configured_md5)
        assert self.add_delete_per_peer_md5_config()
    #end add_delete_per_peer

    @preposttest_wrapper
    def test_diff_keys_per_peer_on_control(self):
        """
        Description: Verify different keys per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        self.addCleanup(self.remove_configured_md5)
        assert self.diff_keys_per_peer_md5_config()
    #end diff_keys_per_peer

    @preposttest_wrapper
    def test_precedence_per_peer_on_control(self):
        """
        Description: Verify precedence per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        self.addCleanup(self.remove_configured_md5)
        assert self.precedence_per_peer_md5_config()
    #end precedence_per_peer
    @preposttest_wrapper

    def test_iter_keys_per_peer_on_control(self):
        """
        Description: Verify iteration of same keys per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        self.addCleanup(self.remove_configured_md5)
        assert self.iter_keys_per_peer_md5_config()
    #end test_iter_keys_per_peer

#end class TestMd5testsonControl 
