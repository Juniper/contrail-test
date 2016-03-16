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
            for i in range(1,5):
                resp = None
                resp = self.ds_obj.subscribe_service_from_discovery(
                    self.inputs.cfgm_ip, service=service, instances=1, client_id=str(cuuid))
                ttl = resp['ttl']
                self.logger.info("ttl : %s" % (ttl))
                self.logger.info("Waiting for %s sec..." % (expected_ttl))
                time.sleep(expected_ttl)
                expected_ttl = expected_ttl * 2
                self.logger.info("Expected ttl is %s..." % (expected_ttl))
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

        '''
        assert self.ds_obj.verify_rule_xmpp_server_vrouter_agent(
        )
        return True
    
    @preposttest_wrapper
    def test_rule_dns_server_vrouter_agent(self):
        ''' Validate that applied rules takes effect correctly for contrail-vrouter-agent and its subscription to DNS Server.

        '''
        assert self.ds_obj.verify_rule_dns_server_vrouter_agent(
        )
        return True
    
    @preposttest_wrapper
    def test_rule_ifmap_server_control_client(self):
        ''' Validate that applied rules takes effect correctly for "contrail-control" and its subscription to IfmapServer.

        '''
        assert self.ds_obj.verify_rule_ifmap_server_control_client(
        )
        return True
    
    @preposttest_wrapper
    def test_rule_op_server_webui_client(self):
        ''' Validate that applied rules takes effect correctly for "contrailWebUI" and its subscription to Op Server.

        '''
        assert self.ds_obj.verify_rule_op_server_webui_client(
        )
    
    @preposttest_wrapper
    def test_rule_api_server_webui_client(self):
        ''' Validate that applied rules takes effect correctly for "contrailWebUI" and its subscription to API Server.

        '''
        assert self.ds_obj.verify_rule_api_server_webui_client(
        )
    
    @preposttest_wrapper    
    def test_rule_collector_vrouter_agent_client(self):
        ''' Validate that applied rules takes effect correctly for "contrail-vrouter-agent" and its subscription to Collector.

        '''
        assert self.ds_obj.verify_rule_collector_vrouter_agent_client(
        )
    
    @preposttest_wrapper    
    def test_rule_collector_multiple_clients(self):
        ''' Validate that applied rules takes effect correctly for multiple clients mentioned sequentially in a single rule.

        '''
        assert self.ds_obj.verify_rule_collector_multiple_clients(
        )
    
    @preposttest_wrapper
    def test_subscribe_request_with_diff_instances_rules(self):
        ''' Validate that different instances of Publishers are assigned to client based on the instance value requested by clients.
            Also validate that if rules are present, requested instances are restricted based on rules.

        '''
        assert self.ds_obj.verify_subscribe_request_with_diff_instances_rules(
        )
    
    @preposttest_wrapper    
    def test_rule_when_service_oper_down(self):
        ''' Validate that when publisher mentioned in rule is operationally down, the subscriber mentioned in rule, do not subscribe to any other publisher.
            Also verify that when publisher comes up, the applicable instance of that client get a subscription from that Publisher.
            For testing purpose, i have use DNS-SERVER as publisher and contrail-vrouter-agent as client.

        '''
        assert self.ds_obj.verify_rule_when_service_oper_down(
        )
    
    @preposttest_wrapper
    def test_multiple_rule_same_subscriber(self):
        ''' Validate that rule restrict the subscriber irrespective of number of intances requested by the client.
            Also verify that, if multiple rules are present for same client, more instances of service gets allocated to that client.
            For testing purpose, i have use XMPP-SERVER as publisher and contrail-vrouter-agent as client.

        '''
        assert self.ds_obj.verify_multiple_rule_same_subscriber(
        )
    
    @preposttest_wrapper    
    def test_discovery_server_restart_rule_present(self):
        ''' Validate that rules are followed even after discovery server restarts.

        '''
        assert self.ds_obj.verify_discovery_server_restart_rule_present(
        )
    
    @preposttest_wrapper
    def test_publisher_restart_rule_present(self):
        ''' Validate that rules are followed even after Publisher servers restarts.

        '''
        assert self.ds_obj.verify_publisher_restart_rule_present(
        )
        
    @preposttest_wrapper
    def test_auto_load_balance_Ifmap(self):
        ''' Validate that auto load balance works correctly for IfmapServer.

        '''
        assert self.ds_obj.verify_auto_load_balance_Ifmap(
        )
    
    @preposttest_wrapper    
    def test_auto_load_balance_xmpp(self):
        ''' Validate that auto load balance works correctly for XmppServer.

        '''
        assert self.ds_obj.verify_auto_load_balance_xmpp(
        )
    
    @preposttest_wrapper    
    def test_auto_load_balance_collector(self):
        ''' Validate that auto load balance works correctly for Collector.

        '''
        assert self.ds_obj.verify_auto_load_balance_collector(
        )
    
    @preposttest_wrapper    
    def test_rules_preferred_over_auto_load_balance(self):
        ''' Validate that rules always takes precedence over auto load balance.
            Also verify that when rules are delted, auto load balance takes its effect.

        '''
        assert self.ds_obj.verify_rules_preferred_over_auto_load_balance(
        )
# end TestDiscoveryFixture

