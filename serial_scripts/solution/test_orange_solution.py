from __future__ import absolute_import
from builtins import str
from builtins import range
from .base import BaseSolutionsTest
from common.heat.base import BaseHeatTest
from tcutils.wrappers import preposttest_wrapper
import test
from vn_test import *
from quantum_test import *
from policy_test import *
from vm_test import *
from tcutils.topo.sdn_topo_setup import sdnTopoSetupFixture
from common.system.system_verification import system_vna_verify_policy
from common.system.system_verification import all_policy_verify
from common.policy import policy_test_helper
from tcutils.test_lib.test_utils import assertEqual
from vnc_api import vnc_api
from vnc_api.gen.resource_test import *
from scripts.policy import sdn_policy_traffic_test_topo
from heat_test import HeatStackFixture
from nova_test import *
import os
import yaml
import time
import glob

af_test = 'dual'

class OrangeSolutionTest(BaseSolutionsTest):
    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(OrangeSolutionTest, cls).setUpClass()
        #Can update deployment path based on variable.
        cls.deploy_path=os.getenv('DEPLOYMENT_PATH',
                            'serial_scripts/solution/topology/mini_deployment/')
        cls.setup_vepg()

    @classmethod
    def tearDownClass(cls):
        cls.delete_vepg()
        super(OrangeSolutionTest, cls).tearDownClass()

    @classmethod
    def setup_vepg(cls):

    #Quota Create.
        cls.quota_env_file=cls.deploy_path+"env/quota.yaml"
        with open(cls.quota_env_file, 'r') as fd:
            cls.quota_env = yaml.load(fd, Loader=yaml.FullLoader)

        cls.quota_template_file=cls.deploy_path+"template/quota.yaml"
        with open(cls.quota_template_file, 'r') as fd:
            cls.quota_template = yaml.load(fd, Loader=yaml.FullLoader)

        #Update env with project name.
        cls.quota_env['parameters']['project'] = cls.connections.project_name
        cls.quota_stack = HeatStackFixture(
                              connections=cls.connections,
                              stack_name=cls.connections.project_name+'_quota',
                              template=cls.quota_template, env=cls.quota_env)
        cls.quota_stack.setUp()

    #Image Upload.
        cls.vrp_image = cls.nova_h.get_image('VRP-IMAGE')
        cls.vsfo_cp_image = cls.nova_h.get_image('VSFO-CP-IMAGE')
        cls.vsfo_up_image = cls.nova_h.get_image('VSFO-UP-IMAGE')

    #Flavor Create.
        cls.flavors_template_file=cls.deploy_path+"template/flavors.yaml"
        with open(cls.flavors_template_file, 'r') as fd:
            cls.flavors_template = yaml.load(fd, Loader=yaml.FullLoader)

        cls.flavors_stack = HeatStackFixture(
                              connections=cls.connections,
                              stack_name=cls.connections.project_name+'_flavors',
                              template=cls.flavors_template)
        cls.flavors_stack.setUp()

    #AZ Create.
        cls.agg_id = {}
        if not cls.inputs.dpdk_ips:
            cls.agg_id['kernel-computes'] = cls.connections.orch.create_agg(
                                                'kernel-computes',
                                                'kernel-computes')
            host_list = cls.connections.orch.get_hosts()
            cls.nova_hosts = copy.deepcopy(host_list)
            cls.connections.orch.add_host_to_agg(cls.agg_id['kernel-computes'],
                                                 cls.nova_hosts)
        else:
            cls.agg_id['kernel-computes'] = cls.connections.orch.create_agg(
                                                'kernel-computes',
                                                'kernel-computes')
            cls.agg_id['dpdk-computes'] = cls.connections.orch.create_agg(
                                              'dpdk-computes',
                                              'dpdk-computes')
            host_list = cls.connections.orch.get_hosts()
            cls.dpdk_hosts = [cls.inputs.host_data[host]['name'] \
                                 for host in cls.inputs.dpdk_ips]
            cls.nova_hosts = copy.deepcopy(host_list)
            for host in host_list:
                if host in cls.dpdk_hosts:
                    cls.nova_hosts.remove(host)
            cls.connections.orch.add_host_to_agg(cls.agg_id['kernel-computes'],
                                                 cls.nova_hosts)    
            cls.connections.orch.add_host_to_agg(cls.agg_id['dpdk-computes'],
                                                 cls.dpdk_hosts)    

    #Floating IP creation.
    #TBD. For now setting this know to false, just as a place holder.
        cls.fip = False

    #Create VEPG.
        if cls.fip == True:
            cls.vepg_env_file=cls.deploy_path+"env/vepg_fip_details.yaml"
            with open(cls.vepg_env_file, 'r') as fd:
                cls.vepg_env = yaml.load(fd, Loader=yaml.FullLoader)

            cls.vepg_template_file=cls.deploy_path+"template/vepg_b2b_main.yaml"
            with open(cls.vepg_template_file, 'r') as fd:
                cls.vepg_template = yaml.load(fd, Loader=yaml.FullLoader)

            for each_resource in cls.vepg_template['resources']:
                if 'personality' in cls.vepg_template['resources']\
                                        [each_resource]['properties']:
                    inject_file='/config/junos-config/configuration.txt'
                    fp1=open(cls.vepg_template['resources'][each_resource]\
                                 ['properties']['personality'][inject_file]\
                                 ['get_file'], 'r')
                    data=fp1.read()
                    cls.vepg_template['resources'][each_resource]['properties']\
                        ['personality'][inject_file]=data
                    fp1.close()

            cls.vepg_stack = HeatStackFixture(
                                 connections=cls.connections,
                                 stack_name=cls.connections.project_name+'_vepg',
                                 template=cls.vepg_template, env=cls.vepg_env,
                                 timeout_mins=15)
            cls.vepg_stack.setUp()
        else:
            cls.vepg_template_file=cls.deploy_path+"template/vepg_b2b_main.yaml"
            with open(cls.vepg_template_file, 'r') as fd:
                cls.vepg_template = yaml.load(fd, Loader=yaml.FullLoader)

            for each_resource in cls.vepg_template['resources']:
                if 'personality' in cls.vepg_template['resources']\
                                        [each_resource]['properties']:
                    inject_file='/config/junos-config/configuration.txt'
                    fp1=open(cls.vepg_template['resources'][each_resource]\
                                 ['properties']['personality'][inject_file]\
                                 ['get_file'], 'r')
                    data=fp1.read()
                    cls.vepg_template['resources'][each_resource]['properties']\
                        ['personality'][inject_file]=data
                    fp1.close()
 
            cls.vepg_stack = HeatStackFixture(
                                 connections=cls.connections,
                                 stack_name=cls.connections.project_name+'_vepg',
                                 template=cls.vepg_template,
                                 timeout_mins=15)
            cls.vepg_stack.setUp()

    # Create BGPaaS stacks.
        #Define variables for template file, env file, bgpaas stack and
        #bfd_health_check_uuid
        cls.bgpaas_stack_status=True
        cls.bgpaas_env_f=glob.glob(cls.deploy_path+'env/VEPG_BGP*')
        cls.bgpaas_template_f=[]
        cls.bgpaas_env={}
        cls.bgpaas_template={}
        cls.bfd_hc_uuid=None
        cls.bgpaas_stacks={}
        #Get bfd_health_check_uuid from the vepg stack created earlier.
        for list_item in cls.vepg_stack.heat_client_obj.stacks.get(
                                            cls.vepg_stack.stack_name).outputs:
            if list_item['output_key'] == 'bfd_health_check':
                cls.bfd_hc_uuid=list_item['output_value']
        #Fail if no bfd_health_check_uuid received.
        if not cls.bfd_hc_uuid:
            self.logger.error("No BFD Health check uuid found !!!")
            cls.bgpaas_stack_status=False
            return False
        #Create BGPaaS stack for each template file using corresponding env file
        #from env dir.
        for each_bef in cls.bgpaas_env_f:
            with open(each_bef, 'r') as fd:
                cls.bgpaas_env[each_bef] = yaml.load(fd, Loader=yaml.FullLoader)
            t1=re.findall("VSFO\d", each_bef)
            t2=re.findall("EXT\d", each_bef)
            #for each of the env file create vsfo_key to get vsfo uuid from
            #vepg stack.
            vsfo_key=t1[0].lower()[:4]+'_'+t1[0].lower()[4:]+'_'+\
                         t2[0].lower()[:3]+'_'+t2[0].lower()[3:]
            vsfo_uuid=None
            for list_item in cls.vepg_stack.heat_client_obj.stacks.get(
                                            cls.vepg_stack.stack_name).outputs:
                if list_item['output_key'] == vsfo_key:
                    #get vsfo uuid to be updated in env file
                    vsfo_uuid=list_item['output_value']
                    break
            vsfo_env_key=None
            #get the vsfo key name from env file that needs to be updated with
            #the uuid.
            for key, value in cls.bgpaas_env[each_bef]['parameters'].items():
                if 'vsfo' in key:
                    vsfo_env_key=key
            #update the bfd_health_check_uuid in env file.
            cls.bgpaas_env[each_bef]['parameters']['bfd_health_check_uuid']=\
                                                                cls.bfd_hc_uuid
            #update the vsfo_env_key in env file.
            cls.bgpaas_env[each_bef]['parameters'][vsfo_env_key]=vsfo_uuid
            #create string to find relevant template files for this
            #environment file.
            t=t1[0].lower()+'_'+t2[0].lower()
            cls.bgpaas_template_f=glob.glob(cls.deploy_path+'template/'+t+'*')
            #Create BGPaaS stack for each template file for this env.
            for each_btf in cls.bgpaas_template_f:
                #generate stack name based on env file name and number of APN's.
                stack_name=re.findall('VEPG\w*',each_bef)[0]+\
                               re.findall('apn_\d*_\d*',each_btf)[0][3:]
                with open(each_btf, 'r') as fd:
                    cls.bgpaas_template[each_btf] = yaml.load(fd,
                                                        Loader=yaml.FullLoader)
                cls.bgpaas_stacks[stack_name] = HeatStackFixture(
                                                    connections=cls.connections,
                                                    stack_name=stack_name,
                                                    template=cls.bgpaas_template[each_btf],
                                                    env=cls.bgpaas_env[each_bef],
                                                    timeout_mins=10)
                cls.bgpaas_stacks[stack_name].setUp()

    #end setup_vepg

    @classmethod
    def delete_vepg(cls):
        for each_stack in cls.bgpaas_stacks:
            cls.bgpaas_stacks[each_stack].cleanUp()

        #Delete vepg Stack
        cls.vepg_stack.cleanUp()

        #Delete AZ
        cls.connections.orch.del_host_from_agg(cls.agg_id['kernel-computes'],
                                               cls.nova_hosts)
        cls.connections.orch.delete_agg(cls.agg_id['kernel-computes'])
        if 'dpdk_hosts' in dir(cls):
            cls.connections.orch.del_host_from_agg(cls.agg_id['dpdk-computes'],
                                                   cls.dpdk_hosts)
            cls.connections.orch.delete_agg(self.agg_id['dpdk-computes']) 

        #Delete Flavor Stack
        cls.flavors_stack.cleanUp()

        #Delete Quota Stack
        cls.quota_stack.cleanUp()
        time.sleep(10)
        return True
    #end delete_vepg

    @preposttest_wrapper
    def test_orange_deploy(self):
        ''' Test to validate orange solution deployment.
        '''
        result = True
        self.logger.info("Running test orange deployment.")
        self.logger.info(self.connections.project_name)
        self.logger.info(self.connections.username)

        sleep(10)
        self.logger.info("DONE... Sleeping for 10 secs.")
        return True
    # end test_orange_deploy

    @preposttest_wrapper
    def test_orange_d(self):
        ''' Test to validate orange solution a.
        '''
        result = True
        self.logger.info("Running test orange solution D.")
        self.logger.info("Sleeping for 10 secs.")
        sleep(10)
        self.logger.info("DONE... Sleeping for 10 secs.")
        return True
    # end test_orange_d

    @preposttest_wrapper
    def test_orange_b(self):
        ''' Test to validate orange solution a.
        '''
        result = True
        self.logger.info("Running test orange solution B.")
        self.logger.info("Sleeping for 10 secs.")
        sleep(10)
        self.logger.info("DONE... Sleeping for 10 secs.")
        return True
    # end test_orange_b

    @preposttest_wrapper
    def test_orange_c(self):
        ''' Test to validate orange solution a.
        '''
        result = True
        self.logger.info("Running test orange solution C.")
        self.logger.info("Sleeping for 10 secs.")
        sleep(10)
        self.logger.info("DONE... Sleeping for 10 secs.")
        return True
    # end test_orange_c

    @preposttest_wrapper
    def test_orange_e(self):
        ''' Test to validate orange solution a.
        '''
        result = True
        self.logger.info("Running test orange solution E.")
        self.logger.info("Sleeping for 10 secs.")
        sleep(10)
        self.logger.info("DONE... Sleeping for 10 secs.")
        return True
    # end test_orange_e

    @preposttest_wrapper
    def test_orange_f(self):
        ''' Test to validate orange solution a.
        '''
        result = True
        self.logger.info("Running test orange solution F.")
        self.logger.info("Sleeping for 10 secs.")
        sleep(10)
        self.logger.info("DONE... Sleeping for 10 secs.")
        return True
    # end test_orange_f

    @preposttest_wrapper
    def test_orange_h(self):
        ''' Test to validate orange solution a.
        '''
        result = True
        self.logger.info("Running test orange solution H.")
        self.logger.info("Sleeping for 10 secs.")
        sleep(10)
        self.logger.info("DONE... Sleeping for 10 secs.")
        return True
    # end test_orange_h

    @preposttest_wrapper
    def test_orange_g(self):
        ''' Test to validate orange solution a.
        '''
        result = True
        self.logger.info("Running test orange solution G.")
        self.logger.info("Sleeping for 10 secs.")
        sleep(10)
        self.logger.info("DONE... Sleeping for 10 secs.")
        return True
    # end test_orange_g

#end class OrangeSolutionTest
