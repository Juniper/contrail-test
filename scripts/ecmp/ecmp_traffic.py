import sys
from time import sleep
import os
import fixtures
import testtools
import unittest
import time
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from fabric.state import connections as fab_connections
from servicechain.config import ConfigSvcChain
from servicechain.verify import VerifySvcChain

class ECMPTraffic(ConfigSvcChain, VerifySvcChain):
    def verify_traffic_flow(self, src_vm, dst_vm):
        fab_connections.clear()
        vm_list= [src_vm, dst_vm]
        for vm in vm_list:
            self.logger.info('Getting the local_ip of the VM')
            vm.verify_vm_in_agent()
            out= self.nova_fixture.wait_till_vm_is_active( vm.vm_obj)
            if out == False: return {'result':out, 'msg':"%s failed to come up"%vm.vm_name}
            else: time.sleep(5); self.logger.info('Installing Traffic package on %s ...'%vm.vm_name); vm.install_pkg("Traffic")

        self.logger.info("-"*80)
        self.logger.info('Starting TCP Traffic from %s to %s'%(src_vm.vm_ip, dst_vm.vm_ip))
        self.logger.info("-"*80)
        stream_list= []
        profile= {}
        sender= {}
        receiver= {}
        
        tx_vm_node_ip= self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(src_vm.vm_obj)]['host_ip']
        tx_local_host= Host(tx_vm_node_ip, self.inputs.username, self.inputs.password)
        send_host= Host(src_vm.local_ip, src_vm.vm_username, src_vm.vm_password)

        rx_vm_node_ip= self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(dst_vm.vm_obj)]['host_ip']
        rx_local_host= Host(rx_vm_node_ip, self.inputs.username, self.inputs.password)
        recv_host=  Host(dst_vm.local_ip, dst_vm.vm_username, dst_vm.vm_password)

        stream1 = Stream(protocol="ip", proto="tcp", src=src_vm.vm_ip,dst= dst_vm.vm_ip, sport= 8000, dport=9000)
        stream2 = Stream(protocol="ip", proto="tcp", src=src_vm.vm_ip,dst= dst_vm.vm_ip, sport= 8000, dport=9001)
        stream3 = Stream(protocol="ip", proto="tcp", src=src_vm.vm_ip,dst= dst_vm.vm_ip, sport= 8000, dport=9002)
        count= 0
        stream_list= [stream1, stream2, stream3]

        for stream in stream_list:
            profile[stream]={}
            sender[stream]= {}
            receiver[stream] = {}
            count= count+1
            send_filename= 'sendtcp_%s'%count
            recv_filename= 'recvtcp_%s'%count
            profile[stream] = ContinuousProfile(stream=stream, listener= dst_vm.vm_ip, chksum= True)
            sender[stream]= Sender(send_filename, profile[stream], tx_local_host, send_host, self.inputs.logger)
            time.sleep(5)
            receiver[stream]= Receiver(recv_filename, profile[stream], rx_local_host, recv_host, self.inputs.logger)
            receiver[stream].start()
            sender[stream].start()
        self.logger.info('Sending traffic for 10 seconds')
        time.sleep(10)
        self.logger.info('Checking Flow records')

        flow_result= False
        flow_result2= False
        flow_result3= False

        rev_flow_result= False
        rev_flow_result1= False
        rev_flow_result2= False
        src_vm_vrf_name= src_vm.vn_fq_name+':'+src_vm.vn_name
        vn_vrf_id= src_vm.get_vrf_id(src_vm.vn_fq_name,src_vm_vrf_name)
 
        src_port= unicode(8000)
        dpi1= unicode(9000)
        dpi2= unicode(9001)
        dpi3= unicode(9002)
        dpi_list= [dpi1, dpi2, dpi3]
              
        vm_node_ips= []
        vm_node_ips.append(src_vm.vm_node_ip)
        if (src_vm.vm_node_ip != dst_vm.vm_node_ip): vm_node_ips.append(dst_vm.vm_node_ip)

        inspect_h100= self.agent_inspect[src_vm.vm_node_ip]
        flow_rec1= inspect_h100.get_vna_fetchflowrecord(vrf=vn_vrf_id,sip=src_vm.vm_ip,dip=dst_vm.vm_ip,sport=src_port,dport=dpi1,protocol='6')
        flow_rec2= inspect_h100.get_vna_fetchflowrecord(vrf=vn_vrf_id,sip=src_vm.vm_ip,dip=dst_vm.vm_ip,sport=src_port,dport=dpi2,protocol='6')
        flow_rec3= inspect_h100.get_vna_fetchflowrecord(vrf=vn_vrf_id,sip=src_vm.vm_ip,dip=dst_vm.vm_ip,sport=src_port,dport=dpi3,protocol='6')
        flow_recs= []
        flow_recs= [flow_rec1, flow_rec2, flow_rec3]
        flow_result= True
        for flow_rec in flow_recs:
            if flow_rec is None:
                flow_result= False
            if flow_result is True:
                self.logger.info('Flows from %s to %s exist on Agent %s'%(src_vm.vm_ip, dst_vm.vm_ip, src_vm.vm_node_ip))
                        
        for agent_ip in self.inputs.compute_ips:
            inspect_h= self.agent_inspect[agent_ip]
            rev_flow_result= False
            for iter in range(25):
                self.logger.debug('**** Iteration %s *****'%iter)
                reverseflowrecords= []
                reverseflowrecords= inspect_h.get_vna_fetchallflowrecords()
                for rec in reverseflowrecords:
                    if ((rec['sip'] == dst_vm.vm_ip) and (rec['protocol'] == '6')):
                        self.logger.info('Reverse Flow from %s to %s exists.'%(dst_vm.vm_ip, src_vm.vm_ip))
                        rev_flow_result= True
                        break
                    else:
                        rev_flow_result= False
                if rev_flow_result:
                    break
                else:
                    iter+= 1
                    sleep(10)
            if rev_flow_result:
                break

        self.logger.info('Stopping Traffic now')
        for stream in stream_list:
            sender[stream].stop()
            time.sleep(5)
        for stream in stream_list:
            receiver[stream].stop()
            time.sleep(5)
        stream_sent_count = {}
        stream_recv_count = {}
        result= True
        for stream in stream_list:
            stream_sent_count[stream]= sender[stream].sent
            stream_recv_count[stream]= receiver[stream].recv
            if abs((stream_recv_count[stream] - stream_sent_count[stream])) < 5:
                self.logger.info('%s packets sent and %s packets received in Stream. No Packet Loss seen.'%(stream_sent_count[stream], stream_recv_count[stream]))
            else:
                result= False
                assert result, '%s packets sent and %s packets received in Stream.Packet Loss.'%(stream_sent_count[stream], stream_recv_count[stream])

        assert flow_result,'Flows from %s to %s not seen on Agent %s'%(src_vm.vm_ip, dst_vm.vm_ip, src_vm.vm_node_ip)
        assert rev_flow_result,'Reverse Flow from %s to %s not seen'%(dst_vm.vm_ip, src_vm.vm_ip)

        return True
    #end verify_traffic_flow

