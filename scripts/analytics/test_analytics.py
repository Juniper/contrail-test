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

class AnalyticsTestSanity(base.AnalyticsBaseTest):

    @classmethod
    def setUpClass(cls):
        super(AnalyticsTestSanity, cls).setUpClass()
    
    def runTest(self):
        pass
    #end runTest

    @preposttest_wrapper
    def test_bgprouter_uve_for_xmpp_and_bgp_peer_count(self):
        ''' Test bgp-router uve for active xmp/bgpp connections count

        '''
        assert self.analytics_obj.verify_bgp_router_uve_xmpp_and_bgp_count()
        return True
    
    @preposttest_wrapper
    def test_colector_uve_module_sates(self):
        '''Test to validate collector uve.
        '''
        result=True
        process_list = ['contrail-query-engine', 'contrail-analytics-api', 'contrail-collector',
                        'contrail-analytics-nodemgr']
        for process in process_list:
            result = result and self.analytics_obj.verify_collector_uve_module_state\
							(self.inputs.collector_names[0],\
							self.inputs.collector_names[0],process)
        assert result
        return True

    @preposttest_wrapper
    def test_message_table(self):
        '''Test MessageTable.
        '''
        start_time=self.analytics_obj.get_time_since_uptime(self.inputs.cfgm_ip)
        assert self.analytics_obj.verify_message_table(start_time= start_time)
        return True
    
    @preposttest_wrapper
    def test_config_node_uve_states(self):
        '''Test to validate config node uve.
        '''
        result=True
        process_list = ['contrail-discovery', 'contrail-config-nodemgr','rabbitmq-server'
                        ,'contrail-svc-monitor', 'ifmap', 'contrail-api', 'contrail-schema']
        for process in process_list:
            result = result and self.analytics_obj.verify_cfgm_uve_module_state(self.inputs.collector_names[0],
				self.inputs.cfgm_names[0],process)
        assert result
    	return True
    
    @preposttest_wrapper
    def test_object_tables(self):
        '''Test object tables.
        '''
        start_time=self.analytics_obj.get_time_since_uptime(self.inputs.cfgm_ip)
        assert self.analytics_obj.verify_object_tables(start_time= start_time,skip_tables = [u'MessageTable', \
                                                            u'ObjectDns', u'ObjectVMTable', \
                                                            u'ConfigObjectTable', u'ObjectQueryTable', \
                                                            u'ObjectBgpPeer', u'ObjectBgpRouter', u'ObjectXmppConnection',\
                                                             u'ObjectVNTable', u'ObjectGeneratorInfo', u'ObjectRoutingInstance', \
                                                            u'ObjectVRouter', u'ObjectConfigNode', u'ObjectXmppPeerInfo', \
                                                            u'ObjectCollectorInfo'])
 
                                                    
        return True

    @test.attr(type=['sanity', 'ci_sanity'])
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
    def test_verify_hrefs(self):
        ''' Test all hrefs for collector/agents/bgp-routers etc

        '''
        assert self.analytics_obj.verify_hrefs_to_all_uves_of_a_given_uve_type()
        return True

class AnalyticsTestSanity1(base.AnalyticsBaseTest):

    @classmethod
    def setUpClass(cls):
        super(AnalyticsTestSanity1, cls).setUpClass()
    
    def runTest(self):
        pass
    #end runTest
    
    @preposttest_wrapper
    def test_stats_tables(self):
        '''Test object tables.
        '''
        start_time=self.analytics_obj.get_time_since_uptime(self.inputs.cfgm_ip)
        assert self.analytics_obj.verify_stats_tables(start_time= start_time , skip_tables = [u'StatTable.ConfigCpuState.\
                                    cpu_info', u'StatTable.AnalyticsCpuState.cpu_info', u'StatTable.ControlCpuState.cpu_info',\
                                     u'StatTable.QueryPerfInfo.query_stats', u'StatTable.UveVirtualNetworkAgent.vn_stats', \
                                    u'StatTable.SandeshMessageStat.msg_info'])
        return True
    
    @preposttest_wrapper
    def test_uves(self):
        '''Test uves.
        '''
        assert self.analytics_obj.verify_all_uves()
        return True

    @preposttest_wrapper
    def test_verify__bgp_router_uve_up_xmpp_and_bgp_count(self):
        ''' Test bgp-router uve for up bgp peer/xmpp peer count

        '''
        assert self.analytics_obj.verify_bgp_router_uve_up_xmpp_and_bgp_count()
        return True
    
    @preposttest_wrapper
    def test_verify_bgp_peer_object_logs(self):
        ''' Test to validate bgp_peer_object logs 

        '''
        if (len(self.inputs.bgp_ips) < 2):
            self.logger.info("bgp ips less than 2...skipping the test...")
            return True
        result = True
        try:
            start_time=self.analytics_obj.getstarttime(self.inputs.bgp_ips[0])
            start_time1=self.analytics_obj.getstarttime(self.inputs.compute_ips[0])
            object_id= 'default-domain:default-project:ip-fabric:__default__:'+\
			self.inputs.bgp_names[1]+':default-domain:default-project:ip-fabric:__default__:'+self.inputs.bgp_names[0]
            object_id1=self.inputs.bgp_ips[0]
            query='('+'ObjectId='+ object_id +')'
            query1='('+'ObjectId='+ object_id1 + ' AND Source='+self.inputs.compute_names[0]+' AND ModuleId=VRouterAgent)'
