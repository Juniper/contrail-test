from time import sleep
import math
from common.servicechain.config import ConfigSvcChain
from tcutils.commands import ssh, execute_cmd, execute_cmd_out


class VerifySvcMirror(ConfigSvcChain):

    def start_tcpdump(self, session, tap_intf):
        pcap = '/tmp/mirror-%s.pcap' % tap_intf
        cmd = "tcpdump -ni %s udp port 8099 -w %s" % (tap_intf, pcap)
        self.logger.info("Staring tcpdump to capture the mirrored packets.")
        execute_cmd(session, cmd, self.logger)
        return pcap

    def stop_tcpdump(self, session, pcap):
        self.logger.info("Waiting for the tcpdump write to complete.")
        sleep(30)
        cmd = 'kill $(pidof tcpdump)'
        execute_cmd(session, cmd, self.logger)
        cmd = 'tcpdump -r %s | wc -l' % pcap
        out, err = execute_cmd_out(session, cmd, self.logger)
        count = int(out.strip('\n'))
        cmd = 'rm -f %s' % pcap
        execute_cmd(session, cmd, self.logger)
        return count

    def tcpdump_on_analyzer(self, si_prefix):
        sessions = {}
        svm_name = si_prefix + '_1'
        host = self.get_svm_compute(svm_name)
        tapintf = self.get_svm_tapintf(svm_name)
        session = ssh(host['host_ip'], host['username'], host['password'])
        pcap = self.start_tcpdump(session, tapintf)
        sessions.update({svm_name: (session, pcap)})

        return sessions

    def verify_mirror(self, svm_name, session, pcap):
        mirror_pkt_count = self.stop_tcpdump(session, pcap)
        errmsg = "Packets not mirrored to the analyzer VM %s," % (svm_name)
        if mirror_pkt_count == 0:
            self.logger.error(errmsg)
            return [False, errmsg]
        self.logger.info("%s packets are mirrored to the analyzer "
                         "service VM '%s'", mirror_pkt_count, svm_name)

        return [True, None]


