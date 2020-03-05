from __future__ import print_function
from builtins import str
from builtins import range
from builtins import object
import test_v1
from common import isolated_creds
from vn_test import *
from vm_test import *
from policy_test import *
import fixtures
from future.utils import with_metaclass
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile, StandardProfile, BurstProfile, ContinuousSportRange
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from tcutils.util import Singleton
from common.base import GenericTestBase

class AnalyticsBaseTest(GenericTestBase):

    @classmethod
    def setUpClass(cls):
        super(AnalyticsBaseTest, cls).setUpClass()
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        cls.orch = cls.connections.orch 
        resource_class = cls.__name__ + 'Resource'
        cls.res = ResourceFactory.createResource(resource_class)
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.res.cleanUp()
        super(AnalyticsBaseTest, cls).tearDownClass()
    #end tearDownClass

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            if fix.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break
    #end remove_from_cleanups


    def check_cmd_output(self, cmd_type, cmd_args_list, check_output=False, form_cmd=True, as_sudo=False, print_output=True):
        failed_cmds = []
        passed_cmds = []
        result = True
        for cmd_args in cmd_args_list:
            cmd = cmd_args
            if form_cmd:
                cmd = self._form_cmd(cmd_type, cmd_args)
            cmd += cmd + ' | wc -l'
            self.logger.info("Running the following cmd:%s \n" %cmd)
            if not self.execute_cli_cmd(cmd, check_output, as_sudo=as_sudo, print_output=print_output):
                self.logger.error('%s command failed..' % cmd)
                failed_cmds.append(cmd)
                result = result and False
            else:
                passed_cmds.append(cmd)

        self.logger.info('%s commands passed..\n' % passed_cmds)
        self.logger.info('%s commands failed..\n ' % failed_cmds)
        return result
   # end check_cmd_output

    def _form_cmd(self, cmd_type, cmd_args):
        cmd = cmd_type
        for k, v in cmd_args.items():
            if k == 'no_key':
                for elem in v:
                    cmd = cmd + ' --' +  elem
            else:
                cmd = cmd + ' --' + k + ' ' + v
        return cmd
    # _form_cmd

    def execute_cli_cmd(self, cmd, check_output=False, as_sudo=False, print_output=True):
        result = True
        analytics = self.res.inputs.collector_ips[0]
        output = self.res.inputs.run_cmd_on_server(analytics, cmd,
                                                   container='analytics-api', as_sudo=as_sudo)
        if print_output:
            self.logger.info("Output: %s \n" % output)
        if output.failed:
            self.logger.error('%s command failed..' % cmd)
            result = result and False
        if check_output:
            output_str = str(output)
            if not output_str:
                self.logger.error("Output is empty")
                result = result and False
        return result
    # end execute_cli_cmd

    def setup_flow_export_rate(self, value):
        ''' Set flow export rate and handle the cleanup
        '''
        vnc_lib_fixture = self.connections.vnc_lib_fixture
        current_rate = vnc_lib_fixture.get_flow_export_rate()
        vnc_lib_fixture.set_flow_export_rate(value)
        self.addCleanup(vnc_lib_fixture.set_flow_export_rate, current_rate)
    # end setup_flow_export_rate

    def verify_vna_stats(self,stat_type=None):
        result = True
        for vn in [self.res.vn1_fixture.vn_fq_name,\
                    self.res.vn2_fixture.vn_fq_name]:
            if stat_type == 'bandwidth_usage':
                #Bandwidth usage
                if not (int(self.analytics_obj.get_bandwidth_usage\
                        (self.inputs.collector_ips[0], vn, direction = 'out')) > 0):
                        self.logger.error("Bandwidth not shown  \
                                    in %s vn uve"%(vn))
                        result = result and False

                if not (int(self.analytics_obj.get_bandwidth_usage\
                        (self.inputs.collector_ips[0], vn, direction = 'in')) > 0):
                        self.logger.error("Bandwidth not shown  \
                                    in %s vn uve"%(vn))
                        result = result and False
            else:
                #ACL count
                if not (int(self.analytics_obj.get_acl\
                        (self.inputs.collector_ips[0],vn)) > 0):
                        self.logger.error("Acl counts not received from Agent uve \
                                    in %s vn uve"%(vn))
                        result = result and False

                if not (int(self.analytics_obj.get_acl\
                        (self.inputs.collector_ips[0], vn, tier = 'Config')) > 0):
                        self.logger.error("Acl counts not received from Config uve \
                                    in %s vn uve"%(vn))
                        result = result and False
                #Flow count
                if not (int(self.analytics_obj.get_flow\
                        (self.inputs.collector_ips[0], vn, direction = 'egress')) > 0):
                        self.logger.error("egress flow  not shown  \
                                    in %s vn uve"%(vn))
                        result = result and False

                if not (int(self.analytics_obj.get_flow\
                        (self.inputs.collector_ips[0], vn, direction = 'ingress')) > 0):
                        self.logger.error("ingress flow  not shown  \
                                    in %s vn uve"%(vn))
                        result = result and False

                #VN stats
                vns = [self.res.vn1_fixture.vn_fq_name,\
                        self.res.vn2_fixture.vn_fq_name]
                vns.remove(vn)
                other_vn = vns[0]
                if not (self.analytics_obj.get_vn_stats\
                        (self.inputs.collector_ips[0], vn, other_vn)):
                        self.logger.error("vn_stats   not shown  \
                                    in %s vn uve"%(vn))
                        result = result and False
        return result
    #end verify_vna_stats

    def setup_and_create_streams(self, src_vm, dst_vm, sport=8000, dport=9000, count=100):

        traffic_objs = list()
        for i in range(3):
            sport = sport
            dport = dport + i
            traffic_objs.append(self.start_traffic(src_vm, dst_vm, 'udp',
                        sport, dport, fip_ip=dst_vm.vm_ip, count=100))
        time.sleep(10)
        for traffic_obj in traffic_objs:
            self.stop_traffic(traffic_obj)

    #end setup_create_streams
    
    def creat_bind_policy(self,policy_name, rules, src_vn_fix, dst_vn_fix):
        #method to avoid redundant code for binding
        policy_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections))
        src_vn_fix.bind_policies([policy_fixture.policy_fq_name], src_vn_fix.vn_id)
        self.addCleanup(src_vn_fix.unbind_policies, src_vn_fix.vn_id, [
                policy_fixture.policy_fq_name])
        
        dst_vn_fix.bind_policies([policy_fixture.policy_fq_name], dst_vn_fix.vn_id)
        self.addCleanup(dst_vn_fix.unbind_policies, dst_vn_fix.vn_id, [
                policy_fixture.policy_fq_name])
    #end create and bind policy
       
    def verify_session_record_table(self, start_time, src_vn, dst_vn):
        self.logger.info('Verify session record table')
        result = True
        for ip in self.inputs.collector_ips:
            self.logger.info(
                    "Verifying SessionRecordTable through opserver %s" %
                    (ip))
            #query and verify number of client session records
            query = 'vn=' + src_vn + ' AND remote_vn=' + dst_vn + ' AND protocol=17'
            res = self.analytics_obj.ops_inspect[ip].post_query(
                'SessionRecordTable',
                start_time=start_time,
                end_time='now',
                select_fields=['forward_flow_uuid',
                           'reverse_flow_uuid', 'vn', 'remote_vn'],
                where_clause=query,
                session_type='client')
            
            if len(res) != 3:
                self.logger.error('Expected client session records 3 got %s'%len(res))
                result = result and False
            self.logger.debug(res)
            
            #query and verify number of server session records
            query = 'vn=' + dst_vn + ' AND remote_vn=' + src_vn + ' AND protocol=17'
            res = self.analytics_obj.ops_inspect[ip].post_query(
                'SessionRecordTable',
                start_time=start_time,
                end_time='now',
                select_fields=['forward_flow_uuid',
                           'reverse_flow_uuid', 'vn', 'remote_vn'],
                where_clause=query,
                session_type='server')
            
            if len(res) != 3:
                self.logger.error('Expected server session records 3 got %s'%len(res))
                result = result and False
            self.logger.debug(res)
            
            #query with local_ip server_port protocol
            query = 'local_ip=%s AND server_port=9001 AND protocol=17'%self.res.vn1_vm1_fixture.vm_ip
            res = self.analytics_obj.ops_inspect[ip].post_query(
                'SessionRecordTable',
                start_time=start_time,
                end_time='now',
                select_fields=['vn', 'remote_vn'],
            where_clause=query,
            session_type="client")
            if len(res) != 1:
               self.logger.error('Expected session records 1 got %s'%len(res))
               result = result and False
            self.logger.debug(res)
            
            #query with server_port local_ip filter by server_port
            query = 'vn=' + src_vn + ' AND remote_vn=' + dst_vn + ' AND protocol=17'
            res = self.analytics_obj.ops_inspect[ip].post_query(
                'SessionRecordTable',
                start_time=start_time,
                end_time='now',
                select_fields=['forward_flow_uuid',
                           'reverse_flow_uuid', 'local_ip', 'server_port'],
            where_clause=query,
            filter='server_port=9001',
            session_type="client")
            if len(res) != 1 :
               self.logger.error('Expected session records 1 got %s'%len(res))
               result = result and False
            self.logger.debug(res)
            
            #query with client_port remote_ip filter by client_port 
            #Total we get three record limit by 2
            query = 'vn=' + src_vn + ' AND remote_vn=' + dst_vn + ' AND protocol=17'
            res = self.analytics_obj.ops_inspect[ip].post_query(
                'SessionRecordTable',
                start_time=start_time,
                end_time='now',
                select_fields=['forward_flow_uuid',
                           'reverse_flow_uuid', 'remote_ip', 'client_port'],
            where_clause=query,
            filter='client_port=8000',
            limit=2,
            session_type="client")
            if len(res) != 2:
               self.logger.error('Expected session records 2 got %s'%len(res))
               result = result and False
            self.logger.debug(res)
            
            #query with sort_fields
            query = 'vn=' + src_vn + ' AND remote_vn=' + dst_vn + ' AND protocol=17'
            res = self.analytics_obj.ops_inspect[ip].post_query(
                'SessionRecordTable',
                start_time=start_time,
                end_time='now',
                select_fields=['forward_flow_uuid',
                           'reverse_flow_uuid', 'local_ip', 'server_port'],
            where_clause=query,
            sort_fields=['server_port'], sort=1,
            session_type="client")
            if res and res[0]['server_port'] != 9000:
               self.logger.error('Expected server port 9000 got %s'%res[0]['server_port'])
               result = result and False
            self.logger.debug(res)
             
        assert result,'Failed to get expected number of Records'
    #end verify_session_record_table
    
    def verify_session_series_table(self, start_time, src_vn, dst_vn):
        
        self.logger.info('Verify session series table and aggregation stats')
        result = True
        query = 'vn=' + src_vn + ' AND remote_vn=' + dst_vn + ' AND protocol=17'
        granularity =10
        vm_node_ip = self.res.vn1_vm1_fixture.vm_node_data_ip
        svc_name = self.inputs.host_data[vm_node_ip]['service_name']
        if not svc_name:
            vm_host = self.inputs.host_data[vm_node_ip]['host_ip']
        else:
            vm_host = self.inputs.host_data[vm_node_ip]['service_name'][vm_node_ip]

        ip = self.inputs.collector_ips[0]
        self.logger.info("Verifying SessionSeriesTable through opserver %s" %(ip))
        #query client session samples
        self.logger.info('SessionSeries: [SUM(forward_sampled_bytes), SUM(reverse_sampled_pkts), sample_count]')
        res = self.analytics_obj.ops_inspect[ip].post_query(
            'SessionSeriesTable',
            start_time=start_time,
            end_time='now',
            select_fields=['SUM(forward_sampled_pkts)', 'SUM(reverse_sampled_bytes)', 'sample_count', 'vrouter'],
            where_clause=query,
            filter='vrouter=%s'% vm_host, session_type="client")
        if len(res) != 1 and res[0]['SUM(forward_sampled_pkts)'] != 300:
            self.logger.error('Session aggregate stats returned %s not expected'%len(res))
            result = result and False
        self.logger.debug(res)
        
        #have three server ports so three record in output each with sum(forward pkts) 100
        res = self.analytics_obj.ops_inspect[ip].post_query(
            'SessionSeriesTable',
            start_time=start_time,
            end_time='now',
            select_fields=['server_port','local_ip','SUM(forward_sampled_pkts)', 'SUM(reverse_sampled_bytes)', 'sample_count', 'vrouter_ip'],
            where_clause=query,
            session_type="client")
        status = True
        for rec in res:
            if rec['SUM(forward_sampled_pkts)'] != 100:
                status = result and False
        if len(res) != 3 and not status:
            self.logger.error('Session series records returned %s not expected'%len(res))
            result = result and status
        self.logger.debug(res)
        
        ## all session msgs have same vn-remote_vn hence following query should return 1 record
        res = self.analytics_obj.ops_inspect[ip].post_query(
            'SessionSeriesTable',
            start_time=start_time,
            end_time='now',
            select_fields=['vn','remote_vn','SUM(forward_sampled_pkts)', 'SUM(reverse_sampled_bytes)', 'sample_count'],
            where_clause=query,
            session_type="client")
        if len(res) != 1 and res[0].get('SUM(forward_sampled_pkts)') !=300 :
            self.logger.error('Session series records returned %s not expected'%len(res))
            result = result and False
        self.logger.debug(res)
        
        ## sort results by server_port column
        res = self.analytics_obj.ops_inspect[ip].post_query(
            'SessionSeriesTable',
            start_time=start_time,
            end_time='now',
            select_fields=['vmi','local_ip','server_port','SUM(forward_sampled_bytes)', 'SUM(reverse_sampled_pkts)', 'sample_count'],
            where_clause=query,
            sort_fields=['server_port'], sort=1, limit=3,
            session_type="client")
        if len(res) !=3 and  res[0]['server_port'] != 9000:
            self.logger.error('Session series records with sort fileld returned %s not expected'%len(res))
            result = result and False
        self.logger.debug(res)
        
        #verify granularity with T=10
        res = self.analytics_obj.ops_inspect[ip].post_query(
            'SessionSeriesTable',
            start_time=start_time,
            end_time='now',
            select_fields=['T=%s' % (granularity), 'SUM(forward_sampled_bytes)',
                           'SUM(reverse_sampled_pkts)', 'vrouter'],
            where_clause=query,
            session_type="client")
        if not len(res) :
            self.logger.error('Session series records with granularity returned %s not expected'%len(res))
            result = result and False
        self.logger.debug(res)
        
        #with sampled bytes
        res = self.analytics_obj.ops_inspect[ip].post_query(
            'SessionSeriesTable',
            start_time=start_time,
            end_time='now',
            select_fields=['T', 'forward_sampled_bytes', 'reverse_sampled_pkts'],
            where_clause=query + ' AND server_port=9001',
            session_type="client")
        if not len(res) :
            self.logger.error('Session series records with specific server_port returned %s not expected'%len(res))
            result = result and False
        self.logger.debug(res)
        
        #with logged bytes
        res = self.analytics_obj.ops_inspect[ip].post_query(
            'SessionSeriesTable',
            start_time=start_time,
            end_time='now',
            select_fields=['T', 'forward_logged_pkts', 'reverse_logged_bytes'],
            where_clause=query,
            session_type="client")
        if not len(res) :
            self.logger.error('Session series records with logged _bytes/pkts returned %s not expected'%len(res))
            result = result and False
        self.logger.debug(res)
        
        #filter by action
        action = 'pass'
        res = self.analytics_obj.ops_inspect[ip].post_query(
            'SessionSeriesTable',
            start_time=start_time,
            end_time='now',
            select_fields=['server_port', 'forward_action',
                                'SUM(forward_sampled_bytes)',
                                'SUM(reverse_sampled_pkts)'],
            where_clause=query,
            session_type="client",
            filter='forward_action=%s'%action)
        if not len(res) and res[0].get('forward_action') != action :
            self.logger.error('Session series records with filter_action pass returned %s not expected'%len(res))
            result = result and False
        self.logger.debug(res)
        
        assert result,'Failed to get expected number of Records'
    #end verify_session_series_table
    
    def verify_session_sampling_teardown(self, start_time, src_vn, dst_vn):
        result = True
        vm_node_ip = self.res.vn1_vm1_fixture.vm_node_data_ip
        svc_name = self.inputs.host_data[vm_node_ip]['service_name']
        if not svc_name:
            vm_host = self.inputs.host_data[vm_node_ip]['host_ip']
        else:
            vm_host = self.inputs.host_data[vm_node_ip]['service_name'][vm_node_ip]
        query = 'vn=' + src_vn + ' AND remote_vn=' + dst_vn + ' AND protocol=1'
        self.logger.info('Verify session samples and teardown pkts')
        ip = self.inputs.collector_ips[0]
        self.logger.info("Verifying SessionSeriesTable through opserver %s" %(ip))
        
        #query client session samples
        res = self.analytics_obj.ops_inspect[ip].post_query(
            'SessionSeriesTable',
            start_time=start_time,
            end_time='now',
            select_fields=['T'],
            where_clause=query,
            session_type='client')
        if len(res) != 3:
            self.logger.error('Session sample client returned %s not expected'%res)
            result = result and False
        self.logger.debug(res)
        
        #query server session samples
        query = 'vn=' + dst_vn + ' AND remote_vn=' + src_vn + ' AND protocol=1'
        res = self.analytics_obj.ops_inspect[ip].post_query(
            'SessionSeriesTable',
            start_time=start_time,
            end_time='now',
            select_fields=['T'],
            where_clause=query,
            session_type='server')
        if len(res) != 3:
            self.logger.error('Session sample server returned %s not expected'%res)
            result = result and False
        self.logger.debug(res)
        
        #query client session to get number of sessions exported
        query = 'vn=' + src_vn + ' AND remote_vn=' + dst_vn + ' AND protocol=1'
        res = self.analytics_obj.ops_inspect[ip].post_query(
            'SessionSeriesTable',
            start_time=start_time,
            end_time='now',
            select_fields=['vn','remote_vn','sample_count'],
            where_clause=query,
            session_type='client')
        if len(res) and res[0].get('sample_count') !=3:
            self.logger.error('Session sample count returned %s not expected'%res)
            result = result and False
        self.logger.debug(res)
        
        #query session record table for teardown bytes/pkts
        self.logger.info('wait for the flows to get expire')
        time.sleep(200)
        flow_record = self.analytics_obj.get_flows_vrouter_uve(
            vrouter=vm_host)
        assert not flow_record,'flows not got deleted even after 240 sec'
        
        res = self.analytics_obj.ops_inspect[ip].post_query(
            'SessionRecordTable',
            start_time=start_time,
            end_time='now',
            select_fields=[
                        'vn',
                        'remote_vn',
                        'forward_teardown_pkts',
                        'reverse_teardown_pkts'],
        where_clause=query,
        session_type="client")
        if len(res) and (res[0].get('forward_teardown_pkts') != 3 and res[0].get('reverse_teardown_pkts') != 3):
           self.logger.error('Teardown fields were missing in the result')
           result = result and False
        self.logger.debug(res)
        
        # verify sample count after teardown on client side
        res = self.analytics_obj.ops_inspect[ip].post_query(
            'SessionSeriesTable',
            start_time=start_time,
            end_time='now',
            select_fields=['vn','remote_vn','sample_count'],
            where_clause=query,
            session_type='client')
        if len(res) and res[0].get('sample_count') !=4:
            self.logger.error('Session sample count returned %s not expected'%res)
            result = result and False
        
        # verify sample count after teardown on server side
        query = 'vn=' + dst_vn + ' AND remote_vn=' + src_vn + ' AND protocol=1'
        res = self.analytics_obj.ops_inspect[ip].post_query(
            'SessionSeriesTable',
            start_time=start_time,
            end_time='now',
            select_fields=['vn','remote_vn','sample_count'],
            where_clause=query,
            session_type='server')
        
        if len(res) and res[0].get('sample_count') !=4:
            self.logger.error('Session sample count returned %s not expected'%res)
            result = result and False
        self.logger.debug(res)
        return result
    #end verify_session_sampling_teardown
    
