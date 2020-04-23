from builtins import str
import re
import copy
import time
import logging
import fixtures
import string
from tcutils.util import retry, search_arp_entry, get_random_name, get_intf_name_from_mac, run_cmd_on_server, get_random_string, get_af_type
from port_fixture import PortFixture
from virtual_port_group import VPGFixture
import tempfile
from tcutils.fabutils import *
dir_path = os.path.dirname(os.path.realpath(__file__))
BROADCAST_SCRIPT = dir_path+'/../tcutils/broadcast.py'

class BMSFixture(fixtures.Fixture):
    def __init__(self,
                 connections,
                 name,
                 is_ironic_node=False,
                 **kwargs
                 ):
        ''' Either VN or Port Fixture is mandatory '''
        self.connections = connections
        self.inputs = connections.inputs
        self.logger = connections.logger
        self.name = name
        self.is_ironic_node = is_ironic_node
        bms_dict = self.inputs.bms_data[name]
        self.interfaces = kwargs.get('interfaces') or bms_dict['interfaces']
        self.mgmt_ip = kwargs.get('mgmt_ip') or bms_dict['mgmt_ip'] # Host IP, optional
        self.username = kwargs.get('username') or bms_dict['username']
        self.password = kwargs.get('password') or bms_dict['password']
        self.namespace = get_random_name('ns')
        self.bms_ip = kwargs.get('bms_ip')   # BMS VMI IP
        self.bms_ip6 = kwargs.get('bms_ip6')   # BMS VMI IPv6
        self.bms_ip_netmask = kwargs.get('bms_ip_netmask', None)
        self.bms_ip6_netmask = kwargs.get('bms_ip6_netmask', None)
        self.vn_fixture = kwargs.get('vn_fixture')
        self.bms_gw_ip = kwargs.get('bms_gw_ip', None)
        self.bms_gw_ip6 = kwargs.get('bms_gw_ip6', None)
        self.bms_mac = kwargs.get('bms_mac') # BMS VMI Mac
        self.static_ip = kwargs.get('static_ip', bool(not self.inputs.get_csn()))
        self.port_fixture = kwargs.get('port_fixture')
        self.fabric_fixture = kwargs.get('fabric_fixture')
        self.security_groups = kwargs.get('security_groups') or list()
        self.vnc_h = connections.orch.vnc_h
        self.vlan_id = self.port_fixture.vlan_id if self.port_fixture else \
                       kwargs.get('vlan_id') or 0
        self.port_profiles = kwargs.get('port_profiles') or list()
        self.tor_port_vlan_tag = kwargs.get('tor_port_vlan_tag')
        self._port_group_name = kwargs.get('port_group_name', None)
        self.ep_style = kwargs.get('ep_style', True)
        self._vpg_fixture = None
        self.bond_name = kwargs.get('bond_name') or 'bond%s'%get_random_string(2,
                         chars=string.ascii_letters)
        self.bms_created = False
        self.bond_created = False
        self.mvlanintf = None
        self._interface = None
        self.ironic_node_obj = None
        self.ironic_node_id = None
        self.copied_files = dict()
    # end __init__

    def read_ironic_node_obj(self):
        try:
          if not self.ironic_node_id:
            self.ironic_node_obj = self.connections.ironic_h.obj.node.get(self.name)
            self.ironic_node_id = self.ironic_node_obj.uuid
          else:
            self.ironic_node_obj = self.connections.ironic_h.obj.node.get(self.name)
        except Exception as e:
            self.ironic_node_obj = None

    def create_bms_node(self,ironic_node_name,port_list,driver_info,properties):
        if not self.ironic_node_obj:
           self.read_ironic_node_obj()
        if self.ironic_node_obj:
           self.logger.info("Ironic node: %s already present, not creating it"%self.name)
           self.logger.info("node-id:%s"%self.ironic_node_obj.uuid)
           return self.ironic_node_obj
        else:
           self.logger.info("Creating Ironic node: %s "%self.name)
           return self.connections.ironic_h.create_ironic_node(ironic_node_name,port_list,driver_info,properties)

    def set_bms_node_state(self,new_state):
        if not self.ironic_node_id:
           self.read_ironic_node_obj()
        self.connections.ironic_h.set_ironic_node_state(self.ironic_node_obj.uuid,new_state)

    def delete_bms_node(self):
        if not self.ironic_node_obj.uuid:
           self.read()
        if not self.ironic_node_obj:
           self.logger.info("BMS Ironic node %s not present, skipping delete "%self.name)
           return
        self.delete_ironic_node()

    def create_vmi(self, interfaces=None):
        interfaces = interfaces or self.interfaces
        fixed_ips = list()
        if self.bms_ip:
            fixed_ips.append({'ip_address': self.bms_ip,
                'subnet_id': self.vn_fixture.get_subnet_id_for_af('v4')[0]
                })
        if self.bms_ip6:
            fixed_ips.append({'ip_address': self.bms_ip6,
                'subnet_id': self.vn_fixture.get_subnet_id_for_af('v6')[0]
                })
        bms_info = list()
        for interface in interfaces:
            intf_dict = dict()
            intf_dict['switch_info'] = interface['tor']
            intf_dict['port_id'] = interface['tor_port']
            intf_dict['fabric'] = self.fabric_fixture.name
            bms_info.append(intf_dict)
        binding_profile = {'local_link_information': bms_info}
        security_groups = None if self.ep_style else self.security_groups
        self.port_fixture = PortFixture(
                                 connections=self.connections,
                                 vn_id=self.vn_fixture.uuid,
                                 mac_address=self.bms_mac,
                                 security_groups=security_groups,
                                 fixed_ips=fixed_ips,
                                 api_type='contrail',
                                 vlan_id=self.vlan_id,
                                 binding_profile=binding_profile,
                                 port_group_name=self._port_group_name,
                                 tor_port_vlan_tag=self.tor_port_vlan_tag,
                             )
        self.port_fixture.setUp()
        self.add_port_profiles(self.port_profiles)
        if self.ep_style:
            self.add_security_groups(self.security_groups)

    @retry(delay=10, tries=30)
    def is_lacp_up(self, interfaces=None, expectation=True):
        interfaces = interfaces or self.interfaces
        status = self.is_bonding_up(interfaces, verify_lacp=True)
        if not status:
            self.logger.warn("Bond interfaces status on "
                             "%s is not as expected"%self.name)
            return False
        return True

    def is_bonding_up(self, interfaces, verify_lacp=False, expectation=True):
        output = self.run("cat /proc/net/bonding/%s"%self.bond_name)
        pattern = "Permanent HW addr: ([:0-9a-z]*).*?partner lacp.*?mac address: ([:0-9a-z]*)"
        match = re.findall(pattern, output, re.M | re.I | re.S)
        if not match:
            if expectation:
                self.logger.debug("Bond interface is down")
                return False
            return True
        mac_map = dict(match)
        for interface in interfaces or self.interfaces:
            mac = interface['host_mac']
            if mac not in mac_map:
                self.logger.debug("Interface %s of BMS %s is not bonded"%(
                    mac, self.name))
                return False
            if verify_lacp:
                if mac_map[mac] == "00:00:00:00:00:00" and expectation:
                    self.logger.debug("Lacp on interface %s of BMS %s is down"%(
                        mac, self.name))
                    return False
                elif mac_map[mac] != "00:00:00:00:00:00" and not expectation:
                    self.logger.debug("Lacp on interface %s of BMS %s is still up"%(
                        mac, self.name))
                    return False
        self.logger.debug("Bond interfaces are up")
        return True

    @property
    def port_group_name(self):
        if not self._port_group_name and self.port_fixture:
            vpg_fqname = self.get_vpg_fqname()
            if vpg_fqname:
                self._port_group_name = vpg_fqname[-1]
        return self._port_group_name

    def get_vpg_fqname(self):
        return self.port_fixture.get_vpg_fqname()

    @property
    def vpg_fixture(self):
        if not self._vpg_fixture:
            self._vpg_fixture = VPGFixture(self.fabric_fixture.name,
                                           connections=self.connections,
                                           name=self.port_group_name)
            self._vpg_fixture.setUp()
        return self._vpg_fixture

    def add_port_profiles(self, port_profiles):
        self.vpg_fixture.add_port_profiles(port_profiles)

    def delete_port_profiles(self, port_profiles):
        self.vpg_fixture.delete_port_profiles(port_profiles)

    def detach_physical_interface(self, interfaces):
        to_create_vmis = list()
        for interface in self.interfaces:
            for detach_vmi in interfaces:
                if interface['tor'] == detach_vmi['tor'] and \
                   interface['tor_port'] == detach_vmi['tor_port']:
                    to_detach = True
                    break
            else:
                to_create_vmis.append(interface)
        self.update_vmi(to_create_vmis, self.port_group_name)

    def attach_physical_interface(self, interfaces):
        to_create_vmis = copy.deepcopy(self.interfaces)
        to_create_vmis.extend(interfaces)
        self.update_vmi(to_create_vmis, self.port_group_name)

    def update_vmi(self, interfaces, port_group_name, fabric=None):
        bms_info = list()
        for interface in interfaces:
            intf_dict = dict()
            intf_dict['switch_info'] = interface['tor']
            intf_dict['port_id'] = interface['tor_port']
            intf_dict['fabric'] = fabric or self.fabric_fixture.name
            bms_info.append(intf_dict)
        binding_profile = {'local_link_information': bms_info or None}
        self.port_fixture.update_bms(binding_profile,
            port_group_name=port_group_name)
        self.interfaces = interfaces

    def update_vlan_id(self, vlan_id):
        self.port_fixture.update_vlan_id(vlan_id)
        self.cleanup_bms()
        self.vlan_id = vlan_id
        self.setup_bms()

    def delete_vmi(self):
        if self.port_fixture:
            self.port_fixture.cleanUp()
            if hasattr(self.port_fixture, '_cleanups') and \
               self.port_fixture._cleanups is None \
               and hasattr(self.port_fixture, '_clear_cleanups'):
                self.port_fixture._clear_cleanups()
        self.bms_ip = None
        self.bms_ip6 = None
        self.bms_mac = None
        self.port_fixture = None
        self._port_group_name = None
        self._vpg_fixture = None

    def get_bms_ips(self, af=None):
        if not af:
            af = self.inputs.get_af()
        af = ['v4', 'v6'] if 'dual' in af else af
        return [ip for ip in [self.bms_ip, self.bms_ip6]
                if (get_af_type(ip) and get_af_type(ip) in af)]

    def run(self, cmd, **kwargs):
        output = run_cmd_on_server(cmd, self.mgmt_ip,
                                   username=self.username,
                                   password=self.password,
                                   **kwargs)
        self.logger.debug('Executing cmd %s on %s returned %s'%(
                          cmd, self.mgmt_ip, output))
        return output

    def run_namespace(self, cmd, **kwargs):
        cmd = 'ip netns exec %s %s'%(self.namespace, cmd)
        return self.run(cmd, **kwargs)

    def get_mvi_interface(self):
        self.logger.info('BMS interface: %s' % self.mvlanintf)
        return self.mvlanintf

    def config_mroute(self,interface,address,mask):
        self.run('ifconfig %s multicast' %(self._interface))
        self.run_namespace('route -n add -net %s  netmask %s dev %s' %(address,mask,interface)) 
 
    def copy_file_to_bms(self, localfile, dstdir=None, force=False):
        if not force and localfile in self.copied_files and \
           self.copied_files[localfile] == dstdir:
            self.logger.debug('File %s already copied'%localfile)
            return True
        dest_dir = '%s@%s:%s' % (self.username, self.mgmt_ip, dstdir or '')
        remote_copy(localfile, dest_dir, dest_password=self.password,
                    with_sudo=True)
        time.sleep(2)
        self.copied_files[localfile] = dstdir
    # end copy_file_to_vm

    def send_broadcast_traffic(self, dport=1111):
        destfile = '/tmp/broadcast.py'
        random_name = get_random_name()
        pid_file = '/tmp/broadcast-%s.pid'%random_name
        stats_file = '/tmp/broadcast-%s.stats'%random_name
        log_file = '/tmp/broadcast-%s.log'%random_name
        self.copy_file_to_bms(BROADCAST_SCRIPT, destfile)
        cmd = 'python %s --dports %s --pid_file %s --stats_file %s'%(
            destfile, dport, pid_file, stats_file)
        cmd = cmd + ' 0<&- &> %s'%log_file
        self.run_namespace(cmd, as_sudo=True)
        return pid_file

    def stop_broadcast_traffic(self, pid_file):
        cmd = 'kill $(cat %s)'%(pid_file)
        self.run_namespace(cmd, as_sudo=True)

    def run_python_code(self, code, as_sudo=True, as_daemon=False, pidfile=None, stdout_path=None, stderr_path=None):

        folder = tempfile.mkdtemp()

        filename_short = 'program.py'
        filename = '%s/%s' % (folder, filename_short)
        fh = open(filename, 'w')
        fh.write(code)
        fh.close()

        dest_login = '%s@%s' % (self.username,self.mgmt_ip)
        dest_path = dest_login + ":/tmp"
        remote_copy(filename, dest_path, dest_password=self.password, with_sudo=True)

        if as_daemon:
            pidfile = pidfile or "/tmp/pidfile_%s.pid" % (get_random_name())
            pidfilename = pidfile.split('/')[-1]
            stdout_path = stdout_path or "/tmp/%s_stdout.log" % pidfilename
            stderr_path = stderr_path or "/tmp/%s_stderr.log" % pidfilename
            cmd = "python /tmp/%s 1>%s 2>%s" % (filename_short,stdout_path,stderr_path)
            outputs = self.run_namespace( cmd, as_sudo=as_sudo, as_daemon=as_daemon, pidfile=pidfile)
        else:
            cmd = "python /tmp/%s" % (filename_short)
            outputs = self.run_namespace( cmd, as_sudo=as_sudo, as_daemon=as_daemon)

    def delete_bonding(self, interfaces=None):
        for interface in interfaces or self.interfaces:
            physical_intf = get_intf_name_from_mac(self.mgmt_ip,
                                                   interface['host_mac'],
                                                   username=self.username,
                                                   password=self.password)
            self.run('ip link set %s down'%(physical_intf))
            self.run('ip link set %s nomaster'%(physical_intf))
        self.run('ip link delete %s'%self.bond_name)

    def remove_interface_from_bonding(self, interfaces):
        self.add_remove_interface_from_bonding(interfaces, remove=True)

    def add_interface_to_bonding(self, interfaces):
        self.add_remove_interface_from_bonding(interfaces)

    def add_remove_interface_from_bonding(self, interfaces, remove=False):
        for interface in interfaces:
           physical_intf = get_intf_name_from_mac(self.mgmt_ip,
                                                  interface['host_mac'],
                                                  username=self.username,
                                                  password=self.password)
           if remove:
               self.run('ip link set %s down'%(physical_intf))
               self.run('ip link set %s nomaster'%(physical_intf))
           else:
               self.run('ip link set %s down'%(physical_intf))
               self.run('ip link set %s master %s'%(physical_intf, self.bond_name))
               self.run('ip link set %s up'%(physical_intf))

    def create_bonding(self, interfaces=None):
        interfaces = interfaces or self.interfaces
        if self.is_bonding_up(interfaces):
            return self.bond_name
        self.delete_bonding(interfaces=interfaces)
        self.bond_created = True
        self.run('ip link add %s type bond mode 802.3ad'%self.bond_name)
        self.run('modprobe bonding mode=802.3ad lacp_rate=fast')
        self.run('ip link add %s type bond'%self.bond_name)
        self.run('ip link set %s up'%self.bond_name)
        self.add_interface_to_bonding(interfaces)
        return self.bond_name

    def setup_bms(self, interfaces=None):
        interfaces = interfaces or self.interfaces
        self.bms_created = True
        if len(interfaces) > 1:
            self._interface = self.create_bonding(interfaces)
        else:
            host_mac = interfaces[0]['host_mac']
            self._interface = get_intf_name_from_mac(self.mgmt_ip,
                                               host_mac,
                                               username=self.username,
                                               password=self.password)
            self.logger.info('BMS interface: %s' % self._interface)
        self.run('ip link set dev %s up'%(self._interface))
        if self.vlan_id:
            # self.run('vconfig add %s %s'%(self._interface, self.vlan_id))
            # Removing the dependency on vconfig
            self.run('ip link add link {ifc} name {ifc}.{vlan} type vlan id '
                     '{vlan}'.format (ifc=self._interface, vlan=self.vlan_id))
            self.run('ip link set dev %s.%s up'%(self._interface, self.vlan_id))
        pvlanintf = '%s.%s'%(self._interface, self.vlan_id) if self.vlan_id\
                    else self._interface
        self.run('ip link set dev %s up'%pvlanintf)
        mvlanintf = '%s-%s'%(pvlanintf,
            get_random_string(2, chars=string.ascii_letters))
        # Truncate the interface name length to 15 char due to linux limitation
        self.mvlanintf = mvlanintf[-15:]
        self.logger.info('BMS mvlanintf: %s' % self.mvlanintf)
        macaddr = 'address %s'%self.bms_mac if self.bms_mac else ''
        self.run('ip link add %s link %s %s type macvlan mode bridge'%(
                 self.mvlanintf, pvlanintf, macaddr))

        self.run('ip netns add %s'%self.namespace)
        self.run('ip link set netns %s %s'%(self.namespace, self.mvlanintf))
        self.run_namespace('ip link set dev %s up'%self.mvlanintf)

    def assign_static_ip(self, v4_ip=None, v4_gw_ip=None,
                         v6_ip=None, v6_gw_ip=None, flush=False):
        if flush is True:
            self.run_namespace('ip addr flush dev %s'%(self.mvlanintf))
        if v4_ip:
            addr = v4_ip + '/' + str(self.bms_ip_netmask)
            self.run_namespace('ip addr add %s dev %s'%(addr, self.mvlanintf))
        if v4_gw_ip:
            self.run_namespace('ip route add default via %s'%(v4_gw_ip))
        if v6_ip:
            addr = v6_ip + '/' + str(self.bms_ip6_netmask)
            self.run_namespace('ip addr add %s dev %s'%(addr, self.mvlanintf))
        if v6_gw_ip:
            self.run_namespace('ip -6 route add default via %s'%(v6_gw_ip))

    def cleanup_bms(self, interfaces=None):
        interfaces = interfaces or self.interfaces
        if getattr(self, 'mvlanintf', None):
            self.run('ip link delete %s'%self.mvlanintf)
        if getattr(self, 'namespace', None):
            self.run('ip netns pids %s | xargs kill -9 ' % (self.namespace))
            self.run('ip netns delete %s' % (self.namespace))
        if self.vlan_id:
            # self.run('vconfig rem %s.%s'%(self._interface, self.vlan_id))
            # Removing the dependency on vconfig
            self.run('ip link delete %s.%s'%(self._interface, self.vlan_id))
        if len(interfaces) > 1 and self.bond_created:
            self.delete_bonding()

    def setUp(self):
        super(BMSFixture, self).setUp()
        if self.is_ironic_node:
           return
        try:
            if not self.port_fixture:
                self.create_vmi()
            if not self.bms_ip and not self.bms_ip6:
                for address in self.port_fixture.get_ip_addresses():
                    if get_af_type(address) == 'v4':
                        self.bms_ip = address
                    elif get_af_type(address) == 'v6':
                        self.bms_ip6 = address
            if not self.bms_mac:
                self.bms_mac = self.port_fixture.mac_address
            if not self.bms_gw_ip and not self.bms_gw_ip6:
                for subnet in self.vn_fixture.vn_subnet_objs:
                    if get_af_type(subnet['gateway_ip']) == 'v4':
                        self.bms_gw_ip = subnet['gateway_ip']
                    elif get_af_type(subnet['gateway_ip']) == 'v6':
                        self.bms_gw_ip6 = subnet['gateway_ip']
            if not self.bms_ip_netmask and not self.bms_ip6_netmask:
                for subnet in self.vn_fixture.vn_subnet_objs:
                    if get_af_type(subnet['cidr']) == 'v4':
                        self.bms_ip_netmask = subnet['cidr'].split('/')[1]
                    if get_af_type(subnet['cidr']) == 'v6':
                        self.bms_ip6_netmask = subnet['cidr'].split('/')[1]
            host_macs = [intf['host_mac'] for intf in self.interfaces]
            if self.bms_mac in host_macs or not self.mgmt_ip:
                self.logger.debug('Not setting up Namespaces')
                return
            self.logger.info('Setting up namespace %s on BMS host %s' % (
                    self.namespace, self.mgmt_ip)) 
            self.setup_bms()
        except:
            try:
                self.cleanUp()
                self._clear_cleanups()
            finally:
                raise
    # end setUp

    def verify_on_setup(self):
        assert self.fabric_fixture.name in self.port_fixture.get_vpg_fqname()
        info = self.get_interface_info()
        if info['hwaddr'].lower() != self.bms_mac.lower():
            msg = 'BMS Mac address doesnt match. Got %s. Exp %s'%(
                   info['hwaddr'], self.bms_mac)
            assert False, msg
        if self.bms_ip:
            msg = 'BMS IP address doesnt match. Got %s, Exp %s'%(
               info['inet_addr'], self.bms_ip)
            assert info['inet_addr'] == self.bms_ip, msg
        if self.bms_ip6:
            msg = 'BMS IP address doesnt match. Got %s, Exp %s'%(
               info['inet6_addr'], self.bms_ip6)
            assert info['inet6_addr'] == self.bms_ip6, msg

    def cleanUp(self):
        self.logger.info('Deleting namespace %s on BMS host %s' % (
            self.namespace, self.name)) 
        if self.bms_created:
            self.cleanup_bms()
        self.delete_vmi()
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
                'inet_addr': None,
                'inet6_addr': None}
        output = self.run_namespace('ip addr show dev %s'%(self.mvlanintf))
        info['hwaddr'] = re.search(r'ether ([:0-9a-z]*)', output,
                                   re.M | re.I).group(1)
        s_obj = re.search(r'inet ([\.0-9]*)', output, re.M | re.I)
        if s_obj:
            info['inet_addr'] = s_obj.group(1)
        s_obj = re.search(r'inet6 ([\.0-9a-f\:]*)/[0-9]+ scope global',
            output, re.M | re.I)
        if s_obj:
            info['inet6_addr'] = s_obj.group(1)
        if 'UP ' in output:
            info['up'] = True
        return info
    # end get_interface_info

    def _run_dhclient(self, af='v4', timeout=60, expectation=True):
        af = '-6 ' if af == 'v6' else ''
        output = self.run_namespace('timeout %s dhclient -v %s %s'%(
                              timeout, af, self.mvlanintf))
        self.logger.debug('Dhcp transaction : %s' % (output))
        if not 'bound to' in output.lower() and expectation:
            self.logger.warn('DHCP did not complete !!')
            return (False, output)
        elif 'bound to' in output.lower() and not expectation:
            self.logger.warn('DHCP should have failed')
            return (False, output)
        return (True, output)

    @retry(delay=5, tries=10)
    def run_dhclient(self, timeout=60, expectation=True):
        if self.static_ip:
            self.logger.debug("Configuring static ip as requested")
            self.assign_static_ip(v4_ip=self.bms_ip, v4_gw_ip=self.bms_gw_ip,
                                  v6_ip=self.bms_ip6, v6_gw_ip=self.bms_gw_ip6)
            return (True, None)
        self.run('pkill -9 dhclient')
        if self.bms_ip:
            result, output = self._run_dhclient(af='v4',
                timeout=timeout,
                expectation=expectation)
            if not result:
                return (result, output)
        if self.bms_ip6:
