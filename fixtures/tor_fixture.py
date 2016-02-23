import os
from netaddr import *
import abc
import time
import re

from jnpr.junos.exception import *
from fabric.operations import get, put, run, local, hide
from fabric.context_managers import settings

import vnc_api_test
from pif_fixture import PhysicalInterfaceFixture
import physical_device_fixture
from tcutils.util import retry


class AbstractToR(object):
    ''' Abstract ToR Switch
    '''
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def restart_ovs(self, *args, **kwargs):
        pass

# end AbstractToR



class ToRFixture(physical_device_fixture.PhysicalDeviceFixture):

    '''Fixture to manage Physical Switch objects

    Mandatory:
    :param name   : name of the device
    :param mgmt_ip  : Management IP

    Optional:
    :param vendor : juniper/openvswitch
    :param model  : optional ,ex : qfx5100
    :param ssh_username : Login username to ssh, default is root
    :param ssh_password : Login password, default is Embe1mpls
    :tunnel_ip      : Tunnel IP (for vtep)
    :ports          : List of Ports which are available to use
    :param tor_ovs_port
    :param controller_ip : vip to which tor connects to in case of HA mode
    :param tor_ovs_protocol     : pssl/tcp
    :param priv_key_file        : private key file (SSL). Default is
                                  contrail-test/tools/tor/sc-privkey.pem 
    :param cert_privkey_file    : Cert for private key file. Default is 
                                  contrail-test/tools/tor/sc-cert.pem 

    Inherited optional parameters:
    :param domain   : default is default-domain
    :param project_name  : default is admin
    :param cfgm_ip  : default is 127.0.0.1
    :param api_port : default is 8082
    :param connections   : ContrailConnections object. default is None
    :param username : default is admin
    :param password : default is contrail123
    :param auth_server_ip : default is 127.0.0.1
    :param logger         : logger object
    '''

    def __init__(self, *args, **kwargs):
        super(ToRFixture, self).__init__(*args, **kwargs)
        self.vendor = kwargs.get('vendor', 'juniper')
        self.model = kwargs.get('model', None)
        self.tunnel_ip = kwargs.get('tunnel_ip', self.mgmt_ip)
        self.controller_ip = kwargs.get('controller_ip', None)
        self.tor_ovs_port = kwargs.get('tor_ovs_port', '6632')
        self.tor_ovs_protocol = kwargs.get('tor_ovs_protocol', 'pssl')
        self.ports = kwargs.get('ports', [])

        # Required for SSL connections
        pwd = os.getcwd()
        self.priv_key_file = kwargs.get('priv_key_file',
            '%s/tools/tor/sc-privkey.pem' % (pwd))
        self.cert_privkey_file = kwargs.get('cert_privkey_file',
            '%s/tools/tor/sc-cert.pem' % (pwd))

        self.bgp_router = None

     # end __init__

    def setUp(self):
        super(ToRFixture, self).setUp()
        self.tor_session = self.get_connection_obj(self.vendor,
            host=self.mgmt_ip,
            username=self.ssh_username,
            password=self.ssh_password,
            logger=self.logger)

    def cleanUp(self):
        super(ToRFixture, self).cleanUp()

    def restart_ovs(self, *args, **kwargs):
        pass

    def get_remote_flood_vtep(self, vn_uuid=None):
        pass

    def get_tor_agents_details(self):
        return self.device_details['tor_agent_dicts']

    def get_active_tor_agent_ip(self, key='ip'):
        ''' Currently TSN and Tor-agent are supposed to have a 1:1 
            relationship
            Get the details from any of the logical switches on the TOR

            Returns mgmt ip by default
            key is host_control_ip for control ip
        '''
        # TODO
        active_tsn_ip = self.get_remote_flood_vtep()
        return self.inputs.host_data[active_tsn_ip][key]
    # end get_active_tor_agent_ip


    def get_backup_tor_agent_ip(self, key='ip'):
        ''' There are only two tsns/TAs possible to be mapped to a TOR

            Returns mgmt ip by default
            key is host_control_ip for control ip
        '''
        active_tsn_ip = self.get_remote_flood_vtep()
        if active_tsn_ip == self.device_details['tor_tsn_ips'][0]:
            index = 1
        if active_tsn_ip == self.device_details['tor_tsn_ips'][1]:
            index = 0
        backup_tsn_ip = self.device_details['tor_tsn_ips'][index]
        return self.inputs.host_data[backup_tsn_ip][key]
    # end get_backup_tor_agent_ip

    def restart_backup_tor_agent(self):
        ''' the tor_agent strings here are of the format 
            root@10.204.216.51:3
        '''
        active_ta = self.get_active_tor_agent_ip()
        tor_agents = self.device_details['tor_agents']
        for tor_agent in tor_agents:
            if active_ta not in tor_agent:
                ta_id =  tor_agent.split('@')[1].split(':')[1]
                ta_ip =  tor_agent.split('@')[1].split(':')[0]
                self.inputs.restart_service('contrail-tor-agent-%s' % (ta_id),
                    [ta_ip])
                time.sleep(20)
    # end restart_backup_tor_agent

    def clear_mac(self, vn_uuid, mac_address):
        pass
        
    def get_other_tor_agent(self, tor_agent_ip):
        pass

    def stop_active_tor_agent(self):
        pass

    def start_active_tor_agent(self):
        pass

