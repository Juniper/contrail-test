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

    @preposttest_wrapper
    def test_agents_connected_to_dns_service(self):
        ''' Validate agents subscribed to dns service

        '''
        for ip in self.inputs.cfgm_ips:
            self.logger.debug("Verifying for ip %s" % (ip))
            assert self.ds_obj.verify_agents_connected_to_dns_service(ip)
        return True

    @test.attr(type=['sanity', 'vcenter'])
    @preposttest_wrapper
    def test_agents_connected_to_collector_service(self):
        '''
         Description:  Validate agents subscribed to collector service
         1.Verify all agents subscribed to collector service from discovery - fails otherwise

         Maintainer: sandipd@juniper.net
        '''
        for ip in self.inputs.cfgm_ips:
            self.logger.debug("Verifying for ip %s" % (ip))
            assert self.ds_obj.verify_agents_connected_to_collector_service(ip)
        return True

    @preposttest_wrapper
    def test_dns_agents_connected_to_collector_service(self):
        ''' Validate dns agents subscribed to collector service

        '''
        for ip in self.inputs.cfgm_ips:
            self.logger.debug("Verifying for ip %s" % (ip))
            assert self.ds_obj.verify_dns_agent_connected_to_collector_service(
                ip)
        return True

    @preposttest_wrapper
    def test_control_nodes_connected_to_collector_service(self):
        ''' Validate control nodes subscribed to collector service

        '''
        for ip in self.inputs.cfgm_ips:
            self.logger.debug("Verifying for ip %s" % (ip))
            assert self.ds_obj.verify_control_nodes_connected_to_collector_service(
                ip)
        return True

    @preposttest_wrapper
    def test_dns_agents_subscribed_to_ifmap_service(self):
        ''' Validate dns agents subscribed to ifmap service

        '''
        for ip in self.inputs.cfgm_ips:
            self.logger.debug("Verifying for ip %s" % (ip))
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

    @test.attr(type=['sanity', 'vcenter'])
    @preposttest_wrapper
    def test_control_nodes_subscribed_to_ifmap_service(self):
        '''
          Description: Validate control nodes subscribed to ifmap service
            1.Verify that control-node subscribed to ifmap server and the get the ifmap server info from discovery - fails otherwise
            2.Go to control node introspect to verify if control node actually connected to that ifmap - fails otherwise

          Maintainer: sandipd@juniper.net
        '''
        for ip in self.inputs.cfgm_ips:
            self.logger.debug("Verifying for ip %s" % (ip))
            assert self.ds_obj.verify_control_nodes_subscribed_to_ifmap_service(
                ip)
        return True

    @preposttest_wrapper
    def test_rule_create_delete(self):
        ''' Validate rules get created and deleted successfully.
        Also verify that created rules are found in the display.
        Read all the rules together.
        Steps:
        1. This test case creates multiple rules for Xmpp-Server and DNS-server
        2. Then it searches for the created rules to check if they are configured properly or not
        3. Read all the rules that are present.
        4. Delete all the configured rules.
        5. Search for the rules if they have been deleted properly or not.
        '''
        result = True
        ds_ip = self.ds_obj.inputs.cfgm_ip
        if len(self.inputs.cfgm_control_ip) > 0:
            self.logger.info("Creating rules corresponding to xmpp-server and dns-server running on all config nodes for vrouter agent running in same subnets")
        for i in range(0,len(self.inputs.cfgm_control_ips)):
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            self.ds_obj.discovery_rule_config("add_rule",\
                        'default-discovery-service-assignment', cfgm_control_ip,\
                        'xmpp-server', cfgm_control_ip, 'contrail-vrouter-agent:0')
            self.ds_obj.discovery_rule_config("add_rule",\
                        'default-discovery-service-assignment', cfgm_control_ip,\
                        'dns-server', cfgm_control_ip, 'contrail-vrouter-agent:0')
        self.ds_obj.read_rule('default-discovery-service-assignment')
        for i in range(0,len(self.inputs.cfgm_control_ips)): 
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            result1 = self.ds_obj.discovery_rule_config("find_rule",\
                    'default-discovery-service-assignment',cfgm_control_ip,\
                    'xmpp-server', cfgm_control_ip,'contrail-vrouter-agent:0')
            if result1 == False:
                self.logger.error("While searching for the configured rule, it was not found. Configuration failed")
                result = False
            result2 = self.ds_obj.discovery_rule_config("find_rule",\
                    'default-discovery-service-assignment',cfgm_control_ip,\
                    'dns-server', cfgm_control_ip,'contrail-vrouter-agent:0')
            if result2 == False:
                self.logger.error("While searching for the configured rule, it was not found. Configuration failed")
                result = False
        for i in range(0,len(self.inputs.cfgm_control_ips)): 
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            self.ds_obj.discovery_rule_config('del_rule',\
                'default-discovery-service-assignment', cfgm_control_ip,\
                'xmpp-server', cfgm_control_ip,'contrail-vrouter-agent:0')
            self.ds_obj.discovery_rule_config('del_rule',\
                'default-discovery-service-assignment', cfgm_control_ip,\
                'dns-server', cfgm_control_ip,'contrail-vrouter-agent:0')
        self.ds_obj.read_rule("default-discovery-service-assignment")
        for i in range(0,len(self.inputs.cfgm_control_ips)): 
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            result1 = self.ds_obj.discovery_rule_config("find_rule",\
                    'default-discovery-service-assignment',cfgm_control_ip,\
                    'xmpp-server', cfgm_control_ip,'contrail-vrouter-agent:0')
            if result1 == True:
                self.logger.error("While searching for the deleted rule, it was found. Deletion failed")
                result = False
            result2 = self.ds_obj.discovery_rule_config("find_rule",\
                    'default-discovery-service-assignment',cfgm_control_ip,\
                    'dns-server', cfgm_control_ip,'contrail-vrouter-agent:0')
            if result2 == True:
                self.logger.error("While searching for the deleted rule, it was found. Deletion failed")
                result = False
        assert result

# end TestDiscoveryFixture
