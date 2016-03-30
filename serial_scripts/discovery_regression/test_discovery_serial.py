import unittest
import fixtures
import testtools
import traceback
from tcutils.wrappers import preposttest_wrapper
import uuid
import base
import test
import time
from time import sleep
import threading
from tcutils.config.discovery_util import DiscoveryServerUtils
from tcutils.contrail_status_check import ContrailStatusChecker
from multiprocessing import Process

class TestDiscoverySerial(base.BaseDiscoveryTest):

    @classmethod
    def setUpClass(cls):
        super(TestDiscoverySerial, cls).setUpClass()

    def runTest(self):
        pass

    # end runTest

    @test.attr(type=['sanity', 'vcenter'])
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
        retry = 0
        for elem in svc_lst:
            ip = elem[0]
            while True:
                svc_status = self.ds_obj.get_service_status(self.inputs.cfgm_ip, service_tuple=elem)
                if svc_status == 'up':
                    self.logger.info(
                        "Service %s came up after service was started" % (elem,))
                    result = result and True
                    break
                else:
                    retry = retry + 1
                    time.sleep(1)
                    self.logger.warn("Service %s isn't up yet " % (elem,))
                    if retry > 30:
                        self.logger.info(
                            "Service %s is down even after service was started" % (elem,))
                        result = result and False
                        break
        assert result
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
            time.sleep(10)  
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
                ip = elem['info']['ip-address']
                elem = (ip, elem['service_type'])
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
            time.sleep(10)  
            resp = None
            resp = self.ds_obj.cleanup_service_from_discovery(
                self.inputs.cfgm_ip)
            assert result
            return True
        # End test test_scale_test

    @preposttest_wrapper
    def test_send_admin_state_in_publish(self):
        ''' 1) Publish services with admin state down
            2) Subscribe clients, and verify that discovery server should not allocate down services
            3) Update admin state of published services from down to up
            4) Subscribe clients, and verify that discovery server should allocate the services
            5) Cleanup
        '''
        try:
            service = 'my_svc_admin_state'
            port = 65093
            base_ip = '192.168.10.'
            no_of_services = 25
            result = True
            msg = ''
            self.ds_obj.modify_discovery_conf_file_params(operation='change_ttl_short_and_hc_max_miss')
            assert self.analytics_obj.verify_cfgm_uve_module_state(
                self.inputs.collector_ips[0], self.inputs.cfgm_names[0], 'contrail-discovery')
            self.publish_service_with_admin_state(service, base_ip, port, 'down', no_of_services)
            if not self.verify_service_status(service, base_ip, no_of_services, expected_status='down'):
                result = result and False
            # Verify instnaces == 0 will send all services
            cuuid = uuid.uuid4()
            resp = self.ds_obj.subscribe_service_from_discovery(
                self.inputs.cfgm_ip, service=service, instances=0, client_id=str(cuuid))
            resp = resp[service]
            if len(resp) == 0 :
                result = result and True
                self.logger.info("Down services are not returned by the discovery server")
            else:
                result = result and False
                self.logger.error("Discovery server returning down services for the client's subscription")
            self.logger.info(
                "Sending 30 subscription message to discovery for the down services \
                and verify if any of them is returned..")
            for i in range(30):
                cuuid = uuid.uuid4()
                resp = self.ds_obj.subscribe_service_from_discovery(self.inputs.cfgm_ip, service, 0, str(cuuid))
                time.sleep(1)
                resp = resp[service]
                if resp:
                    self.logger.error("Down service is returned by the discovery server")
                    result = result and False
            # change the admin state from down to up and verify if discovery started returning services
            published_service_lst = []
            for x in range(1, no_of_services + 1):
                svc_ip = base_ip + str(x)
                svc = 'svc' + str(x)
                self.ds_obj.update_service(self.inputs.cfgm_ip, service, svc_ip, admin_state='up')
            time.sleep(5)
            if not self.verify_service_status(service, base_ip, no_of_services, expected_status='up'):
                result = result and False
            # Verify instnaces == 0 will send all services
            cuuid = uuid.uuid4()
            resp = self.ds_obj.subscribe_service_from_discovery(
                self.inputs.cfgm_ip, service=service, instances=0, client_id=str(cuuid))
            resp = resp[service]
            if len(resp) < no_of_services:
                result = result and False
                self.logger.error("Not all services returned")
            self.logger.info(
                "Sending 30 subscription message to discovery..")
            subs_threads = []
            for i in range(30):
                cuuid = uuid.uuid4()
                t = threading.Thread(target=self.ds_obj.subscribe_service_from_discovery, args=(
                    self.inputs.cfgm_ip, service, 2, str(cuuid)))
                subs_threads.append(t)
            for th in subs_threads:
                th.start()
            time.sleep(3)
            for th in subs_threads:
                th.join()
        except Exception as e:
            self.logger.exception("Got exception %s"%(e))
            raise
        finally:
            self.ds_obj.modify_discovery_conf_file_params(operation='change_ttl_short_and_hc_max_miss',\
                            ttl_short=1, hc_max_miss=3)
            self.logger.info("%s"%(msg))
            resp = self.ds_obj.cleanup_service_from_discovery(
                self.inputs.cfgm_ip)
            assert self.analytics_obj.verify_cfgm_uve_module_state(
                self.inputs.collector_ips[0], self.inputs.cfgm_names[0], 'contrail-discovery')
            resp = None
            assert result
            return True
        # End test test_send_admin_state_in_publish

    @preposttest_wrapper
    def test_publish(self):
        ''' Validate short ttl

        '''
        self.logger.info(
            "********TEST WILL FAIL IF RAN MORE THAN ONCE WITHOUT CLEARING THE ZOOKEEPER DATABASE*********")
        service = 'dummy_service23'
        port = 65093
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
            time.sleep(10)  
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
                self.inputs.cfgm_ip, service=service, instances=0, client_id=str(cuuid))
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
    def test_change_parameters_in_contrail_discovery_conf(self):
        ''' Validate parameters in discovery.conf
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
            time.sleep(10)
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
    def  test_rule_for_vrouter_with_xmpp_server(self):
        ''' Validate that applied rules takes effect correctly for 
            contrail-vrouter-agent and its subscription to XMPP Server.
            Steps:
            1. Create rules for all contrail-vrouter-agent of 1 network
                 to subscribe to XMPP Servers of same network.
            2. Verify if rule is working as expected or not
            Precondition: Assumption is that setup is having a vrouter connected
                    to 2 instances of XMPP servers running in different subnets
                    Also, setup requirement of this test case is to have at 
                    least 2 publishers and 2 subscribers.
                    Both set of publisher and subscriber should be in different network.
        '''
        self.ds_obj.skip_discovery_test("xmpp-server", min_instances=2, different_subnet_flag=True )
        result = True
        ds_ip = self.inputs.cfgm_ip
        self.ds_obj.resubscribe_with_new_ttl( 30, 30, 'contrail-vrouter-agent')
        self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,\
                        "change_min_max_ttl")
        if len(self.inputs.bgp_control_ips) > 0:
            self.logger.info("Creating rules corresponding to control node *xmpp-server*")
            self.logger.info(" Subscribers are *vrouter agent* running in same subnets")
        for i in range(0,len(self.inputs.bgp_control_ips)):
            bgp_control_ip = self.inputs.bgp_control_ips[i].split('.')
            bgp_control_ip[3] = '0'
            bgp_control_ip = ".".join(bgp_control_ip) + "/24"
            rule_status = self.ds_obj.add_and_verify_rule(bgp_control_ip,'xmpp-server',\
                 bgp_control_ip, 'contrail-vrouter-agent:0')
            if rule_status == False:
                result = False
        self.logger.info("#### Waiting for 30 seconds so that TTL expiry for all subscriber happens ###")
        sleep (30)
        self.logger.debug("#### Verifying clients subscribed to publishers ###")
        try:
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.ds_obj.verify_client_subscription_to_expected_publisher\
                                (ds_ip, 'contrail-vrouter-agent:0', \
                                self.inputs.compute_control_ips[i], 'xmpp-server')
                if verification == False:
                    result = False
        except Exception as e:
            self.logger.error(e)
            result = False     
        for i in range(0,len(self.inputs.bgp_control_ips)): 
            bgp_control_ip = self.inputs.bgp_control_ips[i].split('.')
            bgp_control_ip[3] = '0'
            bgp_control_ip = ".".join(bgp_control_ip) + "/24"
            rule_status = self.ds_obj.delete_and_verify_rule( bgp_control_ip,\
                'xmpp-server', bgp_control_ip,'contrail-vrouter-agent:0')
            if rule_status == False:
                result = False
        assert result, "Test case failed due to some error. Please refer to logs"
    
    @preposttest_wrapper
    def  test_rule_for_vrouter_with_dns_server(self):
        ''' Validate that applied rules takes effect correctly for
            contrail-vrouter-agent and its subscription to DNS Server.
            Steps:
            1. Create rules for all contrail-vrouter-agent of 1 network to
                subscribe to DNS Servers of same network.
            2. Verify if rule is working as expected or not
            Precondition: Assumption is that setup is having a vrouter connected
                    to 2 instances of DNS servers running in different subnets
                    Also, setup requirement of this test case is to have at least 
                    2 publishers and 2 subscribers.
                    Both set of publisher and subscriber should be in different network.
        '''
        self.ds_obj.skip_discovery_test("dns-server", min_instances=2, different_subnet_flag=True )
        result = True
        ds_ip = self.inputs.cfgm_ip
        self.ds_obj.resubscribe_with_new_ttl( 30, 30, 'contrail-vrouter-agent')
        self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
        if len(self.inputs.bgp_control_ips) > 0:
            self.logger.info("Creating rules corresponding to control node *DNS-Server*")
            self.logger.info(" Subscribers are *vrouter agent* running in same subnets")
        for i in range(0,len(self.inputs.bgp_control_ips)):
            bgp_control_ip = self.inputs.bgp_control_ips[i].split('.')
            bgp_control_ip[3] = '0'
            bgp_control_ip = ".".join(bgp_control_ip) + "/24"
            rule_status = self.ds_obj.add_and_verify_rule( bgp_control_ip,\
                'dns-server',bgp_control_ip, 'contrail-vrouter-agent:0')
            if rule_status == False:
                result = False
        self.logger.info("#### Waiting for 30 seconds so that TTL expiry for all subscriber happens ###")
        sleep (30)
        self.logger.debug("#### Verifying clients subscribed to publishers ###")
        try:
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.ds_obj.verify_client_subscription_to_expected_publisher\
                            (ds_ip, 'contrail-vrouter-agent:0', \
                            self.inputs.compute_control_ips[i], 'dns-server')
                if verification == False:
                    result = False
        except Exception as e:
            self.logger.error(e)
            result = False    
        for i in range(0,len(self.inputs.bgp_control_ips)): 
            bgp_control_ip = self.inputs.bgp_control_ips[i].split('.')
            bgp_control_ip[3] = '0'
            bgp_control_ip = ".".join(bgp_control_ip) + "/24"
            rule_status = self.ds_obj.delete_and_verify_rule( bgp_control_ip,\
                'dns-server', bgp_control_ip,'contrail-vrouter-agent:0')
            if rule_status == False:
                result = False
        assert result, "Test case failed due to some error. Please refer to logs"
    
    @preposttest_wrapper
    def  test_rule_for_control_with_ifmap_server(self):
        ''' Validate that applied rules takes effect correctly for 
            "contrail-control" and its subscription to IfmapServer.
            Steps:
            1. Create rules for all contrail-control of 1 network to subscribe
                to Ifmap Servers of same network.
            2. Verify if rule is working as expected or not
            Precondition: Assumption is that setup is having a contrail-control
             connected to 2 instances of Ifmap servers running in different subnets
                Also, setup requirement of this test case is to have at least 2
                publishers and 2 subscribers.
                Both set of publisher and subscriber should be in different network.
        '''
        self.ds_obj.skip_discovery_test("IfmapServer", min_instances=2, different_subnet_flag=True )
        result = True
        ds_ip = self.inputs.cfgm_ip
        self.ds_obj.resubscribe_with_new_ttl( 30, 30, 'contrail-control')
        self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
        if len(self.inputs.cfgm_control_ips) > 0:
            self.logger.info("Creating rules corresponding to config node *IfmapServer*")
            self.logger.info(" Subscribers are *contrail-control* running in same subnets")
        for i in range(0,len(self.inputs.cfgm_control_ips)):
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            rule_status = self.ds_obj.add_and_verify_rule( cfgm_control_ip,\
                 'IfmapServer', cfgm_control_ip, 'contrail-control')
            if rule_status == False:
                result = False
        self.logger.info("#### Waiting for 30 seconds so that TTL expiry for all subscriber happens ###")
        sleep (30)
        self.logger.debug("#### Verifying clients subscribed to publishers ###")
        try:
            for i in range(0,len(self.inputs.bgp_control_ips)):
                verification = self.ds_obj.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrail-control', self.inputs.bgp_control_ips[i],\
                  'IfmapServer')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
        except Exception as e:
            self.logger.error(e)
            result = False         
        for i in range(0,len(self.inputs.cfgm_control_ips)): 
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            rule_status = self.ds_obj.delete_and_verify_rule( cfgm_control_ip,\
                'IfmapServer', cfgm_control_ip, 'contrail-control')
            if rule_status == False:
                result = False
        assert result, "Test case failed due to some error. Please refer to logs"
    
    @preposttest_wrapper
    def  test_rule_for_webui_with_op_server(self):
        ''' Validate that applied rules takes effect correctly for 
            "contrailWebUI" and its subscription to Op Server.
            Steps:
            1. Create rules for all contrailWebUI of 1 network to 
                subscribe to Op Servers of same network.
            2. Verify if rule is working as expected or not
            Precondition: Assumption is that setup is having ContrailWebUI
                         connected to OP server running in different subnet.
        '''
        self.ds_obj.skip_discovery_test("OpServer", min_instances=2, different_subnet_flag=True )
        result = True
        ds_ip = self.inputs.cfgm_ip
        assert self.ds_obj.resubscribe_with_new_ttl( 30, 30, 'supervisor-webui')
        self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
        if len(self.inputs.collector_control_ips) > 0:
            self.logger.info("Creating rules corresponding to collector node *OpServer*")
            self.logger.info(" Subscribers are *contrailWebUI* running in same subnets")
        for i in range(0,len(self.inputs.collector_control_ips)):
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            rule_status = self.ds_obj.add_and_verify_rule(collector_control_ip,\
                'OpServer', collector_control_ip,'contrailWebUI')
            if rule_status == False:
                result = False
        self.logger.info("#### Waiting for 30 seconds so that TTL expiry for all subscriber happens ###")
        sleep (30)
        self.logger.debug("#### Verifying clients subscribed to publishers ###")
        try:
            for i in range(0,len(self.inputs.webui_control_ips)):
                verification = self.ds_obj.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrailWebUI', self.inputs.webui_control_ips[i], 'OpServer')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
        except Exception as e:
            self.logger.error(e)
            result = False   
        for i in range(0,len(self.inputs.collector_control_ips)): 
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            rule_status = self.ds_obj.delete_and_verify_rule(collector_control_ip,\
                'OpServer', collector_control_ip,'contrailWebUI')
            if rule_status == False:
                result = False
        assert result, "Test case failed due to some error. Please refer to logs"
    
    @preposttest_wrapper
    def test_rule_for_webui_with_api_server(self):
        ''' Validate that applied rules takes effect correctly for 
            "contrailWebUI" and its subscription to API Server.
            Steps:
            1. Create rules for all contrailWebUI of 1 network to subscribe
                 to Op Servers of same network.
            2. Verify if rule is working as expected or not
            Precondition: Assumption is that setup is having ContrailWebUI 
            connected to API server running in different subnet.
        '''
        self.ds_obj.skip_discovery_test("ApiServer", min_instances=2, different_subnet_flag=True )
        result = True
        ds_ip = self.inputs.cfgm_ip
        assert self.ds_obj.resubscribe_with_new_ttl( 30, 30, 'supervisor-webui')
        self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
        if len(self.inputs.cfgm_control_ips) > 0:
            self.logger.info("Creating rules corresponding to config node *ApiServer*")
            self.logger.info(" Subscribers are *contrailWebUI* running in same subnets")
        for i in range(0,len(self.inputs.cfgm_control_ips)):
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            rule_status = self.ds_obj.add_and_verify_rule(cfgm_control_ip,\
                'ApiServer', cfgm_control_ip, 'contrailWebUI')
            if rule_status == False:
                result = False
        self.logger.info("#### Waiting for 30 seconds so that TTL expiry for all subscriber happens ###")
        sleep (30)
        self.logger.debug("#### Verifying clients subscribed to publishers ###")
        try:
            for i in range(0,len(self.inputs.webui_control_ips)):
                verification = self.ds_obj.verify_client_subscription_to_expected_publisher\
                (ds_ip, 'contrailWebUI', self.inputs.webui_control_ips[i], 'ApiServer')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
        except Exception as e:
            self.logger.error(e)
            result = False
        for i in range(0,len(self.inputs.cfgm_control_ips)): 
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            rule_status = self.ds_obj.delete_and_verify_rule(cfgm_control_ip,\
                'ApiServer', cfgm_control_ip, 'contrailWebUI')
            if rule_status == False:
                result = False
        assert result, "Test case failed due to some error. Please refer to logs"
    
    @preposttest_wrapper    
    def test_rule_for_vrouter_with_collector(self):
        ''' Validate that applied rules takes effect correctly for 
            "contrail-vrouter-agent" and its subscription to Collector.
            Steps:
            1. Create rules for all contrail-vrouter-agent of 1 network 
                to subscribe to Collector of same network.
            2. Verify if rule is working as expected or not
            Precondition: Assumption is that setup is having a vrouter connected
                    to  2 instances of Collectors running in different subnets
                    Also, setup requirement of this test case is to have at least
                    2 publishers and 2 subscribers.
                Both set of publisher and subscriber should be in different network.
        '''
        self.ds_obj.skip_discovery_test("Collector", min_instances=2, different_subnet_flag=True )
        result = True
        ds_ip = self.inputs.cfgm_ip
        assert self.ds_obj.resubscribe_with_new_ttl( 30, 30, 'contrail-vrouter-agent')
        self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
        if len(self.inputs.collector_control_ips) > 0:
            self.logger.info("Creating rules corresponding to collector node *Collector*")
            self.logger.info(" Subscribers are *vrouter-agent* running in same subnets")
        for i in range(0,len(self.inputs.collector_control_ips)):
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            rule_status = self.ds_obj.add_and_verify_rule(collector_control_ip,\
                'Collector', collector_control_ip,'contrail-vrouter-agent:0')
            if rule_status == False:
                result = False
        self.logger.info("#### Waiting for 60 seconds so that TTL expiry for all subscriber happens ###")
        sleep (30)
        self.logger.debug("#### Verifying clients subscribed to publishers ###") 
        try:
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.ds_obj.verify_client_subscription_to_expected_publisher\
                                (ds_ip, 'contrail-vrouter-agent:0', \
                                 self.inputs.compute_control_ips[i], 'Collector')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
        except Exception as e:
            self.logger.error(e)
            result = False
        for i in range(0,len(self.inputs.collector_control_ips)): 
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            rule_status = self.ds_obj.delete_and_verify_rule(collector_control_ip,\
                'Collector', collector_control_ip,'contrail-vrouter-agent:0')
            if rule_status == False:
                result = False
        assert result, "Test case failed due to some error. Please refer to logs"
    
    @preposttest_wrapper    
    def test_rule_for_collector_with_multi_clients(self):
        ''' Validate that applied rules takes effect correctly for multiple
            clients mentioned sequentially in a single rule for Collector as 
            a Server/Publisher.
            Steps:
            1. Create s single rule for multiple types of clients to subscribe 
            to single Publisher. Mention all subscriber in that rule.
            2. Verify if rule is working as expected or not. Verify that all 
            clients subscribe to single publisher only.
            Precondition: Assumption is that setup is having a vrouter connected
                    to  2 instances of Collectors running in different subnets
                    Also, setup requirement of this test case is to have at least
                    2 publishers and 2 subscribers.
                Both set of publisher and subscriber should be in different network.
        '''
        self.ds_obj.skip_discovery_test("Collector", min_instances=2, different_subnet_flag=True )
        result = True
        ds_ip = self.inputs.cfgm_ip
        assert self.ds_obj.resubscribe_with_new_ttl(30, 30, 'contrail-vrouter-agent',\
                                 'contrail-topology', 'contrail-control', 'contrail-api')
        self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
        if len(self.inputs.collector_control_ips) > 0:
            self.logger.info("Creating rules corresponding to collector node *Collector*")
            self.logger.info("Subscribers are mulitple services running in same subnets")
        for i in range(0,len(self.inputs.collector_control_ips)):    
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            self.ds_obj.discovery_rule_config( "add_rule",
                    'default-discovery-service-assignment', collector_control_ip,\
                    'Collector', collector_control_ip, 'contrail-vrouter-agent:0',\
                    collector_control_ip, 'contrail-topology', collector_control_ip,\
                    'contrail-control', collector_control_ip, 'contrail-api')
            result1 = self.ds_obj.discovery_rule_config( "find_rule",\
                    'default-discovery-service-assignment', collector_control_ip,\
                    'Collector', collector_control_ip, 'contrail-vrouter-agent:0',\
                    collector_control_ip, 'contrail-topology', collector_control_ip,\
                    'contrail-control', collector_control_ip, 'contrail-api')
            if result1 == False:
                self.logger.error("# While searching, rule not found. Configuration failed #")
                result = False 
        self.ds_obj.read_rule('default-discovery-service-assignment')
        self.logger.info("#### Waiting for 30 seconds so that TTL expiry for all subscriber happens ###")
        sleep(30)
        self.logger.debug("#### Verifying clients subscribed to publishers ###") 
        try:
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.ds_obj.verify_client_subscription_to_expected_publisher(\
                                ds_ip, 'contrail-vrouter-agent:0', \
                                self.inputs.compute_control_ips[i], 'Collector')
                if verification == False:
                    self.logger.error("# Rule not behaving as expected #")
                    result = False
            for i in range(0,len(self.inputs.bgp_control_ips)):
                verification = self.ds_obj.verify_client_subscription_to_expected_publisher\
                                (ds_ip, 'contrail-control', \
                                 self.inputs.bgp_control_ips[i], 'Collector')
                if verification == False:
                    self.logger.error("# Rule not behaving as expected #")
                    result = False
            for i in range(0,len(self.inputs.collector_control_ips)):
                verification = self.ds_obj.verify_client_subscription_to_expected_publisher\
                                (ds_ip, 'contrail-topology',\
                                self.inputs.collector_control_ips[i], 'Collector')
                if verification == False:
                    self.logger.error("# Rule not behaving as expected #")
                    result = False
            for i in range(0,len(self.inputs.cfgm_control_ips)):
                verification = self.ds_obj.verify_client_subscription_to_expected_publisher\
                                (ds_ip, 'contrail-api', \
                                 self.inputs.cfgm_control_ips[i], 'Collector')
                if verification == False:
                    self.logger.error("# Rule not behaving as expected #")
                    result = False
        except Exception as e:
            self.logger.error(e)
            result = False
        for i in range(0,len(self.inputs.collector_control_ips)): 
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            self.ds_obj.discovery_rule_config( 'del_rule',\
                'default-discovery-service-assignment', collector_control_ip,\
                'Collector', collector_control_ip, 'contrail-vrouter-agent:0',\
                collector_control_ip, 'contrail-topology', collector_control_ip,\
                'contrail-control', collector_control_ip, 'contrail-api')
            result1 = self.ds_obj.discovery_rule_config( "find_rule",\
                'default-discovery-service-assignment', collector_control_ip,\
                'Collector', collector_control_ip, 'contrail-vrouter-agent:0',\
                collector_control_ip, 'contrail-topology', collector_control_ip,\
                'contrail-control', collector_control_ip, 'contrail-api')
            if result1 == True:
                self.logger.error("# While searching for the deleted rule, it was found. Deletion failed #")
                result = False
        self.ds_obj.read_rule("default-discovery-service-assignment")
        assert result, "Test case failed due to some error. Please refer to logs"
    
    @preposttest_wrapper
    def test_subscribe_request_with_diff_instances_rules(self):
        ''' Validate that different instances of Publishers are assigned to
             client based on the instance value requested by clients.
            Also validate that if rules are present, requested instances are 
            restricted based on rules.
            Steps:
            1. Use a non contrail synthetic subscribe request to test this.
            2. Use some instance value in subscribe request and verify that 
                requested instances of publisher are assigned.
            3. Create a rule with same requested Publisher and subscribe request. 
            4. Verify that even if instances asked are more but as rule is present,
                the request will be restricted to get only 1 instance of that publisher.
            5. Delete the rule.
            6. Again test that same subscribe request will again get all instances requested.
            Precondition: Assumption is that setup is having a subscriber 
                connected to  3 instances of XMPP, all running in different subnets
                Also, setup requirement of this test case is to have at least 3 publishers
                All publishers should be in different network.
        '''
        self.ds_obj.skip_discovery_test("IfmapServer", min_instances=2, different_subnet_flag=False )
        result = True
        ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        assert self.ds_obj.modify_discovery_conf_file_params('change_min_max_ttl',\
                                                ttl_min=30, ttl_max=30)
        self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
        try:
            self.logger.info("#### Sending a dummy client request with instance value 3 ##")
            self.logger.info("### Client will subscribe to IfmapServer #####")
            self.ds_obj.subscribe_service_from_discovery(ds_ip, service="IfmapServer", \
                            instances="3", min_instances="0",\
                            client_id=self.inputs.compute_names[0]+":TestClient",\
                            remote_addr= self.inputs.compute_control_ips[0], \
                            client_type= "TestClient")
            sleep(2)
            self.logger.debug("# Verifying the number of instances of publishers granted to the client #")
            ifmap_server_count = len(self.inputs.cfgm_control_ips)
            client_subscribed_service_id = self.ds_obj.get_subscribed_service_id\
                                            (ds_ip, client=(self.inputs.compute_control_ips[0],\
                                            "TestClient"), service="IfmapServer")
            instances_allocated = len(client_subscribed_service_id)
            self.logger.debug("# The instances of publishers allocated to TestClient are %d #" \
                              % instances_allocated)
            self.logger.debug("# The total number of publishers running of such types are %d #" \
                              % ifmap_server_count)
            if ifmap_server_count == instances_allocated or (ifmap_server_count > 3 and instances_allocated == 3):
                self.logger.info("# Instance field working as expected #")
            else:
                self.logger.error("# Instance field not working as expected. #")
                result = False
        except Exception as e:
            self.logger.error(e)
            result = False
        try:
            self.logger.info("# Now creating a rule to verify that even if multiple\
            instances are requested but if a rule is present, it will limit the instances #")
            self.ds_obj.add_and_verify_rule(self.inputs.cfgm_control_ips[0], \
                'IfmapServer', self.inputs.compute_control_ips[0], 'TestClient')
        except Exception as e:
            self.logger.error(e)
            result = False
        self.logger.debug("#### Waiting for 30 seconds so that TTL expiry for all subscriber happens ###")
        sleep(30)
        try:
            self.logger.info("#### Sending a dummy client request with instance value 3 ##")
            self.logger.info("### Client will subscribe to IfmapServer #####")
            self.ds_obj.subscribe_service_from_discovery(ds_ip, service="IfmapServer",\
                            instances="3", min_instances="0",\
                            client_id=self.inputs.compute_names[0]+":TestClient",\
                            remote_addr= self.inputs.compute_control_ips[0],\
                            client_type= "TestClient")
            sleep(2)
            self.logger.debug("# Verifying the number of instances of publishers granted to the client #")      
            client_subscribed_service_id = self.ds_obj.get_subscribed_service_id\
                                            (ds_ip, client=(self.inputs.compute_control_ips[0],\
                                            "TestClient"), service="IfmapServer")
            instances_allocated = len(client_subscribed_service_id)
            service_IPs = []
            for i in range (0,instances_allocated):
                service_endpoint = self.ds_obj.get_service_endpoint_by_service_id\
                (ds_ip,client_subscribed_service_id[i])
                service_IPs.append(service_endpoint[0][0])
            self.logger.debug("# Number of instances of Publishers used by TestClient are %d" \
                              % (instances_allocated))
            self.logger.debug("# IPs of those publishers are %s #" % service_IPs)
            if instances_allocated==1 and service_IPs[0]==self.inputs.cfgm_control_ips[0]:
                self.logger.info("# As expected, TestClient is subscribed to only 1 instance of\
                IfmapServer even if it is requesting for 3 instances. This happened because of rule present #")
                pass
            else:
                result = False
                self.logger.error("# TestClient is subscribed to less/more than 1 instance of IfmapServer.#")
                self.logger.error("#Something went wrong. Expectedly, rules are not working.#")
        except Exception as e:
            self.logger.error(e)
            result = False
        try:
            self.logger.info("# Now deleting a rule to verify that after rule is deleted,\
             instances requested are granted without any restriction #")
            self.ds_obj.delete_and_verify_rule(self.inputs.cfgm_control_ips[0], \
                'IfmapServer', self.inputs.compute_control_ips[0], 'TestClient')
        except Exception as e:
            self.logger.error(e)
            result = False
        self.logger.debug("#### Waiting for 30 seconds so that TTL expiry for all subscriber happens ###")
        sleep (30)
        try:
            self.logger.info("#### Sending a dummy client request with instance value 3 ##")
            self.logger.info("### Client will subscribe to IfmapServer #####")
            self.ds_obj.subscribe_service_from_discovery(ds_ip, service="IfmapServer",\
                            instances="3", min_instances="0",\
                            client_id=self.inputs.compute_names[0]+":TestClient",\
                            remote_addr= self.inputs.compute_control_ips[0],\
                            client_type= "TestClient")
            sleep(2)
            self.logger.debug("# Verifying the number of instances of publishers granted to the client #")
            ifmap_server_count = len(self.inputs.cfgm_control_ips)
            client_subscribed_service_id = self.ds_obj.get_subscribed_service_id\
                                            (ds_ip, client=(self.inputs.compute_control_ips[0],\
                                            "TestClient"), service="IfmapServer")
            instances_allocated = len(client_subscribed_service_id)
            self.logger.debug("# The instances of publishers allocated to TestClient are %d #" \
                              % instances_allocated)
            self.logger.debug("# The total number of publishers running of such types are %d #"\
                               % ifmap_server_count)
            if ifmap_server_count == instances_allocated or (ifmap_server_count > 3 and instances_allocated == 3):
                self.logger.info("# Instance field working as expected #")
            else:
                self.logger.error(" # Instance field not working as expected.#")
                result = False
        except Exception as e:
            self.logger.error(e)
            result = False
        assert result, "Test case failed due to some error. Please refer to logs"
    
    @preposttest_wrapper    
    def test_rule_when_service_admin_down(self):
        ''' Validate that when publisher mentioned in rule is administratively
            down, the subscriber mentioned in rule, do not subscribe to any 
            other publisher.
            Also verify that when publisher comes up, the applicable instance 
            of that client get a subscription from that Publisher.
            For testing purpose, i have use DNS-SERVER as publisher and
            contrail-vrouter-agent as client.
            Steps:
            1. Create a rule using any Publisher and subscriber pair.
            2. Make the Publisher mentioned in the rule as admin down.
            3. Verify that as service is down, the subscriber will not get any
                 other instance of that service because rule still holds true.
            4. Make the Publisher as  admin UP.
            5. Verify that as soon as Publisher is made admin UP, the subscriber
                will get that instance of service.
            Precondition: Assumption is that setup is having a vrouter connected
                to 2 instances of DNS servers running in different subnets
                Also, setup requirement of this test case is to have at least
                2 publishers and 2 subscribers.
                Both set of publisher and subscriber should be in different network.
        '''
        self.ds_obj.skip_discovery_test("dns-server", min_instances=2, different_subnet_flag=False )
        result = True
        ds_ip = self.inputs.cfgm_ip
        assert self.ds_obj.resubscribe_with_new_ttl( 30, 30, 'contrail-vrouter-agent')
        self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
        try:
            self.logger.info("# Create a rule for control node Dns-Server ##")
            self.logger.info("# Subscriber in rule as contrail-vrouter-agent#")
            self.ds_obj.add_and_verify_rule(self.inputs.bgp_control_ips[0], 'dns-server',\
                        self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
            self.logger.info("# Making the admin state of dsn-server as *down*# ")
            self.ds_obj.update_service(ds_ip,service="dns-server",\
                        ip=self.inputs.bgp_control_ips[0],admin_state="down")
        except Exception as e:
            self.logger.error(e)
            result = False
        self.logger.debug("#### Waiting for 45 seconds so that TTL expiry for all subscriber happens ###")
        sleep (45)
        try:
            self.logger.debug("# Verifying that as publisher is admin down,\
             the mentioned subscriber in rule do not get any instance of Publisher #")      
            client_subscribed_service_id = self.ds_obj.get_subscribed_service_id\
                                            (ds_ip, client=(self.inputs.compute_control_ips[0],\
                                            "contrail-vrouter-agent:0"), service="dns-server")
            instances_allocated = len(client_subscribed_service_id)
            if instances_allocated==0:
                self.logger.info("# \n As expected, contrail-vrouter-agent running on %s\n \
                is not subscribed to any dns-server as the rule is restricting it to do\n \
                that and publisher mentioned in rule is admin *down*. #" % self.inputs.compute_control_ips[0])
                pass
            else:
                result = False
                self.logger.error("# \n Even if rule is present and publisher in rule\n \
                is admin *down*, some publisher got assigned to the subscriber\n \
                contrail-vrouter-agent running on %s .#", self.inputs.compute_control_ips[0])
                service_IPs = []
                for i in range (0,instances_allocated):
                    service_endpoint = self.ds_obj.get_service_endpoint_by_service_id\
                    (ds_ip,client_subscribed_service_id[i])
                    service_IPs.append(service_endpoint[0][0])
                self.logger.warn("# The publisher assigned to the client are running at following IPs: %s ###"\
                                  % service_IPs)
            self.logger.info("# Making the admin state of dsn-server as *up*# ")
            self.ds_obj.update_service(ds_ip,service="dns-server",\
                        ip=self.inputs.bgp_control_ips[0],admin_state="up")
            self.logger.debug("\n #### Waiting for 5 seconds so that the client \n \
            subscribe to the new subscriber as soon as it comes administratively up ###")
            sleep(5)
            self.logger.debug("\n # Verifying that as publisher is admin up,\n \
            the mentioned subscriber in rule gets the same instance of Publisher \n \
             as mentione din rule #")      
            client_subscribed_service_id = self.ds_obj.get_subscribed_service_id\
                                            (ds_ip, client=(self.inputs.compute_control_ips[0],\
                                            "contrail-vrouter-agent:0"), service="dns-server")
            instances_allocated = len(client_subscribed_service_id)
            service_IPs = []
            for i in range (0,instances_allocated):
                service_endpoint = self.ds_obj.get_service_endpoint_by_service_id\
                (ds_ip,client_subscribed_service_id[i])
                service_IPs.append(service_endpoint[0][0])
            if instances_allocated==1 and service_IPs[0]==self.inputs.bgp_control_ips[0]:
                self.logger.info("\n # As expected, contrail-vrouter-agent running \n \
                on %s is subscribed to single dns-server as the rule is \n \
                restricting it to do that. #" % self.inputs.compute_control_ips[0])
                pass
            else:
                result = False
                self.logger.error("\n # Even if rule is present and publisher in rule\n \
                is admin *up*, some different publishers or no publisher got \n \
                assigned to the subscriber contrail-vrouter-agent running on %s .#"\
                % self.inputs.compute_control_ips[0])
                self.logger.error("# The publisher assigned to the client are running at following IPs: %s###" \
                                   % service_IPs)
        except Exception as e:
            self.logger.error(e)
            result = False
        self.logger.info("# Now deleting the rule before starting new test case #")
        self.ds_obj.delete_and_verify_rule(self.inputs.bgp_control_ips[0], 'dns-server',\
                    self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
        assert result, "Test case failed due to some error. Please refer to logs"
    
    @preposttest_wrapper
    def test_multiple_rule_same_subscriber(self):
        ''' Validate that rule restrict the subscriber irrespective of number
             of instances requested by the client.
            Also verify that, if multiple rules are present for same client, 
            more instances of service gets allocated to that client.
            For testing purpose, i have used XMPP-SERVER as publisher and 
            contrail-vrouter-agent as client.
            Steps:
            1. Create different rules with same subscriber values and different Publishers.
            2. Verify if rule is working as expected or not
            Precondition: Assumption is that setup is having a vrouter connected
                to 2 instances of XMPP servers running in different subnets
                Also, setup requirement of this test case is to have at least 2
                publishers and 2 subscribers.
                Both set of publisher and subscriber should be in different network.
        '''
        self.ds_obj.skip_discovery_test("xmpp-server", min_instances=2, different_subnet_flag=False )
        result = True
        ds_ip = self.inputs.cfgm_ip
        assert self.ds_obj.resubscribe_with_new_ttl( 30, 30, 'contrail-vrouter-agent')
        self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
        try:
            self.logger.info("\n # Create a rule for xmpp-server running on\n \
            control node and subscriber as contrail-vrouter-agent   #")
            self.ds_obj.add_and_verify_rule(self.inputs.bgp_control_ips[0],'xmpp-server',\
                 self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
        except Exception as e:
            self.logger.error(e)
            result = False
        self.logger.debug("#### Waiting for 30 seconds so that TTL expiry for all subscriber happens ###")
        sleep (30)
        try:
            self.logger.debug("# Verifying that client is only subscribed to mentioned Publisher in the rule #")      
            client_subscribed_service_id = self.ds_obj.get_subscribed_service_id\
                            (ds_ip, client=(self.inputs.compute_control_ips[0],\
                            "contrail-vrouter-agent:0"), service="xmpp-server")
            instances_allocated = len(client_subscribed_service_id)
            service_IPs=[]
            for i in range (0,instances_allocated):
                    service_endpoint = self.ds_obj.get_service_endpoint_by_service_id\
                    (ds_ip,client_subscribed_service_id[i])
                    service_IPs.append(service_endpoint[0][0])
            if instances_allocated==1 and service_IPs[0]==self.inputs.bgp_control_ips[0]:
                self.logger.info("\n # Client contrail-vrouter-agent running on %s\n \
                is subscribed to expected xmpp-server as the rule is restricting \n \
                it to do that #" % self.inputs.compute_control_ips[0])
                pass
            else:
                result = False
                self.logger.error("\n # Even if rule is present, subscription\n \
                not happening as expected for contrail-vrouter-agent running on %s#"\
                 % self.inputs.compute_control_ips[0])
                self.logger.error("\n # The publisher assigned to the client are\n \
                running at following IPs: %s ###" % service_IPs)
                self.logger.error("\n # Expected was that client will subscribe only\n \
                to xmpp-server running on %s node" % self.inputs.bgp_control_ips[0])
        except Exception as e:
            self.logger.error(e)
            result = False
        try:
            self.logger.info("\n # Create another rule for xmpp-server running on\n \
            control node and subscriber as contrail-vrouter-agent so that \n \
            2nd instance of xmpp-server gets a Publisher  #")
            self.ds_obj.add_and_verify_rule(self.inputs.bgp_control_ips[1],'xmpp-server',\
                self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
        except Exception as e:
            self.logger.error(e)
            result = False
        self.logger.debug("#### Waiting for 30 seconds so that TTL expiry for all subscriber happens ###")
        sleep (30)
        try:
            self.logger.debug("\n # Verifying that 2nd instance of the client is\n \
            subscribed to mentioned Publisher in the rule #")      
            client_subscribed_service_id = self.ds_obj.get_subscribed_service_id\
                            (ds_ip, client=(self.inputs.compute_control_ips[0],\
                            "contrail-vrouter-agent:0"),service="xmpp-server")
            instances_allocated = len(client_subscribed_service_id)
            service_IPs=[]
            for i in range (0,instances_allocated):
                    service_endpoint = self.ds_obj.get_service_endpoint_by_service_id\
                    (ds_ip,client_subscribed_service_id[i])
                    service_IPs.append(service_endpoint[0][0])
            if instances_allocated==2 and service_IPs[0] in self.inputs.bgp_control_ips\
            and service_IPs[1] in self.inputs.bgp_control_ips:
                self.logger.info("\n # Client contrail-vrouter-agent running on %s\n \
                is subscribed to expected xmpp-server as the rule is restricting\n \
                it to do that #" % self.inputs.compute_control_ips[0])
                pass
            else:
                result = False
                self.logger.error("\n # Even if 2 rules are present, subscription\n \
                not happening as expected for contrail-vrouter-agent running on %s#"\
                 % self.inputs.compute_control_ips[0])
                self.logger.error("\n # The publisher assigned to the client are running\n \
                 at following IPs: %s ###" % service_IPs)
                self.logger.error("\n # Expected was that client will subscribe to\n \
                 xmpp-server running on %s and %s node" \
                 % (self.inputs.bgp_control_ips[0],self.inputs.bgp_control_ips[1]))
        except Exception as e:
            self.logger.error(e)
            result = False
        try:
            self.logger.info("# Now deleting the rule before starting new test case #")
            self.ds_obj.delete_and_verify_rule(self.inputs.bgp_control_ips[0],\
                'xmpp-server', self.inputs.compute_control_ips[0],'contrail-vrouter-agent:0')
            self.ds_obj.delete_and_verify_rule(self.inputs.bgp_control_ips[1],\
                'xmpp-server', self.inputs.compute_control_ips[0],'contrail-vrouter-agent:0')
        except Exception as e:
            self.logger.error(e)
            result = False
        assert result, "Test case failed due to some error. Please refer to logs"
    
    @preposttest_wrapper
    def test_rule_on_xmpp_do_not_impact_dns(self):
        ''' This test case is specifically written to test Bug ID "#1548771"
             [Discovery-Rel3.0-Centos-1]: Applying rule on DNS-server affects the rule 
             entry already applied to XMPP server and vice versa. 
             (Tested for client type : vrouter-agent) 
            Steps:
            1. Create 2 different rules with same subscriber as 
                "contrail-vrouter-agent" and using xmpp-server in rule 
                1 and dns-server in rule 2.
            2. Verify that both the rules work independently without impacting each other.
            Precondition: Assumption is that setup is having a vrouter connected
                 to 2 instances of XMPP  and DNS servers running in different subnets
                Also, setup requirement of this test case is to have at least 2 publishers
                and 2 subscribers.
                Both set of publisher and subscriber should be in different network.
        '''
        self.ds_obj.skip_discovery_test("xmpp-server", min_instances=2, different_subnet_flag=False )
        result = True
        ds_ip = self.inputs.cfgm_ip
        assert self.ds_obj.resubscribe_with_new_ttl( 30, 30, 'contrail-vrouter-agent')
        self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
        try:
            self.logger.info("\n # Create 2 rules for xmpp-server and dns-server\n \
             running on control node and subscriber as contrail-vrouter-agent#")
            self.ds_obj.add_and_verify_rule(self.inputs.bgp_control_ips[0],\
                'xmpp-server', self.inputs.compute_control_ips[0],\
                'contrail-vrouter-agent:0')
            self.ds_obj.add_and_verify_rule(self.inputs.bgp_control_ips[0],\
                'dns-server', self.inputs.compute_control_ips[0],\
                'contrail-vrouter-agent:0')
        except Exception as e:
            self.logger.error(e)
            result = False
        self.logger.debug("#### Waiting for 30 seconds so that TTL expiry for all subscriber happens ###")
        sleep (30)
        try:
            self.logger.debug("\n# Verifying that client is only subscribed to\n \
             mentioned Publishers in the rule #")      
            client_subscribed_xmpp_service_id = self.ds_obj.get_subscribed_service_id\
                        (ds_ip, client=(self.inputs.compute_control_ips[0],\
                        "contrail-vrouter-agent:0"), service="xmpp-server")
            client_subscribed_dns_service_id = self.ds_obj.get_subscribed_service_id\
                        (ds_ip, client=(self.inputs.compute_control_ips[0],\
                        "contrail-vrouter-agent:0"), service="dns-server")
            instances_allocated_xmpp = len(client_subscribed_xmpp_service_id)
            instances_allocated_dns = len(client_subscribed_dns_service_id)
            service_IPs_xmpp=[]
            service_IPs_dns=[]
            for i in range (0,instances_allocated_xmpp):
                    service_endpoint_xmpp = self.ds_obj.get_service_endpoint_by_service_id\
                    (ds_ip,client_subscribed_xmpp_service_id[i])
                    service_IPs_xmpp.append(service_endpoint_xmpp[0][0])
            for i in range (0,instances_allocated_dns):
                    service_endpoint_dns = self.ds_obj.get_service_endpoint_by_service_id\
                    (ds_ip,client_subscribed_dns_service_id[i])
                    service_IPs_dns.append(service_endpoint_dns[0][0])
            if instances_allocated_xmpp==1 and service_IPs_xmpp[0]==self.inputs.bgp_control_ips[0]:
                self.logger.info("\n # Client contrail-vrouter-agent running on %s\n \
                is subscribed to expected xmpp-server as the rule is restricting\n \
                it to do that #" % self.inputs.compute_control_ips[0])
                pass
            else:
                result = False
                self.logger.error("\n # Even if rule is present, subscription not\n \
                happening as expected for contrail-vrouter-agent running on %s .#" \
                % self.inputs.compute_control_ips[0])
                self.logger.debug("\n # The publisher assigned to the client are \n \
                running at following IPs: %s ###" % service_IPs_xmpp)
                self.logger.debug("\n # Expected was that client will subscribe only\n \
                to xmpp-server running on %s node" % self.inputs.bgp_control_ips[0])
            if instances_allocated_dns==1 and service_IPs_dns[0]==self.inputs.bgp_control_ips[0]:
                self.logger.info("\n # Client contrail-vrouter-agent running on %s \n \
                is subscribed to expected dns-server as the rule is restricting\n \
                it to do that #" % self.inputs.compute_control_ips[0])
                pass
            else:
                result = False
                self.logger.error("\n# Even if rule is present, subscription not\n \
                happening as expected for contrail-vrouter-agent running on %s .#" \
                % self.inputs.compute_control_ips[0])
                self.logger.debug("\n# The publisher assigned to the client are \n \
                running at following IPs: %s ###" % service_IPs_xmpp)
                self.logger.debug("\n# Expected was that client will subscribe only\n \
                to dns-server running on %s node" % self.inputs.bgp_control_ips[0])
        except Exception as e:
            self.logger.error(e)
            result = False
        try:
            self.logger.info("# Now deleting the rule before starting new test case #")
            self.ds_obj.delete_and_verify_rule(self.inputs.bgp_control_ips[0],\
                'xmpp-server', self.inputs.compute_control_ips[0],\
                'contrail-vrouter-agent:0')
            self.ds_obj.delete_and_verify_rule(self.inputs.bgp_control_ips[0],\
                'dns-server', self.inputs.compute_control_ips[0],\
                'contrail-vrouter-agent:0')
        except Exception as e:
            self.logger.error(e)
            result = False
        assert result, "Test case failed due to some error. Please refer to logs"
    
    def test_rule_with_vrouter_agent_do_not_impact_other_subscriptions(self):
        ''' This test case is specifically written to test Bug ID "#1541321" 
            [Discovery_R3.0_ubuntu_2704] : Rule mentioning contrail-vrouter-agent
            affects all the subscriptions of that client with all Publishers
            irrespective of the publisher mentioned in the rule. This happens for
            1/2 cycle of TTL and things recover after that.  
            Steps:
            1. Create a rule and mention subscriber as "contrail-vrouter-agent"
                and using dns-server as publisher.
            2. Verify that the configured rule do not impact subscription of
                "contrail-vrouter-agent" to xmpp-server even for one TTL cycle .
            Precondition: Assumption is that setup is having a vrouter connected
                to 2 instances of XMPP servers running in different subnets
                Also, setup requirement of this test case is to have at least
                2 publishers and 2 subscribers.
                Both set of publisher and subscriber should be in different network.
        '''
        self.ds_obj.skip_discovery_test("xmpp-server", min_instances=2, different_subnet_flag=False )
        result = True
        ds_ip = self.inputs.cfgm_ip
        assert self.ds_obj.resubscribe_with_new_ttl( 30, 30, 'contrail-vrouter-agent')
        self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
        try:
            self.logger.info("\n # Find the instances of subscription of \n \
            contrail-vrouter-agent  to the xmpp-server server #")
            xmpp_vrouter_subscription_list = self.ds_obj.get_all_xmpp_servers(ds_ip)
            self.logger.info("\n # Create a rule for dns-server running on \n \
            control node and subscriber as contrail-vrouter-agent   #")
            compute_control_ip = self.inputs.compute_control_ips[0].split('.')
            compute_control_ip[2:4] = '0','0'
            compute_control_ip = ".".join(compute_control_ip) + "/16"
            self.ds_obj.add_and_verify_rule(self.inputs.bgp_control_ips[0],\
                'dns-server', compute_control_ip, 'contrail-vrouter-agent:0')
            self.logger.debug("\n # Verify that subscription of vrouter-agent\n \
            to xmpp-server is not impacted due to the above rule for 90 seconds #")
            for i in range(1,60):
                new_xmpp_vrouter_subscription_list=self.ds_obj.get_all_xmpp_servers(ds_ip)
                sleep(1)
                if xmpp_vrouter_subscription_list == new_xmpp_vrouter_subscription_list:
                    pass
                else:
                    self.logger.warn("\n #### Some assignment change has happened\n \
                    for vrouter agent subscription to xmpp-server #####")
                    self.logger.warn("\n #### Earlier service IDs in use were %s\n \
                    and after waiting for %i seconds, the service ID has changed to %s #####"\
                    % (xmpp_vrouter_subscription_list,i,new_xmpp_vrouter_subscription_list))
                    result = False
                    break
        except Exception as e:
            self.logger.error(e)
            result = False
        try:
            self.logger.info("# Now deleting the rule before starting new test case #")
            self.ds_obj.delete_and_verify_rule(self.inputs.bgp_control_ips[0],\
                'dns-server', compute_control_ip, 'contrail-vrouter-agent:0')
        except Exception as e:
            self.logger.error(e)
            result = False
        assert result, "Test case failed due to some error. Please refer to logs"
        
    @preposttest_wrapper    
    def test_discovery_server_restart_rule_present(self):
        ''' Validate that rules are followed even after discovery server restarts.
            Steps:
            1. Create rule for any Publisher and subscriber pair and verify 
                that rule is behaving properly.
            2. Restart the discovery server on all config nodes.
            3. Verify that after discovery server comes up again, rules are 
                still followed.
            Precondition: Assumption is that setup is having a vrouter connected
                to 2 instances of XMPP servers running in different subnets
                Also, setup requirement of this test case is to have at least
                2 publishers and 2 subscribers.
                Both set of publisher and subscriber should be in different network.
        '''
        self.ds_obj.skip_discovery_test("IfmapServer", min_instances=2, different_subnet_flag=True )
        result = True
        ds_ip = self.inputs.cfgm_ip
        assert self.ds_obj.resubscribe_with_new_ttl( 30, 30, 'contrail-control')
        self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
        if len(self.inputs.cfgm_control_ips) > 0:
            self.logger.info("\n Creating rules corresponding to *IfmapServer*\n \
            running on all Config nodes for *contrail-control* running in same subnets")
        for i in range(0,len(self.inputs.cfgm_control_ips)):
            cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
            cfgm_control_ip[3] = '0'
            cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
            rule_status = self.ds_obj.add_and_verify_rule(cfgm_control_ip,\
                    'IfmapServer', cfgm_control_ip, 'contrail-control')
            if rule_status == False:
                result = False
        self.logger.debug("#### Waiting for 30 seconds so that TTL expiry for all subscriber happens ###")
        sleep (30)
        try:
            self.logger.debug("#### Verifying clients subscribed to publishers ###")
            for i in range(0,len(self.inputs.cfgm_control_ips)):
                verification = self.ds_obj.verify_client_subscription_to_expected_publisher\
                                (ds_ip, 'contrail-control',\
                                self.inputs.cfgm_control_ips[i], 'IfmapServer')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
            self.logger.debug("#### Stopping the discovery server process on all nodes ###")
            for ip in self.inputs.cfgm_ips:
                self.inputs.stop_service('contrail-discovery', [ip])
            self.logger.debug("\n #### Waiting for 60 seconds so that all clients\n \
            again try to resubscribe when discovery server is down ###")
            sleep(60)
            self.logger.debug("#### Starting the discovery server process on all nodes ###")
            for ip in self.inputs.cfgm_ips:
                self.inputs.start_service('contrail-discovery', [ip])
            for ip in self.inputs.cfgm_ips:
                client_status = self.inputs.confirm_service_active(\
                                                'contrail-discovery',ip)
                if client_status == False:
                    self.logger.error("Some issue happened after restart of discovery process")
                    result = False
                    assert result
            self.logger.debug("\n #### Verifying clients subscribed to publishers\n \
            as per rules, after discovery server restart ###")
            for i in range(0,len(self.inputs.cfgm_control_ips)):
                verification = self.ds_obj.verify_client_subscription_to_expected_publisher(\
                                ds_ip, 'contrail-control',\
                                self.inputs.cfgm_control_ips[i],'IfmapServer')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
        except Exception as e:
            self.logger.error(e)
            result = False
        try:    
            self.logger.info("#### Stopping the discovery server process on all nodes ###")            
            for i in range(0,len(self.inputs.cfgm_control_ips)): 
                cfgm_control_ip = self.inputs.cfgm_control_ips[i].split('.')
                cfgm_control_ip[3] = '0'
                cfgm_control_ip = ".".join(cfgm_control_ip) + "/24"
                rule_status = self.ds_obj.delete_and_verify_rule(cfgm_control_ip,\
                    'IfmapServer', cfgm_control_ip, 'contrail-control')
                if rule_status == False:
                    result = False
        except Exception as e:
            self.logger.error(e)
            result = False
        assert result, "Test case failed due to some error. Please refer to logs"
    
    @preposttest_wrapper
    def test_publisher_restart_rule_present(self):
        ''' Validate that rules are followed even after Publisher servers restarts.
            Steps:
            1. Create multiple rules for  Publisher and subscriber pairs and 
                verify that all rules are behaving properly.
            2. Restart the Publishers mentioned in the rules on all the 
                corresponding nodes.
            3. Verify that after Publisher service restart, rules are still followed.
            Precondition: Assumption is that setup is having a contrail-control
             connected to 2 instances of Ifmap servers running in different subnets
                Also, setup requirement of this test case is to have at least 2
                publishers and 2 subscribers.
                Both set of publisher and subscriber should be in different network.
        '''
        self.ds_obj.skip_discovery_test("xmpp-server", min_instances=2, different_subnet_flag=True )
        self.ds_obj.skip_discovery_test("Collector", min_instances=2, different_subnet_flag=True )
        result = True
        ds_ip = self.inputs.cfgm_ip
        assert self.ds_obj.resubscribe_with_new_ttl( 30, 30, 'contrail-vrouter-agent')
        self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
        self.logger.info("\n Creating rules corresponding to *xmpp-server*,\n \
         *dns-server* and *Collector* running on all control nodes for \n \
         *contrail-vrouter-agent* running in same subnets")
        for i in range(0,len(self.inputs.bgp_control_ips)):
            bgp_control_ip = self.inputs.bgp_control_ips[i].split('.')
            bgp_control_ip[3] = '0'
            bgp_control_ip = ".".join(bgp_control_ip) + "/24"
            rule_status = self.ds_obj.add_and_verify_rule(bgp_control_ip, \
                    'xmpp-server', bgp_control_ip, 'contrail-vrouter-agent:0')
            if rule_status == False:
                result = False
            rule_status = self.ds_obj.add_and_verify_rule(bgp_control_ip, \
                    'dns-server', bgp_control_ip, 'contrail-vrouter-agent:0')
            if rule_status == False:
                result = False
        for i in range(0,len(self.inputs.collector_control_ips)):
            collector_control_ip = self.inputs.collector_control_ips[i].split('.')
            collector_control_ip[3] = '0'
            collector_control_ip = ".".join(collector_control_ip) + "/24"
            rule_status = self.ds_obj.add_and_verify_rule(collector_control_ip,\
                'Collector', collector_control_ip, 'contrail-vrouter-agent:0')
            if rule_status == False:
                result = False
        self.logger.debug("#### Waiting for 30 seconds so that TTL expiry for all subscriber happens ###")
        sleep (30)
        try:
            self.logger.debug("#### Verifying clients subscribed to publishers ###")
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.ds_obj.verify_client_subscription_to_expected_publisher\
                                (ds_ip, 'contrail-vrouter-agent:0',\
                                self.inputs.compute_control_ips[i], 'xmpp-server')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.ds_obj.verify_client_subscription_to_expected_publisher\
                                (ds_ip, 'contrail-vrouter-agent:0',\
                                self.inputs.compute_control_ips[i], 'dns-server')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.ds_obj.verify_client_subscription_to_expected_publisher\
                                (ds_ip, 'contrail-vrouter-agent:0',\
                                 self.inputs.compute_control_ips[i], 'Collector')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
            self.logger.info("#### Restarting the xmpp, dns and Collector server process on all nodes ###")
            for ip in self.inputs.collector_ips:
                self.inputs.restart_service('contrail-collector', [ip])
            for ip in self.inputs.bgp_ips:
                self.inputs.restart_service('contrail-control', [ip])
                self.inputs.restart_service('contrail-dns', [ip])
            for ip in self.inputs.collector_ips:
                client_status = self.inputs.confirm_service_active(\
                                                'contrail-collector', ip)
                if client_status == False:
                    self.logger.error("Some issue happened after restart of server process")
                    result = False
                    assert result
            for ip in self.inputs.bgp_ips:
                client_status = self.inputs.confirm_service_active(\
                                                'contrail-control', ip)
                if client_status == False:
                    self.logger.error("Some issue happened after restart of server process")
                    result = False
                    assert result
            for ip in self.inputs.bgp_ips:
                client_status = self.inputs.confirm_service_active(\
                                                    'contrail-dns', ip)
                if client_status == False:
                    self.logger.error("Some issue happened after restart of server process")
                    result = False
                    assert result
            self.logger.debug("\n #### Waiting for 30 seconds so that all clients\n \
                         again try to resubscribe when discovery server is down ###")
            sleep(30)
            self.logger.debug("\n #### Verifying clients subscribed to publishers\n \
            should follow rules even after publisher process restart ###")
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.ds_obj.verify_client_subscription_to_expected_publisher\
                                (ds_ip, 'contrail-vrouter-agent:0',\
                                self.inputs.compute_control_ips[i], 'xmpp-server')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.ds_obj.verify_client_subscription_to_expected_publisher\
                                (ds_ip, 'contrail-vrouter-agent:0',\
                                self.inputs.compute_control_ips[i], 'dns-server')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
            for i in range(0,len(self.inputs.compute_control_ips)):
                verification = self.ds_obj.verify_client_subscription_to_expected_publisher\
                                (ds_ip, 'contrail-vrouter-agent:0',\
                                self.inputs.compute_control_ips[i], 'Collector')
                if verification == False:
                    self.logger.error("Rule not behaving as expected")
                    result = False
        except Exception as e:
            self.logger.error(e)
            result = False
        try:    
            self.logger.info("#### Deleting the rules at end of test acse ###")          
            for i in range(0,len(self.inputs.bgp_control_ips)):
                bgp_control_ip = self.inputs.bgp_control_ips[i].split('.')
                bgp_control_ip[3] = '0'
                bgp_control_ip = ".".join(bgp_control_ip) + "/24"
                rule_status = self.ds_obj.delete_and_verify_rule( bgp_control_ip,\
                    'xmpp-server', bgp_control_ip, 'contrail-vrouter-agent:0')
                if rule_status == False:
                    result = False
                rule_status = self.ds_obj.delete_and_verify_rule( bgp_control_ip,\
                    'dns-server', bgp_control_ip, 'contrail-vrouter-agent:0')
                if rule_status == False:
                    result = False
            for i in range(0,len(self.inputs.collector_control_ips)):
                collector_control_ip = self.inputs.collector_control_ips[i].split('.')
                collector_control_ip[3] = '0'
                collector_control_ip = ".".join(collector_control_ip) + "/24"
                rule_status = self.ds_obj.delete_and_verify_rule(collector_control_ip,\
                    'Collector', collector_control_ip, 'contrail-vrouter-agent:0')
                if rule_status == False:
                    result = False
        except Exception as e:
            self.logger.error(e)
            result = False
        assert result, "Test case failed due to some error. Please refer to logs"
        
    @preposttest_wrapper
    def test_auto_load_balance_Ifmap(self):
        ''' Validate that auto load balance works correctly for IfmapServer.
            Steps:
            1. Verify that normal load balancing is working correctly by 
                default on IfmapServer.    
            2. Set auto load balance as *True* and stop any one of the IfmapServers.
            3. Verify that stopped Server loses all it's subscribers.
            4. Again start the IfmapServer which was stopped earlier.
            5. Verify auto load balancing takes place.
            Precondition: Assumption is that setup is having at least 3 Ifmap Servers
        '''
        self.ds_obj.skip_discovery_test("IfmapServer", min_instances=3, different_subnet_flag=False )
        result = True
        ds_ip = self.inputs.cfgm_ip
        assert self.ds_obj.resubscribe_with_new_ttl( 30, 30, 'supervisor-control')
        self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
        self.logger.info("# Setting auto load balance to true in contrail-discovery.conf file #")  
        assert self.ds_obj.modify_discovery_conf_file_params( 'set_policy',\
                    publisher_type="IFMAPSERVER",policy='dynamic-load-balance')
        try:
            self.logger.debug("# Verifying that discovery server auto load balance for 'IfmapServer' #")
            self.logger.info("# Stopping the IfmapServer on one of the config node until it looses all subscribers #")
            self.inputs.stop_service('supervisor-config',\
                                     host_ips=[self.inputs.cfgm_ips[0]])
            self.logger.debug("# Waiting for 45 seconds to wait for server to lose all subscriptions #")
            sleep(45)
            count=self.ds_obj.get_service_in_use(ds_ip,(self.inputs.cfgm_control_ips[0],\
                                                 'IfmapServer'))
            if count == 0:
                pass
            else:
                self.logger.error("\n # Even if Server is not running, it still\n \
                 has %d *in use* subscription. Something is wrong #" % count)
                self.inputs.start_service('supervisor-config',\
                                      host_ips=[self.inputs.cfgm_ips[0]])
                self.inputs.confirm_service_active(\
                                    'supervisor-config',self.inputs.cfgm_ips[0])
                self.ds_obj.modify_discovery_conf_file_params( 'set_policy',\
                    publisher_type="IFMAPSERVER",policy='load-balance')
                result = False
                assert result
            self.logger.info("\n # Starting the IfmapServer on one of the config node\n \
            expecting that subscriptions will happen again #")
            self.inputs.start_service('supervisor-config',\
                                      host_ips=[self.inputs.cfgm_ips[0]])
            client_status = self.inputs.confirm_service_active(\
                                    'supervisor-config',self.inputs.cfgm_ips[0])
            if client_status == False:
                self.logger.error("# Some issue happened after restart of config server #")
                self.ds_obj.modify_discovery_conf_file_params( 'set_policy',\
                    publisher_type="IFMAPSERVER",policy='load-balance')
                result = False
                assert result
            self.logger.debug("# Waiting for 30 seconds for restarted server to again get all subscriptions #")
            sleep(30)
            self.logger.debug("# Verifying that auto load balance worked properly or not after service restart #")    
            load_balance = self.ds_obj.check_load_balance(ds_ip, 'IfmapServer')
            if load_balance == False:
                result=False
        except Exception as e:
            self.logger.error(e)
            result = False
        self.logger.info("# Setting policy to 'load-balance' in contrail-discovery.conf file #")  
        assert self.ds_obj.modify_discovery_conf_file_params( 'set_policy',\
                    publisher_type="IFMAPSERVER",policy='load-balance')
        try:
            self.logger.debug("\n # Verifying that discovery server do not do\n \
            auto load balance for *IfmapServer* as policy is set to 'load-balance' #")
            self.logger.info("\n # Stopping the IfmapServer on one of the config\n \
            node until it looses all subscribers #")
            self.inputs.stop_service('supervisor-config',\
                                     host_ips=[self.inputs.cfgm_ips[0]])
            self.logger.debug("# Waiting for 45 seconds to wait for server to lose all subscriptions #")
            sleep(45)
            count=self.ds_obj.get_service_in_use(ds_ip,(self.inputs.cfgm_control_ips[0],\
                                                   'IfmapServer'))
            if count == 0:
                pass
            else:
                self.logger.error("\n # Even if Server is not running, it still has %d\n \
                *in use* subscription. Something is wrong #" % count)
                result = False
                self.inputs.start_service('supervisor-config',\
                                      host_ips=[self.inputs.cfgm_ips[0]])
                self.inputs.confirm_service_active(\
                                    'supervisor-config',self.inputs.cfgm_ips[0])
                assert result
            self.logger.info("\n # Starting the IfmapServer on one of the config node\n \
            expecting that re-subscription will not happen again as auto load balance is off #")
            self.inputs.start_service('supervisor-config',\
                                      host_ips=[self.inputs.cfgm_ips[0]])
            client_status = self.inputs.confirm_service_active(\
                                    'supervisor-config',self.inputs.cfgm_ips[0])
            if client_status == False:
                self.logger.error("# Some issue happened after restart of config server #")
                result = False
                assert result
            self.logger.debug("\n # Waiting for 30 seconds to wait for restarted server\n \
            to give time in case any client subscribes to this server. Not expecting this to happen #")
            sleep(30)
            self.logger.debug("\n # Verifying that as auto load balance was off,\n \
            the restarted service is not used by any subscriber #")    
            count=self.ds_obj.get_service_in_use(ds_ip, (self.inputs.cfgm_control_ips[0],\
                                                  'IfmapServer'))
            if count == 0:
                pass
            else:
                self.logger.error("\n # Even if Server has just restarted and \n \
                auto load balance is off, it has got new subscriptions. Something is wrong #")
                self.logger.error("# Total subscribers which got attached to restarted service are %d #"\
                                   % count)
                result = False
        except Exception as e:
            self.logger.error(e)
            result = False
        assert result, "Test case failed due to some error. Please refer to logs"
    
    @preposttest_wrapper    
    def test_auto_load_balance_xmpp(self):
        ''' Validate that auto load balance works correctly for XmppServer.
            This script also validates Bug 1395099 : Trigger subscription 
            from discovery client for faster convergence
            Steps:
            1. Verify that normal load balancing is working correctly by default 
                on Xmpp-Server.    
            2. Set auto load balance as *True* and stop any one of the Xmpp-Server.
            3. Verify that stopped Server loses all it's subscribers.
            4. Again start the Xmpp-Server which was stopped earlier.
            5. Verify auto load balancing takes place.
            Precondition: Assumption is that setup is having at least 3 XMPP Servers
        '''
        self.ds_obj.skip_discovery_test("xmpp-server", min_instances=3, different_subnet_flag=False )
        result = True
        ds_ip = self.inputs.cfgm_ip
        assert self.ds_obj.resubscribe_with_new_ttl( 30, 30, 'contrail-vrouter-agent')
        self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
        self.logger.info("# Setting auto load balance to true in contrail-discovery.conf file #")  
        assert self.ds_obj.modify_discovery_conf_file_params( 'set_policy',\
                    publisher_type="XMPP-SERVER",policy='dynamic-load-balance')
        try:
            self.logger.debug("# Verifying that discovery server auto load balance for 'XmppServer' #")
            self.logger.info("# Stopping the XmppServer on one of the control node until it looses all subscribers #")
            self.inputs.stop_service('contrail-control',\
                                    host_ips=[self.inputs.bgp_ips[0]])
            self.logger.debug("# Waiting for 20 seconds to wait for server to lose all subscriptions #")
            sleep(20)
            count=self.ds_obj.get_service_in_use(ds_ip,(self.inputs.bgp_control_ips[0],\
                                                 'xmpp-server'))
            if count == 0:
                self.logger.info("## After XMPP server is made down, it looses all subscriptions within 20 seconds")
                pass
            else:
                self.logger.error("\n # Even if Server is not running, it still has %d\n \
                 *in use* subscription. Something is wrong #" % count)
                result = False
                self.inputs.start_service('contrail-control',\
                                      host_ips=[self.inputs.bgp_ips[0]])
                self.inputs.confirm_service_active(\
                                        'contrail-control',self.inputs.bgp_ips[0])
                self.ds_obj.modify_discovery_conf_file_params( 'set_policy',\
                    publisher_type="XMPP-SERVER",policy='load-balance')
                assert result
            self.logger.info("\n# Starting the XmppServer on one of the control node\n \
             expecting that subscriptions will happen again #")
            self.inputs.start_service('contrail-control',\
                                      host_ips=[self.inputs.bgp_ips[0]])
            client_status = self.inputs.confirm_service_active(\
                                        'contrail-control',self.inputs.bgp_ips[0])
            if client_status == False:
                self.logger.error("# Some issue happened after restart of control server #")
                self.ds_obj.modify_discovery_conf_file_params( 'set_policy',\
                    publisher_type="XMPP-SERVER",policy='load-balance')
                result = False
                assert result
            self.logger.debug("# Waiting for 30 seconds for restarted server to again get all subscriptions#")
            sleep(30)
            self.logger.debug("# Verifying that auto load balance worked properly or not after service restart #")    
            load_balance = self.ds_obj.check_load_balance(ds_ip, 'xmpp-server')
            if load_balance == False:
                result=False
        except Exception as e:
            self.logger.error(e)
            result = False
        self.logger.info("# Setting policy as  'load-balance' in contrail-discovery.conf file #")  
        assert self.ds_obj.modify_discovery_conf_file_params( 'set_policy',\
                    publisher_type="XMPP-SERVER",policy='load-balance')
        try:
            self.logger.debug("\n# Verifying that discovery server do not do\n \
            auto load balance for *XmppServer* as policy is set to 'load-balance' #")
            self.logger.info("\n# Stopping the XmppServer on one of the control \n \
            node until it looses all subscribers #")
            self.inputs.stop_service('contrail-control',\
                                     host_ips=[self.inputs.bgp_ips[0]])
            self.logger.debug("# Waiting for 20 seconds to wait for server to lose all subscriptions #")
            sleep(20)
            count=self.ds_obj.get_service_in_use(ds_ip,(self.inputs.bgp_control_ips[0],\
                                                 'xmpp-server'))
            if count == 0:
                self.logger.info("## After XMPP server is made down, it looses all subscriptions within 20 seconds")
                pass
            else:
                self.logger.error("\n# Even if Server is not running, it still has %d\n\
                 *in use* subscription. Something is wrong #" % count)
                self.inputs.start_service('contrail-control',\
                                      host_ips=[self.inputs.bgp_ips[0]])
                self.inputs.confirm_service_active(\
                                        'contrail-control',self.inputs.bgp_ips[0])
                result = False
                assert result
            self.logger.info("\n# Starting the XmppServer on one of the control node\n \
             expecting that re-subscription will not happen again as auto load balance is off #")
            self.inputs.start_service('contrail-control',\
                                      host_ips=[self.inputs.bgp_ips[0]])
            client_status = self.inputs.confirm_service_active(\
                                        'contrail-control',self.inputs.bgp_ips[0])
            if client_status == False:
                self.logger.error("# Some issue happened after restart of control server #")
                result = False
                assert result
            self.logger.debug("\n# Waiting for 30 seconds for restarted server\n \
            to give time in case any client subscribes to this server. \n \
            Not expecting this to happen# ")
            sleep(30)
            self.logger.debug("\n# Verifying that as auto load balance was off,\n \
             the restarted service is not used by any subscriber #")    
            count=self.ds_obj.get_service_in_use(ds_ip,(self.inputs.bgp_control_ips[0],\
                                                 'xmpp-server'))
            if count == 0:
                pass
            else:
                self.logger.error("\n# Even if Server has just restarted and \n \
                auto load balance is off, it has got new subscriptions. Something is wrong #")
                self.logger.error("# Total subscribers which got attached to restarted service are %d #"\
                                   % count)
                result = False
        except Exception as e:
            self.logger.error(e)
            result = False
        assert result, "Test case failed due to some error. Please refer to logs"
    
    @preposttest_wrapper    
    def test_auto_load_balance_collector(self):
        ''' Validate that auto load balance works correctly for Collector.
            Steps:   
            1. Set auto load balance as *True* and stop any one of the Collector.
            2. Verify that stopped Server loses all it's subscribers.
            3. Again start the Collector which was stopped earlier.
            4. Verify auto load balancing takes place.
            Precondition: Assumption is that setup is having at least 3 Collectors
        '''
        self.ds_obj.skip_discovery_test("Collector", min_instances=3, different_subnet_flag=False )
        result = True
        ds_ip = self.inputs.cfgm_ip
        self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
        assert self.ds_obj.modify_discovery_conf_file_params('change_min_max_ttl',\
                                                ttl_min=30, ttl_max=30)
        self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
        self.logger.info("#### Restarting the required subscriber services so that TTL takes effect immediately ###")
        for ip in self.inputs.collector_ips:
            self.inputs.restart_service('supervisor-analytics', [ip])
        for ip in self.inputs.compute_ips:
            self.inputs.restart_service('supervisor-vrouter', [ip])
        for ip in self.inputs.bgp_ips:
            self.inputs.restart_service('supervisor-control', [ip])
        for ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('supervisor-config', [ip])
        for ip in self.inputs.webui_ips:
            self.inputs.restart_service('supervisor-webui', [ip])
        for ip in self.inputs.database_ips:
            self.inputs.restart_service('contrail-database', [ip])
            self.inputs.restart_service('contrail-database-nodemgr', [ip])
        client_status = ContrailStatusChecker()
        client_status.wait_till_contrail_cluster_stable(self.inputs.host_ips)      
        self.logger.info("# Setting auto load balance to true in contrail-discovery.conf file #")  
        assert self.ds_obj.modify_discovery_conf_file_params( 'set_policy',\
                    publisher_type="COLLECTOR",policy='dynamic-load-balance')
        try:
            self.logger.debug("# Verifying that discovery server auto load balance for 'Collector'#")
            self.logger.info("# Stopping the Collector on one of the Analytic node until it looses all subscribers #")
            self.inputs.stop_service('contrail-collector',\
                                     host_ips=[self.inputs.collector_ips[0]])
            self.logger.debug("# Waiting for 45 seconds to wait for server to lose all subscriptions #")
            sleep(45)
            count=self.ds_obj.get_service_in_use(ds_ip,\
                        (self.inputs.collector_control_ips[0],'Collector'))
            if count == 0:
                pass
            else:
                self.logger.error("\n # Even if Server is not running,\n \
                it still has %d *in use* subscription. Something is wrong #" % count)
                result = False
                self.inputs.start_service('contrail-collector',\
                                      host_ips=[self.inputs.collector_ips[0]])
                self.inputs.confirm_service_active(\
                            'contrail-collector',self.inputs.collector_ips[0])
                self.ds_obj.modify_discovery_conf_file_params( 'set_policy',\
                    publisher_type="COLLECTOR",policy='load-balance')
                assert result
            self.logger.info("\n # Starting the Collector on one of the Analytic node\n \
             expecting that subscriptions will happen again #")
            self.inputs.start_service('contrail-collector',\
                                      host_ips=[self.inputs.collector_ips[0]])
            client_status = self.inputs.confirm_service_active(\
                            'contrail-collector',self.inputs.collector_ips[0])
            if client_status == False:
                self.logger.error("# Some issue happened after restart of Collector#")
                self.ds_obj.modify_discovery_conf_file_params( 'set_policy',\
                    publisher_type="COLLECTOR",policy='load-balance')
                result = False
                assert result
            self.logger.debug("# Waiting for 30 seconds for restarted server to again get all subscriptions #")
            sleep(30)
            self.logger.debug("# Verifying that auto load balance worked properly or not after service restart #")    
            load_balance = self.ds_obj.check_load_balance(ds_ip, 'Collector')
            if load_balance == False:
                result=False
        except Exception as e:
            self.logger.error(e)
            result = False
        self.logger.info("# Setting policy as 'load-balance' in contrail-discovery.conf file #")  
        assert self.ds_obj.modify_discovery_conf_file_params( 'set_policy',\
                    publisher_type="COLLECTOR",policy='load-balance')
        try:
            self.logger.debug("\n # Verifying that discovery server do not do\n \
             auto load balance for *Collector* as it is set to load-balance #")
            self.logger.info("\n # Stopping the Collector on one of the Analytic node\n \
             until it looses all subscribers #")
            self.inputs.stop_service('contrail-collector',\
                                     host_ips=[self.inputs.collector_ips[0]])
            self.logger.debug("# Waiting for 45 seconds to wait for server to lose all subscriptions #")
            sleep(45)
            count=self.ds_obj.get_service_in_use(ds_ip,\
                        (self.inputs.collector_control_ips[0],'Collector'))
            if count == 0:
                pass
            else:
                self.logger.error("\n # Even if Server is not running, it still has %d\n \
                 *in use* subscription. Something is wrong #" % count)
                self.inputs.start_service('contrail-collector',\
                                      host_ips=[self.inputs.collector_ips[0]])
                self.inputs.confirm_service_active(\
                            'contrail-collector',self.inputs.collector_ips[0])
                result = False
                assert result
            self.logger.info("\n # Starting the Collector on one of the Analytic node\n \
             expecting that re-subscription will not happen again as auto load balance is off # ")
            self.inputs.start_service('contrail-collector',\
                                      host_ips=[self.inputs.collector_ips[0]])
            client_status = self.inputs.confirm_service_active(\
                            'contrail-collector',self.inputs.collector_ips[0])
            if client_status == False:
                self.logger.error("# Some issue happened after restart of Collector #")
                result = False
                assert result
            self.logger.debug("\n # Waiting for 30 seconds for restarted server\n \
            to give time in case any client subscribes to this server. Not expecting this to happen #")
            sleep(30)
            self.logger.debug("\n # Verifying that as auto load balance was off,\n \
            the restarted service is not used by any subscriber #")    
            count = self.ds_obj.get_service_in_use(ds_ip,\
                    (self.inputs.collector_control_ips[0],'Collector'))
            if count == 0:
                pass
            else:
                self.logger.error("\n # Even if Server has just restarted and \n \
                auto load balance is off, it has got new subscriptions. Something is wrong #" )
                self.logger.error("# Total subscribers which got attached to restarted service are %d #" % count)
                result = False
        except Exception as e:
            self.logger.error(e)
            result = False
        assert result, "Test case failed due to some error. Please refer to logs"
    
    @preposttest_wrapper    
    def test_rules_preferred_over_auto_load_balance(self):
        ''' Validate that rules always takes precedence over auto load balance.
            Also verify that when rules are deleted, auto load balance takes its effect.
            Steps:   
            1. Verify that normal load balancing is working correctly by default
                on XMpp-Server.
            2. Set auto load balance as *True* and stop any one of the Xmpp-Server.
            3. Create multiple rules with single xmpp-server to subscribe to all 
                vrouter-agents in the topology.
            4. Verify that rule is preferred over load balancing and no other
                xmpp-server in the topology gets any subscription.
            5. Delete the rules and verify that auto load balancing takes place.
            Precondition: Assumption is that setup is having at least 3 XMPP Servers
                Also, all XMPP Servers should be in different subnet
        '''
        self.ds_obj.skip_discovery_test("xmpp-server", min_instances=3, different_subnet_flag=False )
        result = True
        ds_ip = self.inputs.cfgm_ip
        assert self.ds_obj.resubscribe_with_new_ttl( 30, 30, 'contrail-vrouter-agent')
        self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
        self.logger.info("# Setting auto load balance to true in contrail-discovery.conf file #")  
        assert self.ds_obj.modify_discovery_conf_file_params( 'set_policy',\
                    publisher_type="XMPP-SERVER",policy='dynamic-load-balance')
        self.logger.debug("# Waiting for 30 seconds to wait for auto load balance to happen #")
        sleep(30)
        try:
            self.logger.info("# Verifying that discovery server is properly load balancing for 'XmppServer' # ")
            load_balance = self.ds_obj.check_load_balance(ds_ip,'xmpp-server')
            if load_balance == False:
                result=False
        except Exception as e:
            self.logger.error(e)
            result = False
        if len(self.inputs.bgp_control_ips) > 0:
            self.logger.info("\n # Creating rules corresponding to *xmpp-server*\n \
            so that all *contrail-vrouter-agent* on any network connects to\n \
            *xmpp-server* running on cfgm0 #")
        for i in range(0,len(self.inputs.compute_control_ips)):
            rule_status = self.ds_obj.add_and_verify_rule(\
                self.inputs.bgp_control_ips[0], 'xmpp-server',\
                self.inputs.compute_control_ips[i], 'contrail-vrouter-agent:0')
            if rule_status == False:
                result = False
        self.logger.info("#### Waiting for 30 seconds so that TTL expiry for all subscriber happens ###")
        sleep (30)
        self.logger.info("#### Verifying that all vrouter-agents subscribe to control node xmpp-server only ###")
        try:
            in_use_list = []
            for i in range(0,len(self.inputs.bgp_control_ips)): 
                in_use_list_elem = self.ds_obj.get_service_in_use\
                (ds_ip, (self.inputs.bgp_control_ips[i],'xmpp-server'))
                in_use_list.append(in_use_list_elem)
            if in_use_list[0] > 0 and sum(in_use_list[1:len(in_use_list)]) == 0:
                self.logger.info("# Rule working as expected. All clients subscribed only to cfgm0 xmpp-server #")
                self.logger.info("# Even if Auto load balance is *True*, rule is taking the priority #")
                pass
            else:
                self.logger.error("\n# Even if rule is applied, rule is not working as expected.\n \
                 May be auto load balance being *True* is creating issue #")
                self.logger.error("\n# It was expected that only cfgm0 xmpp-server\n \
                 will have subscriptions and rest of the xmpp-servers will not have any subscriptions #")
                self.logger.error("\n# The *in-use* list for all xmpp-servers is %s#"\
                                   % in_use_list)
                result = False
        except Exception as e:
            self.logger.error(e)
            result = False
        for i in range(0,len(self.inputs.compute_control_ips)): 
            rule_status = self.ds_obj.delete_and_verify_rule(\
                self.inputs.bgp_control_ips[0], 'xmpp-server',\
                self.inputs.compute_control_ips[i], 'contrail-vrouter-agent:0')
            if rule_status == False:
                result = False
        try:
            self.logger.info("\n # Waiting for 60 seconds(2 TTL cycles)\n \
            to wait for re-subscription and load-balancing to happen after deleting rules #")
            sleep(60)   
            self.logger.info("\n # Verifying that discovery server \n \
            auto load balance for 'XmppServer' as soon as rules are deleted #")
            load_balance = self.ds_obj.check_load_balance(ds_ip,'xmpp-server')
            if load_balance == False:
                result=False
        except Exception as e:
            self.logger.error(e)
            result = False
        self.logger.info(" # Deleting the policy configuration from contrail-discovery.conf file #")  
        assert self.ds_obj.modify_discovery_conf_file_params( 'del_policy',\
                                            publisher_type="XMPP-SERVER")
        assert result, "Test case failed due to some error. Please refer to logs"
    
    @preposttest_wrapper        
    def test_service_in_use_list(self):
        ''' Validate that subscribe request with instance value as 0 and having
            service-in-use-list is considered a subscription request and 
            publishers are assigned to it properly.
            Steps:
            1. Get in-use count of publishers before sending a subscribe 
                request having service-in-use list
            2. Send a subscribe request with instance value as '0' and 
                service-in-use list present in that subscribe request.
            3. See if the in-use count of the publisher increases and client 
                get subscribed successfully.
            Precondition: Assumption is that setup is having at least 3 Ifmap Servers
        '''
        self.ds_obj.skip_discovery_test("IfmapServer", min_instances=3, different_subnet_flag=False )
        result = True
        ds_ip = self.inputs.cfgm_ip
        try:
            self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
            assert self.ds_obj.modify_discovery_conf_file_params(operation='change_min_max_ttl',\
                                                   ttl_min=30, ttl_max=30)
            self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
            self.logger.info("\n# Verifying that if a subscriber has a service in use list,\n\
             same publishers are assigned to it as mentioned in the list.# ")
            self.logger.info("\n#### Getting the in-use count of all Ifmap Servers \n\
            before sending dummy subscribe request ###")
            in_use_list = []
            for i in range(0,len(self.inputs.cfgm_control_ips)): 
                in_use_list_elem = self.ds_obj.get_service_in_use(ds_ip,\
                            (self.inputs.cfgm_control_ips[i],'IfmapServer'))
                in_use_list.append(in_use_list_elem)
            sum_in_use_bfr_subscribe_request = sum(in_use_list)
            self.logger.info("\n#### Total in-use clients subscribed to IfmapServer are %d #####"\
                              % sum_in_use_bfr_subscribe_request)
            self.logger.info("\n#### Sending a dummy client request with instance value as 0\n\
             to subscribe to IfmapServer #####")
            self.logger.info("\n#### The dummy request will have a service-in-use-list \n\
            containing IPs of all Ifmap Server present in the network #####")
            self.ds_obj.subscribe_service_from_discovery(ds_ip, service="IfmapServer",\
                instances="0", min_instances=len(self.inputs.cfgm_control_ips),\
                client_id=self.inputs.compute_names[0]+":TestClient",\
                remote_addr=self.inputs.compute_control_ips[0],client_type="TestClient",\
                svc_in_use_list_present=True,svc_in_use_list=self.inputs.cfgm_control_ips)
            sleep(2)
            self.logger.info("\n#### Getting the in-use count of all Ifmap Servers \n\
            after sending dummy subscribe request ###")
            in_use_list = []
            for i in range(0,len(self.inputs.cfgm_control_ips)): 
                in_use_list_elem = self.ds_obj.get_service_in_use(ds_ip, \
                                        (self.inputs.cfgm_control_ips[i],'IfmapServer'))
                in_use_list.append(in_use_list_elem)
            sum_in_use_aftr_subscribe_request = sum(in_use_list)
            self.logger.info("\n Total in-use clients subscribed to IfmapServer after dummy request are %d"\
                              % sum_in_use_aftr_subscribe_request)
            client_subscribed_service_id = self.ds_obj.get_subscribed_service_id(\
                                ds_ip, client=(self.inputs.compute_control_ips[0],\
                                "TestClient"), service="IfmapServer")
            instances_allocated = len(client_subscribed_service_id)
            service_IPs=[]
            for i in range (0,instances_allocated):
                    service_endpoint = self.ds_obj.get_service_endpoint_by_service_id(\
                                            ds_ip,client_subscribed_service_id[i])
                    service_IPs.append(service_endpoint[0][0])
            self.logger.info("\n# The publishers mentioned in service-in-use list are %s\n\
             and the client is actually subscribed to following publishers %s.######## " \
             % (self.inputs.cfgm_control_ips,service_IPs))
            if instances_allocated == len(self.inputs.cfgm_control_ips) and \
            sum_in_use_aftr_subscribe_request > sum_in_use_bfr_subscribe_request:
                self.logger.info("\n# The subscribe request with instance as 0 \n\
                and service-in-use list has subscribed to expected publishers.######## ")
            else:
                self.logger.info("\n# Something went wrong. \n \
                Expected Publishers not assigned to client request having service in use list ######## ")
                result=False
            self.logger.info("\n##### Waiting for 30 seconds so that dummy client request\n \
             ages out and do not interfere with other test cases ######")
            sleep(30)
        except Exception as e:
            self.logger.error(e)
            result = False
        assert result, "Test case failed due to some error. Please refer to logs"
        
    @preposttest_wrapper
    def test_white_list_security(self):
        ''' To prevent unauthorized publish or subscribe requests to effect
            discovery server state (and assuming such requests are coming through
            load-balancer such ha-proxy), discovery server to apply configured
            publish and subscribe white-lists to incoming IP addresses as obtained
            from X-Forwarded-For header. 
            Load-Balancer must be enabled to forward client's real IP address
            in X-Forwarded-For header to discovery servers.
            Steps:
            1. Configure subscriber and publisher white list and save it in
                contrail-discovery.conf file.
            2. Send publish/subscribe requests with X-Forwarded-for headers with
                IPs same as present in white list 
            3. Verify that publish/subscribe requests are processed correctly
                by discovery server
            4. Send publish/subscribe requests with X-Forwarded-for headers
                with IPs not present in white list 
            5. Verify that publish/subscribe requests are rejected by discovery server.
            6. Delete the white list configurations from contrail-discovery.conf file.
            7. Send publish/subscribe requests with X-Forwarded-for headers 
                with IPs not present in white list 
            8. Verify that publish/subscribe requests are processed correctly 
                by discovery server
        '''
        result = True
        ds_ip = self.inputs.cfgm_ip
        try:
            self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
            assert self.ds_obj.modify_discovery_conf_file_params('change_min_max_ttl',\
                                                    ttl_min=30, ttl_max=30)
            self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
            self.logger.info("\n # Configure white list for publishers\n \
             and subscriber in contrail-discovery.conf file # ")
            self.ds_obj.white_list_conf_file("publisher", '1.1.1.0/24', '2.2.2.0/24')
            self.ds_obj.white_list_conf_file("subscriber", '1.1.1.0/24', '2.2.2.0/24')
            DiscoveryServerUtils.POST_HEADERS={'Content-type': 'application/json'\
                                                  , 'X-Forwarded-For': "1.1.1.1"}
            self.logger.info("Sending a synthetic publish request to verify publishers white list")
            response = self.ds_obj.publish_service_to_discovery(ds_ip,\
                                service="Test_Pub_1",ip="1.1.1.1", port ="123")
            if self.ds_obj.get_all_services_by_service_name(ds_ip, service="Test_Pub_1")==[]:
                result = False
                self.logger.error("\n#### Failure!! The requested publish request\n\
                not accepted by discovery server even if the IP was present in\n \
                 Publisher white list  ###")
            else:
                self.logger.info("\n#### Success!! The requested publish request\n\
                accepted by discovery server as IP was present in Publisher white list")
            sleep(2)
            DiscoveryServerUtils.POST_HEADERS = {'Content-type': 'application/json',\
                                                  'X-Forwarded-For': "3.3.3.3"}
            response = self.ds_obj.publish_service_to_discovery(ds_ip,\
                                service="Test_Pub_2",ip="3.3.3.3", port ="123")
            if self.ds_obj.get_all_services_by_service_name(ds_ip,\
                                             service="Test_Pub_2") == []:
                self.logger.info("\n#### Success!! The requested publish request\n\
                not accepted by discovery as IP was not present in Publisher white list")
            else:
                result = False
                self.logger.error("\n#### Failure!! The requested publish request\n\
                accepted by discovery server even if the IP was not present in Publisher white list")
            self.logger.info("Sending a synthetic subscribe request to verify subscribers white list")
            DiscoveryServerUtils.POST_HEADERS = {'Content-type': 'application/json',\
                                                  'X-Forwarded-For': "2.2.2.2"}
            self.ds_obj.subscribe_service_from_discovery(ds_ip, service="IfmapServer",\
                    instances="2", client_id=self.inputs.compute_names[0]+\
                    ":TestClient_1",remote_addr=self.inputs.compute_control_ips[0],\
                    client_type= "TestClient_1")
            if self.ds_obj.get_subscribed_service_id(ds_ip,client=(\
                            self.inputs.compute_control_ips[0], "TestClient_1"),\
                                                      service="IfmapServer") == []:
                result = False
                self.logger.error("\n#### Failure!! The requested subscribe request\n\
                not accepted by discovery server even if the IP was present\n\
                in Subscriber white list  ###")
            else:
                self.logger.info("\n#### Success!! The requested subscribe request\n\
                accepted by discovery server as IP was present in Subscriber white list") 
            DiscoveryServerUtils.POST_HEADERS={'Content-type': 'application/json',\
                                                 'X-Forwarded-For': "3.3.3.3"}
            self.ds_obj.subscribe_service_from_discovery(ds_ip, service="IfmapServer",\
                instances="2",client_id=self.inputs.compute_names[0]+
                ":TestClient_2",remote_addr= self.inputs.compute_control_ips[0],\
                client_type= "TestClient_2")
            if self.ds_obj.get_subscribed_service_id(ds_ip, client=(self.inputs.compute_control_ips[0],\
                                            "TestClient_2"), service="IfmapServer") == []:
                self.logger.info("\n#### Success!! The requested subscribe request \n\
                not accepted by discovery server as IP was not present in Subscriber white list") 
            else:
                result = False
                self.logger.error("\n#### Failure!! The requested subscribe request\n\
                accepted by discovery server even if the IP was not present in Subscriber white list")
            self.logger.info("Deleting the configurations of white list to clean up for next test case")
            assert self.ds_obj.modify_discovery_conf_file_params( 'delete_white_list',\
                                                   publish=True, subscribe=True)
            self.logger.info("\n# Verify that when white list is deleted, \n\
            then X-Forwarded-Header does not hold relevance and all requests are accepted")
            response = self.ds_obj.publish_service_to_discovery(ds_ip,\
                                    service="Test_Pub_2",ip="3.3.3.3", port ="123")
            if self.ds_obj.get_all_services_by_service_name(ds_ip, service="Test_Pub_2") == []:
                result = False
                self.logger.error("\nFailure!! The requested publish request \n\
                not accepted by discovery server even after deleting publish white list")   
            else:
                self.logger.info("\n#### Success!! The requested publish request\n\
                accepted by discovery server as Publisher white list has been deleted")
            self.ds_obj.subscribe_service_from_discovery(ds_ip, service="IfmapServer",\
                instances="2",client_id=self.inputs.compute_names[0]+\
                ":TestClient_2",remote_addr= self.inputs.compute_control_ips[0],\
                client_type= "TestClient_2")
            if self.ds_obj.get_subscribed_service_id(ds_ip,client=(self.inputs.compute_control_ips[0],\
                                            "TestClient_2"), service="IfmapServer") == []: 
                result = False
                self.logger.error("\nFailure!! The requested subscribe request\n\
                not accepted by discovery server even if Subscriber white list has been deleted")
            else:
                self.logger.info("\nSuccess!! The requested subscribe request\n\
                accepted by discovery server as Subscriber white list has been deleted")
            self.logger.info("\nWaiting for 30 seconds so that dummy client request\n\
            ages out and do not interfere with other test cases ######")
            sleep(30)
        except Exception as e:
            self.logger.error(e)
            result = False
        DiscoveryServerUtils.POST_HEADERS={'Content-type': 'application/json'}    
        assert result, "Test case failed due to some error. Please refer to logs"
        
    @preposttest_wrapper    
    def test_keystone_auth_security(self):
        '''
            Discovery server to require admin keystone credentials to perform
            load-balance and setting of admin state. Discovery server will expect
            admin token in X-Auth-Token header of incoming request. The token
            is sent to keystone for validation and action is only performed if a 
            valid admin token is present. Otherwise 401 HTTP code is returned
            Steps:
            1. Configure authentication as keystone in contrail-dicovery.conf file.
                Don't configure the credentials
            2. Attempt admin-state change, oper-state change and load-balance 
                trigger and expect them to fail as only auth has been configured.
            3. Configure authentication as keystone in contrail-dicovery.conf file.
                Configure the credentials as well.
            4. Attempt admin-state change, oper-state change and load-balance 
                trigger and expect them to pass as auth and it's credentials has
                been configured.
        '''
        result = True
        ds_ip = self.inputs.cfgm_ip
        try:
            self.logger.info("# Configure authentication as *True* in contrail-discovery.conf file # ")
            assert self.ds_obj.modify_discovery_conf_file_params('add_keystone_auth',\
                                        auth="keystone", add_values = "False")
            self.logger.debug("#Verify that all requests fails if Auth is True and credentials are not mentioned#")
            response = self.ds_obj.publish_requests_with_keystone(ds_ip,\
                            operation="oper-state",operation_status="up",\
                            service_id=self.inputs.cfgm_names[0],\
                            service_type="IfmapServer")
            if response != 200:
                self.logger.info("\nSuccess!! As authetication is True and credentials are not configured,\n\
                the oper-state change request has failed")
            else:
                self.logger.error("\nFailure!! Even if authetication is True and credentials are not configured,\n\
                 the oper-state change request is successful")
                result = False
            response = self.ds_obj.publish_requests_with_keystone(ds_ip,\
                            operation="admin-state",operation_status="up",\
                            service_id=self.inputs.cfgm_names[0],\
                            service_type="IfmapServer")
            if response != 200:
                self.logger.info("\nSuccess!! As authetication is True and credentials are not configured,\n\
                 the admin-state change request has failed")
            else:
                self.logger.error("\nFailure!! Even if authetication is True and credentials are not configured,\n\
                 the admin-state change request is successful")
                result = False
            response = self.ds_obj.publish_requests_with_keystone(ds_ip,\
                            operation="load-balance",service_id=\
                            self.inputs.cfgm_names[0],service_type="IfmapServer")
            if response != 200:
                self.logger.info("\n Success!! As authetication is True and credentials are not configured,\n\
                 the load-balance request has failed")
            else:
                self.logger.error("\n Failure!! Even if authetication is True and credentials are not configured,\n\
                 the load-balance request is successful")
                result = False
            self.logger.info("\n # Configure authentication as *True* as well as \n \
            configuring all the required credentials in contrail-discovery.conf file # ")
            assert self.ds_obj.modify_discovery_conf_file_params(operation='add_keystone_auth',\
                                        auth="keystone", add_values = "True")
            self.logger.info("\n # Verify that all requests are passed if Auth is True\n\
             and credentials are mentioned # ")
            response = self.ds_obj.publish_requests_with_keystone(ds_ip,\
                            operation="oper-state",operation_status="up",\
                            service_id=self.inputs.cfgm_names[0],\
                            service_type="IfmapServer")
            if response == 200:
                self.logger.info("\n Success!! As authetication is True and credentials are configured,\n\
                 the oper-state change request has been processed successfully")
            else:
                self.logger.error("\n Failure!! Even if authetication is True and credentials are configured,\n\
                 the oper-state change request has failed")
                result = False
            response = self.ds_obj.publish_requests_with_keystone(ds_ip\
                            ,operation="admin-state",operation_status="up",\
                            service_id=self.inputs.cfgm_names[0],\
                            service_type="IfmapServer")
            if response == 200:
                self.logger.info("\n Success!! As authetication is True and credentials are configured,\n\
                 the admin-state change request has been processed successfully")
            else:
                self.logger.error("\n Failure!! Even if authetication is True and credentials are  configured,\n\
                 the admin-state change request has failed")
                result = False
            response = self.ds_obj.publish_requests_with_keystone(ds_ip,\
                            operation="load-balance",service_id=\
                            self.inputs.cfgm_names[0],service_type="IfmapServer")
            if response == 200:
                self.logger.info("\n Success!! As authetication is True and credentials are configured,\n\
                 the load-balance request has been processed successfully")
            else:
                self.logger.error("\n Failure!! Even if authetication is True and credentials are configured,\n\
                 the load-balance request has failed")
                result = False
        except Exception as e:
            self.logger.error(e)
            result = False
        self.logger.debug("# Deleting the auth configurations from contrail-discovery.conf file # ")
        assert self.ds_obj.modify_discovery_conf_file_params(operation='delete_keystone_auth'\
                                               ,auth="keystone")       
        assert result, "Test case failed due to some error. Please refer to logs"
    
    @preposttest_wrapper
    def test_policy_fixed(self):
        '''
            This test case is specifically written to automate Bug "#1401304 : 
            discovery fixed policy breaks if service stays down for extended period"
            Discovery has fixed policy for service assignment in which services
            are assigned to consumers in a fixed, static or constant manner. 
            For example if there are "n" publishers of a service and there are
            "m" consumers that are interested in "k" instances (say 2) of service, 
            then all "m" consumers will get <n0, n1, n2 ... nk> service instances.
            This is akin to priority order. 
            If an instance, say "ni" such that 0 <= i <= k went down for an 
            extended period (> 15 seconds) and comes back up, it should no longer
            be assigned to a new consumer because it should go to the bottom of
            the prioritized list. 
            It should not retain its position.
            Steps:
            1. Set the policy of publisher named TEST_PUB as fixed in 
                contrail-discovery.conf file.
            2. Create 3 different synthetic Publisher request of Publisher named
                TEST_PUB.
            3. Create 3 different synthetic Subscribe request asking for 2 instances
                of TEST_PUB each. Verify that policy as fixed works as expected.
            4. Now make one of the publisher which was used by subscribers as 
                down for more than extended period.
            5. Again send 3 different synthetic requests asking for 2 instances
                each and verify that the publisher which was made down is not 
                assigned to the clients as it's priority got reduced in the earlier step.
        '''
        result = True
        ds_ip = self.inputs.cfgm_ip
        try:
            self.logger.debug("#### Changing min and max TTL values for testing purpose ##")
            assert self.ds_obj.modify_discovery_conf_file_params(operation='change_min_max_ttl',\
                                                    ttl_min=30, ttl_max=30)
            self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
            self.logger.info("#### Making policy as *fixed* for test publisher  ##")
            assert self.ds_obj.modify_discovery_conf_file_params( 'set_policy',\
                    publisher_type="TEST_PUB",policy='fixed')
            self.logger.info("#### Sending 3 synthetic publish requests of same Publisher type  ###")
            def publish_request():
                for i in range(0,100):
                    response_1 = self.ds_obj.publish_service_to_discovery(ds_ip,\
                                service="TEST_PUB",ip="1.1.1.1",port="123")
                    response_2 = self.ds_obj.publish_service_to_discovery(ds_ip,\
                                service="TEST_PUB",ip="2.2.2.2",port="123")
                    response_3 = self.ds_obj.publish_service_to_discovery(ds_ip,\
                                service="TEST_PUB",ip="3.3.3.3",port="123")
                    sleep(5)
            obj_1 = Process(target=publish_request)
            obj_1.start()
            sleep(1)
            if self.ds_obj.get_service_status(ds_ip,\
                        service_tuple=("1.1.1.1","TEST_PUB")) == "up" \
            and self.ds_obj.get_service_status(ds_ip,\
                        service_tuple=("2.2.2.2","TEST_PUB")) == "up" \
            and self.ds_obj.get_service_status(ds_ip,\
                        service_tuple=("3.3.3.3","TEST_PUB")) == "up":
                self.logger.info("#### All publishers have registered to discovery server successfully.###")
            else:
                self.logger.error("\n#### Either or all Publishers have not registered to discovery server.\n \
                No sense of proceeding the test case. Exiting. ###")
                self.ds_obj.modify_discovery_conf_file_params( 'del_policy',\
                                            publisher_type="TEST_PUB")
                obj_1.terminate()
                result = False
                assert result
            self.logger.info("\n#### Sending 3 synthetic subscribe requests with instance value 2\n \
            to subscribe to Publisher *TEST_PUB*  ###")
            self.ds_obj.subscribe_service_from_discovery(ds_ip,service="TEST_PUB",\
                instances="2",client_id="1.1.1.1:TestClient",\
                remote_addr= "1.1.1.1", client_type= "TestClient")
            self.ds_obj.subscribe_service_from_discovery(ds_ip,service="TEST_PUB",\
                instances="2",client_id="2.2.2.2:TestClient",\
                remote_addr= "2.2.2.2", client_type= "TestClient")
            self.ds_obj.subscribe_service_from_discovery(ds_ip, service="TEST_PUB",\
                instances="2",client_id="3.3.3.3:TestClient",\
                remote_addr= "3.3.3.3", client_type= "TestClient")
            self.logger.debug("#### Verifying the in use count of publishers are subscribe request ###")
            p1_in_use_count = self.ds_obj.get_service_in_use(ds_ip,("1.1.1.1","TEST_PUB"))
            p2_in_use_count = self.ds_obj.get_service_in_use(ds_ip,("2.2.2.2","TEST_PUB"))
            p3_in_use_count = self.ds_obj.get_service_in_use(ds_ip,("3.3.3.3","TEST_PUB"))
            publisher_in_use_list=[p1_in_use_count,p2_in_use_count,p3_in_use_count]
            if sum(publisher_in_use_list) == 6 and 0 in publisher_in_use_list:
                self.logger.info("\n#### Clients subscribed successfully to publishers\n \
                 and policy as *fixed* working as expected ##")
            else:
                self.logger.error("#### Subscription not as expected. The in use list looks like %s  ##"\
                                   % publisher_in_use_list)
                result = False
            self.logger.debug("\n#### Stopping one of the in use Publisher for extended period\n \
             (> 15 seconds) to decrease it's priority ##")
            obj_1.terminate()
            index_first_pub_used = publisher_in_use_list.index(3)
            def new_publish_request():
                for i in range(0,100):
                    if index_first_pub_used == 0:
                        response_2 = self.ds_obj.publish_service_to_discovery(ds_ip,\
                                    service="TEST_PUB",ip="2.2.2.2", port ="123")
                        response_3 = self.ds_obj.publish_service_to_discovery(ds_ip,\
                                    service="TEST_PUB",ip="3.3.3.3", port ="123")
                    elif index_first_pub_used == 1:
                        response_1 = self.ds_obj.publish_service_to_discovery(ds_ip,\
                                    service="TEST_PUB",ip="1.1.1.1", port ="123")
                        response_3 = self.ds_obj.publish_service_to_discovery(ds_ip,\
                                    service="TEST_PUB",ip="3.3.3.3", port ="123")
                    sleep(5)
            new_obj=Process(target =new_publish_request)
            new_obj.start()
            self.logger.debug("#### Waiting for 60 seconds so that all subscriptions are lost ##")
            sleep(60)
            self.logger.debug("\n#### Again starting the stopped publishers\n \
            and hoping that its priority has been reduced and it will not be used by the clients any more##")
            new_obj.terminate()
            obj_2 = Process(target=publish_request)
            obj_2.start()
            sleep(1)
            self.logger.info("\n#### Again sending 3 synthetic subscribe requests\n \
             with instance value 2 to subscribe to Publisher *TEST_PUB*  ###")
            self.ds_obj.subscribe_service_from_discovery(ds_ip, service="TEST_PUB",\
                instances="2",client_id="1.1.1.1:TestClient",\
                remote_addr= "1.1.1.1",client_type= "TestClient")
            self.ds_obj.subscribe_service_from_discovery(ds_ip, service="TEST_PUB",\
                instances="2",client_id="2.2.2.2:TestClient",\
                remote_addr= "2.2.2.2",client_type= "TestClient")
            self.ds_obj.subscribe_service_from_discovery(ds_ip, service="TEST_PUB",\
                instances="2",client_id="3.3.3.3:TestClient",\
                remote_addr= "3.3.3.3",client_type= "TestClient")
            self.logger.debug("#### Verifying the in use count of publishers are subscribe request ###")
            p1_in_use_count = self.ds_obj.get_service_in_use(ds_ip,("1.1.1.1","TEST_PUB"))
            p2_in_use_count = self.ds_obj.get_service_in_use(ds_ip,("2.2.2.2","TEST_PUB"))
            p3_in_use_count = self.ds_obj.get_service_in_use(ds_ip,("3.3.3.3","TEST_PUB"))
            publisher_in_use_list=[p1_in_use_count,p2_in_use_count,p3_in_use_count]
            if sum(publisher_in_use_list) == 6 and publisher_in_use_list.index(index_first_pub_used) == 0:
                self.logger.info("\n#### Clients subscribed successfully to publishers\n \
                 and policy as *fixed* working as expected ##")
                self.logger.info("\n#### Clients not subscribed to publisher \n \
                which went down for time more than extended period as it's priority has been decreased ##")
            else:
                self.logger.error("#### Subscription not as expected. The in use list looks like %s  ##"\
                                   % publisher_in_use_list)
                self.logger.error("\n#### Clients might have subscribed to publisher which went down.\n \
                This means priority of that publisher was not decreased ##")
                result = False
            obj_2.terminate()
            self.logger.info("#### Deleting the policy configurations from .conf file ##")
            assert self.ds_obj.modify_discovery_conf_file_params( 'del_policy',\
                                            publisher_type="TEST_PUB")
            self.logger.debug("#### Waiting for dummy Publish and subscribe requests to expire  ##")
            sleep(30)
            self.ds_obj.cleanup_service_from_discovery(ds_ip)
        except Exception as e:
            self.logger.error(e)
            result = False
        assert result, "Test case failed due to some error. Please refer to logs"
    
    @preposttest_wrapper
    def test_rule_do_not_affect_other_dns_subscriptions(self):
        '''
            This test case is specifically written to automate Bug 
            "#1548638 : [Discovery-Rel3.0-Centos-1]: All clients re-subscribe 
            to a different publisher when a rule is added which was supposed 
            to affect only 1 subscriber (No Auto load balance) "
            Steps:
            1. Search for the DNS-Server to which vrouter agents are subscribed to.
            2. Create a rule entry for nay one of the vrouter agent and Publisher.
            3. Again search for DNS-Server to which vrouter agent is subscribed to 
               and match it to values before creating rule.
            Precondition: Assumption is that setup is having a vrouter connected
                to 2 instances of DNS servers running in different subnets
                Also, setup requirement of this test case is to have at least
                2 publishers and 2 subscribers.
                Both set of publisher and subscriber should be in different network.
        '''
        self.ds_obj.skip_discovery_test("dns-server", min_instances=3, different_subnet_flag=False )
        result = True
        ds_ip = self.inputs.cfgm_ip
        assert self.ds_obj.resubscribe_with_new_ttl( 30, 30, 'contrail-vrouter-agent')
        self.addCleanup(self.ds_obj.modify_discovery_conf_file_params,"change_min_max_ttl")
        self.logger.info("# Finding the subscriptions of all vrouter-agents to DNS-server before creating a rule# ")
        all_vrouter_pub_IPs_bfr_rule = []
        for i in range(0,len(self.inputs.compute_control_ips)):  
            client_subscribed_service_id = self.ds_obj.get_subscribed_service_id\
                        (ds_ip, client=(self.inputs.compute_control_ips[i],\
                        "contrail-vrouter-agent:0"),service="dns-server")
            instances_allocated = len(client_subscribed_service_id)
            service_IPs = []
            for k in range (0,instances_allocated):
                service_endpoint = self.ds_obj.get_service_endpoint_by_service_id\
                (ds_ip,client_subscribed_service_id[k])
                service_IPs.append(service_endpoint[0][0])
            self.logger.debug("Contrail-vrouter-agent running on %s is subscribed to DNS-server running at %s" \
                              % (self.inputs.compute_control_ips[i],service_IPs))
            all_vrouter_pub_IPs_bfr_rule.append(service_IPs)
        self.logger.info("## Creating a rule for 1 of the vrouter-agent subscriber")
        self.ds_obj.add_and_verify_rule(self.inputs.bgp_control_ips[0], 'dns-server',\
            self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
        self.logger.info("#### Waiting for 30 seconds so that TTL expiry for all subscriptions to happens###")
        sleep (30)
        self.logger.info("# Finding the subscriptions of all vrouter-agents to DNS-server after creating a rule# ")
        all_vrouter_pub_IPs_aftr_rule = []
        for i in range(0,len(self.inputs.compute_control_ips)):  
            client_subscribed_service_id=self.ds_obj.get_subscribed_service_id(ds_ip,\
                                client=(self.inputs.compute_control_ips[i],\
                                "contrail-vrouter-agent:0"),service="dns-server")
            instances_allocated = len(client_subscribed_service_id)
            service_IPs = []
            for k in range (0,instances_allocated):
                service_endpoint = self.ds_obj.get_service_endpoint_by_service_id\
                (ds_ip,client_subscribed_service_id[k])
                service_IPs.append(service_endpoint[0][0])
            self.logger.debug("Contrail-vrouter-agent running on %s is subscribed to DNS-server running at %s" \
                              % (self.inputs.compute_control_ips[i],service_IPs))
            all_vrouter_pub_IPs_aftr_rule.append(service_IPs)
        if all_vrouter_pub_IPs_aftr_rule[0][0] == self.inputs.bgp_control_ips[0] \
            and len(all_vrouter_pub_IPs_aftr_rule[0]) == 1:
            self.logger.debug("The rule has worked properly")
            for i in range(1,len(all_vrouter_pub_IPs_aftr_rule)):
                if  all_vrouter_pub_IPs_aftr_rule[i] ==  all_vrouter_pub_IPs_bfr_rule[i]:
                    self.logger.debug("No change has happened in other subscriptions due to rule.")
                else:
                    result = False
                    self.logger.error("\n The publisher assigned to contrail-vrouter\n \
                     running on %s were %s and has changed to %s"\
                        % (self.inputs.compute_control_ips[i],\
                        all_vrouter_pub_IPs_bfr_rule[i],all_vrouter_pub_IPs_aftr_rule[i])) 
        else:
            self.logger.error("Rule has not worked as expected")
            self.logger.debug("Subscriber %s has subscribed to %s Publisher instead of subscribing only to %s"\
                               % (self.inputs.compute_control_ips[i],\
                        all_vrouter_pub_IPs_aftr_rule[0],self.inputs.bgp_control_ips[0]) )
            result = False
        self.logger.info("# Deleting the rule after the test is complete # ")
        self.ds_obj.delete_and_verify_rule(self.inputs.bgp_control_ips[0], 'dns-server',\
            self.inputs.compute_control_ips[0], 'contrail-vrouter-agent:0')
        assert result, "Test case failed due to some error. Please refer to logs"
# end TestDiscoveryFixture

