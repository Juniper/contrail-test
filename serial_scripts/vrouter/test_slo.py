from common.slo.base import *
from tcutils.wrappers import preposttest_wrapper
import test
from tcutils.util import get_random_name, is_almost_same, skip_because
from security_group import get_secgrp_id_from_name, list_sg_rules
import random

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
            step 4 should pass
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
        slo_rate = 1
        slo_fixture = self.create_slo(parent_obj, rate=slo_rate, sg_obj=sg_obj,
            vn_policy_obj=policy_obj)
        for vn in self.vn_fixtures:
            self.add_slo_to_vn(slo_fixture, vn)

        #For intra node traffic there is no tunnel so underlay_proto would be zero
        underlay_proto = 0
        proto_list = [1, 17, 6]
        self.enable_logging_on_compute(self.client_fixture.vm_node_ip,
            log_type=AGENT_LOG, session_type='slo')
        #Clear local ips after agent restart
        self.client_fixture.clear_local_ips()
        self.server_fixture.clear_local_ips()

        #Verify Session logs in agent logs for SLO
        for proto in proto_list:
            self.start_traffic_validate_slo(self.client_fixture,
                self.server_fixture, self.policy_fixture, proto=proto,
                underlay_proto=underlay_proto, slo_rate=slo_rate)
            self.logger.info("SLO: Expected Session logs found in agent log for "
                "protocol %s" % (self.proto))
        #
        #SLO logged session verification in syslog
        self.enable_logging_on_compute(self.client_fixture.vm_node_ip,
            log_type=SYS_LOG, session_type='slo')
        #Clear local ips after agent restart
        self.client_fixture.clear_local_ips()
        self.server_fixture.clear_local_ips()

        #Verify Session logs in syslog
        for proto in proto_list:
            self.start_traffic_validate_slo_in_syslog(self.client_fixture,
                self.server_fixture, self.policy_fixture, proto=proto,
                underlay_proto=underlay_proto)
            self.logger.info("Expected Session logs found in syslog for "
                "protocol %s" % (self.proto))

    @preposttest_wrapper
    def test_slo_inter_node(self):
        """
        Description: Verify security logging for inter-VN inter-Node traffic
        Steps:
            1. create 2 VNs and connect them using policy
            2. launch 1 VM in each VN on diff compute node
            3. set session export rate to 0
            4. start icmp/tcp/udp traffic and verify the session logs in agent log
        Pass criteria:
            step 4 should pass
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
        slo_rate = 1
        slo_fixture = self.create_slo(parent_obj, rate=slo_rate, sg_obj=sg_obj,
            vn_policy_obj=policy_obj)
        for vn in self.vn_fixtures:
            self.add_slo_to_vn(slo_fixture, vn)

        underlay_proto = UNDERLAY_PROTO[
            self.connections.read_vrouter_config_encap()[0]]
        proto_list = [1, 17, 6]
        self.enable_logging_on_compute(self.client_fixture.vm_node_ip,
            log_type=AGENT_LOG, session_type='slo')
        self.enable_logging_on_compute(self.server_fixture.vm_node_ip,
            log_type=AGENT_LOG, session_type='slo')
        #Clear local ips after agent restart
        self.client_fixture.clear_local_ips()
        self.server_fixture.clear_local_ips()

        #Verify Session logs in agent logs for SLO
        for proto in proto_list:
            self.start_traffic_validate_slo(self.client_fixture,
                self.server_fixture, self.policy_fixture, proto=proto,
                underlay_proto=underlay_proto, slo_rate=slo_rate, sg_uuid=sg_id)
            self.logger.info("SLO: Expected Session logs found in agent log for "
                "protocol %s" % (self.proto))

    @preposttest_wrapper
    def test_slo_rate(self):
        """
        Description: Verify security logging rate for inter/intra node traffic
        Steps:
            1. create 2 VNs and connect them using policy
            2. launch 1 VM in each VN on diff compute node
            3. set session export rate to 0 and SLO rate to 5
            4. send 10 ping packets and verify the no. of session logs in agent log
        Pass criteria:
            No. of session logs should be 1 for session creation and 1 for teardown
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
        slo_rate = 5
        slo_fixture = self.create_slo(parent_obj, rate=slo_rate,
            vn_policy_obj=policy_obj)
        for vn in self.vn_fixtures:
            self.add_slo_to_vn(slo_fixture, vn)

        underlay_proto = 0
        proto = 1
        self.enable_logging_on_compute(self.client_fixture.vm_node_ip,
            log_type=AGENT_LOG, session_type='slo')
        #Clear local ips after agent restart
        self.client_fixture.clear_local_ips()
        self.server_fixture.clear_local_ips()

        #Verify Session logs in agent logs for SLO
        self.start_traffic_validate_slo(self.client_fixture,
            self.server_fixture, self.policy_fixture, proto=proto,
            underlay_proto=underlay_proto, slo_rate=slo_rate,
            exp_session_count=2)
        self.logger.info("SLO: Expected Session logs found in agent log for "
            "protocol %s" % (self.proto))

        ##
        #Verify SLO rate for inter node icmp traffic
        compute_hosts = self.orch.get_hosts()
        if not (len(compute_hosts) < 2):
            client_node_ip = self.client_fixture.vm_node_ip
            server2_node_name = compute_hosts[1] if self.inputs.compute_info[
                compute_hosts[1]] != client_node_ip else compute_hosts[0]

            server2_fixture = self.create_vms(vn_fixture=self.vn2_fixture,
                count=1, node_name=server2_node_name, image_name='ubuntu-traffic')[0]
            self.verify_vms([server2_fixture])

            self.enable_logging_on_compute(server2_fixture.vm_node_ip,
                log_type=AGENT_LOG, session_type='slo')
            #Clear local ips after agent restart
            server2_fixture.clear_local_ips()

            underlay_proto = UNDERLAY_PROTO[
                self.connections.read_vrouter_config_encap()[0]]
            #Verify Session logs in agent logs for SLO
            self.start_traffic_validate_slo(self.client_fixture,
                server2_fixture, self.policy_fixture, proto=proto,
                underlay_proto=underlay_proto, slo_rate=slo_rate, sg_uuid=sg_id,
                exp_session_count=2)
            self.logger.info("SLO: Expected Session logs found in agent log for "
                "protocol %s" % (self.proto))

