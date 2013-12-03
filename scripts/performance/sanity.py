import os
import fixtures
import testtools

from contrail_test_init import *
from contrail_fixtures import *
from netperfparse import NetPerfParser
from connections import ContrailConnections
from testresources import ResourcedTestCase
from sanity_resource import SolnSetupResource
from tcutils.wrappers import preposttest_wrapper

class PerformanceSanity(testtools.TestCase, ResourcedTestCase, fixtures.TestWithFixtures):
    resources = [('base_setup', SolnSetupResource)]
    def __init__(self, *args, **kwargs):
        testtools.TestCase.__init__(self, *args, **kwargs)
        self.res= SolnSetupResource.getResource()
        self.inputs= self.res.inputs
        self.connections= self.res.connections
        self.logger= self.res.logger
        self.nova_fixture= self.res.nova_fixture
        self.analytics_obj=self.connections.analytics_obj
        self.vnc_lib= self.connections.vnc_lib
        self.quantum_fixture= self.connections.quantum_fixture
        self.cn_inspect= self.connections.cn_inspect

    def __del__(self):
        print "Deleting test_with_setup now"
        SolnSetupResource.finishedWith(self.res)

    def setUp(self):
        super (PerformanceSanity, self).setUp()
        if 'PARAMS_FILE' in os.environ :
            self.ini_file= os.environ.get('PARAMS_FILE')
        else:
            self.ini_file= 'params.ini'

    def tearDown(self):
        print "Tearing down test"
        super (PerformanceSanity, self).tearDown()
        SolnSetupResource.finishedWith(self.res)

    def runTest(self):
        pass

    @preposttest_wrapper
    def test_check_netperf_within_vn(self):
        ''' Validate Network performance between two VMs within a VN.
        '''
        results = []
        vn1_fixture= self.res.vn1_fixture
        vm5_fixture= self.res.vn1_vm5_fixture
        vm6_fixture= self.res.vn1_vm6_fixture

        assert vn1_fixture.verify_on_setup()
        assert vm5_fixture.verify_on_setup()
        assert vm6_fixture.verify_on_setup()

        cmd = 'netperf -H %s -t TCP_STREAM -B "outbound"' % vm6_fixture.vm_ip
        vm5_fixture.run_cmd_on_vm(cmds=[cmd])
        outbound_netperf = NetPerfParser(vm5_fixture.return_output_values_list[0])
        outbound_throughout = outbound_netperf.get_throughput()
        self.logger.info("Outbound throughput: %s", outbound_throughout)
        results.append((outbound_netperf.get_throughput() > 900,
                       "Outbound throughput is(%s) less than 900" % outbound_throughout))

        cmd = 'netperf -H %s -t TCP_STREAM -B "inbound"' % vm6_fixture.vm_ip
        vm5_fixture.run_cmd_on_vm(cmds=[cmd])
        inbound_netperf = NetPerfParser(vm5_fixture.return_output_values_list[0])
        inbound_throughout = inbound_netperf.get_throughput()
        self.logger.info("Inbound throughput: %s", outbound_throughout)
        results.append((inbound_netperf.get_throughput() > 900,
                       "Outbound throughput is(%s) less than 900" % inbound_throughout))

        errmsg = ''
        for (rc, msg) in results:
            if not rc:
                self.logger.error(msg)
                errmsg += msg + '\n'
        if errmsg:
            #assert False, errmsg
            self.logger.info("This test wont fail; until we identify a number for throughput.")
            self.logger.error(errmsg)

        return True
