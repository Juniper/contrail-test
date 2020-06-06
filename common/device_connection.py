from builtins import object
import abc
import logging
from fabric.operations import get, put, run, local, sudo
from fabric.context_managers import settings, hide
from fabric.contrib.files import exists
from tcutils.verification_util import EtreeToDict
from tcutils.gevent_lib import *

from jnpr.junos import Device
from jnpr.junos.utils.config import Config
from jnpr.junos.exception import LockError
from jnpr.junos.exception import *

from common import log_orig as contrail_logging
import gevent
from future.utils import with_metaclass

class AbstractConnection(with_metaclass(abc.ABCMeta, object)):
    ''' Abstract connnection class for ssh/netconf etc
    '''

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
        self.mode = kwargs.get('mode')
        self.port = kwargs.get('port',None)

    def connect(self):
        if self.port:
            self.handle = Device(host=self.host, user=self.username,
                password=self.password, mode=self.mode, port=self.port)
        else:
            self.handle = Device(host=self.host, user=self.username,
                password=self.password, mode=self.mode)
        try:
            self.handle.open(gather_facts=False)
            self.config_handle = Config(self.handle)
        except (ConnectAuthError,ConnectRefusedError, ConnectTimeoutError,
            ConnectError) as e:
            self.logger.exception(e)
        return self.handle
    # end connect

    def disconnect(self):
        with gevent.Timeout(15.0, False):
            self.handle.close()

    def show_version(self):
        return self.handle.show_version()

    def zeroize(self):
        with gevent.Timeout(15.0, False):
            try:
                self.handle.zeroize()
            except Exception as e:
                pass

    def get_config(self, mode='set'):
        configs = self.handle.rpc.get_config(options={'database' : 'committed',
                                                      'format': mode})
        return configs.text

    def get_interfaces(self, terse=True):
        output = self.handle.rpc.get_interface_information(terse=terse)
        return EtreeToDict('physical-interface').get_all_entry(output)

    def get_bgp_peer_count(self):
        output = self.handle.rpc.get_bgp_summary_information()
        return EtreeToDict('peer-count').get_all_entry(output)

    def config(self, stmts=[], commit=True, merge=True, overwrite=False,
               path=None, ignore_errors=False, timeout=30):
        if path:
            self.config_handle.load(path=path, overwrite=overwrite,
                                    timeout=timeout)
        else:
          for stmt in stmts:
            try:
                self.config_handle.load(stmt, format='set', merge=True)
            except ConfigLoadError as e:
                if ignore_errors:
                    self.logger.debug('Exception %s ignored' % (e))
                    self.logger.exception(e)
                else:
                    raise e
        if commit:
            try:
                self.config_handle.commit(timeout=timeout)
            except CommitError as e:
                self.logger.exception(e)
                return (False,e)
        return (True, None)

    def configure_interface(self, pi_name, address, mask):
        stmt = "set interfaces %s unit 0 family inet address %s/%s"%(
            pi_name, address, mask)
        self.config([stmt])

    def delete_interface(self, pi_name):
        stmt = "delete interfaces %s unit 0"%pi_name
        self.config([stmt])
    
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
