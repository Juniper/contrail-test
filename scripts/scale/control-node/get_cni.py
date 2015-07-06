import time
import sys
import os
import re
from commands import Command
from cn_introspect_bgp import ControlNodeInspect
from ssh_interactive_commnds import *
from netaddr import *
from datetime import datetime
from pytz import timezone
import pytz


if __name__ == '__main__':

    # Create logdir if needed
    if not os.path.exists('log'):
        os.mkdir('log')

    # Logfile init
    fd = open("log/get_cn_%s.log" % os.getpid(), 'w')

    # Control node info
    cn_ip = '10.84.7.42'
    cn_username = 'root'
    cn_password = 'c0ntrail123'
    family = 'inet.0'
    family_mcast = 'inetmcast.0'

    # Router info
    rt_ip = '10.84.7.250'
    router_username = 'root'
    router_password = 'Embe1mpls'

    # BGP Scale test info
    nh = '10.84.7.19'
    oper = 'Delete'
    oper = 'Add'
    iterations = 1
    nagents = 1
    nroutes_per_agent = 20

    # xmpp-source is required when running bgp_stress test remotely,
    # note the adderss must be present on the remote machine's
    # interface and pingable from the control node
    # xmpp_src='2.2.1.1'

    # Worked: 100 x 400, 400 x 40, 600 x 10, 800 x 10, 1000 x 10,

    # Router init - ssh connect and login for stats gathering
    rt = remoteCmdExecuter()
    rt.execConnect(rt_ip, router_username, router_password)

    # Control init - ssh connect and login for stats gathering
    cn_shell = remoteCmdExecuter()
    cn_shell.execConnect(cn_ip, cn_username, cn_password)

    # Init for control node introspect queries
    cn = ControlNodeInspect(cn_ip)

    instance_name = 'instance1'
    nagents = 100
    nroutes_per_agent = 5
    xmpp_src = '2.2.1.1'

    # Testing...

    npeers = cn.get_cn_bgp_neighbor_stats_element('count', 'xmpp', 'up')
    print "no instance specified,  num xmpp peers:", npeers

    #it = 'default-domain:demo:c42_t41_block42_n1:c42_t41_block42_n1'
    #npeers = cn.get_cn_bgp_neighbor_stats_element('count', 'xmpp', 'up', it)
    #nprefixes = cn.get_cn_routing_instance_bgp_active_paths(it, family)
    #status, pending_updates = cn.get_cn_routing_instance_table_element (it, family, 'pending_updates')
    # print "INST NAME:%s num xmpp peers:%s nprefixes:%s pending updates:%s"
    # %(it, npeers, nprefixes, pending_updates)

    nblocks = 10
    ninstances = 10
    # for i in range (1,ninstances+1):
    for j in range(1, nblocks + 1):
        for i in range(1, ninstances + 1):
            iname = 'c28_t39_block%s_n%s' % (j, i)
            iname = 'c42_t41_block%s_n%s' % (j, i)
            instance_name = 'default-domain:demo:%s:%s' % (iname, iname)
            npeers = int(cn.get_cn_bgp_neighbor_stats_element(
                'count', 'xmpp', 'up', instance_name))

            #prefixes, paths, primary_paths, secondary_paths and infeasible_paths

            #status, nprefixes = cn.get_cn_routing_instance_table_element (instance_name, family, 'active_paths')
            #status, nprefixes = cn.get_cn_routing_instance_table_element (instance_name, family, 'total_prefixes')
            status, nprefixes = cn.get_cn_routing_instance_table_element(
                instance_name, family, 'prefixes')
            status, paths = cn.get_cn_routing_instance_table_element(
                instance_name, family, 'paths')
            status, primary_paths = cn.get_cn_routing_instance_table_element(
                instance_name, family, 'primary_paths')
            status, secondary_paths = cn.get_cn_routing_instance_table_element(
                instance_name, family, 'secondary_paths')
            status, infeasible_paths = cn.get_cn_routing_instance_table_element(
                instance_name, family, 'infeasible_paths')
            status, pending_updates = cn.get_cn_routing_instance_table_element(
                instance_name, family, 'pending_updates')
            print "INST NAME:%s num peers:%s nprefixes:%s paths:%s primary_paths:%s secondary_paths:%s infeasible_paths:%s pending updates:%s" % (instance_name, npeers, nprefixes, paths, primary_paths, secondary_paths, infeasible_paths, pending_updates)

    # End test cleanup
    fd.close()
