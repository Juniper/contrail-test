import unittest
from tcutils.wrappers import preposttest_wrapper
from vnc_api.vnc_api import NoIdError
from verify import VerifySecGroup
from policy_test import PolicyFixture
from vn_test import MultipleVNFixture
from vm_test import MultipleVMFixture
from base import BaseSGTest
from common.policy.config import ConfigPolicy
from security_group import SecurityGroupFixture,get_secgrp_id_from_name
from vn_test import VNFixture
from vm_test import VMFixture
from tcutils.topo.topo_helper import *
import os
import sys
sys.path.append(os.path.realpath('scripts/flow_tests'))
from tcutils.topo.sdn_topo_setup import *
import test
import sdn_sg_test_topo
from tcutils.tcpdump_utils import *
from time import sleep
from tcutils.util import get_random_name
from base_traffic import *
from tcutils.util import skip_because

class SecurityGroupBasicRegressionTests1(BaseSGTest, VerifySecGroup, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(SecurityGroupBasicRegressionTests1, cls).setUpClass()
        cls.option = 'openstack'

    def runTest(self):
        pass

    @test.attr(type=['sanity','ci_sanity', 'suite1'])
    @preposttest_wrapper
    def test_sec_group_add_delete(self):
        """
	Description: Verify security group add delete
	Steps:
            1. Create custom security group with rule in it
            2. Delete custom security group
        Pass criteria: Step 1 and 2 should pass
        """
        rule = [{'direction': '>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 8000, 'end_port': 8000}],
                 'src_ports': [{'start_port': 9000, 'end_port': 9000}],
                 'src_addresses': [{'security_group': 'local'}],
                 }]
        secgrp_fix = self.config_sec_group(name='test_sec_group', entries=rule)
        self.delete_sec_group(secgrp_fix)
        return True

    @test.attr(type=['sanity','ci_sanity','vcenter', 'suite1'])
    @preposttest_wrapper
    def test_vm_with_sec_group(self):
        """
	Description: Verify attach dettach security group in VM
	Steps:
            1. Create VN with subnet
            2. Create security group with custom rules
            3. Launch VM in custom created security group and verify
            4. Remove secuity group association with VM
            5. Add back custom security group to VM and verify
            6. Try to delete security group with association to VM. It should fail.
        Pass criteria: Step 2,3,4,5 and 6 should pass
        """
        vn_name = get_random_name("test_sec_vn")
        vn_net = ['11.1.1.0/24']
        vn = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=vn_name, inputs=self.inputs, subnets=vn_net))
        assert vn.verify_on_setup()

        secgrp_name = get_random_name('test_sec_group')
        rule = [{'direction': '>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '10.1.1.0', 'ip_prefix_len': 24}}],
                 'dst_ports': [{'start_port': 8000, 'end_port': 8000}],
                 'src_ports': [{'start_port': 9000, 'end_port': 9000}],
                 'src_addresses': [{'security_group': 'local'}],
                 }]
        secgrp = self.config_sec_group(name=secgrp_name, entries=rule)
	secgrp_id = secgrp.secgrp_id
        vm_name = get_random_name("test_sec_vm")
	img_name = os.environ['ci_image'] if os.environ.has_key('ci_image') else 'ubuntu-traffic'
        vm = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=vn.obj, vm_name=vm_name, image_name=img_name, flavor='contrail_flavor_small',
            sg_ids=[secgrp_id]))
        assert vm.verify_on_setup()
        assert vm.wait_till_vm_is_up()
        result, msg = vm.verify_security_group(secgrp_name)
        assert result, msg

        self.logger.info("Remove security group %s from VM %s",
                         secgrp_name, vm_name)
        vm.remove_security_group(secgrp=secgrp_id)
        result, msg = vm.verify_security_group(secgrp_name)
        if result:
            assert False, "Security group %s is not removed from VM %s" % (secgrp_name,
                                                                           vm_name)

        import time
        time.sleep(4)
        vm.add_security_group(secgrp=secgrp_name)
        result, msg = vm.verify_security_group(secgrp_name)
        assert result, msg

        self.logger.info(
            "Try deleting the security group %s with back ref.", secgrp_name)
        try:
            if secgrp.option == 'openstack':
                secgrp.quantum_h.delete_security_group(secgrp.secgrp_id)
            else:
                secgrp.secgrp_fix.cleanUp()
        except Exception, msg:
            self.logger.info(msg)
            self.logger.info(
                "Not able to delete the security group with back ref as expected")
        else:
            try:
                secgroup = self.vnc_lib.security_group_read(
                    fq_name=secgrp.secgrp_fq_name)
                self.logger.info(
                    "Not able to delete the security group with back ref as expected")
            except NoIdError:
                errmsg = "Security group deleted, when it is attached to a VM."
                self.logger.error(errmsg)
                assert False, errmsg
        return True

