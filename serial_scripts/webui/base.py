import test
from common import isolated_creds
from vn_test import *
from vm_test import *
import fixtures
import testtools
import os
import uuid
from connections import ContrailConnections
from contrail_test_init import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from sdn_topo_setup import *
from webui_topology import *
from floating_ip import *
from policy_test import *
from contrail_fixtures import * 
from tcutils.wrappers import preposttest_wrapper
from selenium import webdriver
from pyvirtualdisplay import Display
from selenium.webdriver.common.keys import Keys
import time
import random
from selenium.webdriver.support.ui import WebDriverWait

class WebuiBaseTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(WebuiBaseTest, cls).setUpClass()
        cls.isolated_creds = isolated_creds.IsolatedCreds(cls.__name__, cls.inputs, ini_file = cls.ini_file, logger = cls.logger)
        cls.inputs = cls.isolated_creds.get_admin_inputs()
        cls.connections = cls.isolated_creds.get_admin_connections()
        cls.quantum_fixture= cls.connections.quantum_fixture
        cls.nova_fixture = cls.connections.nova_fixture
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        resource_class = cls.__name__ + 'Resource'
        cls.res = ResourceFactory.createResource(resource_class)
        cls.res.setUp(cls.inputs , cls.connections)
        if cls.inputs.webui_verification_flag:
            cls.browser = cls.connections.browser
            cls.browser_openstack = cls.connections.browser_openstack
            cls.delay = 10
            cls.webui = WebuiTest(cls.connections, cls.inputs)
            cls.webui_common = WebuiCommon(cls.webui)
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.res.cleanUp()
        #cls.isolated_creds.delete_tenant()
        super(WebuiBaseTest, cls).tearDownClass()
    #end tearDownClass

class ResourceFactory:
    factories = {}
    def createResource(id):
        if not ResourceFactory.factories.has_key(id):
            ResourceFactory.factories[id] = \
              eval(id + '.Factory()')
        return ResourceFactory.factories[id].create()
    createResource = staticmethod(createResource)


class BaseResource(fixtures.Fixture):
    
    def setUp(self,inputs,connections):
        super(BaseResource , self).setUp()
        self.inputs = inputs
        self.connections = connections
        self.setup_common_objects(self.inputs , self.connections)

    def cleanUp(self):
        super(BaseResource, self).cleanUp() 

    def setup_common_objects(self, inputs , connections):
        time.sleep(5)
        topo_obj = sdn_webui_config()
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo_obj))
        out = setup_obj.topo_setup(skip_verify='yes') 
    #end setup_common_objects

class WebuiTestSanityResource (BaseResource): 

    def setUp(self,inputs,connections):
        super(WebuiTestSanityResource , self).setUp(inputs,connections)

    def cleanUp(self):
        super(WebuiTestSanityResource, self).cleanUp()

    class Factory:
        def create(self): return WebuiTestSanityResource()

#End resource


