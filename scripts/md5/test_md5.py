import unittest
from tcutils.wrappers import preposttest_wrapper
from vnc_api.vnc_api import NoIdError
from vnc_api.vnc_api import VncApi
from verify import VerifySecGroup
from policy_test import PolicyFixture
from vn_test import MultipleVNFixture
from vm_test import MultipleVMFixture
from base import Base
from common.policy.config import ConfigPolicy
from security_group import SecurityGroupFixture,get_secgrp_id_from_name
from vn_test import VNFixture
from vm_test import VMFixture
from tcutils.topo.topo_helper import *
import os
import sys
sys.path.append(os.path.realpath('scripts/flow_tests'))
from tcutils.topo.sdn_topo_setup import *
import test
from tcutils.tcpdump_utils import *
from time import sleep
from tcutils.util import get_random_name

class md5tests(Base, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(md5tests, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(md5tests, cls).tearDownClass()

    def setUp(self):
        super(md5tests, self).setUp()
        self.config_basic()

    @preposttest_wrapper
    def test_create_md5(self):
        """
        Description: Verify md5 with allow specific protocol on all ports and policy with allow all between VN's
        """

        vh=VncApi(username='admin',password='contrail123',tenant_name='admin',api_server_host='127.0.0.1',api_server_port='8082')
        uuid = vh.bgp_routers_list()
        uuid = str(uuid)
        cur = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', uuid)
        auth_data=None
        host=cur[1]
        notmx=0
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        auth_data=None
        host=cur[1]
        notmx=1
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        for host in cur:
            auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
        sleep(120)
        if not (self.check_bgp_status()):
            self.logger.error('BGP between nodes after basic md5 config not up')
            return False
        return True

    #end create_md5

    @preposttest_wrapper
    def test_add_delete_md5(self):
        """
        Description: Verify md5 with add,delete and specific protocol on all ports and policy with allow all between VN's
        """
        vh=VncApi(username='admin',password='contrail123',tenant_name='admin',api_server_host='127.0.0.1',api_server_port='8082')
        uuid = vh.bgp_routers_list()
        uuid = str(uuid)
        cur = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', uuid)
        auth_data=None
        host=cur[1]
        notmx=0
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        auth_data=None
        host=cur[1]
        notmx=1
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        for host in cur:
            auth_data=None
            self.config_md5( host=host, auth_data=auth_data )
        sleep(120)
        if (self.check_bgp_status()):
            self.logger.error('BGP between nodes should not be up because mx has md5 config')
            return False
        host=cur[1]
        auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
        self.config_md5(host=host, auth_data=auth_data)
        sleep(120)
        if (self.check_bgp_status()):
            self.logger.error('BGP between nodes should not be up as only one side has md5')
            return False
        
        for host in cur:
            auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )

        sleep(120)
        if not (self.check_bgp_status()):
            self.logger.error('BGP between nodes not up after both sides have md5')
            return False
        host=cur[1]
        auth_data=None
        self.config_md5(host=host, auth_data=auth_data)
        sleep(120)
        if (self.check_bgp_status()):
            self.logger.error('BGP between nodes 2 should not be up as mx still has md5 config')
            return False

        for host in cur:
            auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
        sleep(120)
        if not (self.check_bgp_status()):
            self.logger.error('BGP between nodes not up after 2 both sides have md5')
            return False

        for host in cur:
            auth_data=None
            self.config_md5( host=host, auth_data=auth_data )
        sleep(120)
        if (self.check_bgp_status()):
            self.logger.error('BGP between nodes should not be up 3 as mx still has md5 config')
            return False
        return True
    #end add_delete_md5

    @preposttest_wrapper
    def test_different_keys_md5(self):
        """
        Description: Verify md5 with add,delete and specific protocol on all ports and policy with allow all between VN's
        """
        vh=VncApi(username='admin',password='contrail123',tenant_name='admin',api_server_host='127.0.0.1',api_server_port='8082')
        uuid = vh.bgp_routers_list()
        uuid = str(uuid)
        cur = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', uuid)
        auth_data=None
        host=cur[1]
        notmx=0
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        auth_data=None
        host=cur[1]
        notmx=1
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        for host in cur:
            auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
        sleep(120)
        if not (self.check_bgp_status()):
            self.logger.error('BGP between nodes not up after md5 config')
            return False
        i=1
        for host in cur:
            auth_data={'key_items': [ { 'key':i,"key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
            i += 1
        sleep(120)
        if (self.check_bgp_status()):
            self.logger.error('BGP between nodes should not be up as keys are different')
            return False 
        
        for host in cur:
            auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
        sleep(120)

        if not (self.check_bgp_status()):
            self.logger.error('BGP between nodes not up after md5 config on all sides')
            return False

        for host in cur:
            auth_data=None
            self.config_md5( host=host, auth_data=auth_data )
        sleep(120)
        if (self.check_bgp_status()):
            self.logger.error('BGP between nodes should not be up as mx still has md5 config')
            return False
        return True
    #end different_keys_md5

    @preposttest_wrapper
    def test_check_per_peer(self):
        """
        Description: Verify per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        vh=VncApi(username='admin',password='contrail123',tenant_name='admin',api_server_host='127.0.0.1',api_server_port='8082')
        uuid = vh.bgp_routers_list()
        uuid = str(uuid)
        cur = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', uuid)
        for host in cur:
            auth_data=None
            self.config_md5( host=host, auth_data=auth_data )
        auth_data=None
        host=cur[1]
        notmx=0
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        auth_data=None
        host=cur[1]
        notmx=1
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )

        sleep(120)
        if (self.check_bgp_status()):
            self.logger.error('BGP between nodes should not be up as mx still has md5')
            return False
        auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
        host=cur[1]
        notmx=0
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        sleep(120)
        if not (self.check_bgp_status()):
            self.logger.error('BGP between nodes not up after per peer config')
            return False
        return True
    #end check_per_peer   

    @preposttest_wrapper
    def test_add_delete_per_peer(self):
        """
        Description: Verify add delete per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        vh=VncApi(username='admin',password='contrail123',tenant_name='admin',api_server_host='127.0.0.1',api_server_port='8082')
        uuid = vh.bgp_routers_list()
        uuid = str(uuid)
        cur = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', uuid)
        for host in cur:
            auth_data=None
            self.config_md5( host=host, auth_data=auth_data )
        
        auth_data=None
        host=cur[1]
        notmx=0
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        auth_data=None
        host=cur[1]
        notmx=1
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        sleep(120)
        if (self.check_bgp_status()):
            self.logger.error('BGP between nodes should not be up as mx still has md5')
            return False
        auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
        host=cur[1]
        notmx=0
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        sleep(120)
        if not (self.check_bgp_status()):
            self.logger.error('BGP between nodes not up after per peer with mx')
            return False
        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        host=cur[1]
        notmx=1
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        sleep(120)
        if not (self.check_bgp_status()):
            self.logger.error('BGP between nodes not up after per peer with control node')
            return False

        auth_data=None
        host=cur[1]
        notmx=0
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        sleep(120)
        if (self.check_bgp_status()):
            self.logger.error('BGP between nodes should not be up after removing per peer with mx')
            return False

        auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
        host=cur[1]
        notmx=0
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        sleep(120)
        if not (self.check_bgp_status()):
            self.logger.error('BGP between nodes not up after reconfig per peer with mx')
            return False
        auth_data=None
        host=cur[1]
        notmx=1
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        sleep(120)
        if not (self.check_bgp_status()):
            self.logger.error('BGP between nodes not up after removing md5 with control')
            return False
        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        host=cur[1]
        notmx=1
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        sleep(120)
        if not (self.check_bgp_status()):
            self.logger.error('BGP between nodes not up after reconfiguring md5 with control')
            return False
        return True
    #end add_delete_per_peer

    @preposttest_wrapper
    def test_diff_keys_per_peer(self):
        """
        Description: Verify different keys per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        vh=VncApi(username='admin',password='contrail123',tenant_name='admin',api_server_host='127.0.0.1',api_server_port='8082')
        uuid = vh.bgp_routers_list()
        uuid = str(uuid)
        cur = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', uuid)
        for host in cur:
            auth_data=None
            self.config_md5( host=host, auth_data=auth_data )
        auth_data=None
        host=cur[1]
        notmx=0
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        auth_data=None
        host=cur[1]
        notmx=1
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )

        sleep(120)
        if (self.check_bgp_status()):
            self.logger.error('BGP between nodes should not be up as mx still has md5')
            return False
        auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
        host=cur[1]
        notmx=0
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        sleep(120)
        if not (self.check_bgp_status()):
            self.logger.error('BGP between nodes not up after per peer with mx')
            return False

        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        host=cur[1]
        notmx=0
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        sleep(120)
        if (self.check_bgp_status()):
            self.logger.error('BGP between nodes should not be up key mismatch with mx')
            return False
        auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
        host=cur[1]
        notmx=0
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        sleep(120)
        if not (self.check_bgp_status()):
            self.logger.error('BGP between nodes not up after reconfiguring key with mx')
            return False
        return True
    #end diff_keys_per_peer
       
    @preposttest_wrapper
    def test_precedence_per_peer(self):
        """
        Description: Verify precedence per peer md5 and specific protocol on all ports and policy with allow all between VN's
        """
        vh=VncApi(username='admin',password='contrail123',tenant_name='admin',api_server_host='127.0.0.1',api_server_port='8082')
        uuid = vh.bgp_routers_list()
        uuid = str(uuid)
        cur = re.findall('u\'uuid\': u\'([a-zA-Z0-9-]+)\'', uuid)
        for host in cur:
            auth_data=None
            self.config_md5( host=host, auth_data=auth_data )
        auth_data=None
        host=cur[1]
        notmx=0
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        auth_data=None
        host=cur[1]
        notmx=1
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )

        sleep(120)
        if (self.check_bgp_status()):
            self.logger.error('BGP between nodes should not be up as mx still has md5')
            return False
        auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
        host=cur[1]
        notmx=0
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        sleep(120)
        if not (self.check_bgp_status()):
            self.logger.error('BGP between nodes not up after per peer with mx')
            return False

        i=1
        for host in cur:
            auth_data={'key_items': [ { 'key':i,"key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
            i += 1
        sleep(120)
        if (self.check_bgp_status()):
            self.logger.error('BGP between nodes should not be up after global md5 key mismatch')
            return False        
        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        host=cur[1]
        notmx=1
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        sleep(120)
        if not (self.check_bgp_status()):
            self.logger.error('BGP between nodes not up after global mismatch, but per peer match')
            return False

        auth_data={'key_items': [ { 'key':"juniper","key_id":0 } ], "key_type":"md5"}
        host=cur[1]
        notmx=0
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        sleep(120)
        if (self.check_bgp_status()):
            self.logger.error('BGP between nodes should not be up after mismatch with mx')
            return False

        auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
        host=cur[1]
        notmx=0
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        sleep(120)
        if not (self.check_bgp_status()):
            self.logger.error('BGP between nodes not up after reconfiguring key with mx')
            return False
        
        auth_data=None
        host=cur[1]
        notmx=1
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )

        sleep(120)
        if (self.check_bgp_status()):
            self.logger.error('BGP between nodes should not be up as global mismatch still exists')
            return False
        for host in cur:
            auth_data={'key_items': [ { 'key':"7","key_id":0 } ], "key_type":"md5"}
            self.config_md5( host=host, auth_data=auth_data )
        sleep(120)
        if not (self.check_bgp_status()):
            self.logger.error('BGP between nodes not up after reconfiguring global match')
            return False

        for host in cur:
            auth_data=None
            self.config_md5( host=host, auth_data=auth_data )
        sleep(120)
        if not (self.check_bgp_status()):
            self.logger.error('BGP between nodes not up after having no md5 between control')
            return False

        auth_data=None
        host=cur[1]
        notmx=0
        self.per_peer( host=host, auth_data=auth_data, notmx=notmx )
        sleep(120)
        if (self.check_bgp_status()):
            self.logger.error('BGP between nodes should not be up as mx still has md5')
            return False
        return True
    #end precedence_per_peer
    #@preposttest_wrapper
#end class md5tests
