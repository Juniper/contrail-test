import os

import fixtures
from testresources import TestResource

from policy_test import PolicyFixture
from vn_test import MultipleVNFixture
from vm_test import MultipleVMFixture
from common.connections import ContrailConnections
from securitygroup.config import ConfigSecGroup
from common.contrail_test_init import ContrailTestInit


class SecurityGroupSetup(fixtures.Fixture, ConfigSecGroup):

    """Common resources required for the security group regression test suite.
    """

    def __init__(self, common_resource):
        super(SecurityGroupSetup, self).__init__()
        self.common_resource = common_resource

    def setUp(self):
        super(SecurityGroupSetup, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = ContrailTestInit(self.ini_file)
        self.connections = ContrailConnections(self.inputs)
        self.quantum_h = self.connections.quantum_h
        self.nova_h = self.connections.nova_h
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger

        self.logger.info("Configuring setup for security group tests.")
        self.setup()
        self.logger.info("Verifying setup of security group tests.")
        self.verify()
        self.logger.info(
            "Finished configuring setup for security group tests.")
        return self

    def setup(self):
        """Config common resources."""
        vn_s = {'vn1': '20.1.1.0/24', 'vn2': ['10.1.1.0/24']}
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
        self.vm1_fix.remove_security_group(secgrp='default')
        self.vm2_fix.remove_security_group(secgrp='default')
        self.vm4_fix.remove_security_group(secgrp='default')
        self.vm5_fix.remove_security_group(secgrp='default')

    def config_sec_groups(self):
        self.sg1_name = 'test_tcp_sec_group'
        rule = [{'direction': '<>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]

        self.sg1_fix = self.config_sec_group(name=self.sg1_name, entries=rule)

        self.sg2_name = 'test_udp_sec_group'
        rule = [{'direction': '<>',
                'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}},
                                   {'subnet': {'ip_prefix': '20.1.1.0', 'ip_prefix_len': 24}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        self.sg2_fix = self.config_sec_group(name=self.sg2_name, entries=rule)

    def verify(self):
        """verfiy common resources."""
        self.logger.debug("Verify the configured VN's.")
        assert self.multi_vn_fixture.verify_on_setup()

        self.logger.debug("Verify the configured VM's.")
        assert self.multi_vm_fixture.verify_on_setup()

        self.logger.info("Installing traffic package in VM.")
        self.vm1_fix.install_pkg("Traffic")
        self.vm2_fix.install_pkg("Traffic")
        self.vm3_fix.install_pkg("Traffic")
        self.vm4_fix.install_pkg("Traffic")
        self.vm5_fix.install_pkg("Traffic")
        self.vm6_fix.install_pkg("Traffic")

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
        result, msg = self.vm5_fix.verify_security_group(self.sg2_name)
        assert result, msg

    def tearDown(self):
        self.logger.info("Tearing down resources of security group tests")
        super(SecurityGroupSetup, self).cleanUp()

    def dirtied(self):
        self.common_resource.dirtied(self)


class _SecurityGroupSetupResource(TestResource):

    def make(self, dependencyresource):
        base_setup = SecurityGroupSetup(self)
        base_setup.setUp()
        return base_setup

    def clean(self, base_setup):
        base_setup.logger.info(
            "Cleaning up security group test resources here")
        base_setup.tearDown()

SecurityGroupSetupResource = _SecurityGroupSetupResource()