class ResourceFactory(object):
    factories = {}
    def createResource(id):
        if id not in ResourceFactory.factories:
            ResourceFactory.factories[id] = \
              eval(id + '.Factory()')
        return ResourceFactory.factories[id].create()
    createResource = staticmethod(createResource)

class BaseSanityResource(with_metaclass(Singleton, fixtures.Fixture)):
   
    def setUp(self,inputs,connections):
        super(BaseSanityResource , self).setUp()
        self.inputs = inputs
        self.connections = connections
        self.setup_sanity_common_objects(self.inputs , self.connections)

    def cleanUp(self):
        super(BaseSanityResource, self).cleanUp()

    def setup_sanity_common_objects(self, inputs , connections):
        self.inputs = inputs
        self.connections = connections
        self.orch = self.connections.orch
        self.logger = self.inputs.logger
        self.vn1_name = get_random_name("vn1")
        (self.vn1_vm1_name, self.vn1_vm2_name) = (get_random_name('vn1_vm1'),
                get_random_name('vn1_vm2'))

        self.vn1_fixture=self.useFixture( VNFixture(project_name= self.inputs.project_name,
                            connections= self.connections, inputs= self.inputs,
                            vn_name= self.vn1_name))

        host_list = self.orch.get_hosts()
        compute_1 = host_list[0]
        self.vn1_vm1_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,
                                connections= self.connections, vn_obj= self.vn1_fixture.obj,
                                vm_name= self.vn1_vm1_name,image_name='ubuntu-traffic',
                flavor='contrail_flavor_medium', node_name=compute_1))

        self.vn1_vm2_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,
                                connections= self.connections, vn_obj= self.vn1_fixture.obj,
                                vm_name= self.vn1_vm2_name , image_name='ubuntu-traffic',
                flavor='contrail_flavor_medium'))

        self.verify_sanity_common_objects()
    #end setup_common_objects

    def verify_sanity_common_objects(self):
        assert self.vn1_fixture.verify_on_setup()
        assert self.vn1_vm1_fixture.wait_till_vm_is_up()
        assert self.vn1_vm2_fixture.wait_till_vm_is_up()
    #end verify_common_objects


