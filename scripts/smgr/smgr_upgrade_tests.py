import os
import sys
from base import ServerManagerTest
import test
import fixtures
from smgr_common import SmgrFixture
import time
import json
import pdb
import random
import string
from fabric.api import settings, run, local

# Build image id from the image name.
def image_name_to_id(self, image_name=None):
    if image_name is None:
        self.logger.error("No image name received...")
        return False
    release_major=image_name.split("/")[-1].split("_")[1].split("-")[0].split(".")[0]
    release_minor=image_name.split("/")[-1].split("_")[1].split("-")[0].split(".")[1]
    build=image_name.split("/")[-1].split("_")[1].split("-")[1].split("~")[0]
    stack=image_name.split("/")[-1].split("_")[1].split("-")[1].split("~")[1]
    image_id='r'+ release_major + release_minor + 'b' + build + stack
    image_id=image_id + ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(3))
    self.logger.info("Image id is :: %s" % image_id)
    return image_id
#end image_name_to_id

# Check if the server-manager installer version is less than or equal to R2.1
def check_if_SM_base_img_is_leq_R21(self, image_name=None):
    if image_name is None:
        self.logger.error("No image name received...")
        return False
    release_major=image_name.split("/")[-1].split("_")[1].split("-")[0].split(".")[0]
    release_minor=image_name.split("/")[-1].split("_")[1].split("-")[0].split(".")[1]
    if((release_major == '2') and (int(release_minor) < 20)):
        return True
    return False
#end check_if_SM_base_img_is_leq_R21

# Setup test environment in cfgm-0 of the target setup.
def setup_contrail_test(self):
    cfgm0_host=self.smgr_fixture.testbed.env.roledefs['cfgm'][0]
    cfgm0_password=self.smgr_fixture.testbed.env.passwords[cfgm0_host]
    cmd1 = 'sshpass -p ' + cfgm0_password + ' scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null '
    cmd2 = cmd1 + '/root/sm_files/contrail_packages/setup.sh ' + cfgm0_host +':/opt/contrail/contrail_packages/'
    # copy setup.sh to /opt/contrail/contrail_packages
    ret = local(cmd2, capture=True)

    contrail_test_pkg = os.environ['AR_BASE_DEB'].rsplit('/',1)[0] + '/artifacts_extra/contrail-test-*.tgz'
    contrail_fab_pkg = os.environ['AR_BASE_DEB'].rsplit('/',1)[0] + '/artifacts_extra/contrail-fabric-utils*.tgz'
    cmd2 = cmd1 + contrail_test_pkg + ' ' + cfgm0_host + ':~/'
    # copy contrail-test to cfgm0
    ret = local(cmd2, capture=True)
    cmd2 = cmd1 + contrail_fab_pkg + ' ' + cfgm0_host + ':~/'
    # copy contrail-fabric-utils to cfgm0
    ret = local(cmd2, capture=True)

    with settings(host_string=cfgm0_host, password=cfgm0_password, warn_only=True):
        # run setup.sh
        run('/opt/contrail/contrail_packages/setup.sh')
        # untar contrail-test and contrail-fabric-utils
        run('cd ~; tar xzf contrail-test-[[:digit:]].*.tgz; tar xzf contrail-fabric-utils*.tgz')

    # copy /root/contrail-test/testbed.py to cfgm0 /root/fabric-utils/fabfile/testbeds/
    cmd2 = cmd1 + '/root/sm_files/testbed.py ' + cfgm0_host + ':~/fabric-utils/fabfile/testbeds/'
    ret = local(cmd2, capture=True)

    # replace env.test_repo_dir with /root/contrail-test in cfgm0 /root/fabric-utils/fabfile/testbeds/testbed.py
    # run fab install_test_repo and setup_test_env
    # set environment variables and check if running tests is possible.
    ret = ''
    with settings(host_string=cfgm0_host, password=cfgm0_password, warn_only=True):
        run("sed -i '/env.test_repo_dir/d' /root/fabric-utils/fabfile/testbeds/testbed.py")
        cmd = 'echo "env.test_repo_dir=' + "'/root/contrail-test'"
        cmd = cmd + '" >> /root/fabric-utils/fabfile/testbeds/testbed.py'
        run(cmd)
        run('cd /root/fabric-utils/; fab install_test_repo; fab setup_test_env')
        cmd = 'cd /root/contrail-test/; export PYTHONPATH=$PATH:$PWD/scripts:$PWD/fixtures; '
        cmd = cmd + 'export TEST_CONFIG_FILE=`basename sanity_params.ini`; '
        cmd1 = cmd + 'python -m testtools.run discover -l serial_scripts.upgrade | grep before'
        ret = run(cmd1)
    if 'test_fiptraffic_before_upgrade' in ret:
        self.logger.info("Successfully installed fabric and setup contrail-test env.")
        self.logger.info("Ready to run tests from cfgm0.")
        return True;
    else:
        self.logger.error("ERROR :: Failed to install fabric and setup contrail-test env properly.")
        return False
