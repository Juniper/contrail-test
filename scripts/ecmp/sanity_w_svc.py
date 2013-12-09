import os
import fixtures
import testtools
import unittest
import traffic_tests
import time
from connections import ContrailConnections
from contrail_test_init import ContrailTestInit
from vn_test import *
from floating_ip import *
from quantum_test import *
from vnc_api_test import *
from nova_test import *
from vm_test import *
from tcutils.wrappers import preposttest_wrapper
from servicechain.firewall.verify import VerifySvcFirewall
from ecmp.ecmp_traffic import ECMPTraffic
from ecmp.ecmp_verify import ECMPVerify
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver

class ECMPSvcMonSanityFixture(testtools.TestCase, VerifySvcFirewall, ECMPTraffic, ECMPVerify):
    
    def setUp(self):
        super (ECMPSvcMonSanityFixture, self).setUp()
        if 'PARAMS_FILE' in os.environ :
            self.ini_file= os.environ.get('PARAMS_FILE')
        else:
            self.ini_file= 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.quantum_fixture = self.connections.quantum_fixture
        self.nova_fixture = self.connections.nova_fixture
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.analytics_obj=self.connections.analytics_obj
        self.api_s_inspect= self.connections.api_server_inspect
        self.cn_inspect= self.connections.cn_inspect
        self.agent_inspect= self.connections.agent_inspect
        self.quantum_fixture= self.connections.quantum_fixture

    def cleanUp(self):
        self.logger.info("Cleaning up")
        super(SvcMonSanityFixture, self).cleanUp()
 
    @preposttest_wrapper
    def test_ecmp_with_svc_with_fip_dest(self):
        """Validate ECMP with service chaining and FIP at the destination"""
        self.verify_svc_in_network_datapath(si_count=1, svc_scaling= True, max_inst= 3)
        self.logger.info('.'*80)
        self.logger.info('We will create 3 VMs at the destination and make them share the same FIP address')
        self.logger.info('.'*80)
        self.my_fip_name = 'fip'
        self.my_fip= '10.1.1.10'
        
        #self.fvn= self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name='fvn', inputs= self.inputs, subnets=['30.1.1.0/29']))
        self.vm2_1= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,vn_obj = self.vn2_fixture.obj, ram= 4096, image_name= 'ubuntu-traffic', vm_name= 'vm2_1'))
        self.vm2_2= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,vn_obj = self.vn2_fixture.obj, ram= 4096, image_name= 'ubuntu-traffic', vm_name= 'vm2_2'))

        #assert self.fvn.verify_on_setup()
        assert self.vm2_1.verify_on_setup()
        assert self.vm2_2.verify_on_setup()

        self.fip_fixture= self.useFixture(FloatingIPFixture( project_name= self.inputs.project_name, inputs = self.inputs,connections= self.connections, pool_name = 'some-pool1', vn_id= self.vn1_fixture.vn_id ))
        assert self.fip_fixture.verify_on_setup()

        self.fvn_obj= self.vnc_lib.virtual_network_read( id = self.vn1_fixture.vn_id )
        self.fip_pool_obj = FloatingIpPool( 'some-pool1', self.fvn_obj )
        self.fip_obj = FloatingIp( 'fip', self.fip_pool_obj, '10.1.1.10', True)

        self.vn2_fq_name= self.vn2_fixture.vn_fq_name
        self.vn2_vrf_name= self.vn2_fixture.vrf_name
        self.vn2_ri_name= self.vn2_fixture.ri_name
        self.vmi1_id=  self.vm2_fixture.tap_intf[self.vn2_fixture.vn_fq_name]['uuid']
        self.vmi2_id=  self.vm2_1.tap_intf[self.vn2_fixture.vn_fq_name]['uuid']
        self.vmi3_id=  self.vm2_2.tap_intf[self.vn2_fixture.vn_fq_name]['uuid']
        self.vm2_intf = self.vnc_lib.virtual_machine_interface_read( id = self.vmi1_id )
        self.vm2_1_intf = self.vnc_lib.virtual_machine_interface_read( id = self.vmi2_id )
        self.vm2_2_intf = self.vnc_lib.virtual_machine_interface_read( id = self.vmi3_id )
        for intf in [self.vm2_intf, self.vm2_1_intf, self.vm2_2_intf]:
            self.fip_obj.add_virtual_machine_interface(intf)
        self.vnc_lib.floating_ip_create(self.fip_obj)
        self.addCleanup(self.vnc_lib.floating_ip_delete,self.fip_obj.fq_name)
        svm_ids= self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(self.vn1_fixture, self.vm1_fixture, svm_ids)

        vm_list= [self.vm1_fixture, self.vm2_fixture, self.vm2_1, self.vm2_2]
        for vm in vm_list:
            self.logger.info('Getting the local_ip of the VM')
            vm.verify_vm_in_agent()
            out= self.nova_fixture.wait_till_vm_is_up( vm.vm_obj)
            if out == False: return {'result':out, 'msg':"%s failed to come up"%vm.vm_name}
            else: time.sleep(5); self.logger.info('Installing Traffic package on %s ...'%vm.vm_name); vm.install_pkg("Traffic")

        # Starting two flows of TCP Traffic from fvn_vm1 to 10.1.1.10

        self.logger.info("-"*80)
        self.logger.info('Starting TCP Traffic from %s to 10.1.1.10'%self.vm1_fixture.vm_name)
        self.logger.info("-"*80)

        recv_vm_list= []
        recv_vm_list= [self.vm2_fixture, self.vm2_1, self.vm2_2]
        profile= {}
        sender= {}
        receiver= {}

        rx_vm_node_ip= {}
        rx_local_host= {}
        recv_host= {}


        stream1 = Stream(protocol="ip", proto="tcp", src=self.vm1_fixture.vm_ip,dst= '10.1.1.10', sport= unicode(8000), dport=unicode(9000))
        stream2 = Stream(protocol="ip", proto="tcp", src=self.vm1_fixture.vm_ip,dst= '10.1.1.10', sport= unicode(8000), dport=unicode(9001))
        stream3 = Stream(protocol="ip", proto="tcp", src=self.vm1_fixture.vm_ip,dst= '10.1.1.10', sport= unicode(8000), dport=unicode(9002))
        stream_list= [stream1, stream2, stream3]

        tx_vm_node_ip=  self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(self.vm1_fixture.vm_obj)]['host_ip']
        tx_local_host = Host(tx_vm_node_ip, self.inputs.username, self.inputs.password)
        send_host = Host(self.vm1_fixture.local_ip)

        for vm in recv_vm_list:
            rx_vm_node_ip[vm]= self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(vm.vm_obj)]['host_ip']
            rx_local_host[vm]= Host(rx_vm_node_ip[vm], self.inputs.username, self.inputs.password)
            recv_host[vm] =  Host(vm.local_ip)
        count= 0
        for stream in stream_list:
            profile[stream]={}
            receiver[stream] = {}
            for vm in recv_vm_list:
                count= count+1
                recv_filename= 'recvtcp_%s'%count
                profile[stream][vm] = ContinuousProfile(stream=stream, listener= vm.vm_ip, chksum= True)
                receiver[stream][vm] = Receiver(recv_filename, profile[stream][vm], rx_local_host[vm], recv_host[vm], self.inputs.logger)
                receiver[stream][vm].start()
        count= 0
        for stream in stream_list:
            sender[stream]= {}
            count= count+1
            send_filename= 'sendtcp_%s'%count
            profile[stream]= ContinuousProfile(stream=stream, chksum= True)
            sender[stream]= Sender(send_filename, profile[stream], tx_local_host, send_host, self.inputs.logger)
            sender[stream].start()
        self.logger.info('Sending traffic for 10 seconds')
        sleep(10)
        for stream in stream_list:
            sender[stream].stop()

        for stream in stream_list:
            for vm in recv_vm_list:
                receiver[stream][vm].stop()

        stream_sent_count = {}
        stream_recv_count = {}
        result= True

        for stream in stream_list:
            stream_sent_count[stream]= 0
            stream_recv_count[stream]= 0
            stream_sent_count[stream]= stream_sent_count[stream] + sender[stream].sent
            for vm in recv_vm_list:
                stream_recv_count[stream]= stream_recv_count[stream] + receiver[stream][vm].recv
            if abs(stream_recv_count[stream] - stream_sent_count[stream]) < 5 :
                self.logger.info('%s packets sent and %s packets received in Stream. No Packet Loss.'%(stream_sent_count[stream], stream_recv_count[stream]))
            else:
                result= False
                assert result, '%s packets sent and %s packets received in Stream. Packet Loss.'%(stream_sent_count[stream], stream_recv_count[stream])

        #Checking Flow Records

        flow_result= False
        flow_result2= False
        flow_result3= False

        rev_flow_result= False
        rev_flow_result1= False
        rev_flow_result2= False

        vn1_vrf_id= self.vm1_fixture.get_vrf_id(self.vn1_fixture.vn_fq_name, self.vn1_fixture.vrf_name)
        vn2_vrf_id= self.vm2_fixture.get_vrf_id(self.vn2_fixture.vn_fq_name, self.vn2_fixture.vrf_name)
        inspect_h100= self.agent_inspect[self.vm1_fixture.vm_node_ip]

        src_port= unicode(8000)
        dpi1= unicode(9000)
        dpi2= unicode(9001)
        dpi3= unicode(9002)

        flow_rec1= inspect_h100.get_vna_fetchflowrecord(vrf=vn1_vrf_id,sip=self.vm1_fixture.vm_ip,dip='10.1.1.10',sport=src_port,dport=dpi1,protocol='6')
        flow_rec2= inspect_h100.get_vna_fetchflowrecord(vrf=vn1_vrf_id,sip=self.vm1_fixture.vm_ip,dip='10.1.1.10',sport=src_port,dport=dpi2,protocol='6')
        flow_rec3= inspect_h100.get_vna_fetchflowrecord(vrf=vn1_vrf_id,sip=self.vm1_fixture.vm_ip,dip='10.1.1.10',sport=src_port,dport=dpi3,protocol='6')

        dpi_list= [dpi1, dpi2, dpi3]
        
        rev_flow_rec= {}
        rev_flow_result= False
        for dpi in dpi_list:
            rev_flow_rec[dpi]= inspect_h100.get_vna_fetchflowrecord(vrf=vn1_vrf_id,sip='10.1.1.10',dip=self.vm1_fixture.vm_ip,sport=dpi,dport=src_port,protocol='6')
            if rev_flow_rec[dpi]:
                self.logger.info('Reverse Flow from 10.1.1.10 to %s exists'%self.vm1_fixture.vm_ip)
                rev_flow_result= True
            else:
                 rev_flow_result= rev_flow_result or False
        assert rev_flow_result, 'Records for the reverse flow not seen on any of the agents'
                

        flow_recs= []
        flow_recs= [flow_rec1, flow_rec2, flow_rec3]

        flow_result= True
        for flow_rec in flow_recs:
            if flow_rec is None:
                flow_result= False
            if flow_result is True:
                self.logger.info('Flows from %s to 10.1.1.10 exist on Agent %s'%(self.vm1_fixture.vm_ip, self.vm1_fixture.vm_node_ip))
            else:
                assert flow_result,'Flows from %s to 10.1.1.10 not seen on Agent %s'%(self.vm1_fixture.vm_ip,self.vm1_fixture.vm_node_ip)

        return True
    #end test_ecmp_with_svc_with_fip_dest
 
    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_3_instance_reboot_nodes(self):
        """Validate ECMP after restarting control and vrouter services with service chaining in-network mode datapath having 
        service instance. Check the ECMP behaviour after rebooting the nodes"""
        cmd= 'reboot'
        self.verify_svc_in_network_datapath(si_count=1, svc_scaling= True, max_inst= 3, flavor= 'm1.large')
        svm_ids= self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(self.vn1_fixture, self.vm1_fixture, svm_ids)
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        
        self.logger.info('Will reboot the Compute Nodes')
        for compute_ip in self.inputs.compute_ips:
            self.logger.info('Will reboot the node %s'%socket.gethostbyaddr(compute_ip)[0])
            self.inputs.run_cmd_on_server(compute_ip,cmd,username='root',password='c0ntrail123')
            sleep(120)
        
        self.logger.info('Will check the state of the SIs and power it ON, if it is in SHUTOFF state')
        for vm in self.nova_fixture.get_vm_list():
            if vm.status != 'ACTIVE':
                self.logger.info('Will Power-On %s'%vm.name)
                vm.start()
                sleep(60)
                if ((vm.name == self.vm1_fixture.vm_name) or (vm.name == self.vm2_fixture.vm_name)):
                    vm.stop()
                    sleep(15)
                    vm.start()
                    sleep(15)
        self.get_rt_info_tap_intf_list(self.vn1_fixture, self.vm1_fixture, svm_ids)
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        
        self.logger.info('Will reboot the Control Nodes')
        for bgp_ip in self.inputs.bgp_ips:
            self.logger.info('Will reboot the node %s'%socket.gethostbyaddr(bgp_ip)[0])
            self.inputs.run_cmd_on_server(bgp_ip,cmd,username='root',password='c0ntrail123')
            sleep(120)
        self.logger.info('Will check the state of the SIs and power it ON, if it is in SHUTOFF state')
        for vm in self.nova_fixture.get_vm_list():
            if vm.status != 'ACTIVE':
                self.logger.info('Will Power-On %s'%vm.name)
                vm.start()
                sleep(60)
                if ((vm.name == self.vm1_fixture.vm_name) or (vm.name == self.vm2_fixture.vm_name)):
                    vm.stop()
                    sleep(15)
                    vm.start()
                    sleep(15)
        self.get_rt_info_tap_intf_list(self.vn1_fixture, self.vm1_fixture, svm_ids)
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        
        return True
    #end test_ecmp_svc_in_network_with_3_instance_reboot_nodes
   
    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_3_instance_reboot(self):
        """Validate ECMP after restarting control and vrouter services with service chaining in-network mode datapath having 
        service instance"""
        self.verify_svc_in_network_datapath(si_count=1, svc_scaling= True, max_inst= 3)
        svm_ids= self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(self.vn1_fixture, self.vm1_fixture, svm_ids)
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)

        for compute_ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter',[compute_ip])
            self.logger.info('Sleeping for 30 seconds')
            sleep(30)
        self.get_rt_info_tap_intf_list(self.vn1_fixture, self.vm1_fixture, svm_ids)
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        
        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('contrail-control',[bgp_ip])
            self.logger.info('Sleeping for 30 seconds')
            sleep(30)
        self.get_rt_info_tap_intf_list(self.vn1_fixture, self.vm1_fixture, svm_ids)
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        return True
    #end test_ecmp_svc_in_network_with_3_instance_reboot
 
    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_3_instance_diff_proto(self):
        """Validate ECMP with service chaining in-network mode datapath having 
        service instance. Send 3 different protocol traffic to the same destination"""
        self.verify_svc_in_network_datapath(si_count=1, svc_scaling= True, max_inst= 3)
        svm_ids= self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(self.vn1_fixture, self.vm1_fixture, svm_ids)
        vm_list= [self.vm1_fixture, self.vm2_fixture]
        for vm in vm_list:
            self.logger.info('Getting the local_ip of the VM')
            vm.verify_vm_in_agent()
            out= self.nova_fixture.wait_till_vm_is_up( vm.vm_obj)
            if out == False: return {'result':out, 'msg':"%s failed to come up"%vm.vm_name}
            else: time.sleep(5); self.logger.info('Installing Traffic package on %s ...'%vm.vm_name); vm.install_pkg("Traffic")

        self.logger.info("-"*80)
        self.logger.info('Starting a stream each of ICMP, UDP and TCP Traffic from %s:8000 to %s:9000'%(self.vm1_fixture.vm_ip, self.vm2_fixture.vm_ip))
        self.logger.info("-"*80)

        stream_list= []
        profile= {}
        sender= {}
        receiver= {}


        stream1 = Stream(protocol="ip", proto="icmp", src=self.vm1_fixture.vm_ip,dst= self.vm2_fixture.vm_ip, sport= unicode(8000), dport=unicode(9000))
        stream2 = Stream(protocol="ip", proto="udp", src=self.vm1_fixture.vm_ip,dst= self.vm2_fixture.vm_ip, sport= unicode(8000), dport=unicode(9000))
        stream3 = Stream(protocol="ip", proto="tcp", src=self.vm1_fixture.vm_ip,dst= self.vm2_fixture.vm_ip, sport= unicode(8000), dport=unicode(9000))
        stream_list= [stream1, stream2, stream3]
 
        tx_vm_node_ip= self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(self.vm1_fixture.vm_obj)]['host_ip']
        tx_local_host= Host(tx_vm_node_ip, self.inputs.username, self.inputs.password)
        send_host= Host(self.vm1_fixture.local_ip)
       
        rx_vm_node_ip= self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(self.vm2_fixture.vm_obj)]['host_ip']
        rx_local_host= Host(rx_vm_node_ip, self.inputs.username, self.inputs.password)
        recv_host=  Host(self.vm2_fixture.local_ip)
        count= 0
        
        for i in range(len(stream_list)):
            profile[i]={}
            sender[i]= {}
            receiver[i] = {}
            count= count+1
            send_filename= 'sendtraffic_%s'%count
            recv_filename= 'recvtraffic_%s'%count
            profile[i] = ContinuousProfile(stream=stream_list[i], chksum= True)
            sender[i]= Sender(send_filename, profile[i], tx_local_host, send_host, self.inputs.logger)
            time.sleep(5)
            receiver[i]= Receiver(recv_filename, profile[i], rx_local_host, recv_host, self.inputs.logger)
            receiver[i].start()
            sender[i].start()
        self.logger.info('Sending traffic for 10 seconds')
        time.sleep(10)
        for i in range(len(stream_list)):
            sender[i].stop()
            time.sleep(5)
            receiver[i].stop()
            time.sleep(5)

        stream_sent_count = 0
        stream_recv_count = 0
        
        result= True
        
        for i in range(len(stream_list)):

            if sender[i].sent == None:
                sender[i].sent = 0
            self.logger.info('%s packets sent in Stream_%s'%(sender[i].sent, i))
            stream_sent_count= stream_sent_count + sender[i].sent

            if receiver[i].recv == None:
                receiver[i].recv = 0
            self.logger.info('%s packets received in Stream_%s'%(receiver[i].recv, i))
            stream_recv_count= stream_recv_count + receiver[i].recv

        self.logger.info('Total %s packets sent out.'%stream_sent_count)
        self.logger.info('Total %s packets received.'%stream_recv_count)
        if abs(stream_recv_count - stream_sent_count) < 5:
                self.logger.info('No Packet Loss Seen')
        else:
            self.logger.info('Packet Loss Seen')
        #Checking Flow Records

        vn1_vrf_id= self.vm1_fixture.get_vrf_id(self.vn1_fixture.vn_fq_name, self.vn1_fixture.vrf_name)
       
        inspect_h100= self.agent_inspect[self.vm1_fixture.vm_node_ip]
        
        flow_rec1= None
        flow_rec2= None
        flow_rec3= None

        dpi=unicode(9000)
        sport=unicode(8000)
        
        flow_rec1= inspect_h100.get_vna_fetchflowrecord(vrf=vn1_vrf_id,sip=self.vm1_fixture.vm_ip,dip=self.vm2_fixture.vm_ip,sport=sport,dport=dpi,protocol='6')
        flow_rec2= inspect_h100.get_vna_fetchflowrecord(vrf=vn1_vrf_id,sip=self.vm1_fixture.vm_ip,dip=self.vm2_fixture.vm_ip,sport=sport,dport=dpi,protocol='17')
        flow_rec3= inspect_h100.get_vna_fetchflowrecord(vrf=vn1_vrf_id,sip=self.vm1_fixture.vm_ip,dip=self.vm2_fixture.vm_ip,sport=unicode(0),dport=unicode(0),protocol='1')

        rev_flow_rec1= inspect_h100.get_vna_fetchflowrecord(vrf=vn1_vrf_id,dip=self.vm1_fixture.vm_ip,sip=self.vm2_fixture.vm_ip,dport=sport,sport=dpi,protocol='6')
        rev_flow_rec2= inspect_h100.get_vna_fetchflowrecord(vrf=vn1_vrf_id,dip=self.vm1_fixture.vm_ip,sip=self.vm2_fixture.vm_ip,dport=sport,sport=dpi,protocol='17')
        rev_flow_rec3= inspect_h100.get_vna_fetchflowrecord(vrf=vn1_vrf_id,dip=self.vm1_fixture.vm_ip,sip=self.vm2_fixture.vm_ip,dport=unicode(0),sport=unicode(0),protocol='1')

        flow_recs= []
        flow_recs= [flow_rec1, flow_rec2, flow_rec3]
        flow_result= True
        for flow_rec in flow_recs:
            if flow_rec is None:
                flow_result= False
        if flow_result is True:
            self.logger.info('Forward Flows exist on Agent %s'%self.vm1_fixture.vm_node_ip)
        else:
            assert flow_result,'No Forward Flows seen on Agent %s'%self.vm1_fixture.vm_node_ip

        rev_flow_recs= []
        rev_flow_recs= [rev_flow_rec1, rev_flow_rec2, rev_flow_rec3]
        rev_flow_result= False
        for rev_flow_rec in rev_flow_recs:
            if rev_flow_rec:
                rev_flow_result= rev_flow_result or True
        if rev_flow_result:
            self.logger.info('Reverse Flows exist on Agent %s'%self.vm1_fixture.vm_node_ip)
        else:
            assert rev_flow_result,'Reverse Flows not seen on Agent %s'%self.vm1_fixture.vm_node_ip

        return True
    #end test_ecmp_svc_in_network_with_3_instance_diff_proto
   
    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_3_instance_incr_dip(self):
        """Validate ECMP with service chaining in-network mode datapath having 
        service instance. Send traffic to 3 different DIPs"""
        self.verify_svc_in_network_datapath(si_count=1, svc_scaling= True, max_inst= 3)
        svm_ids= self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(self.vn1_fixture, self.vm1_fixture, svm_ids)
        dest_vm2= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,vn_obj = self.vn2_fixture.obj, ram= 4096, image_name= 'ubuntu-traffic', vm_name= 'dest_vm2'))
        assert dest_vm2.verify_on_setup()
        dest_vm3= self.useFixture(VMFixture(project_name= self.inputs.project_name, connections= self.connections,vn_obj = self.vn2_fixture.obj, ram= 4096, image_name= 'ubuntu-traffic', vm_name= 'dest_vm3'))
        assert dest_vm3.verify_on_setup()
        vm_list= [self.vm1_fixture, self.vm2_fixture, dest_vm2, dest_vm3]
        for vm in vm_list:
            self.logger.info('Getting the local_ip of the VM')
            vm.verify_vm_in_agent()
            out= self.nova_fixture.wait_till_vm_is_up( vm.vm_obj)
            if out == False: return {'result':out, 'msg':"%s failed to come up"%vm.vm_name}
            else: time.sleep(5); self.logger.info('Installing Traffic package on %s ...'%vm.vm_name); vm.install_pkg("Traffic")

        self.logger.info("-"*80)
        self.logger.info('Starting TCP Traffic from %s:8000 to %s:9000, %s:9000 and %s:9000'%(self.vm1_fixture.vm_ip, self.vm2_fixture.vm_ip, dest_vm2.vm_ip, dest_vm3.vm_ip))
        self.logger.info("-"*80)

        stream_list= []
        profile= {}
        sender= {}
        receiver= {}

        tx_vm_node_ip= self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(self.vm1_fixture.vm_obj)]['host_ip']
        tx_local_host= Host(tx_vm_node_ip, self.inputs.username, self.inputs.password)
        send_host= Host(self.vm1_fixture.local_ip)

        stream1 = Stream(protocol="ip", proto="tcp", src=self.vm1_fixture.vm_ip,dst= self.vm2_fixture.vm_ip, sport= unicode(8000), dport=unicode(9000))
        stream2 = Stream(protocol="ip", proto="tcp", src=self.vm1_fixture.vm_ip,dst= dest_vm2.vm_ip, sport= unicode(8000), dport=unicode(9000))
        stream3 = Stream(protocol="ip", proto="tcp", src=self.vm1_fixture.vm_ip,dst= dest_vm3.vm_ip, sport= unicode(8000), dport=unicode(9000))

        stream_list= [stream1, stream2, stream3]
        
        rx_vm_node_ip= {}
        rx_local_host= {}
        recv_host= {}
        dst_vm_list= [self.vm2_fixture, dest_vm2, dest_vm3]
        
        for vm in dst_vm_list:
            rx_vm_node_ip[vm]= self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(vm.vm_obj)]['host_ip']
            rx_local_host[vm]= Host(rx_vm_node_ip[vm], self.inputs.username, self.inputs.password)
            recv_host[vm] =  Host(vm.local_ip)
        count= 0
        
        for i in range(len(stream_list)):
            profile[i]={}
            sender[i]= {}
            receiver[i] = {}
            count= count+1
            send_filename= 'sendtcp_%s'%count
            recv_filename= 'recvtcp_%s'%count
            profile[i] = ContinuousProfile(stream=stream_list[i], chksum= True)
            sender[i]= Sender(send_filename, profile[i], tx_local_host, send_host, self.inputs.logger)
            time.sleep(5)
            receiver[i]= Receiver(recv_filename, profile[i], rx_local_host[dst_vm_list[i]], recv_host[dst_vm_list[i]], self.inputs.logger)
            receiver[i].start()
            sender[i].start()
        self.logger.info('Sending traffic for 10 seconds')
        time.sleep(10)
        for i in range(len(stream_list)):
            sender[i].stop()
            time.sleep(5)
            receiver[i].stop()
            time.sleep(5)

        stream_sent_count = 0
        stream_recv_count = 0
        
        result= True
        
        for i in range(len(stream_list)):

            if sender[i].sent == None:
                sender[i].sent = 0
            self.logger.info('%s packets sent in Stream_%s'%(sender[i].sent, i))
            stream_sent_count= stream_sent_count + sender[i].sent

            if receiver[i].recv == None:
                receiver[i].recv = 0
            self.logger.info('%s packets received in Stream_%s'%(receiver[i].recv, i))
            stream_recv_count= stream_recv_count + receiver[i].recv

        self.logger.info('Total %s packets sent out.'%stream_sent_count)
        self.logger.info('Total %s packets received.'%stream_recv_count)
        if abs(stream_recv_count - stream_sent_count) < 5:
                self.logger.info('No Packet Loss Seen')
        else:
            self.logger.info('Packet Loss Seen')
        #Checking Flow Records

        vn1_vrf_id= self.vm1_fixture.get_vrf_id(self.vn1_fixture.vn_fq_name, self.vn1_fixture.vrf_name)
       
        inspect_h100= self.agent_inspect[self.vm1_fixture.vm_node_ip]
        
        flow_rec1= None
        flow_rec2= None
        flow_rec3= None

        dpi=unicode(9000)
        sport=unicode(8000)
        
        flow_rec1= inspect_h100.get_vna_fetchflowrecord(vrf=vn1_vrf_id,sip=self.vm1_fixture.vm_ip,dip=self.vm2_fixture.vm_ip,sport=sport,dport=dpi,protocol='6')
        flow_rec2= inspect_h100.get_vna_fetchflowrecord(vrf=vn1_vrf_id,sip=self.vm1_fixture.vm_ip,dip=dest_vm2.vm_ip,sport=sport,dport=dpi,protocol='6')
        flow_rec3= inspect_h100.get_vna_fetchflowrecord(vrf=vn1_vrf_id,sip=self.vm1_fixture.vm_ip,dip=dest_vm3.vm_ip,sport=sport,dport=dpi,protocol='6')

        rev_flow_rec1= inspect_h100.get_vna_fetchflowrecord(vrf=vn1_vrf_id,dip=self.vm1_fixture.vm_ip,sip=self.vm2_fixture.vm_ip,dport=sport,sport=dpi,protocol='6')
        rev_flow_rec2= inspect_h100.get_vna_fetchflowrecord(vrf=vn1_vrf_id,dip=self.vm1_fixture.vm_ip,sip=dest_vm2.vm_ip,dport=sport,sport=dpi,protocol='6')
        rev_flow_rec3= inspect_h100.get_vna_fetchflowrecord(vrf=vn1_vrf_id,dip=self.vm1_fixture.vm_ip,sip=dest_vm3.vm_ip,dport=sport,sport=dpi,protocol='6')

        flow_recs= []
        flow_recs= [flow_rec1, flow_rec2, flow_rec3]
        flow_result= True
        for flow_rec in flow_recs:
            if flow_rec is None:
                flow_result= False
        if flow_result is True:
            self.logger.info('Forward Flows exist on Agent %s'%self.vm1_fixture.vm_node_ip)
        else:
            assert flow_result,'No Forward Flows seen on Agent %s'%self.vm1_fixture.vm_node_ip

        rev_flow_recs= []
        rev_flow_recs= [rev_flow_rec1, rev_flow_rec2, rev_flow_rec3]
        rev_flow_result= False
        for rev_flow_rec in rev_flow_recs:
            if rev_flow_rec:
                rev_flow_result= rev_flow_result or True
        if rev_flow_result:
            self.logger.info('Reverse Flows exist on Agent %s'%self.vm1_fixture.vm_node_ip)
        else:
            assert rev_flow_result,'Reverse Flows not seen on Agent %s'%self.vm1_fixture.vm_node_ip

        return True
    #end test_ecmp_svc_in_network_with_3_instance_incr_dip

    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_add_del_SI(self):
        """Validate ECMP with service chaining in-network mode datapath having 
        multiple service chain. Add and delete SIs and check for ECMP behaviour."""
        self.verify_svc_in_network_datapath(si_count=3, svc_scaling= True, max_inst= 3)
        svm_ids= self.si_fixtures[1].svm_ids
        self.get_rt_info_tap_intf_list(self.vn1_fixture, self.vm1_fixture, svm_ids)
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        policy_id= self.policy_fixture.policy_obj['policy']['id']
        action_list= []
        for fix in self.si_fixtures:
            self.logger.info("."*40)
            self.logger.info('Updating the policy %s and then deleting SI %s'%(self.policy_fixture.policy_name, fix.si_name))
            self.logger.info("."*40)
            old_policy_entries= self.policy_fixture.policy_obj['policy']['entries']
            action_list= self.policy_fixture.policy_obj['policy']['entries']['policy_rule'][0]['action_list']['apply_service']
            self.logger.info('Old list is %s'% action_list)
            svc= ':'.join(fix.si_fq_name)
            action_list.remove(svc)
            self.logger.info('New list is %s'%action_list)
            for i, j in old_policy_entries.items():
                 for x,y in j[0].items():
                     if x == 'action_list':
                          y['apply_service']= action_list
            self.logger.info('Updating the policy with entries')
            new_policy_entries= old_policy_entries
            data= {'policy': {'entries': new_policy_entries}}
            self.policy_fixture.update_policy(policy_id, data)
            fix.cleanUp()
            self.remove_from_cleanups(fix)
            time.sleep(10)
            if len(action_list) != 0:
                self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        self.logger.info("."*40)
        self.logger.info('Deleting the ST %s'%self.st_fixture.st_name)
        self.logger.info("."*40)
        self.st_fixture.cleanUp()
        self.remove_from_cleanups(self.st_fixture)
        self.logger.info("-"*40)
        self.logger.info('Deleting the policy %s'%self.policy_fixture.policy_name)
        self.logger.info("-"*40)
        self.detach_policy(self.vn1_policy_fix)
        self.detach_policy(self.vn2_policy_fix)
        self.unconfig_policy(self.policy_fixture)
        self.logger.info("."*40)
        self.logger.info('Reconfiguring the ST and SIs')
        self.logger.info("."*40)
        self.verify_svc_in_network_datapath(si_count=3, svc_scaling= True, max_inst= 3)
        svm_ids= self.si_fixtures[1].svm_ids
        self.get_rt_info_tap_intf_list(self.vn1_fixture, self.vm1_fixture, svm_ids)
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        return True
    #end test_ecmp_svc_in_network_with_add_del_SI

    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_multi_path_diff_route(self):
        """Validate ECMP with service chaining in-network mode datapath having 
        multiple paths for different routes"""
        self.logger.info('We will create 11 different networks. VN1 talks to 10 other VNs via specific Service Chains')
        vn_obj_list= []
        vm_list= []
        for i in range(1,12):
            vn_name='vn_%s'%i
            vm_name='vm_%s'%i
            subnets='10.%s.1.0/24'%i
            vn_obj=self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,vn_name=vn_name, inputs= self.inputs, subnets=[subnets] ))
            vn_obj_list.append(vn_obj)
            assert vn_obj.verify_on_setup()
            assert vn_obj
            vm_fix= self.useFixture(VMFixture(connections= self.connections,vn_obj=vn_obj.obj, vm_name= vm_name, project_name= self.inputs.project_name, ram= 4096, image_name='ubuntu-traffic'))
            assert vm_fix.verify_on_setup()
            self.nova_fixture.wait_till_vm_is_up(vm_fix.vm_obj)
            vm_list.append(vm_fix)
            
        action_list = []
        if_list = [['management', False], ['left', True], ['right', True]]
        si_count= 1
        svc_scaling= True
        max_inst= 2
        svc_mode= 'in-network'
        for vn_obj in vn_obj_list:
            if vn_obj!= vn_obj_list[0]:
                self.logger.info('Adding a service chain between %s and %s'%(vn_obj_list[0].vn_name, vn_obj.vn_name))
                st_name = '%s_ST_%s'%(vn_obj_list[0].vn_name, vn_obj.vn_name)
                si_name = '%s_SI_%s'%(vn_obj_list[0].vn_name, vn_obj.vn_name)
                policy_name = '%s_policy_%s'%(vn_obj_list[0].vn_name, vn_obj.vn_name)
                
                st_fixture, self.si_fixtures = self.config_st_si(st_name, si_name, si_count, svc_scaling, max_inst, left_vn= vn_obj_list[0].vn_fq_name, right_vn=vn_obj.vn_fq_name, svc_mode= svc_mode)
                action_list = self.chain_si(si_count, si_name)
                rules = [
                            {
                             'direction'     : '<>',
                             'protocol'      : 'any',
                             'source_network': vn_obj_list[0].vn_name,
                             'src_ports'     : [0, -1],
                             'dest_network'  : vn_obj.vn_name,
                             'dst_ports'     : [0, -1],
                             'simple_action' : None,
                             'action_list'   : {'apply_service': action_list}
                            },
                        ]
                policy_fixture = self.config_policy(policy_name, rules)
                vn1_policy_fix = self.attach_policy_to_vn(policy_fixture, vn_obj_list[0])
                vn2_policy_fix = self.attach_policy_to_vn(policy_fixture, vn_obj)
                time.sleep(10)
                self.validate_vn(vn_obj.vn_name)
                for si_fix in self.si_fixtures:
                    si_fix.verify_on_setup()

        #Ping from left VM to all the right VMs
        for vm in vm_list:
            if vm!= vm_list[0]:
                errmsg = "Ping to right VM ip %s from left VM failed" % vm.vm_ip
                assert vm_list[0].ping_with_certainty(vm.vm_ip), errmsg
                svm_ids= self.si_fixtures[0].svm_ids
                self.get_rt_info_tap_intf_list(vn_obj_list[0], vm_list[0], svm_ids)
                self.verify_traffic_flow(vm_list[0], vm)
        return True
    #end test_ecmp_svc_in_network_with_multi_path_diff_route

    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_multi_SC_multi_SI(self):
        """Validate ECMP with service chaining in-network mode datapath having 
        multiple service chain with a multiple service instances in each"""
        self.verify_svc_in_network_datapath(si_count=3, svc_scaling= True, max_inst= 3)
        svm_ids= self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(self.vn1_fixture, self.vm1_fixture, svm_ids)
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        return True
    #end test_ecmp_svc_in_network_with_multi_SC_multi_SI

    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_multi_SC_single_SI(self):
        """Validate ECMP with service chaining in-network mode datapath having 
        multiple service chain with a single service instance in each"""
        self.verify_svc_in_network_datapath(si_count=3, svc_scaling= True, max_inst= 1)
        svm_ids= self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(self.vn1_fixture, self.vm1_fixture, svm_ids)
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        return True
    #end test_ecmp_svc_in_network_with_multi_SC_single_SI
    
    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_3_instance_add_flows(self):
        """Validate ECMP with service chaining in-network mode datapath having 
        service instance. Add flows on top and verify that the current flows are unaffected"""
        self.verify_svc_in_network_datapath(si_count=1, svc_scaling= True, max_inst= 3)
        svm_ids= self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(self.vn1_fixture, self.vm1_fixture, svm_ids)
        vm_list= [self.vm1_fixture, self.vm2_fixture]
        for vm in vm_list:
            self.logger.info('Getting the local_ip of the VM')
            vm.verify_vm_in_agent()
            out= self.nova_fixture.wait_till_vm_is_up( vm.vm_obj)
            if out == False: return {'result':out, 'msg':"%s failed to come up"%vm.vm_name}
            else: time.sleep(5); self.logger.info('Installing Traffic package on %s ...'%vm.vm_name); vm.install_pkg("Traffic")
        self.logger.info("-"*80)
        self.logger.info('Starting a stream each of ICMP, UDP and TCP Traffic on different ports')
        self.logger.info("-"*80)
        old_stream_list= []
        old_profile= {}
        old_sender= {}
        old_receiver= {}
        old_stream1 = Stream(protocol="ip", proto="icmp", src=self.vm1_fixture.vm_ip,dst= self.vm2_fixture.vm_ip, sport= unicode(10000), dport=unicode(11000))
        old_stream2 = Stream(protocol="ip", proto="udp", src=self.vm1_fixture.vm_ip,dst= self.vm2_fixture.vm_ip, sport= unicode(10000), dport=unicode(11000))
        old_stream3 = Stream(protocol="ip", proto="tcp", src=self.vm1_fixture.vm_ip,dst= self.vm2_fixture.vm_ip, sport= unicode(10000), dport=unicode(11000))
        old_stream_list= [old_stream1, old_stream2, old_stream3]

        tx_vm_node_ip= self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(self.vm1_fixture.vm_obj)]['host_ip']
        tx_local_host= Host(tx_vm_node_ip, self.inputs.username, self.inputs.password)
        old_send_host= Host(self.vm1_fixture.local_ip)

        rx_vm_node_ip= self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(self.vm2_fixture.vm_obj)]['host_ip']
        rx_local_host= Host(rx_vm_node_ip, self.inputs.username, self.inputs.password)
        old_recv_host=  Host(self.vm2_fixture.local_ip)
        count= 0

        for i in range(len(old_stream_list)):
            old_profile[i]={}
            old_sender[i]= {}
            old_receiver[i] = {}
            count= count+1
            send_filename= 'sendtraffic_%s'%count
            recv_filename= 'recvtraffic_%s'%count
            old_profile[i] = ContinuousProfile(stream=old_stream_list[i], chksum= True)
            old_sender[i]= Sender(send_filename, old_profile[i], tx_local_host, old_send_host, self.inputs.logger)
            time.sleep(5)
            old_receiver[i]= Receiver(recv_filename, old_profile[i], rx_local_host, old_recv_host, self.inputs.logger)
            old_receiver[i].start()
            old_sender[i].start()
        self.logger.info('Sending traffic for 10 seconds and will start more flows')
        time.sleep(10)

        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)

        for i in range(len(old_stream_list)):
            old_sender[i].stop()
            time.sleep(5)
            old_receiver[i].stop()
            time.sleep(5)

        old_stream_sent_count = 0
        old_stream_recv_count = 0

        for i in range(len(old_stream_list)):
            if old_sender[i].sent == None:
                old_sender[i].sent = 0
            self.logger.info('%s packets sent in Stream_%s'%(old_sender[i].sent, i))
            old_stream_sent_count= old_stream_sent_count + old_sender[i].sent

            if old_receiver[i].recv == None:
                old_receiver[i].recv = 0
            self.logger.info('%s packets received in Stream_%s'%(old_receiver[i].recv, i))
            old_stream_recv_count= old_stream_recv_count + old_receiver[i].recv
                                            
        self.logger.info('Total %s packets sent out.'%old_stream_sent_count)
        self.logger.info('Total %s packets received.'%old_stream_recv_count)
        if abs(old_stream_recv_count - old_stream_sent_count) < 5:
            self.logger.info('No Packet Loss Seen. Flows unaffected')
        else:
            self.logger.info('Packet Loss Seen')

        return True
    #end test_ecmp_svc_in_network_with_3_instance_add_flows
    
    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_3_instance_del_add_agent(self):
        """Validate ECMP with service chaining in-network mode datapath having 
        service instance, by removing one of the agents and adding it back"""
        self.verify_svc_in_network_datapath(si_count=1, svc_scaling= True, max_inst= 3)
        svm_ids= self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(self.vn1_fixture, self.vm1_fixture, svm_ids)
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        self.logger.info("-"*80)
        self.logger.info('Starting a stream each of ICMP, UDP and TCP Traffic on different ports')
        self.logger.info("-"*80)
        
        new_stream_list= []
        new_profile= {}
        new_sender= {}
        new_receiver= {}

        new_stream1 = Stream(protocol="ip", proto="tcp", src=self.vm1_fixture.vm_ip,dst= self.vm2_fixture.vm_ip, sport= unicode(10000), dport=unicode(11000))
        new_stream2 = Stream(protocol="ip", proto="tcp", src=self.vm1_fixture.vm_ip,dst= self.vm2_fixture.vm_ip, sport= unicode(10000), dport=unicode(12000))
        new_stream3 = Stream(protocol="ip", proto="tcp", src=self.vm1_fixture.vm_ip,dst= self.vm2_fixture.vm_ip, sport= unicode(10000), dport=unicode(13000))
        new_stream_list= [new_stream1, new_stream2, new_stream3]

        tx_vm_node_ip= self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(self.vm1_fixture.vm_obj)]['host_ip']
        tx_local_host= Host(tx_vm_node_ip, self.inputs.username, self.inputs.password)
        new_send_host= Host(self.vm1_fixture.local_ip)

        rx_vm_node_ip= self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(self.vm2_fixture.vm_obj)]['host_ip']
        rx_local_host= Host(rx_vm_node_ip, self.inputs.username, self.inputs.password)
        new_recv_host=  Host(self.vm2_fixture.local_ip)
        count= 0

        for i in range(len(new_stream_list)):
            new_profile[i]={}
            new_sender[i]= {}
            new_receiver[i] = {}
            count= count+1
            send_filename= 'sendtraffic_%s'%count
            recv_filename= 'recvtraffic_%s'%count
            new_profile[i] = ContinuousProfile(stream=new_stream_list[i], chksum= True)
            new_sender[i]= Sender(send_filename, new_profile[i], tx_local_host, new_send_host, self.inputs.logger)
            time.sleep(5)
            new_receiver[i]= Receiver(recv_filename, new_profile[i], rx_local_host, new_recv_host, self.inputs.logger)
            new_receiver[i].start()
            new_sender[i].start()
            sleep(10)
            
        for addr in self.inputs.compute_ips:
            if ((addr != self.vm1_fixture.vm_node_ip) and (addr != self.vm2_fixture.vm_node_ip)):
                cmd= 'reboot'
                self.logger.info('Will reboot the node %s'%socket.gethostbyaddr(addr)[0])
                self.inputs.run_cmd_on_server(addr,cmd,username='root',password='c0ntrail123')
                sleep(120)
        self.logger.info('We will now check that the route entries are updated by BGP and that there is no traffic loss')
        self.get_rt_info_tap_intf_list(self.vn1_fixture, self.vm1_fixture, svm_ids)
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        self.logger.info('Will check the state of the SIs and power it ON, if it is in SHUTOFF state')
        for si in self.si_fixtures[0].nova_fixture.get_vm_list():
            if si.status != 'ACTIVE':
                self.logger.info('Will Power On %s'%si.name)
                si.start()
                sleep(120)
        self.logger.info('We will now check that the route entries are updated by BGP and that there is no traffic loss')
        self.get_rt_info_tap_intf_list(self.vn1_fixture, self.vm1_fixture, svm_ids)
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        for i in range(len(new_stream_list)):
            new_sender[i].stop()
            time.sleep(5)
            new_receiver[i].stop()
            time.sleep(5)

        new_stream_sent_count = 0
        new_stream_recv_count = 0

        for i in range(len(new_stream_list)):
            if new_sender[i].sent == None:
                new_sender[i].sent = 0
            self.logger.info('%s packets sent in Stream_%s'%(new_sender[i].sent, i))
            new_stream_sent_count= new_stream_sent_count + new_sender[i].sent

            if new_receiver[i].recv == None:
                new_receiver[i].recv = 0
            self.logger.info('%s packets received in Stream_%s'%(new_receiver[i].recv, i))
            new_stream_recv_count= new_stream_recv_count + new_receiver[i].recv

        self.logger.info('Total %s packets sent out.'%new_stream_sent_count)
        self.logger.info('Total %s packets received.'%new_stream_recv_count)
        if abs(new_stream_recv_count - new_stream_sent_count) < 5:
            self.logger.info('No Packet Loss Seen. Flows unaffected')
        else:
            self.logger.info('Packet Loss Seen. Bug 2072.')

        return True
    #end test_ecmp_svc_in_network_with_3_instance_del_add_agent

    @preposttest_wrapper
    def test_ecmp_svc_in_network_with_3_instance(self):
        """Validate ECMP with service chaining in-network mode datapath having 
        service instance"""
        self.verify_svc_in_network_datapath(si_count=1, svc_scaling= True, max_inst= 3)
        svm_ids= self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(self.vn1_fixture, self.vm1_fixture, svm_ids)
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        return True
    #end test_ecmp_svc_in_network_with_3_instance
    
    @preposttest_wrapper
    def test_ecmp_svc_in_network_nat_with_3_instance(self):
        """Validate ECMP with service chaining in-network-nat mode datapath having 
        service instance"""
        self.verify_svc_in_network_datapath(si_count=1, svc_scaling= True, max_inst= 3, svc_mode= 'in-network-nat')
        svm_ids= self.si_fixtures[0].svm_ids
        self.get_rt_info_tap_intf_list(self.vn1_fixture, self.vm1_fixture, svm_ids)
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        return True
    #end test_ecmp_svc_in_network_nat_with_3_instance
  
    @preposttest_wrapper
    def test_ecmp_svc_transparent_with_3_instance(self):
        """Validate ECMP with service chaining transparent mode datapath having 
        service instance"""
        self.verify_svc_transparent_datapath(si_count=1, svc_scaling= True, max_inst= 3)
        self.logger.info('Verify Traffic Flow in both the directions')
        self.verify_traffic_flow(self.vm1_fixture, self.vm2_fixture)
        self.verify_traffic_flow(self.vm2_fixture, self.vm1_fixture)
        return True
    #end test_ecmp_svc_transparent_with_3_instance

#    @preposttest_wrapper
#    def test_ecmp_svc_in_network_right_shared_ip(self):
#        """Validate ECMP with service chaining in network mode with the right side sharing IP"""
#        self.verify_svc_in_network_datapath(si_count=1, svc_scaling= True, max_inst= 3, rtol= True)
#        import pdb;pdb.set_trace()
#        svm_ids= self.si_fixtures[0].svm_ids
#        self.get_rt_info_tap_intf_list(self.vn2_fixture, self.vm2_fixture, svm_ids)
#        self.verify_traffic_flow(self.vm2_fixture, self.vm1_fixture)
#        return True
#    #end test_ecmp_svc_transparent_with_3_instance

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            if fix.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break