class BaseResource(with_metaclass(Singleton, BaseSanityResource)):

    def setUp(self,inputs,connections):
        super(BaseResource , self).setUp(inputs, connections)
        self.setup_common_objects(self.inputs , self.connections)

    def cleanUp(self):
        super(BaseResource, self).cleanUp()

    def setup_common_objects(self, inputs , connections):
        (self.vn2_name, self.fip_vn_name) = (get_random_name("vn2"), get_random_name("fip_vn"))
        self.vn2_vm2_name = get_random_name('vn2_vm2')
        self.fvn_vm1_name = get_random_name('fvn_vm1')

        self.vn2_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name,
            connections=self.connections,
            inputs=self.inputs,
            vn_name=self.vn2_name))

        self.fvn_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name,
            connections=self.connections,
            inputs=self.inputs,
            vn_name=self.fip_vn_name))

        # Making sure VM falls on diffrent compute host
        self.orch = self.connections.orch 
        host_list = self.orch.get_hosts()
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_2 = host_list[1]

        self.vn2_vm2_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,
                            connections= self.connections, vn_obj= self.vn2_fixture.obj,
                            vm_name= self.vn2_vm2_name, image_name='ubuntu-traffic',
                            node_name=compute_2))
        self.fvn_vm1_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,
                                connections= self.connections, vn_obj= self.fvn_fixture.obj,
                                vm_name= self.fvn_vm1_name))
        self.multi_intf_vm_fixture = self.useFixture(VMFixture(connections=self.connections,
                                     vn_objs=[self.vn1_fixture.obj , self.vn2_fixture.obj],
                                     vm_name='mltf_vm',
                                     project_name=self.inputs.project_name))

        self.verify_common_objects()
    #end setup_common_objects

    def verify_common_objects(self):
        super(BaseResource , self).verify_sanity_common_objects()
        assert self.vn2_fixture.verify_on_setup()
        assert self.fvn_fixture.verify_on_setup()
        assert self.fvn_vm1_fixture.wait_till_vm_is_up()
        assert self.vn2_vm2_fixture.wait_till_vm_is_up()
        assert self.multi_intf_vm_fixture.wait_till_vm_is_up()
    #end verify_common_objects

    def start_traffic(self):
        # installing traffic package in vm
        self.vn1_vm1_fixture.install_pkg("Traffic")
        self.vn2_vm2_fixture.install_pkg("Traffic")
        self.fvn_vm1_fixture.install_pkg("Traffic")

        self.tx_vm_node_ip = self.vn1_vm1_fixture.vm_node_ip
        self.rx_vm_node_ip = self.vn2_vm2_fixture.vm_node_ip
        self.tx_local_host = Host(
                            self.tx_vm_node_ip, self.inputs.host_data[
                            self.tx_vm_node_ip]['username'], self.inputs.host_data[
                            self.tx_vm_node_ip]['password'])
        self.rx_local_host = Host(
                            self.rx_vm_node_ip, self.inputs.host_data[
                            self.rx_vm_node_ip]['username'], self.inputs.host_data[
                            self.rx_vm_node_ip]['password'])
        self.send_host = Host(self.vn1_vm1_fixture.local_ip,
                            self.vn1_vm1_fixture.vm_username,
                            self.vn1_vm1_fixture.vm_password)
        self.recv_host = Host(self.vn2_vm2_fixture.local_ip,
                            self.vn2_vm2_fixture.vm_username,
                            self.vn2_vm2_fixture.vm_password)
        # Create traffic stream
        self.logger.info("Creating streams...")
        stream = Stream(
            protocol="ip",
            proto="udp",
            src=self.vn1_vm1_fixture.vm_ip,
            dst=self.vn2_vm2_fixture.vm_ip,
            dport=9000)

        profile = StandardProfile(
            stream=stream,
            size=100,
            count=10,
            listener=self.vn2_vm2_fixture.vm_ip)
        self.sender = Sender(
            "sendudp",
            profile,
            self.tx_local_host,
            self.send_host,
            self.inputs.logger)
        self.receiver = Receiver(
            "recvudp",
            profile,
            self.rx_local_host,
            self.recv_host,
            self.inputs.logger)
        self.receiver.start()
        self.sender.start()
        time.sleep(10)

    def stop_traffic(self):
        self.sender.stop()
        self.receiver.stop()
        self.logger.info("Sent traffic: %s"%(self.sender.sent))
        self.logger.info("Received traffic: %s"%(self.receiver.recv))

