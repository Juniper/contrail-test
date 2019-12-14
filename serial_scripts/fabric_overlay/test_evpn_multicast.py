from builtins import str
from builtins import range
from tcutils.wrappers import preposttest_wrapper
from common.contrail_fabric.mcast_base import *
import ipaddress
from multicast_policy_fixture import MulticastPolicyFixture
from vn_policy_test import VN_Policy_Fixture

class TestEvpnt6SPStyle(Evpnt6TopologyBase):
    enterprise_style = False
    def _verify_multinode_sanity(self, bms_node=None):
        ''' 
            VM1 ,VM2 and VM3 in different compute nodes.
            Send IGMP join from all 3 . 
            Send IGMP leave from all 3 VMs. 
            VM should get traffic on IGMP join, on leave traffic should stop.
        '''

        vxlan = random.randrange(400, 405)
        vm_fixtures = self.configure_evpn_topology(vxlan, bms_node=bms_node)
        vm_fixtures['vrf'] = vm_fixtures['vm1']
        bms_fixture = vm_fixtures['bms']
        interface = bms_fixture.get_mvi_interface()
        bms_fixture.config_mroute(interface,'225.1.1.1','255.255.255.255')


        igmp = {'type': 22,                # IGMPv3 Report
                'numgrp': 1,               # Number of group records
                'gaddr': '225.1.1.1'       # Multicast group address
               }

        #1 Before sending igmp join , VM shouldnt receive traffic.
        ################################################################

        self.logger.info('#1 Before sending igmp join , VM shouldnt receive traffic')
 
        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': [],     # Multicast receivers
                             'non_rcvrs': ['vm1','vm2','vm3'],        # Non Multicast receivers
                             'maddr': '225.1.1.1',          # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of groups
                               }
                  }

        assert self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)


        #2 Send igmp join , All VMs should get traffic.
        ########################################################
        self.logger.info('#2 Send igmp join , All VMs should get traffic.')

        # Multicast Traffic details
        # IGMPv3 join is sent from vm2 and vm3, not from vm4. So, that when
        # multicast source vm1 starts sending data traffic, vm2 and vm3 only
        # should receive the traffic, not vm4.
        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': ['vm1','vm2','vm3'],     # Multicast receivers
                             'non_rcvrs': [],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }

        # Send and verify IGMP reports and multicast traffic

        assert self.send_verify_mcastv2(vm_fixtures, traffic, igmp ,vxlan)
           
        #3 Send igmp leave , VMs should not get multicast traffic.
        #########################################################
        self.logger.info('#3 Send igmp leave , VMs should not get multicast traffic.')

        igmp = {'type': 23,                   # IGMPv3 Report
              'numgrp': 1,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }

        self.send_igmp_reportv2(vm_fixtures['vm1'], igmp)
        self.send_igmp_reportv2(vm_fixtures['vm2'], igmp)
        self.send_igmp_reportv2(vm_fixtures['vm3'], igmp)
        time.sleep(10)

        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': [],     # Multicast receivers
                             'non_rcvrs': ['vm1','vm2','vm3'],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }

        assert self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)


        #4 Send igmp join after leave from 2 VM, VMs should get multicast traffic.
        ################################################################
        self.logger.info('#4 Send igmp join after leave from 2 VM, VMs should get multicast traffic.')

        igmp = {'type': 22,                   # IGMPv3 Report
              'numgrp': 1,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }


        # Multicast Traffic details
        # IGMPv3 join is sent from vm2 and vm3, not from vm4. So, that when
        # multicast source vm1 starts sending data traffic, vm2 and vm3 only
        # should receive the traffic, not vm4.
        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': ['vm1','vm2'],     # Multicast receivers
                             'non_rcvrs': ['vm3'],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }

        # Send and verify IGMP reports and multicast traffic

        assert self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)


        #5 Send igmp join from all VMs , VMs should get multicast traffic.
        ################################################################
        self.logger.info('#5 Send igmp join from all VMs , VMs should get multicast traffic.')

        igmp = {'type': 22,                   # IGMPv3 Report
              'numgrp': 1,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }

        # Multicast Traffic details
        # IGMPv3 join is sent from vm2 and vm3, not from vm4. So, that when
        # multicast source vm1 starts sending data traffic, vm2 and vm3 only
        # should receive the traffic, not vm4.
        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': ['vm1','vm2','vm3'],     # Multicast receivers
                             'non_rcvrs': [],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }

        # Send and verify IGMP reports and multicast traffic
        assert self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)

    # End _verify_multinode_sanity

    @preposttest_wrapper
    def test_evpnt6_multinode_basic_crb_access(self):
        bms_node = self.get_bms_nodes()[0]
        devices = self.get_associated_prouters(bms_node)
        self.addCleanup(self.assign_roles, self.fabric, self.devices,
                        rb_roles=self.rb_roles)
        self.assign_roles(self.fabric, devices,
                        rb_roles={device.name: ['CRB-Access']
                        for device in devices})
        self._verify_multinode_sanity(bms_node=bms_node)

