#!/bin/sh
vif --create vhost0 --mac {{ mac_address }}
ip link set vhost0 up
vif --add {{ interface }} --mac {{ mac_address }} --vrf 0 --type physical --vhost-phys
vif --add vhost0 --mac {{ mac_address }} --vrf 0 --type vhost --xconnect {{ interface }}
dhclient -r
ip addr flush dev {{ interface }}
dhclient vhost0
