from common.sessionlogging.base import *
from tcutils.wrappers import preposttest_wrapper
import test
import random
from tcutils.util import skip_because

AF_TEST = 'v6'

class SessionLogging(SessionLoggingBase):

    @classmethod
    def setUpClass(cls):
        super(SessionLogging, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(SessionLogging, cls).tearDownClass()

    def _test_logging_intra_node(self):

        self._create_resources(test_type='intra-node')

        #For intra node traffic there is no tunnel so underlay_proto would be zero
        underlay_proto = 0
        proto_list = [1, 17, 6]
        self.enable_logging_on_compute(self.client_fixture.vm_node_ip,
            log_type=AGENT_LOG)
        #Clear local ips after agent restart
        self.client_fixture.clear_local_ips()
        self.server_fixture.clear_local_ips()
        #Verify Session logs in agent logs
        for proto in proto_list:
            self.start_traffic_validate_sessions(self.client_fixture,
                self.server_fixture, self.policy_fixture, proto=proto,
                underlay_proto=underlay_proto)
            self.logger.info("Expected Session logs found in agent log for "
                "protocol %s" % (proto))

        self.enable_logging_on_compute(self.client_fixture.vm_node_ip,
            log_type=SYS_LOG)
        #Clear local ips after agent restart
        self.client_fixture.clear_local_ips()
        self.server_fixture.clear_local_ips()
        #Verify Session logs in syslog
        for proto in proto_list:
            self.start_traffic_validate_sessions_in_syslog(self.client_fixture,
                self.server_fixture, self.policy_fixture, proto=proto,
                underlay_proto=underlay_proto)
            self.logger.info("Expected Session logs found in syslog for "
                "protocol %s" % (proto))

    def _test_logging_inter_node(self):

        self._create_resources(test_type='inter-node')

        underlay_proto = UNDERLAY_PROTO[
            self.connections.read_vrouter_config_encap()[0]]
        proto_list = [1, 17, 6]
        self.enable_logging_on_compute(self.client_fixture.vm_node_ip,
            log_type=AGENT_LOG)
        self.enable_logging_on_compute(self.server_fixture.vm_node_ip,
            log_type=AGENT_LOG)
        #Clear local ips after agent restart
        self.client_fixture.clear_local_ips()
        self.server_fixture.clear_local_ips()
        #Verify Session logs in agent logs
        for proto in proto_list:
            self.start_traffic_validate_sessions(self.client_fixture,
                self.server_fixture, self.policy_fixture, proto=proto,
                underlay_proto=underlay_proto)
            self.logger.info("Expected Session logs found in agent log for "
                "protocol %s" % (proto))

        self.enable_logging_on_compute(self.client_fixture.vm_node_ip,
            log_type=SYS_LOG)
        self.enable_logging_on_compute(self.server_fixture.vm_node_ip,
            log_type=SYS_LOG)
        #Clear local ips after agent restart
        self.client_fixture.clear_local_ips()
        self.server_fixture.clear_local_ips()
        #Verify Session logs in syslog
        for proto in proto_list:
            self.start_traffic_validate_sessions_in_syslog(self.client_fixture,
                self.server_fixture, self.policy_fixture, proto=proto,
                underlay_proto=underlay_proto)
            self.logger.info("Expected Session logs found in syslog for "
                "protocol %s" % (proto))

    @preposttest_wrapper
    def test_local_logging_intra_node(self):
        """
        Description: Verify sessions logged for inter-VN intra-Node traffic
        Steps:
            1. create 2 VNs and connect them using policy
            2. launch 1 VM in each VN on same compute node
            3. start icmp/tcp/udp traffic and verify the session logs in agent log
                as well as in syslog
        Pass criteria:
            step 3 should pass
        """
        self._test_logging_intra_node()

    @preposttest_wrapper
    def test_local_logging_inter_node(self):
        """
        Description: Verify sessions logged for inter-VN inter-Node traffic
        Steps:
            1. create 2 VNs and connect them using policy
            2. launch 1 VM in each VN on different compute nodes
            3. start icmp/tcp/udp traffic and verify the session logs in agent log
                as well as in syslog
        Pass criteria:
            step 3 should pass
        """
        self._test_logging_inter_node()

    @preposttest_wrapper
    def test_client_session_aggregation(self):
        """
        Description: Verify client sessions aggregation for tcp and udp
        """
        self._create_resources(test_type='inter-node', no_of_server=3)

        underlay_proto = UNDERLAY_PROTO[
            self.connections.read_vrouter_config_encap()[0]]

        self.enable_logging_on_compute(self.client_fixture.vm_node_ip,
            log_type=AGENT_LOG)
        self.enable_logging_on_compute(self.server_fixture.vm_node_ip,
            log_type=AGENT_LOG)
        #Clear local ips after agent restart
        for vm in self.client_fixtures + self.server_fixtures:
            vm.clear_local_ips()
        pkt_count = 100
        client_port = random.randint(12000, 65000)
        service_port = client_port + 1
        hping3_obj = {}
        traffic_stats = {}

        project_fqname = ':'.join(self.project.project_fq_name)
        client_vmi_fqname = project_fqname + ':' +\
            self.client_fixture.vmi_ids[self.client_fixture.vn_fq_name]
        server_vn_fq_name = self.server_fixture.vn_fq_name
        is_client_session = 1
        policy_api_obj = self.vnc_lib.network_policy_read(
            id=self.policy_fixture.get_id())
        nw_ace_uuid = policy_api_obj.get_network_policy_entries(
            ).policy_rule[0].rule_uuid

        interval = 1
        tcp_flags = 0
        for proto in [17, 6]:
            traffic_stats[proto] = {}
            hping3_obj[proto] = {}
            udp = True if proto == 17 else False
            #Start the traffic
            for idx, server in enumerate(self.server_fixtures):
                hping3_obj[proto][server] = self.send_hping3_traffic(
                    self.client_fixture, server.vm_ip, client_port+idx,
                    service_port, count=pkt_count, interval=interval,
                    wait=False, stop=False, udp=udp, keep=True)[0]

            if proto != 6:
                expected_client_session = SESSION_CLIENT_AGGR % (
                    client_vmi_fqname,#Client vmi name
                    self.client_fixture.vn_fq_name, FIREWALL_RULE_ID_DEFAULT,
                    server_vn_fq_name, is_client_session, 0,
                    self.client_fixture.vm_node_ip,
                    self.client_fixture.vm_ip, service_port, proto,#Session agg
                    INT_RE, INT_RE, INT_RE, INT_RE,
                    self.server_fixtures[0].vm_ip, client_port,#Server1
                    INT_RE, 1, UUID_RE, tcp_flags, INT_RE,#Fwd flow info
                    'pass', UUID_RE, nw_ace_uuid, INT_RE,
                    INT_RE, 1, UUID_RE, tcp_flags, INT_RE,#Reverse flow info
                    'pass', UUID_RE, nw_ace_uuid, INT_RE,
                    self.client_fixture.vm_id,#Client vm ID
                    self.server_fixtures[0].vm_node_ip, underlay_proto,
                    self.server_fixtures[1].vm_ip, client_port+1,#Server2
                    INT_RE, 1, UUID_RE, tcp_flags, INT_RE,#Fwd flow info
                    'pass', UUID_RE, nw_ace_uuid, INT_RE,
                    INT_RE, 1, UUID_RE, tcp_flags, INT_RE,#Reverse flow info
                    'pass', UUID_RE, nw_ace_uuid, INT_RE,
                    self.client_fixture.vm_id,
                    self.server_fixtures[1].vm_node_ip, underlay_proto,
                    self.server_fixtures[2].vm_ip, client_port+2,#Server3
                    INT_RE, 1, UUID_RE, tcp_flags, INT_RE,#Fwd flow info
                    'pass', UUID_RE, nw_ace_uuid, INT_RE,
                    INT_RE, 1, UUID_RE, tcp_flags, INT_RE,#Reverse flow info
                    'pass', UUID_RE, nw_ace_uuid, INT_RE,
                    self.client_fixture.vm_id,
                    self.server_fixtures[2].vm_node_ip, underlay_proto)

                #Verify session aggregation on client node
                result, output = self.search_session_in_agent_log(
                    self.client_fixture.vm_node_ip,
                    expected_client_session)
                assert result, ("Expected client session not found in agent log "
                    "for protocol %s" % (proto))

            #Stop the traffic
            for idx, server in enumerate(self.server_fixtures):
                traffic_stats[proto][server] = hping3_obj[proto][server].stop()[0]
            #Delete all the flows
            self.delete_all_flows_on_vms_compute(
                self.client_fixtures + self.server_fixtures)

            if proto == 6:
                pkt_count1 = pkt_count2 = pkt_count3 = 1
            else:
                pkt_count1 = traffic_stats[proto][self.server_fixtures[0]]['sent']
                pkt_count2 = traffic_stats[proto][self.server_fixtures[1]]['sent']
                pkt_count3 = traffic_stats[proto][self.server_fixtures[2]]['sent']

            expected_client_session = SESSION_CLIENT_AGGR_TEARDOWN % (
                client_vmi_fqname,
                self.client_fixture.vn_fq_name, FIREWALL_RULE_ID_DEFAULT,
                server_vn_fq_name, is_client_session, 0,
                self.client_fixture.vm_node_ip,
                self.client_fixture.vm_ip, service_port, proto,
                INT_RE, INT_RE, INT_RE, INT_RE,
                self.server_fixtures[0].vm_ip, client_port,
                UUID_RE, INT_RE, INT_RE, INT_RE, pkt_count1,
                'pass', UUID_RE, nw_ace_uuid,
                UUID_RE, INT_RE, INT_RE, INT_RE, pkt_count1,
                'pass', UUID_RE, nw_ace_uuid,
                self.client_fixture.vm_id,
                self.server_fixtures[0].vm_node_ip, underlay_proto,
                self.server_fixtures[1].vm_ip, client_port+1,
                UUID_RE, INT_RE, INT_RE, INT_RE, pkt_count2,
                'pass', UUID_RE, nw_ace_uuid,
                UUID_RE, INT_RE, INT_RE, INT_RE, pkt_count2,
                'pass', UUID_RE, nw_ace_uuid,
                self.client_fixture.vm_id,
                self.server_fixtures[1].vm_node_ip, underlay_proto,
                self.server_fixtures[2].vm_ip, client_port+2,
                UUID_RE, INT_RE, INT_RE, INT_RE, pkt_count3,
                'pass', UUID_RE, nw_ace_uuid,
                UUID_RE, INT_RE, INT_RE, INT_RE, pkt_count3,
                'pass', UUID_RE, nw_ace_uuid,
                self.client_fixture.vm_id,
                self.server_fixtures[2].vm_node_ip, underlay_proto)

            #Verify teardown session after deleting the flows
            result, output = self.search_session_in_agent_log(
                self.client_fixture.vm_node_ip,
                expected_client_session)

            if ((not result) and (proto == 6)):
                expected_client_session = SESSION_CLIENT_AGGR_TEARDOWN_TCP % (
                    client_vmi_fqname,
                    self.client_fixture.vn_fq_name, FIREWALL_RULE_ID_DEFAULT,
                    server_vn_fq_name, is_client_session, 0,
                    self.client_fixture.vm_node_ip,
                    self.client_fixture.vm_ip, service_port, proto,
                    INT_RE, INT_RE, INT_RE, INT_RE,
                    self.server_fixtures[0].vm_ip, client_port,#Server1
                    INT_RE, pkt_count1, UUID_RE, tcp_flags, INT_RE,#Fwd flow info
                    INT_RE, INT_RE, pkt_count1,
                    'pass', UUID_RE, nw_ace_uuid, INT_RE,
                    INT_RE, pkt_count1, UUID_RE, tcp_flags, INT_RE,#Reverse flow info
                    INT_RE, INT_RE, pkt_count1,
                    'pass', UUID_RE, nw_ace_uuid, INT_RE,
                    self.client_fixture.vm_id,
                    self.server_fixtures[0].vm_node_ip, underlay_proto,
                    self.server_fixtures[1].vm_ip, client_port+1,#Server2
                    INT_RE, pkt_count1, UUID_RE, tcp_flags, INT_RE,#Fwd flow info
                    INT_RE, INT_RE, pkt_count1,
                    'pass', UUID_RE, nw_ace_uuid, INT_RE,
                    INT_RE, pkt_count1, UUID_RE, tcp_flags, INT_RE,#Reverse flow info
                    INT_RE, INT_RE, pkt_count1,
                    'pass', UUID_RE, nw_ace_uuid, INT_RE,
                    self.client_fixture.vm_id,
                    self.server_fixtures[1].vm_node_ip, underlay_proto,
                    self.server_fixtures[2].vm_ip, client_port+2,#Server3
                    INT_RE, pkt_count1, UUID_RE, tcp_flags, INT_RE,#Fwd flow info
                    INT_RE, INT_RE, pkt_count1,
                    'pass', UUID_RE, nw_ace_uuid, INT_RE,
                    INT_RE, pkt_count1, UUID_RE, tcp_flags, INT_RE,#Reverse flow info
                    INT_RE, INT_RE, pkt_count1,
                    'pass', UUID_RE, nw_ace_uuid, INT_RE,
                    self.client_fixture.vm_id,
                    self.server_fixtures[2].vm_node_ip, underlay_proto)

                result_tcp, output = self.search_session_in_agent_log(
                    self.client_fixture.vm_node_ip,
                    expected_client_session)
                result = result or result_tcp

            assert result, ("Expected client session not found in agent log "
                "for protocol %s" % (proto))

            self.logger.info("Expected Session logs found in agent log for "
                "protocol %s" % (proto))

    @preposttest_wrapper
    def test_server_session_aggregation(self):
        """
        Description: Verify server sessions aggregation
        """
        self._create_resources(test_type='inter-node', no_of_client=3)

        underlay_proto = UNDERLAY_PROTO[
            self.connections.read_vrouter_config_encap()[0]]

        self.enable_logging_on_compute(self.client_fixture.vm_node_ip,
            log_type=AGENT_LOG)
        self.enable_logging_on_compute(self.server_fixture.vm_node_ip,
            log_type=AGENT_LOG)
        #Clear local ips after agent restart
        for vm in self.client_fixtures + self.server_fixtures:
            vm.clear_local_ips()
        pkt_count = 100
        client_port = random.randint(12000, 65000)
        service_port = client_port + 1
        hping3_obj = {}
        traffic_stats = {}

        project_fqname = ':'.join(self.project.project_fq_name)
        server_vmi_fqname = project_fqname + ':' +\
            self.server_fixture.vmi_ids[self.server_fixture.vn_fq_name]
        client_vn_fq_name = self.client_fixture.vn_fq_name
        is_client_session = 0
        policy_api_obj = self.vnc_lib.network_policy_read(
            id=self.policy_fixture.get_id())
        nw_ace_uuid = policy_api_obj.get_network_policy_entries(
            ).policy_rule[0].rule_uuid

        interval = 1
        tcp_flags = 0
        proto = 17
        traffic_stats[proto] = {}
        hping3_obj[proto] = {}
        udp = True if proto == 17 else False
        #Start the traffic
        for idx, client in enumerate(self.client_fixtures):
            hping3_obj[proto][client] = self.send_hping3_traffic(
                client, self.server_fixture.vm_ip, client_port+idx,
                service_port, count=pkt_count, interval=interval,
                wait=False, stop=False, udp=udp, keep=True)[0]

        expected_server_session = SESSION_SERVER_AGGR % (
            server_vmi_fqname,#Server vmi name
            self.server_fixture.vn_fq_name, FIREWALL_RULE_ID_DEFAULT,
            client_vn_fq_name, is_client_session, 0,
            self.server_fixture.vm_node_ip,
            self.server_fixture.vm_ip, service_port, proto,#Session agg
            INT_RE, INT_RE, INT_RE, INT_RE,
            self.client_fixtures[0].vm_ip, client_port,#Client1
            INT_RE, 1, UUID_RE, tcp_flags, INT_RE,#Fwd flow info
            'pass', UUID_RE, nw_ace_uuid, INT_RE,
            INT_RE, 1, UUID_RE, tcp_flags, INT_RE,#Reverse flow info
            'pass', UUID_RE, nw_ace_uuid, INT_RE,
            self.server_fixture.vm_id,#Server vm ID
            self.client_fixtures[0].vm_node_ip, underlay_proto,
            self.client_fixtures[1].vm_ip, client_port+1,#Client2
            INT_RE, 1, UUID_RE, tcp_flags, INT_RE,#Fwd flow info
            'pass', UUID_RE, nw_ace_uuid, INT_RE,
            INT_RE, 1, UUID_RE, tcp_flags, INT_RE,#Reverse flow info
            'pass', UUID_RE, nw_ace_uuid, INT_RE,
            self.server_fixture.vm_id,
            self.client_fixtures[1].vm_node_ip, underlay_proto,
            self.client_fixtures[2].vm_ip, client_port+2,#Client3
            INT_RE, 1, UUID_RE, tcp_flags, INT_RE,#Fwd flow info
            'pass', UUID_RE, nw_ace_uuid, INT_RE,
            INT_RE, 1, UUID_RE, tcp_flags, INT_RE,#Reverse flow info
            'pass', UUID_RE, nw_ace_uuid, INT_RE,
            self.server_fixture.vm_id,
            self.client_fixtures[2].vm_node_ip, underlay_proto)

        #Verify session aggregation on client node
        result, output = self.search_session_in_agent_log(
            self.server_fixture.vm_node_ip,
            expected_server_session)
        assert result, ("Expected server session not found in agent log "
            "for protocol %s" % (proto))

        #Stop the traffic
        for idx, client in enumerate(self.client_fixtures):
            traffic_stats[proto][client] = hping3_obj[proto][client].stop()[0]
        #Delete all the flows
        self.delete_all_flows_on_vms_compute(
            self.client_fixtures + self.server_fixtures)

        pkt_count1 = traffic_stats[proto][self.client_fixtures[0]]['sent']
        pkt_count2 = traffic_stats[proto][self.client_fixtures[1]]['sent']
        pkt_count3 = traffic_stats[proto][self.client_fixtures[2]]['sent']

        expected_server_session = SESSION_CLIENT_AGGR_TEARDOWN % (
            server_vmi_fqname,
            self.server_fixture.vn_fq_name, FIREWALL_RULE_ID_DEFAULT,
            client_vn_fq_name, is_client_session, 0,
            self.server_fixture.vm_node_ip,
            self.server_fixture.vm_ip, service_port, proto,
            INT_RE, INT_RE, INT_RE, INT_RE,
            self.client_fixtures[0].vm_ip, client_port,
            UUID_RE, INT_RE, INT_RE, INT_RE, pkt_count1,
            'pass', UUID_RE, nw_ace_uuid,
            UUID_RE, INT_RE, INT_RE, INT_RE, pkt_count1,
            'pass', UUID_RE, nw_ace_uuid,
            self.server_fixture.vm_id,
            self.client_fixtures[0].vm_node_ip, underlay_proto,
            self.client_fixtures[1].vm_ip, client_port+1,
            UUID_RE, INT_RE, INT_RE, INT_RE, pkt_count2,
            'pass', UUID_RE, nw_ace_uuid,
            UUID_RE, INT_RE, INT_RE, INT_RE, pkt_count2,
            'pass', UUID_RE, nw_ace_uuid,
            self.server_fixture.vm_id,
            self.client_fixtures[1].vm_node_ip, underlay_proto,
            self.client_fixtures[2].vm_ip, client_port+2,
            UUID_RE, INT_RE, INT_RE, INT_RE, pkt_count3,
            'pass', UUID_RE, nw_ace_uuid,
            UUID_RE, INT_RE, INT_RE, INT_RE, pkt_count3,
            'pass', UUID_RE, nw_ace_uuid,
            self.server_fixture.vm_id,
            self.client_fixtures[2].vm_node_ip, underlay_proto)

        #Verify teardown session after deleting the flows
        result, output = self.search_session_in_agent_log(
            self.server_fixture.vm_node_ip,
            expected_server_session)
        assert result, ("Expected server session not found in agent log "
            "for protocol %s" % (proto))

        self.logger.info("Expected Session logs found in agent log for "
            "protocol %s" % (proto))

class SessionLoggingIpv6(SessionLogging):
    @classmethod
    def setUpClass(cls):
        super(SessionLoggingIpv6, cls).setUpClass()
        cls.inputs.set_af(AF_TEST)

    def is_test_applicable(self):
        if (self.inputs.orchestrator == 'vcenter') and (
            not self.orch.is_feature_supported('ipv6')):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)

    @preposttest_wrapper
    @skip_because(address_family = 'v6')
    def test_client_session_aggregation(self):
        '''
        This test uses hping3 utils which does not support ipv6, so need to skip
        '''
        super(SessionLoggingIpv6, self).test_client_session_aggregation()

    @preposttest_wrapper
    @skip_because(address_family = 'v6')
    def test_server_session_aggregation(self):
        '''
        This test uses hping3 utils which does not support ipv6, so need to skip
        '''
        super(SessionLoggingIpv6, self).test_server_session_aggregation()
