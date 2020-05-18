from common.securitygroup.base import BaseSGTest
import unittest
from tcutils.wrappers import preposttest_wrapper
from vnc_api.vnc_api import NoIdError
import os
import sys
from common.securitygroup.verify import VerifySecGroup
from common.policy.config import ConfigPolicy
from tcutils.topo.topo_helper import *
from tcutils.topo.sdn_topo_setup import *
import test
from common.securitygroup import sdn_sg_test_topo
from tcutils.util import skip_because, get_random_name
from security_group import set_default_sg_rules

AF_TEST = 'v6'

class SecurityGroupMultiProject(BaseSGTest, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupMultiProject, cls).setUpClass()
        cls.option = 'openstack'

    def runTest(self):
        pass

    @preposttest_wrapper
    @skip_because(feature='multi-tenant')
    def test_sg_multiproject(self):
        """
        Description: Test SG across projects
        Steps:
            1. define the topology for the test
            2. create the resources as defined in the topo
            3. verify the traffic
        Pass criteria: step 3 should pass
        """

        topology_class_name = None
        user = 'user' + get_random_name()
        result = True
        msg = []
        if not topology_class_name:
            topology_class_name = sdn_sg_test_topo.sdn_topo_config_multiproject

        self.logger.info("Scenario for the test used is: %s" %
                         (topology_class_name))

        topo = topology_class_name(username=user, password=user)
        self.topo = topo

        #
        # Test setup: Configure policy, VN, & VM
        # return {'result':result, 'msg': err_msg, 'data': [self.topo, config_topo]}
        # Returned topo is of following format:
        # config_topo= {'policy': policy_fixt, 'vn': vn_fixture, 'vm': vm_fixture}
        topo_objs = {}
        config_topo = {}
        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.sdn_topo_setup(config_option=self.option)
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_objs, config_topo, vm_fip_info = out['data']

        self.start_traffic_and_verify_multiproject(
            topo_objs,
            config_topo,
            traffic_reverse=False)

        return True
    # end test_sg_multiproject

class SecurityGroupMultiProject_contrail(SecurityGroupMultiProject):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupMultiProject_contrail, cls).setUpClass()
        cls.option = 'contrail'

class SecurityGroupMultiProjectIpv6(SecurityGroupMultiProject):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupMultiProjectIpv6, cls).setUpClass()
        cls.inputs.set_af(AF_TEST)

    def is_test_applicable(self):
        if self.inputs.orchestrator == 'vcenter' and not self.orch.is_feature_supported(
                'ipv6'):
            return(False, 'Skipping IPv6 Test on vcenter setup')
        return (True, None)
