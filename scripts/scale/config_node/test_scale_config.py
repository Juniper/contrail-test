import os
import sys
import time
import argparse
import unittest
import traceback
from fabric.api import local, run

sys.path.append(os.path.realpath('../fixtures'))
sys.path.append(os.path.realpath('../scripts'))
from tcutils.util import *
from vm_test import *
from vn_test import *
from ipam_test import *
from policy_test import *
from project_test import *
from security_group import *
from common.contrail_test_init import ContrailTestInit
from tcutils.wrappers import preposttest_wrapper   
from keystoneclient.v2_0 import client as ksclient
from vnc_api import vnc_api
from scale.config_node.base import BaseScaleTest

import test

class TestScale(BaseScaleTest):
    def __init__(self, testname=None, tenants=1, ipams=1, vns=1, policies=1, vms=1, rules=1, sgs=1):
        if testname:
            super(TestScale, self).__init__(testname)
        self.dummy_tap_open = {}
        self.n_tenants = tenants
        self.n_ipams = ipams
        self.n_vns = vns
        self.n_policies = policies
        self.n_vms = vms
        self.n_rules = rules
        self.n_sgs = sgs

    @classmethod
    def setUpClass(cls):
        super(TestScale, cls).setUpClass()
        cls.auth_url = 'http://%s:5000/v2.0' % (cls.inputs.openstack_ip)
        cls.keystone = ksclient.Client(username=cls.inputs.stack_user,
                                        password=cls.inputs.stack_password,
                                        tenant_name=cls.inputs.project_name,
                                        auth_url=cls.auth_url)

    @classmethod
    def tearDownClass(cls):
        super(TestScale, cls).tearDownClass()

    def scale_test_common (self):
        n_tenants= self.n_tenants
        n_ipams= self.n_ipams
        n_vns= self.n_vns
        n_vms= self.n_vms
        n_rules= self.n_rules
        n_policies= self.n_policies
        n_sgs= self.n_sgs

        self.cleanup_before_test()

        project_fixture_list= []
        ipam_fixture_list= []
        policy_fixture_list= []
        vn_fixture_list= []
        vm_fixture_list= []
        sg_fixture_list= []
        self.user = self.get_user_dict()
        self.role = self.get_role_dict()

        start=1
        try:
            for i in range(start, start+n_tenants):

    # Temp hack for memcached issue
                if i%512 == 0:
                    self.inputs.restart_service('memcached')
                    time.sleep(15)

    # Create Project
                project_name= 'project%s'%i
                project_fixture= self.useFixture(ProjectFixture(
                                                 vnc_lib_h= self.vnc_lib,
                                                 project_name= project_name,
                                                 connections= self.connections,
                                                 scale= True))
                project_fixture_list.append(project_fixture)

    # Add admin user to project and get new connection info
                self.keystone= project_fixture.kc
                self.add_user_to_tenant(project_fixture)
                project_connections= project_fixture.get_project_connections(
                                         username=self.inputs.stack_user,
                                         password=self.inputs.stack_password)

    # Create security group
                sg_name_list= []
                for sg_index in range(n_sgs):
                    sg_name = 'SG%s-%s' %(sg_index, project_name)
                    rule_list = []
                    for rule_index in range(n_rules):
                        port = (sg_index*n_rules+rule_index-sg_index)%65535
                        protocol = 'udp'
                        rule_list.append({
                                  'direction' : '>',
                                  'protocol'  : protocol,
                                  'dst_ports' : [{'start_port': port,
                                                  'end_port': port}],
                                  'src_ports' : [{'start_port': port,
                                                  'end_port': port}],
                                  'src_addresses': [{
                                      'security_group': 'local'}],
                                  'dst_addresses': [{
                                          'subnet': {
                                          'ip_prefix': '10.1.1.0',
                                          'ip_prefix_len': 24}}],
                                          })
                    sg_fixture = self.useFixture(SecurityGroupFixture(
                                                 self.inputs,
                                                 self.connections,
                                                 self.inputs.domain_name,
                                                 project_name,
                                                 secgrp_name=sg_name,
                                                 secgrp_entries=rule_list))
                    sg_fixture_list.append(sg_fixture)
                    sg_name_list.append(sg_name)

    # Create IPAM
                for ipam_index in range(n_ipams):
                    ipam_name= 'ipam%s-%s'%(ipam_index, project_name)

                    ipam_fixture = self.useFixture(IPAMFixture(
                                                   project_obj= project_fixture,
                                                   name= ipam_name))
                    self.logger.info("Created ipam %s on %s" %(
                                           ipam_name, project_name))
                    ipam_fixture_list.append(ipam_fixture)

    # Create VN
                    for vn_index in range(n_vns):
                        vn_name = 'VN%s-ipam%s-%s' %(
                                      vn_index, ipam_index, project_name)
                        second_octet = vn_index/255
                        third_octet = vn_index%255
                        vn_subnet = '%s.%s.%s.0/24' %(
                                      i%223 + 1, second_octet, third_octet)

    # Create Policies and Rules
                        policy_objs_list = []
                        for policy_index in range(n_policies):
                            policy_name = 'policy%s-VN%s-ipam%s-%s' %(
                                           policy_index, vn_index, ipam_index, project_name)
                            rule_list = [{ 'direction'     : '<>',
                                           'simple_action' : 'pass',
                                           'protocol'      : 'icmp',
                                           'source_network': 'any',
                                           'dest_network'  : 'any',
                                        }]
                            for rule_index in range(1, n_rules):
                                port = (policy_index * n_rules + rule_index
                                                     - policy_index)%65535
                                protocol = 'udp'
                                rule_list.append( {
                                                  'direction' : '<>',
                                                  'simple_action' : 'pass',
                                                  'protocol'  : protocol,
                                                  'dst_ports' : [port, port],
                                                  'src_ports' : [port, port],
                                                  'source_network': 'any',
                                                  'dest_network'  : 'any',
                                                  } )
                            policy_fixture = self.useFixture(PolicyFixture(
                                               policy_name= policy_name,
                                               rules_list= rule_list,
                                               inputs= self.inputs,
                                               connections= project_connections,
                                               project_fixture=project_fixture))
                            policy_objs_list.append(policy_fixture.policy_obj)
                            policy_fixture_list.append(policy_fixture)
                            self.logger.info("Created Policy %s with %d rules"%(
                                                          policy_name, n_rules))

                        vn_fixture = self.useFixture( VNFixture(
                                             project_name= project_name,
                                             connections= project_connections,
                                             vn_name= vn_name,
                                             inputs= self.inputs,
                                             subnets= [vn_subnet],
                                             policy_objs= policy_objs_list,
                                             ipam_fq_name= ipam_fixture.fq_name,
                                             project_obj= project_fixture ))
                        vn_fixture_list.append(vn_fixture)

    # Create VMs
                        for vm_index in range(n_vms):
                            vm_name = 'VM%s-VN%s-ipam%s-%s' %(vm_index,
                                            vn_index, ipam_index, project_name)
                            vm_fixture = self.useFixture( VMFixture(
                                            connections= project_connections,
                                            vn_obj=vn_fixture.obj,
                                            project_fixture= project_fixture,
                                            vm_name= vm_name,
                                            flavor= 'm1.small',
                                            node_name='disable',
                                            project_name= project_name))
                            vm_fixture_list.append(vm_fixture)
    # Assign Floating IP

        except:
            et, ei, tb = sys.exc_info()
            formatted_traceback = ''.join(traceback.format_tb(tb))
            test_fail_trace = '\n{0}\n{1}:\n{2}'.format(formatted_traceback,
                                                  et.__name__, ei.message)
            print test_fail_trace
    #        import pdb; pdb.set_trace()

        self.logger.info("\n\nBeen successful configuring %s Projects,\
                          %s ipams, %s polices, %s policy rules, %s SGs,\
                          %s SG rules, %s VNs and %s VMs\n\n" %(
                         len(project_fixture_list),
                         len(ipam_fixture_list),
                         len(policy_fixture_list),
                         len(policy_fixture_list)*n_rules,
                         len(sg_fixture_list),
                         len(sg_fixture_list)*n_rules,
                         len(vn_fixture_list),
                         len(vm_fixture_list)))

    # Enable Tap Interface
        vm_index=0
        for vm_fixture in vm_fixture_list:
            self.enable_tap_interface(vm_fixture)
            if n_sgs:
                vm_fixture.add_security_group(
                    secgrp=sg_name_list[vm_index%n_sgs])
            vm_index +=1

    # Verification Routines
        for project_fixture in project_fixture_list:
            assert project_fixture.verify_on_setup()
        for policy_fixture in policy_fixture_list:
            assert policy_fixture.verify_on_setup()
        for sg_fixture in sg_fixture_list:
            assert sg_fixture.verify_on_setup()
        for vn_fixture in vn_fixture_list:
            assert vn_fixture.verify_on_setup()
        import pdb; pdb.set_trace()
        for vm_fixture in vm_fixture_list:
            assert vm_fixture.verify_on_setup()

        return True
    #end scale_test_common

    @preposttest_wrapper
    def scale_test_custom (self):
        ''' Custom openstack scale test routine
            Use python <script_name> -h for more info
        '''
        self.scale_test_common()
    #end scale_test_custom

    @preposttest_wrapper
    def test_scale_tenant (self):
        ''' Scale testing for max no of tenants supported by Contrail+Openstack
        '''
        self.n_tenants = 8192
        self.n_ipams = 0
        self.n_vns = 0
        self.n_policies = 0
        self.n_rules = 0
        self.n_vms = 0
        self.n_sgs = 0
        self.scale_test_common()
    #end test_scale_tenant

    @preposttest_wrapper
    def test_scale_ipams (self):
        ''' Scale testing for max no of ipams supported by Contrail+Openstack
        '''
        self.n_tenants = 1024
        self.n_ipams = 64
        self.n_vns = 0
        self.n_policies = 0
        self.n_rules = 0
        self.n_vms = 0
        self.n_sgs = 0
        self.scale_test_common()
    #end test_scale_ipams

    @preposttest_wrapper
    def test_scale_vns (self):
        ''' Scale testing for max no of virtual-networks
            supported by Contrail+Openstack
        '''
        self.n_tenants = 16
        self.n_ipams = 1
        self.n_vns = 1024
        self.n_policies = 0
        self.n_vms = 0
        self.n_sgs = 0
        self.scale_test_common()
    #end test_scale_vns

    @preposttest_wrapper
    def test_scale_policies (self):
        ''' Scale testing for max no of policies
            supported by Contrail+Openstack
        ''' 
        self.n_tenants = 16
        self.n_ipams = 1
        self.n_vns = 16
        self.n_policies = 128
        self.n_vms = 0
        self.n_sgs = 0
        self.scale_test_common()
    #end test_scale_policies

    @preposttest_wrapper  
    def test_scale_policies_rules (self):
        ''' Scale testing for max no of rules supported by Contrail+Openstack
        '''
        self.n_tenants = 16
        self.n_ipams = 1
        self.n_vns = 16
        self.n_policies = 128
        self.n_rules = 128
        self.n_vms = 0
        self.n_sgs = 0
        self.scale_test_common()
    #end test_scale_policies_rules

    @preposttest_wrapper    
    def test_scale_sgs (self):
        ''' Scale testing for max no of Security Groups
            supported by Contrail+Openstack
        '''
        self.n_tenants = 128
        self.n_ipams = 1
        self.n_vns = 1
        self.n_sgs = 1024
        self.n_rules = 1
        self.n_vms = 0
        self.n_policies = 0
        self.scale_test_common()
    #end test_scale_sgs

    @preposttest_wrapper
    def test_scale_vms (self):
        ''' Scale testing for max no of VMs supported by Contrail+Openstack
        '''
        self.n_tenants = 512
        self.n_ipams = 1
        self.n_vns = 8
        self.n_sgs = 0
        self.n_rules = 0
        self.n_vms = 16
        self.n_policies = 0
        self.scale_test_common()
    #end test_scale_vms

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tenants', default='1')
    parser.add_argument('--ipams', default='1')
    parser.add_argument('--vns', default='1')
    parser.add_argument('--policies', default='1')
    parser.add_argument('--vms', default='1')
    parser.add_argument('--rules', default='1')
    parser.add_argument('--sgs', default='0')
    parser.add_argument('unittest_args', nargs='*')
    args = parser.parse_args()
    sys.argv[1:] = args.unittest_args

    '''
    os.environ['SCRIPT_TS']= time.strftime("%Y_%m_%d_%H_%M_%S")
    if 'PARAMS_FILE' in os.environ :
        ini_file= os.environ.get('PARAMS_FILE')
    else:
        ini_file= '../../sanity_params.ini'
    inputs= ContrailTestInit( ini_file)
    inputs.setUp()
    file_to_send= inputs.log_file
    '''

    suite= unittest.TestSuite()
    test_result= unittest.TestResult()
    suite.addTest(TestScale('scale_test_custom',
                            tenants= int(args.tenants),
                            ipams= int(args.ipams),
                            vns= int(args.vns),
                            policies= int(args.policies),
                            rules= int(args.rules),
                            vms= int(args.vms),
                            sgs= int(args.sgs)))
    unittest.TextTestRunner().run(suite)

