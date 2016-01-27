#! /usr/bin/env python

from scapy.all import *
import sys

ip_remote = sys.argv[1]
ip_local = sys.argv[2]

os.system(
         'iptables -A OUTPUT -p tcp --tcp-flags RST RST -s %s -j DROP' %
            ip_local)

ip=IP(dst=ip_remote)
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
