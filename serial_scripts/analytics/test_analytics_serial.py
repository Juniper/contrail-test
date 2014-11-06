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

class AnalyticsTestSanity(base.AnalyticsBaseTest):

    @classmethod
    def setUpClass(cls):
        super(AnalyticsTestSanity, cls).setUpClass()
    
    def runTest(self):
        pass
    #end runTest
    
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
        assert vm1_fixture.wait_till_vm_is_up()
        vm_uuid=vm1_fixture.vm_id
        self.logger.info("Waiting for logs to be updated in the database...")
        time.sleep(10)
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
    
    @preposttest_wrapper
    def test_verify_xmpp_peer_object_logs(self):
        ''' Test to validate xmpp peer object logs 
        '''
        result = True
        try:
            start_time=self.analytics_obj.getstarttime(self.inputs.compute_ips[0])
            object_id= self.inputs.bgp_names[0]+':'+self.inputs.compute_ips[0]
            query='('+'ObjectId='+ object_id +')'
            self.logger.info("Stopping the xmpp node in %s"%(self.inputs.compute_ips[0]))
            self.inputs.stop_service('contrail-vrouter',[self.inputs.compute_ips[0]])
            self.logger.info("Waiting for the logs to be updated in database..")
            time.sleep(20)
            self.logger.info("Verifying ObjectXmppPeerInfo Table through opserver %s.."%(self.inputs.collector_ips[0]))    
            self.res1=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query('ObjectXmppPeerInfo',
                                                                                start_time=start_time,end_time='now'
                                                                                ,select_fields=['ObjectId', 'Source',
                                                                                'ObjectLog', 'SystemLog','Messagetype',
                                                                                'ModuleId','MessageTS'],
                                                                                 where_clause=query)
#            self.logger.info("query output : %s"%(self.res1))
            if not self.res1:
                self.logger.info("query output : %s"%(self.res1))
                st=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].send_trace_to_database\
			 (node= self.inputs.collector_names[0], module= 'QueryEngine',trace_buffer_name= 'QeTraceBuf')
                self.logger.info("status: %s"%(st))
                result = result and False
                        
            start_time=self.analytics_obj.getstarttime(self.inputs.compute_ips[0])
            time.sleep(2)
            self.inputs.start_service('contrail-vrouter',[self.inputs.compute_ips[0]])
            self.logger.info("Waiting for the logs to be updated in database..")
            time.sleep(30)
            self.logger.info("Verifying ObjectXmppPeerInfo Table through opserver %s.."%(self.inputs.collector_ips[0]))    
            self.res1=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query('ObjectXmppPeerInfo',
                                                                                start_time=start_time,end_time='now'
                                                                                ,select_fields=['ObjectId', 'Source',
                                                                                'ObjectLog', 'SystemLog','Messagetype',
                                                                                'ModuleId','MessageTS'],
                                                                                 where_clause=query)
#            self.logger.info("query output : %s"%(self.res1))
            if not self.res1:
                self.logger.info("query output : %s"%(self.res1))
                st=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].send_trace_to_database\
			 (node= self.inputs.collector_names[0], module= 'QueryEngine',trace_buffer_name= 'QeTraceBuf')
                self.logger.info("status: %s"%(st))
                result = result and False
                     
        except Exception as e:
            print e
            result=result and False
        finally:
#            start_time=self.analytics_obj.getstarttime(self.inputs.compute_ips[0])
            self.inputs.start_service('contrail-vrouter',[self.inputs.compute_ips[0]])
            time.sleep(20)
            self.logger.info("Verifying ObjectVRouter Table through opserver %s.."%(self.inputs.collector_ips[0]))    
            object_id= self.inputs.compute_names[0]
            query='('+'ObjectId='+ object_id +')'
            self.res1=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query('ObjectVRouter',
                                                                                start_time=start_time,end_time='now'
                                                                                ,select_fields=['ObjectId', 'Source',
                                                                                'ObjectLog', 'SystemLog','Messagetype',
                                                                                'ModuleId','MessageTS'],
                                                                                 where_clause=query)
            if (self.res1):
                self.logger.info("ObjectVRouter table query passed")
                result = result and True
                self.logger.info("Query output: %s"%(self.res1))
            else:
                self.logger.warn("ObjectVRouter table query failed")
                result = result and False
                
                
            assert result
            return True
