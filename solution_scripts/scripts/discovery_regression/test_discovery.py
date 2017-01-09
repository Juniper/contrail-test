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


class TestDiscovery(BaseDiscoveryTest):

    @classmethod
    def setUpClass(cls):
        super(TestDiscovery, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    @test.attr(type=['sanity', 'ci_sanity', 'vcenter'])
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
            self.logger.info("Verifying for ip %s" % (ip))
            assert self.ds_obj.verify_registered_services_to_discovery_service(
                ip)
        return True

    
    @test.attr(type=['sanity', 'ci_sanity', 'vcenter'])
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
            self.logger.info("Verifying for ip %s" % (ip))
            assert self.ds_obj.verify_bgp_connection(ip)
        return True

    @preposttest_wrapper
    def test_agents_connected_to_dns_service(self):
        ''' Validate agents subscribed to dns service

        '''
        for ip in self.inputs.cfgm_ips:
            self.logger.info("Verifying for ip %s" % (ip))
            assert self.ds_obj.verify_agents_connected_to_dns_service(ip)
        return True

    @test.attr(type=['sanity', 'vcenter'])
    #@test.attr(type=['sanity', 'ci_sanity'])
    @preposttest_wrapper
    def test_agents_connected_to_collector_service(self):
        '''
         Description:  Validate agents subscribed to collector service
         1.Verify all agents subscribed to collector service from discovery - fails otherwise

         Maintainer: sandipd@juniper.net
        '''
        for ip in self.inputs.cfgm_ips:
            self.logger.info("Verifying for ip %s" % (ip))
            assert self.ds_obj.verify_agents_connected_to_collector_service(ip)
        return True

    @preposttest_wrapper
    def test_dns_agents_connected_to_collector_service(self):
        ''' Validate dns agents subscribed to collector service

        '''
        for ip in self.inputs.cfgm_ips:
            self.logger.info("Verifying for ip %s" % (ip))
            assert self.ds_obj.verify_dns_agent_connected_to_collector_service(
                ip)
        return True

    @preposttest_wrapper
    def test_control_nodes_connected_to_collector_service(self):
        ''' Validate control nodes subscribed to collector service

        '''
        for ip in self.inputs.cfgm_ips:
            self.logger.info("Verifying for ip %s" % (ip))
            assert self.ds_obj.verify_control_nodes_connected_to_collector_service(
                ip)
        return True

    @test.attr(type=['sanity', 'ci_sanity', 'vcenter'])
    @preposttest_wrapper
    def test_control_nodes_subscribed_to_ifmap_service(self):
        '''
          Description: Validate control nodes subscribed to ifmap service
            1.Verify that control-node subscribed to ifmap server and the get the ifmap server info from discovery - fails otherwise
            2.Go to control node introspect to verify if control node actually connected to that ifmap - fails otherwise

          Maintainer: sandipd@juniper.net
        '''
        for ip in self.inputs.cfgm_ips:
            self.logger.info("Verifying for ip %s" % (ip))
            assert self.ds_obj.verify_control_nodes_subscribed_to_ifmap_service(
                ip)
        return True

    @preposttest_wrapper
    def test_dns_agents_subscribed_to_ifmap_service(self):
        ''' Validate dns agents subscribed to ifmap service

        '''
        for ip in self.inputs.cfgm_ips:
            self.logger.info("Verifying for ip %s" % (ip))
            assert self.ds_obj.verify_dns_agent_subscribed_to_ifmap_service(ip)
        return True

    @preposttest_wrapper
    def test_ApiServer_subscribed_to_collector_service(self):
        ''' Validate apiserver subscribed to collector service

        '''
        for ip in self.inputs.cfgm_ips:
            self.logger.info("Verifying for ip %s" % (ip))
            assert self.ds_obj.verify_ApiServer_subscribed_to_collector_service(
                ip)
        return True

    @preposttest_wrapper
    def test_Schema_subscribed_to_collector_service(self):
        ''' Validate schema subscribed to collector service

        '''
        assert self.ds_obj.verify_Schema_subscribed_to_collector_service()
        return True

    @preposttest_wrapper
    def itest_cross_verification_objects_in_all_discovery(self):
        ''' cross verification objects in all discovery

        '''
        assert self.ds_obj.cross_verification_objects_in_all_discovery()
        return True

    @preposttest_wrapper
    def test_ServiceMonitor_subscribed_to_collector_service(self):
        ''' Validate service monitor subscribed to collector service

        '''
        assert self.ds_obj.verify_ServiceMonitor_subscribed_to_collector_service(
        )
        return True

    @preposttest_wrapper
    def itest_control_node_restart_and_validate_status_of_the_service(self):
        ''' Validate restart of control node services

        '''
        result = True
        svc_lst = []
        svc_lst = self.ds_obj.get_all_control_services(self.inputs.cfgm_ip)
        for elem in svc_lst:
            if (self.ds_obj.get_service_status(self.inputs.cfgm_ip, service_tuple=elem) == 'up'):
                self.logger.info("Service %s is up" % (elem,))
                result = result and True
            else:
                self.logger.warn("Service %s is down" % (elem,))
                result = result and False
                svc_lst.remove(elem)
        # Stopping the control node service
        for elem in svc_lst:
            ip = elem[0]
            self.logger.info("Stopping service %s.." % (elem,))
            self.inputs.stop_service('contrail-control', [ip])
        time.sleep(20)
        for elem in svc_lst:
            ip = elem[0]
            if (self.ds_obj.get_service_status(self.inputs.cfgm_ip, service_tuple=elem) == 'up'):
                self.logger.warn("Service %s is still up" % (elem,))
                result = result and False
            else:
                self.logger.info("Service %s is down" % (elem,))
                result = result and True
        # Starting the control node service
        for elem in svc_lst:
            ip = elem[0]
            self.logger.info("Starting service %s.." % (elem,))
            self.inputs.start_service('contrail-control', [ip])
        time.sleep(6)
        for elem in svc_lst:
            ip = elem[0]
            if (self.ds_obj.get_service_status(self.inputs.cfgm_ip, service_tuple=elem) == 'up'):
                self.logger.info(
                    "Service %s came up after service was started" % (elem,))
                result = result and True
            else:
                self.logger.info(
                    "Service %s is down even after service was started" % (elem,))
                result = result and False

        assert result
        return True

    @preposttest_wrapper
    def test_cleanup(self):
        ''' cleanup service from discovery

        '''
        resp = None
        resp = self.ds_obj.cleanup_service_from_discovery(self.inputs.cfgm_ip)
        return True

    @test.attr(type=['sanity', 'ci_sanity', 'vcenter'])
    @preposttest_wrapper
    def test_webui_subscribed_to_opserver_service(self):
        ''' Validate webui subscribed to opserver service

        '''
        assert self.ds_obj.verify_webui_subscribed_to_opserver_service(
        )
        return True

    @test.attr(type=['sanity', 'ci_sanity', 'vcenter'])
    @preposttest_wrapper
    def test_webui_subscribed_to_apiserver_service(self):
        ''' Validate webui subscribed to apiserver service

        '''
        assert self.ds_obj.verify_webui_subscribed_to_apiserver_service(
        )
        return True
# end TestDiscoveryFixture
