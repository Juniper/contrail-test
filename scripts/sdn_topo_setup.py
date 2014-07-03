# sdn_topo_setup can be used to configure/verify Openstack/Contrail features across projects/tenants...
# This calls project_setup to configure at project level.
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
from project_setup import *
from compute_node_test import *

class sdnTopoSetupFixture(fixtures.Fixture):

    def __init__(self, connections, topo):
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
    # end __init__

    def setUp(self, config_option='openstack', skip_verify='no', flavor='contrail_flavor_small', vms_on_single_compute=False):
        super(sdnTopoSetupFixture, self).setUp()
        topo = {}
        topo_objs = {}
        self.config_topo = {}
        self.flavor = flavor
        total_vm_cnt = 0
        fip_possible = False

        # If a vm to compute node mapping is defined pass it on to topo_setup()
        VmToNodeMapping = None
        if 'vm_node_map' in dir(self.topo):
            VmToNodeMapping = self.topo.vm_node_map
        self.public_vn_present = False
        self.fvn_vm_map = False
        self.fip_ip_by_vm = {
        }
        self.fvn_fixture = None
        self.fip_fixture = None
        self.fip_fixture_dict = {}
        topo_name = self.topo.__class__
        if 'project_list' in dir(self.topo):
            self.projectList = self.topo.project_list
        else:
            self.projectList = [self.inputs.project_name]
        for project in self.projectList:
            topo_obj = topo_name()
            # expect class topology elements to be defined under method
            # "build_topo_<project_name>"
            topo[project] = eval("topo_obj.build_topo_" + project + "()")
            out = self.useFixture(
                ProjectSetupFixture(self.connections, topo[project], config_option, skip_verify, flavor, vms_on_single_compute, VmToNodeMapping))
            if out.result == True:
                topo_objs[project] = out.topo
                self.config_topo[project] = out.config_topo
                total_vm_cnt = total_vm_cnt + len(self.config_topo[project]['vm'])
                fip_info = self.config_topo[project]['fip']
                # If public VN present, get the public vn and FIP fixture obj
                if fip_info[0]:
                    self.public_vn_present = True
                    self.fvn_fixture = fip_info[1]
                    self.fip_fixture = fip_info[2]
                self.logger.info("Setup completed for project %s with result %s" %
                                 (project, out.result))
            if out.result == False:
                self.logger.info("Setup failed for project %s " %(project))
                self.result = out.result
                self.msg = out.err_msg
                return 
        self.data = [topo_objs, self.config_topo]

        # Allocate and Associate floating IP to VM,if there is any provision to
        # do so; this is for public-vn [with access to IPs from lab network]
        fip_possible = topo_steps.verify_fip_associate_possible(
            self, vm_cnt=total_vm_cnt)
        if fip_possible:
            topo_steps.allocateNassociateFIP(self, self.config_topo)
            self.data = [topo_objs, self.config_topo, [fip_possible, self.fip_ip_by_vm]]

        # Extra steps to assign FIP from VNs configured with FIP pool to VMs as defined in topology
        topo_steps.createAllocateAssociateVnFIPPools(self)

        # Save config data for calling tests to refer..
        self.result = out.result
        self.msg = out.err_msg

    # end setUp

    def cleanUp(self):
        if self.inputs.fixture_cleanup == 'yes':
            super(sdnTopoSetupFixture, self).cleanUp()
        else:
            self.logger.info('Skipping sdn topology config cleanup')
    # end cleanUp

# end sdnSetupFixture
