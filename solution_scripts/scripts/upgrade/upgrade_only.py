import os
import unittest
import fixtures
import testtools
import re
from common.connections import ContrailConnections
from common.contrail_test_init import ContrailTestInit
from tcutils.wrappers import preposttest_wrapper
from fabric.context_managers import settings
from fabric.api import run
from fabric.state import connections
import time
from tcutils import get_release


class Upgradeonly(testtools.TestCase):

    def setUp(self):
        super(Upgradeonly, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.agent_inspect = self.connections.agent_inspect
        self.quantum_h = self.connections.quantum_h
        self.nova_h = self.connections.nova_h
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.analytics_obj = self.connections.analytics_obj

    def cleanUp(self):
        self.logger.info("Cleaning up")
        super(Upgradeonly, self).cleanUp()

    @preposttest_wrapper
    def test_upgrade_only(self):
        ''' Test to upgrade contrail software from existing build to new build and then rebooting resource vm's
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
                username, self.inputs.cfgm_ip),
                password, warn_only=True, abort_on_prompts=False, debug=True):
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

            upgrade_cmd = "cd /opt/contrail/utils;fab upgrade_contrail:%s,/tmp/temp/%s" % (base_rel, rpms)
            status = run(upgrade_cmd)
            self.logger.debug(
                "LOG for fab upgrade_contrail command: \n %s" % status)
            assert not(
                status.return_code), 'Failed in running : cd /opt/contrail/utils;fab upgrade_contrail:/tmp/temp/' + rpms

            m = re.search(
                'contrail-install-packages(.*)([0-9]{3,4})(.*)(_all.deb|.el6.noarch.rpm)', rpms)
            build_id = m.group(2)
            status = run(
                "contrail-version | awk '{if (NR!=1 && NR!=2) {print $1, $2, $3}}'")
            self.logger.debug("contrail-version :\n %s" % status)
            assert not(status.return_code)
            lists = status.split('\r\n')
            for module in lists:
                success = re.search(build_id, module)
                if not success:
                    contrail_mod = re.search(
                        'contrail-', module) and not(re.search('contrail-openstack-dashboard', module))

                    if not contrail_mod:
                        success = True
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
    # end test_upgrade_only


if __name__ == '__main__':
    unittest.main()