def get_flow_data(
        config_topo,
        src_vm_name,
        dst_vm_name,
        proto,
        src_proj,
        dst_proj):
    '''Flows can be of following types:
    i. intra-VN, intra-Node
    ii. intra-VN, inter-Node
    iii. inter-VN, intra-Node, by policy
    iv. inter-VN, inter-node, by policy
    v. inter-VN, intra-Node, by FIP
    vi. inter-VN, inter-Node, by FIP
    Need to consider these in preparing flow data...
    Fields to be used for populating flow data:
    src_ip, dst_ip, protocol, src_vrf, dst_vrf [can be same or different based on node]
    if src/dst in different vn, need 2 flows with different src_vrf.
    if src/dst are connected by FIP, need 2 flows with different pair of IPs..
        fwd_flow: src_ip->dst_ip, reverse_flow: fip_ip->src_ip
    Sample:
       236<=>521432       10.3.1.2:1809             10.4.1.6:9100     17 (3->2)
            (K(nh):31, Action:N(S), S(nh):31,  Statistics:3311/423808)

       260<=>500380       10.4.1.6:9100            10.5.1.10:3306     17 (2->3)
            (K(nh):19, Action:N(D), S(nh):19,  Statistics:0/0)

       276                10.4.1.6:9100            10.5.1.10:4149     17 (2)
            (K(nh):19, Action:D(FlowLim), S(nh):19,  Statistics:0/0)
    '''
    proto_map = {'icmp': 1, 1: 1, 'udp': 17, 17: 17, 'tcp': 6, 6: 6}
    src_vm_fixture = config_topo[src_proj]['vm'][src_vm_name]
    dst_vm_fixture = config_topo[dst_proj]['vm'][dst_vm_name]
    src_vm_vn_name = src_vm_fixture.vn_names[0]
    dst_vm_vn_name = dst_vm_fixture.vn_names[0]
    src_vm_vn_fixt = config_topo[src_proj]['vn'][src_vm_vn_name]
    dst_vm_vn_fixt = config_topo[dst_proj]['vn'][dst_vm_vn_name]
    src_vm_node_ip = src_vm_fixture.vm_ip
    dst_vm_node_ip = dst_vm_fixture.vm_ip
    src_vrf = src_vm_fixture.get_vrf_id(
        src_vm_vn_fixt.vn_fq_name,
        src_vm_vn_fixt.vrf_name)
    if src_vm_fixture.vm_node_ip == dst_vm_fixture.vm_node_ip:
        dst_vrf = src_vm_fixture.get_vrf_id(
            dst_vm_vn_fixt.vn_fq_name,
            dst_vm_vn_fixt.vrf_name)
    else:
        dst_vrf = dst_vm_fixture.get_vrf_id(
            dst_vm_vn_fixt.vn_fq_name,
            dst_vm_vn_fixt.vrf_name)
    fip_flow = False
    src_vm_in_dst_vn_fip = src_vm_fixture.chk_vmi_for_fip(
        dst_vm_vn_fixt.vn_fq_name)
    if src_vm_in_dst_vn_fip is not None:
        fip_flow = True
    if fip_flow:
        # For FIP case, always get dst_vrf from src node
        dst_vrf = src_vm_fixture.get_vrf_id(
            dst_vm_vn_fixt.vn_fq_name,
            dst_vm_vn_fixt.vrf_name)
        # inter-VN, connected by fip scenario, vrf trnslation happens only in
        # this case
        f_flow = {'src_ip': src_vm_node_ip, 'dst_ip': dst_vm_node_ip,
                  'proto': proto_map[proto], 'vrf': src_vrf}
        r_flow = {'src_ip': dst_vm_node_ip, 'dst_ip': src_vm_in_dst_vn_fip,
                  'proto': proto_map[proto], 'vrf': dst_vrf}
        return [f_flow, r_flow]
    else:
        # intra-VN scenario
        if src_vm_vn_name == dst_vm_vn_name:
            f_flow = {'src_ip': src_vm_node_ip, 'dst_ip': dst_vm_node_ip,
                      'proto': proto_map[proto], 'vrf': src_vrf}
            return [f_flow]
        else:
            # inter-VN, connected by policy scenario
            f_flow = {'src_ip': src_vm_node_ip, 'dst_ip': dst_vm_node_ip,
                      'proto': proto_map[proto], 'vrf': src_vrf}
            r_flow = {'src_ip': dst_vm_node_ip, 'dst_ip': src_vm_node_ip,
                      'proto': proto_map[proto], 'vrf': dst_vrf}
            return [f_flow, r_flow]
# end get_flow_data


def vm_vrouter_flow_count(self):
    cmd = 'flow -l | grep Action | grep -E "F|N" | wc -l '
    result = ''
    output = self.inputs.run_cmd_on_server(
        self.vm_node_ip, cmd, self.inputs.host_data[
            self.vm_node_ip]['username'], self.inputs.host_data[
            self.vm_node_ip]['password'])
    for s in output:
        if s.isdigit():
            result = result + s

    return int(result)
# end vm_vrouter_flow_count


def get_max_flow_removal_time(generated_flows, flow_cache_timeout):
    '''Based on total flows in the node & flow_cache_timeout'''
    max_stats_pass_interval = 1000
    num_entries_inspected_per_stats_pass = (
        max_stats_pass_interval * generated_flows) / (1000 * flow_cache_timeout)
    num_passes_needed_for_total_flows = generated_flows / \
        num_entries_inspected_per_stats_pass
    time_to_complete_all_passes = num_passes_needed_for_total_flows * \
        max_stats_pass_interval
    flow_removal_time_in_secs = time_to_complete_all_passes / 1000
    return flow_removal_time_in_secs
# end get_max_flow_removal_time


