from __future__ import division
# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
from common.max_flows.base import BaseMaxFlowsTest
from builtins import str
from builtins import range
from past.utils import old_div
from tcutils.wrappers import preposttest_wrapper
from tcutils.agent import *
from common.max_flows.verify import VerifyMaxFlows
import test
from tcutils.util import skip_because
import time
from tcutils.traffic_utils.scapy_traffic_gen import ScapyTraffic
from tcutils.traffic_utils.traffic_analyzer import TrafficAnalyzer
from compute_node_test import ComputeNodeFixture


class TestMaxFlows(VerifyMaxFlows, BaseMaxFlowsTest):
   
    setup_fixtures = {}

    DEFAULT_FLOW_TIMEOUT = 120

    @classmethod
    def setUpClass(cls):
        super(TestMaxFlows, cls).setUpClass(flow_timeout=120)

    @classmethod
    def tearDownClass(cls):
        super(TestMaxFlows, cls).tearDownClass()

    def runTest(self):
        pass
    #end runTest

    def waiting_for_flow_timeout(self):
        self.logger.info("Sleeping for flow timeout (%d seconds)..." % (self.DEFAULT_FLOW_TIMEOUT))
        time.sleep(self.DEFAULT_FLOW_TIMEOUT)
        self.logger.info("Sleeping for flow timeout (%d seconds)...Completed" % (self.DEFAULT_FLOW_TIMEOUT))

    @preposttest_wrapper
    def test_max_flows_vn_level(self):

        '''
        Description: 
                Verify max_flows functionality at VN level
        Test steps:
               1.Create a vn1 and vn2
               2.configure max_flows as 1000 @ vn1
               3.Launch  vm11, vm12 and vm13 on vn1 network 
               4.Launch vm21 and vm22 on vn2 network 
               5.Verify traffic between the VMs
               6.send 2000 flows traffic from vm11 to vm12 , it should allow only 1000 flows 
               7.send 2000 flows traffic from vm11 to vm13, it should all only 1000 flows 
               8.Modify the max_flows value as 1500, verify traffic between vm11 and vm12 
               9.send 2000 flows traffic from vm21 to vm22, it should allow all the traffic
               10.Delete the max_flows @ vn1 ( by setting the value as 0 )
               11.send 2000 flows traffic from vm11 to vm12 , it should allow all the traffic
        Pass criteria: 
               Number of flows should be created as per max_flows configured at VN level.
               Other VNs should not be imapacted
               After deleting max_flows configuration, it should allow all the flows.
        Maintainer : mmohan@juniper.net
        '''

        vn = {'count':2,            # VN coun
            'vn1':{'subnet':'21.0.0.0/24'},
            'vn2':{'subnet':'22.0.0.0/24'},
            }
        vmi = {'count':5, # VMI Count
            'vmi11':{'vn': 'vn1'}, # VMI details
            'vmi12':{'vn': 'vn1'}, # VMI details
            'vmi13':{'vn': 'vn1'}, # VMI details
            'vmi21':{'vn': 'vn2'}, # VMI details
            'vmi22':{'vn': 'vn2'}, # VMI details
            }
         
        # Input Variables 
        compute_nodes = self.orch.get_hosts()
        assert len(compute_nodes) >= 2 , "Required Minimum 2 Compute Nodes"

        vm = {'count':5, 
                'launch_mode':'distribute',
                'vm11':{'vn':['vn1'], 'vmi':['vmi11'],'node': compute_nodes[0]}, # VM Details
                'vm12':{'vn':['vn1'], 'vmi':['vmi12'],'node': compute_nodes[1]}, # VM Details
                'vm13':{'vn':['vn1'], 'vmi':['vmi13'],'node': compute_nodes[0]}, # VM Details
                'vm21':{'vn':['vn2'], 'vmi':['vmi21'],'node': compute_nodes[0]}, # VM Details
                'vm22':{'vn':['vn2'], 'vmi':['vmi22'],'node': compute_nodes[1]}, # VM Details
                }

        # Create Virtual Networks (VNs) 
        vn_fixtures = self.setup_vns(vn=vn)
        vn1_fix = vn_fixtures['vn1']
        vn2_fix = vn_fixtures['vn2']
        
        # Setting MAX Flows only on VN-1
        vn1_max_flows = 1000
        vn1_fix.set_max_flows(max_flows=vn1_max_flows)

        # Create VMIs
        vmi_fixtures = self.setup_vmis(vn_fixtures, vmi=vmi)
        
        # Create VMs
        vm_fixtures = self.setup_vms(vn_fixtures, vmi_fixtures, vm=vm, image_name='ubuntu-traffic')
        vm11_fix = vm_fixtures['vm11']
        vm12_fix = vm_fixtures['vm12']
        vm13_fix = vm_fixtures['vm13']
        vm21_fix = vm_fixtures['vm21']
        vm22_fix = vm_fixtures['vm22']
       
        # Creating ComputeNode/Vrouter Fixtures
        vm11_vrouter_fixture = ComputeNodeFixture(self.connections, vm11_fix.vm_node_ip)
        vm12_vrouter_fixture = ComputeNodeFixture(self.connections, vm12_fix.vm_node_ip)
        vm21_vrouter_fixture = ComputeNodeFixture(self.connections, vm11_fix.vm_node_ip)
        vm22_vrouter_fixture = ComputeNodeFixture(self.connections, vm12_fix.vm_node_ip)

       

        self.logger.info("Verify Traffic within VMs in VN-1")
        send_vm_fixture = vm11_fix
        recv_vm_fixture = vm12_fix
        traffic_result = self.verify_traffic(sender_vm=send_vm_fixture, receiver_vm=recv_vm_fixture,
                                        proto='udp', sport=1500, dport=10001, count=100)
        self.logger.info("Traffic Tx-Pkts: %d  Rx-Pkts: %d" % (traffic_result[0],traffic_result[1]))
        assert traffic_result[0] == traffic_result[1], "Traffic between VMs Failed"

        self.logger.info("Verify Traffic within VMs in VN-2")
        send_vm_fixture = vm21_fix
        recv_vm_fixture = vm22_fix
        traffic_result = self.verify_traffic(sender_vm=send_vm_fixture, receiver_vm=recv_vm_fixture,
                                        proto='udp', sport=1500, dport=10001, count=100)
        self.logger.info("Traffic Tx-Pkts: %d  Rx-Pkts: %d" % (traffic_result[0],traffic_result[1]))
        assert traffic_result[0] == traffic_result[1], "Traffic between VMs Failed"

        self.logger.info("Sleeping for dns/metadata flows to timeout...")
        self.waiting_for_flow_timeout()

        
        # Verify Max_flows functionality on VN level 
        #import pdb; pdb.set_trace()
        send_flow_count = self.send_traffic(
                src=str(vm11_fix.vm_ip), 
                dst=str(vm12_fix.vm_ip), 
                max_flows=vn1_max_flows, 
                vm_fix=vm11_fix
                )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm12_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %d" % (vn1_max_flows))
        #import pdb; pdb.set_trace()
        if total_flow_count == vn1_max_flows:
            self.logger.info("VN level Max Flows Provisioning is working fine")

        assert total_flow_count == vn1_max_flows, "VN level Max Flows Provisioning is not working"


        self.waiting_for_flow_timeout()
          
        # Source and Destination VMs part of the same Compute Node
        send_flow_count = self.send_traffic(
                src=str(vm11_fix.vm_ip),
                dst=str(vm13_fix.vm_ip),
                max_flows=vn1_max_flows,
                vm_fix=vm11_fix
                )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %d" % (vn1_max_flows))
        #import pdb; pdb.set_trace()
        if total_flow_count == vn1_max_flows:
            self.logger.info("VMs are the part of the same Compute - VN level Max Flows Provisioning is working fine")

        assert total_flow_count == vn1_max_flows, "VMs are the part of the same Compute - VN level Max Flows Provisioning is not working"

        self.waiting_for_flow_timeout()

        # Modifiy max flows to differnet values 
        # Setting MAX Flows on VN-1
        vn1_max_flows_new = vn1_max_flows + 500 
        vn1_fix.set_max_flows(max_flows=vn1_max_flows_new)
        send_flow_count = self.send_traffic(
                src=str(vm11_fix.vm_ip), 
                dst=str(vm12_fix.vm_ip), 
                max_flows=vn1_max_flows,
                vm_fix=vm11_fix
                )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm12_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %d" % (vn1_max_flows_new))
        if total_flow_count == vn1_max_flows_new:
            self.logger.info("VN level Max Flows Provisioning is working fine as per modified value")

        assert total_flow_count == vn1_max_flows_new, "VN level Max Flows is not working as per modified value"


        # check other VN-2 should allow all the flows 
        send_flow_count = self.send_traffic(
                src=str(vm21_fix.vm_ip), 
                dst=str(vm22_fix.vm_ip), 
                max_flows=vn1_max_flows,
                vm_fix=vm21_fix
            )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm21_fix.vm_ip),
                dest_ip=str(vm22_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn2_fix.vn_fq_name),
                metadata_ip=str(vm21_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %s" % ('Not Configured'))
        #import pdb; pdb.set_trace()
        if total_flow_count >= send_flow_count:
            self.logger.info("VN-2 is allowing all the flows")
        assert total_flow_count >= send_flow_count, "Other VN (VN-2) impacted due to VN level max flows configuration @ VN-1"

        self.waiting_for_flow_timeout()

        # Reset the VN level Max flows to default value (0)
        vn1_fix.set_max_flows(max_flows=0)
        send_flow_count = self.send_traffic(
                src=str(vm11_fix.vm_ip), 
                dst=str(vm12_fix.vm_ip), 
                max_flows=vn1_max_flows,
                vm_fix=vm11_fix
                )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm12_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %s" % ('Deleted - It should allow the flows'))

        if total_flow_count >= send_flow_count:
            self.logger.info("VN level Max Flows Provisioning is deleted properly")

        assert total_flow_count >= send_flow_count, "VN level Max Flows Provisioning is not deleted properly"





    def send_traffic(self,**kwargs):

        vm_fix = kwargs.get('vm_fix', None)
        src_ip = kwargs.get('src', None)
        dst_ip = kwargs.get('dst', None)
        max_flows = kwargs.get('max_flows', None)
        flow_count = kwargs.get('flow_count', max_flows)
        sport = kwargs.get('sport', 1500)
        dport_start = kwargs.get('dport_start', 10001)
        dport_end = kwargs.get('dport_end', dport_start+flow_count-1)
        dport_range = kwargs.get('dport_range', (dport_start, dport_end))

        params = {}
        params['ip'] = {'src': src_ip , 'dst': dst_ip}
        params['udp'] = {'sport': sport, 'dport': dport_range}
        params['count'] = 1
        params['interval'] = 0
        params['mode'] = 'L3'
        scapy_obj = ScapyTraffic(vm_fix, **params)
        scapy_obj.start()
        sleep_time = int(old_div(flow_count,25))
        self.logger.info("Started Traffic...sleeping for %d secs..." % sleep_time )
        time.sleep(sleep_time)
        flow_count = dport_range[1]-dport_range[0]+1
        return flow_count
   

    def get_total_flow_count(self,**kwargs):
        source_ip = kwargs.get('source_ip', None)
        dest_ip = kwargs.get('dest_ip', None)
        vrf_id = kwargs.get('vrf_id', None)
        metadata_ip = kwargs.get('metadata_ip', None)
        vrouter_fixture = kwargs.get('vrouter_fixture', None)

        flow_table = vrouter_fixture.get_flow_table()
        if dest_ip == None:
            (ff_count, rf_count) = vrouter_fixture.get_flow_count(
                flow_table=flow_table,
                refresh=False,
                source_ip=source_ip,
                proto='udp',
                vrf_id=vrf_id
                )
        elif source_ip == None:
            (ff_count, rf_count) = vrouter_fixture.get_flow_count(
                flow_table=flow_table,
                refresh=False,
                dest_ip=dest_ip,
                proto='udp',
                vrf_id=vrf_id
                )
        else:    
            (ff_count, rf_count) = vrouter_fixture.get_flow_count(
                flow_table=flow_table,
                refresh=False,
                source_ip=source_ip,
                dest_ip=dest_ip,
                proto='udp',
                vrf_id=vrf_id
                )
        self.logger.info("Flow Count Forward: %d  Reverse: %d" % (ff_count, rf_count))

        (ff_dns_count, rf_dns_count) = vrouter_fixture.get_flow_count(
                flow_table=flow_table,
                refresh=False,
                source_ip=source_ip,
                dest_port=53,
                proto='udp',
                vrf_id=vrf_id
            )

        self.logger.info("DNS Flow Count Forward: %d  Reverse: %d" % (ff_dns_count, rf_dns_count))

        (ff_meta_ip, rf_meta_ip) = vrouter_fixture.get_flow_count(
                flow_table=flow_table,
                refresh=False,
                dest_ip=metadata_ip
            )

        self.logger.info("Meta Data Flow Count Forward: %d  Reverse: %d" % (ff_meta_ip, rf_meta_ip))

        total_flow_count = ff_count + rf_count + ff_dns_count + rf_dns_count + ff_meta_ip + rf_meta_ip
        
        return total_flow_count

        
    @preposttest_wrapper
    def test_max_flows_vmi_level(self):

        '''
        Description: 
                Verify max_flows functionality at VMI level
        Test steps:
               1.Create a virtual network (vn1)
               2.Launch  vm11, vm12 and vm13 on vn1 network 
               3.Configure vmi level max_flows as 1000, 2000 and 3000 on vmi11, vmi12 and vmi13 respectively
               5.Verify traffic between the VMs
               6.send 2000 flows traffic from vm11 to vm13 , it should allow only 1000 flows @vmi11
               7.send 4000 flows traffic from vm12 to vm13, it should all only 2000 flows @vmi12
               8.Modify the max_flows value as 1500 @ vmi11
               9.verify sending traffic between vm11 and vm13, now it should all 1500 flows  
               10.Delete the max_flows @ all VMIs ( by setting the value as 0 )
               11.send traffics across vm11, vm12 and vm13 , it should allow all the traffic
        Pass criteria: 
               Number of flows should be created as per max_flows configured at VMI level.
               After modification, it should work as per modified value
               After deleting max_flows configuration, it should allow all the flows.
        Maintainer : mmohan@juniper.net
        '''

        vn = {'count':1,            # VN coun
            'vn1':{'subnet':'21.0.0.0/24'},
            }
        vmi = {'count':3, # VMI Count
            'vmi11':{'vn': 'vn1'}, # VMI details
            'vmi12':{'vn': 'vn1'}, # VMI details
            'vmi13':{'vn': 'vn1'}, # VMI details
            }
         
        # Input Variables 
        compute_nodes = self.orch.get_hosts()
        assert len(compute_nodes) >= 2 , "Required Minimum 2 Compute Nodes"

        vm = {'count':3, 
                'launch_mode':'distribute',
                'vm11':{'vn':['vn1'], 'vmi':['vmi11'],'node': compute_nodes[0]}, # VM Details
                'vm12':{'vn':['vn1'], 'vmi':['vmi12'],'node': compute_nodes[1]}, # VM Details
                'vm13':{'vn':['vn1'], 'vmi':['vmi13'],'node': compute_nodes[0]}, # VM Details
                }

        # Create Virtual Networks (VNs) 
        vn_fixtures = self.setup_vns(vn=vn)
        vn1_fix = vn_fixtures['vn1']

        #import pdb; pdb.set_trace()
        # Create VMIs
        vmi_fixtures = self.setup_vmis(vn_fixtures, vmi=vmi)
        vmi11_fix = vmi_fixtures['vmi11']
        vmi12_fix = vmi_fixtures['vmi12']
        vmi13_fix = vmi_fixtures['vmi13']

        #import pdb; pdb.set_trace()
        # Setting MAX Flows only on VMI 11
        vmi11_max_flows = 100
        vmi11_fix.set_max_flows(max_flows=vmi11_max_flows)
        vmi12_max_flows = 200
        vmi12_fix.set_max_flows(max_flows=vmi12_max_flows)
        vmi13_max_flows = 300
        vmi13_fix.set_max_flows(max_flows=vmi13_max_flows)
        
        # Create VMs
        vm_fixtures = self.setup_vms(vn_fixtures, vmi_fixtures, vm=vm, image_name='ubuntu-traffic')
        vm11_fix = vm_fixtures['vm11']
        vm12_fix = vm_fixtures['vm12']
        vm13_fix = vm_fixtures['vm13']
       
        # Creating ComputeNode/Vrouter Fixtures
        vm11_vrouter_fixture = ComputeNodeFixture(self.connections, vm11_fix.vm_node_ip)
        vm12_vrouter_fixture = ComputeNodeFixture(self.connections, vm12_fix.vm_node_ip)
        vm13_vrouter_fixture = ComputeNodeFixture(self.connections, vm13_fix.vm_node_ip)
       

        self.logger.info("Verify Traffic within VMs in VN-1")
        send_vm_fixture = vm11_fix
        recv_vm_fixture = vm13_fix
        traffic_result = self.verify_traffic(sender_vm=send_vm_fixture, receiver_vm=recv_vm_fixture,
                                        proto='udp', sport=1500, dport=10001, count=100)
        self.logger.info("Traffic Tx-Pkts: %d  Rx-Pkts: %d" % (traffic_result[0],traffic_result[1]))
        assert traffic_result[0] == traffic_result[1], "Basic Traffic Validation Failed between VMs ( VN-1)"

        send_vm_fixture = vm12_fix
        recv_vm_fixture = vm13_fix
        traffic_result = self.verify_traffic(sender_vm=send_vm_fixture, receiver_vm=recv_vm_fixture,
                                        proto='udp', sport=1500, dport=10001, count=100)
        self.logger.info("Traffic Tx-Pkts: %d  Rx-Pkts: %d" % (traffic_result[0],traffic_result[1]))
        assert traffic_result[0] == traffic_result[1], "Basic Traffic Validation Failed between VMs ( VN-1)"

        #import pdb; pdb.set_trace()
        vm11_inspect = self.agent_inspect[vm11_fix.vm_node_ip]
        vm12_inspect = self.agent_inspect[vm12_fix.vm_node_ip]
        vm13_inspect = self.agent_inspect[vm13_fix.vm_node_ip]
        

        vm11_tap_intf = vm11_inspect.get_vna_tap_interface_by_ip(vm11_fix.vm_ip)

        self.logger.info("drop_new_flows flag values @ vifs before sending traffics...")
        vm11_drop_new_flows = vm11_inspect.get_vna_tap_interface_by_ip(vm11_fix.vm_ip)[0]['drop_new_flows']
        self.logger.info("drop_new_flows flag value @ vm11: %s " % (vm11_drop_new_flows))
        vm12_drop_new_flows = vm12_inspect.get_vna_tap_interface_by_ip(vm12_fix.vm_ip)[0]['drop_new_flows']
        self.logger.info("drop_new_flows flag value @ vm12: %s " % (vm12_drop_new_flows))
        vm13_drop_new_flows = vm13_inspect.get_vna_tap_interface_by_ip(vm13_fix.vm_ip)[0]['drop_new_flows']
        self.logger.info("drop_new_flows flag value @ vm13: %s " % (vm13_drop_new_flows))
        
        if vm11_drop_new_flows != 'false' and vm11_drop_new_flows != 'false' and vm13_drop_new_flows != 'false' :
            assert False, "drop_new_flows flag is set even before sending traffics..."

            
        self.logger.info("Sleeping for dns/meta flows timeout seconds...")
        self.waiting_for_flow_timeout()

        
        # Verify Max_flows functionality on VMI level 
        #import pdb; pdb.set_trace()
        send_flow_count_vm11 = self.send_traffic(
                src=str(vm11_fix.vm_ip), 
                dst=str(vm13_fix.vm_ip), 
                max_flows=vmi11_max_flows, 
                vm_fix=vm11_fix
                )
        total_flow_count_vm11 = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        send_flow_count_vm12 = self.send_traffic(
                src=str(vm12_fix.vm_ip),
                dst=str(vm13_fix.vm_ip),
                max_flows=vmi12_max_flows,
                vm_fix=vm12_fix
                )

        total_flow_count_vm12 = self.get_total_flow_count(
                source_ip=str(vm12_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm12_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm12_fix.get_local_ip()),
                vrouter_fixture=vm12_vrouter_fixture
            )

        send_flow_count_vm13 = self.send_traffic(
                src=str(vm13_fix.vm_ip),
                dst=str(vm11_fix.vm_ip),
                max_flows=vmi13_max_flows,
                vm_fix=vm13_fix
                )

        total_flow_count_vm13 = self.get_total_flow_count(
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm13_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm13_fix.get_local_ip()),
                vrouter_fixture=vm13_vrouter_fixture
            )
        
        
        self.logger.info("drop_new_flows flag values @ vifs after max_flows exceeds..")
        vm11_drop_new_flows = vm11_inspect.get_vna_tap_interface_by_ip(vm11_fix.vm_ip)[0]['drop_new_flows']
        self.logger.info("drop_new_flows flag value @ vm11: %s " % (vm11_drop_new_flows))
        vm12_drop_new_flows = vm12_inspect.get_vna_tap_interface_by_ip(vm12_fix.vm_ip)[0]['drop_new_flows']
        self.logger.info("drop_new_flows flag value @ vm12: %s " % (vm12_drop_new_flows))
        vm13_drop_new_flows = vm13_inspect.get_vna_tap_interface_by_ip(vm13_fix.vm_ip)[0]['drop_new_flows']
        self.logger.info("drop_new_flows flag value @ vm13: %s " % (vm13_drop_new_flows))
        
        if vm11_drop_new_flows != 'true' and vm11_drop_new_flows != 'true' and vm13_drop_new_flows != 'true' :
            assert False, "drop_new_flows flag is NOT set even after max_flows execeeded.."


        self.logger.info("Total Obtained Flow Count @ vm11: %d"% (total_flow_count_vm11))
        self.logger.info("Total Expected Flow Count @ vm11: %d" % (vmi11_max_flows))

        self.logger.info("Total Obtained Flow Count @ vm12: %d"% (total_flow_count_vm12))
        self.logger.info("Total Expected Flow Count @ vm12: %d" % (vmi12_max_flows))

        self.logger.info("Total Obtained Flow Count @ vm13: %d"% (total_flow_count_vm13))
        self.logger.info("Total Expected Flow Count @ vm13: %d" % (vmi13_max_flows))

        #import pdb; pdb.set_trace()

        if total_flow_count_vm11 == vmi11_max_flows:
            self.logger.info("VMI level (vm11) Max Flows Provisioning is working fine")

        assert total_flow_count_vm11 == vmi11_max_flows, "VMI (vm11) level Provisioning is not working"

        if total_flow_count_vm12 == vmi12_max_flows:
            self.logger.info("VMI level (vm12) Max Flows Provisioning is working fine")

        assert total_flow_count_vm12 == vmi12_max_flows, "VMI (vm12) level Provisioning is not working"

        vmi13_max_flows_low = vmi13_max_flows - 10
        vmi13_max_flows_high = vmi13_max_flows + 10

        if total_flow_count_vm13 >=  vmi13_max_flows_low and total_flow_count_vm13 <= vmi13_max_flows_high:
            self.logger.info("VMI level (vm13) Max Flows Provisioning is working fine")
        else:
            assert False, "VMI (vm13) level Provisioning is not working"
            
        self.waiting_for_flow_timeout()

        self.logger.info("drop_new_flows flag values @ vifs after flows timedout...")
        vm11_drop_new_flows = vm11_inspect.get_vna_tap_interface_by_ip(vm11_fix.vm_ip)[0]['drop_new_flows']
        self.logger.info("drop_new_flows flag value @ vm11: %s " % (vm11_drop_new_flows))
        vm12_drop_new_flows = vm12_inspect.get_vna_tap_interface_by_ip(vm12_fix.vm_ip)[0]['drop_new_flows']
        self.logger.info("drop_new_flows flag value @ vm12: %s " % (vm12_drop_new_flows))
        vm13_drop_new_flows = vm13_inspect.get_vna_tap_interface_by_ip(vm13_fix.vm_ip)[0]['drop_new_flows']
        self.logger.info("drop_new_flows flag value @ vm13: %s " % (vm13_drop_new_flows))

        if vm11_drop_new_flows != 'false' and vm11_drop_new_flows != 'false' and vm13_drop_new_flows != 'false' :
            assert False, "drop_new_flows flag is set even after flows timedout..."
        

        # Modifiy max flows to differnet values 
        # Setting MAX Flows on VMI 11
        vmi11_max_flows_new = vmi11_max_flows + 50
        vmi11_fix.set_max_flows(max_flows=vmi11_max_flows_new)

        send_flow_count_vm11 = self.send_traffic(
                src=str(vm11_fix.vm_ip),
                dst=str(vm13_fix.vm_ip),
                max_flows=vmi11_max_flows,
                vm_fix=vm11_fix
                )
        total_flow_count_vm11 = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        send_flow_count_vm12 = self.send_traffic(
                src=str(vm12_fix.vm_ip),
                dst=str(vm13_fix.vm_ip),
                max_flows=vmi12_max_flows,
                vm_fix=vm12_fix
                )
        total_flow_count_vm12 = self.get_total_flow_count(
                source_ip=str(vm12_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm12_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm12_fix.get_local_ip()),
                vrouter_fixture=vm12_vrouter_fixture
            )

        total_flow_count_vm13 = self.get_total_flow_count(
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm13_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm13_fix.get_local_ip()),
                vrouter_fixture=vm13_vrouter_fixture
            )


        self.logger.info("Total Obtained Flow Count @ vm11: %d"% (total_flow_count_vm11))
        self.logger.info("Total Expected Flow Count @ vm11: %d" % (vmi11_max_flows_new))

        self.logger.info("Total Obtained Flow Count @ vm12: %d"% (total_flow_count_vm12))
        self.logger.info("Total Expected Flow Count @ vm12: %d" % (vmi12_max_flows))

        self.logger.info("Total Obtained Flow Count @ vm13: %d"% (total_flow_count_vm13))
        self.logger.info("Total Expected Flow Count @ vm13: %d" % (vmi13_max_flows))

        #import pdb; pdb.set_trace()
        if total_flow_count_vm11 == vmi11_max_flows_new:
            self.logger.info("VMI(vm11) level Max Flows Provisioning is working fine as per modified value")

        assert total_flow_count_vm11 == vmi11_max_flows_new, "VMI(vm11) level Max Flows is not working as per modified value"

        if total_flow_count_vm12 == vmi12_max_flows:
            self.logger.info("VMI level (vm12) Max Flows Provisioning is working fine")

        assert total_flow_count_vm12 == vmi12_max_flows, "VMI (vm12) level Provisioning is not working"

        vmi13_max_flows_low = vmi13_max_flows - 10
        vmi13_max_flows_high = vmi13_max_flows + 10
        if total_flow_count_vm13 >=  vmi13_max_flows_low and total_flow_count_vm13 <= vmi13_max_flows_high :
            self.logger.info("VMI level (vm13) Max Flows Provisioning is working fine")
        else:
            assert False, "VMI (vm13) level Provisioning is not working"

        self.logger.info("Sleeping for dns/meta flows timeout seconds...")
        self.waiting_for_flow_timeout()

        vmi11_fix.set_max_flows(max_flows=vmi11_max_flows)
        # Verify Max_flows functionality on VMI level
        #import pdb; pdb.set_trace()
        send_flow_count_vm11 = self.send_traffic(
                src=str(vm11_fix.vm_ip),
                dst=str(vm13_fix.vm_ip),
                max_flows=vmi11_max_flows,
                vm_fix=vm11_fix
                )
        total_flow_count_vm11 = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        send_flow_count_vm12 = self.send_traffic(
                src=str(vm12_fix.vm_ip),
                dst=str(vm13_fix.vm_ip),
                max_flows=vmi12_max_flows,
                vm_fix=vm12_fix
                )

        total_flow_count_vm12 = self.get_total_flow_count(
                source_ip=str(vm12_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm12_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm12_fix.get_local_ip()),
                vrouter_fixture=vm12_vrouter_fixture
            )

        total_flow_count_vm13 = self.get_total_flow_count(
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm13_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm13_fix.get_local_ip()),
                vrouter_fixture=vm13_vrouter_fixture
            )


        self.logger.info("Total Obtained Flow Count @ vm11: %d"% (total_flow_count_vm11))
        self.logger.info("Total Expected Flow Count @ vm11: %d" % (vmi11_max_flows))

        self.logger.info("Total Obtained Flow Count @ vm12: %d"% (total_flow_count_vm12))
        self.logger.info("Total Expected Flow Count @ vm12: %d" % (vmi12_max_flows))

        self.logger.info("Total Obtained Flow Count @ vm13: %d"% (total_flow_count_vm13))
        self.logger.info("Total Expected Flow Count @ vm13: %d" % (vmi13_max_flows))

        #import pdb; pdb.set_trace()

        if total_flow_count_vm11 == vmi11_max_flows:
            self.logger.info("VMI level (vm11) Max Flows Provisioning is working fine")

        assert total_flow_count_vm11 == vmi11_max_flows, "VMI (vm11) level Provisioning is not working"

        if total_flow_count_vm12 == vmi12_max_flows:
            self.logger.info("VMI level (vm12) Max Flows Provisioning is working fine")

        assert total_flow_count_vm12 == vmi12_max_flows, "VMI (vm12) level Provisioning is not working"

        vmi13_max_flows_low = vmi13_max_flows - 10
        vmi13_max_flows_high = vmi13_max_flows + 10

        if total_flow_count_vm13 >=  vmi13_max_flows_low and total_flow_count_vm13 <= vmi13_max_flows_high:
            self.logger.info("VMI level (vm13) Max Flows Provisioning is working fine")
        else:
            assert False, "VMI (vm13) level Provisioning is not working"

        self.waiting_for_flow_timeout()
        time.sleep(10)

        # Reset the VN level Max flows to default value (0)
        vmi11_fix.set_max_flows(max_flows=0)
        vmi12_fix.set_max_flows(max_flows=0)
        vmi13_fix.set_max_flows(max_flows=0)

        send_flow_count_vm11 = self.send_traffic(
                src=str(vm11_fix.vm_ip),
                dst=str(vm13_fix.vm_ip),
                max_flows=vmi11_max_flows,
                vm_fix=vm11_fix
                )
        time.sleep(10)
        total_flow_count_vm11 = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        send_flow_count_vm12 = self.send_traffic(
                src=str(vm12_fix.vm_ip),
                dst=str(vm13_fix.vm_ip),
                max_flows=vmi12_max_flows,
                vm_fix=vm12_fix
                )
        total_flow_count_vm12 = self.get_total_flow_count(
                source_ip=str(vm12_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm12_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm12_fix.get_local_ip()),
                vrouter_fixture=vm12_vrouter_fixture
            )

        send_flow_count_vm13 = send_flow_count_vm11+send_flow_count_vm12
        total_flow_count_vm13 = self.get_total_flow_count(
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm13_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm13_fix.get_local_ip()),
                vrouter_fixture=vm13_vrouter_fixture
            )


        self.logger.info("Total Obtained Flow Count @ vm11: %d"% (total_flow_count_vm11))
        self.logger.info("Total Expected Flow Count @ vm11: %d" % (send_flow_count_vm11*2))

        self.logger.info("Total Obtained Flow Count @ vm12: %d"% (total_flow_count_vm12))
        self.logger.info("Total Expected Flow Count @ vm12: %d" % (send_flow_count_vm12*2))

        self.logger.info("Total Obtained Flow Count @ vm13: %d"% (total_flow_count_vm13))
        self.logger.info("Total Expected Flow Count @ vm13: %d" % (send_flow_count_vm13*2))
               #import pdb; pdb.set_trace()
        if total_flow_count_vm11 >= send_flow_count_vm11*2:
            self.logger.info("VMI(vm11) level Max Flows Provisioning is deleted properly")
        assert total_flow_count_vm11 >= send_flow_count_vm11*2, "VMI (vm11) level Provisioning is not deleted properly"

        if total_flow_count_vm12 >= send_flow_count_vm12*2:
            self.logger.info("VMI(vm12) level Max Flows Provisioning is deleted properly")
        assert total_flow_count_vm12 >= send_flow_count_vm12*2, "VMI (vm12) level Provisioning is not deleted properly"

        if total_flow_count_vm13 >= send_flow_count_vm13*2:
            self.logger.info("VMI(vm13) level Max Flows Provisioning is deleted properly")
        assert total_flow_count_vm13 >= send_flow_count_vm13*2, "VMI (vm13) level Provisioning is not deleted properly"



    @preposttest_wrapper
    def test_max_flows_precedence(self):

        '''
        Description: 
                Verify precedence order between VMI level and VN level configuration
        Test steps:
               1.Create a virtaul network (vn1)
               2.Launch  vm11, vm12 and vm13 on vn1 network
               3.configure max_flows as 400 @ VN level (vn1)
               4.configure max_flows as 1000 and 2000 on VMIs ( vmi11 and vmi13) respectively
               5.send traffic between vm11 and vm12 and it should allow only 1000 flows 
               6.send traffic between vm12 and vm13 , it should all only 400 flows  
               7.Delete VMI level configuration @ vmi11 (max_flows=0)
               8.Now send traffic between vm11 and vm12 and it should allow only 400 flows
        Pass criteria: 
               VMI level is preferred when max_flows configured @ both VMI and VN level 
               After removing configration from VMI level, it should use VN level value
        Maintainer : mmohan@juniper.net
        '''
        vn = {'count':1,            # VN coun
            'vn1':{'subnet':'21.0.0.0/24'},
            }
        vmi = {'count':3, # VMI Count
            'vmi11':{'vn': 'vn1'}, # VMI details
            'vmi12':{'vn': 'vn1'}, # VMI details
            'vmi13':{'vn': 'vn1'}, # VMI details
            }
         
        # Input Variables 
        compute_nodes = self.orch.get_hosts()
        assert len(compute_nodes) >= 2 , "Required Minimum 2 Compute Nodes"

        vm = {'count':3, 
                'launch_mode':'distribute',
                'vm11':{'vn':['vn1'], 'vmi':['vmi11'],'node': compute_nodes[0]}, # VM Details
                'vm12':{'vn':['vn1'], 'vmi':['vmi12'],'node': compute_nodes[1]}, # VM Details
                'vm13':{'vn':['vn1'], 'vmi':['vmi13'],'node': compute_nodes[0]}, # VM Details
                }

        # Create Virtual Networks (VNs) 
        vn_fixtures = self.setup_vns(vn=vn)
        vn1_fix = vn_fixtures['vn1']

        #import pdb; pdb.set_trace()
        # Create VMIs
        vmi_fixtures = self.setup_vmis(vn_fixtures, vmi=vmi)
        vmi11_fix = vmi_fixtures['vmi11']
        vmi12_fix = vmi_fixtures['vmi12']
        vmi13_fix = vmi_fixtures['vmi13']

        #import pdb; pdb.set_trace()
        # Setting MAX Flows only on VMI 11
        vn1_max_flows = 400
        vmi11_max_flows = 1000
        vmi13_max_flows = 2000
        vn1_fix.set_max_flows(max_flows=vn1_max_flows)
        vmi11_fix.set_max_flows(max_flows=vmi11_max_flows)
        vmi13_fix.set_max_flows(max_flows=vmi13_max_flows)
        
        # Create VMs
        vm_fixtures = self.setup_vms(vn_fixtures, vmi_fixtures, vm=vm, image_name='ubuntu-traffic')
        vm11_fix = vm_fixtures['vm11']
        vm12_fix = vm_fixtures['vm12']
        vm13_fix = vm_fixtures['vm13']
       
        # Creating ComputeNode/Vrouter Fixtures
        vm11_vrouter_fixture = ComputeNodeFixture(self.connections, vm11_fix.vm_node_ip)
        vm12_vrouter_fixture = ComputeNodeFixture(self.connections, vm12_fix.vm_node_ip)
       

        self.logger.info("Verify Traffic within VMs in VN-1")
        send_vm_fixture = vm11_fix
        recv_vm_fixture = vm13_fix
        traffic_result = self.verify_traffic(sender_vm=send_vm_fixture, receiver_vm=recv_vm_fixture,
                                        proto='udp', sport=1500, dport=10001, count=100)
        self.logger.info("Traffic Tx-Pkts: %d  Rx-Pkts: %d" % (traffic_result[0],traffic_result[1]))
        assert traffic_result[0] == traffic_result[1], "Basic Traffic Validation Failed between VMs ( VN-1)"

        self.logger.info("Sleeping for dns/meta flows timeout seconds...")
        self.waiting_for_flow_timeout()

        
        # Verify Max_flows functionality on VMI level 
        #import pdb; pdb.set_trace()
        send_flow_count = self.send_traffic(
                src=str(vm11_fix.vm_ip), 
                dst=str(vm13_fix.vm_ip), 
                max_flows=vmi11_max_flows, 
                vm_fix=vm11_fix
                )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %d" % (vmi11_max_flows))
        #import pdb; pdb.set_trace()
        if total_flow_count == vmi11_max_flows:
            self.logger.info("VMI level Max Flows Provisioning is working fine")

        assert total_flow_count == vmi11_max_flows, "VMI level Max Flows Provisioning is not working"
       
        send_flow_count = self.send_traffic(
                src=str(vm12_fix.vm_ip), 
                dst=str(vm13_fix.vm_ip), 
                max_flows=vmi11_max_flows,
                vm_fix=vm12_fix
            )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm12_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm12_fix.get_local_ip()),
                vrouter_fixture=vm12_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %s" % ('Not VMI level Configured - Should use VN level value'))
        self.logger.info("Total Expected Flow Count: %d" % (vn1_max_flows))
        # import pdb; pdb.set_trace()
        if total_flow_count == vn1_max_flows:
            self.logger.info("No VMI level configuration - VN level max flows is used correctly")
        assert total_flow_count == vn1_max_flows, "Other VMI ( VMI 12) are not taking VN level value"

        self.waiting_for_flow_timeout()

        # Reset the VN level Max flows to default value (0)
        vmi11_fix.set_max_flows(max_flows=0)
        send_flow_count = self.send_traffic(
                src=str(vm11_fix.vm_ip), 
                dst=str(vm13_fix.vm_ip), 
                max_flows=vmi11_max_flows,
                vm_fix=vm11_fix
                )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %s" % ('VMI level Deleted - Should use VN level'))
        self.logger.info("Total Expected Flow Count: %d" % (vn1_max_flows))

        if total_flow_count == vn1_max_flows:
            self.logger.info("VMI level deleted properly and it uses VN level Value")

        assert total_flow_count == vn1_max_flows, "VMI level Max Flows Provisioning is not deleted properly"






    @preposttest_wrapper
    def test_max_flows_precedence_with_max_vm_flows(self):

        '''
        Description: 
                Verify precedence order between VMI level and VN level configuration
        Test steps:
               1.Create a virtaul network (vn1)
               2.Launch  vm11, vm12 and vm13 on vn1 network
               3.configure max_flows as 400 @ VN level (vn1)
               4.configure max_flows as 1000 and 2000 on VMIs ( vmi11 and vmi13) respectively
               5.configure max_vm_flows as 0.02 @ vm11 (vm level) 
               6.send traffic between vm11 and vm12 and it should allow only 1000 flows 
               7.send traffic between vm12 and vm13 , it should all only 400 flows  
               8.Delete VMI level configuration @ vmi11 (max_flows=0)
               9.Now send traffic between vm11 and vm12
               10.It should allow only 400 flows, as per VN level configuration
               11.Delete VN level configration @ vn1 (max_flows=0)
               12.Now send traffic between vm11 and vm12
               13.It should allow only ~120 flows, as per max_vm_flows configuration
        Pass criteria: 
               Precedence order:  VMI > VN > max_vm_flows 
               After removing configration from VMI level, it should use VN level value
               After removing VN level, it should use VM level ( max_vm_flows)
        Maintainer : mmohan@juniper.net
        '''
        vn = {'count':1,            # VN coun
            'vn1':{'subnet':'21.0.0.0/24'},
            }
        vmi = {'count':3, # VMI Count
            'vmi11':{'vn': 'vn1'}, # VMI details
            'vmi12':{'vn': 'vn1'}, # VMI details
            'vmi13':{'vn': 'vn1'}, # VMI details
            }
         
        # Input Variables 
        compute_nodes = self.orch.get_hosts()
        assert len(compute_nodes) >= 2 , "Required Minimum 2 Compute Nodes"

        vm = {'count':3, 
                'launch_mode':'distribute',
                'vm11':{'vn':['vn1'], 'vmi':['vmi11'],'node': compute_nodes[0]}, # VM Details
                'vm12':{'vn':['vn1'], 'vmi':['vmi12'],'node': compute_nodes[1]}, # VM Details
                'vm13':{'vn':['vn1'], 'vmi':['vmi13'],'node': compute_nodes[0]}, # VM Details
                }

        # Create Virtual Networks (VNs) 
        vn_fixtures = self.setup_vns(vn=vn)
        vn1_fix = vn_fixtures['vn1']

        #import pdb; pdb.set_trace()
        # Create VMIs
        vmi_fixtures = self.setup_vmis(vn_fixtures, vmi=vmi)
        vmi11_fix = vmi_fixtures['vmi11']
        vmi12_fix = vmi_fixtures['vmi12']
        vmi13_fix = vmi_fixtures['vmi13']

        #import pdb; pdb.set_trace()
        # Setting MAX Flows only on VMI 11
        vn1_max_flows = 400
        vmi11_max_flows = 1000
        vmi13_max_flows = 2000
        vn1_fix.set_max_flows(max_flows=vn1_max_flows)
        vmi11_fix.set_max_flows(max_flows=vmi11_max_flows)
        vmi13_fix.set_max_flows(max_flows=vmi13_max_flows)
       

        # Create VMs
        vm_fixtures = self.setup_vms(vn_fixtures, vmi_fixtures, vm=vm, image_name='ubuntu-traffic')
        vm11_fix = vm_fixtures['vm11']
        vm12_fix = vm_fixtures['vm12']
        vm13_fix = vm_fixtures['vm13']
       
        # Creating ComputeNode/Vrouter Fixtures
        vm11_vrouter_fixture = ComputeNodeFixture(self.connections, vm11_fix.vm_node_ip)
        vm12_vrouter_fixture = ComputeNodeFixture(self.connections, vm12_fix.vm_node_ip)

        vm11_vrouter_fixture.set_per_vm_flow_limit(0.02) 
        #import pdb; pdb.set_trace()
       
        self.logger.info("Sleeping for 360 secs...")
        time.sleep(360)
        self.logger.info("Sleeping for 360 secs...Completed")

        self.addCleanup(self.cleanup_test_max_vm_flows_vrouter_config, [vm11_vrouter_fixture])

        self.logger.info("Verify Traffic within VMs in VN-1")

        send_vm_fixture = vm11_fix
        recv_vm_fixture = vm13_fix
        traffic_result = self.verify_traffic(sender_vm=send_vm_fixture, receiver_vm=recv_vm_fixture,
                                        proto='udp', sport=1500, dport=10001, count=100)
        self.logger.info("Traffic Tx-Pkts: %d  Rx-Pkts: %d" % (traffic_result[0],traffic_result[1]))
        assert traffic_result[0] == traffic_result[1], "Basic Traffic Validation Failed between VMs ( VN-1)"

        self.logger.info("Sleeping for dns/meta flows timeout seconds...")
        self.waiting_for_flow_timeout()

        
        # Verify Max_flows functionality on VMI level 
        #import pdb; pdb.set_trace()
        send_flow_count = self.send_traffic(
                src=str(vm11_fix.vm_ip), 
                dst=str(vm13_fix.vm_ip), 
                max_flows=vmi11_max_flows, 
                vm_fix=vm11_fix
                )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %d" % (vmi11_max_flows))
        #import pdb; pdb.set_trace()
        if total_flow_count == vmi11_max_flows:
            self.logger.info("VMI level Max Flows Provisioning is working fine")

        assert total_flow_count == vmi11_max_flows, "VMI level Max Flows Provisioning is not working"
       
        send_flow_count = self.send_traffic(
                src=str(vm12_fix.vm_ip), 
                dst=str(vm13_fix.vm_ip), 
                max_flows=vmi11_max_flows,
                vm_fix=vm12_fix
            )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm12_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm12_fix.get_local_ip()),
                vrouter_fixture=vm12_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %s" % ('Not VMI level Configured - Should use VN level value'))
        self.logger.info("Total Expected Flow Count: %d" % (vn1_max_flows))
        # import pdb; pdb.set_trace()
        if total_flow_count == vn1_max_flows:
            self.logger.info("No VMI level configuration - VN level max flows is used correctly")
        assert total_flow_count == vn1_max_flows, "Other VMI ( VMI 12) are not taking VN level value"

        self.waiting_for_flow_timeout()

        # Reset the VN level Max flows to default value (0)
        vmi11_fix.set_max_flows(max_flows=0)
        send_flow_count = self.send_traffic(
                src=str(vm11_fix.vm_ip), 
                dst=str(vm13_fix.vm_ip), 
                max_flows=vmi11_max_flows,
                vm_fix=vm11_fix
                )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %s" % ('VMI level Deleted - Should use VN level'))
        self.logger.info("Total Expected Flow Count: %d" % (vn1_max_flows))

        if total_flow_count == vn1_max_flows:
            self.logger.info("VMI level deleted properly and it uses VN level Value")

        assert total_flow_count == vn1_max_flows, "VMI level Max Flows Provisioning is not deleted properly"

        vn1_fix.set_max_flows(max_flows=0)
        self.waiting_for_flow_timeout()

        send_flow_count = self.send_traffic(
                src=str(vm11_fix.vm_ip),
                dst=str(vm13_fix.vm_ip),
                max_flows=vmi11_max_flows,
                vm_fix=vm11_fix
                )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %s" % ('VMI level Deleted - Should use VN level'))
        self.logger.info("Total Expected Flow Count: ~120 flows(0.02*512K)")

        if total_flow_count < 130 and total_flow_count > 100:
            self.logger.info("VN level is deleted properly and it uses max_vm_flows Value")
        else:
            assert False, "VN level Max Flows Provisioning is not deleted properly, it should use max_vm_flows level value"


    @preposttest_wrapper
    def test_max_flows_vn_level_already_has_some_vmis(self):

        '''
        Description: 
                Verify max_flows functionality at VN which already has some VMIs
        Test steps:
               1.Create a virtaul network (vn1)
               2.Launch  vm11, vm12  vn1 network
               3.configure max_flows as 1000 @ vn1
               4.send traffic between vm11 and vm12 and it should allow only 1000 flows 
               4.Launch 1 more VM(vm13) on vn1 network 
               5.Verify traffic between the vm13 and vm12, it shouls allow only 1000 flows
        Pass criteria: 
               Number of flows should be created as per max_flows configured at VN level.
        Maintainer : mmohan@juniper.net
        '''

        vn = {'count':1,            # VN coun
            'vn1':{'subnet':'21.0.0.0/24'},
            }
        vmi = {'count':2, # VMI Count
            'vmi11':{'vn': 'vn1'}, # VMI details
            'vmi12':{'vn': 'vn1'}, # VMI details
            }
        vmi_3 = {'count':1, # VMI Count
            'vmi13':{'vn': 'vn1'}, # VMI details
            }
         
        # Input Variables 
        compute_nodes = self.orch.get_hosts()
        assert len(compute_nodes) >= 2 , "Required Minimum 2 Compute Nodes"

        vm = {'count':2, 
                'launch_mode':'distribute',
                'vm11':{'vn':['vn1'], 'vmi':['vmi11'],'node': compute_nodes[0]}, # VM Details
                'vm12':{'vn':['vn1'], 'vmi':['vmi12'],'node': compute_nodes[1]}, # VM Details
                }
        vm_3 = {'count':1, 
                'launch_mode':'distribute',
                'vm13':{'vn':['vn1'], 'vmi':['vmi13'],'node': compute_nodes[0]}, # VM Details
                }

        # Create Virtual Networks (VNs) 
        vn_fixtures = self.setup_vns(vn=vn)
        vn1_fix = vn_fixtures['vn1']

        # Create VMIs
        vmi_fixtures = self.setup_vmis(vn_fixtures, vmi=vmi)
        
        # Create VMs
        vm_fixtures = self.setup_vms(vn_fixtures, vmi_fixtures, vm=vm, image_name='ubuntu-traffic')
        vm11_fix = vm_fixtures['vm11']
        vm12_fix = vm_fixtures['vm12']
       
        # Creating ComputeNode/Vrouter Fixtures
        vm11_vrouter_fixture = ComputeNodeFixture(self.connections, vm11_fix.vm_node_ip)
        vm12_vrouter_fixture = ComputeNodeFixture(self.connections, vm12_fix.vm_node_ip)

        self.logger.info("Verify Traffic within VMs in VN-1")
        send_vm_fixture = vm11_fix
        recv_vm_fixture = vm12_fix
        traffic_result = self.verify_traffic(sender_vm=send_vm_fixture, receiver_vm=recv_vm_fixture,
                                        proto='udp', sport=1500, dport=10001, count=100)
        self.logger.info("Traffic Tx-Pkts: %d  Rx-Pkts: %d" % (traffic_result[0],traffic_result[1]))
        assert traffic_result[0] == traffic_result[1], "Traffic between VMs Failed"

        # Setting MAX Flows only on VN-1
        vn1_max_flows = 1000
        vn1_fix.set_max_flows(max_flows=vn1_max_flows)

        self.logger.info("Sleeping for dns/metadata flows to timeout 180 seconds...")
        self.waiting_for_flow_timeout()

        
        # Verify Max_flows functionality on VN level 
        #import pdb; pdb.set_trace()
        send_flow_count = self.send_traffic(
                src=str(vm11_fix.vm_ip), 
                dst=str(vm12_fix.vm_ip), 
                max_flows=vn1_max_flows, 
                vm_fix=vm11_fix
                )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm12_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %d" % (vn1_max_flows))
        #import pdb; pdb.set_trace()
        if total_flow_count == vn1_max_flows:
            self.logger.info("VN level Max Flows Provisioning is working fine")

        assert total_flow_count == vn1_max_flows, "VN level Max Flows Provisioning is not working"

        self.waiting_for_flow_timeout()

          
        self.logger.info("Creating 1 more VM on the same VN....")
        # Create VMIs
        vmi_fixtures_3 = self.setup_vmis(vn_fixtures, vmi=vmi_3)

        # Create VMs
        vm_fixtures_3 = self.setup_vms(vn_fixtures, vmi_fixtures_3, vm=vm_3, image_name='ubuntu-traffic')
        vm13_fix = vm_fixtures_3['vm13']

        vm13_vrouter_fixture = ComputeNodeFixture(self.connections, vm13_fix.vm_node_ip)

        self.logger.info("Sleeping for dns/metadata flows to timeout 180 seconds...")
        self.waiting_for_flow_timeout()

