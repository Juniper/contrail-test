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
from scripts.securitygroup.config import ConfigSecGroup
from common.neutron.base import BaseNeutronTest
from common.neutron.lbaas.base import BaseTestLbaas
from tcutils import get_release
from contrail_fixtures import *
from quantum_test import QuantumHelper
from nova_test import NovaHelper
from tcutils.commands import *
from tcutils.util import *
from fabric.state import connections
from scripts.securitygroup.config import ConfigSecGroup

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
        assert self.vn11_fixture.verify_on_setup()
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


class VerifyFeatureTestCases(ConfigSecGroup):
    
    def verify_config_before_feature_test(self):
                
        result = True
        vn11_vm3_fixture = self.res.vn11_vm3_fixture
        vn11_vm4_fixture = self.res.vn11_vm4_fixture

        assert self.res.verify_common_objects()

        # Ping between project1 and project2
        self.logger.info("Ping across projects with policy")
        src_vm_project1 = self.res.config_topo['project1']['vm']['vmc1']
        dst_vm_project2 = self.res.config_topo['project2']['vm']['vmc2']
        if not src_vm_project1.ping_to_ip(dst_vm_project2.vm_ip):
            result = result and False
            self.logger.error(
                'Ping acorss project failed with allowed policy and security group rule..\n')
            assert result, "ping failed across projects with policy"

        # Check security group for vn11_vm3 and vn11_vm4 first deny icmp then
        # allow it expect ping accordingly ####

        assert vn11_vm3_fixture.ping_with_certainty(vn11_vm4_fixture.vm_ip)
        assert vn11_vm4_fixture.ping_with_certainty(vn11_vm3_fixture.vm_ip)

        sec_grp_obj = self.vnc_lib.security_group_read(
            fq_name=[u'default-domain', self.inputs.project_name, 'default'])
        vn11_vm3_fixture.remove_security_group(secgrp=sec_grp_obj.uuid)
        vn11_vm4_fixture.remove_security_group(secgrp=sec_grp_obj.uuid)

        result = self.check_secgrp_traffic()
        assert result

        # checking traffic between common resource vm's by floating ip rule ###

        result = self.check_floatingip_traffic()
        assert result

        # Checking  Policy between vn11 and vn22  ######

        result = self.check_policy_traffic()
        assert result

        # Validate the service chaining in network  datapath ###

        for si_fix in self.res.si_fixtures:
            si_fix.verify_on_setup()

        assert self.res.vm1_fixture.ping_with_certainty(
            self.res.vm2_fixture.vm_ip)

        return result
    # end verify_config_before_feature_test

    
    def verify_config_after_feature_test(self):
        result = True
        assert self.res.verify_common_objects_without_collector()
        vn11_fixture = self.res.vn11_fixture
        vn11_vm3_fixture = self.res.vn11_vm3_fixture
        vn11_vm4_fixture = self.res.vn11_vm4_fixture
        vn22_fixture = self.res.vn22_fixture

        # Ping between project1 and project2
        self.logger.info("Ping across projects with policy")
        src_vm_project1 = self.res.config_topo['project1']['vm']['vmc1']
        dst_vm_project2 = self.res.config_topo['project2']['vm']['vmc2']
        if not src_vm_project1.ping_to_ip(dst_vm_project2.vm_ip):
            result = result and False
            self.logger.error(
                'Ping acorss project failed with allowed policy and security group rule..\n')
            assert result, "ping failed across projects with policy"

        # Check security group for vn11_vm3 and vn11_vm4 first add default
        # secgrp then remove it and add new secgrp to  deny icmp then allow it
        # expect ping accordingly ####

        sec_grp_obj = self.vnc_lib.security_group_read(
            fq_name=[u'default-domain', self.inputs.project_name, 'default'])
        vn11_vm3_fixture.add_security_group(secgrp=sec_grp_obj.uuid)
        vn11_vm3_fixture.verify_security_group('default')
        vn11_vm4_fixture.add_security_group(secgrp=sec_grp_obj.uuid)
        vn11_vm4_fixture.verify_security_group('default')

        assert vn11_vm3_fixture.ping_with_certainty(vn11_vm4_fixture.vm_ip)
        assert vn11_vm4_fixture.ping_with_certainty(vn11_vm3_fixture.vm_ip)

        vn11_vm3_fixture.remove_security_group(secgrp=sec_grp_obj.uuid)
        vn11_vm4_fixture.remove_security_group(secgrp=sec_grp_obj.uuid)

        result = self.check_secgrp_traffic()
        assert result

        # checking traffic using floating ip defined before upgrade  ####

        result = self.check_floatingip_traffic()
        assert result

        # checking policy before upgrade ####

        result = self.check_policy_traffic()
        assert result

        # creating new resources after upgrade #####

        new_res = self.vn_add_delete()
        result = result and new_res
        assert result

        new_res = self.vm_add_delete()
        result = result and new_res
        assert result

        # create floating ip with new vms #######
        fip_pool_name = 'some-pool'
        self.fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name, vn_id=self.res.vn11_fixture.vn_id))

        self.fip_new_id = self.fip_fixture1.create_and_assoc_fip(
            self.res.vn11_fixture.vn_id, self.vm22_fixture.vm_id)
        assert self.fip_fixture1.verify_fip(
            self.fip_new_id, self.vm22_fixture, self.res.vn11_fixture)
        self.addCleanup(self.fip_fixture1.disassoc_and_delete_fip,
                        self.fip_new_id)

        self.fip_new_id1 = self.fip_fixture1.create_and_assoc_fip(
            self.res.vn11_fixture.vn_id, self.vm33_fixture.vm_id)
        assert self.fip_fixture1.verify_fip(
            self.fip_new_id1, self.vm33_fixture, self.res.vn11_fixture)
        self.addCleanup(self.fip_fixture1.disassoc_and_delete_fip,
                        self.fip_new_id1)

        self.logger.debug('pinging from vn22_vm1_mine to fip_vn_vm1_mine \n')
        if not self.vm22_fixture.ping_with_certainty(self.fip_fixture1.fip[self.fip_new_id1]):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result
        fips = self.vm22_fixture.vnc_lib_h.floating_ip_read(
            id=self.fip_new_id).get_floating_ip_address()

        self.logger.debug('pinging from vn11_vm1_mine to vn22_vm1_mine \n')
        if not self.vm11_fixture.ping_to_ip(fips):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result

        # Creating policy  for newly created vn's

        newvn_fixture = self.newvn_fixture
        newvn11_fixture = self.newvn11_fixture

        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any', 'src_ports': 'any',
                'dst_ports': 'any',
                'source_network': 'any',
                'dest_network': 'any',
            },
        ]
        policy_name = 'newpolicy'

        policy_fixture1 = self.useFixture(
            PolicyFixture(
                policy_name=policy_name, rules_list=rules, inputs=self.inputs,
                connections=self.connections))

        policy_fq_name = [policy_fixture1.policy_fq_name]
        newvn_fixture.bind_policies(policy_fq_name, newvn_fixture.vn_id)
        self.addCleanup(newvn_fixture.unbind_policies,
                        newvn_fixture.vn_id, [policy_fixture1.policy_fq_name])
        newvn11_fixture.bind_policies(policy_fq_name, newvn11_fixture.vn_id)
        self.addCleanup(newvn11_fixture.unbind_policies,
                        newvn11_fixture.vn_id, [policy_fixture1.policy_fq_name])

        assert newvn_fixture.verify_on_setup()
        assert newvn11_fixture.verify_on_setup()

        self.logger.debug(
            "Pinging from newvn_vm1_mine to newvn11_vm1_mine by policy rule ")

        if not self.vm4_fixture.ping_with_certainty(self.vm5_fixture.vm_ip, expectation=True):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result
        if not self.vm5_fixture.ping_with_certainty(self.vm4_fixture.vm_ip, expectation=True):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result
        # Validate the service chaining in network  datapath ###

        for si_fix in self.res.si_fixtures:
            si_fix.verify_on_setup()

        assert self.res.vm1_fixture.ping_with_certainty(
            self.res.vm2_fixture.vm_ip)

        return result
    # end verify_config_after_feature_test
    
    def check_secgrp_traffic(self):
        result = True
        vn11_vm3_fixture = self.res.vn11_vm3_fixture
        vn11_vm4_fixture = self.res.vn11_vm4_fixture

        self.sg1_name = get_random_name('sec_grp1')
        rule = [{'direction': '<>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '192.168.1.0', 'ip_prefix_len': 24}}, ],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': '192.168.1.0', 'ip_prefix_len': 24}}, ],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]

        self.secgrp_fixture = self.config_sec_group(
            name=self.sg1_name, entries=rule)
        self.logger.info("Adding the sec groups to the VM's")
        vn11_vm3_fixture.add_security_group(secgrp=self.sg1_name)
        vn11_vm3_fixture.verify_security_group(self.sg1_name)
        vn11_vm4_fixture.add_security_group(secgrp=self.sg1_name)
        vn11_vm4_fixture.verify_security_group(self.sg1_name)

        # vn11_vm3 and vn11_vm4 are in sme(vm_name1)ec_grp1  not allowing icmp traffic so
        # ping should fail ###
        self.logger.info("test for Security Group ")
        if vn11_vm3_fixture.ping_to_ip(vn11_vm4_fixture.vm_ip) or vn11_vm4_fixture.ping_to_ip(vn11_vm3_fixture.vm_ip):
            result = result and False
            self.logger.error(
                'Test to ping between VMs was  expected to FAIL problem with security group \n')
            assert result
        self.logger.info(
            "Ping test between vms  vn11_vm3  and vn11_vm4 was expected to fail since security group denies  'icmp' traffic")

        rule = [{'direction': '<>',
                'protocol': 'icmp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '192.168.1.0', 'ip_prefix_len': 24}}, ],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'icmp',
                 'src_addresses': [{'subnet': {'ip_prefix': '192.168.1.0', 'ip_prefix_len': 24}}, ],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]

        self.secgrp_fixture.replace_rules(rule)
        if not (vn11_vm3_fixture.ping_with_certainty(vn11_vm4_fixture.vm_ip) and vn11_vm4_fixture.ping_with_certainty(vn11_vm3_fixture.vm_ip)):
            result = result and False
            assert result, 'Failed in replacing security group rules to allow icmp traffic'
        vn11_vm3_fixture.remove_security_group(secgrp=self.sg1_name)
        vn11_vm4_fixture.remove_security_group(secgrp=self.sg1_name)

        return result
    #end check_secgrp_traffic

    def check_policy_traffic(self):

        result = True
        vn11_vm2_fixture = self.res.vn11_vm2_fixture
        vn22_vm2_fixture = self.res.vn22_vm2_fixture
        self.logger.debug("Pinging from vn11_vm2 to vn22_vm2 by policy rule ")

        if not vn11_vm2_fixture.ping_with_certainty(vn22_vm2_fixture.vm_ip, expectation=True):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result

        self.logger.debug("Pinging from vn22_vm2 to vn11_vm2 by policy rule ")

        if not vn22_vm2_fixture.ping_with_certainty(vn11_vm2_fixture.vm_ip, expectation=True):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result
        return result
    #end check_policy_traffic

    def check_floatingip_traffic(self):

        result = True
        vn11_fixture = self.res.vn11_fixture
        vn22_fixture = self.res.vn22_fixture
        fvn_fixture = self.res.fvn_fixture
        vn11_vm1_fixture = self.res.vn11_vm1_fixture
        vn22_vm1_fixture = self.res.vn22_vm1_fixture
        fvn_vm1_fixture = self.res.fvn_vm1_fixture
        fip_fixture = self.res.fip_fixture
        fip_id = self.res.fip_id
        fip_id1 = self.res.fip_id1
        self.logger.debug('pinging from VN11_VM1 TO VN22_VM1 \n')
        if not vn11_vm1_fixture.ping_with_certainty(fip_fixture.fip[fip_id1]):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result

        self.logger.debug('pinging from VN11_VM1 TO FVN_VM1 \n')
        if not vn11_vm1_fixture.ping_to_ip(fvn_vm1_fixture.vm_ip):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result

        self.logger.debug('pinging from VN22_VM1 TO FVN_VM1 \n')
        if not vn22_vm1_fixture.ping_to_ip(fvn_vm1_fixture.vm_ip):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result

        fip = vn11_vm1_fixture.vnc_lib_h.floating_ip_read(
            id=fip_id).get_floating_ip_address()

        self.logger.debug('pinging from FVN_VM1 to VN11_VM1 \n')
        if not fvn_vm1_fixture.ping_to_ip(fip):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result
        return result
    #end check_floatingip_traffic

    # adding function to create more resources these will be created after feature test    
    def vn_add_delete(self):

        self.newvn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='newvn', inputs=self.inputs, subnets=['22.1.1.0/24']))
        self.newvn_fixture.verify_on_setup()

        self.newvn11_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='newvn11', inputs=self.inputs, subnets=['11.1.1.0/24']))
        self.newvn11_fixture.verify_on_setup()

        return True
    #end vn_add_delete
    
    def vm_add_delete(self):

        vm1_name = 'vn11_vm1_mine'
        vm2_name = 'vn22_vm1_mine'
        vm3_name = 'fip_vn_vm1_mine'
        vm4_name = 'newvn_vm1_mine'
        vm5_name = 'newvn11_vm1_mine'

        vn_obj = self.res.vn11_fixture.obj
        self.vm11_fixture = self.useFixture(
            VMFixture(connections=self.connections,
                      vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name))
        assert self.vm11_fixture.verify_on_setup()

        vn_obj = self.res.vn22_fixture.obj
        self.vm22_fixture = self.useFixture(
            VMFixture(connections=self.connections,
                      vn_obj=vn_obj, vm_name=vm2_name, project_name=self.inputs.project_name))
        assert self.vm22_fixture.verify_on_setup()

        vn_obj = self.res.fvn_fixture.obj
        self.vm33_fixture = self.useFixture(
            VMFixture(connections=self.connections,
                      vn_obj=vn_obj, vm_name=vm3_name, project_name=self.inputs.project_name))
        assert self.vm33_fixture.verify_on_setup()

        vn_obj = self.newvn_fixture.obj
        self.vm4_fixture = self.useFixture(
            VMFixture(connections=self.connections,
                      vn_obj=vn_obj, vm_name=vm4_name, project_name=self.inputs.project_name))
        assert self.vm4_fixture.verify_on_setup()

        vn_obj = self.newvn11_fixture.obj
        self.vm5_fixture = self.useFixture(
            VMFixture(connections=self.connections,
                      vn_obj=vn_obj, vm_name=vm5_name, project_name=self.inputs.project_name))
        assert self.vm5_fixture.verify_on_setup()

        return True
    #end vm_add_delete
