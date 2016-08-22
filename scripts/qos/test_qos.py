from tcutils.wrappers import preposttest_wrapper
from compute_node_test import ComputeNodeFixture

from common.qos.base import *

from svc_instance_fixture import SvcInstanceFixture
from svc_template_fixture import SvcTemplateFixture
from policy_test import PolicyFixture
from vn_policy_test import VN_Policy_Fixture
from security_group import SecurityGroupFixture

from tcutils.traffic_utils.scapy_traffic_gen import ScapyTraffic

class QosTestExtendedBase(QosTestBase):
    @classmethod
    def setUpClass(cls):
        cls.setupClass_is_run = False
        super(QosTestExtendedBase, cls).setUpClass()
        if len(cls.inputs.compute_names) < 2 :
            cls.inputs.logger.warn('Cannot setup env since cluster has less'
                ' than 2 compute nodes')
            return
        cls.setupClass_is_run = True
        cls.vnc_api_h = cls.vnc_lib
        cls.inputs.address_family = "dual"
        cls.vn1_fixture = cls.create_only_vn()
        cls.vn2_fixture = cls.create_only_vn()
        cls.vn1_vm1_fixture = cls.create_only_vm(cls.vn1_fixture,
                                  node_name=cls.inputs.compute_names[0])
        cls.vn1_vm2_fixture = cls.create_only_vm(cls.vn1_fixture,
                                  node_name=cls.inputs.compute_names[1])
        cls.vn2_vm1_fixture = cls.create_only_vm(cls.vn2_fixture,
                                  node_name=cls.inputs.compute_names[1])
        cls.check_vms_booted([cls.vn1_vm1_fixture, cls.vn1_vm2_fixture,
                              cls.vn2_vm1_fixture])
        cls.vn1_vm1_compute_fixture = ComputeNodeFixture(
                                        cls.connections,
                                        cls.vn1_vm1_fixture.vm_node_ip)
        cls.vn1_vm1_compute_fixture.setUp()
        cls.vn1_vm2_compute_fixture = ComputeNodeFixture(
                                        cls.connections,
                                        cls.vn1_vm2_fixture.vm_node_ip)
        cls.vn1_vm2_compute_fixture.setUp()
        cls.vn2_vm1_compute_fixture = ComputeNodeFixture(
                                        cls.connections,
                                        cls.vn2_vm1_fixture.vm_node_ip)
        cls.vn2_vm1_compute_fixture.setUp()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        if not cls.setupClass_is_run:
            return
        cls.inputs.address_family = "v4"
        cls.vn2_vm1_compute_fixture.cleanUp()
        cls.vn1_vm2_compute_fixture.cleanUp()
        cls.vn1_vm1_compute_fixture.cleanUp()
        cls.vn2_vm1_fixture.cleanUp()
        cls.vn1_vm2_fixture.cleanUp()
        cls.vn1_vm1_fixture.cleanUp()
        cls.vn2_fixture.cleanUp()
        cls.vn1_fixture.cleanUp()
        super(QosTestExtendedBase, cls).tearDownClass()
    # end tearDownClass

    def is_test_applicable(self):
        if len(self.inputs.compute_ips) < 2:
            return (False, 'Skipping tests since cluster has less than 2 '
                'compute nodes')
        else:
            return (True, None)
    # end is_test_applicable


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
        fcs = [ {'fc_id':10, 'dscp': 10, 'dot1p': 1, 'exp': 1}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = { 1: 10 }
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        vm1_vmi_id = self.vn1_vm1_fixture.get_vmi_ids().values()[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        assert self.validate_packet_qos_marking(
                    src_vm_fixture=self.vn1_vm1_fixture,
                    dest_vm_fixture=self.vn1_vm2_fixture,
#                    count=1,
                    dscp=1,
                    expected_dscp=10,
                    expected_dot1p=1,
#                    protocol='tcp',
                    src_port='10000',
                    dest_port='20000',
                    src_compute_fixture=self.vn1_vm1_compute_fixture,
                    encap = "VxLAN")
    # end test_qos_remark_dscp_on_vmi
    
    @preposttest_wrapper
    def test_qos_remark_dscp_on_vmi_ipv6(self):
        ''' Create a qos config for remarking DSCP 1 to 10
            Have VMs A, B with IPv6 IPs configured
            Apply the qos config to VM A
            Validate that packets from A to B have DSCP marked correctly
        '''
        fcs = [ {'fc_id':10, 'dscp': 10, 'dot1p': 1, 'exp': 1}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = { 1: 10 }
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        vm1_vmi_id = self.vn1_vm1_fixture.get_vmi_ids().values()[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        assert self.validate_packet_qos_marking(
                    src_vm_fixture=self.vn1_vm1_fixture,
                    dest_vm_fixture=self.vn1_vm2_fixture,
                    traffic_generator = 'scapy',
                    dscp=1,
                    expected_dscp=10,
                    expected_dot1p=1,
                    src_compute_fixture=self.vn1_vm1_compute_fixture,
                    #encap = "VxLAN",
                    af ='ipv6',
                    src_mac = self.vn1_vm1_fixture.mac_addr[
                                    self.vn1_fixture.vn_fq_name],
                    dst_mac = self.vn1_vm2_fixture.mac_addr[
                                    self.vn1_fixture.vn_fq_name],
                    ipv6_src = str(self.vn1_vm1_fixture.vm_ips[1]),
                    ipv6_dst = str(self.vn1_vm2_fixture.vm_ips[1]))
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
        fcs = [ {'fc_id':10, 'dscp': 12, 'dot1p': 6, 'exp': 2}]
        fc_fixtures = self.setup_fcs(fcs)
        dot1p_map = { 2: 10 }
        qos_fixture = self.setup_qos_config(dot1p_map=dot1p_map)
        vm1_vmi_id = self.vn1_vm1_fixture.get_vmi_ids().values()[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        assert self.validate_packet_qos_marking(
                    src_vm_fixture=self.vn1_vm1_fixture,
                    dest_vm_fixture=self.vn1_vm2_fixture,
                    traffic_generator = 'scapy',
#                    count=1,
                    expected_dscp=12,
                    expected_dot1p=6,
                    src_compute_fixture=self.vn1_vm1_compute_fixture,
                    dot1p = 2,
                    src_mac = self.vn1_vm1_fixture.mac_addr[
                                    self.vn1_fixture.vn_fq_name],
                    dst_mac = self.vn1_vm2_fixture.mac_addr[
                                    self.vn1_fixture.vn_fq_name])
    # end test_qos_remark_dot1p_on_vmi

    @preposttest_wrapper
    def test_qos_remark_dscp_on_vn(self):
        ''' Create a qos config for remarking DSCP 1 to 10
            Have VMs A, B
            Apply the qos config to the VN
            Validate that packets from A to B have DSCP marked correctly
        '''
        fcs = [ {'fc_id':10, 'dscp': 10, 'dot1p': 1, 'exp': 1}]
        self.setup_fcs(fcs)
        dscp_map = { 1: 10 }
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        self.setup_qos_config_on_vn(qos_fixture, self.vn1_fixture.uuid)
        assert self.validate_packet_qos_marking(
                    src_vm_fixture=self.vn1_vm1_fixture,
                    dest_vm_fixture=self.vn1_vm2_fixture,
                    dscp=1,
                    expected_dscp=10,
                    expected_dot1p=1,
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
        fcs = [ {'fc_id':10, 'dscp': 23, 'dot1p': 3, 'exp': 7}]
        self.setup_fcs(fcs)
        dscp_map = { 10: 10 }
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        self.setup_qos_config_on_vn(qos_fixture, self.vn1_fixture.uuid)
        assert self.validate_packet_qos_marking(
                    src_vm_fixture=self.vn1_vm1_fixture,
                    dest_vm_fixture=self.vn1_vm2_fixture,
                    traffic_generator = 'scapy',
                    dscp=10,
                    expected_dscp=23,
                    expected_dot1p=3,
                    expected_exp=7,
                    src_compute_fixture=self.vn1_vm1_compute_fixture,
                    #encap = "VxLAN",
                    af ='ipv6',
                    src_mac = self.vn1_vm1_fixture.mac_addr[
                                    self.vn1_fixture.vn_fq_name],
                    ipv6_src = str(self.vn1_vm1_fixture.vm_ips[1]),
                    ipv6_dst = str(self.vn1_vm2_fixture.vm_ips[1]))
    # end test_qos_remark_dscp_on_vn_ipv6
    
    @preposttest_wrapper
    def test_qos_remark_dot1p_on_vn(self):
        ''' Create a qos config for remarking Dot1p 3 to 5
            Have VMs A, B
            Apply the qos config to the VN
            Validate that packets from A to B have Dot1P marked correctly
        '''
        fcs = [ {'fc_id':10, 'dscp': 23, 'dot1p': 5, 'exp': 3}]
        self.setup_fcs(fcs)
        dot1p_map = { 3: 10 }
        qos_fixture = self.setup_qos_config(dot1p_map=dot1p_map)
        self.setup_qos_config_on_vn(qos_fixture, self.vn1_fixture.uuid)
        assert self.validate_packet_qos_marking(
                    src_vm_fixture=self.vn1_vm1_fixture,
                    dest_vm_fixture=self.vn1_vm2_fixture,
                    traffic_generator = 'scapy',
#                    count=1,
                    expected_dscp=23,
                    expected_dot1p=5,
                    expected_exp=3,
                    src_compute_fixture=self.vn1_vm1_compute_fixture,
                    dot1p = 3,
                    src_mac = self.vn1_vm1_fixture.mac_addr[
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
        fcs = [ {'fc_id':1, 'dscp': 10, 'dot1p': 1, 'exp': 1},
                {'fc_id':2, 'dscp': 11, 'dot1p': 1, 'exp': 1}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map1 = { 1: 1 }
        dscp_map2 = { 1: 2 }
        dscp_map3 = { 1: 3 }
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map1)
        vm1_vmi_id = self.vn1_vm1_fixture.get_vmi_ids().values()[0]
        self.setup_qos_config_on_vmi(qos_fixture, vm1_vmi_id)
        # Change the FC for the qos-config entry
        qos_fixture.set_entries(dscp_mapping=dscp_map2)
        validate_method_args = {
            'src_vm_fixture':self.vn1_vm1_fixture,
            'dest_vm_fixture':self.vn1_vm2_fixture,
            'dscp': 1,
            'expected_dscp': fcs[1]['dscp'],
            'expected_dot1p': fcs[1]['dot1p'],
            'src_port':'10000',
            'dest_port':'20000',
            'src_compute_fixture': self.vn1_vm1_compute_fixture }
        self.validate_packet_qos_marking(**validate_method_args)
        # Change FC's dscp remark now
        fc_fixtures[1].update(dscp=12, dot1p=5)
        validate_method_args['expected_dscp'] = 12
        validate_method_args['expected_dot1p'] = 5
        self.validate_packet_qos_marking(**validate_method_args)
        # Change FC id 
        fc_fixtures[1].update(fc_id=3)
        qos_fixture.set_entries(dscp_mapping=dscp_map3)
        self.validate_packet_qos_marking(**validate_method_args)
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
        fcs = [ {'fc_id':1, 'dscp': 10, 'dot1p': 4, 'exp': 1},
                {'fc_id':2, 'dscp': 11, 'dot1p': 6, 'exp': 1}]
        fc_fixtures = self.setup_fcs(fcs)
        dot1p_map1 = { 1: 1 }
        dot1p_map2 = { 1: 2 }
        dot1p_map3 = { 1: 3 }
        dot1p_map4 = { 2: 1 }
        qos_fixture = self.setup_qos_config(dot1p_map=dot1p_map1)
        self.setup_qos_config_on_vn(qos_fixture, self.vn1_fixture.uuid)
        validate_method_args = {
            'src_vm_fixture':self.vn1_vm1_fixture,
            'dest_vm_fixture':self.vn1_vm2_fixture,
            'dot1p': 1,
            'expected_dscp': fcs[1]['dscp'],
            'expected_dot1p': fcs[1]['dot1p'],
            'traffic_generator' : 'scapy',
            'src_mac' : self.vn1_vm1_fixture.mac_addr[
                                    self.vn1_fixture.vn_fq_name],
            'dst_mac' : self.vn1_vm2_fixture.mac_addr[
                                    self.vn1_fixture.vn_fq_name],
            'src_compute_fixture' : self.vn1_vm1_compute_fixture }
        # Change the FC for the qos-config entry
        qos_fixture.set_entries(dot1p_mapping=dot1p_map2)
        self.validate_packet_qos_marking(**validate_method_args)
        # Change FC's dot1p remark now
        fc_fixtures[1].update(dscp=12, dot1p=7)
        validate_method_args['expected_dscp'] = 12
        validate_method_args['expected_dot1p'] = 7
        self.validate_packet_qos_marking(**validate_method_args)
        # Change FC id 
        fc_fixtures[1].update(fc_id=3)
        qos_fixture.set_entries(dot1p_mapping=dot1p_map3)
        self.validate_packet_qos_marking(**validate_method_args)
        # Add entry in Dot1P map tablee
        qos_fixture.add_entries(dot1p_mapping=dot1p_map4)
        validate_method_args['dot1p'] = 2
        validate_method_args['expected_dscp'] = 10
        validate_method_args['expected_dot1p'] = 4
        self.validate_packet_qos_marking(**validate_method_args)
    # end test_qos_config_and_fc_update_for_dot1p

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
        for k in range(0,256):
            if self.agent_inspect[self.inputs.compute_ips[0]]\
            .get_vrouter_forwarding_class(k):
                fc_already_present.append(k)
        for i in range(0,4):
            for k in range(0,64):
                fc_dict={'name':"FC_Test_"+str(i*64+k),'fc_id':i*64+k,
                         'dscp': k, 'exp':i, 'dot1p':i}
                if i*64+k not in fc_already_present:
                    fc_fixture = self.setup_fcs([fc_dict])
                    sleep(0.1) # Configuration takes some time to reflect in agent.
                    assert fc_fixture[0].verify_on_setup()
        for i in range(0,256):
            dscp_map = {10 : i}
            if i not in fc_already_present:
                qos_fixture = self.setup_qos_config(name = 
                                    "qos_config_"+str(i),
                                    dscp_map=dscp_map)
                sleep(0.1)
                assert qos_fixture.verify_on_setup()
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
        qc_already_present = []
        for k in range(0,4000):
            if self.agent_inspect[self.inputs.compute_ips[0]]\
            .get_vrouter_qos_config(k):
                qc_already_present.append(k)
        dscp_map, dot1p_map, exp_map  = {}, {}, {}
        for k in range(0,80):
            if k < 64:
                fc_dict={'name':"FC_Test_"+str(k),'fc_id':k,'dscp': k}
                dscp_map[k] = k
            elif k >=64 and k < 72:
                fc_dict={'name':"FC_Test_"+str(k),'fc_id':k,'dot1p': k-64}
                dot1p_map[k-64] = k-64
            elif k >=72:
                fc_dict={'name':"FC_Test_"+str(k),'fc_id':k,'exp': k-72}
                exp_map[k-72] = k-72
            fcs.append(fc_dict)
        fc_fixtures = self.setup_fcs(fcs)
        for fc in fc_fixtures:
            assert fc.verify_on_setup()
        for i in range(0,4000):
            if i not in qc_already_present:
                qos_fixture = self.setup_qos_config(name="qos_config_"+str(i),
                                                      dscp_map=dscp_map,
                                                      dot1p_map = dot1p_map,
                                                      exp_map = exp_map)
                sleep(0.1)
                assert qos_fixture.verify_on_setup()
                vn_fixture = self.create_only_vn()
                self.setup_qos_config_on_vn(qos_fixture, vn_fixture.uuid)
    # end test_qos_config_scaling

class TestQosPolicy(QosTestExtendedBase):
    
    @classmethod
    def setUpClass(cls):
        super(TestQosPolicy, cls).setUpClass()
        rules = [{'direction': '<>',
                  'protocol': 'any',
                  'dest_network': cls.vn1_fixture.vn_name,
                  'source_network': cls.vn2_fixture.vn_name,
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'}]
        cls.policy_fixture = PolicyFixture(
                            policy_name='policyTestQos',
                            rules_list=rules,
                            inputs=cls.inputs,
                            connections=cls.connections)
        cls.policy_fixture.setUp()
        cls.vn1_policy_fixture = VN_Policy_Fixture(
                            connections=cls.connections,
                            vn_name=cls.vn1_fixture.vn_name,
                            policy_obj={cls.vn1_fixture.vn_name :\
                                         [cls.policy_fixture.policy_obj]},
                            vn_obj={cls.vn1_fixture.vn_name : cls.vn1_fixture},
                            vn_policys=['policyTestQos'],
                            project_name=cls.project.project_name)
        cls.vn1_policy_fixture.setUp()
        cls.vn2_policy_fixture = VN_Policy_Fixture(
                            connections=cls.connections,
                            vn_name=cls.vn2_fixture.vn_name,
                            policy_obj={cls.vn2_fixture.vn_name : \
                                        [cls.policy_fixture.policy_obj]},
                            vn_obj={cls.vn2_fixture.vn_name : cls.vn2_fixture},
                            vn_policys=['policyTestQos'],
                            project_name=cls.project.project_name)
        cls.vn2_policy_fixture.setUp()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        if not cls.setupClass_is_run:
            return
        cls.vn1_policy_fixture.cleanUp()
        cls.vn2_policy_fixture.cleanUp()
        cls.policy_fixture.cleanUp()
        super(TestQosPolicy, cls).tearDownClass()
    # end tearDownClass

    @preposttest_wrapper
    def test_qos_config_and_fc_update_for_dscp_map_on_policy(self):
        ''' To test that qos config works correctly even after editing the
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
        fcs = [ {'name':"FC1_Test",'fc_id':10,'dscp': 62, 'dot1p': 6,'exp': 6},
               {'name':"FC2_Test",'fc_id':11,'dscp': 2,'dot1p': 4,'exp': 4}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map1 = { 0:10,1:10,2:10,3:10,4:10,5:10,6:10,7:10,8:10,9:10}
        dscp_map2 = { 0:11,1:11,2:11,3:11,4:11,5:11,6:11,7:11,8:11,9:11}
        dscp_map3 = { 0:12,1:12,2:12,3:12,4:12,5:12,6:12,7:12,8:12,9:12}
        dscp_map4 = { 10:10,11:10,12:10,13:10,14:10,15:10,16:10,17:10,18:10,19:10}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map1)
        self.update_policy_qos_config(self.policy_fixture, qos_fixture)
        validate_method_args = {
            'src_vm_fixture':self.vn1_vm1_fixture,
            'dest_vm_fixture':self.vn2_vm1_fixture,
            #'count': 30,
            'dscp': 9,
            'expected_dscp': fcs[0]['dscp'],
            'expected_exp': fcs[0]['exp'],
            'expected_dot1p': fcs[0]['dot1p'],
            #'protocol':'tcp',
            'src_compute_fixture' :self.vn1_vm1_compute_fixture}
        self.validate_packet_qos_marking(**validate_method_args)
        validate_method_args['expected_dscp'] = fcs[1]['dscp']
        validate_method_args['expected_exp'] = fcs[1]['exp']
        validate_method_args['expected_dot1p'] = fcs[1]['dot1p']
        # Change the FC for the qos-config entry
        qos_fixture.set_entries(dscp_mapping=dscp_map2)   
        self.validate_packet_qos_marking(**validate_method_args)
        # Change FC's dscp remark now
        fc_fixtures[1].update(dscp=12, exp =2, dot1p=2)
        validate_method_args['expected_dscp'] = 12
        validate_method_args['expected_exp'] = 2
        validate_method_args['expected_dot1p'] = 2
        self.validate_packet_qos_marking(**validate_method_args)
        # Change FC id 
        fc_fixtures[1].update(fc_id=12)
        qos_fixture.set_entries(dscp_mapping=dscp_map3)
        self.validate_packet_qos_marking(**validate_method_args)
        # Adding more entries in qos-config
        qos_fixture.add_entries(dscp_mapping=dscp_map4)
        self.validate_packet_qos_marking(**validate_method_args)
        
        validate_method_args['dscp'] = 19
        validate_method_args['expected_dscp'] = fcs[0]['dscp']
        validate_method_args['expected_exp'] = fcs[0]['exp']
        validate_method_args['expected_dot1p'] = fcs[0]['dot1p']
        self.validate_packet_qos_marking(**validate_method_args)
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
        for i in range(1,63):
            fc={'name':"FC_Test"+str(i),'fc_id':i,'dscp': i}
            fcs.append(fc)
            dscp_map[i] = 63-i
        fc_fixtures = self.setup_fcs(fcs)
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        self.update_policy_qos_config(self.policy_fixture, qos_fixture)      
        validate_method_args = {
            'src_vm_fixture':self.vn1_vm1_fixture,
            'dest_vm_fixture':self.vn2_vm1_fixture,
            #'count': 30,
            'dscp': None,
            'expected_dscp': None,
            'protocol':'tcp',
            'src_compute_fixture' :self.vn1_vm1_compute_fixture,
            'encap' : "MPLSoUDP"}
        for i in range(1,63):
            validate_method_args['expected_dscp'] = i
            validate_method_args['dscp'] = 63-i
            self.validate_packet_qos_marking(**validate_method_args)
    # end test_qos_config_on_policy_for_all_dscp_entries
         
    @preposttest_wrapper
    def test_qos_vmi_precedence_over_policy_over_vn(self):
        ''' Create qos-config1 for remarking DSCP 1 to fc1(DSCP 10)
            Create qos-config2 for remarking DSCP 1 to fc2(DSCP 20)
            Apply qos-config1 to vmi and qos-config2 to VN
            Validate that qos-config1's dscp rewrite is applied
        '''
        fcs = [{'name':"FC1_Test",'fc_id':10,'dscp': 62, 'dot1p': 7,'exp': 7},
               {'name':"FC2_Test",'fc_id':11,'dscp': 2,'dot1p': 5,'exp': 5},
               {'name':"FC3_Test",'fc_id':12,'dscp': 30,'dot1p': 3,'exp': 3}]
        self.setup_fcs(fcs)
        dscp_map_vmi = { 49: 10 }
        dscp_map_vn = { 49: 11 }
        dscp_map_policy = { 49: 12}
        qos_fixture1 = self.setup_qos_config(dscp_map=dscp_map_vmi)
        qos_fixture2 = self.setup_qos_config(dscp_map=dscp_map_vn)
        qos_fixture3 = self.setup_qos_config(dscp_map=dscp_map_policy)
        vn1_vm_vmi_id = self.vn1_vm1_fixture.get_vmi_ids().values()[0]
        self.setup_qos_config_on_vmi(qos_fixture1, vn1_vm_vmi_id)
        self.setup_qos_config_on_vn(qos_fixture2, self.vn1_fixture.uuid)
        self.update_policy_qos_config(self.policy_fixture, qos_fixture3)
        validate_method_args = {
            'src_vm_fixture':self.vn1_vm1_fixture,
            'dest_vm_fixture':self.vn2_vm1_fixture,
            #'count': 30,
            'dscp': 49,
            'expected_dscp': fcs[0]['dscp'],
            'expected_exp': fcs[0]['exp'],
            'expected_dot1p': fcs[0]['dot1p'],
            'protocol':'tcp',
            'src_compute_fixture':self.vn1_vm1_compute_fixture}
        self.validate_packet_qos_marking(**validate_method_args)
        # Once qos config on vmi is removed, the one on policy should be applied
        self.remove_qos_config_on_vmi(qos_fixture1, vn1_vm_vmi_id)
        validate_method_args['expected_dscp'] = fcs[2]['dscp']
        validate_method_args['expected_exp'] = fcs[2]['exp']
        validate_method_args['expected_dot1p'] = fcs[2]['dot1p']
        self.validate_packet_qos_marking(**validate_method_args)
        # Once qos config on policy is removed, the one on policy should be applied
        self.update_policy_qos_config(self.policy_fixture, qos_fixture3,\
                                       operation = "remove")
        validate_method_args['expected_dscp'] = fcs[1]['dscp']
        validate_method_args['expected_exp'] = fcs[1]['exp']
        validate_method_args['expected_dot1p'] = fcs[1]['dot1p']
        self.validate_packet_qos_marking(**validate_method_args)
    # end test_qos_vmi_precedence_over_policy_over_vn



class TestQosSVC(QosTestExtendedBase):
    
    @classmethod
    def setUpClass(cls):
        super(TestQosSVC, cls).setUpClass()
        if_list = [['left', False, False], ['right', False, False]]
        cls.st_fixture= SvcTemplateFixture(connections=cls.connections, inputs=cls.inputs,
                        domain_name=cls.inputs.domain_name, st_name="service_template", 
                        svc_img_name='ubuntu-in-net', svc_type='firewall',
                        if_list=if_list, svc_mode='in-network',
                        svc_scaling=False, flavor='contrail_flavor_2cpu', 
                        ordered_interfaces=True, availability_zone_enable = True)
        cls.st_fixture.setUp()
        cls.si_fixture= SvcInstanceFixture(connections=cls.connections, inputs=cls.inputs,
                        domain_name=cls.inputs.domain_name, project_name= cls.inputs.project_name,
                        si_name="service_instance", svc_template= cls.st_fixture.st_obj,
                        if_list=if_list, left_vn_name=cls.vn1_fixture.vn_fq_name,
                        right_vn_name=cls.vn2_fixture.vn_fq_name,
                        do_verify=True, max_inst=1, static_route=['None', 'None', 'None'],
                        availability_zone = "nova:"+cls.inputs.compute_names[0])
        cls.si_fixture.setUp()
        cls.si_fixture.verify_on_setup()
        cls.action_list =  [":".join(cls.si_fixture.si_fq_name)]
        rules = [{'direction': '<>',
                  'protocol': 'any',
                  'dest_network': cls.vn2_fixture.vn_name,
                  'source_network': cls.vn1_fixture.vn_name,
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any',
                  'action_list': {'apply_service': cls.action_list}}]
        cls.policy_fixture = PolicyFixture(
                            policy_name='policyTestQos',
                            rules_list=rules,
                            inputs=cls.inputs,
                            connections=cls.connections)
        cls.policy_fixture.setUp()
        cls.vn1_policy_fixture = VN_Policy_Fixture(
                            connections=cls.connections,
                            vn_name=cls.vn1_fixture.vn_name,
                            policy_obj={cls.vn1_fixture.vn_name :\
                                         [cls.policy_fixture.policy_obj]},
                            vn_obj={cls.vn1_fixture.vn_name : cls.vn1_fixture},
                            vn_policys=['policyTestQos'],
                            project_name=cls.project.project_name)
        cls.vn1_policy_fixture.setUp()
        cls.vn2_policy_fixture = VN_Policy_Fixture(
                            connections=cls.connections,
                            vn_name=cls.vn2_fixture.vn_name,
                            policy_obj={cls.vn2_fixture.vn_name : \
                                        [cls.policy_fixture.policy_obj]},
                            vn_obj={cls.vn2_fixture.vn_name : cls.vn2_fixture},
                            vn_policys=['policyTestQos'],
                            project_name=cls.project.project_name)
        cls.vn2_policy_fixture.setUp()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        if not cls.setupClass_is_run:
            return
        cls.vn1_policy_fixture.cleanUp()
        cls.vn2_policy_fixture.cleanUp()
        cls.policy_fixture.cleanUp()
        cls.si_fixture.cleanUp()
        cls.st_fixture.cleanUp()
        super(TestQosSVC, cls).tearDownClass()
    # end tearDownClass
    
    @preposttest_wrapper
    def test_qos_remark_with_dscp_map_on_vmi_of_si(self):
        '''Test that qos marking happens when qos config is applied on vmi
           interface of service instance.
           Steps:
           1.Create a Forwarding class with ID 10 to mark dscp as 62
           2.Create a qos config for remarking dscp 0-9 traffic to dscp 62.
           3.Validate that packets on fabric from Service instance VMi to
            node B have DSCP marked to 62
        '''
        fcs = [{'name':"FC_Test",'fc_id':10,'dscp': 62,'dot1p': 7,'exp': 3}]
        fc_fixtures = self.setup_fcs(fcs)
        dscp_map = {0:10,1:10,2:10,3:10,4:10,5:10,6:10,7:10,8:10,9:10}
        qos_fixture = self.setup_qos_config(dscp_map=dscp_map)
        ### Getting the VMI of Service Instance 
        cs_si = self.si_fixture.api_s_inspect.get_cs_si(
                        project= self.inputs.project_name,
                        si=self.si_fixture.si_name,
                        refresh=True)
        vm_refs = cs_si['service-instance']['virtual_machine_back_refs']
        svm_ids = [vm_ref['to'][0] for vm_ref in vm_refs]
        cs_svm = self.si_fixture.api_s_inspect.get_cs_vm(
                                vm_id=svm_ids[0], refresh=True)
        cs_svmis = cs_svm['virtual-machine']['virtual_machine_interface_back_refs']
        for svmi in cs_svmis:
            if 'right' in svmi['to'][2]:
                right_svmi = svmi['uuid']
                break
        ### Getting the SI node IP to check traffic flow on that node        
        vm_obj = self.connections.orch.get_vm_by_id(svm_ids[0])
        si_vm_node = self.connections.orch.get_host_of_vm(vm_obj)
        si_vm_node_ip = self.inputs.get_host_ip(si_vm_node)
        si_source_compute_fixture = self.useFixture(ComputeNodeFixture(
                                        self.connections,
                                        si_vm_node_ip))
        ## Applying qos-config on right VMI of service instance
        self.setup_qos_config_on_vmi(qos_fixture, right_svmi)
        si_right_vrf_id = self.agent_inspect[
                        si_vm_node_ip].get_vna_vrf_objs( \
                        project=self.project.project_name, 
                        vn_name=self.vn2_fixture.vn_name \
                        )['vrf_list'][0]['ucindex']
        assert self.validate_packet_qos_marking(
                    src_vm_fixture=self.vn1_vm1_fixture,
                    dest_vm_fixture=self.vn2_vm1_fixture,
                    #count=20,
                    dscp=9,
                    expected_dscp=62,
                    expected_exp=3,
                    expected_dot1p =7,
                    src_compute_fixture = si_source_compute_fixture,
                    #protocol='tcp',
                    vrf_id = si_right_vrf_id)
    # end test_qos_remark_with_dscp_map_on_vmi_of_si
    