#            query1='('+'ObjectId='+ object_id1 +')' 
            self.logger.info("Stopping the control node in %s"%(self.inputs.bgp_ips[0]))
            self.inputs.stop_service('contrail-control',[self.inputs.bgp_ips[0]])
            self.logger.info("Waiting for the logs to be updated in database..")
            time.sleep(20)
            self.logger.info("Verifying ObjectBgpPeer Table through opserver %s.."%(self.inputs.collector_ips[0]))    
            self.res1=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query('ObjectBgpPeer',
                                                                                start_time=start_time,end_time='now'
                                                                                ,select_fields=['ObjectId', 'Source',
                                                                                'ObjectLog', 'SystemLog','Messagetype',
                                                                                'ModuleId','MessageTS'],
                                                                                 where_clause=query)

            self.logger.info("Verifying ObjectXmppConnection Table through opserver %s.."%(self.inputs.collector_ips[0]))    
            self.res2=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query('ObjectXmppConnection',
                                                                                start_time=start_time1,end_time='now'
                                                                                ,select_fields=['ObjectId', 'Source',
                                                                                'ObjectLog', 'SystemLog','Messagetype',
                                                                                'ModuleId','MessageTS'],
                                                                                 where_clause=query1)
#            self.logger.info("query output : %s"%(self.res1))
            if not self.res1:
                self.logger.info("query output : %s"%(self.res1))
                st=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].\
				send_trace_to_database (node= self.inputs.collector_names[0],\
				 module= 'QueryEngine',trace_buffer_name= 'QeTraceBuf')
                self.logger.info("status: %s"%(st))
                result = result and False
            if not self.res2:
                self.logger.info("query output : %s"%(self.res2))
                st=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].\
			send_trace_to_database (node= self.inputs.collector_names[0],\
				 module= 'QueryEngine',trace_buffer_name= 'QeTraceBuf')
                self.logger.info("status: %s"%(st))
                result = result and False
            if self.res1:
                self.logger.info("Verifying logs from ObjectBgpPeer table")
                result1=False
                result2=False
                for elem in self.res1:
                    if re.search('EvConnectTimerExpired',str(elem['ObjectLog'])):
                        self.logger.info("EvConnectTimerExpired log sent")
                        result1 = True
                    if re.search('EvTcpConnectFail',str(elem['ObjectLog'])):
                        self.logger.info("EvTcpConnectFail log sent")
                        result2 = True
                if not result1:
                        self.logger.warn("EvConnectTimerExpired log NOT sent")
                if not result2:
                        self.logger.warn("EvTcpConnectFail log NOT sent")
                    
            if self.res2:
                self.logger.info("Verifying logs from ObjectXmppConnection table")
                result6=False
                for elem in self.res2:
                    if re.search('EvTcpConnectFail',str(elem['ObjectLog'])):
                        self.logger.info("EvTcpConnectFail log sent")
                        result6 = True
                if not result6:
                        self.logger.warn("EvTcpConnectFail log NOT sent")
                        
            start_time=self.analytics_obj.getstarttime(self.inputs.bgp_ips[0])
            start_time1=self.analytics_obj.getstarttime(self.inputs.compute_ips[0])
            time.sleep(2)
            self.inputs.start_service('contrail-control',[self.inputs.bgp_ips[0]])
            self.logger.info("Waiting for the logs to be updated in database..")
            time.sleep(30)
            self.logger.info("Verifying ObjectBgpPeer Table through opserver %s.."%(self.inputs.collector_ips[0]))    
            self.res1=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query('ObjectBgpPeer',
                                                                                start_time=start_time,end_time='now'
                                                                                ,select_fields=['ObjectId', 'Source',
                                                                                'ObjectLog', 'SystemLog','Messagetype',
                                                                                'ModuleId','MessageTS'],
                                                                                 where_clause=query)
            
            self.logger.info("Verifying ObjectXmppConnection Table through opserver %s.."%(self.inputs.collector_ips[0]))    
            self.res2=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].post_query('ObjectXmppConnection',
                                                                                start_time=start_time1,end_time='now'
                                                                                ,select_fields=['ObjectId', 'Source',
                                                                                'ObjectLog', 'SystemLog','Messagetype',
                                                                                'ModuleId','MessageTS'],
                                                                                 where_clause=query1)
