import unittest
import fixtures
import testtools
import traceback
from tcutils.wrappers import preposttest_wrapper
import uuid
import base
import test
import time
import threading

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
            self.ds_obj.change_ttl_short_and_hc_max_miss()
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
            self.ds_obj.change_ttl_short_and_hc_max_miss(ttl_short=1, hc_max_miss=3)
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
    def test_rule_xmpp_server_vrouter_agent(self):
        ''' Validate that applied rules takes effect correctly for contrail-vrouter-agent and its subscription to XMPP Server.
            Steps:
            1. Create rules for all contrail-vrouter-agent of 1 network to subscribe to XMPP Servers of same network.
            2. Verify if rule is working as expected or not
        '''
        assert self.ds_obj.verify_rule_xmpp_server_vrouter_agent(
        )
    
    @preposttest_wrapper
    def test_rule_dns_server_vrouter_agent(self):
        ''' Validate that applied rules takes effect correctly for contrail-vrouter-agent and its subscription to DNS Server.
            Steps:
            1. Create rules for all contrail-vrouter-agent of 1 network to subscribe to DNS Servers of same network.
            2. Verify if rule is working as expected or not
        '''
        assert self.ds_obj.verify_rule_dns_server_vrouter_agent(
        )
    
    @preposttest_wrapper
    def test_rule_ifmap_server_control_client(self):
        ''' Validate that applied rules takes effect correctly for "contrail-control" and its subscription to IfmapServer.
            Steps:
            1. Create rules for all contrail-control of 1 network to subscribe to Ifmap Servers of same network.
            2. Verify if rule is working as expected or not
        '''
        assert self.ds_obj.verify_rule_ifmap_server_control_client(
        )
    
    @preposttest_wrapper
    def test_rule_op_server_webui_client(self):
        ''' Validate that applied rules takes effect correctly for "contrailWebUI" and its subscription to Op Server.
            Steps:
            1. Create rules for all contrailWebUI of 1 network to subscribe to Op Servers of same network.
            2. Verify if rule is working as expected or not
        '''
        assert self.ds_obj.verify_rule_op_server_webui_client(
        )
    
    @preposttest_wrapper
    def test_rule_api_server_webui_client(self):
        ''' Validate that applied rules takes effect correctly for "contrailWebUI" and its subscription to API Server.
            Steps:
            1. Create rules for all contrailWebUI of 1 network to subscribe to Op Servers of same network.
            2. Verify if rule is working as expected or not

        '''
        assert self.ds_obj.verify_rule_api_server_webui_client(
        )
    
    @preposttest_wrapper    
    def test_rule_collector_vrouter_agent_client(self):
        ''' Validate that applied rules takes effect correctly for "contrail-vrouter-agent" and its subscription to Collector.
            Steps:
            1. Create rules for all contrail-vrouter-agent of 1 network to subscribe to Collector of same network.
            2. Verify if rule is working as expected or not
        '''
        assert self.ds_obj.verify_rule_collector_vrouter_agent_client(
        )
    
    @preposttest_wrapper    
    def test_rule_collector_multiple_clients(self):
        ''' Validate that applied rules takes effect correctly for multiple clients mentioned sequentially in a single rule.
            Steps:
            1. Create s single rule for multiple types of clients to subscribe to single Publisher. Mention all subscriber in that rule.
            2. Verify if rule is working as expected or not. Verify that all clients subscribe to single publisher only.
        '''
        assert self.ds_obj.verify_rule_collector_multiple_clients(
        )
    
    @preposttest_wrapper
    def test_subscribe_request_with_diff_instances_rules(self):
        ''' Validate that different instances of Publishers are assigned to client based on the instance value requested by clients.
            Also validate that if rules are present, requested instances are restricted based on rules.
            Steps:
            1. Use a non contrail synthetic subscribe request to test this.
            2. Use some instance value in subscribe request and verify that requested instances of publisher are assigned.
            3. Create a rule with same requested Publisher and subscribe request. 
            4. Verify that even if instances asked are more but as rule is present, the request will be restricted to get only 1 instance of that publisher.
            5. Delete the rule.
            6. Again test that same subscribe request will again get all instances requested.
        '''
        assert self.ds_obj.verify_subscribe_request_with_diff_instances_rules(
        )
    
    @preposttest_wrapper    
    def test_rule_when_service_oper_down(self):
        ''' Validate that when publisher mentioned in rule is operationally down, the subscriber mentioned in rule, do not subscribe to any other publisher.
            Also verify that when publisher comes up, the applicable instance of that client get a subscription from that Publisher.
            For testing purpose, i have use DNS-SERVER as publisher and contrail-vrouter-agent as client.
            Steps:
            1. Create a rule using any Publisher and subscriber pair.
            2. Make the Publisher mentioned in the rule as operational down.
            3. Verify that as service is down, the subscriber will not get any other instance of that service because rule still holds true.
            4. Make the Publisher as  operational UP.
            5. Verify that as soon as Publisher is made operational UP, the subscriber will get that instance of service.
        '''
        assert self.ds_obj.verify_rule_when_service_oper_down(
        )
    
    @preposttest_wrapper
    def test_multiple_rule_same_subscriber(self):
        ''' Validate that rule restrict the subscriber irrespective of number of instances requested by the client.
            Also verify that, if multiple rules are present for same client, more instances of service gets allocated to that client.
            For testing purpose, i have use XMPP-SERVER as publisher and contrail-vrouter-agent as client.
            Steps:
            1. Create different rules with same subscriber values and different Publishers.
            2. Verify if rule is working as expected or not
            
        '''
        assert self.ds_obj.verify_multiple_rule_same_subscriber(
        )
    
    @preposttest_wrapper
    def test_rule_on_xmpp_do_not_impact_dns(self):
        ''' This test case is specifically written to test Bug ID "#1548771" [Discovery-Rel3.0-Centos-1]: Applying rule on DNS-server affects the rule entry already applied to XMPP server and vice versa. (Tested for client type : vrouter-agent) 
            Steps:
            1. Create 2 different rules with same subscriber as "contrail-vrouter-agent" and using xmpp-server in rule 1 and dns-server in rule 2.
            2. Verify that both the rules work independently without impacting each other.
        '''
        assert self.ds_obj.verify_rule_on_xmpp_do_not_impact_dns(
        )
    
    def test_rule_with_vrouter_agent_do_not_impact_other_subscriptions(self):
        ''' This test case is specifically written to test Bug ID "#1541321" [Discovery_R3.0_ubuntu_2704] : Rule mentioning contrail-vrouter-agent affects all the subscriptions of that client with all Publishers irrespective of the publisher mentioned in the rule. This happens for 1/2 cycle of TTL and things recover after that.  
            Steps:
            1. Create a rule and mention subscriber as "contrail-vrouter-agent" and using dns-server as publisher.
            2. Verify that the configured rule do not impact subscription of "contrail-vrouter-agent" to xmpp-server even for one TTL cycle .
        '''
        assert self.ds_obj.verify_rule_with_vrouter_agent_do_not_impact_other_subscriptions(
        )
        
    @preposttest_wrapper    
    def test_discovery_server_restart_rule_present(self):
        ''' Validate that rules are followed even after discovery server restarts.
            Steps:
            1. Create rule for any Publisher and subscriber pair and verify that rule is behaving properly.
            2. Restart the discovery server on all config nodes.
            3. Verify that after discovery server comes up again, rules are still followed.
        '''
        assert self.ds_obj.verify_discovery_server_restart_rule_present(
        )
    
    @preposttest_wrapper
    def test_publisher_restart_rule_present(self):
        ''' Validate that rules are followed even after Publisher servers restarts.
            Steps:
            1. Create multiple rules for  Publisher and subscriber pairs and verify that all rules are behaving properly.
            2. Restart the Publishers mentioned in the rules on all the corresponding nodes.
            3. Verify that after Publisher service restart, rules are still followed.
        '''
        assert self.ds_obj.verify_publisher_restart_rule_present(
        )
        
    @preposttest_wrapper
    def test_auto_load_balance_Ifmap(self):
        ''' Validate that auto load balance works correctly for IfmapServer.
            Steps:
            1. Verify that normal load balancing is working correctly by default on IfmapServer.    
            2. Set auto load balance as *True* and stop any one of the IfmapServers.
            3. Verify that stopped Server loses all it's subscribers.
            4. Again start the IfmapServer which was stopped earlier.
            5. Verify auto load balancing takes place.

        '''
        assert self.ds_obj.verify_auto_load_balance_Ifmap(
        )
    
    @preposttest_wrapper    
    def test_auto_load_balance_xmpp(self):
        ''' Validate that auto load balance works correctly for XmppServer.
            Steps:
            1. Verify that normal load balancing is working correctly by default on Xmpp-Server.    
            2. Set auto load balance as *True* and stop any one of the Xmpp-Server.
            3. Verify that stopped Server loses all it's subscribers.
            4. Again start the Xmpp-Server which was stopped earlier.
            5. Verify auto load balancing takes place.
        '''
        assert self.ds_obj.verify_auto_load_balance_xmpp(
        )
    
    @preposttest_wrapper    
    def test_auto_load_balance_collector(self):
        ''' Validate that auto load balance works correctly for Collector.
            Steps:   
            1. Set auto load balance as *True* and stop any one of the Collector.
            2. Verify that stopped Server loses all it's subscribers.
            3. Again start the Collector which was stopped earlier.
            4. Verify auto load balancing takes place.
        '''
        assert self.ds_obj.verify_auto_load_balance_collector(
        )
    
    @preposttest_wrapper    
    def test_rules_preferred_over_auto_load_balance(self):
        ''' Validate that rules always takes precedence over auto load balance.
            Also verify that when rules are deleted, auto load balance takes its effect.
            Steps:   
            1. Verify that normal load balancing is working correctly by default on XMpp-Server.
            2. Set auto load balance as *True* and stop any one of the Xmpp-Server.
            3. Create multiple rules with single xmpp-server to subscribe to all vrouter-agents in the topology.
            4. Verify that rule is preferred over load balancing and no other xmpp-server in the topology gets any subscription.
            5. Delete the rules and verify that auto load balancing takes place.
        '''
        assert self.ds_obj.verify_rules_preferred_over_auto_load_balance(
        )
    
    @preposttest_wrapper        
    def test_service_in_use_list(self):
        ''' Validate that subscribe request with instance value as 0 and having service-in-use-list is considered 
            a subscription request and publishers are assigned to it properly.
            Steps:
            1. Get in-use count of publishers before sending a subscribe request having service-in-use list
            2. Send a subscribe request with instance value as '0' and service-in-use list present in that subscribe request.
            3. See if the in-use count of the publisher increases and client get subscribed successfully.
        '''
        assert self.ds_obj.verify_service_in_use_list(
        )
    @preposttest_wrapper
    def test_white_list_security(self):
        ''' To prevent unauthorized publish or subscribe requests to effect discovery server state (and assuming such requests are
            coming through load-balancer such ha-proxy), discovery server to apply configured publish and subscribe white-lists to 
            incoming IP addresses as obtained from X-Forwarded-For header. Load-Balancer must be enabled to forward client's real IP address
            in X-Forwarded-For header to discovery servers.
            Steps:
            1. Configure subscriber and publisher white list and save it in contrail-discovery.conf file.
            2. Send publish/subscribe requests with X-Forwarded-for headers with IPs same as present in white list 
            3. Verify that publish/subscribe requests are processed correctly by discovery server
            4. Send publish/subscribe requests with X-Forwarded-for headers with IPs not present in white list 
            5. Verify that publish/subscribe requests are rejected by discovery server.
            6. Delete the white list configurations from contrail-discovery.conf file.
            7. Send publish/subscribe requests with X-Forwarded-for headers with IPs not present in white list 
            8. Verify that publish/subscribe requests are processed correctly by discovery server
        '''
        assert self.ds_obj.verify_white_list_security(
        )
        
    @preposttest_wrapper    
    def test_keystone_auth_security(self):
        '''
            Discovery server to require admin keystone credentials to perform load-balance and setting of admin state. Discovery server will expect
            admin token in X-Auth-Token header of incoming request. The token is sent to keystone for validation and action is only performed if a valid 
            admin token is present. Otherwise 401 HTTP code is returned
            Steps:
            1. Configure authentication as keystone in contrail-dicovery.conf file. Don't configure the credentials
            2. Attempt admin-state change, oper-state change and load-balance trigger and expect them to fail as only auth has been configured.
            3. Configure authentication as keystone in contrail-dicovery.conf file. Configure the credentials as well.
            4. Attempt admin-state change, oper-state change and load-balance trigger and expect them to pass as auth and it's credentials has been configured.
        '''
        assert self.ds_obj.verify_keystone_auth_security(
        )
    
    @preposttest_wrapper    
    def test_policy_fixed(self):
        '''
            This test case is specifically written to automate Bug "#1401304 : discovery fixed policy breaks if service stays down for extended period"
            Discovery has fixed policy for service assignment in which services are assigned to consumers in a fixed, static or constant manner. 
            For example if there are "n" publishers of a service and there are "m" consumers that are interested in "k" instances (say 2) of service, 
            then all "m" consumers will get <n0, n1, n2 ... nk> service instances. This is akin to priority order. 
            If an instance, say "ni" such that 0 <= i <= k went down for an extended period (> 15 seconds) and comes back up, it should no longer be assigned to a new consumer because it should go to the bottom of the prioritized list. 
            It should not retain its position.
            Steps:
            1. Set the policy of publisher named TEST_PUB as fixed in contrail-discovery.conf file.
            2. Create 3 different synthetic Publisher request of Publisher named TEST_PUB.
            3. Create 3 different synthetic Subscribe request asking for 2 instances of TEST_PUB each. Verify that policy as fixed works as expected.
            4. Now make one of the publisher which was used by subscribers as down for more than extended period.
            5. Again send 3 different synthetic requests asking for 2 instances each and verify that the publisher which was made down is not assigned to the clients as it's priority got reduced in the earlier step.
        '''
        assert self.ds_obj.verify_policy_fixed(
        )
# end TestDiscoveryFixture

