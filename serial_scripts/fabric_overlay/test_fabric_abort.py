from builtins import str
from builtins import range
import test
import uuid
import copy
import random
from netaddr import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import skip_because, get_random_cidr, get_random_name
from common.contrail_fabric.base import BaseFabricTest
from common.base import GenericTestBase
from netaddr import IPNetwork, IPAddress
from vnc_api.vnc_api import *

class TestFabricAbort(BaseFabricTest):
    enterprise_style = False
    abort=True
    @preposttest_wrapper
    def test_fabric_abort_brownfield(self):
        self.onboard_existing_fabric(self.inputs.fabrics[0], cleanup=False,
                    enterprise_style=False, abort=False)
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')
        bms_fixtures = list()
        vn = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn, image_name='ubuntu')
        for bms in self.get_bms_nodes():
            bms_fixtures.append(self.create_bms(bms_name=bms,
                vn_fixture=vn, tor_port_vlan_tag=10))
        vm1.wait_till_vm_is_up()
        self.do_ping_mesh(bms_fixtures+[vm1])


