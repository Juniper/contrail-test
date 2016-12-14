import os
import copy
from common.openstack_libs import nova_client as mynovaclient
from common.openstack_libs import nova_exception as novaException
import fixtures
import testtools
from tcutils.topo import topo_steps
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
from tcutils.topo.topo_helper import *
from vnc_api import vnc_api
from vnc_api.gen.resource_test import *
try:
    from webui_test import *
    from tcutils.topo import ui_topo_steps
except ImportError:
    pass


class sdnUiTopoSetupFixture(fixtures.Fixture):

    def __init__(self, connections, topo):
        self.ini_file = os.environ.get('TEST_CONFIG_FILE')
        self.connections = connections
        self.inputs = self.connections.inputs
        self.quantum_h = self.connections.quantum_h
        self.nova_h = self.connections.nova_h
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.topo = topo
        self.orch = self.connections.orch
        if self.inputs.verify_thru_gui():
            self.browser = self.connections.browser
            self.browser_openstack = self.connections.browser_openstack
            self.webui = WebuiTest(self.connections, self.inputs)
    # end __init__

    def setUp(self):
        super(sdnUiTopoSetupFixture, self).setUp()
    # end setUp

    def topo_setup(
            self,
            config_option='openstack',
            skip_verify='no',
            flavor='contrail_flavor_small',
            vms_on_single_compute=False,
            VmToNodeMapping=None):
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
        self.config_option = config_option
        self.secgrp_fixture = None
        self.config_topo = {}
        topo_helper_obj = topology_helper(self.topo)
        self.topo.vmc_list = topo_helper_obj.get_vmc_list()
        self.topo.policy_vn = topo_helper_obj.get_policy_vn()
        self.logger.info("Starting setup")
        topo_steps.createUser(self)
        topo_steps.createProject(self)
    # end topo_setup

    def create_security_group(self):
        assert topo_steps.createSec_group(self)
        return True
    # end create_security_group

    def create_svc_instance(self):
        assert topo_steps.createServiceInstance(self)
        return True
    # end create_svc_instance

    def create_policy(self):
        assert topo_steps.createPolicy(self)
        return True
    # end create_policy

    def attach_policy_to_vn(self, option='openstack'):
        assert topo_steps.attachPolicytoVN(self, option)
        return True
    # end attach_policy_to_vn

    def create_vm(self):
        assert topo_steps.createVMNova(self)
        return True
    # end create_vm

    def create_svc_template(self):
        assert topo_steps.createServiceTemplate(self)
        return True
    # end create_svc_template

    def create_dns_server(self):
        assert ui_topo_steps.createDnsServer(self)
        return True
    # end create_dns_server

    def create_dns_record(self):
        assert ui_topo_steps.createDnsRecord(self)
        return True
    # end create_dns_record

    def create_ipam(self):
        assert topo_steps.createIPAM(self)
        return True
    # end create_ipam

    def create_vn(self):
        assert topo_steps.createVN(self)
        return True
    # end create_vn

    def create_floating_ip(self):
        self.config_topo = {
            self.project_fixture.keys()[0] : {'vn' : self.vn_fixture, 
                                              'vm' : self.vm_fixture,
                                              'fip' : self.fip_fixture}
                       }
        assert topo_steps.createAllocateAssociateVnFIPPools(self, self.config_topo, alloc=False)
        return True
    # end create_floating_ip

    def allocate_floating_ip(self):
        assert topo_steps.allocNassocFIP(self, self.config_topo, assoc=False)
        return True
    # end allocate_floating_ip

    def associate_floating_ip(self):
        assert topo_steps.allocNassocFIP(self, self.config_topo)
        return True
    # end associate_floating_ip

    def create_port(self):
        assert ui_topo_steps.createPort(self)
        return True
    # end create_port

    def create_router(self):
        assert ui_topo_steps.createRouter(self)
        return True
    # end create_router

    def create_security_group(self, option='contrail'):
        assert topo_steps.createSec_group(self, option)
        return True
   # end create_security_group

    def cleanUp(self):
        if self.inputs.fixture_cleanup == 'yes':
            super(sdnUiTopoSetupFixture, self).cleanUp()
        else:
            self.logger.info('Skipping sdn topology config cleanup')
    # end cleanUp

# end sdnSetupFixture
