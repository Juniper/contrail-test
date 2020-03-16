from analytics import base
from builtins import str
from builtins import range
import os
import datetime
import time
from vn_test import *
from vm_test import *
from tcutils.wrappers import preposttest_wrapper
import test
from tcutils.collector.opserver_util import OpServerUtils

class AnalyticsBasicTestSanity(base.AnalyticsBaseTest):

    @classmethod
    def setUpClass(cls):
        super(AnalyticsBasicTestSanity, cls).setUpClass()

    def runTest(self):
        pass
    #end runTest

    @test.attr(type=['sanity', 'ci_sanity', 'vcenter', 'suite1', 'vcenter_compute'])
    @preposttest_wrapper
    def test_verify_object_logs(self):
        '''
          Description: Test to validate object logs
              1.Create vn/vm and verify object log tables updated with
                those vn, vm and routing-instance - fails otherwise
          Maintainer: sandipd@juniper.net
        '''
        vn_name=get_random_name('vn22')
        vn_subnets=[get_random_cidr()]
        start_time=str(OpServerUtils.utc_timestamp_usec())
        vn_fixture= self.useFixture(VNFixture(connections=self.connections,
                                    vn_name=vn_name, subnets=vn_subnets))
        vm1_fixture = self.create_vm(vn_fixture=vn_fixture, image_name='cirros')
        assert vm1_fixture.wait_till_vm_is_active()
        vm_uuid=vm1_fixture.vm_id
        query='('+'ObjectId=%s)'%vn_fixture.vn_fq_name
        result=True
        msg = "ObjectVNTable for vn %s on analytics node %s"%(
              vn_fixture.vn_fq_name, self.inputs.collector_ips[0])
        self.logger.debug("Verifying %s"%msg)
        res2 = self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]
                                             ].post_query('ObjectVNTable',
                                             start_time=start_time,
                                             end_time='now',
                                             select_fields=['ObjectId',
                                             'Source', 'ObjectLog',
                                             'SystemLog','Messagetype',
                                             'ModuleId','MessageTS'],
                                             where_clause=query)
        self.logger.debug("Query output : %s"%(res2))
        if not res2:
            st=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]
                                  ].send_trace_to_database(
                                  node=self.inputs.collector_names[0],
                                  module='contrail-query-engine',
                                  trace_buffer_name='QeTraceBuf')
            self.logger.debug("Status: %s"%(st))
        assert res2, "Verification of %s failed"%msg

        for i in range(2):
            query='('+'ObjectId='+ vm_uuid +')'
            msg = "ObjectVMTable for vm %s on analytics node %s"%(
                  vm_uuid, self.inputs.collector_ips[0])
            self.logger.debug("Verifying %s"%msg)
            res1=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]
                                           ].post_query('ObjectVMTable',
                                           start_time=start_time,end_time='now',
                                           select_fields=['ObjectId','Source',
                                           'ObjectLog','SystemLog','ModuleId',
                                           'Messagetype','MessageTS'],
                                           where_clause=query)
            self.logger.debug("Query output : %s"%(res1))
            if not res1:
                st=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]
                                  ].send_trace_to_database(
                                  node=self.inputs.collector_names[0],
                                  module='contrail-query-engine',
                                  trace_buffer_name='QeTraceBuf')
                self.logger.debug("status: %s"%(st))
                self.sleep(5)
                continue

            object_id='%s:%s:%s:%s'%(self.inputs.project_fq_name[0],
                                     self.inputs.project_fq_name[1],
                                     vn_name, vn_name)
            query='(ObjectId=%s)'%(object_id)

            msg = "ObjectRoutingInstance for RI %s on analytics node %s"%(
                  object_id, self.inputs.collector_ips[0])
            self.logger.debug("Verifying %s"%msg)
            res1=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]
                                           ].post_query('ObjectRoutingInstance',
                                           start_time=start_time,end_time='now'
                                           ,select_fields=['ObjectId', 'Source',
                                           'ObjectLog', 'SystemLog','ModuleId',
                                           'Messagetype','MessageTS'],
                                           where_clause=query)
            self.logger.debug("Query output : %s"%(res1))
            if not res1:
                st=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]
                                  ].send_trace_to_database(
                                  node=self.inputs.collector_names[0],
                                  module='contrail-query-engine',
                                  trace_buffer_name='QeTraceBuf')
                self.logger.debug("Status: %s"%(st))
                self.sleep(5)
                continue
        assert res1, "Verification of %s failed"%msg
        self.logger.info('Validated ObjectVNTable, ObjectRoutingInstance, '
                         'ObjectVMTable logs')
        return True
