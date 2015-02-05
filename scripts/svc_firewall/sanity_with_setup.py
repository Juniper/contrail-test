import os
import fixtures
import testtools
import unittest

from common.connections import ContrailConnections
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
from testresources import ResourcedTestCase
from sanity_resource import SolnSetupResource
from time import sleep
from common.servicechain.config import ConfigSvcChain
from common.servicechain.verify import VerifySvcChain
from common.servicechain.firewall.verify import VerifySvcFirewall


class SvcMonSanityFixture(testtools.TestCase, ResourcedTestCase, VerifySvcFirewall):

    resources = [('base_setup', SolnSetupResource)]

    def __init__(self, *args, **kwargs):
        testtools.TestCase.__init__(self, *args, **kwargs)
        self.res = SolnSetupResource.getResource()
        self.inputs = self.res.inputs
        self.connections = self.res.connections
        self.logger = self.res.logger
        self.nova_fixture = self.res.nova_fixture
        self.analytics_obj = self.connections.analytics_obj
        self.vnc_lib = self.connections.vnc_lib
        self.quantum_fixture = self.connections.quantum_fixture

    def __del__(self):
        print "Deleting test_with_setup now"
        SolnSetupResource.finishedWith(self.res)

    def setUp(self):
        super(SvcMonSanityFixture, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'

    def tearDown(self):
        print "Tearing down test"
        super(SvcMonSanityFixture, self).tearDown()
        SolnSetupResource.finishedWith(self.res)

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_svc_in_network_datapath(self):
        """
        Description:  Validate the service chaining in network datapath.
        Test steps:
                1. Create two VN's and launch a VM on each VN
                2. Create in-network service template and service instance.
                3. Create a policy to allow traffic from VN1 to VN2 via/appy_service in-network serivce instacnce
                4. Send ICMP traffic from VN1 to VN2
        Pass criteria: Traffic should go through VN1 to VN2.

        Maintainer : ijohnson@juniper.net
        """
        return self.verify_svc_in_network_datapath()

    @preposttest_wrapper
    def test_svc_monitor_datapath(self):
        """
        Description:  Validate the service chaining transparent/bridge datapath.
        Test steps:
                1. Create two VN's and launch a VM on each VN
                2. Create transparent service template and service instance.
                3. Create a policy to allow traffic from VN1 to VN2 via/appy_service transparent serivce instacnce
                4. Send ICMP traffic from VN1 to VN2
        Pass criteria: Traffic should go through VN1 to VN2.

        Maintainer : ijohnson@juniper.net
        """
        return self.verify_svc_transparent_datapath()

    @preposttest_wrapper
    def test_svc_transparent_with_3_instance(self):
        """
        Description:  Validate the service chaining transparent/bridge datapath with 3 service instance.
        Test steps:
                1. Create two VN's and launch a VM on each VN
                2. Create transparent service template and 3 service instance.
                3. Create a policy to allow traffic from VN1 to VN2 via/appy_service 3 transparent serivce instacnce
                4. Send ICMP traffic from VN1 to VN2
        Pass criteria: Traffic should go through VN1 to VN2.

        Maintainer : ijohnson@juniper.net
        """
        return self.verify_svc_transparent_datapath(si_count=3)


# end TestSanityFixture
