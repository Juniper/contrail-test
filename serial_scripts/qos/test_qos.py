from common.qos.base import *
from builtins import str
from builtins import range
from tcutils.wrappers import preposttest_wrapper
from compute_node_test import ComputeNodeFixture


class TestQosQueueSerial(QosTestExtendedBase):

    @classmethod
    def setUpClass(cls):
        super(TestQosQueueSerial, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestQosQueueSerial, cls).tearDownClass()
    # end tearDownClass
    
    @preposttest_wrapper
    def test_queue_dscp(self):
        '''
        This test case aims at testing that traffic is steered to corresponding queue
        which was mentioned in the attached FC.
        This test case test DSCP based qos maps
        Steps:
        1. Read testbed file and populate logical to HW queue mappings.
        2. Configure queue objects picking a single logical ID from every entry in list
        3. Dynamically create single FC object for each queue object
        4. Dynamically create dscp mapping table as per entries in fc
        5. Create a qos map with entries in the dscp map table and attach to VMI.
        6. Test for all entries in qos map and verify that traffic is steered to right 
           hardware queue.
        '''
        self.skip_tc_if_no_queue_config()
        # Below function return the logical to HW queue mapping table
        queue_mapping = self.get_configured_queue_mapping(
                                                self.qos_node_ip)
        # Dynamically creating the queues list containing single logical queue from each entry
        queues = []
        for logical_id in queue_mapping[1]:
            entry = {'queue_id': logical_id}
            queues.append(entry)
        queue_fixtures = self.setup_queues(queues)
        # Dynamically creating FC list based on number of logical qos queues present
        fcs, logical_ids = self.configure_fc_list_dynamically(queue_fixtures)
        fc_fixtures = self.setup_fcs(fcs)
        # Dynamically creating DSCP map based on FCs present
        dscp_map = self.configure_map_dynamically("dscp", fcs)
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map,
                                            default_fc_id=0)
        vm1_vmi_id = list(self.vn1_vm1_fixture.get_vmi_ids().values())[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        i = 0
        for dscp, fc_id in dscp_map.items():
            hw_queue = self.get_hw_queue_from_fc_id(fc_id, fcs, logical_ids)
            validate_method_args = {
                    'src_vm_fixture': self.vn1_vm1_fixture,
                    'dest_vm_fixture': self.vn1_vm2_fixture,
                    'dscp': dscp,
                    'src_port': '10000',
                    'dest_port': '20000',
                    'src_compute_fixture': self.vn1_vm1_compute_fixture,
                    'queue_id' : hw_queue,
                    'interval' : 0.001,
                    'min_expected_pkts' : 5000,
                    'traffic_duration' : 5}
            assert self.validate_packet_qos_marking(**validate_method_args)
    #end test_queue_dscp

    @preposttest_wrapper
    def test_queue_dot1p(self):
        '''
        This test case aims at testing that traffic is steered to corresponding queue
        which was mentioned in the attached FC.
        This test case test DOT1p based qos maps
        Steps:
        1. Read testbed file and populate logical to HW queue mappings.
        2. Configure queue objects picking a single logical ID from every entry in list
        3. Dynamically create single FC object for each queue object
        4. Dynamically create dot1p mapping table as per entries in fc
        5. Create a qos with entries in the dot1p map table and attach to VN.
        6. Test for all entries in qos map and verify that traffic is steered to right 
           hardware queue.
        '''
        self.skip_tc_if_no_queue_config()
        # Below function return the logical to HW queue mapping table
        queue_mapping = self.get_configured_queue_mapping(self.qos_node_ip)
        # Dynamically creating the queues list containing single logical queue from each entry
        queues = []
        for logical_id in queue_mapping[1]:
            entry = {'queue_id': logical_id}
            queues.append(entry)
        queue_fixtures = self.setup_queues(queues)
        # Dynamically creating FC list based on number of logical qos queues present
        fcs, logical_ids = self.configure_fc_list_dynamically(queue_fixtures)
        fc_fixtures = self.setup_fcs(fcs)
        # Dynamically creating dot1p map based on FCs present
        dot1p_map = self.configure_map_dynamically("dot1p", fcs)
        qos_fixture = self.setup_qos_config(dot1p_map=dot1p_map)
        self.setup_qos_config_on_vn(qos_fixture, self.vn1_fixture.uuid)
        i = 0
        for dot1p, fc_id in dot1p_map.items():
            hw_queue = self.get_hw_queue_from_fc_id(fc_id, fcs, logical_ids)
            validate_method_args = {
                    'src_vm_fixture': self.vn1_vm1_fixture,
                    'dest_vm_fixture': self.vn1_vm2_fixture,
                    'traffic_generator' : 'scapy',
                    'dot1p': dot1p,
                    'src_compute_fixture': self.vn1_vm1_compute_fixture,
                    'queue_id' : hw_queue,
                    'interval' : 0.001,
                    'min_expected_pkts' : 1000, # Due to scapy performance issue, keeping value less than expected.
                    'traffic_duration' : 60,
                    'src_mac' : self.vn1_vm1_fixture.mac_addr[
                                            self.vn1_fixture.vn_fq_name]}
            assert self.validate_packet_qos_marking(**validate_method_args)
    #end test_queue_dscp
    
    @preposttest_wrapper
    def test_fc_queue_id_update(self):
        '''
        This test case aims at testing that traffic steered to configured queue 
        while queue id in FC is updated.
        Steps:
        1. Read testbed file and populate logical to HW queue mappings.
        2. Configure queue objects picking a single logical ID from every entry in list
        3. Create a single FC and corresponding dot1p map
        4. Create a qos config with entry in the dot1p map table and attach to VN.
        5. Test that traffic is directed to the configured queue as per FC.
        6. Update the FC with new queue ID and check traffic steered to a different queue.
        '''
        self.skip_tc_if_no_queue_config()
        # Below function return the logical to HW queue mapping table
        queue_mapping = self.get_configured_queue_mapping(self.qos_node_ip)
        # Dynamically creating the queues list containing single logical queue from each entry
        queues = []
        for logical_id in queue_mapping[1]:
            entry = {'queue_id': logical_id}
            queues.append(entry)
        queue_fixtures = self.setup_queues(queues)
        # Creating a FC. The same FC will be updated with different queue values
        iteration = 1
        for queue_fixture in queue_fixtures:
            if iteration == 1:
                fc = [{'fc_id': 1, 'dscp': 10, 'dot1p': 1, 'exp': 1,
                       'queue_uuid' : queue_fixture.uuid}]
                fc_fixture = self.setup_fcs(fc)
                dot1p_map = {3 : 1}
                qos_fixture = self.setup_qos_config(dot1p_map=dot1p_map)
                self.setup_qos_config_on_vn(qos_fixture, self.vn1_fixture.uuid)
                iteration = iteration +1
            else:
                fc_fixture[0].update(queue_uuid =  queue_fixture.uuid)
            logical_queue_id = queue_fixture.queue_id
            logical_queue_id_index = queue_mapping[1].index(
                                            logical_queue_id)
            hw_queue = queue_mapping[0][logical_queue_id_index]
            validate_method_args = {
                'src_vm_fixture': self.vn1_vm1_fixture,
                'dest_vm_fixture': self.vn1_vm2_fixture,
                'traffic_generator' : 'scapy',
                'dot1p': list(dot1p_map.keys())[0],
                'src_compute_fixture': self.vn1_vm1_compute_fixture,
                'queue_id' : hw_queue,
                'interval' : 0.001,
                'min_expected_pkts' : 1000, # Due to scapy performance issue, keeping value less than expected.
                'traffic_duration' : 60,
                'src_mac' : self.vn1_vm1_fixture.mac_addr[
                                    self.vn1_fixture.vn_fq_name]}
            assert self.validate_packet_qos_marking(**validate_method_args)
    #end test_fc_queue_id_update
    
    @preposttest_wrapper
    def test_default_queueing(self):
        '''
        This test case aims at testing all scenarios where traffic is steered to default queue
        Steps:
        1. Create a Logical queue with unique ID which is not configured by user
        2. Configure different FCs 
            A. FC0 to be configured as default FC for qos config
            B. FC1 to be configured without mentioning any queue id
            C. FC2 to be configured with queue id which is not configured by user.
        3. Create a qos config and attach to VMI.
        4. Test that traffic is directed to default queue in all above FC configurations..
        '''
        self.skip_tc_if_no_queue_config()
        # Below function return the logical to HW queue mapping table
        queue_mapping = self.get_configured_queue_mapping(
                                                self.qos_node_ip)
        # Below code will search for a logical queue ID not configured by user
        logical_queue_ids = self.get_all_configured_logical_ids(
                                                self.qos_node_ip)
        for value in range(0, 255):
            if value not in logical_queue_ids:
                unique_queue_id = value
                break
        queue = [{'queue_id': unique_queue_id}] # Assuming that user has not configured above value 255
        queue_fixture = self.setup_queues(queue)
        
        fcs = [{'fc_id': 0, 'dscp': 10, 'dot1p': 1, 'exp': 1},
               {'fc_id': 1, 'dscp': 20, 'dot1p': 2, 'exp': 2},
               {'fc_id': 2, 'dscp': 30, 'dot1p': 3, 'exp': 3,
                       'queue_uuid' : queue_fixture[0].uuid}]
        self.setup_fcs(fcs)
        dscp_map = {20: 1 , 40: 2}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map,
                                            default_fc_id=0)
        vm1_vmi_id = list(self.vn1_vm1_fixture.get_vmi_ids().values())[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        dscpValues = [20, 40, 60]
        for elem in dscpValues:
            hw_queue = queue_mapping[2]
            validate_method_args = {
                    'src_vm_fixture': self.vn1_vm1_fixture,
                    'dest_vm_fixture': self.vn1_vm2_fixture,
                    'dscp': elem,
                    'src_port': '10000',
                    'dest_port': '20000',
                    'src_compute_fixture': self.vn1_vm1_compute_fixture,
                    'queue_id' : hw_queue,
                    'interval' : 0.001,
                    'min_expected_pkts' : 5000,
                    'traffic_duration' : 5}
            assert self.validate_packet_qos_marking(**validate_method_args)
    #end test_default_queueing
    
    @preposttest_wrapper
    def test_queueing_dscp_on_vhost(self):
        '''
        This test case aims at testing that traffic is steered to corresponding queue
        as per the qos config applied on vhost interface
        This test case test DOT1p based qos maps
        Steps:
        1. Read testbed file and populate logical to HW queue mappings.
        2. Configure queue objects picking a single logical ID from every entry in list
        3. Dynamically create single FC object for each queue object
        4. Dynamically create dscp mapping table as per entries in fc
        5. Create vhost based qos config using the above dscp map.
        6. Send traffic from 1 host to another which passes thorugh vhost interface
        '''
        self.skip_tc_if_no_queue_config()
        # Below function return the logical to HW queue mapping table
        queue_mapping = self.get_configured_queue_mapping(self.qos_node_ip)
        # Dynamically creating the queues list containing single logical queue from each entry
        queues = []
        for logical_id in queue_mapping[1]:
            entry = {'queue_id': logical_id}
            queues.append(entry)
        queue_fixtures = self.setup_queues(queues)
        # Dynamically creating FC list based on number of logical qos queues present
        fcs, logical_ids = self.configure_fc_list_dynamically(queue_fixtures)
        fc_fixtures = self.setup_fcs(fcs)
        # Dynamically creating dot1p map based on FCs present
        dscp_map_vhost = self.configure_map_dynamically("dscp", fcs)
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map_vhost,
                                             qos_config_type='vhost')
        # Getting control data IP of the host where destination VM was spawned
        compute_control_ip_idx = self.inputs.compute_ips.index(
                                            self.vn1_vm2_fixture.vm_node_ip)
        compute_control_ip = self.inputs.compute_control_ips[
                                        compute_control_ip_idx] 
        interface = self.vn1_vm1_compute_fixture.agent_physical_interface
        for key,value in dscp_map_vhost.items():
            dscp =key
            tos = format(dscp << 2, 'x')
            # Building command for traffic
            cmd = "ping %s -c 5000 -i 0.001 -Q 0x%s" % (compute_control_ip,
                                                         tos)
            # Getting the count of packets through desired queue before transmitting.
            fc_id = value
            hw_queue = self.get_hw_queue_from_fc_id(fc_id, fcs, logical_ids)
            if 'bond' in interface:
                interface_list = self.get_active_bond_intf(
                                                self.vn1_vm1_compute_fixture.ip,
                                                interface,
                                                get_all_interfaces = True)
            else :
                interface_list = [interface]
            for interface in interface_list:
                init_pkt_count = self.get_queue_count(self.vn1_vm1_fixture.vm_node_ip,
                                              interface, queue_id = hw_queue)
                self.inputs.run_cmd_on_server(self.vn1_vm1_fixture.vm_node_ip, cmd,
                                          container='agent')
                final_pkt_count = self.get_queue_count(
                                        self.vn1_vm1_fixture.vm_node_ip,
                                        interface, queue_id = hw_queue)
                if self.match_traffic(init_pkt_count, final_pkt_count, 5000):
                    return
            assert False, "Expected packets not recieved from desired queue"

