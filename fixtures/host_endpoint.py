import logging
import fixtures
from fabric.api import env
from fabric.api import run
from fabric.context_managers import settings, hide
import re
import time

from tcutils.util import retry

class HostEndpointFixture(fixtures.Fixture):

    ''' HostEndpointFixture sets up a namespace 
        
        Connection will be of the form
        (Physical network)----p1p2(br-ns1)ovs-tap1----tap1(ns1)
        

        openvswitch is required on host_ip to act as a bridge
        vlan package is also required
    '''

    def __init__(self,
                 host_ip,
                 namespace,
                 username='root',
                 password='c0ntrail123',
                 interface='p1p2',
                 ns_intf='tap1',
                 ns_mac_address=None,
                 ns_ip_address=None,
                 ns_netmask=None,
                 ns_gateway=None,
                 connections=None,
                 vlan_id=None,
                 ):
        self.host_ip = host_ip
        self.username = username
        self.password = password
        self.phy_interface = interface
        self.namespace = namespace
        self.bridge = 'br%s' % (self.namespace)
        self.ns_intf = ns_intf
        self.bridge_intf = 'ovs%s' % (self.ns_intf)
        self.ns_mac_address = ns_mac_address
        self.ns_ip_address = ns_ip_address
        self.ns_netmask = ns_netmask
        self.ns_gateway = ns_gateway
        self.vlan_id = vlan_id
        if vlan_id:
            self.interface = interface + '.' + str(vlan_id)
        else:
            self.interface = interface

        if connections:
            self.logger = connections.inputs.logger
            self.connections = connections
        else:
            self.logger = logging.getLogger(__name__)

    # end __init__

    def setUp(self):
        super(HostEndpointFixture, self).setUp()
        self.logger.info('Setting up namespace %s on BMS host %s' % (
            self.namespace, self.host_ip)) 
        with settings(
            host_string='%s@%s' % (self.username, self.host_ip),
            password=self.password,
                warn_only=True, abort_on_prompts=False):
            if self.vlan_id:
                run('vconfig add %s %s' % (self.phy_interface, self.vlan_id))

            run('ip netns add %s' % (self.namespace))
            time.sleep(1)
            run('ovs-vsctl add-br %s' % (self.bridge))
            time.sleep(1)
            run('ip link set %s up' % (self.bridge))
            run('ovs-vsctl set bridge %s stp_enable=false' % (self.bridge))
            time.sleep(1)
            run('ovs-vsctl add-port %s %s' % (self.bridge, self.interface))
            time.sleep(1)
