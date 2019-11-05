from __future__ import print_function
from __future__ import absolute_import
import test_v1
from vn_test import *
from vm_test import *
import re
from common.connections import ContrailConnections
from common import isolated_creds
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
import re
from common import *
from tools import *
from nova_test import *
from .env import *
import os
from common.openstack_libs import ks_client
from project_test import *
from .test_ukai import *

#class UKAIProc(fixtures.Fixture):

#test_v1.BaseTestCase_v1
class UKAIProc(test_v1.BaseTestCase_v1):
     @classmethod
     def setUpClass(cls):
         super(UKAIProc, cls).setUpClass()
         cls.inputs.set_af('v4')
         cls.orch = cls.connections.orch
         cls.quantum_h= cls.connections.quantum_h
         cls.nova_h = cls.connections.nova_h
         cls.vnc_lib= cls.connections.vnc_lib
         cls.agent_inspect= cls.connections.agent_inspect
         cls.cn_inspect= cls.connections.cn_inspect
         cls.analytics_obj=cls.connections.analytics_obj
         cls.api_s_inspect = cls.connections.api_server_inspect
     #end setUpClass

     @classmethod
     def tearDownClass(cls):
         super(UKAIProc, cls).tearDownClass()
     #end tearDownClass

     def remove_from_cleanups(self, fix):
         for cleanup in self._cleanups:
             if fix.cleanUp in cleanup:
                 self._cleanups.remove(cleanup)

                 break
   #end remove_from_cleanups
     '''Create/Del Image
        Create/Del Flavor
        Create/Del policy
        Create/Del network
        Create/Del security group
        Launch VM


     '''

     def __init__(self, connections,project_name='admin',user_name='admin',tenant_name='None',tenant_id='None', flavor_name='None', flavor_ram='1', 
                  flavor_vcpus = '1', flavor_disk='1', flavor_swap='1', flavor_ephemeral='1',image_name='None', container_format='None', 
                  disk_format='None',min_disk='None', min_ram='None',  pol_name='None', pol_action='pass', pol_direction='\u003c\u003e', 
                  pol_protocol='any', vn_name='None', vn_cidr = 'None', vn_prefix_len='None', vm_name='None', 
                  image_id='None',flavor_id='None',vn_id='None',sg_id='None',sg_name='None',svc_template='svc_temp1'):
       
          self.connections = connections
          self.project_name = project_name
          self.user_name = user_name
          self.inputs = connections.inputs
          self.tenant_id = tenant_id
          self.tenant_name = tenant_name
          self.flavor_name = flavor_name
          self.flavor_ram = flavor_ram
          self.flavor_vcpus = flavor_vcpus
          self.flavor_disk = flavor_disk
          self.flavor_swap = flavor_swap
          self.flavor_ephemeral = flavor_ephemeral
          self.pol_name = pol_name
          self.pol_action = pol_action
          self.pol_direction = pol_direction
          self.pol_protocol = pol_protocol
          self.vn_name = vn_name
          self.vn_cidr = vn_cidr
          self.vn_prefix_len = vn_prefix_len
          self.image_name = image_name
          self.container_format = container_format
          self.disk_format = disk_format
          self.min_disk = min_disk
          self.min_ram = min_ram
          self.vm_name = vm_name
          self.image_id = image_id
          self.flavor_id = flavor_id
          self.vn_id = vn_id
          self.sg_id = sg_id
          self.sg_name = sg_name
          self.svc_template = svc_template
          self.images_info = parse_cfg_file('configs/images.cfg')
          self.auth_url = "http://%s:5000/v2.0/" %(self.inputs.gc_host_control_data)
          self.ukai_url = "http://%s:9500/" %(self.inputs.gc_host_mgmt)
          self.env_non_admin = 'export GOHAN_ENDPOINT_URL=http://%s:9500; export GOHAN_SCHEMA_URL=/gohan/v0.1/schemas; export OS_AUTH_URL="http://%s:5000/v2.0";' \
                          %(self.inputs.gc_host_mgmt, self.inputs.gc_host_mgmt)
          self.env_admin = 'export GOHAN_ENDPOINT_URL=http://%s:9500; export OS_USERNAME=admin; export OS_PASSWORD=%s; \
                            export GOHAN_SCHEMA_URL=/gohan/v0.1/schemas; export OS_TENANT_NAME=admin; export OS_AUTH_URL="http://%s:5000/v2.0";' \
                            %(self.inputs.gc_host_mgmt,self.inputs.keystone_password,self.inputs.gc_host_mgmt)
          self.env_vm =  'export GOHAN_ENDPOINT_URL=http://%s:9500; export OS_USERNAME=admin; export OS_PASSWORD=%s; \
                          export GOHAN_SCHEMA_URL=/gohan/v0.1/schemas; export OS_AUTH_URL="http://%s:5000/v2.0";' \
                          %(self.inputs.gc_host_mgmt,self.inputs.keystone_password,self.inputs.gc_host_mgmt)
          self.contrail_env = 'source /etc/contrail/openstackrc;'

          


