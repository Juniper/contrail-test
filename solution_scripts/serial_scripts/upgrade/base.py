import test
from common.connections import ContrailConnections
from common.contrail_test_init import ContrailTestInit
from common import isolated_creds
from vn_test import VNFixture
from vm_test import VMFixture
import fixtures
from policy_test import PolicyFixture
from floating_ip import FloatingIPFixture 
from tcutils.topo.sdn_topo_setup import sdnTopoSetupFixture
from sdn_topo_with_multi_project import *
from common.servicechain.config import ConfigSvcChain
from common.servicechain.verify import VerifySvcChain
from common.neutron.base import BaseNeutronTest
from common.neutron.lbaas.base import BaseTestLbaas
from tcutils import get_release

class UpgradeBaseTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(UpgradeBaseTest, cls).setUpClass()
        cls.isolated_creds = isolated_creds.IsolatedCreds(cls.__name__, cls.inputs, ini_file = cls.ini_file, logger = cls.logger)
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant()
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.connections = cls.isolated_creds.get_conections()
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        resource_class = cls.__name__ + 'Resource'
        cls.res = ResourceFactory.createResource(resource_class)
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.res.cleanUp()
        cls.isolated_creds.delete_tenant()
        super(UpgradeBaseTest, cls).tearDownClass()
    #end tearDownClass

class ResourceFactory:
    factories = {}
    def createResource(id):
        if not ResourceFactory.factories.has_key(id):
            ResourceFactory.factories[id] = \
              eval(id + '.Factory()')
        return ResourceFactory.factories[id].create()
    createResource = staticmethod(createResource)

