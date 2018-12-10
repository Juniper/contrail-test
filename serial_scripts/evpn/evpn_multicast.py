from tcutils.wrappers import preposttest_wrapper
from evpn_multicast import *
from tcutils.util import skip_because
import ipaddress


class TestEvpnt6Mn(Evpnt6MultinodeBase):

    @classmethod
    def setUpClass(cls):
        super(TestEvpnt6Mn, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestEvpnt6Mn, cls).tearDownClass()

    @preposttest_wrapper
    def verify_evpnt6_multinode_sanity(self):
        ''' 
            VM1 ,VM2 and VM3 in different compute nodes.
            Send IGMP join from all 3 . 
            Send IGMP leave from all 3 VMs. 
            VM should get traffic on IGMP join, on leave traffic should stop.
        '''

        result = True
        vm_fixtures = self.configure_evpn_mn_topology()
        vm_fixtures['vrf']= vm_fixtures['vm1']
        bms_fixtures = vm_fixtures['bms']
        int = bms_fixtures.get_mvi_interface()
        bms_fixtures.config_mroute(int,'225.1.1.1','255.255.255.255')
        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name)
        vxlan = 400


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
                             'source': '5.1.1.10',        # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of groups
                               }
                  }

        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)


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
                             'source': '5.1.1.10',        # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }


        # Send and verify IGMP reports and multicast traffic

        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp ,vxlan)
           
        #3 Send igmp leave , VMs should not get multicast traffic.
        #########################################################
        self.logger.info('#3 Send igmp leave , VMs should not get multicast traffic.')

        igmp = {'type': 23,                   # IGMPv3 Report
              'numgrp': 1,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }

        result = self.send_igmp_reportv2(vm_fixtures['vm1'], igmp)
        result = self.send_igmp_reportv2(vm_fixtures['vm2'], igmp)
        result = self.send_igmp_reportv2(vm_fixtures['vm3'], igmp)
        time.sleep(10)

        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': [],     # Multicast receivers
                             'non_rcvrs': ['vm1','vm2','vm3'],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': '5.1.1.10',        # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }

        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)


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
                             'source': '5.1.1.10',        # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }

        # Send and verify IGMP reports and multicast traffic

        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)


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
                             'source': '5.1.1.10',        # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }

        # Send and verify IGMP reports and multicast traffic

        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)

        return result
    # End verify_evpnt6_multinode_sanity

    @preposttest_wrapper
    def verify_evpnt6_multinode_ext(self):
        ''' 
            VM1 ,VM2 and VM3 in different compute nodes.
            Send IGMP join from all 3 . 
            Send IGMP leave from all 3 VMs. 
            VM should get traffic on IGMP join, on leave traffic should stop.
        '''

        result = True
        vm_fixtures = self.configure_evpn_mn_topology()
        vm_fixtures['vrf']= vm_fixtures['vm1']
        bms_fixtures = vm_fixtures['bms']
        int = bms_fixtures.get_mvi_interface()
        bms_fixtures.config_mroute(int,'225.1.1.1','255.255.255.255')
        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name)
        vxlan = 400

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

        result = self.send_igmp_reportv2(vm_fixtures['vm2'], igmp1)
        result = self.send_igmp_reportv2(vm_fixtures['vm3'], igmp1)

        # Multicast Traffic details
        # IGMPv3 join is sent from vm2 and vm3, not from vm4. So, that when
        # multicast source vm1 starts sending data traffic, vm2 and vm3 only
        # should receive the traffic, not vm4.
        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': ['vm1'],     # Multicast receivers
                             'non_rcvrs': ['vm2','vm3'],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': '5.1.1.10',        # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }


        # Send and verify IGMP reports and multicast traffic
        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)
        
        #2 Restart agent and recheck functionality
        ###########################################################################################
        self.logger.info('#2 Restart agent and recheck functionality')

        for compute_ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter', [compute_ip],
                                       container='agent')
        time.sleep(60)

        #3 Flap control plane and check functionality
        ###########################################################################################
        self.logger.info('#3 Flap control plane and check functionality')

        # Send and verify IGMP reports and multicast traffic
        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)

        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('contrail-control', [bgp_ip],
                                        container='control')

        time.sleep(60)
        # Send and verify IGMP reports and multicast traffic
        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)
 
        #4 Ensure entries are removed after timeout
        ###########################################################################################
        self.logger.info('#4 Ensure entries are removed after timeout')

        time.sleep(180)
        time.sleep(60)
  
        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': [],     # Multicast receivers
                             'non_rcvrs': ['vm1','vm2','vm3'],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': '5.1.1.10',        # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }



        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp, vxlan,False)
        #def send_verify_mcastv2(self, vm_fixtures, traffic, igmp, assert=True):
    
        if result:
            self.logger.info('Multicast entry removed after timeout')
        else:
            self.logger.info('Multicast entry seen after timeout')
            import pdb;pdb.set_trace()
            assert result, "Error Multicast entry seen after timeout"

        #5 Disable igmp . No type 6 routes are sent.
        #######################################################################################
        self.logger.info('#5 Disable igmp . No type 6 routes are sent.')
        
        vn1_fixture = vm_fixtures['vn1']
        self.vn1_fixture.set_igmp_config(False)
        self.connections.vnc_lib_fixture.set_global_igmp_config(igmp_enable=False)

        time.sleep(40)

        igmp = {'type': 22,                   # IGMPv3 Report
              'numgrp': 1,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }


        igmp1 = {'type': 22,                   # IGMPv3 Report
              'numgrp': 1,                    # Number of group records
              'gaddr': '225.1.1.2'       # Multicast group address
               }
        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': [],     # Multicast receivers
                             'non_rcvrs': ['vm1','vm2','vm3'],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': '5.1.1.10',        # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }

        result = self.send_igmp_reportv2(vm_fixtures['vm1'], igmp)
        result = self.send_igmp_reportv2(vm_fixtures['vm2'], igmp)
        result = self.send_igmp_reportv2(vm_fixtures['vm3'], igmp)

        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp, vxlan,False)

        if result:
            self.logger.info('Type 6 routes are not seen after disabling igmp')
        else:
            self.logger.info('Type 6 routes are seen after disabling igmp')
            #import pdb;pdb.set_trace()
            assert result, "Error Type 6 routes are seen after disabling igmp"

        #6 Enable igmp . Test type 6 functionality.
        #######################################################################################
        self.logger.info('#6 Enable igmp . Test type 6 functionality.')

        self.connections.vnc_lib_fixture.set_global_igmp_config(igmp_enable=True)
        self.connections.vnc_lib_fixture.set_global_igmp_config(igmp_enable=True)
        time.sleep(60)
    

        #result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)
        return result


