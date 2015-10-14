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
        self.config_basic()

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_create_md5(self):
        """
        Description: Verify md5 with allow specific protocol on all ports and policy with allow all between VN's
        """

        uuid = self.vnc_lib.bgp_routers_list()
        uuid = str(uuid)
        list_uuid = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', uuid)
        auth_data=None
        for host in list_uuid:
            self.config_per_peer(auth_data=auth_data)
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes should be up before md5"
        for host in list_uuid:
            auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes after basic md5 config not up"
        return True

    #end create_md5

    @preposttest_wrapper
    def test_add_delete_md5(self):
        """
        Description: Verify md5 with add,delete and specific protocol on all ports and policy with allow all between VN's
        """
        uuid = self.vnc_lib.bgp_routers_list()
        uuid = str(uuid)
        list_uuid = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', uuid)
        auth_data=None
        for host in list_uuid:
            self.config_per_peer(auth_data=auth_data)
            self.config_md5( host=host, auth_data=auth_data )        
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes should be up before md5" 
        host=list_uuid[1]
        auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
        self.config_md5(host=host, auth_data=auth_data)
        sleep(95)
        assert not (self.check_bgp_status()), "BGP between nodes should not be up as only one side has md5"
        
        for host in list_uuid:
            auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )

        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes not up after both sides have md5"
        host=list_uuid[1]
        auth_data=None
        self.config_md5(host=host, auth_data=auth_data)
        sleep(95)
        assert not (self.check_bgp_status()), "BGP between nodes 2 should not be up as others have md5"

        for host in list_uuid:
            auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes not up after 2 both sides have md5"

        for host in list_uuid:
            auth_data=None
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes should be up"
        return True
    #end add_delete_md5

    @preposttest_wrapper
    def test_different_keys_md5(self):
        """
        Description: Verify md5 with add,delete and specific protocol on all ports and policy with allow all between VN's
        """
        uuid = self.vnc_lib.bgp_routers_list()
        uuid = str(uuid)
        list_uuid = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', uuid)
        auth_data=None
        for host in list_uuid:
            self.config_per_peer(auth_data=auth_data)
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes should be up before md5"
        for host in list_uuid:
            auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes not up after md5 config"
        i=1
        for host in list_uuid:
            key = i.__str__()
            auth_data={'key_items': [ { 'key':key,"key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
            i += 1
        sleep(95)
        assert not (self.check_bgp_status()), "BGP between nodes should not be up as keys are different"
        
        for host in list_uuid:
            auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes not up after md5 config on all sides"

        for host in list_uuid:
            auth_data=None
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes should be up"
        return True
    #end different_keys_md5

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_check_per_peer(self):
        """
        Description: Verify per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        uuid = self.vnc_lib.bgp_routers_list()
        uuid = str(uuid)
        list_uuid = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', uuid)

        auth_data=None
        for host in list_uuid:
            self.config_per_peer(auth_data=auth_data)
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes should be up before md5"

        auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
        host=list_uuid[1]
        self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes not up after per peer config"        
        return True
    #end check_per_peer   

    @preposttest_wrapper
    def test_add_delete_per_peer(self):
        """
        Description: Verify add delete per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        uuid = self.vnc_lib.bgp_routers_list()
        uuid = str(uuid)
        list_uuid = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', uuid)
        
        auth_data=None
        for host in list_uuid:
            self.config_per_peer(auth_data=auth_data)
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes should be up before md5"

        auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
        host=list_uuid[1]
        self.config_per_peer(auth_data=auth_data)
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes not up after per peer with mx"        
        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        host=list_uuid[1]
        self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes not up after different per peer value"        

        auth_data=None
        host=list_uuid[1]
        self.config_per_peer(auth_data=auth_data)
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes should be up"

        auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
        host=list_uuid[1]
        self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes not up after reconfig per peer with mx"
        auth_data=None
        host=list_uuid[1]
        self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes not up after removing md5 with control"        
        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        host=list_uuid[1]
        self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes not up after reconfiguring md5 with control"        
        return True
    #end add_delete_per_peer

    @preposttest_wrapper
    def test_diff_keys_per_peer(self):
        """
        Description: Verify different keys per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        uuid = self.vnc_lib.bgp_routers_list()
        uuid = str(uuid)
        list_uuid = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', uuid)
        auth_data=None
        for host in list_uuid:
            self.config_per_peer(auth_data=auth_data)
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes should be up before md5"

        auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
        host=list_uuid[1]
        self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes not up after per peer with mx"        

        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        host=list_uuid[1]
        self.config_per_peer( auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes should be up"
        auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
        host=list_uuid[1]
        self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes not up after reconfiguring key with mx"        
        return True
    #end diff_keys_per_peer
       
    @preposttest_wrapper
    def test_precedence_per_peer(self):
        """
        Description: Verify precedence per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        uuid = self.vnc_lib.bgp_routers_list()
        uuid = str(uuid)
        list_uuid = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', uuid)
        auth_data=None
        host=list_uuid[1]
        self.config_per_peer(auth_data=auth_data)
        for host in list_uuid:
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes should be up before md5"
        #import pdb;pdb.set_trace()
        auth_data={'key_items': [ { 'key':"simple","key_id":0 } ], "key_type":"md5"}
        host=list_uuid[1]
        self.config_per_peer( auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes not up after per peer with mx"        

        auth_data=None
        host=list_uuid[1]
        self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes not up after removing md5 with control"

        i=1
        for host in list_uuid:
            key = i.__str__()
            auth_data={'key_items': [ { 'key':key,"key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
            i += 1
        sleep(95)
        assert not (self.check_bgp_status()), "BGP between nodes should not be up after global md5 key mismatch"
        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        host=list_uuid[1]
        self.config_per_peer( auth_data=auth_data )
        sleep(95)
        #import pdb;pdb.set_trace()
        assert (self.check_bgp_status()), "BGP between nodes not up after global mismatch, but per peer match"
 
        
        auth_data=None
        host=list_uuid[1]
        self.config_per_peer( auth_data=auth_data )

        sleep(95)
        assert not (self.check_bgp_status()), "BGP between nodes should not be up as global mismatch still exists"       
        for host in list_uuid:
            auth_data={'key_items': [ { 'key':"trialbyerror","key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes not up after reconfiguring global match"        

        for host in list_uuid:
            auth_data=None
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes not up after having no md5 between control"

        return True
    #end precedence_per_peer
    @preposttest_wrapper

    def test_iter_keys_per_peer(self):
        """
        Description: Verify iteration of same keys per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        uuid = self.vnc_lib.bgp_routers_list()
        uuid = str(uuid)
        list_uuid = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', uuid)
        auth_data=None
        for host in list_uuid:
            self.config_per_peer(auth_data=auth_data)
            self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes should be up before md5"

        auth_data={'key_items': [ { 'key':"iter","key_id":0 } ], "key_type":"md5"}
        host=list_uuid[1]
        self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes not up after per peer with mx"

        for i in range(1, 11):
            for host in list_uuid:
                key = i.__str__()
                auth_data={'key_items': [ { 'key':key,"key_id":0 } ], "key_type":"md5"}
                self.config_md5( host=host, auth_data=auth_data )
            sleep(95)
            assert (self.check_bgp_status()), "BGP between nodes should be up 1 as keys are the same everywhere"
            with settings(
                host_string='%s@%s' % (
                    self.inputs.username, self.inputs.cfgm_ips[0]),
                    password=self.inputs.password, warn_only=True, abort_on_prompts=False, debug=True):
                conrt = run('service contrail-control restart')
            sleep(95)
            assert (self.check_bgp_status()), "BGP between nodes should be up 2 as keys are the same everywhere"            

        for i in range(1, 11):
            for host in list_uuid:
                key = i.__str__()
                auth_data={'key_items': [ { 'key':key,"key_id":0 } ], "key_type":"md5"}
                self.config_md5( host=host, auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes should be up 3 as keys are the same everywhere"
        with settings(
            host_string='%s@%s' % (
                self.inputs.username, self.inputs.cfgm_ips[0]),
                password=self.inputs.password, warn_only=True, abort_on_prompts=False, debug=True):
            conrt = run('service contrail-control restart')
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes should be up 4 as keys are the same everywhere"        

        for i in range(1, 11):
            key = i.__str__()
            auth_data={'key_items': [ { 'key':key,"key_id":0 } ], "key_type":"md5"}
            host=list_uuid[1]
            self.config_per_peer( auth_data=auth_data )
            sleep(95)
            assert (self.check_bgp_status()), "BGP between nodes not up after per peer match"

        for i in range(1, 11):
            key = i.__str__()
            auth_data={'key_items': [ { 'key':key,"key_id":0 } ], "key_type":"md5"}
            host=list_uuid[1]
            notmx=1
            self.config_per_peer(auth_data=auth_data )
        sleep(95)
        assert (self.check_bgp_status()), "BGP between nodes not up after per peer match"

        return True
    #end test_iter_keys_per_peer

#end class md5tests