class TestEvpnt6(TestEvpnt6SPStyle):
    enterprise_style = True
    @preposttest_wrapper
    def test_evpnt6_multinode_basic(self, bms_node=None):
        self._verify_multinode_sanity()

    @preposttest_wrapper
    def test_evpnt6_restart(self):
        ''' 
            Verify VMs are getting traffic only from subscribed groups.
            Verify evpn multicast after agent restart.
            Verify evpn multicast after control plane flap.
            Verify evpn type 6 routes are timed out.
        '''

        vxlan = random.randrange(400, 405)
        vm_fixtures = self.configure_evpn_topology(vxlan)
        vm_fixtures['vrf']= vm_fixtures['vm1']
        bms_fixture = vm_fixtures['bms']
        interface = bms_fixture.get_mvi_interface()
        bms_fixture.config_mroute(interface,'225.1.1.1','255.255.255.255')

        #1 Send igmp join from different groups , VM should get traffic only form  subscribed groups 
        ###########################################################################################

        self.logger.info('#1 Send igmp join from different groups , VM should get traffic only form  subscribed groups')

        igmp = {'type': 22,                   # IGMPv3 Report
              'numgrp': 1,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }

        igmp1 = {'type': 22,                   # IGMPv3 Report
              'numgrp': 1,                    # Number of group records
              'gaddr': '225.1.1.2'       # Multicast group address
               }

        self.send_igmp_reportv2(vm_fixtures['vm2'], igmp1)
        self.send_igmp_reportv2(vm_fixtures['vm3'], igmp1)

        # Multicast Traffic details
        # IGMPv3 join is sent from vm2 and vm3, not from vm4. So, that when
        # multicast source vm1 starts sending data traffic, vm2 and vm3 only
        # should receive the traffic, not vm4.
        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': ['vm1'],     # Multicast receivers
                             'non_rcvrs': ['vm2','vm3'],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }


        # Send and verify IGMP reports and multicast traffic
        assert self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)
        
        #2 Restart agent and recheck functionality
        ###########################################################################################
        self.logger.info('#2 Restart agent and recheck functionality')

        for compute_ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter', [compute_ip],
                                       container='agent')
        time.sleep(20)

        for compute_ip in self.inputs.compute_ips:
            state, state1 = self.inputs.verify_service_state(compute_ip, service='agent')
            assert state,'contrail agent is inactive'
            self.logger.info('contrail agent is active')



        #3 Flap control plane and check functionality
        ###########################################################################################
        self.logger.info('#3 Flap control plane and check functionality')

        # Send and verify IGMP reports and multicast traffic
        assert self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)

        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('contrail-control', [bgp_ip],
                                        container='control')

        for bgp_ip in self.inputs.bgp_ips:
            state, state1 = self.inputs.verify_service_state(bgp_ip, service='control')
            assert state,'contrail control service is inactive'
            self.logger.info('contrail control service is active')


        time.sleep(60)
        time.sleep(60)
        # Send and verify IGMP reports and multicast traffic
        assert self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)
 
        #4 Ensure entries are removed after timeout
        ###########################################################################################
        self.logger.info('#4 Ensure entries are removed after timeout')

        # After 220 sec igmp entry should time out 

        time.sleep(240)
  
        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': [],     # Multicast receivers
                             'non_rcvrs': ['vm1','vm2','vm3'],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }



        assert self.send_verify_mcastv2(vm_fixtures, traffic,
            igmp, vxlan, False), "Error Multicast entry seen after timeout"
        self.logger.info('Multicast entry removed after timeout')

    @preposttest_wrapper
    def test_evpnt6_igmp_config(self):
        '''
            Disable IGMP.Traffic is flooded using type 3 routes.
            Configure IGMP at global level and verify functionality.
        '''

        vxlan = random.randrange(400, 405)
        vm_fixtures = self.configure_evpn_topology(vxlan)
        vm_fixtures['vrf']= vm_fixtures['vm1']
        bms_fixture = vm_fixtures['bms']
        interface = bms_fixture.get_mvi_interface()
        bms_fixture.config_mroute(interface,'225.1.1.1','255.255.255.255')


        #1 Disable igmp . Traffic is flooded using type 3 routes.
        #######################################################################################
        self.logger.info('#1 Disable igmp . Traffic is flooded using type 3 routes.')
        
        vn1_fixture = vm_fixtures['vn1']
        self.vn1_fixture.set_igmp_config(False)
        self.connections.vnc_lib_fixture.set_global_igmp_config(igmp_enable=False)
        self.addCleanup(self.connections.vnc_lib_fixture.set_global_igmp_config, igmp_enable=True)

        prouters = self.get_associated_prouters(bms_fixture.name)
        self.disable_snooping(prouters)
        self.addCleanup(self.enable_snooping, prouters)

        time.sleep(40)

        igmp = {'type': 22,                   # IGMPv3 Report
              'numgrp': 1,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }


        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': ['vm1','vm2','vm3'],     # Multicast receivers
                             'non_rcvrs': [],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }

        self.send_igmp_reportv2(vm_fixtures['vm1'], igmp)
        self.send_igmp_reportv2(vm_fixtures['vm2'], igmp)
        self.send_igmp_reportv2(vm_fixtures['vm3'], igmp)

        msg = "After disabling IGMP multcast traffic is not sent to all VMs"
        assert self.send_verify_mcast_traffic(vm_fixtures,
            traffic, igmp, vxlan, False), msg

        self.logger.info('After disabling IGMP , multcast traffic is sent to all VMs.')

        self.enable_snooping(prouters)


 
        #2 Enable igmp at global level. Test type 6 functionality.
        #######################################################################################


        self.logger.info('#2 Enable igmp at global level. Test type 6 functionality.')

        self.connections.vnc_lib_fixture.set_global_igmp_config(igmp_enable=True)
        time.sleep(180)

        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': ['vm1','vm2'],     # Multicast receivers
                             'non_rcvrs': ['vm3'],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }


        assert self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)

        self.connections.vnc_lib_fixture.set_global_igmp_config(igmp_enable=False)
        time.sleep(30)

        #3 Enable igmp on VMI level. Test type 6 functionality.
        #######################################################################################

        self.logger.info('#2 Enable igmp at VMI level. Test type 6 functionality.')

        vmi1= list(vm_fixtures['vm1'].get_vmi_ids().values())[0]
        vmi2= list(vm_fixtures['vm2'].get_vmi_ids().values())[0]
        vmi3= list(vm_fixtures['vm3'].get_vmi_ids().values())[0]
        self.configure_igmp_on_vmi(vmi1,True)
        self.configure_igmp_on_vmi(vmi2,True)
        self.configure_igmp_on_vmi(vmi3,True)

        time.sleep(180)

        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': ['vm1','vm2'],     # Multicast receivers
                             'non_rcvrs': ['vm3'],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }

        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)
        self.connections.vnc_lib_fixture.set_global_igmp_config(igmp_enable=True)

    @preposttest_wrapper
    def test_multicast_policy(self):
        ''' 
            VM1 ,VM2 and VM3 in different compute nodes.
            Add multicast policy to block multicast traffic.On applying policy multicast traffic should be discarded.
            On removing policy multicast traffic should be allowed.
        '''

        result = True
        vxlan = random.randrange(400, 405)
        vm_fixtures = self.configure_evpn_topology(vxlan)
        vm_fixtures['vrf']= vm_fixtures['vm1']
        bms_fixture = vm_fixtures['bms']
        vn1_fixture = vm_fixtures['vn1']
        interface = bms_fixture.get_mvi_interface()
        bms_fixture.config_mroute(interface,'225.1.1.1','255.255.255.255')
        bms_fixture.config_mroute(interface,'225.1.1.2','255.255.255.255')

        #1 Add multicast policy to block multicast traffic.On applying policy multicast traffic should be discarded
        #############################################################################################################

        name = 'policy1'
        pol1 =[{'action' : 'deny' ,'source' : '0.0.0.0','group' : '225.1.1.1'}]
        pol2 =[{'action' : 'pass' ,'source' : '0.0.0.0','group' : '225.1.1.2'}]
  
        policy_obj = self.useFixture(MulticastPolicyFixture(name=name,policy=pol1,connections=self.connections))
        self.logger.info('!!!!!!!!!!!!!!!!!!!!! uuid is %s ' %(policy_obj.uuid))
        name2 = 'policy2'
        policy_obj2 = self.useFixture(MulticastPolicyFixture(name=name2,policy=pol2,connections=self.connections))

        self.logger.info('!!!!!!!!!!!!!!!!!!!!! uuid is %s ' %(policy_obj2.uuid))

        # attach policy to VN
        VN1_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=vn1_fixture.vn_name,
                policy_obj={vn1_fixture.vn_name : \
                           [policy_obj,policy_obj2]},
                vn_obj={vn1_fixture.vn_name : vn1_fixture},
                vn_policys=['policy1','policy2'],
                project_name=self.project.project_name,options='contrail',type='multicast'))


        self.logger.info('#1 Send igmp join from different groups , VM should get traffic only form  subscribed groups')

        igmp = {'type': 22,                   # IGMPv3 Report
              'numgrp': 1,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }

        self.send_igmp_reportv2(vm_fixtures['vm1'], igmp)
        self.send_igmp_reportv2(vm_fixtures['vm2'], igmp)
        self.send_igmp_reportv2(vm_fixtures['vm3'], igmp)

        time.sleep(5)
  
        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': [],     # Multicast receivers
                             'non_rcvrs': ['vm1','vm2','vm3'],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }

        result = result & self.send_verify_mcast_traffic(vm_fixtures, traffic, igmp, vxlan,False)
    
        if result:
            self.logger.info('Multicast entry removed after timeout')
        else:
            self.logger.info('Multicast entry seen after timeout')
            assert result, "Error Multicast entry seen after timeout"

        igmp = {'type': 22,                   # IGMPv3 Report
              'numgrp': 1,                    # Number of group records
              'gaddr': '225.1.1.2'       # Multicast group address
               }
        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': ['vm1','vm2','vm3'],     # Multicast receivers
                             'non_rcvrs': [],        # Non Multicast receivers
                             'maddr': '225.1.1.2',        # Multicast group address
                             'mnet': '225.1.1.2/32',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }


        # Send and verify IGMP reports and multicast traffic

        result = result & self.send_verify_mcastv2(vm_fixtures, traffic, igmp ,vxlan)




        #2 On removing policy multicast traffic should be allowed.
        #######################################################################################

        self.logger.info('#2 Detach policy from VN--------------.')

        VN1_policy_fixture.detach_Policy_VN()

        time.sleep(60)

        igmp = {'type': 22,                   # IGMPv3 Report
              'numgrp': 1,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }

        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': ['vm1','vm2','vm3'],     # Multicast receivers
                             'non_rcvrs': [],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }


        # Send and verify IGMP reports and multicast traffic

        result = result & self.send_verify_mcastv2(vm_fixtures, traffic, igmp ,vxlan)


        return result



    @preposttest_wrapper
    def test_source_within_cluster(self):
        ''' 
            VM1 ,VM2 and VM3 in different compute nodes.
            Send IGMP join from all 3 . 
            Send IGMP leave from all 3 VMs. 
            VM should get traffic on IGMP join, on leave traffic should stop.
        '''

        result = True
        vxlan = random.randrange(400, 405)
        vm_fixtures = self.configure_evpn_topology(vxlan)
        vm_fixtures['vrf']= vm_fixtures['vm1']
        bms_fixture = vm_fixtures['bms']
        interface = bms_fixture.get_mvi_interface()
        bms_fixture.config_mroute(interface,'225.1.1.1','255.255.255.255')

        igmp = {'type': 22,                   # IGMPv3 Report
              'numgrp': 1,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }

        #1 Before sending igmp join , VM shouldnt receive traffic.
        ################################################################

        self.logger.info('#1 Before sending igmp join , VM shouldnt receive traffic')
 
        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': [],     # Multicast receivers
                             'non_rcvrs': ['vm1','vm2','vm3'],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of groups
                               }
                  }

        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)
        return result

    @preposttest_wrapper
    def test_evpnt6_singlenode_sanity(self):
        ''' 
            VM1 ,VM2 and VM3 in same compute nodes.
            Send IGMP join from all 3 . 
            Send IGMP leave from all 3 VMs. 
            VM should get traffic on IGMP join, on leave traffic should stop.
        '''

        result = True
        vxlan = random.randrange(400, 405)
        vm_fixtures = self.configure_evpn_topology(vxlan,multinode=0)
        vm_fixtures['vrf']= vm_fixtures['vm1']
        bms_fixture = vm_fixtures['bms']
        interface = bms_fixture.get_mvi_interface()
        bms_fixture.config_mroute(interface,'225.1.1.1','255.255.255.255')


        #1 Before sending igmp join , VM shouldnt receive traffic.
        ################################################################
        self.logger.info('#1 Before sending igmp join , VM shouldnt receive traffic.')

        igmp = {'type': 22,                   # IGMPv3 Report
              'numgrp': 1,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }

        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': [],     # Multicast receivers
                             'non_rcvrs': ['vm1','vm2','vm3'],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }

        result = result & self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)


        #2 Send igmp join , All VMs should get traffic.
        ##########################################################
        self.logger.info('#2 Send igmp join , All VMs should get traffic..')

        # Multicast Traffic details
        # IGMPv2 join is sent from vm1,vm2 and vm3. So, that when
        # multicast source starts sending data traffic, vm1,vm2 and vm3 only
        # should receive the traffic.

        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': ['vm1','vm2','vm3'],     # Multicast receivers
                             'non_rcvrs': [],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }


        # Send and verify IGMP reports and multicast traffic
        result = result & self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)
           
        #3 Send igmp leave , VMs should not get multicast traffic.
        #########################################################
        self.logger.info('#3 Send igmp leave , VMs should not get multicast traffic..')

        igmp = {'type': 23,                   # IGMPv3 Report
              'numgrp': 1,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }

        self.send_igmp_reportv2(vm_fixtures['vm1'], igmp)
        self.send_igmp_reportv2(vm_fixtures['vm2'], igmp)
        self.send_igmp_reportv2(vm_fixtures['vm3'], igmp)
        time.sleep(10)

        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': [],     # Multicast receivers
                             'non_rcvrs': ['vm1','vm2','vm3'],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }

        result = result & self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)

        #4 Send igmp join after leave , VMs should get multicast traffic.
        ################################################################
        self.logger.info('#4 Send igmp join after leave , VMs should get multicast traffic..')


        igmp = {'type': 22,                   # IGMPv3 Report
              'numgrp': 1,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }


        # Multicast Traffic details
        # IGMPv3 join is sent from vm2 and vm3, not from vm4. So, that when
        # multicast source vm1 starts sending data traffic, vm2 and vm3 only
        # should receive the traffic, not vm4.
        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': ['vm1','vm2','vm3'],     # Multicast receivers
                             'non_rcvrs': [],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }

        # Send and verify IGMP reports and multicast traffic
        result = result & self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)

        return result



    @preposttest_wrapper
    def test_evpnt6_multigroup_basic(self):
        ''' 
            Send multiple (*,G)  for different groups.
            Ensure Type6 route is generated for each group.Send traffic to all groups.
            
        '''


        result = True
        vxlan = random.randrange(400, 405)
        vm_fixtures = self.configure_evpn_topology(vxlan)
        vm_fixtures['vrf']= vm_fixtures['vm1']
        bms_fixture = vm_fixtures['bms']
        interface = bms_fixture.get_mvi_interface()
        bms_fixture.config_mroute(interface,'225.1.1.0','255.255.255.0')


        group_count = 10

        igmp = {'type': 22,                   # IGMPv3 Report
              'numgrp': group_count,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }


        #1 Multicast traffic should drop if no join is sent.
        ################################################################
        self.logger.info('#1 Multicast traffic should drop if no join is sent..')

        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': [],     # Multicast receivers
                             'non_rcvrs': ['vm1','vm2','vm3'],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.0/24',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':group_count                   # Num of packets
                               }
                  }

        result = result & self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)


        #2 Send igmp join , All VMs should get traffic.
        ########################################################
        self.logger.info('#2 Send igmp join from 10 groups, All VMs should get traffic.')

        # Multicast Traffic details
        # IGMPv3 join is sent from vm2 and vm3, not from vm4. So, that when
        # multicast source vm1 starts sending data traffic, vm2 and vm3 only
        # should receive the traffic, not vm4.
        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': ['vm1','vm2','vm3'],     # Multicast receivers
                             'non_rcvrs': [],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.0/24',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':group_count                   # Num of packets
                               }
                  }


        # Send and verify IGMP reports and multicast traffic
        result = result & self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)
           
        #3 Send igmp leave , VMs should not get multicast traffic.
        #########################################################
        self.logger.info('#3 Send igmp leave , VMs should not get multicast traffic.')

        igmp = {'type': 23,                   # IGMPv3 Report
              'numgrp': group_count,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }

        self.send_igmp_reportv2(vm_fixtures['vm1'], igmp)
        self.send_igmp_reportv2(vm_fixtures['vm2'], igmp)
        self.send_igmp_reportv2(vm_fixtures['vm3'], igmp)
        time.sleep(10)

        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': [],     # Multicast receivers
                             'non_rcvrs': ['vm1','vm2','vm3'],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.0/24',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':group_count                   # Num of packets
                               }
                  }

        result = result & self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)
        time.sleep(10)


        #4 Send igmp join after leave , VMs should get multicast traffic.
        ################################################################
        self.logger.info('#4 Send igmp join after leave , VMs should get multicast traffic..')

        igmp = {'type': 22,                   # IGMPv3 Report
              'numgrp': group_count,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }


        # Multicast Traffic details
        # IGMPv3 join is sent from vm2 and vm3, not from vm4. So, that when
        # multicast source vm1 starts sending data traffic, vm2 and vm3 only
        # should receive the traffic, not vm4.
        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': ['vm1','vm2','vm3'],     # Multicast receivers
                             'non_rcvrs': [],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.0/24',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':group_count                   # Num of packets
                               }
                  }

        # Send and verify IGMP reports and multicast traffic
        result = result & self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)

        return result
    # End TestEvpnt6MultiGroup


