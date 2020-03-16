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
import test

'''
   This test suite runs only on control node scale setup 
   Where MX is connected to one of the control node and two 
   compute nodes were connected to each of the agent which 
   is taken care during Base class setup
   In each of the steps following steps were exectued 
   Launch a Sigle VM for North/South traffic 
   Start ping from VM IP to MX loopback IP
   Start a failure ( link failure / MX restart )
   Check flags for Route advertised by MX is in GR/LLGR state
   Check if there is a drop in traffic
   Restore the failure 
   Check for BGP open message for notification bit and restart
   capabilities advertised by controller to MX
'''

class TestLlgr(TestLlgrBase):

    @classmethod
    def setUpClass(cls):
        super(TestLlgr, cls).setUpClass()
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
        super(TestLlgr, cls).tearDownClass()
        return True
    # end cleanUp

    @test.attr(type=['llgr'])
    @preposttest_wrapper
    def test_gr_mx(self):
        '''
           Check Traffic to MX goes fine when BGP session is down during GR configuration 
        '''
        self.set_gr_llgr(gr=35,llgr=0,mode='enable')
        #self.set_gr_llgr(mode='disable')
        if not self.create_vm_start_ping(ping_count=30):
            self.logger.error("Error in creating VM")
            return False

        session , pcap_file = start_tcpdump_for_intf(self.inputs.bgp_ips[0], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['username'], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['password'],
                              'bond0', filters='-vvv port bgp') 

        self.set_bgp_peering(mode='disable')

        self.addCleanup(self.set_bgp_peering,mode='enable')

        time.sleep(self.timeout)

        assert self.verify_gr_llgr_flags(flags=['Stale'], vn_fix=self.vn_fix, prefix=self.mx_loopback_ip)

        assert self.verify_gr_llgr_flags(flags=['Stale'], vn_fix=self.vn_fix, prefix=self.mx_loopback_ip6)

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
    def test_gr_llgr_mx(self):
        '''
           Check Traffic to MX goes fine when BGP session is down durin GR and LLGR configuration 
        '''
        timeout = 60
        #enable llgr 
        self.set_gr_llgr(gr=35,llgr=60,mode='enable')

        #self.set_gr_llgr(mode='disable')
        if not self.create_vm_start_ping(ping_count=60):
            self.logger.error("Error in creating VM")
            return False

        session , pcap_file = start_tcpdump_for_intf(self.inputs.bgp_ips[0], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['username'], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['password'],
                              'bond0', filters='-vvv port bgp') 

        self.set_bgp_peering(mode='disable')

        self.addCleanup(self.set_bgp_peering,mode='enable')

        time.sleep(timeout)

        assert self.verify_gr_llgr_flags(flags=['Stale','LlgrStale'], vn_fix=self.vn_fix, prefix=self.mx_loopback_ip)
        assert self.verify_gr_llgr_flags(flags=['Stale','LlgrStale'], vn_fix=self.vn_fix, prefix=self.mx_loopback_ip6)

        if not self.verify_ping_stats():
            self.logger.error("Error in ping stats")
            return False

        self.set_bgp_peering(mode='enable')

        time.sleep(20)

        stop_tcpdump_for_intf(session, pcap_file)

        if not self.verify_gr_bgp_flags(pcap_file=pcap_file,host=self.inputs.bgp_ips[0]):
            self.logger.error("Error in restart gr flags of Open message")
            return False

        if not self.verify_llgr_bgp_flags(pcap_file=pcap_file,host=self.inputs.bgp_ips[0]):
            self.logger.error("Error in restart llgr flags of Open message")
            return False

        return True

    @test.attr(type=['llgr'])
    @preposttest_wrapper
    def test_llgr_mx(self):
        '''
           Check Traffic to MX goes fine when BGP session is down during LLGR configuration 
        '''
        timeout = 60
        #enable llgr 
        self.set_gr_llgr(gr=0,llgr=60,mode='enable')

        #self.set_gr_llgr(mode='disable')
        if not self.create_vm_start_ping(ping_count=60):
            self.logger.error("Error in creating VM")
            return False

        session , pcap_file = start_tcpdump_for_intf(self.inputs.bgp_ips[0], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['username'], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['password'],
                              'bond0', filters='-vvv port bgp') 

        self.set_bgp_peering(mode='disable')

        self.addCleanup(self.set_bgp_peering,mode='enable')

        time.sleep(timeout)

        assert self.verify_gr_llgr_flags(flags=['Stale','LlgrStale'], vn_fix=self.vn_fix, prefix=self.mx_loopback_ip)
        assert self.verify_gr_llgr_flags(flags=['Stale','LlgrStale'], vn_fix=self.vn_fix, prefix=self.mx_loopback_ip6)

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
    def test_gr_mx_restart(self):
        '''
           Check Traffic to MX goes fine when rpd is restarted during GR configuration 
        '''
        #enable llgr 
        self.set_gr_llgr(gr=35,llgr=0,mode='enable')

        #self.set_gr_llgr(mode='disable')
        if not self.create_vm_start_ping(ping_count=30):
            self.logger.error("Error in creating VM")
            return False

        session , pcap_file = start_tcpdump_for_intf(self.inputs.bgp_ips[0], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['username'], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['password'],
                              'bond0', filters='-vvv port bgp') 

        # restart rpd 
        self.mx1_handle.restart('routing immediately')
        #self.stop_bgp_peering()

        time.sleep(self.timeout)
  
        assert self.verify_gr_llgr_flags(flags=['None'], vn_fix=self.vn_fix, prefix=self.mx_loopback_ip)

        assert self.verify_gr_llgr_flags(flags=['None'], vn_fix=self.vn_fix, prefix=self.mx_loopback_ip6)

        if not self.verify_ping_stats():
            self.logger.error("Error in ping stats")
            return False

        time.sleep(20)

        stop_tcpdump_for_intf(session, pcap_file)

        if not self.verify_gr_bgp_flags(pcap_file=pcap_file,host=self.inputs.bgp_ips[0]):
            self.logger.error("Error in restart gr flags of Open message")
            return False

        return True

    @test.attr(type=['llgr'])
    @preposttest_wrapper
    def test_gr_mx_restart_gracefully(self):
        '''
           Check Traffic to MX goes fine when rpd is restarted gracefully during GR configuration 
        '''
        #enable llgr 
        self.set_gr_llgr(gr=35,llgr=0,mode='enable')

        #self.set_gr_llgr(mode='disable')
        if not self.create_vm_start_ping(ping_count=30):
            self.logger.error("Error in creating VM")
            return False

        session , pcap_file = start_tcpdump_for_intf(self.inputs.bgp_ips[0], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['username'], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['password'],
                              'bond0', filters='-vvv port bgp') 

        # restart rpd 
        self.mx1_handle.restart('routing gracefully')

        time.sleep(self.timeout)
  
        assert self.verify_gr_llgr_flags(flags=['None'], vn_fix=self.vn_fix, prefix=self.mx_loopback_ip)

        assert self.verify_gr_llgr_flags(flags=['None'], vn_fix=self.vn_fix, prefix=self.mx_loopback_ip6)

        if not self.verify_ping_stats():
            self.logger.error("Error in ping stats")
            return False

        time.sleep(20)

        stop_tcpdump_for_intf(session, pcap_file)

        if not self.verify_gr_bgp_flags(pcap_file=pcap_file,host=self.inputs.bgp_ips[0]):
            self.logger.error("Error in restart gr flags of Open message")
            return False

        return True

    @test.attr(type=['llgr'])
    @preposttest_wrapper
    def test_llgr_mx_restart(self):
        '''
           Check Traffic to MX goes fine when rpd is restarted immediately during LLGR configuration 
        '''
        timeout = 60
        #enable llgr 
        self.set_gr_llgr(gr=35,llgr=60,mode='enable')

        if not self.create_vm_start_ping(ping_count=60):
            self.logger.error("Error in creating VM")
            return False

        session , pcap_file = start_tcpdump_for_intf(self.inputs.bgp_ips[0], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['username'], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['password'],
                              'bond0', filters='-vvv port bgp') 

        self.mx1_handle.restart('routing immediately')

        time.sleep(timeout)

        assert self.verify_gr_llgr_flags(flags=['None'], vn_fix=self.vn_fix, prefix=self.mx_loopback_ip)
        assert self.verify_gr_llgr_flags(flags=['None'], vn_fix=self.vn_fix, prefix=self.mx_loopback_ip6)

        if not self.verify_ping_stats():
            self.logger.error("Error in ping stats")
            return False

        time.sleep(20)

        stop_tcpdump_for_intf(session, pcap_file)

        if not self.verify_llgr_bgp_flags(pcap_file=pcap_file,host=self.inputs.bgp_ips[0]):
            self.logger.error("Error in llgr restart flags of Open message")
            return False

        return True


    @test.attr(type=['llgr'])
    @preposttest_wrapper
    def test_llgr_mx_restart_gracefully(self):
        '''
           Check Traffic to MX goes fine when rpd is restarted gracefully during LLGR configuration 
        '''
        #enable llgr 
        timeout = 60
        self.set_gr_llgr(gr=35,llgr=60,mode='enable')

        if not self.create_vm_start_ping(ping_count=60):
            self.logger.error("Error in creating VM")
            return False

        session , pcap_file = start_tcpdump_for_intf(self.inputs.bgp_ips[0], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['username'], 
                              self.inputs.host_data[self.inputs.bgp_ips[0]]['password'],
                              'bond0', filters='-vvv port bgp') 

        self.mx1_handle.restart('routing gracefully')

        time.sleep(timeout)

        assert self.verify_gr_llgr_flags(flags=['None'], vn_fix=self.vn_fix, prefix=self.mx_loopback_ip)
        assert self.verify_gr_llgr_flags(flags=['None'], vn_fix=self.vn_fix, prefix=self.mx_loopback_ip6)

        if not self.verify_ping_stats():
            self.logger.error("Error in ping stats")
            return False

        time.sleep(20)

        stop_tcpdump_for_intf(session, pcap_file)

        if not self.verify_llgr_bgp_flags(pcap_file=pcap_file,host=self.inputs.bgp_ips[0]):
            self.logger.error("Error in llgr restart flags of Open message")
            return False

        return True

    def create_vm_start_ping(self,ping_count = 10):
        self.vn_fix = self.useFixture(VNFixture(connections=self.connections, router_external=True,rt_number=2500,af='dual'))

        self.vm1_fixture = self.create_vm(self.vn_fix,node_name=self.inputs.get_node_name(self.host_list[0]))

        assert self.vm1_fixture.wait_till_vm_is_up()

        assert self.vm1_fixture.ping_with_certainty(self.mx_loopback_ip)
   
        cmd = 'ping %s -c %s > %s' % (self.mx_loopback_ip,ping_count,self.result_file)

        self.logger.info('Starting ping on %s to %s' % (
                              self.vm1_fixture.vm_name,self.mx_loopback_ip))

        self.logger.debug('ping cmd : %s' %(cmd))

        self.vm1_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True,
            as_daemon=True, pidfile=self.pid_file)

        cmd = 'ping6 %s -c %s > %s' % (self.mx_loopback_ip6,ping_count,self.result6_file)

        self.logger.info('Starting ping on %s to %s' % (
                              self.vm1_fixture.vm_name,self.mx_loopback_ip6))

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

