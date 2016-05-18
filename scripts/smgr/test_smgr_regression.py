from tcutils.wrappers import preposttest_wrapper
import os
import sys
from base import ServerManagerTest
import test
import fixtures
import unittest
import testtools
from common.contrail_test_init import ContrailTestInit
from smgr_common import SmgrFixture
import smgr_upgrade_tests, smgr_inventory_monitoring_tests
from fabric.api import local
from fabric.api import settings, run
from tcutils.util import retry
import time
import pdb

PROVISION_TIME=2400

class SmgrRegressionTests(ServerManagerTest):

    @classmethod
    def setUpClass(self):
        super(SmgrRegressionTests, self).setUpClass()
    #end setUpClass

    @classmethod
    def tearDownClass(self):
        super(SmgrRegressionTests, self).setUpClass()
    #end tearDownClass

    def runTest(self):
        pass

    @retry(delay=5, tries=30)
    def check_cfgm0_status(self):
        result=False
        cfgm0 = self.smgr_fixture.testbed.env.roledefs['cfgm'][0]
        cfgm0_pswd=self.smgr_fixture.testbed.env.passwords[cfgm0]
        try:
            with settings(host_string=cfgm0, password=cfgm0_pswd, warn_only=True):
                run('ls')
            result=True
        except:
            self.logger.error("Login trial to cfgm failed...")
        return result
    #end check_cfgm0_status

    def test_setup_cluster(self):
        """Verify setup cluster using server Manager"""
        self.logger.info("Verify setup cluster  using server manager ")
        assert self.smgr_fixture.setup_cluster()
        return True

    def test_setup_cluster_with_no_pkg_during_reimage(self):
        """Verify setup cluster using server manager. Reimage with base os only."""
        self.logger.info("Verify setup cluster using server manager. Reimage with base os only. ")
        assert self.smgr_fixture.setup_cluster(no_reimage_pkg=True)
        return True

    def test_restart(self):
        """Verify restart server using server Manager"""
        self.logger.info("Verify cluster_restart using server manager ")
        assert self.smgr_fixture.reimage(no_pkg=True, restart_only=True)
        return True

    def test_node_add_delete(self):
        """Verify node add delete using server Manager"""
        self.logger.info("Verify setup cluster  using server manager ")
        assert self.smgr_fixture.verify_node_add_delete(no_reimage_pkg=True)
        return True

    def test_accross_release_upgrade(self):
        """Verify accross release upgrade using Server Manager"""
        self.logger.info("Verify accross release upgrade using Server Manager.")
        result=False
        SM_base_img=None
        SM_upgd_img=None
        AR_base_img=None
        AR_upgd_img=None
        try:
            SM_base_img=os.environ['SM_BASE_IMG']
            self.logger.info("%s" % SM_base_img)
        except:
            self.logger.error("SM_BASE_IMG is not specified as environment variable.")
            self.logger.error("Exiting test")
            return False
        try:
            SM_upgd_img=os.environ['SM_UPGD_IMG']
            self.logger.info("%s" % SM_upgd_img)
        except:
            self.logger.error("SM_UPGD_IMG is not specified as environment variable.")
            self.logger.error("Exiting test")
            return False

        try:
            AR_base_img=os.environ['AR_BASE_DEB']
            self.logger.info("%s" % AR_base_img)
        except:
            self.logger.error("AR_BASE_DEB is not specified as environment variable.")
            self.logger.error("Exiting test")
            return False
        try:
            AR_upgd_img=os.environ['AR_UPGD_DEB']
            self.logger.info("%s" % AR_upgd_img)
        except:
            self.logger.error("AR_UPGD_DEB is not specified as environment variable.")
            self.logger.error("Exiting test")
            return False

        if((SM_base_img is None) or (SM_base_img == SM_upgd_img)):
            self.logger.info("Running Across release test without SM upgrade")
            result=smgr_upgrade_tests.AR_upgrade_test_without_SM_upgrade(self)
        else:
            self.logger.info("Running Across release test with SM upgrade")
            result=smgr_upgrade_tests.AR_upgrade_test_with_SM_upgrade(self)
        return True

    def test_list_servers_using_tag(self):
        self.logger.info("Verify server listing using tags.")
        nodes = self.smgr_fixture.testbed.env.roledefs['all']
        # Atleast 3 nodes are needed to run this test.
        if len(nodes) < 3:
            raise self.skipTest(
                "Skipping Test. At least 3 nodes required to run the test")

        # Configure datacenter tag on alternate servers.
        count=0
        dc_server_list=[]
        for node in nodes:
            count=count+1
            if (count%2) == 0:
                continue
            else:
                dc_server_list.append(node)
        result = self.smgr_fixture.add_tag_and_verify_server_listing(dc_server_list, tag_ind='datacenter', tag_val='testdatacenter1')
        if result == False:
            return False

        # Configure floor tag on alternate servers.
        count=0
        fl_server_list=[]
        for node in nodes:
            count=count+1
            if ((count+1)%2) == 0:
                continue
            else:
                fl_server_list.append(node)
        result = self.smgr_fixture.add_tag_and_verify_server_listing(fl_server_list, tag_ind='floor', tag_val='testfloor1')
        if result == False:
            return False

        # Configure hall tag on first 50% servers.
        count=0
        hl_server_list=[]
        for node in nodes:
            count=count+1
            if count > (len(nodes)/2):
                continue
            else:
                hl_server_list.append(node)
        result = self.smgr_fixture.add_tag_and_verify_server_listing(hl_server_list, tag_ind='hall', tag_val='testhall1')
        if result == False:
            return False

        # Configure rack tag on last 50% servers.
        count=0
        rk_server_list=[]
        for node in nodes:
            count=count+1
            if count <= (len(nodes)/2):
                continue
            else:
                rk_server_list.append(node)
        result = self.smgr_fixture.add_tag_and_verify_server_listing(rk_server_list, tag_ind='rack', tag_val='testrack1')
        if result == False:
            return False

        # Configure user_tag on all servers.
        us_server_list=[]
        for node in nodes:
            us_server_list.append(node)
        result = self.smgr_fixture.add_tag_and_verify_server_listing(us_server_list, tag_ind='user_tag', tag_val='testusertag1')
        if result == False:
            return False

        # Verify nested tag listing
        nested_set = set(dc_server_list).intersection(set(rk_server_list))
        nest_server_list=list(nested_set)
        nest_server_ids=[]
        for node in nest_server_list:
            nest_server_ids.append(self.smgr_fixture.get_server_with_ip_from_db(ip=node.split('@')[1])['server'][0]['id'])
        with settings(host_string=self.smgr_fixture.svrmgr, password=self.smgr_fixture.svrmgr_password, warn_only=True):
            no_of_servers=run('server-manager show server --tag "%s=%s,%s=%s" | grep id | wc -l'
                % ('datacenter', 'testdatacenter1', 'rack', 'testrack1'))
            server_ids=run('server-manager show server --tag "%s=%s,%s=%s" | grep id'
                % ('datacenter', 'testdatacenter1', 'rack', 'testrack1'))
        if (len(nest_server_ids) != int(no_of_servers)):
            self.logger.error('All the nodes with nested tag "%s=%s,%s=%s" were not listed'
                % ('datacenter', 'testdatacenter1', 'rack', 'testrack1'))
            return False
        fail_flag=0
        for server_id in nest_server_ids:
            if server_id in server_ids:
                self.logger.info('Server %s listed with nested tag "%s=%s,%s=%s"'
                    % (server_id, 'datacenter', 'testdatacenter1', 'rack', 'testrack1'))
            else:
                self.logger.error('Server %s not listed with nested tag "%s=%s,%s=%s"'
                    % (server_id, 'datacenter', 'testdatacenter1', 'rack', 'testrack1'))
                fail_flag=1
        if fail_flag == 1:
            self.logger.error("Test test_list_servers_using_tag FAILED")
            return False
        for node in nodes:
            self.smgr_fixture.delete_tag_from_server(server_ip=node.split('@')[1],
                all_tags=True)
        return True

    #end test_list_servers_using_tag


    def test_restart_servers_using_tag(self):
        self.logger.info("Verify server restart using tags.")
        nodes = self.smgr_fixture.testbed.env.roledefs['all']
        # Atleast 3 nodes are needed to run this test.
        if len(nodes) < 3:
            raise self.skipTest(
                "Skipping Test. At least 3 nodes required to run the test")

        # Configure datacenter tag on alternate servers.
        count=0
        dc_server_list=[]
        for node in nodes:
            count=count+1
            if (count%2) == 0:
                continue
            else:
                dc_server_list.append(node)
        result = self.smgr_fixture.add_tag_and_verify_server_listing(dc_server_list, tag_ind='datacenter', tag_val='testdatacenter1')
        if result == False:
            return False
        dc_server_ids=[]
        for node in dc_server_list:
            dc_server_ids.append(self.smgr_fixture.get_server_with_ip_from_db(ip=node.split('@')[1])['server'][0]['id'])

        # Configure user_tag tag on alternate servers.
        count=0
        us_server_list=[]
        for node in nodes:
            count=count+1
            if ((count+1)%2) == 0:
                continue
            else:
                us_server_list.append(node)
        result = self.smgr_fixture.add_tag_and_verify_server_listing(us_server_list, tag_ind='user_tag', tag_val='testusertag1')
        if result == False:
            return False
        us_server_ids=[]
        for node in us_server_list:
            us_server_ids.append(self.smgr_fixture.get_server_with_ip_from_db(ip=node.split('@')[1])['server'][0]['id'])

        #Verify restart using tag.
        with settings(host_string=self.smgr_fixture.svrmgr, password=self.smgr_fixture.svrmgr_password, warn_only=True):
            run('server-manager restart -F --tag %s=%s' % ('datacenter', 'testdatacenter1'))
        time.sleep(10)
        with settings(host_string=self.smgr_fixture.svrmgr, password=self.smgr_fixture.svrmgr_password, warn_only=True):
            server_ids=run('server-manager status server | grep restart_issued -B4 | grep id')
        fail_flag=0
        for node in dc_server_ids:
            if node in server_ids:
                self.logger.info('Server %s restarted with tag %s=%s' % (node, 'datacenter', 'testdatacenter1'))
            else:
                self.logger.error('Server %s not restarted with tag %s=%s' % (node, 'datacenter', 'testdatacenter1'))
                fail_flag=1
        if fail_flag == 1:
            self.logger.error("Test test_restart_servers_using_tag FAILED")
            return False
        with settings(host_string=self.smgr_fixture.svrmgr, password=self.smgr_fixture.svrmgr_password, warn_only=True):
            run('server-manager restart -F --tag %s=%s' % ('user_tag', 'testusertag1'))
        time.sleep(10)
        with settings(host_string=self.smgr_fixture.svrmgr, password=self.smgr_fixture.svrmgr_password, warn_only=True):
            server_ids=run('server-manager status server | grep restart_issued -B4 | grep id')
        fail_flag=0
        for node in us_server_ids:
            if node in server_ids:
                self.logger.info('Server %s restarted with tag %s=%s' % (node, 'user_tag', 'testusertag1'))
            else:
                self.logger.error('Server %s not restarted with tag %s=%s' % (node, 'user_tag', 'testusertag1'))
                fail_flag=1
        if fail_flag == 1:
            self.logger.error("Test test_restart_servers_using_tag FAILED")
            return False
        for node in nodes:
            self.smgr_fixture.delete_tag_from_server(server_ip=node.split('@')[1],
                all_tags=True)
        return True
    #end test_restart_servers_using_tag


    def test_reimage_servers_and_status_check_using_tag(self):
        self.logger.info("Verify server reimage and check reimage status using tags.")
        nodes = self.smgr_fixture.testbed.env.roledefs['all']
        # Atleast 3 nodes are needed to run this test.
        if len(nodes) < 3:
            raise self.skipTest(
                "Skipping Test. At least 3 nodes required to run the test")

        # Configure demo-dc-1 tag on first 50% servers.
        count=0
        dc1_server_list=[]
        for node in nodes:
            count=count+1
            if count > (len(nodes)/2):
                continue
            else:
                dc1_server_list.append(node)
        result = self.smgr_fixture.add_tag_and_verify_server_listing(dc1_server_list, tag_ind='datacenter', tag_val='demo-dc-1')
        if result == False:
            return False
        dc1_server_ids=[]
        for node in dc1_server_list:
            dc1_server_ids.append(self.smgr_fixture.get_server_with_ip_from_db(ip=node.split('@')[1])['server'][0]['id'])

        # Configure demo-dc-2 tag on last 50% servers.
        count=0
        dc2_server_list=[]
        for node in nodes:
            count=count+1
            if count <= (len(nodes)/2):
                continue
            else:
                dc2_server_list.append(node)
        result = self.smgr_fixture.add_tag_and_verify_server_listing(dc2_server_list, tag_ind='datacenter', tag_val='demo-dc-2')
        if result == False:
            return False
        dc2_server_ids=[]
        for node in dc2_server_list:
            dc2_server_ids.append(self.smgr_fixture.get_server_with_ip_from_db(ip=node.split('@')[1])['server'][0]['id'])

        # Configure demo-floor-1 tag on alternate servers.
        count=0
        fl1_server_list=[]
        for node in nodes:
            count=count+1
            if (count%2) == 0:
                continue
            else:
                fl1_server_list.append(node)
        result = self.smgr_fixture.add_tag_and_verify_server_listing(fl1_server_list, tag_ind='floor', tag_val='demo-floor-1')
        if result == False:
            return False
        fl1_server_ids=[]
        for node in fl1_server_list:
            fl1_server_ids.append(self.smgr_fixture.get_server_with_ip_from_db(ip=node.split('@')[1])['server'][0]['id'])

        # Configure demo-floor-2 tag on alternate servers.
        count=0
        fl2_server_list=[]
        for node in nodes:
            count=count+1
            if ((count+1)%2) == 0:
                continue
            else:
                fl2_server_list.append(node)
        result = self.smgr_fixture.add_tag_and_verify_server_listing(fl2_server_list, tag_ind='floor', tag_val='demo-floor-2')
        if result == False:
            return False
        fl2_server_ids=[]
        for node in fl2_server_list:
            fl2_server_ids.append(self.smgr_fixture.get_server_with_ip_from_db(ip=node.split('@')[1])['server'][0]['id'])

        #Verify reimage and check reimage status using tag.
        nested_tag = 'datacenter=demo-dc-1,floor=demo-floor-1'
        nested_set = set(dc1_server_ids).intersection(set(fl1_server_ids))
        nested_tag_server_ids=list(nested_set)
        result = self.smgr_fixture.reimage(tag=nested_tag, tag_server_ids=nested_tag_server_ids)

        for node in nodes:
            self.smgr_fixture.delete_tag_from_server(server_ip=node.split('@')[1],
                all_tags=True)

        return result
    #end test_restart_servers_using_tag

    def test_provision_servers_and_add_compute_using_tag(self):
        self.logger.info("Verify server provisioning and add delete of a compute node using tags.")
        nodes = self.smgr_fixture.testbed.env.roledefs['all']

        # Atleast 3 nodes are needed to run this test.
        if len(nodes) < 3:
            raise self.skipTest(
                "Skipping Test. At least 3 nodes required to run the test")

        # Atleast 2 compute nodes are needed to run this test.
        compute_nodes=self.smgr_fixture.testbed.env.roledefs['compute']
        if len(compute_nodes) < 2:
            raise self.skipTest(
                "Skipping Test. At least 2 compute nodes required to run the test")

        # Reimage all the nodes in the cluster.
        self.smgr_fixture.reimage(no_pkg=True)

        # Create list of computes to provision first and added later.
        first_compute_nodes=list(compute_nodes[:-1])
        add_later_compute=list(set(compute_nodes).difference(set(first_compute_nodes)))

        # Configure user_tag first-provision on nodes to be provisioned first.
        first_tag='user_tag=first-provision'
        fp_server_list=[]
        for node in nodes:
            if node in add_later_compute:
                continue
            else:
                fp_server_list.append(node)
        result = self.smgr_fixture.add_tag_and_verify_server_listing(fp_server_list, tag_ind='user_tag', tag_val='first-provision')
        if result == False:
            return False

        # Configure user_tag second-provision on nodes to be provisioned later.
        second_tag='user_tag=second-provision'
        result = self.smgr_fixture.add_tag_and_verify_server_listing(add_later_compute, tag_ind='user_tag', tag_val='second-provision')
        if result == False:
            return False

        # provision the first set of nodes.
        result=self.smgr_fixture.provision(tag=first_tag)
        if result is True:
            for index in range(PROVISION_TIME/10):
                time.sleep(10)
                with settings(host_string=self.smgr_fixture.svrmgr, password=self.smgr_fixture.svrmgr_password, warn_only=True):
                    states=run('server-manager status server --tag %s | grep status' % first_tag)
                if len(states.splitlines()) == len(fp_server_list):
                    flag_prov_comp=len(fp_server_list)
                    for each_state in states.splitlines():
                        if ('provision_completed' in each_state.split(':')[1]):
                            flag_prov_comp=flag_prov_comp-1
                    if flag_prov_comp == 0:
                        self.logger.info('All the servers with tag %s have provisioned successfully' % first_tag)
                        break
                else:
                    self.logger.error('Number of servers with tag %s and servers listed are not matching.' % first_tag)

        # Check only the provisioned computes are listed.
        cfgm_status=self.check_cfgm0_status()
        if not cfgm_status:
            self.logger.error('Connection failed to Cfgm-0, please check the node.')
            return False.

        add_later_compute_id=self.smgr_fixture.get_server_with_ip_from_db(ip=add_later_compute[0].split('@')[1])['server'][0]['id']
        config_node = self.smgr_fixture.testbed.env.roledefs['cfgm']
        cfgm_pswd=self.smgr_fixture.testbed.env.passwords[config_node[0]]
        with settings(host_string=config_node[0], password=cfgm_pswd, warn_only=True):
            result=run('source /etc/contrail/openstackrc; nova service-list | grep nova-compute | grep enabled')
            if add_later_compute_id in result:
                self.logger.error('Compute node %s was not provisioned but still shows up in nova service-list, FAILED!!!' % add_later_compute_id)
                return False

        # Add an cirros image and create a VM out of it.
        open_stack_host = self.smgr_fixture.testbed.env.roledefs['openstack'][0]
        open_stack_pswd = self.smgr_fixture.testbed.env.passwords[open_stack_host]
        cmd = 'source /etc/contrail/openstackrc; gunzip /root/cirros-0.3.0-x86_64-disk.vmdk.gz | glance '
        cmd = cmd + 'image-create --name "cirros" --is-public True --container-format bare --disk-format vmdk --property '
        cmd = cmd + 'vmware_disktype="sparse" --property vmware_adaptertype="ide" --file /root/cirros-0.3.0-x86_64-disk.vmdk'
        copy_VM_image = local('sshpass -p "%s" scp -o "StrictHostKeyChecking no" -r %s %s:%s' % (
            open_stack_pswd,'/cs-shared/images/converts/cirros-0.3.0-x86_64-disk.vmdk.gz',open_stack_host,'/root/'), capture=True)
        with settings(host_string=open_stack_host, password=open_stack_pswd, warn_only=True):
            add_cirros_image=run(cmd)
            cmd = 'source /etc/contrail/openstackrc; neutron net-create VN1; neutron subnet-create --ip-version 4 VN1 10.1.1.0/24; '
            cmd = cmd + 'nova boot --flavor m1.tiny --min-count %s --max-count %s --image cirros VM1' % (
                              len(compute_nodes)-1, len(compute_nodes)-1)
            bring_up_vm=run(cmd)
            for i in range(10):
                vm_state=run('source /etc/contrail/openstackrc; nova list --name VM1')
                if vm_state.find('ACTIVE'):
                    break
                time.sleep(10)
            if i == 10:
                self.logger.error('VM1 did not come to active state even after 100 sec, FAILED!!!')
            cmd = 'source /etc/contrail/openstackrc; nova list --ip 10.1.1 | grep "10.1.1" | cut -d "=" -f 2 | '
            cmd = cmd + "awk '{print $1}'"
            vm1_ip=run(cmd)

        # add the second set of compute nodes through provision.
        result=self.smgr_fixture.provision(tag=second_tag)
        if result is True:
            for index in range(PROVISION_TIME/10):
                time.sleep(10)
                with settings(host_string=self.smgr_fixture.svrmgr, password=self.smgr_fixture.svrmgr_password, warn_only=True):
                    states=run('server-manager status server --tag %s | grep status' % second_tag)
                if len(states.splitlines()) == len(add_later_compute):
                    flag_prov_comp=len(add_later_compute)
                    for each_state in states.splitlines():
                        if ('provision_completed' in each_state.split(':')[1]):
                            flag_prov_comp=flag_prov_comp-1
                    if flag_prov_comp == 0:
                        self.logger.info('All the servers with tag %s have provisioned successfully' % second_tag)
                        break
                else:
                    self.logger.error('Number of servers with tag %s and servers listed are not matching.' % second_tag)

        # check for compute node added/provisioned later with tag, is registered with nova or not.
        cfgm_status=self.check_cfgm0_status()
        if not cfgm_status:
            self.logger.error('Connection failed to Cfgm-0, please check the node.')
            return False.

        with settings(host_string=config_node[0], password=cfgm_pswd, warn_only=True):
            result=run('source /etc/contrail/openstackrc; nova service-list | grep nova-compute | grep enabled | grep up')
            if add_later_compute_id not in result:
                self.logger.error('Compute node %s added later is not in nova service-list, FAILED!!!' % add_later_compute_id)
                return False

        # Launch a cirros VM on the new compute and ping the earlier VM's.
        with settings(host_string=open_stack_host, password=open_stack_pswd, warn_only=True):
            cmd = 'source /etc/contrail/openstackrc; '
            cmd = cmd + 'nova boot --flavor m1.tiny --image cirros VM2'
            cmd = cmd + ' --availability-zone nova:%s' % add_later_compute_id
            bring_up_vm=run(cmd)
            for i in range(10):
                vm_state=run('source /etc/contrail/openstackrc; nova list --name VM2')
                if vm_state.find('ACTIVE'):
                    break
                time.sleep(10)
            if i == 10:
                self.logger.error('VM2 did not come to active state even after 100 sec, FAILED!!!')
            cmd = 'source /etc/contrail/openstackrc; nova list --host %s --ip 10.1.1 | grep "10.1.1" | cut -d "=" -f 2 | ' % add_later_compute_id
            cmd = cmd + "awk '{print $1}'"
            vm2_ip=run(cmd)
            vm2_meta_ip=run("route | grep 169 | awk '{print $1}'")

        # Connect to vm2_ip and run ping to vm1_ip and check for 0% packet loss.
        with settings(host_string='root@%s' % '10.204.221.37', password='contrail123', warn_only=True):
            with settings(host_string='cirros@169.254.0.3', password='cubswin:)', warn_only=True):
                ret=run("ping -c 10 %s | grep ' 0% packet'" % vm1_ip)

        # reimage the compute node with tag, that was added/provisioned later. This is to remove it from the setup.
        self.smgr_fixture.reimage(tag=second_tag, tag_server_ids=[add_later_compute_id])

        # Check the removal of compute node from registered nova computes.
        cfgm_status=self.check_cfgm0_status()
        if not cfgm_status:
            self.logger.error('Connection failed to Cfgm-0, please check the node.')
            return False.

        with settings(host_string=config_node[0], password=cfgm_pswd, warn_only=True):
            result=run('source /etc/contrail/openstackrc; nova service-list | grep nova-compute | grep enabled | grep up')
            if add_later_compute_id in result:
                self.logger.error('Compute node %s is still in nova service-list after it was reimaged, FAILED!!!' % add_later_compute_id)
                return False

        return True
    #end test_provision_servers_and_add_compute_using_tag

    def test_inventory_information(self):
        self.logger.info("Check for inventory information of the servers attached to the SM.")
        self.logger.info("Verify few of the fields in the inventory information for the servers attached to the SM.")
        nodes = self.smgr_fixture.testbed.env.roledefs['all']
        # Atleast 1 node is needed to run this test.
        if len(nodes) < 1:
            raise self.skipTest(
                "Skipping Test. At least 1 target node required to run the test")

        #Run general inventory show test cases.
        if not smgr_inventory_monitoring_tests.inventory_show_tests(self):
            self.logger.error("Inventory Show Tests FAILED !!!")
            return False
        self.logger.info("Inventory Show Tests passed!!!")

        #Run field verification tests on each of the computes inventory output.
        target_computes=self.smgr_fixture.get_compute_node_from_testbed_py()
        for each_target_node in target_computes:
            node_name=self.smgr_fixture.get_server_with_ip_from_db(each_target_node.split('@')[1])['server'][0]['id']
            if not smgr_inventory_monitoring_tests.inventory_tests(self, node_name):
                self.logger.error("Inventory Tests for %s FAILED !!!" % node_name)
                return False
        self.logger.info("Inventory Tests for all the compute nodes passed!!!")
        return True
    #end test_inventory_information

    def test_monitoring_information(self):
        self.logger.info("Check for monitoring information of the servers attached to the SM.")
        self.logger.info("Verify few of the fields in the monitoring information for the servers attached to the SM.")
        nodes = self.smgr_fixture.testbed.env.roledefs['all']
        # Atleast 1 node is needed to run this test.
        if len(nodes) < 1:
            raise self.skipTest(
                "Skipping Test. At least 1 target node required to run the test")

        #Run general monitoring show test cases.
        if not smgr_inventory_monitoring_tests.monitoring_show_tests(self):
            self.logger.error("Monitoring Show Tests FAILED !!!")
            return False
        self.logger.info("Monitoring Show Tests passed!!!")

        #Run negative tests and restart cases on monitoring functionality.
        if not smgr_inventory_monitoring_tests.monitoring_functionality_tests(self):
            self.logger.error("Monitoring Functionality Tests FAILED !!!")
            return False
        self.logger.info("Monitoring Functionality Tests passed!!!")
        return True

    #end test_monitoring_information
