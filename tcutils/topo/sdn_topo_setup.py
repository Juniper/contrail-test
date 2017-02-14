import os
import copy
import fixtures
import testtools
import topo_steps
from common.contrail_test_init import ContrailTestInit
from vn_test import *
from vn_policy_test import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from common.connections import ContrailConnections
from floating_ip import *
from policy_test import *
from contrail_fixtures import *
from tcutils.agent.vna_introspect_utils import *
from topo_helper import *
from vnc_api import vnc_api
from vnc_api.gen.resource_test import *
try:
    from webui_test import *
except ImportError:
    pass

class sdnTopoSetupFixture(fixtures.Fixture):

    def __init__(self, connections, topo):
        self.ini_file = os.environ.get('TEST_CONFIG_FILE')
        self.connections = connections
        self.inputs = self.connections.inputs
        self.quantum_h = self.connections.quantum_h
        self.nova_h = self.connections.nova_h
        self.vnc_lib = self.connections.vnc_lib
        self.orch = self.connections.orch
        self.logger = self.inputs.logger
        self.topo = topo
        if self.inputs.verify_thru_gui():
            self.browser = self.connections.browser
            self.browser_openstack = self.connections.browser_openstack
            self.webui = WebuiTest(self.connections, self.inputs)
    # end __init__

    def setUp(self):
        super(sdnTopoSetupFixture, self).setUp()
    # end setUp

    def topo_setup(self, config_option='openstack', skip_verify='no', flavor='contrail_flavor_small', vms_on_single_compute=False, VmToNodeMapping=None):
        '''Take topology to be configured as input and return received & configured topology -collection 
        of dictionaries. we return received topology as some data is updated and is required for 
        reference.
        Bring up with 2G RAM to support multiple traffic streams..For scaling tests, min of 8192 is recommended.
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
        config_option = 'contrail' if self.inputs.orchestrator == 'vcenter' else config_option
        self.result = True
        self.err_msg = []
        self.flavor = flavor
        self.skip_verify = skip_verify
        self.public_vn_present = False
        self.fvn_vm_map = False
        self.fvn_fixture = None
        self.fip_fixture = None
        self.si_fixture = {}
        self.fip_fixture_dict = {
        }
        self.secgrp_fixture = None
        topo_helper_obj = topology_helper(self.topo)
        self.topo.vmc_list = topo_helper_obj.get_vmc_list()
        self.topo.policy_vn = topo_helper_obj.get_policy_vn()
        self.logger.debug("Starting setup")
        topo_helper_obj.update_policy_rules_for_v6_test(self.inputs.get_af())
        topo_steps.createUser(self)
        topo_steps.createProject(self)
        topo_steps.createSec_group(self, option=config_option)
        topo_steps.createServiceTemplate(self)
        topo_steps.createServiceInstance(self)
        topo_steps.createIPAM(self, option=config_option)
        topo_steps.createVN(self, option=config_option)
        topo_steps.createPolicy(self, option=config_option)
        topo_steps.attachPolicytoVN(self, option=config_option)
        # If vm to node pinning is defined then pass it on to create VM method.
        if VmToNodeMapping is not None:
            topo_steps.createVMNova(
                self, config_option, vms_on_single_compute, VmToNodeMapping)
        else:
            topo_steps.createVMNova(self, config_option, vms_on_single_compute)
        topo_steps.createPublicVN(self)
        topo_steps.verifySystemPolicy(self)
        # prepare return data
        config_topo = {
            'project': self.project_fixture, 'policy': self.policy_fixt, 'vn': self.vn_fixture, 'vm': self.vm_fixture,
            'fip': [self.public_vn_present, self.fvn_fixture, self.fip_fixture, self.fvn_vm_map, self.fip_fixture_dict],
            'si': self.si_fixture, 'st': self.st_fixture, 'sec_grp': self.secgrp_fixture, 'ipam': self.ipam_fixture}
        if self.err_msg != []:
            self.result = False
        updated_topo = copy.copy(self.topo)
        return {'result': self.result, 'msg': self.err_msg, 'data': [updated_topo, config_topo]}
    # end topo_setup

    def sdn_topo_setup(self, config_option='openstack', skip_verify='no', flavor='contrail_flavor_small', vms_on_single_compute=False):
        '''This is wrapper script which internally calls topo_setup to setup sdn topology based on topology.
        This wrapper is basically used to configure multiple projects and it support assigning of FIP to VM from public VN.
        '''
        topo = {}
        topo_objs = {}
        config_topo = {}
        result = True
        err_msg = [
        ]
        total_vm_cnt = 0
        fip_possible = False

        # If a vm to compute node mapping is defined pass it on to topo_setup()
        try:
            if self.topo.vm_node_map:
                VmToNodeMapping = self.topo.vm_node_map
            else:
                VmToNodeMapping = None
        except:
            VmToNodeMapping = None

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
            setup_obj = {}
            topo_obj = topo_name()
            # expect class topology elements to be defined under method
            # "build_topo_<project_name>"
            try:
                topo[project] = eval("topo_obj." + self.topo.topo_of_project[project] + "(" +
                                        "project='" + project +
                                        "',username='" + self.topo.user_of_project[project] +
                                        "',password='" + self.topo.pass_of_project[project] +
                                        "',config_option='" + config_option +
                                        "')")
            except (NameError, AttributeError):
                topo[project] = eval("topo_obj.build_topo_" + project + "()")

            setup_obj[project] = self.useFixture(
                sdnTopoSetupFixture(self.connections, topo[project]))
            out = setup_obj[project].topo_setup(
                config_option, skip_verify, flavor, vms_on_single_compute, VmToNodeMapping)
            if out['result'] == True:
                topo_objs[project], config_topo[project] = out['data']
            total_vm_cnt = total_vm_cnt + len(config_topo[project]['vm'])
            fip_info = config_topo[project]['fip']
            # If public VN present, get the public vn and FIP fixture obj
            if fip_info[0]:
                self.public_vn_present = True
                self.fvn_fixture = fip_info[1]
                self.fip_fixture = fip_info[2]
            # If floating ip pools are created in VN's and supposed to be
            # assigned to VM's in other VN
            if fip_info[3]:
                self.fvn_vm_map = True
                self.fip_fixture_dict = fip_info[4]
            self.logger.info("Setup completed for project %s with result %s" %
                             (project, out['result']))
            if out['result'] == False:
                result = False
                err_msg.append(out['msg'])
        # Allocate and Associate floating IP to VM,if there is any provision to
        # do so
        fip_possible = topo_steps.verify_fip_associate_possible(
            self, vm_cnt=total_vm_cnt)
        if fip_possible:
            topo_steps.allocateNassociateFIP(self, config_topo)

        self.config_topo = config_topo
        # Extra steps to assign FIP from VNs configured with FIP pool to VMs as defined in topology
        topo_steps.createAllocateAssociateVnFIPPools(self)

        if len(self.projectList) == 1 and 'admin' in self.projectList:
            return {'result': result, 'msg': err_msg, 'data': [topo_objs[self.inputs.project_name], config_topo[self.inputs.project_name], [fip_possible, self.fip_ip_by_vm]]}
        else:
            return {'result': result, 'msg': err_msg, 'data': [topo_objs, config_topo, [fip_possible, self.fip_ip_by_vm]]}

    # end sdn_topo_setup

    def verify_sdn_topology(self, topo_objects, config_topo):
        """Verify basic components of sdn topology. Takes topo_objects and config_topo as input parameter"""
        for project in topo_objects.keys():
            # verify projects
            assert config_topo[project]['project'][
                project].verify_on_setup(), "One or more verifications failed for Project:%s" % project
            # verify security-groups
            for sec_grp in topo_objects[project].sg_list:
                assert config_topo[project]['sec_grp'][sec_grp].verify_on_setup(
                ), "One or more verifications failed for Security-Group:%s" % sec_grp
            # verify virtual-networks and ipams
            for vnet in topo_objects[project].vnet_list:
                assert config_topo[project]['vn'][vnet].verify_on_setup_without_collector(
                ), "One or more verifications failed for VN:%s" % vnet
                if vnet in topo_objects[project].vn_ipams.keys():
                    ipam = topo_objects[project].vn_ipams[vnet]
                    assert config_topo[project]['ipam'][
                        ipam].verify_on_setup(), "One or more verifications failed for IPAM:%s" % ipam
            # verify policy
            for policy in topo_objects[project].policy_list:
                assert config_topo[project]['policy'][
                    policy].verify_on_setup(), "One or more verifications failed for Policy:%s" % policy
            # verify virtual-machines
            for vmc in topo_objects[project].vmc_list:
                assert config_topo[project]['vm'][
                    vmc].verify_on_setup(), "One or more verifications failed for VM:%s" % vmc
        return True
    # end verify_sdn_topology

    def cleanUp(self):
        if self.inputs.fixture_cleanup == 'yes':
            super(sdnTopoSetupFixture, self).cleanUp()
        else:
            self.logger.info('Skipping sdn topology config cleanup')
    # end cleanUp

# end sdnSetupFixture
