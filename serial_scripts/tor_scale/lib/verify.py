''' This module provides utils for setting up scale config'''
import copy
import argparse
import random
import fixtures
from contrail_fixtures import *
from user_test import UserFixture
from host_endpoint import HostEndpointFixture
from decimal import Decimal


class VerifyScale(object):

    def __init__(self, inputs, logger, connections, vnc_lib, auth, config_lib_handle):

        self.inputs = inputs
        self.logger = logger
        self.connections = connections
        self.vnc_lib = vnc_lib
        self.auth = auth
        self.config_lib_handle= config_lib_handle 

    def verify_scale_config(self,config_dict,tor_id):

        for pif in self.config_lib_handle.get_physical_port_list(config_dict, tor_id):
      
            # Select a randim VLAN and compute corresponding MAC
            random_vlan=random.randint(3,int(config_dict[tor_id]['lif_num']))
            mac_offset=(self.config_lib_handle.get_physical_port_list(config_dict, tor_id).index(pif) * int(config_dict[tor_id]['lif_num'])) + random_vlan - 2
            bms_mac=self.config_lib_handle.get_mac(config_dict, tor_id, mac_offset) 

            # Get TOR Info from Sanity params
            self.tor_dict, self.tor_info = self.config_lib_handle.get_tor_info(tor_id=tor_id)
            
            # Verify TOR BMS connectivity
            self.logger.info('******Creating a BMS host on TOR %s , port %s ******' % (self.tor_dict['tor_name'], pif))
            if self.create_bms(port_index=0, ns_mac_address=bms_mac, vlan_id=random_vlan, tor_mgmt_ip=config_dict[tor_id]['tor_mgmt_ip']):
                self.logger.info('******Success::BMS host on TOR %s , port %s got IP from TSN******' % (self.tor_dict['tor_name'], pif))     
            else:
                self.logger.error('******FAIL::BMS host on TOR %s , port %s did not get IP******' % (self.tor_dict['tor_name'], pif))     

    def create_bms(self, port_index=0, namespace='ns1',
        ns_intf='tap1', ns_mac_address=None,
        ns_ip_address=None,
        ns_netmask=None,
        ns_gateway=None,
        tor_mgmt_ip=None,
        vlan_id=None,
        verify=True,
        cleanup=True):
        '''Setups up a bms using HostEndpointFixture

            tor_ip : tor mgmt IP 
            port_index : index of the port in tor_hosts dict of 
                         the ToR
            namespace : name of the netns instance
            ns_intf   : Interface name on the netns instance
            ns_mac_address : MAC address of ns_intf on netns instance
            ns_ip_address  : IP Address of ns_intf 
            ns_gateway     : Gateway IP to be assigned to netns 
            vlan_id        : Vlan id to be assigned to ns_intf, default is 
                             untagged
            verify         : If True, does dhclient on the netns intf and 
                             verifies if it has got the expected IP
        '''
        host_info = self.inputs.tor_hosts_data[tor_mgmt_ip][port_index]
        bms_obj = HostEndpointFixture(
            host_ip=host_info['mgmt_ip'],
            namespace=namespace,
            interface=host_info['host_port'],
            username=host_info['username'] or 'root',
            password=host_info['password'] or 'c0ntrail123',
            ns_intf=ns_intf,
            ns_mac_address=ns_mac_address,
            ns_ip_address=ns_ip_address,
            ns_netmask=ns_netmask,
            ns_gateway=ns_gateway,
            connections=self.connections,
            vlan_id=vlan_id,
            tor_name=self.tor_dict['tor_name'])
        
        bms_obj.setUp()
        if verify:
            retval,output = bms_obj.run_dhclient()
            assert retval, "BMS %s did not seem to have got an IP" % (
                bms_obj.name)
            if ns_ip_address:
                self.validate_interface_ip(bms_obj, ns_ip_address)
        
        # Delete the Host endpoint 
        bms_obj.cleanUp()  
        return retval
    # end setup_bms
