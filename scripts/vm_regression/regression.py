import traffic_tests
from vn_test import *
from vm_test import *
from floating_ip import *
from policy_test import *
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from base import BaseVnVmTest
from common import isolated_creds
import inspect


class TestBasicVMVN(BaseVnVmTest):
    _interface = 'json'

    @classmethod
    def setUpClass(cls):
        super(TestBasicVMVN, cls).setUpClass()

    def runTest(self):
        pass
    #end runTes

    @preposttest_wrapper
    def test_bring_up_vm_with_control_node_down(self):
        ''' Create VM when there is not active control node. Verify VM comes up fine when all control nodes are back
        
        '''
        if len(set(self.inputs.bgp_ips)) < 2 :
            raise self.skipTest("Skiping Test. At least 2 control node required to run the test")
        result = True
        vn1_name='vn30'
        vn1_subnets=['30.1.1.0/24']

        # Collecting all the control node details
        controller_list= []
        for entry in self.inputs.compute_ips:
            inspect_h= self.agent_inspect[entry]
            agent_xmpp_status= inspect_h.get_vna_xmpp_connection_status()
            for entry in agent_xmpp_status:
                controller_list.append(entry['controller_ip'])
        controller_list = set(controller_list)

        # Stop all the control node
        for entry in controller_list:
            self.logger.info('Stoping the Control service in  %s' %(entry))
