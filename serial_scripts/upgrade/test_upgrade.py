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
from verify import VerifyFeatureTestCases
class UpgradeTestSanityWithResource(base.UpgradeBaseTest,VerifyFeatureTestCases):
    
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
        return self.verify_config_after_feature_test()
        
        
    @test.attr(type=['upgrade'])
    @preposttest_wrapper
    def test_fiptraffic_before_upgrade(self):
        ''' Test to create policy, security group  and floating ip rules on common resources and checking if they work fine
        '''
        return self.verify_config_before_feature_test()
        
        
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
                'contrail-install-packages(_|-)(.*?-)(\d{1,})(.*)(_all.deb|.el6.noarch.rpm)', rpms)
            build_id = m.group(3)
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
