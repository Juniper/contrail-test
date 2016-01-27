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
from vn_test import *
from vm_test import *
from policy_test import *
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
from fabric.api import run, local
from analytics import base
import fixtures

import test

class AnalyticsBasicTestSanity(base.AnalyticsBaseTest):

    @classmethod
    def setUpClass(cls):
        super(AnalyticsBasicTestSanity, cls).setUpClass()

    def runTest(self):
        pass
    #end runTest

    @test.attr(type=['sanity', 'ci_sanity', 'vcenter'])
    @preposttest_wrapper
    def test_verify_object_logs(self):
        '''
          Description: Test to validate object logs
              1.Create vn/vm and verify object log tables updated with those vn/vm - fails otherwise
          Maintainer: sandipd@juniper.net
        '''
        vn_name='vn22'
        vn_subnets=['22.1.1.0/24']
        vm1_name='vm_test'
        start_time=self.analytics_obj.getstarttime(self.inputs.cfgm_ip)
        vn_fixture= self.useFixture(VNFixture(project_name= self.inputs.project_name, connections= self.connections,
                     vn_name=vn_name, inputs= self.inputs, subnets= vn_subnets))
        vn_obj= vn_fixture.obj
        vm1_fixture= self.useFixture(VMFixture(connections= self.connections,
                vn_obj=vn_obj, vm_name= vm1_name, project_name= self.inputs.project_name))
        #getting vm uuid
        assert vm1_fixture.verify_on_setup()
        vm_uuid=vm1_fixture.vm_id
        self.logger.info("Waiting for logs to be updated in the database...")
        time.sleep(20)
        query='('+'ObjectId=%s)'%vn_fixture.vn_fq_name
        result=True
        self.logger.info("Verifying ObjectVNTable through opserver %s.."%(self.inputs.collector_ips[0]))
        res2=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query('ObjectVNTable',
                                                                                start_time=start_time,end_time='now'
                                                                                ,select_fields=['ObjectId', 'Source',
                                                                                'ObjectLog', 'SystemLog','Messagetype',
                                                                                'ModuleId','MessageTS'],
                                                                                 where_clause=query)
        self.logger.info("query output : %s"%(res2))
        if not res2:
            st=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].send_trace_to_database\
                                 (node= self.inputs.collector_names[0], module= 'QueryEngine',trace_buffer_name= 'QeTraceBuf')
            self.logger.info("status: %s"%(st))
        assert res2

        self.logger.info("Getting object logs for vm")
        query='('+'ObjectId='+ vm_uuid +')'
        self.logger.info("Verifying ObjectVMTable through opserver %s.."%(self.inputs.collector_ips[0]))
        res1=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query('ObjectVMTable',
                                                                                start_time=start_time,end_time='now'
                                                                                ,select_fields=['ObjectId', 'Source',
                                                                                'ObjectLog', 'SystemLog','Messagetype',
                                                                                'ModuleId','MessageTS'],
                                                                                 where_clause=query)
        self.logger.info("query output : %s"%(res1))
        if not res1:
            st=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].send_trace_to_database\
                         (node= self.inputs.collector_names[0], module= 'QueryEngine',trace_buffer_name= 'QeTraceBuf')
            self.logger.info("status: %s"%(st))
        assert res1

        self.logger.info("Getting object logs for ObjectRoutingInstance table")
#        object_id=self.inputs.project_fq_name[0]+':'+self.inputs.project_fq_name[1]+vn_name+':'+vn_name
        object_id='%s:%s:%s:%s'%(self.inputs.project_fq_name[0],self.inputs.project_fq_name[1],vn_name,vn_name)
#        query='('+'ObjectId=default-domain:admin:'+vn_name+')'
        query='(ObjectId=%s)'%(object_id)

        self.logger.info("Verifying ObjectRoutingInstance through opserver %s.."%(self.inputs.collector_ips[0]))
        res1=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query('ObjectRoutingInstance',
                                                                                start_time=start_time,end_time='now'
                                                                                ,select_fields=['ObjectId', 'Source',
                                                                                'ObjectLog', 'SystemLog','Messagetype',
                                                                                'ModuleId','MessageTS'],
                                                                                 where_clause=query)
        self.logger.info("query output : %s"%(res1))
        if not res1:
            self.logger.warn("ObjectRoutingInstance  query did not return any output")
            st=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].send_trace_to_database\
                         (node= self.inputs.collector_names[0], module= 'QueryEngine',trace_buffer_name= 'QeTraceBuf')
            self.logger.info("status: %s"%(st))
        assert res1
        return True