# Verify Max_flows functionality on VN level
        #import pdb; pdb.set_trace()
        send_flow_count = self.send_traffic(
                src=str(vm13_fix.vm_ip),
                dst=str(vm12_fix.vm_ip),
                max_flows=vn1_max_flows,
                vm_fix=vm13_fix
                )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm13_fix.vm_ip),
                dest_ip=str(vm12_fix.vm_ip),
                vrf_id=vm13_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm13_fix.get_local_ip()),
                vrouter_fixture=vm13_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %d" % (vn1_max_flows))
        #import pdb; pdb.set_trace()
        if total_flow_count == vn1_max_flows:
            self.logger.info("VN level Max Flows Provisioning is working fine")

        assert total_flow_count == vn1_max_flows, "VN level Max Flows Provisioning is not working"


    @preposttest_wrapper
    def test_drop_new_flows_flag(self):

        '''
        Description: 
               Verify Drop new flows flag is set once flow count value exceeds max_flows
               and flag is set as false after flow count value reduces below 90% max_flows
        Test steps:
               1.Create a virtaul network (vn1)
               2.Launch VMs( vm11, vm12) on vn1 network
               3.configure max_flows as 1000 @ VMI (vmi11)
               4.send traffic (2000 flows)  between vm11 and vm12 
               5.it should allow only 1000 flows and drop_new_flows should be set (true)
               6.Keep sending 90% of flows @ every 60 seconds 
               7.wait for flow timeout to happens
               8.drop_new_flows flag should be removed (False),onces flows reduces below <90%
        Pass criteria: 
               drop_new_flows flag should be set when flow rate exceeds max_flows 
               flag should be removed once number of flows reduces to <=90% of max_flows
        Maintainer : mmohan@juniper.net
        '''
        vn = {'count':1,            # VN coun
            'vn1':{'subnet':'21.0.0.0/24'},
            }
        vmi = {'count':2, # VMI Count
            'vmi11':{'vn': 'vn1'}, # VMI details
            'vmi12':{'vn': 'vn1'}, # VMI details
            }
         
        # Input Variables 
        compute_nodes = self.orch.get_hosts()
        assert len(compute_nodes) >= 2 , "Required Minimum 2 Compute Nodes"

        vm = {'count':2, 
                'launch_mode':'distribute',
                'vm11':{'vn':['vn1'], 'vmi':['vmi11'],'node': compute_nodes[0]}, # VM Details
                'vm12':{'vn':['vn1'], 'vmi':['vmi12'],'node': compute_nodes[1]}, # VM Details
                }

        # Create Virtual Networks (VNs) 
        vn_fixtures = self.setup_vns(vn=vn)
        vn1_fix = vn_fixtures['vn1']

        #import pdb; pdb.set_trace()
        # Create VMIs
        vmi_fixtures = self.setup_vmis(vn_fixtures, vmi=vmi)
        vmi11_fix = vmi_fixtures['vmi11']
        vmi12_fix = vmi_fixtures['vmi12']

        #import pdb; pdb.set_trace()
        # Setting MAX Flows only on VMI 11
        vmi11_max_flows = 1000
        vmi11_fix.set_max_flows(max_flows=vmi11_max_flows)
        
        # Create VMs
        vm_fixtures = self.setup_vms(vn_fixtures, vmi_fixtures, vm=vm, image_name='ubuntu-traffic')
        vm11_fix = vm_fixtures['vm11']
        vm12_fix = vm_fixtures['vm12']
       
        # Creating ComputeNode/Vrouter Fixtures
        vm11_vrouter_fixture = ComputeNodeFixture(self.connections, vm11_fix.vm_node_ip)
        vm12_vrouter_fixture = ComputeNodeFixture(self.connections, vm12_fix.vm_node_ip)
       

        self.logger.info("Verify Traffic within VMs in VN-1")
        send_vm_fixture = vm11_fix
        recv_vm_fixture = vm12_fix
        traffic_result = self.verify_traffic(sender_vm=send_vm_fixture, receiver_vm=recv_vm_fixture,
                                        proto='udp', sport=1500, dport=10001, count=100)
        self.logger.info("Traffic Tx-Pkts: %d  Rx-Pkts: %d" % (traffic_result[0],traffic_result[1]))
        assert traffic_result[0] == traffic_result[1], "Basic Traffic Validation Failed between VMs ( VN-1)"

        #import pdb; pdb.set_trace()
        vm11_inspect = self.agent_inspect[vm11_fix.vm_node_ip]
        

        vm11_tap_intf = vm11_inspect.get_vna_tap_interface_by_ip(vm11_fix.vm_ip)

        self.logger.info("drop_new_flows flag values @ vifs before sending traffics...")
        vm11_drop_new_flows = vm11_inspect.get_vna_tap_interface_by_ip(vm11_fix.vm_ip)[0]['drop_new_flows']
        self.logger.info("drop_new_flows flag value @ vm11: %s " % (vm11_drop_new_flows))
        
        if vm11_drop_new_flows != 'false':
            assert False, "drop_new_flows flag is set even before sending traffics..."

        self.logger.info("Sleeping for dns/meta flows timeout seconds...")
        self.waiting_for_flow_timeout()

        
        # Verify Max_flows functionality on VMI level 
        #import pdb; pdb.set_trace()
        send_flow_count_vm11 = self.send_traffic(
                src=str(vm11_fix.vm_ip), 
                dst=str(vm12_fix.vm_ip), 
                max_flows=vmi11_max_flows, 
                vm_fix=vm11_fix
                )
        total_flow_count_vm11 = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm12_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("drop_new_flows flag values @ vifs after max_flows exceeds..")
        vm11_drop_new_flows = vm11_inspect.get_vna_tap_interface_by_ip(vm11_fix.vm_ip)[0]['drop_new_flows']
        self.logger.info("drop_new_flows flag value @ vm11: %s " % (vm11_drop_new_flows))
        
        if vm11_drop_new_flows != 'true':
            assert False, "drop_new_flows flag is NOT set even after max_flows execeeded.."

        self.logger.info("Total Obtained Flow Count @ vm11: %d"% (total_flow_count_vm11))
        self.logger.info("Total Expected Flow Count @ vm11: %d" % (vmi11_max_flows))

        #import pdb; pdb.set_trace()

        if total_flow_count_vm11 == vmi11_max_flows:
            self.logger.info("VMI level (vm11) Max Flows Provisioning is working fine")

        assert total_flow_count_vm11 == vmi11_max_flows, "VMI (vm11) level Provisioning is not working"

        vmi11_max_flows_90_percentage = int(vmi11_max_flows*0.9)-20

        flow_timeout = self.DEFAULT_FLOW_TIMEOUT

        while (flow_timeout > 0):
            if flow_timeout < 60:
                time.sleep(flow_timeout)
                flow_timeout = 0
            else:
                time.sleep(60)
                flow_timeout = flow_timeout - 60
            send_flow_count_vm11 = self.send_traffic(
                                         src=str(vm11_fix.vm_ip), 
                                         dst=str(vm12_fix.vm_ip), 
                                         max_flows=old_div(vmi11_max_flows_90_percentage,2), 
                                         vm_fix=vm11_fix
                                         )
        total_flow_count_vm11 = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm12_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count @ vm11: %d"% (total_flow_count_vm11))
        self.logger.info("Total Expected Flow Count @ vm11: %d" % (vmi11_max_flows_90_percentage))
        #import pdb; pdb.set_trace()
        vmi11_max_flows_90_percentage_high = vmi11_max_flows_90_percentage + 20
        vmi11_max_flows_90_percentage_low = vmi11_max_flows_90_percentage - 20
        if total_flow_count_vm11 <= vmi11_max_flows_90_percentage_high and total_flow_count_vm11 >= vmi11_max_flows_90_percentage_low:
            self.logger.info("VMI level (vm11) Max Flows Provisioning is working fine")
        else:
            assert False, "VMI (vm11) level Provisioning is not working"

        self.logger.info("drop_new_flows flag values @ vifs after flowcount to reduces < 90% of max_flows")
        vm11_drop_new_flows = vm11_inspect.get_vna_tap_interface_by_ip(vm11_fix.vm_ip)[0]['drop_new_flows']
        self.logger.info("drop_new_flows flag value @ vm11: %s " % (vm11_drop_new_flows))

        if vm11_drop_new_flows != 'false':
            assert False, "drop_new_flows flag is set even after flowcount to reduces < 90% of max_flows"
       
        self.waiting_for_flow_timeout()

        self.logger.info("drop_new_flows flag values @ vifs after all flows timed out...")
        vm11_drop_new_flows = vm11_inspect.get_vna_tap_interface_by_ip(vm11_fix.vm_ip)[0]['drop_new_flows']
        self.logger.info("drop_new_flows flag value @ vm11: %s " % (vm11_drop_new_flows))

        if vm11_drop_new_flows != 'false':
            assert False, "drop_new_flows flag is set even after all flows timedout..."



    
    @preposttest_wrapper
    def test_dropstats(self):

        '''
        Description: 
           Verify VN max_flows with values as  -1
           Verify VMI max_flows with values as  -1
           Verify vrouter drop_stats are incremented properly after exceeding max_flows limit
           Verify clearing dropstats counter
        Test steps:
               1.Create a virtaul network (vn1)
               2.Launch VMs( vm11, vm12) on vn1 network
               3.Try configuring max_flows as -1 @ VN level
               4.Try configuring max_flows as -1 @ VMI level
               5.Configure VMI level max_flows as 1000 @ vmi11
               4.send traffic (1000 flows)  between vm11 and vm12 
               5.verify dropstats (New Flow Drops), it should not be increated 
               6.send traffic (2000 flows) between vm11 and vm12
               7.verify dropstats (New Flow Drop), it should be increated 
               8.clear dropstats values using dropstats --clear
               9.verify counter (New Flow Drop) value
        Pass criteria: 
               It should NOT allow configuration of negative values (-1)
               dropstats(New Flow Drop) should not be incremented when flows are <= max_flows
               dropstats(New Flow Drop) should be incremented when flows are > max_flows
               Counter value should become 0 after doing clear dropstats
        Maintainer : mmohan@juniper.net
        '''
        vn = {'count':1,            # VN coun
            'vn1':{'subnet':'21.0.0.0/24'},
            }
        vmi = {'count':2, # VMI Count
            'vmi11':{'vn': 'vn1'}, # VMI details
            'vmi12':{'vn': 'vn1'}, # VMI details
            }
         
        # Input Variables 
        compute_nodes = self.orch.get_hosts()
        assert len(compute_nodes) >= 2 , "Required Minimum 2 Compute Nodes"

        vm = {'count':2, 
                'launch_mode':'distribute',
                'vm11':{'vn':['vn1'], 'vmi':['vmi11'],'node': compute_nodes[0]}, # VM Details
                'vm12':{'vn':['vn1'], 'vmi':['vmi12'],'node': compute_nodes[1]}, # VM Details
                }

        # Create Virtual Networks (VNs) 
        vn_fixtures = self.setup_vns(vn=vn)
        vn1_fix = vn_fixtures['vn1']

        #import pdb; pdb.set_trace()
        # Create VMIs
        vmi_fixtures = self.setup_vmis(vn_fixtures, vmi=vmi)
        vmi11_fix = vmi_fixtures['vmi11']
        vmi12_fix = vmi_fixtures['vmi12']

        #import pdb; pdb.set_trace()
        # Setting MAX Flows only on VMI 11
        
        # Try configuring negative value @ VN level ... 
        self.logger.info("Try Configuring negative value @ VN level ...")
        try:
            vn1_fix.set_max_flows(max_flows=-1)
        except Exception as exp :
            self.logger.info(str(exp))
            self.logger.info("Not able to configure negative value (-1) @ VN level max_flows")
        else:
            assert False, self.logger.info("Able to configure negative value (-1) @ VN level max_flows")

        self.logger.info("Try Configuring negative value @ VMI level ...")
        try:
            vmi11_fix.set_max_flows(max_flows=-1)
        except Exception as exp :
            self.logger.info(str(exp))
            self.logger.info("Not able to configure negative value (-1) @ VMI level max_flows")
        else:
            assert False, self.logger.info("Able to configure negative value (-1) @ VMI level max_flows")
             

        vmi11_max_flows = 1000
        vmi11_fix.set_max_flows(max_flows=vmi11_max_flows)
        
        # Create VMs
        vm_fixtures = self.setup_vms(vn_fixtures, vmi_fixtures, vm=vm, image_name='ubuntu-traffic')
        vm11_fix = vm_fixtures['vm11']
        vm12_fix = vm_fixtures['vm12']
       
        # Creating ComputeNode/Vrouter Fixtures
        vm11_vrouter_fixture = ComputeNodeFixture(self.connections, vm11_fix.vm_node_ip)
        vm12_vrouter_fixture = ComputeNodeFixture(self.connections, vm12_fix.vm_node_ip)
       

        self.logger.info("Verify Traffic within VMs in VN-1")
        send_vm_fixture = vm11_fix
        recv_vm_fixture = vm12_fix
        traffic_result = self.verify_traffic(sender_vm=send_vm_fixture, receiver_vm=recv_vm_fixture,
                                        proto='udp', sport=1500, dport=10001, count=100)
        self.logger.info("Traffic Tx-Pkts: %d  Rx-Pkts: %d" % (traffic_result[0],traffic_result[1]))
        assert traffic_result[0] == traffic_result[1], "Basic Traffic Validation Failed between VMs ( VN-1)"

        vm11_inspect = self.agent_inspect[vm11_fix.vm_node_ip]

        vm11_tap_intf = vm11_inspect.get_vna_tap_interface_by_ip(vm11_fix.vm_ip)
        #import pdb; pdb.set_trace()

        vm11_dropstats = vm11_inspect.get_agent_vrouter_drop_stats()
        vm11_drop_new_flow_before = int(vm11_dropstats['ds_drop_new_flow'])
        self.logger.info("New Flow Drops stats value before traffic @ %s :  %d" % (vm11_fix.vm_node_ip,vm11_drop_new_flow_before))
        

        self.logger.info("drop_new_flows flag values @ vifs before sending traffics...")
        vm11_drop_new_flows = vm11_inspect.get_vna_tap_interface_by_ip(vm11_fix.vm_ip)[0]['drop_new_flows']
        self.logger.info("drop_new_flows flag value @ vm11: %s " % (vm11_drop_new_flows))
        
        if vm11_drop_new_flows != 'false':
            assert False, "drop_new_flows flag is set even before sending traffics..."

        self.logger.info("Sleeping for dns/meta flows timeout seconds...")
        self.waiting_for_flow_timeout()


        vmi11_max_flows_exact = (old_div(vmi11_max_flows,2))-10
        # Verify Max_flows functionality on VMI level 
        #import pdb; pdb.set_trace()
        send_flow_count_vm11 = self.send_traffic(
                src=str(vm11_fix.vm_ip), 
                dst=str(vm12_fix.vm_ip), 
                max_flows=vmi11_max_flows_exact, 
                vm_fix=vm11_fix
                )
        total_flow_count_vm11 = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm12_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("drop_new_flows flag values @ vifs after max_flows exceeds..")
        vm11_drop_new_flows = vm11_inspect.get_vna_tap_interface_by_ip(vm11_fix.vm_ip)[0]['drop_new_flows']
        self.logger.info("drop_new_flows flag value @ vm11: %s " % (vm11_drop_new_flows))
        
        if vm11_drop_new_flows != 'false':
            assert False, "drop_new_flows flag is set even before max_flows execeeded.."

        self.logger.info("Total Obtained Flow Count @ vm11: %d"% (total_flow_count_vm11))
        self.logger.info("Total Expected Flow Count +/- 10  @ vm11: %d" % (vmi11_max_flows_exact*2))

        #import pdb; pdb.set_trace()
        vmi11_max_flows_high = (vmi11_max_flows_exact*2) + 20
        vmi11_max_flows_low = (vmi11_max_flows_exact*2) - 20

        if total_flow_count_vm11 <= vmi11_max_flows_high and total_flow_count_vm11 >= vmi11_max_flows_low:
            self.logger.info("VMI level (vm11) Max Flows Provisioning is working fine")
        else:
            assert False, "VMI (vm11) level Provisioning is not working"


        vm11_dropstats = vm11_inspect.get_agent_vrouter_drop_stats()
        vm11_drop_new_flow_after = int(vm11_dropstats['ds_drop_new_flow'])
        self.logger.info("New Flow Drops stats value after traffic @ %s :  %d" % (vm11_fix.vm_node_ip,vm11_drop_new_flow_after))
        
        if vm11_drop_new_flow_before == vm11_drop_new_flow_after: 
            self.logger.info("Dropstats for 'New Flow Drops' is not incremented when num of flows <= max_flows")
        else:
            assert False, "Dropstats for 'New Flow Drops' is incremented when num of flows <= max_flows"


        vm11_dropstats = vm11_inspect.get_agent_vrouter_drop_stats()
        vm11_drop_new_flow_before = int(vm11_dropstats['ds_drop_new_flow'])
        self.logger.info("New Flow Drops stats value before traffic @ %s :  %d" % (vm11_fix.vm_node_ip,vm11_drop_new_flow_before))

        send_flow_count_vm11 = self.send_traffic(
                src=str(vm11_fix.vm_ip),
                dst=str(vm12_fix.vm_ip),
                max_flows=vmi11_max_flows,
                vm_fix=vm11_fix
                )
        total_flow_count_vm11 = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm12_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )


        self.logger.info("Total Obtained Flow Count @ vm11: %d"% (total_flow_count_vm11))
        self.logger.info("Total Expected Flow Count @ vm11: %d" % (vmi11_max_flows))

        #import pdb; pdb.set_trace()

        if total_flow_count_vm11 == vmi11_max_flows:
            self.logger.info("VMI level (vm11) Max Flows Provisioning is working fine")
        else:
            assert False, "VMI (vm11) level Provisioning is not working"

        self.logger.info("drop_new_flows flag values @ vifs after max_flows exceeds..")
        vm11_drop_new_flows = vm11_inspect.get_vna_tap_interface_by_ip(vm11_fix.vm_ip)[0]['drop_new_flows']
        self.logger.info("drop_new_flows flag value @ vm11: %s " % (vm11_drop_new_flows))
        
        if vm11_drop_new_flows != 'true':
            assert False, "drop_new_flows flag is NOT set even after max_flows execeeded.."

        expected_drop_high = (old_div(vmi11_max_flows,2)) + 10
        expected_drop_low = (old_div(vmi11_max_flows,2)) - 10
        for i in range(1,8):
            time.sleep(5)
            vm11_dropstats = vm11_inspect.get_agent_vrouter_drop_stats()
            vm11_drop_new_flow_after = int(vm11_dropstats['ds_drop_new_flow'])
            vm11_drop_new_flow_diff  = vm11_drop_new_flow_after - vm11_drop_new_flow_before
            if vm11_drop_new_flow_diff >= expected_drop_low and vm11_drop_new_flow_diff <= expected_drop_high:
                self.logger.info("New Flow Drops stats value detected after seconds %d" % (5*i))
                break

        self.logger.info("New Flow Drops stats value after traffic @ %s :  %d" % (vm11_fix.vm_node_ip,vm11_drop_new_flow_after))
        self.logger.info("New Flow Drops stats value difference (dropped pkts) @ %s :  %d" % (vm11_fix.vm_node_ip,vm11_drop_new_flow_diff))

        if vm11_drop_new_flow_diff >= expected_drop_low and vm11_drop_new_flow_diff <= expected_drop_high:
            self.logger.info("Dropstats for 'New Flow Drops' is incremented when num of flows execeeds max_flows")
        else:
            assert False, "Dropstats for 'New Flow Drops' is NOT incremented when num of flows exceeds max_flows"

        # Verify clearing drop stats 

        vm11_dropstats = vm11_inspect.get_agent_vrouter_drop_stats()
        vm11_drop_new_flow_before = int(vm11_dropstats['ds_drop_new_flow'])
        self.logger.info("Dropstats value before executing clear command: %d " % (vm11_drop_new_flow_before))

        self.inputs.run_cmd_on_server(vm11_fix.vm_node_ip, "dropstats --clear", container='agent')
        for i in range(1,12):
            time.sleep(5)
            vm11_dropstats = vm11_inspect.get_agent_vrouter_drop_stats()
            vm11_drop_new_flow_after = int(vm11_dropstats['ds_drop_new_flow'])
            if vm11_drop_new_flow_after <= 10:
                self.logger.info("New Flow Drops stats value detected after seconds %d" % (5*i))
                break
        self.logger.info("Dropstats value before doing clear: %d " % (vm11_drop_new_flow_before))
        self.logger.info("Dropstats value after doing clear: %d " % (vm11_drop_new_flow_after))

        if vm11_drop_new_flow_after <= 10:
            self.logger.info("Dropstats(Drop New Flows) is cleared properly, becomes zero(0) after execting 'dropstats --clear'")
        else:
            assert False, "Dropstats(Drop New Flows) is NOT cleared properly, even after executing 'dropstats --clear'"
    
    @preposttest_wrapper
    def test_restart_vrouter_agent(self):

        '''
        Description: 
               Verify VMI level functionality after restart of Vrouter Agent
        Test steps:
               1.Create a virtual network (vn1)
               2.Launch  vm11, vm12 and vm13 on vn1 network 
               3.Configure vmi level max_flows as 1000, 2000 and 3000 on vmi11, vmi12 and vmi13 respectively
               5.Verify traffic between the VMs
               6.send 2000 flows traffic from vm11 to vm13 , it should allow only 1000 flows @vmi11
               7.send 4000 flows traffic from vm12 to vm13, it should all only 2000 flows @vmi12
               8.Modify the max_flows value as 1500 @ vmi11
               9.verify sending traffic between vm11 and vm13, now it should all 1500 flows  
               10.Delete the max_flows @ all VMIs ( by setting the value as 0 )
               11.send traffics across vm11, vm12 and vm13 , it should allow all the traffic
        Pass criteria: 
               Number of flows should be created as per max_flows configured at VMI level.
               After modification, it should work as per modified value
               After deleting max_flows configuration, it should allow all the flows.
        Maintainer : mmohan@juniper.net
        '''
        vn = {'count':1,            # VN coun
            'vn1':{'subnet':'21.0.0.0/24'},
            }
        vmi = {'count':3, # VMI Count
            'vmi11':{'vn': 'vn1'}, # VMI details
            'vmi12':{'vn': 'vn1'}, # VMI details
            'vmi13':{'vn': 'vn1'}, # VMI details
            }
         
        # Input Variables 
        compute_nodes = self.orch.get_hosts()
        assert len(compute_nodes) >= 2 , "Required Minimum 2 Compute Nodes"

        vm = {'count':3, 
                'launch_mode':'distribute',
                'vm11':{'vn':['vn1'], 'vmi':['vmi11'],'node': compute_nodes[0]}, # VM Details
                'vm12':{'vn':['vn1'], 'vmi':['vmi12'],'node': compute_nodes[1]}, # VM Details
                'vm13':{'vn':['vn1'], 'vmi':['vmi13'],'node': compute_nodes[0]}, # VM Details
                }

        # Create Virtual Networks (VNs) 
        vn_fixtures = self.setup_vns(vn=vn)
        vn1_fix = vn_fixtures['vn1']

        #import pdb; pdb.set_trace()
        # Create VMIs
        vmi_fixtures = self.setup_vmis(vn_fixtures, vmi=vmi)
        vmi11_fix = vmi_fixtures['vmi11']
        vmi12_fix = vmi_fixtures['vmi12']
        vmi13_fix = vmi_fixtures['vmi13']

        #import pdb; pdb.set_trace()
        # Setting MAX Flows only on VMI 11
        vn1_max_flows = 400
        vmi11_max_flows = 1000
        vmi13_max_flows = 2000
        vn1_fix.set_max_flows(max_flows=vn1_max_flows)
        vmi11_fix.set_max_flows(max_flows=vmi11_max_flows)
        vmi13_fix.set_max_flows(max_flows=vmi13_max_flows)
        
        # Create VMs
        vm_fixtures = self.setup_vms(vn_fixtures, vmi_fixtures, vm=vm, image_name='ubuntu-traffic')
        vm11_fix = vm_fixtures['vm11']
        vm12_fix = vm_fixtures['vm12']
        vm13_fix = vm_fixtures['vm13']
       
        # Creating ComputeNode/Vrouter Fixtures
        vm11_vrouter_fixture = ComputeNodeFixture(self.connections, vm11_fix.vm_node_ip)
        vm12_vrouter_fixture = ComputeNodeFixture(self.connections, vm12_fix.vm_node_ip)
       

        self.logger.info("Verify Traffic within VMs in VN-1")
        send_vm_fixture = vm11_fix
        recv_vm_fixture = vm12_fix
        traffic_result = self.verify_traffic(sender_vm=send_vm_fixture, receiver_vm=recv_vm_fixture,
                                        proto='udp', sport=1500, dport=10001, count=100)
        self.logger.info("Traffic Tx-Pkts: %d  Rx-Pkts: %d" % (traffic_result[0],traffic_result[1]))
        assert traffic_result[0] == traffic_result[1], "Basic Traffic Validation Failed between VMs ( VN-1)"


        self.logger.info("Sleeping for dns/meta flows timeout seconds...")
        self.waiting_for_flow_timeout()

        
        # Verify Max_flows functionality on VMI level 
        #import pdb; pdb.set_trace()
        send_flow_count = self.send_traffic(
                src=str(vm11_fix.vm_ip), 
                dst=str(vm13_fix.vm_ip), 
                max_flows=vmi11_max_flows, 
                vm_fix=vm11_fix
                )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %d" % (vmi11_max_flows))
        #import pdb; pdb.set_trace()
        if total_flow_count == vmi11_max_flows:
            self.logger.info("VMI level Max Flows Provisioning is working fine")

        assert total_flow_count == vmi11_max_flows, "VMI level Max Flows Provisioning is not working"
       
        # check other VMIs part of that same VN should allow all the flows 
        send_flow_count = self.send_traffic(
                src=str(vm12_fix.vm_ip), 
                dst=str(vm13_fix.vm_ip), 
                max_flows=vmi11_max_flows,
                vm_fix=vm12_fix
            )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm12_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm12_fix.get_local_ip()),
                vrouter_fixture=vm12_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %s" % ('Not VMI level Configured - Should use VN level value'))
        self.logger.info("Total Expected Flow Count: %d" % (vn1_max_flows))
        # import pdb; pdb.set_trace()
        if total_flow_count == vn1_max_flows:
            self.logger.info("No VMI level configuration - VN level max flows is used correctly")
        assert total_flow_count == vn1_max_flows, "Other VMI ( VMI 12) are not taking VN level value"

        self.logger.info("Restarting Vrouter Agent...")
        self.inputs.restart_service('contrail-vrouter-agent', [vm11_fix.vm_node_ip], container='agent', verify_service=True)
        self.inputs.restart_service('contrail-vrouter-agent', [vm12_fix.vm_node_ip], container='agent', verify_service=True)

        self.logger.info("After Agent restart, Sleeping for 180 secs...")
        time.sleep(180)
 # Verify Max_flows functionality on VMI level
        #import pdb; pdb.set_trace()
        send_flow_count = self.send_traffic(
                src=str(vm11_fix.vm_ip),
                dst=str(vm13_fix.vm_ip),
                max_flows=vmi11_max_flows,
                vm_fix=vm11_fix
                )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %d" % (vmi11_max_flows))
        #import pdb; pdb.set_trace()
        if total_flow_count == vmi11_max_flows:
            self.logger.info("After Agrent restarting, VMI level Max Flows Provisioning is working fine")

        assert total_flow_count == vmi11_max_flows, "After Agenr restart, VMI level Max Flows Provisioning is not working"

        # check other VMIs part of that same VN should allow all the flows
        send_flow_count = self.send_traffic(
                src=str(vm12_fix.vm_ip),
                dst=str(vm13_fix.vm_ip),
                max_flows=vmi11_max_flows,
                vm_fix=vm12_fix
            )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm12_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm12_fix.get_local_ip()),
                vrouter_fixture=vm12_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %s" % ('Not VMI level Configured - Should use VN level value'))
        self.logger.info("Total Expected Flow Count: %d" % (vn1_max_flows))
        # import pdb; pdb.set_trace()
        if total_flow_count == vn1_max_flows:
            self.logger.info("After Agenr restart, No VMI level configuration - VN level max flows is used correctly")
        assert total_flow_count == vn1_max_flows, "After Agrent Restart, Other VMI ( VMI 12) are not taking VN level value"

        self.logger.info("Sleeping for dns/meta flows timeout seconds...")
        self.waiting_for_flow_timeout()

        # Reset the VN level Max flows to default value (0)
        vmi11_fix.set_max_flows(max_flows=0)
        send_flow_count = self.send_traffic(
                src=str(vm11_fix.vm_ip), 
                dst=str(vm13_fix.vm_ip), 
                max_flows=vmi11_max_flows,
                vm_fix=vm11_fix
                )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %s" % ('VMI level Deleted - Should use VN level'))
        self.logger.info("Total Expected Flow Count: %d" % (vn1_max_flows))

        if total_flow_count == vn1_max_flows:
            self.logger.info("VMI level deleted properly and it uses VN level Value")
        
        assert total_flow_count == vn1_max_flows, "VMI level deleted properly and it uses VN level Value"

        self.logger.info("Restarting Vrouter Agent...")
        self.inputs.restart_service('contrail-vrouter-agent', [vm11_fix.vm_node_ip], container='agent', verify_service=True)
        self.inputs.restart_service('contrail-vrouter-agent', [vm12_fix.vm_node_ip], container='agent', verify_service=True)

        self.logger.info("After Agent restart, Sleeping for 180 secs...")
        time.sleep(180)

        send_flow_count = self.send_traffic(
                src=str(vm11_fix.vm_ip),
                dst=str(vm13_fix.vm_ip),
                max_flows=vmi11_max_flows,
                vm_fix=vm11_fix
                )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %s" % ('VMI level set as 0 - Should use VN level'))
        self.logger.info("Total Expected Flow Count: %d" % (vn1_max_flows))

        if total_flow_count == vn1_max_flows:
            self.logger.info("After Vrouter Agent Restart : VMI level set as 0 and it uses VN level Value")

        assert total_flow_count == vn1_max_flows, "After Vrouter Agent Restart : It should use VN level Value"

        send_flow_count = self.send_traffic(
                src=str(vm12_fix.vm_ip),
                dst=str(vm13_fix.vm_ip),
                max_flows=vmi11_max_flows,
                vm_fix=vm12_fix
            )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm12_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm12_fix.get_local_ip()),
                vrouter_fixture=vm12_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %s" % ('Not VMI level Configured - Should use VN level value'))
        self.logger.info("Total Expected Flow Count: %d" % (vn1_max_flows))
        # import pdb; pdb.set_trace()
        if total_flow_count == vn1_max_flows:
            self.logger.info("After Vrouter-Agent Restart: No VMI level configuration - VN level max flows is used correctly")
        assert total_flow_count == vn1_max_flows, "After Agent restart, Other VMI ( VMI 12) are not taking VN level value"






    @preposttest_wrapper
    def test_restart_vm(self):

        '''
        Description: 
               Verify VMI level functionality after restart of VM
        Test steps:
               1.Create a virtaul network (vn1)
               2.Launch VMs( vm11, vm12) on vn1 network
               3.configure max_flows as 1000 @ VMI (vmi11)
               4.send traffic (2000 flows)  between vm11 and vm12 
               5.it should allow only 1000 flows and drop_new_flows should be set (true)
               6.Keep sending 90% of flows @ every 60 seconds 
               7.wait for flow timeout to happens
               8.drop_new_flows flag should be removed (False),onces flows reduces below <90%
        Pass criteria: 
               drop_new_flows flag should be set when flow rate exceeds max_flows 
               flag should be removed once number of flows reduces to <=90% of max_flows
        Maintainer : mmohan@juniper.net
        '''
        vn = {'count':1,            # VN coun
            'vn1':{'subnet':'21.0.0.0/24'},
            }
        vmi = {'count':3, # VMI Count
            'vmi11':{'vn': 'vn1'}, # VMI details
            'vmi12':{'vn': 'vn1'}, # VMI details
            'vmi13':{'vn': 'vn1'}, # VMI details
            }
         
        # Input Variables 
        compute_nodes = self.orch.get_hosts()
        assert len(compute_nodes) >= 2 , "Required Minimum 2 Compute Nodes"

        vm = {'count':3, 
                'launch_mode':'distribute',
                'vm11':{'vn':['vn1'], 'vmi':['vmi11'],'node': compute_nodes[0]}, # VM Details
                'vm12':{'vn':['vn1'], 'vmi':['vmi12'],'node': compute_nodes[1]}, # VM Details
                'vm13':{'vn':['vn1'], 'vmi':['vmi13'],'node': compute_nodes[0]}, # VM Details
                }

        # Create Virtual Networks (VNs) 
        vn_fixtures = self.setup_vns(vn=vn)
        vn1_fix = vn_fixtures['vn1']

        #import pdb; pdb.set_trace()
        # Create VMIs
        vmi_fixtures = self.setup_vmis(vn_fixtures, vmi=vmi)
        vmi11_fix = vmi_fixtures['vmi11']
        vmi12_fix = vmi_fixtures['vmi12']
        vmi13_fix = vmi_fixtures['vmi13']

        #import pdb; pdb.set_trace()
        # Setting MAX Flows only on VMI 11
        vn1_max_flows = 400
        vmi11_max_flows = 1000
        vmi13_max_flows = 2000
        vn1_fix.set_max_flows(max_flows=vn1_max_flows)
        vmi11_fix.set_max_flows(max_flows=vmi11_max_flows)
        vmi13_fix.set_max_flows(max_flows=vmi13_max_flows)
        
        # Create VMs
        vm_fixtures = self.setup_vms(vn_fixtures, vmi_fixtures, vm=vm, image_name='ubuntu-traffic')
        vm11_fix = vm_fixtures['vm11']
        vm12_fix = vm_fixtures['vm12']
        vm13_fix = vm_fixtures['vm13']
       
        # Creating ComputeNode/Vrouter Fixtures
        vm11_vrouter_fixture = ComputeNodeFixture(self.connections, vm11_fix.vm_node_ip)
        vm12_vrouter_fixture = ComputeNodeFixture(self.connections, vm12_fix.vm_node_ip)
       

        self.logger.info("Verify Traffic within VMs in VN-1")
        send_vm_fixture = vm11_fix
        recv_vm_fixture = vm12_fix
        traffic_result = self.verify_traffic(sender_vm=send_vm_fixture, receiver_vm=recv_vm_fixture,
                                        proto='udp', sport=1500, dport=10001, count=100)
        self.logger.info("Traffic Tx-Pkts: %d  Rx-Pkts: %d" % (traffic_result[0],traffic_result[1]))
        assert traffic_result[0] == traffic_result[1], "Basic Traffic Validation Failed between VMs ( VN-1)"


        self.logger.info("Sleeping for dns/meta flows timeout seconds...")
        self.waiting_for_flow_timeout()

        
        # Verify Max_flows functionality on VMI level 
        #import pdb; pdb.set_trace()
        send_flow_count = self.send_traffic(
                src=str(vm11_fix.vm_ip), 
                dst=str(vm13_fix.vm_ip), 
                max_flows=vmi11_max_flows, 
                vm_fix=vm11_fix
                )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %d" % (vmi11_max_flows))
        #import pdb; pdb.set_trace()
        if total_flow_count == vmi11_max_flows:
            self.logger.info("VMI level Max Flows Provisioning is working fine")

        assert total_flow_count == vmi11_max_flows, "VMI level Max Flows Provisioning is not working"
       
        # check other VMIs part of that same VN should allow all the flows 
        send_flow_count = self.send_traffic(
                src=str(vm12_fix.vm_ip), 
                dst=str(vm13_fix.vm_ip), 
                max_flows=vmi11_max_flows,
                vm_fix=vm12_fix
            )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm12_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm12_fix.get_local_ip()),
                vrouter_fixture=vm12_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %s" % ('Not VMI level Configured - Should use VN level value'))
        self.logger.info("Total Expected Flow Count: %d" % (vn1_max_flows))
        # import pdb; pdb.set_trace()
        if total_flow_count == vn1_max_flows:
            self.logger.info("No VMI level configuration - VN level max flows is used correctly")
        assert total_flow_count == vn1_max_flows, "Other VMI ( VMI 12) are not taking VN level value"

        self.logger.info("Restarting Virtual Machines (vm11 and vm12)...")

        # Restart the VM here
        self.logger.info('Rebooting the VMs...')
        cmd_to_reboot_vm = ['sudo reboot']
        vm11_fix.run_cmd_on_vm(cmds=cmd_to_reboot_vm)
        vm12_fix.run_cmd_on_vm(cmds=cmd_to_reboot_vm)
        vm11_fix.wait_till_vm_boots()
        vm12_fix.wait_till_vm_boots()
        assert vm11_fix.verify_on_setup()
        assert vm12_fix.verify_on_setup()

        self.logger.info("After VM restart, Sleeping for 180 secs...")
        #self.waiting_for_flow_timeout()
        time.sleep(240)


 # Verify Max_flows functionality on VMI level
        #import pdb; pdb.set_trace()
        send_flow_count = self.send_traffic(
                src=str(vm11_fix.vm_ip),
                dst=str(vm13_fix.vm_ip),
                max_flows=vmi11_max_flows,
                vm_fix=vm11_fix
                )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm11_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm11_fix.get_local_ip()),
                vrouter_fixture=vm11_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %d" % (vmi11_max_flows))
        #import pdb; pdb.set_trace()
        if total_flow_count == vmi11_max_flows:
            self.logger.info("After VM restarting, VMI level Max Flows Provisioning is working fine")

        assert total_flow_count == vmi11_max_flows, "After VM restart, VMI level Max Flows Provisioning is not working"

        # check other VMIs part of that same VN should allow all the flows
        send_flow_count = self.send_traffic(
                src=str(vm12_fix.vm_ip),
                dst=str(vm13_fix.vm_ip),
                max_flows=vmi11_max_flows,
                vm_fix=vm12_fix
            )
        total_flow_count = self.get_total_flow_count(
                source_ip=str(vm12_fix.vm_ip),
                dest_ip=str(vm13_fix.vm_ip),
                vrf_id=vm11_vrouter_fixture.get_vrf_id(vn1_fix.vn_fq_name),
                metadata_ip=str(vm12_fix.get_local_ip()),
                vrouter_fixture=vm12_vrouter_fixture
            )

        self.logger.info("Total Obtained Flow Count: %d"% (total_flow_count))
        self.logger.info("Total Expected Flow Count: %s" % ('Not VMI level Configured - Should use VN level value'))
        self.logger.info("Total Expected Flow Count: %d" % (vn1_max_flows))
        # import pdb; pdb.set_trace()
        if total_flow_count == vn1_max_flows:
            self.logger.info("After VM restart, No VMI level configuration - VN level max flows is used correctly")
        assert total_flow_count == vn1_max_flows, "After VM Restart, Other VMI ( VMI 12) are not taking VN level value"









