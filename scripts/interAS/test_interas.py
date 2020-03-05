from common.interAS.base import BaseInterAS
from tcutils.wrappers import preposttest_wrapper
from common.neutron.base import BaseNeutronTest
from security_group import SecurityGroupFixture
import test
import time
from tcutils.util import *
from tcutils.tcpdump_utils import *
from common import isolated_creds
from test import attr

class TestInterAS(BaseInterAS):

    @preposttest_wrapper
    def test_interAS_labeled_unicast(self):
        '''
            configure labeled unicast address family on all control nodes
            also configure local ASBR with same address family
            verify the neighborship
        '''
        self.configure_labeled_unicast()
        self.configure_local_asbr()
        assert self.verify_asbr_connection()
        assert self.verify_inet3_routing_instance()
    # end test_interAS_labeled_unicast

    def test_interAS_remote_vpn(self):
        '''
            configure remote asbr with inet-vpn address family
            and verify the neighborship
        '''
        self.configure_remote_asbr()
        assert self.verify_asbr_connection(local=False)