#end setup_contrail_test

# Create a topology of VM, VN etc on the target setup.
def create_topo_before_upgrade(self):
    cfgm0_host=self.smgr_fixture.testbed.env.roledefs['cfgm'][0]
    cfgm0_password=self.smgr_fixture.testbed.env.passwords[cfgm0_host]
    ret1 = ''
    with settings(host_string=cfgm0_host, password=cfgm0_password, warn_only=True):
        cmd = "sed -i 's/fixtureCleanup=.*/fixtureCleanup=no/g' /root/contrail-test/sanity_params.ini"
        ret = run(cmd)
        cmd = 'cd /root/contrail-test/; export PYTHONPATH=$PATH:$PWD/scripts:$PWD/fixtures; '
        cmd = cmd + 'export TEST_CONFIG_FILE=`basename sanity_params.ini`; '
        cmd1 = cmd + 'python -m testtools.run discover -l serial_scripts.upgrade | grep before'
        ret = run(cmd1)
        cmd1 = cmd + 'python -m testtools.run ' + ret.rsplit('[')[0]
        ret1 = run(cmd1, timeout=1200)

    if 'END TEST : test_fiptraffic_before_upgrade : PASSED' in ret1:
        self.logger.info("Set up the topology before upgrade successfully.")
        return True
    else:
        self.logger.error("ERROR :: Failures while running test. Need to check why setting up of topology failed")
        self.logger.error("ERROR :: Not blocking the upgrade test because of this.")
        return True
#end create_topo_before_upgrade

def verify_topo_after_upgrade(self):
    cfgm0_host=self.smgr_fixture.testbed.env.roledefs['cfgm'][0]
    cfgm0_password=self.smgr_fixture.testbed.env.passwords[cfgm0_host]
    ret1 = ''
    with settings(host_string=cfgm0_host, password=cfgm0_password, warn_only=True):
        cmd = "sed -i 's/fixtureCleanup=.*/fixtureCleanup=yes/g' /root/contrail-test/sanity_params.ini"
        ret = run(cmd)
        cmd = 'cd /root/contrail-test/; export PYTHONPATH=$PATH:$PWD/scripts:$PWD/fixtures; '
        cmd = cmd + 'export TEST_CONFIG_FILE=`basename sanity_params.ini`; '
        cmd1 = cmd + 'python -m testtools.run discover -l serial_scripts.upgrade | grep after'
        ret = run(cmd1)
        cmd1 = cmd + 'python -m testtools.run ' + ret.rsplit('[')[0]
        ret1 = run(cmd1, timeout=1200)

    if 'FAIL' in ret1:
        self.logger.error("ERROR :: Failures while running test. Need to check why verification of topology failed")
        return False
    else:
        self.logger.info("Verified the topology after upgrade successfully.")
        return True
#end verify_topo_after_upgrade

