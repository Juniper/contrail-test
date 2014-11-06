# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import os
import time
import fixtures
import testtools
import re
import test
from tcutils.wrappers import preposttest_wrapper
import base

class WebuiTestSanity(base.WebuiBaseTest):

    @classmethod
    def setUpClass(cls):
        super(WebuiTestSanity, cls).setUpClass()

    def runTest(self):
        pass
    #end runTest

    @preposttest_wrapper                                                                                                     
    def test_floating_ips(self):                                                                                             
        '''Test floating ips on config->Networking->Manage Floating IPs page                                                 
        '''                                                                                                                  
        assert self.webui.verify_floating_ip_api_data()                                                                      
        return True                                                                                                          
    # end test_floating_ips                                                                                                  
                                                                                                                             
    @preposttest_wrapper                                                                                                     
    def test_networks(self):                                                                                                 
        '''Test networks on config->Networking->Networks page                                                                
        '''                                                                                                                  
        assert self.webui.verify_vn_api_data()                                                                               
        return True                                                                                                          
    # end test_networks                                                                                                      
                                                                                                                             
    @preposttest_wrapper                                                                                                     
    def test_ipams(self):                                                                                                    
        '''Test ipams on config->Networking->IP Adress Management page                                                       
        '''                                                                                                                  
        assert self.webui.verify_ipam_api_data()                                                                             
        return True                                                                                                          
    # end test_ipams                                                                                                         
                                                                                                                             
    @preposttest_wrapper                                                                                                     
    def test_policies(self):                                                                                                 
        '''Test polcies on config->Networking->Policies page                                                                 
        '''                                                                                                                  
        assert self.webui.verify_policy_api_data()                                                                           
        return True                                                                                                          
    # end test_policies                                                                                                      

    @preposttest_wrapper                                                                                                     
    def test_service_templates(self):                                                                                        
        '''Test svc templates on config->Services->Service Templates page                                                    
        '''                                                                                                                  
        assert self.webui.verify_service_template_api_basic_data()                                                           
        return True                                                                                                          
    # end test_service_templates                                                                                             
                                                                                                                             
    @preposttest_wrapper                                                                                                     
    def test_service_instances(self):                                                                                        
        '''Test svc instances on config->Services->Service Instances page                                                    
        '''                                                                                                                  
        assert self.webui.verify_service_instance_api_basic_data()                                                           
        return True                                                                                                          
    # end test_service_instances                                                                                             
                                                                                                                             
    @preposttest_wrapper                                                                                                     
    def test_project_quotas(self):                                                                                           
        '''Test project quotas on config->Networking->Project Quotas page                                                    
        '''                                                                                                                  
        assert self.webui.verify_project_quotas()                                                                            
        return True                                                                                                          
    # end test_project_quotas                   

    @preposttest_wrapper                                                                                                     
    def test_control_node_basic_details(self):                                                                               
        '''Test control node basic details on monitor->Infrastruture->Control Nodes->Node Details-> Basic view page          
        '''                                                                                                                  
        assert self.webui.verify_bgp_routers_ops_basic_data()                                                                
        return True                                                                                                          
    # end test_control_node_basic_details                                                                                    
                                                                                                                             
    @preposttest_wrapper                                                                                                     
    def test_control_node_advance_details(self):                                                                             
        '''Test control node advance details on monitor->Infrastruture->Control Nodes->Node Details-> Advanced view page     
        '''                                                                                                                  
        assert self.webui.verify_bgp_routers_ops_advance_data()                                                              
        return True                                                                                                          
    # end test_control_node_advance_details                                                                                  
                                                                                                                             
    @preposttest_wrapper                                                                                                     
    def test_vrouter_basic_details(self):                                                                                    
        '''Test virtual routers basic details on monitor->Infrastruture->Virtual Routers->Node Details-> Basic view page     
        '''                                                                                                                  
        assert self.webui.verify_vrouter_ops_basic_data()                                                                    
        return True                                                                                                          
    # end test_vrouter_basic_details                                                                                         
                                                                                                                             
    @preposttest_wrapper                                                                                                     
    def test_vrouter_advance_details(self):                                                                                  
        '''Test virtual routers advance details on monitor->Infrastruture->Virtual Routers->Node Details-> Advanced view page
        '''                                                                                                                  
        assert self.webui.verify_vrouter_ops_advance_data()                                                                  
        return True                                                                                                          
    # end test_vrouter_advance_details  

    @preposttest_wrapper                                                                                                     
    def test_analytics_node_basic_details(self):                                                                             
        '''Test analytics node basic details on monitor->Infrastruture->Analytics Nodes->Node Details-> Basic view page      
        '''                                                                                                                  
        assert self.webui.verify_analytics_nodes_ops_basic_data()                                                            
        return True                                                                                                          
    # end test_analytics_node_basic_details                                                                                  
                                                                                                                             
    @preposttest_wrapper                                                                                                     
    def test_analytics_node_advance_details(self):                                                                           
        '''Test analytics node advance details on monitor->Infrastruture-> Analytics Nodes->Node Details-> Advanced view page
        '''                                                                                                                  
        assert self.webui.verify_analytics_nodes_ops_advance_data()                                                          
        return True                                                                                                          
    # end test_analytics_node_advance_details                                                                                
                                                                                                                             
    @preposttest_wrapper                                                                                                     
    def test_config_node_basic_details(self):                                                                                
        '''Test config node basic details on monitor->Infrastruture->Config Nodes->Node Details-> Basic view page            
        '''                                                                                                                  
        assert self.webui.verify_config_nodes_ops_basic_data()                                                               
        return True                                                                                                          
    # end test_config_node_basic_details                                                                                     
                                                                                                                             
    @preposttest_wrapper                                                                                                     
    def test_config_node_advance_details(self):                                                                              
        '''Test config node advance details on monitor->Infrastruture->Config Nodes->Node Details-> Advanced view page       
        '''                                                                                                                  
        assert self.webui.verify_config_nodes_ops_advance_data()                                                             
        return True                                                                                                          
    # end test_config_node_advance_details                                                                                   
                                                                                                                             
    @preposttest_wrapper                                                                                                     
    def test_network_basic_details(self):                                                                                    
        '''Test network basic on monitor->Networking->Networks->Network Summary-> basic page                                 
        '''                                                                                                                  
        assert self.webui.verify_vn_ops_basic_data()                                                                         
        return True                                                                                                          
    # end test_network_basic_details                                                                                         
                                                                                                                             
    @preposttest_wrapper                                                                                                     
    def test_network_advance_details(self):                                                                                  
        '''Test network advance details on monitor->Networking->Networks->Network Summary-> Advanced page                    
        '''                                                                                                                  
        assert self.webui.verify_vn_ops_advance_data()                                                                       
        return True                                                                                                          
    # end test_network_advance_details                                                                                       
                                                                                                                             
    @preposttest_wrapper                                                                                                     
    def test_dashboard_details(self):                                                                                        
        '''Test dashboard details on monitor->Infra->Dashboard page                                                          
        '''                                                                                                                  
        assert self.webui.verify_dashboard_details()                                                                         
        return True                                                                                                          
    # end test_dashboard_details                                                                                             
                                                                                                                             
    @preposttest_wrapper                                                                                                     
    def test_instance_basic_details(self):                                                                                   
        '''Test instance basic details on Monitor->Networking->Instances page                                                
        '''                                                                                                                  
        assert self.webui.verify_vm_ops_basic_data()                                                                         
        return True                                                                                                          
    # end test_instance_basic_details                                                                                        
                                                                                                                             
    @preposttest_wrapper                                                                                                     
    def test_instance_advance_details(self):                                                                                 
        '''Test instance advance details on Monitor->Networking->Instances page                                              
        '''                                                                                                                  
        assert self.webui.verify_vm_ops_advance_data()                                                                       
        return True                                                                                                          
    # end test_instance_advance_details                                                                                      
                                                                                                                             
                                                                                                                             
# end WebuiTestSanity
