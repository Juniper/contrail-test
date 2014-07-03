# Covers all configuration in project scope..
#
import os
import copy
from novaclient import client as mynovaclient
from novaclient import exceptions as novaException
import fixtures
import testtools
import topo_steps
from contrail_test_init import *
from vn_test import *
from vn_policy_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from connections import ContrailConnections
from floating_ip import *
from policy_test import *
from contrail_fixtures import *
from vna_introspect_utils import *
from topo_helper import *
from vnc_api import vnc_api
from vnc_api.gen.resource_test import *
from compute_node_test import *

class ProjectSetupFixture(fixtures.Fixture):

    def __init__(self, connections, topo, config_option='openstack', skip_verify='no', flavor='contrail_flavor_small', vms_on_single_compute=False, VmToNodeMapping=None):
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.connections = connections
        self.inputs = self.connections.inputs
        self.quantum_fixture = self.connections.quantum_fixture
        self.nova_fixture = self.connections.nova_fixture
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.topo = topo
        self.config_option = config_option
        self.skip_verify = skip_verify
        self.flavor = flavor
        self.vms_on_single_compute = vms_on_single_compute
        self.VmToNodeMapping = VmToNodeMapping
    # end __init__

    def setUp(self):
        super(ProjectSetupFixture, self).setUp()
        '''Take topology to be configured as input and return received & configured topology -collection 
        of dictionaries. we return received topology as some data is updated and is required for 
        reference.
        Available config_option for SDN topo setup
        1. 'openstack': Configures all sdn entities like VN,policy etc using Openstack API 
           a. Project: Keystone
           b. Policy:  Quantum
           c. IPAM:    Contrail API
           d. VN:      Quantum
           e. VM:      Nova
        2. 'contrail': Configures all sdn entities like VN,policy etc using Contrail API 
           a. Project: Keystone
           b. Policy:  Contrail API 
           c. IPAM:    Contrail API
           d. VN:      Contrail API 
           e. VM:      Nova
        '''
        self.result = True
        self.err_msg = []
        self.public_vn_present = False
        self.fvn_vm_map = False
        self.fvn_fixture = None
        self.fip_fixture = None
        self.fip_fixture_dict = {
        }
        self.secgrp_fixture = None
        topo_helper_obj = topology_helper(self.topo)
        self.topo.vmc_list = topo_helper_obj.get_vmc_list()
        self.topo.policy_vn = topo_helper_obj.get_policy_vn()
        self.logger.info("Starting setup")
        topo_steps.createProject(self)
        topo_steps.createSec_group(self, option=self.config_option)
        topo_steps.createServiceTemplate(self)
        topo_steps.createServiceInstance(self)
        topo_steps.createIPAM(self, option=self.config_option)
        topo_steps.createVN(self, option=self.config_option)
        topo_steps.createPolicy(self, option=self.config_option)
        topo_steps.attachPolicytoVN(self, option=self.config_option)
        # If vm to node pinning is defined then pass it on to create VM method.
        if self.VmToNodeMapping is not None:
            topo_steps.createVMNova(
                self, self.config_option, self.vms_on_single_compute, self.VmToNodeMapping)
        else:
            topo_steps.createVMNova(self, self.config_option, self.vms_on_single_compute)
        topo_steps.createPublicVN(self)
        topo_steps.createStaticRouteBehindVM(self)
        # prepare return data
        self.config_topo = {
            'project': self.project_fixture, 'policy': self.policy_fixt, 'vn': self.vn_fixture, 'vm': self.vm_fixture,
            'fip': [self.public_vn_present, self.fvn_fixture, self.fip_fixture, self.fvn_vm_map, self.fip_fixture_dict],
            'si': self.si_fixture, 'st': self.st_fixture, 'sec_grp': self.secgrp_fixture, 'ipam': self.ipam_fixture}
        self.data = [self.topo, self.config_topo]
        self.msg = self.err_msg
        if self.err_msg != []:
            self.result = False
    # end setUp

    def cleanUp(self):
        if self.inputs.fixture_cleanup == 'yes':
            super(ProjectSetupFixture, self).cleanUp()
        else:
            self.logger.info('Skipping sdn topology config cleanup')
    # end cleanUp

# end sdnSetupFixture
