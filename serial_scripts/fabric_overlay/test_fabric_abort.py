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

'''
There are 2 methods of calling abort: Graceful and Force.
If there are 2 fabric jobs that can be aborted, lets say onboarding and role assignment, that gives us 4 combinations of aborts.
Below classes will be defined based in what method is used for aborting and what job is being aborted
'''

class TestFabricAbortGracefulOnboard(BaseFabricTest):
    enterprise_style = False
    abort_mode='graceful_onboard'

    def setUp(self):
        super(TestFabricAbortGracefulOnboard, self).setUp()

    @preposttest_wrapper
    def test_fabric_abort_greenfield(self):
        '''
         Description: Test to validate if aborting a job works.
         Test steps:
                1. In base file, there will be a fabric spawned. Based on what method is used for aborting and what job is being aborted, define the variable here.
                2. After that job is aborted, start a new fabric job without abort
                3. This new fabric should work fine even though the previous one was aborted.
         Pass criteria: The new fabric should be operational.
        '''
        self.onboard_existing_fabric(self.inputs.fabrics[0], cleanup=False,
                    enterprise_style=False, abort_mode=False)
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

class TestFabricAbortGracefulRoles(TestFabricAbortGracefulOnboard):
    enterprise_style = False
    abort_mode='graceful_roles'
    @classmethod
    def setUpClass(cls):
        super(TestFabricAbortGracefulRoles, cls).setUpClass()

class TestFabricAbortForceOnboard(TestFabricAbortGracefulOnboard):
    enterprise_style = False
    abort_mode='force_onboard'
    @classmethod
    def setUpClass(cls):
        super(TestFabricAbortForceOnboard, cls).setUpClass()

class TestFabricAbortForceRoles(TestFabricAbortGracefulOnboard):
    enterprise_style = False
    abort_mode='force_roles'
    @classmethod
    def setUpClass(cls):
        super(TestFabricAbortForceRoles, cls).setUpClass()
