from netaddr import * 

from common.neutron.base import BaseNeutronTest

from pif_fixture import PhysicalInterfaceFixture
from port_fixture import PortFixture
from lif_fixture import LogicalInterfaceFixture
from physical_router_fixture import PhysicalRouterFixture
from host_endpoint import HostEndpointFixture
import test


class BaseTorTest(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(BaseTorTest, cls).setUpClass()
        cls.vnc_api_h = cls.vnc_lib
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

    def setup_tor_port(self, device_id, tor_dict, port_index, vlan_id=0, vmi_objs=[]):
        pif_name = self.inputs.tor_hosts_data[tor_dict['tor_ip']][port_index]['tor_port']
        lif_name = pif_name + '.' + str(vlan_id)
        pif_fixture = self.useFixture(PhysicalInterfaceFixture(pif_name,
            device_id,
            connections=self.connections))
        lif_fixture = self.useFixture(LogicalInterfaceFixture(
            lif_name,
            pif_fixture.uuid,
            vlan_id=vlan_id,
            vmi_ids=[x.uuid for x in vmi_objs],
            connections=self.connections))
        return (pif_fixture, lif_fixture)

    def get_tor_info(self, tor_id):
        tor_dict = self.inputs.tor_data
        for (k,v) in tor_dict.items():
            if v['tor_id'] == tor_id:
                tor_obj = self.vnc_api_h.physical_router_read(
                    fq_name=['default-global-system-config', v['tor_name']])
                return v, tor_obj
    # end get_tor_info

    def setup_bms(self, tor_dict, port_index=0, namespace='ns1',
        ns_intf='tap1', ns_mac_address=None, 
        ns_ip_address=None,
        ns_netmask=None,
        ns_gateway=None,
        vlan_id=None,
        verify=True):
        '''Setups up a bms using HostEndpointFixture

            tor_info : tor info in a dict
            port_index : index of the port in tor_hosts dict of 
                         the ToR
        '''
        host_info = self.inputs.tor_hosts_data[tor_dict['tor_ip']][port_index]
        self.logger.info('Creating a BMS host on TOR %s , port %s' % (
            tor_dict['tor_ip'], host_info['tor_port']))
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
            vlan_id=vlan_id))
        if verify:
            retval,output = bms_obj.run_dhclient()
            assert retval, "BMS %s did not seem to have got an IP" % (
                bms_obj.name)
            if ns_ip_address:
                self.validate_interface_ip(bms_obj, ns_ip_address)
        return bms_obj
    # end setup_bms
    
    def create_vn(self, vn_name=None, vn_subnets=None, disable_dns=False):
        vn_fixture = super(BaseTorTest, self).create_vn(vn_name, vn_subnets)
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