class TestEvpnt6Sn(Evpnt6SinglenodeBase):

    @classmethod
    def setUpClass(cls):
        super(TestEvpnt6Sn, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestEvpnt6Sn, cls).tearDownClass()

    @preposttest_wrapper
    def verify_evpnt6_singlenode_sanity(self):
        ''' 
            VM1 ,VM2 and VM3 in same compute nodes.
            Send IGMP join from all 3 . 
            Send IGMP leave from all 3 VMs. 
            VM should get traffic on IGMP join, on leave traffic should stop.
        '''

        result = True
        vm_fixtures = self.configure_evpn_sn_topology()
        vm_fixtures['vrf']= vm_fixtures['vm1']
        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name)
        bms_fixtures = vm_fixtures['bms']
        int = bms_fixtures.get_mvi_interface()
        bms_fixtures.config_mroute(int,'225.1.1.1','255.255.255.255')
        vxlan = 400


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
                             'source': '5.1.1.10',        # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }

        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)


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
                             'source': '5.1.1.10',        # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }


        # Send and verify IGMP reports and multicast traffic
        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)
           
        #3 Send igmp leave , VMs should not get multicast traffic.
        #########################################################
        self.logger.info('#3 Send igmp leave , VMs should not get multicast traffic..')

        igmp = {'type': 23,                   # IGMPv3 Report
              'numgrp': 1,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }

        result = self.send_igmp_reportv2(vm_fixtures['vm1'], igmp)
        result = self.send_igmp_reportv2(vm_fixtures['vm2'], igmp)
        result = self.send_igmp_reportv2(vm_fixtures['vm3'], igmp)
        time.sleep(10)

        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': [],     # Multicast receivers
                             'non_rcvrs': ['vm1','vm2','vm3'],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.1/32',        # Multicast group address
                             'source': '5.1.1.10',        # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }

        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)

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
                             'source': '5.1.1.10',        # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':1                   # Num of packets
                               }
                  }

        # Send and verify IGMP reports and multicast traffic
        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)

        return result


