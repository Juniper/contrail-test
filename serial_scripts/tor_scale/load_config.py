import argparse
import random
import socket
import struct
import os
import sys
import time
import string
import unicodedata
from netaddr import *
from datetime import datetime
from common.contrail_test_init import ContrailTestInit
import logging as std_logging
from neutronclient.neutron import client as neutron_client
from vnc_api.vnc_api import *
from common.connections import ContrailConnections
import convertor
from common import log_orig as logging
import test
from serial_scripts.tor_scale.lib.config import ConfigScale


class ConfigScaleSetup(convertor.ReadConfigIni):

    def __init__(self):

        convertor.ReadConfigIni.__init__(self)
        self.ini_file = 'sanity_params.ini'
        self.log_name = 'tor-scale.log'
        Logger = logging.ContrailLogger(self.log_name)
        Logger.setUp()
        self.logger = Logger.logger

    def get_connections_handle(self):

        self.inputs = ContrailTestInit(self.ini_file, logger=self.logger)
        self.connections = ContrailConnections(self.inputs, self.logger)
        self.vnc_lib = self.connections.vnc_lib
        self.auth = self.connections.auth
        self.lib_handle = ConfigScale(
            self.inputs,
            self.logger,
            self.connections,
            self.vnc_lib,
            self.auth)

    def config_one_tor(self, config_dict, tor_id):

        # VNC Lib and other connection
        self.get_connections_handle()

        # Get TOR Info from Sanity params
        self.tor_dict, self.tor_info = self.lib_handle.get_tor_info(
            tor_id=tor_id)

        create_new_vn = 1
        num_lif_in_systems = 1

        # Config project
        self.project_handle = self.lib_handle.create_project(
            project_name=self.lib_handle.get_project_name(
                config_dict,
                tor_id))
        self.lib_handle.create_and_attach_user_to_tenant(
            user=tor_id,
            password=tor_id)

        for pif in self.lib_handle.get_physical_port_list(config_dict, tor_id):

            # Config Physical Intreface
            self.pif_handle = self.lib_handle.create_pif(pif_name=pif,
                                                         device_id=self.tor_info.uuid)

            lif_count = int(config_dict[tor_id].get('lif_num', None))
            lif_count = int(lif_count) + 3

            for lif in range(3, lif_count):

                if create_new_vn:

                    # Config VN
                    self.vn_handle = self.lib_handle.create_vn(vn_name=self.lib_handle.get_vn_name(self.lib_handle.get_vxlan_id(config_dict,
                                                                                                                                tor_id, num_lif_in_systems)),
                                                               vn_subnet=[
                        self.lib_handle.get_subnet(
                            config_dict,
                            tor_id,
                            num_lif_in_systems)],
                        project_name=self.lib_handle.get_project_name(
                        config_dict,
                        tor_id),
                        project_obj=self.project_handle,
                        vxlan_id=self.lib_handle.get_vxlan_id(config_dict, tor_id, num_lif_in_systems))
                # Crete VMI (BMS Server)
                self.vmi_obj = self.lib_handle.create_vmi(vn_id=self.vn_handle.uuid,
                                                          mac_address=self.lib_handle.get_mac(config_dict, tor_id, num_lif_in_systems))

                # Config Logical Intreface
                self.lig_handle = self.lib_handle.create_lif(lif_name=self.lib_handle.get_lif_name(pif, lif),
                                                             pif_id=self.pif_handle,
                                                             vlan_id=lif,
                                                             vmi_objs=[self.vmi_obj])

                num_lif_in_systems = num_lif_in_systems + 1
                create_new_vn = num_lif_in_systems % self.lib_handle.get_num_vmi_per_vn(
                    config_dict,
                    tor_id)
if __name__ == "__main__":

    config = ConfigScaleSetup()
    config.create_config_dict()
    config.config_one_tor(config.tor_scale_dict, 'TOR3')
