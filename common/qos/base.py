import re
from tcutils.util import Lock

from common.neutron.base import BaseNeutronTest
from compute_node_test import ComputeNodeFixture
from qos_fixture import QosForwardingClassFixture, QosConfigFixture

from tcutils.traffic_utils.traffic_analyzer import TrafficAnalyzer
from tcutils.traffic_utils.scapy_traffic_gen import ScapyTraffic
from tcutils.traffic_utils.hping_traffic import Hping3

from time import sleep
from netaddr import *

from svc_instance_fixture import SvcInstanceFixture
from svc_template_fixture import SvcTemplateFixture
from policy_test import PolicyFixture
from vn_policy_test import VN_Policy_Fixture

class QosTestBase(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(QosTestBase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(QosTestBase, cls).tearDownClass()
    # end tearDownClass

    def setup_fcs(self, fcs_list):
        fc_fixtures = []
        for fc_dict in fcs_list:
            fc_dict['connections'] = self.connections
            fc_fixture = self.useFixture(
                            QosForwardingClassFixture(**fc_dict))
            fc_fixtures.append(fc_fixture)
        return fc_fixtures
    # end 

    def setup_qos_config(self, name=None, dscp_map={}, dot1p_map={}, exp_map={},
                          **kwargs):
        ''' Helper to add and delete qos-config and forwarding-class objects
        '''
        qos_config_fixture = self.useFixture(QosConfigFixture(name=name,
                                             dscp_mapping=dscp_map,
                                             dot1p_mapping=dot1p_map,
                                             exp_mapping=exp_map,
                                             connections=self.connections,
                                             **kwargs))
        return qos_config_fixture
    # end setup_qos_config 

    def setup_qos_config_on_vmi(self, qos_fixture, vmi_uuid):
        ret_val = qos_fixture.apply_to_vmi(vmi_uuid)
        self.addCleanup(qos_fixture.remove_from_vmi, vmi_uuid)
        return ret_val
    # end setup_qos_config_on_vmi

    def remove_qos_config_on_vmi(self, qos_fixture, vmi_uuid):
        self._remove_from_cleanup(qos_fixture.remove_from_vmi, vmi_uuid)
        return qos_fixture.remove_from_vmi(vmi_uuid)

    def setup_qos_config_on_vn(self, qos_fixture, vn_uuid):
        ret_val = qos_fixture.apply_to_vn(vn_uuid)
        self.addCleanup(qos_fixture.remove_from_vn, vn_uuid)
        return ret_val
    # end setup_qos_config_on_vn

    def remove_qos_config_on_vn(self, qos_fixture, vn_uuid):
        self._remove_from_cleanup(qos_fixture.remove_from_vn, vn_uuid)
        return qos_fixture.remove_from_vn(vn_uuid)

    def delete_qos_config(self, qos_fixture):
        qos_fixture.cleanUp()
        self._remove_from_cleanup(qos_fixture.cleanUp)
    # end delete_qos_config
    
    def validate_packet_qos_marking(self,
                                    src_vm_fixture,
                                    dest_vm_fixture,
                                    traffic_generator = "hping",
                                    dest_ip=None,
                                    count=30000,
                                    dscp=None,
                                    dot1p=None,
                                    exp=None,
                                    protocol='udp',
                                    src_port=None,
                                    dest_port=None,
                                    src_compute_fixture=None,
                                    expected_dscp=None,
                                    expected_dot1p=None,
                                    expected_exp=None,
                                    encap = None,
                                    vrf_id = None,
                                    af = "ipv4",
                                    **kwargs):
        '''
            dest_compute_fixture should be supplied if underlay traffic is 
            being checked
            dest_vm_fixture should be supplied if traffic is being checked for a
            specific estination VM
            
            Few things to note:
            1. traffic_generator can be "scapy" or "hping"
            2. "scapy" is specifically used here to test l2 and IPv6 traffic only.
               For all other traffic, hping is being used.
        '''
        interval = kwargs.get('interval', 1)
        src_mac = kwargs.get('src_mac', "11:22:33:44:55:66")
        dst_mac = kwargs.get('dst_mac', "ff:ff:ff:ff:ff:ff")
        ipv6_src = kwargs.get('ipv6_src', None)
        ipv6_dst = kwargs.get('ipv6_dst', None)
        src_vm_cidr = src_vm_fixture.vn_objs[0]['network']\
                        ['contrail:subnet_ipam'][0]['subnet_cidr']
        dest_vm_cidr = dest_vm_fixture.vn_objs[0]['network']\
                        ['contrail:subnet_ipam'][0]['subnet_cidr']
        if IPNetwork(src_vm_cidr) == IPNetwork(dest_vm_cidr):
            traffic_between_diff_networks = False
        else:
            traffic_between_diff_networks = True
        #src_vm_interface = kwargs.get('src_vm_interface', "eth0")
        # TCP is anyway the default for hping3
        icmp = False; tcp = False; udp = False
        if protocol == 'icmp': icmp = True
        if protocol == 'udp': udp = True
        if isinstance(dscp,int):
            tos = format(dscp << 2, 'x')
        else:
            tos = None
        if not src_compute_fixture and src_vm_fixture:
            src_compute_fixture = self.useFixture(ComputeNodeFixture(
                                        self.connections,
                                        src_vm_fixture.vm_node_ip))
        username = self.inputs.host_data[src_compute_fixture.ip]['username']
        password = self.inputs.host_data[src_compute_fixture.ip]['password']
        interface = src_compute_fixture.agent_physical_interface
        src_ip = src_vm_fixture.vm_ip
        dest_ip = dest_ip or dest_vm_fixture.vm_ip
        if traffic_generator == "scapy":
            self.logger.debug("Generating L2 only stream and ignoring all"
                              " other parameters of layers above L2")
            dot1p = dot1p or 0
            ether = {'src':src_mac, 'dst':dst_mac}
            dot1q = {'prio':dot1p, 'vlan':100}
            ipv6 = {}
            udp_header = {}
            if af == "ipv6":
                tos = int(tos,16) if dscp else 0
                ipv6 = {'tc':tos, 'src':ipv6_src, 'dst':ipv6_dst}
                ## WA for Bug 1614472. Internal protocol inside IPv6 is must
                udp_header = {'sport' : 1234}
            offset =156 if ipv6 else 100
            traffic_obj, scapy_obj = self._generate_scapy_traffic(
                                                        src_vm_fixture, 
                                                        src_compute_fixture,
                                                        interface,
                                                        encap = encap, 
                                                        interval=interval,
                                                        count=count, 
                                                        ether = ether,
                                                        dot1q = dot1q,
                                                        ipv6 = ipv6,
                                                        udp = udp_header)
            session,pcap = traffic_obj.packet_capture_start(
                                    capture_on_payload = True,
                                    signature_string ='5a5a5a5a5a5a5a5a',
                                    offset = offset,
                                    bytes_to_match = 8,
                                    min_length = 100,
                                    max_length = 250)
        elif traffic_generator == "hping":
            traffic_obj, hping_obj = self._generate_hping_traffic(
                                                        src_vm_fixture,
                                                        src_compute_fixture,
                                                        interface,
                                                        dest_ip =dest_ip,
                                                        src_port = src_port,
                                                        dest_port = dest_port,
                                                        encap = encap,
                                                        interval = interval,
                                                        count = count,
                                                        proto = protocol,
                                                        vrf_id = vrf_id,
                                                        udp = udp,
                                                        tos = tos)
            session,pcap = traffic_obj.packet_capture_start(
                                    traffic_between_diff_networks =
                                     traffic_between_diff_networks)
        sleep(5)
        traffic_obj.packet_capture_stop()
        if traffic_generator == "scapy":
            scapy_obj.stop()
        elif traffic_generator == "hping":
            (stats, hping_log) = hping_obj.stop()
        if isinstance(expected_dscp,int):
            result = traffic_obj.verify_packets('dscp',
                                                pcap_path_with_file_name = pcap,
                                                expected_count=1,
                                                dscp=expected_dscp)
            assert result, 'DSCP remarking checks failed. Please check logs'
        if isinstance(expected_dot1p,int):
            result = traffic_obj.verify_packets('dot1p',
                                                pcap_path_with_file_name = pcap,
                                                expected_count=1,
                                                dot1p=expected_dot1p)
            assert result, '802.1p remarking checks failed. Please check logs'
        if isinstance(expected_exp,int):
            result = traffic_obj.verify_packets('exp',
                                                pcap_path_with_file_name = pcap,
                                                expected_count=1,
                                                mpls_exp=expected_exp)
            assert result, 'MPLS exp remarking checks failed. Please check logs'
        self.inputs.run_cmd_on_server(src_compute_fixture.ip, "rm %s" % pcap,)
        return True
    # end validate_packet_qos_marking
    
    def _generate_scapy_traffic(self, src_vm_fixture, src_compute_fixture,
                                interface, encap = None, username = None,
                                password = None, interval=1, count=1, **kwargs):
        params = {}
        params['ether'] = kwargs.get('ether',{})
        params['dot1q'] = kwargs.get('dot1q',{})
        params['ip'] = kwargs.get('ip',{})
        params['ipv6'] = kwargs.get('ipv6',{})
        params['tcp'] = kwargs.get('tcp',{})
        params['udp'] = kwargs.get('udp',{})
        username = username or self.inputs.host_data[
                                    src_compute_fixture.ip]['username']
        password = password or self.inputs.host_data[
                                    src_compute_fixture.ip]['password']
        scapy_obj = ScapyTraffic(src_vm_fixture,
                                   interval= interval,
                                   count = count,
                                   **params)
        scapy_obj.start()
        traffic_obj = TrafficAnalyzer(interface,
                                    src_compute_fixture,
                                    username,
                                    password,
                                    logger=self.logger,
                                    encap_type = encap)
        return traffic_obj, scapy_obj
    
    def _generate_hping_traffic(self, src_vm_fixture, src_compute_fixture,
                                interface, dest_ip =None, src_port = None,
                                dest_port = None, encap = None, username = None,
                                password = None, interval=1, count=1,
                                vrf_id = None, proto = None, **kwargs):
        udp = kwargs.get('udp', False)
        tos = kwargs.get('tos', None)
        username = username or self.inputs.host_data[
                                    src_compute_fixture.ip]['username']
        password = password or self.inputs.host_data[
                                    src_compute_fixture.ip]['password']
        src_ip = src_vm_fixture.vm_ip
        hping_obj = Hping3(src_vm_fixture,
                             dest_ip,
                             destport=dest_port,
                             baseport=src_port,
                             count=count,
                             interval=interval,
                             udp=udp,
                             tos=tos,
                             keep=True,
                             numeric=True)
        hping_obj.start(wait=kwargs.get('wait', False))
        sleep(5)
        if encap == "MPLSoGRE":
            traffic_obj = TrafficAnalyzer(interface,
                                          src_compute_fixture,
                                          username,
                                          password,
                                          src_ip=src_ip,
                                          dest_ip=dest_ip,
                                          logger=self.logger,
                                          encap_type = encap)
        else:
            fwd_flow,rev_flow = src_compute_fixture.get_flow_entry(
                                    source_ip=src_ip,
                                    dest_ip=dest_ip,
                                    proto=proto,
                                    source_port=src_port,
                                    dest_port=dest_port,
                                    vrf_id=vrf_id)
            if not fwd_flow or not rev_flow:
                self.logger.error('Flow not created. Cannot proceed with analysis')
                return False
            src_port1 = fwd_flow.dump()['underlay_udp_sport']
            if src_port1 == '0':
                self.logger.error('Flow does not seem active..something is '
                                'wrong. Cannot proceed')
                self.logger.debug('Fwd flow :%s, Rev flow: %s' % (
                                fwd_flow.dump(), rev_flow.dump()))
                return False
            traffic_obj = TrafficAnalyzer(interface,
                                          src_compute_fixture,
                                          username,
                                          password,
                                          src_port=src_port1,
                                          protocol='udp',
                                          logger=self.logger,
                                          encap_type = encap)
        return traffic_obj, hping_obj
        
    def update_policy_qos_config(self, policy_fixture, qos_config_fixture, 
                                 operation = "add", entry_index =0):
        policy_entry = policy_fixture.policy_obj['policy']['entries']
        new_policy_entry = policy_entry
        if operation == "add":
            qos_obj_fq_name_str = self.vnc_lib.qos_config_read(
                                    id = qos_config_fixture.uuid).\
                                    get_fq_name_str()
            new_policy_entry['policy_rule'][entry_index]['action_list']\
                            ['qos_action'] = qos_obj_fq_name_str
        elif operation == "remove":
            new_policy_entry['policy_rule'][entry_index]['action_list']\
                            ['qos_action'] = ''
        policy_id = policy_fixture.policy_obj['policy']['id']
        policy_data = {'policy': {'entries': new_policy_entry}}
        policy_fixture.update_policy(policy_id, policy_data)
    
    def update_sg_qos_config(self, sg_fixture, qos_config_fixture, 
                             operation = "add"):
        sg_object = self.vnc_lib.security_group_read(id = sg_fixture.get_uuid())
        sg_rules = sg_object.get_security_group_entries().policy_rule
        if operation == "add":
            qos_obj_fq_name_str = self.vnc_lib.qos_config_read(
                                    id = qos_config_fixture.uuid).\
                                    get_fq_name_str()
            for elem in sg_rules:
                elem.action_list=ActionListType(qos_action=qos_obj_fq_name_str)
        elif operation == "remove":
            for elem in sg_rules:
                elem.action_list.qos_action = None
        sg_entries = sg_object.get_security_group_entries()
        sg_entries.set_policy_rule(sg_rules)
        sg_object.set_security_group_entries(sg_entries)
        self.vnc_lib.security_group_update(sg_object)

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
    
class TestQosPolicyBase(QosTestExtendedBase):
    
    @classmethod
    def setUpClass(cls):
        super(TestQosPolicyBase, cls).setUpClass()
        rules = [{'direction': '<>',
                  'protocol': 'udp',
                  'dest_network': cls.vn1_fixture.vn_name,
                  'source_network': cls.vn2_fixture.vn_name,
                  'dst_ports': 'any',
                  'simple_action': 'pass',
                  'src_ports': 'any'},
                 {'direction': '<>',
                  'protocol': 'tcp',
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
        super(TestQosPolicyBase, cls).tearDownClass()
    # end tearDownClass
    
class TestQosSVCBase(QosTestExtendedBase):
    
    @classmethod
    def setUpClass(cls):
        super(TestQosSVCBase, cls).setUpClass()
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
        super(TestQosSVCBase, cls).tearDownClass()
    # end tearDownClass
    
class FcIdGenerator():
    '''
        This class parse through the FCs present and 
        return a unique FC ID which is not in use.
    '''
    
    def __init__(self, vnc_lib):
        self.vnc_lib = vnc_lib
    
    def get_free_fc_ids(self, number):
        ''' "number" is number of free fc_ids to be returned'''
        try:
            file = '/tmp/fc_id.lock'
            lock = Lock(file)
            lock.acquire()
            fc_uuids = []
            for elem in self.vnc_lib.forwarding_classs_list()['forwarding-classs']:
                fc_uuids.append(elem['uuid'])
            fc_ids = []
            for elem in fc_uuids:
                fc_ids.append(self.vnc_lib.forwarding_class_read(id =elem).\
                            forwarding_class_id)
            returned_fc_ids = []
            count = 0
            for fc_id in range(0, 256):
                if number > 0:
                    if fc_id not in fc_ids:
                        returned_fc_ids.append(fc_id)
                        count = count +1
                        if count == number:
                            break
                else:
                    break
        finally:
            lock.release()
            return returned_fc_ids
