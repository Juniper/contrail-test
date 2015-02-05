import os
import unittest
import fixtures
import testtools

from common.connections import ContrailConnections
from common.contrail_test_init import ContrailTestInit
from tcutils.wrappers import preposttest_wrapper

from common.servicechain.firewall.verify import VerifySvcFirewall


class SvcMonSanityFixture(testtools.TestCase, VerifySvcFirewall):

    def setUp(self):
        super(SvcMonSanityFixture, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.quantum_fixture = self.connections.quantum_fixture
        self.nova_fixture = self.connections.nova_fixture
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.analytics_obj = self.connections.analytics_obj

    def cleanUp(self):
        self.logger.info("Cleaning up")
        super(SvcMonSanityFixture, self).cleanUp()

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

if __name__ == '__main__':
    unittest.main()
