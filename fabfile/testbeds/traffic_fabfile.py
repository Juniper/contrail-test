"""
This package implements a set of `fabric <http://www.fabfile.org>` tasks to 
provision a Juniper VNS traffic setup. 


"""

from fabric.api import env, parallel, roles, run, settings, sudo, task, cd, execute, local, lcd ,hide
from fabric.state import output
from fabric.operations import get, put

import os
import re
import json
import glob
import string
import socket
import tempfile
import time
import requests
from lxml import etree
from datetime import datetime
from random import randrange
from time import sleep
from traffic_profile import traffic_servers as servers
from traffic_profile import traffic_clients as clients

def setup_hosts():
    resp = requests.get("http://127.0.0.1:8085/Snh_ItfReq?name=")
    xmlout = etree.fromstring(resp.text)
    itf_list=xmlout.xpath('./itf_list/list/ItfSandeshData')

    ip_dict = {}
    env.l2g_map = {}
    for itf in itf_list:
       ipa = itf.xpath('./ip_addr')
       if (len(ipa) == 1) and ipa[0].text != None:
          mipa = itf.xpath('./mdata_ip_addr')
          if mipa[0].text != '0.0.0.0':
              ip_dict[ipa[0].text] = mipa[0].text
              env.l2g_map[mipa[0].text] = ipa[0].text

    env.hosts = []
    for ip in ip_dict:
        env.hosts.append("ubuntu@"+ip_dict[ip])
        env.password = "ubuntu"

def start_servers():
    if not env.host_string:
        return
    curr_host = env.host_string.split('@')[1]

    try:
        sock_dict = servers[env.l2g_map[curr_host]]
    except:
        print "Nothing to be done for %s/%s" %(env.l2g_map[curr_host], curr_host)
        return

    for prot in sock_dict:
        if (prot == 'tcp'):
            for port in sock_dict[prot]:
                command = "/home/ubuntu/traffic/client_server.py -s -t -p " + port
                command = "nohup " + command + " >& /dev/null < /dev/null &"
                print "running %s on %s/%s" %(command, env.host_string, env.l2g_map[curr_host])
                with settings(warn_only = True, timeout=2):
                    try:
                        run(command, pty=False)
                    except:
                        print "FAILED..."

        elif (prot == 'udp'):
            for port in sock_dict[prot]:
                command = "/home/ubuntu/traffic/client_server.py -s -u -p " + port
                command = "nohup " + command + " >& /dev/null < /dev/null &"
                print "running %s on %s/%s" %(command, env.host_string, env.l2g_map[curr_host])
                with settings(warn_only = True, timeout=2):
                    try:
                        run(command, pty=False)
                    except:
                        print "FAILED..."
        else:
            print "Nothing to be done..."
            return

def start_clients():
    if not env.host_string:
        return
    curr_host = env.host_string.split('@')[1]

    try:
        serv_dict = clients[env.l2g_map[curr_host]]
    except:
        return

    for serv in serv_dict:
        for prot in serv_dict[serv]:
            if (prot == 'tcp'):
                for port in serv_dict[serv][prot]:
                    command = "/home/ubuntu/traffic/client_server.py -c -n 1 -t -p " + port + " -i " + serv
                    command = "nohup " + command + " >& /dev/null < /dev/null &"
                    print "running %s on %s/%s" %(command, env.host_string, env.l2g_map[curr_host])
                    with settings(warn_only = True, timeout=2):
                       try:
                           run(command, pty=False)
                       except:
                           print "FAILED..."
            elif (prot == 'udp'):
                for port in serv_dict[serv][prot]:
                    command = "/home/ubuntu/traffic/client_server.py -c -n 1 -u -p " + port + " -i " + serv
                    command = "nohup " + command + " >& /dev/null < /dev/null &"
                    print "running %s on %s/%s" %(command, env.host_string, env.l2g_map[curr_host])
                    with settings(warn_only = True, timeout=2):
                       try:
                           run(command, pty=False)
                       except:
                           print "FAILED..."
            else:
                print "Nothing to be done..."
                return

