from common.service_connections.base import BaseServiceConnectionsTest
from tcutils.wrappers import preposttest_wrapper


class TestServiceConnections(BaseServiceConnectionsTest):

    @classmethod
    def setUpClass(cls):
        super(TestServiceConnections, cls).setUpClass()

    @preposttest_wrapper
    def test_webui_configs(self):
        '''
        This test case verifies that Web UI configuration file has been updated
        correctly with all valid server values.
        Steps:
        1. Read "config.global.js" and verify all API servers are updated.
        2. Read "config.global.js" and verify all Op servers are updated.
        3. Read "config.global.js" and verify all DNS servers are updated.
        '''
        api_servers = self.get_all_configured_servers_for_webui("api")
        op_servers = self.get_all_configured_servers_for_webui("collector")
        dns_servers = self.get_all_configured_servers_for_webui("dns")
        if set(api_servers) == set(self.inputs.api_server_ip):
            self.logger.info("Webui updated correctly with API Server list")
        else:
            assert False, "Webui updated incorrectly with API Server list"
        if set(op_servers) == set(self.inputs.collector_control_ips):
            self.logger.info("Webui updated correctly with OP Server list")
        else:
            assert False, "Webui updated incorrectly with OP Server list"
        if set(dns_servers) == set(self.inputs.bgp_control_ips):
            self.logger.info("Webui updated correctly with DNS Server list")
        else:
            assert False, "Webui updated incorrectly with DNS Server list"
    # end test_webui_configs

    @preposttest_wrapper
    def test_contrail_dns_connects_to_rabbitmq(self):
        '''
        This test case verifies that Contrail DNS connects to a valid 
        Rabbit MQ Server
        Steps:
        1. Read "contrail-dns.conf" and read all valid rabbitMQ servers.
        2. Read OpServer connections and find valid rabbitMQ server connected
           to the contrail-dns client.
        3. Check that contrail-dns connections to RabbitMQ server is a 
           subset of values configured in client .conf file
        '''
        valid_rabbitmq_servers = self.get_all_configured_servers("rabbitmq",
                                                "dns", "contrail-dns")[0]
        for node in self.inputs.bgp_control_ips:
            rabbitmq_server = self.get_all_in_use_servers("rabbitmq" ,\
                                                "dns", "contrail-dns",\
                                                 node)
            if rabbitmq_server and rabbitmq_server in valid_rabbitmq_servers:
                self.logger.info("contrail-dns running on '%s' connected to"
                                " correct RabbitMQ server" % node)
            else:
                self.logger.error("Either connection is absent or incorrect or "
                                  "status is Down")
                assert False, "Connection issue between contrail-dns and RabbitMQ"
    # test_contrail_dns_connects_to_rabbitmq

    @preposttest_wrapper
    def test_contrail_control_connects_to_rabbitmq(self):
        '''
        This test case verifies that Contrail Control connects to a valid 
        Rabbit MQ Server
        Steps:
        1. Read "contrail-control.conf" and read all valid rabbitMQ servers.
        2. Read OpServer connections and find valid rabbitMQ server connected
           to the contrail-control client.
        3. Check that contrail-control connections to RabbitMQ server is a 
           subset of values configured in client .conf file
        '''
        valid_rabbitmq_servers = self.get_all_configured_servers("rabbitmq",
                                            "control", "contrail-control")[0]
        for node in self.inputs.bgp_control_ips:
            rabbitmq_server = self.get_all_in_use_servers("rabbitmq",
                                                "control", "contrail-control",
                                                 node)
            if rabbitmq_server and rabbitmq_server in valid_rabbitmq_servers:
                self.logger.info("contrail-control running on '%s' connected to"
                                " correct RabbitMQ server" % node)
            else:
                self.logger.error("Either connection is absent or incorrect or "
                                  "status is Down")
                assert False, "Connection issue between contrail-control and RabbitMQ"
    # test_contrail_control_connects_to_rabbitmq

    @preposttest_wrapper
    def test_contrail_agent_connects_to_dns(self):
        '''
        This test case verifies that Contrail Vrouter agent connects to a valid 
        DNS Server
        Steps:
        1. Read "contrail-vrouter-agent.conf" and read all valid DNS servers.
        2. Read OpServer connections and find valid DNS servers connected
           to the contrail-vrouter-agent client.
        3. Check that contrail-vrouter-agent connections to DNS server is a
           subset of values configured in client .conf file
        '''
        valid_dns_servers = self.get_all_configured_servers("dns",
                                        "agent", "contrail-vrouter-agent")[0]
        for node in self.inputs.compute_control_ips:
            dns_servers, status, ports = self.get_all_in_use_servers("dns" ,
                                            "agent", "contrail-vrouter-agent",
                                            node)
            if dns_servers and set(dns_servers) <= set(valid_dns_servers)\
                and all(x == 'Up' for x in status) and all(y == '53' for y in ports):
                self.logger.info("contrail-vrouter-agent running on '%s'"
                                "connected to correct DNS Servers" % node)
            else:
                self.logger.error("Either connection is absent or incorrect or "
                                  "status is Down")
                assert False, "Connection issue between vrouter-agent and DNS Server"
    # test_contrail_agent_connects_to_dns

    @preposttest_wrapper
    def test_contrail_agent_connects_to_control(self):
        '''
        This test case verifies that Contrail Vrouter agent connects to a valid 
        Controller
        Steps:
        1. Read "contrail-vrouter-agent.conf" and read all valid Control servers.
        2. Read OpServer connections and find valid Control servers connected
           to the contrail-vrouter-agent client.
        3. Check that contrail-vrouter-agent connections to Control server is a
           subset of values configured in client .conf file
        '''
        valid_controllers = self.get_all_configured_servers("xmpp",
                                        "agent", "contrail-vrouter-agent")[0]
        for node in self.inputs.compute_control_ips:
            controllers, status, ports = self.get_all_in_use_servers("xmpp" ,
                                            "agent", "contrail-vrouter-agent",
                                            node)
            if controllers and set(controllers) <= set(valid_controllers)\
                and all(x == 'Up' for x in status) and all(y == '5269' for y in ports):
                self.logger.info("contrail-vrouter-agent running on '%s'"
                                "connected to correct Controller" % node)
            else:
                self.logger.error("Either connection is absent or incorrect or "
                                  "status is Down")
                assert False, "Connection issue between vrouter-agent and Controller"
    # test_contrail_agent_connects_to_control

    @preposttest_wrapper
    def test_contrail_agent_connects_to_collector(self):
        '''
        This test case verifies that Contrail Vrouter agent connects to a valid 
        Collector
        Steps:
        1. Read "contrail-vrouter-agent.conf" and read all valid Collector.
        2. Read OpServer connections and find valid Collector is connected
           to the contrail-vrouter-agent client.
        3. Check that contrail-vrouter-agent connections to Collector is a
           subset of values configured in client .conf file
        '''
        valid_collectors = self.get_all_configured_servers("collector",
                                        "agent", "contrail-vrouter-agent")[0]
        for node in self.inputs.compute_control_ips:
            collectors, status, ports = self.get_all_in_use_servers("collector" ,
                                            "agent", "contrail-vrouter-agent",
                                            node)
            if collectors and set(collectors) <= set(valid_collectors)\
                and all(x == 'Up' for x in status) and all(y == '8086' for y in ports):
                self.logger.info("contrail-vrouter-agent running on '%s'"
                                "connected to correct Collector" % node)
            else:
                self.logger.error("Either connection is absent or incorrect or"
                                  "status is Down")
                assert False, "Connection issue between vrouter-agent and Collector"
    # test_contrail_agent_connects_to_collector

    @preposttest_wrapper
    def test_random_client_connections_to_collector(self):
        '''
        Almost all contrail services connects to Collector.
        Following test verifies that various clients have connection
        to the collector servers
        '''
        verification_dict = \
            {'agent' : 
                {'contrail-vrouter-agent' : self.inputs.compute_control_ips[0],
                 'contrail-vrouter-nodemgr' : self.inputs.compute_control_ips[0]},
             'control' :
                {'contrail-control' : self.inputs.bgp_control_ips[0],
                 'contrail-control-nodemgr' : self.inputs.bgp_control_ips[0],
                 'contrail-dns' : self.inputs.bgp_control_ips[0]},
             'config' :
                {'contrail-api' : self.inputs.cfgm_control_ips[0],
                 'contrail-config-nodemgr' : self.inputs.cfgm_control_ips[0]},
             'analytics':
                { 'contrail-analytics-api' : self.inputs.collector_control_ips[0],
                 'contrail-analytics-nodemgr' : self.inputs.collector_control_ips[0]},
             'database':
                {'contrail-database-nodemgr' : self.inputs.database_control_ips[0],
                 'contrail-query-engine' : self.inputs.collector_control_ips[0]}
            }
        for client_type, client_process in verification_dict.items():
            for process_name, client_node in client_process.items():
                collectors, status, ports = self.get_all_in_use_servers("collector" ,
                                            client_type, process_name, client_node)
                if collectors and all(x == 'Up' for x in status)\
                    and all(y == '8086' for y in ports):
                    self.logger.debug("Connection between collector and %s is"
                                      "established" % process_name)
                else:
                    self.logger.error("Either connection is absent or incorrect or "
                                  "status is Down")
                    assert False, "Connection issue between %s and Collector" \
                                % process_name
    # test_random_client_connections_to_collector
