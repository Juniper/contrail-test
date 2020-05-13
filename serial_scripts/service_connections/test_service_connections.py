from common.service_connections.base import BaseServiceConnectionsTest
from tcutils.wrappers import preposttest_wrapper

class TestServiceConnectionsSerial(BaseServiceConnectionsTest):

    @classmethod
    def setUpClass(cls):
        super(TestServiceConnectionsSerial, cls).setUpClass()
    
    @preposttest_wrapper
    def test_add_remove_control_from_agent(self):
        '''
        Verify that on removing the entry from contail-vrouter-agent.conf
        file CONTROL-NODE servers section, the connection to that server is
         lost.
        Steps:
        1. Check the connections of agent to Control node(XMPP)
        2. Remove the entry of in use server from all client .conf files
        3. Verify that removed server is not connected to any client.
        4. Add the entry back in all client .conf file as part of cleanup
        '''
        self.skip_if_setup_incompatible("agent", 1, "control", 3)
        result = True
        in_use_servers, status, ports = self.get_all_in_use_servers("xmpp" ,"agent", 
                                            "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        self.add_remove_server("remove", in_use_servers[0], "CONTROL-NODE",
                                "servers", "agent", "contrail-vrouter-agent", "vrouter_vrouter-agent_1")
        self.addCleanup(self.add_remove_server, "add", in_use_servers[0],
                "CONTROL-NODE", "servers", "agent", "contrail-vrouter-agent", "vrouter_vrouter-agent_1")
        for node in self.inputs.compute_control_ips:
            new_in_use_servers, status, ports = self.get_all_in_use_servers("xmpp",
                                            "agent", "contrail-vrouter-agent",
                                            node)
            if in_use_servers[0] in new_in_use_servers or 'Down' in status:
                self.logger.error("Connection unexpected. Either the server "
                                "removed from .conf file is still getting"
                                " used or the status of connection is down")
                result = False
            else:
                self.logger.info("Connections switched to other server after "
                                 "removal of entry in .conf file")
        assert result, "Unexpected Connection"
    #end test_add_remove_control_from_agent

    @preposttest_wrapper
    def test_add_remove_dns_from_agent(self):
        '''
        Verify that on removing the entry from contail-vrouter-agent.conf
        file DNS servers section, the connection to that server is lost.
        Steps:
        1. Check the connections of agent to Control node(DNS)
        2. Remove the entry of in use server from all client .conf files
        3. Verify that removed server is not connected to any client.
        4. Add the entry back in all client .conf file as part of cleanup
        '''
        self.skip_if_setup_incompatible("agent", 1, "control", 3)
        result = True
        in_use_servers, status, ports = self.get_all_in_use_servers("dns" ,"agent",
                                            "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        self.add_remove_server("remove", in_use_servers[0], "DNS",
                                "servers", "agent", "contrail-vrouter-agent", "vrouter_vrouter-agent_1")
        self.addCleanup(self.add_remove_server, "add", in_use_servers[0], "DNS",
                                "servers", "agent", "contrail-vrouter-agent", "vrouter_vrouter-agent_1")
        for node in self.inputs.compute_control_ips:
            new_in_use_servers, status, ports = self.get_all_in_use_servers("dns",
                                            "agent", "contrail-vrouter-agent",
                                            node)
            if in_use_servers[0] in new_in_use_servers or 'Down' in status:
                self.logger.error("Connection unexpected. Either the server "
                                "removed from .conf file is still getting"
                                " used or the status of connection is down")
                result = False
            else:
                self.logger.info("Connections switched to other server after "
                                 "removal of entry in .conf file")
        assert result, "Unexpected Connection"
    #end test_add_remove_dns_from_agent

    @preposttest_wrapper
    def test_add_remove_collector_from_agent(self):
        '''
        Verify that on removing the entry from contail-vrouter-agent.conf
        file "collectors" section, the connection to that server is lost.
        Steps:
        1. Check the connections of agent to Collector
        2. Remove the entry of in use server from all client .conf files
        3. Verify that removed server is not connected to any client.
        4. Add the entry back in all client .conf file as part of cleanup
        '''
        self.skip_if_setup_incompatible("agent", 1, "analytics", 2)
        result = True
        in_use_servers, status, ports = self.get_all_in_use_servers("collector" ,
                                        "agent", "contrail-vrouter-agent",
                                        self.inputs.compute_control_ips[0])
        self.add_remove_server("remove", in_use_servers[0], "DEFAULT",
                            "collectors", "agent", "contrail-vrouter-agent", "vrouter_vrouter-agent_1")
        self.addCleanup(self.add_remove_server, "add", in_use_servers[0], "DEFAULT",
                            "collectors", "agent", "contrail-vrouter-agent", "vrouter_vrouter-agent_1")
        for node in self.inputs.compute_control_ips:
            new_in_use_servers, status, ports = self.get_all_in_use_servers(
                                            "collector", "agent",
                                            "contrail-vrouter-agent", node)
            if in_use_servers[0] in new_in_use_servers or 'Down' in status:
                self.logger.error("Connection unexpected. Either the server "
                                "removed from .conf file is still getting"
                                " used or the status of connection is down")
                result = False
            else:
                self.logger.info("Connections switched to other server after "
                                 "removal of entry in .conf file")
        assert result, "Unexpected Connection"
    #end test_add_remove_collector_from_agent
    
    @preposttest_wrapper
    def test_add_remove_rabbitmq_from_control(self):
        '''
        Verify that on removing the entry from contail-control.conf file 
        "rabbitmq_server_list" section, the connection to that server is lost.
        Steps:
        1. Check the connections of control to RabbitMQ
        2. Remove the entry of in use server from all client .conf files
        3. Verify that removed server is not connected to any client.
        4. Add the entry back in all client .conf file as part of cleanup
        '''
        self.skip_if_setup_incompatible("control", 1, "openstack", 2)
        result = True
        in_use_server = self.get_all_in_use_servers("rabbitmq" ,
                                        "control", "contrail-control",
                                        self.inputs.bgp_control_ips[0])
        self.add_remove_server("remove", in_use_server, "CONFIGDB",
                        "rabbitmq_server_list", "control", "contrail-control", "control_control_1")
        self.addCleanup(self.add_remove_server, "add", in_use_server, "CONFIGDB",
                        "rabbitmq_server_list", "control", "contrail-control", "control_control_1")
        for node in self.inputs.bgp_control_ips:
            new_in_use_server = self.get_all_in_use_servers(
                                            "rabbitmq", "control",
                                            "contrail-control", node)
            if in_use_server == new_in_use_server:
                self.logger.error("Connection unexpected. Either the server "
                                "removed from .conf file is still getting used")
                result = False
            else:
                self.logger.info("Connections switched to other server after "
                                 "removal of entry in .conf file")
        
        assert result, "Unexpected Connection"
    #end test_add_remove_rabbitmq_from_control
    
    @preposttest_wrapper
    def test_add_remove_rabbitmq_from_dns(self):
        '''
        Verify that on removing the entry from contail-dns.conf file 
        "rabbitmq_server_list" section, the connection to that server is lost.
        Steps:
        1. Check the connections of DNS to RabbitMQ
        2. Remove the entry of in use server from all client .conf files
        3. Verify that removed server is not connected to any client.
        4. Add the entry back in all client .conf file as part of cleanup
        '''
        self.skip_if_setup_incompatible("control", 1, "openstack", 2)
        result = True
        in_use_server = self.get_all_in_use_servers("rabbitmq" ,
                                        "dns", "contrail-dns",
                                        self.inputs.bgp_control_ips[0])
        self.add_remove_server("remove", in_use_server, "CONFIGDB",
                        "rabbitmq_server_list", "dns", "contrail-dns", "control_dns_1")
        self.addCleanup(self.add_remove_server, "add", in_use_server, "CONFIGDB",
                        "rabbitmq_server_list", "dns", "contrail-dns", "control_dns_1")
        for node in self.inputs.bgp_control_ips:
            new_in_use_server = self.get_all_in_use_servers(
                                            "rabbitmq", "dns",
                                            "contrail-dns", node)
            if in_use_server == new_in_use_server:
                self.logger.error("Connection unexpected. Either the server "
                                "removed from .conf file is still getting used")
                result = False
            else:
                self.logger.info("Connections switched to other server after "
                                 "removal of entry in .conf file")
        assert result, "Unexpected Connection"
    #end test_add_remove_rabbitmq_from_dns
    
    @preposttest_wrapper
    def test_recovery_from_errored_configdb_entry_in_control(self):
        '''
        Verify that when an Errored entry in config db list is corrected
        and SIGHUP is issued, the connection is resumed.
        This test case is to verify scenario of bug1690715
        Steps:
        1. Check the connections of Control to Config DB. 
        2. Change the entry to an invalid IP and issue SIGHUP.
        3. Verify that connection is lost 
        3. Again edit and correct the entry of config DB and issue SIGHUP
        4. Verify that connection is resumed.
        '''
        result = True
        ctrl_ip = self.inputs.bgp_control_ips[0]
        ip = self.inputs.bgp_ips[0]
        conf_file = "/etc/contrail/contrail-control.conf"
        in_use_servers, status, db_ports = self.get_all_in_use_servers(
                              "configdb", "control", "contrail-control", ip)
        server_list = [s+":"+p for s,p in zip(in_use_servers, db_ports)]
        self.configure_server_list(ip, "contrail-control", "CONFIGDB",
                                   "config_db_server_list",
                                   ["254.254.254.254:%s" % db_ports[0]],
                                   conf_file, "control_control_1", "control",
                                   False)
        self.addCleanup(self.configure_server_list, ip, "contrail-control",
                        "CONFIGDB", "config_db_server_list", server_list, conf_file,
                        "control_control_1", "control", True)
        self.inputs.run_cmd_on_server(ip, "kill -s HUP `pidof contrail-control`",
                                self.inputs.host_data[ip]['username'],
                                self.inputs.host_data[ip]['password'],
                                pty=True, as_sudo=True)
        self.sleep(10)
        new_in_use_servers, new_status, _ = self.get_all_in_use_servers("configdb" ,
                                        "control", "contrail-control", ip)
        if new_in_use_servers[0] != "254.254.254.254" or new_status[0] == "Up":
            result = False
            self.logger.error("Config DB connection still UP even if no valid "
                              "entry mentioned in config db list")
        else:
            self.logger.info("As expected, connection to config DB is down as "
                              "there is no valid entry in config db list")

        self.configure_server_list(ip, "contrail-control", "CONFIGDB",
                                   "config_db_server_list", server_list,
                                   conf_file, "control_control_1", "control", False)
        self.inputs.run_cmd_on_server(ip, "kill -s HUP `pidof contrail-control`",
                                self.inputs.host_data[ip]['username'],
                                self.inputs.host_data[ip]['password'],
                                pty=True, as_sudo=True)
        self.sleep(10)
        new_in_use_servers, new_status, _ = self.get_all_in_use_servers("configdb" ,
                                        "control", "contrail-control",
                                        self.inputs.bgp_control_ips[0])
        if not all(x == 'Up' for x in new_status):
            result = False
            self.logger.error("Config DB connection still Down even if valid "
                              "entries are mentioned in config db list")
        else:
            self.logger.info("As expected, connection to config DB is established as"
                              " valid entries are updated in config db list")
        assert result, "Unexpected Connection"
    #end test_recovery_from_errored_configdb_entry_in_control
    
    @preposttest_wrapper
    def test_add_remove_collector_from_config_nodemgr(self):
        '''
        Verify that on removing the entry from contail-config-nodemgr.conf file 
        [Collector] server_list section, the connection to that server is lost.
        Steps:
        1. Check the connections of collector and config-nodemgr.
        2. Remove the entry of in use server from all client .conf files
        3. Verify that removed server is not connected to any client.
        4. Add the entry back in all client .conf file as part of cleanup
        '''
        self.skip_if_setup_incompatible("config", 1, "analytics", 2)
        result = True
        in_use_servers, status, ports = self.get_all_in_use_servers("collector" ,
                                        "config", "contrail-config-nodemgr",
                                        self.inputs.cfgm_control_ips[0])
        self.add_remove_server("remove", in_use_servers[0], "COLLECTOR",
                        "server_list", "config", "contrail-config-nodemgr", "config_nodemgr_1")
        self.addCleanup(self.add_remove_server, "add", in_use_servers[0],
                        "COLLECTOR", "server_list", "config",
                        "contrail-config-nodemgr", "config_nodemgr_1")
        for node in self.inputs.cfgm_control_ips:
            new_in_use_servers, status, ports = self.get_all_in_use_servers(
                                            "collector", "config",
                                            "contrail-config-nodemgr", node)
            if in_use_servers[0] in new_in_use_servers or 'Down' in status:
                self.logger.error("Connection unexpected. Either the server "
                                "removed from .conf file is still getting"
                                " used or the status of connection is down")
                result = False
            else:
                self.logger.info("Connections switched to other server after "
                                 "removal of entry in .conf file")
        assert result, "Unexpected Connection"
    #end test_add_remove_collector_from_config_nodemgr
    
    @preposttest_wrapper
    def test_control_agent_connection_on_control_restart(self):
        '''
        This test case verifies that on bringing down a Controller connected
        to contrail-vrouter-agent, it should immediately switch to new controller.
        Steps:
        1. Check the Controller to which contrail-vrouter-agent is connected to.
        2. Stop that Controller service
        3. Check that contrail-vrouter-agent immediately switches to new collector.
        4. Start the controller stopped in step 2.
        '''
        self.skip_if_setup_incompatible("agent", 1, "control", 3)
        in_use_servers, status, ports = self.get_all_in_use_servers("xmpp" ,"agent", 
                                            "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        self.inputs.stop_service("contrail-control",[in_use_servers[0]],
                                 container = "control")
        self.addCleanup(self.inputs.start_service, "contrail-control",
                        [in_use_servers[0]], container = "control")
        self.addCleanup(self.inputs.verify_service_state, [in_use_servers[0]],
                        "xmpp", "control")
        self.sleep(15) # Agent retries to connect to previous Controller 4 times in an interval of 1,2,4,8 seconds
        new_in_use_servers, status, ports = self.get_all_in_use_servers(
                                            "xmpp" ,"agent", 
                                            "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        if len(new_in_use_servers) == 2 and \
            in_use_servers[0] not in new_in_use_servers \
            and all(x == 'Up' for x in status):
            self.logger.info("Connections switched to other Controller")
        else:
            self.logger.error("Connection not switched to new Controller")
            assert False, "Unexpected Connection"
    #end test_control_agent_connection_on_control_restart
    
    @preposttest_wrapper
    def test_dns_agent_connection_on_dns_restart(self):
        '''
        This test case verifies that on bringing down a DNS connected
        to contrail-vrouter-agent, it should immediately switch to new DNS server.
        Steps:
        1. Check the DNS to which contrail-vrouter-agent is connected to.
        2. Stop that DNS service
        3. Check that contrail-vrouter-agent immediately switches to new DNS server.
        4. Start the DNS server stopped in step 2.
        '''
        self.skip_if_setup_incompatible("agent", 1, "control", 3)
        in_use_servers, status, ports = self.get_all_in_use_servers("dns" ,"agent", 
                                            "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        self.inputs.stop_service("contrail-dns",[in_use_servers[0]],
                                 container = "dns")
        self.addCleanup(self.inputs.start_service,
                        "contrail-dns",[in_use_servers[0]],
                        container = "dns")
        self.addCleanup(self.inputs.verify_service_state, [in_use_servers[0]],
                        "dns", "control")
        self.sleep(15) # Agent retries to connect to previous DNS Server 4 times in an interval of 1,2,4,8 seconds
        new_in_use_servers, status, ports = self.get_all_in_use_servers(
                                            "dns" ,"agent", 
                                            "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        if len(new_in_use_servers) == 2 and \
            in_use_servers[0] not in new_in_use_servers \
            and all(x == 'Up' for x in status):
            self.logger.info("Connections switched to other DNS Server")
        else:
            self.logger.error("Connection not switched to new DNS server")
            assert False, "Unexpected Connection"
    #end test_dns_agent_connection_on_dns_restart
    
    @preposttest_wrapper
    def test_collector_agent_connection_on_collector_restart(self):
        '''
        This test case verifies that on bringing down a Collector connected
        to contrail-vrouter-agent, it should immediately switch to new Collector.
        Steps:
        1. Check the Collector to which contrail-vrouter-agent is connected to.
        2. Stop that Collector service
        3. Check that contrail-vrouter-agent immediately switches to new Collector.
        4. Start the Collector stopped in step 2.
        '''
        self.skip_if_setup_incompatible("agent", 1, "analytics", 2)
        in_use_servers, status, ports = self.get_all_in_use_servers("collector" ,"agent", 
                                            "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        self.inputs.stop_service("contrail-collector",[in_use_servers[0]],
                                 container = "collector")
        self.addCleanup(self.inputs.start_service,
                        "contrail-collector",[in_use_servers[0]],
                        container = "collector")
        self.addCleanup(self.inputs.verify_service_state, [in_use_servers[0]],
                        "collector", "analytics")
        self.sleep(15) # Agent retries to connect to previous Collector 4 times in an interval of 1,2,4,8 seconds
        new_in_use_servers, status, ports = self.get_all_in_use_servers(
                                            "collector" ,"agent", 
                                            "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        if in_use_servers[0] not in new_in_use_servers \
            and all(x == 'Up' for x in status):
            self.logger.info("Connections switched to other Collector")
        else:
            self.logger.error("Connection not switched to new Collector")
            assert False, "Unexpected Connection"
    #end test_collector_agent_connection_on_collector_restart
    
    @preposttest_wrapper
    def test_rabbitmq_control_connection_on_rabbitmq_restart(self):
        '''
        This test case verifies that on bringing down a rabbitMQ connected
        to contrail-control, it should immediately switch to new RabbitMQ server.
        Steps:
        1. Check the RabbitMQ Server to which contrail-control is connected to.
        2. Stop that RabbitMq service
        3. Check that contrail-control immediately switches to new RabbitMQ server.
        4. Start the  RabbitMQ server stopped in step 2.
        '''
        self.skip_if_setup_incompatible("control", 1, "openstack", 2)
        in_use_server = self.get_all_in_use_servers("rabbitmq" ,
                                            "control", "contrail-control",
                                            self.inputs.bgp_control_ips[0])
        self.inputs.stop_service("rabbitmq-server",[in_use_server], container='rabbitmq',
            verify_service=False)
        self.addCleanup(self.inputs.start_service,
                        "rabbitmq-server",[in_use_server], 'rabbitmq', False)
        new_in_use_server = self.get_all_in_use_servers("rabbitmq" ,
                                            "control", "contrail-control",
                                            self.inputs.bgp_control_ips[0])
        if in_use_server != new_in_use_server:
            self.logger.info("Connections switched to other RabbitMQ Server")
        else:
            self.logger.error("Connection not switched to new RabbitMQ server")
            assert False, "Unexpected Connection"
    #end test_rabbitmq_control_connection_on_rabbitmq_restart
    
    @preposttest_wrapper
    def test_rabbitmq_dns_connection_on_rabbitmq_restart(self):
        '''
        This test case verifies that on bringing down a rabbitMQ connected
        to contrail-dns, it should immediately switch to new RabbitMQ server.
        Steps:
        1. Check the RabbitMQ Server to which contrail-dns is connected to.
        2. Stop that RabbitMq service
        3. Check that contrail-dns immediately switches to new RabbitMQ server.
        4. Start the  RabbitMQ server stopped in step 2.
        '''
        self.skip_if_setup_incompatible("control", 1, "openstack", 2)
        in_use_server = self.get_all_in_use_servers("rabbitmq" ,
                                            "control", "contrail-dns",
                                            self.inputs.bgp_control_ips[0])
        self.inputs.stop_service("rabbitmq-server",[in_use_server], container='rabbitmq',
            verify_service=False)
        self.addCleanup(self.inputs.start_service,
                        "rabbitmq-server",[in_use_server], 'rabbitmq', False)
        new_in_use_server = self.get_all_in_use_servers("rabbitmq" ,
                                            "control", "contrail-dns",
                                            self.inputs.bgp_control_ips[0])
        if in_use_server != new_in_use_server:
            self.logger.info("Connections switched to other RabbitMQ Server")
        else:
            self.logger.error("Connection not switched to new RabbitMQ server")
            assert False, "Unexpected Connection"
    #end test_rabbitmq_dns_connection_on_rabbitmq_restart
    
    @preposttest_wrapper
    def disabled_test_control_agent_connection_after_active_control_restart_agent_sighup(self):
        '''
        This test case verifies the issue captured in bug 1694793.
        Expectations:
        1. If an active server goes down/up, then the client which switched connection
           due to server restart will reallocate resource/load balance after giving a SIGHUP.
        2. If an server which is not connected to the client goes down, then client should 
           not reallocate/load balance on SIGHUP. It should retain previous connections. 
        Steps:
        1. Check the Controller to which contrail-vrouter-agent is connected to.
        2. Stop that Controller service
        3. Check that contrail-vrouter-agent immediately switches to new collector.
        4. Start the Controller stopped in step 2.
        5. Issue SIGHUPs on client to verify that the client should lose previous 
           connection and should take part in re-allocation or load  balancing.
        6. Stop and start the Controller service to which the client do not connect.
        7. Issue SIGHUPs on client to verify that the client should not lose the 
           previous connections as it was not affected due to server restart.
        '''
        self.skip_if_setup_incompatible("agent", 1, "control", 3)
        in_use_servers, status, ports = self.get_all_in_use_servers("xmpp" ,"agent", 
                                            "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        self.inputs.stop_service('control', [in_use_servers[0]], container='control')
        self.sleep(15)
        self.inputs.start_service('control', [in_use_servers[0]], container='control')
        new_in_use_servers, status, ports = self.get_all_in_use_servers(
                                            "xmpp", "agent", "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        if in_use_servers[0] not in new_in_use_servers \
            and all(x == 'Up' for x in status):
            self.logger.info("Connections switched to other Controller")
        else:
            self.logger.error("Connection not switched to new Controller")
            assert False, "Unexpected Connection"
        ip = self.inputs.compute_control_ips[0]
        self.inputs.run_cmd_on_server(ip, "kill -s HUP `pidof contrail-vrouter-agent`",
                                self.inputs.host_data[ip]['username'],
                                self.inputs.host_data[ip]['password'], pty=True, as_sudo=True)
        self.sleep(10)
        servers_in_use, status, ports = self.get_all_in_use_servers("xmpp",
                                        "agent", "contrail-vrouter-agent",
                                        self.inputs.compute_control_ips[0])
        if new_in_use_servers != servers_in_use \
            and all(x == 'Up' for x in status):
            self.logger.info("The client which was affected due to down/up of server "
                            " has successfully taken part in reallocation/load " 
                            " balancing after issuing SIGHUP")
        else:
            self.logger.error("The client which was affected due to down/up of server "
                            " has not taken part in reallocation/load balancing after"
                            " issuing SIGHUP")
            assert False, "Unexpected Connection"
        # checking that restarting inactive collector doesnt affect the connections after SIGHUP
        self.inputs.stop_service('control', [new_in_use_servers[0]], container='control')
        self.sleep(15)
        self.inputs.start_service('control', [new_in_use_servers[0]], container='control')
        in_use_servers_new, status, ports = self.get_all_in_use_servers(
                                            "xmpp", "agent", "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        if servers_in_use == in_use_servers_new \
            and all(x == 'Up' for x in status):
            self.logger.info("Connections still same after restart as restarted server"
                             " was not being used by the client")
        else:
            self.logger.error("Connection switched to new Collector. As restarted server"
                              " was not being used by client, connection should not have"
                              " been affected")
            assert False, "Unexpected Connection"
        ip = self.inputs.compute_control_ips[0]
        self.inputs.run_cmd_on_server(ip, "kill -s HUP `pidof contrail-vrouter-agent`",
                                self.inputs.host_data[ip]['username'],
                                self.inputs.host_data[ip]['password'], pty=True, as_sudo=True)
        self.sleep(10)
        servers_in_use, status, ports = self.get_all_in_use_servers(
                                        "xmpp", "agent", "contrail-vrouter-agent",
                                        self.inputs.compute_control_ips[0])
        if servers_in_use == in_use_servers_new \
            and all(x == 'Up' for x in status):
            self.logger.info("There is no affect on client which was connected to "
                            "different servers than the server which went down/up")
        else:
            self.logger.error("Even if the client did not had any impact due to down/up "
                              "of the server, still client participated in re allocation")
            assert False, "Unexpected Connection"
    # end test_control_agent_connection_after_active_control_restart_agent_sighup

    @preposttest_wrapper
    def test_collector_agent_connection_after_collector_restart_and_agent_sighup(self):
        '''
        This test case verifies the issue captured in bug 1694793.
        Expectations:
        1. If an active server goes down/up, then the client which switched connection
           due to server restart will reallocate resource/load balance after giving a SIGHUP.
        2. If an server which is not connected to the client goes down, then client should 
           not reallocate/load balance on SIGHUP. It should retain previous connections. 
        Steps:
        1. Check the Collector to which contrail-vrouter-agent is connected to.
        2. Stop that Collector service
        3. Check that contrail-vrouter-agent immediately switches to new collector.
        4. Start the collector stopped in step 2.
        5. Issue SIGHUPs on client to verify that the client should lose previous 
           connection and should take part in re-allocation or load  balancing.
        6. Stop and start the Collector service to which the client do not connect.
        7. Issue SIGHUPs on client to verify that the client should not lose the 
           previous connections as it was not affected due to server restart.
        '''
        self.skip_if_setup_incompatible("agent", 1, "collector", 2)
        in_use_servers, status, ports = self.get_all_in_use_servers("collector" ,"agent", 
                                            "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        self.inputs.stop_service('collector', [in_use_servers[0]], container='collector')
        self.sleep(15)
        self.inputs.start_service('collector', [in_use_servers[0]], container='collector')
        new_in_use_servers, status, ports = self.get_all_in_use_servers(
                                            "collector", "agent", "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        if in_use_servers[0] not in new_in_use_servers \
            and all(x == 'Up' for x in status):
            self.logger.info("Connections switched to other Collector")
        else:
            self.logger.error("Connection not switched to new Collector")
            assert False, "Unexpected Connection"
        ip = self.inputs.compute_control_ips[0]
        self.inputs.run_cmd_on_server(ip, "kill -s HUP `pidof contrail-vrouter-agent`",
                                self.inputs.host_data[ip]['username'],
                                self.inputs.host_data[ip]['password'], pty=True, as_sudo=True)
        self.sleep(10)
        servers_in_use, status, ports = self.get_all_in_use_servers("collector",
                                        "agent", "contrail-vrouter-agent",
                                        self.inputs.compute_control_ips[0])
        if new_in_use_servers != servers_in_use \
            and all(x == 'Up' for x in status):
            self.logger.info("The client which was affected due to down/up of server "
                            " has successfully taken part in reallocation/load " 
                            " balancing after issuing SIGHUP")
        else:
            self.logger.error("The client which was affected due to down/up of server "
                            " has not taken part in reallocation/load balancing after"
                            " issuing SIGHUP")
            assert False, "Unexpected Connection"
        # checking that restarting inactive collector doesnt affect the connections after SIGHUP
        self.inputs.stop_service('collector', [new_in_use_servers[0]], container='collector')
        self.sleep(15)
        self.inputs.start_service('collector', [new_in_use_servers[0]], container='collector')
        in_use_servers_new, status, ports = self.get_all_in_use_servers(
                                            "collector", "agent", "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        if servers_in_use == in_use_servers_new \
            and all(x == 'Up' for x in status):
            self.logger.info("Connections still same after restart as restarted server"
                             " was not being used by the client")
        else:
            self.logger.error("Connection switched to new Collector. As restarted server"
                              " was not being used by client, connection should not have"
                              " been affected")
            assert False, "Unexpected Connection"
        ip = self.inputs.compute_control_ips[0]
        self.inputs.run_cmd_on_server(ip, "kill -s HUP `pidof contrail-vrouter-agent`",
                                self.inputs.host_data[ip]['username'],
                                self.inputs.host_data[ip]['password'], pty=True, as_sudo=True)
        self.sleep(10)
        servers_in_use, status, ports = self.get_all_in_use_servers("collector",
                                        "agent", "contrail-vrouter-agent",
                                        self.inputs.compute_control_ips[0])
        if servers_in_use == in_use_servers_new \
            and all(x == 'Up' for x in status):
            self.logger.info("There is no affect on client which was connected to "
                            "different servers than the server which went down/up")
        else:
            self.logger.error("Even if the client did not had any impact due to down/up "
                              "of the server, still client participated in re allocation")
            assert False, "Unexpected Connection"
    # end test_collector_agent_connection_after_collector_restart_and_agent_sighup

    @preposttest_wrapper
    def test_collector_control_connection_after_collector_restart_and_control_sighup(self):
        '''
        This test case verifies the issue captured in bug 1694793.
        Expectations:
        1. If an active server goes down/up, then the client which switched connection
           due to server restart will reallocate resource/load balance after giving a SIGHUP.
        2. If an server which is not connected to the client goes down, then client should 
           not reallocate/load balance on SIGHUP. It should retain previous connections. 
        Steps:
        1. Check the Collector to which contrail-control is connected to.
        2. Stop that Collector service
        3. Check that contrail-control immediately switches to new collector.
        4. Start the collector stopped in step 2.
        5. Issue SIGHUPs on client to verify that the client should lose previous 
           connection and should take part in re-allocation or load  balancing.
        6. Stop and start the Collector service to which the client do not connect.
        7. Issue SIGHUPs on client to verify that the client should not lose the 
           previous connections as it was not affected due to server restart.
        '''
        self.skip_if_setup_incompatible("control", 1, "collector", 2)
        in_use_servers, status, ports = self.get_all_in_use_servers("collector" ,"control", 
                                            "contrail-control",
                                            self.inputs.bgp_control_ips[0])
        self.inputs.stop_service('collector', [in_use_servers[0]], container='collector')
        self.sleep(15)
        self.inputs.start_service('collector', [in_use_servers[0]], container='collector')
        new_in_use_servers, status, ports = self.get_all_in_use_servers(
                                            "collector", "control", "contrail-control", 
                                            self.inputs.bgp_control_ips[0])
        if in_use_servers[0] not in new_in_use_servers \
            and all(x == 'Up' for x in status):
            self.logger.info("Connections switched to other Collector")
        else:
            self.logger.error("Connection not switched to new Collector")
            assert False, "Unexpected Connection"
        ip = self.inputs.bgp_control_ips[0]
        self.inputs.run_cmd_on_server(ip, "kill -s HUP `pidof contrail-control`",
                                self.inputs.host_data[ip]['username'],
                                self.inputs.host_data[ip]['password'], pty=True, as_sudo=True)
        self.sleep(10)
        servers_in_use, status, ports = self.get_all_in_use_servers("collector",
                                        "control", "contrail-control",
                                        self.inputs.bgp_control_ips[0])
        if new_in_use_servers != servers_in_use \
            and all(x == 'Up' for x in status):
            self.logger.info("The client which was affected due to down/up of server "
                            " has successfully taken part in reallocation/load " 
                            " balancing after issuing SIGHUP")
        else:
            self.logger.error("The client which was affected due to down/up of server "
                            " has not taken part in reallocation/load balancing after"
                            " issuing SIGHUP")
            assert False, "Unexpected Connection"
        # checking that restarting inactive collector doesnt affect the connections after SIGHUP
        self.inputs.stop_service('collector', [new_in_use_servers[0]], container='collector')
        self.sleep(15)
        self.inputs.start_service('collector', [new_in_use_servers[0]], container='collector')
        in_use_servers_new, status, ports = self.get_all_in_use_servers(
                                            "collector", "control", "contrail-control",
                                            self.inputs.bgp_control_ips[0])
        if servers_in_use == in_use_servers_new \
            and all(x == 'Up' for x in status):
            self.logger.info("Connections still same after restart as restarted server"
                             " was not being used by the client")
        else:
            self.logger.error("Connection switched to new Collector. As restarted server"
                              " was not being used by client, connection should not have"
                              " been affected")
            assert False, "Unexpected Connection"
        ip = self.inputs.bgp_control_ips[0]
        self.inputs.run_cmd_on_server(ip, "kill -s HUP `pidof contrail-control`",
                                self.inputs.host_data[ip]['username'],
                                self.inputs.host_data[ip]['password'], pty=True, as_sudo=True)
        self.sleep(10)
        servers_in_use, status, ports = self.get_all_in_use_servers(
                                        "collector", "control", "contrail-control",
                                        self.inputs.bgp_control_ips[0])
        if servers_in_use == in_use_servers_new \
            and all(x == 'Up' for x in status):
            self.logger.info("There is no affect on client which was connected to "
                            "different servers than the server which went down/up")
        else:
            self.logger.error("Even if the client did not had any impact due to down/up "
                              "of the server, still client participated in re allocation")
            assert False, "Unexpected Connection"
    # end test_collector_control_connection_after_collector_restart_and_control_sighup
