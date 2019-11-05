from __future__ import absolute_import
from __future__ import division
# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
from builtins import str
from past.utils import old_div
import os
import time
import fixtures
import testtools
import re
import test
from tcutils.wrappers import preposttest_wrapper
from . import base
from .webui_topology import *
topo = sdn_webui_config()
global count, mirror_enabled_already
count = 1
mirror_enabled_already = False

class WebuiTestSanity(base.WebuiBaseTest):

    @classmethod
    def setUpClass(cls):
        super(WebuiTestSanity, cls).setUpClass()

    def runTest(self):
        pass
    # end runTest

    # UI config tests #

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test1_1_create_svc_templates(self):
        ''' UI Config-> Services-> Service Templates  : Test svc template creation
        '''
        assert self.res.setup_obj.create_svc_template(), 'Svc template creation failed'
        return True
    # end test_create_svc_template

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test1_9_create_svc_instances(self):
        '''UI Config-> Services-> Service Instances : Test svc instance creation
        '''
        assert self.res.setup_obj.create_svc_instance(), 'Svc instance creation failed'
        return True
    # end test_create_svc_instance

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test1_2_create_ipams(self):
        '''UI Config : Networking -> IP Address Management :  Test ipam creation
        '''
        assert self.res.setup_obj.create_ipam(), 'Ipam creation failed'
        return True
    # end test_create_svc_instance

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test1_3_create_virtual_networks(self):
        '''UI Config : Networking -> Networks : Test virtual network creation
        '''
        assert self.res.setup_obj.create_vn(),'Virtual network creation failed'
        return True
    # end test_create_virtual_networks

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test1_4_create_ports(self):
        '''UI Config : Networking -> ports : Test port creation
        '''
        assert self.res.setup_obj.create_port(), 'Port creation creation failed'
        return True
    # end test_create_ports

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test1_5_create_routers(self):
        '''UI Config : Networking -> Routers : Test router creation
        '''
        assert self.res.setup_obj.create_router(), 'Router creation failed'
        return True
    # end test_create_routers

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test1_6_create_policies(self):
        '''UI Config : Networking -> Policies : Test Policy creation
        '''
        assert self.res.setup_obj.create_policy(), 'Policy creation failed'
        return True
    # end test_create_policies

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test1_7_attach_policy_to_vn(self):
        '''UI Config : Networking -> Networks : Test attach_policy to vn
        '''
        assert self.res.setup_obj.attach_policy_to_vn(), 'Policy attach to a VN failed'
        return True
    # end test_attach_policy_to_vn

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test1_8_launch_virtual_instances(self):
        ''' Horizon Config : Test launch_virtual_instance
        '''
        assert self.res.setup_obj.create_vm(), 'Virtual instance launch failed'
        return True
    # end test_launch_virtual_instances

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_3_create_security_groups(self):
        assert self.res.setup_obj.create_security_group(), 'Security group creation failed'
        return True
    # end test_create_security_groups

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_1_create_dns_servers(self):
        '''UI Config : DNS -> Servers : Test dns server creation
        '''
        assert self.res.setup_obj.create_dns_server(), 'Dns server creation failed'
        return True
    # end test_create_dns_servers

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_2_create_dns_records(self):
        '''UI Config : DNS -> Records : Test dns record creation
        '''
        assert self.res.setup_obj.create_dns_record(), 'DNS record creation failed'
        return True
    # end test_create_dns_records

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_4_create_floating_ips(self):
        '''UI Config : Networking -> Networks : Test Floating IP creation
        '''
        assert self.res.setup_obj.create_floating_ip(), 'Floating IP creation failed'
        return True
    # end test_create_floating_ips

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_5_allocate_floating_ips(self):
        '''UI Config : Networking -> Floating IPs : Test allocation of FIPs
        '''
        assert self.res.setup_obj.allocate_floating_ip(), 'Allocation of fip failed'
        return True
    # end test_allocate_floating_ips

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_6_associate_floating_ips(self):
        '''UI Config : Networking -> Floating IPs : Test association of FIPs
        '''
        assert self.res.setup_obj.associate_floating_ip(), 'Association of fip failed'
        return True
    # end test_associate_floating_ips

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_2_3_create_svc_health_check(self):
        '''UI Config : Networking -> Services -> Health Check : Test svc health check creation
        '''
        assert self.res.setup_obj.create_svc_health_check(), 'Creation of health check failed'
        return True
    # end test_create_svc_health_check

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_8_create_bgp_aas(self):
        '''UI Config : Networking -> Services -> BGP as a Service : Test bgpaas creation
        '''
        assert self.res.setup_obj.create_bgp_aas(), 'Creation of bgpaas failed'
        return True
    # end test_create_bgp_aas

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_9_create_global_qos_config(self):
        '''
        Description: Test to create Global QoS config on the UI
        Steps:
            1. On the Contrail UI, go to Configure -> Infrastructure -> Global Config -> QoS
            2. Click on create, enter the config details in the fields and click on 'Save'
        Pass criteria:
            1. Step 2 above should pass
        '''
        assert self.res.setup_obj.create_global_qos_config(), 'Global QoS config creation failed'
        return True
    # end test_create_global_qos_config

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_1_4_create_qos_config(self):
        '''
        Description: Test to create QoS config on UI
        Steps:
            1. On the Contrail UI, go to Config -> Networking -> QoS
            2. Click on create, enter the config details in the fields and click on 'Save'
            3. Verify the creation of the QoS config
        Pass criteria:
            1. Step 2 and 3 above should pass
        '''
        assert self.res.setup_obj.create_qos_config(), 'Creation of QoS failed'
        return True
    # end test_create_qos_config

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_1_1_create_physical_router(self):
        '''
        Description: Test to create Physical Router on UI
        Steps:
            1. On the Contrail UI, go to Configure -> Physical Devices -> Physical Routers
            2. Click on create, enter the config details in the fields and click on 'Save'
        Pass criteria:
            1. Step 2 above should pass
        '''
        assert self.res.setup_obj.create_physical_router(), 'Creation of physical router failed'
        return True
    # end test_create_physical_router

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_1_2_create_physical_interfaces(self):
        '''
        Description: Test to create Physical Interfaces on UI
        Steps:
            1. On the Contrail UI, go to Configure -> Physical Devices -> Interfaces
            2. Click on create, enter the config details in the fields and click on 'Save'
        Pass criteria:
            1. Step 2 above should pass
        '''
        assert self.res.setup_obj.create_physical_interface(), 'Creation of physical interface failed'
        return True
    # end test_create_physical_interface

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_1_3_create_forwarding_classes(self):
        '''
        Description: Test to create Forwarding Classes on the UI
        Steps:
            1. On the Contrail UI, go to Configure -> Infrastructure -> Global Config -> Forwarding Classes
            2. Click on create, enter the config details in the fields and click on 'Save'
        Pass criteria:
            1. Step 2 above should pass
        '''
        assert self.res.setup_obj.create_forwarding_class(), 'Forwarding class creation failed'
        return True
    # end test_create_forwarding_classes

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_1_5_attach_qos_config_to_vn(self):
        '''
        Description: Test to attach a created QoS config to VN on UI
        Steps:
            1. On the Contrail UI, go to Config -> Networking -> Networks
            2. Click on edit on one of the VNs
            3. Click on 'Advanced Options', attach Qos config
            4. Click on 'Save'
        Pass criteria:
            1. Steps 3 and 4 above should pass
        '''
        assert self.res.setup_obj.attach_qos_config_to_vn(), 'Attaching of QoS failed'
        return True
    # end test_attach_qos_config_to_vn

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_1_6_create_network_route_table(self):
        '''
        Description: Test to create Network Route Table on UI
        Steps:
            1. On the Contrail UI, go to Config -> Networking -> Routing
            2. Click on create, enter the config details in the fields and click on 'Save'
            3. Verify the creation of the Network Route Table
        Pass criteria:
            1. Step 2 and 3 above should pass
        '''
        assert self.res.setup_obj.create_network_route_table(), 'Creation of Network Route Table failed'
        return True
    # end test_create_network_route_table

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_1_7_attach_network_route_table_to_VN(self):
        '''
        Description: Test to attach Network Route Table to VN on UI
        Steps:
            1. On the Contrail UI, go to Config -> Networking -> Networks
            2. Click on edit on one of the VNs
            3. Click on 'Advanced Options', attach Route table
            4. Click on 'Save'
        Pass criteria:
            1. Steps 3 and 4 above should pass
        '''
        assert self.res.setup_obj.attach_network_route_table(), 'Attaching of Network Route Table to VN failed'
        return True
    # end test_attach_network_route_table_to_VN

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_1_8_create_routing_policies(self):
        '''
        Description: Test to create Routing Policies on UI
        Steps:
            1. On the Contrail UI, go to Config -> Networking -> Routing -> Routing Policies
            2. Click on create, enter the config details in the fields and click on 'Save'
        Pass criteria:
            1. Step 2 above should pass
        '''
        assert self.res.setup_obj.create_routing_policies(), 'Creation of Routing Policie failed'
        return True
    # end test_create_routing_policies

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_1_9_create_route_aggregates(self):
        '''
        Description: Test to create Route Aggregates on UI
        Steps:
            1. On the Contrail UI, go to Config -> Networking -> Routing -> Route Aggregates
            2. Click on create, enter the config details in the fields and click on 'Save'
        Pass criteria:
            1. Step 2 above should pass
        '''
        assert self.res.setup_obj.create_route_aggregates(), 'Creation of Route Aggregates failed'
        return True
    # end test_create_route_aggregates

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_2_1_attach_routing_policy_to_si(self):
        '''
        Description: Test to attach a created Routing Policy to SI on UI
        Steps:
            1. On the Contrail UI, go to Config -> Services -> Service Instances
            2. Click on edit on the SI with NAT template
            3. Click on 'Routing Policy', attach the Routing policy
            4. Click on 'Save'
        Pass criteria:
            1. Steps 3 and 4 above should pass
        '''
        assert self.res.setup_obj.attach_routing_policy(), 'Attaching of Routing Policy failed'
        return True
    # end test_attach_routing_policy_to_si

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_2_2_attach_route_aggregate_to_si(self):
        '''
        Description: Test to attach a created Route Aggregate to SI on UI
        Steps:
            1. On the Contrail UI, go to Config -> Services -> Service Instances
            2. Click on edit on the SI with NAT template
            3. Click on 'Route Aggregate', attach the Route aggregate
            4. Click on 'Save'
        Pass criteria:
            1. Steps 3 and 4 above should pass
        '''
        assert self.res.setup_obj.attach_route_aggregate(), 'Attaching of Route Aggregate failed'
        return True
    # end test_attach_route_aggregate_to_si

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test2_7_attach_svc_health_check_to_si(self):
        '''
        Description: Test to attach a created Service Health Check template to SI on UI
        Steps:
            1. On the Contrail UI, go to Config -> Services -> Service Instances
            2. Click on edit on the SI v2
            3. Click on 'Service Health Check', attach the health check template
            4. Click on 'Save'
        Pass criteria:
            1. Steps 3 and 4 above should pass
        '''
        assert self.res.setup_obj.attach_svc_health_check(), 'Attaching of Health Check failed'
        return True
    # end test_attach_svc_health_check_to_si

    # UI verification tests

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test_verify_config_infra_global_config(self):
        '''Test to verify global config on config->Infrastructure->Global Config
           1. Go to Configure->Infrastructure->Global Config.
              and Get all the details of global config from both WebUI and API server.
              and Verify the WebUI details against API server details.

           Pass Criteria: Step 1 should pass
        '''
        assert self.webui.verify_global_api_data(), \
                                              'Global config data verification failed'
        return True
    # end test_verify_config_infra_global_config

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test_verify_config_infra_rbac_global(self):
        '''Test to verify RBAC under Configure->Infrastructure->RBAC->Global
           1. Go to Configure->Infrastructure->RBAC->Global.
           2. Get all the details of RBAC from both WebUI and API server.
           3. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_rbac_api_data(), 'RBAC config data verification failed'
        return True
    # end test_verify_config_infra_rbac_global

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test_verify_config_infra_rbac_domain(self):
        '''Test to verify RBAC under Configure->Infrastructure->RBAC->Domain
           1. Go to Configure->Infrastructure->RBAC->Domain.
           2. Get all the details of RBAC from both WebUI and API server.
           3. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_rbac_api_data(rbac_type='domain'), \
                                              'RBAC config data verification failed'
        return True
    # end test_verify_config_infra_rbac_domain

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test_verify_config_infra_rbac_project(self):
        '''Test to verify RBAC under Configure->Infrastructure->RBAC->Project
           1. Go to Configure->Infrastructure->RBAC->Project.
           2. Get all the details of RBAC from both WebUI and API server.
           3. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_rbac_api_data(rbac_type='project'), \
                                              'RBAC config data verification failed'
        return True
    # end test_verify_config_infra_rbac_project

    @preposttest_wrapper
    def test_verify_config_infra_global_log_statistic(self):
        '''Test to verify Log Statistic under Configure->Infrastructure->Global Config
           1. Go to Configure->Infrastructure->Global Config->Log Statistic
           2. Get all the details of Log statistic from both WebUI and API server.
           3. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_log_stat_api_data(), \
                   'Log Statistic config data verification failed'
        return True
    # end test_verify_config_infra_global_log_statistic

    @preposttest_wrapper
    def test_verify_config_infra_link_local_service(self):
        '''Test to verify LinkLocalService under Configure->Infrastructure->LinkLocalServices
           1. Go to Configure->Infrastructure->Link Local Services
           2. Get all the details of Link Local Services from both WebUI and API server.
           3. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_link_local_services_api_data(), \
                   'Link Local Services config data verification failed'
        return True
    # end test_verify_config_infra_link_local_services

    @preposttest_wrapper
    def test_verify_config_infra_virtual_router(self):
        '''Test to verify virtual router under Configure->Infrastructure->Virtual Router
           1. Go to Configure->Infrastructure->Virtual Router.
           2. Get all the details of virtual router from both WebUI and API server.
           3. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_vrouter_api_data(), \
                   'Virtual Router config data verification failed'
        return True
    # end test_verify_config_infra_virtual_router

    @preposttest_wrapper
    def test_verify_config_infra_service_appliances(self):
        '''Test to verify Service Appliance under Configure->Infrastructure
           1. Go to Configure->Infrastructure->Service Appliances.
           2. Get all the details of Service Appliances
              from both WebUI and API server.
           3. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_svc_appls_api_data(topo.svc_appliances_params), \
                   'Service Appliances config data verification failed'
        return True
    # end test_verify_config_infra_service_appliances

    @preposttest_wrapper
    def test_verify_config_infra_bgp_router(self):
        '''Test to verify BGP router under Configure->Infrastructure->BGP Routers
           1. Go to Configure->Infrastructure->BGP Routers.
           2. Get all the details of bgp router from both WebUI and API server.
           3. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_bgp_router_api_data(), \
                   'BGP Router config data verification failed'
        return True
    # end test_verify_config_infra_bgp_router

    @preposttest_wrapper
    def test_verify_config_infra_service_appl_set(self):
        '''Test to verify Service Appliance Sets under Configure->Infrastructure
           1. Go to Configure->Infrastructure->Service Appliance Sets.
           2. Get all the details of service appliance sets from
              both WebUI and API server.
           3. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_svc_appl_sets_api_data(), \
                   'Service Appliance Sets config data verification failed'
        return True
    # end test_verify_config_infra_service_appl_set

    @preposttest_wrapper
    def test_verify_config_infra_global_flow_aging(self):
        '''Test to verify Flow Aging under Configure->Infrastructure->Global Config
           1. Go to Configure->Infrastructure->Global Config->Flow Aging
           2. Get all the details of Flow Aging from both WebUI and API server.
           3. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_flow_aging_api_data(), \
                   'Flow Aging config data verification failed'
        return True
    # end test_verify_config_infra_global_flow_aging

    @preposttest_wrapper
    def test_verify_config_networking_floating_ips(self):
        '''Test floating ips on config->Networking->Manage Floating IPs page
        '''
        assert self.webui.verify_floating_ip_api_data(), 'Floating ips config data verification failed' 
        return True
    # end test_verify_config_networking_floating_ips

    @preposttest_wrapper
    def test_verify_config_networking_virtual_networks(self):
        '''Test networks on config->Networking->Networks page
        '''
        assert self.webui.verify_vn_api_data(), 'Virtual netoworks config data verification failed'
        return True
    # end test_verify_config_networking_virtual_networks

    @preposttest_wrapper
    def test_verify_config_networking_ports(self):
        '''Test to verify ports on config->Networking->Ports
           1. Go to Configure->Networking->Ports.
           2. Get all the details of ports from both WebUI and API server.
           3. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_port_api_data(topo.port_params), \
                                              'Ports config data verification failed'
        return True
    # end test_verify_config_networking_ports

    @preposttest_wrapper
    def test_verify_config_networking_intf_table(self):
        '''Test to verify Interface Route Table
           on config->Networking->Routing->Interface Route Table
           1. Go to Configure->Networking->Routing->Interface Route Table.
           2. Get all the details of interface table from both WebUI and API server.
           3. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_intf_route_tab_api_data(), \
                   'Interface Route Table config data verification failed'
        return True
    # end test_verify_config_networking_intf_table

    @preposttest_wrapper
    def test_verify_config_networking_ipams(self):
        '''Test ipams on config->Networking->IP Address Management page
        '''
        assert self.webui.verify_ipam_api_data(), 'Ipams config data verification failed'
        return True
    # end test_verify_config_networking_ipams

    @preposttest_wrapper
    def test_verify_config_networking_sec_group(self):
        '''Test to verify Security Groups under Configure->Networking->Security Groups
           1. Go to Configure->Networking->Security Groups
           2. Get all the details of security group from both WebUI and API server.
           3. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_security_group_api_data(), \
                   'Security Groups config data verification failed'
        return True
    # end test_verify_config_networking_sec_group

    @preposttest_wrapper
    def test_verify_config_networking_policies(self):
        '''Test polcies on config->Networking->Policies page
        '''
        assert self.webui.verify_policy_api_data(), 'Policies config data verification failed'
        return True
    # end test_verify_config_networking_policies

    @preposttest_wrapper
    def test_verify_config_networking_routers(self):
        '''Test to verify Routers under Configure->Networking->Routers
           1. Go to Configure->Networking->Routers
           2. Get all the details of Routers from both WebUI and API server.
           3. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_routers_api_data(), \
                   'Routers config data verification failed'
        return True
    # end test_verify_config_networking_routers

    @preposttest_wrapper
    def test_verify_config_dns_servers(self):
        '''Test to verify DNS Servers under Configure->DNS->Servers
           1. Go to Configure->DNS->Servers
           2. Get all the details of DNS servers from both WebUI and API server.
           3. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_dns_servers_api_data(), \
                   'DNS Servers config data verification failed'
        return True
    # end test_verify_config_dns_servers

    @preposttest_wrapper
    def test_verify_config_dns_records(self):
        '''Test to verify DNS Records under Configure->DNS->Records
           1. Go to Configure->DNS->Records
           2. Get all the details of DNS Records from both WebUI and API server.
           3. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_dns_records_api_data(topo.dns_record_params), \
                   'DNS Records config data verification failed'
        return True
    # end test_verify_config_dns_records

    @preposttest_wrapper
    def test_verify_config_phy_dev_phy_rtr(self):
        '''Test to verify Config->Physical Devices->Physical Routers
           1. Go to Configure->Physical Devices->Physical Routers.
           2. Get all the details of interface table from both WebUI and API server.
           3. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_phy_rtr_api_data(), \
                   'Physical Routers data verification failed'
        return True
    # end test_verify_config_phy_dev_phy_rtr

    @preposttest_wrapper
    def test_verify_config_services_service_templates(self):
        '''Test svc templates on config->Services->Service Templates page
        '''
        assert self.webui.verify_service_template_api_basic_data(), 'Svc templates config data verification failed'
        return True
    # end test_verify_config_services_service_templates

    @preposttest_wrapper
    def test_verify_config_services_service_instances(self):
        '''Test svc instances on config->Services->Service Instances page
        '''
        assert self.webui.verify_service_instance_api_basic_data(), 'Svc instances config data verification failed'
        return True
    # end test_verify_config_services_service_instances

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test_verify_config_network_route_table(self):
        '''
        Description: Test to verify Network Route Table on UI against Route Table on API
        Steps:
            1. On the Contrail UI, go to Config -> Networking -> Routing
            2. Get all the route table config details from the page
            3. Go to the API server and fetch all the route table config details
            4. Verify the WebUI details against the details from the API server
        Pass criteria:
            1. Step 4 above should pass
        '''
        assert self.webui.verify_route_table_api_basic_data(), 'Network Route Table data verification failed'
        return True
    # end test_verify_config_network_route_table

    @preposttest_wrapper
    def test_verify_config_route_aggregates(self):
        '''
        Description: Test to verify Route Aggregates on UI against Route Aggregates on API
        Steps:
            1. On the Contrail UI, go to Config -> Networking -> Routing -> Route Aggregates
            2. Get all the route aggregate config details from the page
            3. Go to the API server and fetch all the route aggregate config details
            4. Verify the WebUI details against the details from the API server
        Pass criteria:
            1. Step 4 above should pass
        '''
        assert self.webui.verify_route_aggregate_api_basic_data(), 'Route Aggregate data verification failed'
        return True
    # end test_verify_config_route_aggregates

    @preposttest_wrapper
    def test_verify_config_routing_policies(self):
        '''
        Description: Test to verify Routing Policies on UI against Routing Policies on API
        Steps:
            1. On the Contrail UI, go to Config -> Networking -> Routing -> Routing Policies
            2. Get all the routing policy config details from the page
            3. Go to the API server and fetch all the routing policy config details
            4. Verify the WebUI details against the details from the API server
        Pass criteria:
            1. Step 4 above should pass
        '''
        assert self.webui.verify_routing_policy_api_basic_data(), 'Routing Policy data verification failed'
        return True
    # end test_verify_config_routing_policies

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test_verify_config_forwarding_classes(self):
        '''
        Description: Test to verify Forwarding Classes on UI against Forwarding Classes on API
        Steps:
            1. On the Contrail UI, go to Configure -> Infrastructure -> Global Config -> Forwarding Classes
            2. Get all the forwarding class config details from the page
            3. Go to the API server and fetch all the forwarding class config details
            4. Verify the WebUI details against the details from the API server
        Pass criteria:
            1. Step 4 above should pass
        '''
        assert self.webui.verify_forwarding_class_api_basic_data(), 'Forwarding Class data verification failed'
        return True
    # end test_verify_config_forwarding_classes

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test_verify_config_qos_config(self):
        '''
        Description: Test to verify QoS config on UI against QoS config on API
        Steps:
            1. On the Contrail UI, go to Config -> Networking -> QoS
                In case of global config, go to Configure -> Infrastructure -> Global Config -> QoS
            2. Get all the qos config details from the page
            3. Go to the API server and fetch all the qos config details
            4. Verify the WebUI details against the details from the API server
        Pass criteria:
            1. Step 4 above should pass
        '''
        assert self.webui.verify_qos_config_api_basic_data(), 'QoS config data verification failed'
        return True
    # end test_verify_config_qos_config

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test_verify_config_svc_health_check(self):
        '''
        Description: Test to verify Service Health Check on UI against Health check on API
        Steps:
            1. On the Contrail UI, go to Config -> Networking -> Services -> Health Check
            2. Get all the health check config details from the page
            3. Go to the API server and fetch all the health check config details
            4. Verify the WebUI details against the details from the API server
        Pass criteria:
            1. Step 4 above should pass
        '''
        assert self.webui.verify_svc_health_check_api_basic_data(), 'Service Health Check data verification failed'
        return True
    # end test_verify_config_svc_health_check

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test_verify_config_services_bgpaas(self):
        '''
        Description: Test to verify BGP As a Service on UI against BGP As a Service on API
        Steps:
            1. On the Contrail UI, go to Configure -> Networking -> Services -> BGP as a Service
            2. Get all the bgppas config details from the page
            3. Go to the API server and fetch all the bgppas config details
            4. Verify the WebUI details against the details from the API server
        Pass criteria:
            1. Step 4 above should pass
        '''
        assert self.webui.verify_bgpaas_api_basic_data(), 'BGP As a Service data verification failed'
        return True
    # end test_verify_config_services_bgpaas

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test_verify_config_phy_dev_physical_interfaces(self):
        '''
        Description: Test to verify Physical Interface on UI against Physical Interfaces on API
        Steps:
            1. On the Contrail UI, go to Configure -> Physical Devices -> Interfaces
            2. Get all the physical interface config details from the page
            3. Go to the API server and fetch all the physical interface config details
            4. Verify the WebUI details against the details from the API server
        Pass criteria:
            1. Step 4 above should pass
        '''
        assert self.webui.verify_phy_int_api_basic_data(), 'Physical Interface data verification failed'
        return True
    # end test_verify_config_phy_dev_physical_interfaces

    @preposttest_wrapper
    def test_verify_config_infra_project_quotas(self):
        '''Test project quotas on config->Networking->Project Quotas page
        '''
        assert self.webui.verify_project_quotas(), 'Project Quotas config data verification failed'
        return True
    # end test_verify_config_infra_project_quotas

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test_verify_config_alarms_project_and_global(self):
        '''Test to verify alarms under project and Global
           1. Go to Configure->Alarms->Project.
           2. Get all the details of alarm from both WebUI and API server.
           3. Verify the WebUI details against API server details.
           4. Then Go to Configure->Global Config->Alarm Rules.
           5. Get all the details of alarm from both WebUI and API server.
           6. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 and 6 should pass
        '''
        assert self.webui.verify_alarms_api_data(topo.alarms_params), \
                   'Alarms data verification failed'
        return True
    # end test_verify_config_alarms_project_and_global

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test_verify_monitor_infra_control_node_basic_details(self):
        '''Test control node basic details on monitor->Infrastruture->Control Nodes->Node Details-> Basic view page
        '''
        assert self.webui.verify_bgp_routers_ops_basic_data(), 'Control node basic details verification failed'
        return True
    # end test_verify_monitor_infra_control_node_basic_details

    @preposttest_wrapper
    def test_verify_monitor_infra_control_node_advance_details(self):
        '''Test control node advance details on monitor->Infrastruture->Control Nodes->Node Details-> Advanced view page
        '''
        assert self.webui.verify_bgp_routers_ops_advance_data(), 'Control node advance details verification failed'
        return True
    # end test_verify_monitor_infra_control_node_advance_details

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test_verify_monitor_infra_vrouter_basic_details(self):
        '''Test virtual routers basic details on monitor->Infrastruture->Virtual Routers->Node Details-> Basic view page
        '''
        assert self.webui.verify_vrouter_ops_basic_data(),'Vrouter node basic details verification failed'
        return True
    # end test_verify_monitor_infra_vrouter_basic_details

    @preposttest_wrapper
    def test_verify_monitor_infra_vrouter_advance_details(self):
        '''Test virtual routers advance details on monitor->Infrastruture->Virtual Routers->Node Details-> Advanced view page
        '''
        assert self.webui.verify_vrouter_ops_advance_data(), 'Vrouter advance details verification failed'
        return True
    # end test_verify_monitor_infra_vrouter_advance_details

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test_verify_monitor_infra_analytics_node_basic_details(self):
        '''Test analytics node basic details on monitor->Infrastruture->Analytics Nodes->Node Details-> Basic view page
        '''
        assert self.webui.verify_analytics_nodes_ops_basic_data(),'Analytics nodes basic details verification failed'
        return True
    # end test_verify_monitor_infra_analytics_node_basic_details

    @preposttest_wrapper
    def test_verify_monitor_infra_analytics_node_advance_details(self):
        '''Test analytics node advance details on monitor->Infrastruture-> Analytics Nodes->Node Details-> Advanced view page
        '''
        assert self.webui.verify_analytics_nodes_ops_advance_data(), 'Analytics nodes advance details verification failed'
        return True
    # end test_verify_monitor_infra_analytics_node_advance_details

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test_verify_monitor_infra_config_node_basic_details(self):
        '''Test config node basic details on monitor->Infrastruture->Config Nodes->Node Details-> Basic view page
        '''
        assert self.webui.verify_config_nodes_ops_basic_data(), 'Config node basic details verification failed'
        return True
    # end test_verify_monitor_infra_config_node_basic_details

    @preposttest_wrapper
    def test_verify_monitor_infra_config_node_advance_details(self):
        '''Test config node advance details on monitor->Infrastruture->Config Nodes->Node Details-> Advanced view page
        '''
        assert self.webui.verify_config_nodes_ops_advance_data(), 'Config node advance details verification failed'
        return True
    # end test_config_node_advance_details

    @preposttest_wrapper
    def test_verify_monitor_infra_database_node_basic_details(self):
        '''
        Description: Test to verify database node basic detials on UI against details from OPS
        Steps:
            1. On the Contrail UI, go to Monitor -> Infrastructure -> Database Nodes -> Node details > Basic view page
            2. Get all the basic details from the page
            3. Go to the OPS server and fetch all the required details
            4. Verify the WebUI details against the details from the OPS server
        Pass criteria:
            1. Step 4 above should pass
        '''
        assert self.webui.verify_database_nodes_ops_basic_data(), 'Database node basic details verification failed'
        return True
    # end test_verify_monitor_infra_database_node_basic_details

    @preposttest_wrapper
    def test_verify_monitor_infra_database_node_advance_details(self):
        '''
        Description: Test to verify database node advanced details on UI against details from OPS
        Steps:
            1. On the Contrail UI, go to Monitor -> Infrastructure -> Database Nodes -> Node details > Advanced view page
            2. Get all the advanced details from the page
            3. Go to the OPS server and fetch all the required details
            4. Verify the WebUI details against the details from the OPS server
        Pass criteria:
            1. Step 4 above should pass
        '''
        assert self.webui.verify_database_nodes_ops_advance_data(), 'Database node advanced details verification failed'
        return True
    # end test_verify_monitor_infra_database_node_advanced_details

    @preposttest_wrapper
    def test_verify_monitor_infra_control_node_peer_details(self):
        '''
        Description: Test to verify control node peer details on UI against details from OPS
        Steps:
            1. On the Contrail UI, go to Monitor -> Infrastructure -> Control Nodes -> Node details > Peers
            2. Get all the peer details from the page
            3. Go to the OPS server and fetch all the required details
            4. Verify the WebUI details against the details from the OPS server
        Pass criteria:
            1. Step 4 above should pass
        '''
        assert self.webui.verify_control_nodes_ops_peer_data(), 'Control node peer details verification failed'
        return True
    # end test_verify_monitor_infra_control_node_peer_details

    @preposttest_wrapper
    def test_verify_monitor_networking_dashboard_networks(self):
        '''Test to verify networks on Monitor Networking dashboard
           1. Go to Monitor->Networking->Dasboard->Networks
           2. Get all the details of networks from both WebUI and OPS server.
           3. Verify the WebUI details against OPS server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_vn_ops_basic_data(option='dashboard'), \
                   'Network basic details verification failed on Monitor->Neworking->Dashboard->Networks'
        return True
    # end test_verify_monitor_networking_dashboard_networks

    @preposttest_wrapper
    def test_verify_monitor_networking_dashboard_networks_advance_details(self):
        '''Test to verify networks on Monitor Networking Dashboard Networks advance details
           1. Go to Monitor->Networking->Dashboard->Networks
           2. Get all the advanced details of Networks from both WebUI and OPS server.
           3. Verify the WebUI details against OPS server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_vn_ops_advance_data(option='dashboard'), \
                   'Networks advance details verification failed on \
                   Monitor->Networking->Dashboard->Networks'
        return True
    # end test_verify_monitor_networking_dashboard_networks_advance_details

    @preposttest_wrapper
    def test_verify_monitor_networking_interfaces(self):
        '''Test to verify networks on Monitor Networking Interfaces
           1. Go to Monitor->Networking->Interfaces
           2. Get all the details of interfaces from both WebUI and OPS server.
           3. Verify the WebUI details against OPS server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_vmi_ops_basic_data(), \
                   'Interface basic details verification failed on Monitor->Networking->Interfaces'
        return True
    # end test_verify_monitor_networking_interfaces

    @preposttest_wrapper
    def test_verify_monitor_networking_dashboard_interfaces(self):
        '''Test to verify networks on Monitor Networking Dashboard Interfaces
           1. Go to Monitor->Networking->Dashboard->Interfaces
           2. Get all the details of interfaces from both WebUI and OPS server.
           3. Verify the WebUI details against OPS server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_vmi_ops_basic_data(option='dashboard'), \
                   'Interface basic details verification failed on Monitor->Networking->Dashboard->Interfaces'
        return True
    # end test_verify_monitor_networking_dashboard_interfaces

    @preposttest_wrapper
    def test_verify_monitor_networking_interfaces_advance_details(self):
        '''Test to verify networks on Monitor Networking Interfaces Advance Details
           1. Go to Monitor->Networking->Interfaces
           2. Get all the advance details of interfaces from both WebUI and OPS server.
           3. Verify the WebUI details against OPS server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_vmi_ops_advance_data(), \
                   'Interface advance details verification failed on Monitor->Networking->Interfaces'
        return True
    # end test_verify_monitor_networking_interfaces_advance_details

    @preposttest_wrapper
    def test_verify_monitor_networking_dashboard_interfaces_advance_details(self):
        '''Test to verify networks on Monitor Networking Dashboard Interfaces Advance Details
           1. Go to Monitor->Networking->Dashboard->Interfaces
           2. Get all the advance details of interfaces from both WebUI and OPS server.
           3. Verify the WebUI details against OPS server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_vmi_ops_advance_data(option='dashboard'), \
                   'Interface advance details verification failed on \
                   Monitor->Networking->Dashboard->Interfaces'
        return True
    # end test_verify_monitor_networking_dashboard_interfaces_advance_details

    @preposttest_wrapper
    def test_verify_monitor_networking_projects(self):
        '''Test to verify networks on Monitor Networking Projects
           1. Go to Monitor->Networking->Projects
           2. Get all the details of interfaces from both WebUI and API server.
           3. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_project_api_basic_data(), \
                   'Projects basic details verification failed on Monitor->Networking->Projects'
        return True
    # end test_verify_monitor_networking_projects

    @preposttest_wrapper
    def test_verify_monitor_networking_projects_advance_details(self):
        '''Test to verify networks on Monitor Networking Projects advance details
           1. Go to Monitor->Networking->Projects
           2. Get all the advance details of interfaces from both WebUI and API server.
           3. Verify the WebUI details against API server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_project_api_advance_data(), \
                   'Projects advance details verification failed on Monitor->Networking->Projects'
        return True
    # end test_verify_monitor_networking_projects_advance_details

    @preposttest_wrapper
    def test_verify_monitor_networking_network_basic_details(self):
        '''Test network basic on monitor->Networking->Networks->Network Summary-> basic page
        '''
        assert self.webui.verify_vn_ops_basic_data(), 'Network basic details verification failed'
        return True
    # end test_network_basic_details

    @preposttest_wrapper
    def test_verify_monitor_networking_network_advance_details(self):
        '''Test network advance details on monitor->Networking->Networks->Network Summary-> Advanced page
        '''
        assert self.webui.verify_vn_ops_advance_data(), 'Network advance details verification failed'
        return True
    # end test_network_advance_details

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test_verify_monitor_infra_dashboard_details(self):
        '''Test dashboard details on monitor->Infra->Dashboard page
        '''
        assert self.webui.verify_dashboard_details(), 'Dashboard details verification failed'
        return True
    # end test_verify_monitor_infra_dashboard_details

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test_verify_monitor_networking_dashboard_instances(self):
        '''Test to verify instances on Monitor Networking dashboard
           1. Go to Monitor->Networking->Dasboard->Instances
           2. Get all the details of networks from both WebUI and OPS server.
           3. Verify the WebUI details against OPS server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_vm_ops_basic_data(option='dashboard'), \
                   'Instance basic details verification failed on Monitor->Neworking->Dashboard->Instances'
        return True
    # end test_verify_monitor_networking_dashboard_instances

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test_verify_monitor_networking_instance_basic_details(self):
        '''Test instance basic details on Monitor->Networking->Instances page
        '''
        assert self.webui.verify_vm_ops_basic_data(), 'Instance basic details verification failed'
        return True
    # end test_instance_basic_details

    @preposttest_wrapper
    def test_verify_monitor_networking_dashboard_instances_advance_details(self):
        '''Test to verify networks on Monitor Networking Dashboard Instances advance details
           1. Go to Monitor->Networking->Dashboard->Instances
           2. Get all the advanced details of instances from both WebUI and OPS server.
           3. Verify the WebUI details against OPS server details.

           Pass Criteria: Step 3 should pass
        '''
        assert self.webui.verify_vm_ops_advance_data(option='dashboard'), \
                   'Instances advance details verification failed on \
                   Monitor->Networking->Dashboard->Instances'
        return True
    # end test_verify_monitor_networking_dashboard_instances_advance_details

    @preposttest_wrapper
    def test_verify_monitor_networking_instance_advance_details(self):
        '''Test instance advance details on Monitor->Networking->Instances page
        '''
        assert self.webui.verify_vm_ops_advance_data(), 'Instance advance details verification failed'
        return True
    # end test_instance_advance_details

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test3_1_1_create_bgp_router(self):
        '''UI Config : Infrastructure -> BGP Router : Test BGP Router creation
           1. Go to Configure->Infrastructure->BGP Router.
           2. Click on create and enter the config details and save.

           Pass Criteria: Step 2 should pass without any error.
        '''
        assert self.res.setup_obj.create_bgp_router(), 'BGP Router creation failed'
        return True
    # end test3_1_1_create_bgp_router

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test3_1_2_create_link_local_service(self):
        '''Test to create Link Local service on UI
           1. Go to Configure->Infrastructure->LinkLocalService.
           2. Click on create and enter the config details and save.

           Pass Criteria: Step 2 should pass without any error
        '''
        assert self.res.setup_obj.create_link_local_service(), \
                                  'LinkLocalSerice creation failed'
        return True
    # end test3_1_2_create_link_local_service

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test3_1_3_create_virtual_router(self):
        '''Test to create virtual routers on UI
           1. Go to Configure->Infrastructure->VirtualRouter.
           2. Click on create and enter the config details and save.

           Pass Criteria: Step 2 should pass without any error
        '''
        assert self.res.setup_obj.create_virtual_router(), \
                                  'Virtual Router creation failed'
        return True
    # end test3_1_3_create_virtual_router

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test3_1_4_create_service_appliance_set(self):
        '''Test to create service appliance set on UI
           1. Go to Configure->Infrastructure->Service Appliance Sets.
           2. Click on create and enter the config details and save.

           Pass Criteria: Step 2 should pass without any error
        '''
        assert self.res.setup_obj.create_service_appliance_set(), \
                                  'Service Appliance Set creation failed'
        return True
    # end test3_1_4_create_service_appliance_set

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test3_1_5_create_service_appliances(self):
        '''Test to create service appliances on UI
           1. Go to Configure->Infrastructure->Service Appliances.
           2. Click on create and enter the config details and save.

           Pass Criteria: Step 2 should pass without any error
        '''
        assert self.res.setup_obj.create_service_appliances(), \
                                  'Service Appliances creation failed'
        return True
    # end test3_1_5_create_service_appliances

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test3_1_6_create_alarms_in_project_and_in_global(self):
        '''Test to create alarms in both project wise and global wise on UI
           1. Go to Configure->Alarms->Project.
           2. Click on create and enter the config details and save.
           3. Go to Infrastructure->Global Config->Alarm Rules.
           4. Click on create and enter the config details and save.

           Pass Criteria: Both Step 2 and 4 should pass without any error
        '''
        assert self.res.setup_obj.create_alarms(), 'Alarm creation failed'
        return True
    # end test3_1_6_create_alarms_in_project_and_in_global

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test3_1_7_create_rbac(self):
        '''Test to create rbac in both global, domain and project wise on UI
           1. Go to Configure->Infrastructure->RBAC->Global.
           2. Click on create and enter the config details and save.
           3. Go to Configure->Infrastructure->RBAC->Domain.
           4. Click on create and enter the config details and save.
           5. Go to Configure->Infrastructure->RBAC->Project.
           6. Click on create and enter the config details and save.

           Pass Criteria: Both Step 2, 4 and 6 should pass without any error
        '''
        assert self.res.setup_obj.create_rbac(), 'RBAC creation failed'
        return True
    # end test3_1_7_create_rbac

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test3_1_8_create_ovsdb_tor_agent(self):
        '''Test to create ovsdb managed tor agent on UI
           1. Go to Configure->Physical Devices->Physical Routers->OVSDB Managed TOR.
           2. Click on create and enter the config details and save.

           Pass Criteria: Step 2 should pass without any error
        '''
        assert self.res.setup_obj.create_ovsdb_tor_agent(), \
                   'OVSDB Managed ToR creation failed'
        return True
    # end test3_1_8_create_ovsdb_tor_agent

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test3_1_9_create_netconf_phy_router(self):
        '''Test to create netconf managed physical router on UI
           1. Go to Configure->Physical Devices->Physical Routers->Netconf Managed
              Physical Router.
           2. Click on create and enter the config details and save.

           Pass Criteria: Step 2 should pass without any error
        '''
        assert self.res.setup_obj.create_netconf_prouter(), \
                   'Netconf Managed Physical Router creation failed'
        return True
    # end test3_1_9_create_netconf_phy_router

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test3_2_1_create_vcpe_router(self):
        '''Test to create vcpe router on UI
           1. Go to Configure->Physical Devices->Physical Routers->VCPE Router.
           2. Click on create and enter the config details and save.

           Pass Criteria: Step 2 should pass without any error
        '''
        assert self.res.setup_obj.create_vcpe_router(), \
                   'VCPE Router creation failed'
        return True
    # end test3_2_1_create_vcpe_router

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test3_2_2_create_log_statistic(self):
        '''Test to create log statistic on UI
           1. Go to Configure->Global Config->Log statistic.
           2. Click on create and enter the config details and save.

           Pass Criteria: Step 2 should pass without any error
        '''
        assert self.res.setup_obj.create_log_statistic(), \
                   'Log Statistic creation failed'
        return True
    # end test3_2_2_create_log_statistic

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test3_2_3_create_flow_aging(self):
        '''Test to create Flow Aging on UI
           1. Go to Configure->Global Config->Flow Aging.
           2. Click on create and enter the config details and save.

           Pass Criteria: Step 2 should pass without any error
        '''
        assert self.res.setup_obj.create_flow_aging(), \
                   'Flow Aging creation failed'
        return True
    # end test3_2_3_create_flow_aging

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test3_2_4_create_interface_route_table(self):
        '''Test to create interface route table on UI
           1. Go to Configure->Networking->Routing->Interface Route Table.
           2. Click on create and enter the config details and save.

           Pass Criteria: Step 2 should pass without any error
        '''
        assert self.res.setup_obj.create_interface_route_table(), \
                   'Interface Route Table creation failed'
        return True
    # end test3_2_4_create_interface_route_table

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test3_2_5_attach_intf_route_table_to_port(self):
        '''
        Description: Test to attach Interface Route Table to Port on UI
        Steps:
            1. On the Contrail UI, go to Config -> Networking -> Ports
            2. Click on edit on one of the Ports
            3. Click on 'Advanced Options', attach Interface Route table
               as static route
            4. Click on 'Save'
        Pass criteria:
            1. Steps 3 and 4 above should pass
        '''
        assert self.res.setup_obj.attach_intf_route_table(), \
                   'Attaching of Interface Route Table to Port failed'
        return True
    # end test_attach_intf_route_table_to_port

    @preposttest_wrapper
    def test3_1_edit_net_without_change(self):
        '''Test to edit the existing network without changing anything
           1. Go to Configure->Networking->Networks. Then select any of the vn and
              click the edit button
           2. Click the save button without changing anything
           3. Check the UUID in UI page and API and OPS

           Pass Criteria: UUID shouldn't be changed after editing
        '''
        result = True
        opt_list = []
        self.webui.logger.debug("Step 1 : Get the uuid before editing")
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        vn_name = self.webui_common.get_vn_detail_ui('Display Name')
        self.webui.logger.debug("UUID before editing " + uuid)
        self.webui.logger.debug("Step 2 : Verify WebUI before editing")
        if not self.webui.verify_vn_after_edit_ui('UUID', uuid, opt_list):
            self.webui.logger.debug("Virtual networks config data verification in WebUI failed")
            result = result and False
        self.webui.logger.debug("Step 3 : Verify API server before editing")
        if not self.webui.verify_vn_after_edit_api('UUID', uuid, uuid, opt_list):
            self.webui.logger.debug("Virtual networks config data verification in API failed")
            result = result and False
        self.webui.logger.debug("Step 4 : Verify OPS server before editing")
        if not self.webui.verify_vn_after_edit_ops('UUID', vn_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Edit the VN without changing anything")
        if not self.webui_common.edit_without_change('networks'):
            self.webui.logger.debug('Editing Network failed')
            result = result and False
        self.webui.logger.debug("Step 6 : Verify WebUI server after editing")
        if not self.webui.verify_vn_after_edit_ui('UUID', uuid, opt_list):
            self.webui.logger.debug("Virtual networks config data verification in UI failed")
            result = result and False
        self.webui.logger.debug("Step 7 : Verify API server after editing")
        if not self.webui.verify_vn_after_edit_api('UUID', uuid, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 8 : Verify OPS server after editing")
        if not self.webui.verify_vn_after_edit_ops('UUID', vn_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        return result
    #end test3_1_edit_vn_witout_change

    @preposttest_wrapper
    def test3_2_edit_net_disp_name_change(self):
        ''' Test to edit the existing network by changing VN display name
            1. Go to Configure->Networking->Networks. Then select any of the vn and
               click the edit button
            2. Change the Display name and click the save button
            3. Check that new display name got reflected in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        self.webui.logger.debug("Step 1 : Get the display name of the VN before editing")
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        opt_list = [topo.vn_disp_name]
        result = True
        if self.vn_disp_name:
            self.webui.logger.debug("Getting VN display name is successful and \
                                     the VN name is %s" %(self.vn_disp_name))
            self.webui.logger.debug("Step 2 : Editing the VN by the name")
            if not self.webui_common.edit_vn_disp_name_change(topo.vn_disp_name):
                self.webui.logger.debug("Editing network failed")
                result = result and False
            self.webui.logger.debug("Step 3 : Verify WebUI server after editing")
            if not self.webui.verify_vn_after_edit_ui('Display Name', \
                                                      topo.vn_disp_name, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in UI failed')
                result = result and False
            self.webui.logger.debug("Step 4 : Verify API server after editing")
            if not self.webui.verify_vn_after_edit_api('Display Name', topo.vn_disp_name, \
                                                       uuid, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in API failed')
                result = result and False
            self.webui.logger.debug("Step 5 : Verify OPS server after editing")
            if not self.webui.verify_vn_after_edit_ops('Display Name', \
                                                        self.vn_disp_name, uuid, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in OPS failed')
                result = result and False
            self.webui.logger.debug("Step 6 : Editing the VN with the previous vn name")
            if not self.webui_common.edit_vn_disp_name_change(self.vn_disp_name):
                self.webui.logger.debug('Editing Network failed')
                result = result and False
            opt_list = [self.vn_disp_name]
            self.webui.logger.debug("Step 7 : Verify WebUI after editing with previous vn name")
            if not self.webui.verify_vn_after_edit_ui('Display Name', self.vn_disp_name, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in UI failed')
                result = result and False
            self.webui.logger.debug("Step 8 : Verifying the VN after editing \
                                    previous vn name in API")
            if not self.webui.verify_vn_after_edit_api('Display Name', self.vn_disp_name, \
                                                       uuid, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in API failed')
                result = result and False
            self.webui.logger.debug("Step 9 : Verify OPS server after editing with previous name")
            if not self.webui.verify_vn_after_edit_ops('Display Name', \
                                                        self.vn_disp_name, uuid, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in OPS failed')
                result = result and False
        else:
            self.webui.logger.error("Not able to get the display name. \
                                    So Editing Vn is not possible")
            result = result and False
        return result
    #end test3_2_edit_vn_witout_change

    @preposttest_wrapper
    def test3_3_edit_net_disp_name_change_with_spl_char(self):
        ''' Test to edit the existing network by changing VN display name with special character
            1. Go to Configure->Networking->Networks. Then select any of the vn and
               click the edit button
            2. Change the Display name with special character and click the save button
            3. Check that new display name got reflected in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        opt_list = [topo.vn_disp_name_spl_char_ops]
        result = True
        self.webui.logger.debug("Step 1 : Get the display name of the VN before editing")
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        if self.vn_disp_name:
            self.webui.logger.debug("Getting VN display name is successful \
                                     and the VN name is %s" %(self.vn_disp_name))
            self.webui.logger.debug("Step 2 : Editing the VN by the name with special characters")
            if not self.webui_common.edit_vn_disp_name_change(topo.vn_disp_name_spl_char):
                self.webui.logger.debug('Editing Network failed')
                result = result and False
            self.webui.logger.debug("Step 3 : Verify WebUI server after editing")
            if not self.webui.verify_vn_after_edit_ui('Display Name', topo.vn_disp_name_spl_char, \
                                                      opt_list):
                self.webui.logger.debug('Virtual networks config data verification in UI failed')
                result = result and False
            self.webui.logger.debug("Step 4 : Verify API server after editing")
            if not self.webui.verify_vn_after_edit_api('Display Name', \
                                                        topo.vn_disp_name_spl_char, uuid, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in API failed')
                result = result and False
            self.webui.logger.debug("Step 5 : Verify OPS server after editing")
            if not self.webui.verify_vn_after_edit_ops('Display Name', self.vn_disp_name, \
                                                        uuid, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in OPS failed')
                result = result and False
            self.webui.logger.debug("Step 6 : Editing the VN with the previous vn name")
            if not self.webui_common.edit_vn_disp_name_change(self.vn_disp_name):
                self.webui.logger.debug('Editing Network failed')
                result = result and False
            self.webui.logger.debug("Step 7 : Verify WebUI after editing with previous vn name")
            opt_list = [self.vn_disp_name]
            if not self.webui.verify_vn_after_edit_ui('Display Name', self.vn_disp_name, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in UI failed')
                result = result and False
            self.webui.logger.debug("Step 8 : Verifying the VN after editing previous \
                                    vn name in API")
            if not self.webui.verify_vn_after_edit_api('Display Name', self.vn_disp_name, \
                                                       uuid, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in API failed')
            self.webui.logger.debug("Step 9 : Verify OPS server after editing")
            if not self.webui.verify_vn_after_edit_ops('Display Name', \
                                                        self.vn_disp_name, uuid, opt_list):
                self.webui.logger.debug('Virtual networks config data verification in OPS failed')
                result = result and False
        else:
            self.webui.logger.error("Not able to get the display name. \
                                    So Editing Vn is not possible")
            result = result and False
        return result
    #end test3_3_edit_vn_witout_change

    @preposttest_wrapper
    def test3_4_edit_net_by_add_policy(self):
        ''' Test to edit the existing network by policy
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Attach one policy for the vn and save.
            3. Check that attached policy is there in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        self.webui.logger.debug("Step 1 : Attach policy to the VN")
        pol_name = ""
        pol_name = self.webui_common.add_vn_with_policy(pol_name)
        result = True
        opt_list = [pol_name]
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        self.vn_policy = str(self.webui_common.get_vn_detail_ui('Policy'))
        self.webui.logger.debug("Step 2 : Verify the VN for the attached policy \
                                through WebUI server")
        if not self.webui.verify_vn_after_edit_ui('Policy', self.vn_policy, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify the VN for the attached policy through API server")
        if not self.webui.verify_vn_after_edit_api("Policy", "Policy", uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for the attached policy through OPS server")
        if not self.webui.verify_vn_after_edit_ops('Policy', self.vn_disp_name, \
                                                   self.vn_disp_name, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the policy which is attached")
        if not self.webui_common.del_vn_with_policy(pol_name):
            self.webui.logger.debug('Editing network with policy failed')
            result = result and False
        return result
    #end test3_4_edit_net_policy

    @preposttest_wrapper
    def test3_5_edit_net_by_add_subnet(self):
        ''' Test to edit the existing network by subnet
            1. Go to configure->Networking->Networks. Create a new VN
            2. Edit the created VN and add subnet with all options and save
            3. Check that subnet with all options got reflected in WebUI,API and OPS.
            4. Remove the subnet and and add it back with subnet-gate option.
            5. Check the same got updated in WebUI, API and OPs.
               Similarly doing for subnet-dns and subnet-dhcp

            Pass Criteria : Step 3,4,5 should pass
        '''
        opt_list = [topo.subnet_edit, topo.mask, topo.subnet_sip, topo.subnet_eip,
                    topo.subnet_dns_ip, topo.subnet_gate_ip, topo.subnet_default_gate_ip]
        result = True
        if self.webui_common.click_on_create('Network', 'networks', topo.vn_disp_name,
                                            prj_name=self.webui.project_name_input):
            self.webui_common.wait_till_ajax_done(self.browser, wait=3)
            self.webui_common.send_keys(topo.vn_disp_name, 'display_name', 'name')
            self.webui_common.wait_till_ajax_done(self.browser, wait=3)
            self.webui_common.click_element('configure-networkbtn1')
            self.webui_common.wait_till_ajax_done(self.browser, wait=5)
            verify_list = ['Subnet', 'Subnet-gate', 'Subnet-dns', 'Subnet-dhcp']
            for subnet_type in verify_list:
                if subnet_type == 'Subnet':
                    str1 = 'all'
                else:
                    str1 = subnet_type + 'disabled'
                self.webui.logger.debug("Step 1 - " + subnet_type + \
                                        ": Add subnet with " + str1 + "options")
                ind = self.webui_common.edit_vn_with_subnet(subnet_type, topo.subnet_edit + \
                                                             "/" + topo.mask, \
                                                             topo.subnet_sip + "-" + \
                                                             topo.subnet_eip, \
                                                             topo.subnet_gate_ip, topo.vn_disp_name)
                if not ind:
                    self.webui.logger.debug('Editing network with subnet failed')
                    result = result and False
                uuid = self.webui_common.get_vn_detail_ui('UUID', index=ind)
                self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name', index=ind)
                subnet = self.webui_common.get_vn_detail_ui('Subnet', index=ind)
                self.webui.logger.debug("Step 2 - " + subnet_type + \
                                        ": Verify the VN for subnet in WebUI")
                if not self.webui.verify_vn_after_edit_ui(subnet_type, subnet, opt_list,
                                                         index=ind):
                    self.webui.logger.debug('Virtual networks config data \
                                             verification in UI failed')
                    result = result and False
                self.webui.logger.debug("Step 3 - " + subnet_type + \
                                        ": Verify the VN for subnet in API server")
                if not self.webui.verify_vn_after_edit_api(subnet_type, subnet, uuid, opt_list):
                    self.webui.logger.debug('Virtual networks config data verification \
                                            in API failed')
                    result = result and False
                self.webui.logger.debug("Step 4 - " + subnet_type + \
                                        ": Verify the VN for subnet in OPS server")
                if not self.webui.verify_vn_after_edit_ops(subnet_type, self.vn_disp_name, \
                                                           uuid, opt_list):
                    self.webui.logger.debug('Virtual networks config data verification \
                                            in OPS failed')
                    result = result and False
                self.webui.logger.debug("Step 5 : Remove the subnet which is added")
                if not self.webui_common.del_vn_with_subnet(topo.vn_disp_name):
                    self.webui.logger.debug('Editing network with subnet failed')
                    result = result and False
        self.webui.logger.debug("Step 6 : Remove the VN which is added")
        if not self.webui_common.edit_remove_option("Networks", 'remove', \
                                                   display_name=topo.vn_disp_name):
            self.webui.logger.debug('Editing network with advanced options is failed')
            result = result and False
        return result
    #end test3_5_edit_net_subnet

    @preposttest_wrapper
    def test3_6_edit_net_host_opt(self):
        ''' Test to edit the existing network by Host routes
            1. Go to Configure->Networking->Networks.
               Then select any of the vn and click the edit button
            2. Add Host route with route prefix and next hop and save.
            3. Check that host route is added in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        opt_list = [topo.host_prefix, topo.host_nexthop]
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        self.webui.logger.debug("Step 1 : Add Host Route under VN")
        if not self.webui_common.edit_vn_with_host_route('add', 'pos', topo.host_prefix, \
                                                         topo.host_nexthop):
            self.webui.logger.debug('Editing network with host routes failed')
            result = result and False
        host_route = self.webui_common.get_vn_detail_ui('Host Route')
        self.webui.logger.debug("Step 2 : Verify the host route in WebUI")
        if not self.webui.verify_vn_after_edit_ui('Host Route', host_route, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify the host route in API server")
        if not self.webui.verify_vn_after_edit_api('Host Route', host_route, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for host route in OPS server")
        if not self.webui.verify_vn_after_edit_ops('Host Route', self.vn_disp_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the Host Route which is added")
        if not self.webui_common.edit_vn_with_host_route('remove', 'pos', \
                                                         topo.host_prefix, topo.host_nexthop):
            self.webui.logger.debug('Editing network with host routes failed')
            result = result and False
        return result
    # end test3_6_edit_net_host_opt

    @preposttest_wrapper
    def test5_1_edit_net_host_opt_neg(self):
        ''' Test to edit the existing network by Invalid Host routes
            1. Go to Configure->Networking->Networks.
               Then select any of the vn and click the edit button
            2. Add Host route with invalid route prefix and invalid next hop and save it.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.webui.logger.debug("Step 1 : Add Host Route under VN")
        assert self.webui_common.edit_vn_with_host_route('add', 'neg', topo.dns_ip, \
                                                         topo.host_nexthop), \
                                                         'Editing network with host routes failed \
                                                         as expected for negative scenario'
    # end test5_1_edit_net_host_opt_neg

    @preposttest_wrapper
    def test3_7_edit_net_adv_opt(self):
        ''' Test to edit the existing network by Advanced Options
            1. Go to Configure->Networking->Networks.
               Then select any of the vn and click the edit button
            2. Select all the options under advanced option and save.
            3. Check that all the options under advanced option got reflected in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        opt_list = [topo.vlan_id, topo.phy_net, topo.subnet_adv_option, topo.vn_disp_name]
        self.webui.logger.debug("Step 1 : Add advanced options under VN")
        index = self.webui_common.edit_vn_with_adv_option(1, 'pos-phy', opt_list)
        if not index:
            self.webui.logger.debug('Editing network with advanced options is failed')
            result = result and False
        uuid = self.webui_common.get_vn_detail_ui('UUID', index=index)
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name', index=index)
        adv_option = self.webui_common.get_vn_detail_ui('Adv Option', index=index)
        self.webui.logger.debug("Step 2 : Verify the advanced option in WebUI")
        if not self.webui.verify_vn_after_edit_ui('Adv Option', adv_option, opt_list, index=index):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify advanced option in API server")
        if not self.webui.verify_vn_after_edit_api('Adv Option', adv_option, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        if not self.webui.verify_vn_after_edit_ops('Adv Option', self.vn_disp_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the VN which is added")
        if not self.webui_common.edit_remove_option("Networks", 'remove', \
                                                   display_name=topo.vn_disp_name):
            self.webui.logger.debug('Editing network with advanced options is failed')
            result = result and False
        return result
    # end test3_7_edit_net_adv_opt

    @preposttest_wrapper
    def test5_2_edit_net_adv_opt_neg(self):
        ''' Test to edit the existing network by Invalid physical network
            and invalid vlan id under Advanced option
            1. Go to Configure->Networking->Networks.
               Then select any of the vn and click the edit button
            2. Select all the options under advanced option and give
               invalid physical network and invalid vlan and save it.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        self.webui.logger.debug("Step 1 : Add advanced options under VN")
        opt_list = [topo.vlan_id, topo.phy_net, topo.subnet_adv_option, topo.vn_disp_name]
        index = self.webui_common.edit_vn_with_adv_option(1, 'pos-phy', opt_list)
        if not index:
            self.webui.logger.debug('Editing network with advanced options is failed')
            result = result and False
        self.webui.logger.debug("Step 2 : Edit the vn using advanced options")
        opt_list_invalid = [topo.invalid_vlan_id, topo.phy_net, topo.subnet_edit, topo.vn_disp_name]
        if not self.webui_common.edit_vn_with_adv_option(0, 'neg-phy', opt_list_invalid):
            self.webui.logger.debug('Editing network with advanced option is failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Remove the VN which is added")
        if not self.webui_common.edit_remove_option("Networks", 'remove', \
                                                   display_name=topo.vn_disp_name):
            self.webui.logger.debug('Editing network with advanced options is failed')
            result = result and False
        return result
    # end test5_2_edit_net_adv_opt_neg

    @preposttest_wrapper
    def test3_8_edit_net_dns(self):
        ''' Test to edit the existing network by DNS
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add dns IP under DNS Server.
            3. Check that dns Ip got added in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        opt_list = [topo.dns_ip]
        self.webui.logger.debug("Step 1 : Add dns server IP under VN")
        if not self.webui_common.edit_vn_with_dns('add', 'pos', topo.dns_ip):
            self.webui.logger.debug('Editing network with dns is failed')
            result = result and False
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        dns = self.webui_common.get_vn_detail_ui('DNS')
        self.webui.logger.debug("Step 2 : Verify the DNS server IP in WebUI")
        if not self.webui.verify_vn_after_edit_ui('DNS', dns, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify DNS server IP in API server")
        if not self.webui.verify_vn_after_edit_api('DNS', dns, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for DNS server IP in OPS server")
        if not self.webui.verify_vn_after_edit_ops('DNS', self.vn_disp_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the VN which is added")
        if not self.webui_common.edit_vn_with_dns('remove', 'pos', topo.dns_ip):
            self.webui.logger.debug('Editing network with dns is failed')
            result = result and False
        return result
    # end test3_8_edit_net_dns

    @preposttest_wrapper
    def test3_9_edit_net_dns_neg(self):
        ''' Test to edit the existing network by DNS
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add Invalid dns IP under DNS Server.
            3. WebUI should thrown an error message while saving

            Pass Criteria : Step 3 should pass
        '''
        self.webui.logger.debug("Step 1 : Add dns server IP under VN")
        assert self.webui_common.edit_vn_with_dns('add', 'neg', topo.invalid_dns_ip), \
                                                  'Editing network with dns is failed'
    # end test3_9_edit_dns_neg

    @preposttest_wrapper
    def test4_2_edit_net_route_target_asn_num(self):
        ''' Test to edit the existing network by Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add ASN number and Target number under Route Target.
            3. Check the asn and target number got added in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        opt_list = [topo.asn_num, topo.target_num, topo.asn_ip]
        self.webui.logger.debug("Step 1 : Add Route Target under VN")
        if not self.webui_common.edit_vn_with_route_target('add', 'pos', 'RT', \
                                                           topo.asn_num, topo.target_num):
            self.webui.logger.debug('Editing network with Route target failed')
            result = result and False
        self.webui_common.wait_till_ajax_done(self.browser)
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        rt = self.webui_common.get_vn_detail_ui('RT')
        self.webui.logger.debug("Step 2 : Verify the Route Target in WebUI")
        if not self.webui.verify_vn_after_edit_ui('RT', rt, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify advanced option in API server")
        if not self.webui.verify_vn_after_edit_api('RT', rt, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for n in OPS server")
        if not self.webui.verify_vn_after_edit_ops('RT', self.vn_disp_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the Route Target which is added")
        if not self.webui_common.edit_vn_with_route_target('remove', 'pos', 'RT', \
                                                           topo.asn_num, topo.target_num):
            self.webui.logger.debug('Editing network with Route Target is failed')
            result = result and False
        return result
    # end test4_2_edit_net_route_target_asn_num

    @preposttest_wrapper
    def test4_3_edit_net_route_target_asn_ip(self):
        ''' Test to edit the existing network by Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add IP as asn and Target number under Route Target.
            3. Check the asn ip and target number got added in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        opt_list = [topo.asn_num, topo.target_num, topo.asn_ip]
        self.webui.logger.debug("Step 1 : Add Route Target under VN")
        if not self.webui_common.edit_vn_with_route_target('add', 'pos', 'RT', \
                                                           topo.asn_ip, topo.target_num):
            self.webui.logger.debug('Editing network with Route target failed')
            result = result and False
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        rt = self.webui_common.get_vn_detail_ui('RT')
        self.webui.logger.debug("Step 2 : Verify the advanced option in WebUI")
        if not self.webui.verify_vn_after_edit_ui('RT', rt, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify advanced option in API server")
        if not self.webui.verify_vn_after_edit_api('RT', rt, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        if not self.webui.verify_vn_after_edit_ops('RT', self.vn_disp_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the Route Target which is added")
        if not self.webui_common.edit_vn_with_route_target('remove', 'pos', 'RT', \
                                                           topo.asn_ip, topo.target_num):
            self.webui.logger.debug('Editing network with Route Target is failed')
            result = result and False
        return result
    # end test4_3_edit_net_route_target_asn_ip

    @preposttest_wrapper
    def test5_3_edit_net_route_target_neg_asn_ip(self):
        ''' Test to edit the existing network by Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add invalid IP as asn and invalid Target number under Route Target.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        self.webui.logger.debug("Step 1 : Add Route Target under VN")
        assert self.webui_common.edit_vn_with_route_target('add', 'neg', 'RT', \
                                                           topo.invalid_asn_ip, \
                                                           topo.invalid_target_num), \
                                                           'Editing network with Route \
                                                           target failed'
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
    # end test5_3_edit_net_route_target_neg_asn_ip

    @preposttest_wrapper
    def test5_4_edit_net_route_target_neg_asn_num(self):
        ''' Test to edit the existing network by Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add invalid asn number and invalid Target number under Route Target.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        self.webui.logger.debug("Step 1 : Add Route Target under VN")
        assert self.webui_common.edit_vn_with_route_target('add', 'neg', 'RT', \
                                                           topo.invalid_asn_num, \
                                                           topo.invalid_target_num), \
                                                           'Editing network with \
                                                           Route target failed'
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
    # end test5_4_edit_net_route_target_neg_asn_num

    @preposttest_wrapper
    def test5_5_edit_net_exp_route_target_asn_num(self):
        ''' Test to edit the existing network by Export Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add asn number and Target number under Export Route Target.
            3. Check the asn number and target number got added in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        opt_list = [topo.asn_num, topo.target_num, topo.asn_ip]
        self.webui.logger.debug("Step 1 : Add Export Route Target under VN")
        if not self.webui_common.edit_vn_with_route_target('add', 'pos', 'ERT', \
                                                           topo.asn_num, topo.target_num):
            self.webui.logger.debug('Editing network with Export Route target failed')
            result = result and False
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        ert = self.webui_common.get_vn_detail_ui('ERT')
        self.webui.logger.debug("Step 2 : Verify the advanced option in WebUI")
        if not self.webui.verify_vn_after_edit_ui('ERT', ert, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify advanced option in API server")
        if not self.webui.verify_vn_after_edit_api('ERT', ert, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        if not self.webui.verify_vn_after_edit_ops('ERT', self.vn_disp_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the Route Target which is added")
        if not self.webui_common.edit_vn_with_route_target('remove', 'pos', 'ERT', \
                                                           topo.asn_num, topo.target_num):
            self.webui.logger.debug('Editing network with Export Route Target is failed')
            result = result and False
        return result
    # end test5_5_edit_net_exp_route_target_asn_num

    @preposttest_wrapper
    def test4_4_edit_net_exp_route_target_asn_ip(self):
        ''' Test to edit the existing network by Export Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add IP as asn and Target number under Export Route Target.
            3. Check the asn ip and target number got added in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        opt_list = [topo.asn_num, topo.target_num, topo.asn_ip]
        self.webui.logger.debug("Step 1 : Add Export Route Target under VN")
        if not self.webui_common.edit_vn_with_route_target('add', 'pos', 'ERT', \
                                                           topo.asn_ip, topo.target_num):
            self.webui.logger.debug('Editing network with Export Route target failed')
            result = result and False
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        ert = self.webui_common.get_vn_detail_ui('ERT')
        self.webui.logger.debug("Step 2 : Verify the advanced option in WebUI")
        if not self.webui.verify_vn_after_edit_ui('ERT', ert, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify advanced option in API server")
        if not self.webui.verify_vn_after_edit_api('ERT', ert, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        if not self.webui.verify_vn_after_edit_ops('ERT', self.vn_disp_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the Export Route which is added")
        if not self.webui_common.edit_vn_with_route_target('remove', 'pos', 'ERT', \
                                                           topo.asn_ip, topo.target_num):
            self.webui.logger.debug('Editing network with Export Route Target is failed')
            result = result and False
        return result
    # end test4_4_edit_net_exp_route_target_asn_ip

    @preposttest_wrapper
    def test5_6_edit_net_exp_route_target_neg_asn_ip(self):
        ''' Test to edit the existing network by Export Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add invalid IP as asn and invalid Target number under Export Route Target.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        self.webui.logger.debug("Step 1 : Add Export Route Target under VN")
        assert self.webui_common.edit_vn_with_route_target('add', 'neg', 'ERT', \
                                                           topo.invalid_asn_ip, \
                                                           topo.invalid_target_num), \
                                                           'Editing network with \
                                                           Export Route target failed'
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
    # end test5_6_edit_net_exp_route_target_neg_asn_ip

    @preposttest_wrapper
    def test5_8_edit_net_exp_route_target_neg_asn_num(self):
        ''' Test to edit the existing network by Export Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add invalid asn number and invalid Export Target number under Route Target.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        self.webui.logger.debug("Step 1 : Add Export Route Target under VN")
        assert self.webui_common.edit_vn_with_route_target('add', 'neg', 'ERT', \
                                                           topo.invalid_asn_num, \
                                                           topo.invalid_target_num), \
                                                           'Editing network with \
                                                           Export Route target failed'
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
    # end test5_8_edit_net_exp_route_target_neg_asn_num

    @preposttest_wrapper
    def test4_5_edit_net_imp_route_target_asn_num(self):
        ''' Test to edit the existing network by Import Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add asn and Target number under Import Route Target.
            3. Check the asn and target number got added in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        global count
        count  = count + 1
        result = True
        opt_list = [topo.asn_num, topo.target_num, topo.asn_ip]
        self.webui.logger.debug("Step 1 : Add Import Route Target under VN")
        if not self.webui_common.edit_vn_with_route_target('add', 'pos', 'IRT', \
                                                           topo.asn_num, topo.target_num, \
                                                           count=count):
            self.webui.logger.debug('Editing network with import Route target failed')
            result = result and False
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        irt = self.webui_common.get_vn_detail_ui('IRT')
        self.webui.logger.debug("Step 2 : Verify the advanced option in WebUI")
        if not self.webui.verify_vn_after_edit_ui('IRT', irt, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify advanced option in API server")
        if not self.webui.verify_vn_after_edit_api('IRT', irt, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        if not self.webui.verify_vn_after_edit_ops('IRT', self.vn_disp_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the Import Route Target which is added")
        if not self.webui_common.edit_vn_with_route_target('remove', 'pos', \
                                                           'IRT', topo.asn_ip, topo.target_num):
            self.webui.logger.debug('Editing network with Import Route Target is failed')
            result = result and False
        return result
    # end test4_5_edit_net_imp_route_target_asn_num

    @test.attr(type=['ui_sanity'])
    @preposttest_wrapper
    def test4_6_edit_net_imp_route_target_asn_ip(self):
        ''' Test to edit the existing network by Import Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add IP as asn and Target number under Import Route Target.
            3. Check the asn ip and target number got added in WebUI,API and OPS.

            Pass Criteria : Step 3 should pass
        '''
        global count
        count = count + 1
        result = True
        opt_list = [topo.asn_num, topo.target_num, topo.asn_ip]
        self.webui.logger.debug("Step 1 : Add Import Route Target under VN")
        self.webui_common.wait_till_ajax_done(self.browser)
        if not self.webui_common.edit_vn_with_route_target('add', 'pos', 'IRT', \
                                                           topo.asn_ip, topo.target_num, \
                                                           count=count):
            self.webui.logger.debug('Editing network with Import Route target failed')
            result = result and False
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
        uuid = self.webui_common.get_vn_detail_ui('UUID')
        self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name')
        irt = self.webui_common.get_vn_detail_ui('IRT')
        self.webui.logger.debug("Step 2 : Verify the advanced option in WebUI")
        if not self.webui.verify_vn_after_edit_ui('IRT', irt, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in UI failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify advanced option in API server")
        if not self.webui.verify_vn_after_edit_api('IRT', irt, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in API failed')
            result = result and False
        self.webui.logger.debug("Step 4 : Verify the VN for advancded option in OPS server")
        if not self.webui.verify_vn_after_edit_ops('IRT', self.vn_disp_name, uuid, opt_list):
            self.webui.logger.debug('Virtual networks config data verification in OPS failed')
            result = result and False
        self.webui.logger.debug("Step 5 : Remove the Import Route Target which is added")
        if not self.webui_common.edit_vn_with_route_target('remove', 'pos', 'IRT', \
                                                           topo.asn_ip, topo.target_num):
            self.webui.logger.debug('Editing network with Import Route Target is failed')
            result = result and False
        return result
    # end test4_6_edit_net_route_target_asn_ip

    @preposttest_wrapper
    def test5_7_negative_case_edit_net_with_invalid_route_target_ip(self):
        ''' Test to edit the existing network by Import Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add invalid IP as asn and invalid Import Target number under Import Route Target.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        global count
        count += 1
        self.webui.logger.debug("Step 1 : Add Import Route Target under VN")
        assert self.webui_common.edit_vn_with_route_target('add', 'neg', 'IRT', \
                                                           topo.invalid_asn_ip, \
                                                           topo.invalid_target_num, \
                                                           count=count), \
                                                           'Editing network with \
                                                           Import Route target failed'
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
    # end test5_7_negative_case_edit_net_with_invalid_route_target_ip

    @preposttest_wrapper
    def test5_9_negative_case_edit_net_with_invalid_route_target_num(self):
        ''' Test to edit the existing network by Import Route Target
            1. Go to Configure->Networking->Networks. Then select any of the vn
               and click the edit button
            2. Add invalid asn number and invalid Target number under Import Route Target.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        global count
        count += 1
        self.webui.logger.debug("Step 1 : Add Import Route Target under VN")
        assert self.webui_common.edit_vn_with_route_target('add', 'neg', 'IRT', \
                                                           topo.invalid_asn_num, \
                                                           topo.invalid_target_num, \
                                                           count=count), \
                                                           'Editing network with \
                                                           Import Route target failed'
        self.webui_common.wait_till_ajax_done(self.browser, wait=3)
    # end test5_9_negative_case_edit_net_with_invalid_route_target_num

    @preposttest_wrapper
    def test4_7_create_vn_with_spl_char(self):
        ''' Test to create vn with combination of spl char and verify in all API, OPS and WebUI
            1. Go to Configure->Networking->Networks. Then create VN with all
               combination of spl characters
            2. Verify the VN in WebUI, OPS and API server.

            Pass Criteria : Step 2 should pass
        '''
        vn_list = [topo.vn_name_beg_spl_char, topo.vn_name_end_spl_char, topo.vn_name_mid_spl_char]
        opt_list = []
        result = True
        for vn in vn_list:
            self.webui.logger.debug("Step 1 : Create vn %s " %(vn))
            if self.webui_common.click_on_create('Network', 'networks', vn,
                                                prj_name=self.webui.project_name_input):
                self.webui_common.wait_till_ajax_done(self.browser, wait=3)
                self.webui_common.send_keys(vn, 'display_name', 'name')
                self.webui_common.click_element('configure-networkbtn1')
                self.webui_common.wait_till_ajax_done(self.browser)
                uuid = self.webui_common.get_vn_detail_ui('UUID', vn_name='vn1')
                self.vn_disp_name = self.webui_common.get_vn_detail_ui('Display Name', \
                                                                      vn_name='vn1')
                self.webui.logger.debug("Step 2 : Verify WebUI server after editing")
                if not self.webui.verify_vn_after_edit_ui('Display Name', vn, opt_list):
                    self.webui.logger.debug('Virtual networks config data verification \
                                            in UI failed')
                    result = result and False
                self.webui.logger.debug("Step 3 : Verify API server after editing")
                if not self.webui.verify_vn_after_edit_api('Display Name', vn, uuid, opt_list):
                    self.webui.logger.debug('Virtual networks config data verification \
                                            in API failed')
                    result = result and False
                self.webui.logger.debug("Step 4 : Verify OPS server after editing")
                if not self.webui.verify_vn_after_edit_ops('Display Name', vn, vn, opt_list):
                    self.webui.logger.debug('Virtual networks config data verification \
                                            in OPS failed')
                    result = result and False
                self.webui.logger.debug("Step 5 : Remove the VN which is added")
                if not self.webui_common.edit_remove_option("Networks", 'remove',
                                                           display_name='vn1'):
                    self.webui.logger.debug('Editing network with advanced options is failed')
                    result = result and False
        return result
    # test4_7_create_vn_with_spl_char

    @preposttest_wrapper
    def test6_1_edit_port_without_change(self):
        ''' Test to edit the port without changing anything and
            check the UUID in API and WebUI
            1. Go to Configure->Networking->Ports. Then select one of the ports.
            2. Click the Edit button and Click the save button without changing anything.
            3. Verify the Port's UUID in WebUI and API server.

            Pass Criteria: UUID shouldn't be changed after editing
        '''
        result = True
        self.webui.logger.debug("Step 1 : Get the uuid before editing")
        uuid_port = self.webui_common.get_ui_value('Ports', 'UUID', name=topo.port_list[0])
        self.webui.logger.debug("UUID before editing " + str(uuid_port))
        self.webui.logger.debug("Step 2 : Edit the port without changing anything")
        if not self.webui_common.edit_without_change('Ports', display_name=topo.port_list[0]):
            self.webui.logger.debug('Editing Port failed')
            result = result and False
        self.webui.logger.debug("Step 3 : Verify WebUI and API server after editing")
        if not self.webui.verify_port_api_data([topo.port_list[0]], action='edit',
                                              expected_result=uuid_port):
            self.webui.logger("Verifying port in WebUI and API is failed")
            result = result and False
        return result
    # end test6_1_edit_port_without_change

    @preposttest_wrapper
    def test6_2_edit_port_vn_port_name(self):
        ''' Test to edit the port's VN and Port name
            1. Go to Configure->Networking->Ports. Then select any of the ports.
            2. Click the Edit button and Try to edit vn and port name.
            3. Verify the vn and port name disabled for existing port.

            Pass Criteria: Step 3 should pass
        '''
        self.webui.logger.debug("Step 1 : Edit VN and port in port page")
        assert self.webui.edit_port('vn_port', 'Ports', topo.port_list[0]), \
                                 'VN and Port name not disabled for editing'
        return True
    # end test6_2_edit_port_vn_port_name

    @preposttest_wrapper
    def test_write_port_with_add_security_group(self):
        ''' Test to edit the existing port by security group
            1. Go to Configure->Networking->Ports. Then select the one of the port
               and click the edit button.
            2. Attach one security group for the port and save.
            3. Check that attached security group is there in WebUI and API.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        sec_group_value = []
        self.webui.logger.debug("Step 1 : Attach security group to the port")
        sg_list = [topo.sg_list[0], 'default (default-domain:admin)']
        self.webui.edit_port('security_group', 'Ports', topo.port_list[0],
                                                  sg_list=sg_list)
        sec_group_value = self.webui_common.get_ui_value('ports', 'Security Groups',
                         name=topo.port_list[0])
        sec_group = sec_group_value[0]['value'].split('\n')
        sec_group.pop(0)
        sec_groups = sec_group[0].split(',')
        sec_group_list = self.webui_common.format_sec_group_name(sec_groups,
                                                                self.webui.project_name_input)
        self.webui.logger.debug("Step 2 : Verify the port for the attached security group \
                                in WebUI and API server")
        expected_sec_group_list = [{'key': 'Security_Groups', 'value': sec_group_list}]
        if not self.webui.verify_port_api_data([topo.port_list[0]], action='edit',
                                              expected_result=expected_sec_group_list):
            self.webui.logger.debug('API and UI verification failed for Security Group')
            result = result and False
        return result
    #end test6_3_edit_port_by_add_security_group

    @preposttest_wrapper
    def test6_4_edit_port_by_add_advanced_option_with_nh_mode_dynamic(self):
        ''' Test to edit the existing port by Advanced Options
            1. Go to Configure->Networking->Ports. Then select the last port
               and click the edit button
            2. Editing the port by adding the values and setting default values for
               juniper header, next hop mode and Traffic direction under advanced options.
            3. Verify the values added under advanced option with WebUI's and API's values.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        global mirror_enabled_already
        self.webui.logger.debug("Step 1 : Edit the port by adding the values \
                               under advanced option")
        port_params_list = [list(topo.vn_nets.values())[0][0]] + list(topo.port_advanced_option.values())
        fixed_ip = self.webui_common.get_ui_value('Ports', 'Fixed IPs',
                                                 name=topo.port_list[0])
        fixed_ip[0]['value'] = [list(fixed_ip[0].values())[0]] + \
                               [topo.port_advanced_option['subnet_ip']]
        result = self.webui.edit_port('advanced_option', 'Ports',
                     topo.port_list[0], port_admin_state='Down', params_list=port_params_list)
        if result:
            mirror_enabled_already = True
        adv_option_list = [{'key': 'Admin_State', 'value': 'Down'},
                          {'key': 'Local_Preference', 'value': '100'},
                          {'key': 'Allowed_address_pairs', 'value':
                              [topo.port_advanced_option['allowed_address_pair_ip'] + ' ' +
                              topo.port_advanced_option['allowed_address_pair_mac']]},
                          {'key': 'Analyzer_IP', 'value':
                              topo.port_advanced_option['analyzer_ip']},
                          {'key': 'UDP_Port', 'value':
                          topo.port_advanced_option['port']},
                          {'key': 'Analyzer_Name', 'value':
                              topo.port_advanced_option['analyzer_name']},
                          {'key': 'Juniper_Header', 'value': 'Enabled'},
                          {'key': 'Analyzer_MAC', 'value':
                              topo.port_advanced_option['analyzer_mac']},
                          {'key': 'Traffic_Direction', 'value': 'Both'},
                          {'key': 'Nexthop_Mode', 'value': 'Dynamic'},
                          {'key': 'Disable_Policy', 'value': 'True'},
                          {'key': 'ECMP_Hashing_Fields', 'value': 'destination-ip'}] + \
                          fixed_ip
        self.webui.logger.debug("Step 2 : Verify the port with WebUI and API")
        if not self.webui.verify_port_api_data([topo.port_list[0]], action='edit',
                                              expected_result=adv_option_list):
            result = result and False
        return result
    #end test6_4_edit_port_by_add_advanced_option_with_nh_mode_dynamic

    @preposttest_wrapper
    def test6_5_edit_port_by_add_advanced_option_with_nh_mode_static(self):
        ''' Test to edit the existing port by Advanced Options
            1. Go to Configure->Networking->Ports. Then select the last port
               and click the edit button
            2. Editing the port by adding the values and setting juniper header
               as disabled, next hop mode as static and Traffic direction as
               egress under advanced options.
            3. Verify the values added under advanced option with WebUI's and
               API's values.

            Pass Criteria : Step 3 should pass
        '''
        global mirror_enabled_already
        result = True
        self.webui.logger.debug("Step 1 : Edit the port by adding the values \
                               under advanced option")
        port_params_list = [list(topo.vn_nets.values())[0][0]] + list(topo.port_advanced_option.values())
        port_params_list.append(topo.vnet_list[0])
        result = self.webui.edit_port('advanced_option', 'Ports',
                     topo.port_list[0], params_list=port_params_list, subnet=False,
                     allowed_address_pair=False, ecmp=False, mirror=True,
                     mirror_enabled_already=mirror_enabled_already, header_mode='Disabled',
                     traffic_direction='Egress', next_hop_mode='Static')
        if result:
            mirror_enabled_already = True
        adv_option_list = [{'key': 'Admin_State', 'value': 'Up'},
                          {'key': 'Routing_Instance', 'value': topo.domain + ":" +
                              self.webui.project_name_input + ":" +
                              topo.vnet_list[0] + ":" + topo.vnet_list[0]},
                          {'key': 'Juniper_Header', 'value': 'Disabled'},
                          {'key': 'Traffic_Direction', 'value': u'Egress'},
                          {'key': 'Nexthop_Mode', 'value': 'Static'},
                          {'key': 'Disable_Policy', 'value': 'True'},
                          {'key': 'VTEP_Dest_IP', 'value':
                              topo.port_advanced_option['vtep_dst_ip_address']},
                          {'key': 'VTEP_Dest_MAC', 'value':
                              topo.port_advanced_option['vtep_dst_mac_address']},
                          {'key': 'VxLAN_ID', 'value':
                              topo.port_advanced_option['vxlan_id']}]
        self.webui.logger.debug("Step 2 : Verify the port with WebUI and API")
        if not self.webui.verify_port_api_data([topo.port_list[0]], action='edit',
                                              expected_result=adv_option_list):
            result = result and False
        return result
    #end test6_5_edit_port_by_add_advanced_option_with_nh_mode_static

    @preposttest_wrapper
    def test6_6_edit_port_by_dhcp_option(self):
        ''' Test to edit the existing port with DHCP options
            1. Go to Configure->Networking->Ports. Then select one of the port
               and click the edit button
            2. Try to edit the port with DHCP options.
            3. Verify DHCP code, value exactly updated or not in WebUI and API.

            Pass Criteria : Step 3 should pass
        '''
        self.webui.logger.debug("Step 1 : Add the DHCP options")
        expected_dhcp_value = [{'key': 'DHCP_Options', 'value': topo.dhcp_option_code +
                               " " +  topo.dhcp_option_value + " " + str(old_div(int
                               (topo.dhcp_option_value),8))}]
        dhcp_option_list = [topo.dhcp_option_code, topo.dhcp_option_value]
        result = self.webui.edit_port('dhcp', 'Ports', topo.port_list[0],
                                     dhcp_option=dhcp_option_list)
        if not self.webui.verify_port_api_data([topo.port_list[0]], action='edit',
                                              expected_result=expected_dhcp_value):
            self.webui.logger.debug('API and UI verification failed for DHCP Option')
            result = result and False
        return result
    #end test6_6_edit_port_by_dhcp_option

    @preposttest_wrapper
    def test6_7_edit_port_by_fat_flow_protocol(self):
        ''' Test to edit the existing port with FatFlow options
            1. Go to Configure->Networking->Ports. Then select one of the port
               and click the edit button
            2. Try to edit the port with Fat flow protocols.
            3. Verify Fat flow protocol value exactly updated or not in WebUI and API.

            Pass Criteria : Step 3 should pass
        '''
        self.webui.logger.debug("Step 1 : Add the Fat Flow Protocol")
        fat_flow_list = []
        for key, value in list(topo.fat_flow_values.items()):
            if key == 'ICMP':
                value = '0'
            fat_flow_list.append(key.lower() + ' ' + value)
        expected_fat_flow = [{'key': 'Fatflow', 'value': fat_flow_list}]
        result = self.webui.edit_port('FatFlow', 'Ports', topo.port_list[0],
                                     fat_flow_values=topo.fat_flow_values)
        if not self.webui.verify_port_api_data([topo.port_list[0]], action='edit',
                                              expected_result=expected_fat_flow):
            self.webui.logger.debug('API and UI verification failed for DHCP Option')
            result = result and False
        return result
    #end test6_7_edit_port_by_fat_flow_protocol

    @preposttest_wrapper
    def test6_8_1_edit_port_by_add_advanced_option_allowed_address_neg(self):
        ''' Test to edit the existing port by Advanced Options
            1. Go to Configure->Networking->Ports. Then select the last port
               and click the edit button.
            2. Editing the port by adding invalid allowed address pair under
               advanced options.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        self.webui.logger.debug("Step 1 : Edit the port by adding the values \
                               under advanced option")
        port_params_list = [list(topo.vn_nets.values())[0][0]] + list(topo.port_advanced_option.values())
        port_params_list[8] = topo.invalid_ip_mask
        port_params_list[6] = topo.invalid_mac
        port_params_list.append(topo.vnet_list[0])
        assert not self.webui.edit_port('advanced_option', 'Ports',
                     topo.port_list[0], params_list=port_params_list, subnet=False,
                     allowed_address_pair=True, ecmp=False, mirror=False,
                     mirror_enabled_already=True, header_mode='Disabled',
                     traffic_direction='Egress', next_hop_mode='Static'), \
                     'Editing the port with invalid allowed address pair is passed'
        return True
    #end test6_8_1_edit_port_by_add_advanced_option_allowed_address_neg

    @preposttest_wrapper
    def test6_8_2_edit_port_by_add_advanced_option_analyzer_neg(self):
        ''' Test to edit the existing port by Advanced Options
            1. Go to Configure->Networking->Ports. Then select the last port
               and click the edit button.
            2. Editing the port by adding invalid Analyzer IP and Analyzer MAC
               under Advanced Options.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        self.webui.logger.debug("Step 1 : Edit the port by adding the values \
                               under advanced option")
        global mirror_enabled_already
        port_params_list = [list(topo.vn_nets.values())[0][0]] + list(topo.port_advanced_option.values())
        port_params_list[5] = topo.invalid_ip_mask
        port_params_list[2] = topo.invalid_mac
        port_params_list[10] = topo.invalid_port
        port_params_list.append(topo.vnet_list[0])
        if not self.webui.edit_port('advanced_option', 'Ports',
               topo.port_list[0], params_list=port_params_list, subnet=False,
               allowed_address_pair=False, ecmp=False, mirror=True,
               mirror_enabled_already=mirror_enabled_already, header_mode='Disabled',
               traffic_direction='Egress'):
            mirror_enabled_already = True
            self.logger.info('WebUI throws an error as expected for \
                            invalid Analyzer IP and MAC')
        else:
            result = result and False
        return result
    #end test6_8_2_edit_port_by_add_advanced_option_analyzer_neg

    @preposttest_wrapper
    def test6_8_3_edit_port_by_add_advanced_option_nh_static_neg(self):
        ''' Test to edit the existing port by Advanced Options
            1. Go to Configure->Networking->Ports. Then select the last port
               and click the edit button.
            2. Editing the port by adding invalid VTEP IP and VTEP MAC under
               Advanced Options.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        result = True
        self.webui.logger.debug("Step 1 : Edit the port by adding the values \
                               under advanced option")
        global mirror_enabled_already
        port_params_list = [list(topo.vn_nets.values())[0][0]] + list(topo.port_advanced_option.values())
        port_params_list[7] = topo.invalid_ip_mask
        port_params_list[3] = topo.invalid_mac
        port_params_list.append(topo.vnet_list[0])
        if not self.webui.edit_port('advanced_option', 'Ports',
                     topo.port_list[0], params_list=port_params_list, subnet=False,
                     allowed_address_pair=True, ecmp=False, mirror=True,
                     mirror_enabled_already=mirror_enabled_already, header_mode='Disabled',
                     traffic_direction='Egress', next_hop_mode='Static'):
            mirror_enabled_already = True
            self.logger.info('WebUI throws an error as expected for \
                            invalid VTEP IP and VTEP MAC')
        else:
            result = result and False
        return result
    #end test6_8_3_edit_port_by_add_advanced_option_nh_static_neg

    @preposttest_wrapper
    def test6_7_1_edit_port_by_fat_flow_protocol_neg(self):
        ''' Test to edit the existing port with Invalid FatFlow Protocol options
            1. Go to Configure->Networking->Ports. Then select one of the port
               and click the edit button
            2. Try to edit the port with invalid Fat flow ports.
            3. WebUI should throw an error message while saving.

            Pass Criteria : Step 3 should pass
        '''
        self.webui.logger.debug("Step 1 : Add the Fat Flow Protocol with invalid port")
        fat_flow = {'TCP':'abcd'}
        assert not self.webui.edit_port('FatFlow', 'Ports', topo.port_list[0],
                    fat_flow_values=fat_flow), 'WebUI throws an error as expected \
                    for invalid fat flow port'
        return True
    #end test6_7_1_edit_port_by_fat_flow_protocol_neg

    @preposttest_wrapper
    def test6_9_add_sub_interface(self):
        ''' Test to add the sub interface for the existing port
            1. Go to Configure->Networking->Ports. Then select one of the port
               and add the sub interface
            2. Verify the sub-interface in WebUI and API.

            Pass Criteria : Step 2 should pass
        '''
        result = True
        self.webui.logger.debug('Step 1 : Add subinterface for the exiting port')
        uuid_port = self.webui_common.get_ui_value('Ports', 'UUID', name=topo.port_list[0])
        port_params_list = [topo.vnet_list[0], topo.sub_interface_name, topo.vlan_id]
        if self.webui.add_subinterface_ports('Ports', topo.port_list[0],
                                                   port_params_list):
            self.webui.logger.debug('WebUI throws an error as expected \
                                   for invalid fat flow port')
        else:
            result = result and False
        self.webui.logger.debug('Step 2 : Verify the Sub-Interface details in both WebUI \
                               and API')
        expected_result = [{'key': 'Parent_Port', 'value': list(uuid_port[0].values())[0]},
                           {'key': 'Sub_Interface_VLAN', 'value': topo.vlan_id}]
        if not self.webui.verify_port_api_data([topo.sub_interface_name], action='edit',
                                              expected_result=expected_result):
            self.webui.logger.debug('API and UI verification failed for Subinterface')
            result = result and False
        if not self.webui_common.edit_remove_option('Ports', 'subinterface', \
                                                   display_name=topo.sub_interface_name):
            self.webui.logger.debug('Deleting the existing sub-interface is failed')
            result = result and False
        return result
    #end test6_9_add_sub_interface

    @preposttest_wrapper
    def test6_9_1_add_sub_interface_with_invalid_vlan_id(self):
        ''' Test to add the sub interface for the existing port
            1. Go to Configure->Networking->Ports. Then select one of the port
               and add the sub interface with invalid vlan id
            2. WebUI shoud throw error while saving.

            Pass Criteria : Step 2 should pass
        '''
        result = True
        self.webui.logger.debug('Step 1 : Add subinterface for the exiting port')
        port_params_list = [topo.vnet_list[0], topo.sub_interface_name, topo.invalid_vlan_id]
        assert not self.webui.add_subinterface_ports('Ports', topo.port_list[0],
                    port_params_list), 'WebUI throws is not throwing an error \
                    as expected for invalid vlan id while adding sub-interface'
        return True
    #end test6_9_1_add_sub_interface_with_invalid_vlan_id

    @preposttest_wrapper
    def test7_1_edit_config_infra_global_config_forwarding_option(self):
        '''Test to verify global config on config->Infrastructure->Global Config
           ->Forwarding Option
           1. Go to Configure->Infrastructure->Global Config->Forwarding Option.

           2. Get all the details of global config from both WebUI and API server.
              and Verify the WebUI details against API server details.

           Pass Criteria: Step 2 should pass
        '''
        result = True
        if not self.webui.edit_and_verify_global_config('forwarding', ['L2 and L3', '10'],
                                            default=False):
            result = result and False
        if not self.webui.edit_and_verify_global_config('forwarding', ['Default']):
            result = result and False
        return result
    # end test7_1_edit_config_infra_global_config_forwarding_option

    @preposttest_wrapper
    def test7_2_edit_config_infra_global_config_bgp_option(self):
        '''Test to verify global config on config->Infrastructure->Global Config->
           BGP Option
           1. Go to Configure->Infrastructure->Global Config->BGP Option.
              and Edit the global config bgp options on WebUI.
           2. Verify the WebUI details against API server details.

           Pass Criteria: Step 2 should pass
        '''
        result = True
        bgp_params_list  = [topo.global_asn_num, 'Disabled', topo.bgp_restart_time,
                          topo.bgp_llgr_time, topo.bgp_end_rib, topo.host_prefix]
        if not self.webui.edit_and_verify_global_config('bgp', bgp_params_list, default=False):
            result = result and False
        bgp_orig_params_list = [topo.orig_bgp_asn, 'Enabled', topo.orig_bgp_restart_time,
                         topo.orig_bgp_llgr_time, topo.orig_bgp_end_rib]
        if not self.webui.edit_and_verify_global_config('bgp', bgp_orig_params_list, default=False,
                                              grace_restart=False, subnet=False):
            result = result and False
        if not self.webui.edit_and_verify_global_config('bgp', bgp_orig_params_list,
                                                       grace_restart=True):
            result = result and False
        return result
    # end test7_2_edit_config_infra_global_config_bgp_option

    @preposttest_wrapper
    def test7_2_1_edit_config_infra_global_config_bgp_option_invalid_values(self):
        '''Test to verify global config on config->Infrastructure->Global Config->
           BGP Option
           1. Go to Configure->Infrastructure->Global Config->BGP Option.
              and edit with invalid bgp option values on WebUI.
           2. WebUI should throw an error while editing.

           Pass Criteria: Step 2 should pass
        '''
        bgp_invalid_params_list  = [topo.invalid_asn_num, 'Enabled',
                          topo.invalid_bgp_restart_time[1],
                          topo.invalid_bgp_llgr_time[1], topo.invalid_bgp_end_rib[1],
                          topo.invalid_ip_mask]
        assert not self.webui.edit_and_verify_global_config('bgp', bgp_invalid_params_list,
                                            default=False), \
                                            'Edit global config under infrastructure is \
                                            failed for invalid asn and timers'
        return True
    # end test7_2_1_edit_config_infra_global_config_bgp_option_invalid_values

# end WebuiTestSanity
