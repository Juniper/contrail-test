import os
import fixtures
import testtools
import datetime

from vn_test import *
from vm_test import *
from common.connections import ContrailConnections
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import run_fab_cmd_on_node
from common.openstack_libs import neutron_client_exception as NeutronClientException

from common.neutron.lbaas.base import BaseTestLbaas
import test


class TestLbaas(BaseTestLbaas):

    @classmethod
    def setUpClass(cls):
        super(TestLbaas, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestLbaas, cls).tearDownClass()

    @preposttest_wrapper
    def test_active_standby_failover(self):
        '''Creates Lbaas pool with lb-method ROUND ROBIN, 3 members and vip
           Verifies in active standby mode traffic flows through only Active
           Stop Agent service and verify traffic shifts to stnadby
           Fail otherwise
        '''

        vn_pool = get_random_name('vn_pool')
        vn_vip = get_random_name('vn_vip')
        vn_pool_subnets = ['10.1.1.0/24']
        vn_vip_subnets = ['20.1.1.0/24']
        pool_vm1 = get_random_name('server1')
        pool_vm2 = get_random_name('server2')
        pool_vm3 = get_random_name('server3')
        client_vm1 = get_random_name('client1')
        client_vm2 = get_random_name('client2')

        vn_pool_fixture = self.create_vn(vn_pool, vn_pool_subnets)
        assert vn_pool_fixture.verify_on_setup()
        vn_vip_fixture = self.create_vn(vn_vip, vn_vip_subnets)
        assert vn_vip_fixture.verify_on_setup()
        pool_vm1_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm1,
                flavor='contrail_flavor_small', image_name='ubuntu')
        pool_vm2_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm2,
                flavor='contrail_flavor_small', image_name='ubuntu')
        pool_vm3_fixture = self.create_vm(vn_pool_fixture,vm_name=pool_vm3,
                flavor='contrail_flavor_small', image_name='ubuntu')
        client_vm1_fixture = self.create_vm(vn_vip_fixture,vm_name=client_vm1,
                flavor='contrail_flavor_small', image_name='ubuntu')

        lb_pool_servers = [pool_vm1_fixture, pool_vm2_fixture, pool_vm3_fixture]

        assert pool_vm1_fixture.wait_till_vm_is_up()
        assert pool_vm2_fixture.wait_till_vm_is_up()
        assert pool_vm3_fixture.wait_till_vm_is_up()
        assert client_vm1_fixture.wait_till_vm_is_up()

        pool_name = 'mypool'
        lb_method = 'ROUND_ROBIN'
        protocol = 'HTTP'
        protocol_port = 80
        vip_name = 'myvip'

        #create lb pool
        self.logger.info("creating lb pool:%s" % (pool_name))
        lb_pool = self.create_lb_pool(pool_name, lb_method, protocol, vn_pool_fixture.vn_subnet_objs[0]['id'])
        assert lb_pool, "lb pool create failed"
        #api server verification
        assert self.verify_lb_pool_in_api_server(lb_pool['id']), \
               "API server verification failed for pool with pool id %s" % (lb_pool['id'])

        #create lb member
        self.logger.info("creating lb member")
        lb_member1 = self.create_lb_member(pool_vm1_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member1, "lb member create failed"
        assert self.verify_member_in_api_server(lb_member1['id']), \
              "API server verification failed for member with id %s" % (lb_member1['id'])
        lb_member2 = self.create_lb_member(pool_vm2_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member2, "lb member create failed"
        assert self.verify_member_in_api_server(lb_member2['id']), \
              "API server verification failed for member with id %s" % (lb_member2['id'])
        lb_member3 = self.create_lb_member(pool_vm3_fixture.vm_ip, protocol_port, lb_pool['id'])
        assert lb_member3, "lb member create failed"
        assert self.verify_member_in_api_server(lb_member3['id']), \
              "API server verification failed for member with id %s" % (lb_member3['id'])

        #create vip
        self.logger.info("creating lb vip:%s" % (vip_name))
        lb_vip = self.create_vip(vip_name, protocol, protocol_port, vn_vip_fixture.vn_subnet_objs[0]['id'], lb_pool['id'])
        assert lb_vip, "lb vip create failed"
        vip_ip = lb_vip['address']
        #api server verification
        assert self.verify_vip_in_api_server(lb_vip['id']), \
               "API server verification failed for vip with vip id %s" % (lb_vip['id'])
        #TODO : agent verification

        #sleep for 10 sec for netns to get created
        sleep(10)

        #get the active and standby computes
        obj = self.api_s_inspect.get_lb_pool(pool_id=lb_pool['id'])
        si = self.api_s_inspect.get_cs_si(project= self.project.project_name, si=lb_pool['id'], refresh=True)
        domain,project,name = si['service-instance']['fq_name']
        si_name='%s:%s:%s'%(domain,project,name)
        si_ops = self.analytics_obj.get_svc_instance(self.inputs.collector_ips[0], project= self.project.project_name,
                                                      instance=si_name)
        for vm in si_ops['vm_list'] :
            if vm['ha'] == 'active: 200':
                active = vm['vr_name']
            if vm['ha'] == 'standby: 100':
                standby = vm['vr_name']
        self.logger.info("lbaas, active is: %s and stnadby is: %s" % (active, standby))

        left_int_active = self.get_netns_left_intf(self.inputs.compute_info[active],lb_pool['id'])
        left_int_standby = self.get_netns_left_intf(self.inputs.compute_info[standby],lb_pool['id'])

        #Start SimpleHTTPServer on port 80 on all lb pool servers
        self.start_simpleHTTPserver(lb_pool_servers)

        #start tcpdump on Active
        pcap_active,session_active = self.start_tcpdump(self.inputs.compute_info[active], left_int_active)
        #start tcpdump on stndby
        pcap_standby,session_standby = self.start_tcpdump(self.inputs.compute_info[standby], left_int_standby)

        #Do wget on the VIP ip from the client, Lets do it 3 times
        result = ''
        for i in range (0,3):
            result,output = self.run_wget(client_vm1_fixture,vip_ip)

        #stop tcpdump
        count_active = self.stop_tcpdump(session_active, pcap_active)
        count_standby = self.stop_tcpdump(session_standby, pcap_standby)

        if (count_active != 0) and (count_standby ==0):
            self.logger.info("traffic is flowing only through active %s" % (active))
        else:
            assert False, "traffic is flowing through standby %s, when active %s is present" % (standby, active)

        #Check if the client VM is runing on the same compute before stopping the agent service.
        if client_vm1_fixture.vm_node_ip == self.inputs.compute_info[active]:
            self.logger.info("clinet vm %s running on active compute, launching another client vm on standby"
                             " %s before stopping the agent in active %s" % (client_vm1_fixture, standby, active))
            client_vm2_fixture = self.create_vm(vn_vip_fixture,vm_name=client_vm2,
                    flavor='contrail_flavor_small', node_name=standby, image_name='ubuntu')
            assert client_vm2_fixture.wait_till_vm_is_up()
            client_vm_fixture = client_vm2_fixture
        else:
            client_vm_fixture = client_vm1_fixture

        #stop the agent service in agent and check if the failover scenario is working.
        self.logger.info("stopping the agent service in active: %s to check the failover scenario" % (active))
        self.start_stop_service(self.inputs.compute_info[active], 'contrail-vrouter-agent', 'stop')

        #start tcpdump on Active
        pcap_active,session_active = self.start_tcpdump(self.inputs.compute_info[active], left_int_active)
        #start tcpdump on stndby
        pcap_standby,session_standby = self.start_tcpdump(self.inputs.compute_info[standby], left_int_standby)

        #Do wget on the VIP ip from the client, Lets do it 3 times
        result = ''
        for i in range (0,3):
            result,output = self.run_wget(client_vm_fixture,vip_ip)

        #stop tcpdump
        count_active = self.stop_tcpdump(session_active, pcap_active)
        count_standby = self.stop_tcpdump(session_standby, pcap_standby)

        #start the agent service in agent and check if the failover scenario is working.
        self.logger.info("start the agent service back in active: %s" % (active))
        self.start_stop_service(self.inputs.compute_info[active], 'contrail-vrouter-agent', 'start')

        if (count_active == 0) and (count_standby !=0):
            self.logger.info("traffic is flowing only through standby %s, failover working" % (standby))
        else:
            assert False, "traffic is not flowing through standby %s \
                           when agent in Active is down,  failover not \
                           working" % (standby)

    # end test_active_standby_failover

    @preposttest_wrapper
    def test_lbaas_garbage_collector(self):
        '''Create 2 Lbaas pool and 2 vips
           Check for netns got created and haproxy running
           Restart the agent service in compute and verify garbage collector
           working as expected, fail otherwise
        '''
        result = True
        vn_pool = get_random_name('vn_pool')
        vn_vip = get_random_name('vn_vip')
        vn_pool_subnets = ['10.1.1.0/24']
        vn_vip_subnets = ['20.1.1.0/24']
        pool_vm1 = get_random_name('server1')

        vn_pool_fixture = self.create_vn(vn_pool, vn_pool_subnets)
        assert vn_pool_fixture.verify_on_setup(), "vn %s verification failed" % vn_pool
        vn_vip_fixture = self.create_vn(vn_vip, vn_vip_subnets)
        assert vn_vip_fixture.verify_on_setup(), "vn %s verification failed" % vn_vip

        pool_name = 'mypool'
        lb_method = 'ROUND_ROBIN'
        protocol = 'HTTP'
        protocol_port = 80
        vip_name = 'myvip'

        #create lb pool
        self.logger.info("creating lb pool:%s" % pool_name)
        lb_pool = self.create_lb_pool(pool_name, lb_method, protocol, vn_pool_fixture.vn_subnet_objs[0]['id'])
        assert lb_pool, "lb pool create failed"
        #api server verification
        assert self.verify_lb_pool_in_api_server(lb_pool['id']), \
               "API server verification failed for pool with pool id %s" % (lb_pool['id'])

        #create vip
        self.logger.info("creating lb vip:%s" % vip_name)
        lb_vip = self.create_vip(vip_name, protocol, protocol_port, vn_vip_fixture.vn_subnet_objs[0]['id'], lb_pool['id'])
        assert lb_vip, "lb vip create failed"
        #api server verification
        assert self.verify_vip_in_api_server(lb_vip['id']), \
               "API server verification failed for vip with vip id %s" % (lb_vip['id'])
        #TODO : agent verification

        #sleep for 10 sec netns to get created
        sleep(10)

        #Check if nets ns got created and haproxy running in compute nodes after vip creation
        result,errmsg = self.verify_active_standby(self.inputs.compute_ips, lb_pool['id'])
        assert result, errmsg

        #Get the active and standby computes
        obj = self.api_s_inspect.get_lb_pool(pool_id=lb_pool['id'])
        si = self.api_s_inspect.get_cs_si(project= self.project.project_name, si=lb_pool['id'], refresh=True)
        domain,project,name = si['service-instance']['fq_name']
        si_name='%s:%s:%s'%(domain,project,name)
        si_ops = self.analytics_obj.get_svc_instance(self.inputs.collector_ips[0], project= self.project.project_name,
                                                      instance=si_name)
        for vm in si_ops['vm_list'] :
            if vm['ha'] == 'active: 200':
                active = vm['vr_name']
            if vm['ha'] == 'standby: 100':
                standby = vm['vr_name']
        self.logger.info("lbaas, active is: %s and stnadby is: %s for pool %s"
                         % (active, standby, lb_pool['name']))

        #Restart the agent service in Active and Standby
        self.logger.info("stop and start the agent service in active: %s and standby %s"
                         " to verify the garbage collector functionallity" % (active, standby))
        self.start_stop_service(self.inputs.compute_info[active], 'contrail-vrouter-agent', 'stop')
        self.start_stop_service(self.inputs.compute_info[standby], 'contrail-vrouter-agent', 'stop')
        sleep(5)
        self.start_stop_service(self.inputs.compute_info[active], 'contrail-vrouter-agent', 'start')
        self.start_stop_service(self.inputs.compute_info[standby], 'contrail-vrouter-agent', 'start')
        result, msg = self.verify_agent_process_active(active)
        if not result:
            self.logger.error("Agent process did not come to active state in compute %s"
                              " after process is started again. failing the test here" % (active))
        assert result, msg
        result, msg = self.verify_agent_process_active(standby)
        if not result:
            self.logger.error("Agent process did not come to active state in compute %s"
                              " after process is started again. failing the test here" % (standby))
        assert result, msg

        #Check if there are any stale net ns in compute due to agent restart
        self.logger.info("verifying after the agent restart there are any stale entris of net ns"
                         "and haproxy")
        result,errmsg = self.verify_active_standby(self.inputs.compute_ips, lb_pool['id'])
        if result:
            self.logger.info("Stale entries of NET NS and haproxy not found in compute."
                              "garbage collector working as expected")
        assert result, errmsg

        #Stop the agent process and delete the vip. Verify netns gets deleted and haproxy gets killed
        #after agent is started.
        self.start_stop_service(self.inputs.compute_info[active], 'contrail-vrouter-agent', 'stop')
        sleep(5)

        #Delete VIP while the agent is stopped
        self.quantum_h.delete_vip(lb_vip['id'])
        self.remove_method_from_cleanups((self.quantum_h.delete_vip, (lb_vip['id'],), {}))

        result, msg = self.verify_vip_delete(lb_vip['id'])
        assert result, msg

        self.start_stop_service(self.inputs.compute_info[active], 'contrail-vrouter-agent', 'start')
        result, msg = self.verify_agent_process_active(active)
        if not result:
            self.logger.error("Agent process did not come to active state in compute %s"
                              " after process is started again. failing the test here" % (active))
        assert result, msg

        maxduration = 300
        start = datetime.datetime.now()
        timedelta = datetime.timedelta(seconds=maxduration)
        maxtime = start + timedelta
        while maxtime >= datetime.datetime.now():
            result, msg = self.verify_netns_delete(self.inputs.compute_info[active], lb_pool['id'])
            if result:
                self.logger.info("NET NS got deleted with in the garbage collector timeout,"
                                 " which is 5 mins in agent")
                break
        if not result:
            self.logger.error("waited till gargabe collector timeout which is (%s sec) in agent"
                              "NET NS did not get deleted in compute %s with in this time"
                              % (maxduration, active))
            assert result, msg
    #end test_lbaas_garbage_collector
