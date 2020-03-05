from common.vrouter.base import BaseVrouterTest
from common.vrouter.base_drop_stats import BaseDropStats
import os
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import *
from netaddr import IPNetwork, IPAddress
import test

class TestDropStats(BaseVrouterTest, BaseDropStats):

    @classmethod
    def setUpClass(cls):
        super(TestDropStats, cls).setUpClass()
        cls.agent_inspect_h = cls.connections.agent_inspect

    @classmethod
    def tearDownClass(cls):
        super(TestDropStats, cls).tearDownClass()

    @test.attr(type=['sanity','dev_reg'])
    @preposttest_wrapper
    def test_flow_action_drop_stats(self):
        """
        Description: Verify flow action drop stats
        Steps:
            1. Create 2 VNs and launch 1 VM in each VN, on different nodes on multi node setup
            2. Add policy to deny pkts between VNs.
            3. Ping VM2 from VM1
        Pass criteria:
            1. Verify flow action count gets incremented, get it from introspect
            2. Verify flow action count gets incremented for the vmi of VM1, get it from introspect
              
        """
        compute_hosts = self.orch.get_hosts()
        if len(compute_hosts) < 2:
            raise self.skipTest("Skipping test case,this test needs atleast 2 compute nodes")
        
        assert self.verify_flow_action_drop_stats()
        return True
    # end test_drop_stats


