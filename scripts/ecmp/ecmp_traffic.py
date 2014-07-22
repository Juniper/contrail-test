import sys
from time import sleep
from datetime import datetime
import os
import fixtures
import testtools
import unittest
import types
import time
sys.path.append(os.path.realpath('scripts/tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile, ContinuousSportRange
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
#from tcutils.pkgs.Traffic.traffic.core.stream import Stream
#from tcutils.pkgs.Traffic.traffic.core.profile import create, ContinuousProfile
#from tcutils.pkgs.Traffic.traffic.core.helpers import Host
#from tcutils.pkgs.Traffic.traffic.core.helpers import Sender, Receiver
from fabric.state import connections as fab_connections
from servicechain.config import ConfigSvcChain
from servicechain.verify import VerifySvcChain


class ECMPTraffic(ConfigSvcChain, VerifySvcChain):

    def verify_traffic_flow(self, src_vm, dst_vm_list, src_ip= None, dst_ip= None):
        fab_connections.clear()
        src_ip= src_vm.vm_ip
        if dst_ip == None: 
            dst_ip= dst_vm_list[0].vm_ip
        src_vm.install_pkg("Traffic")
        for vm in dst_vm_list:
            vm.install_pkg("Traffic")
        sleep(5)
        stream_list= self.setup_streams(src_vm, dst_vm_list, src_ip= src_ip, dst_ip= dst_ip)
        sender, receiver= self.start_traffic(src_vm, dst_vm_list, stream_list, src_ip= src_ip, dst_ip= dst_ip)
        self.verify_flow_records(src_vm, src_ip= src_ip, dst_ip= dst_ip)
        self.stop_traffic(sender, receiver, dst_vm_list, stream_list)
		
        return True
    
    def setup_streams(self, src_vm, dst_vm_list, src_ip= None, dst_ip= None):

        src_ip= src_vm.vm_ip
        if dst_ip == None:
            dst_ip= dst_vm_list[0].vm_ip

        stream1 = Stream(protocol="ip", proto="udp", src=src_ip,
                         dst=dst_ip, sport=8000, dport=9000)
        stream2 = Stream(protocol="ip", proto="udp", src=src_ip,
                         dst=dst_ip, sport=8000, dport=9001)
        stream3 = Stream(protocol="ip", proto="udp", src=src_ip,
                         dst=dst_ip, sport=8000, dport=9002)
        stream_list = [stream1, stream2, stream3]

        return stream_list
	# end setup_streams
    
    def start_traffic(self, src_vm, dst_vm_list, stream_list, src_ip= None, dst_ip= None):
        
        self.logger.info("-" * 80)
        self.logger.info('Starting Traffic from %s to %s' %
                         (src_ip, dst_ip))
        self.logger.info("-" * 80)
        profile = {}
        sender = {}
        receiver = {}
        tx_vm_node_ip = self.inputs.host_data[
            self.nova_fixture.get_nova_host_of_vm(src_vm.vm_obj)]['host_ip']
        tx_local_host = Host(
            tx_vm_node_ip, self.inputs.username, self.inputs.password)
        send_host = Host(src_vm.local_ip, src_vm.vm_username,
                         src_vm.vm_password)
        rx_vm_node_ip = {}
        rx_local_host = {} 
        recv_host = {}
        
        for dst_vm in dst_vm_list:
            rx_vm_node_ip[dst_vm]= self.inputs.host_data[
            	self.nova_fixture.get_nova_host_of_vm(dst_vm.vm_obj)]['host_ip']
            rx_local_host[dst_vm] = Host(
            	rx_vm_node_ip[dst_vm], self.inputs.username, self.inputs.password)
            recv_host[dst_vm] = Host(dst_vm.local_ip, dst_vm.vm_username,
                         dst_vm.vm_password)
        count= 0
        for stream in stream_list:
            profile[stream] = {}
            sender[stream] = {}
            receiver[stream] = {}
            for dst_vm in dst_vm_list:
                count = count + 1
                x= datetime.now().microsecond
                send_filename = "sendudp_" + str(x) + "_"+ "%s" %count
                recv_filename = "recvudp_" + str(x) + "_"+ "%s" %count
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
    
    def verify_flow_records(self, src_vm, src_ip= None, dst_ip= None):
		
        self.logger.info('Checking Flow records')
        src_port = unicode(8000)
        dpi1 = unicode(9000)
        dpi2 = unicode(9001)
        dpi3 = unicode(9002)
        dpi_list = [dpi1, dpi2, dpi3]
        vn_fq_name= src_vm.vn_fq_name
        items_list= src_vm.tap_intf[vn_fq_name].items()
        for items, values in items_list:
            if items == 'flow_key_idx':
                nh_id= values
        self.logger.debug('Flow Index of the src_vm is %s'%nh_id)
        inspect_h = self.agent_inspect[src_vm.vm_node_ip]
        flow_rec = inspect_h.get_vna_fetchflowrecord(
                nh= nh_id, sip=src_ip, dip=dst_ip, sport=src_port, dport=dpi1, protocol='17')

        flow_result= True
        if flow_rec is None:
            flow_result= False
        else:
            self.logger.info('Flow between %s and %s seen' % (dst_ip, src_ip))
        assert flow_result, 'Flow between %s and %s not seen' % (dst_ip, src_ip)

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
                stream_sent_count[stream] = stream_sent_count[stream] + sender[stream][dst_vm].sent
                stream_recv_count[stream] = stream_recv_count[stream] + receiver[stream][dst_vm].recv
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