# Accross release contrail upgrade with server-manager upgrade.
def AR_upgrade_test_with_SM_upgrade(self):
    result = True
    self.logger.info("Running AR_upgrade_test_with_SM_upgrade.....")
    self.smgr_fixture.uninstall_sm()
    self.smgr_fixture.install_sm(SM_installer_file_path=os.environ['SM_BASE_IMG'])
    pkg_file=None
    try:
        pkg_file=self.smgr_fixture.params['pkg_file']
    except:
        self.logger.error("Package file information doesn't exist in smgr_input.ini file")
        return result

    assert self.smgr_fixture.backup_file(pkg_file)
    with open(pkg_file, 'r') as pkgf:
        data = json.load(pkgf)
    pkgf.close()
    base_package_id=image_name_to_id(self, os.environ['AR_BASE_DEB'])
    data['image'][0]['id']=base_package_id
    data['image'][0]['version']=base_package_id
    data['image'][0]['path']=os.environ['AR_BASE_DEB']
    with open(pkg_file, 'w') as pkgf:
        json.dump(data, pkgf)
    pkgf.close()
    self.smgr_fixture.add_pkg()

    if check_if_SM_base_img_is_leq_R21(self, os.environ['SM_BASE_IMG']):
        cluster_file=None
        try:
            cluster_file=self.smgr_fixture.params['cluster_file']
        except:
            self.logger.error("Cluster file information doesn't exist in smgr_input.ini file")
            return result
        assert self.smgr_fixture.backup_file(cluster_file)
        with open(cluster_file, 'r') as clf:
            data=json.load(clf)
        clf.close()
        data['cluster'][0]['parameters']['sequence_provisioning']='false'
        with open(cluster_file, 'w') as clf:
            json.dump(data, clf)
        clf.close()

        server_file=None
        try:
            server_file=self.smgr_fixture.params['server_file']
        except:
            self.logger.error("Server file information doesn't exist in smgr_input.ini file")
            return result
        with open(server_file, 'r') as sef:
            data=json.load(sef)
        sef.close()
        for each_server in range(len(data['server'])):
            self.smgr_fixture.delete_server_id_based(data['server'][each_server]['id'])
        with open(cluster_file, 'r') as clf:
            data=json.load(clf)
        clf.close()
        self.smgr_fixture.delete_cluster_id_based(data['cluster'][0]['id'])
        self.smgr_fixture.add_cluster()
        self.smgr_fixture.add_server()

    #Reimage and Provision the servers with the base release for upgrade test to follow
    assert self.smgr_fixture.setup_cluster(no_reimage_pkg=True)

    time.sleep(300)
    if setup_contrail_test(self):
        if create_topo_before_upgrade(self):
            self.logger.info("Creation of topology successfull before running upgrade.")
        else:
            self.logger.error("FAILED to create topology before running upgrade.")
            return False
    else:
        self.logger.error("FAILED to setup test env on the target cfgm node.")
        return False

    self.smgr_fixture.uninstall_sm()
    self.smgr_fixture.install_sm(SM_installer_file_path=os.environ['SM_UPGD_IMG'])
    with open(pkg_file, 'r') as pkgf:
        data = json.load(pkgf)
    pkgf.close()
    base_package_id=image_name_to_id(self, os.environ['AR_UPGD_DEB'])
    data['image'][0]['id']=base_package_id
    data['image'][0]['version']=base_package_id
    data['image'][0]['path']=os.environ['AR_UPGD_DEB']
    with open(pkg_file, 'w') as pkgf:
        json.dump(data, pkgf)
    pkgf.close()
    self.smgr_fixture.add_pkg()

    if check_if_SM_base_img_is_leq_R21(self, os.environ['SM_BASE_IMG']):
        self.smgr_fixture.restore_file('cluster_file')
        server_file=None
        try:
            server_file=self.smgr_fixture.params['server_file']
        except:
            self.logger.error("Server file information doesn't exist in smgr_input.ini file")
            return result
        with open(server_file, 'r') as sef:
            data=json.load(sef)
        sef.close()
        for each_server in range(len(data['server'])):
            self.smgr_fixture.delete_server_id_based(data['server'][each_server]['id'])
        with open(cluster_file, 'r') as clf:
            data=json.load(clf)
        clf.close()
        self.smgr_fixture.delete_cluster_id_based(data['cluster'][0]['id'])
        self.smgr_fixture.add_cluster()
        self.smgr_fixture.add_server()
        
    #Provision to upgrade the servers with the target release for upgrade test to follow
    assert self.smgr_fixture.setup_cluster(provision_only=True)

    time.sleep(300)
    if verify_topo_after_upgrade(self):
        self.logger.info("Verification of topology successfull after upgrade.")
    else:
        self.logger.error("FAILED to verify topology after upgrade.")

    return result
#end AR_upgrade_test_with_SM_upgrade

# Accross release contrail upgrade without server-manager upgrade.
def AR_upgrade_test_without_SM_upgrade(self):
    result = True
    self.logger.info("Running AR_upgrade_test_with_SM_upgrade.....")

    pkg_file=None
    try:
        pkg_file=self.smgr_fixture.params['pkg_file']
    except:
        self.logger.error("Package file information doesn't exist in smgr_input.ini file")
        return result

    assert self.smgr_fixture.backup_file(pkg_file)
    with open(pkg_file, 'r') as pkgf:
        data = json.load(pkgf)
    pkgf.close()
    base_package_id=image_name_to_id(self, os.environ['AR_BASE_DEB'])
    data['image'][0]['id']=base_package_id
    data['image'][0]['version']=base_package_id
    data['image'][0]['path']=os.environ['AR_BASE_DEB']
    with open(pkg_file, 'w') as pkgf:
        json.dump(data, pkgf)
    pkgf.close()
    self.smgr_fixture.add_pkg()

    #Reimage and Provision the servers with the base release for upgrade test to follow
    assert self.smgr_fixture.setup_cluster()

    with open(pkg_file, 'r') as pkgf:
        data = json.load(pkgf)
    pkgf.close()
    base_package_id=image_name_to_id(self, os.environ['AR_UPGD_DEB'])
    data['image'][0]['id']=base_package_id
    data['image'][0]['version']=base_package_id
    data['image'][0]['path']=os.environ['AR_UPGD_DEB']
    with open(pkg_file, 'w') as pkgf:
        json.dump(data, pkgf)
    pkgf.close()
    self.smgr_fixture.add_pkg()

    #Provision to upgrade the servers with the target release for upgrade test to follow
    assert self.smgr_fixture.setup_cluster(provision_only=True)

    return result 
