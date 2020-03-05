from builtins import str
from common.qos.base import *
from tcutils.wrappers import preposttest_wrapper
from compute_node_test import ComputeNodeFixture
import test
from svc_instance_fixture import SvcInstanceFixture
from svc_template_fixture import SvcTemplateFixture
from policy_test import PolicyFixture
from vn_policy_test import VN_Policy_Fixture

from tcutils.traffic_utils.scapy_traffic_gen import ScapyTraffic
from tcutils.traffic_utils.traffic_analyzer import TrafficAnalyzer
from tcutils.util import skip_because

class TestQos(QosTestExtendedBase):

    @classmethod
    def setUpClass(cls):
        super(TestQos, cls).setUpClass()
        cls.fc_id_obj = FcIdGenerator(cls.vnc_lib)
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestQos, cls).tearDownClass()
    # end tearDownClass

    @test.attr(type=['cb_sanity', 'sanity'])
    @preposttest_wrapper
    @skip_because(hypervisor='docker',msg='Bug 1654955',dpdk_cluster=True)
    def test_qos_remark_dscp_on_vmi(self):
        ''' Create a qos config for remarking DSCP 1 to 10
            Have VMs A, B
            Apply the qos config to VM A
            Validate that packets from A to B have DSCP marked correctly
        '''
        fc_id = self.fc_id_obj.get_free_fc_ids(1)
        fcs = [{'fc_id': fc_id[0], 'dscp': 10, 'dot1p': 1, 'exp': 1}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {1: fc_id[0]}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        vm1_vmi_id = list(self.vn1_vm1_fixture.get_vmi_ids().values())[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        assert self.validate_packet_qos_marking(
            src_vm_fixture=self.vn1_vm1_fixture,
            dest_vm_fixture=self.vn1_vm2_fixture,
            dscp=list(dscp_map.keys())[0],
            expected_dscp=fcs[0]['dscp'],
            expected_dot1p=fcs[0]['dot1p'],
            src_port='10000',
            dest_port='20000',
            src_compute_fixture=self.vn1_vm1_compute_fixture)
    # end test_qos_remark_dscp_on_vmi

    @preposttest_wrapper
    def test_qos_remark_dscp_on_vmi_ipv6(self):
        ''' Create a qos config for remarking DSCP 1 to 10
            Have VMs A, B with IPv6 IPs configured
            Apply the qos config to VM A
            Validate that packets from A to B have DSCP marked correctly
        '''
        fc_id = self.fc_id_obj.get_free_fc_ids(1)
        fcs = [{'fc_id': fc_id[0], 'dscp': 10, 'dot1p': 1, 'exp': 1}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {1: fc_id[0]}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        vm1_vmi_id = list(self.vn1_vm1_fixture.get_vmi_ids().values())[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        assert self.validate_packet_qos_marking(
            src_vm_fixture=self.vn1_vm1_fixture,
            dest_vm_fixture=self.vn1_vm2_fixture,
            traffic_generator='scapy',
            dscp=list(dscp_map.keys())[0],
            expected_dscp=fcs[0]['dscp'],
            expected_dot1p=fcs[0]['dot1p'],
            src_compute_fixture=self.vn1_vm1_compute_fixture,
            af='ipv6',
            src_mac=self.vn1_vm1_fixture.mac_addr[
                self.vn1_fixture.vn_fq_name],
            dst_mac=self.vn1_vm2_fixture.mac_addr[
                self.vn1_fixture.vn_fq_name],
            ipv6_src=str(self.vn1_vm1_fixture.vm_ips[1]),
            ipv6_dst=str(self.vn1_vm2_fixture.vm_ips[1]),
            offset = 132)
    # end test_qos_remark_dscp_on_vmi_ipv6

    @preposttest_wrapper
    def test_qos_remark_dot1p_on_vmi(self):
        ''' Create a qos config for remarking DOT1P 2 to 6
            Have VMs A, B
            Apply the qos config to VM A
            Validate that packets from A to B have all fields marked correctly
            Giving a valid destination mac in the packet.
        '''
        fc_id = self.fc_id_obj.get_free_fc_ids(1)
        fcs = [{'fc_id': fc_id[0], 'dscp': 12, 'dot1p': 6, 'exp': 2}]
        fc_fixtures = self.setup_fcs(fcs)
        dot1p_map = {2: fc_id[0]}
        qos_fixture = self.setup_qos_config(dot1p_map=dot1p_map)
        vm1_vmi_id = list(self.vn1_vm1_fixture.get_vmi_ids().values())[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        assert self.validate_packet_qos_marking(
            src_vm_fixture=self.vn1_vm1_fixture,
            dest_vm_fixture=self.vn1_vm2_fixture,
            traffic_generator='scapy',
            expected_dscp=fcs[0]['dscp'],
            expected_dot1p=fcs[0]['dot1p'],
            src_compute_fixture=self.vn1_vm1_compute_fixture,
            dot1p=list(dot1p_map.keys())[0],
            src_mac=self.vn1_vm1_fixture.mac_addr[
                self.vn1_fixture.vn_fq_name],
            dst_mac=self.vn1_vm2_fixture.mac_addr[
                self.vn1_fixture.vn_fq_name],
            offset = 100)
    # end test_qos_remark_dot1p_on_vmi

    @preposttest_wrapper
    def test_qos_remark_dscp_on_vn(self):
        ''' Create a qos config for remarking DSCP 1 to 10
            Have VMs A, B
            Apply the qos config to the VN
            Validate that packets from A to B have DSCP marked correctly
        '''
        fc_id = self.fc_id_obj.get_free_fc_ids(1)
        fcs = [{'fc_id': fc_id[0], 'dscp': 10, 'dot1p': 1, 'exp': 1}]
        self.setup_fcs(fcs)
        dscp_map = {1: fc_id[0]}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        self.setup_qos_config_on_vn(qos_fixture, self.vn1_fixture.uuid)
        assert self.validate_packet_qos_marking(
            src_vm_fixture=self.vn1_vm1_fixture,
            dest_vm_fixture=self.vn1_vm2_fixture,
            dscp=list(dscp_map.keys())[0],
            expected_dscp=fcs[0]['dscp'],
            expected_dot1p=fcs[0]['dot1p'],
            src_port='10000',
            dest_port='20000',
            src_compute_fixture=self.vn1_vm1_compute_fixture)
    # end test_qos_remark_dscp_on_vmi

    @preposttest_wrapper
    def test_qos_remark_dscp_on_vn_ipv6(self):
        ''' Create a qos config for remarking DSCP 1 to 10
            Have VMs A, B with IPv6 IPs configured
            Apply the qos config to the VN
            Validate that packets from A to B have DSCP marked correctly
        '''
        fc_id = self.fc_id_obj.get_free_fc_ids(1)
        fcs = [{'fc_id': fc_id[0], 'dscp': 23, 'dot1p': 3, 'exp': 7}]
        self.setup_fcs(fcs)
        dscp_map = {10: fc_id[0]}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        self.setup_qos_config_on_vn(qos_fixture, self.vn1_fixture.uuid)
        assert self.validate_packet_qos_marking(
            src_vm_fixture=self.vn1_vm1_fixture,
            dest_vm_fixture=self.vn1_vm2_fixture,
            traffic_generator='scapy',
            dscp=list(dscp_map.keys())[0],
            expected_dscp=fcs[0]['dscp'],
            expected_dot1p=fcs[0]['dot1p'],
            expected_exp=fcs[0]['exp'],
            src_compute_fixture=self.vn1_vm1_compute_fixture,
            af='ipv6',
            src_mac=self.vn1_vm1_fixture.mac_addr[
                self.vn1_fixture.vn_fq_name],
            ipv6_src=str(self.vn1_vm1_fixture.vm_ips[1]),
            ipv6_dst=str(self.vn1_vm2_fixture.vm_ips[1]),
            offset = 156,
            encap = "MPLS_any")
    # end test_qos_remark_dscp_on_vn_ipv6

    @preposttest_wrapper
    def test_qos_remark_dot1p_on_vn(self):
        ''' Create a qos config for remarking Dot1p 3 to 5
            Have VMs A, B
            Apply the qos config to the VN
            Validate that packets from A to B have Dot1P marked correctly
        '''
        fc_id = self.fc_id_obj.get_free_fc_ids(1)
        fcs = [{'fc_id': fc_id[0], 'dscp': 23, 'dot1p': 5, 'exp': 3}]
        self.setup_fcs(fcs)
        dot1p_map = {3: fc_id[0]}
        qos_fixture = self.setup_qos_config(dot1p_map=dot1p_map)
        self.setup_qos_config_on_vn(qos_fixture, self.vn1_fixture.uuid)
        assert self.validate_packet_qos_marking(
            src_vm_fixture=self.vn1_vm1_fixture,
            dest_vm_fixture=self.vn1_vm2_fixture,
            traffic_generator='scapy',
            expected_dscp=fcs[0]['dscp'],
            expected_dot1p=fcs[0]['dot1p'],
            expected_exp=fcs[0]['exp'],
            src_compute_fixture=self.vn1_vm1_compute_fixture,
            dot1p=list(dot1p_map.keys())[0],
            src_mac=self.vn1_vm1_fixture.mac_addr[
                self.vn1_fixture.vn_fq_name],
            encap = "MPLS_any")
        # As dst_mac is not mentioned, it will be set to bcast mac.
    # end test_qos_remark_dot1p_on_vn

    @preposttest_wrapper
    def test_qos_config_and_fc_update_for_dscp(self):
        ''' Create a qos config for remarking DSCP 1 to fc1(DSCP 10)
            Have vms A,B. Apply the qos config to VM A
            Update the qos-config to map DSCP 1 to fc 2(DSCP 11)
            Validate that packets from A to B have DSCP marked to 11
            Update the FC 2 with dscp 12
            Validate that packets from A to B have DSCP marked to 12
            Update FC 2 with fc_id 3
            Update qos-config also to point dscp 1 to fc id 3
            Validate that packets from A to B have DSCP marked to 12

        '''
        fc_ids= self.fc_id_obj.get_free_fc_ids(2)
        fcs = [{'fc_id': fc_ids[0], 'dscp': 10, 'dot1p': 1, 'exp': 1},
               {'fc_id': fc_ids[1], 'dscp': 11, 'dot1p': 1, 'exp': 1}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map1 = {1: fc_ids[0]}
        dscp_map2 = {1: fc_ids[1]}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map1)
        vm1_vmi_id = list(self.vn1_vm1_fixture.get_vmi_ids().values())[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        # Change the FC for the qos-config entry
        qos_fixture.set_entries(dscp_mapping=dscp_map2)
        validate_method_args = {
            'src_vm_fixture': self.vn1_vm1_fixture,
            'dest_vm_fixture': self.vn1_vm2_fixture,
            'dscp': list(dscp_map1.keys())[0],
            'expected_dscp': fcs[1]['dscp'],
            'expected_dot1p': fcs[1]['dot1p'],
            'src_port': '10000',
            'dest_port': '20000',
            'src_compute_fixture': self.vn1_vm1_compute_fixture}
        assert self.validate_packet_qos_marking(**validate_method_args)
        # Change FC's dscp remark now
        fc_fixtures[1].update(dscp=12, dot1p=5)
        validate_method_args['expected_dscp'] = 12
        validate_method_args['expected_dot1p'] = 5
        assert self.validate_packet_qos_marking(**validate_method_args)
        # Change FC id
        new_fc_id = self.fc_id_obj.get_free_fc_ids(1)
        dscp_map3 = {1: new_fc_id[0]}
        fc_fixtures[1].update(fc_id=new_fc_id[0])
        qos_fixture.set_entries(dscp_mapping=dscp_map3)
        assert self.validate_packet_qos_marking(**validate_method_args)
    # end test_qos_config_and_fc_update_for_dscp

    @preposttest_wrapper
    def test_qos_config_and_fc_update_for_dot1p(self):
        ''' Create a qos config for remarking Dot1p 1 to fc1(Dot1p 4)
            Have vms A,B. Apply the qos config to VN
            Update the qos-config to map Dot1p 1 to fc2(Dot1p 6)
            Validate that packets from A to B have Dot1P marked to 6
            Update the FC 2 with dot1p 2
            Validate that packets from A to B have Dot1p marked to 2
            Update FC 2 with fc_id 3
            Update qos-config also to point Dot1p 1 to fc id 3
            Validate that packets from A to B have Dot1p marked to 2

        '''
        fc_ids= self.fc_id_obj.get_free_fc_ids(2)
        fcs = [{'fc_id': fc_ids[0], 'dscp': 10, 'dot1p': 4, 'exp': 1},
               {'fc_id': fc_ids[1], 'dscp': 11, 'dot1p': 6, 'exp': 1}]
        fc_fixtures = self.setup_fcs(fcs)
        dot1p_map1 = {1: fc_ids[0]}
        dot1p_map2 = {1: fc_ids[1]}
        dot1p_map4 = {2: fc_ids[0]}
        qos_fixture = self.setup_qos_config(dot1p_map=dot1p_map1)
        self.setup_qos_config_on_vn(qos_fixture, self.vn1_fixture.uuid)
        validate_method_args = {
            'src_vm_fixture': self.vn1_vm1_fixture,
            'dest_vm_fixture': self.vn1_vm2_fixture,
            'dot1p': list(dot1p_map1.keys())[0],
            'expected_dscp': fcs[1]['dscp'],
            'expected_dot1p': fcs[1]['dot1p'],
            'traffic_generator': 'scapy',
            'src_mac': self.vn1_vm1_fixture.mac_addr[
                self.vn1_fixture.vn_fq_name],
            'dst_mac': self.vn1_vm2_fixture.mac_addr[
                self.vn1_fixture.vn_fq_name],
            'src_compute_fixture': self.vn1_vm1_compute_fixture,
            'offset' : 100}
        # Change the FC for the qos-config entry
        qos_fixture.set_entries(dot1p_mapping=dot1p_map2)
        assert self.validate_packet_qos_marking(**validate_method_args)
        # Change FC's dot1p remark now
        fc_fixtures[1].update(dscp=12, dot1p=7)
        validate_method_args['expected_dscp'] = 12
        validate_method_args['expected_dot1p'] = 7
        assert self.validate_packet_qos_marking(**validate_method_args)
        # Change FC id
        new_fc_id = self.fc_id_obj.get_free_fc_ids(1)
        dot1p_map3 = {1: new_fc_id[0]}
        fc_fixtures[1].update(fc_id=new_fc_id[0])
        qos_fixture.set_entries(dot1p_mapping=dot1p_map3)
        assert self.validate_packet_qos_marking(**validate_method_args)
        # Add entry in Dot1P map tablee
        qos_fixture.add_entries(dot1p_mapping=dot1p_map4)
        validate_method_args['dot1p'] = list(dot1p_map4.keys())[0]
        validate_method_args['expected_dscp'] = fcs[0]['dscp']
        validate_method_args['expected_dot1p'] = fcs[0]['dot1p']
        assert self.validate_packet_qos_marking(**validate_method_args)
    # end test_qos_config_and_fc_update_for_dot1p

    @preposttest_wrapper
    def test_qos_remark_based_on_default_fc(self):
        ''' 
        To test dafault FC ID 0 works as expected
        Steps:
        1. Configure FC ID 0 which is default FC for all Qos Configs.
        2. Create another FC ID
        3. Send traffic for Non default FC ID and verify that marking
           happens as per that FC ID.
        4. Send any other traffic and verify that it automatically gets
           mapped to default FC ID and gets marking as per FC ID 0

        '''
        fc_ids= self.fc_id_obj.get_free_fc_ids(2)
        fcs = [{'fc_id': fc_ids[0], 'dscp': 9, 'dot1p': 3, 'exp': 3},
               {'fc_id': fc_ids[1], 'dscp': 10, 'dot1p': 4, 'exp': 1}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {30: fc_ids[1]}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map,
                                            default_fc_id = fc_ids[0])
        vm1_vmi_id = list(self.vn1_vm1_fixture.get_vmi_ids().values())[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        validate_method_args = {
            'src_vm_fixture': self.vn1_vm1_fixture,
            'dest_vm_fixture': self.vn1_vm2_fixture,
            'dscp': list(dscp_map.keys())[0],
            'expected_dscp': fcs[1]['dscp'],
            'expected_dot1p': fcs[1]['dot1p'],
            'src_compute_fixture': self.vn1_vm1_compute_fixture}
        assert self.validate_packet_qos_marking(**validate_method_args)
        validate_method_args['dscp'] = 31
        validate_method_args['expected_dscp'] = fcs[0]['dscp']
        validate_method_args['expected_dot1p'] = fcs[0]['dot1p']
        assert self.validate_packet_qos_marking(**validate_method_args)
        validate_method_args['dscp'] = 0
        assert self.validate_packet_qos_marking(**validate_method_args)
    # end test_qos_remark_based_on_default_fc

    @preposttest_wrapper
    def test_default_fc_update(self):
        ''' 
        To test dafault FC ID values can be modified
        Steps:
        1. Create a qos config and use default FC ID as 0.
        2. Verify that traffic get marked as per default FC ID  1
        3. Change the default FC ID applied to same qos-config to value 3
           and verify marking happens as per new FC ID 3
        4. Verify that traffic mapping to valid dscp value in qos-map
           gets marked as per the non defaul FC mentioned in qos-map
        '''
        fc_ids= self.fc_id_obj.get_free_fc_ids(3)
        fcs = [{'fc_id': fc_ids[0] , 'dscp': 9, 'dot1p': 3, 'exp': 3},
               {'fc_id': fc_ids[1], 'dscp': 10, 'dot1p': 4, 'exp': 4},
               {'fc_id': fc_ids[2], 'dscp': 11, 'dot1p': 5, 'exp': 5}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {30: fc_ids[1]}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map,
                                            default_fc_id=fc_ids[0])
        vm1_vmi_id = list(self.vn1_vm1_fixture.get_vmi_ids().values())[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        validate_method_args = {
            'src_vm_fixture': self.vn1_vm1_fixture,
            'dest_vm_fixture': self.vn1_vm2_fixture,
            'dscp': 40,
            'expected_dscp': fcs[0]['dscp'],
            'expected_dot1p': fcs[0]['dot1p'],
            'src_compute_fixture': self.vn1_vm1_compute_fixture}
        assert self.validate_packet_qos_marking(**validate_method_args)
        qos_fixture.set_default_fc(fc_ids[2])
        validate_method_args['expected_dscp'] = fcs[2]['dscp']
        validate_method_args['expected_dot1p'] = fcs[2]['dot1p']
        assert self.validate_packet_qos_marking(**validate_method_args)
        validate_method_args['dscp'] = list(dscp_map.keys())[0]
        validate_method_args['expected_dscp'] = fcs[1]['dscp']
        validate_method_args['expected_dot1p'] = fcs[1]['dot1p']
        assert self.validate_packet_qos_marking(**validate_method_args)
    # end test_default_fc_update

    @preposttest_wrapper
    def test_qos_marking_dscp_on_vhost(self):
        ''' Create qos-config1 for remarking DSCP 1 to fc1(DSCP 10)
            Create qos-config2 for remarking DSCP 0 to fc2(DSCP 20) for fabric
            Have VMs A and B
            Apply qos-config1 to vmi on VM A and validate the marking happens
            as per fc1.
            Apply qos-config2 on vhost interface and verify that all packets 
            going out of vhost interface are marked as per fc2
        '''
        fc_ids= self.fc_id_obj.get_free_fc_ids(2)
        fcs = [{'fc_id': fc_ids[0], 'dscp': 10, 'dot1p': 5, 'exp': 1},
               {'fc_id': fc_ids[1], 'dscp': 20, 'dot1p': 6, 'exp': 2}]
        self.setup_fcs(fcs)
        dscp_map_vmi = {1: fc_ids[0]}
        dscp_map_vhost = {0: fc_ids[1]}
        qos_fixture1 = self.setup_qos_config(dscp_map=dscp_map_vmi)
        qos_fixture2 = self.setup_qos_config(dscp_map=dscp_map_vhost,
                                             qos_config_type='vhost')
        vn1_vm1_vmi_id = list(self.vn1_vm1_fixture.get_vmi_ids().values())[0]
        self.setup_qos_config_on_vmi(qos_fixture1, vn1_vm1_vmi_id)
        validate_method_args = {
            'src_vm_fixture': self.vn1_vm1_fixture,
            'dest_vm_fixture': self.vn1_vm2_fixture,
            'dscp': list(dscp_map_vmi.keys())[0],
            'expected_dscp': fcs[0]['dscp'],
            'expected_dot1p': fcs[0]['dot1p'],
            'src_compute_fixture': self.vn1_vm1_compute_fixture}
        assert self.validate_packet_qos_marking(**validate_method_args)
        interface = self.vn1_vm1_compute_fixture.agent_physical_interface
        username = self.inputs.host_data[self.vn1_vm1_compute_fixture.ip]\
                                        ['username']
        password = self.inputs.host_data[self.vn1_vm1_compute_fixture.ip]\
                                        ['password']
        compute_index = self.inputs.compute_names.index(self.first_node_name)
        traffic_obj = TrafficAnalyzer(interface,
                                      self.vn1_vm1_compute_fixture,
                                      username,
                                      password,
                                      src_ip=self.inputs.compute_control_ips[
                                          compute_index],
                                      dest_port=5269,
                                      protocol='tcp',
                                      logger=self.logger)
        session,pcap = traffic_obj.packet_capture_start()
        sleep(10)
        traffic_obj.packet_capture_stop()
        assert traffic_obj.verify_packets("dot1p_dscp",
                                          pcap_path_with_file_name = pcap,
                                          expected_count=1,
                                          dscp=fcs[1]['dscp'],
                                          dot1p=fcs[1]['dot1p'])

    """
    # NOTE: Below test cases are fabric qos related TCs.
    # The functionality got deprecated at end of R3.1 due to issues.
    # Keeping the code as it will be useful in future.
    @preposttest_wrapper
    def test_dscp_qos_config_on_fabric(self):
        ''' Create qos-config1 for remarking DSCP 1 to fc1(DSCP 10)
            Create qos-config2 for remarking DSCP 10 to fc2(DSCP 20) for fabric
            Have VMs A and B
            Apply qos-config1 to vmi on VM A
            Validate that qos-config2's dscp rewrite is applied on traffic 
            which is getting into the dest VM B
            On the fabric link on compute node hosting B, qos-config1's values
            should be observed
        '''

        fcs = [ {'fc_id':1, 'dscp': 10, 'dot1p': 5, 'exp': 1},
                {'fc_id':2, 'dscp': 20, 'dot1p': 6, 'exp': 2}]
        self.setup_fcs(fcs)
        dscp_map_vmi = { 1: 1 }
        dscp_map_fabric = { 10: 2 }
        qos_fixture1 = self.setup_qos_config(dscp_map=dscp_map_vmi)
        qos_fixture2 = self.setup_qos_config(dscp_map=dscp_map_fabric,
                                             qos_config_type='fabric')
        vn1_vm1_vmi_id = self.vn1_vm1_fixture.get_vmi_ids().values()[0]

        self.setup_qos_config_on_vmi(qos_fixture1, vn1_vm1_vmi_id)
        validate_method_args = {
            'src_vm_fixture':self.vn1_vm1_fixture,
            'dest_vm_fixture':self.vn1_vm2_fixture,
            'dscp': 1,
            'expected_dscp': fcs[0]['dscp'],
            'expected_dot1p': fcs[0]['dot1p'],
            'expected_exp': fcs[0]['exp'],
            'src_port':'10000',
            'dest_port':'20000',
            'src_compute_fixture': self.vn1_vm1_compute_fixture}
        self.validate_packet_qos_marking(**validate_method_args)

        # TODO
        # If dscp does not match in fabric qos-config, default fc should be applied

        validate_method_args['underlay'] = False
        validate_method_args['expected_dscp'] = fcs[1]['dscp']
        validate_method_args['expected_exp'] = None
        validate_method_args['expected_dot1p'] = None
        self.validate_packet_qos_marking(**validate_method_args)
    # end test_dscp_qos_config_on_fabric

    @preposttest_wrapper
    def test_all_exp_mapping_on_fabric(self):
        '''
        Create a qos config with all valid EXP values and verify traffic
        for all exp values
        Steps:
        1. Create 8 FC IDs having unique EXP values in all
        2. Create another 8 FC IDs just to convert mpls exp to a non
           default value.
        3. Create a qos config and apply in VMi to convert default mpls
           exp traffic to non default value
        2. Create a qos config and map all EXP to different exp
        3. Validate that packets with exp 0 on fabric from A to B
           have exp marked to 7
        4. Validate that packets with exp 7 on fabric from A to B
           have exp marked to 0
        5. Similarly, verify for all exp values
        '''
        fcs = []
        fc_exp = []
        fc_dscp = []
        exp_map_fabric = {}
        for i in range(0,8):
            fc_dict={'name':"FC_Test"+str(i+1),'fc_id':i+1,'exp': i}
            fcs.append(fc_dict)
            exp_map_fabric[i] = 7-i
        for i in range(8,16):
            # Below list of FCs will help change default mpls exp to some other value
            fc_dscp={'name':"FC_Test"+str(i+1),'fc_id':i+1,'dscp': i-8,'exp':i-8}
            fcs.append(fc_dict)
        dscp_map_vmi = {0:9,1:10,2:11,3:12,4:13,5:14,6:15,7:16}
        fc_fixtures = self.setup_fcs(fcs)
        qos_fixture1 = self.setup_qos_config(dscp_map=dscp_map_vmi)
        qos_fixture2 = self.setup_qos_config(exp_map=exp_map_fabric,
                                             qos_config_type='fabric')
        vn1_vm1_vmi_id = self.vn1_vm1_fixture.get_vmi_ids().values()[0]
        self.setup_qos_config_on_vmi(qos_fixture1, vn1_vm1_vmi_id)
        validate_method_args = {
            'src_vm_fixture':self.vn1_vm1_fixture,
            'dest_vm_fixture':self.vn1_vm2_fixture,
            'dscp': None,
            'expected_dscp': None,
            'expected_exp': None,
            'src_port':'10000',
            'dest_port':'20000',
            'src_compute_fixture': self.vn1_vm1_compute_fixture}
        self.validate_packet_qos_marking(**validate_method_args)
        for i in range(0,8):
            validate_method_args['expected_dscp'] = i
            validate_method_args['expected_exp'] = i
            validate_method_args['dscp'] = i
            self.validate_packet_qos_marking(**validate_method_args)
            validate_method_args['underlay'] = False
            validate_method_args['expected_dscp'] = i
            validate_method_args['expected_exp'] = 7-i
        self.validate_packet_qos_marking(**validate_method_args)
    # end test_all_exp_mapping_on_fabric
    '''
    """

class TestQosPolicy(TestQosPolicyBase):

    @classmethod
    def setUpClass(cls):
        super(TestQosPolicy, cls).setUpClass()
        cls.fc_id_obj = FcIdGenerator(cls.vnc_lib)
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestQosPolicy, cls).tearDownClass()
    # end tearDownClass

    @preposttest_wrapper
    def test_qos_config_and_fc_update_for_dscp_map_on_policy(self):
        ''' 
            To test that qos config works correctly even after editing the
            FC and Qos config parameters.
            Steps:
            1. Create a qos config for remarking DSCP 0-9 to fc1(DSCP 62 & EXP 6)
            2. Apply the qos config to policy between VN1 and VN2
            3. Update the qos-config to map DSCP 0-9 to fc 2(DSCP 2 & EXP 4) 
            4. Validate that packets on fabric from A to B have DSCP marked to 2
               and mpls exp marked as 4
            5. Update the FC 2 with dscp 12 and exp as 2
            6. Validate that packets on fabric from A to B have DSCP marked to 12
               and mpls exp marked as 2
            7. Update FC 2 with fc_id 12
            8. Set entries in qos-config to point dscp 10-19 to fc id 12
            9. Validate that packets with dscp 0-9 on fabric from A to B have 
               DSCP marked to 12 and mpls exp marked to 2.
            10.Validate that packets with dscp 10-19 on fabric from A to B have 
               DSCP marked to 62 and mpls exp marked to 6.
        '''
        fc_ids= self.fc_id_obj.get_free_fc_ids(2)
        fcs = [
            {'name': "FC1_Test", 'fc_id': fc_ids[0],
                'dscp': 62, 'dot1p': 6, 'exp': 6},
            {'name': "FC2_Test", 'fc_id': fc_ids[1], 'dscp': 2, 'dot1p': 4, 'exp': 4}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map1 = {0: fc_ids[0], 1: fc_ids[0], 2: fc_ids[0], 3: fc_ids[0],
                    4: fc_ids[0], 5: fc_ids[0], 6: fc_ids[0], 7: fc_ids[0],
                     8: fc_ids[0], 9: fc_ids[0]}
        dscp_map2 = {0: fc_ids[1], 1: fc_ids[1], 2: fc_ids[1], 3: fc_ids[1],
                    4: fc_ids[1], 5: fc_ids[1], 6: fc_ids[1], 7: fc_ids[1],
                     8: fc_ids[1], 9: fc_ids[1]}
        dscp_map4 = {10: fc_ids[0], 11: fc_ids[0], 12: fc_ids[0], 13: fc_ids[0],
                    14: fc_ids[0], 15: fc_ids[0], 16: fc_ids[0], 17: fc_ids[0],
                     18: fc_ids[0], 19: fc_ids[0]}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map1)
        self.update_policy_qos_config(self.policy_fixture, qos_fixture)
        validate_method_args = {
            'src_vm_fixture': self.vn1_vm1_fixture,
            'dest_vm_fixture': self.vn2_vm1_fixture,
            'dscp': list(dscp_map1.keys())[9],
            'expected_dscp': fcs[0]['dscp'],
            'expected_exp': fcs[0]['exp'],
            'expected_dot1p': fcs[0]['dot1p'],
            'src_compute_fixture': self.vn1_vm1_compute_fixture}
        assert self.validate_packet_qos_marking(**validate_method_args)
        validate_method_args['expected_dscp'] = fcs[1]['dscp']
        validate_method_args['expected_exp'] = fcs[1]['exp']
        validate_method_args['expected_dot1p'] = fcs[1]['dot1p']
        # Change the FC for the qos-config entry
        qos_fixture.set_entries(dscp_mapping=dscp_map2)
        assert self.validate_packet_qos_marking(**validate_method_args)
        # Change FC's dscp remark now
        fc_fixtures[1].update(dscp=12, exp=2, dot1p=2)
        validate_method_args['expected_dscp'] = 12
        validate_method_args['expected_exp'] = 2
        validate_method_args['expected_dot1p'] = 2
        assert self.validate_packet_qos_marking(**validate_method_args)
        # Change FC id
        new_fc_id = self.fc_id_obj.get_free_fc_ids(1)
        dscp_map3 = {0: new_fc_id[0], 1: new_fc_id[0], 2: new_fc_id[0],
                    3: new_fc_id[0], 4: new_fc_id[0], 5: new_fc_id[0],
                    6: new_fc_id[0], 7: new_fc_id[0], 8: new_fc_id[0],
                    9: new_fc_id[0]}
        fc_fixtures[1].update(fc_id=new_fc_id[0])
        qos_fixture.set_entries(dscp_mapping=dscp_map3)
        assert self.validate_packet_qos_marking(**validate_method_args)
        # Adding more entries in qos-config
        qos_fixture.add_entries(dscp_mapping=dscp_map4)
        assert self.validate_packet_qos_marking(**validate_method_args)
        validate_method_args['dscp'] = list(dscp_map4.keys())[9]
        validate_method_args['expected_dscp'] = fcs[0]['dscp']
        validate_method_args['expected_exp'] = fcs[0]['exp']
        validate_method_args['expected_dot1p'] = fcs[0]['dot1p']
        assert self.validate_packet_qos_marking(**validate_method_args)
    # end test_qos_config_and_fc_update_for_dscp_map_on_policy

    @preposttest_wrapper
    def test_qos_vmi_precedence_over_policy_over_vn(self):
        ''' Create qos-config1 for remarking DSCP 1 to fc1(DSCP 10)
            Create qos-config2 for remarking DSCP 1 to fc2(DSCP 20)
            Apply qos-config1 to vmi and qos-config2 to VN
            Validate that qos-config1's dscp rewrite is applied
        '''
        fc_ids= self.fc_id_obj.get_free_fc_ids(3)
        fcs = [
            {'name': "FC1_Test", 'fc_id': fc_ids[0],
                'dscp': 62, 'dot1p': 7, 'exp': 7},
            {'name': "FC2_Test", 'fc_id': fc_ids[1],
             'dscp': 2, 'dot1p': 5, 'exp': 5},
            {'name': "FC3_Test", 'fc_id': fc_ids[2],
             'dscp': 30, 'dot1p': 3, 'exp': 3}]
        self.setup_fcs(fcs)
        dscp_map_vmi = {49: fc_ids[0]}
        dscp_map_vn = {49: fc_ids[1]}
        dscp_map_policy = {49: fc_ids[2]}
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
            'dscp': list(dscp_map_vmi.keys())[0],
            'expected_dscp': fcs[0]['dscp'],
            'expected_exp': fcs[0]['exp'],
            'expected_dot1p': fcs[0]['dot1p'],
            'src_compute_fixture': self.vn1_vm1_compute_fixture}
        assert self.validate_packet_qos_marking(**validate_method_args)
        # Once qos config on vmi is removed, the one on policy should be
        # applied
        self.remove_qos_config_on_vmi(qos_fixture1, vn1_vm_vmi_id)
        validate_method_args['expected_dscp'] = fcs[2]['dscp']
        validate_method_args['expected_exp'] = fcs[2]['exp']
        validate_method_args['expected_dot1p'] = fcs[2]['dot1p']
        assert self.validate_packet_qos_marking(**validate_method_args)
        # Once qos config on policy is removed, the one on policy should be
        # applied
        self.update_policy_qos_config(self.policy_fixture, qos_fixture3,
                                      operation="remove")
        validate_method_args['expected_dscp'] = fcs[1]['dscp']
        validate_method_args['expected_exp'] = fcs[1]['exp']
        validate_method_args['expected_dot1p'] = fcs[1]['dot1p']
        assert self.validate_packet_qos_marking(**validate_method_args)
    # end test_qos_vmi_precedence_over_policy_over_vn

    @preposttest_wrapper
    def test_qos_remark_dscp_on_particular_rule_of_policy(self):
        ''' To test that qos config works correctly if applied on a specific rule
            in policy which is above or below the rule in use.
            Steps:
            1. Create a qos config for remarking DSCP 0-9 to fc1(DSCP 62 & EXP 6)
            2. Apply the qos config to 1st rule of Policy at index 0
            3. Verify that traffic for rule 1 is marked and for rule 2 is untouched
            4. Remove qos config from 1st rule and apply to 2nd rule
            5. Verify that traffic for rule 2 is marked and for rule 1 is untouched
        '''
        fc_ids= self.fc_id_obj.get_free_fc_ids(1)
        fcs = [{'name': "FC1_Test", 'fc_id': fc_ids[0],
                'dscp': 62, 'dot1p': 6, 'exp': 6}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {0: fc_ids[0], 1: fc_ids[0], 2: fc_ids[0], 3: fc_ids[0],
                    4: fc_ids[0], 5: fc_ids[0], 6: fc_ids[0], 7: fc_ids[0],
                    8: fc_ids[0], 9: fc_ids[0]}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        self.update_policy_qos_config(self.policy_fixture, qos_fixture,
                                      entry_index=1)
        validate_method_args = {
            'src_vm_fixture': self.vn1_vm1_fixture,
            'dest_vm_fixture': self.vn2_vm1_fixture,
            'dscp': list(dscp_map.keys())[9],
            'expected_dscp': 0,
            'expected_exp': 0,
            'expected_dot1p': 0,
            'src_compute_fixture': self.vn1_vm1_compute_fixture}
        assert self.validate_packet_qos_marking(protocol="udp",
                                                **validate_method_args)
        validate_method_args['expected_dscp'] = fcs[0]['dscp']
        validate_method_args['expected_exp'] = fcs[0]['exp']
        validate_method_args['expected_dot1p'] = fcs[0]['dot1p']
        assert self.validate_packet_qos_marking(protocol="tcp",
                                                **validate_method_args)
        self.update_policy_qos_config(self.policy_fixture, qos_fixture,
                                      operation="remove", entry_index=1)
        self.update_policy_qos_config(self.policy_fixture, qos_fixture,
                                      entry_index=0)
        assert self.validate_packet_qos_marking(protocol="udp",
                                                **validate_method_args)
        validate_method_args['expected_dscp'] = 0
        validate_method_args['expected_exp'] = 0
        validate_method_args['expected_dot1p'] = 0
        assert self.validate_packet_qos_marking(protocol="tcp",
                                                **validate_method_args)
    # end test_qos_remark_dscp_on_particular_rule_of_policy


class TestQosSVC(TestQosSVCBase):

    @classmethod
    def setUpClass(cls):
        super(TestQosSVC, cls).setUpClass()
        cls.fc_id_obj = FcIdGenerator(cls.vnc_lib)
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestQosSVC, cls).tearDownClass()
    # end tearDownClass

    @preposttest_wrapper
    def test_qos_remark_dscp_on_vmi_of_si(self):
        '''Test that qos marking happens when qos config is applied on vmi
           interface of service instance.
           Steps:
           1.Create a Forwarding class with ID 10 to mark dscp as 62
           2.Create a qos config for remarking dscp 0-9 traffic to dscp 62.
           3.Validate that packets on fabric from Service instance VMi to
            node B have DSCP marked to 62
        '''
        fc_ids= self.fc_id_obj.get_free_fc_ids(1)
        fcs = [{'name': "FC_Test", 'fc_id': fc_ids[0],
                'dscp': 62, 'dot1p': 7, 'exp': 3}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {0: fc_ids[0], 1: fc_ids[0], 2: fc_ids[0], 3: fc_ids[0],
                    4: fc_ids[0], 5: fc_ids[0], 6: fc_ids[0], 7: fc_ids[0],
                    8: fc_ids[0], 9: fc_ids[0]}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        # Getting the VMI of Service Instance
        right_svmi = self.service_vm_fixture.cs_vmi_obj[\
                                    self.vn2_fixture.vn_fq_name][\
                                    'virtual-machine-interface']['uuid']
        si_source_compute_fixture = self.useFixture(ComputeNodeFixture(
                                    self.connections,
                                    self.service_vm_fixture.vm_node_ip))
        # Applying qos-config on right VMI of service instance
        self.setup_qos_config_on_vmi(qos_fixture, right_svmi)
        si_right_vrf_id = self.agent_inspect[
                        self.service_vm_fixture.vm_node_ip].get_vna_vrf_objs(
                        project=self.project.project_name,
                        vn_name=self.vn2_fixture.vn_name
                        )['vrf_list'][0]['ucindex']
        assert self.validate_packet_qos_marking(
            src_vm_fixture=self.vn1_vm1_fixture,
            dest_vm_fixture=self.vn2_vm1_fixture,
            dscp=list(dscp_map.keys())[9],
            expected_dscp=fcs[0]['dscp'],
            expected_exp=fcs[0]['exp'],
            expected_dot1p=fcs[0]['dot1p'],
            src_compute_fixture=si_source_compute_fixture,
            vrf_id=si_right_vrf_id)
    # end test_qos_remark_dscp_on_vmi_of_si

    @preposttest_wrapper
    def test_qos_remark_dscp_on_policy_including_si(self):
        '''Test that qos marking happens when qos config is applied on policy
           in which a SI is also associated.
           Steps:
           1.Create a Forwarding class with ID 10 to mark dscp as 62
           2.Create a qos config for remarking dscp 0-9 traffic to dscp 62.
           3.Apply the qos config to the policy
           4.Verify that packets to and from the SI are marked as expected
        '''
        fc_ids= self.fc_id_obj.get_free_fc_ids(1)
        fcs = [{'name': "FC_Test", 'fc_id': fc_ids[0],
                'dscp': 62, 'dot1p': 7, 'exp': 3}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {0: fc_ids[0], 1: fc_ids[0], 2: fc_ids[0], 3: fc_ids[0],
                    4: fc_ids[0], 5: fc_ids[0], 6: fc_ids[0], 7: fc_ids[0],
                    8: fc_ids[0], 9: fc_ids[0]}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        self.update_policy_qos_config(self.policy_fixture, qos_fixture)
        # verifying marking on packets from SI to right VN
        compute_node_index = self.inputs.compute_names.index(
                                            self.first_node_name)
        si_vm_node_ip = self.inputs.compute_ips[compute_node_index]
        si_source_compute_fixture = self.useFixture(ComputeNodeFixture(
            self.connections,
            si_vm_node_ip))
        si_right_vrf_id = self.agent_inspect[
            si_vm_node_ip].get_vna_vrf_objs(
            project=self.project.project_name,
            vn_name=self.vn2_fixture.vn_name
        )['vrf_list'][0]['ucindex']
        validate_method_args = {
            'src_vm_fixture': self.vn1_vm1_fixture,
            'dest_vm_fixture': self.vn2_vm1_fixture,
            'dscp': list(dscp_map.keys())[9],
            'expected_dscp': fcs[0]['dscp'],
            'expected_exp': fcs[0]['exp'],
            'expected_dot1p': fcs[0]['dot1p'],
            'src_compute_fixture': si_source_compute_fixture,
            'vrf_id': si_right_vrf_id}
        assert self.validate_packet_qos_marking(**validate_method_args)
        # verifying marking on packets from right VN to SI
        validate_method_args['src_vm_fixture'] = self.vn2_vm1_fixture
        validate_method_args['dest_vm_fixture'] = self.vn1_vm1_fixture
        validate_method_args['src_compute_fixture'] = \
            self.vn2_vm1_compute_fixture
        validate_method_args['vrf_id'] = None
        assert self.validate_packet_qos_marking(**validate_method_args)
    # end test_qos_remark_dscp_on_policy_including_si
