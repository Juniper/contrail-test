# general traffic class to use different traffic tools to trigger traffic based on input tool/utils
# if no tool is passed, then netcat traditional is used for tcp/udp and
# scapy is used for icmp

import os
import sys
sys.path.append(os.path.realpath('tcutils/traffic_utils'))
from time import sleep

NETCAT = 'netcat'
SCAPY = 'scapy'
TCP = 'tcp'
UDP = 'udp'


class BaseTraffic():

    @staticmethod
    def factory(tool=None, proto=None):

        if tool and not (tool == NETCAT or tool == SCAPY):
            # tool not supported, return False
            return False

        if not tool and (proto == TCP or proto == UDP):
            tool = NETCAT
        if not tool and not (proto == TCP or proto == UDP):
            tool = SCAPY

        if tool == NETCAT: 
            from netcat_traffic import Netcat    
            return Netcat()
        elif tool == SCAPY:
            from scapy_traffic import Scapy 
            return Scapy()
 