class AnalyticsTestSanityWithMinResource(BaseSanityResource):

    def setUp(self,inputs,connections):
        super(AnalyticsTestSanityWithMinResource , self).setUp(inputs,connections)

    def cleanUp(self):
        super(AnalyticsTestSanityWithMinResource , self).cleanUp()

    class Factory(object):
        def create(self): return AnalyticsTestSanityWithMinResource()

class AnalyticsTestSanityResource(BaseResource): 

    def setUp(self,inputs,connections):
        pass
        #super(AnalyticsTestSanityResource , self).setUp(inputs,connections)

    def cleanUp(self):
        pass
        #super(AnalyticsTestSanityResource, self).cleanUp()

    class Factory(object):
        def create(self): return AnalyticsTestSanityResource()

class AnalyticsTestSanity1Resource(BaseResource):

    def setUp(self,inputs,connections):
        pass
        #super(AnalyticsTestSanity1Resource , self).setUp(inputs,connections)

    def cleanUp(self):
        pass
        #super(AnalyticsTestSanity1Resource, self).cleanUp()

    class Factory(object):
        def create(self): return AnalyticsTestSanity1Resource()


class AnalyticsTestSanity2Resource(BaseResource):

    def setUp(self,inputs,connections):
        pass
        #super(AnalyticsTestSanity2Resource , self).setUp(inputs,connections)

    def cleanUp(self):
        pass
        #super(AnalyticsTestSanity2Resource, self).cleanUp()

    class Factory(object):
        def create(self): return AnalyticsTestSanity2Resource()

class AnalyticsTestSanity3Resource(BaseResource):

    def setUp(self,inputs,connections):
        pass
        #super(AnalyticsTestSanity3Resource , self).setUp(inputs,connections)

    def cleanUp(self):
        pass
        #super(AnalyticsTestSanity3Resource, self).cleanUp()

    class Factory(object):
        def create(self): return AnalyticsTestSanity3Resource()

class AnalyticsTestSanityWithResourceResource(BaseResource):

    def setUp(self,inputs,connections):
        super(AnalyticsTestSanityWithResourceResource , self).setUp(inputs,connections)

    def cleanUp(self):
        super(AnalyticsTestSanityWithResourceResource, self).cleanUp()

    class Factory(object):
        def create(self): return AnalyticsTestSanityWithResourceResource()
#End resource