#            self.logger.info("query output : %s"%(self.res1))
            if not self.res1:
                self.logger.info("query output : %s"%(self.res1))
                st=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].\
			send_trace_to_database (node= self.inputs.collector_names[0],\
			 module= 'QueryEngine',trace_buffer_name= 'QeTraceBuf')
                self.logger.info("status: %s"%(st))
                result = result and False
            if not self.res2:
                self.logger.info("query output : %s"%(self.res2))
                st=self.analytics_obj.ops_inspect[self.inputs.collector_ips[0]].\
			send_trace_to_database (node= self.inputs.collector_names[0],\
				 module= 'QueryEngine',trace_buffer_name= 'QeTraceBuf')
                self.logger.info("status: %s"%(st))
                result = result and False
            if self.res1:
                self.logger.info("Verifying logs from ObjectBgpPeer table")
                result3=False
                result4=False
                result5=False
                for elem in self.res1:
                    if re.search('EvTcpPassiveOpen',str(elem['ObjectLog'])):
                        self.logger.info("EvTcpPassiveOpen log sent")
                        result3 = True
                    if re.search('OpenConfirm',str(elem['ObjectLog'])):
                        self.logger.info("OpenConfirm log sent")
                        result4=True
                    if re.search('Established',str(elem['ObjectLog'])):
                        self.logger.info("Established log sent")
                        result5 = True
                if not result3:
                        self.logger.warn("EvTcpPassiveOpen log NOT sent")
                if not result4:
                        self.logger.warn("OpenConfirm log NOT sent")
                if not result5:
                        self.logger.warn("Established log NOT sent")
                    
                     
            if self.res2:
                self.logger.info("Verifying logs from ObjectXmppConnection table")
                result7=False
                result8=False
                for elem in self.res2:
                    if re.search('EvXmppOpen',str(elem['ObjectLog'])):
                        self.logger.info("EvXmppOpen log sent")
                        result7 = True
                    if re.search('EvTcpConnected',str(elem['ObjectLog'])):
                        self.logger.info("EvTcpConnected log sent")
                        result8 = True
                if not result7:
                        self.logger.warn("EvXmppOpen log NOT sent")
                if not result8:
                        self.logger.warn("EvTcpConnected log NOT sent")
        except Exception as e:
            print e
            result=result and False
        finally:
            self.inputs.start_service('contrail-control',[self.inputs.bgp_ips[0]])
            time.sleep(4)
            result = result and result1 and result2 and result3 and result4\
			 and result5 and result6 and result7 and result8
            assert result
            return True
    
    @preposttest_wrapper
    def test_verify_bgp_peer_uve(self):
        ''' Test to validate bgp peer uve

        '''
        abc= self.analytics_obj.get_peer_stats_info_tx_proto_stats(self.inputs.collector_ips[0],
			(self.inputs.bgp_names[0],self.inputs.bgp_names[1]))
        assert abc
        return True
    
class AnalyticsTestSanity2(base.AnalyticsBaseTest):

    @classmethod
    def setUpClass(cls):
        super(AnalyticsTestSanity2, cls).setUpClass()
    
    def runTest(self):
        pass
    #end runTest
    
    @preposttest_wrapper
    def itest_object_tables_parallel_query(self):
        '''Test object tables.
        '''
        threads=[]
        first_vm = self.res.vn1_vm1_fixture
        vm_list = [self.res.vn1_vm2_fixture]
        tx_vm_node_ip= self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(first_vm.vm_obj)]['host_ip']
        #start_time=self.analytics_obj.getstarttime(tx_vm_node_ip)
        start_time=self.analytics_obj.get_time_since_uptime(self.inputs.cfgm_ip)
        #Configuring static route
        prefix = '111.1.0.0/16'
        vm_uuid = self.res.vn1_vm1_fixture.vm_obj.id
        vm_ip = self.res.vn1_vm1_fixture.vm_ip
        self.analytics_obj.provision_static_route(prefix = prefix, virtual_machine_id = vm_uuid,
                                virtual_machine_interface_ip= vm_ip, route_table_name= 'my_route_table',
                                user= 'admin',password= 'contrail123')

        #Setting up traffic
        dest_min_port = 8000
        dest_max_port = 8002
        ips = self.analytics_obj.get_min_max_ip_from_prefix(prefix)

        traffic_threads= []
        for vm in vm_list:
            self.analytics_obj.start_traffic(first_vm,ips[0], ips[-1], vm.vm_ip,dest_min_port, dest_max_port)
            time.sleep(15)