#            result, output = self._run_dhclient(af='v6',
#                timeout=timeout,
#                expectation=expectation)
            # Workaround to assign gw ip manually for v6
            self.assign_static_ip(v6_ip=self.bms_ip6, v6_gw_ip=self.bms_gw_ip6)
        return (result, output)
    # end run_dhclient

    @retry(tries=2, delay=2)
    def arping(self, ip):
        cmd = 'arping -I %s -c 2 %s' % (self.mvlanintf, ip)
        output = self.run_namespace(cmd)
        self.logger.debug('arping to %s returned %s' % (ip, output))
        return (output.succeeded, output)

    def ping(self, ip, other_opt='', size='56', count='5', expectation=True):
        src_ip = self.bms_ip6 if get_af_type(ip) == 'v6' else self.bms_ip
        ping = 'ping6' if get_af_type(ip) == 'v6' else 'ping'
        cmd = '%s -s %s -c %s %s %s' % (
            ping, str(size), str(count), other_opt, ip)
        output = self.run_namespace(cmd)
        if expectation:
            expected_result = ' 0% packet loss'
        else:
            expected_result = '100% packet loss'
        try:
            if expected_result not in output:
                self.logger.warn("Ping to IP %s from host %s(%s) should have %s"
                %(ip, src_ip, self.name, "passed" if expectation else "failed"))
                return False
            else:
                self.logger.info('Ping to IP %s from host %s(%s) %s as expected'
                %(ip, src_ip, self.name, "passed" if expectation else "failed"))
            return True
        except Exception as e:
            self.logger.warn("Got exception in ping from host ns ip %s: %s" % (
                src_ip, e))
            return False
    # end ping

    @retry(delay=1, tries=10)
    def ping_with_certainty(self, ip, other_opt='', size='56', count='5',
                            expectation=True):
        return self.ping(ip, other_opt=other_opt,
                         size=size,
                         count=count,
                         expectation=expectation)
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

    def add_security_groups(self, security_groups):
        if self.ep_style:
            self.vpg_fixture.add_security_groups(security_groups)
        else:
            self.port_fixture.add_security_groups(security_groups)

    def delete_security_groups(self, security_groups):
        if self.ep_style:
            self.vpg_fixture.delete_security_groups(security_groups)
        else:
            self.port_fixture.delete_security_groups(security_groups)