class TestEvpnt6MultiGroup(Evpnt6MultinodeBase):

    @classmethod
    def setUpClass(cls):
        super(TestEvpnt6MultiGroup, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestEvpnt6MultiGroup, cls).tearDownClass()

    @preposttest_wrapper
    def verify_evpnt6_multigroup_sanity(self):
        ''' 
            Send multiple (*,G)  for different groups.
            Ensure Type6 route is generated for each group.Send traffic to all groups.
            
        '''


        result = True
        vm_fixtures = self.configure_evpn_mn_topology()
        vm_fixtures['vrf']= vm_fixtures['vm1']
        bms_fixtures = vm_fixtures['bms']
        int = bms_fixtures.get_mvi_interface()
        bms_fixtures.config_mroute(int,'225.1.1.0','255.255.255.0')

        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name)

        group_count = 10
        vxlan = 400

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
                             'source': '5.1.1.10',        # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':group_count                   # Num of packets
                               }
                  }

        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)


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
                             'source': '5.1.1.10',        # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':group_count                   # Num of packets
                               }
                  }


        # Send and verify IGMP reports and multicast traffic
        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)
           
        #3 Send igmp leave , VMs should not get multicast traffic.
        #########################################################
        self.logger.info('#3 Send igmp leave , VMs should not get multicast traffic.')

        igmp = {'type': 23,                   # IGMPv3 Report
              'numgrp': group_count,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }

        result = self.send_igmp_reportv2(vm_fixtures['vm1'], igmp)
        result = self.send_igmp_reportv2(vm_fixtures['vm2'], igmp)
        result = self.send_igmp_reportv2(vm_fixtures['vm3'], igmp)
        time.sleep(10)

        traffic = {'stream1': {'src':['bms'],                 # Multicast source
                             'rcvrs': [],     # Multicast receivers
                             'non_rcvrs': ['vm1','vm2','vm3'],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.0/24',        # Multicast group address
                             'source': '5.1.1.10',        # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':group_count                   # Num of packets
                               }
                  }

        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)


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
                             'source': '5.1.1.10',        # Multicast group address
                             'pcount':10,                 # Num of packets
                             'count':group_count                   # Num of packets
                               }
                  }

        # Send and verify IGMP reports and multicast traffic
        result = self.send_verify_mcastv2(vm_fixtures, traffic, igmp,vxlan)
        #import pdb;pdb.set_trace()

        return result
    # End TestEvpnt6MultiGroup


class TestEvpnt6MultiVn(Evpnt6MultiVnBase):

    @classmethod
    def setUpClass(cls):
        super(TestEvpnt6MultiVn, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestEvpnt6MultiVn, cls).tearDownClass()

    @preposttest_wrapper
    def verify_evpnt6_multivn_sanity(self):
        ''' 
            Create multiple VN and send igmp join form each VN.
            Ensure type 6 routes are generated and VM should get multicast traffic.
        '''

        result = True
        group_count = 1
        vn_count = 4

        self.allow_default_sg_to_allow_all_on_project(self.inputs.project_name)
        vm_fixtures = self.configure_evpn_mvn_topology(vn_count)


        igmp = {'type': 22,                   # IGMPv3 Report
              'numgrp': group_count,                    # Number of group records
              'gaddr': '225.1.1.1'       # Multicast group address
               }

        vn_ip = unicode('5.1.1.0', "utf-8")
        vn_ip = ipaddress.ip_address(vn_ip)
        vxlan = 400
        for i in range(1,vn_count):

            bms_name= Template('bms$i')
            bms_name =bms_name.substitute(i=i)
            vm_name= Template('vm$i')
            vm_name =vm_name.substitute(i=i)
            vn_name= Template('vn$i')
            vn_name =vn_name.substitute(i=i)
            vn_subnet = str(vn_ip) +'/24'
            bms_ip = vn_ip + 10
            vn_subnets = [vn_subnet]

            bms_fixtures = vm_fixtures[bms_name]
            int = bms_fixtures.get_mvi_interface()
            bms_fixtures.config_mroute(int,'225.1.1.0','255.255.255.0')

            self.logger.info('Testing vm %s bms %s bms source %s ' %(vm_name,bms_name,bms_ip))

          
            traffic = {'stream1': {'src':[bms_name],                 # Multicast source
                             'rcvrs': [vm_name],     # Multicast receivers
                             'non_rcvrs': [],        # Non Multicast receivers
                             'maddr': '225.1.1.1',        # Multicast group address
                             'mnet': '225.1.1.0/24',        # Multicast group address
                             'source': bms_ip,        # Multicast group address
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
    # End TestEvpnt6MultiVn