###########################################
#Name : create_flavor
#Description: Create flavor for VM to be 
#launched
###########################################
     def create_flavor(self):
          connections = self.connections
          tenant_id = self.tenant_id
          name = self.flavor_name
          ram = self.flavor_ram 
          vcpu = self.flavor_vcpus
          disk = self.flavor_disk 
          swap = self.flavor_swap 
          ephemeral = self.flavor_ephemeral
          project_name = self.project_name
          user_name = self.user_name
          tenant = self.connections.auth.get_project_id(project_name)
          #projectObj= ProjectFixture(connections=self.connections,
          #                          project_name=project_name,username=user_name,password=user_name)
          #project_connections = projectObj.get_project_connections()
          env_admin = self.env_admin
          env_non_admin = self.env_non_admin
          env_vm = self.env_vm

          #Check flavor already exist or not"
          cmd = 'ukai client flavor list |grep %s' %(name)
          cmd = env_admin+cmd
          output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
          flavor_id = re.search(r'\w+-\w+-\w+-\w+-\w+', output);
          if flavor_id:
             raise Exception("Flavor already present ")           

          cmd = 'ukai client flavor create  --name %s --ram %s --vcpus %s --disk %s --swap %s --ephemeral %s' %(name,ram,vcpu,disk,swap,ephemeral)
          cmd = env_admin+cmd
          output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
                     
          connections.logger.info("Return flavor Id")
          cmd = 'ukai client flavor list |grep %s' %(name)
          cmd = env_admin+cmd
          output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
          flavor_id = re.search(r'\w+-\w+-\w+-\w+-\w+', output)
          flavor_id = flavor_id.group()
          if not flavor_id:
             msg = "FAIL: flavor is not created"
             result = False
             assert result,msg

          return flavor_id

#End of create_flavor



###########################################
#Name : delete_flavor
#Description: Delete flavor for VM to be
#launched
###########################################
     def delete_flavor(self):
          connections = self.connections
          name = self.flavor_name
          project_name = self.project_name
          user_name = self.user_name
          tenant = self.connections.auth.get_project_id(project_name)
          #projectObj=ProjectFixture(vnc_lib_h=connections.vnc_lib, connections=self.connections,
          #                          project_name=project_name,username=user_name,password=user_name)
          #project_connections = projectObj.get_project_connections()
          env_admin = self.env_admin
          env_non_admin = self.env_non_admin
          env_vm = self.env_vm

          cmd = 'ukai client flavor delete  %s' %(name)
          cmd = env_admin+cmd
          output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
          flavor_id = re.search(r'\w+-\w+-\w+-\w+-\w+', output)
          connections.logger.info("check flavor is deleted")
          cmd = 'ukai client flavor list |grep %s' %(name)
          cmd = env_admin+cmd
          output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
          flavor_name = re.search('name', output)
          if flavor_name:
             msg = "FAIL: flavor is not deleted"
             result = False
             assert result,msg
          else:
             return True

             

#End of delete_flavor




