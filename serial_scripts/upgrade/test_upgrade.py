# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
# Test to upgrade to new contrail version  from existing version usage :
# fab run_sanity:upgrade,rpmfile

import re
import time
import os
from contrail_fixtures import *
import fixtures
import testtools
import traceback
from vn_test import VNFixture
from vm_test import VMFixture
from quantum_test import QuantumHelper
from nova_test import NovaHelper
from floating_ip import FloatingIPFixture
from policy_test import PolicyFixture
from tcutils.commands import *
from fabric.context_managers import settings
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import *
from fabric.api import run
from fabric.state import connections
from scripts.securitygroup.config import ConfigSecGroup
import base
import test

class UpgradeTestSanityWithResource(base.UpgradeBaseTest, ConfigSecGroup):

    @classmethod
    def setUpClass(cls):
        super(UpgradeTestSanityWithResource, cls).setUpClass()
        cls.res.setUp(cls.inputs , cls.connections, cls.logger)
  
    @classmethod
    def tearDownClass(cls):
        cls.res.cleanUp()
        super(UpgradeTestSanityWithResource, cls).tearDownClass()

    def runTest(self):
        pass
    #end runTest

    @test.attr(type=['upgrade'])
    @preposttest_wrapper
    def test_traffic_after_upgrade(self):
        '''Test to test traffic after upgrade using previouly defined  policy and floating ip and then adding new policy,fip to new resources also  validate service chaining in network  datapath and security group
        '''
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

        self.logger.info('PINGING FROM vn22_vm1_mine TO fip_vn_vm1_mine \n')
        if not self.vm22_fixture.ping_with_certainty(self.fip_fixture1.fip[self.fip_new_id1]):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result
        fips = self.vm22_fixture.vnc_lib_h.floating_ip_read(
            id=self.fip_new_id).get_floating_ip_address()

        self.logger.info('PINGING FROM vn11_vm1_mine to vn22_vm1_mine \n')
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

        self.logger.info(
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
    # end test_traffic_after_upgrade
 
    @test.attr(type=['upgrade'])
    @preposttest_wrapper
    def test_fiptraffic_before_upgrade(self):
        ''' Test to create policy, security group  and floating ip rules on common resources and checking if they work fine
        '''
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
    # end test_fiptraffic_before_upgrade

    def check_secgrp_traffic(self):
        result = True
        vn11_vm3_fixture = self.res.vn11_vm3_fixture
        vn11_vm4_fixture = self.res.vn11_vm4_fixture

        self.sg1_name = 'sec_grp1'
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

        # vn11_vm3 and vn11_vm4 are in sec_grp1  not allowing icmp traffic so
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

    def check_policy_traffic(self):

        result = True
        vn11_vm2_fixture = self.res.vn11_vm2_fixture
        vn22_vm2_fixture = self.res.vn22_vm2_fixture
        self.logger.info("Pinging from vn11_vm2 to vn22_vm2 by policy rule ")

        if not vn11_vm2_fixture.ping_with_certainty(vn22_vm2_fixture.vm_ip, expectation=True):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result

        self.logger.info("Pinging from vn22_vm2 to vn11_vm2 by policy rule ")

        if not vn22_vm2_fixture.ping_with_certainty(vn11_vm2_fixture.vm_ip, expectation=True):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result
        return result

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
        self.logger.info('PINGING FROM VN11_VM1 TO VN22_VM1 \n')
        if not vn11_vm1_fixture.ping_with_certainty(fip_fixture.fip[fip_id1]):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result

        self.logger.info('PINGING FROM VN11_VM1 TO FVN_VM1 \n')
        if not vn11_vm1_fixture.ping_to_ip(fvn_vm1_fixture.vm_ip):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result

        self.logger.info('PINGING FROM VN22_VM1 TO FVN_VM1 \n')
        if not vn22_vm1_fixture.ping_to_ip(fvn_vm1_fixture.vm_ip):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result

        fip = vn11_vm1_fixture.vnc_lib_h.floating_ip_read(
            id=fip_id).get_floating_ip_address()

        self.logger.info('PINGING FROM  FVN_VM1 to VN11_VM1 \n')
        if not fvn_vm1_fixture.ping_to_ip(fip):
            result = result and False
        if not result:
            self.logger.error('Test to ping between VMs FAILED \n')
            assert result
        return result

    @test.attr(type=['upgrade']) 
    @preposttest_wrapper
    def test_to_upgrade(self):
        '''Test to upgrade contrail software from existing build to new build and then rebooting resource vm's
        '''
        result = True

        if(set(self.inputs.compute_ips) & set(self.inputs.cfgm_ips)):
            raise self.skipTest(
                "Skipping Test. Cfgm and Compute nodes should be different to run  this test case")
        self.logger.info("STARTING UPGRADE")
        username = self.inputs.host_data[self.inputs.cfgm_ip]['username']
        password = self.inputs.host_data[self.inputs.cfgm_ip]['password']
        with settings(
            host_string='%s@%s' % (
                username, self.inputs.cfgm_ips[0]),
                password = password, warn_only=True, abort_on_prompts=False, debug=True):
            status = run("cd /tmp/temp/;ls")
            self.logger.debug("%s" % status)

            m = re.search(
                r'contrail-install-packages(-|_)(.*)(_all.deb|.noarch.rpm)', status)
            assert m, 'Failed in importing rpm'
            rpms = m.group(0)
            rpm_type = m.group(3)

            if re.search(r'noarch.rpm', rpm_type):
                status = run("yum -y localinstall /tmp/temp/" + rpms)
                self.logger.debug(
                    "LOG for yum -y localinstall command: \n %s" % status)
                assert not(
                    status.return_code), 'Failed in running: yum -y localinstall /tmp/temp/' + rpms

            else:
                status = run("dpkg -i /tmp/temp/" + rpms)
                self.logger.debug(
                    "LOG for dpkg -i debfile  command: \n %s" % status)
                assert not(
                    status.return_code), 'Failed in running: dpkg -i /tmp/temp/' + rpms

            status = run("cd /opt/contrail/contrail_packages;./setup.sh")
            self.logger.debug(
                "LOG for /opt/contrail/contrail_packages;./setup.sh command: \n %s" % status)
            assert not(
                status.return_code), 'Failed in running : cd /opt/contrail/contrail_packages;./setup.sh'

            status = run("cd /opt/contrail/utils" + ";" +
                         "fab upgrade_contrail:%s,/tmp/temp/%s" % (self.res.base_rel, rpms))
            self.logger.debug(
                "LOG for fab upgrade_contrail command: \n %s" % status)
            assert not(
                status.return_code), 'Failed in running : cd /opt/contrail/utils;fab upgrade_contrail:/tmp/temp/' + rpms

            m = re.search(
                'contrail-install-packages(.*)([0-9]{2,4})(.*)(_all.deb|.el6.noarch.rpm)', rpms)
            build_id = m.group(2)
            status = run(
                "contrail-version | grep contrail- | grep -v contrail-openstack-dashboard | awk '{print $1, $2, $3}'")
            self.logger.debug("contrail-version :\n %s" % status)
            assert not(status.return_code)
            lists = status.split('\r\n')
            for module in lists:
                success = re.search(build_id, module)
                result = result and success
                if not (result):
                    self.logger.error(' Failure while upgrading ' +
                                      module + 'should have upgraded to ' + build_id)
                    assert result, 'Failed to Upgrade ' + module

            if result:
                self.logger.info("Successfully upgraded all modules")

            time.sleep(90)
            connections.clear()
            self.logger.info('Will REBOOT the SHUTOFF VMs')
            for vm in self.nova_h.get_vm_list():
                if vm.status != 'ACTIVE':
                    self.logger.info('Will Power-On %s' % vm.name)
                    vm.start()
                    self.nova_h.wait_till_vm_is_active(vm)

            run("rm -rf /tmp/temp")
            run("rm -rf /opt/contrail/utils/fabfile/testbeds/testbed.py")

        return result
 
    # end test_to_upgrade

    # adding function to create more resources these will be created after
    # upgrade
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