#            t= threading.Thread(target=self.analytics_obj.start_traffic, args=(first_vm,ips[0], ips[-1], vm.vm_ip,
#                                                                 dest_min_port, dest_max_port,))
#            traffic_threads.append(t)
#
#        for th in traffic_threads:
#            time.sleep(0.5)
#            th.start()
        self.logger.info("Waiting for traffic to flow for 10 mins...")
        time.sleep(600)
        threads= self.analytics_obj.build_parallel_query_to_object_tables(start_time= start_time,skip_tables = ['FlowSeriesTable' ,
                                                                'FlowRecordTable',
                                                            'ObjectQueryQid','StatTable.ComputeCpuState.cpu_info',
                                                            u'StatTable.ComputeCpuState.cpu_info', u'StatTable.ControlCpuState.cpu_info',
                                                        u'StatTable.ConfigCpuState.cpu_info', u'StatTable.FieldNames.fields',
                                                                u'StatTable.SandeshMessageStat.msg_info', u'StatTable.FieldNames.fieldi',
                                                            'ServiceChain','ObjectSITable','ObjectModuleInfo','ObjectQueryQid',
                                                    'StatTable.QueryPerfInfo.query_stats', 'StatTable.UveVirtualNetworkAgent.vn_stats',
                                                            'StatTable.AnalyticsCpuState.cpu_info','ObjectQueryTable'])
        self.analytics_obj.start_query_threads(threads)

        vm1_name='vm_mine'
        vn_name='vn222'
        vn_subnets=['11.1.1.0/24']
        vn_count_for_test=32
        if (len(self.inputs.compute_ips) == 1):
            vn_count_for_test=2
        try:
            vm_fixture= self.useFixture(create_multiple_vn_and_multiple_vm_fixture (connections= self.connections,
                     vn_name=vn_name, vm_name=vm1_name, inputs= self.inputs,project_name= self.inputs.project_name,
                      subnets= vn_subnets,vn_count=vn_count_for_test,vm_count=1,subnet_count=1,
                      image_name='cirros-0.3.0-x86_64-uec',ram='512'))

            compute_ip=[]
            time.sleep(100)
        except Exception as e:
            self.logger.exception("Got exception as %s"%(e))

        try:
            assert vm_fixture.verify_vms_on_setup()
            assert vm_fixture.verify_vns_on_setup()
        except Exception as e:
            self.logger.exception("Got exception as %s"%(e))

        for vmobj in vm_fixture.vm_obj_dict.values():
            vm_host_ip=vmobj.vm_node_ip
            if vm_host_ip not in compute_ip:
                compute_ip.append(vm_host_ip)
        #self.inputs.restart_service('contrail-vrouter',compute_ip)
        sleep(30)

        try:
            assert vm_fixture.verify_vms_on_setup()
        except Exception as e:
            self.logger.exception("got exception as %s"%(e))

        self.analytics_obj.join_threads(threads)
        self.analytics_obj.get_value_from_query_threads()
        return True

class AnalyticsTestSanity3(base.AnalyticsBaseTest):

    @classmethod
    def setUpClass(cls):
        super(AnalyticsTestSanity3, cls).setUpClass()
    
    def runTest(self):
        pass
    #end runTest

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_verify_generator_collector_connections(self):
        '''
         Description: Verify generator:module connections to collector

              1.Verify all generators connected to collector - fails otherwise
              2.Get the xmpp peers in vrouter uve and get the active xmpp peer out of it
              3.Verify from agent introspect that active xmpp matches with step 2 - fails otherwise
              4.Get bgp peers from bgp-peer uve and verify from control node introspect that that matches - fails otherwise

         Maintainer: sandipd@juniper.net
        '''
        self.logger.info("START ...")
        # check collector-generator connections through uves.
        assert self.analytics_obj.verify_collector_uve()
        # Verify vrouter uve active xmpp connections
        assert self.analytics_obj.verify_active_xmpp_peer_in_vrouter_uve()
        # Verify vrouter uve for xmpp connections
        assert self.analytics_obj.verify_vrouter_xmpp_connections()
        # count of xmpp peer and bgp peer verification in bgp-router uve
        assert self.analytics_obj.verify_bgp_router_uve_xmpp_and_bgp_count()
        self.logger.info("END...")
        return True
    # end test_remove_policy_with_ref