###########################################
#Name : create_image 
#Description: Add Image used for launching VM
#Verify image added through UKAI is added on 
#the clusters
###########################################
     def create_image(self, image_name):
          connections = self.connections
          images_info = self.images_info[image_name] 
          webserver = images_info['webserver'] or \
            os.getenv('IMAGE_WEB_SERVER', '10.204.216.50')
          location = images_info['location']
          params = images_info['params']
          image = images_info['name']
          image_type = images_info['type']
          tenant_id = self.tenant_id
          name = self.image_name
          container_format = self.container_format
          disk_format = self.disk_format
          min_disk = self.min_disk
          min_ram = self.min_ram
          project_name = self.project_name
          user_name = self.user_name
          env_admin = self.env_admin
          env_non_admin = self.env_non_admin
          env_vm = self.env_vm
          tenant = self.connections.auth.get_project_id(project_name)
          #projectObj=ProjectFixture(vnc_lib_h=connections.vnc_lib, connections=self.connections,
          #                          project_name=project_name,username=user_name,password=user_name)
          #project_connections = projectObj.get_project_connections()

        
          contrail_test_path = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)),'..'))
        
          if contrail_test_path and os.path.isfile("%s/images/%s" % (contrail_test_path, image)):
             build_path = "file://%s/images/%s" % (contrail_test_path, image)
          elif re.match(r'^file://', location):
               build_path = '%s/%s' % (location, image)
          else:
              build_path = 'http://%s/%s/%s' % (webserver, location, image)
        
          if min_disk == 'None' and min_ram == 'None' :
               cmd = 'ukai client image create --name "%s" --description "%s" --url "%s" \
                      --disk_format "%s" --container_format "%s"' \
                     %(name, name, build_path, disk_format, container_format)
               cmd = env_admin+cmd
               connections.logger.info("cmd %s" %(cmd))
               output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)

          else:
               cmd = 'ukai client image create  --name "%s" --description "%s" --url "%s" --disk_format "%s" --container_format "%s" --min_disk "%s" --min_ram "%s"' \
                      %(name, name, build_path, disk_format, container_format, min_disk, min_ram)
               cmd = env_admin+cmd
               print("cmd %s" %(cmd))
               output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)

          print("check the image is added on the server")
          time.sleep (30)
          image = NovaHelper(inputs=self.inputs, project_name='admin')        
          if image.find_image(name):
              msg= "PASS: VM Image is created is Pass"
              result = True
              assert result, msg
          else:
              msg = "FAIL: VM Image create Failed"
              result = False
              assert result,msg   
          
          print("Return image Id") 
          cmd = 'ukai client image list |grep %s' %(name)
          cmd = env_admin+cmd
          output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
          image_id = re.search(r'\w+-\w+-\w+-\w+-\w+', output) 
          image_id = image_id.group()
          return image_id

#End of create_image



###########################################
#Name : deleting_image
#Description:Delete the VM image through 
#UKAI and check image is deleted from the 
#server
###########################################
     def delete_image(self):
          connections = self.connections
          name = self.image_name
          project_name = self.project_name
          user_name = self.user_name
          env_admin = self.env_admin
          env_non_admin = self.env_non_admin
          env_vm = self.env_vm
          tenant = self.connections.auth.get_project_id(project_name)
          #projectObj=ProjectFixture(vnc_lib_h=connections.vnc_lib, connections=self.connections,project_name=project_name,
          #                          username=user_name,password=user_name)
          #project_connections = projectObj.get_project_connections()


          print("Delete image")
          cmd = 'ukai client image delete %s' %(name)
          cmd = env_admin+cmd
          output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
          time.sleep (5)
          print("check image is deleted from the server")
          image = NovaHelper(inputs=self.inputs, project_name='admin')
          if image.find_image(name):
              msg= "FAIL: VM Image is not deleted from the server"
              result = False
              assert result, msg
          else:
              msg = "PASS: VM Image is deleted from the served"
              return True

#End of delete_image          



