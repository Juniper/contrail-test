from builtins import str
import random
import time
from tcutils.tcpdump_utils import *
from common.base import GenericTestBase
from router_fixture import LogicalRouterFixture
import copy
import re
from security_group import SecurityGroupFixture, get_secgrp_id_from_name
from common.neutron.base import BaseNeutronTest
from common.fabric_utils import FabricUtils
from bms_fixture import BMSFixture
from vm_test import VMFixture
from tcutils.util import Singleton, skip_because, get_random_vxlan_id, get_an_ip
from tcutils.util import create_netns, delete_netns, get_intf_name_from_mac, run_dhcp_server
from future.utils import with_metaclass
from netaddr import *

class FabricSingleton(with_metaclass(Singleton, type('NewBase', (FabricUtils, GenericTestBase), {}))):
    def __init__(self, connections):
        self.vnc_h = connections.orch.vnc_h
        self.invoked = False
        self.connections = connections
        self.inputs = connections.inputs
        self.logger = connections.logger

    def create_fabric(self, rb_roles=None, enterprise_style=True, ztp=False, dc_asn=None):
        self.invoked = True
        fabric_dict = self.inputs.fabrics[0]
        if ztp:
            self.fabric, self.devices, self.interfaces = \
                self.onboard_fabric(fabric_dict, cleanup=False,
                    enterprise_style=enterprise_style)
        else:
            self.fabric, self.devices, self.interfaces = \
                self.onboard_existing_fabric(fabric_dict, cleanup=False,
                    enterprise_style=enterprise_style)
            if len(self.inputs.fabrics) > 1:
                fabric_dict = self.inputs.fabrics[1]
                self.fabric2, self.devices2, self.interfaces2 = \
                self.onboard_existing_fabric(fabric_dict, cleanup=False,
                    enterprise_style=enterprise_style, dc_asn=dc_asn)
                assert self.interfaces2, 'Failed to onboard existing fabric %s'%fabric_dict
                self.logger.info("Assigning roles for devices in the fabric2")
                self.assign_roles(self.fabric2, self.devices2, rb_roles=rb_roles)
        assert self.interfaces, 'Failed to onboard fabric %s'%fabric_dict

        self.logger.info("Assigning roles for devices in the fabric")
        self.assign_roles(self.fabric, self.devices, rb_roles=rb_roles)
        if ztp:
            self.logger.info("Create provisioning infra network")
            self.infra_ipam, self.infra_vn, self.tag_id = \
                self.create_provisioning_network(self.fabric, fabric_dict)
            self.logger.info("Import server node profile")
            self.cards, self.hardwares, self.node_profiles = \
                self.create_server_node_profile(self.fabric,
                    fabric_dict, self.infra_vn.vn_name)
            self.logger.info("Import server topology")
            self.servers, self.ports = \
                self.create_server_object(self.fabric, fabric_dict)

    def create_ironic_provision_vn(self, admin_connections):
        bms_lcm_config = self.inputs.bms_lcm_config
        if not bms_lcm_config.get('ironic_provision_vn'):
            return
        ironic_net_name = bms_lcm_config["ironic_provision_vn"]["name"]
        ironic_cidr = bms_lcm_config["ironic_provision_vn"]["subnet"]

        services_ip = [self.inputs.internal_vip] if self.inputs.internal_vip\
            else self.inputs.openstack_ips
        self.ironic_vn = self.create_only_vn(
            connections=admin_connections,
            vn_name=ironic_net_name,
            vn_subnets=[ironic_cidr],
            router_external=True, shared=True,
            dns_nameservers_list=services_ip)
        self.inputs.restart_container(self.inputs.openstack_ips,
            'ironic_conductor')
        for device in self.devices:
            device.add_virtual_network(self.ironic_vn.uuid)

        self.update_nova_quota()
        time.sleep(120)

    def update_nova_quota(self):
        self.connections.nova_h.update_quota(self.connections.project_id,
            ram=-1, cores=-1)

    def cleanup(self):
        del self.__class__._instances[self.__class__]
        if self.invoked and getattr(self, 'fabric', None):
            if getattr(self, 'ironic_vn', None):
                for device in self.devices:
                    device.delete_virtual_network(self.ironic_vn.uuid)
                self.ironic_vn.cleanUp()
            if getattr(self, 'servers', None):
                for port in self.ports:
                    self.vnc_h.delete_port(id=port)
                for server in self.servers:
                    self.vnc_h.delete_node(id=server)
            if getattr(self, 'cards', None):
                for np in self.node_profiles:
                    self.vnc_h.delete_node_profile(id=np)
                for hardware in self.hardwares:
                    self.vnc_h.delete_hardware(id=hardware)
                for card in self.cards:
                    self.vnc_h.delete_card(id=card)
            if getattr(self, 'infra_vn', None):
                self.infra_vn.cleanUp()
                self.infra_ipam.cleanUp()
                self.vnc_h.delete_tag(id=self.tag_id)
            super(FabricSingleton, self).cleanup_fabric(self.fabric,
                self.devices, self.interfaces)
            if len(self.inputs.fabrics) > 1:
                super(FabricSingleton, self).cleanup_fabric(self.fabric2,
                    self.devices2, self.interfaces2)