class SecurityLoggingFw(SloBase, SessionLoggingFwBase):

    @classmethod
    def setUpClass(cls):
        super(SecurityLoggingFw, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(SecurityLoggingFw, cls).tearDownClass()

    def _test_slo_with_fw(self, exp_srv_session_count=None,
            exp_clnt_session_count=None, create_resources=True, slo_fixture=None,
            fw_objs_dict=None):

        if create_resources:
            self._create_resources(test_type='inter-node', session_export_rate=0)

        policy_obj = self.policy_fixture.policy_obj
        project_name = self.project.project_name
        sg_fq_name = '%s:%s:default' % (self.connections.domain_name,
            project_name)
        sg_id = get_secgrp_id_from_name(self.connections, sg_fq_name)
        sg_obj = self.vnc_h._vnc.security_group_read(id=sg_id)

        parent_obj = self.vnc_h.project_read(
            fq_name=[self.connections.domain_name, project_name])
        slo_rate = 1
        if slo_fixture is None:
            slo_fixture = self.create_slo(parent_obj, rate=slo_rate)
            for vn in self.vn_fixtures:
                self.add_slo_to_vn(slo_fixture, vn)

        if fw_objs_dict is None:
            #create firewall rule and policy
            slo_rate_obj = SloRateType(rate=slo_rate)
            slo_dict = {'slo_obj': slo_fixture.obj, 'rate_obj':slo_rate_obj}
            fw_objs_dict = self.config_tag_firewall_policy(self.vn_fixtures, slo=slo_dict)

        underlay_proto = UNDERLAY_PROTO[
            self.connections.read_vrouter_config_encap()[0]]
        proto_list = [17]
        self.enable_logging_on_compute(self.client_fixture.vm_node_ip,
            log_type=AGENT_LOG, session_type='slo')
        self.enable_logging_on_compute(self.server_fixture.vm_node_ip,
            log_type=AGENT_LOG, session_type='slo')
        #Clear local ips after agent restart
        self.client_fixture.clear_local_ips()
        self.server_fixture.clear_local_ips()

        #Verify Session logs in agent logs for SLO
        for proto in proto_list:
            self.start_traffic_validate_slo_fw(self.client_fixture,
                self.server_fixture, self.policy_fixture, proto=proto,
                underlay_proto=underlay_proto, slo_rate=slo_rate, sg_uuid=sg_id,
                fw_objs_dict=fw_objs_dict,
                exp_srv_session_count=exp_srv_session_count,
                exp_clnt_session_count=exp_clnt_session_count)
            self.logger.info("SLO: Expected Session logs found in agent log for "
                "protocol %s" % (self.proto))

        return {'sg_obj':sg_obj, 'slo_fix':slo_fixture, 'fw_objs':fw_objs_dict}

    @preposttest_wrapper
    def test_slo_on_vmi(self):
        """
        Description: Verify SLO on vmi
        Steps:
            1. create 2 VNs and connect them using network and firewall policy
            2. launch 1 VM in each VN on diff compute node
            3. set session export rate to 0 and attach SLO to dest vmi only
            4. start udp traffic and verify the session logs in agent log on dest node
                and no logs in src node
        Pass criteria:
            step 4 should pass
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
        slo_rate = 1
        slo_fixture = self.create_slo(parent_obj, rate=slo_rate, sg_obj=sg_obj,
            vn_policy_obj=policy_obj)
        server_vmi_id = list(self.server_fixture.get_vmi_ids().values())[0]
        self.add_slo_to_vmi(slo_fixture, server_vmi_id)

        #create firewall rule and policy
        slo_rate_obj = SloRateType(rate=slo_rate)
        slo_dict = {'slo_obj': slo_fixture.obj, 'rate_obj':slo_rate_obj}
        fw_objs_dict = self.config_tag_firewall_policy(self.vn_fixtures, slo=slo_dict)

        underlay_proto = UNDERLAY_PROTO[
            self.connections.read_vrouter_config_encap()[0]]
        proto_list = [17]
        self.enable_logging_on_compute(self.client_fixture.vm_node_ip,
            log_type=AGENT_LOG, session_type='slo')
        self.enable_logging_on_compute(self.server_fixture.vm_node_ip,
            log_type=AGENT_LOG, session_type='slo')
        #Clear local ips after agent restart
        self.client_fixture.clear_local_ips()
        self.server_fixture.clear_local_ips()

        #Verify Session logs in agent logs for SLO
        for proto in proto_list:
            self.start_traffic_validate_slo_fw(self.client_fixture,
                self.server_fixture, self.policy_fixture, proto=proto,
                underlay_proto=underlay_proto, slo_rate=slo_rate, sg_uuid=sg_id,
                fw_objs_dict=fw_objs_dict, exp_clnt_session_count=0)
            self.logger.info("SLO: Expected Session logs found in agent log for "
                "protocol %s" % (self.proto))

    @preposttest_wrapper
    def test_slo_global(self):
        """
        Description: Verify global security logging for inter-VN inter-Node traffic
            with firewall policy and rules
        Steps:
            1. disable/enable global SLO flag and verify logging
            2. Create global and tenant level SLO and verify logging
            3. Delete global SLO and verify session get logged only matching tenant level SLO
        Pass criteria:
            All logging verifications should pass
        """
        self.set_global_slo_flag(enable=False)
        #Logged session should be 0 when global slo is disabled
        created_objs = self._test_slo_with_fw(exp_srv_session_count=0,exp_clnt_session_count=0)

        self.set_global_slo_flag(enable=True)
        #Logged session should be seen when global slo is enabled
        self._test_slo_with_fw(create_resources=False,
            slo_fixture=created_objs['slo_fix'],
            fw_objs_dict=created_objs['fw_objs'])

        eth_type = 'IPv4' if (self.inputs.get_af() == 'v4') else 'IPv6'
        proto_str = 'any'
        sg_rule_id_ingress = list_sg_rules(self.connections,
            created_objs['sg_obj'].uuid,
            eth_type=eth_type, proto=proto_str, direction='ingress')[0]['id']
        sg_rule_id_egress = list_sg_rules(self.connections,
            created_objs['sg_obj'].uuid,
            eth_type=eth_type, proto=proto_str, direction='egress')[0]['id']

        #Create global SLO using sg_rule_id_ingress
        slo_rate = 10
        rules_list = [{'uuid':sg_rule_id_ingress, 'rate':100}]
        g_slo_fixture = self.create_slo(rate=slo_rate, rules_list=rules_list)

        #Remove old slo from VNs
        for vn in self.vn_fixtures:
            vn.set_slo_list([])

        #Create tenant level SLO with sg_rule_id_egress and add to VNs
        project_name = self.project.project_name
        parent_obj = self.vnc_h.project_read(
            fq_name=[self.connections.domain_name, project_name])
        rules_list = [{'uuid':sg_rule_id_egress, 'rate':1}]
        slo_fixture = self.create_slo(parent_obj, rate=slo_rate, rules_list=rules_list)
        for vn in self.vn_fixtures:
            self.add_slo_to_vn(slo_fixture, vn)
        #With tenant level SLO created above, Client session will match and logged
        #With global SLO, server session will match and logged
        self._test_slo_with_fw(create_resources=False,
            slo_fixture=slo_fixture, fw_objs_dict=created_objs['fw_objs'])

        #Disable global slo again
        self.set_global_slo_flag(enable=False)
        #Now no logging should happen
        self._test_slo_with_fw(create_resources=False,
            slo_fixture=slo_fixture, fw_objs_dict=created_objs['fw_objs'],
            exp_srv_session_count=0, exp_clnt_session_count=0)

        #Enable global slo again
        self.set_global_slo_flag(enable=True)
        #Delete global SLO
        g_slo_fixture.cleanUp()
        self._remove_fixture_from_cleanup(g_slo_fixture)
        #Now only Client session should get logged matching tenant level SLO
        #Server session should be 0 as it will match ingress rule
        self._test_slo_with_fw(create_resources=False,
            exp_srv_session_count=0,
            slo_fixture=slo_fixture, fw_objs_dict=created_objs['fw_objs'])

    @preposttest_wrapper
    def test_slo_fw_update(self):
        """
        Description: Verify security logging for inter-VN inter-Node traffic
            with firewall policy and rules and verify SLO update
        Steps:
            1. create 2 VNs and connect them using network and firewall policy
            2. launch 1 VM in each VN on diff compute node
            3. set session export rate to 0
            4. start udp traffic and verify the session logs in agent log
        Pass criteria:
            step 4 should pass
        """
        created_objs = self._test_slo_with_fw()

        eth_type = 'IPv4' if (self.inputs.get_af() == 'v4') else 'IPv6'
        proto_str = 'any'
        sg_rule_id_ingress = list_sg_rules(self.connections,
            created_objs['sg_obj'].uuid,
            eth_type=eth_type, proto=proto_str, direction='ingress')[0]['id']
        sg_rule_id_egress = list_sg_rules(self.connections,
            created_objs['sg_obj'].uuid,
            eth_type=eth_type, proto=proto_str, direction='egress')[0]['id']

        #Remove old slo from VNs
        for vn in self.vn_fixtures:
            vn.set_slo_list([])

        #Create tenant level SLO with sg_rule_id_egress and add to VNs
        project_name = self.project.project_name
        parent_obj = self.vnc_h.project_read(
            fq_name=[self.connections.domain_name, project_name])
        rules_list = [{'uuid':sg_rule_id_egress, 'rate':1}]
        slo_fixture = self.create_slo(parent_obj, rate=10, rules_list=rules_list)

        for vn in self.vn_fixtures:
            self.add_slo_to_vn(slo_fixture, vn)
        #With tenant level SLO created above, Client session will match and logged
        self._test_slo_with_fw(create_resources=False,
            slo_fixture=slo_fixture, fw_objs_dict=created_objs['fw_objs'],
            exp_srv_session_count=0)

        #Update SLO with both rules
        rules_list.append({'uuid':sg_rule_id_ingress, 'rate':1})
        self.update_slo(slo_fixture.obj, rules_list)

        #Now both client and server sessions should get logged
        self._test_slo_with_fw(create_resources=False,
            slo_fixture=slo_fixture, fw_objs_dict=created_objs['fw_objs'])

class SecurityLoggingIpv6(SecurityLogging):
    @classmethod
    def setUpClass(cls):
        super(SecurityLoggingIpv6, cls).setUpClass()
        cls.inputs.set_af(AF_TEST)

    def is_test_applicable(self):
        if (self.inputs.orchestrator == 'vcenter') and (
            not self.orch.is_feature_supported('ipv6')):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)

class SecurityLoggingFwIpv6(SecurityLoggingFw):
    @classmethod
    def setUpClass(cls):
        super(SecurityLoggingFwIpv6, cls).setUpClass()
        cls.inputs.set_af(AF_TEST)

    def is_test_applicable(self):
        if (self.inputs.orchestrator == 'vcenter') and (
            not self.orch.is_feature_supported('ipv6')):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)
