#!/usr/bin/env python

from __future__ import print_function
from __future__ import division
from builtins import range
from past.utils import old_div
from scapy.all import *
import sys
import argparse
import math

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("remoteIP", help="Remote IP")
    parser.add_argument("localIP", help="Local IP")
    parser.add_argument("-p", "--protocol", type=str, default='udp',
        help="Layer 4 protocol", choices=['icmp', 'tcp', 'udp'])
    parser.add_argument("-o", "--order", type=str, default="1023",
        help="Order of the fragments, index starting with 0")
    parser.add_argument("-d", "--data", type=str, default="Z"*20,
        help="Payload")
    parser.add_argument("-f", "--fragsize", type=int, default=8,
        help="Fragment Size")
    parser.add_argument("-s", "--size", type=int, default=0,
        help="Payload Size")
    parser.add_argument("-t", "--tcp_syn", action='store_true',
        help="Send TCP SYN")
    parser.add_argument("-l", "--overlap", action='store_true',
        help="Send overlapping fragments")
    parser.add_argument("-c", "--duplicate", type=int, default=0,
        help="identical/duplicate fragments count")

    return parser.parse_args(sys.argv[1:])

args = parse_args()

METHOD_MAP = {
    'icmp': 'ICMP()',
    'tcp': 'TCP()',
    'udp': 'UDP()'
}
HEADER_SIZE = {
    'icmp': 8,
    'tcp': 20,
    'udp': 8,
}
if args.size:
    payload = "Z" * args.size
else:
    payload = args.data
no_of_frags = int(math.ceil((HEADER_SIZE[args.protocol] + len(payload))/float(args.fragsize)))
os.system(
         'iptables -A OUTPUT -p tcp --tcp-flags RST RST -s %s -j DROP' %
            args.localIP)

id = random.randint(0, 65535)
print("Using IP id %s" % (id))


if args.overlap:
    payload1 = "This is "
    payload2 = "overlapp"
    payload3 = "ing frag"
    proto = 1

    ip=IP(id=id, dst=args.remoteIP, proto=proto, flags=1)
    icmp = ICMP(type=8, code=0, chksum=0xe3eb)
    packet=old_div(old_div(ip,icmp),payload1)
    send(packet)

    ip = IP(id=id, dst=args.remoteIP, proto=proto, flags=1, frag=1)
    packet = old_div(ip,payload2)
    send(packet)

    ip = IP(id=id, dst=args.remoteIP, proto=proto, flags=0, frag=2)
    packet = old_div(ip,payload3)
    send(packet)

    exit()

ip=IP(id=id, dst=args.remoteIP)
proto = eval(METHOD_MAP[args.protocol])

if args.tcp_syn:
    # Create SYN packet
    packet=old_div(old_div(ip,TCP(sport=8100, dport=8000, flags="S", seq=42)),(payload))
else:
    packet=old_div(old_div(ip,proto),(payload))
frag = fragment(packet, fragsize=args.fragsize)

if len(frag) != no_of_frags:
    print("Failure:No. of fragments mismatch for packet length %s, from scapy:%s, expected:%s" % (
        len(packet), len(frag), no_of_frags))
    exit()

#Send the same fragments args.duplicate times
for i in range(args.duplicate):
    send(frag[int(args.order[0])])

for c in args.order:
    send(frag[int(c)])
    print("===================================================")
    print("Sent fragment:")
    frag[int(c)].show()

#Send the remaining fragments if any
if len(frag) > len(args.order):
    for i in range(len(args.order),len(frag)):
        send(frag[i])

