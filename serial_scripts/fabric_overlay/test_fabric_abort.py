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
from common.contrail_fabric.base import FabricSingleton
from common.base import GenericTestBase
from netaddr import IPNetwork, IPAddress
from vnc_api.vnc_api import *

'''
There are 2 methods of calling abort: Graceful and Force.
If there are 2 fabric jobs that can be aborted, lets say onboarding and role assignment, that gives us 4 combinations of aborts.
Below classes will be defined based in what method is used for aborting and what job is being aborted
'''

class TestFabricAbortGracefulOnboard(BaseFabricTest):
    abort_mode = 'graceful'
    action = 'onboard'
    def setUp(self):
        super(BaseFabricTest, self).setUp()
        self.fabric, self.devices, self.interfaces, self.execution_id = \
            self.onboard_existing_fabric(self.inputs.fabrics[0],
                wait_for_finish=False, cleanup=False)

    @skip_because(bms=2)
    @preposttest_wrapper
    def test_fabric_abort(self):
        '''
         Description: Test to validate if aborting a job works.
         Test steps:
                1. In base file, there will be a fabric spawned. Based on what method is used for aborting and what job is being aborted, define the variable here.
                2. After that job is aborted, start a new fabric job without abort
                3. This new fabric should work fine even though the previous one was aborted.
         Pass criteria: The new fabric should be operational.
        '''
        try:
            self.abort_job(self.execution_id, self.abort_mode, self.action)
        finally:
            self.cleanup_fabric(self.fabric, verify=False, retry=False)
        self._setup_fabric()
        bms_nodes = self.get_bms_nodes()
        vn = self.create_vn()
        bms1 = self.create_bms(bms_name=bms_nodes[0], vn_fixture=vn, vlan_id=10)
        bms2 = self.create_bms(bms_name=bms_nodes[1], vn_fixture=vn, vlan_id=10)
        self.do_ping_test(bms1, bms2.bms_ip)

class TestFabricAbortForceOnboard(TestFabricAbortGracefulOnboard):
    abort_mode='force'

class TestFabricAbortGracefulRoles(TestFabricAbortGracefulOnboard):
    abort_mode='graceful'
    action = 'assign_roles'
    def setUp(self):
        super(BaseFabricTest, self).setUp()
        self.fabric, self.devices, self.interfaces, _ = \
            self.onboard_existing_fabric(self.inputs.fabrics[0],
                wait_for_finish=True, cleanup=False)
        self.execution_id, _ = self.assign_roles(self.fabric,
            self.devices, wait_for_finish=False)
        self.sleep(5)

class TestFabricAbortForceRoles(TestFabricAbortGracefulRoles):
    abort_mode='force'
