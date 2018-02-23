import abc
import logging
from fabric.operations import get, put, run, local, sudo
from fabric.context_managers import settings, hide
from fabric.contrib.files import exists

from jnpr.junos import Device
from jnpr.junos.utils.config import Config
from jnpr.junos.exception import LockError
from jnpr.junos.exception import *

from common import log_orig as contrail_logging

class AbstractConnection(object):
    ''' Abstract connnection class for ssh/netconf etc
    '''
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    def connect(self, *args, **kwargs):
        pass

# end AbstractConnection

    
class SSHConnection(AbstractConnection):
    '''
    :param host     : Mgmt IP of the host 
    :param username
    :param password
    '''
    def __init__(self, host, username='root', password='c0ntrail123',
        logger=None, **kwargs):
        self.host = host
        self.username = username
        self.password = password
        self.handle = None
        self.logger = kwargs.get('logger', contrail_logging.getLogger(__name__))

    def connect(self):
        '''Since its a ssh connection, fab will take care, no action needed
        '''
        pass

    def disconnect(self):
        '''Since its a ssh connection, fab will take care, no action needed
        '''
        pass

    def run_cmd(self, cmds, as_sudo=False):
        cmd_outputs = []
        for cmd in cmds :
            with settings(host_string='%s@%s' % (self.username, self.host),
                password=self.password):
                if as_sudo:
                    output = sudo(cmd)
                else:
                    output = run(cmd, shell=True) 
                self.logger.debug('Command :%s, Succeeded: %s' % (
                    cmd, output.succeeded))
                self.logger.debug('Output:  %s' % (output))
                cmd_outputs.append(output)
        return cmd_outputs

    def exists(self, filepath):
        with settings(host_string='%s@%s' % (self.username, self.host),
            password=self.password):
            return exists(filepath)

# end SSHConnection

class NetconfConnection(AbstractConnection):
    ''' Netconf connection class
    '''
    def __init__(self, host, username='root', password='c0ntrail123',
        logger=None, **kwargs):
        self.host = host
        self.username = username
        self.password = password
        self.handle = None
        self.logger = kwargs.get('logger', contrail_logging.getLogger(__name__))
        self.config_handle = None

        
    def connect(self):
        self.handle = Device(host=self.host, user=self.username, 
            password=self.password)
        try:
            self.handle.open(gather_facts=False)
            self.config_handle = Config(self.handle)
        except (ConnectAuthError,ConnectRefusedError, ConnectTimeoutError,
            ConnectError) as e:
            self.logger.exception(e)
        return self.handle 
    # end connect

    def disconnect(self):
        self.handle.close()

    def show_version(self):
        return self.handle.show_version()

    def config(self, stmts=[], commit=True, ignore_errors=False, timeout = 30):
        for stmt in stmts:
            try:
                self.config_handle.load(stmt, format='set', merge=True)
            except ConfigLoadError,e:
                if ignore_errors:
                    self.logger.debug('Exception %s ignored' % (e))
                    self.logger.exception(e)
                else:
                    raise e
        if commit:
            try:
                self.config_handle.commit(timeout = timeout)
            except CommitError,e:
                self.logger.exception(e)
                return (False,e)
        return (True, None)
    
    def restart(self, process_name):
        #TODO Not sure of apis other than cli
        self.handle.cli('restart %s' % (process_name))

    def get_mac_address(self, interface):
        # Use physical interface
        interface = interface.split('.')[0]
        xml_resp = self.handle.rpc.get_interface_information(interface_name=interface)
        mac_address = xml_resp.findtext(
            'physical-interface/current-physical-address')
        return mac_address.rstrip('\n').lstrip('\n')
    # end get_mac_address

    def get_mac_in_arp_table(self, ip_address):
        # From 'show arp' output, get the MAC address 
        # of a IP 
        xml_resp = self.handle.rpc.get_arp_table_information(no_resolve=True)
        arp_entries = xml_resp.findall('arp-table-entry')
        for arp_entry in arp_entries:
            if arp_entry.find('ip-address').text.strip() == ip_address:
                mac = arp_entry.find('mac-address').text.strip()
                self.logger.debug('Found MAC %s for IP %s in arp table of '
                    '%s' % (mac, ip_address, self.host))
                return mac
        self.logger.warn('IP %s not found in arp table of %s' % (
            ip_address, self.host)) 
        return None
    # end get_mac_in_arp_table 
        

# end NetconfConnection

class ConnectionFactory(object):
    ''' Factory for Connection classes
    '''
    __connection_classes = {
        "juniper": NetconfConnection,
        "openvswitch": SSHConnection,
    }

    @staticmethod
    def get_connection_obj(vendor, *args, **kwargs):
        connection_class = ConnectionFactory.__connection_classes.get(
            vendor.lower(), None)

        if connection_class:
            return connection_class(*args, **kwargs)
        raise NotImplementedError("The requested connection has not been implemented")

if __name__ == "__main__":
    nc = ConnectionFactory.get_connection_obj('juniper',
            host='10.204.216.186', username = 'root', password='c0ntrail123')
