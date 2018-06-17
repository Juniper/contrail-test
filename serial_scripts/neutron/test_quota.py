import random
from vn_test import VNFixture
from security_group import SecurityGroupFixture 
from vn_test import MultipleVNFixture
from floating_ip import FloatingIPFixture
from common.connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper
from user_test import UserFixture
from project_test import ProjectFixture
from common.neutron.base import BaseNeutronTest
from test import *
from common.isolated_creds import IsolatedCreds
from tcutils.util import *
from tcutils.contrail_status_check import *
from common.openstack_libs import neutron_client_exception as CommonNetworkClientException 


class TestQuotaUpdate(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(TestQuotaUpdate, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestQuotaUpdate, cls).tearDownClass()

    @preposttest_wrapper
    def test_update_default_quota_for_admin_tenant(self):
        result = True
        # Get current object count and test on top of that
        admin_proj_obj = self.vnc_lib.project_read(
                         fq_name=['default-domain', self.inputs.admin_tenant])
        subnets = self.get_subnets_count(admin_proj_obj.uuid) + 3
        vns = len(admin_proj_obj.get_virtual_networks() or []) + 3
        floating_ips = len(admin_proj_obj.get_floating_ip_back_refs() or []) + 10
        routers = len(admin_proj_obj.get_logical_routers() or []) + 10
        sgs = len(admin_proj_obj.get_security_groups() or []) + 5
        vmis = len(admin_proj_obj.get_virtual_machine_interfaces() or []) + 5

        self.update_default_quota_list(
            subnet=subnets,
            virtual_network=vns,
            floating_ip=floating_ips,
            logical_router=routers,
            security_group_rule=10,
            virtual_machine_interface=vmis,
            security_group=sgs)

        # Account for 1 default SG rule created
        resource_dict = self.create_quota_test_resources(
            self.admin_inputs,
            self.admin_connections,
            vn_count=3,
            router_count=10,
            secgrp_count=5,
            secgep_rule_count=8,
            fip_count=10,
            port_count=5)

        for item in resource_dict.keys():
            if item != 'vn_fix':
                if None in resource_dict[item]:
                    result = False
                    self.logger.error(
                        "Error while creating resource within quota limit for %s.Please check logs " %
                        (item))

        (vn_name, vn_fix) = resource_dict['vn_fix']._vn_fixtures[1]
        sg_objs = resource_dict['sg_grps']
        response_dict = self.verify_quota_limit(
            self.admin_inputs,
            self.admin_connections,
            vn_fix,
            sg_objs[0])
        for item in response_dict.keys():
            if response_dict[item]:
                result = False
                self.logger.error("Quota limit not followed for %s " % (item))

        assert result, 'Quota tests failed'


    @preposttest_wrapper
    def test_update_default_quota_for_new_tenant(self):
        result = True

        self.update_default_quota_list(
            subnet=3,
            virtual_network=3,
            floating_ip=10,
            logical_router=10,
            security_group_rule=10,
            virtual_machine_interface=5,
            security_group=5)

        project_name = 'Project'
        isolated_creds = IsolatedCreds(
            self.admin_inputs,
            project_name,
            ini_file=self.ini_file,
            logger=self.logger)
        project_obj = self.admin_isolated_creds.create_tenant(isolated_creds.project_name)
        self.admin_isolated_creds.create_and_attach_user_to_tenant(project_obj,
                            isolated_creds.username,isolated_creds.password)
        proj_inputs = isolated_creds.get_inputs(project_obj)
        proj_connection = project_obj.get_project_connections()
        resource_dict = self.create_quota_test_resources(
            proj_inputs,
            proj_connection,
            vn_count=3,
            router_count=10,
            secgrp_count=4,
            secgep_rule_count=8,
            fip_count=10,
            port_count=5)

        for item in resource_dict.keys():
            if item != 'vn_fix':
                if None in resource_dict[item]:
                    result = False
                    self.logger.error(
                        "Error while creating resource within quota limit for %s please check logs " %
                        (item))

        (vn_name, vn_fix) = resource_dict['vn_fix']._vn_fixtures[1]
        sg_objs = resource_dict['sg_grps']

        response_dict = self.verify_quota_limit(
            proj_inputs,
            proj_connection,
            vn_fix,
            sg_objs[0])
        for item in response_dict.keys():
            if response_dict[item]:
                result = False
                self.logger.error("Quota limit not followed for %s " % (item))

        assert result, 'Quota tests failed'
       
        
    @preposttest_wrapper
    def test_update_quota_for_admin_tenant(self):
        '''Update quota for admin tenent using neutron quota_update
        '''
        result = True
        quota_dict = {
            'subnet': 3,
            'router': 5,
            'network': 3,
            'floatingip': 4,
            'port': 5,
            'security_group': 4,
            'security_group_rule': 6}
        quota_rsp = self.admin_connections.quantum_h.update_quota(
            self.admin_connections.project_id,
            quota_dict)

        self.addCleanup(self.admin_connections.quantum_h.delete_quota, self.admin_connections.project_id)
        quota_show_dict = self.connections.quantum_h.show_quota(
            self.admin_connections.project_id)

        for neutron_obj in quota_rsp['quota']:
            if quota_rsp['quota'][neutron_obj] != quota_show_dict[
                    'quota'][neutron_obj]:
                self.logger.error(
                    "Quota update unsuccessful for %s for admin tenant " %
                    (neutron_obj))
                result = False
        assert result, 'Failed to update quota for admin tenant'

    @preposttest_wrapper
    def test_finite_default_quota_for_multiple_tenants(self):
        '''Test finite default quota for multiple tenants
        '''
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        result = True
        finite_default_val = 15
        self.update_default_quota_list(defaults=finite_default_val,defaults_knob=True)

        #Create project 1
        project_name = get_random_name('project1')
        isolated_creds = IsolatedCreds(
            self.admin_inputs,
            project_name,
            ini_file=self.ini_file,
            logger=self.logger)
        project_obj = self.admin_isolated_creds.create_tenant(isolated_creds.project_name)
        self.admin_isolated_creds.create_and_attach_user_to_tenant(project_obj,
                            isolated_creds.username,isolated_creds.password)
        proj_inputs = isolated_creds.get_inputs(project_obj)
        proj_connection = project_obj.get_project_connections()
        quota_dict1 = self.admin_connections.quantum_h.show_quota(
            project_obj.uuid)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict1)) 

        for neutron_obj in quota_dict1['quota']:
            if neutron_obj != 'nat_instance':
                if quota_dict1['quota'][neutron_obj] != finite_default_val:
                    self.logger.error(
                        "Default Quota limit not followed for %s and is set to %s " %
                        (neutron_obj, quota_dict1['quota'][neutron_obj]))
                    result = False
            else:
                if quota_dict1['quota'][neutron_obj] != -1:
                    self.logger.error(
                        "Default Quota limit not followed for %s and is set to %s " %
                        (neutron_obj, quota_dict1['quota'][neutron_obj]))
                    result = False


        #Create project 2
        project_name1 = get_random_name('project2')
        isolated_creds1 = IsolatedCreds(
            self.admin_inputs,
            project_name1,
            ini_file=self.ini_file,
            logger=self.logger)
        project_obj1 = self.admin_isolated_creds.create_tenant(isolated_creds1.project_name)
        self.admin_isolated_creds.create_and_attach_user_to_tenant(project_obj1,
                            isolated_creds1.username,isolated_creds1.password)
        proj_inputs1 = isolated_creds1.get_inputs(project_obj1)
        proj_connection1 = project_obj1.get_project_connections()
        quota_dict2 = self.admin_connections.quantum_h.show_quota(
            project_obj1.uuid)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict2))

        for neutron_obj in quota_dict2['quota']:
            if neutron_obj != 'nat_instance':
                if quota_dict2['quota'][neutron_obj] != finite_default_val:
                    self.logger.error(
                        "Default Quota limit not followed for %s and is set to %s " %
                        (neutron_obj, quota_dict2['quota'][neutron_obj]))
                    result = False
            else:
                if quota_dict2['quota'][neutron_obj] != -1:
                    self.logger.error(
                        "Default Quota limit not followed for %s and is set to %s " %
                        (neutron_obj, quota_dict2['quota'][neutron_obj]))
                    result = False

        self.admin_isolated_creds.delete_user(isolated_creds.username)
        self.admin_isolated_creds.delete_user(isolated_creds1.username)
        self.admin_isolated_creds.delete_tenant(project_obj)
        self.admin_isolated_creds.delete_tenant(project_obj1)
        assert result, 'Default quota for custom tenant is not set' 


    @preposttest_wrapper
    def test_combo_default_quota_for_multiple_tenants(self):
        '''Test default quota for multiple tenants having defaults and specific resource
        '''
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        result = True
        finite_default_val = 15
        virtual_network = 5
        self.update_default_quota_list(defaults=finite_default_val,
            defaults_knob=True,virtual_network=virtual_network)

       #Create project 1
        project_name = get_random_name('project1')
        isolated_creds = IsolatedCreds(
            self.admin_inputs,
            project_name,
            ini_file=self.ini_file,
            logger=self.logger)
        project_obj = self.admin_isolated_creds.create_tenant(isolated_creds.project_name)
        self.admin_isolated_creds.create_and_attach_user_to_tenant(project_obj,
                            isolated_creds.username,isolated_creds.password)
        proj_inputs = isolated_creds.get_inputs(project_obj)
        proj_connection = project_obj.get_project_connections()

        quota_dict1 = self.admin_connections.quantum_h.show_quota(
            project_obj.uuid)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict1))

        for neutron_obj in quota_dict1['quota']:
            if neutron_obj != 'nat_instance' and neutron_obj != 'network':
                if quota_dict1['quota'][neutron_obj] != finite_default_val:
                    self.logger.error(
                        "Default Quota limit not followed for %s and is set to %s " %
                        (neutron_obj, quota_dict1['quota'][neutron_obj]))
                    result = False
            else:
                if neutron_obj == 'network':
                    if quota_dict1['quota'][neutron_obj] != virtual_network:
                        self.logger.error(
                                "Default Quota limit not followed for %s and is set to %s " %
                                (neutron_obj, quota_dict1['quota'][neutron_obj]))
                        result = False
                else:
                    if quota_dict1['quota'][neutron_obj] != -1:
                        self.logger.error(
                            "Default Quota limit not followed for %s and is set to %s " %
                            (neutron_obj, quota_dict1['quota'][neutron_obj]))
                        result = False

        #Create project 2
        project_name1 = get_random_name('project2')
        isolated_creds1 = IsolatedCreds(
            self.admin_inputs,
            project_name1,
            ini_file=self.ini_file,
            logger=self.logger)
        project_obj1 = self.admin_isolated_creds.create_tenant(isolated_creds1.project_name)
        self.admin_isolated_creds.create_and_attach_user_to_tenant(project_obj1,
                            isolated_creds1.username,isolated_creds1.password)
        proj_inputs1 = isolated_creds1.get_inputs(project_obj1)
        proj_connection1 = project_obj1.get_project_connections()

        quota_dict2 = self.admin_connections.quantum_h.show_quota(
            project_obj1.uuid)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict2))

        for neutron_obj in quota_dict2['quota']:
            if neutron_obj != 'nat_instance' and neutron_obj != 'network':
                if quota_dict2['quota'][neutron_obj] != finite_default_val:
                    self.logger.error(
                        "Default Quota limit not followed for %s and is set to %s " %
                        (neutron_obj, quota_dict2['quota'][neutron_obj]))
                    result = False
            else:
                if neutron_obj == 'network':
                    if quota_dict2['quota'][neutron_obj] != virtual_network:
                        self.logger.error(
                                "Default Quota limit not followed for %s and is set to %s " %
                                (neutron_obj, quota_dict2['quota'][neutron_obj]))
                        result = False
                else:
                    if quota_dict2['quota'][neutron_obj] != -1:
                        self.logger.error(
                            "Default Quota limit not followed for %s and is set to %s " %
                            (neutron_obj, quota_dict2['quota'][neutron_obj]))
                        result = False

        self.admin_isolated_creds.delete_user(isolated_creds.username)
        self.admin_isolated_creds.delete_user(isolated_creds1.username)
        self.admin_isolated_creds.delete_tenant(project_obj)
        self.admin_isolated_creds.delete_tenant(project_obj1)
        assert result, 'Default quota for custom tenant is not set'

    @preposttest_wrapper
    def test_unlimited_quota_to_limited_quota_when_current_usage_higher(self):
        '''
        Test quota update from unlimited to limited value when current usage is 
        already higher than then the quota limit
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24']
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        for quota_iterator in xrange(5):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(3):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        quota_dict = {
            'subnet' : 3,
            'network': 3,
            'security_group_rule': 8}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        try:
            temp_list = {'cidr' : '11.1.99.0/24'}
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            result &= False
            self.logger.error("Subnet creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn5"), inputs=self.inputs,
                subnets=['11.1.5.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        assert result, 'Update of Unlimited Quota to Limited Quota when current usage higher than quota limit'

    @preposttest_wrapper
    def test_unlimited_quota_to_limited_quota_when_current_usage_equal(self):
        '''
        Test quota update from unlimited to limited value when current usage is
        equal to the quota limit
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24']
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(5):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(3):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        quota_dict = {
            'subnet' : 5,
            'network': 5,
            'security_group_rule': 10}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn5"), inputs=self.inputs,
                subnets=['11.1.5.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        assert result, 'Update of Unlimited Quota to Limited Quota when current usage equals quota limit'


    @preposttest_wrapper
    def test_unlimited_quota_to_limited_quota_when_current_usage_lesser(self):
        '''
        Test quota update from unlimited to limited value when current usage is
        lesser than then the quota limit
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24']
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        for quota_iterator in xrange(5):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(3):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        quota_dict = {
            'subnet' : 6,
            'network': 6,
            'security_group_rule': 12}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(5,6):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(3,4):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)            
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn6"), inputs=self.inputs,
                subnets=['11.1.6.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        assert result, 'Update of Unlimited Quota to Limited Quota when current usage lesser than quota limit'
       
 
    @preposttest_wrapper
    def test_limited_quota_to_unlimited_quota_before_limit(self):
        '''
        Test quota update from limited to unlimited value when current usage is
        lesser than then the quota limit
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))            
        quota_dict = {
            'subnet' : 6,
            'network': 6,
            'security_group_rule': 10}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24']
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(5):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(2):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        quota_dict = {
            'subnet' : -1,
            'network': -1,
            'security_group_rule': -1}  
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(5,6):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(2,3):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        assert result, 'Update of Limited Quota to Unlimited Quota Before Limit' 


    @preposttest_wrapper
    def test_limited_quota_to_unlimited_quota_on_limit(self):
        '''
        Test quota update from limited to unlimited value when current usage is
        equal to the quota limit
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))            
        quota_dict = {
            'subnet' : 5,
            'network': 5,
            'security_group_rule': 8}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24']
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(5):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(2):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        quota_dict = {
            'subnet' : -1,
            'network': -1,
            'security_group_rule': -1}  
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(5,6):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(2,3):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)        
        assert result, 'Update of Limited Quota to Unlimited Quota On Limit'  

    @preposttest_wrapper
    def test_limited_quota_to_unlimited_quota_after_limit(self):
        '''
        Test quota update from limited to unlimited value when current usage is
        greater than then the quota limit
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))            
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24']
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(6):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(3):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        quota_dict = {
            'subnet' : 5,
            'network': 5,
            'security_group_rule': 8}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))           
        quota_dict = {
            'subnet' : -1,
            'network': -1,
            'security_group_rule': -1}  
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(6,7):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(3,4):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)        
        assert result, 'Update of Limited Quota to Unlimited Quota After Limit'  

    @preposttest_wrapper
    def test_inc_limited_quota_to_limited_quota_current_usage_lesser(self):
        '''
        Test increase in quota limit from limited to limited value when current usage is
        lesser than then the quota limit
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        quota_dict = {
            'subnet' : 5,
            'network': 5,
            'security_group_rule': 8}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))               
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24']
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(3):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(1):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        quota_dict = {
            'subnet' : 10,
            'network': 10,
            'security_group_rule': 10}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))           
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(3,10):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(1,3):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn10"), inputs=self.inputs,
                subnets=['11.1.10.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)        
        assert result, 'Update of Limited Quota to Limited Quota when current usage lesser than Quota limit' 


    @preposttest_wrapper
    def test_inc_limited_quota_to_limited_quota_current_usage_equal(self):
        '''
        Test increase in quota limit from limited to limited value when current usage is
        equal to the quota limit
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        quota_dict = {
            'subnet' : 5,
            'network': 5,
            'security_group_rule': 8}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))               
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24']
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(5):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(2):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        quota_dict = {
            'subnet' : 10,
            'network': 10,
            'security_group_rule': 10}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))           
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(5,10):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(2,3):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn10"), inputs=self.inputs,
                subnets=['11.1.10.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)        
        assert result, 'Update of Limited Quota to Limited Quota when current usage equal to Quota limit'   

    @preposttest_wrapper
    def test_inc_limited_quota_to_limited_quota_current_usage_higher(self):
        '''
        Test increase in quota limit from limited to limited value when current usage is
        higher than then the quota limit
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24']
        for quota_iterator in xrange(6):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(3):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        quota_dict = {
            'subnet' : 5,
            'network': 5,
            'security_group_rule': 8}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))         
        quota_dict = {
            'subnet' : 10,
            'network': 10,
            'security_group_rule': 12}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict)) 
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)             
        for quota_iterator in xrange(6,10):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(3,4):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn10"), inputs=self.inputs,
                subnets=['11.1.10.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)        
        assert result, 'Update of Limited Quota to Limited Quota when current usage higher than Quota limit'            

    @preposttest_wrapper
    def test_inc_limited_quota_to_limited_quota_current_usage_equal_newquota(self):
        '''
        Test increase in quota limit from limited to limited value when current usage is
        equal to the new quota limit
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24']
        for quota_iterator in xrange(10):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(3):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        quota_dict = {
            'subnet' : 5,
            'network': 5,
            'security_group_rule': 8}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))         
        quota_dict = {
            'subnet' : 10,
            'network': 10,
            'security_group_rule': 10}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict)) 
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn10"), inputs=self.inputs,
                subnets=['11.1.10.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)        
        assert result, 'Update of Limited Quota to Limited Quota when current usage equals new Quota limit'  
    
    @preposttest_wrapper
    def test_inc_limited_quota_to_limited_quota_current_usage_higher_newquota(self):
        '''
        Test increase in quota limit from limited to limited value when current usage is
        higher than the new quota limit
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24','11.1.10.0/24']
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(11):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(4):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        quota_dict = {
            'subnet' : 5,
            'network': 5,
            'security_group_rule': 8}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))         
        quota_dict = {
            'subnet' : 10,
            'network': 10,
            'security_group_rule': 10}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict)) 
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn10"), inputs=self.inputs,
                subnets=['11.1.11.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        resp = self.display_current_quota_usage_api_server(self.connections.project_id) 
        assert result, 'Update of Limited Quota to Limited Quota when current usage is higher than new Quota limit'  

    @preposttest_wrapper
    def test_dec_limited_quota_to_limited_quota_current_usage_lesser(self):
        '''
        Test deccrease in quota limit from limited to limited value when current usage is
        lesser than the quota limit
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        quota_dict = {
            'subnet' : 10,
            'network': 10,
            'security_group_rule': 10}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))             
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24','11.1.10.0/24']
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(6):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(2):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        quota_dict = {
            'subnet' : 5,
            'network': 5,
            'security_group_rule': 5}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict)) 
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn10"), inputs=self.inputs,
                subnets=['11.1.11.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)        
        assert result, 'Decrease Quota when current usage is lesser than Quota limit' 

    @preposttest_wrapper
    def test_dec_limited_quota_to_limited_quota_current_usage_equal(self):
        '''
        Test deccrease in quota limit from limited to limited value when current usage is
        equal to the quota limit
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        quota_dict = {
            'subnet' : 10,
            'network': 10,
            'security_group_rule': 10}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))             
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24','11.1.10.0/24']
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(10):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(3):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        quota_dict = {
            'subnet' : 5,
            'network': 5,
            'security_group_rule': 5}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict)) 
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn10"), inputs=self.inputs,
                subnets=['11.1.11.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        assert result, 'Decrease Quota when current usage is equal to Quota limit' 

    @preposttest_wrapper
    def test_dec_limited_quota_to_limited_quota_current_usage_higher(self):
        '''
        Test deccrease in quota limit from limited to limited value when current usage is
        higher than the quota limit
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24','11.1.10.0/24']
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(11):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(4):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        quota_dict = {
            'subnet' : 10,
            'network': 10,
            'security_group_rule': 10}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict)) 
        quota_dict = {
            'subnet' : 5,
            'network': 5,
            'security_group_rule': 5}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict)) 
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn10"), inputs=self.inputs,
                )))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        assert result, 'Decrease Quota when current usage is higher than Quota limit' 

    @preposttest_wrapper
    def test_dec_limited_quota_to_limited_quota_current_usage_equal_newquota(self):
        '''
        Test deccrease in quota limit from limited to limited value when current usage is
        equal to the new quota limit
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        quota_dict = {
            'subnet' : 10,
            'network': 10,
            'security_group_rule': 10}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict)) 
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24','11.1.10.0/24']
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(5):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(1):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        quota_dict = {
            'subnet' : 5,
            'network': 5,
            'security_group_rule': 6}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict)) 
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn10"), inputs=self.inputs,
                subnets=['11.1.11.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)        
        assert result, 'Decrease Quota when current usage is equal to new Quota limit' 

    @preposttest_wrapper
    def test_dec_limited_quota_to_limited_quota_current_usage_lesser_newquota(self):
        '''
        Test deccrease in quota limit from limited to limited value when current usage is
        lesser than the new quota limit
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        quota_dict = {
            'subnet' : 10,
            'network': 10,
            'security_group_rule': 14}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict)) 
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24','11.1.10.0/24']
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(3):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(1):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        quota_dict = {
            'subnet' : 5,
            'network': 5,
            'security_group_rule': 10}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict)) 
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(3,5):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(1,3):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()          
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn10"), inputs=self.inputs,
                subnets=['11.1.11.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)        
        assert result, 'Decrease Quota when current usage is lesser than new Quota limit' 

    @preposttest_wrapper
    def test_create_max_quota_delete_max_quota_new_quota_lesser(self):
        '''
        Test creation of resource to max quota limit followed by deletion
        and update new quota with lesser value
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        quota_dict = {
            'subnet' : 5,
            'network': 5,
            'security_group_rule': 10}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict)) 
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24','11.1.10.0/24']
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(5):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(3):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(5):
            vn_obj[quota_iterator].cleanUp()
            self.remove_from_cleanups(vn_obj[quota_iterator])
        for quota_iterator in xrange(3):
            sg_obj[quota_iterator].cleanUp()
            self.remove_from_cleanups(sg_obj[quota_iterator])
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)            
        quota_dict = {
            'subnet' : 3,
            'network': 3,
            'security_group_rule': 8}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict)) 
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        for quota_iterator in xrange(3):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(2):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)          
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn10"), inputs=self.inputs,
                subnets=['11.1.11.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)        
        assert result, 'Reach max_quota and resource and reach max_quota which is lesser than previous max' 

    @preposttest_wrapper
    def test_create_max_quota_delete_max_quota_new_quota_higher(self):
        '''
        Test creation of resource to max quota limit followed by deletion
        and update new quota with higher value
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        quota_dict = {
            'subnet' : 5,
            'network': 5,
            'security_group_rule': 10}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict)) 
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24','11.1.10.0/24']
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(5):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(3):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(5):
            vn_obj[quota_iterator].cleanUp()
            self.remove_from_cleanups(vn_obj[quota_iterator])
        for quota_iterator in xrange(3):
            sg_obj[quota_iterator].cleanUp()
            self.remove_from_cleanups(sg_obj[quota_iterator])
        quota_dict = {
            'subnet' : 8,
            'network': 8,
            'security_group_rule': 12}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict)) 
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(8):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(4):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)          
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn10"), inputs=self.inputs,
                subnets=['11.1.11.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)        
        assert result, 'Reach max_quota and resource and reach max_quota which is higher than previous max' 


    @preposttest_wrapper
    def test_create_max_quota_delete_max_quota_new_quota_equal(self):
        '''
        Test creation of resource to max quota limit followed by deletion
        and update new quota same as old quota
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        quota_dict = {
            'subnet' : 5,
            'network': 5,
            'security_group_rule': 10}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict)) 
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24','11.1.10.0/24']
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(5):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(3):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(5):
            vn_obj[quota_iterator].cleanUp()
            self.remove_from_cleanups(vn_obj[quota_iterator])
        for quota_iterator in xrange(3):
            sg_obj[quota_iterator].cleanUp()
            self.remove_from_cleanups(sg_obj[quota_iterator])
        quota_dict = {
            'subnet' : 5,
            'network': 5,
            'security_group_rule': 10}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict)) 
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        for quota_iterator in xrange(5):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(3):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn10"), inputs=self.inputs,
                subnets=['11.1.11.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)        
        assert result, 'Reach max_quota and resource and reach max_quota which is equal to previous max'

    @preposttest_wrapper
    def test_validate_quota_delete_finite_default(self):
        '''
        Test deletion of quota limit reverts quota limit to
        finite default value
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        finite_default_val = 6
        self.update_default_quota_list(defaults=finite_default_val,defaults_knob=True)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))        
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24','11.1.10.0/24']            
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(6):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(1):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup() 
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn10"), inputs=self.inputs,
                subnets=['11.1.11.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        quota_dict = {
            'subnet' : 8,
            'network': 8,
            'security_group_rule': 8}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict)) 
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(6,8):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(1,2):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn10"), inputs=self.inputs,
                subnets=['11.1.11.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        quota_rsp = self.connections.quantum_h.delete_quota(
            self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn10"), inputs=self.inputs,
                subnets=['11.1.11.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        assert result, 'Quota delete reverts quota limit to a finite default value' 

    @preposttest_wrapper
    def test_validate_quota_delete_unlimited_default(self):
        '''
        Test deletion of quota limit reverts quota limit to
        unlimited default value
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict)) 
        quota_dict = {
            'subnet' : 5,
            'network': 5,
            'security_group_rule': 8}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))            
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24','11.1.10.0/24']            
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(5):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(2):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup() 
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            temp = (self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn10"), inputs=self.inputs,
                subnets=['11.1.11.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        quota_rsp = self.connections.quantum_h.delete_quota(
            self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(5,8):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(2,3):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)        
        assert result, 'Quota delete reverts quota limit to a unlimited default value' 

    @preposttest_wrapper
    def test_contrail_restart_inc_limited_quota_to_limited_quota_current_usage_higher(self):
        '''
        Test contrail api restart does not have any un-desired impact on quota management
        '''
        result = True
        net_rsp = self.connections.quantum_h.list_networks()
        self.logger.info(
            "Network list is : \n %s" %
            (net_rsp))
        if len(net_rsp) > 3:
            self.remove_stale_networks(net_rsp,self.connections.project_id)
        self.addCleanup(self.connections.quantum_h.delete_quota, self.connections.project_id)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Defalult quota set for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        vn_name,vn_obj,sg_name,sg_obj = [],[],[],[]
        subnet_list = ['11.1.0.0/24','11.1.1.0/24','11.1.2.0/24','11.1.3.0/24', \
            '11.1.4.0/24','11.1.5.0/24','11.1.6.0/24','11.1.7.0/24','11.1.8.0/24', \
            '11.1.9.0/24']
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(6):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(3):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        quota_dict = {
            'subnet' : 5,
            'network': 5,
            'security_group_rule': 8}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        # Restart contrail-api service on all cfgm nodes
        for cfgm_ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('contrail-api', [cfgm_ip])
        cs_obj = ContrailStatusChecker(self.inputs)
        clusterstatus, error_nodes = cs_obj.wait_till_contrail_cluster_stable()
        assert clusterstatus, (
            'Hash of error nodes and services : %s' % (error_nodes))            
        quota_dict = {
            'subnet' : 10,
            'network': 10,
            'security_group_rule': 12}
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        self.logger.info(
            "Updated quota for tenant %s is : \n %s" %
            (self.inputs.project_name, quota_dict))
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        for quota_iterator in xrange(6,10):
            it_name = ''.join(["test_sec_vn",str(quota_iterator)])
            vn_name.append(get_random_name(it_name))
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name[quota_iterator], inputs=self.inputs, subnets=[subnet_list[quota_iterator]])))
            assert vn_obj[quota_iterator].verify_on_setup()
        for quota_iterator in xrange(3,4):
            it_name = ''.join(["test_sec_grp",str(quota_iterator)])
            sg_name.append(get_random_name(it_name))
            sg_obj.append(self.useFixture(SecurityGroupFixture(
                self.connections, self.inputs.domain_name,
                self.inputs.project_name, secgrp_name=sg_name[quota_iterator],
                option='neutron')))
            sg_obj[quota_iterator].create_sg_rule(sg_obj[quota_iterator].secgrp_id,secgrp_rules=self.get_rule(number=2))
            assert sg_obj[quota_iterator].verify_on_setup()
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        try:
            temp_list = {
            'cidr' : '11.1.99.0/24'
            }
            vn_obj[0].create_subnet(temp_list,vn_obj[0].ipam_fq_name)
            self.logger.error("Subnet creation should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'subnet\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("Subnet creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("Subnet creation failed with un-excepted exception : %s" % e.message)
                result &= False
        try:
            vn_obj.append(self.useFixture(VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=get_random_name("test_sec_vn10"), inputs=self.inputs,
                subnets=['11.1.10.0/24'])))
            result &= False
            self.logger.error("VN creation should not be successfull")
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'virtual_network\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("VN creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("VN creation failed with un-expected exception : %s" % e.message)
                result &= False
        try:
            sg_obj[0].delete_all_rules(sg_obj[0].secgrp_id)
            sg_obj[0].create_sg_rule(sg_obj[0].secgrp_id,secgrp_rules=self.get_rule(number=3))
            self.logger.error("Security group rule addition should not be successfull")
            result &= False
        except CommonNetworkClientException as e:
            regex_vn = r"Quota exceeded for resources\: \[\'security_group_rule\'\]"
            if re.search(regex_vn,e.message):
                self.logger.info("SG Rule creation failed as expected with Quota exception : %s" % e.message)
            else:
                self.logger.exception("SG Rule creation failed with un-excepted exception: %s" % e.message)
                result &= False
        resp = self.display_current_quota_usage_api_server(self.connections.project_id)
        assert result, 'Update of Limited Quota to Limited Quota when current usage higher than Quota limit with api restart'

    def create_quota_test_resources(
            self,
            inputs,
            connections,
            vn_count=1,
            vm_count=1,
            router_count=1,
            secgrp_count=1,
            secgep_rule_count=1,
            fip_count=1,
            port_count=1):
        resource_dict = {}
        vn_s = self.create_random_vn_list(vn_count)
        multi_vn_fixture = self.create_multiple_vn(inputs, connections, vn_s)
        assert multi_vn_fixture.verify_on_setup()
        vn_objs = multi_vn_fixture.get_all_fixture_obj()
        (self.vn1_name, self.vn1_fix) = multi_vn_fixture._vn_fixtures[0]
        assert self.vn1_fix.verify_on_setup()
        fip_list = self.create_multiple_floatingip(
            inputs,
            connections,
            fip_count,
            self.vn1_fix)
        router_objs = self.create_multiple_router(connections, router_count)
        secgrp_objs = self.create_multiple_secgrp(connections, secgrp_count)
        sg_rule_objs = self.create_multiple_secgrp_rule(
            connections,
            secgrp_objs[
                :1],
            secgep_rule_count)
        port_objs = self.create_multiple_ports(
            connections, [
                self.vn1_fix], port_count)
        resource_dict['vn_fix'] = multi_vn_fixture
        resource_dict['sg_grps'] = secgrp_objs
        resource_dict['fips'] = fip_list
        resource_dict['routers'] = router_objs
        resource_dict['sg_rules'] = sg_rule_objs
        resource_dict['ports'] = port_objs

        return resource_dict

    def verify_quota_limit(self, inputs, connections, vn_fix, sg_obj):

        response_dict = {}
        vn1_name = get_random_name('vn_test_quota')
        vn1_obj = connections.quantum_h.create_network(vn1_name)
        if vn1_obj:
            self.addCleanup(
                connections.quantum_h.delete_vn,
                vn1_obj['network']['id'])
        response_dict['network'] = vn1_obj
        subnet_cidr = get_random_cidr()
        subnet_rsp = connections.quantum_h.create_subnet(
            {'cidr': subnet_cidr}, vn_fix.vn_id)
        response_dict['subnet'] = subnet_rsp
        secgrp_obj = self.create_security_group(
            get_random_name('sec_grp'),
            connections.quantum_h)
        response_dict['secgrp'] = secgrp_obj
        router_obj = self.create_router(
            get_random_name('router'),
            connections)
        response_dict['router'] = router_obj
        sg_rule_obj = connections.quantum_h.create_security_group_rule(
            sg_obj['id'],
            protocol='tcp')
        response_dict['sg_rule'] = sg_rule_obj
        port_obj = connections.quantum_h.create_port(
            vn_fix.vn_id)
        # Cleanup the port incase port-create works
        if port_obj:
            self.addCleanup(connections.quantum_h.delete_port,
            port_obj['id'])
        response_dict['port'] = port_obj
        fip_obj = self.create_multiple_floatingip(
            inputs,
            connections,
            1,
            vn_fix)
        response_dict['fip'] = fip_obj

        return response_dict

    def create_multiple_vn(self, inputs, connections, vn_s, subnet_count=1):
        multi_vn_fixture = self.useFixture(MultipleVNFixture(
            connections=connections, inputs=inputs, subnet_count=subnet_count,
            vn_name_net=vn_s, project_name=inputs.project_name))
        return multi_vn_fixture

    def create_random_vn_list(self, count):
        vn_s = {}
        for i in range(count):
            vn_s[get_random_name('vn')] = [get_random_cidr()]
        return vn_s

    def create_multiple_router(self, connections, count=1):
        router_objs = []
        for i in range(count):
            router_obj = self.create_router(
                get_random_name('router'),
                connections)
            router_objs.append(router_obj)
        return router_objs

    def create_multiple_floatingip(
            self,
            inputs,
            connections,
            count,
            fvn_fixture):
        body = {'router:external': 'True'}
        net_dict = {'network': body}
        net_rsp = connections.quantum_h.update_network(
            fvn_fixture.vn_id,
            net_dict)
        assert net_rsp['network'][
            'router:external'] == True, 'Failed to update router:external to True'
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=inputs.project_name,
                inputs=inputs,
                connections=connections,
                pool_name='',
                vn_id=fvn_fixture.vn_id, option='neutron'))
        assert fip_fixture.verify_on_setup()
        if count == 1:
            fip_resp = connections.quantum_h.create_floatingip(
                fvn_fixture.vn_id,
                connections.project_id)
            if fip_resp:
                self.addCleanup(
                    fip_fixture.delete_floatingip,
                    fip_resp['floatingip']['id'])
        else:
            fip_resp = fip_fixture.create_floatingips(
                fvn_fixture.vn_id,
                count)
            self.addCleanup(fip_fixture.delete_floatingips, fip_resp)
        return fip_resp

    def create_multiple_secgrp(self, connections, count=1):
        secgrp_objs = []
        for i in range(count):
            secgrp_obj = self.create_security_group(
                get_random_name('sec_grp'),
                connections.quantum_h)
            secgrp_objs.append(secgrp_obj)
        return secgrp_objs

    def create_multiple_secgrp_rule(self, connections, sg_obj_list, count=1):
        proto = 'tcp'
        port_range_min = 1
        sg_rule_objs = []
        for sg_obj in sg_obj_list:
            for i in range(count):
                port = port_range_min + i
                sg_rule_obj = connections.quantum_h.create_security_group_rule(
                    sg_obj['id'],
                    protocol=proto,
                    port_range_min=port,
                    port_range_max=port)
                sg_rule_objs.append(sg_rule_obj)

        return sg_rule_objs

    def create_multiple_ports(self, connections, vn_fix_list, count=1):
        port_obj_list = []
        for vn_fix in vn_fix_list:
            for i in range(count):
                port_obj = connections.quantum_h.create_port(
                    vn_fix.vn_id)
                if port_obj:
                    self.addCleanup(
                        connections.quantum_h.delete_port,
                        port_obj['id'])
                port_obj_list.append(port_obj)
        return port_obj_list

    def display_current_quota_usage_api_server(self,tenant_id):
        quota_count = self.api_s_inspect.get_quota_usage_count(tenant_id)
        for resource in quota_count.keys():
            self.logger.info("Resource : %s -- Quota Consumed : %s " %
                (resource,quota_count[resource]))
        return None

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            if fix.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break

    def remove_stale_networks(self,net_rsp,project_id):
        default_nws = ['default-virtual-network','ip-fabric','__link_local__']
        tenant_id = str(get_plain_uuid(project_id))
        for network in net_rsp:
            self.logger.info("Network Name : %s Tenant id from list : %s Tenant id from script: %s" % 
                (network['name'],network['tenant_id'],tenant_id))
            if network['name'] not in default_nws and network['tenant_id'] == tenant_id:
                self.logger.info("Deleting network : %s " % (network['name']))
                self.connections.quantum_h.delete_vn(network['id'])

    def get_rule(self,number=2):
        if number == 2:
            rule2 = [{'direction': '<>',
                'protocol': 'tcp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                 {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]    
            return rule2 
        if number == 3:
            rule3 = [{'direction': '<>',
                'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                 {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 },
                 {'direction': '<>',
                 'protocol': 'udp',
                 'src_addresses': [{'subnet': {'ip_prefix': '::', 'ip_prefix_len': 0}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
            return rule3


