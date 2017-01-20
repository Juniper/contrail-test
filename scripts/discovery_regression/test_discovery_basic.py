# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import unittest
import fixtures
import testtools
import traceback
from tcutils.wrappers import preposttest_wrapper
import uuid
from base import BaseDiscoveryTest
import test


class TestDiscoveryBasic(BaseDiscoveryTest):

    @classmethod
    def setUpClass(cls):
        super(TestDiscoveryBasic, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    #@test.attr(type=['sanity', 'ci_sanity', 'vcenter', 'suite1']) # Disabling discovery sanity run due to changes in R4.0-Bug 1658035 
    @preposttest_wrapper
    def test_all_publishers_registered_to_discovery_service(self):
        '''
         Description:Validate all services are registered to discovery service
         Steps:
           1.Gets expected services to be published to discovery from testbed.py
           2.Gets actually published services to discovery from <ip>:5998/services.json
           3.Find out any diff between expected and actual list of publishers - fails test case if there is any diff
           4.Checkes all the published services are up from discovery - fails if any of them down
         Maintainer: sandipd@juniper.net
        '''
        for ip in self.inputs.cfgm_ips:
            self.logger.debug("Verifying for ip %s" % (ip))
            assert self.ds_obj.verify_registered_services_to_discovery_service(
                ip)
        return True


    #@test.attr(type=['sanity', 'ci_sanity', 'vcenter', 'suite1']) # Disabling discovery sanity run due to changes in R4.0-Bug 1658035 
    @preposttest_wrapper
    def test_agent_gets_control_nodes_from_discovery(self):
        '''
         Description:Validate agents subscribed to control node service
             Steps:
             1.Get all xmpp-clients from connected to a xmpp server from discovery
             2.From introspect of each of those xmpp-clients,verify if that client connected to the same xmpp server and connection established- fails otherwise
         Maintainer: sandipd@juniper.net
        '''
        for ip in self.inputs.cfgm_ips:
            self.logger.debug("Verifying for ip %s" % (ip))
            assert self.ds_obj.verify_bgp_connection(ip)
        return True

    @preposttest_wrapper
    def test_webui_subscribed_to_apiserver_service(self):
        ''' Validate webui subscribed to apiserver service

        '''
        assert self.ds_obj.verify_webui_subscribed_to_apiserver_service(
        )
        return True

    @preposttest_wrapper
    def test_webui_subscribed_to_opserver_service(self):
        ''' Validate webui subscribed to opserver service

        '''
        assert self.ds_obj.verify_webui_subscribed_to_opserver_service(
        )
        return True

# end TestDiscoveryFixture
