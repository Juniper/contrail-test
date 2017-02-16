import re
from tcutils.util import Lock
from tcutils.util import is_almost_same

from common.neutron.base import BaseNeutronTest
from compute_node_test import ComputeNodeFixture
from qos_fixture import QosForwardingClassFixture, QosConfigFixture, QosQueueFixture
from collections import OrderedDict

from tcutils.traffic_utils.traffic_analyzer import TrafficAnalyzer
from tcutils.traffic_utils.scapy_traffic_gen import ScapyTraffic
from tcutils.traffic_utils.hping_traffic import Hping3
from tcutils.traffic_utils.iperf3_traffic import Iperf3

from time import sleep
from netaddr import *

from svc_instance_fixture import SvcInstanceFixture
from svc_template_fixture import SvcTemplateFixture
from policy_test import PolicyFixture
from vn_policy_test import VN_Policy_Fixture

from tcutils.contrail_status_check import *

class QosTestBase(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(QosTestBase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(QosTestBase, cls).tearDownClass()
    # end tearDownClass

    def setup_queues(self, queues_list):
        queue_fixtures = []
        for queue_dict in queues_list:
            queue_dict['connections'] = self.connections
            queue_fixture = self.useFixture(
                            QosQueueFixture(**queue_dict))
            queue_fixtures.append(queue_fixture)
        return queue_fixtures
    # end 

    def setup_fcs(self, fcs_list):
        fc_fixtures = []
        for fc_dict in fcs_list:
            fc_dict['connections'] = self.connections
            self.logger.debug("FC Dict is %s" % fc_dict)
            fc_fixture = self.useFixture(
                            QosForwardingClassFixture(**fc_dict))
            fc_fixtures.append(fc_fixture)
        return fc_fixtures
    # end 

    def setup_qos_config(self, name=None, dscp_map={}, dot1p_map={}, exp_map={},
                          **kwargs):
        ''' Helper to add and delete qos-config and forwarding-class objects
        '''
        qos_config_fixture = self.useFixture(QosConfigFixture(name=name,
                                             dscp_mapping=dscp_map,
                                             dot1p_mapping=dot1p_map,
                                             exp_mapping=exp_map,
                                             connections=self.connections,
                                             **kwargs))
        return qos_config_fixture
    # end setup_qos_config 

    def setup_qos_config_on_vmi(self, qos_fixture, vmi_uuid):
        ret_val = qos_fixture.apply_to_vmi(vmi_uuid)
        self.addCleanup(qos_fixture.remove_from_vmi, vmi_uuid)
        return ret_val
    # end setup_qos_config_on_vmi

    def remove_qos_config_on_vmi(self, qos_fixture, vmi_uuid):
        self.remove_from_cleanups(qos_fixture.remove_from_vmi, vmi_uuid)
        return qos_fixture.remove_from_vmi(vmi_uuid)

    def setup_qos_config_on_vn(self, qos_fixture, vn_uuid):
        ret_val = qos_fixture.apply_to_vn(vn_uuid)
        self.addCleanup(qos_fixture.remove_from_vn, vn_uuid)
        return ret_val
    # end setup_qos_config_on_vn

    def remove_qos_config_on_vn(self, qos_fixture, vn_uuid):
        self.remove_from_cleanups(qos_fixture.remove_from_vn, vn_uuid)
        return qos_fixture.remove_from_vn(vn_uuid)

    def delete_qos_config(self, qos_fixture):
        qos_fixture.cleanUp()
        self.remove_from_cleanups(qos_fixture.cleanUp)
    # end delete_qos_config
    
    def validate_packet_qos_marking(self,
                                    src_vm_fixture,
                                    dest_vm_fixture,
                                    traffic_generator = "hping",
                                    dest_ip=None,
                                    count=10000,
                                    dscp=None,
                                    dot1p=None,
                                    exp=None,
                                    protocol='udp',
                                    src_port=None,
                                    dest_port=None,
                                    src_compute_fixture=None,
                                    expected_dscp=None,
                                    expected_dot1p=None,
                                    expected_exp=None,
                                    encap = None,
                                    vrf_id = None,
                                    queue_id = None,
                                    traffic_duration = 5,
                                    min_expected_pkts = 0,
                                    af = "ipv4",
                                    **kwargs):
        '''
            dest_compute_fixture should be supplied if underlay traffic is 
            being checked
            dest_vm_fixture should be supplied if traffic is being checked for a
            specific estination VM
            
            Few things to note:
            1. traffic_generator can be "scapy" or "hping"
            2. "scapy" is specifically used here to test l2 and IPv6 traffic only.
               For all other traffic, hping is being used.
            3. If queue_id is not None, then it do not validate  content of packets.
                It just verify the count of packets through a queue. It use 
                "min_expected_pkts" to verify minimum packets transmitted.
        '''
        interval = kwargs.get('interval', 1) # interval in seconds
        src_mac = kwargs.get('src_mac', "11:22:33:44:55:66")
        dst_mac = kwargs.get('dst_mac', "ff:ff:ff:ff:ff:ff")
        ipv6_src = kwargs.get('ipv6_src', None)
        ipv6_dst = kwargs.get('ipv6_dst', None)
        src_vm_cidr = src_vm_fixture.vn_objs[0]['network']\
                        ['contrail:subnet_ipam'][0]['subnet_cidr']
        dest_vm_cidr = dest_vm_fixture.vn_objs[0]['network']\
                        ['contrail:subnet_ipam'][0]['subnet_cidr']
        if IPNetwork(src_vm_cidr) == IPNetwork(dest_vm_cidr):
            traffic_between_diff_networks = False
        else:
            traffic_between_diff_networks = True
        #src_vm_interface = kwargs.get('src_vm_interface', "eth0")
        # TCP is anyway the default for hping3
        icmp = False; tcp = False; udp = False
        if protocol == 'icmp': icmp = True
        if protocol == 'udp': udp = True
        if isinstance(dscp,int):
            tos = format(dscp << 2, 'x')
        else:
            tos = None
        if not src_compute_fixture and src_vm_fixture:
            src_compute_fixture = self.useFixture(ComputeNodeFixture(
                                        self.connections,
                                        src_vm_fixture.vm_node_ip))
        username = self.inputs.host_data[src_compute_fixture.ip]['username']
        password = self.inputs.host_data[src_compute_fixture.ip]['password']
        interface = src_compute_fixture.agent_physical_interface
        src_ip = src_vm_fixture.vm_ip
        dest_ip = dest_ip or dest_vm_fixture.vm_ip
        if queue_id != None:
            cmd = "for i in `ls /sys/class/net/%s/queues/tx*/xps_cpus`;do echo 0 > $i;done"\
                     % interface
            self.inputs.run_cmd_on_server(src_vm_fixture.vm_node_ip, cmd )
        if traffic_generator == "scapy":
            self.logger.debug("Generating L2 only stream and ignoring all"
                              " other parameters of layers above L2")
            dot1p = dot1p or 0
            ether = {'src':src_mac, 'dst':dst_mac}
            dot1q = {'prio':dot1p, 'vlan':100}
            ipv6 = {}
            udp_header = {}
            if af == "ipv6":
                tos = int(tos,16) if dscp else 0
                ipv6 = {'tc':tos, 'src':ipv6_src, 'dst':ipv6_dst}
                ## WA for Bug 1614472. Internal protocol inside IPv6 is must
                udp_header = {'sport' : 1234}
            offset =156 if ipv6 else 100
            traffic_obj, scapy_obj = self._generate_scapy_traffic(
                                                        src_vm_fixture, 
                                                        src_compute_fixture,
                                                        interface,
                                                        encap = encap, 
                                                        interval=interval,
                                                        count=count, 
                                                        ether = ether,
                                                        dot1q = dot1q,
                                                        ipv6 = ipv6,
                                                        udp = udp_header)
            if queue_id == None:
                session,pcap = traffic_obj.packet_capture_start(
                                    capture_on_payload = True,
                                    signature_string ='5a5a5a5a5a5a5a5a',
                                    offset = offset,
                                    bytes_to_match = 8,
                                    min_length = 100,
                                    max_length = 250)
            else:
                init_pkt_count = self.get_queue_count(src_vm_fixture.vm_node_ip,
                                                      interface, queue_id)
        elif traffic_generator == "hping":
            if interval != 1:
                interval = 'u' + str(interval*1000000)
            traffic_obj, hping_obj = self._generate_hping_traffic(
                                                        src_vm_fixture,
                                                        src_compute_fixture,
                                                        interface,
                                                        dest_ip =dest_ip,
                                                        src_port = src_port,
                                                        dest_port = dest_port,
                                                        encap = encap,
                                                        interval = interval,
                                                        count = count,
                                                        proto = protocol,
                                                        vrf_id = vrf_id,
                                                        udp = udp,
                                                        tos = tos)
            if queue_id == None:
                session,pcap = traffic_obj.packet_capture_start(
                                    traffic_between_diff_networks =
                                     traffic_between_diff_networks)
            else:
                init_pkt_count = self.get_queue_count(src_vm_fixture.vm_node_ip,
                                                      interface, queue_id)
        sleep(traffic_duration)
        if queue_id == None:
            traffic_obj.packet_capture_stop()
        else:
            sleep(1) # Additional wait for stats to be updated.
            final_pkt_count = self.get_queue_count(src_vm_fixture.vm_node_ip,
                                                      interface, queue_id)
            assert self.match_traffic(init_pkt_count, final_pkt_count, min_expected_pkts)
            return True
        if traffic_generator == "scapy":
            scapy_obj.stop()
        elif traffic_generator == "hping":
            (stats, hping_log) = hping_obj.stop()
        if isinstance(expected_dscp,int):
            result = traffic_obj.verify_packets('dscp',
                                                pcap_path_with_file_name = pcap,
                                                expected_count=1,
                                                dscp=expected_dscp)
            assert result, 'DSCP remarking checks failed. Please check logs'
        if isinstance(expected_dot1p,int):
            result = traffic_obj.verify_packets('dot1p',
                                                pcap_path_with_file_name = pcap,
                                                expected_count=1,
                                                dot1p=expected_dot1p)
            assert result, '802.1p remarking checks failed. Please check logs'
        if isinstance(expected_exp,int):
            result = traffic_obj.verify_packets('exp',
                                                pcap_path_with_file_name = pcap,
                                                expected_count=1,
                                                mpls_exp=expected_exp)
            assert result, 'MPLS exp remarking checks failed. Please check logs'
        self.inputs.run_cmd_on_server(src_compute_fixture.ip, "rm %s" % pcap)
        return True
    # end validate_packet_qos_marking
    
    def validate_queue_performance(self,
                            src_vn1_vm1_fixture,
                            src_vn2_vm1_fixture,
                            dest_vn1_vm2_fixture,
                            dest_vn2_vm2_fixture,
                            queue_types,
                            bandwidth= '7G',
                            protocol = 'udp',
                            time = 60,
                            interval = 1,
                            dscp_vn1_traffic=None,
                            dscp_vn2_traffic=None,
                            queue_id_vn1_traffic = None,
                            queue_id_vn2_traffic = None,
                            strict_queue_id = None,
                            traffic_duration = 5,
                            min_expected_pkts = 5000,
                            expected_ratio_q1_q2 = 1.0):
        '''
        This function starts full rate traffic using iperf3 utility.
        It verifies if traffic is flowing thorugh desired queues.
        It also verifies bandwidth and strictness values.
        
        This function starts 2 parallel streams of iperf3 traffic
        to congest the egress port.
        After creating congestion, it verifies for the BW and strictness 
        behavior
        
        Set queue_type = rr (If traffic between 2 rr queues)
                             In this case expected_ratio_q1_q2 need to be updated
                       = strict (If traffic between 2 strict queues)
                       = strcit_rr (If traffic between a strict and a rr queue)  
                             In this case strict_queue_id need to be updated
                             Other queue will be assumed as Round robin
        
        Note that iperf3 has some limitations.
        Some times when 2 parallel stream of high Bandwidth (7-10G) are started,
        one of the iperf3 stream do not get initiated until the first one completes.
        This result in wrong results.
        Thus, we have come up to a number as "7G" where we the chances of other stream 
        not getting started are less.
        '''
        if protocol == 'udp':
            udp = True
        if isinstance(dscp_vn1_traffic,int):
            tos_vn1 = '0x' + format(dscp_vn1_traffic << 2, 'x')
        else:
            tos_vn1 = False
        if isinstance(dscp_vn2_traffic,int):
            tos_vn2 = '0x' + format(dscp_vn2_traffic << 2, 'x')
        else:
            tos_vn2 = False
        src_compute_fixture = self.useFixture(ComputeNodeFixture(
                                        self.connections,
                                        src_vn1_vm1_fixture.vm_node_ip))
        interface = src_compute_fixture.agent_physical_interface
        self.logger.debug("Generating iperf traffic")
        init_q_drops_vn1_traffic = self.get_queue_drop_count(
                                            src_vn1_vm1_fixture.vm_node_ip,
                                            interface,
                                            queue_id_vn1_traffic)
        init_q_drops_vn2_traffic = self.get_queue_drop_count(
                                            src_vn2_vm1_fixture.vm_node_ip,
                                            interface,
                                            queue_id_vn2_traffic)
        iperf_stream1_obj = self._generate_iperf_traffic(
                                                src_vn1_vm1_fixture, 
                                                dest_vn1_vm2_fixture,
                                                bandwidth = bandwidth,
                                                udp = udp,
                                                time=time,
                                                tos = tos_vn1,
                                                port = 5203)
        iperf_stream2_obj = self._generate_iperf_traffic(
                                                src_vn2_vm1_fixture, 
                                                dest_vn2_vm2_fixture,
                                                bandwidth = bandwidth,
                                                udp = udp,
                                                time=time,
                                                tos = tos_vn2,
                                                port = 5204)
        init_stream1_pkts = self.get_queue_count(src_vn1_vm1_fixture.vm_node_ip,
                                                interface, queue_id_vn1_traffic)
        init_stream2_pkts = self.get_queue_count(src_vn2_vm1_fixture.vm_node_ip,
                                                interface, queue_id_vn2_traffic)
        sleep(traffic_duration)
        final_stream1_pkts = self.get_queue_count(src_vn1_vm1_fixture.vm_node_ip,
                                                  interface, queue_id_vn1_traffic)
        final_stream2_pkts = self.get_queue_count(src_vn2_vm1_fixture.vm_node_ip,
                                                  interface, queue_id_vn2_traffic)
        iperf_stream1_obj.stop()
        iperf_stream2_obj.stop()
        final_q_drops_vn1_traffic = self.get_queue_drop_count(
                                            src_vn1_vm1_fixture.vm_node_ip,
                                            interface,
                                            queue_id_vn1_traffic)
        final_q_drops_vn2_traffic = self.get_queue_drop_count(
                                            src_vn2_vm1_fixture.vm_node_ip,
                                            interface,
                                            queue_id_vn2_traffic)
        # Below match_traffic just ensures that traffic is passing through desired queue.
        assert self.match_traffic(init_stream1_pkts, final_stream1_pkts,
                                  min_expected_pkts)
        assert self.match_traffic(init_stream2_pkts, final_stream2_pkts,
                                  min_expected_pkts)
        queue_drops_vn1_traffic = final_q_drops_vn1_traffic - \
                                    init_q_drops_vn1_traffic
        self.logger.debug("Drops in queue for VN1 traffic %d"
                               % queue_drops_vn1_traffic)
        queue_drops_vn2_traffic = final_q_drops_vn2_traffic - \
                                    init_q_drops_vn2_traffic
        self.logger.debug("Drops in queue for VN2 traffic %d"
                               % queue_drops_vn2_traffic)
        if queue_types == "rr":
            traffic_ratio = float(final_stream1_pkts - init_stream1_pkts)/\
                            float(final_stream2_pkts - init_stream2_pkts)
            self.logger.debug("Ratio of traffic is %f" % traffic_ratio)
            compare_values = is_almost_same(expected_ratio_q1_q2, traffic_ratio,
                                 threshold_percent=10, num_type=float)
            if compare_values:
                self.logger.info("Ratio of traffic between 2 round robin queues "
                                "was as expected")
            else:
                self.logger.error("Ratio of traffic between 2 round robin queues "
                                "was not as expected")
                return False
            if queue_drops_vn1_traffic > 0 and queue_drops_vn2_traffic > 0:
                self.logger.info("Both the queues have dropped counters as expected")
        elif queue_types == "strict":
            if queue_id_vn1_traffic > queue_id_vn2_traffic:
                if queue_drops_vn1_traffic == 0 and queue_drops_vn2_traffic > 1000:
                    self.logger.info("Queue for VN1 traffic got priority over queue"
                                     "for VN2 traffic")
                else:
                    self.logger.error("Strictness not maintained between 2 PGs with"
                                      "scheduling set to Strict")
                    return False
            elif queue_id_vn2_traffic > queue_id_vn1_traffic:
                if queue_drops_vn2_traffic == 0 and queue_drops_vn1_traffic > 1000:
                    self.logger.info("Queue for VN2 traffic got priority over queue"
                                     "for VN1 traffic")
                else:
                    self.logger.error("Strictness not maintained between 2 PGs with"
                                      "scheduling set to Strict")
                    return False
        elif queue_types == "strict_rr":
            if queue_id_vn1_traffic == strict_queue_id:
                if queue_drops_vn1_traffic == 0 and queue_drops_vn2_traffic > 1000:
                    self.logger.info("Queue for VN1 traffic got priority over queue"
                                     "for VN2 traffic")
                else:
                    self.logger.error("Strictness not maintained between 2 PGs with"
                                      "scheduling set to Strict")
                    return False
            elif queue_id_vn2_traffic == strict_queue_id:
                if queue_drops_vn2_traffic == 0 and queue_drops_vn1_traffic > 1000:
                    self.logger.info("Queue for VN2 traffic got priority over queue"
                                     "for VN1 traffic")
                else:
                    self.logger.error("Strictness not maintained between 2 PGs with"
                                      "scheduling set to Strict")
                    return False
        return True
    # end validate_queue_performance
    
    def _generate_scapy_traffic(self, src_vm_fixture, src_compute_fixture,
                                interface, encap = None, username = None,
                                password = None, interval=1, count=1, **kwargs):
        params = {}
        params['ether'] = kwargs.get('ether',{})
        params['dot1q'] = kwargs.get('dot1q',{})
        params['ip'] = kwargs.get('ip',{})
        params['ipv6'] = kwargs.get('ipv6',{})
        params['tcp'] = kwargs.get('tcp',{})
        params['udp'] = kwargs.get('udp',{})
        username = username or self.inputs.host_data[
                                    src_compute_fixture.ip]['username']
        password = password or self.inputs.host_data[
                                    src_compute_fixture.ip]['password']
        scapy_obj = ScapyTraffic(src_vm_fixture,
                                   interval= interval,
                                   count = count,
                                   **params)
        scapy_obj.start()
        traffic_obj = TrafficAnalyzer(interface,
                                    src_compute_fixture,
                                    username,
                                    password,
                                    logger=self.logger,
                                    encap_type = encap)
        return traffic_obj, scapy_obj
    
    def _generate_hping_traffic(self, src_vm_fixture, src_compute_fixture,
                                interface, dest_ip =None, src_port = None,
                                dest_port = None, encap = None, username = None,
                                password = None, interval=1, count=1,
                                vrf_id = None, proto = None, **kwargs):
        udp = kwargs.get('udp', False)
        tos = kwargs.get('tos', None)
        username = username or self.inputs.host_data[
                                    src_compute_fixture.ip]['username']
        password = password or self.inputs.host_data[
                                    src_compute_fixture.ip]['password']
        src_ip = src_vm_fixture.vm_ip
        hping_obj = Hping3(src_vm_fixture,
                             dest_ip,
                             destport=dest_port,
                             baseport=src_port,
                             count=count,
                             interval=interval,
                             udp=udp,
                             tos=tos,
                             keep=True,
                             numeric=True)
        hping_obj.start(wait=kwargs.get('wait', False))
        sleep(5)
        if encap == "MPLSoGRE":
            traffic_obj = TrafficAnalyzer(interface,
                                          src_compute_fixture,
                                          username,
                                          password,
                                          src_ip=src_ip,
                                          dest_ip=dest_ip,
                                          logger=self.logger,
                                          encap_type = encap)
        else:
            fwd_flow,rev_flow = src_compute_fixture.get_flow_entry(
                                    source_ip=src_ip,
                                    dest_ip=dest_ip,
                                    proto=proto,
                                    source_port=src_port,
                                    dest_port=dest_port,
                                    vrf_id=vrf_id)
            if not fwd_flow or not rev_flow:
                self.logger.error('Flow not created. Cannot proceed with analysis')
                return False
            src_port1 = fwd_flow.dump()['underlay_udp_sport']
            if src_port1 == '0':
                self.logger.error('Flow does not seem active..something is '
                                'wrong. Cannot proceed')
                self.logger.debug('Fwd flow :%s, Rev flow: %s' % (
                                fwd_flow.dump(), rev_flow.dump()))
                return False
            traffic_obj = TrafficAnalyzer(interface,
                                          src_compute_fixture,
                                          username,
                                          password,
                                          src_port=src_port1,
                                          protocol='udp',
                                          logger=self.logger,
                                          encap_type = encap)
        return traffic_obj, hping_obj
    
    def _generate_iperf_traffic(self, src_vm_fixture, dst_vm_fixture,
                                **kwargs):
        params = OrderedDict()
        params["port"] = kwargs.get('port', 4203)
        params["bandwidth"]  = kwargs.get('bandwidth', '1G')     
        params["udp"] = kwargs.get('udp', True)
        if params["udp"] == True:
            params["length"] = kwargs.get('length', 65507)
        else:
            params["length"] = kwargs.get('length', 1048576)
        params["time"] = kwargs.get('time', 10)
        params["tos"] = kwargs.get('tos', None)
        iperf_obj = Iperf3( src_vm_fixture,
                            dst_vm_fixture,
                            **params)
        iperf_obj.start(wait=kwargs.get('wait', False))
        return iperf_obj

    def update_policy_qos_config(self, policy_fixture, qos_config_fixture, 
                                 operation = "add", entry_index =0):
        policy_entry = policy_fixture.policy_obj['policy']['entries']
        new_policy_entry = policy_entry
        if operation == "add":
            qos_obj_fq_name_str = self.vnc_lib.qos_config_read(
                                    id = qos_config_fixture.uuid).\
                                    get_fq_name_str()
            new_policy_entry['policy_rule'][entry_index]['action_list']\
                            ['qos_action'] = qos_obj_fq_name_str
        elif operation == "remove":
            new_policy_entry['policy_rule'][entry_index]['action_list']\
                            ['qos_action'] = ''
        policy_id = policy_fixture.policy_obj['policy']['id']
        policy_data = {'policy': {'entries': new_policy_entry}}
        policy_fixture.update_policy(policy_id, policy_data)
    
    def update_sg_qos_config(self, sg_fixture, qos_config_fixture, 
                             operation = "add"):
        sg_object = self.vnc_lib.security_group_read(id = sg_fixture.get_uuid())
        sg_rules = sg_object.get_security_group_entries().policy_rule
        if operation == "add":
            qos_obj_fq_name_str = self.vnc_lib.qos_config_read(
                                    id = qos_config_fixture.uuid).\
                                    get_fq_name_str()
            for elem in sg_rules:
                elem.action_list=ActionListType(qos_action=qos_obj_fq_name_str)
        elif operation == "remove":
            for elem in sg_rules:
                elem.action_list.qos_action = None
        sg_entries = sg_object.get_security_group_entries()
        sg_entries.set_policy_rule(sg_rules)
        sg_object.set_security_group_entries(sg_entries)
        self.vnc_lib.security_group_update(sg_object)
        
    def configure_fc_list_dynamically(self, queue_fixtures):
        ''' Read queue_fixtures and dynamically create FC list 
            Also returns the corresponding logical ids list'''
        fcs = []
        logical_ids = []
        for count in range(len(queue_fixtures)):
            fc_id = count + 1
            dscp = count
            if count > 7 or count == 0:
                dot1p_exp = 0
            dot1p, exp = dot1p_exp, dot1p_exp
            dot1p_exp += 1
            fc_dict = {'fc_id': fc_id, 'dscp': dscp, 'dot1p': dot1p,
                       'exp': exp, 'queue_uuid' : queue_fixtures[count].uuid}
            fcs.append(fc_dict)
            logical_ids.append(queue_fixtures[count].queue_id)
        return fcs, logical_ids
    
    def configure_map_dynamically(self, map_type, fcs):
        ''' Read fc list and dynamically create dscp/dot1p/exp map 
            map_type is either of "dscp", "dot1p" or "exp"'''
        map = {}
        if map_type == "dscp":
            value = 63
        elif map_type == "dot1p" or map_type == "exp":
            value = 7
        i = 0
        while 1:
            if i >= len(fcs) or value < 0:
                break
            fc_id = fcs[i]['fc_id']
            map.update({value : fc_id})
            i = i + 1
            value = value - 1
        return map
    
    @classmethod
    def get_qos_queue_params(cls, node_ip):
        '''
        This method will populate multi queueing interface, it's speed and 
        number of queue supported
        '''
        # Searching for fabric interface on which to test queuing
        cmd = 'cat /etc/contrail/contrail-vrouter-agent.conf \
               | grep "physical_interface=" | grep -v "vmware"'
        output = cls.inputs.run_cmd_on_server(node_ip, cmd, container='agent')
        fabric_interface = output.split('=')[-1]
        # Getting the speed of the interface
        cmd= 'ethtool %s | grep "Speed"' % fabric_interface
        output = cls.inputs.run_cmd_on_server(node_ip, cmd)
        interface_speed = output.split(' ')[-1]
        # Getting the number of Hardware queues
        cmd = 'ls -la /sys/class/net/%s/queues/ | grep "tx" | wc -l'\
                 % fabric_interface
        output = cls.inputs.run_cmd_on_server(node_ip, cmd)
        queue_count = output.split(' ')[-1]
        return (fabric_interface, interface_speed, queue_count)
    
    def get_configured_queue_mapping(self, node_ip):
        '''
        This method will populate list of HW queues.
        It also populates list of logical queues. Note that logical queue ID 
        list only contains first element. eg, if logical_queue=[1, 6-10, 12-15] 
        for any single HW queue ,it picks only first element "1".
        
        hw_queues = [3, 11, 18, 28, 36, 43, 53, 61]
        logical_ids = [1, 40, 70, 115, 140, 175, 180, 245]
        '''
        hw_queues = []
        logical_ids = []
        default_queue = 0
        for elem in self.inputs.qos_queue:
            if elem[0] == node_ip:
                map = elem[1]
        for hw_to_logical_value in map:
            hw_queues.append(int(hw_to_logical_value.keys()[0]))
            if 'default' in hw_to_logical_value.values()[0]:
                default_queue = int(hw_to_logical_value.keys()[0])
            if hw_to_logical_value.values()[0][0] != 'default':
                logical_id = int(hw_to_logical_value.values()[0][0].split('-')[0])
                logical_ids.append(logical_id)
        return (hw_queues, logical_ids, default_queue)
    
    def get_all_configured_logical_ids(self, node_ip):
        '''
        This method will populate list logical queues.
        This proc populates all logical ids for a particular HW queue
        '''
        logical_ids = []
        for elem in self.inputs.qos_queue:
            if elem[0] == node_ip:
                map = elem[1]
        for hw_to_logical_value in map:
            if 'default' in hw_to_logical_value.values()[0]:
                hw_to_logical_value.values()[0].remove('default')
            for elem in hw_to_logical_value.values()[0]:
                if '-' not in elem:
                    logical_ids.append(int(elem))
                else:
                    elem = elem.split('-')
                    for integers in range(int(elem[0]), int(elem[1])+1):
                        logical_ids.append(integers)
        return logical_ids

    @classmethod
    def pick_nodes(cls):
        ''' Based on qos queue configurations present in the testbed file,
            it pick the first and the 2nd node to test.
            Priority is given to a node having 10G interface over a 1G interface node'''
        cls.qos_node_ip = ""
        for elem in cls.inputs.qos_queue:
            cls.qos_node_ip = elem[0]
            cls.queue_params = cls.get_qos_queue_params(cls.qos_node_ip)
            if cls.queue_params[1] == "10000Mb/s":
                first_node_interface_bw = cls.queue_params[1]
                break
            else:
                first_node_interface_bw = "1000Mb/s"
        try:
            first_node_name = cls.inputs.host_data[cls.qos_node_ip]['name']
        except:
            first_node_name = cls.inputs.compute_names[0]
            first_node_interface_bw = "1000Mb/s"
        for elem in cls.inputs.compute_ips:
            if elem != cls.qos_node_ip and cls.qos_node_ip!= '':
                second_node_ip = elem
                break
            else:
                second_node_ip = cls.inputs.compute_ips[1]
        second_node_name = cls.inputs.host_data[second_node_ip]['name']
        return first_node_name, second_node_name, first_node_interface_bw

    def get_queue_count(self, node_ip, interface, queue_id):
        cmd = 'ethtool -S %s | grep tx_queue_%d_packets' % \
                (interface, queue_id)
        output = self.inputs.run_cmd_on_server(node_ip, cmd)
        packets = int(output.split(' ')[-1])
        self.logger.debug("Number of packets in queue %d is %d" 
                          % (queue_id, packets))
        return packets

    def get_queue_drop_count(self, node_ip, interface, queue_id):
        non_index_queue_id = queue_id + 1
        hex_queue_id = hex(non_index_queue_id).strip('0x')
        cmd = 'tc -s class show dev %s| grep "class mq :%s " -A 1' % \
                 (interface, hex_queue_id)
        output = self.inputs.run_cmd_on_server(node_ip, cmd)
        obj = re.search("(.*)[dropped ](.*?),(.*)", output.split('\n')[1])
        dropped_count = int(obj.group(2))
        self.logger.debug("Number of dropped packets in queue %d are %d"
                          % (queue_id, dropped_count))
        return dropped_count

    def get_hw_queue_from_fc_id(self, fc_id, fcs, logical_ids):
        # Matching the fc_id in list of fcs and taking the index where match is found
        # Using that index to find the logical ID associated with that FC ID
        queue_mapping = self.get_configured_queue_mapping(
                                                self.qos_node_ip)
        for idx,value in enumerate(fcs):
            if value['fc_id'] == fc_id:
                logical_id = logical_ids[idx]
                break
        # Finding the HW queue corresponding to that logical queue
        hw_queue = queue_mapping[0][queue_mapping[1].index(logical_id)]
        return hw_queue

    def match_traffic(self, init_pkts, final_pkts, min_expected_pkts):
        ''' 
        It ask user for minimum expected packets in the duration of transmission
        If also take initial count and final count of packets during transmission period.
        It allows 1% error in expected packets and return the result.
        '''
        total_packets = final_pkts - init_pkts
        if total_packets == 0:
            self.logger.error("No packet transmitted through the queue")
            return False
        compare_values = is_almost_same(min_expected_pkts, total_packets,
                                 threshold_percent=1, num_type=int)
        if compare_values or total_packets > min_expected_pkts:
            self.logger.info("Expected packets received through"
                             " the desired queue")
            return True
        else:
            self.logger.error("Expected packets not received through"
                              " the desired queue")
            self.logger.error("Traffic might not be queuing to the"
                              " correct queue")
            return False
        
    def skip_tc_if_no_queue_config(self):
        if not self.inputs.qos_queue:
            self.logger.error("Qos Queue configurations not present."
                               " Skipping test case")
            skip = True
            msg = "Qos Queue configurations not present."
            raise testtools.TestCase.skipException(msg)
    
    @classmethod
    def skip_tc_if_no_10G_interface(cls, interface_speed):
        if interface_speed != "10000Mb/s":
            cls.logger.error("Queue interface does not support scheduling"
                              " and bandwidth configurations")
            skip = True
            msg = "DCB not supported on interface"
            raise testtools.TestCase.skipException(msg)
    
    @classmethod
    def delete_conf_file_qos_config(cls):
        conf_file = '/etc/contrail/contrail-vrouter-agent.conf'
        for hw_queue in range(0,64):
            cmd = 'openstack-config --del %s QUEUE-%d' % (conf_file,
                                                          hw_queue)
            cls.inputs.run_cmd_on_server(cls.qos_node_ip, cmd, container='agent')
        cmd = 'openstack-config --del %s QOS' % (conf_file)
        cls.inputs.run_cmd_on_server(cls.qos_node_ip, cmd, container='agent')
        for priority_group in range(0,8):
            cmd = 'openstack-config --del %s PG-%d' % (conf_file,
                                                        priority_group)
            cls.inputs.run_cmd_on_server(cls.qos_node_ip, cmd, container='agent')
        cmd = 'openstack-config --del %s QOS-NIANTIC' % (conf_file)
        cls.inputs.run_cmd_on_server(cls.qos_node_ip, cmd, container='agent')
        
    @classmethod
    def update_conf_file_queueing(cls):
        '''
        This function removes all QOS related configurations from 
        agent.conf and updates the agent.conf with some fixed static values
        which will be used across QOS queueing test cases
        '''
        conf_file = '/etc/contrail/contrail-vrouter-agent.conf'
        # Deleting previous configurations to set new config
        cls.delete_conf_file_qos_config()
        ## Now adding static entries
        cmds = []
        # Below 2 lines are used to create a empty Section named "QOS"
        cmds.append('openstack-config --set %s QOS hack create' % 
                        (conf_file))
        cmds.append('openstack-config --del %s QOS hack' % (conf_file))
        cmds.append('openstack-config --set %s QUEUE-3 logical_queue [15]'
                     % (conf_file))
        cmds.append('openstack-config --set %s QUEUE-11 logical_queue [45]'
                     % (conf_file))
        cmds.append('openstack-config --set %s QUEUE-18 logical_queue [75]'
                     % (conf_file))
        cmds.append('openstack-config --set %s QUEUE-28 logical_queue [115]'
                     % (conf_file))
        # Below 2 lines are used to create a empty Section named "QOS-NIANTEC"
        cmds.append('openstack-config --set %s QOS-NIANTIC hack create' 
                        % (conf_file))
        cmds.append('openstack-config --del %s QOS-NIANTIC hack' % (conf_file))
        cmds.append('openstack-config --set %s PG-0 scheduling strict' 
                    % (conf_file))
        cmds.append('openstack-config --set %s PG-0 bandwidth 0' 
                    % (conf_file))
        cmds.append('openstack-config --set %s PG-1 scheduling rr' 
                    % (conf_file))
        cmds.append('openstack-config --set %s PG-1 bandwidth 60' 
                    % (conf_file))
        cmds.append('openstack-config --set %s PG-2 scheduling strict' 
                    % (conf_file))
        cmds.append('openstack-config --set %s PG-2 bandwidth 0' 
                    % (conf_file))
        cmds.append('openstack-config --set %s PG-3 scheduling rr' 
                    % (conf_file))
        cmds.append('openstack-config --set %s PG-3 bandwidth 40' 
                    % (conf_file))
        for cmd in cmds:
            cls.inputs.run_cmd_on_server(cls.qos_node_ip, cmd, container='agent')
        cls.inputs.restart_service("contrail-vrouter-agent",
                                     [cls.qos_node_ip],
									container='agent')
        cluster_status, error_nodes = ContrailStatusChecker(
                                    ).wait_till_contrail_cluster_stable()
        assert cluster_status, 'Hash of error nodes and services : %s' % (
            error_nodes)
    # update_conf_file_queue_map
    
    @classmethod
    def restore_conf_file_queueing(cls):
        '''
        This function reads the cls.inputs.qos_queue
        and cls.inputs.qos_queue_pg_properties. It again populates the
        agent.conf file with default values as in testbed  file.
        '''
        conf_file = '/etc/contrail/contrail-vrouter-agent.conf'
        cls.delete_conf_file_qos_config()
        for elem in cls.inputs.qos_queue:
            if elem[0] == cls.qos_node_ip:
                queue_mapping = elem[1]
                break
        for elem in cls.inputs.qos_queue_pg_properties:
            if elem[0] == cls.qos_node_ip:
                queue_properties = elem[1]
                break
        cmds = []
        # Below 2 lines are used to create a empty Section named "QOS"
        cmds.append('openstack-config --set %s QOS hack create' % 
                        (conf_file))
        cmds.append('openstack-config --del %s QOS hack' % (conf_file))
        for elem in queue_mapping:
            for key, value in elem.items():
                if "default" in value:
                    cmds.append('openstack-config --set %s QUEUE-%s default_hw_queue true'
                                % (conf_file, key))
                    value.remove("default")
                    if len(value) > 0:
                        value = [str(x) for x in value]
                        value = str(value).replace("'","")
                        cmds.append('openstack-config --set %s QUEUE-%s logical_queue "%s"'
                                % (conf_file, key, value))
                else:
                    value = [str(x) for x in value]
                    value = str(value).replace("'","")
                    cmds.append('openstack-config --set %s QUEUE-%s logical_queue "%s"'
                                % (conf_file, key, value))
        # Below 2 lines are used to create a empty Section named "QOS-NIANTEC"
        cmds.append('openstack-config --set %s QOS-NIANTIC hack create' 
                        % (conf_file))
        cmds.append('openstack-config --del %s QOS-NIANTIC hack' % (conf_file))
        for elem in queue_properties:
            priority_id = elem['priority_id']
            bandwidth = elem['bandwidth']
            scheduling = elem['scheduling']
            cmds.append('openstack-config --set %s PG-%s scheduling %s'
                        % (conf_file, priority_id, scheduling))
            cmds.append('openstack-config --set %s PG-%s bandwidth %s'
                        % (conf_file, priority_id, bandwidth))
        for cmd in cmds:
            cls.inputs.run_cmd_on_server(cls.qos_node_ip, cmd, container='agent')
        cls.inputs.restart_service("contrail-vrouter-agent",
                                     [cls.qos_node_ip],
									container='agent')
        cluster_status, error_nodes = ContrailStatusChecker(
                                    ).wait_till_contrail_cluster_stable()
        assert cluster_status, 'Hash of error nodes and services : %s' % (
            error_nodes)
    # update_conf_file_queue_map
    
    @classmethod
    def configure_queue_features(cls):
        '''
        This function use qosmap tool to configure NIC parameters for
        different priority groups
        '''
        interface = cls.get_qos_queue_params(cls.qos_node_ip)[0]
        cmd = "qosmap --set-queue %s --dcbx ieee --bw 0,60,0,40,0,0,0,0 "\
                "--strict 10101010 --tc 0,1,2,3,4,5,6,7" % interface
        cls.inputs.run_cmd_on_server(cls.qos_node_ip, cmd)

class QosTestExtendedBase(QosTestBase):
    @classmethod
    def setUpClass(cls):
        cls.setupClass_is_run = False
        super(QosTestExtendedBase, cls).setUpClass()
        if len(cls.inputs.compute_names) < 2 :
            cls.inputs.logger.warn('Cannot setup env since cluster has less'
                ' than 2 compute nodes')
            return
        cls.setupClass_is_run = True
        cls.vnc_api_h = cls.vnc_lib
        cls.inputs.address_family = "dual"
        cls.first_node_name , cls.second_node_name, cls.first_node_interface_bw\
                                                             = cls.pick_nodes()
        cls.vn1_fixture = cls.create_only_vn()
        cls.vn2_fixture = cls.create_only_vn()
        cls.vn1_vm1_fixture = cls.create_only_vm(cls.vn1_fixture,
                                  node_name=cls.first_node_name)
        cls.vn1_vm2_fixture = cls.create_only_vm(cls.vn1_fixture,
                                  node_name=cls.second_node_name)
        cls.vn2_vm1_fixture = cls.create_only_vm(cls.vn2_fixture,
                                  node_name=cls.second_node_name)
        cls.check_vms_booted([cls.vn1_vm1_fixture, cls.vn1_vm2_fixture,
                              cls.vn2_vm1_fixture])
        cls.vn1_vm1_compute_fixture = ComputeNodeFixture(
                                        cls.connections,
                                        cls.vn1_vm1_fixture.vm_node_ip)
        cls.vn1_vm1_compute_fixture.setUp()
        cls.vn1_vm2_compute_fixture = ComputeNodeFixture(
                                        cls.connections,
                                        cls.vn1_vm2_fixture.vm_node_ip)
        cls.vn1_vm2_compute_fixture.setUp()
        cls.vn2_vm1_compute_fixture = ComputeNodeFixture(
                                        cls.connections,
                                        cls.vn2_vm1_fixture.vm_node_ip)
        cls.vn2_vm1_compute_fixture.setUp()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        if not cls.setupClass_is_run:
            return
        cls.inputs.address_family = "v4"
        cls.vn2_vm1_compute_fixture.cleanUp()
        cls.vn1_vm2_compute_fixture.cleanUp()
        cls.vn1_vm1_compute_fixture.cleanUp()
        cls.vn2_vm1_fixture.cleanUp()
        cls.vn1_vm2_fixture.cleanUp()
        cls.vn1_vm1_fixture.cleanUp()
        cls.vn2_fixture.cleanUp()
        cls.vn1_fixture.cleanUp()
        super(QosTestExtendedBase, cls).tearDownClass()
    # end tearDownClass

    def is_test_applicable(self):
        if len(self.inputs.compute_ips) < 2:
            return (False, 'Skipping tests since cluster has less than 2 '
                'compute nodes')
        else:
            return (True, None)
    # end is_test_applicable
    
class TestQosPolicyBase(QosTestExtendedBase):
    
    @classmethod
    def setUpClass(cls):
        super(TestQosPolicyBase, cls).setUpClass()
        rules = [{'direction': '<>',
                  'protocol': 'udp',
                  'dest_network': cls.vn1_fixture.vn_name,
                  'source_network': cls.vn2_fixture.vn_name,
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'},
                 {'direction': '<>',
                  'protocol': 'tcp',
                  'dest_network': cls.vn1_fixture.vn_name,
                  'source_network': cls.vn2_fixture.vn_name,
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]
        cls.policy_fixture = PolicyFixture(
                            policy_name='policyTestQos',
                            rules_list=rules,
                            inputs=cls.inputs,
                            connections=cls.connections)
        cls.policy_fixture.setUp()
        cls.vn1_policy_fixture = VN_Policy_Fixture(
                            connections=cls.connections,
                            vn_name=cls.vn1_fixture.vn_name,
                            policy_obj={cls.vn1_fixture.vn_name :\
                                         [cls.policy_fixture.policy_obj]},
                            vn_obj={cls.vn1_fixture.vn_name : cls.vn1_fixture},
                            vn_policys=['policyTestQos'],
                            project_name=cls.project.project_name)
        cls.vn1_policy_fixture.setUp()
        cls.vn2_policy_fixture = VN_Policy_Fixture(
                            connections=cls.connections,
                            vn_name=cls.vn2_fixture.vn_name,
                            policy_obj={cls.vn2_fixture.vn_name : \
                                        [cls.policy_fixture.policy_obj]},
                            vn_obj={cls.vn2_fixture.vn_name : cls.vn2_fixture},
                            vn_policys=['policyTestQos'],
                            project_name=cls.project.project_name)
        cls.vn2_policy_fixture.setUp()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        if not cls.setupClass_is_run:
            return
        cls.vn1_policy_fixture.cleanUp()
        cls.vn2_policy_fixture.cleanUp()
        cls.policy_fixture.cleanUp()
        super(TestQosPolicyBase, cls).tearDownClass()
    # end tearDownClass
    
class TestQosSVCBase(QosTestExtendedBase):
    
    @classmethod
    def setUpClass(cls):
        super(TestQosSVCBase, cls).setUpClass()
        if_details = { 'left': {'shared_ip_enable': False,
                                'static_route_enable' : False},
                       'right': {'shared_ip_enable': False,
                                'static_route_enable' : False}}
        cls.st_fixture= SvcTemplateFixture(connections=cls.connections,
                        st_name="service_template",
                        svc_img_name='ubuntu-in-net', svc_type='firewall',
                        if_details=if_details, svc_mode='in-network',
                        svc_scaling=False, flavor='contrail_flavor_2cpu',
                        availability_zone_enable = True)
        cls.st_fixture.setUp()
        cls.si_fixture= SvcInstanceFixture(connections=cls.connections,
                        si_name="service_instance", svc_template= cls.st_fixture.st_obj,
                        if_details=if_details, left_vn_name=cls.vn1_fixture.vn_fq_name,
                        right_vn_name=cls.vn2_fixture.vn_fq_name,
                        do_verify=True, max_inst=1,
                        availability_zone = "nova:"+cls.first_node_name)
        cls.si_fixture.setUp()
        cls.si_fixture.verify_on_setup()
        cls.action_list =  [":".join(cls.si_fixture.si_fq_name)]
        rules = [{'direction': '<>',
                  'protocol': 'any',
                  'dest_network': cls.vn2_fixture.vn_name,
                  'source_network': cls.vn1_fixture.vn_name,
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any',
                  'action_list': {'apply_service': cls.action_list}}]
        cls.policy_fixture = PolicyFixture(
                            policy_name='policyTestQos',
                            rules_list=rules,
                            inputs=cls.inputs,
                            connections=cls.connections)
        cls.policy_fixture.setUp()
        cls.vn1_policy_fixture = VN_Policy_Fixture(
                            connections=cls.connections,
                            vn_name=cls.vn1_fixture.vn_name,
                            policy_obj={cls.vn1_fixture.vn_name :\
                                         [cls.policy_fixture.policy_obj]},
                            vn_obj={cls.vn1_fixture.vn_name : cls.vn1_fixture},
                            vn_policys=['policyTestQos'],
                            project_name=cls.project.project_name)
        cls.vn1_policy_fixture.setUp()
        cls.vn2_policy_fixture = VN_Policy_Fixture(
                            connections=cls.connections,
                            vn_name=cls.vn2_fixture.vn_name,
                            policy_obj={cls.vn2_fixture.vn_name : \
                                        [cls.policy_fixture.policy_obj]},
                            vn_obj={cls.vn2_fixture.vn_name : cls.vn2_fixture},
                            vn_policys=['policyTestQos'],
                            project_name=cls.project.project_name)
        cls.vn2_policy_fixture.setUp()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        if not cls.setupClass_is_run:
            return
        cls.vn1_policy_fixture.cleanUp()
        cls.vn2_policy_fixture.cleanUp()
        cls.policy_fixture.cleanUp()
        cls.si_fixture.cleanUp()
        cls.st_fixture.cleanUp()
        super(TestQosSVCBase, cls).tearDownClass()
    # end tearDownClass

class TestQosQueueProperties(QosTestExtendedBase):
    
    @classmethod
    def setUpClass(cls):
        super(TestQosQueueProperties, cls).setUpClass()
        cls.skip_tc_if_no_10G_interface(cls.first_node_interface_bw)
        cls.update_conf_file_queueing()
        cls.configure_queue_features()
        cls.vn2_vm2_fixture = cls.create_only_vm(cls.vn2_fixture,
                                  node_name=cls.first_node_name)
        cls.check_vms_booted([cls.vn1_vm1_fixture, cls.vn1_vm2_fixture,
                              cls.vn2_vm1_fixture, cls.vn2_vm2_fixture])
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        if not cls.setupClass_is_run:
            return
        cls.restore_conf_file_queueing()
        cls.vn2_vm2_fixture.cleanUp()
        super(TestQosQueueProperties, cls).tearDownClass()
    # end tearDownClass

class FcIdGenerator():
    '''
        This class parse through the FCs present and 
        return a unique FC ID which is not in use.
    '''
    
    def __init__(self, vnc_lib):
        self.vnc_lib = vnc_lib
    
    def get_free_fc_ids(self, number):
        ''' "number" is number of free fc_ids to be returned'''
        try:
            file = '/tmp/fc_id.lock'
            lock = Lock(file)
            lock.acquire()
            fc_uuids = []
            for elem in self.vnc_lib.forwarding_classs_list()['forwarding-classs']:
                fc_uuids.append(elem['uuid'])
            fc_ids = []
            for elem in fc_uuids:
                fc_ids.append(self.vnc_lib.forwarding_class_read(id =elem).\
                            forwarding_class_id)
            returned_fc_ids = []
            count = 0
            for fc_id in range(0, 256):
                if number > 0:
                    if fc_id not in fc_ids:
                        returned_fc_ids.append(fc_id)
                        count = count +1
                        if count == number:
                            break
                else:
                    break
        finally:
            lock.release()
            return returned_fc_ids
