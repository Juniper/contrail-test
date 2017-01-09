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
    assert self.smgr_fixture.setup_cluster()

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

    return result


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