class TestEvpnt6MultiVn(Evpnt6MultiVnBase):

    @preposttest_wrapper
    def test_evpnt6_multivn_basic(self):
        ''' 
            Create multiple VN and send igmp join form each VN.
            Ensure type 6 routes are generated and VM should get multicast traffic.
        '''

        result = True
        group_count = 1
        vn_count = 5

        vxlan = random.randrange(400, 405)
        vm_fixtures = self.configure_evpn_mvn_topology(vxlan,vn_count)


        igmp = {'type': 22,                   # IGMPv3 Report
              'numgrp': group_count,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }

        vn_ip = str('5.1.1.0', "utf-8")
        vn_ip = ipaddress.ip_address(vn_ip)
        for i in range(1,vn_count):

            bms_name= Template('bms$i')
            bms_name =bms_name.substitute(i=i)
            vm_name= Template('vm$i')
            vm_name =vm_name.substitute(i=i)
            vn_name= Template('vn$i')
            vn_name =vn_name.substitute(i=i)
            vn_subnet = str(vn_ip) +'/24'
            vn_subnets = [vn_subnet]

            bms_fixture = vm_fixtures[bms_name]
            interface = bms_fixture.get_mvi_interface()
            bms_fixture.config_mroute(interface,'225.1.1.0','255.255.255.0')

            self.logger.info('Testing vm %s bms %s bms source %s ' %(vm_name,bms_name,bms_fixture.bms_ip))

          
            traffic = {'stream1': {'src':[bms_name],                 # Multicast source
                             'rcvrs': [vm_name],     # Multicast receivers
                             'non_rcvrs': [],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.0/24',        # Multicast group address
                             'source': bms_fixture.bms_ip,  # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':group_count                   # Num of packets
                               }
                  }
            vm_fixtures['bms'] = vm_fixtures[bms_name]
            vm_fixtures['vrf']= vm_fixtures[vm_name]

            # Send and verify IGMP reports and multicast traffic

            result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)

            vn_ip =  vn_ip + 16777216
            vxlan = vxlan +1

        return result
