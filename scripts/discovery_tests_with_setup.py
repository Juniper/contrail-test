# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import signal
from novaclient import client as mynovaclient
from novaclient import exceptions as novaException
import unittest
import fixtures
import testtools
import traceback
import traffic_tests
from contrail_test_init import *
from vn_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from connections import ContrailConnections
from floating_ip import *
from policy_test import *
from multiple_vn_vm_test import *
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
import uuid
#from analytics_tests import *


class TestDiscoveryFixture(testtools.TestCase, fixtures.TestWithFixtures):

#    @classmethod
    def setUp(self):
        super(TestDiscoveryFixture, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.quantum_fixture = self.connections.quantum_fixture
        self.nova_fixture = self.connections.nova_fixture
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.analytics_obj = self.connections.analytics_obj
        self.ds_obj = self.connections.ds_verification_obj
    # end setUpClass

    def cleanUp(self):
        super(TestDiscoveryFixture, self).cleanUp()
    # end cleanUp

    def runTest(self):
        pass
    # end runTest

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
    def test_control_node_restart_and_validate_status_of_the_service(self):
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
    def test_agent_restart(self):
        ''' Validate agent start and stop

        '''
        assert self.ds_obj.verify_bgp_connection()
        result = True
        cmd = 'cd /etc/contrail;sed -i \'/ttl_min.*=.*/c\\ttl_min = 5\' contrail-discovery.conf'
        for ip in self.inputs.cfgm_ips:
            self.inputs.run_cmd_on_server(
                ip, cmd, username='root', password='c0ntrail123')
        cmd = 'cd /etc/contrail;sed -i \'/ttl_max.*=.*/c\\ttl_max = 10\' contrail-discovery.conf'
        for ip in self.inputs.cfgm_ips:
            self.inputs.run_cmd_on_server(
                ip, cmd, username='root', password='c0ntrail123')
        for ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('contrail-discovery', [ip])
        time.sleep(2)
        assert self.analytics_obj.verify_cfgm_uve_module_state(
            self.inputs.collector_ips[0], self.inputs.cfgm_names[0], 'contrail-discovery')
        for ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter-agent', [ip])
        time.sleep(20)

        for ip in self.inputs.compute_ips:
            in_use_initial = {}
            in_use_after_stop = {}
            in_use_after_start = {}
            lst_in_use = []
            lst_svc_id = []
            t = {}
            svc_id = []
            svc_id = self.ds_obj.get_subscribed_service_id(
                self.inputs.cfgm_ip, client=(ip, 'Contrail-Vrouter-Agent'), service='xmpp-server')
            for service in svc_id:
                t = self.ds_obj.get_service_status_by_service_id(
                    self.inputs.cfgm_ip, service_id=service)
                in_use_initial[service] = t['in_use']
                self.logger.info(
                    "%s service id in use before agent %s restart: %s" %
                    (service, ip, t['in_use']))
            compute_node_process = ['contrail-vrouter-agent']
            for process in compute_node_process:
                try:
                    self.inputs.stop_service(process, [ip])
                    time.sleep(50)
                    for service in svc_id:
                        t = self.ds_obj.get_service_status_by_service_id(
                            self.inputs.cfgm_ip, service_id=service)
                        in_use_after_stop[service] = t['in_use']
                        self.logger.info(
                            "%s service id in use after agent %s restart: %s" %
                            (service, ip, t['in_use']))
                    for k, v in in_use_after_stop.iteritems():
                        for k1, v1 in in_use_initial.iteritems():
                            if (k1 == k):
                                if (int(v1) - int(v) == 1):
                                    self.logger.info(
                                        "in-use decremented for %s service-id after %s agent stopped" % (k1, ip))
                                    result = result and True
                                else:
                                    self.logger.warn(
                                        "in-use not decremented for %s service-id after %s agent stopped" % (k1, ip))
                                    result = result and False
                except Exception as e:
                    print e
                finally:
                    self.inputs.start_service(process, [ip])
                    time.sleep(10)
                    svc_id = self.ds_obj.get_subscribed_service_id(
                        self.inputs.cfgm_ip, client=(ip, 'Contrail-Vrouter-Agent'), service='xmpp-server')
                    for service in svc_id:
                        t = self.ds_obj.get_service_status_by_service_id(
                            self.inputs.cfgm_ip, service_id=service)
                        in_use_after_start[service] = t['in_use']
                        self.logger.info(
                            "%s service id in use after agent %s restart: %s" %
                            (service, ip, t['in_use']))
                    for k, v in in_use_after_start.iteritems():
                        for k1, v1 in in_use_after_stop.iteritems():
                            if (k1 == k):
                                if (int(v) - int(v1) == 1):
                                    self.logger.info(
                                        "in-use incremented for %s service-id after %s agent started" % (k1, ip))
                                    result = result and True
                                else:
                                    self.logger.warn(
                                        "in-use not incremented for %s service-id after %s agent started" % (k1, ip))
                                    result = result and False
                    self.logger.info(
                        "************ END for %s *************" % (ip))
        # reverting back the changes in contrail-discovery.conf
        cmd = 'cd /etc/contrail;sed -i \'/ttl_min.*=.*/c\\ttl_min = 300\' contrail-discovery.conf'
        for ip in self.inputs.cfgm_ips:
            self.inputs.run_cmd_on_server(
                ip, cmd, username='root', password='c0ntrail123')
        cmd = 'cd /etc/contrail;sed -i \'/ttl_max.*=.*/c\\ttl_max = 1800\' contrail-discovery.conf'
        for ip in self.inputs.cfgm_ips:
            self.inputs.run_cmd_on_server(
                ip, cmd, username='root', password='c0ntrail123')
        for ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('contrail-discovery', [ip])
        time.sleep(2)
        assert self.analytics_obj.verify_cfgm_uve_module_state(
            self.inputs.collector_ips[0], self.inputs.cfgm_names[0], 'contrail-discovery')
        assert self.ds_obj.verify_bgp_connection()
        assert result
        time.sleep(300)
        return True

    @preposttest_wrapper
    def test_change_parameters_in_contrail_discovery_conf(self):
        ''' Validate parameters in contrail-discovery.conf
            -ttl_min
            -ttl_max
            -hc_max_miss
            -policy

        '''
        # Changing the hc_max_miss=5 and verifying that the services are down
        # after 25 sec
        try:
            cmd = 'cd /etc/contrail;sed -i \'/hc_max_miss.*=.*/c\hc_max_miss = 10\' contrail-discovery.conf'
            for ip in self.inputs.cfgm_ips:
                self.inputs.run_cmd_on_server(
                    ip, cmd, username='root', password='c0ntrail123')
                self.inputs.restart_service('contrail-discovery', [ip])
            assert self.analytics_obj.verify_cfgm_uve_module_state(
                self.inputs.collector_ips[0], self.inputs.cfgm_names[0], 'contrail-discovery')
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
            time.sleep(15)
            for elem in svc_lst:
                ip = elem[0]
                if (self.ds_obj.get_service_status(self.inputs.cfgm_ip, service_tuple=elem) == 'up'):
                    self.logger.info("Service %s is still up" % (elem,))
                    result = result and True
                else:
                    self.logger.warn("Service %s is down before 25 sec" %
                                     (elem,))
                    result = result and False
            time.sleep(45)
            for elem in svc_lst:
                ip = elem[0]
                if (self.ds_obj.get_service_status(self.inputs.cfgm_ip, service_tuple=elem) == 'up'):
                    self.logger.warn("Service %s is still up after 30 secs" %
                                     (elem,))
                    result = result and False
                else:
                    self.logger.info("Service %s is down after 30 sec" %
                                     (elem,))
                    result = result and True
            # Starting the control node service
            for elem in svc_lst:
                ip = elem[0]
                self.logger.info("Starting service %s.." % (elem,))
                self.inputs.start_service('contrail-control', [ip])
            time.sleep(6)
        except Exception as e:
            print e
        finally:
            # Changing the hc_max_miss=3
            cmd = 'cd /etc/contrail;sed -i \'/hc_max_miss.*=.*/c\hc_max_miss = 3\' contrail-discovery.conf'
            for ip in self.inputs.cfgm_ips:
                self.inputs.run_cmd_on_server(
                    ip, cmd, username='root', password='c0ntrail123')
                self.inputs.restart_service('contrail-discovery', [ip])
            assert self.analytics_obj.verify_cfgm_uve_module_state(
                self.inputs.collector_ips[0], self.inputs.cfgm_names[0], 'contrail-discovery')
            time.sleep(40)  # workarond for bug 2489
            assert result
            # Change policy and verify discovery functionality: policy =
            # [load-balance | round-robin | fixed]
            self.logger.info("Changing the discovery policy to round-robin")
            cmd = 'cd /etc/contrail;echo \'policy = round-robin \'>> contrail-discovery.conf'
            self.inputs.run_cmd_on_server(
                self.inputs.cfgm_ip, cmd, username='root', password='c0ntrail123')
            self.inputs.restart_service(
                'contrail-discovery', [self.inputs.cfgm_ip])
            assert self.analytics_obj.verify_cfgm_uve_module_state(
                self.inputs.collector_ips[0], self.inputs.cfgm_names[0], 'contrail-discovery')
            assert self.ds_obj.verify_bgp_connection()
            self.logger.info("Changing the discovery policy to fixed")
            cmd = 'cd /etc/contrail;sed -i \'/policy = round-robin/c\policy = fixed\' contrail-discovery.conf'
            self.inputs.run_cmd_on_server(
                self.inputs.cfgm_ip, cmd, username='root', password='c0ntrail123')
            self.inputs.restart_service(
                'contrail-discovery', [self.inputs.cfgm_ip])
            assert self.analytics_obj.verify_cfgm_uve_module_state(
                self.inputs.collector_ips[0], self.inputs.cfgm_names[0], 'contrail-discovery')
            assert self.ds_obj.verify_bgp_connection()
            self.logger.info("Reverting back policy to default")
            cmd = 'cd /etc/contrail;sed -i \'/policy = fixed/c\ \' contrail-discovery.conf'
            self.inputs.run_cmd_on_server(
                self.inputs.cfgm_ip, cmd, username='root', password='c0ntrail123')
            self.inputs.restart_service(
                'contrail-discovery', [self.inputs.cfgm_ip])
            assert self.analytics_obj.verify_cfgm_uve_module_state(
                self.inputs.collector_ips[0], self.inputs.cfgm_names[0], 'contrail-discovery')
            assert self.ds_obj.verify_bgp_connection()
            return True

    @preposttest_wrapper
    def test_publish(self):
        ''' Validate short ttl

        '''
        self.logger.info(
            "********TEST WILL FAIL IF RAN MORE THAN ONCE WITHOUT CLEARING THE ZOOKEEPER DATABASE*********")
        service = 'dummy_service23'
        port = 658093
        result = True
        try:
            # Changing the hc_max_miss=3000 and verifying that the services are
            # down after 25 mins
            cmd = 'cd /etc/contrail;sed -i \'/hc_max_miss/c\hc_max_miss = 3000\' contrail-discovery.conf'
            for ip in self.inputs.cfgm_ips:
                self.inputs.run_cmd_on_server(
                    ip, cmd, username='root', password='c0ntrail123')
            cmd = 'cd /etc/contrail;sed -i \'/ttl_short/c\\ttl_short = 2\' contrail-discovery.conf'
            for ip in self.inputs.cfgm_ips:
                self.inputs.run_cmd_on_server(
                    ip, cmd, username='root', password='c0ntrail123')
            cmd = 'cd /etc/contrail;cat contrail-discovery.conf'
            for ip in self.inputs.cfgm_ips:
                out_put = self.inputs.run_cmd_on_server(
                    ip, cmd, username='root', password='c0ntrail123')
                self.logger.info("%s" % (out_put))
                self.inputs.restart_service('contrail-discovery', [ip])
            assert self.analytics_obj.verify_cfgm_uve_module_state(
                self.inputs.collector_ips[0], self.inputs.cfgm_names[0], 'contrail-discovery')
            time.sleep(40)  # workaround for bug 2489
            base_ip = '192.168.1.'
            expected_ttl = 2
            cuuid = uuid.uuid4()
            while(expected_ttl <= 32):
                resp = None
                resp = self.ds_obj.subscribe_service_from_discovery(
                    self.inputs.cfgm_ip, service=service, instances=1, client_id=str(cuuid))
                ttl = resp['ttl']
                self.logger.info("ttl : %s" % (ttl))
                if (ttl <= expected_ttl):
                    result = result and True
                else:
                    result = result and False
                self.logger.info("Waiting for %s sec..." % (expected_ttl))
                time.sleep(expected_ttl)
                expected_ttl = expected_ttl * 2

            self.logger.info("Verifying that the ttl sablizes at 32 sec..")
            resp = None
            resp = self.ds_obj.subscribe_service_from_discovery(
                self.inputs.cfgm_ip, service=service, instances=1, client_id=str(cuuid))
            ttl = resp['ttl']
            self.logger.info("ttl : %s" % (ttl))
            if (ttl <= 32):
                result = result and True
            else:
                result = result and False
        # Bringing up services
            self.logger.info("Bringing up services...")
            for x in range(1, 4):
                svc_ip = base_ip + str(x)
                svc = 'svc' + str(x)
                self.logger.info("Publishing service with ip %s and port %s" %
                                 (svc_ip, port))
                svc = self.ds_obj.publish_service_to_discovery(
                    self.inputs.cfgm_ip, service=service, ip=svc_ip, port=port)
            time.sleep(5)

            self.logger.info("Verifying that the nornal ttl sent..")
            resp = None
            resp = self.ds_obj.subscribe_service_from_discovery(
                self.inputs.cfgm_ip, service=service, instances=1, client_id=str(cuuid))
            ttl = resp['ttl']
            self.logger.info("ttl : %s" % (ttl))
            if (ttl in range(300, 1800)):
                result = result and True
            else:
                result = result and False
            # Verify instnaces == 0 will send all services
            cuuid = uuid.uuid4()
            resp = self.ds_obj.subscribe_service_from_discovery(
                iself.inputs.cfgm_ip, service=service, instances=0, client_id=str(cuuid))
            resp = resp[service]
            if len(resp) < 3:
                result = result and False
                self.logger.warn("Not all services returned")

            expected_ip_list = ['192.168.1.1', '192.168.1.2', '192.168.1.3']
            result1 = True
            for elem in resp:
                self.logger.info("%s" % (elem))
                if (elem['ip-address'] in expected_ip_list and elem['port'] == port):
                    result1 = result1 and True
                    expected_ip_list.remove(elem['ip-address'])
                else:
                    self.logger.info('inside else')
                    result1 = result1 and False
            if result1:
                self.logger.info(
                    "All services correctly received by subscriber")
                result = result and result1
            else:
                self.logger.warn("All services not received by subscriber")
                result = result and result1
                self.logger.warn("Missing service as %s" % (expected_ip_list))
        except Exception as e:
            print e
        finally:

            cmd = 'cd /etc/contrail;sed -i \'/hc_max_miss/c\hc_max_miss = 3\' contrail-discovery.conf'
            for ip in self.inputs.cfgm_ips:
                self.inputs.run_cmd_on_server(
                    ip, cmd, username='root', password='c0ntrail123')
            cmd = 'cd /etc/contrail;sed -i \'/ttl_short/c\\ttl_short = 1\' contrail-discovery.conf'
            for ip in self.inputs.cfgm_ips:
                self.inputs.run_cmd_on_server(
                    ip, cmd, username='root', password='c0ntrail123')
            cmd = 'cd /etc/contrail;cat contrail-discovery.conf'
            for ip in self.inputs.cfgm_ips:
                out_put = self.inputs.run_cmd_on_server(
                    ip, cmd, username='root', password='c0ntrail123')
                self.logger.info("%s" % (out_put))
                self.inputs.restart_service('contrail-discovery', [ip])
            assert self.analytics_obj.verify_cfgm_uve_module_state(
                self.inputs.collector_ips[0], self.inputs.cfgm_names[0], 'contrail-discovery')
            time.sleep(40)
            resp = None
            resp = self.ds_obj.cleanup_service_from_discovery(
                self.inputs.cfgm_ip)
            assert result
            return True

    @preposttest_wrapper
    def test_cleanup(self):
        ''' cleanup service from discovery

        '''
        resp = None
        resp = self.ds_obj.cleanup_service_from_discovery(self.inputs.cfgm_ip)
        return True

    @preposttest_wrapper
    def test_scale_test(self):
        ''' Publish 100 sevices, subscribe to them and then delete them

        '''
        try:
            service = 'dummy_service'
            port = 658093
            base_ip = '192.168.1.'
            result = True
            # Changing the hc_max_miss=3000 and verifying that the services are
            # down after 25 mins
            cmd = 'cd /etc/contrail;sed -i \'/hc_max_miss/c\hc_max_miss = 3000\' contrail-discovery.conf'
            for ip in self.inputs.cfgm_ips:
                self.inputs.run_cmd_on_server(
                    ip, cmd, username='root', password='c0ntrail123')
            cmd = 'cd /etc/contrail;sed -i \'/ttl_short/c\\ttl_short = 2\' contrail-discovery.conf'
            for ip in self.inputs.cfgm_ips:
                self.inputs.run_cmd_on_server(
                    ip, cmd, username='root', password='c0ntrail123')
            cmd = 'cd /etc/contrail;cat contrail-discovery.conf'
            for ip in self.inputs.cfgm_ips:
                out_put = self.inputs.run_cmd_on_server(
                    ip, cmd, username='root', password='c0ntrail123')
                self.logger.info("%s" % (out_put))
                self.inputs.restart_service('contrail-discovery', [ip])
            assert self.analytics_obj.verify_cfgm_uve_module_state(
                self.inputs.collector_ips[0], self.inputs.cfgm_names[0], 'contrail-discovery')
            time.sleep(40)  # workarond for bug 2489
        # Bringing up services
            self.logger.info("Bringing up services...")
            threads = []
            published_service_lst = []
            for x in range(1, 101):
                svc_ip = base_ip + str(x)
                svc = 'svc' + str(x)
#                self.logger.info("Publishing service with ip %s and port %s"%(svc_ip,port))
                t = threading.Thread(target=self.ds_obj.publish_service_to_discovery, args=(
                    self.inputs.cfgm_ip, service, svc_ip, port))
                threads.append(t)

            for th in threads:
                self.logger.info("Publishing service with ip %s and port %s" %
                                 (svc_ip, port))
                th.start()
            for th in threads:
                th.join()
#                svc = self.ds_obj.publish_service_to_discovery(service=service,ip=svc_ip,port=port)
            time.sleep(5)
            self.logger.info("Verifying all services are up...")
            svc = self.ds_obj.get_all_services_by_service_name(
                self.inputs.cfgm_ip, service=service)
            for elem in svc:
                ip = elem[0]
                self.logger.info("ip: %s" % (ip))
                if (ip in (base_ip + str(x) for x in range(1, 101))):
                    self.logger.info("%s is added to discovery service" %
                                     (elem,))
                    result = result and True
                    self.logger.info("Verifying if the service is up")
                    svc_status = self.ds_obj.get_service_status(
                        self.inputs.cfgm_ip, service_tuple=elem)
                    if (svc_status == 'up'):
                        self.logger.info("svc is up")
                        result = result and True
                    else:
                        result = result and False
                        self.logger.warn("svc not up")
                else:
                    self.logger.warn("%s is NOT added to discovery service" %
                                     (elem,))
                    result = result and False

            # Verify instnaces == 0 will send all services
            cuuid = uuid.uuid4()
            resp = self.ds_obj.subscribe_service_from_discovery(
                self.inputs.cfgm_ip, service=service, instances=0, client_id=str(cuuid))
            resp = resp[service]
            if len(resp) < 100:
                result = result and False
                self.logger.warn("Not all services returned")
            self.logger.info(
                "Sending 100 subscription message to discovery..")
            subs_threads = []
            for i in range(100):
                cuuid = uuid.uuid4()
                t = threading.Thread(target=self.ds_obj.subscribe_service_from_discovery, args=(
                    self.inputs.cfgm_ip, service, 2, str(cuuid)))
                subs_threads.append(t)
            for th in subs_threads:
                th.start()
            time.sleep(3)
            for th in subs_threads:
                th.join()

#            assert result
        except Exception as e:
            print e
        finally:
            # Chaging the contrail-discovery.conf to default
            cmd = 'cd /etc/contrail;sed -i \'/hc_max_miss/c\hc_max_miss = 3\' contrail-discovery.conf'
            for ip in self.inputs.cfgm_ips:
                self.inputs.run_cmd_on_server(
                    ip, cmd, username='root', password='c0ntrail123')
            cmd = 'cd /etc/contrail;sed -i \'/ttl_short/c\\ttl_short = 1\' contrail-discovery.conf'
            for ip in self.inputs.cfgm_ips:
                self.inputs.run_cmd_on_server(
                    ip, cmd, username='root', password='c0ntrail123')
            cmd = 'cd /etc/contrail;cat contrail-discovery.conf'
            for ip in self.inputs.cfgm_ips:
                out_put = self.inputs.run_cmd_on_server(
                    ip, cmd, username='root', password='c0ntrail123')
                self.logger.info("%s" % (out_put))
                self.inputs.restart_service('contrail-discovery', [ip])
            assert self.analytics_obj.verify_cfgm_uve_module_state(
                self.inputs.collector_ips[0], self.inputs.cfgm_names[0], 'contrail-discovery')
            time.sleep(40)  # workarond for bug 2489
            resp = None
            resp = self.ds_obj.cleanup_service_from_discovery(
                self.inputs.cfgm_ip)
            assert result
            return True
        # End test test_scale_test
# end TestDiscoveryFixture