class BaseResource(fixtures.Fixture, ConfigSvcChain, VerifySvcChain, BaseTestLbaas, BaseNeutronTest):

    def setUp(self, inputs, connections, logger):
        super(BaseResource , self).setUp()
        self.inputs = inputs
        self.connections = connections
        self.logger = logger
        self.quantum_h = connections.quantum_h
        self.vnc_lib = connections.vnc_lib
        self.setup_common_objects(self.inputs , self.connections)

    def cleanUp(self):
        super(BaseResource, self).cleanUp()

    def setup_common_objects(self, inputs, connections):
        self.inputs = inputs
        self.connections = connections
        self.base_rel = get_release() 
        (self.vn11_name, self.vn11_subnets) = ("vn11", ["192.168.1.0/24"])
        (self.vn22_name, self.vn22_subnets) = ("vn22", ["192.168.2.0/24"])
        (self.fip_vn_name, self.fip_vn_subnets) = ("fip_vn", ['200.1.1.0/24'])
        (self.vn11_vm1_name, self.vn11_vm2_name, self.vn11_vm3_name,
         self.vn11_vm4_name) = ('vn11_vm1', 'vn11_vm2', 'vn11_vm3', 'vn11_vm4')
        self.vn22_vm1_name = 'vn22_vm1'
        self.vn22_vm2_name = 'vn22_vm2'
        self.fvn_vm1_name = 'fvn_vm1'

        # Configure 3 VNs, 2 of them vn11, vn22 and 1 fip_vn
        self.vn11_fixture = self.useFixture(
            VNFixture(project_name=self.inputs.project_name,
                      connections=self.connections, inputs=self.inputs, vn_name=self.vn11_name, subnets=self.vn11_subnets))
        self.vn22_fixture = self.useFixture(
            VNFixture(project_name=self.inputs.project_name,
                      connections=self.connections, inputs=self.inputs, vn_name=self.vn22_name, subnets=self.vn22_subnets))
        self.fvn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                inputs=self.inputs, vn_name=self.fip_vn_name, subnets=self.fip_vn_subnets))

        # Configure 4 VMs in VN11, 2 VM in VN22, and 1 VM in FVN
        self.vn11_vm1_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections, vn_obj=self.vn11_fixture.obj, vm_name=self.vn11_vm1_name, image_name='ubuntu'))
        self.vn11_vm2_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections, vn_obj=self.vn11_fixture.obj, vm_name=self.vn11_vm2_name, image_name='ubuntu'))
        self.vn11_vm3_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections, vn_obj=self.vn11_fixture.obj, vm_name=self.vn11_vm3_name, image_name='ubuntu'))
        self.vn11_vm4_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections, vn_obj=self.vn11_fixture.obj, vm_name=self.vn11_vm4_name, image_name='ubuntu'))
        self.vn22_vm1_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections, vn_obj=self.vn22_fixture.obj, vm_name=self.vn22_vm1_name, image_name='ubuntu'))
        self.vn22_vm2_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections, vn_obj=self.vn22_fixture.obj, vm_name=self.vn22_vm2_name, image_name='ubuntu'))
        self.fvn_vm1_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections, vn_obj=self.fvn_fixture.obj, vm_name=self.fvn_vm1_name, image_name='ubuntu'))

        # Adding Policy between vn11 and vn22  ######
        assert self.vn11_fixture.verify_on_setup()
        assert self.vn22_fixture.verify_on_setup()
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any', 'src_ports': 'any',
                'dst_ports': 'any',
                'source_network': 'any',
                'dest_network': 'any',
            },
        ]
        policy_name = 'p1'

        self.policy_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name, rules_list=rules, inputs=self.inputs,
                connections=self.connections))

        policy_fq_name = [self.policy_fixture.policy_fq_name]
        self.vn11_fixture.bind_policies(
            policy_fq_name, self.vn11_fixture.vn_id)
        self.addCleanup(self.vn11_fixture.unbind_policies,
                        self.vn11_fixture.vn_id, [self.policy_fixture.policy_fq_name])
        self.vn22_fixture.bind_policies(
            policy_fq_name, self.vn22_fixture.vn_id)
        self.addCleanup(self.vn22_fixture.unbind_policies,
                        self.vn22_fixture.vn_id, [self.policy_fixture.policy_fq_name])

        # Adding Floating ip ###

        assert self.fvn_fixture.verify_on_setup()

        fip_pool_name = 'some-pool1'
        self.fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name, vn_id=self.fvn_fixture.vn_id))

        self.vn11_vm1_fixture.verify_on_setup()
        self.vn11_vm1_fixture.wait_till_vm_is_up()
        self.fip_id = self.fip_fixture.create_and_assoc_fip(
            self.fvn_fixture.vn_id, self.vn11_vm1_fixture.vm_id)
        self.addCleanup(self.fip_fixture.disassoc_and_delete_fip, self.fip_id)
        assert self.fip_fixture.verify_fip(
            self.fip_id, self.vn11_vm1_fixture, self.fvn_fixture)

        self.vn22_vm1_fixture.verify_on_setup()
        self.vn22_vm1_fixture.wait_till_vm_is_up()
        self.fip_id1 = self.fip_fixture.create_and_assoc_fip(
            self.fvn_fixture.vn_id, self.vn22_vm1_fixture.vm_id)
        assert self.fip_fixture.verify_fip(
            self.fip_id1, self.vn22_vm1_fixture, self.fvn_fixture)
        self.addCleanup(self.fip_fixture.disassoc_and_delete_fip, self.fip_id1)

        # Adding  the service chaining resources for firewall  ###
        si_count = 1
        svc_scaling = False
        max_inst = 1
        svc_mode = 'in-network'
        flavor = 'm1.medium'
        self.vn1_fq_name = "default-domain:" + self.inputs.project_name + ":in_network_vn1"
        self.vn1_name = "in_network_vn1"
        self.vn1_subnets = ['10.1.1.0/24']
        self.vm1_name = 'in_network_vm1'
        self.vn2_fq_name = "default-domain:" + self.inputs.project_name + ":in_network_vn2"
        self.vn2_name = "in_network_vn2"
        self.vn2_subnets = ['20.2.2.0/24']
        self.vm2_name = 'in_network_vm2'

        self.action_list = []
        self.if_list = [['management', False], ['left', True], ['right', True]]
        self.st_name = 'in_net_svc_template_1'
        si_prefix = 'in_net_svc_instance_'
        self.policy_name = 'policy_in_network'

        self.vn1_fixture = self.config_vn(self.vn1_name, self.vn1_subnets)
        self.vn2_fixture = self.config_vn(self.vn2_name, self.vn2_subnets)
        self.st_fixture, self.si_fixtures = self.config_st_si(
            self.st_name, si_prefix, si_count, svc_scaling, max_inst, project=self.inputs.project_name, left_vn=self.vn1_fq_name, right_vn=self.vn2_fq_name, svc_mode=svc_mode, flavor=flavor)
        self.action_list = self.chain_si(si_count, si_prefix, self.inputs.project_name)
        self.rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': self.vn1_name,
                'src_ports': [0, -1],
                'dest_network': self.vn2_name,
                'dst_ports': [0, -1],
                'simple_action': None,
                'action_list': {'apply_service': self.action_list}
            },
        ]
        self.policy_fixtures = self.config_policy(self.policy_name, self.rules)

        self.vn1_policy_fix = self.attach_policy_to_vn(
            self.policy_fixtures, self.vn1_fixture)
        self.vn2_policy_fix = self.attach_policy_to_vn(
            self.policy_fixtures, self.vn2_fixture)
        self.vm1_fixture = self.config_vm(self.vn1_fixture, self.vm1_name)
        self.vm2_fixture = self.config_vm(self.vn2_fixture, self.vm2_name)
        #self.vm1_fixture.verify_on_setup()
        #self.vm2_fixture.verify_on_setup()
        self.vm1_fixture.wait_till_vm_is_up()
        self.vm2_fixture.wait_till_vm_is_up()

        result, msg = self.validate_vn(self.vn1_name, project_name=self.inputs.project_name)
        assert result, msg
        result, msg = self.validate_vn(self.vn2_name, project_name=self.inputs.project_name)
        assert result, msg

        # non-admin tenant config
        result = True
        msg = []
        self.topo_obj = sdn_topo_with_multi_project()
        self.setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, self.topo_obj))
        out = self.setup_obj.sdn_topo_setup()
        self.assertEqual(out['result'], True, out['msg'])
        if out['result'] == True:
            self.topo_objs, self.config_topo, vm_fip_info = out['data']

        # snat config
        # TO DO

        # lbass config
        # TO DO

    # end setup_common_objects

    def verify_common_objects_without_collector(self):
        assert self.vn11_fixture.verify_on_setup_without_collector()
        assert self.vn22_fixture.verify_on_setup_without_collector()
        assert self.fvn_fixture.verify_on_setup_without_collector()
        assert self.vn11_vm1_fixture.verify_on_setup()
        assert self.vn11_vm2_fixture.verify_on_setup()
        assert self.vn11_vm3_fixture.verify_on_setup()
        assert self.vn11_vm4_fixture.verify_on_setup()
        assert self.vn22_vm1_fixture.verify_on_setup()
        assert self.vn22_vm2_fixture.verify_on_setup()
        assert self.fvn_vm1_fixture.verify_on_setup()
        assert self.vn1_fixture.verify_on_setup_without_collector()
        assert self.vn2_fixture.verify_on_setup_without_collector()
        assert self.vm1_fixture.verify_on_setup()
        assert self.vm2_fixture.verify_on_setup()
        assert self.fip_fixture.verify_on_setup()
        # non-admin tenant verification
        assert self.setup_obj.verify_sdn_topology(
            self.topo_objs, self.config_topo)
        return True

    def verify_common_objects(self):
        assert self.vn11_fixture.verify_on_setup()
        assert self.vn22_fixture.verify_on_setup()
        assert self.fvn_fixture.verify_on_setup()
        self.vn11_vm1_fixture.verify_on_setup()
        self.vn11_vm1_fixture.wait_till_vm_is_up()
        self.vn11_vm2_fixture.verify_on_setup()
        self.vn11_vm2_fixture.wait_till_vm_is_up()
        self.vn11_vm3_fixture.verify_on_setup()
        self.vn11_vm3_fixture.wait_till_vm_is_up()
        self.vn11_vm4_fixture.verify_on_setup()
        self.vn11_vm4_fixture.wait_till_vm_is_up()
        self.vn22_vm1_fixture.verify_on_setup()
        self.vn22_vm1_fixture.wait_till_vm_is_up()
        self.vn22_vm2_fixture.verify_on_setup()
        self.vn22_vm2_fixture.wait_till_vm_is_up()
        self.fvn_vm1_fixture.verify_on_setup()
        self.fvn_vm1_fixture.wait_till_vm_is_up()
        assert self.fip_fixture.verify_on_setup()
        # non-admin tenant verification
        assert self.setup_obj.verify_sdn_topology(
            self.topo_objs, self.config_topo)
        return True
    # end verify_common_objects

class UpgradeTestSanityWithResourceResource(BaseResource):

    def setUp(self,inputs,connections, logger):
        super(UpgradeTestSanityWithResourceResource, self).setUp(inputs,connections, logger)

    def cleanUp(self):
        super(UpgradeTestSanityWithResourceResource, self).cleanUp()

    class Factory:
        def create(self): return UpgradeTestSanityWithResourceResource()

    def runTest(self):
        pass

#End resource

