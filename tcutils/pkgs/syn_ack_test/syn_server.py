#! /usr/bin/env python

from scapy.all import *
from time import sleep
import sys

ip_remote = sys.argv[1]
ip_local = sys.argv[2]
af = sys.argv[3]

iptables = 'iptables'

if af == 'v6':
    iptables = 'ip6tables'
    ip = IPv6(dst=ip_remote)
elif af == 'v4':
    ip=IP(dst=ip_remote)

os.system(
         '%s -A OUTPUT -p tcp --tcp-flags RST RST -s %s -j DROP' %
            (iptables, ip_local))

server = conf.L3socket(filter='host %s' % ip_remote)
SYN = server.recv()
sleep(182)
SYNACK = ip/TCP(sport=SYN.dport, dport=SYN.sport, flags="SA", seq=1001, ack=SYN.seq + 1)
sr1(SYNACK)

print "SUCCESS"
