#! /usr/bin/env python

from scapy.all import *
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

# Generate random source port number
port=8100

# Create SYN packet
SYN=ip/TCP(sport=port, dport=8000, flags="S", seq=42)

# Send SYN and receive SYN,ACK
SYNACK=sr1(SYN)
print SYNACK

# Create ACK packet
ACK=ip/TCP(sport=SYNACK.dport, dport=8000, flags="A", seq=SYNACK.ack, ack=SYNACK.seq + 1)

# SEND our ACK packet
send(ACK)

print "SUCCESS"
