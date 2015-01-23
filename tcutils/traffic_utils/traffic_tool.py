# general traffic class to use different traffic tools to trigger traffic based on input tool/utils
# if no tool is passed, then netcat traditional is used for tcp/udp and
# scapy is used for icmp

import os
import sys
sys.path.append(os.path.realpath('tcutils/traffic_utils'))
from netcat_traffic import *
from scapy_traffic import *
from time import sleep

NETCAT = 'netcat'
SCAPY = 'scapy'
TCP = 'tcp'
UDP = 'udp'


class Traffic():

    def __init__(
            self,
            sender_vm_fix,
            receiver_vm_fix,
            proto,
            sport,
            dport,
            tool=None,
            pkt_count=None,
            fip=None):

        self.tool = tool
        self.sender = None  # pid in case of netcat tool
        self.receiver = None  # pid in case of netcat tool
        self.sender_vm_fix = sender_vm_fix
        self.receiver_vm_fix = receiver_vm_fix
        self.proto = proto
        self.sport = sport
        self.dport = dport
        self.sent = None
        self.recv = None
        self.inputs = sender_vm_fix.inputs
        self.logger = self.inputs.logger
        self.pkt_count = pkt_count
        self.fip = fip
        if (self.proto == TCP or self.proto == UDP) and not self.tool:
            self.tool = NETCAT
        if not (self.proto == TCP or self.proto == UDP) and not self.tool:
            self.tool = SCAPY

    def start_traffic(self):
        if self.tool == NETCAT and (self.proto == TCP or self.proto == UDP):
            self.sent, self.receiver = start_nc(
                self, self.sender_vm_fix, self.receiver_vm_fix,
                self.proto, self.sport, self.dport, pkt_count=self.pkt_count)
        elif self.tool == NETCAT and (self.proto != TCP and self.proto != UDP):
            self.logger.warn(
                "netcat can not be used for %s protocol" %
                self.proto)
            return False

        if self.tool == SCAPY:
            self.sender, self.receiver = start_scapy(
                self, self.sender_vm_fix, self.receiver_vm_fix,
                self.proto, self.sport, self.dport, count=self.pkt_count, fip=self.fip)

        return True

    def stop_traffic(self):
        if self.tool == NETCAT and (self.proto == TCP or self.proto == UDP):
            stop_nc(self, self.receiver_vm_fix, self.receiver)

        if self.tool == SCAPY:
            self.sent, self.recv = stop_scapy(self, self.sender, self.receiver)

    def get_packet_count(self):
        '''this method can be called once traffic is stopped using stop_traffic method '''

        if self.tool == NETCAT and (self.proto == TCP or self.proto == UDP):
            sent, self.recv = get_packet_count_nc(self, self.receiver_vm_fix)

        self.logger.info("Sent : %s, Received: %s" % (self.sent, self.recv))
        return self.sent, self.recv
