import time
from netaddr import * 
from random import randint

from common.neutron.base import BaseNeutronTest

from policy_test import PolicyFixture, copy
from pif_fixture import PhysicalInterfaceFixture
from lif_fixture import LogicalInterfaceFixture
from physical_router_fixture import PhysicalRouterFixture
from host_endpoint import HostEndpointFixture
from tor_fixture import ToRFixtureFactory
import test
from tcutils.tcpdump_utils import search_in_pcap, delete_pcap
from vm_test import VMFixture


class BaseTorTest(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(BaseTorTest, cls).setUpClass()
        cls.vnc_api_h = cls.vnc_lib
        cls.vnc_lib_fixture = cls.connections.vnc_lib_fixture
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseTorTest, cls).tearDownClass()
    # end tearDownClass

    def get_available_devices(self, device_type):
        ''' device_type is one of router/tor
        '''
        available = []
        for (device, device_dict) in self.inputs.physical_routers_data.iteritems():
            if device_dict['type'] == device_type :
                available.append(device_dict)
        return available
    # end get_available_devices

    def get_available_endpoints(self, device_ip):
        endpoints = []
        for (ip, ep_list) in self.inputs.tor_hosts_data.iteritems():
            if device_ip == ip:
                return ep_list 
        return endpoints
    # end get_available_endpoints

    def setup_routers(self, count=1):
        ''' Returns a list of physical router fixtures
        '''
        router_objs = []
        routers_info_list = self.get_available_devices('router')
        assert len(routers_info_list) >= count, (
            'Not enough devices available! Expected %s, Got %s' % (
                count, len(routers_info_list)))
        for i in range(0,count):
            router_params = routers_info_list[i]
            phy_router_fixture = self.useFixture(PhysicalRouterFixture(
                router_params['name'], router_params['mgmt_ip'],
                model=router_params['model'],
                vendor=router_params['vendor'],
                asn=router_params['asn'],
                ssh_username=router_params['ssh_username'],
                ssh_password=router_params['ssh_password'],
                mgmt_ip=router_params['mgmt_ip'],
                tunnel_ip=router_params['tunnel_ip'],
                ports=router_params['ports'],
                connections=self.connections,
                logger=self.logger))
            router_objs.append(phy_router_fixture)
        return router_objs
    # end setup_routers

    def setup_tors(self, count=1):
        tor_objs = []
        tors_info_list = self.get_available_devices('tor')
        assert len(tors_info_list) >= count, (
            'Not enough devices available! Expected %s, Got %s' % (
                count, len(tors_info_list)))  
        for i in range(0, count):
            tor_params = tors_info_list[i]
            tor_fixture = self.useFixture(ToRFixtureFactory.get_tor(
                tor_params['name'], 
                tor_params['mgmt_ip'],
                vendor=tor_params['vendor'],
                ssh_username=tor_params['ssh_username'],
                ssh_password=tor_params['ssh_password'],
                tunnel_ip=tor_params['tunnel_ip'],
                ports=tor_params['ports'],
                tor_ovs_port=tor_params['tor_ovs_port'],
                tor_ovs_protocol=tor_params['tor_ovs_protocol'],
                controller_ip=tor_params['controller_ip'],
                connections=self.connections,
                logger=self.logger))
            tor_objs.append(tor_fixture)
        return tor_objs
    # end setup_tors

    def setup_vmis(self, vn_id, fixed_ips=[],
                  mac_address=None,
                  security_groups=[],
                  extra_dhcp_opts=[], count=1):
        vmis=[]
        if mac_address:
            mac_address = EUI(mac_address)
            mac_address.dialect = mac_unix
        real_fixed_ips = fixed_ips
        for i in range(0,count):
            if fixed_ips:
                ip_address = fixed_ips[0]['ip_address']
                real_fixed_ips[0]['ip_address'] = str(IPAddress(
                    real_fixed_ips[0]['ip_address']) + i)
            vmi = self.setup_vmi(vn_id, real_fixed_ips,
                                 mac_address,
                                 security_groups,
                                 extra_dhcp_opts)
            vmis.append(vmi)
            if mac_address:
                mac_address = EUI(mac_address.value + 1)
                mac_address.dialect = mac_unix
        return vmis
    # end setup_vmis

    def setup_tor_port(self, tor_fixture, port_index=0, vlan_id=0, vmi_objs=[],
        cleanup=True):
        device_id = tor_fixture.phy_device.uuid
        tor_ip = tor_fixture.mgmt_ip 
        pif_name = self.inputs.tor_hosts_data[tor_ip][port_index]['tor_port']
        lif_name = pif_name + '.' + str(vlan_id)
        pif_fixture = PhysicalInterfaceFixture(pif_name,
            device_id=device_id,
            connections=self.connections)
        pif_fixture.setUp()
        if cleanup:
            self.addCleanup(pif_fixture.cleanUp)

        lif_fixture = LogicalInterfaceFixture(
            lif_name,
            pif_id=pif_fixture.uuid,
            vlan_id=vlan_id,
            vmi_ids=[x.uuid for x in vmi_objs],
            connections=self.connections)
        lif_fixture.setUp()
        if cleanup:
            self.addCleanup(lif_fixture.cleanUp)
        return (pif_fixture, lif_fixture)
    # end setup_tor_port

    def setup_bms(self, tor_fixture, port_index=0, namespace=None,
        ns_intf=None, ns_mac_address=None, 
        ns_ip_address=None,
        ns_netmask=None,
        ns_gateway=None,
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
        if namespace is None:
            namespace='ns'+str(randint(0,99))
        if ns_intf is None:
            ns_intf='tap'+str(randint(0,99))
        tor_ip = tor_fixture.mgmt_ip
        tor_name = tor_fixture.name
        host_info = self.inputs.tor_hosts_data[tor_ip][port_index]
        self.logger.info('Creating a BMS host on TOR %s , port %s' % (
            tor_ip, host_info['tor_port']))
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
            tor_name=tor_name)
        bms_obj.setUp()
        if cleanup:
            self.addCleanup(bms_obj.cleanUp)
        if verify:
            retval,output = bms_obj.run_dhclient()
            assert retval, "BMS %s did not seem to have got an IP" % (
                bms_obj.name)
            if ns_ip_address:
                self.validate_interface_ip(bms_obj, ns_ip_address)
        return bms_obj
    # end setup_bms
    
    def create_vn(self, vn_name=None, vn_subnets=None, disable_dns=False,
                  vxlan_id=None, enable_dhcp=True, **kwargs):
        vn_fixture = super(BaseTorTest, self).create_vn(vn_name, vn_subnets,
            vxlan_id, enable_dhcp, **kwargs)
        if disable_dns:
            dns_dict = {'dns_nameservers': ['0.0.0.0']}
            for vn_subnet_obj in vn_fixture.vn_subnet_objs:
                vn_fixture.update_subnet(vn_subnet_obj['id'], dns_dict) 
        return vn_fixture
    # end create_vn

    def validate_interface_ip(self, bms_fixture, expected_ip):
        assert expected_ip == bms_fixture.info['inet_addr'],\
            'BMS IP not expected : Seen:%s, Expected:%s' % (
            bms_fixture.info['inet_addr'], expected_ip)
    # end validate_interface_ip  

    def set_configured_vxlan_mode(self):
        self.vnc_lib_fixture.set_vxlan_mode('configured')
        self.addCleanup(self.vnc_lib_fixture.set_vxlan_mode, 'automatic')

    def restart_openvwitches(self, tor_fixtures):
        '''In some scenarios,(Ex: Vxlan id change), it is required 
            that one needs to restart the openvswitch processes ourselves
            This is unlike QFX where a change is taken care of by itself.
        '''
        for tor_fixture in tor_fixtures:
            if tor_fixture.vendor == 'openvswitch':
                tor_fixture.restart_ovs()
    # end restart_openvwitches

    def clear_arps(self, bms_fixtures):
        for bms_fixture in bms_fixtures:
            bms_fixture.clear_arp(all_entries=True)
    # end clear_arps

    def set_global_asn(self, asn):
        existing_asn = self.vnc_lib_fixture.get_global_asn()
        ret = self.vnc_lib_fixture.set_global_asn(asn)
        self.addCleanup(self.vnc_lib_fixture.set_global_asn, existing_asn)
        return ret
    # end set_global_asn

    def add_vmi_to_lif(self, lif_fixture, vmi_uuid):
        lif_fixture.add_virtual_machine_interface(vmi_uuid)
        self.addCleanup(lif_fixture.delete_virtual_machine_interface, vmi_uuid)
    # end add_vmi_to_lif


    def validate_arp(self, bms_fixture, ip_address=None,
                     mac_address=None, expected_mac=None,
                     expected_ip=None):
        ''' Method to validate IP/MAC
            Given a IP and expected MAC of the IP,
            or given a MAC and expected IP, this method validates it
            against the arp table in the BMS and returns True/False
        '''
        (ip, mac) = bms_fixture.get_arp_entry(ip_address=ip_address,
                                              mac_address=mac_address)
        search_term = ip_address or mac_address
        if expected_mac :
            assert expected_mac == mac, (
                'Arp entry mismatch for %s, Expected : %s, Got : %s' % (
                    search_term, expected_mac, mac))
        if expected_ip :
            assert expected_ip == ip, (
                'Arp entry mismatch for %s, Expected : %s, Got : %s' % (
                    search_term, expected_ip, ip))
        self.logger.info('BMS %s:ARP check using %s : Got (%s, %s)' % (
            bms_fixture.identifier, search_term, ip, mac))
    # end validate_arp

    def validate_bms_gw_mac(self, bms_fixture, physical_router_fixture):
        '''
            Validate that the Gw MAC of the BMS is the irb MAC of the physical
            router
        '''
        bms_gw_mac = bms_fixture.get_gateway_mac()
        bms_gw_ip = bms_fixture.get_gateway_ip()
        router_irb_mac = physical_router_fixture.get_virtual_gateway_mac(
            bms_gw_ip)
        assert bms_gw_mac == router_irb_mac, (
            "BMS Gateway MAC mismatch! Expected: %s, Got: %s" % (
                bms_gw_mac, router_irb_mac))
        self.logger.info('Validated on BMS %s that MAC of gateway is '
            'same as routers irb MAC : %s' % (bms_fixture.identifier,
                router_irb_mac))
    # end validate_bms_gw_mac

    def get_mgmt_ip_of_node(self, ip):
        return self.inputs.host_data[ip]['ip']

    def validate_arp_forwarding(self, source_fixture,
            ip, dest_fixture, source_interface=None):
        '''
            Validate that arp packet from a VM/BMS destined to 'ip'
            is seen on the destination VM/BMS
            Returns True in such a case, else False
        '''
        (session, pcap) = dest_fixture.start_tcpdump(filters='arp -v')
        source_fixture.arping(ip, source_interface)
        time.sleep(5)
        dest_fixture.stop_tcpdump(session, pcap)
        if isinstance(source_fixture, HostEndpointFixture):
            source_ip = source_fixture.info['inet_addr']
        elif isinstance(source_fixture, VMFixture):
            source_ip = source_fixture.vm_ips[0]

        if isinstance(dest_fixture, HostEndpointFixture):
            dest_name = dest_fixture.identifier
        elif isinstance(dest_fixture, VMFixture):
            dest_name = dest_fixture.vm_name
        
        result = search_in_pcap(session, pcap, 'Request who-has %s tell %s' % (
            ip, source_ip))
        if result :
            message = 'ARP request from %s to %s is seen on %s' % (
                source_ip, ip, dest_name)
        else:
            message = 'ARP request from %s to %s is NOT seen on %s' % (
                source_ip, ip, dest_name)
                
        self.logger.info(message)
        delete_pcap(session, pcap)
        return (result, message)
    # end validate_arp_forwarding

    def validate_dhcp_forwarding(self, source_fixture,
            dest_fixture, source_interface=None):
        '''
            Validate that dhcp discover packet from a VM/BMS 
            is seen on the destination VM/BMS
            Returns True in such a case, else False
        '''
        (session, pcap) = dest_fixture.start_tcpdump(filters='udp port 68 -v')
        source_fixture.run_dhclient(source_interface, timeout=20)
        time.sleep(5)
        dest_fixture.stop_tcpdump(session, pcap)
        if isinstance(source_fixture, HostEndpointFixture):
            source_mac = source_fixture.info['hwaddr']
            source_name = source_fixture.identifier
        elif isinstance(source_fixture, VMFixture):
            source_mac = source_fixture.get_vm_interface_name(source_interface)
            source_name = source_fixture.vm_name

        if isinstance(dest_fixture, HostEndpointFixture):
            dest_name = dest_fixture.identifier
        elif isinstance(dest_fixture, VMFixture):
            dest_name = dest_fixture.vm_name

        result = search_in_pcap(session, pcap, 'BOOTP/DHCP, Request from %s' % (
            source_mac))
        if result :
            message = 'DHCP discover/request from %s, MAC %s is seen '\
                'on %s' % (source_name, source_mac, dest_name)
        else:
            message = 'DHCP discover/request from %s, MAC %s is NOT '\
                'seen on %s' % (source_name, source_mac, dest_name)

        self.logger.info(message)
        delete_pcap(session, pcap)
        return (result, message)
    # end validate_dhcp_forwarding

    def start_webserver_in_ns(self, bms_fixture, listen_port=8000, content=None):
        cmd = 'mkdir -p '+bms_fixture.namespace+';'
        cmd = cmd + 'cd '+bms_fixture.namespace + ';'
        cmd = cmd + 'echo '+bms_fixture.namespace+' >& index.html;'
        cmd = cmd + 'nohup python -m SimpleHTTPServer '+str(listen_port) + ' &'
        cmd = '''bash -c "''' + cmd + '"'
        bms_fixture.run_cmd(cmd)
    