class BaseFabricTest(BaseNeutronTest, FabricUtils):
    enterprise_style = True
    ztp = False
    dci_mode = 'ibgp'
    @classmethod
    def setUpClass(cls):
        super(BaseFabricTest, cls).setUpClass()
        cls.vnc_h = cls.connections.orch.vnc_h
        cls.bms = dict(); cls.spines = list();
        cls.leafs = list(); cls.pnfs = list()
        cls.default_sg = cls.get_default_sg()
        cls.allow_default_sg_to_allow_all_on_project(cls.inputs.project_name)
        cls.current_encaps = cls.get_encap_priority()
        cls.set_encap_priority(['VXLAN', 'MPLSoGRE', 'MPLSoUDP'])
        cls.vnc_h.enable_vxlan_routing()
        cls.rb_roles = dict()
        cls.dci_ebgp_asn = None

    @skip_because(function='is_test_applicable')
    def setUp(self):
        super(BaseFabricTest, self).setUp()
        self.allow_all_on_default_fwaas_policy()
        obj = FabricSingleton(self.connections)
        self.singleton = obj
        if not obj.invoked:
            try:
                obj.create_fabric(self.rb_roles,
                    enterprise_style=self.enterprise_style, ztp=self.ztp,
                    dc_asn=self.dci_ebgp_asn if self.dci_mode == 'ebgp' else None)
            except:
                obj.cleanup()
            if self.inputs.is_ironic_enabled:
                obj.create_ironic_provision_vn(self.admin_connections)
        assert obj.fabric and obj.devices and obj.interfaces 
        if len(self.inputs.fabrics) > 1:
            assert obj.fabric2 and obj.devices2, "Onboarding fabric failed"
            self.fabric2 = obj.fabric2
            self.devices2 = obj.devices2
        self.fabric = obj.fabric
        self.devices = obj.devices
        self.interfaces = obj.interfaces
        self._populate_attrs()

    def _populate_attrs(self):
        self.leafs = list(); self.spines = list(); self.pnfs = list()
        for device in self.devices:
            role = self.get_role_from_inputs(device.name)
            if role == 'spine':
                self.spines.append(device)
            elif role == 'leaf':
                self.leafs.append(device)
            elif role == 'pnf':
                self.pnfs.append(device)

    def is_test_applicable(self):
        if not self.inputs.fabrics or not self.inputs.physical_routers_data \
           or not self.inputs.bms_data:
            return (False, 'skipping not a fabric environment')
        return (True, None)

    def is_bms_on_node(self, device_name):
        for name, prop in self.inputs.bms_data.items():
            for interface in prop.get('interfaces') or []:
                if interface['tor'] == device_name:
                    return True

    def get_rb_roles(self, device_name):
        for device in self.inputs.physical_routers_data.values():
            if device['name'] == device_name:
                return device.get('rb_roles') or []

    def get_bms_nodes(self, role='leaf', bms_type=None,
                      no_of_interfaces=0, rb_role=None, devices=None):
        bms, dummy = self.filter_bms_nodes(role=role, bms_type=bms_type,
                         no_of_interfaces=no_of_interfaces,
                         rb_role=rb_role, devices=devices)
        return bms and list(bms)

    def filter_bms_nodes(self, bms_type=None, no_of_interfaces=0,
                         role='leaf', rb_role=None, devices=None,
                         min_bms_count=1):
        device_names = set()
        for device in devices or list():
            device_names.add(device.name)
        bms_nodes = self.inputs.bms_data
        regular_nodes = set()
        multi_homed_nodes = set()
        lag_nodes = set()
        interfaces_filtered = set()
        msg = "Unable to find BMS of type %s with interfaces %s"%(bms_type,
            no_of_interfaces)
        for name, details in bms_nodes.items():
            if role and role not in [self.get_role_from_inputs(interface['tor'])
               for interface in details['interfaces']]:
                continue
            if rb_role and not all([rb_role in self.get_rb_roles(
               interface['tor']) for interface in details['interfaces']]):
                continue
            devices = set()
            for interface in details['interfaces']:
                devices.add(interface['tor'])
            if device_names and devices.difference(device_names):
                continue
            if len(details['interfaces']) >= no_of_interfaces:
                interfaces_filtered.add(name)
            if len(details['interfaces']) == 1:
                regular_nodes.add(name)
                continue
            if len(devices) > 1:
                multi_homed_nodes.add(name)
            else:
                lag_nodes.add(name)

        if bms_type == "multi_homing":
           nodes = multi_homed_nodes.intersection(interfaces_filtered)
        elif bms_type == 'link_aggregation':
           nodes = lag_nodes.intersection(interfaces_filtered)
        elif bms_type == 'single_interface':
           nodes = regular_nodes.intersection(interfaces_filtered)
        else:
           nodes = interfaces_filtered

        msg = "Unable to find %s BMS node of type %s with interfaces %s" % (
               min_bms_count if min_bms_count > 1 else 'a',
               bms_type, no_of_interfaces)
        if len(nodes) < min_bms_count:
            return None, msg
        return nodes, msg

    def get_associated_prouters(self, bms_name, interfaces=None):
        bms_node = self.inputs.bms_data[bms_name]
        devices = set()
        for interface in interfaces or bms_node['interfaces']:
             devices.add(interface['tor'])
        return [device for device in self.devices if device.name in devices]

    @classmethod
    def tearDownClass(cls):
        obj = FabricSingleton(cls.connections)
        try:
            obj.cleanup()
        finally:
            if getattr(cls, 'current_encaps', None):
                cls.set_encap_priority(cls.current_encaps)
            cls.vnc_h.disable_vxlan_routing()
            super(BaseFabricTest, cls).tearDownClass()

    def _my_ip(self, fixture):
        if type(fixture) == VMFixture:
            return fixture.get_vm_ips()
        elif type(fixture) == BMSFixture:
            return fixture.get_bms_ips()

    def do_ping_mesh(self, fixtures, expectation=True):
        list_of_ips = list()
        for fixture in fixtures:
            list_of_ips.extend(self._my_ip(fixture))
        for fixture in fixtures:
            for ip in set(list_of_ips) - set(self._my_ip(fixture)):
                fixture.clear_arp()
                assert fixture.ping_with_certainty(ip, expectation=expectation)

    def clear_arps(self, bms_fixtures):
        for bms_fixture in bms_fixtures:
            bms_fixture.clear_arp(all_entries=True)
    # end clear_arps

    def validate_arp(self, bms_fixture, ip_address=None,
                     mac_address=None, expected_mac=None,
                     expected_ip=None, expectation=True):
        ''' Method to validate IP/MAC
            Given a IP and expected MAC of the IP,
            or given a MAC and expected IP, this method validates it
            against the arp table in the BMS and returns True/False
        '''
        (ip, mac) = bms_fixture.get_arp_entry(ip_address=ip_address,
                                              mac_address=mac_address)
        search_term = ip_address or mac_address
        if expected_mac :
            result = False
            if expected_mac == mac:
                result = True
            assert result == expectation, (
                'Validating Arp entry with expectation %s, Failed' % (
                    expectation))
        if expected_ip :
            result = False
            if expected_ip == ip:
                result = True
            assert result == expectation, (
                'Validating Arp entry with expectation %s, Failed' % (
                    expectation))
        self.logger.info('BMS %s:ARP check using %s : Got (%s, %s)' % (
            bms_fixture.name, search_term, ip, mac))
    # end validate_arp

    def create_sec_group(self, name, secgrpid=None, entries=None):
        secgrp_fixture = self.useFixture(SecurityGroupFixture(
            self.connections, self.inputs.domain_name,
            self.inputs.project_name, secgrp_name=name,
            uuid=secgrpid, secgrp_entries=entries,option='neutron'))
        result, msg = secgrp_fixture.verify_on_setup()
        assert result, msg
        return secgrp_fixture

    def create_logical_router(self, vn_fixtures, vni=None, devices=None,
                              **kwargs):
        vn_ids = [vn.uuid for vn in vn_fixtures]
        vni = vni or str(get_random_vxlan_id(min=10000))
        self.logger.info('Creating Logical Router with VN uuids: %s, VNI %s'%(
            vn_ids, vni))
        lr = self.useFixture(LogicalRouterFixture(
            connections=self.connections,
            connected_networks=vn_ids, vni=vni, vxlan_enabled=True,
            **kwargs))
        for spine in devices or self.spines:
            if kwargs.get('is_public_lr') == True:
                if 'dc_gw' not in self.inputs.get_prouter_rb_roles(spine.name):
                    continue
            lr.add_physical_router(spine.uuid)
        return lr

    def start_dhcp_server(self, vn_fixtures, dhcp_server=None,
                          bms_node=None, namespace=None):
        subnet_ranges = list()
        for vn in vn_fixtures:
            cidr = vn.get_cidrs()[0]
            subnet_ranges.append(
                {'start': get_an_ip(cidr, 8),
                 'end': get_an_ip(cidr, 15),
                 'mask': str(IPNetwork(cidr).netmask)})
        if dhcp_server:
            dhcp_server.run_dhcp_server(subnet_ranges)
        else:
            bms_data = self.inputs.bms_data[bms_node]
            server_ip = bms_data['mgmt_ip']
            username = bms_data['username']
            password = bms_data['password']
            run_dhcp_server(subnet_ranges, server_ip, username,
                            password, namespace)

    def stop_dhcp_server(self, dhcp_server):
        dhcp_server.stop_dhcp_server()

    def create_netns(self, bms_node, namespace, cidr):
        bms_data = self.inputs.bms_data[bms_node]
        server_ip = bms_data['mgmt_ip']
        username = bms_data['username']
        password = bms_data['password']
        intf = bms_data['interfaces'][0]
        mac = intf['host_mac']
        gw_ip = get_an_ip(cidr, offset=1)
        bms_ip = get_an_ip(cidr, offset=2)
        mask = cidr.split('/')[1]
        interface = get_intf_name_from_mac(server_ip, mac,
            username=username, password=password)
        create_netns(server_ip, username, password, namespace,
                     interface, address=bms_ip, gateway=gw_ip, mask=mask)
        self.addCleanup(delete_netns, server_ip, username, password, namespace)
        prouter = self.get_associated_prouters(bms_node, [intf])[0]
        prouter.configure_interface(intf['tor_port'], gw_ip, mask)
        self.addCleanup(prouter.delete_interface, intf['tor_port'])
