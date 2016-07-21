import sys
import os
import fixtures
#from common.contrail_test_init import ContrailTestInit
from nova_test import *
from common.connections import ContrailConnections
trafficdir = os.path.join(os.path.dirname(__file__), '../tcutils/pkgs/Traffic')
sys.path.append(trafficdir)
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile, ContinuousSportRange
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver

class trafficTestFixture(fixtures.Fixture):

    def __init__(self, connections):
        self.connections = connections
        self.inputs = self.connections.inputs
        self.nova_h = self.connections.nova_h
        self.logger = self.inputs.logger
    # end __init__

    def setUp(self):
        super(trafficTestFixture, self).setUp()
    # end setUp

    def startTraffic(
        self, name='stream', num_streams=1, start_port=9100, tx_vm_fixture=None,
        rx_vm_fixture=None, stream_proto='udp', vm_fip_info=None,
        packet_size=100, cfg_profile='ContinuousProfile', start_sport=8000,
        total_single_instance_streams=20, chksum=False, pps=100, fip=None,
        tx_vn_fixture=None, rx_vn_fixture=None, af=None):
        ''' Start traffic based on inputs given..
        Return {'status': True, 'msg': None} if traffic started successfully..else return {'status': False, 'msg': err_msg}..
        Details on inputs:
        name    : Stream identifier;    num_streams     : number of separate sendpkts instance streams [will take more memory]
        start_port  : Destination start port if num_streams is used
        tx_vm_fixture & rx_vm_fixture  : Needed for vm_ip and vm_mdata_ip [to access vm from compute]
        stream_proto    : TCP, UDP or ICMP; packet_size : if custom size if needed
        start_sport     : if ContinuousSportRange is used, only supports UDP, starting number for source port
        total_single_instance_streams   : if ContinuousSportRange is used, specify number of streams
        pps             :Number of packets to launch per sec
        ContinuousSportRange launches n streams @defined pps, with one instance of sendpkts..
        '''
        self.logger.info("startTraffic data: name- %s, stream_proto-%s, packet_size-%s, total_single_instance_streams-%s, chksum-%s, pps-%s"
                         % (name, stream_proto, packet_size, total_single_instance_streams, chksum, pps))
        status = True
        msg = None
        self.packet_size = packet_size
        self.chksum = chksum
        self.start_port = start_port
        self.start_sport = start_sport
        self.endport = start_sport + total_single_instance_streams
        self.total_single_instance_streams = total_single_instance_streams
        self.tx_vm_fixture = tx_vm_fixture
        self.rx_vm_fixture = rx_vm_fixture
        tx_vn_fq_name = tx_vn_fixture.get_vn_fq_name() if tx_vn_fixture else None
        rx_vn_fq_name = rx_vn_fixture.get_vn_fq_name() if rx_vn_fixture else None
        af = af if af is not None else self.inputs.get_af()
        self.stream_proto = stream_proto
        self.vm_fip_info = vm_fip_info
        self.traffic_fip = False
        if self.vm_fip_info == None:
            self.traffic_fip = False
        else:
            self.traffic_fip = True
        if not self.traffic_fip:
            self.tx_vm_node_ip = self.inputs.host_data[
                self.nova_h.get_nova_host_of_vm(self.tx_vm_fixture.vm_obj)]['host_ip']
            self.rx_vm_node_ip = self.inputs.host_data[
                self.nova_h.get_nova_host_of_vm(self.rx_vm_fixture.vm_obj)]['host_ip']
            self.tx_local_host = Host(
                self.tx_vm_node_ip,
                self.inputs.host_data[self.tx_vm_node_ip]['username'],
                self.inputs.host_data[self.tx_vm_node_ip]['password'])
            self.rx_local_host = Host(
                self.rx_vm_node_ip,
                self.inputs.host_data[self.rx_vm_node_ip]['username'],
                self.inputs.host_data[self.rx_vm_node_ip]['password'])
            self.send_host = Host(self.tx_vm_fixture.local_ip,
                                  self.tx_vm_fixture.vm_username, self.tx_vm_fixture.vm_password)
            self.recv_host = Host(self.rx_vm_fixture.local_ip,
                                  self.rx_vm_fixture.vm_username, self.rx_vm_fixture.vm_password)
        else:
            self.tx_vm_node_ip = None
            self.rx_vm_node_ip = None
            self.tx_local_host = Host(
                self.inputs.cfgm_ip,
                self.inputs.host_data[self.tx_vm_node_ip]['username'],
                self.inputs.host_data[self.tx_vm_node_ip]['password'])
            self.rx_local_host = Host(
                self.inputs.cfgm_ip,
                self.inputs.host_data[self.rx_vm_node_ip]['username'],
                self.inputs.host_data[self.rx_vm_node_ip]['password'])
            self.send_host = Host(self.vm_fip_info[self.tx_vm_fixture.vm_name])
            self.recv_host = Host(self.vm_fip_info[self.rx_vm_fixture.vm_name])
        self.sender = list()
        self.receiver = list()
        self.num_streams = 0

        if fip is None:
            self.dst_ips = list(); self.src_ips = list()
            if af == 'dual' or af == 'v4':
                self.src_ips.extend(self.tx_vm_fixture.get_vm_ips(
                                    vn_fq_name=tx_vn_fq_name, af='v4'))
                self.dst_ips.extend(self.rx_vm_fixture.get_vm_ips(
                                    vn_fq_name=rx_vn_fq_name, af='v4'))
            if af == 'dual' or af == 'v6':
                self.src_ips.extend(self.tx_vm_fixture.get_vm_ips(
                                    vn_fq_name=tx_vn_fq_name, af='v6'))
                self.dst_ips.extend(self.rx_vm_fixture.get_vm_ips(
                                    vn_fq_name=rx_vn_fq_name, af='v6'))
        else:
            self.dst_ips = [fip]
            self.src_ips = [self.tx_vm_fixture.vm_ip]
        if len(self.dst_ips) > len(self.src_ips):
            raise Exception('No of destination ips cant be greater than'
                            ' source ips, for multi stream case')

        for index in range(len(self.dst_ips)):
            name = name + '_dst' + str(index) + '_'
            for i in range(num_streams):
                self.name = name + self.stream_proto + str(i)
                self.dport = start_port + i
                m = "Send protocol %s traffic to port %s" % (
                    self.stream_proto, self.dport)
                if self.stream_proto == 'icmp':
                    m = "Send protocol %s traffic" % self.stream_proto
                self.logger.info(m)
                stream = Stream(proto=self.stream_proto,
                                src=self.src_ips[index],
                                dst=self.dst_ips[index],
                                dport=self.dport)
                if fip:
                   listener = self.rx_vm_fixture.vm_ip
                else:
                   listener = self.dst_ips[index]
                # stream profile...
                if cfg_profile == 'ContinuousSportRange':
                    profile = ContinuousSportRange(stream=stream,
                                                   startport=self.start_sport,
                                                   endport=self.endport,
                                                   listener=listener,
                                                   size=self.packet_size,
                                                   chksum=self.chksum, pps=pps)
                elif cfg_profile == 'ContinuousProfile':
                    profile = ContinuousProfile(stream=stream,
                                                listener=listener,
                                                size=self.packet_size,
                                                chksum=self.chksum)
                # sender profile...
                sender = Sender(self.name, profile, self.tx_local_host,
                                self.send_host, self.inputs.logger)
                receiver = Receiver(self.name, profile, self.rx_local_host,
                                    self.recv_host, self.inputs.logger)
                self.logger.info("tx vm - node %s, mdata_ip %s, vm_ip %s" %(
                                 self.tx_local_host.ip, self.send_host.ip,
                                 self.src_ips[index]))
                self.logger.info("rx vm - node %s, mdata_ip %s, vm_ip %s" %(
                                 self.rx_local_host.ip, self.recv_host.ip,
                                 self.dst_ips[index]))
                receiver.start()
                self.logger.info("Starting %s traffic from %s to %s" %(
                                  self.stream_proto, self.src_ips[index],
                                  self.dst_ips[index]))
                sender.start()
                retries = 10
                j = 0
                sender.sent = None
                while j < retries and sender.sent == None:
                    # wait before checking for stats as it takes time for file
                    # update with stats
                    time.sleep(5)
                    sender.poll()
                # end while
                if sender.sent == None:
                    msg = "send %s traffic failure from %s " % (
                        self.stream_proto, self.src_ips[index])
                    self.logger.info(
                        "traffic tx stats not available !!, details: %s" % msg)
                else:
                    self.logger.info(
                        "traffic running good, sent %s pkts so far.." %
                        sender.sent)
                self.sender.append(sender)
                self.receiver.append(receiver)
                self.num_streams += 1
        if msg != None:
            status = False
        return {'status': status, 'msg': msg}
    # end of startTraffic

    def getLiveTrafficStats(self):
        ''' get stats of traffic streams launched using startTraffic..
        Return True if sender & receiver stats are incrementing [confirms that sender is still sending]..
        Return False if the stats is not incrementing.. which implies traffic is disrupted..
        Depending on the trigger applied, calling code can use the return value to make decision..
        '''
        ret = {}
        ret['msg'] = []
        ret['status'] = None
        stats = {}
        poll_cnt = 5
        status = {}
        for j in range(poll_cnt):
            stats['poll' + str(j)] = {}
            st = stats['poll' + str(j)]
            for i in range(self.num_streams):
                st[i] = {}
                status[i] = {}
                self.receiver[i].poll()
                self.sender[i].poll()
                if self.stream_proto == 'tcp' or self.stream_proto == 'udp':
                    st[i]['sent'] = self.sender[i].sent
                    st[i]['recv'] = self.receiver[i].recv
                elif self.stream_proto == 'icmp' or self.stream_proto == 'icmpv6':
                    st[i]['sent'] = self.sender[i].sent
                    st[i]['recv'] = self.sender[i].recv
                self.logger.info("stream %s: stats sent: %s, stats rev: %s" %
                                 (i, st[i]['sent'], st[i]['recv']))
                # compare stats in this loop with previous to see if traffic
                # flowing
                if j > 0:
                    # checking sender..
                    if stats['poll' + str(j)][i]['sent'] > stats['poll' + str(j - 1)][i]['sent']:
                        self.logger.info("stream %s of type %s, sender %s good, sent pkts in last 2 polls: %s, %s" % (
                            i, self.stream_proto, self.tx_vm_fixture.vm_ip, stats['poll' + str(j - 1)][i]['sent'], stats['poll' + str(j)][i]['sent']))
                        status[i]['sent'] = True
                    else:
                        msg = "stream %s of type %s, from sender %s seems to be down; sent pkts in last 2 polls: %s, %s" % (
                            i, self.stream_proto, self.tx_vm_fixture.vm_ip, stats['poll' + str(j - 1)][i]['sent'], stats['poll' + str(j)][i]['sent'])
                        ret['msg'].append(msg)
                        self.logger.info(msg)
                        status[i]['sent'] = False
                    # checking receiver..
                    if stats['poll' + str(j)][i]['recv'] > stats['poll' + str(j - 1)][i]['recv']:
                        self.logger.info("stream %s, of type %s, receiver %s good, recd. pkts in last 2 polls: %s, %s" % (
                            i, self.stream_proto, self.rx_vm_fixture.vm_ip, stats['poll' + str(j - 1)][i]['recv'], stats['poll' + str(j)][i]['recv']))
                        status[i]['recv'] = True
                    else:
                        msg = "stream %s of type %s @receiver %s seems to be down; recd. pkts in last 2 polls: %s, %s" % (
                            i, self.stream_proto, self.rx_vm_fixture.vm_ip, stats['poll' + str(j - 1)][i]['recv'], stats['poll' + str(j)][i]['recv'])
                        ret['msg'].append(msg)
                        self.logger.info(msg)
                        status[i]['recv'] = False
                    if status[i]['sent'] == False or status[i]['recv'] == False:
                        ret['status'] = False
                    else:
                        ret['status'] = True
                # end compare if loop
            # end for loop for checking all streams
            # if stats are incrementing [True case], come out of poll loop.. no need to recheck again.
            # if stats dont increment, go into loop to poll multiple times to confirm that its due to traffic not flowing
            # and not due to stats file update issue [where file update takes
            # sometime to reflect changes]
            if ret['status'] == True:
                print "breaking loop in %s attempts" % j
                break
            else:
                time.sleep(3)   # sleep and poll again..
        return ret
    # end of getLiveTrafficStats

    def stopTraffic(self, loose='no', loose_allow=100, wait_for_stop=True):
        ''' Stop traffic launched using startTraffic. 
        Return [] if recv = sent, else, return error info
        set loose if you are ok with allowing some loss, used for scale/stress tests.
        '''
        msg = []
        setFail = -1
        for i in range(self.num_streams):
            self.dport = self.start_port + i
            self.sender[i].stop()
            self.logger.info(
                "Waiting for Receiver to receive all packets in transit after stopping sender..")
            if wait_for_stop:
                time.sleep(
                    60) if self.total_single_instance_streams > 1 else time.sleep(2)
            else:
                time.sleep(1)
            self.receiver[i].stop()
            #import pdb; pdb.set_trace()
            if self.sender[i].sent == None or self.receiver[i].recv == None:
                msg = "Cannot proceed with stats check to compare"
                self.logger.error(msg)
                return msg
            if self.stream_proto == 'tcp' or self.stream_proto == 'udp':
                stats = " dest_port: %s, sender %s sent: %s, receiver %s recd: %s" % (
                    self.dport, self.tx_vm_fixture.vm_ip, self.sender[i].sent, self.rx_vm_fixture.vm_ip, self.receiver[i].recv)
                if self.receiver[i].recv == 0:
                    msg.append("receiver recv counter is 0 !!")
                    setFail = 1
                if self.receiver[i].recv != self.sender[i].sent:
                    if loose == 'yes':
                        self.logger.info(
                            "rx less than tx, check within expected number- %s" % stats)
                        setFail = 0
                        if self.sender[i].sent - self.receiver[i].recv < loose_allow:
                            setFail = 0
                        else:
                            setFail = 1
                    elif self.receiver[i].recv > self.sender[i].sent:
                        self.logger.info(
                            "rx more than tx, traffic tool issue with filter, can be ignored- %s" % stats)
                        setFail = 0
                    else:
                        setFail = 1
                    if setFail == 1:
                        msg.append(
                            "data loss seen, receiver received less than sent !!")
            elif self.stream_proto == 'icmp':
                stats = " sender %s sent: %s, sender recd responses: %s" % (
                    self.tx_vm_fixture.vm_ip, self.sender[i].sent, self.sender[i].recv)
                if self.sender[i].sent != self.sender[i].recv:
                    setFail = 1

            self.logger.info(
                "stats after stopping stream %s for proto %s is %s" %
                (i, self.stream_proto, stats))
            if setFail == 1:
                msg.extend(
                    ["traffic failed for stream ", self.stream_proto, stats])
            else:
                self.logger.info(
                    "traffic test for stream %s, proto %s passed" %
                    (i, self.stream_proto))
        return msg
    # end of stopTraffic

    def returnStats(self):
        '''
          Returns traffic stats for each stream which has sent
          it returns list of all streams for which traffic has sent
        '''
        trafficstats = []
        total_pkt_sent = 0
        total_pkt_recv = 0
        for i in range(self.num_streams):
            traffic_flow_stat = {
                'src_ip': self.tx_vm_fixture.vm_ip, 'dst_ip': self.rx_vm_fixture.vm_ip, 'dst_port': self.dport,
                'protocol': self.stream_proto, 'sent_traffic': self.sender[i].sent, 'recv_traffic': self.receiver[i].recv}
            trafficstats.append(traffic_flow_stat)
            if self.sender[i].sent:
                total_pkt_sent = total_pkt_sent + self.sender[i].sent
            if self.receiver[i].recv:
                total_pkt_recv = total_pkt_recv + self.receiver[i].recv

        return {'traffic_stats': trafficstats, 'total_pkt_sent': total_pkt_sent, 'total_pkt_recv': total_pkt_recv}
    # end returnStats
