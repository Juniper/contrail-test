from tcutils.wrappers import preposttest_wrapper
from compute_node_test import ComputeNodeFixture

from common.qos.base import *

from svc_instance_fixture import SvcInstanceFixture
from svc_template_fixture import SvcTemplateFixture
from policy_test import PolicyFixture
from vn_policy_test import VN_Policy_Fixture
from cfgm_common.exceptions import BadRequest

from tcutils.traffic_utils.scapy_traffic_gen import ScapyTraffic
from tcutils.traffic_utils.traffic_analyzer import TrafficAnalyzer


class TestQos(QosTestExtendedBase):

    @classmethod
    def setUpClass(cls):
        super(TestQos, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestQos, cls).tearDownClass()
    # end tearDownClass

    @preposttest_wrapper
    def test_qos_remark_dscp_on_vmi(self):
        ''' Create a qos config for remarking DSCP 1 to 10
            Have VMs A, B
            Apply the qos config to VM A
            Validate that packets from A to B have DSCP marked correctly
        '''
        fcs = [{'fc_id': 10, 'dscp': 10, 'dot1p': 1, 'exp': 1}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {1: 10}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        vm1_vmi_id = self.vn1_vm1_fixture.get_vmi_ids().values()[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        assert self.validate_packet_qos_marking(
            src_vm_fixture=self.vn1_vm1_fixture,
            dest_vm_fixture=self.vn1_vm2_fixture,
            dscp=dscp_map.keys()[0],
            expected_dscp=fcs[0]['dscp'],
            expected_dot1p=fcs[0]['dot1p'],
            src_port='10000',
            dest_port='20000',
            src_compute_fixture=self.vn1_vm1_compute_fixture,
            encap="VxLAN")
    # end test_qos_remark_dscp_on_vmi

    @preposttest_wrapper
    def test_qos_remark_dscp_on_vmi_ipv6(self):
        ''' Create a qos config for remarking DSCP 1 to 10
            Have VMs A, B with IPv6 IPs configured
            Apply the qos config to VM A
            Validate that packets from A to B have DSCP marked correctly
        '''
        fcs = [{'fc_id': 10, 'dscp': 10, 'dot1p': 1, 'exp': 1}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {1: 10}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        vm1_vmi_id = self.vn1_vm1_fixture.get_vmi_ids().values()[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        assert self.validate_packet_qos_marking(
            src_vm_fixture=self.vn1_vm1_fixture,
            dest_vm_fixture=self.vn1_vm2_fixture,
            traffic_generator='scapy',
            dscp=dscp_map.keys()[0],
            expected_dscp=fcs[0]['dscp'],
            expected_dot1p=fcs[0]['dot1p'],
            src_compute_fixture=self.vn1_vm1_compute_fixture,
            af='ipv6',
            src_mac=self.vn1_vm1_fixture.mac_addr[
                self.vn1_fixture.vn_fq_name],
            dst_mac=self.vn1_vm2_fixture.mac_addr[
                self.vn1_fixture.vn_fq_name],
            ipv6_src=str(self.vn1_vm1_fixture.vm_ips[1]),
            ipv6_dst=str(self.vn1_vm2_fixture.vm_ips[1]))
    # end test_qos_remark_dscp_on_vmi_ipv6

    @preposttest_wrapper
    def test_qos_remark_dot1p_on_vmi(self):
        ''' Create a qos config for remarking DOT1P 2 to 6
            Have VMs A, B
            Apply the qos config to VM A
            Validate that packets from A to B have all fields marked correctly
            Giving a valid destination mac in the packet.
            Unicast traffic will be VxLAN encapsulated.
        '''
        fcs = [{'fc_id': 10, 'dscp': 12, 'dot1p': 6, 'exp': 2}]
        fc_fixtures = self.setup_fcs(fcs)
        dot1p_map = {2: 10}
        qos_fixture = self.setup_qos_config(dot1p_map=dot1p_map)
        vm1_vmi_id = self.vn1_vm1_fixture.get_vmi_ids().values()[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        assert self.validate_packet_qos_marking(
            src_vm_fixture=self.vn1_vm1_fixture,
            dest_vm_fixture=self.vn1_vm2_fixture,
            traffic_generator='scapy',
            expected_dscp=fcs[0]['dscp'],
            expected_dot1p=fcs[0]['dot1p'],
            src_compute_fixture=self.vn1_vm1_compute_fixture,
            dot1p=dot1p_map.keys()[0],
            src_mac=self.vn1_vm1_fixture.mac_addr[
                self.vn1_fixture.vn_fq_name],
            dst_mac=self.vn1_vm2_fixture.mac_addr[
                self.vn1_fixture.vn_fq_name])
    # end test_qos_remark_dot1p_on_vmi

    @preposttest_wrapper
    def test_qos_remark_dscp_on_vn(self):
        ''' Create a qos config for remarking DSCP 1 to 10
            Have VMs A, B
            Apply the qos config to the VN
            Validate that packets from A to B have DSCP marked correctly
        '''
        fcs = [{'fc_id': 10, 'dscp': 10, 'dot1p': 1, 'exp': 1}]
        self.setup_fcs(fcs)
        dscp_map = {1: 10}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        self.setup_qos_config_on_vn(qos_fixture, self.vn1_fixture.uuid)
        assert self.validate_packet_qos_marking(
            src_vm_fixture=self.vn1_vm1_fixture,
            dest_vm_fixture=self.vn1_vm2_fixture,
            dscp=dscp_map.keys()[0],
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
        fcs = [{'fc_id': 10, 'dscp': 23, 'dot1p': 3, 'exp': 7}]
        self.setup_fcs(fcs)
        dscp_map = {10: 10}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        self.setup_qos_config_on_vn(qos_fixture, self.vn1_fixture.uuid)
        assert self.validate_packet_qos_marking(
            src_vm_fixture=self.vn1_vm1_fixture,
            dest_vm_fixture=self.vn1_vm2_fixture,
            traffic_generator='scapy',
            dscp=dscp_map.keys()[0],
            expected_dscp=fcs[0]['dscp'],
            expected_dot1p=fcs[0]['dot1p'],
            expected_exp=fcs[0]['exp'],
            src_compute_fixture=self.vn1_vm1_compute_fixture,
            af='ipv6',
            src_mac=self.vn1_vm1_fixture.mac_addr[
                self.vn1_fixture.vn_fq_name],
            ipv6_src=str(self.vn1_vm1_fixture.vm_ips[1]),
            ipv6_dst=str(self.vn1_vm2_fixture.vm_ips[1]))
    # end test_qos_remark_dscp_on_vn_ipv6

    @preposttest_wrapper
    def test_qos_remark_dot1p_on_vn(self):
        ''' Create a qos config for remarking Dot1p 3 to 5
            Have VMs A, B
            Apply the qos config to the VN
            Validate that packets from A to B have Dot1P marked correctly
        '''
        fcs = [{'fc_id': 10, 'dscp': 23, 'dot1p': 5, 'exp': 3}]
        self.setup_fcs(fcs)
        dot1p_map = {3: 10}
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
            dot1p=dot1p_map.keys()[0],
            src_mac=self.vn1_vm1_fixture.mac_addr[
                self.vn1_fixture.vn_fq_name])
        # As dst_mac is not mentioned, it will be set to bcast mac.
        # The Bcast L2 traffic will go via UDP encap. Validating that.
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
        fcs = [{'fc_id': 1, 'dscp': 10, 'dot1p': 1, 'exp': 1},
               {'fc_id': 2, 'dscp': 11, 'dot1p': 1, 'exp': 1}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map1 = {1: 1}
        dscp_map2 = {1: 2}
        dscp_map3 = {1: 3}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map1)
        vm1_vmi_id = self.vn1_vm1_fixture.get_vmi_ids().values()[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        # Change the FC for the qos-config entry
        qos_fixture.set_entries(dscp_mapping=dscp_map2)
        validate_method_args = {
            'src_vm_fixture': self.vn1_vm1_fixture,
            'dest_vm_fixture': self.vn1_vm2_fixture,
            'dscp': dscp_map1.keys()[0],
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
        fc_fixtures[1].update(fc_id=3)
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
        fcs = [{'fc_id': 1, 'dscp': 10, 'dot1p': 4, 'exp': 1},
               {'fc_id': 2, 'dscp': 11, 'dot1p': 6, 'exp': 1}]
        fc_fixtures = self.setup_fcs(fcs)
        dot1p_map1 = {1: 1}
        dot1p_map2 = {1: 2}
        dot1p_map3 = {1: 3}
        dot1p_map4 = {2: 1}
        qos_fixture = self.setup_qos_config(dot1p_map=dot1p_map1)
        self.setup_qos_config_on_vn(qos_fixture, self.vn1_fixture.uuid)
        validate_method_args = {
            'src_vm_fixture': self.vn1_vm1_fixture,
            'dest_vm_fixture': self.vn1_vm2_fixture,
            'dot1p': dot1p_map1.keys()[0],
            'expected_dscp': fcs[1]['dscp'],
            'expected_dot1p': fcs[1]['dot1p'],
            'traffic_generator': 'scapy',
            'src_mac': self.vn1_vm1_fixture.mac_addr[
                self.vn1_fixture.vn_fq_name],
            'dst_mac': self.vn1_vm2_fixture.mac_addr[
                self.vn1_fixture.vn_fq_name],
            'src_compute_fixture': self.vn1_vm1_compute_fixture}
        # Change the FC for the qos-config entry
        qos_fixture.set_entries(dot1p_mapping=dot1p_map2)
        assert self.validate_packet_qos_marking(**validate_method_args)
        # Change FC's dot1p remark now
        fc_fixtures[1].update(dscp=12, dot1p=7)
        validate_method_args['expected_dscp'] = 12
        validate_method_args['expected_dot1p'] = 7
        assert self.validate_packet_qos_marking(**validate_method_args)
        # Change FC id
        fc_fixtures[1].update(fc_id=3)
        qos_fixture.set_entries(dot1p_mapping=dot1p_map3)
        assert self.validate_packet_qos_marking(**validate_method_args)
        # Add entry in Dot1P map tablee
        qos_fixture.add_entries(dot1p_mapping=dot1p_map4)
        validate_method_args['dot1p'] = dot1p_map4.keys()[0]
        validate_method_args['expected_dscp'] = fcs[0]['dscp']
        validate_method_args['expected_dot1p'] = fcs[0]['dot1p']
        assert self.validate_packet_qos_marking(**validate_method_args)
    # end test_qos_config_and_fc_update_for_dot1p

    @preposttest_wrapper
    def test_invalid_range_for_fc(self):
        '''
        Validate that incorrect values while configuring Forwarding class
        are not accepted:
        Verify following:
        1. To verify that FC ID more than 255 is not accepted
        2. To verify that FC ID as negative value is not accepted
        3. To verify that FC ID as string is not accepted
        4. To verify that DSCP more than 63 is not accepted
        5. To verify that Dot1p more than 7 is not accepted
        6. To verify that exp more than 8 is not accepted
        7. To verify that negative values for dscp,dot1p and exp
            are not accepted
        8. To verify that string values for dscp,dot1p and exp
            are not accepted
        '''
        fc_list = []
        fc_list.append([{'fc_id': 256, 'dscp': 10, 'dot1p': 4, 'exp': 1}])
        fc_list.append([{'fc_id': -1, 'dscp': 10, 'dot1p': 4, 'exp': 1}])
        fc_list.append([{'fc_id': "string", 'dscp': 10, 'dot1p': 4, 'exp': 1}])
        fc_list.append([{'fc_id': 1, 'dscp': 64, 'dot1p': 4, 'exp': 1}])
        fc_list.append([{'fc_id': 2, 'dscp': 62, 'dot1p': 8, 'exp': 1}])
        fc_list.append([{'fc_id': 3, 'dscp': 62, 'dot1p': 4, 'exp': 8}])
        fc_list.append([{'fc_id': 4, 'dscp': -1, 'dot1p': -1, 'exp': -1}])
        fc_list.append([{'fc_id': 5, 'dscp': "x", 'dot1p': "y", 'exp': "z"}])
        for elem in fc_list:
            try:
                import pdb
                pdb.set_trace()
                self.setup_fcs(elem)
                self.logger.error("Creation of invalid FC '%s' passed" % elem)
                assert False, "FC with invalid values got created"
            except BadRequest, e:
                self.logger.debug(e)
                self.logger.debug("Creation of invalid FC '%s' failed as expected"
                                  % elem)
    # end test_invalid_range_for_qc_and_fc

    @preposttest_wrapper
    def test_invalid_range_for_qc(self):
        '''
        Validate that incorrect values while configuring Qos config are 
        not accepted:
        Verify following:
        1. To verify that DSCP > 63 in dscp map is not accepted
        2. To verify that Dot1P > 8 in dot1p map is not accepted
        3. To verify that EXP > 8 in exp map is not accepted
        4. To verify that negative value for any map is not accepted
        5. To verify that string value for any map is not accepted
        6. To verify that negative FC value in map is not accepted
        7. To verify that string FC value in map is not accepted
        8. To verify that FC ID in map should not be more than 255
        '''
        maps = [{'dscp_map': {64: 4}},
                {'dot1p_map': {8: 4}},
                {'exp_map': {8: 4}},
                {'dscp_map': {-1: 4}, 'dot1p_map':
                    {-1: 4}, 'exp_map': {-1: 4}},
                {'dscp_map': {"x": 4}, 'dot1p_map':
                 {"y": 4}, 'exp_map': {"z": 4}},
                {'dscp_map': {63: -1}, 'dot1p_map':
                 {7: -1}, 'exp_map': {7: -1}},
                {'dscp_map': {63: "x"}, 'dot1p_map':
                 {7: "y"}, 'exp_map': {7: "z"}},
                {'dscp_map': {64: 4}}]
        for elem in maps:
            try:
                qos_fixture = self.setup_qos_config(**elem)
                self.logger.error("Creation of invalid QC with map '%s'"
                                  "passed" % elem)
                assert False, "QC with invalid values got created"
            except BadRequest, e:
                self.logger.debug(e)
                self.logger.debug("Creation of invalid QC with map '%s'"
                                  " failed as expected" % elem)
    # end test_invalid_range_for_qc

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
        fcs = [{'fc_id': 0, 'dscp': 9, 'dot1p': 3, 'exp': 3},
               {'fc_id': 1, 'dscp': 10, 'dot1p': 4, 'exp': 1}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {30: 1}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        vm1_vmi_id = self.vn1_vm1_fixture.get_vmi_ids().values()[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        validate_method_args = {
            'src_vm_fixture': self.vn1_vm1_fixture,
            'dest_vm_fixture': self.vn1_vm2_fixture,
            'dscp': dscp_map.keys()[0],
            'expected_dscp': fcs[1]['dscp'],
            'expected_dot1p': fcs[1]['dot1p'],
            'src_compute_fixture': self.vn1_vm1_compute_fixture,
            'encap': "VxLAN"}
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
        fcs = [{'fc_id': 1, 'dscp': 9, 'dot1p': 3, 'exp': 3},
               {'fc_id': 2, 'dscp': 10, 'dot1p': 4, 'exp': 4},
               {'fc_id': 3, 'dscp': 11, 'dot1p': 5, 'exp': 5}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {30: 2}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map,
                                            default_fc_id=1)
        vm1_vmi_id = self.vn1_vm1_fixture.get_vmi_ids().values()[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        validate_method_args = {
            'src_vm_fixture': self.vn1_vm1_fixture,
            'dest_vm_fixture': self.vn1_vm2_fixture,
            'dscp': 40,
            'expected_dscp': fcs[0]['dscp'],
            'expected_dot1p': fcs[0]['dot1p'],
            'src_compute_fixture': self.vn1_vm1_compute_fixture,
            'encap': "VxLAN"}
        assert self.validate_packet_qos_marking(**validate_method_args)
        qos_fixture.set_default_fc(3)
        validate_method_args['expected_dscp'] = fcs[2]['dscp']
        validate_method_args['expected_dot1p'] = fcs[2]['dot1p']
        assert self.validate_packet_qos_marking(**validate_method_args)
        validate_method_args['dscp'] = dscp_map.keys()[0]
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
        fcs = [{'fc_id': 1, 'dscp': 10, 'dot1p': 5, 'exp': 1},
               {'fc_id': 2, 'dscp': 20, 'dot1p': 6, 'exp': 2}]
        self.setup_fcs(fcs)
        dscp_map_vmi = {1: 1}
        dscp_map_vhost = {0: 2}
        qos_fixture1 = self.setup_qos_config(dscp_map=dscp_map_vmi)
        qos_fixture2 = self.setup_qos_config(dscp_map=dscp_map_vhost,
                                             qos_config_type='vhost')
        vn1_vm1_vmi_id = self.vn1_vm1_fixture.get_vmi_ids().values()[0]
        self.setup_qos_config_on_vmi(qos_fixture1, vn1_vm1_vmi_id)
        validate_method_args = {
            'src_vm_fixture': self.vn1_vm1_fixture,
            'dest_vm_fixture': self.vn1_vm2_fixture,
            'dscp': dscp_map_vmi.keys()[0],
            'expected_dscp': fcs[0]['dscp'],
            'expected_dot1p': fcs[0]['dot1p'],
            'src_compute_fixture': self.vn1_vm1_compute_fixture}
        assert self.validate_packet_qos_marking(**validate_method_args)
        interface = self.vn1_vm1_compute_fixture.agent_physical_interface
        username = self.inputs.host_data[self.vn1_vm1_compute_fixture.ip]\
                                        ['username']
        password = self.inputs.host_data[self.vn1_vm1_compute_fixture.ip]\
                                        ['password']
        traffic_obj = TrafficAnalyzer(interface,
                                      self.vn1_vm1_compute_fixture,
                                      username,
                                      password,
                                      src_ip=self.inputs.compute_control_ips[
                                          0],
                                      dest_port=5269,
                                      protocol='tcp',
                                      logger=self.logger)
        traffic_obj.packet_capture_start()
        sleep(10)
        traffic_obj.packet_capture_stop()
        assert traffic_obj.verify_packets("dot1p_dscp",
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

    @preposttest_wrapper
    def test_forwarding_class_scaling(self):
        '''
        Verify Scaling limits for Forwarding class
        Steps:
        1. Create 256 forwarding class entries
        2. Map all 256 FC entries to some qos-config
        '''
        fc_already_present = []
        for k in range(0, 256):
            if self.agent_inspect[self.inputs.compute_ips[0]]\
                    .get_vrouter_forwarding_class(k):
                fc_already_present.append(k)
        fc_fixtures = []
        qos_fixtures = []
        for i in range(0, 4):
            for k in range(0, 64):
                fc_dict = {
                    'name': "FC_Test_" + str(i * 64 + k), 'fc_id': i * 64 + k,
                    'dscp': k, 'exp': i, 'dot1p': i}
                if i * 64 + k not in fc_already_present:
                    fc_fixtures.append(self.setup_fcs([fc_dict]))
                    # Configuration takes some time to reflect in agent.
        for elem in fc_fixtures:
            assert elem[0].verify_on_setup()
        for i in range(0, 256):
            dscp_map = {10: i}
            if i not in fc_already_present:
                qos_fixtures.append(self.setup_qos_config(name=
                                                    "qos_config_" + str(i),
                                                    dscp_map=dscp_map))
        for elem in qos_fixtures:
            assert elem.verify_on_setup()
    # end test_forwarding_class_scaling

    @preposttest_wrapper
    def test_qos_config_scaling(self):
        '''
        Verify Scaling limits for Forwarding class
        Steps:
        1. Create few forwarding class entries.
        2. Create all type of mappings to be used in qos_map
        3. Configure 4K qos config tables with 80 entries in each table
        4. Associate each qos-config with a VN
        '''
        fcs = []
        qos_fixtures = []
        qc_already_present = []
        for k in range(0, 4000):
            if self.agent_inspect[self.inputs.compute_ips[0]]\
                    .get_vrouter_qos_config(k):
                qc_already_present.append(k)
        dscp_map, dot1p_map, exp_map = {}, {}, {}
        for k in range(0, 80):
            if k < 64:
                fc_dict = {'name': "FC_Test_" + str(k), 'fc_id': k, 'dscp': k}
                dscp_map[k] = k
            elif k >= 64 and k < 72:
                fc_dict = {'name': "FC_Test_" +
                           str(k), 'fc_id': k, 'dot1p': k - 64}
                dot1p_map[k - 64] = k - 64
            elif k >= 72:
                fc_dict = {'name': "FC_Test_" +
                           str(k), 'fc_id': k, 'exp': k - 72}
                exp_map[k - 72] = k - 72
            fcs.append(fc_dict)
        fc_fixtures = self.setup_fcs(fcs)
        for fc in fc_fixtures:
            assert fc.verify_on_setup()
        for i in range(0, 100):
            if i not in qc_already_present:
                qos_fixtures.append(self.setup_qos_config(
                    name="qos_config_" + str(i),
                    dscp_map=dscp_map,
                    dot1p_map=dot1p_map,
                    exp_map=exp_map))
        for qos_fixture in qos_fixtures:
            assert qos_fixture.verify_on_setup()
            vn_fixture = self.create_vn()
            self.setup_qos_config_on_vn(qos_fixture, vn_fixture.uuid)
    # end test_qos_config_scaling


class TestQosPolicy(TestQosPolicyBase):

    @classmethod
    def setUpClass(cls):
        super(TestQosPolicy, cls).setUpClass()
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
        fcs = [
            {'name': "FC1_Test", 'fc_id': 10,
                'dscp': 62, 'dot1p': 6, 'exp': 6},
            {'name': "FC2_Test", 'fc_id': 11, 'dscp': 2, 'dot1p': 4, 'exp': 4}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map1 = {0: 10, 1: 10, 2: 10, 3: 10, 4:
                     10, 5: 10, 6: 10, 7: 10, 8: 10, 9: 10}
        dscp_map2 = {0: 11, 1: 11, 2: 11, 3: 11, 4:
                     11, 5: 11, 6: 11, 7: 11, 8: 11, 9: 11}
        dscp_map3 = {0: 12, 1: 12, 2: 12, 3: 12, 4:
                     12, 5: 12, 6: 12, 7: 12, 8: 12, 9: 12}
        dscp_map4 = {10: 10, 11: 10, 12: 10, 13: 10, 14:
                     10, 15: 10, 16: 10, 17: 10, 18: 10, 19: 10}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map1)
        self.update_policy_qos_config(self.policy_fixture, qos_fixture)
        validate_method_args = {
            'src_vm_fixture': self.vn1_vm1_fixture,
            'dest_vm_fixture': self.vn2_vm1_fixture,
            'dscp': dscp_map1.keys()[9],
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
        fc_fixtures[1].update(fc_id=12)
        qos_fixture.set_entries(dscp_mapping=dscp_map3)
        assert self.validate_packet_qos_marking(**validate_method_args)
        # Adding more entries in qos-config
        qos_fixture.add_entries(dscp_mapping=dscp_map4)
        assert self.validate_packet_qos_marking(**validate_method_args)
        validate_method_args['dscp'] = dscp_map4.keys()[9]
        validate_method_args['expected_dscp'] = fcs[0]['dscp']
        validate_method_args['expected_exp'] = fcs[0]['exp']
        validate_method_args['expected_dot1p'] = fcs[0]['dot1p']
        assert self.validate_packet_qos_marking(**validate_method_args)
    # end test_qos_config_and_fc_update_for_dscp_map_on_policy

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
            'encap': "MPLSoUDP"}
        for i in range(1, 63):
            validate_method_args['expected_dscp'] = i
            validate_method_args['dscp'] = 63 - i
            assert self.validate_packet_qos_marking(**validate_method_args)
    # end test_qos_config_on_policy_for_all_dscp_entries

    @preposttest_wrapper
    def test_qos_vmi_precedence_over_policy_over_vn(self):
        ''' Create qos-config1 for remarking DSCP 1 to fc1(DSCP 10)
            Create qos-config2 for remarking DSCP 1 to fc2(DSCP 20)
            Apply qos-config1 to vmi and qos-config2 to VN
            Validate that qos-config1's dscp rewrite is applied
        '''
        fcs = [
            {'name': "FC1_Test", 'fc_id': 10,
                'dscp': 62, 'dot1p': 7, 'exp': 7},
            {'name': "FC2_Test", 'fc_id': 11,
             'dscp': 2, 'dot1p': 5, 'exp': 5},
            {'name': "FC3_Test", 'fc_id': 12, 'dscp': 30, 'dot1p': 3, 'exp': 3}]
        self.setup_fcs(fcs)
        dscp_map_vmi = {49: 10}
        dscp_map_vn = {49: 11}
        dscp_map_policy = {49: 12}
        qos_fixture1 = self.setup_qos_config(dscp_map=dscp_map_vmi)
        qos_fixture2 = self.setup_qos_config(dscp_map=dscp_map_vn)
        qos_fixture3 = self.setup_qos_config(dscp_map=dscp_map_policy)
        vn1_vm_vmi_id = self.vn1_vm1_fixture.get_vmi_ids().values()[0]
        self.setup_qos_config_on_vmi(qos_fixture1, vn1_vm_vmi_id)
        self.setup_qos_config_on_vn(qos_fixture2, self.vn1_fixture.uuid)
        self.update_policy_qos_config(self.policy_fixture, qos_fixture3)
        validate_method_args = {
            'src_vm_fixture': self.vn1_vm1_fixture,
            'dest_vm_fixture': self.vn2_vm1_fixture,
            'dscp': dscp_map_vmi.keys()[0],
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
        fcs = [{'name': "FC1_Test", 'fc_id': 10,
                'dscp': 62, 'dot1p': 6, 'exp': 6}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {0: 10, 1: 10, 2: 10, 3: 10, 4:
                    10, 5: 10, 6: 10, 7: 10, 8: 10, 9: 10}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        self.update_policy_qos_config(self.policy_fixture, qos_fixture,
                                      entry_index=1)
        validate_method_args = {
            'src_vm_fixture': self.vn1_vm1_fixture,
            'dest_vm_fixture': self.vn2_vm1_fixture,
            'dscp': dscp_map.keys()[9],
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
        fcs = [{'name': "FC_Test", 'fc_id': 10,
                'dscp': 62, 'dot1p': 7, 'exp': 3}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {0: 10, 1: 10, 2: 10, 3: 10, 4:
                    10, 5: 10, 6: 10, 7: 10, 8: 10, 9: 10}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        # Getting the VMI of Service Instance
        cs_si = self.si_fixture.api_s_inspect.get_cs_si(
            project=self.inputs.project_name,
            si=self.si_fixture.si_name,
            refresh=True)
        vm_refs = cs_si['service-instance']['virtual_machine_back_refs']
        svm_ids = [vm_ref['to'][0] for vm_ref in vm_refs]
        cs_svm = self.si_fixture.api_s_inspect.get_cs_vm(
            vm_id=svm_ids[0], refresh=True)
        cs_svmis = cs_svm[
            'virtual-machine']['virtual_machine_interface_back_refs']
        for svmi in cs_svmis:
            if 'right' in svmi['to'][2]:
                right_svmi = svmi['uuid']
                break
        # Getting the SI node IP to check traffic flow on that node
        vm_obj = self.connections.orch.get_vm_by_id(svm_ids[0])
        si_vm_node = self.connections.orch.get_host_of_vm(vm_obj)
        si_vm_node_ip = self.inputs.get_host_ip(si_vm_node)
        si_source_compute_fixture = self.useFixture(ComputeNodeFixture(
            self.connections,
            si_vm_node_ip))
        # Applying qos-config on right VMI of service instance
        self.setup_qos_config_on_vmi(qos_fixture, right_svmi)
        si_right_vrf_id = self.agent_inspect[
            si_vm_node_ip].get_vna_vrf_objs(
            project=self.project.project_name,
            vn_name=self.vn2_fixture.vn_name
        )['vrf_list'][0]['ucindex']
        assert self.validate_packet_qos_marking(
            src_vm_fixture=self.vn1_vm1_fixture,
            dest_vm_fixture=self.vn2_vm1_fixture,
            dscp=dscp_map.keys()[9],
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
        fcs = [{'name': "FC_Test", 'fc_id': 10,
                'dscp': 62, 'dot1p': 7, 'exp': 3}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {0: 10, 1: 10, 2: 10, 3: 10, 4:
                    10, 5: 10, 6: 10, 7: 10, 8: 10, 9: 10}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        self.update_policy_qos_config(self.policy_fixture, qos_fixture)
        # verifying marking on packets from SI to right VN
        si_vm_node_ip = self.inputs.compute_ips[0]
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
            'dscp': dscp_map.keys()[9],
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
