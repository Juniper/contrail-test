import re
import time
import logging
import fixtures
from tcutils.util import retry, search_arp_entry, get_random_name, get_intf_name_from_mac, run_cmd_on_server, get_random_string
from port_fixture import PortFixture
from lif_fixture import LogicalInterfaceFixture

class BMSFixture(fixtures.Fixture):
    def __init__(self,
                 connections,
                 name,
                 tor=None,
                 tor_port=None,
                 host_mac=None,
                 username=None,
                 password=None,
                 mgmt_ip=None,
                 **kwargs
                 ):
        ''' Either VN or Port Fixture is mandatory '''
        self.connections = connections
        self.inputs = connections.inputs
        self.logger = connections.logger
        self.name = name
        bms_dict = self.inputs.bms_data[name]
        self.tor = kwargs.get('tor') or bms_dict['tor']
        self.tor_port = kwargs.get('tor_port') or bms_dict['tor_port']
        self.host_mac = kwargs.get('host_mac') or bms_dict['host_mac'] # To identify the host interface name
        self.mgmt_ip = kwargs.get('mgmt_ip') or bms_dict['mgmt_ip'] # Host IP, optional
        self.username = kwargs.get('username') or bms_dict['username']
        self.password = kwargs.get('password') or bms_dict['password']
        self.namespace = get_random_name('ns')
        self.bms_ip = kwargs.get('bms_ip')   # BMS VMI IP
        self.bms_mac = kwargs.get('bms_mac') # BMS VMI Mac
        self.vn_fixture = kwargs.get('vn_fixture')
        self.port_fixture = kwargs.get('port_fixture')
        self.lif_fixture = kwargs.get('lif_fixture')
        self.security_groups = kwargs.get('security_groups') #UUID List
        self.lif = self.tor_port+'.'+str(kwargs.get('unit', 0))
        self.vnc_h = connections.orch.vnc_h
        self.vlan_id = self.port_fixture.vlan_id if self.port_fixture else \
                       kwargs.get('vlan_id')
        self.bms_created = False
    # end __init__

    def create_lif(self):
        pif_fqname = ['default-global-system-config', self.tor,
                      self.tor_port.replace(':', '__')]
        self.lif_fixture = self.useFixture(LogicalInterfaceFixture(
                                name=self.lif,
                                pif_fqname=pif_fqname,
                                connections=self.connections,
                                vlan_id=self.vlan_id,
                                interface_type=None,
                           ))

    def create_vmi(self):
        fixed_ips = None
        if self.bms_ip:
            fixed_ips = [{'ip_address': self.bms_ip,
                          'subnet_id': self.vn_fixture.vn_subnet_objs[0]['id']
                         }]
        self.port_fixture = self.useFixture(PortFixture(
                                 connections=self.connections,
                                 vn_id=self.vn_fixture.uuid,
                                 mac_address=self.bms_mac,
                                 security_groups=self.security_groups,
                                 fixed_ips=fixed_ips,
                                 vlan_id=self.vlan_id,
                             ))
        if not self.bms_ip:
            self.bms_ip = self.port_fixture.get_ip(
                 self.vn_fixture.vn_subnet_objs[0]['id'])
        if not self.bms_mac:
            self.bms_mac = self.port_fixture.mac_address

    def associate_lif(self):
        self.lif_fixture.add_virtual_machine_interface(self.port_fixture.uuid)

    def disassociate_lif(self):
        self.lif_fixture.delete_virtual_machine_interface(
            self.port_fixture.uuid)

    def run(self, cmd, **kwargs):
        return run_cmd_on_server(cmd, self.mgmt_ip,
                                 username=self.username,
                                 password=self.password,
                                 **kwargs)

    def run_namespace(self, cmd, **kwargs):
        cmd = 'ip netns exec %s %s'%(self.namespace, cmd)
        return self.run(cmd, **kwargs)

    def setup_bms(self):
        self.bms_created = True
        if self.vlan_id:
            self.run('vconfig add %s %s'%(self.physical_intf, self.vlan_id))
        pvlanintf = '%s.%s'(self.physical_intf, self.vlan_id) if self.vlan_id\
                    else self.physical_intf
        self.mvlanintf = '%s-mv%s'%(pvlanintf, get_random_string(4))
        macaddr = 'address %s'%self.bms_mac if self.bms_mac else ''
        self.run('ip link add %s link %s %s type macvlan mode bridge'%(
                 self.mvlanintf, pvlanintf, macaddr))
        self.run('ip netns add %s'%self.namespace)
        self.run('ip link set netns %s %s'%(self.namespace, self.mvlanintf))
        self.run_namespace('ip link set dev %s up'%self.mvlanintf)

    def cleanup_bms(self):
        self.run('ip link delete %s'%self.mvlanintf)
        self.run('ip netns pids %s | xargs kill -9 ' % (self.namespace))
        self.run('ip netns delete %s' % (self.namespace))

    def setUp(self):
        super(BMSFixture, self).setUp()
        try:
            if not self.port_fixture:
                self.create_vmi()
            else:
                self.bms_ip = self.port_fixture.get_ip_addresses[0]

            if not self.lif_fixture:
                self.create_lif()
            self.associate_lif()

            if self.host_mac == self.bms_mac or not self.mgmt_ip:
                self.logger.debug('Not setting up Namespaces')
            self.logger.info('Setting up namespace %s on BMS host %s' % (
                    self.namespace, self.mgmt_ip)) 
            self.physical_intf = get_intf_name_from_mac(self.mgmt_ip,
                                                        self.host_mac,
                                                        username=self.username,
                                                        password=self.password)
            self.setup_bms()
            self.run_dhclient()
        except:
            self.cleanUp()
            raise
    # end setUp

    def verify_on_setup(self):
        info = self.get_interface_info()
        if info['hwaddr'].lower() != self.bms_mac.lower():
            msg = 'BMS Mac address doesnt match. Got %s. Exp %s'%(
                   info['hwaddr'], self.bms_mac)
            assert False, msg
        msg = 'BMS IP address doesnt match. Got %s, Exp %s'%(
               info['inet_addr'], self.bms_ip)
        assert info['inet_addr'] == self.bms_ip, msg

    def cleanUp(self):
        self.logger.info('Deleting namespace %s on BMS host %s' % (
            self.namespace, self.name)) 
        if self.bms_created:
            self.cleanup_bms()
        super(BMSFixture, self).cleanUp()
    # end cleanUp

    def get_interface_info(self):
        '''Returns interface info as a dict from ifconfig output
            Ex : 
            info = { 'up' : True,
                     'hwaddr' : '00:00:00:00:00:01',
                     'inet_addr': '10.1.1.10'
                   }
        '''
        info = {'up': False,
                'hwaddr': None,
                'inet_addr': None}
        output = self.run_namespace('ifconfig %s'%(self.mvlanintf))
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

    def run_dhclient(self, timeout=60):
        #self.run_namespace('dhclient -r -v %s' % (self.mvlanintf))
        output = self.run_namespace('timeout %s dhclient -v %s'%(
                              timeout, self.mvlanintf))
        self.logger.info('Dhcp transaction : %s' % (output))

        if not 'bound to' in output:
            self.logger.warn('DHCP did not complete !!')
            return (False, output)
        return (True, output)
    # end run_dhclient

    def arping(self, ip):
        cmd = 'arping -i %s -c 1 -r %s' % (self.mvlanintf, ip)
        output = self.run_namespace(cmd)
        self.logger.debug('arping to %s returned %s' % (ip, output))
        return (output.succeeded, output)

    def ping(self, ip, other_opt='', size='56', count='5'):
        src_ip = self.bms_ip
        cmd = 'ping -s %s -c %s %s %s' % (
            str(size), str(count), other_opt, ip)
        output = self.run_namespace(cmd)
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

    def get_arp_entry(self, ip_address=None, mac_address=None):
        output = self.run_namespace('arp -an')
        return search_arp_entry(output, ip_address, mac_address)
    # end get_arp_entry

    def get_gateway_ip(self):
        cmd = '''netstat -anr  |grep ^0.0.0.0 | awk '{ print $2 }' '''
        gw_ip = self.run_namespace(cmd)
        return gw_ip
    # end get_gateway_ip

    def get_gateway_mac(self):
        return self.get_arp_entry(ip_address=self.get_gateway_ip())[1]

    def clear_arp(self, all_entries=True, ip_address=None, mac_address=None):
        if ip_address or mac_address:
            (output, ip, mac) = self.get_arp_entry(ip_address, mac_address)
            cmd = 'arp -d %s' % (ip_address)
        elif all_entries:
            cmd = 'ip -s -s neigh flush all'
        output = self.run_namespace(cmd)
        return output
    # end clear_arp

    def start_tcpdump(self, filters=''):
        (session, pcap) = start_tcpdump_for_intf(self.mgmt_ip, self.username,
            self.password, self.mvlanintf, filters, self.logger)
        return (session, pcap)

    def stop_tcpdump(self, session, pcap):
        stop_tcpdump_for_intf(session, pcap, self.logger)
        
    def add_static_arp(self, ip, mac):
        self.run_namespace('arp -s %s %s' % (ip, mac), as_sudo=True)
        self.logger.info('Added static arp %s:%s on BMS %s' % (ip, mac,
                                                              self.name))
