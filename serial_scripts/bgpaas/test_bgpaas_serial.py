from tcutils.wrappers import preposttest_wrapper
from common.bgpaas.base import BaseBGPaaS
from common.neutron.base import BaseNeutronTest
import test
import time
from tcutils.util import *
from tcutils.tcpdump_utils import *
from common import isolated_creds


class TestBGPaaS(BaseBGPaaS):

    @preposttest_wrapper
    def test_bgpaas_service_port_update(self):
        '''
        Description: Test the global BGPaaS service port-range changes
        Test Steps:
             1. Create bgpaas service and verify BGP session is established with controller.
             2. Modify end port so that port-range is shrunk.Verify its not allowed
             3. Modify start port so that port-range is shrunk.Verify its not allowed.
             4. Modify start port,end port so that port-range is shrunk.Verify its not allowed.
             5. Modify start port,end port so that port-range is expanded.Verify its allowed
                Verify existing BGPaaS Session is UP.
             6. Create new bgpaas service and verify BGPaaS session is UP.
        Maintainer: vageesant@juniper.net
        '''
 
        bgpaas_fixture,bgpaas_vm1 = self.create_bird_bgpaas()

        port_start,port_end = self.get_global_service_port_range()
        new_port_end = port_end - 100
        ret = self.set_global_service_port_range(port_start=port_start,port_end=new_port_end)

        if ret:
           assert False,"BGP End Port range shrunk is allowed"  
        else:
           self.logger.info("BGP End Port range shrunk is not allowed")
        assert bgpaas_fixture.verify_in_control_node(bgpaas_vm1),"BGP session with Controller is not seen"
        self.logger.info("BGP session with Controller is seen")

        new_port_start = port_start + 100
        ret = self.set_global_service_port_range(port_start=port_start,port_end=new_port_end)

        if ret:
           assert False,"BGP Start Port range shrunk is allowed"  
        else:
           self.logger.info("BGP Start Port range shrunk is not allowed")
        assert bgpaas_fixture.verify_in_control_node(bgpaas_vm1),"BGP session with Controller is not seen"
        self.logger.info("BGP session with Controller is seen")
     
        ret = self.set_global_service_port_range(port_start=new_port_start,port_end=new_port_end)

        if ret:
           assert False,"BGP Start,End Port range shrunk is allowed"  
        else:
           self.logger.info("BGP Start,End Port range shrunk is not allowed")
        assert bgpaas_fixture.verify_in_control_node(bgpaas_vm1),"BGP session with Controller is not seen"
        self.logger.info("BGP session with Controller is seen")

        new_port_start = port_start + 100
        new_port_end = port_end + 100

        ret = self.set_global_service_port_range(port_start=new_port_start,port_end=new_port_end)

        if ret:
           assert False,"BGP Start Port range shrunk is allowed"  
        else:
           self.logger.info("BGP Start,End Port range shrunk is not allowed")
        assert bgpaas_fixture.verify_in_control_node(bgpaas_vm1),"BGP session with Controller is not seen"
        self.logger.info("BGP session with Controller is seen")

        new_port_start = port_start - 1000
        new_port_end = port_end + 1000

        ret = self.set_global_service_port_range(port_start=new_port_start,port_end=new_port_end)

        if not ret:
           assert False,"BGP Start,End Port range expand is NOT allowed"  
        else:
           self.logger.info("BGP Start,End Port range expand is allowed")

        time.sleep(60)

        assert bgpaas_fixture.verify_in_control_node(bgpaas_vm1),"BGP session with Controller is not seen"
        self.logger.info("BGP session with Controller is seen")

        bgpaas_fixture2,bgpaas_vm2 = self.create_bird_bgpaas()

        assert bgpaas_fixture2.verify_in_control_node(bgpaas_vm2),"BGP session with Controller is not seen"
        self.logger.info("BGP session with Controller is seen")

    @preposttest_wrapper
    def test_bgpaas_stop_start_controllers(self):
        """
        Description: stop active-vrouter controller,backup-vrouter controller,restart non-vrouter controller.
        Test Steps:
           1. create bgpaas service,vsrx vm and establish bgp session with .1 and .2 and advertise route 9.9.9.9/32
           2. verify 9.9.9.9/32 is seen in VRF
           3. start ping to 9.9.9.9 from test vm
           4. stop the active-vrouter controller and verify there is no traffic loss to 9.9.9.9
           5. start the active-vrouter controller and stopped the backup-vrouter controller , which will be active-controller now
              verify there is no traffic loss
           6. non-vrouter controller:
              ensure both the active-vrouter and backup-vrouter controller are up
              restart the non-vrouter controller and verify is there is no BGP session flap and no traffic loss.
        Maintainer: vageesant@juniper.net
        1. restart active controller,backup controller
        2. restart non-vrouter controller
        """

        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='ubuntu-traffic')
        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',image_name='vsrx')
        assert test_vm.wait_till_vm_is_up(),"Failed to bringup testvm"
        bgpaas_vm1_state = False
        for i in range(5):
            bgpaas_vm1_state = bgpaas_vm1.wait_till_vm_is_up()
            if bgpaas_vm1_state:
               break
        assert bgpaas_vm1_state,"bgpaas_vm1 failed to come up"

        cluster_local_autonomous_system = random.randint(200, 800)
        bgpaas_as = random.randint(45000,45100)
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=True, autonomous_system=bgpaas_as, bgpaas_ip_address=bgpaas_vm1.vm_ip,local_autonomous_system=cluster_local_autonomous_system)

        port1 = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        self.attach_vmi_to_bgpaas(port1, bgpaas_fixture)

        address_families = ['inet', 'inet6']
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        neighbors = [gw_ip, dns_ip]
        self.logger.info('Configuring BGP on the vsrx vm')

        cn_inspect_handle = {}
        for cn in self.inputs.bgp_control_ips:
           cn_inspect_handle[cn] = self.connections.get_control_node_inspect_handle(cn)

        self.config_bgp_on_vsrx(src_vm=test_vm, dst_vm=bgpaas_vm1, bgp_ip=bgpaas_vm1.vm_ip, lo_ip=bgpaas_vm1.vm_ip,
                                address_families=address_families, autonomous_system=bgpaas_as, neighbors=neighbors,
                                 bfd_enabled=True,local_autonomous_system=cluster_local_autonomous_system)
        cmds = []
        cmds.append("set interfaces lo0 unit 0 family inet address 9.9.9.9/32")
        cmds.append("set security zones security-zone trust interfaces lo0 host-inbound-traffic system-services all")
        cmds.append("activate security policies")
        self.configure_vsrx(srv_vm=test_vm,dst_vm=bgpaas_vm1,cmds=cmds)

        ret = bgpaas_fixture.verify_in_control_node(bgpaas_vm1)
        if ret:
           self.logger.info("BGP session with Controller is seen")
        else:
           assert False,"BGP session with Controller is NOT seen"

        route_seen = False
        for cn in self.inputs.bgp_control_ips:
            rt_entries = cn_inspect_handle[cn].get_cn_route_table_entry(prefix="9.9.9.9/32",table="inet.0",ri_name=vn_fixture.ri_name) or []
            for rt_entry in rt_entries:
               if rt_entry['protocol'] == "BGP (bgpaas)":
                  route_seen = True
         
        if route_seen:
           self.logger.info("route 9.9.9.9/32 is seen in controller")
        else:
           assert False,"route 9.9.9.9/32 is seen NOT in Controller" 

        ping_h = self.start_ping(test_vm, dst_ip="9.9.9.9")

        self.logger.info("stopping the active controller")

        control_nodes1 = bgpaas_vm1.get_control_nodes()
        active_controller1 = bgpaas_vm1.get_active_controller()
        self.inputs.stop_service('contrail-control',
            [active_controller1], container='control')
        self.addCleanup(self.inputs.start_service,'contrail-control',
            [active_controller1], container='control')

        time.sleep(30)

        ping_stats = ping_h.get_stats()
        if int(ping_stats["loss"]) == 0:
           self.logger.info("there is no traffic loss when first active controller is stopped")
        else:
            assert False , "There is traffic loss when first active controller is stopped"

        ret = bgpaas_fixture.verify_in_control_node(bgpaas_vm1)
        if ret:
           self.logger.info("BGP session with Controller is seen after stopping active controller")
        else:
           assert False,"BGP session with Controller is not seen after stopping active controller"

        route_seen = False
        for cn in self.inputs.bgp_control_ips:
            try:
               rt_entries = cn_inspect_handle[cn].get_cn_route_table_entry(prefix="9.9.9.9/32",table="inet.0",ri_name=vn_fixture.ri_name) or []
            except:
               continue
            for rt_entry in rt_entries:
               if rt_entry['protocol'] == "BGP (bgpaas)":
                  route_seen = True

        if route_seen:
           self.logger.info("route 9.9.9.9/32 is seen in Controller after active controller is stopped")
        else:
           assert False,"route 9.9.9.9/32 is NOT seen in Controller after active controller is stopped" 

        time.sleep(30)


        active_controller2 = bgpaas_vm1.get_active_controller()
        control_nodes2 = bgpaas_vm1.get_control_nodes()

        self.logger.info("start the previously stopped active controller and stop the backup controller , which will be active controller now")

        self.inputs.start_service('contrail-control',
            [active_controller2], container='control')
        time.sleep(30)

        self.inputs.stop_service('contrail-control',
            [active_controller2], container='control')
        self.addCleanup(self.inputs.start_service,'contrail-control',
            [active_controller2], container='control')

        time.sleep(30)

        ping_stats = ping_h.get_stats()

        if int(ping_stats["loss"]) == 0 :
           self.logger.info("there is no traffic loss when second controller is stopped")
        else:
           assert False, "There is traffic loss when second active controller is stopped"

        route_seen = False
        for cn in self.inputs.bgp_control_ips:
            try:
              rt_entries = cn_inspect_handle[cn].get_cn_route_table_entry(prefix="9.9.9.9/32",table="inet.0",ri_name=vn_fixture.ri_name) or []
            except:
              continue
            for rt_entry in rt_entries:
               if rt_entry['protocol'] == "BGP (bgpaas)":
                  route_seen = True
        if route_seen:
           self.logger.info("route 9.9.9.9/32 is seen in Controller after stopping second active controller")
        else:
           assert False,"route 9.9.9.9/32 is NOT seen in Controller after stopping second active controller"

        ping_stats = ping_h.get_stats()
        assert int(ping_stats["loss"]) == 0 , "There is traffic loss when second active controller is stopped"

        self.logger.info("start the second active controller")
        self.inputs.start_service('contrail-control',
            self.inputs.bgp_control_ips, container='control')

        time.sleep(30)

        init_flap_count = self.get_bgp_router_flap_count(bgpaas_fixture)

        non_vrouter_controller =  list(set(self.inputs.bgp_control_ips) - set(bgpaas_vm1.get_control_nodes()))[0]
        self.logger.info("restarting non-vrouter controller and validating bgp session flap and traffic loss")
        self.inputs.restart_service('contrail-control', [non_vrouter_controller], container='control')

        time.sleep(60)
        final_flap_count = self.get_bgp_router_flap_count(bgpaas_fixture)

        if init_flap_count == final_flap_count:
           self.logger.info("There is no flap on restarting non-vrouter controller")
        else:
           assert False,"Session flap seen on restarting non-vrouter controller"

        ping_stats = ping_h.get_stats()
        if int(ping_stats["loss"]) == 0:
           self.logger.info("There is no traffic loss when non-vrouter controller is restarted")
        else:
           assert False , "There is traffic loss when non-vrouter controller is restarted"

        ret = bgpaas_fixture.verify_in_control_node(bgpaas_vm1)
        if ret:
           self.logger.info("BGP session with Controller is  seen after restarting non-vrouter controller")
        else:
           assert False,"BGP session with Controller is not seen after restarting non-vrouter controller"

    @preposttest_wrapper
    def test_bgpaas_vsrx_agent_stop(self):
        """
        Description: Single BGPaaS Session with 2 VMI from 2 VMs on different computes.
                     Verify agent stop on one compute does not interrupt traffic.
        Test Steps:
             1. Bringup test vm on compute1,vsrx1 on compute2,vsrx2 on compute3
             2. Create single bgpaas service and attach vmi from vsrx1 and vsrx2 and bgpaas_shared=False
             3. run aap on both vmi ports in active-active mode.
             4. run vrrp between both vsrx with same vrrp priority
             5. Configure BGP session on both vsrx to .1
             6. Configure both vsrx to advertise 9.9.9.9 from lo0
             7. start the ping traffic from test-vm
             8. stop the vrouter-agent on vsrx1 compute. Verify there is no traffic loss
             9. start the vrouter-agent on vsrx1 compute again and verify there is no traffic loss
            10. stop the vrouter-agent on vsrx2 compute and verify there is no traffic loss
        Maintainer: vageesant@juniper.net
        """

        if len(self.inputs.compute_ips) < 3:
           raise self.skipTest("Skipping test case,this test needs atleast 3 compute nodes")

        vn_name = get_random_name('bgpaas_vn')
        vn_subnets = [get_random_cidr()]
        vn_fixture = self.create_vn(vn_name, vn_subnets)
        test_vm = self.create_vm(vn_fixture, 'test_vm',
                                 image_name='ubuntu-traffic',node_name=self.inputs.compute_names[0])
        bgpaas_vm1 = self.create_vm(vn_fixture, 'bgpaas_vm1',
                                    image_name='vsrx',node_name=self.inputs.compute_names[1])
        bgpaas_vm2 = self.create_vm(vn_fixture, 'bgpaas_vm2',
                                    image_name='vsrx',node_name=self.inputs.compute_names[2])
        assert test_vm.wait_till_vm_is_up()

        autonomous_system = random.randint(30000,31000)
        bgpaas_vm1_state = False
        bgpaas_vm2_state = False
        for i in range(3):
            bgpaas_vm1_state = bgpaas_vm1.wait_till_vm_is_up()
            if bgpaas_vm1_state:
               break
        assert bgpaas_vm1_state,"bgpaas_vm1 failed to come up"
        for i in range(3):
            bgpaas_vm2_state = bgpaas_vm2.wait_till_vm_is_up()
            if bgpaas_vm2_state:
               break
        assert bgpaas_vm2_state,"bgpaas_vm2 failed to come up"

        bgp_ip = get_an_ip(vn_subnets[0], offset=10)
        bfd_enabled = True
        lo_ip = get_an_ip(vn_subnets[0], offset=15)
        bgpaas_fixture = self.create_bgpaas(
            bgpaas_shared=False, autonomous_system=autonomous_system, bgpaas_ip_address=bgp_ip)
        self.logger.info('Configure two ports and configure AAP between them')
        port1 = bgpaas_vm1.vmi_ids[bgpaas_vm1.vn_fq_name]
        port2 = bgpaas_vm2.vmi_ids[bgpaas_vm2.vn_fq_name]
        port_list = [port1, port2]
        for port in port_list:
            self.config_aap(port, bgp_ip, mac='00:00:5e:00:01:01',aap_mode="active-active",contrail_api=True)
        self.logger.info('We will configure VRRP on the two vSRX')
        self.config_vrrp_on_vsrx(
            src_vm=test_vm, dst_vm=bgpaas_vm1, vip=bgp_ip, priority='200', interface='ge-0/0/0')
        self.config_vrrp_on_vsrx(
            src_vm=test_vm, dst_vm=bgpaas_vm2, vip=bgp_ip, priority='200', interface='ge-0/0/0')
        self.logger.info('Will wait for both the vSRXs to come up')

        address_families = []
        address_families = ['inet', 'inet6']
        gw_ip = vn_fixture.get_subnets()[0]['gateway_ip']
        dns_ip = vn_fixture.get_subnets()[0]['dns_server_address']
        #neighbors = [gw_ip, dns_ip]
        neighbors = [gw_ip]
        self.logger.info('We will configure BGP on the two vSRX')
        self.config_bgp_on_vsrx(src_vm=test_vm, dst_vm=bgpaas_vm1, bgp_ip=bgp_ip, lo_ip=lo_ip,
                                address_families=address_families, autonomous_system=autonomous_system, neighbors=neighbors, bfd_enabled=True)
        self.config_bgp_on_vsrx(src_vm=test_vm, dst_vm=bgpaas_vm2, bgp_ip=bgp_ip, lo_ip=lo_ip,
                                address_families=address_families, autonomous_system=autonomous_system, neighbors=neighbors, bfd_enabled=True)
        cmds = []
        cmds.append("set interfaces lo0 unit 0 family inet address 9.9.9.9/32")
        cmds.append("set security zones security-zone trust interfaces lo0 host-inbound-traffic system-services all")
        cmds.append("activate security policies")
        self.configure_vsrx(srv_vm=test_vm,dst_vm=bgpaas_vm1,cmds=cmds)
        self.configure_vsrx(srv_vm=test_vm,dst_vm=bgpaas_vm2,cmds=cmds)

        self.logger.info('Attaching both the VMIs to the BGPaaS object')
        self.attach_vmi_to_bgpaas(port1, bgpaas_fixture)
        self.addCleanup(self.detach_vmi_from_bgpaas,
                        port1, bgpaas_fixture)
        self.attach_vmi_to_bgpaas(port2, bgpaas_fixture)
        self.addCleanup(self.detach_vmi_from_bgpaas,
                        port2, bgpaas_fixture)

        session1 = bgpaas_fixture.verify_in_control_node(
                bgpaas_vm1)
        session2 = bgpaas_fixture.verify_in_control_node(
                bgpaas_vm2)

        if session1 and session2:
          self.logger.info("BGP Session is established with both vsrx")
        else:
          assert False,"BGP Session is not established with both vsrx"

        time.sleep(30)

        ping_h = self.start_ping(test_vm, dst_ip="9.9.9.9")

        self.logger.info("Stop the active VM's vrouter-agent")
        self.addCleanup(self.inputs.start_service('contrail-vrouter-agent', [bgpaas_vm1.vm_node_data_ip,bgpaas_vm2.vm_node_data_ip],
                                         container='agent'))
        self.inputs.stop_service('contrail-vrouter-agent', [bgpaas_vm1.vm_node_data_ip],
                                         container='agent')
        time.sleep(60)

        ping_stats = ping_h.get_stats()
        if int(ping_stats["loss"]) == 0:
           self.logger.info("there is no traffic loss on stopping one of the vrouter-agent")
        else:
           self.inputs.restart_service('contrail-vrouter-agent', [bgpaas_vm1.vm_node_data_ip,bgpaas_vm2.vm_node_data_ip],
                                         container='agent') 
           assert False , "There is traffic loss when stopping one of the vrouter-agent"

        self.inputs.restart_service('contrail-vrouter-agent', [bgpaas_vm1.vm_node_data_ip],
                                         container='agent')

        time.sleep(60)

        ping_stats = ping_h.get_stats()
        if int(ping_stats["loss"]) == 0:
           self.logger.info("there is no traffic loss on starting again one of the vrouter-agent")
        else:
           self.inputs.restart_service('contrail-vrouter-agent', [bgpaas_vm1.vm_node_data_ip,bgpaas_vm2.vm_node_data_ip],
                                         container='agent') 
           assert False,"There is traffic loss when active VMs vrouter-agent is started again"

        self.logger.info("stopping the secondary VMs vrouter-agent")

        self.inputs.stop_service('contrail-vrouter-agent', [bgpaas_vm2.vm_node_data_ip],
                                         container='agent')
        time.sleep(60)

        ping_stats = ping_h.get_stats()
        if int(ping_stats["loss"]) == 0:
           self.logger.info("there is no traffic loss on stopping second vrouter-agent")
        else:
           self.inputs.start_service('contrail-vrouter-agent', [bgpaas_vm1.vm_node_data_ip,bgpaas_vm2.vm_node_data_ip],
                                         container='agent')
           assert False , "There is traffic loss when secondary VMs vrouter-agent is stopped"