###########################################
#Name : create_policy
#Description: Add network policy through UKAI
###########################################
     def create_pol(self):
          connections = self.connections
          tenant_id = self.tenant_id
          project_name=self.project_name
          name = self.pol_name
          action = self.pol_action 
          direction = self.pol_direction 
          protocol = self.pol_protocol
          project_name = self.project_name
          user_name = self.user_name
          env_admin = self.env_admin
          env_non_admin = self.env_non_admin
          env_vm = self.env_vm
          tenant = self.connections.auth.get_project_id(project_name)
          #projectObj=ProjectFixture(vnc_lib_h=connections.vnc_lib, connections=self.connections,project_name=project_name,
          #                          username=user_name,password=user_name)
          #project_connections = projectObj.get_project_connections()
          if user_name is not "admin":
             credentials = " export OS_TENANT_NAME=%s export OS_USERNAME=%s export OS_PASSWORD=%s; " %(project_name,user_name, user_name)
             env_cli = env_non_admin+credentials
          else:
             credentials = 'None'
             project_name = 'admin'
             env_cli = env_admin

          print("Creating policy with %s, %s, %s, %s" %(name, action, direction, protocol))
          cmd = 'ukai client network_policy create  --name %s --entries  \'[{"action_list": {"apply_service": [],"simple_action": "%s"},\
                 "direction": "%s","protocol": "%s"}]\''%(name, action, direction, protocol)
          cmd = env_cli+cmd
          print("cmd %s" %(cmd))
          
          output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
          time.sleep(30)
          cmd = cmd = 'ukai client network_policy list |grep %s' %(name)
          cmd = env_cli+cmd
          output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
          uuid = re.search(r'\w+-\w+-\w+-\w+-\w+', output)
          uuid = uuid.group()
          return uuid
         
#End of create_policy 



###########################################
#Name : delete_policy
#Description: Del network policy through UKAI
###########################################
     def delete_pol(self):
          connections = self.connections
          tenant_id = self.tenant_id
          project_name=self.project_name
          name = self.pol_name
          project_name = self.project_name
          user_name = self.user_name
          env_admin = self.env_admin
          env_non_admin = self.env_non_admin
          env_vm = self.env_vm
          tenant = self.connections.auth.get_project_id(project_name)
          #projectObj=ProjectFixture(vnc_lib_h=connections.vnc_lib, connections=self.connections,project_name=project_name,
          #                          username=user_name,password=user_name)
          #project_connections = projectObj.get_project_connections()

          if user_name is not "admin":
             credentials = " export OS_TENANT_NAME=%s export OS_USERNAME=%s export OS_PASSWORD=%s; " %(project_name,user_name, user_name)
             env_cli = env_non_admin+credentials
          else:
             credentials = 'None'
             project_name = 'admin'
             env_cli = env_admin
 
          print("Del policy  %s" %(name))
          cmd = 'ukai client network_policy delete  %s' %(name)
          cmd = env_cli+cmd
          print("cmd %s" %(cmd))

          output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
          time.sleep(5)
          #check policy is del
          cmd = cmd = 'ukai client network_policy list |grep %s' %(name)
          cmd = env_cli+cmd
          output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
          pol_name = re.search(name, output)

          if pol_name:
             msg = "FAIL: policy is not deleted"
             result = False
             assert result,msg

          else:
             return True

#End of delete_pol()