# end ToRFixture

class QFXFixture(ToRFixture, AbstractToR):
    def __init__(self, *args, **kwargs):
        super(QFXFixture, self).__init__(*args, **kwargs)
        self.bringup = kwargs.get('bringup', False)
        self.model = kwargs.get('model', 'qfx5100')

    def setUp(self):
        super(QFXFixture, self).setUp()
        if self.bringup:
            if self.tor_ovs_protocol == 'pssl':
                self._copy_certs_to_switch()
            self.config_ovsdb()

    def cleanUp(self):
        super(QFXFixture, self).cleanUp()
        if self.bringup:
            self.remove_ovsdb()

    def _copy_certs_to_switch(self):
        pwd = os.getcwd()
        with settings(host_string='%s@%s' % (self.ssh_username, self.mgmt_ip),
            password=self.ssh_password, shell='/bin/sh -c') :
            put(self.priv_key_file, '/var/db/certs/vtep-privkey.pem')
            put(self.cert_privkey_file, '/var/db/certs/vtep-cert.pem')
            run('rm -f /var/db/certs/ca-cert.pem')

    def _delete_ovsdb_config(self):
        stmts = []
        stmts.append('delete protocols ovsdb')
        try:
            self.tor_session.config(stmts, ignore_errors=True)
        except ConfigLoadError,e:
            self.logger.debug('No ovsdb config present to delete..ok')

    def config_ovsdb(self):
        stmts = []

        # Delete all ovsdb config first 
        self._delete_ovsdb_config()
        if 'pssl' in self.tor_ovs_protocol:
            stmts.append('set protocols ovsdb controller %s protocol ssl port '\
                '%s' % (self.controller_ip, self.tor_ovs_port))
        else:
            stmts.append('set protocols ovsdb passive-connection protocol tcp'
                ' port %s' % (self.tor_ovs_port))
        for port in self.ports:
            stmts.append('set protocols ovsdb interfaces %s' % (port))
        stmts.append('set protocols ovsdb traceoptions file ovsdb.log')
        self.logger.debug('Configuring QFX : ' % (stmts))
        self.tor_session.config(stmts)
        #self.restart_ovs()

    def remove_ovsdb(self):
        stmts = ['delete protocols ovsdb']
        self.logger.debug('Configuring QFX : ' % (stmts))
        self.tor_session.config(stmts)
    # end remove_ovsdb
        
    def restart_ovs(self, *args, **kwargs):
        ''' Ex : ovsdb-server, virtual-tunnel-end-point-management

            setting all_ovs to True will restart both the above procs
        '''
        all_ovs_procs = ['ovsdb-server',
            'virtual-tunnel-end-point-management']
        if args:
            procs_to_restart = args
        else:
            procs_to_restart = all_ovs_procs
        for proc in procs_to_restart:
            self.tor_session.restart(proc)
    # end restart_ovs

    @retry(delay=3, tries=5)
    def is_logical_switch_present(self, vn_id, expectation=True):
        handle = self.tor_session.handle
        xml_resp = handle.rpc.get_ovsdb_logical_switch_information()
        ls_list = [x.text for x in xml_resp.findall(
            'logical-switch/logical-switch-name')]
        if 'Contrail-%s' % (vn_id) in ls_list:
            self.logger.debug('Logical switch for VN %s seen on ToR' % (
                vn_id))
        else:
            self.logger.debug('Logical switch for VN %s not seen on ToR' % (
                vn_id))
        result = 'Contrail-%s' % (vn_id) in ls_list
        return (result == expectation)
    # end is_logical_switch_present

    def get_remote_flood_vtep(self, vn_uuid=None):
        '''
            Returns the current flood vtep on the TOR
            If VN UUID is passed, lookup is done for the corresponding logical
            switch.
            If VN UUID is not passed, the first logical switch seen is picked
        '''
        if vn_uuid:
            logical_switch = 'Contrail-%s' % (vn_uuid)
        else:
            logical_switch = None
        handle = self.tor_session.handle
        if logical_switch:
            xml_resp = handle.rpc.get_ovsdb_mac_routes_information(remote=True,
                logical_switch=logical_switch)
        else:
            xml_resp = handle.rpc.get_ovsdb_mac_routes_information(remote=True)
        entries = xml_resp.findall('vtep-mac-routes')
        for entry in entries:
            mac = entry.find('mac').text
            vtep_ip = entry.find('vtep-address').text
            if mac == 'ff:ff:ff:ff:ff:ff':
                return vtep_ip
    # end get_remote_flood_vtep

    def clear_mac(self, vn_uuid, mac_address):
        handle = self.tor_session.handle
        vlan_name = 'Contrail-%s' % (vn_uuid)
        handle.rpc.clear_ethernet_switching_table(address=mac_address,
                                                  vlan_name=vlan_name)
        self.logger.info('Cleared MAC %s in MAC table of %s on %s' % (
            mac_address, vlan_name, self.name))
        # Workaround to avoid backup having the cleaned up mac for 5 min
        # Restart the backup tor-agent
        self.restart_backup_tor_agent()
    # end clear_mac

    # TODO
    # Enable this method once a clean solution is found for openvswitch also
