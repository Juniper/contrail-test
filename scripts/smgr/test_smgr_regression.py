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
import smgr_upgrade_tests
from fabric.api import settings, run
import time
import pdb

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


