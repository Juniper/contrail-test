# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import unittest
import testtools
from tcutils.wrappers import preposttest_wrapper
from common.service_connections.base import BaseServiceConnectionsTest
from time import sleep

class TestServiceConnectionsSerial(BaseServiceConnectionsTest):

    @classmethod
    def setUpClass(cls):
        super(TestServiceConnectionsSerial, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest
    
    @preposttest_wrapper
    def add_remove_control_from_agent(self):
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
        in_use_servers, status = self.get_all_in_use_servers("xmpp" ,"agent", 
                                            "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        self.add_remove_server("remove", in_use_servers[0], "CONTROL-NODE",
                                "servers", "agent", "contrail-vrouter-agent")
        for node in self.inputs.compute_control_ips:
            new_in_use_servers, status = self.get_all_in_use_servers("xmpp" ,
                                            "agent", "contrail-vrouter-agent",
                                            node)
            if in_use_servers[0] in new_in_use_servers or 'Down' in status:
                self.logger.error("Connection unexpected. Either the server "
                                "removed from .conf file is setill getting"
                                " used or the status of connection is down")
                result = False
            else:
                self.logger.info("Connections switched to other server after "
                                 "removal of entry in .conf file")
        self.add_remove_server("add", in_use_servers[0], "CONTROL-NODE",
                                "servers", "agent", "contrail-vrouter-agent")
        assert result, "Unexpected Connection"
    #end add_remove_control_from_agent
    
    @preposttest_wrapper
    def add_remove_dns_from_agent(self):
        '''
        Verify that on removing the entry from contail-vrouter-agent.conf
        file DNS servers section, the connection to that server is lost.
        Steps:
        1. Get list of all valid DNS Servers. 1st 2 should be applicable candidates
        2. Check the connections of agent to DNS server. The agent should be
           connected to first 2 entries as mentioned in .conf file.
        3. Remove the entry of in use server from all client .conf files
        4. Verify that removed server is not connected to any client.
           Also verify that agent is connected to next 2 servers in the list
        5. Add the entry back in all client .conf file as part of cleanup
        6. Check the connections of agent to DNS server. The agent should be
           connected to first 2 entries as mentioned in .conf file
        '''
        self.skip_if_setup_incompatible("agent", 1, "control", 3)
        valid_dns_servers = self.get_all_configured_servers("dns",
                                            "agent", "contrail-vrouter-agent")
        applicable_dns_servers = [valid_dns_servers[0], valid_dns_servers[1]]
        for node in self.inputs.compute_control_ips:
            in_use_servers, status = self.get_all_in_use_servers("dns" ,"agent",
                                            "contrail-vrouter-agent", node)
            if set(in_use_servers) == set(applicable_dns_servers):
                self.logger.info("Agent connected correctly to 1st 2 entries "
                                 "in .conf file")
            else:
                self.logger.error("Agent not connected to 1st 2 entries in "
                                  ".conf file")
                assert False, "Agent connection to DNS is unexpected"
        result = True
        self.add_remove_server("remove", in_use_servers[0], "DNS",
                                "servers", "agent", "contrail-vrouter-agent")
        valid_dns_servers = self.get_all_configured_servers("dns",
                                            "agent", "contrail-vrouter-agent")
        applicable_dns_servers = [valid_dns_servers[0], valid_dns_servers[1]]
        for node in self.inputs.compute_control_ips:
            new_in_use_servers, status = self.get_all_in_use_servers("dns" ,
                                            "agent", "contrail-vrouter-agent",
                                            node)
            if set(applicable_dns_servers) != set(new_in_use_servers) or \
                'Down' in status:
                self.logger.error("Agent not connected to 1st 2 entries in "
                            ".conf file or the status of connection is down")
                result = False
            else:
                self.logger.info("Connections switched to other server after "
                                 "removal of entry in .conf file")
        self.add_remove_server("add", in_use_servers[0], "DNS",
                                "servers", "agent", "contrail-vrouter-agent")
        assert result, "Agent connection to DNS is unexpected"
        valid_dns_servers = self.get_all_configured_servers("dns",
                                            "agent", "contrail-vrouter-agent")
        applicable_dns_servers = [valid_dns_servers[0], valid_dns_servers[1]]
        for node in self.inputs.compute_control_ips:
            in_use_servers, status = self.get_all_in_use_servers("dns" ,"agent",
                                            "contrail-vrouter-agent", node)
            if set(in_use_servers) == set(applicable_dns_servers):
                self.logger.info("Agent connected correctly to 1st 2 entries "
                                 "in .conf file")
            else:
                self.logger.error("Agent not connected to 1st 2 entries in "
                                  ".conf file")
                assert False, "Agent connection to DNS is unexpected"
    #end add_remove_dns_from_agent
    
    @preposttest_wrapper
    def add_remove_collector_from_agent(self):
        '''
        Verify that on removing the entry from contail-vrouter-agent.conf
        file "collectors" section, the connection to that server is lost.
        Steps:
        1. Check the connections of agent to Collector
        2. Remove the entry of in use server from all client .conf files
        3. Verify that removed server is not connected to any client.
        4. Add the entry back in all client .conf file as part of cleanup
        '''
        self.skip_if_setup_incompatible("agent", 1, "analytic", 2)
        result = True
        in_use_servers, status = self.get_all_in_use_servers("collector" ,
                                        "agent", "contrail-vrouter-agent",
                                        self.inputs.compute_control_ips[0])
        self.add_remove_server("remove", in_use_servers[0], "DEFAULT",
                            "collectors", "agent", "contrail-vrouter-agent")
        for node in self.inputs.compute_control_ips:
            new_in_use_servers, status = self.get_all_in_use_servers(
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
        self.add_remove_server("add", in_use_servers[0], "DEFAULT",
                            "collectors", "agent", "contrail-vrouter-agent")
        assert result, "Unexpected Connection"
    #end add_remove_collector_from_agent
    
    @preposttest_wrapper
    def add_remove_rabbitmq_from_control(self):
        '''
        Verify that on removing the entry from contail-control.conf file 
        "rabbitmq_server_list" section, the connection to that server is lost.
        Steps:
        1. Check the connections of control to RabbitMQ
        2. Remove the entry of in use server from all client .conf files
        3. Verify that removed server is not connected to any client.
        4. Add the entry back in all client .conf file as part of cleanup
        '''
        self.skip_if_setup_incompatible("control", 1, "config", 2)
        result = True
        in_use_servers, status = self.get_all_in_use_servers("rabbitmq" ,
                                        "control", "contrail-control",
                                        self.inputs.bgp_control_ips[0])
        self.add_remove_server("remove", in_use_servers[0], "IFMAP",
                        "rabbitmq_server_list", "control", "contrail-control")
        for node in self.inputs.bgp_control_ips:
            new_in_use_servers, status = self.get_all_in_use_servers(
                                            "rabbitmq", "control",
                                            "contrail-control", node)
            if in_use_servers[0] in new_in_use_servers or 'Down' in status:
                self.logger.error("Connection unexpected. Either the server "
                                "removed from .conf file is still getting"
                                " used or the status of connection is down")
                result = False
            else:
                self.logger.info("Connections switched to other server after "
                                 "removal of entry in .conf file")
        self.add_remove_server("add", in_use_servers[0], "IFMAP",
                        "rabbitmq_server_list", "control", "contrail-control")
        assert result, "Unexpected Connection"
    #end add_remove_rabbitmq_from_control
    
    @preposttest_wrapper
    def add_remove_rabbitmq_from_dns(self):
        '''
        Verify that on removing the entry from contail-dns.conf file 
        "rabbitmq_server_list" section, the connection to that server is lost.
        Steps:
        1. Check the connections of DNS to RabbitMQ
        2. Remove the entry of in use server from all client .conf files
        3. Verify that removed server is not connected to any client.
        4. Add the entry back in all client .conf file as part of cleanup
        '''
        self.skip_if_setup_incompatible("control", 1, "config", 2)
        result = True
        in_use_servers, status = self.get_all_in_use_servers("rabbitmq" ,
                                        "control", "contrail-dns",
                                        self.inputs.bgp_control_ips[0])
        self.add_remove_server("remove", in_use_servers[0], "IFMAP",
                        "rabbitmq_server_list", "control", "contrail-dns")
        for node in self.inputs.bgp_control_ips:
            new_in_use_servers, status = self.get_all_in_use_servers(
                                            "rabbitmq", "control",
                                            "contrail-dns", node)
            if in_use_servers[0] in new_in_use_servers or 'Down' in status:
                self.logger.error("Connection unexpected. Either the server "
                                "removed from .conf file is still getting"
                                " used or the status of connection is down")
                result = False
            else:
                self.logger.info("Connections switched to other server after "
                                 "removal of entry in .conf file")
        self.add_remove_server("add", in_use_servers[0], "IFMAP",
                        "rabbitmq_server_list", "control", "contrail-dns")
        assert result, "Unexpected Connection"
    #end add_remove_rabbitmq_from_dns
    
    @preposttest_wrapper
    def add_remove_collector_from_config(self):
        '''
        Verify that on removing the entry from contail-config-nodemgr.conf file 
        [Collector] server_list section, the connection to that server is lost.
        Steps:
        1. Check the connections of collector and config-nodemgr.
        2. Remove the entry of in use server from all client .conf files
        3. Verify that removed server is not connected to any client.
        4. Add the entry back in all client .conf file as part of cleanup
        '''
        self.skip_if_setup_incompatible("config", 1, "analytic", 2)
        result = True
        in_use_servers, status = self.get_all_in_use_servers("collector" ,
                                        "config", "contrail-config-nodemgr",
                                        self.inputs.cfgm_control_ips[0])
        self.add_remove_server("remove", in_use_servers[0], "COLLECTOR",
                        "server_list", "config", "contrail-config-nodemgr")
        for node in self.inputs.cfgm_control_ips:
            new_in_use_servers, status = self.get_all_in_use_servers(
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
        self.add_remove_server("add", in_use_servers[0], "COLLECTOR",
                        "server_list", "config", "contrail-config-nodemgr")
        assert result, "Unexpected Connection"
    #end add_remove_collector_from_config
    
    @preposttest_wrapper
    def add_remove_redis_from_alarm_gen(self):
        '''
        Verify that on removing the entry from contail-alarm-gen.conf file 
        [REDIS] redis_uve_list section, the connection to that server is lost.
        Steps:
        1. Check the connections of contail-alarm-gen and REDIS.
        2. Remove the entry of in use server from all client .conf files
        3. Verify that removed server is not connected to any client.
        4. Add the entry back in all client .conf file as part of cleanup
        '''
        self.skip_if_setup_incompatible("analytic", 1, "analytic", 2)
        result = True
        in_use_servers, status = self.get_all_in_use_servers("redis" ,
                                        "analytic", "contrail-alarm-gen",
                                        self.inputs.collector_control_ips[0])
        self.add_remove_server("remove", in_use_servers[0], "REDIS",
                        "redis_uve_list", "analytic", "contrail-alarm-gen")
        for node in self.inputs.cfgm_control_ips:
            new_in_use_servers, status = self.get_all_in_use_servers(
                                            "redis", "analytic",
                                            "contrail-alarm-gen", node)
            if in_use_servers[0] in new_in_use_servers or 'Down' in status:
                self.logger.error("Connection unexpected. Either the server "
                                "removed from .conf file is still getting"
                                " used or the status of connection is down")
                result = False
            else:
                self.logger.info("Connections switched to other server after "
                                 "removal of entry in .conf file")
        self.add_remove_server("add", in_use_servers[0], "REDIS",
                        "redis_uve_list", "analytic", "contrail-alarm-gen")
        assert result, "Unexpected Connection"
    #end add_remove_redis_from_alarm_gen
    
    @preposttest_wrapper
    def collector_alarm_gen_connection_on_collector_restart(self):
        '''
        This test case verifies that on bringing down a Collector connected
        to contrail-alarm-gen, it should not take more than 40 seconds (TTL)
        to connect to a new Collector.
        Steps:
        1. Check the Collector to which contrail-alarm-gen is connected to.
        2. Stop that Collector service
        3. Check that contrail-alarm-gen switches to new collector within
           40 seconds which is the TTL time.
        4. Start the collector stopped in step 2.
        '''
        self.skip_if_setup_incompatible("analytic", 1, "analytic", 2)
        result = True
        in_use_servers, status = self.get_all_in_use_servers("collector" ,
                                        "analytic", "contrail-alarm-gen",
                                        self.inputs.collector_control_ips[0])
        self.inputs.stop_service("contrail-collector",[in_use_servers[0]])
        self.addCleanup(self.inputs.start_service,
                        "contrail-collector",[in_use_servers[0]])
        self.addCleanup(self.inputs.confirm_service_active, 
                        "contrail-collector",in_use_servers[0])
        for i in range(0,11):   # Testing for 50 seconds. 10 Seconds allowance from TTL
            new_in_use_servers, status = self.get_all_in_use_servers(
                                            "collector", "analytic",
                                            "contrail-alarm-gen", 
                                            self.inputs.collector_control_ips[0])
            if i == 10:
                self.logger.error("Connection to collector cannot be switched"
                                " to new server even after collector is down")
                result = False
                break
            if in_use_servers[0] in new_in_use_servers:
                self.logger.warn("Connection not switched to new collector")
                self.logger.warn("Waiting for 5 seconds")
                sleep(5)
            elif new_in_use_servers:
                self.logger.info("Connections switched to other collector")
                break
        assert result, "Unexpected Connection"
    #end collector_alarm_gen_connection_on_collector_restart

    @preposttest_wrapper
    def control_agent_connection_on_control_restart(self):
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
        in_use_servers, status = self.get_all_in_use_servers("xmpp" ,"agent", 
                                            "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        self.inputs.stop_service("contrail-control",[in_use_servers[0]])
        self.addCleanup(self.inputs.start_service,
                        "contrail-control",[in_use_servers[0]])
        self.addCleanup(self.inputs.confirm_service_active, 
                        "contrail-control",in_use_servers[0])
        sleep(15) # Agent retries to connect to previous Controller 4 times in an interval of 1,2,4,8 seconds
        new_in_use_servers, status = self.get_all_in_use_servers(
                                            "xmpp" ,"agent", 
                                            "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        if len(new_in_use_servers) == 2 and \
            in_use_servers[0] not in new_in_use_servers \
            and all(x == 'Up' for x in status):
            self.logger.info("Connections switched to other Controller")
        else:
            self.logger.error("Connection not switched to new collector")
            assert False, "Unexpected Connection"
    #end control_agent_connection_on_control_restart
    
    @preposttest_wrapper
    def dns_agent_connection_on_dns_restart(self):
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
        in_use_servers, status = self.get_all_in_use_servers("dns" ,"agent", 
                                            "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        self.inputs.stop_service("contrail-dns",[in_use_servers[0]])
        self.addCleanup(self.inputs.start_service,
                        "contrail-dns",[in_use_servers[0]])
        self.addCleanup(self.inputs.confirm_service_active, 
                        "contrail-dns",in_use_servers[0])
        sleep(15) # Agent retries to connect to previous DNS Server 4 times in an interval of 1,2,4,8 seconds
        new_in_use_servers, status = self.get_all_in_use_servers(
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
    #end dns_agent_connection_on_dns_restart
    
    @preposttest_wrapper
    def collector_agent_connection_on_collector_restart(self):
        '''
        This test case verifies that on bringing down a Collector connected
        to contrail-vrouter-agent, it should immediately switch to new Collector.
        Steps:
        1. Check the Collector to which contrail-vrouter-agent is connected to.
        2. Stop that Collector service
        3. Check that contrail-vrouter-agent immediately switches to new Collector.
        4. Start the Collector stopped in step 2.
        '''
        self.skip_if_setup_incompatible("agent", 1, "analytic", 2)
        in_use_servers, status = self.get_all_in_use_servers("collector" ,"agent", 
                                            "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        self.inputs.stop_service("contrail-collector",[in_use_servers[0]])
        self.addCleanup(self.inputs.start_service,
                        "contrail-collector",[in_use_servers[0]])
        self.addCleanup(self.inputs.confirm_service_active, 
                        "contrail-collector",in_use_servers[0])
        sleep(15) # Agent retries to connect to previous Collector 4 times in an interval of 1,2,4,8 seconds
        new_in_use_servers, status = self.get_all_in_use_servers(
                                            "collector" ,"agent", 
                                            "contrail-vrouter-agent",
                                            self.inputs.compute_control_ips[0])
        if in_use_servers[0] not in new_in_use_servers \
            and all(x == 'Up' for x in status):
            self.logger.info("Connections switched to other Collector")
        else:
            self.logger.error("Connection not switched to new Collector")
            assert False, "Unexpected Connection"
    #end collector_agent_connection_on_collector_restart
    
    @preposttest_wrapper
    def rabbitmq_control_connection_on_rabbitmq_restart(self):
        '''
        This test case verifies that on bringing down a rabbitMQ connected
        to contrail-control, it should immediately switch to new RabbitMQ server.
        Steps:
        1. Check the RabbitMQ Server to which contrail-control is connected to.
        2. Stop that RabbitMq service
        3. Check that contrail-control immediately switches to new RabbitMQ server.
        4. Start the  RabbitMQ server stopped in step 2.
        '''
        self.skip_if_setup_incompatible("control", 1, "config", 2)
        in_use_servers, status = self.get_all_in_use_servers("rabbitmq" ,
                                            "control", "contrail-control",
                                            self.inputs.bgp_control_ips[0])
        self.inputs.stop_service("rabbitmq-server",[in_use_servers[0]])
        self.addCleanup(self.inputs.start_service,
                        "rabbitmq-server",[in_use_servers[0]])
        self.addCleanup(self.inputs.confirm_service_active, 
                        "rabbitmq-server",in_use_servers[0])
        sleep(15)
        new_in_use_servers, status = self.get_all_in_use_servers("rabbitmq" ,
                                            "control", "contrail-control",
                                            self.inputs.bgp_control_ips[0])
        if in_use_servers[0] not in new_in_use_servers \
            and all(x == 'Up' for x in status):
            self.logger.info("Connections switched to other RabbitMQ Server")
        else:
            self.logger.error("Connection not switched to new RabbitMQ server")
            assert False, "Unexpected Connection"
    #end rabbitmq_control_connection_on_rabbitmq_restart
    
    @preposttest_wrapper
    def rabbitmq_dns_connection_on_rabbitmq_restart(self):
        '''
        This test case verifies that on bringing down a rabbitMQ connected
        to contrail-dns, it should immediately switch to new RabbitMQ server.
        Steps:
        1. Check the RabbitMQ Server to which contrail-dns is connected to.
        2. Stop that RabbitMq service
        3. Check that contrail-dns immediately switches to new RabbitMQ server.
        4. Start the  RabbitMQ server stopped in step 2.
        '''
        self.skip_if_setup_incompatible("control", 1, "config", 2)
        in_use_servers, status = self.get_all_in_use_servers("rabbitmq" ,
                                            "control", "contrail-dns",
                                            self.inputs.bgp_control_ips[0])
        self.inputs.stop_service("rabbitmq-server",[in_use_servers[0]])
        self.addCleanup(self.inputs.start_service,
                        "rabbitmq-server",[in_use_servers[0]])
        self.addCleanup(self.inputs.confirm_service_active, 
                        "rabbitmq-server",in_use_servers[0])
        sleep(15)
        new_in_use_servers, status = self.get_all_in_use_servers("rabbitmq" ,
                                            "control", "contrail-dns",
                                            self.inputs.bgp_control_ips[0])
        if in_use_servers[0] not in new_in_use_servers \
            and all(x == 'Up' for x in status):
            self.logger.info("Connections switched to other RabbitMQ Server")
        else:
            self.logger.error("Connection not switched to new RabbitMQ server")
            assert False, "Unexpected Connection"
    #end rabbitmq_dns_connection_on_rabbitmq_restart
