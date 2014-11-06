# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#

import fixtures
import testtools
import unittest
import time
import requests
from vnc_api import vnc_api
from common.contrail_test_init import ContrailTestInit
from common.connections import ContrailConnections
from contrail_fixtures import *
from tcutils.wrappers import preposttest_wrapper
from cfgm_fixture import CfgmFixture
from quantum_fixture import QuantumFixture


class CfgmScaleTest(testtools.TestCase, fixtures.TestWithFixtures):

    def setUp(self):
        super(CfgmScaleTest, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.logger = self.inputs.logger
        self.vnc_lib = self.connections.vnc_lib_fixture.obj
        self.tid = str(
            self.vnc_lib.project_read(fq_name=[u'default-domain', u'demo']).uuid)
        self.asi = self.connections.api_server_inspect
    # end setUp

    def cleanUp(self):
        super(CfgmScaleTest, self).cleanUp()
    # end cleanUp

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_cfgm_scale(self):
        '''Test to setup VM and read them
           def __init__(self, connections, inputs, vn_count, vms_per_vn):
        '''
        # return True
        self.logger.info("Setting up CFGM at %d" % time.time())
        #import pdb; pdb.set_trace()
        cfgm_obj = self.useFixture(CfgmFixture(connections=self.connections,
                                               inputs=self.inputs, vn_count=1, vms_per_vn=100))
        self.logger.info("Reading VNs at %d" % time.time())
        self.logger.info(
            str(len(self.vnc_lib.virtual_networks_list()['virtual-networks'])))
        #import pdb; pdb.set_trace()
        self.logger.info("Reading VMs at %d" % time.time())
        self.logger.info(
            str(len(self.vnc_lib.virtual_machines_list()['virtual-machines'])))
        self.logger.info("Reading VN %s from API at %d ..." %
                         (cfgm_obj._vns[0].get_fq_name_str(), time.time()))
        bb = requests.get('http://localhost:8082/virtual-network/%s' %
                          cfgm_obj._vns[0].uuid)
        self.logger.info(len(str(bb.content)))
        self.logger.info("Reading VN %s from LIB at %d ..." %
                         (cfgm_obj._vns[0].get_fq_name_str(), time.time()))
        #self.logger.info(self.vnc_lib.virtual_network_read(id = cfgm_obj._vns[0].uuid).dump())
        self.logger.info("Test Completed at %d" % time.time())
        return True
    # end test_generator_scale

    @preposttest_wrapper
    def test_quantum_scale(self):
        '''Test to setup VM and read them
           def __init__(self, connections, inputs, vn_count, vms_per_vn):
        '''
        self.logger.info("Setting up Quantum at %d" % time.time())
        #import pdb; pdb.set_trace()
        q_obj = self.useFixture(
            QuantumFixture(connections=self.connections, tid=self.tid,
                           inputs=self.inputs, vn_count=1, vms_per_vn=100))
        self.logger.info("Reading VNs at %d" % time.time())
        self.logger.info(
            str(len(self.vnc_lib.virtual_networks_list()['virtual-networks'])))
        #import pdb; pdb.set_trace()
        self.logger.info("Reading VMs at %d" % time.time())
        self.logger.info(
            str(len(self.vnc_lib.virtual_machines_list()['virtual-machines'])))
        self.logger.info("Reading VN %s from API at %d ..." %
                         (q_obj.topVN(), time.time()))
        bb = requests.get('http://localhost:8082/virtual-network/%s' %
                          q_obj.topVN())
        self.logger.info(len(str(bb.content)))
        self.logger.info("Reading VN %s from LIB at %d ..." %
                         (q_obj.topVN(), time.time()))
        self.logger.info(self.vnc_lib.virtual_network_read(id=q_obj.topVN()))
        self.logger.info("Reading VN %s from Quantum at %d ..." %
                         (q_obj.topVN(), time.time()))
        # self.logger.info(q_obj.obj.show_network(q_obj.topVN()))
        self.logger.info("Test Completed at %d" % time.time())
        return True
    # end test_quantum_scale

# end class CfgmScaleTest