###########################################
#Name : create_sg
#Description: Creating security group
#Not fully implemented as SG rule addition 
#through CLI is not yet implemented
###########################################
     def create_sg(self):
          connections = self.connections
          tenant_id = self.tenant_id
          project_name=self.inputs.project_name
          name = self.sg_name
          project_name = self.project_name
          user_name = self.user_name
          env_admin = self.env_admin
          env_non_admin = self.env_non_admin
          env_vm = self.env_vm
          tenant = self.connections.auth.get_project_id(project_name)
          #projectObj=ProjectFixture(vnc_lib_h=connections.vnc_lib, connections=self.connections,project_name=project_name,
          #                          username=user_name,password=user_name)
          #project_connections = projectObj.get_project_connections()

          if user_name is not "admin":
             credentials = " export OS_TENANT_NAME=%s export OS_USERNAME=%s export OS_PASSWORD=%s; " %(project_name,user_name, user_name)
             env_cli = env_non_admin+credentials
          else:
             credentials = 'None'
             project_name = 'admin'
             env_cli = env_admin



          cmd =  'ukai client security_group create --name %s' %(name)
          cmd = env_cli+cmd
          output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)

          print("get SG Id")
          cmd = 'ukai client security_group list |grep %s' %(name)
          cmd = env_cli+cmd
          output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
          sg_id = re.search(r'\w+-\w+-\w+-\w+-\w+', output)
          sg_id = sg_id.group()
          connections.logger.info('SG created is %s' %(sg_id)) 
          if not sg_id:
             msg = "FAIL: security group creation failed"
             result = False
             assert result,msg

          return sg_id

#End of create_sg



###########################################
#Name : delete_sg
#Description: Del security group
###########################################
     def delete_sg(self):
          connections = self.connections
          tenant_id = self.tenant_id
          name = self.sg_name
          project_name = self.project_name
          user_name = self.user_name
          env_admin = self.env_admin
          env_non_admin = self.env_non_admin
          env_vm = self.env_vm
          tenant = self.connections.auth.get_project_id(project_name)
          #projectObj=ProjectFixture(vnc_lib_h=connections.vnc_lib, connections=self.connections,project_name=project_name,
          #                          username=user_name,password=user_name)
          #project_connections = projectObj.get_project_connections()

          if user_name is not "admin":
             credentials = " export OS_TENANT_NAME=%s export OS_USERNAME=%s export OS_PASSWORD=%s; " %(project_name,user_name, user_name)
             env_cli = env_non_admin+credentials
          else:
             credentials = 'None'
             project_name = 'admin'
             env_cli = env_admin
          

          cmd =  'ukai client security_group delete %s' %(name)
          cmd = env_cli+cmd
          output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
          time.sleep(5)
          print("check SG is deleted")
          cmd = 'ukai client security_group list |grep %s' %(name)
          cmd = env_cli+cmd
          output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
          sg_id = re.search(name, output)

          if sg_id:
             msg = "FAIL: security group is not deleted"
             result = False
             assert result,msg

          else:
             return True

#End of delete_sg()



###########################################
#Name : create_svc_template
#Description: Create service templare
###########################################
     def create_svc_template(self):
          connections = self.connections
          tenant_id = self.tenant_id
          svc_template = self.svc_template
          project_name = self.project_name
          user_name = self.user_name
          env_admin = self.env_admin
          env_non_admin = self.env_non_admin
          env_vm = self.env_vm
          tenant = self.connections.auth.get_project_id(project_name)
          #projectObj=ProjectFixture(vnc_lib_h=connections.vnc_lib, connections=self.connections,project_name=project_name,
          #                          username=user_name,password=user_name)
          #project_connections = projectObj.get_project_connections()

          if user_name is not "admin":
             credentials = " export OS_TENANT_NAME=%s export OS_USERNAME=%s export OS_PASSWORD=%s; " %(project_name,user_name, user_name)
             env_cli = env_non_admin+credentials
          else:
             credentials = 'None'
             project_name = 'admin'
             env_cli = env_admin

#End of create_svc_template