#            run('ifconfig %s 10.1.1.100/24' % (self.bridge))

            run('ip link add %s type veth peer name %s' % (self.ns_intf,
                                                           self.bridge_intf))
            run('ovs-vsctl add-port %s %s' % (self.bridge, self.bridge_intf))
            time.sleep(1)
            run('ip link set netns %s %s' % (self.namespace, self.ns_intf))
            time.sleep(1)
            if self.ns_mac_address:
                self.set_interface_mac(self.ns_mac_address)
                time.sleep(1)
            if self.ns_ip_address:
                self.set_interface_ip(self.ns_ip_address, self.ns_netmask,
                                      gateway=self.ns_gateway)
            run('ip link set dev %s up' % (self.bridge_intf))
            time.sleep(1)
            run('ip link set dev %s up' % (self.interface))
            time.sleep(1)
            run('ip netns exec %s ip link set dev %s up' % (self.namespace,
                                                            self.ns_intf))
            run('ip netns exec %s ifconfig lo up' % (self.namespace))
            time.sleep(1)

        self.info = self.get_interface_info()
    # end setUp

    def cleanUp(self):
        super(HostEndpointFixture, self).cleanUp()
        self.logger.info('Deleting namespace %s on BMS host %s' % (
            self.namespace, self.host_ip)) 
        with settings(
            host_string='%s@%s' % (self.username, self.host_ip),
            password=self.password,
                warn_only=True, abort_on_prompts=False):
            run('ovs-vsctl del-port %s %s' % (self.bridge, self.bridge_intf))
            time.sleep(1)
            run('ovs-vsctl del-port %s %s' % (self.bridge, self.interface))
            time.sleep(1)
            run('ovs-vsctl del-br %s' % (self.bridge))
            time.sleep(1)
            if self.vlan_id:
                run('vconfig rem %s' % (self.interface))
            run('ip netns exec %s ip link delete tap1' % (self.namespace))
            time.sleep(1)
            run('ip netns pids %s | xargs kill -9 ' % (self.namespace))
            time.sleep(1)
            run('rm -f /run/dhclient.pid; rm -f /var/lib/dhcp/dhclient.leases')
            run('ip netns delete %s' % (self.namespace))
            time.sleep(1)
    # end cleanUp

    def run_cmd(self, cmd, pty=True, timeout=None):
        self.logger.debug("Running Command on namespace %s-%s: (%s)" % (
            self.host_ip, self.namespace, cmd))
        if not timeout:
            timeout = env.timeout
        with settings(
            host_string='%s@%s' % (self.username, self.host_ip),
            password=self.password,
            warn_only=True, abort_on_prompts=False,
                timeout=timeout):
            cmd = 'ip netns exec %s %s' % (self.namespace, cmd)
            output = run('%s' % (cmd), pty=pty)
            self.logger.debug(output)
            return output
    # end run_cmd

    def set_interface_mac(self,  mac, interface=None):
        if not interface:
            interface = self.ns_intf
        if not mac:
            self.logger.debug('ns %s : No MAC to set on interface %s' % (
                self.namespace, interface))
            return

        with settings(
            host_string='%s@%s' % (self.username, self.host_ip),
            password=self.password,
                warn_only=True, abort_on_prompts=False):
            run('ip netns exec %s ip link set %s address %s' % (
                self.namespace, self.ns_intf, mac))

    def set_interface_ip(self,  ip, netmask, gateway=None, interface=None):
        if not interface:
            interface = self.ns_intf
        if not ip:
            self.logger.debug('ns %s : No IP to set on interface %s' % (
                self.namespace, interface))
            return
        with settings(
            host_string='%s@%s' % (self.username, self.host_ip),
            password=self.password,
                warn_only=True, abort_on_prompts=False):
            run('ip netns exec %s ifconfig %s %s netmask %s' % (
                self.namespace, self.ns_intf, ip, netmask))
            if gateway:
                run('ip netns exec %s route add default gw %s' % (self.namespace,
                    gateway))
    # end set_interface_ip

    def get_interface_info(self, interface=None):
        '''Returns interface info as a dict from ifconfig output
            Ex : 
            info = { 'up' : True,
                     'hwaddr' : '00:00:00:00:00:01',
                     'inet_addr': '10.1.1.10'
                   }
        '''
        if not interface:
            interface = self.ns_intf
        info = {'up': False,
                'hwaddr': None,
                'inet_addr': None}
        with settings(
            host_string='%s@%s' % (self.username, self.host_ip),
            password=self.password,
                warn_only=True, abort_on_prompts=False):
            output = run('ip netns exec %s ifconfig %s' % (self.namespace,
                                                           interface))
        info['hwaddr'] = re.search(r'Hwaddr ([:0-9a-z]*)', output,
                                   re.M | re.I).group(1)
        s_obj = re.search(r'inet addr:([\.0-9]*)',
                          output, re.M | re.I)
        if s_obj:
            info['inet_addr'] = s_obj.group(1)
        if 'UP ' in output:
            info['up'] = True
        return info
    # end get_interface_info

    def run_dhclient(self, interface=None, timeout=200):
        if not interface:
            interface = self.ns_intf
        self.run_cmd('ifconfig %s 0.0.0.0' % (interface))
        output = self.run_cmd('dhclient -r -v %s' % (interface))
        output = self.run_cmd('timeout %s dhclient -v %s' % (
                              timeout, interface), timeout=20)
        self.logger.info('Dhcp transaction : %s' % (output))
        if not 'bound to' in output:
            self.logger.warn('DHCP did not complete !!')
            return (False, output)
        else:
            self.info = self.get_interface_info()

        return (True, output)
    # end run_dhclient

    def ping(self, ip, other_opt='', size='56', count='5'):
        src_ip = self.info['inet_addr']
        cmd = 'ping -s %s -c %s %s %s' % (
            str(size), str(count), other_opt, ip)
        output = self.run_cmd(cmd)
        expected_result = ' 0% packet loss'
        try:
            if expected_result not in output:
                self.logger.warn("Ping to IP %s from host %s failed" %
                                 (ip, src_ip))
                return False
            else:
                self.logger.info('Ping to IP %s from host %s passed' %
                                 (ip, src_ip))
            return True
        except Exception as e:
            self.logger.warn("Got exception in ping from host ns ip %s: :%s" % (
                src_ip, e))
            return False
        return False
    # end ping

    @retry(delay=1, tries=10)
    def ping_with_certainty(self, ip, other_opt='', size='56', count='5',
                            expectation=True):
        retval = self.ping(ip, other_opt=other_opt,
                           size=size,
                           count=count)
        return ( retval== expectation )
    # end ping_with_certainty

if __name__ == "__main__":
    host_ip = '10.204.217.16'
    # h_f = HostEndpointFixture(host_ip,'ns1', interface='p1p2',
    # ns_mac_address='fe:d3:bc:f0:ac:05', ns_ip_address='10.1.1.7',
    # ns_netmask='255.255.255.0')
    h_f = HostEndpointFixture(host_ip, 'ns1', interface='p1p2',
                              ns_mac_address='fe:d3:bc:f0:ac:05', vlan_id=5)
    h_f.setUp()
    h_f.run_dhclient()
    import pdb
    pdb.set_trace()
    h_f.cleanUp()