def update_vm_mdata_ip(compute_node, self):
    '''Once vrouter service is restarted in compute_node, update VM metadata IPs
    '''
    if 'project_list' in dir(self.topo):
        self.projectList = self.topo.project_list
    else:
        self.projectList = [self.inputs.project_name]
    for project in self.projectList:
        vm_fixtures = self.config_topo[project]['vm']
        for name, vm_fixt in vm_fixtures.items():
            if vm_fixt.vm_node_data_ip == compute_node:
                vm_fixt.wait_till_vm_is_up()
        # end for vm fixture
     # end for project


def verify_node_flow_setup(self):
    '''Written for agent params test to test flow setup data
    generated_flows: generated by tool
    allowed_flows: set by max_vm_flows value in agent conf
    expected_flows: expected non FlowLimited flows based on above 2 values
    '''
    self.flow_data = get_flow_data(
        self.config_topo,
        self.src_vm,
        self.dst_vm,
        self.proto,
        self.src_proj,
        self.dst_proj)
    self.logger.info(
        "Received flow_data for checking: %s" %
        self.flow_data)
    self.comp_node_fixt[
        self.cmp_node].get_vrouter_flow_count()
    # keep generated flow info for processing flow removal
    allowed_flows = int(
        float(self.max_system_flows) * (float(self.max_vm_flows) / 100))
    self.logger.info(
        "In node %s, allowed_flows is set to %s" %
        (self.cmp_node, allowed_flows))
    if self.generated_flows < allowed_flows:
        expected_flows = self.generated_flows
        # assert if flows_beyond_limit found, as we don't expect to see
        flow_limit_assert = False
    else:
        expected_flows = allowed_flows
        # don't assert if flows_beyond_limit found, as we expect to see
        flow_limit_assert = True
    node_flow_data = self.comp_node_fixt[
        self.cmp_node].get_vrouter_matching_flow_count(self.flow_data)
    actual_flows = int(node_flow_data['allowed'])
    retries = 0
    retry_wait_time = 2
    max_retries = math.ceil(self.generated_flows / self.flow_gen_rate)
    while retries < max_retries and actual_flows < expected_flows:
        self.logger.info(
            "Wait for flows to be setup completely, flows so far: %s, expected: %s" %
            (actual_flows, expected_flows))
        sleep(retry_wait_time)
        retries += 1
        node_flow_data = self.comp_node_fixt[
            self.cmp_node].get_vrouter_matching_flow_count(self.flow_data)
        actual_flows = int(node_flow_data['allowed'])
    diff_flows = actual_flows - expected_flows
    # allow 5% diff on upper side..
    allowed_upper_threshold = expected_flows * 0.05
    if diff_flows > allowed_upper_threshold:
        msg = "Seeing more flows in system than expected - node: "
        msg = msg + "%s, expected_flows: %s, actual_flows: %s" % (
            self.cmp_node, expected_flows, actual_flows)
        self.reset_vm_flow_limit_and_stop_traffic()
        assert False, msg
    # allow 5% diff on lower side..
    allowed_lower_threshold = expected_flows * 0.05
    if diff_flows < -allowed_lower_threshold:
        msg = "Don't see expected flows in node "
        msg = msg + "%s, expected_flows: %s, actual_flows: %s" % (
            self.cmp_node, expected_flows, actual_flows)
        self.reset_vm_flow_limit_and_stop_traffic()
        assert False, msg
    else:
        self.logger.info(
            "Flow count good as configured.., expected %s, actual %s" %
            (expected_flows, actual_flows))
    # If generated_flows < allowed_flows, flows_beyond_limit is not
    # expected..
    flows_beyond_limit = int(node_flow_data['dropped_by_limit'])
    if flows_beyond_limit > 0:
        msg = "Seeing dropped flows due to FlowLimit in system than "
        msg = msg + "expected - node: %s, flows_beyond_limit: " % self.cmp_node
        msg = msg + "%s, allowed_flows: %s" % (
            flows_beyond_limit, allowed_flows)
        assert flow_limit_assert, msg
    else:
        self.logger.info(
            "Dont see Flow Limited Dropped flows as expected, flow limited drop count is %s.." %
            flows_beyond_limit)

# end verify_node_flow_setup
