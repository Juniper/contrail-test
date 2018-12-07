#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
from tcutils.wrappers import preposttest_wrapper
from tcutils.util import *
from common.neutron.lbaasv2.base import BaseLBaaSTest
import os
import fixtures
import tcutils.wrappers
import time
from vn_test import VNFixture
from vm_test import VMFixture
from test import attr
from base import TestLlgrBase
from tcutils.tcpdump_utils import start_tcpdump_for_intf,\
     stop_tcpdump_for_intf, verify_tcpdump_count

#from cn_introspect_bgp import ControlNodeInspect
import test
'''
   This test suite runs only on control node scale setup 
   Where MX is connected to one of the control node and two 
   compute nodes were connected to each of the agent which 
   is taken care during Base class setup
   In each of the steps following steps were exectued 
   Launch a two VMs for North/South traffic 
   Start a failure ( link failure / Agent restart )
   Check flags for Route advertised by agent is in GR/LLGR state
   Check if there is a drop in traffic
   Restore the failure 

   Following paramters should be given in instances.yaml under
   test_configuration:
   public_host : '121.1.1.1'
   public_host_v6 : '2002::1'
     physical_routers:
      5b4-mx240-1-re0:
          asn: 64512
          mgmt_ip: 10.87.64.246
          mode: mx
          name: 5b4-mx240-1-re0
          ssh_password: Embe1mpls
          ssh_username: root
          tunnel_ip : 6.6.6.10
          vendor: juniper
          rt : 2500
          type: tor

   And on router following configuration needs to be set on mx router
   set groups ixia_flow protocols bgp group llgr_contrail type internal
   set groups ixia_flow protocols bgp group llgr_contrail traceoptions file bgp.log
   set groups ixia_flow protocols bgp group llgr_contrail traceoptions flag all
   set groups ixia_flow protocols bgp group llgr_contrail local-address 6.6.6.10
   set groups ixia_flow protocols bgp group llgr_contrail hold-time 20
   set groups ixia_flow protocols bgp group llgr_contrail keep all
   set groups ixia_flow protocols bgp group llgr_contrail family inet-vpn unicast graceful-restart long-lived restarter stale-time 60
   set groups ixia_flow protocols bgp group llgr_contrail family inet6-vpn unicast graceful-restart long-lived restarter stale-time 60
   set groups ixia_flow protocols bgp group llgr_contrail family evpn signaling
   set groups ixia_flow protocols bgp group llgr_contrail family route-target graceful-restart long-lived restarter stale-time 60
   set groups ixia_flow protocols bgp group llgr_contrail vpn-apply-export
   set groups ixia_flow protocols bgp group llgr_contrail graceful-restart restart-time 30
   set groups ixia_flow protocols bgp group llgr_contrail graceful-restart stale-routes-time 30
   set groups ixia_flow protocols bgp group llgr_contrail neighbor 5.5.5.129 peer-as 64512
   set groups ixia_flow protocols bgp group llgr_contrail neighbor 5.5.5.130 peer-as 64512
   set groups ixia_flow protocols bgp group llgr_contrail neighbor 5.5.5.131 peer-as 64512
   set groups ixia_flow routing-instances llgr-port1 instance-type vrf
   set groups ixia_flow routing-instances llgr-port1 interface lo0.4
   set groups ixia_flow routing-instances llgr-port1 route-distinguisher 64512:2500
   set groups ixia_flow routing-instances llgr-port1 vrf-target target:64512:2500
   set groups ixia_flow routing-instances llgr-port1 vrf-table-label

'''


