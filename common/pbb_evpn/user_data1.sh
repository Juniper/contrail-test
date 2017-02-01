#!/bin/bash

# Meant for ubuntu-traffic image
# TODO
# Take vlan-id as an argument

echo "auto lo
iface lo inet loopback

auto eth0
iface eth0 inet dhcp
auto eth0.212
iface eth0.212 inet dhcp
vlan-raw-device eth0" > /etc/network/interfaces

/etc/init.d/networking restart
