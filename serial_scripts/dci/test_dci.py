import test
from netaddr import *
import uuid
import copy
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because, get_random_cidr, get_random_name
from common.contrail_fabric.base import BaseFabricTest
from common.base import GenericTestBase
from netaddr import IPNetwork, IPAddress
from vnc_api.vnc_api import *

class TestDCI(BaseFabricTest):
    @preposttest_wrapper
    def test_basic_dci(self):
        bms_fixtures1 = list(); bms_vns1 = dict()
        vn1 = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn1, image_name='cirros')
        for bms in self.inputs.bms_data.keys():
            bms_fixtures.append(self.create_bms(bms_name=bms, vn_fixture=vn1))
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures1+[vm1])
        bms_fixtures2 = list(); bms_vns2 = dict()
        vn2 = self.create_vn()
        vm2 = self.create_vm(vn_fixture=vn2, image_name='cirros')
        for bms in self.inputs.bms_data.keys():
            bms_fixtures.append(self.create_bms(bms_name=bms, vn_fixture=vn2))
        vm2.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures2+[vm2])
        lr1 = self.create_logical_router([vn1]+bms_vns1.values())
        lr2 = self.create_logical_router([vn2]+bms_vns2.values())
        self.config_dci(lr1, lr2)
        self.do_ping_mesh([vm1]+[vm2])