#            self.inputs.stop_service('contrail-control',[entry])
            self.addCleanup( self.inputs.start_service, 'contrail-control', [entry] )
        sleep(30)

        vn1_vm1_name= 'vm1'
        vn1_vm2_name= 'vm2'
        vn1_fixture= self.useFixture(VNFixture(project_name= self.project.project_name, connections= self.connections,
                     vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        vm1_fixture= self.useFixture(VMFixture(project_name= self.project.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm1_name))

        vm2_fixture= self.useFixture(VMFixture(project_name= self.project.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, vm_name= vn1_vm2_name))

        vm1_fixture.verify_vm_launched()
        vm2_fixture.verify_vm_launched()
        vm1_node_ip=self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(vm1_fixture.vm_obj)]['host_ip']
        vm2_node_ip=self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(vm2_fixture.vm_obj)]['host_ip']
        inspect_h1= self.agent_inspect[vm1_node_ip]
        inspect_h2= self.agent_inspect[vm2_node_ip]
        self.logger.info('Checking TAP interface is created for all VM and  should be in Error state')
        vm1_tap_intf = None
        vm2_tap_intf = None
        vm1_tap_intf=inspect_h1.get_vna_tap_interface_by_ip(vm1_fixture.vm_ip)
        if vm1_tap_intf is []:
            self.logger.error('TAP interface is not created for VM %s' %(vn1_vm1_name))
            result= result and False
        else:
            if vm1_tap_intf[0]['vrf_name'] != '--ERROR--':
                self.logger.error('TAP interface VRF info should be Error . But currently in %s' %(vm1_tap_intf[0]['vrf_name']))
                result= result and False

        vm2_tap_intf=inspect_h2.get_vna_tap_interface_by_ip(vm2_fixture.vm_ip)
        if vm2_tap_intf is []:
                self.logger.error('TAP interface is not created for VM %s' %(vn1_vm2_name))
                result= result and False
        else:
            if vm2_tap_intf[0]['vrf_name'] != '--ERROR--':
                self.logger.error('TAP interface VRF info should be Error . But currently in %s' %(vm2_tap_intf[0]['vrf_name']))
                result= result and False

        self.logger.info('Waiting for 120 sec for cleanup to begin')
        sleep (120)
        # Check agent should not have any VN info
        for entry in self.inputs.compute_ips:
            inspect_h= self.agent_inspect[entry]
            self.logger.info('Checking VN info in agent %s.' %(entry))
            if inspect_h.get_vna_vn_list()['VNs'] != []:
                self.logger.error('Agent should not have any VN info present when control node is down')
                result= result and False
        # Start all the control nodea
        for entry in controller_list:
            self.logger.info('Starting the Control service in  %s' %(entry))
            self.inputs.start_service('contrail-control',[entry])
        sleep(10)

        self.logger.info('Checking the VM came up properly or not')
        assert vn1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm1_fixture.verify_on_setup()

        # Check ping between VM
        assert vm2_fixture.ping_to_ip( vm1_fixture.vm_ip )
        if not result :
            self.logger.error('Test to verify cleanup of agent after control nodes stop Failed')
            assert result
        return True

    @preposttest_wrapper
    def test_broadcast_udp_w_chksum(self):
        ''' Validate Broadcast UDP stream with checksum check enabled .
        
        '''
        vn1_name='vn30'
        vn1_subnets=['30.1.1.0/24']
        ts = time.time()
        vn1_name = '%s_%s'%(inspect.stack()[0][3],str(ts))
        vn1_vm1_name= 'vm1'
        vn1_vm2_name= 'vm2'
        vn1_vm3_name= 'vm3'
        vn1_vm4_name= 'vm4'
        result= True
        list_of_ips=['30.1.1.255','224.0.0.1','255.255.255.255']
        vn1_fixture= self.useFixture(VNFixture(project_name= self.project.project_name, connections= self.connections,
                     vn_name=vn1_name, inputs= self.inputs, subnets= vn1_subnets))
        assert vn1_fixture.verify_on_setup()

        vm1_fixture= self.useFixture(VMFixture(project_name= self.project.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, ram= 4096, image_name= 'ubuntu-traffic', vm_name= vn1_vm1_name))
        vm2_fixture= self.useFixture(VMFixture(project_name= self.project.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, ram= 4096, image_name= 'ubuntu-traffic', vm_name= vn1_vm2_name))
        vm3_fixture= self.useFixture(VMFixture(project_name= self.project.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, ram= 4096, image_name= 'ubuntu-traffic', vm_name= vn1_vm3_name))
        vm4_fixture= self.useFixture(VMFixture(project_name= self.project.project_name, connections= self.connections,
                vn_obj= vn1_fixture.obj, ram= 4096, image_name= 'ubuntu-traffic', vm_name= vn1_vm4_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()
        #self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj )
        #self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj )
        #self.nova_fixture.wait_till_vm_is_up( vm3_fixture.vm_obj )
        #self.nova_fixture.wait_till_vm_is_up( vm4_fixture.vm_obj )

        out1= self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj)
        if out1 == False: return {'result':out1, 'msg':"%s failed to come up"%vm1_fixture.vm_name}
        else: sleep (10); self.logger.info('Installing Traffic package on %s ...'%vm1_fixture.vm_name); vm1_fixture.install_pkg("Traffic")

        out2= self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj)
        if out2 == False: return {'result':out2, 'msg':"%s failed to come up"%vm2_fixture.vm_name}
        else: sleep (10); self.logger.info('Installing Traffic package on %s ...'%vm2_fixture.vm_name); vm2_fixture.install_pkg("Traffic")

        out3= self.nova_fixture.wait_till_vm_is_up( vm3_fixture.vm_obj)
        if out3 == False: return {'result':out3, 'msg':"%s failed to come up"%vm3_fixture.vm_name}
        else: sleep (10); self.logger.info('Installing Traffic package on %s ...'%vm3_fixture.vm_name); vm3_fixture.install_pkg("Traffic")

        out4= self.nova_fixture.wait_till_vm_is_up( vm4_fixture.vm_obj)
        if out4 == False: return {'result':out4, 'msg':"%s failed to come up"%vm4_fixture.vm_name}
        else: sleep (10); self.logger.info('Installing Traffic package on %s ...'%vm4_fixture.vm_name); vm4_fixture.install_pkg("Traffic")

        # Starting Multicast_UDP
        for ips in list_of_ips:
            self.logger.info("-"*80)
            self.logger.info('Sending UDP packets to %s'%ips)
            self.logger.info("-"*80)
            stream = Stream(protocol="ip", proto="udp", src=vm1_fixture.vm_ip,dst= ips, dport=9000)
            profile = ContinuousProfile(stream=stream, listener= ips, capfilter="udp port 8000", chksum= True)

            tx_vm_node_ip=  self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(vm1_fixture.vm_obj)]['host_ip']
            rx1_vm_node_ip= self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(vm2_fixture.vm_obj)]['host_ip']
            rx2_vm_node_ip= self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(vm3_fixture.vm_obj)]['host_ip']
            rx3_vm_node_ip= self.inputs.host_data[self.nova_fixture.get_nova_host_of_vm(vm4_fixture.vm_obj)]['host_ip']

            tx_local_host = Host(tx_vm_node_ip, self.inputs.username, self.inputs.password)
            rx1_local_host = Host(rx1_vm_node_ip, self.inputs.username, self.inputs.password)
            rx2_local_host = Host(rx2_vm_node_ip, self.inputs.username, self.inputs.password)
            rx3_local_host = Host(rx3_vm_node_ip, self.inputs.username, self.inputs.password)

            send_host = Host(vm1_fixture.local_ip, vm1_fixture.vm_username, vm1_fixture.vm_password)
            recv_host1 = Host(vm2_fixture.local_ip, vm2_fixture.vm_username, vm2_fixture.vm_password)
            recv_host2 = Host(vm3_fixture.local_ip, vm3_fixture.vm_username, vm3_fixture.vm_password)
            recv_host3 = Host(vm4_fixture.local_ip, vm4_fixture.vm_username, vm4_fixture.vm_password)

