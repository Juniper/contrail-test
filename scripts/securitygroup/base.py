import test_v1
from vn_test import MultipleVNFixture
from vm_test import MultipleVMFixture
from fabric.api import run, hide, settings
from vn_test import VNFixture
from vm_test import VMFixture
from policy_test import PolicyFixture
from common.policy.config import ConfigPolicy
from security_group import SecurityGroupFixture, get_secgrp_id_from_name
from common import isolated_creds
from tcutils.util import get_random_name, copy_file_to_server, fab_put_file_to_vm
import os
from tcutils.topo.sdn_topo_setup import *

class BaseSGTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BaseSGTest, cls).setUpClass()
        cls.orch = cls.connections.orch
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        cls.api_s_inspect = cls.connections.api_server_inspect

    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseSGTest, cls).tearDownClass()
    #end tearDownClass

    def setUp(self):
        super(BaseSGTest, self).setUp()

    def tearDown(self):
        super(BaseSGTest, self).tearDown()

    def create_sg_test_resources(self):
        """Config common resources."""
        self.logger.info("Configuring setup for security group tests.")

        self.vn1_subnets = get_random_cidrs(self.inputs.get_af())
        self.vn2_subnets = get_random_cidrs(self.inputs.get_af())

        self.vn1_prefix = self.vn1_subnets[0].split('/')[0]
        self.vn1_prefix_len = int(self.vn1_subnets[0].split('/')[1])
        self.vn2_prefix = self.vn2_subnets[0].split('/')[0]
        self.vn2_prefix_len = int(self.vn2_subnets[0].split('/')[1])

        vn_s = {'vn1': self.vn1_subnets[0], 'vn2': self.vn2_subnets}

        self.multi_vn_fixture = self.useFixture(MultipleVNFixture(
            connections=self.connections, inputs=self.inputs, subnet_count=2,
            vn_name_net=vn_s,  project_name=self.inputs.project_name))
        vns = self.multi_vn_fixture.get_all_fixture_obj()
        (self.vn1_name, self.vn1_fix) = self.multi_vn_fixture._vn_fixtures[0]
        (self.vn2_name, self.vn2_fix) = self.multi_vn_fixture._vn_fixtures[1]

        self.logger.info("Configure security groups required for test.")
        self.config_sec_groups()

        self.multi_vm_fixture = self.useFixture(MultipleVMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vm_count_per_vn=3, vn_objs=vns, image_name='ubuntu-traffic',
            flavor='contrail_flavor_small'))
        vms = self.multi_vm_fixture.get_all_fixture()
        (self.vm1_name, self.vm1_fix) = vms[0]
        (self.vm2_name, self.vm2_fix) = vms[1]
        (self.vm3_name, self.vm3_fix) = vms[2]
        (self.vm4_name, self.vm4_fix) = vms[3]
        (self.vm5_name, self.vm5_fix) = vms[4]
        (self.vm6_name, self.vm6_fix) = vms[5]

        self.logger.info("Adding the sec groups to the VM's")
        self.vm1_fix.add_security_group(secgrp=self.sg1_name)
        self.vm1_fix.add_security_group(secgrp=self.sg2_name)
        self.vm2_fix.add_security_group(secgrp=self.sg2_name)
        self.vm4_fix.add_security_group(secgrp=self.sg1_name)
        self.vm4_fix.add_security_group(secgrp=self.sg2_name)
        self.vm5_fix.add_security_group(secgrp=self.sg1_name)

        self.logger.info("Remove the default sec group form the VM's")
	default_secgrp_id = get_secgrp_id_from_name(
                        	self.connections,
                        	':'.join([self.inputs.domain_name,
                                    self.inputs.project_name,
                                    'default']))
        self.vm1_fix.remove_security_group(secgrp=default_secgrp_id)
        self.vm2_fix.remove_security_group(secgrp=default_secgrp_id)
        self.vm4_fix.remove_security_group(secgrp=default_secgrp_id)
        self.vm5_fix.remove_security_group(secgrp=default_secgrp_id)

        self.logger.info("Verifying setup of security group tests.")
        self.verify_sg_test_resources()

        self.set_tcp_port_use_optimizations([self.vm1_fix, self.vm2_fix,
            self.vm3_fix, self.vm4_fix, self.vm5_fix, self.vm6_fix])

        self.logger.info(
            "Finished configuring setup for security group tests.")


    def config_sec_groups(self):
        self.sg1_name = 'test_tcp_sec_group' + '_' + get_random_name()
        rule = [{'direction': '<>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]

        self.sg1_fix = self.config_sec_group(name=self.sg1_name, entries=rule)

        self.sg2_name = 'test_udp_sec_group' + '_' + get_random_name()
        rule = [{'direction': '<>',
                'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': self.vn1_prefix,
                                        'ip_prefix_len': self.vn1_prefix_len}},
                                   {'subnet': {'ip_prefix': self.vn2_prefix,
                                        'ip_prefix_len': self.vn2_prefix_len}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.sg2_fix = self.config_sec_group(name=self.sg2_name, entries=rule)

    def verify_sg_test_resources(self):
        """verfiy common resources."""
        self.logger.debug("Verify the configured VN's.")
        assert self.multi_vn_fixture.verify_on_setup()

        self.logger.debug("Verify the configured VM's.")
        assert self.multi_vm_fixture.verify_on_setup()

        self.logger.debug("Verify the configured security groups.")
        result, msg = self.sg1_fix.verify_on_setup()
        assert result, msg
        result, msg = self.sg2_fix.verify_on_setup()
        assert result, msg

        self.logger.debug("Verify the attached security groups in the VM.")
        result, msg = self.vm1_fix.verify_security_group(self.sg1_name)
        assert result, msg
        result, msg = self.vm1_fix.verify_security_group(self.sg2_name)
        assert result, msg
        result, msg = self.vm2_fix.verify_security_group(self.sg2_name)
        assert result, msg
        result, msg = self.vm4_fix.verify_security_group(self.sg1_name)
        assert result, msg
        result, msg = self.vm4_fix.verify_security_group(self.sg2_name)
        assert result, msg
        result, msg = self.vm5_fix.verify_security_group(self.sg1_name)
        assert result, msg

        assert self.multi_vm_fixture.wait_for_ssh_on_vm()


    def config_sec_group(self, name, secgrpid=None, entries=None):
	option = self.option
	if self.option == 'openstack':
	    option = 'neutron'
        secgrp_fixture = self.useFixture(SecurityGroupFixture(self.inputs,
                                                              self.connections, self.inputs.domain_name, self.inputs.project_name,
                                                              secgrp_name=name, uuid=secgrpid, secgrp_entries=entries,option=option))
        result, msg = secgrp_fixture.verify_on_setup()
        assert result, msg
        return secgrp_fixture

    def delete_sec_group(self, secgrp_fix):
        secgrp_fix.cleanUp()
        self.remove_from_cleanups(secgrp_fix)

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            if fix.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break

    def config_policy_and_attach_to_vn(self, rules):
	randomname = get_random_name()
	policy_name = "sec_grp_policy_" + randomname
        policy_fix = self.config_policy(policy_name, rules)
        assert policy_fix.verify_on_setup()
        policy_vn1_attach_fix = self.attach_policy_to_vn(
            policy_fix, self.vn1_fix)
        policy_vn2_attach_fix = self.attach_policy_to_vn(
            policy_fix, self.vn2_fix)

    def create_sec_group_allow_all(self):
        ''' create security group which allows all traffic '''

        self.sg_allow_all = 'sec_group_allow_all' + '_' + get_random_name()
        rule = [{'direction': '<>',
                'protocol': 'any',
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'any',
                 'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.sg_allow_all_fix = self.config_sec_group(name=self.sg_allow_all, entries=rule)

        return self.sg_allow_all_fix.secgrp_id

    def create_topo_setup(self,
                          topology_class_name,
                          topo_method):

        topo = topology_class_name()
        try:
            eval("topo." + topo_method + "(" +
                                    "project='" + self.project.project_name +
                                    "',username='" + self.project.username +
                                    "',password='" + self.project.password +
                                    "',compute_node_list=" + str(self.inputs.compute_ips) +
                                    ",config_option='" + self.option +
                                    "')")
        except (NameError, AttributeError):
            eval("topo." + topo_method + "(" +
                                    "compute_node_list='" + self.inputs.compute_ips +
                                    "',config_option='" + self.option +
                                    "')")

        setup_obj = self.useFixture(
            sdnTopoSetupFixture(self.connections, topo))
        out = setup_obj.topo_setup(VmToNodeMapping=topo.vm_node_map,
                                    config_option=self.option)
        self.logger.info("Setup completed with result %s" % (out['result']))
        self.assertEqual(out['result'], True, out['msg'])
        if out['result']:
            topo_obj, config_topo = out['data']

        return (topo_obj, config_topo)

    def set_tcp_port_use_optimizations(self, vm_list):
        '''
        Sets various tcp level optimization for port reuse and recycling to
        avoid bind failure on the instances
        As of now it only sets tcp_tw_reuse, more can be added here if required.
        '''
        cmd = 'echo 1 > /proc/sys/net/ipv4/tcp_tw_reuse'
        for vm in vm_list:
            vm.run_cmd_on_vm(cmds=[cmd], as_sudo=True)

#end class BaseSGTest

