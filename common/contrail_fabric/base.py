from common.neutron.base import BaseNeutronTest
from common.fabric_utils import FabricUtils
from tcutils.util import get_random_name
from lif_fixture import LogicalInterfaceFixture
from bms_fixture import BMSFixture
from vm_test import VMFixture
import time

class BaseFabricTest(BaseNeutronTest, FabricUtils):

    @classmethod
    def setUpClass(cls):
        super(BaseFabricTest, cls).setUpClass()
        cls.vnc_h = cls.connections.orch.vnc_h
        cls.interfaces = {'physical': [], 'logical': []}
        cls.bms = dict()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseFabricTest, cls).tearDownClass()
    # end tearDownClass

    def create_bms(self, bms_name, **kwargs):
        self.logger.info('Creating bms %s'%bms_name)
        bms = self.useFixture(BMSFixture(
                              connections=self.connections,
                              name=bms_name,
                              **kwargs))
        status, msg = bms.run_dhclient()
        assert status, 'DHCP failed to fetch address'
        bms.verify_on_setup()
        return bms

    def create_lif(self, pif_fixture, unit=0, vlan_id=None, interface_type=None):
        lif_name = pif_fixture.name + '.' + str(unit)
        lif = self.useFixture(LogicalInterfaceFixture(name=lif_name,
                              pif_fqname=pif_fixture.fq_name,
                              connections=self.connections,
                              vlan_id=vlan_id,
                              interface_type=interface_type))
        self.interfaces['logical'].append(lif)
        return lif

    def _my_ip(self, fixture):
        if type(fixture) == VMFixture:
            return fixture.vm_ip
        elif type(fixture) == BMSFixture:
            return fixture.bms_ip

    def do_ping_mesh(self, fixtures, expectation=True):
        list_of_ips = set()
        for fixture in fixtures:
            list_of_ips.add(self._my_ip(fixture))
        for fixture in fixtures:
            for ip in list_of_ips - set([self._my_ip(fixture)]):
                fixture.clear_arp()
                assert fixture.ping_with_certainty(ip, expectation=expectation)

#Need to revisit after logical router fixture is stabilized
    def create_logical_router(self, physical_devices, vn_fixtures, **kwargs):
            vni = 5000
            self.logger.info('Creating Logical Router')
            vn_uuid_list = []
            for vn in vn_fixtures:
                vn_uuid_list.append(vn.uuid)

            self.logger.info('Creating Logical Router with VN uuids: %s'%(vn_uuid_list))
            logical_router_fixture = self.useFixture(LogicalRouterFixture(connections=self.connections, private={'vns': vn_uuid_list}))
            logical_router_fixture.set_vni = vni
            for physical_device in physical_devices:
                logical_router_fixture.add_physical_router(physical_device.uuid)

            return logical_router_fixture

    def enable_vxlan_routing(self, create=False):
      '''Used to change the existing encapsulation priorities to new values'''
      if self.connections:
          project_name = self.connections.project_name
          vnc_api_h = self.connections.vnc_lib
          project_id = self.connections.project_id

      project_id = vnc_api_h.project_read(fq_name=['default-domain',
                                                        project_name]).uuid
      self.logger.info('Enabling VxLAN Routing for the project: %s' %(project_name))
      project_obj = vnc_api_h.project_read(id=project_id)
      project_obj.set_vxlan_routing(True)
      result  = vnc_api_h.project_update(project_obj)

    def clear_arps(self, bms_fixtures):
        for bms_fixture in bms_fixtures:
            bms_fixture.clear_arp(all_entries=True)
    # end clear_arps

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

    def validate_arp_forwarding(self, source_fixture,
            ip, dest_fixture):
        '''
            Validate that arp packet from a VM/BMS destined to 'ip'
            is seen on the destination VM/BMS
            Returns True in such a case, else False
        '''
        (session, pcap) = dest_fixture.start_tcpdump(filters='arp -v')
        source_fixture.arping(ip)
        time.sleep(5)
        dest_fixture.stop_tcpdump(session, pcap)
        if isinstance(source_fixture, BMSFixture):
            source_ip = source_fixture.bms_ip
        elif isinstance(source_fixture, VMFixture):
            source_ip = source_fixture.vm_ips[0]

        if isinstance(dest_fixture, BMSFixture):
            dest_name = dest_fixture.name
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
    # end validate_arp_forwardingw
