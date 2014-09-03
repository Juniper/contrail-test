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


class ConfigTab(
        testtools.TestCase,
        ResourcedTestCase,
        fixtures.TestWithFixtures):

    resources = [('base_setup', SolnSetupResource)]

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
        super(ConfigTab, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'

    def tearDown(self):
        print "Tearing down test"
        super(ConfigTab, self).tearDown()
        SolnSetupResource.finishedWith(self.res)

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_floating_ips(self):
        '''Test floating ips on config->Networking->Manage Floating IPs page
        '''
        assert self.webui.verify_floating_ip_api_data()
        return True
    # end test_floating_ips

    @preposttest_wrapper
    def test_networks(self):
        '''Test networks on config->Networking->Networks page
        '''
        assert self.webui.verify_vn_api_data()
        return True
    # end test_networks

    @preposttest_wrapper
    def test_ipams(self):
        '''Test ipams on config->Networking->IP Adress Management page
        '''
        assert self.webui.verify_ipam_api_data()
        return True
    # end test_ipams

    @preposttest_wrapper
    def test_policies(self):
        '''Test polcies on config->Networking->Policies page
        '''
        assert self.webui.verify_policy_api_data()
        return True
    # end test_policies

    @preposttest_wrapper
    def test_service_templates(self):
        '''Test svc templates on config->Services->Service Templates page
        '''
        assert self.webui.verify_service_template_api_basic_data()
        return True
    # end test_service_templates

    @preposttest_wrapper
    def test_service_instances(self):
        '''Test svc instances on config->Services->Service Instances page
        '''
        assert self.webui.verify_service_instance_api_basic_data()
        return True
    # end test_service_instances

    @preposttest_wrapper
    def test_project_quotas(self):
        '''Test project quotas on config->Networking->Project Quotas page
        '''
        assert self.webui.verify_project_quotas()
        return True
    # end test_project_quotas
# end ConfigTab
