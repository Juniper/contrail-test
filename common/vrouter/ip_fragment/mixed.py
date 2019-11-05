#!/usr/bin/env python

from __future__ import print_function
from __future__ import division
from past.utils import old_div
from scapy.all import *
import sys
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    defaults = {
    }
    parser.set_defaults(**defaults)
    parser.add_argument("remoteIP", help="Remote IP")
    parser.add_argument("localIP", help="Local IP")
    parser.add_argument("-i", "--id", help="IP ID")
    parser.add_argument("-o", "--order", type=str, default="1023", help="Order of the fragments, index starting with 0")

    return parser.parse_args(sys.argv[1:])

args = parse_args()
os.system(
         'iptables -A OUTPUT -p tcp --tcp-flags RST RST -s %s -j DROP' %
            args.localIP)

id = int(args.id)
print("using IP id %s" % (id))
ip1=IP(id=id, dst=args.remoteIP)
ip2=IP(id=id+1, dst=args.remoteIP)

packet1=old_div(old_div(ip1,ICMP()),("X"*20))
packet2=old_div(old_div(ip2,ICMP()),("X"*17))
frag1 = fragment(packet1, fragsize=8)
frag2= fragment(packet2, fragsize=8)

send(frag1[1])
send(frag2[0])
send(frag2[2])
send(frag1[3])
send(frag2[1])
send(frag1[0])
send(frag1[2])
send(frag2[3])