###########################################
#Name : create_vn
#Description: create network thhrough ukai
###########################################
     def create_vn(self):
          connections = self.connections
          tenant_id = self.tenant_id
          name = self.vn_name
          cidr = self.vn_cidr
          prefix_len = self.vn_prefix_len
          policy = self.pol_name
          project_name = self.project_name
          user_name = self.user_name
          env_admin = self.env_admin
          env_non_admin = self.env_non_admin
          env_vm = self.env_vm
          tenant = self.connections.auth.get_project_id(project_name)
          #projectObj=ProjectFixture(vnc_lib_h=connections.vnc_lib, connections=self.connections,project_name=project_name,
          #                          username=user_name,password=user_name)
          #project_connections = projectObj.get_project_connections()


          if user_name is not "admin":
             credentials = " export OS_TENANT_NAME=%s export OS_USERNAME=%s export OS_PASSWORD=%s; " %(project_name,user_name, user_name)
             env_cli = env_non_admin+credentials
          else:
             credentials = 'None'
             project_name = 'admin'
             env_cli = env_admin

          print("Creating a network with %s, %s, %s" %(name, cidr, prefix_len))
          print("Get policy Id")
          if policy != 'None':
                cmd = ' ukai client network_policy list|grep %s' %(policy)
                cmd = env_cli+cmd
                output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
                policy_id = re.search(r'\w+-\w+-\w+-\w+-\w+', output); policy_id = policy_id.group()

          if policy != 'None':
                cmd = 'ukai client network create   --name %s  --cidr %s --local_prefix_len %s --policies \'["%s"]\'' %(name, cidr, prefix_len, policy_id)
                cmd = env_cli+cmd
                print("cmd %s" %(cmd))
                output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)         
          else: 
                cmd = 'ukai client network create   --name %s  --cidr %s --local_prefix_len %s' %(name, cidr, prefix_len)
                cmd = env_cli+cmd
                print("cmd %s" %(cmd))
                output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
   
          print("get VN Id")
          cmd = 'ukai client network list |grep %s' %(name)
          cmd = env_cli+cmd
          output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
          vn_id = re.search(r'\w+-\w+-\w+-\w+-\w+', output)
          vn_id = vn_id.group()
          return vn_id
           
#End of create_vn       



###########################################
#Name : delete_vn
#Description: delete network through ukai
###########################################
     def delete_vn(self):
          connections = self.connections
          tenant_id = self.tenant_id
          name = self.vn_name
          project_name = self.project_name
          user_name = self.user_name
          env_admin = self.env_admin
          env_non_admin = self.env_non_admin
          env_vm = self.env_vm
          tenant = self.connections.auth.get_project_id(project_name)
          #projectObj=ProjectFixture(vnc_lib_h=connections.vnc_lib, connections=self.connections,project_name=project_name,
          #                          username=user_name,password=user_name)
          #project_connections = projectObj.get_project_connections()

          if user_name is not "admin":
             credentials = " export OS_TENANT_NAME=%s export OS_USERNAME=%s export OS_PASSWORD=%s; " %(project_name,user_name, user_name)
             env_cli = env_non_admin+credentials
          else:
             credentials = 'None'
             project_name = 'admin'
             env_cli = env_admin
        
          cmd = 'ukai client network delete  %s ' %(name)
          cmd = env_cli+cmd
          print("cmd %s" %(cmd))
          output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
  
          #check VN is deleted
          cmd = 'ukai client network list |grep %s' %(name)
          cmd = env_cli+cmd
          output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
          vn_name = re.search(name, output)
          
          if vn_name:
             msg = "FAIL: VN is not deleted"
             result = False
             assert result,msg

          else:
             return True




###########################################
#Name : update_vn
#Description: updating the already created
#VN like attaching policy 
###########################################
     def update_vn(self):
          connections = self.connections
          name = self.vn_name
          policy = self.pol_name
          project_name = self.project_name
          user_name = self.user_name
          env_admin = self.env_admin
          env_non_admin = self.env_non_admin
          env_vm = self.env_vm
          tenant = self.connections.auth.get_project_id(project_name)
          #projectObj=ProjectFixture(vnc_lib_h=connections.vnc_lib, connections=self.connections,project_name=project_name,
          #                          username=user_name,password=user_name)
          #project_connections = projectObj.get_project_connections()


          if user_name is not "admin":
             credentials = " export OS_TENANT_NAME=%s export OS_USERNAME=%s export OS_PASSWORD=%s; " %(project_name,user_name, user_name)
             env_cli = env_non_admin+credentials
          else:
             credentials = 'None'
             project_name = 'admin'
             env_cli = env_admin

          
          print("Update the VN with policy")
          if policy != 'None':
               cmd = ' ukai client network_policy list|grep %s' %(policy)
               cmd = env_cli+cmd
               output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
               policy_id = re.search(r'\w+-\w+-\w+-\w+-\w+', output); policy_id = policy_id.group()

          if policy != 'None':
               cmd = 'ukai client network set --policies \'["%s"]\' %s' %(policy_id, name)
               cmd = env_cli+cmd
               print("cmd %s" %(cmd))
               output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)


