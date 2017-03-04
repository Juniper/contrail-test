import sys
from time import sleep
from datetime import datetime
import os
import fixtures
import testtools
import unittest
import types
import time
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile, ContinuousSportRange
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from fabric.state import connections as fab_connections
from common.servicechain.verify import VerifySvcChain


class ECMPTraffic(VerifySvcChain):

    def verify_traffic_flow(self, src_vm, dst_vm_list, si_fix, src_vn, src_ip=None, dst_ip=None, ecmp_hash=None, flow_count=3):
        fab_connections.clear()
        src_ip = src_vm.vm_ip
        if dst_ip == None:
            dst_ip = dst_vm_list[0].vm_ip
        src_vm.install_pkg("Traffic")
        for vm in dst_vm_list:
            vm.install_pkg("Traffic")
        sleep(5)
        stream_list = self.setup_streams(
            src_vm, dst_vm_list, src_ip=src_ip, dst_ip=dst_ip, flow_count=flow_count)
        sender, receiver = self.start_traffic(
            src_vm, dst_vm_list, stream_list, src_ip=src_ip, dst_ip=dst_ip)
        self.verify_flow_thru_si(si_fix, src_vn, ecmp_hash=ecmp_hash, flow_count=flow_count)
        self.verify_flow_records(src_vm, src_ip=src_ip, dst_ip=dst_ip, flow_count=flow_count)
        self.stop_traffic(sender, receiver, dst_vm_list, stream_list)

        return True

    def setup_streams(self, src_vm, dst_vm_list, src_ip=None, dst_ip=None, flow_count=3):

        src_ip = src_vm.vm_ip
        if dst_ip == None:
            dst_ip = dst_vm_list[0].vm_ip

        stream_list=[]
        for i in range(0,flow_count):
            stream_name = "stream"+str(i+1)
            dport = 9000+i
            stream_name = Stream(proto="udp", src=src_ip, dst=dst_ip, sport=8000,
                                 dport=dport)
            stream_list.append(stream_name)

        return stream_list
        # end setup_streams

    def start_traffic(self, src_vm, dst_vm_list, stream_list, src_ip=None, dst_ip=None):

        self.logger.info("-" * 80)
        self.logger.info('Starting Traffic from %s to %s' %
                         (src_ip, dst_ip))
        self.logger.info("-" * 80)
        profile = {}
        sender = {}
        receiver = {}
        tx_vm_node_ip = self.inputs.host_data[
            self.nova_h.get_nova_host_of_vm(src_vm.vm_obj)]['host_ip']
        tx_local_host = Host(
            tx_vm_node_ip,
            self.inputs.host_data[tx_vm_node_ip]['username'],
            self.inputs.host_data[tx_vm_node_ip]['password'])
        send_host = Host(src_vm.local_ip, src_vm.vm_username,
                         src_vm.vm_password)
        rx_vm_node_ip = {}
        rx_local_host = {}
        recv_host = {}

        for dst_vm in dst_vm_list:
            rx_vm_node_ip[dst_vm] = self.inputs.host_data[
                self.nova_h.get_nova_host_of_vm(dst_vm.vm_obj)]['host_ip']
            rx_local_host[dst_vm] = Host(
                rx_vm_node_ip[dst_vm],
                self.inputs.host_data[rx_vm_node_ip[dst_vm]]['username'],
                self.inputs.host_data[rx_vm_node_ip[dst_vm]]['password'])
            recv_host[dst_vm] = Host(dst_vm.local_ip, dst_vm.vm_username,
                                     dst_vm.vm_password)
        count = 0
        for stream in stream_list:
            profile[stream] = {}
            sender[stream] = {}
            receiver[stream] = {}
            for dst_vm in dst_vm_list:
                count = count + 1
                x = datetime.now().microsecond
                send_filename = "sendudp_" + str(x) + "_" + "%s" % count
                recv_filename = "recvudp_" + str(x) + "_" + "%s" % count
                profile[stream][dst_vm] = ContinuousProfile(
                    stream=stream, listener=dst_vm.vm_ip, chksum=True)
                sender[stream][dst_vm] = Sender(
                    send_filename, profile[stream][dst_vm], tx_local_host, send_host, self.inputs.logger)
                receiver[stream][dst_vm] = Receiver(
                    recv_filename, profile[stream][dst_vm], rx_local_host[dst_vm], recv_host[dst_vm], self.inputs.logger)
                receiver[stream][dst_vm].start()
                sender[stream][dst_vm].start()
        return sender, receiver
        # end start_traffic

    def verify_flow_thru_si(self, si_fix, src_vn=None, ecmp_hash=None, flow_count=3):
        self.logger.info(
            'Will start a tcpdump on the left-interfaces of the Service Instances to find out which flow is entering which Service Instance')
        flowcount = 0
        result = True
        flow_pattern = {}
        svms = self.get_svms_in_si(si_fix)
        svms = sorted(set(svms))
        if None in svms:
            svms.remove(None)
        for svm in svms:
            self.logger.info('SVM %s is in %s state' % (svm.name, svm.status))
            if svm.status == 'ACTIVE':
                svm_name = svm.name
                host = self.get_svm_compute(svm_name)
                if src_vn is not None:
                    tapintf = self.get_svm_tapintf_of_vn(svm_name, src_vn)
                else:
                    direction = 'left'
                    tapintf = self.get_bridge_svm_tapintf(svm_name, direction)
                session = ssh(
                    host['host_ip'], host['username'], host['password'])
                cmd = 'tcpdump -nni %s -c 10 > /tmp/%s_out.log' % (
                    tapintf, tapintf)
                execute_cmd(session, cmd, self.logger)
            else:
                self.logger.info('%s is not in ACTIVE state' % svm.name)
        sleep(15)

        self.logger.info('%%%%% Will check the result of tcpdump %%%%%')
        svms = self.get_svms_in_si(si_fix)
        svms = sorted(set(svms))
        if None in svms:
            svms.remove(None)
        for svm in svms:
            self.logger.info('SVM %s is in %s state' % (svm.name, svm.status))
            if svm.status == 'ACTIVE':
                svm_name = svm.name
                host = self.get_svm_compute(svm_name)
                if src_vn is not None:
                    tapintf = self.get_svm_tapintf_of_vn(svm_name, src_vn)
                else:
                    direction = 'left'
                    tapintf = self.get_bridge_svm_tapintf(svm_name, direction)
                session = ssh(
                    host['host_ip'], host['username'], host['password'])
                output_cmd = 'cat /tmp/%s_out.log' % tapintf
                out, err = execute_cmd_out(session, output_cmd, self.logger)

                for i in range(0,flow_count):
                    dport = str(9000+i)
                    if dport in out:
                        flowcount = flowcount + 1
                        self.logger.info(
                            'Flow with dport %s seen flowing inside %s' % (dport,svm_name))
                        flow_pattern[dport] = svm_name
            else:
                self.logger.info('%s is not in ACTIVE state' % svm.name)
        if flowcount > 0:
            self.logger.info(
                'Flows are distributed across the Service Instances as :')
            self.logger.info('%s' % flow_pattern)
        else:
            result = False

        if ecmp_hash and ecmp_hash != 'default':
            # count the number of hash fields set
            hash_var_count = sum(ecmp_hash.values())

            # Incase, only one hash field is set, all flows should go through
            # single service instance. One exception here is destination_port.
            # Destination port varies for traffic streams.So, for destination
            # port, traffic will get load balanced even if ecmp hash is
            # configured "destination_port" alone.
            if hash_var_count == 1 and (not 'destination_port' in ecmp_hash):
                flow_pattern_ref = flow_pattern['9000']
                if all(flow_pattern_ref  == item for item in flow_pattern.values()):
                    self.logger.info(
                        'Flows are flowing through Single Service Instance: %s, as per config hash: %s' % (flow_pattern_ref, ecmp_hash))
                    self.logger.info('%s' % flow_pattern)
                else:
                    result = False
                    self.logger.error(
                        'Flows are flowing through multiple Service Instances:%s, where as it should not as per config hash:%s' % (flow_pattern, ecmp_hash))
                    assert result, 'Config hash is not working for: %s' % ( ecmp_hash)
            # Incase, multiple ecmp hash fields are configured or default ecmp
            # hash is present or only 'destionation_port' is configured in
            # ecmp_hash
            else:
                flow_pattern_ref = flow_pattern['9000']
                if all(flow_pattern_ref  == item for item in flow_pattern.values()):
                    result = False
                    self.logger.error(
                        'Flows are flowing through Single Service Instance:%s, where as it should not as per config hash:%s' % (flow_pattern_ref, ecmp_hash))
                    #assert result, 'Config hash is not working fine.'
                else:
                    self.logger.info(
                        'Flows are flowing through multiple Service Instances:%s, as per config hash: %s' % (flow_pattern, ecmp_hash))
                    self.logger.info('%s' % flow_pattern)
        else:
            assert result, 'No Flow distribution seen'

        # end verify_flow_thru_si

    def verify_flow_records(self, src_vm, src_ip=None, dst_ip=None, flow_count=3):

        self.logger.info('Checking Flow records')
        vn_fq_name = src_vm.vn_fq_name
        items_list = src_vm.tap_intf[vn_fq_name].items()
        for items, values in items_list:
            if items == 'flow_key_idx':
                nh_id = values
        self.logger.debug('Flow Index of the src_vm is %s' % nh_id)
        inspect_h = self.agent_inspect[src_vm.vm_node_ip]

        flow_result = True
        for i in range(0,flow_count):
            src_port = unicode(8000)
            dest_port =unicode(9000+i)
            flow_rec = inspect_h.get_vna_fetchflowrecord(
                nh=nh_id, sip=src_ip, dip=dst_ip, sport=src_port, dport=dest_port, protocol='17')
            if flow_rec is None:
                flow_result = False
        if flow_result:
            self.logger.info('Flow between %s and %s seen' % (dst_ip, src_ip))
        else:
            assert flow_result, 'Flow between %s and %s not seen' % ( dst_ip, src_ip)

        return True
        # end verify_flow_records

    def stop_traffic(self, sender, receiver, dst_vm_list, stream_list):

        self.logger.info('Stopping Traffic now')

        for stream in stream_list:
            for dst_vm in dst_vm_list:
                sender[stream][dst_vm].stop()
                receiver[stream][dst_vm].stop()
        time.sleep(5)
        stream_sent_count = {}
        stream_recv_count = {}
        result = True
        for stream in stream_list:
            stream_sent_count[stream] = 0
            stream_recv_count[stream] = 0
            for dst_vm in dst_vm_list:
                if sender[stream][dst_vm].sent == None:
                    sender[stream][dst_vm].sent = 0
                if receiver[stream][dst_vm].recv == None:
                    receiver[stream][dst_vm].recv = 0
                stream_sent_count[stream] = stream_sent_count[
                    stream] + sender[stream][dst_vm].sent
                stream_recv_count[stream] = stream_recv_count[
                    stream] + receiver[stream][dst_vm].recv
            pkt_diff = (stream_sent_count[stream] - stream_recv_count[stream])
            if pkt_diff < 0:
                self.logger.debug('Some problem with Scapy. Please check')
            elif pkt_diff in range(0, 6):
                self.logger.info(
                    '%s packets sent and %s packets received in Stream%s. No Packet Loss seen.' %
                    (stream_sent_count[stream], stream_recv_count[stream], stream_list.index(stream)))
            else:
                self.logger.error('%s packets sent and %s packets received in Stream%s. Packet Loss.' % (
                    stream_sent_count[stream], stream_recv_count[stream], stream_list.index(stream)))
        return True
    # end stop_traffic
