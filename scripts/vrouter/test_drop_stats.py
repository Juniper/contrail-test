# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
from tcutils.wrappers import preposttest_wrapper
from common.vrouter.base import BaseVrouterTest
from common.agent.drop_stats import DropStats
from tcutils.util import *
from netaddr import IPNetwork, IPAddress
import test

class TestDropStats(BaseVrouterTest, DropStats):

    @classmethod
    def setUpClass(cls):
        super(TestDropStats, cls).setUpClass()
        cls.agent_inspect_h = cls.connections.agent_inspect

    @classmethod
    def tearDownClass(cls):
        super(TestDropStats, cls).tearDownClass()

    @test.attr(type=['sanity', 'vcenter'])
    @preposttest_wrapper
    def test_flow_action_drop_stats(self):
        """
        Description: Verify flow action drop stats
        Steps:
            1. Create 2 VNs and launch 1 VM in each VN, on different nodes on multi node setup
            2. Add policy to deny pkts between VNs.
            3. Ping VM2 from VM1
        Pass criteria:
            1. Verify flow action count gets incremented in dropstats (vrouter) output
            2. Verify flow action count gets incremented for the vmi of VM1 
               in 'vif --get vif_index --get-drop-stats' (if_stats) output
        """
        assert self.verify_flow_action_drop_stats(drop_type='Flow Action Drop')
        return True
    # end test_drop_stats


