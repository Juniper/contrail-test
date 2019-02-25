import test
from tcutils.wrappers import preposttest_wrapper
from common.neutron.base import BaseNeutronTest
from collections import OrderedDict as dict
from tcutils import gevent_lib
from tcutils.util import get_an_ip
from vnc_api.vnc_api import BadRequest

class TestFwaasBasic(BaseNeutronTest):
    @classmethod
    def setUpClass(cls):
        super(TestFwaasBasic, cls).setUpClass()

    @preposttest_wrapper
    def test_fwaas_basic(self):
        import pdb; pdb.set_trace()
        self.create_fwaas_rule()