class TestLlgrXmpp(TestLlgrBase):

    @classmethod
    def setUpClass(cls):

        super(TestLlgrXmpp, cls).setUpClass()
        cls.result_file = 'ping_stats'
        cls.result6_file = 'ping6_stats'
        cls.pid_file = '/tmp/llgr.pid'
        cls.pid6_file = '/tmp/llgr6.pid'
        cls.timeout = 30 
        cls.gr_timeout = 60
        cls.llgr_timeout = 120
        return True
    # end cleanUp

    @classmethod
    def tearDownClass(cls):
        cls.inputs.start_container([cls.inputs.bgp_ips[1]], container='control')
        super(TestLlgrXmpp, cls).tearDownClass()
        return True
    # end cleanUp

    @test.attr(type=['llgr'])
    @preposttest_wrapper
    def test_gr_xmpp(self):
        '''
           Check Traffic to VM on different host goes fine when BGP session is down during GR configuration 
           holdtime of 90sec + stale time of 35sec 
        '''
        timeout = 30  

        self.set_gr_llgr(gr=35,llgr=0,mode='enable',bgp_hlp='disable',xmpp_hlp='enable')

        if not self.create_vm_start_ping(ping_count=3000):
            self.logger.error("Error in creating VM")
            return False

        self.set_bgp_peering(mode='disable',port=5269)

        self.addCleanup(self.set_bgp_peering,mode='enable',port=5269)

        time.sleep(timeout)
 
        if not self.verify_gr_llgr_flags(flags=['Stale'], vn_fix=self.vn_fix, prefix=self.vm1_fixture.vm_ip):
            self.logger.error("Stale flag is not set for route : %s"%self.vm1_fixture.vm_ip)
            return False

        if not self.verify_gr_llgr_flags(flags=['Stale'], vn_fix=self.vn_fix, prefix=self.vm1_ipv6_addr):
            self.logger.error("Stale flag is not set for route : %s"%self.vm1_ipv6_addr)
            return False

        if not self.verify_ping_stats():
            self.logger.error("Error in ping stats")
            return False

        self.set_bgp_peering(mode='enable',port=5269)
 
        time.sleep(20)

        return True

    @test.attr(type=['llgr'])
    @preposttest_wrapper
    def test_gr_llgr_xmpp(self):
        '''
           Check Traffic to VM on different host goes fine when BGP session is down during GR and LLGR configuration 
           holdtime of 90sec + stale time of 30sec + llgr stale time of 60sec
        '''
        timeout = 100  

        self.set_gr_llgr(gr=35,llgr=120,mode='enable',bgp_hlp='disable',xmpp_hlp='enable')

        if not self.create_vm_start_ping(ping_count=6000):
            self.logger.error("Error in creating VM")
            return False

        self.set_bgp_peering(mode='disable',port=5269)

        self.addCleanup(self.set_bgp_peering,mode='enable',port=5269)

        time.sleep(timeout)
 
        if not self.verify_gr_llgr_flags(flags=['Stale','LlgrStale'], vn_fix=self.vn_fix, prefix=self.vm1_fixture.vm_ip):
            self.logger.error("Stale flag is not set for route : %s"%self.vm1_fixture.vm_ip)
            return False

        if not self.verify_gr_llgr_flags(flags=['Stale','LlgrStale'], vn_fix=self.vn_fix, prefix=self.vm1_ipv6_addr):
            self.logger.error("Stale flag is not set for route : %s"%self.vm1_ipv6_addr)
            return False

        if not self.verify_ping_stats():
            self.logger.error("Error in ping stats")
            return False

        self.set_bgp_peering(mode='enable',port=5269)

        time.sleep(30)

        return True


    @test.attr(type=['llgr'])
    @preposttest_wrapper
    def test_llgr_xmpp(self):
        '''
           Check Traffic to VM on different host goes fine when BGP session is down during GR and LLGR configuration 
           holdtime of 90sec + llgr stale time of 60sec 
        '''
        #enable llgr 
        # holdtime of 90sec + stale time of 30sec 
        timeout = 60 

        self.set_gr_llgr(gr=0,llgr=120,mode='enable',bgp_hlp='disable',xmpp_hlp='enable')

        if not self.create_vm_start_ping(ping_count=6000):
            self.logger.error("Error in creating VM")
            return False

        self.set_bgp_peering(mode='disable',port=5269)

        self.addCleanup(self.set_bgp_peering,mode='enable',port=5269)

        time.sleep(timeout)
 
        if not self.verify_gr_llgr_flags(flags=['Stale','LlgrStale'], vn_fix=self.vn_fix, prefix=self.vm1_fixture.vm_ip):
            self.logger.error("Stale flag is not set for route : %s"%self.vm1_fixture.vm_ip)
            return False

        if not self.verify_gr_llgr_flags(flags=['Stale','LlgrStale'], vn_fix=self.vn_fix, prefix=self.vm1_ipv6_addr):
            self.logger.error("Stale flag is not set for route : %s"%self.vm1_ipv6_addr)
            return False

        if not self.verify_ping_stats():
            self.logger.error("Error in ping stats")
            return False

        self.set_bgp_peering(mode='enable',port=5269)

        time.sleep(20)

        return True


    # RESTART of controller 
    @test.attr(type=['llgr'])
    @preposttest_wrapper
    def test_gr_xmpp_restart(self):
        '''
           Check Traffic to VM on different host goes fine when control node session is restarted during GR configuration 
           holdtime of 0sec + stale time of 60sec 
           In this case route state is immediately changed to stale , holdtime is not triggered
        '''
        timeout = 30  
        self.set_gr_llgr(gr=60,llgr=0,mode='enable',bgp_hlp='enable',xmpp_hlp='enable')

        if not self.create_vm_start_ping(ping_count=3000):
            self.logger.error("Error in creating VM")
            return False

        self.inputs.restart_container([self.inputs.bgp_ips[1]], container='control') 

        time.sleep(timeout)

        assert self.verify_gr_llgr_flags(flags=['None'], vn_fix=self.vn_fix, prefix=self.vm2_fixture.vm_ip) 
        assert self.verify_gr_llgr_flags(flags=['None'], vn_fix=self.vn_fix, prefix=self.ipv6_addr) 

        if not self.verify_ping_stats():
            self.logger.error("Error in ping stats")
            return False

        return True


    # RESTART of controller 
    @test.attr(type=['llgr'])
    @preposttest_wrapper
    def test_llgr_xmpp_restart(self):
        '''
           Check Traffic to VM on different host goes fine when control node session is restarted during LLGR configuration 
           holdtime of 0sec + stale time of 30sec and llgr time of 60 
        '''
        # holdtime of 90sec + stale time of 30sec 
        timeout = 50  
        self.set_gr_llgr(gr=35,llgr=60,mode='enable',bgp_hlp='enable',xmpp_hlp='enable')

        if not self.create_vm_start_ping(ping_count=4000):
            self.logger.error("Error in creating VM")
            return False

        self.inputs.restart_container([self.inputs.bgp_ips[1]], container='control') 

        time.sleep(timeout)
 
        assert self.verify_gr_llgr_flags(flags=['None'], vn_fix=self.vn_fix, prefix=self.vm2_fixture.vm_ip) 
        assert self.verify_gr_llgr_flags(flags=['None'], vn_fix=self.vn_fix, prefix=self.ipv6_addr) 

        if not self.verify_ping_stats():
            self.logger.error("Error in ping stats")
            return False

        return True


    # RESTART of controller 
    @test.attr(type=['llgr'])
    @preposttest_wrapper
    def test_gr_xmpp_start_stop(self):
        '''
           Check Traffic to VM on different host goes fine when control node session is restarted during GR configuration 
           holdtime of 0sec + stale time of 60sec 
           In this case route state is immediately changed to stale , holdtime is not triggered
        '''
        timeout = 30  
        self.set_gr_llgr(gr=60,llgr=0,mode='enable',bgp_hlp='enable',xmpp_hlp='enable')

        if not self.create_vm_start_ping(ping_count=3000):
            self.logger.error("Error in creating VM")
            return False

        self.inputs.stop_container([self.inputs.bgp_ips[1]], container='control') 

        time.sleep(timeout)

        assert self.verify_gr_llgr_flags(flags=['Stale'], vn_fix=self.vn_fix, prefix=self.vm2_fixture.vm_ip) 
        assert self.verify_gr_llgr_flags(flags=['Stale'], vn_fix=self.vn_fix, prefix=self.ipv6_addr) 

        self.inputs.start_container([self.inputs.bgp_ips[1]], container='control') 

        assert self.verify_gr_llgr_flags(flags=['None'], vn_fix=self.vn_fix, prefix=self.vm2_fixture.vm_ip) 
        assert self.verify_gr_llgr_flags(flags=['None'], vn_fix=self.vn_fix, prefix=self.ipv6_addr) 

        if not self.verify_ping_stats():
            self.logger.error("Error in ping stats")
            return False

        return True


    # RESTART of controller 
    @test.attr(type=['llgr'])
    @preposttest_wrapper
    def test_llgr_xmpp_start_stop(self):
        '''
           Check Traffic to VM on different host goes fine when control node session is restarted during LLGR configuration 
           holdtime of 0sec + stale time of 30sec and llgr time of 60 
        '''
        # holdtime of 90sec + stale time of 30sec 
        timeout = 50  
        self.set_gr_llgr(gr=35,llgr=60,mode='enable',bgp_hlp='enable',xmpp_hlp='enable')

        if not self.create_vm_start_ping(ping_count=4000):
            self.logger.error("Error in creating VM")
            return False

        self.inputs.stop_container([self.inputs.bgp_ips[1]], container='control') 

        time.sleep(timeout)
 
        assert self.verify_gr_llgr_flags(flags=['Stale','LlgrStale'], vn_fix=self.vn_fix, prefix=self.vm2_fixture.vm_ip) 
        assert self.verify_gr_llgr_flags(flags=['Stale','LlgrStale'], vn_fix=self.vn_fix, prefix=self.ipv6_addr) 

        self.inputs.start_container([self.inputs.bgp_ips[1]], container='control') 

        assert self.verify_gr_llgr_flags(flags=['None'], vn_fix=self.vn_fix, prefix=self.vm2_fixture.vm_ip) 
        assert self.verify_gr_llgr_flags(flags=['None'], vn_fix=self.vn_fix, prefix=self.ipv6_addr) 

        if not self.verify_ping_stats():
            self.logger.error("Error in ping stats")
            return False

        return True

    # RESTART of controller 
    @test.attr(type=['llgr'])
    @preposttest_wrapper
    def test_gr_agent_restart(self):
        '''
           Check Traffic to VM on different host goes fine when control node session is restarted during GR configuration 
           holdtime of 0sec + stale time of 60sec 
           In this case route state is immediately changed to stale , holdtime is not triggered
        '''
        timeout = 30  
        self.set_gr_llgr(gr=30,llgr=0,mode='enable',bgp_hlp='disable',xmpp_hlp='enable')

        if not self.create_vm_start_ping(ping_count=3000):
            self.logger.error("Error in creating VM")
            return False

        # Get the labels for the routes 
        self.inputs.restart_container(self.inputs.compute_ips, container='agent') 

        time.sleep(timeout)

        # check to see if labels for the routes were not modified

        if not self.verify_ping_stats():
            self.logger.error("Error in ping stats")
            return False

        return True

    # RESTART of agent 
    @test.attr(type=['llgr'])
    @preposttest_wrapper
    def test_llgr_agent_restart(self):
        '''
           Check Traffic to VM on different host goes fine when control node session is restarted during LLGR configuration 
           holdtime of 0sec + stale time of 30sec and llgr time of 60 
        '''
        # holdtime of 90sec + stale time of 30sec 
        timeout = 50  
        self.set_gr_llgr(gr=35,llgr=120,mode='enable',bgp_hlp='disable',xmpp_hlp='enable')

        #self.set_gr_llgr(mode='disable')
        if not self.create_vm_start_ping(ping_count=4000):
            self.logger.error("Error in creating VM")
            return False

        self.inputs.restart_container(self.inputs.compute_ips, container='agent') 

        time.sleep(timeout)
 
        if not self.verify_ping_stats():
            self.logger.error("Error in ping stats")
            return False

        return True


    def create_vm_start_ping(self,ping_count = 10):

        self.vn_fix = self.useFixture(VNFixture(connections=self.connections, router_external=True,rt_number=2500,af='dual'))

        self.vm1_fixture = self.create_vm(self.vn_fix)

        self.vm2_fixture = self.create_vm(self.vn_fix)

        assert self.vm1_fixture.wait_till_vm_is_up()

        assert self.vm2_fixture.wait_till_vm_is_up()

        assert self.vm1_fixture.ping_with_certainty(self.vm2_fixture.vm_ip)

        cmd = 'ping %s -c %s -i 0.01 > %s' % (self.vm2_fixture.vm_ip,ping_count,self.result_file)

        self.logger.info('Starting ping on %s to %s' % (
                              self.vm1_fixture.vm_name,self.vm2_fixture.vm_ip))

        self.logger.debug('ping cmd : %s' %(cmd))

        self.vm1_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True,
            as_daemon=True, pidfile=self.pid_file)
    
        self.ipv6_addr =  ''.join(self.vm2_fixture.get_vm_ips(vn_fq_name=self.vn_fix.vn_fq_name,af='v6'))

        self.vm1_ipv6_addr =  ''.join(self.vm1_fixture.get_vm_ips(vn_fq_name=self.vn_fix.vn_fq_name,af='v6'))

        cmd = 'ping6 %s -c %s -i 0.01 > %s' % (self.ipv6_addr,ping_count,self.result6_file)

        self.logger.info('Starting ping on %s to %s' % (
                              self.vm1_fixture.vm_name,self.ipv6_addr))

        self.logger.debug('ping6 cmd : %s' %(cmd))

        self.vm1_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True,
            as_daemon=True, pidfile=self.pid6_file)

        return True 

    def verify_ping_stats(self):

        result,pkts_trans,pkts_recv = self.verify_traffic_loss(
                vm_fixture = self.vm1_fixture,result_file = self.result_file)

        if not result :
            self.logger.error("Error in getting stats")
            return False

        if pkts_trans != pkts_recv:
            self.logger.error("sent pkts not matching with recv: %s , %s "%(pkts_trans,pkts_recv))
            return False

        result,pkts_trans,pkts_recv = self.verify_traffic_loss(
                vm_fixture = self.vm1_fixture,result_file = self.result6_file)

        if not result :
            self.logger.error("Error in getting stats")
            return False

        if pkts_trans != pkts_recv:
            self.logger.error("sent pkts not matching with recv: %s , %s "%(pkts_trans,pkts_recv))
            return False

        return True