#    def get_vxlan_id_on_tor(self, vn_id):
#        vn_ls_name = 'Contrail-%s' % (vn_id)
#        handle = self.tor.session.handle
#        xml_resp = handle.rpc.get_ovsdb_logical_switch_information()
#        ls_xml = [x for xml_resp.findall('logical-switch')]
#        for ls in ls_xml:
#            ls_name = ls.findtext('logical-switch-name')
#            if ls_name == vn_ls_name:
#                tunnel_key = ls.findtext('tunnel-key')
#                return tunnel_key
#        return None
#    # end get_vxlan_id_on_tor
        

class OpenVSwitchFixture(ToRFixture, AbstractToR):
    '''
    The openvswitch node should be running Ubuntu 14.04 atleast
    ssh_username should be a sudo user (no password prompt)

    Optional:
    :param bringup : Bringup a new openvswitch. Default is False
                     Setup is assumed to be brought up earlier

    '''
    def __init__(self, *args, **kwargs):
        super(OpenVSwitchFixture, self).__init__(*args, **kwargs)
        self.bringup = kwargs.get('bringup', False)
        self.timeout = kwargs.get('timeout', '200')

        self.common_cmd_str = 'timeout %s bash -x contrail-ovs-tool.sh --name %s '\
            '-t %s ' % (self.timeout, self.name, self.tunnel_ip)
        if self.tor_ovs_protocol == 'pssl':
            self.remote = ' -r ssl:%s:%s ' % (self.controller_ip, self.tor_ovs_port)
        else:
            self.remote = ' -r ptcp:%s ' % (self.tor_ovs_port)
        self.common_cmd_str += '%s' % (self.remote) 
        pwd = os.getcwd()
        self.cacert_file = '/tmp/%s-cacert.pem' % (self.name)

    def setUp(self):
        super(OpenVSwitchFixture, self).setUp()
        self._copy_tool_to_ovs_node()
        if self.bringup:
            self.config_ovsdb()

    def cleanUp(self):
        super(OpenVSwitchFixture, self).cleanUp()

        # Workaround for issue in ovs-vtep where the local-macs 
        # are not deleted on deleting the bindings
        # We manually go ahead and clear the local-macs 
        # so that tor-agent deletes the logical switch
        self.delete_all_local_macs()

        if self.bringup:
            self.delete_ports()
            self.remove_ovsdb()

    def delete_all_local_macs(self):
        ls_list = self.get_all_logical_switches()
        for ls in ls_list:
            self.vtep_ctl('clear-local-macs %s' % (ls))

    def ovs_vsctl(self, args):
        if self.tor_session.exists('/var/run/openvswitch/db-%s.sock ' % (
            self.name)):
            prefix = '--db=unix:/var/run/openvswitch/db-%s.sock ' % (self.name)
        else:
            prefix = ''
        args = prefix + args
        output = self.tor_session.run_cmd(['ovs-vsctl %s' % (args)])
        return output[0]
    # end ovs_vsctl

    def vtep_ctl(self, args):
        if self.tor_session.exists('/var/run/openvswitch/db-%s.sock ' % (
            self.name)):
            prefix = '--db=unix:/var/run/openvswitch/db-%s.sock ' % (self.name)
        else:
            prefix = ''
        args = prefix + args 

        output = self.tor_session.run_cmd(['vtep-ctl %s' % (args)])
        return output[0]
    # end vtep_ctl

    def _copy_tool_to_ovs_node(self):
        '''
        Copies the tool contrail-ovs-tool.sh to the openvswitch node
        Std ovs-vtep does not have a way to work with non-default db
        So copy the patched ovs-vtep to the node
        '''
        pwd = os.getcwd()
        with settings(hide('everything'),host_string='%s@%s' % (
                self.ssh_username, self.mgmt_ip),
                password=self.ssh_password):
            put('%s/tools/tor/contrail-ovs-tool.sh' % (pwd))
            put('%s/tools/tor/ovs-vtep' % (pwd),
                '/usr/share/openvswitch/scripts/ovs-vtep')
            self.logger.debug('Copied contrail-ovs-tool.sh and ovs-vtep ',
                ' to %s' % (self.mgmt_ip))
            if self.tor_ovs_protocol == 'pssl':
                self.remote_home = run('pwd')
                put(self.priv_key_file)
                put(self.cert_privkey_file)
                run('rm -f %s' % (self.cacert_file))

                self.ssl_args = ' -p %s/sc-privkey.pem -c %s/sc-cert.pem '\
                    '-b %s ' % (self.remote_home, self.remote_home,
                        self.cacert_file)
                self.common_cmd_str += '%s' % (self.ssl_args)

    def _run_ovs_tool_cmd(self, cmd):
        output = self.tor_session.run_cmd([cmd], as_sudo=True)
        if output[0].failed:
            self.logger.error('Ovs tool cmd %s on node %s failed! ' % (
                cmd, self.mgmt_ip))
        else:
            self.logger.debug('Started ovs tool with cmd : %s' % (
                cmd))
    # end _run_ovs_tool_cmd

    def config_ovsdb(self):
        start_cmd = self.common_cmd_str + ' -T init'
        self._run_ovs_tool_cmd(start_cmd)
        self.add_ports()
    # end config_ovsdb 

    def remove_ovsdb(self):
        stop_cmd = self.common_cmd_str + ' -T stop'
        self._run_ovs_tool_cmd(stop_cmd)

    def stop_ovsdb(self):
        return self.remove_ovsdb()

    def restart_ovs(self):
        restart_cmd = self.common_cmd_str + ' -T restart'
        self._run_ovs_tool_cmd(restart_cmd)

    def start_ovs(self):
        stop_cmd = self.common_cmd_str + ' -T start'
        self._run_ovs_tool_cmd(start_cmd)

    def delete_ports(self, ports=[]):
        if ports:
            ports_to_delete = ports
        else:
            ports_to_delete = self.ports
        socket = '--db unix:/var/run/openvswitch/db-%s.sock ' % (self.name)
        for port in ports_to_delete:
            cmds = [
                'ovs-vsctl %s del-port %s %s' % (socket, self.name, port),
                'ip link delete %s ' % (port),
            ]
            self.run_cmd(cmds)
    # end delete_ports

    def add_ports(self, ports=[]):
        if ports:
            ports_to_add = ports
        else:
            ports_to_add = self.ports
        for port in ports_to_add:
            hostport = 'host%s' % (port)
            socket = '--db unix:/var/run/openvswitch/db-%s.sock ' % (self.name)
            cmds = [
                'ip link delete %s || echo ok ' % (port),
                'ip link add %s type veth peer name %s' % (
                    hostport, port),
                'ovs-vsctl %s add-port %s %s' % (socket, self.name, port),
                'ifconfig %s up' % (port),
            ]
            self.tor_session.run_cmd(cmds, as_sudo=True)
    # end add_ports

    @retry(delay=3, tries=5)
    def is_logical_switch_present(self, vn_id, expectation=True):
        output = self.vtep_ctl('list-ls')
        result = 'Contrail-%s' % (vn_id) in output
        return (result == expectation)
    # end is_logical_switch_present

    def get_any_logical_switch_present(self):
        output = self.vtep_ctl('list-ls| head -1')
        return output
    # end get_any_logical_switch_present

    def get_all_logical_switches(self):
        output = self.vtep_ctl('list-ls')
        if not output:
            return []
        lines = output.split('\n')
        return lines

    def get_remote_flood_vtep(self, vn_uuid=None):
        ''' 
            Returns the current flood vtep on the TOR
            If VN UUID is passed, lookup is done for the corresponding logical
            switch.
            If VN UUID is not passed, the first logical switch seen is picked
        '''
        if vn_uuid:
            logical_switch = 'Contrail-%s' % (vn_uuid)
        else:
            logical_switch = self.get_any_logical_switch_present()
        output = self.vtep_ctl('list-remote-macs %s| grep unknown-dst' % (logical_switch))
        match = re.search('vxlan_over_ipv4/(.*)', output)
        if match:
            ip = match.group(1)
        return ip
    # end get_remote_flood_vtep
        
    def clear_mac(self, vn_uuid, mac_address):
        logical_switch = 'Contrail-%s' % (vn_uuid)
        self.vtep_ctl('del-ucast-local %s %s' % (logical_switch, mac_address))

        self.logger.info('Cleared MAC %s in MAC table of %s on %s' % (
            mac_address, logical_switch, self.name))
        # Workaround to avoid backup having the cleaned up mac for 5 min
        # Restart the backup tor-agent
        self.restart_backup_tor_agent()
        # Ovs-vtep doesnt learn MACs automatically after clearing MAC
        # Restart ovs-vtep for now
        self.restart_ovs()
    # end clear_mac 