class TestQosEncap(QosTestExtendedBase):

    @classmethod
    def setUpClass(cls):
        super(TestQosEncap, cls).setUpClass()
        cls.existing_encap = cls.connections.read_vrouter_config_encap()
        cls.connections.update_vrouter_config_encap(
            'MPLSoGRE', 'MPLSoUDP', 'VXLAN')
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.connections.update_vrouter_config_encap(
            cls.existing_encap[0], cls.existing_encap[1],
            cls.existing_encap[2])
        super(TestQosEncap, cls).tearDownClass()
    # end tearDownClass

    @preposttest_wrapper
    def test_qos_remark_dscp_on_vmi_gre_encap(self):
        ''' Create a qos config for remarking DSCP 1 to 10
            Have VMs A, B
            Apply the qos config to VM A
            Validate that packets from A to B have DSCP marked correctly
        '''
        fcs = [{'fc_id': 100, 'dscp': 10, 'dot1p': 1, 'exp': 1}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {1: 100}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        vm1_vmi_id = list(self.vn1_vm1_fixture.get_vmi_ids().values())[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        assert self.validate_packet_qos_marking(
            src_vm_fixture=self.vn1_vm1_fixture,
            dest_vm_fixture=self.vn1_vm2_fixture,
            dscp=list(dscp_map.keys())[0],
            expected_dscp=fcs[0]['dscp'],
            expected_dot1p=fcs[0]['dot1p'],
            expected_exp=fcs[0]['exp'],
            src_port='10000',
            dest_port='20000',
            src_compute_fixture=self.vn1_vm1_compute_fixture,
            encap="MPLSoGRE")
    # end test_qos_remark_dscp_on_vmi_gre_encap


class TestQosPolicyEncap(TestQosPolicyBase):

    @classmethod
    def setUpClass(cls):
        super(TestQosPolicyEncap, cls).setUpClass()
        cls.existing_encap = cls.connections.read_vrouter_config_encap()
        cls.connections.update_vrouter_config_encap(
                                        'MPLSoGRE', 'MPLSoUDP', 'VXLAN')
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.connections.update_vrouter_config_encap(
            cls.existing_encap[0], cls.existing_encap[1],
            cls.existing_encap[2])
        super(TestQosPolicyEncap, cls).tearDownClass()
    # end tearDownClass

    @preposttest_wrapper
    def test_qos_remark_exp_dscp_on_policy_gre_encap(self):
        '''Test that qos marking happens on fabric interface when qos
           config is applied on policy applied between 2 VNs
           Steps:
           1.Create a Forwarding class with ID 10 to mark dscp as 62
           2.Create a qos config for remarking dscp 0-9 traffic to dscp 62.
           3.Validate that packets on fabric from A to B have DSCP 
             marked to 62
        '''
        fcs = [{'name': "FC_Test", 'fc_id': 100,
                'dscp': 62, 'dot1p': 7, 'exp': 3}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {0: 100, 1: 100, 2: 100, 3: 100, 4:
                    100, 5: 100, 6: 100, 7: 100, 8: 100, 9: 100}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        self.update_policy_qos_config(self.policy_fixture, qos_fixture)
        assert self.validate_packet_qos_marking(
            src_vm_fixture=self.vn1_vm1_fixture,
            dest_vm_fixture=self.vn2_vm1_fixture,
            dscp=list(dscp_map.keys())[9],
            expected_dscp=fcs[0]['dscp'],
            expected_exp=fcs[0]['exp'],
            expected_dot1p=fcs[0]['dot1p'],
            src_compute_fixture=self.vn1_vm1_compute_fixture,
            encap="MPLSoGRE")
    # end test_qos_remark_exp_dscp_on_policy_gre_encap
    
    @preposttest_wrapper
    def test_qos_config_on_policy_for_all_dscp_entries(self):
        '''
        Create a qos config with all valid DSCP values and verify traffic
        for all dscp values
        Steps:
        1. Create 62 FC IDs having unique DSCP values in all
        2. Create a qos config and map all DSCP to unique FC ID
        3. Validate that packets with dscp 1 on fabric from A to B 
           have DSCP marked to 62
        4. Validate that packets with dscp 62 on fabric from A to B 
           have DSCP marked to 1
        5. Similarly, verify for all DSCP values
        '''
        fcs = []
        dscp_map = {}
        for i in range(1, 63):
            fc = {'name': "FC_Test" + str(i), 'fc_id': i, 'dscp': i}
            fcs.append(fc)
            dscp_map[i] = 63 - i
        fc_fixtures = self.setup_fcs(fcs)
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        self.update_policy_qos_config(self.policy_fixture, qos_fixture)
        validate_method_args = {
            'src_vm_fixture': self.vn1_vm1_fixture,
            'dest_vm_fixture': self.vn2_vm1_fixture,
            'dscp': None,
            'expected_dscp': None,
            'src_compute_fixture': self.vn1_vm1_compute_fixture,
            'encap': "MPLSoGRE"}
        for i in range(1, 63):
            validate_method_args['expected_dscp'] = i
            validate_method_args['dscp'] = 63 - i
            assert self.validate_packet_qos_marking(**validate_method_args)
    # end test_qos_config_on_policy_for_all_dscp_entries

class TestQosPolicyQueueSerial(TestQosPolicyBase):

    @classmethod
    def setUpClass(cls):
        super(TestQosPolicyQueueSerial, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestQosPolicyQueueSerial, cls).tearDownClass()
    # end tearDownClass
    
    @preposttest_wrapper
    def test_queue_dscp_on_policy(self):
        '''
        This test case aims at testing that traffic is steered to corresponding queue
        which was mentioned in the attached FC.
        This test case test DSCP based qos maps applied on Policy
        Steps:
        1. Read testbed file and populate logical to HW queue mappings.
        2. Configure queue objects picking a single logical ID from every entry in list
        3. Dynamically create single FC object for each queue object
        4. Dynamically create dscp mapping table as per entries in fc
        5. Create a qos map with entries in the dscp map table and attach to Policy rule.
        6. Test for all entries in qos map and verify that traffic is steered to right 
           hardware queue.
        '''
        self.skip_tc_if_no_queue_config()
        # Below function return the logical to HW queue mapping table
        queue_mapping = self.get_configured_queue_mapping(self.qos_node_ip)
        # Dynamically creating the queues list containing single logical queue from each entry
        queues = []
        for logical_id in queue_mapping[1]:
            entry = {'queue_id': logical_id}
            queues.append(entry)
        queue_fixtures = self.setup_queues(queues)
        # Dynamically creating FC list based on number of logical qos queues present
        fcs, logical_ids = self.configure_fc_list_dynamically(queue_fixtures)
        fc_fixtures = self.setup_fcs(fcs)
        # Dynamically creating DSCP map based on FCs present
        dscp_map = self.configure_map_dynamically("dscp", fcs)
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map,
                                            default_fc_id=0)
        self.update_policy_qos_config(self.policy_fixture, qos_fixture)
        i = 0
        for dscp, fc_id in dscp_map.items():
            hw_queue = self.get_hw_queue_from_fc_id(fc_id, fcs, logical_ids)
            validate_method_args = {
                    'src_vm_fixture': self.vn1_vm1_fixture,
                    'dest_vm_fixture': self.vn2_vm1_fixture,
                    'dscp': dscp,
                    'src_port': '10000',
                    'dest_port': '20000',
                    'src_compute_fixture': self.vn1_vm1_compute_fixture,
                    'queue_id' : hw_queue,
                    'interval' : 0.001,
                    'min_expected_pkts' : 5000,
                    'traffic_duration' : 5}
            assert self.validate_packet_qos_marking(**validate_method_args)
    #end test_queue_dscp_on_policy
    
    @preposttest_wrapper
    def test_qos_queue_on_vmi_precedence_over_policy_over_vn(self):
        '''
        This test case verifies that precedence is maintained for queueing as well.
        Steps:
        1. Create 3 FCs to point to different HW queues.
        2. Map 1 FC to VMI, 2nd FC to VN and 3rd FC to Policy
        3. Send traffic. Check that traffic is steered to HW queue mentioned in FC mapped to VMI
        4. Remove qos config from VMI
        5. Send traffic. Check that traffic is steered to HW queue mentioned in FC mapped to Policy
        6. Remove qos config from Policy
        7. Send traffic. Check that traffic is steered to HW queue mentioned in FC mapped to VN
        '''
        self.skip_tc_if_no_queue_config()
        # Below function return the logical to HW queue mapping table
        queue_mapping = self.get_configured_queue_mapping(self.qos_node_ip)
        # Dynamically creating the queues list containing single logical queue from each entry
        queues = []
        for logical_id in queue_mapping[1]:
            entry = {'queue_id': logical_id}
            queues.append(entry)
        queue_fixtures = self.setup_queues(queues)
        if len(queue_fixtures) < 3:
            skip = True
            msg = "Minimum 3 different HW to logical entries should be present"
            raise testtools.TestCase.skipException(msg)
        fcs = [
            {'name': "FC1_Test", 'fc_id': 10, 'dscp': 62, 'dot1p': 7, 'exp': 7,
             'queue_uuid' : queue_fixtures[0].uuid},
            {'name': "FC2_Test", 'fc_id': 11, 'dscp': 2, 'dot1p': 5, 'exp': 5,
             'queue_uuid' : queue_fixtures[1].uuid},
            {'name': "FC3_Test", 'fc_id': 12, 'dscp': 30, 'dot1p': 3, 'exp': 3,
             'queue_uuid' : queue_fixtures[2].uuid}]
        fc_fixtures = self.setup_fcs(fcs)
        self.setup_fcs(fcs)
        dscp_map_vmi = {49: 10}
        dscp_map_vn = {49: 11}
        dscp_map_policy = {49: 12}
        qos_fixture1 = self.setup_qos_config(dscp_map=dscp_map_vmi)
        qos_fixture2 = self.setup_qos_config(dscp_map=dscp_map_vn)
        qos_fixture3 = self.setup_qos_config(dscp_map=dscp_map_policy)
        vn1_vm_vmi_id = list(self.vn1_vm1_fixture.get_vmi_ids().values())[0]
        self.setup_qos_config_on_vmi(qos_fixture1, vn1_vm_vmi_id)
        self.setup_qos_config_on_vn(qos_fixture2, self.vn1_fixture.uuid)
        self.update_policy_qos_config(self.policy_fixture, qos_fixture3)
        validate_method_args = {
                    'src_vm_fixture': self.vn1_vm1_fixture,
                    'dest_vm_fixture': self.vn2_vm1_fixture,
                    'dscp': 49,
                    'src_compute_fixture': self.vn1_vm1_compute_fixture,
                    'interval' : 0.001,
                    'min_expected_pkts' : 5000,
                    'traffic_duration' : 5}
        # Verifying queueing happens as per qos config on VMI
        logical_queue_id = queue_fixtures[0].queue_id
        logical_queue_id_index = queue_mapping[1].index(
                                            logical_queue_id)
        hw_queue = queue_mapping[0][logical_queue_id_index]
        validate_method_args['queue_id'] = hw_queue
        assert self.validate_packet_qos_marking(**validate_method_args)
        # Once qos config on vmi is removed, the one on policy should be
        # applied
        self.remove_qos_config_on_vmi(qos_fixture1, vn1_vm_vmi_id)
        logical_queue_id = queue_fixtures[2].queue_id
        logical_queue_id_index = queue_mapping[1].index(
                                            logical_queue_id)
        hw_queue = queue_mapping[0][logical_queue_id_index]
        validate_method_args['queue_id'] = hw_queue
        assert self.validate_packet_qos_marking(**validate_method_args)
        # Once qos config on policy is removed, the one on policy should be
        # applied
        self.update_policy_qos_config(self.policy_fixture, qos_fixture3,
                                      operation="remove")
        logical_queue_id = queue_fixtures[1].queue_id
        logical_queue_id_index = queue_mapping[1].index(
                                            logical_queue_id)
        hw_queue = queue_mapping[0][logical_queue_id_index]
        validate_method_args['queue_id'] = hw_queue
        assert self.validate_packet_qos_marking(**validate_method_args)
    # end test_qos_queue_on_vmi_precedence_over_policy_over_vn
    

class TestQosSVCSerial(TestQosSVCBase):

    @classmethod
    def setUpClass(cls):
        super(TestQosSVCSerial, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestQosSVCSerial, cls).tearDownClass()
    # end tearDownClass
    
    @preposttest_wrapper
    def test_qos_queueing_on_vmi_of_si(self):
        '''Test that qos queueing happens when qos config is applied on vmi
           interface of service instance.
           Steps:
           1.Create a Forwarding class with ID 10 to mark dscp as 62
           2.Create a qos config for remarking dscp 0-9 traffic to dscp 62.
           3.Validate that packets on fabric from Service instance VMi to
            node B have DSCP marked to 62
        '''
        self.skip_tc_if_no_queue_config()
        # Below function return the logical to HW queue mapping table
        queue_mapping = self.get_configured_queue_mapping(
                                                self.qos_node_ip)
        # Dynamically creating the queues list containing single logical queue from each entry
        queues = []
        for logical_id in queue_mapping[1]:
            entry = {'queue_id': logical_id}
            queues.append(entry)
        queue_fixtures = self.setup_queues(queues)
        # Dynamically creating FC list based on number of logical qos queues present
        fcs, logical_ids = self.configure_fc_list_dynamically(queue_fixtures)
        fc_fixtures = self.setup_fcs(fcs)
        # Dynamically creating DSCP map based on FCs present
        dscp_map = self.configure_map_dynamically("dscp", fcs)
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map,
                                            default_fc_id=0)
        # Getting the VMI of Service Instance
        right_svmi = self.service_vm_fixture.cs_vmi_obj[\
                                    self.vn2_fixture.vn_fq_name][\
                                    'virtual-machine-interface']['uuid']
        si_source_compute_fixture = self.useFixture(ComputeNodeFixture(
                                    self.connections,
                                    self.service_vm_fixture.vm_node_ip))
        # Applying qos-config on right VMI of service instance
        self.setup_qos_config_on_vmi(qos_fixture, right_svmi)
        i = 0
        for dscp, fc_id in dscp_map.items():
            hw_queue = self.get_hw_queue_from_fc_id(fc_id, fcs, logical_ids)
            validate_method_args = {
                    'src_vm_fixture': self.vn1_vm1_fixture,
                    'dest_vm_fixture': self.vn2_vm1_fixture,
                    'dscp': dscp,
                    'src_compute_fixture': si_source_compute_fixture,
                    'queue_id' : hw_queue,
                    'interval' : 0.001,
                    'min_expected_pkts' : 5000,
                    'traffic_duration' : 5}
            assert self.validate_packet_qos_marking(**validate_method_args)
    #end test_qos_queueing_on_vmi_of_si

class TestQosQueueQosmap(TestQosQueueProperties):

    @classmethod
    def setUpClass(cls):
        super(TestQosQueueQosmap, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestQosQueueQosmap, cls).tearDownClass()
    # end tearDownClass
    
    def preconfiguration_queueing_test(self):
        '''
        This module is not a test case.
        It only has pre configurations required for queueing test cases
        '''
        self.skip_tc_if_no_queue_config()
        queues = [{'queue_id': 15}, 
                  {'queue_id': 45},
                  {'queue_id': 75},
                  {'queue_id': 115}]
        queue_fixtures = self.setup_queues(queues)
        for elem in queue_fixtures:
            assert elem.verify_on_setup()
        fcs = [{'fc_id': 101, 'dscp': 5, 'dot1p': 1, 'exp': 1, 
                'queue_uuid' :queue_fixtures[0].uuid},
               {'fc_id': 102, 'dscp': 10, 'dot1p': 2, 'exp': 2, 
                'queue_uuid' :queue_fixtures[1].uuid},
               {'fc_id': 103, 'dscp': 15, 'dot1p': 3, 'exp': 3, 
                'queue_uuid' :queue_fixtures[2].uuid},
               {'fc_id': 104, 'dscp': 20, 'dot1p': 4, 'exp': 4, 
                'queue_uuid' :queue_fixtures[3].uuid}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {25: 101, 26 : 102, 27 : 103,28 : 104}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        vn1_vmi_id = list(self.vn1_vm1_fixture.get_vmi_ids().values())[0]
        vn2_vmi_id = list(self.vn2_vm2_fixture.get_vmi_ids().values())[0]
        self.setup_qos_config_on_vmi(qos_fixture, vn1_vmi_id)
        self.setup_qos_config_on_vmi(qos_fixture, vn2_vmi_id)

    @preposttest_wrapper
    def test_scheduling_rr_queues(self):
        '''
        This test case verifies that if traffic is sent through 2 different
        queues which are mapping to 2 different Priority groups and both the
        PGs are having strictness as round robin, the traffic is distributed as
        per the Bandwidth configurations of those priority groups
        Steps:
        1. Start sending traffic through 2 different queues configured with
        BW ratio as 60:40.
        2. Verify that traffic through the queues flow with same ratio.
        '''
        self.skip_tc_if_bond_interface(self.fabric_interface)
        self.preconfiguration_queueing_test()
        validate_method_args = {'src_vn1_vm1_fixture': self.vn1_vm1_fixture,
                                'src_vn2_vm1_fixture': self.vn2_vm2_fixture,
                                'dest_vn1_vm2_fixture': self.vn1_vm2_fixture,
                                'dest_vn2_vm2_fixture': self.vn2_vm1_fixture,
                                'queue_types': "rr",
                                'expected_ratio_q1_q2': 1.5,
                                'queue_id_vn1_traffic': 11,
                                'queue_id_vn2_traffic': 28,
                                'dscp_vn1_traffic': 26,
                                'dscp_vn2_traffic': 28}
        assert self.validate_queue_performance(**validate_method_args)
    #end test_scheduling_rr_queues
    
    @preposttest_wrapper
    def test_scheduling_strict_queues(self):
        '''
        This test case verifies that if traffic is sent through 2 different
        queues which are mapping to 2 different Priority groups and both the
        PGs are having strictness as strict, the traffic of higher PG ID queue
        will not get affected
        Steps:
        1. Start sending traffic through 2 different queues configured with
        strictness as 1
        2. Verify that traffic through the higher PG ID queue will be through
        without any drops and drops should be observed in other queue
        '''
        self.skip_tc_if_bond_interface(self.fabric_interface)
        self.preconfiguration_queueing_test()
        validate_method_args = {'src_vn1_vm1_fixture': self.vn1_vm1_fixture,
                                'src_vn2_vm1_fixture': self.vn2_vm2_fixture,
                                'dest_vn1_vm2_fixture': self.vn1_vm2_fixture,
                                'dest_vn2_vm2_fixture': self.vn2_vm1_fixture,
                                'queue_types': "strict",
                                'expected_ratio_q1_q2': 1.5,
                                'queue_id_vn1_traffic': 3,
                                'queue_id_vn2_traffic': 18,
                                'dscp_vn1_traffic': 25,
                                'dscp_vn2_traffic': 27}
        assert self.validate_queue_performance(**validate_method_args)
    #end test_scheduling_strict_queues
    
    @preposttest_wrapper
    def test_scheduling_strict_rr_queues(self):
        '''
        This test case verifies that if traffic is sent through 2 different
        queues which are mapping to 2 different Priority groups where 1 PG is
        having scheduling as strict and other as round robin , the traffic of
        strict priority group should not get dropped. 
        Steps:
        1. Start sending traffic through 2 different queues where q1 configured
        with strictness as 1 and q2 configured with strictness as 0.
        2. Verify that traffic through the queue with strictness as 1 will be
        through without any drops and drops should be observed in other queue.
        '''
        self.skip_tc_if_bond_interface(self.fabric_interface)
        self.preconfiguration_queueing_test()
        validate_method_args = {'src_vn1_vm1_fixture': self.vn1_vm1_fixture,
                                'src_vn2_vm1_fixture': self.vn2_vm2_fixture,
                                'dest_vn1_vm2_fixture': self.vn1_vm2_fixture,
                                'dest_vn2_vm2_fixture': self.vn2_vm1_fixture,
                                'queue_types': "strict_rr",
                                'expected_ratio_q1_q2': 1.5,
                                'queue_id_vn1_traffic': 3,
                                'queue_id_vn2_traffic': 28,
                                'dscp_vn1_traffic': 25,
                                'dscp_vn2_traffic': 28,
                                'strict_queue_id' : 3}
        assert self.validate_queue_performance(**validate_method_args)
    #end test_scheduling_strict_rr_queues

    @preposttest_wrapper
    def test_scheduling_configuration_on_bond_intf(self):
        '''
        Verify that Bandwidth and strictness can be configured on all
        the interfaces of a bond.
        Note that configurations have been done already as part of setUpClass
        under class TestQosQueueProperties in base.py
        '''
        server = self.qos_node_ip
        if "bond" in self.fabric_interface:
            interface_list = self.get_active_bond_intf(
                                        server,
                                        self.fabric_interface,
                                        get_all_interfaces = True)
            for intf in interface_list:
                # Getting priority group Bandwidth configurations
                cmd = "qosmap --get-queue %s| grep 'Priority Group Bandwidth:'"\
                                                                         % intf
                output = self.inputs.run_cmd_on_server(server , cmd,
                                                       container = 'agent')
                output = output.split()[3:11]
                if output == ['0','60','0','40','0','0','0','0']:
                    self.logger.debug("Bandwidth configured correctly on physical"
                                      "interface %s of bond interface" % intf)
                else: 
                    assert False, "BW values not configured correctly"
                cmd = "qosmap --get-queue %s| grep 'Strictness:'" % intf
                output = self.inputs.run_cmd_on_server(server , cmd,
                                                       container = 'agent')
                output = output.split()[1:9]
                if output == ['1','0','1','0','1','0','1','0']:
                    self.logger.debug("Stritness configured correctly on physical"
                                      "interface %s of bond interface" % intf)
                else: 
                    assert False, "Strictness values not configured correctly"
        else:
            msg = "Not a bond interface. Test case runs only over bond"
            raise testtools.TestCase.skipException(msg)
    # end test_scheduling_configuration_on_bond_intf

class TestQosControlDscp(QosTestExtendedBase):

    @classmethod
    def setUpClass(cls):
        super(TestQosControlDscp, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestQosControlDscp, cls).tearDownClass()
    # end tearDownClass

    @preposttest_wrapper
    def test_xmpp_packet_dscp(self):
        '''
        This test case verifies XMPPP control packet marking from packets 
        generated by agent and control node.
        Steps:
        1. Set the global control packet DSCP marking.
        2. Capture XMPP packets generated by agent and verify that DSCP is 
           marked as configured.
        3. Capture the XMPP packets generated by control node and verify 
           that DSCP is marked as configured.
        '''
        control_dscp, dns_dscp, analytics_dscp = 10, 20, 30
        self.setup_control_dscp_values(control_dscp, dns_dscp, analytics_dscp)
        username = self.vn1_vm1_compute_fixture.username
        password = self.vn1_vm1_compute_fixture.password
        # Verifying traffic from agent to controller
        agent_interface = self.vn1_vm1_compute_fixture.agent_physical_interface
        compute_index = self.inputs.compute_names.index(self.first_node_name)
        src_ip = self.inputs.compute_control_ips[compute_index]
        dest_ip = self.agent_inspect[self.inputs.compute_ips[compute_index]].\
                get_vna_xmpp_connection_status()[0]['controller_ip']
        validate_method_args_1 = {
            'interface': agent_interface,
            'compute_node_fixture' : self.vn1_vm1_compute_fixture,
            'username': username,
            'password': password,
            'src_ip': src_ip,
            'dest_ip': dest_ip,
            'dest_port': 5269,
            'logger': self.logger}
        traffic_obj = TrafficAnalyzer(**validate_method_args_1)
        session,pcap = traffic_obj.packet_capture_start()
        sleep(10)
        traffic_obj.packet_capture_stop()
        assert traffic_obj.verify_packets("dscp",
                                          pcap_path_with_file_name = pcap,
                                          expected_count=1,
                                          dscp=control_dscp)
        # Verifying traffic from controller to agent
        validate_method_args_2 = {
            'node_ip' : dest_ip,
            'expected_dscp' : control_dscp,
            'packet_src_ip': dest_ip,
            'packet_dst_ip': src_ip,
            'packet_src_port': 5269}
        assert self.validate_control_packet_dscp_marking(
                                    **validate_method_args_2)
    #end test_xmpp_packet_dscp

    @preposttest_wrapper
    def test_analytics_packet_dscp(self):
        '''
        This test case verifies Analytcis control packet marking from packets 
        generated by agent to collector node.
        Steps:
        1. Set the global control packet DSCP marking.
        2. Capture Analytics packets generated by agent and verify that DSCP is 
           marked as configured.
        '''
        control_dscp, dns_dscp, analytics_dscp = 10, 20, 30
        self.setup_control_dscp_values(control_dscp, dns_dscp, analytics_dscp)
        username = self.vn1_vm1_compute_fixture.username
        password = self.vn1_vm1_compute_fixture.password
        # Verifying traffic from agent to analytics
        agent_interface = self.vn1_vm1_compute_fixture.agent_physical_interface
        compute_index = self.inputs.compute_names.index(self.first_node_name)
        compute_ip = self.inputs.compute_control_ips[compute_index]
        # Searching for analytics node(Collector) IP and source port of 
        # TCP connection of contrail-vrouter-agent with collector 
        cmd = "pidof contrail-vrouter-agent"
        pid = self.inputs.run_cmd_on_server(compute_ip, cmd)
        cmd = "netstat -nap | grep 8086 | grep %s" % pid
        connection_info = self.inputs.run_cmd_on_server(compute_ip, cmd)
        analytics_ip = connection_info.split()[4].split(":")[0]
        src_ip = connection_info.split()[3].split(":")[0]
        compute_port = int(connection_info.split()[3].split(":")[1])
        cmd = "ip -o -4 addr show | grep %s | awk '{print $2}'" % src_ip
        src_intf = self.inputs.run_cmd_on_server(compute_ip, cmd)
        validate_method_args_1 = {
            'interface': src_intf,
            'compute_node_fixture' : self.vn1_vm1_compute_fixture,
            'username': username,
            'password': password,
            'src_ip': src_ip,
            'dest_ip': analytics_ip,
            'dest_port': 8086,
            'src_port': compute_port,
            'logger': self.logger}
        traffic_obj = TrafficAnalyzer(**validate_method_args_1)
        session,pcap = traffic_obj.packet_capture_start()
        sleep(15)
        traffic_obj.packet_capture_stop()
        assert traffic_obj.verify_packets("dscp",
                                          pcap_path_with_file_name = pcap,
                                          expected_count=1,
                                          dscp=analytics_dscp)
    #end test_analytics_packet_dscp

    @preposttest_wrapper
    def test_dns_packet_dscp(self):
        '''
        This test case verifies DNS packet marking from packets 
        generated by agent.
        Steps:
        1. Set the global control packet DSCP marking.
        2. Determine the in use interface of agent for DNS packets. In case 
           Default DNS method is used, DNS packets use the management Interface.
        3. Do a DNS lookup and generate a query.
        4. Capture DNS packets generated by agent and verify that DSCP is 
           marked as configured.
        '''
        control_dscp, dns_dscp, analytics_dscp = 10, 20, 30
        self.setup_control_dscp_values(control_dscp, dns_dscp, analytics_dscp)
        username = self.vn1_vm1_compute_fixture.username
        password = self.vn1_vm1_compute_fixture.password
        # Verifying traffic from agent to Control node
        compute_index = self.inputs.compute_names.index(self.first_node_name)
        compute_ip = self.vn1_vm1_fixture.vm_node_ip
        cmd = 'netstat -ie | grep -B1 %s | grep -o "^\w*"' % compute_ip
        agent_interface = self.inputs.run_cmd_on_server(compute_ip,cmd)
        external_dns_servers = self.get_external_dns_servers(compute_ip)
        cmd = "num=0; while [ ${num} -lt 60 ]; do nslookup google.com; sleep 1; num=$((num+1)); done"
        self.vn1_vm1_fixture.run_cmd_on_vm([cmd], timeout =5)
        validate_method_args_1 = {
            'node_ip' : compute_ip,
            'expected_dscp' : dns_dscp,
            'packet_src_ip': compute_ip,
            'packet_dst_ip': external_dns_servers,
            'packet_dst_port': 53}
        assert self.validate_control_packet_dscp_marking(
                                    **validate_method_args_1)
    #end test_dns_packet_dscp
    
    @preposttest_wrapper
    def test_vhost_marking_over_control_packet_marking(self):
        """
        This test case verifies that vhost qos marking works correctly on
        control packet which was marked by Control DSCP marking. 
        Steps:
        1. Set the global control packet DSCP marking.
        2. Capture XMPP packets generated by agent and verify that DSCP is 
           marked as configured.
        3. Apply a vHOST QOS config for DSCP value same as changed by control
           data marking.
        4. Verify that packet is further marked at the fabric onterface with
           vhost QOS marking.
        """
        control_dscp, dns_dscp, analytics_dscp = 10, 20, 30
        self.setup_control_dscp_values(control_dscp, dns_dscp, analytics_dscp)
        username = self.vn1_vm1_compute_fixture.username
        password = self.vn1_vm1_compute_fixture.password
        # Verifying traffic from agent to controller
        agent_interface = self.vn1_vm1_compute_fixture.agent_physical_interface
        compute_index = self.inputs.compute_names.index(self.first_node_name)
        src_ip = self.inputs.compute_control_ips[compute_index]
        dest_ip = self.agent_inspect[self.inputs.compute_ips[compute_index]].\
                get_vna_xmpp_connection_status()[0]['controller_ip']
        validate_method_args_1 = {
            'interface': agent_interface,
            'compute_node_fixture' : self.vn1_vm1_compute_fixture,
            'username': username,
            'password': password,
            'src_ip': src_ip,
            'dest_ip': dest_ip,
            'dest_port': 5269,
            'logger': self.logger}
        traffic_obj = TrafficAnalyzer(**validate_method_args_1)
        session,pcap = traffic_obj.packet_capture_start()
        sleep(10)
        traffic_obj.packet_capture_stop()
        assert traffic_obj.verify_packets("dscp",
                                          pcap_path_with_file_name = pcap,
                                          expected_count=1,
                                          dscp=control_dscp)
        fcs = [{'fc_id': 100, 'dscp': 25, 'dot1p': 6, 'exp': 2}]
        self.setup_fcs(fcs)
        dscp_map_vhost = {10: 100}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map_vhost,
                                             qos_config_type='vhost')
        session,pcap = traffic_obj.packet_capture_start()
        sleep(10)
        traffic_obj.packet_capture_stop()
        assert traffic_obj.verify_packets("dscp",
                                          pcap_path_with_file_name = pcap,
                                          expected_count=1,
                                          dscp=fcs[0]['dscp'])
    #end test_vhost_marking_over_control_packet_marking

