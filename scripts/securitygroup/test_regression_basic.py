import unittest
from tcutils.wrappers import preposttest_wrapper
from vnc_api.vnc_api import NoIdError
from common.securitygroup.verify import VerifySecGroup
from common.securitygroup.base import BaseSGTest
from common.policy.config import ConfigPolicy
from vn_test import VNFixture
from vm_test import VMFixture
import os
import sys
import test
from tcutils.util import get_random_name, get_random_cidrs

class SecurityGroupBasicRegressionTests1(BaseSGTest, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupBasicRegressionTests1, cls).setUpClass()
        cls.option = 'openstack'

    def runTest(self):
        pass

    @test.attr(type=['sanity','ci_sanity','vcenter', 'suite1', 'cb_sanity'])
    @preposttest_wrapper
    def test_sec_group_basic(self):
        """
	Description: Test basic SG features
            1. Security group create and delete
            2. Create security group with custom rules and then update it for tcp
            3. Launch VM with custom created security group and verify
            4. Remove secuity group association with VM
            5. Add back custom security group to VM and verify
            6. Try to delete security group with association to VM. It should fail.
            7. Test with ping, which should fail
            8. Test with TCP which should pass
            9. Update the rules to allow icmp, ping should pass now.
        """
        secgrp_name = get_random_name('test_sec_group')
        (prefix, prefix_len) = get_random_cidrs(self.inputs.get_af())[0].split('/')
        prefix_len = int(prefix_len)
        rule = [{'direction': '>',
                'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': prefix,
                    'ip_prefix_len': prefix_len}}],
                 'dst_ports': [{'start_port': 8000, 'end_port': 8000}],
                 'src_ports': [{'start_port': 9000, 'end_port': 9000}],
                 'src_addresses': [{'security_group': 'local'}],
                 }]
        #Create the SG
        sg_fixture = self.config_sec_group(name=secgrp_name, entries=rule)
        #Delete the SG
        self.delete_sec_group(sg_fixture)
        #Create SG again and update the rules
        sg_fixture = self.config_sec_group(name=secgrp_name, entries=rule)
        secgrp_id = sg_fixture.secgrp_id
        vn_net = get_random_cidrs(self.inputs.get_af())
        (prefix, prefix_len) = vn_net[0].split('/')
        rule = [{'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': prefix,
                    'ip_prefix_len': prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': prefix,
                    'ip_prefix_len': prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        #Update the rules
        sg_fixture.replace_rules(rule)
        #Create VN and VMs
        vn_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            inputs=self.inputs, subnets=vn_net))
        assert vn_fixture.verify_on_setup()
        img_name = self.inputs.get_ci_image() or 'ubuntu-traffic'
        vm1_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=vn_fixture.obj, image_name=img_name, flavor='contrail_flavor_small',
            sg_ids=[secgrp_id]))
        vm2_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=vn_fixture.obj, image_name=img_name, flavor='contrail_flavor_small',
            sg_ids=[secgrp_id]))
        assert vm1_fixture.verify_on_setup()
        assert vm1_fixture.wait_till_vm_is_up()
        result, msg = vm1_fixture.verify_security_group(secgrp_name)
        assert result, msg

        #Remove secuity group association with VM and verify
        self.logger.info("Remove security group %s from VM %s",
                         secgrp_name, vm1_fixture.vm_name)
        vm1_fixture.remove_security_group(secgrp=secgrp_id)
        result, msg = vm1_fixture.verify_security_group(secgrp_name)
        if result:
            assert False, "Security group %s is not removed from VM %s" % (secgrp_name,
                                                                           vm1_fixture.vm_name)
        #Add back security group to VM and verify
        vm1_fixture.add_security_group(secgrp=secgrp_id)
        result, msg = vm1_fixture.verify_security_group(secgrp_name)
        assert result, msg

        #Try to delete security group with back ref
        self.logger.info(
            "Try deleting the security group %s with back ref.", secgrp_name)
        try:
            if sg_fixture.option == 'openstack':
                sg_fixture.quantum_h.delete_security_group(sg_fixture.secgrp_id)
            else:
                sg_fixture.cleanUp()
        except Exception, msg:
            self.logger.info(msg)
            self.logger.info(
                "Not able to delete the security group with back ref as expected")
        else:
            try:
                secgroup = self.vnc_lib.security_group_read(
                    fq_name=sg_fixture.secgrp_fq_name)
                self.logger.info(
                    "Not able to delete the security group with back ref as expected")
            except NoIdError:
                errmsg = "Security group deleted, when it is attached to a VM."
                self.logger.error(errmsg)
                assert False, errmsg

        assert vm2_fixture.verify_on_setup()
        assert vm2_fixture.wait_till_vm_is_up()

        #Ping test, should fail
        assert vm1_fixture.ping_with_certainty(ip=vm2_fixture.vm_ip,
            expectation=False)
        self.logger.info("Ping FAILED as expected")

        #TCP test, should pass
        nc_options = '' if self.inputs.get_af() == 'v4' else '-6'
        assert vm1_fixture.nc_file_transfer(vm2_fixture, nc_options=nc_options)

        proto = '1' if self.inputs.get_af() == 'v4' else '58'
        rule = [{'protocol': proto,
                 'dst_addresses': [{'subnet': {'ip_prefix': prefix,
                    'ip_prefix_len': prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'protocol': proto,
                 'src_addresses': [{'subnet': {'ip_prefix': prefix,
                    'ip_prefix_len': prefix_len}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        #Update the rules
        sg_fixture.replace_rules(rule)

        #Ping should pass now
        assert vm1_fixture.ping_with_certainty(ip=vm2_fixture.vm_ip,
            expectation=True)
