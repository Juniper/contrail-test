#!/bin/bash

modprobe pktgen

function pgset() {
   local result

   echo $1 > $PGDEV

   result=$(cat $PGDEV | fgrep "Result: OK:")
   if [ "$result" = "" ]; then
        cat $PGDEV | fgrep Result:
   fi
}

PGDEV=/proc/net/pktgen/kpktgend_0
pgset "rem_device_all"

PGDEV=/proc/net/pktgen/kpktgend_0
pgset "add_device eth0"

PGDEV=/proc/net/pktgen/eth0
pgset "clone_skb 0"
pgset "pkt_size $__pkt_size__"
pgset "count $__count__"
pgset "delay 0"
pgset "dst $__dst_ip__"
pgset "src_min $__src_ip__"
pgset "src_max 10.100.12.252"
pgset "udp_dst_min $__dst_port_mim__"
pgset "udp_dst_max $__dst_port_max__"
pgset "udp_src_min $__src_port_min__"
pgset "udp_src_max $__src_port_max__"


PGDEV=/proc/net/pktgen/pgctrl
echo "Starting...ctrl^C to stop"
pgset "start"
echo "Done
