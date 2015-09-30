''' This module provides utils for setting up scale config'''
import copy
import argparse
import random
import socket
import struct
import sys
import time
from netaddr import *
import fixtures
from vn_policy_test import *
from vnc_api_test import *
from vm_test import *
from contrail_fixtures import *
import project_test
import vn_test
import pif_fixture
import port_fixture
import lif_fixture
from user_test import UserFixture
from tcutils.agent.vna_introspect_utils import *
from vnc_api import vnc_api
from vnc_api.gen.resource_test import *
from common.policy import policy_test_helper
from decimal import Decimal


class ConfigScale(object):

    def __init__(self, inputs, logger, connections, vnc_lib, auth):

        self.inputs = inputs
        self.logger = logger
        self.connections = connections
        self.vnc_lib = vnc_lib
        self.auth = auth

    def create_project(self, project_name):

        self.project_name = project_name
        self.user = project_name
        self.password = project_name
        # time.sleep(4)
        try:
            self.project = project_test.ProjectFixture(project_name=self.project_name, auth=self.auth,
                                                       vnc_lib_h=self.vnc_lib, username=self.user, password=self.password,
                                                       connections=self.connections)
            self.project.setUp()
        except Exception as e:
            self.logger.warn("got exception as %s" % (e))
        finally:
            return self.project

    def create_and_attach_user_to_tenant(self, user, password):
        self.auth.create_user(user, password)
        self.auth.add_user_to_project(user, self.project_name)
        self.auth.add_user_to_project('admin', self.project_name)
        time.sleep(1)

    def create_vn(
            self, vn_name, vn_subnet, project_name, project_obj, vxlan_id):

        self.vn_name = vn_name
        self.vn_subnet = vn_subnet
        self.project_name = project_name
        self.project_obj = project_obj
        self.vxlan_id = vxlan_id

        time.sleep(1)
        try:
            self.vn = vn_test.VNFixture(project_name=self.project_name, connections=self.connections,
                                        inputs=self.inputs, vn_name=self.vn_name, subnets=self.vn_subnet,
                                        project_obj=self.project_obj,
                                        option='api',
                                        vxlan_id=self.vxlan_id)
            self.vn.setUp()
        except Exception as e:
            self.logger.warn("got exception as %s" % (e))
        finally:
            return self.vn

    def create_pif(self, pif_name, device_id):

        time.sleep(1)
        try:
            self.pif_fixture = pif_fixture.PhysicalInterfaceFixture(pif_name,
                                                                    device_id=device_id,
                                                                    connections=self.connections)
            self.pif_fixture.setUp()
        except Exception as e:
            self.logger.warn("got exception as %s" % (e))
        finally:
            return self.pif_fixture

    def create_vmi(self, vn_id, fixed_ips=[],
                   mac_address=None,
                   security_groups=[],
                   extra_dhcp_opts=[]):
        if mac_address:
            mac_address = EUI(mac_address)
            mac_address.dialect = mac_unix
        # time.sleep(1)
        try:

            self.port_fixture = port_fixture.PortFixture(
                vn_id,
                mac_address=mac_address,
                fixed_ips=fixed_ips,
                security_groups=security_groups,
                extra_dhcp_opts=extra_dhcp_opts,
                connections=self.connections,
            )
            self.port_fixture.setUp()
        except Exception as e:
            self.logger.warn("got exception as %s" % (e))
        finally:
            return self.port_fixture

    def create_lif(self, lif_name, pif_id, vlan_id, vmi_objs=[]):
        try:
            self.lif_fixture = lif_fixture.LogicalInterfaceFixture(
                lif_name,
                pif_id=pif_id.uuid,
                vlan_id=vlan_id,
                vmi_ids=[x.uuid for x in vmi_objs],
                connections=self.connections)
            self.lif_fixture.setUp()
        except Exception as e:
            self.logger.warn("got exception as %s" % (e))
        finally:
            return self.lif_fixture

  
    def get_tor_info(self, tor_id):
        tor_id = tor_id.replace("TOR", "")
        tor_dict = self.inputs.tor_agent_data
        for (k,v) in tor_dict.items():
            for item in v:
                if item['tor_id'] == tor_id:
                    tor_obj = self.vnc_lib.physical_router_read(
                        fq_name=['default-global-system-config', item['tor_name']])
                    return item, tor_obj

    def get_project_name(self, scale_dict, tor_id):
        tor_dict = scale_dict[tor_id]
        return tor_dict.get('project', None)

    def get_project_name(self, scale_dict, tor_id):
        tor_dict = scale_dict[tor_id]
        return tor_dict.get('project', None)

    def get_physical_port_list(self, scale_dict, tor_id):
        tor_dict = scale_dict[tor_id]
        return tor_dict.get('pif_list', None).split(',')

    def get_vn_name(self, itr):

        vn_name = 'vn-test' + '-' + str(itr)
        return vn_name

    def get_subnet(self, scale_dict, tor_id, ip_incr):

        base_ip = scale_dict[tor_id].get('subnet_ip', None).split('/')[0]
        prefix = scale_dict[tor_id].get('subnet_ip', None).split('/')[1]
        powerof = 32 - int(prefix)
        incr_factor = 2 ** powerof
        ip2int = lambda ipstr: struct.unpack('!I', socket.inet_aton(ipstr))[0]
        base_ip_int = (ip2int(base_ip))
        new_ip_int = base_ip_int + incr_factor * int(ip_incr)
        int2ip = lambda n: socket.inet_ntoa(struct.pack('!I', n))
        new_ip = (int2ip(new_ip_int))
        cidr = new_ip + '/' + str(prefix)
        return cidr

    def get_mac(self, scale_dict, tor_id, offset):

        base_mac = scale_dict[tor_id].get('initial_mac', None).split('/')[0]
        offset = int(offset)
        base_mac = base_mac.replace(":", "")
        mac_addr = EUI("{:012X}".format(int(base_mac, 16) + offset))
        mac_address = EUI(mac_addr)
        mac_address.dialect = mac_unix
        return mac_address

    def get_lif_name(self, pif, lif):
        lif_name = str(pif) + '.' + str(lif)
        return lif_name

    def get_num_vmi_per_vn(self, scale_dict, tor_id):

        lif_per_pif = int(scale_dict[tor_id].get('lif_num', None))
        pif_num = len(self.get_physical_port_list(scale_dict, tor_id))
        vn_num = int(scale_dict[tor_id].get('vn_number', None))
        lif_per_vn = lif_per_pif * pif_num / vn_num
        return lif_per_vn

    def get_vxlan_id(self, scale_dict, tor_id, itr):
        tor_dict = scale_dict[tor_id]
        vxlan_id = tor_dict.get('initial_vxlan_id', None)
        vxlan_id = int(vxlan_id) + int(itr)
        return vxlan_id
