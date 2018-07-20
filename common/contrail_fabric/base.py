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
