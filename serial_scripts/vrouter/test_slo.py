from tcutils.wrappers import preposttest_wrapper
from common.slo.base import *
import test
from tcutils.util import get_random_name
from security_group import get_secgrp_id_from_name

AF_TEST = 'v6'

class SecurityLogging(SloBase):

    @classmethod
    def setUpClass(cls):
        super(SecurityLogging, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(SecurityLogging, cls).tearDownClass()

    @preposttest_wrapper
    def test_slo_intra_node(self):
        """
        Description: Verify security logging for inter-VN intra-Node traffic
        Steps:
            1. create 2 VNs and connect them using policy
            2. launch 1 VM in each VN on same compute node
            3. set session export rate to 0
            4. start icmp/tcp/udp traffic and verify the session logs in agent log
                as well as in syslog
        Pass criteria:
            step 3 should pass
        """
        self._create_resources(test_type='intra-node', session_export_rate=0)

        policy_obj = self.policy_fixture.policy_obj
        project_name = self.project.project_name
        sg_fq_name = '%s:%s:default' % (self.connections.domain_name,
            project_name)
        sg_id = get_secgrp_id_from_name(self.connections, sg_fq_name)
        sg_obj = self.vnc_h._vnc.security_group_read(id=sg_id)

        parent_obj = self.vnc_h.project_read(
            fq_name=[self.connections.domain_name, project_name])
        slo_rate = 10
        slo_fixture = self.create_slo(parent_obj, rate=slo_rate, sg_obj=sg_obj,
            vn_policy_obj=policy_obj)
        for vn in self.vn_fixtures:
            self.add_slo_to_vn(slo_fixture, vn)

        #For intra node traffic there is no tunnel so underlay_proto would be zero
        underlay_proto = 0
        #<TBD for tcp>proto_list = [1, 17, 6]
        proto_list = [1, 17]
        self.enable_logging_on_compute(self.client_fixture.vm_node_ip,
            log_type=AGENT_LOG)
        #Clear local ips after agent restart
        self.client_fixture.clear_local_ips()
        self.server_fixture.clear_local_ips()

        #Verify Session logs in agent logs for SLO
        for proto in proto_list:
            self.start_traffic_validate_slo(self.client_fixture,
                self.server_fixture, self.policy_fixture, proto=proto,
                underlay_proto=underlay_proto, slo_rate=slo_rate)
            self.logger.info("SLO: Expected Session logs found in agent log for "
                "protocol %s" % (proto))
        #<TBD for syslog>

    @preposttest_wrapper
    def test_slo_inter_node(self):
        """
        Description: Verify security logging for inter-VN inter-Node traffic
        Steps:
            1. create 2 VNs and connect them using policy
            2. launch 1 VM in each VN on diff compute node
            3. set session export rate to 0
            4. start icmp/tcp/udp traffic and verify the session logs in agent log
                as well as in syslog
        Pass criteria:
            step 3 should pass
        """
        self._create_resources(test_type='inter-node', session_export_rate=0)

        policy_obj = self.policy_fixture.policy_obj
        project_name = self.project.project_name
        sg_fq_name = '%s:%s:default' % (self.connections.domain_name,
            project_name)
        sg_id = get_secgrp_id_from_name(self.connections, sg_fq_name)
        sg_obj = self.vnc_h._vnc.security_group_read(id=sg_id)

        parent_obj = self.vnc_h.project_read(
            fq_name=[self.connections.domain_name, project_name])
        slo_rate = 10
        slo_fixture = self.create_slo(parent_obj, rate=slo_rate, sg_obj=sg_obj,
            vn_policy_obj=policy_obj)
        for vn in self.vn_fixtures:
            self.add_slo_to_vn(slo_fixture, vn)

        underlay_proto = UNDERLAY_PROTO[
            self.connections.read_vrouter_config_encap()[0]]
        proto_list = [1, 17]
        self.enable_logging_on_compute(self.client_fixture.vm_node_ip,
            log_type=AGENT_LOG)
        #Clear local ips after agent restart
        self.client_fixture.clear_local_ips()
        self.server_fixture.clear_local_ips()

        #Verify Session logs in agent logs for SLO
        for proto in proto_list:
            self.start_traffic_validate_slo(self.client_fixture,
                self.server_fixture, self.policy_fixture, proto=proto,
                underlay_proto=underlay_proto, slo_rate=slo_rate, sg_uuid=sg_id)
            self.logger.info("SLO: Expected Session logs found in agent log for "
                "protocol %s" % (proto))
