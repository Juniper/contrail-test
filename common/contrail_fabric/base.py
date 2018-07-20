from common.neutron.base import BaseNeutronTest
from common.fabric_utils import FabricUtils
from tcutils.util import get_random_name
from lif_fixture import LogicalInterfaceFixture
from bms_fixture import BMSFixture

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

    def create_bms(self, bms_name, **kwargs):
        self.bms[bms_name] = self.useFixture(BMSFixture(
                                 connections=self.connections,
                                 name=bms_name,
                                 **kwargs))
        self.bms[bms_name].verify_on_setup()
        #vn_id = self.bms[bms_name].port_fixture.vn_id
        #self.vnc_h.add_vn_to_physical_router(self.inputs.bms[bms_name]['tor'],
        #                                     vn_id)
        #self.addCleanup(self.vnc_h.delete_vn_from_physical_router,
        #                self.inputs.bms[bms_name]['tor'],
        #                vn_id)
        return self.bms[bms_name]