class ToRFixtureFactory(object):
    ''' Factory for ToR classes
    '''
    __tor_classes = {
        "juniper": QFXFixture,
        "openvswitch": OpenVSwitchFixture,
    }

    @staticmethod
    def get_tor(*args, **kwargs):
        vendor = kwargs.get('vendor', 'juniper')
        tor_class = ToRFixtureFactory.__tor_classes.get(
            vendor.lower(), None)

        if tor_class:
            return tor_class(*args, **kwargs)
        raise NotImplementedError("The requested ToR has not been implemented")


# end ToRFixtureFactory
if __name__ == "__main__":
    ovs_fix = ToRFixtureFactory.get_tor( 'bng-contrail-qfx51-1', '10.204.218.10', vendor='juniper', ssh_username='root', ssh_password='c0ntrail123',
        tunnel_ip='99.99.99.99', ports=['ge-0/0/0'], tor_ovs_port='9999', tor_ovs_protocol='pssl', controller_ip='10.204.216.184')
    ovs_fix.setUp()
    ovs_fix._copy_certs_to_switch()
    ovs_fix.config_ovsdb()
    #ovs_fix.restart_ovs()
    #ovs_fix.remove_ovsdb()

    ovs_fix1 = ToRFixtureFactory.get_tor( 'br0', '10.204.216.195', vendor='openvswitch', ssh_username='root', ssh_password='c0ntrail123',
        tunnel_ip='10.204.216.195', ports=['torport1'], tor_ovs_port='6632', tor_ovs_protocol='pssl', controller_ip='10.204.216.184')
    ovs_fix1.setUp()
    ovs_fix1.config_ovsdb()

    #ovs_fix2 = ToRFixtureFactory.get_tor( 'br1', '10.204.216.195', vendor='openvswitch', ssh_username='root', ssh_password='c0ntrail123',
    #    tunnel_ip='10.204.216.195', ports=['torport2'], tor_ovs_port='6633', tor_ovs_protocol='pssl', controller_ip='10.204.216.184')
    #ovs_fix2.setUp()
    #ovs_fix2.config_ovsdb()
        
    pass
