from netaddr import * 

from common.neutron.base import BaseNeutronTest

from pif_fixture import PhysicalInterfaceFixture
from port_fixture import PortFixture
from lif_fixture import LogicalInterfaceFixture
from physical_router_fixture import PhysicalRouterFixture
from host_endpoint import HostEndpointFixture
from tor_fixture import ToRFixtureFactory
import test


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

    def setup_vmi(self, vn_id, fixed_ips=[],
                  mac_address=None,
                  security_groups=[],
                  extra_dhcp_opts=[]):
        if mac_address:
            mac_address = EUI(mac_address)
            mac_address.dialect = mac_unix
        return self.useFixture(PortFixture(
            vn_id,
            mac_address=mac_address,
            fixed_ips=fixed_ips,
            security_groups=security_groups,
            extra_dhcp_opts=extra_dhcp_opts,
            connections=self.connections,
        ))

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
                connections=self.connections))
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
                controller_ip=tor_params['controller_ip']))
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
            ip_address = fixed_ips[0]['ip_address']
            real_fixed_ips[0]['ip_address'] = str(IPAddress(
                real_fixed_ips[0]['ip_address']) + i)
            vmi = self.setup_vmi(vn_id, fixed_ips,
                                 mac_address,
                                 security_groups,
                                 extra_dhcp_opts)
            vmis.append(vmi)
            if mac_address:
                mac_address = EUI(mac_address.value + 1)
                mac_address.dialect = mac_unix
        return vmis
    # end setup_vmis

    def setup_tor_port(self, tor_fixture, port_index, vlan_id=0, vmi_objs=[]):
        device_id = tor_fixture.phy_device.uuid
        tor_ip = tor_fixture.mgmt_ip 
        pif_name = self.inputs.tor_hosts_data[tor_ip][port_index]['tor_port']
        lif_name = pif_name + '.' + str(vlan_id)
        pif_fixture = self.useFixture(PhysicalInterfaceFixture(pif_name,
            device_id=device_id,
            connections=self.connections))
        lif_fixture = self.useFixture(LogicalInterfaceFixture(
            lif_name,
            pif_id=pif_fixture.uuid,
            vlan_id=vlan_id,
            vmi_ids=[x.uuid for x in vmi_objs],
            connections=self.connections))
        return (pif_fixture, lif_fixture)
    # end setup_tor_port

    def setup_bms(self, tor_fixture, port_index=0, namespace='ns1',
        ns_intf='tap1', ns_mac_address=None, 
        ns_ip_address=None,
        ns_netmask=None,
        ns_gateway=None,
        vlan_id=None,
        verify=True):
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
        tor_ip = tor_fixture.mgmt_ip
        tor_name = tor_fixture.name
        host_info = self.inputs.tor_hosts_data[tor_ip][port_index]
        self.logger.info('Creating a BMS host on TOR %s , port %s' % (
            tor_ip, host_info['tor_port']))
        bms_obj = self.useFixture(HostEndpointFixture(
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
            tor_name=tor_name))
        if verify:
            retval,output = bms_obj.run_dhclient()
            assert retval, "BMS %s did not seem to have got an IP" % (
                bms_obj.name)
            if ns_ip_address:
                self.validate_interface_ip(bms_obj, ns_ip_address)
        return bms_obj
    # end setup_bms
    
    def create_vn(self, vn_name=None, vn_subnets=None, disable_dns=False,
                  vxlan_id=None):
        vn_fixture = super(BaseTorTest, self).create_vn(vn_name, vn_subnets,
                                                        vxlan_id)
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

    def do_ping_test(self, fixture_obj, sip, dip, expectation=True):
        assert fixture_obj.ping_with_certainty(dip, expectation=expectation),\
            'Ping from %s to %s with expectation %s failed!' % (
                sip, dip, str(expectation))
        self.logger.info('Ping test from %s to %s with expectation %s passed' % (sip,
                          dip, str(expectation)))
    # end do_ping_test

