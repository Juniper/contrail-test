# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import fixtures
import testtools
import time

from vn_test import *
from vm_test import *
from common.connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper

from common.neutron.base import BaseNeutronTest
import test
from tcutils.util import *


class TestSecurityGroup(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(TestSecurityGroup, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestSecurityGroup, cls).tearDownClass()

    @preposttest_wrapper
    def test_security_group_rename(self):
        ''' Test Security Group Rename
        '''
        sg1 = self.create_security_group(get_random_name('sg1'))
        sg_dict = {'name': "test_sec_grp"}
        sg_rsp = self.quantum_h.update_security_group(
            sg1['id'],
            sg_dict)
        assert sg_rsp['security_group'][
            'name'] == "test_sec_grp", 'Failed to update security group name'

    # end test_security_group_rename
