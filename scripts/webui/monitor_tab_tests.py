# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import fixtures
import testtools

from contrail_test_init import *
from vn_test import *
from vm_test import *
from connections import ContrailConnections
from floating_ip import *
from policy_test import *
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
from testresources import ResourcedTestCase
from .webui_sanity_resource import SolnSetupResource
from selenium import webdriver
from pyvirtualdisplay import Display
from selenium.webdriver.common.keys import Keys
import time
import random
from webui_test import *
from selenium.webdriver.support.ui import WebDriverWait


class MonitorTab(
        testtools.TestCase,
        ResourcedTestCase,
        fixtures.TestWithFixtures):

    def __init__(self, *args, **kwargs):
        testtools.TestCase.__init__(self, *args, **kwargs)
        self.res = SolnSetupResource.getResource()
        self.inputs = self.res.inputs
        self.connections = self.res.connections
        self.logger = self.res.logger
        self.nova_fixture = self.res.nova_fixture
        self.analytics_obj = self.connections.analytics_obj
        self.vnc_lib = self.connections.vnc_lib
        self.quantum_fixture = self.connections.quantum_fixture
        self.cn_inspect = self.connections.cn_inspect
        if self.inputs.webui_verification_flag:
            self.browser = self.connections.browser
            self.browser_openstack = self.connections.browser_openstack
            self.delay = 10
            self.webui = WebuiTest(self.connections, self.inputs)
            self.webui_common = WebuiCommon(self.webui)

    def __del__(self):
        print "Deleting test_with_setup now"
        SolnSetupResource.finishedWith(self.res)

    def setUp(self):
        super(MonitorTab, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'

    def tearDown(self):
        print "Tearing down test"
        super(MonitorTab, self).tearDown()
        SolnSetupResource.finishedWith(self.res)

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_control_node_basic_details(self):
        '''Test control node basic details on monitor->Infrastruture->Control Nodes->Node Details-> Basic view page
        '''
        assert self.webui.verify_bgp_routers_ops_basic_data()
        return True
    # end test_control_node_basic_details

    @preposttest_wrapper
    def test_control_node_advance_details(self):
        '''Test control node advance details on monitor->Infrastruture->Control Nodes->Node Details-> Advanced view page
        '''
        assert self.webui.verify_bgp_routers_ops_advance_data()
        return True
    # end test_control_node_advance_details

    @preposttest_wrapper
    def test_vrouter_basic_details(self):
        '''Test virtual routers basic details on monitor->Infrastruture->Virtual Routers->Node Details-> Basic view page
        '''
        assert self.webui.verify_vrouter_ops_basic_data()
        return True
    # end test_vrouter_basic_details

    @preposttest_wrapper
    def test_vrouter_advance_details(self):
        '''Test virtual routers advance details on monitor->Infrastruture->Virtual Routers->Node Details-> Advanced view page
        '''
        assert self.webui.verify_vrouter_ops_advance_data()
        return True
    # end test_vrouter_advance_details

    @preposttest_wrapper
    def test_analytics_node_basic_details(self):
        '''Test analytics node basic details on monitor->Infrastruture->Analytics Nodes->Node Details-> Basic view page
        '''
        assert self.webui.verify_analytics_nodes_ops_basic_data()
        return True
    # end test_analytics_node_basic_details

    @preposttest_wrapper
    def test_analytics_node_advance_details(self):
        '''Test analytics node advance details on monitor->Infrastruture-> Analytics Nodes->Node Details-> Advanced view page
        '''
        assert self.webui.verify_analytics_nodes_ops_advance_data()
        return True
    # end test_analytics_node_advance_details

    @preposttest_wrapper
    def test_config_node_basic_details(self):
        '''Test config node basic details on monitor->Infrastruture->Config Nodes->Node Details-> Basic view page
        '''
        assert self.webui.verify_config_nodes_ops_basic_data()
        return True
    # end test_config_node_basic_details

    @preposttest_wrapper
    def test_config_node_advance_details(self):
        '''Test config node advance details on monitor->Infrastruture->Config Nodes->Node Details-> Advanced view page
        '''
        assert self.webui.verify_config_nodes_ops_advance_data()
        return True
    # end test_config_node_advance_details

    @preposttest_wrapper
    def test_network_basic_details(self):
        '''Test network basic on monitor->Networking->Networks->Network Summary-> basic page
        '''
        assert self.webui.verify_vn_ops_basic_data()
        return True
    # end test_network_basic_details

    @preposttest_wrapper
    def test_network_advance_details(self):
        '''Test network advance details on monitor->Networking->Networks->Network Summary-> Advanced page
        '''
        assert self.webui.verify_vn_ops_advance_data()
        return True
    # end test_network_advance_details

    @preposttest_wrapper
    def test_dashboard_details(self):
        '''Test dashboard details on monitor->Infra->Dashboard page
        '''
        assert self.webui.verify_dashboard_details()
        return True
    # end test_dashboard_details

    @preposttest_wrapper
    def test_instance_basic_details(self):
        '''Test instance basic details on Monitor->Networking->Instances page
        '''
        assert self.webui.verify_vm_ops_basic_data()
        return True
    # end test_instance_basic_details

    @preposttest_wrapper
    def test_instance_advance_details(self):
        '''Test instance advance details on Monitor->Networking->Instances page
        '''
        assert self.webui.verify_vm_ops_advance_data()
        return True
    # end test_instance_advance_details

# end MonitorTab
