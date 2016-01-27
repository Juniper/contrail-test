import os
import sys
from time import sleep
from tcutils.util import retry
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.helpers import Host, Sender, Receiver
from traffic.core.profile import StandardProfile,\
                                                    ContinuousProfile
from tcutils.util import get_random_name
sys.path.append(os.path.realpath('tcutils/traffic_utils'))
from base_traffic import *
from security_group import list_sg_rules 
from tcutils.tcpdump_utils import *

class VerifySecGroup():

    def verify_traffic(self, sender_vm, receiver_vm, proto, sport, dport, count=None, fip=None):

        traffic_obj = BaseTraffic.factory(proto=proto)
        assert traffic_obj
        assert traffic_obj.start(sender_vm, receiver_vm,
                              proto, sport, dport, pkt_count=count)
        sleep(1)
        sent, recv = traffic_obj.stop()

        return (sent, recv)

    def assert_traffic(self, sender, receiver, proto, sport, dport,
                       expectation='pass'):
        self.logger.info("Sending %s traffic from %s with %s to %s with %s" %
                         (proto, sender[0].vm_name, sender[1], receiver[0].vm_name, receiver[1]))
        sent, recv = self.verify_traffic(sender[0], receiver[0],
                                         proto, sport, dport)
        if expectation == 'pass':
            msg = "%s traffic from %s with %s to %s with %s passed " % (proto,
                                                                        sender[0].vm_name, sender[1], receiver[0].vm_name, receiver[1])
            errmsg = "%s traffic from %s with %s to %s with %s Failed " % (proto,
                                                                           sender[0].vm_name, sender[1], receiver[0].vm_name, receiver[1])
            if (sent and (recv == sent or recv > sent)):
                self.logger.info(msg)
                return (True, msg)
            else:
                self.logger.error(errmsg)
                if self.inputs.stop_on_fail:
                    self.logger.info(
                        "Sub test failed; Stopping test for debugging.")
                    import pdb
                    pdb.set_trace()
                return (False, errmsg)

        elif expectation == 'fail':
            msg = "%s traffic from %s with %s to %s with %s "\
                "failed as expected" % (proto, sender[0].vm_name, sender[1],
                                        receiver[0].vm_name, receiver[1])
            errmsg = "%s traffic from %s port %s with %s to %s port %s with %s "\
                     "passed; Expcted to fail " % (proto, sender[0].vm_name,sport, sender[1],
                                                   receiver[0].vm_name,dport, receiver[1])
            if (recv == 0):
                self.logger.info(msg)
                return (True, msg)
            else:
                self.logger.error(errmsg)
                if self.inputs.stop_on_fail:
                    self.logger.info(
                        "Sub test failed; Stopping test for debugging.")
                    import pdb
                    pdb.set_trace()
                return (False, errmsg)

    def start_traffic_scapy(self, sender_vm, receiver_vm, proto,
				sport, dport, count=None, fip=None,
				payload=None, icmp_type=None, icmp_code=None,
				recvr=True):
        # Create stream and profile
        if fip:
            stream = Stream(
                protocol="ip", sport=sport, dport=dport, proto=proto, src=sender_vm.vm_ip,
                dst=fip,type=icmp_type,code=icmp_code)
        else:
            stream = Stream(
                protocol="ip", sport=sport, dport=dport, proto=proto, src=sender_vm.vm_ip,
                dst=receiver_vm.vm_ip,type=icmp_type,code=icmp_code)
        profile_kwargs = {'stream': stream}
        if fip:
            profile_kwargs.update({'listener': receiver_vm.vm_ip})
	if payload:
	    profile_kwargs.update({'payload': payload})
        if count:
            profile_kwargs.update({'count': count})
            profile = StandardProfile(**profile_kwargs)
        else:
            profile = ContinuousProfile(**profile_kwargs)

        # Set VM credentials
        send_node = Host(sender_vm.vm_node_ip,
                         self.inputs.username, self.inputs.password)
        recv_node = Host(receiver_vm.vm_node_ip,
                         self.inputs.username, self.inputs.password)
        send_host = Host(sender_vm.local_ip,
                         sender_vm.vm_username, sender_vm.vm_password)
        recv_host = Host(receiver_vm.local_ip,
                         receiver_vm.vm_username, receiver_vm.vm_password)

        # Create send, receive helpers
        sender = Sender("send%s" %
                        proto, profile, send_node, send_host, self.inputs.logger)
        receiver = Receiver("recv%s" %
                            proto, profile, recv_node, recv_host, self.inputs.logger)

        # start traffic
	if recvr:
            receiver.start()
        sender.start()

        return (sender, receiver)

    def stop_traffic_scapy(self, sender, receiver,recvr=True):

        # stop traffic
        sender.stop()
	if recvr:
            receiver.stop()
        self.logger.info("Sent: %s; Received: %s", sender.sent, receiver.recv)
        return (sender.sent, receiver.recv)


    def verify_sec_group_port_proto(self, port_test=False, double_rule=False):
        results = []
        self.logger.info("Verifcations with UDP traffic")
        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm2_fix, self.sg2_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'pass'))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'udp', 8010, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm3_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'udp', 8010, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm4_fix, self.sg2_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'pass'))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'udp', 8010, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm5_fix, self.sg1_fix.secgrp_name)
	if double_rule:
	    exp = 'pass'
	else:
	    exp = 'fail'
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, exp))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'udp', 8010, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm6_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'udp', 8010, 9010, 'fail'))

        self.logger.info("Verifcations with TCP traffic")
        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm2_fix, self.sg2_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'fail'))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'tcp', 8010, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm3_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'fail'))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'tcp', 8010, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm4_fix, self.sg1_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'pass'))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'tcp', 8010, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm5_fix, self.sg1_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'pass'))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'tcp', 8010, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm6_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'fail'))
        if port_test:
            results.append(
                self.assert_traffic(sender, receiver, 'tcp', 8010, 9010, 'fail'))

        errmsg = ''
        for (rc, msg) in results:
            if rc:
                self.logger.debug(msg)
            else:
                errmsg += msg + '\n'
        if errmsg:
            assert False, errmsg

    def verify_sec_group_with_udp_and_policy_with_tcp(self):
        results = []
        self.logger.info("Verifcations with TCP traffic")
        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm2_fix, self.sg2_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'fail'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm3_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'fail'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm4_fix, self.sg1_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'pass'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm5_fix, self.sg1_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'pass'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm6_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'fail'))

        self.logger.info("Verifcations with UDP traffic")
        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm2_fix, self.sg2_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'pass'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm3_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm4_fix, self.sg2_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm5_fix, self.sg1_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm6_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))

        errmsg = ''
        for (rc, msg) in results:
            if rc:
                self.logger.debug(msg)
            else:
                errmsg += msg + '\n'
        if errmsg:
            assert False, errmsg

    def verify_sec_group_with_udp_and_policy_with_tcp_port(self):
        results = []
        self.logger.info("Verifcations with TCP traffic")
        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm2_fix, self.sg2_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'fail'))
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8010, 9000, 'fail'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm3_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'fail'))
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8010, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm4_fix, self.sg1_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'pass'))
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9010, 'fail'))

        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm5_fix, self.sg1_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'pass'))
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8010, 9000, 'fail'))
        sender = (self.vm1_fix, self.sg1_fix.secgrp_name)
        receiver = (self.vm6_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8000, 9000, 'fail'))
        results.append(
            self.assert_traffic(sender, receiver, 'tcp', 8010, 9000, 'fail'))

        self.logger.info("Verifcations with UDP traffic")
        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm2_fix, self.sg2_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'pass'))
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8010, 9000, 'pass'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm3_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8010, 9000, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm4_fix, self.sg2_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8010, 9000, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm5_fix, self.sg1_fix.secgrp_name)
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8010, 9000, 'fail'))

        sender = (self.vm1_fix, self.sg2_fix.secgrp_name)
        receiver = (self.vm6_fix, 'default')
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8000, 9000, 'fail'))
        results.append(
            self.assert_traffic(sender, receiver, 'udp', 8010, 9000, 'fail'))

        errmsg = ''
        for (rc, msg) in results:
            if rc:
                self.logger.debug(msg)
            else:
                errmsg += msg + '\n'
        if errmsg:
            assert False, errmsg

    def start_traffic_and_verify(self, topo, config_topo, prto=None, sprt=None, dprt=None, expt=None, start=0, end=None, traffic_reverse=True):
        results = []
        if not end:
            end = len(topo.traffic_profile) - 1
        for i in range(start, end+1):
            sender = (config_topo['vm'][topo.traffic_profile[i]['src_vm']], topo.sg_of_vm[topo.traffic_profile[i]['src_vm']])
            receiver = (config_topo['vm'][topo.traffic_profile[i]['dst_vm']], topo.sg_of_vm[topo.traffic_profile[i]['dst_vm']])
            if not sprt:
                sport = topo.traffic_profile[i]['sport']
            else:
                sport = sprt
            if not dprt:
                dport = topo.traffic_profile[i]['dport']
            else:
                dport = dprt
            if not prto:
                proto = topo.traffic_profile[i]['proto']
            else:
                proto = prto
            if not expt:
                exp = topo.traffic_profile[i]['exp']
            else:
                exp = expt
            results.append(self.assert_traffic(sender, receiver, proto, sport, dport, exp))
	    if traffic_reverse:
	       results.append(self.assert_traffic(receiver, sender, proto, sport, dport, exp))

        errmsg = ''
        for (rc, msg) in results:
            if rc:
                self.logger.debug(msg)
            else:
                errmsg += msg + '\n'
        if errmsg:
            assert False, errmsg


    def start_traffic_and_verify_multiproject(self, topo_objs, config_topo, prto=None, sprt=None, dprt=None, expt=None, start=0, end=None, traffic_reverse=True):
        results = []
        topo = topo_objs[self.topo.project_list[0]]
        if not end:
            end = len(topo.traffic_profile) - 1
        for i in range(start, end+1):
            sender = (config_topo[topo.traffic_profile[i]['src_vm'][0]]['vm'][topo.traffic_profile[i]['src_vm'][1]],
                                                topo_objs[topo.traffic_profile[i]['src_vm'][0]].sg_of_vm[topo.traffic_profile[i]['src_vm'][1]])
            receiver = (config_topo[topo.traffic_profile[i]['dst_vm'][0]]['vm'][topo.traffic_profile[i]['dst_vm'][1]],
                                                topo_objs[topo.traffic_profile[i]['dst_vm'][0]].sg_of_vm[topo.traffic_profile[i]['dst_vm'][1]])

            if not sprt:
                sport = topo.traffic_profile[i]['sport']
            else:
                sport = sprt
            if not dprt:
                dport = topo.traffic_profile[i]['dport']
            else:
                dport = dprt
            if not prto:
                proto = topo.traffic_profile[i]['proto']
            else:
                proto = prto
            if not expt:
                exp = topo.traffic_profile[i]['exp']
            else:
                exp = expt
            results.append(self.assert_traffic(sender, receiver, proto, sport, dport, exp))
            if traffic_reverse:
               results.append(self.assert_traffic(receiver, sender, proto, sport, dport, exp))

        errmsg = ''
        for (rc, msg) in results:
            if rc:
                self.logger.debug(msg)
            else:
                errmsg += msg + '\n'
        if errmsg:
            assert False, errmsg


    def start_traffic_and_verify_negative_cases(self, topo, config_topo):
        self.start_traffic_and_verify(topo, config_topo)
        self.start_traffic_and_verify(topo, config_topo, prto='tcp',expt='fail',start=4)
        self.start_traffic_and_verify(topo, config_topo, prto='icmp',expt='fail',start=4)

    def fetch_flow_verify_sg_uuid(
            self,
            nh,
            src_vm_fix,
            dst_vm_fix,
            sport,
            dport,
            proto,
            uuid_exp,
            comp_node_ip):
        # get the forward flow on compute node
        inspect_h1 = self.agent_inspect[comp_node_ip]
        flow_rec1 = None
        count = 1
        test_result = False
        while (flow_rec1 is None and count < 10):
            flow_rec1 = inspect_h1.get_vna_fetchflowrecord(
                nh=nh,
                sip=src_vm_fix.vm_ip,
                dip=dst_vm_fix.vm_ip,
                sport=unicode(sport),
                dport=unicode(dport),
                protocol=proto)
            count += 1
            sleep(0.5)

        key = 'sg_rule_uuid'
        if flow_rec1 is None:
            self.logger.error(
                "no flow in agent introspect for the proto:%s traffic" %
                (proto))
            test_result = False
        else:
            self.logger.info("Flow found in agent %s for nh %s is: %s" % (comp_node_ip, nh, flow_rec1))
            for item in flow_rec1:
                if key in item:
                    # compare uuid here 
                    if item[key] == uuid_exp:
                        self.logger.info(
                            "security group rule uuid matches with flow secgrp uuid %s" %
                            (uuid_exp))
                        test_result = True
                    else:
                        self.logger.error(
                            "security group rule uuid %s doesn't matches with flow secgrp uuid %s" %
                            (uuid_exp, item[key]))
                        test_result = False

        return test_result

    def verify_flow_to_sg_rule_mapping(
            self,
            src_vm_fix,
            dst_vm_fix,
            src_vn_fix,
            dst_vn_fix, 
            secgrp_id,
            proto,
            port):
        ''' this method verifies flow to security group mapping for both forward and reverse flow
        for the given sec grp id'''

        if self.option == 'openstack':
            src_vn_fq_name = src_vn_fix.vn_fq_name
            dst_vn_fq_name = dst_vn_fix.vn_fq_name
        else:
            src_vn_fq_name = ':'.join(src_vn_fix._obj.get_fq_name())
            dst_vn_fq_name = ':'.join(dst_vn_fix._obj.get_fq_name())

        nh_src = src_vm_fix.tap_intf[src_vn_fq_name]['flow_key_idx']
        nh_dst = dst_vm_fix.tap_intf[dst_vn_fq_name]['flow_key_idx']
        proto_num = {'udp': '17', 'tcp': '6', 'icmp': '1'}

        test_result = True
        rule_uuid = None
        # get the egress rule uuid
        rules = list_sg_rules(self.connections, secgrp_id)
        for rule in rules:
            if rule['direction'] == 'egress' and (rule['ethertype'] == 'IPv4' or \
                       rule['remote_ip_prefix'] == '0.0.0.0/0') and \
                       (rule['protocol'] == 'any' or rule['protocol'] == proto):
                rule_uuid = rule['id']
                break
        assert rule_uuid, "Egress rule id could not be found"

        # verify forward flow on src compute node
        if not self.fetch_flow_verify_sg_uuid(
                nh_src,
                src_vm_fix,
                dst_vm_fix,
                port,
                port,
                proto_num[proto],
                rule_uuid,
                src_vm_fix.vm_node_ip):
            test_result = False
        # verify reverse flow on src compute node
        if src_vm_fix.vm_node_ip == dst_vm_fix.vm_node_ip:
            nh = nh_dst 
        else:
            nh = nh_src
        if not self.fetch_flow_verify_sg_uuid(
                nh,
                dst_vm_fix,
                src_vm_fix,
                port,
                port,
                proto_num[proto],
                rule_uuid,
                src_vm_fix.vm_node_ip):
            test_result = False

        if src_vm_fix.vm_node_ip != dst_vm_fix.vm_node_ip:
            self.logger.info("verify on destination compute too, \
                      as source and destination computes are different")
            # get the ingress rule uuid
            rule_uuid = None
            rules = list_sg_rules(self.connections, secgrp_id)
            for rule in rules:
                if rule['direction'] == 'ingress' and \
                     (rule['ethertype'] == 'IPv4' or \
                        rule['remote_group_id'] == secgrp_id or \
                        rule['remote_ip_prefix'] == '0.0.0.0/0') and \
                     (rule['protocol'] == 'any' or rule['protocol'] == proto):
                    rule_uuid = rule['id']
                    break
            assert rule_uuid, "Ingress rule id could not be found"
            # verify forward flow on dst compute node
            if not self.fetch_flow_verify_sg_uuid(
                    nh_dst,
                    src_vm_fix,
                    dst_vm_fix,
                    port,
                    port,
                    proto_num[proto],
                    rule_uuid,
                    dst_vm_fix.vm_node_ip):
                test_result = False
            # verify reverse flow on dst compute node
            if not self.fetch_flow_verify_sg_uuid(
                    nh_dst,
                    dst_vm_fix,
                    src_vm_fix,
                    port,
                    port,
                    proto_num[proto],
                    rule_uuid,
                    dst_vm_fix.vm_node_ip):
                test_result = False

        return test_result

    def verify_traffic_on_vms(self,
                             src_vm_fix, src_vn_fix,
                             dst_vm_fix, dst_vn_fix,
                             src_filters, dst_filters,
                             src_exp_count=None, dst_exp_count=None
                             ):

        result = False
        if self.option == 'openstack':
            src_vn_fq_name = src_vn_fix.vn_fq_name
            dst_vn_fq_name = dst_vn_fix.vn_fq_name
        else:
            src_vn_fq_name = ':'.join(src_vn_fix._obj.get_fq_name())
            dst_vn_fq_name = ':'.join(dst_vn_fix._obj.get_fq_name())

        # start tcpdump on dst VM
        session1, pcap1 = start_tcpdump_for_vm_intf(self,
                                    dst_vm_fix, dst_vn_fq_name,
                                    filters = dst_filters)
        # start tcpdump on src VM
        session2, pcap2 = start_tcpdump_for_vm_intf(self,
                                    src_vm_fix, src_vn_fq_name,
                                    filters = src_filters)

        #verify packet count and stop tcpdump on dst VM
        if not verify_tcpdump_count(self, session1, pcap1, exp_count=dst_exp_count):
            return result
        #verify packet count and stop tcpdump on src VM
        if not verify_tcpdump_count(self, session2, pcap2, exp_count=src_exp_count):
            return result

        return True
