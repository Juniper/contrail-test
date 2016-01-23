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
from common.connections import ContrailConnections
import convertor
from common import log_orig as logging
import test
from serial_scripts.tor_scale.lib.config import ConfigScale
from serial_scripts.tor_scale.lib.verify import VerifyScale


class VerifyScaleSetup(convertor.ReadConfigIni):

    def __init__(self):

        convertor.ReadConfigIni.__init__(self)
        self.ini_file = 'sanity_params.ini'
        self.verify_log_name = 'tor-scale-verify'
        Logger = logging.ContrailLogger(self.verify_log_name)
        Logger.setUp()
        self.logger = Logger.logger

    def get_connections_handle(self):

        self.inputs = ContrailTestInit(self.ini_file, logger=self.logger)
        self.inputs.setUp()
        self.connections = ContrailConnections(self.inputs, self.logger)
        self.vnc_lib = self.connections.vnc_lib
        self.auth = self.connections.auth
        self.lib_config_handle = ConfigScale(
            self.inputs,
            self.logger,
            self.connections,
            self.vnc_lib,
            self.auth)

        self.lib_verify_handle = VerifyScale(
            self.inputs,
            self.logger,
            self.connections,
            self.vnc_lib,
            self.auth,
            self.lib_config_handle)

        self.lib_health_handle = ServerHealth(
            self.inputs,
            self.logger,
            self.connections,
            self.vnc_lib,
            self.auth)

    def verify_one_tor(self, config_dict, tor_id):

        # VNC Lib and other connection
        self.get_connections_handle()

        # Verify BMS 
        self.verification_dhcp_status = self.lib_verify_handle.verify_scale_config(config_dict,tor_id)

if __name__ == "__main__":

    verify = VerifyScaleSetup()
    verify.create_config_dict()
    verify.verify_one_tor(verify.tor_scale_dict, 'TOR1')
