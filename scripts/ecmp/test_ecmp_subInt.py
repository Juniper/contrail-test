
from tcutils.wrappers import preposttest_wrapper

from common.vrouter.base import BaseVrouterTest
from tcutils.util import *
from svc_instance_fixture import SvcInstanceFixture
from svc_template_fixture import SvcTemplateFixture
from common.servicechain.config import ConfigSvcChain

# Use common vlan ids for all tests for now
VLAN_ID_101 = 101
VLAN_ID_102 = 102

class TestSubInterfacesECMP(BaseVrouterTest,ConfigSvcChain):

    @classmethod
    def setUpClass(cls):
        super(TestSubInterfacesECMP, cls).setUpClass()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestSubInterfacesECMP, cls).tearDownClass()

    def setUp(self):
        super(TestSubInterfacesECMP, self).setUp()
        # Sub interfaces are present on net1 and net2
        self.left_vn_fixture = self.create_only_vn(vn_name='left_vn', vn_subnets=['10.10.10.0/24'])
        self.right_vn_fixture = self.create_only_vn(vn_name='right_vn', vn_subnets=['20.20.20.0/24'])
        self.mgmt_vn_fixture = self.create_only_vn(vn_name='mgmt_vn', vn_subnets=['192.168.1.0/24'])
        self.net1_vn_fixture = self.create_only_vn(vn_name='net1_vn', vn_subnets=['1.1.1.0/24'])
        self.net2_vn_fixture = self.create_only_vn(vn_name='net2_vn', vn_subnets=['2.2.2.0/24'])

        self.left_vn_port = self.setup_only_vmi(self.left_vn_fixture.uuid)
        self.right_vn_port = self.setup_only_vmi(self.right_vn_fixture.uuid)
        self.mgmt_vn_port = self.setup_only_vmi(self.mgmt_vn_fixture.uuid)

        self.net1_port1 = self.setup_only_vmi(self.net1_vn_fixture.uuid)
        self.net1_subIntf1 = self.setup_only_vmi(self.left_vn_fixture.uuid,
                                       parent_vmi=self.net1_port1.vmi_obj,
                                       vlan_id=VLAN_ID_101,
                                       api_type='contrail',
                                       mac_address=self.net1_port1.mac_address)

        self.net1_subIntf2 = self.setup_only_vmi(self.left_vn_fixture.uuid,
                                       parent_vmi=self.net1_port1.vmi_obj,
                                       vlan_id=VLAN_ID_102,
                                       api_type='contrail',
                                       mac_address=self.net1_port1.mac_address)


        self.net2_port1 = self.setup_only_vmi(self.net2_vn_fixture.uuid)
        self.net2_subIntf1 = self.setup_only_vmi(self.right_vn_fixture.uuid,
                                       parent_vmi=self.net2_port1.vmi_obj,
                                       vlan_id=VLAN_ID_101,
                                       api_type='contrail',
                                       mac_address=self.net2_port1.mac_address)

        self.net2_subIntf2 = self.setup_only_vmi(self.right_vn_fixture.uuid,
                                       parent_vmi=self.net2_port1.vmi_obj,
                                       vlan_id=VLAN_ID_102,
                                       api_type='contrail',
                                       mac_address=self.net2_port1.mac_address)
        self.left_vm_fixture = self.create_vm(vn_objs=[self.left_vn_fixture.obj],
                                         image_name='cirros',
                                         port_ids=[self.left_vn_port.uuid])
        self.right_vm_fixture = self.create_vm(vn_objs=[self.right_vn_fixture.obj],
                                         image_name='cirros',
                                         port_ids=[self.right_vn_port.uuid])

        self.svm_fixture = self.create_vm(vn_objs=[self.mgmt_vn_fixture.obj,
                                              self.net1_vn_fixture.obj,
                                              self.net2_vn_fixture.obj],
                                    image_name='tiny_in_net',
                                    port_ids=[self.mgmt_vn_port.uuid,self.net1_port1.uuid,self.net2_port1.uuid])


        self.left_vm_fixture.wait_till_vm_is_up()
        self.right_vm_fixture.wait_till_vm_is_up()
        self.svm_fixture.wait_till_vm_is_up()

    def tearDown(self):
        self.net1_subIntf1.cleanUp()
        self.net1_subIntf2.cleanUp()
        self.net2_subIntf1.cleanUp()
        self.net2_subIntf2.cleanUp()
        self.net1_port1.cleanUp()
        self.net2_port1.cleanUp()
        self.left_vn_port.cleanUp()
        self.right_vn_port.cleanUp()
        self.mgmt_vn_port.cleanUp()
        self.left_vn_fixture.cleanUp()
        self.right_vn_fixture.cleanUp()
        self.mgmt_vn_fixture.cleanUp()
        self.net1_vn_fixture.cleanUp()
        self.net2_vn_fixture.cleanUp()
        super(TestSubInterfacesECMP, self).tearDown()

    def cleanUp(self):
        super(TestSubInterfacesECMP, self).cleanUp()

    def config_st_si_subInt(self):
        st_name = get_random_name("in_net_svc_template_1")
        svc_scaling = False
        max_inst=1
        svc_img_name='tiny_in_net'
        svc_type = 'firewall'
        static_route=[None, None, None]
        left_scaling = False
        right_scaling = False
        if_details = { 'management' : { 'shared_ip_enable' : False,
                                        'static_route_enable' : False },
                       'left' : { 'shared_ip_enable' : left_scaling,
                                  'static_route_enable' : False },
                       'right' : { 'shared_ip_enable' : right_scaling,
                                  'static_route_enable' : False }}
        flavor='contrail_flavor_2cpu'
        st_version=2
        si_name= get_random_name("in_net_svc_instance")
        svc_mode = 'in-network'
        st_fixture = self.useFixture(SvcTemplateFixture(
            connections=self.connections,
            st_name=st_name, service_type=svc_type,
            if_details=if_details, service_mode=svc_mode, version=st_version))

        si_fixture = self.useFixture(SvcInstanceFixture(
                connections=self.connections,
                si_name=si_name,
                svc_template=st_fixture.st_obj, if_details=if_details,
                max_inst=max_inst))

        return si_fixture

    @preposttest_wrapper
    def test_svc_subIntf(self):
        '''
        Test basic service chain with port tuples as vlan sub-interfaces

        '''
        cmd_to_create_subIntf = ["vconfig add eth1 101","ifconfig eth1.101 up","udhcpc -i eth1.101","vconfig add eth2 101","ifconfig eth2.101 up","udhcpc -i eth2.101"]
        self.svm_fixture.run_cmd_on_vm(cmds=cmd_to_create_subIntf, as_sudo=True)
        si_fixture = self.config_st_si_subInt()
        pt_name = get_random_name("port_tuple")
        si_fixture.add_port_tuple_subIntf(self.mgmt_vn_port.uuid, self.net1_subIntf1.uuid, self.net2_subIntf1.uuid, pt_name)
        si_fq_name = 'default-domain' + ':' + self.inputs.project_name + ':' + si_fixture.si_name
        self.action_list = []
        self.action_list.append(si_fq_name)
        self.rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': self.left_vn_fixture.vn_fq_name,
                'src_ports': 'any',
                'dest_network': self.right_vn_fixture.vn_fq_name,
                'dst_ports': 'any',
                'simple_action': None,
                'action_list': {'apply_service': self.action_list}
            },
        ]
        policy_name = get_random_name("policy_in_network")
        self.policy_fixture = self.config_policy(policy_name, self.rules)

        self.left_vn_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture, self.left_vn_fixture)
        self.right_vn_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture, self.right_vn_fixture)

        errmsg = "Ping to right VM ip %s from left VM passed; expected to fail" % self.right_vm_fixture.vm_ip
        assert self.left_vm_fixture.ping_with_certainty(
            self.right_vm_fixture.vm_ip), errmsg
    # end test_svc_subIntf

    @preposttest_wrapper
    def test_svc_ecmp_subIntf(self):
        '''
        Test ecmp with service chain when port tuples are vlan sub-interfaces

        '''
        cmd_to_create_subIntf = ["vconfig add eth1 101","ifconfig eth1.101 up","udhcpc -i eth1.101","vconfig add eth2 101","ifconfig eth2.101 up","udhcpc -i eth2.101"]
        self.svm_fixture.run_cmd_on_vm(cmds=cmd_to_create_subIntf, as_sudo=True)

        cmd_to_create_subIntf = ["vconfig add eth1 102","ifconfig eth1.102 up","udhcpc -i eth1.102","vconfig add eth2 102","ifconfig eth2.102 up","udhcpc -i eth2.102"]
        self.svm_fixture.run_cmd_on_vm(cmds=cmd_to_create_subIntf, as_sudo=True)
        si_fixture = self.config_st_si_subInt()

        pt1_name = get_random_name("port_tuple")
        pt2_name = get_random_name("port_tuple")
        si_fixture.add_port_tuple_subIntf(self.mgmt_vn_port.uuid, self.net1_subIntf1.uuid, self.net2_subIntf1.uuid, pt1_name)
        si_fixture.add_port_tuple_subIntf(self.mgmt_vn_port.uuid, self.net1_subIntf2.uuid, self.net2_subIntf2.uuid, pt2_name)
        si_fq_name = 'default-domain' + ':' + self.inputs.project_name + ':' + si_fixture.si_name
        self.action_list = []
        self.action_list.append(si_fq_name)
        self.rules = [
            {
                'direction': '<>',
                'protocol': 'any',
                'source_network': self.left_vn_fixture.vn_fq_name,
                'src_ports': 'any',
                'dest_network': self.right_vn_fixture.vn_fq_name,
                'dst_ports': 'any',
                'simple_action': None,
                'action_list': {'apply_service': self.action_list}
            },
        ]
        policy_name = get_random_name("policy_in_network")
        self.policy_fixture = self.config_policy(policy_name, self.rules)

        self.left_vn_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture, self.left_vn_fixture)
        self.right_vn_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture, self.right_vn_fixture)

        errmsg = "Ping to right VM ip %s from left VM passed; expected to fail" % self.right_vm_fixture.vm_ip
        assert self.left_vm_fixture.ping_with_certainty(
            self.right_vm_fixture.vm_ip), errmsg
    # end test_svc_ecmp_subIntf