#End of update_vn   




###########################################
#Name : create_vm
#Description: Launch VM 
###########################################
     def create_vm(self):
           connections = self.connections
           #credentials = self.credentials
           tenant_name = self.tenant_name
           name = self.vm_name
           image_id = self.image_id
           flavor_id = self.flavor_id
           sg_id = self.sg_id
           nw_id = self.vn_id
           auth_url = self.auth_url
           ukai_url = self.ukai_url
           env_admin = self.env_admin
           env_non_admin = self.env_non_admin
           env_vm = self.env_vm



           env_cli = env_vm + "export OS_TENANT_NAME=%s; " %(tenant_name)
           keystone = ks_client.Client(username=username, password=password,tenant_name=admin_tenant_name,auth_url=auth_url)

           if sg_id =='None':
                cmd = 'ukai client server create --name %s --image_id %s --network_id %s --flavor_id %s' %(name,image_id,nw_id,flavor_id)
                cmd = env_cli+cmd
                output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)

           else:
                cmd = 'ukai client server create --name %s --image_id %s --network_id %s --flavor_id %s --security_group_id %s' %(name,image_id,nw_id,flavor_id,sg_id)
                cmd = env_cli+cmd
                output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)

           

           #wait for vm to be UP before checking the uuid
           time.sleep(20)
           response, servers = keystone.get(ukai_url + "v1.0/servers")
           if not response.ok:
              print(response.reason)
              os.exit()

           for server in servers['servers']:
                print(server['name'])
                response, local_servers = keystone.get("%sv1.0/servers/%s/local_servers" % (ukai_url, server['id']))
                if not response.ok:
                     print(response.reason)

                for local_server in local_servers['local_servers']:
                     print(local_server['status'], local_server['instance_id'])
                     if local_server ['server']['name'] == name:
                        if local_server ['location']['address'] == "99.1.1.13":
                           uuid = local_server['instance_id']
                           break

           return uuid

                     
#End of create_vm



###########################################
#Name : delete_vm
#Description: Delete VM and return err if
#vm is not deleted
###########################################
     def delete_vm(self):
           connections = self.connections
           #credentials = self.credentials
           tenant_name = self.tenant_name
           name = self.vm_name
           env_cli = env_vm + "export OS_TENANT_NAME=%s; " %(tenant_name)
           auth_url = self.auth_url
           ukai_url = self.ukai_url
           env_admin = self.env_admin
           env_non_admin = self.env_non_admin
           env_vm = self.env_vm


           keystone = client.Client(
                   username=username,
                   password=password,
                   tenant_name=admin_tenant_name,
                   auth_url=auth_url
           )

           cmd = 'ukai client server delete  %s' %(name)
           cmd = env_cli+cmd
           output = self.inputs.run_cmd_on_server(gc_host, cmd, username = gc_user_name , password = gc_user_pwd)
           
           time.sleep(5)
           response, servers = keystone.get(ukai_url + "v1.0/servers")
           if not response.ok:
              print(response.reason)
              servers = []
              os.exit()

           if servers['servers']:
              for server in servers['servers']:
                   print(server['name'])
                   if server['name'] is name:
                      msg = "FAIL: VM is not deleted"
                      result = False
                      assert result,msg 
                   else:
                      return True
           else:
               return True

#End of delete_vm


class ukaiBaseTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(ukaiBaseTest, cls).setUpClass()
        cls.inputs.set_af('v4')
        cls.orch = cls.connections.orch
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        cls.api_s_inspect = cls.connections.api_server_inspect
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(ukaiBaseTest, cls).tearDownClass()
    #end tearDownClass 

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            if fix.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break
   #end remove_from_cleanups

