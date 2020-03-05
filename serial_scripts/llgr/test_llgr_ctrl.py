from __future__ import absolute_import
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
from .base import TestLlgrBase
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
   Start ping from VM IP to MX loopback IP
   Start a failure ( link failure / MX restart )
   Check flags for Route advertised by MX is in GR/LLGR state
   Check if there is a drop in traffic
   Restore the failure 
   Check for BGP open message for notification bit and restart
   capabilities advertised by controller to MX
'''


class TestLlgrCtrl(TestLlgrBase):

    @classmethod
    def setUpClass(cls):

        super(TestLlgrCtrl, cls).setUpClass()
        cls.set_headless_mode(mode='enable')
        cls.mx_loopback_ip = '121.1.1.1'
        cls.mx_loopback_ip6 = '2002::1'
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
        cls.set_headless_mode(mode='disable')
        cls.inputs.start_service('contrail-control', [cls.inputs.bgp_ips[1]], container='control')
        super(TestLlgrCtrl, cls).tearDownClass()
        return True
    # end cleanUp

    @test.attr(type=['llgr'])
    @preposttest_wrapper
    def test_gr_ctrl(self):
        '''
           Check Traffic to VM on different host goes fine when BGP session is down during GR configuration 
           holdtime of 90sec + stale time of 35sec 
        '''
        timeout = 90  

        self.set_gr_llgr(gr=35,llgr=0,mode='enable')

        #self.set_gr_llgr(mode='disable')
        if not self.create_vm_start_ping(ping_count=3000):
            self.logger.error("Error in creating VM")
            return False

        session , pcap_file = start_tcpdump_for_intf(self.inputs.bgp_ips[0], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['username'], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['password'],
                              'bond0', filters='-vvv port bgp') 

        self.set_bgp_peering(mode='disable')

        self.addCleanup(self.set_bgp_peering,mode='enable')

        time.sleep(timeout)
 
        if not self.verify_gr_llgr_flags(flags=['Stale'], vn_fix=self.vn_fix, prefix=self.vm2_fixture.vm_ip):
            self.logger.error("Stale flag is not set for route : %s"%self.vm2_fixture.vm_ip)
            return False

        if not self.verify_gr_llgr_flags(flags=['Stale'], vn_fix=self.vn_fix, prefix=self.ipv6_addr):
            self.logger.error("Stale flag is not set for route : %s"%self.ipv6_addr)
            return False

        if not self.verify_ping_stats():
            self.logger.error("Error in ping stats")
            return False

        self.set_bgp_peering(mode='enable')
 
        time.sleep(20)

        stop_tcpdump_for_intf(session, pcap_file)

        if not self.verify_gr_bgp_flags(pcap_file=pcap_file,host=self.inputs.bgp_ips[0]):
            self.logger.error("Error in restart GR flags of Open message")
            return False

        return True

    @test.attr(type=['llgr'])
    @preposttest_wrapper
    def test_gr_llgr_ctrl(self):
        '''
           Check Traffic to VM on different host goes fine when BGP session is down during GR and LLGR configuration 
           holdtime of 90sec + stale time of 30sec + llgr stale time of 60sec
        '''
        timeout = 140  

        self.set_gr_llgr(gr=35,llgr=60,mode='enable')

        #self.set_gr_llgr(mode='disable')
        if not self.create_vm_start_ping(ping_count=6000):
            self.logger.error("Error in creating VM")
            return False

        session , pcap_file = start_tcpdump_for_intf(self.inputs.bgp_ips[0], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['username'], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['password'],
                              'bond0', filters='-vvv port bgp') 

        self.set_bgp_peering(mode='disable')

        self.addCleanup(self.set_bgp_peering,mode='enable')

        time.sleep(timeout)
 
        if not self.verify_gr_llgr_flags(flags=['Stale','LlgrStale'], vn_fix=self.vn_fix, prefix=self.vm2_fixture.vm_ip):
            self.logger.error("Stale flag is not set for route : %s"%self.vm2_fixture.vm_ip)
            return False

        if not self.verify_gr_llgr_flags(flags=['Stale','LlgrStale'], vn_fix=self.vn_fix, prefix=self.ipv6_addr):
            self.logger.error("Stale flag is not set for route : %s"%self.ipv6_addr)
            return False

        if not self.verify_ping_stats():
            self.logger.error("Error in ping stats")
            return False

        self.set_bgp_peering(mode='enable')

        time.sleep(20)

        stop_tcpdump_for_intf(session, pcap_file)

        if not self.verify_llgr_bgp_flags(pcap_file=pcap_file,host=self.inputs.bgp_ips[0]):
            self.logger.error("Error in llgr restart flags of Open message")
            return False

        return True


    @test.attr(type=['llgr'])
    @preposttest_wrapper
    def test_llgr_ctrl(self):
        '''
           Check Traffic to VM on different host goes fine when BGP session is down during GR and LLGR configuration 
           holdtime of 90sec + llgr stale time of 60sec 
        '''
        #enable llgr 
        # holdtime of 90sec + stale time of 30sec 
        timeout = 100  

        self.set_gr_llgr(gr=0,llgr=60,mode='enable')

        #self.set_gr_llgr(mode='disable')
        if not self.create_vm_start_ping(ping_count=6000):
            self.logger.error("Error in creating VM")
            return False

        session , pcap_file = start_tcpdump_for_intf(self.inputs.bgp_ips[0], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['username'], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['password'],
                              'bond0', filters='-vvv port bgp') 

        self.set_bgp_peering(mode='disable')

        self.addCleanup(self.set_bgp_peering,mode='enable')

        time.sleep(timeout)
 
        if not self.verify_gr_llgr_flags(flags=['Stale','LlgrStale'], vn_fix=self.vn_fix, prefix=self.vm2_fixture.vm_ip):
            self.logger.error("Stale flag is not set for route : %s"%self.vm2_fixture.vm_ip)
            return False

        if not self.verify_gr_llgr_flags(flags=['Stale','LlgrStale'], vn_fix=self.vn_fix, prefix=self.ipv6_addr):
            self.logger.error("Stale flag is not set for route : %s"%self.ipv6_addr)
            return False

        if not self.verify_ping_stats():
            self.logger.error("Error in ping stats")
            return False

        self.set_bgp_peering(mode='enable')

        time.sleep(20)

        stop_tcpdump_for_intf(session, pcap_file)

        if not self.verify_llgr_bgp_flags(pcap_file=pcap_file,host=self.inputs.bgp_ips[0]):
            self.logger.error("Error in llgr restart flags of Open message")
            return False

        return True

    # RESTART of controller 
    @test.attr(type=['llgr'])
    @preposttest_wrapper
    def test_gr_ctrl_restart(self):
        '''
           Check Traffic to VM on different host goes fine when control node session is restarted during GR configuration 
           holdtime of 0sec + stale time of 60sec 
           In this case route state is immediately changed to stale , holdtime is not triggered
        '''
        timeout = 40  
        self.set_gr_llgr(gr=60,llgr=0,mode='enable')

        #self.set_gr_llgr(mode='disable')
        if not self.create_vm_start_ping(ping_count=3000):
            self.logger.error("Error in creating VM")
            return False

        self.inputs.stop_service('contrail-control', [self.inputs.bgp_ips[1]], container='control')

        time.sleep(timeout)

        assert self.verify_gr_llgr_flags(flags=['Stale'], vn_fix=self.vn_fix, prefix=self.vm2_fixture.vm_ip) 
        assert self.verify_gr_llgr_flags(flags=['Stale'], vn_fix=self.vn_fix, prefix=self.ipv6_addr) 

        self.inputs.start_service('contrail-control', [self.inputs.bgp_ips[1]], container='control')

        if not self.verify_ping_stats():
            self.logger.error("Error in ping stats")
            return False

        return True


    # RESTART of controller 
    @test.attr(type=['llgr'])
    @preposttest_wrapper
    def test_llgr_ctrl_restart(self):
        '''
           Check Traffic to VM on different host goes fine when control node session is restarted during LLGR configuration 
           holdtime of 0sec + stale time of 30sec and llgr time of 60 
        '''
        # holdtime of 90sec + stale time of 30sec 
        timeout = 50  
        self.set_gr_llgr(gr=35,llgr=60,mode='enable')

        #self.set_gr_llgr(mode='disable')
        if not self.create_vm_start_ping(ping_count=4000):
            self.logger.error("Error in creating VM")
            return False

        self.inputs.stop_service('contrail-control', [self.inputs.bgp_ips[1]], container='control')

        time.sleep(timeout)
 
        assert self.verify_gr_llgr_flags(flags=['Stale','LlgrStale'], vn_fix=self.vn_fix, prefix=self.vm2_fixture.vm_ip) 
        assert self.verify_gr_llgr_flags(flags=['Stale','LlgrStale'], vn_fix=self.vn_fix, prefix=self.ipv6_addr) 

        self.inputs.start_service('contrail-control', [self.inputs.bgp_ips[1]], container='control')

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
