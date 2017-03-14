from vnc_api.vnc_api import *
from tcutils.util import get_random_name, get_random_cidrs

def get_sg_rule(direction, af='v4', proto='udp'):
    prefix_len = 0
    src_addresses = [{'security_group': 'local', 'subnet' : None}]
    dst_addresses = src_addresses
    src_ports = [{'start_port' : 0, 'end_port' : 65535}]
    dst_ports = src_ports

    if af == 'v4':
        ip_prefix = '0.0.0.0'
        ethertype = 'IPv4'
    elif af == 'v6':
        ip_prefix = '0::'
        ethertype = 'IPv6'
        if proto == 'icmp':
            proto = '58'

    if direction  == 'egress':
        dst_addresses = [{'subnet' : {'ip_prefix' : ip_prefix, 'ip_prefix_len' : prefix_len}}]
    elif direction == 'ingress':
        src_addresses = [{'subnet' : {'ip_prefix' : ip_prefix, 'ip_prefix_len' : prefix_len}}]

    rule = {'direction' : '>',
             'protocol' : proto,
             'src_addresses': src_addresses,
             'dst_ports': dst_ports,
             'src_ports': src_ports,
             'dst_addresses': dst_addresses,
             'ethertype': ethertype}

    return rule
################################################################################
class sdn_4vn_xvm_config ():
    def __init__(self, domain= 'default-domain', project= 'admin',
            compute_node_list= None, username= None, password= None,
            config_option='openstack', af_test='v4'):
        self.af_test = af_test
        ##
        # Domain and project defaults: Do not change until support for non-default is tested!
        self.domain= domain; self.project= project; self.username= username; self.password= password
        ##
        # Define VN's in the project:
        self.vnet_list=  ['vnet1','vnet2', 'vnet3', 'vnet4']
        ##
        # Define network info for each VN:
        self.vnet1_subnets = get_random_cidrs(self.af_test)
        self.vnet2_subnets = get_random_cidrs(self.af_test)
        self.vnet3_subnets = get_random_cidrs(self.af_test)
        self.vnet4_subnets = get_random_cidrs(self.af_test)

        self.vnet1_prefix = self.vnet1_subnets[0].split('/')[0]
        self.vnet1_prefix_len = int(self.vnet1_subnets[0].split('/')[1])
        self.vnet2_prefix = self.vnet2_subnets[0].split('/')[0]
        self.vnet2_prefix_len = int(self.vnet2_subnets[0].split('/')[1])
        self.vnet3_prefix = self.vnet3_subnets[0].split('/')[0]
        self.vnet3_prefix_len = int(self.vnet3_subnets[0].split('/')[1])
        self.vnet4_prefix = self.vnet4_subnets[0].split('/')[0]
        self.vnet4_prefix_len = int(self.vnet4_subnets[0].split('/')[1])

	if config_option == 'openstack':
            self.vn_nets=  {'vnet1': self.vnet1_subnets,
                            'vnet2': self.vnet2_subnets,
                            'vnet3': self.vnet3_subnets,
                            'vnet4': self.vnet4_subnets}
        else:
            self.vn_nets = {
            'vnet1': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(
                        subnet=SubnetType(self.vnet1_prefix,
                                        self.vnet1_prefix_len))]))],
	    'vnet2': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(
                        subnet=SubnetType(self.vnet2_prefix,
                                        self.vnet2_prefix_len))]))],
	    'vnet3': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(
                        subnet=SubnetType(self.vnet3_prefix,
                                        self.vnet3_prefix_len))]))],
	    'vnet4': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(
                        subnet=SubnetType(self.vnet4_prefix,
                                        self.vnet4_prefix_len))]))]
                           }

        ##
        # Define network policies
        self.policy_list=  ['policy0', 'policy1', 'policy100']
        self.vn_policy=  {'vnet1': ['policy0'], 'vnet2': ['policy0'],'vnet3':['policy0'],'vnet4':['policy0']}

        self.vn_of_vm= {'vm1': 'vnet1', 'vm2': 'vnet1', 'vm3': 'vnet1', 'vm4': 'vnet2', 'vm5': 'vnet2',
                        'vm6': 'vnet3', 'vm7': 'vnet3', 'vm8': 'vnet3', 'vm9': 'vnet4', 'vm10': 'vnet4','vm11':'vnet4','vm12':'vnet3'}

        #Define the vm to compute node mapping to pin a vm to a particular
        #compute node or else leave empty.
        self.vm_node_map = {}
        if compute_node_list is not None:
            if len(compute_node_list) == 2:
                self.vm_node_map = {'vm1':'CN0', 'vm2':'CN0', 'vm3':'CN1', 'vm4':'CN0', 'vm5':'CN1',
                                    'vm6':'CN0', 'vm7':'CN0', 'vm8':'CN1', 'vm9':'CN0', 'vm10':'CN1','vm11':'CN0','vm12':'CN1'}
            elif len(compute_node_list) > 2:
               self.vm_node_map = {'vm1':'CN0', 'vm2':'CN0', 'vm3':'CN2', 'vm4':'CN0', 'vm5':'CN1', 'vm6':'CN0',
                                   'vm7':'CN0', 'vm8':'CN2', 'vm9':'CN0', 'vm10':'CN1', 'vm11':'CN0','vm12':'CN1'}

        #Logic to create a vm to Compute node mapping.
        if self.vm_node_map:
            CN = []
            for cn in self.vm_node_map.keys():
                if self.vm_node_map[cn] not in CN:
                    CN.append(self.vm_node_map[cn])
            my_node_dict = {}
            if compute_node_list is not None:
                if len(compute_node_list) >= len(CN):
                    my_node_dict = dict(zip(CN, compute_node_list))

            if my_node_dict:
                for key in my_node_dict:
                    for key1 in self.vm_node_map:
                        if self.vm_node_map[key1] == key:
                            self.vm_node_map[key1] = my_node_dict[key]

        ##
        # Define network policy rules
        self.rules= {}
        # Multiple policies are defined with different action for the test traffic streams..
        self.policy_test_order= ['policy0', 'policy1', 'policy0']
	if config_option == 'openstack':
            self.rules['policy0']= [
            {'direction': '<>', 'protocol': 'any', 'dest_network': 'any', 'source_network': 'any', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
            self.rules['policy1']= [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet1', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet2', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
            self.rules['policy100']= [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'any', 'source_network': 'any', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        else:
            self.rules['policy0'] = [
            PolicyRuleType(direction='<>', protocol='any', dst_addresses=[AddressType(virtual_network='any')], src_addresses=[AddressType(
                virtual_network='any')], dst_ports=[PortType(-1, -1)], action_list=ActionListType(simple_action='pass'), src_ports=[PortType(-1, -1)])
            ]
            self.rules['policy1'] = [
            PolicyRuleType(direction='<>', protocol='udp', dst_addresses=[AddressType(virtual_network='vnet1')], src_addresses=[AddressType(
                virtual_network='vnet0')], dst_ports=[PortType(-1, -1)], action_list=ActionListType(simple_action='pass'), src_ports=[PortType(-1, -1)]),
	    PolicyRuleType(direction='<>', protocol='udp', dst_addresses=[AddressType(virtual_network='vnet2')], src_addresses=[AddressType(
                virtual_network='vnet0')], dst_ports=[PortType(-1, -1)], action_list=ActionListType(simple_action='pass'), src_ports=[PortType(-1, -1)])
            ]
            self.rules['policy100'] = [
            PolicyRuleType(direction='<>', protocol='udp', dst_addresses=[AddressType(virtual_network='any')], src_addresses=[AddressType(
                virtual_network='any')], dst_ports=[PortType(-1, -1)], action_list=ActionListType(simple_action='pass'), src_ports=[PortType(-1, -1)])
            ]

        #Define the security_group and its rules
        # Define security_group name
        self.sg_list=['sg_allow_all', 'sg_allow_tcp', 'sg_allow_udp', 'sg_allow_icmp', 'sg_allow_udp_sg']
        self.sg_names = self.sg_list[:]
        ##
        #Define security_group with vm
        self.sg_of_vm = {}
        for key in self.vn_of_vm:
           self.sg_of_vm[key] = []
        self.sg_of_vm['vm6'] = [self.sg_list[4]]; self.sg_of_vm['vm9'] = [self.sg_list[4]]; self.sg_of_vm['vm10'] = [self.sg_list[4]];
        self.sg_of_vm['vm11'] = [self.sg_list[4]]; self.sg_of_vm['vm12'] = [self.sg_list[4]];
        ##Define the security group rules
        import uuid
        uuid_1= uuid.uuid1().urn.split(':')[2]
        uuid_2= uuid.uuid1().urn.split(':')[2]
        self.sg_rules={}
        for sg in self.sg_list:
            self.sg_rules[sg] = []
        self.sg_rules[self.sg_list[2]]=[
            get_sg_rule('ingress',af=self.af_test,
                proto='udp'),
            get_sg_rule('egress',af=self.af_test,
                proto='any')]

        self.sg_rules[self.sg_list[4]]=[
               {'direction' : '>',
                 'protocol' : 'udp',
                 'dst_addresses': [{'security_group': 'local', 'subnet' : None}],
                 'dst_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'src_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'src_addresses': [{'security_group': self.domain + ':'+ self.project+ ':'+ self.sg_list[4]}],
                 'rule_uuid': uuid_1
               },
               get_sg_rule('egress',af=self.af_test,
                proto='any')]

        ##
        # Define traffic profile.
        self.traffic_profile= [{'src_vm':'vm1', 'dst_vm':'vm2', 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'pass'},# intra VN, intra compute, same default SG
                               {'src_vm':'vm1', 'dst_vm':'vm3', 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'pass'},# intra VN, inter compute, same default SG
                               {'src_vm':'vm1', 'dst_vm':'vm5', 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'pass'},# inter VN, inter compute, same default SG
                               {'src_vm':'vm1', 'dst_vm':'vm4', 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'pass'},# inter VN, intra compute, same default SG
                               {'src_vm':'vm6', 'dst_vm':'vm7', 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'fail'},# intra VN, intra compute, diff. SG
                               {'src_vm':'vm6', 'dst_vm':'vm8', 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'fail'},# intra VN, inter compute, diff. SG
                               {'src_vm':'vm6', 'dst_vm':'vm5', 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'fail'},# inter VN, inter compute, diff. SG
                               {'src_vm':'vm6', 'dst_vm':'vm4', 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'fail'},# inter VN, intra compute, diff. SG
                               {'src_vm':'vm9', 'dst_vm':'vm11','proto':'udp','sport':8000,'dport':9000,'exp':'pass'},# intra VN, intra compute, same non-default SG
                               {'src_vm':'vm9', 'dst_vm':'vm10','proto':'udp','sport':8000,'dport':9000,'exp':'pass'},# intra VN, inter compute, same non-default SG
                               {'src_vm':'vm9', 'dst_vm':'vm12','proto':'udp','sport':8000,'dport':9000,'exp':'pass'},# inter VN, inter compute, same non-default SG
                               {'src_vm':'vm9', 'dst_vm':'vm6', 'proto':'udp','sport':8000,'dport':9000,'exp':'pass'}]# inter VN, intra compute, same non-default SG

        # end __init__
# end class sdn_4vn_xvm_config

################################################################################
class sdn_topo_config ():
    def __init__(self, af_test='v4'):
        self.af_test = af_test

	#2 VN and 4 VM
    def build_topo_sg_stateful(self, domain= 'default-domain', project= 'admin', compute_node_list= None, username= None, password= None,config_option='openstack'):
        print "building dynamic topo"
        ##
        # Domain and project defaults: Do not change until support for non-default is tested!
        self.domain= domain; self.project= project; self.username= username; self.password= password
        ##
        # Define VN's in the project:
        self.vnet_list=  ['vnet1','vnet2']
        ##
        # Define network info for each VN:
        self.vnet1_subnets = get_random_cidrs(self.af_test)
        self.vnet2_subnets = get_random_cidrs(self.af_test)

        self.vnet1_prefix = self.vnet1_subnets[0].split('/')[0]
        self.vnet1_prefix_len = int(self.vnet1_subnets[0].split('/')[1])
        self.vnet2_prefix = self.vnet2_subnets[0].split('/')[0]
        self.vnet2_prefix_len = int(self.vnet2_subnets[0].split('/')[1])

	if config_option == 'openstack':
            self.vn_nets=  {'vnet1': self.vnet1_subnets, 'vnet2': self.vnet2_subnets}
        else:
            self.vn_nets = {
            'vnet1': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(subnet=SubnetType(self.vnet1_prefix, self.vnet1_prefix_len))]))],
            'vnet2': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(subnet=SubnetType(self.vnet2_prefix, self.vnet2_prefix_len))]))]
                           }

        ##
        # Define network policies
        self.policy_list=  ['policy0']
        self.vn_policy=  {'vnet1': ['policy0'], 'vnet2': ['policy0']}

        self.vn_of_vm= {'vm1': 'vnet1', 'vm2': 'vnet1', 'vm3': 'vnet2', 'vm4': 'vnet2'}

        #Define the vm to compute node mapping to pin a vm to a particular
        #compute node or else leave empty.
        self.vm_node_map = {}

        ##
        # Define network policy rules
        self.rules= {}
        # Multiple policies are defined with different action for the test traffic streams..
        self.policy_test_order= ['policy0']
	if config_option == 'openstack':
            self.rules['policy0']= [
            {'direction': '<>', 'protocol': 'any', 'dest_network': 'any', 'source_network': 'any', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        else:
            self.rules['policy0'] = [
            PolicyRuleType(direction='<>', protocol='any', dst_addresses=[AddressType(virtual_network='any')], src_addresses=[AddressType(
                virtual_network='any')], dst_ports=[PortType(-1, -1)], action_list=ActionListType(simple_action='pass'), src_ports=[PortType(-1, -1)])
            ]
        #Define the security_group and its rules
        # Define security_group name
        self.sg_list=['sg1_ingress', 'sg2_ingress', 'sg1_egress', 'sg2_egress']
        self.sg_names = self.sg_list[:]
        ##
        #Define security_group with vm
        self.sg_of_vm = {}
        for key in self.vn_of_vm:
           self.sg_of_vm[key] = []
        self.sg_of_vm['vm1'] = [self.sg_list[0]]; self.sg_of_vm['vm2'] = [self.sg_list[2]]; self.sg_of_vm['vm3'] = [self.sg_list[1]];
        self.sg_of_vm['vm4'] = [self.sg_list[3]];
        ##Define the security group rules
        self.sg_rules={}
        for sg in self.sg_list:
            self.sg_rules[sg] = []

        self.sg_rules[self.sg_list[0]]=[get_sg_rule('ingress',af=self.af_test,
            proto='udp')]
        self.sg_rules[self.sg_list[1]]=[get_sg_rule('ingress',af=self.af_test,
            proto='udp')]
        self.sg_rules[self.sg_list[2]]=[get_sg_rule('egress',af=self.af_test,
            proto='udp')]
        self.sg_rules[self.sg_list[3]]=[get_sg_rule('egress',af=self.af_test,
            proto='udp')]

        ##
        # Define traffic profile.
        self.traffic_profile= [{'src_vm':'vm1', 'dst_vm':'vm2', 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'fail'},
                               {'src_vm':'vm2', 'dst_vm':'vm1', 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'pass'},
    			       {'src_vm':'vm1', 'dst_vm':'vm3', 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'fail'},
                               {'src_vm':'vm3', 'dst_vm':'vm1', 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'fail'},
                               {'src_vm':'vm1', 'dst_vm':'vm4', 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'fail'},
                               {'src_vm':'vm4', 'dst_vm':'vm1', 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'pass'},
                               {'src_vm':'vm2', 'dst_vm':'vm4', 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'fail'},
                               {'src_vm':'vm4', 'dst_vm':'vm2', 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'fail'}
			      ]

        # end build_topo_sg_stateful
# end class sdn_topo_config
################################################################################

class sdn_topo_config_multiproject():

    def __init__(self, domain= 'default-domain', project= 'admin',
            username= None, password= None):
        print "building dynamic topo"
	project1 = 'project1'
        project2 = 'admin'
        user1 = username or 'user1'
        user2 = username or 'user2'
        password1 = password or 'user123'
        password2 = password or 'user223'
        self.project_list = [project1, project2]
	self.topo_of_project = {self.project_list[0]:'build_topo1', self.project_list[1]:'build_topo1'}
	self.user_of_project = {self.project_list[0]:user1, self.project_list[1]:user2}
	self.pass_of_project = {self.project_list[0]:password1, self.project_list[1]:password2}

        ##
        # Define traffic profile.
        self.traffic_profile= [{'src_vm':[project1,'vm1'], 'dst_vm':[project2,'vm1'], 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'pass'},
                               {'src_vm':[project1,'vm2'], 'dst_vm':[project2,'vm2'], 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'fail'},
                               {'src_vm':[project1,'vm1'], 'dst_vm':[project2,'vm2'], 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'fail'},
                               {'src_vm':[project1,'vm2'], 'dst_vm':[project2,'vm1'], 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'pass'},
                               {'src_vm':[project2,'vm1'], 'dst_vm':[project1,'vm1'], 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'pass'},
                               {'src_vm':[project2,'vm2'], 'dst_vm':[project1,'vm2'], 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'fail'},
                               {'src_vm':[project2,'vm2'], 'dst_vm':[project1,'vm1'], 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'pass'},
                               {'src_vm':[project2,'vm1'], 'dst_vm':[project1,'vm2'], 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'fail'}
                              ]


    def build_topo1(self, domain= 'default-domain', project= 'admin',
            username= None, password= None,config_option='openstack',
            af_test='v4'):
        self.af_test = af_test
        ##
        # Domain and project defaults: Do not change until support for non-default is tested!
        self.domain= domain; self.project= project; self.username= username; self.password= password
        ##
        # Define VN's in the project:
        self.vnet_list=  ['vnet1']
        ##
        # Define network info for each VN:
        self.vnet1_subnets = get_random_cidrs(self.af_test)
        self.vnet2_subnets = get_random_cidrs(self.af_test)

        self.vnet1_prefix = self.vnet1_subnets[0].split('/')[0]
        self.vnet1_prefix_len = int(self.vnet1_subnets[0].split('/')[1])
        self.vnet2_prefix = self.vnet2_subnets[0].split('/')[0]
        self.vnet2_prefix_len = int(self.vnet2_subnets[0].split('/')[1])

	if config_option == 'openstack':
	    if self.project == self.project_list[1]:
                self.vn_nets=  {'vnet1': self.vnet1_subnets}
	    else:
                self.vn_nets=  {'vnet1': self.vnet2_subnets}
	else:
	    if self.project == self.project_list[1]:
		 self.vn_nets = {
            'vnet1': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(
                subnet=SubnetType(self.vnet1_prefix, self.vnet1_prefix_len))]))]
                           }
	    else:
                 self.vn_nets = {
            'vnet1': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(
                subnet=SubnetType(self.vnet2_prefix, self.vnet2_prefix_len))]))]
                           }

        ##
        # Define network policies
        self.policy_list=  ['policy0']
        self.vn_policy=  {'vnet1': ['policy0']}

        self.vn_of_vm= {'vm1': 'vnet1', 'vm2': 'vnet1'}

        #Define the vm to compute node mapping to pin a vm to a particular
        #compute node or else leave empty.
        self.vm_node_map = {}

        ##
        # Define network policy rules
        self.rules= {}
        # Multiple policies are defined with different action for the test traffic streams..
        self.policy_test_order= ['policy0']
	if config_option == 'openstack':
            self.rules['policy0']= [
            {'direction': '<>', 'protocol': 'any', 'dest_network': ':'.join([self.domain,self.project_list[0],self.vnet_list[0]]), 'source_network': ':'.join([self.domain,self.project_list[1],self.vnet_list[0]]), 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
	else:
            self.rules['policy0'] = [
            PolicyRuleType(direction='<>', protocol='any',
		dst_addresses=[AddressType(virtual_network=':'.join([self.domain,self.project_list[0],self.vnet_list[0]]))],
		src_addresses=[AddressType(virtual_network=':'.join([self.domain,self.project_list[1],self.vnet_list[0]]))],
		dst_ports=[PortType(-1, -1)], action_list=ActionListType(simple_action='pass'), src_ports=[PortType(-1, -1)])
            ]

        #Define the security_group and its rules
        # Define security_group name
        self.sg_list=['sg1']
        self.sg_names = self.sg_list[:]
        ##
        #Define security_group with vm
        self.sg_of_vm = {}
        for key in self.vn_of_vm:
           self.sg_of_vm[key] = []
        self.sg_of_vm['vm1'] = [self.sg_list[0]]
        ##Define the security group rules
        self.sg_rules={}
        for sg in self.sg_list:
            self.sg_rules[sg] = []
        self.sg_rules[self.sg_list[0]]=[
            get_sg_rule('ingress',af=self.af_test, proto='udp'),
            get_sg_rule('egress',af=self.af_test, proto='udp')]

	return self
        # end build_topo1
# end class sdn_topo_config_multiproject
################################################################################

class sdn_topo_1vn_2vm_config ():
    def __init__(self, af_test='v4'):
        self.af_test = af_test

    def build_topo(self, domain= 'default-domain', project= 'admin', username= None, password= None,config_option='openstack'):
        ##
        # Domain and project defaults: Do not change until support for non-default is tested!
        self.domain= domain; self.project= project; self.username= username; self.password= password
        ##
        # Define VN's in the project:
        self.vnet_list=  ['vnet1']
        ##
        # Define network info for each VN:
        self.vnet1_subnets = get_random_cidrs(self.af_test)

        self.vnet1_prefix = self.vnet1_subnets[0].split('/')[0]
        self.vnet1_prefix_len = int(self.vnet1_subnets[0].split('/')[1])

	if config_option == 'openstack':
            self.vn_nets=  {'vnet1': self.vnet1_subnets}
	else:
	    self.vn_nets = {
            'vnet1': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(
                subnet=SubnetType(self.vnet1_prefix, self.vnet1_prefix_len))]))]
        		   }

        ##
        # Define network policies
        self.policy_list=  ['policy0']
        self.vn_policy=  {'vnet1': ['policy0']}

        self.vn_of_vm= {'vm1': 'vnet1', 'vm2': 'vnet1'}

        #Define the vm to compute node mapping to pin a vm to a particular
        #compute node or else leave empty.
        self.vm_node_map = {}

        ##
        # Define network policy rules
        self.rules= {}
        self.policy_test_order= ['policy0']
	if config_option == 'openstack':
            self.rules['policy0']= [
            {'direction': '<>', 'protocol': 'any', 'dest_network': 'any', 'source_network': 'any', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
	else:
            self.rules['policy0'] = [
            PolicyRuleType(direction='<>', protocol='any', dst_addresses=[AddressType(virtual_network='any')], src_addresses=[AddressType(
                virtual_network='any')], dst_ports=[PortType(-1, -1)], action_list=ActionListType(simple_action='pass'), src_ports=[PortType(-1, -1)])
        ]

        #Define the security_group and its rules
        # Define security_group name
        self.sg_list=['sg1']
        self.sg_names = self.sg_list[:]
        ##
        #Define security_group with vm
        self.sg_of_vm = {}
        for key in self.vn_of_vm:
           self.sg_of_vm[key] = []
        self.sg_of_vm['vm1'] = [self.sg_list[0]]; self.sg_of_vm['vm2'] = [self.sg_list[0]];
        ##Define the security group rules
        self.sg_rules={}
        for sg in self.sg_list:
            self.sg_rules[sg] = []
        self.sg_rules[self.sg_list[0]]=[]

        ##
        # Define traffic profile.
        self.traffic_profile= [{'src_vm':'vm1', 'dst_vm':'vm2', 'proto':'udp', 'sport':8000, 'dport':9000, 'exp':'fail'},
                               {'src_vm':'vm1', 'dst_vm':'vm2', 'proto':'tcp', 'sport':8000, 'dport':9000, 'exp':'fail'},
                               {'src_vm':'vm1', 'dst_vm':'vm2', 'proto':'icmp', 'sport':8000, 'dport':9000, 'exp':'fail'}
                              ]

        return self
        # end build_topo1


################################################################################
class sdn_topo_icmp_error_handling():
    def __init__(self, af_test='v4'):
        self.af_test = af_test

        #2 VN and 3 VM
    def build_topo(self, domain= 'default-domain', project= 'admin', compute_node_list= None, username= None, password= None,config_option='openstack'):
        print "building dynamic topo"
        ##
        # Domain and project defaults: Do not change until support for non-default is tested!
        self.domain= domain; self.project= project; self.username= username; self.password= password
        ##
        # Define VN's in the project:
        self.vnet_list=  ['vnet1','vnet2']
        ##
        # Define network info for each VN:
        self.vnet1_subnets = get_random_cidrs(self.af_test)
        self.vnet2_subnets = get_random_cidrs(self.af_test)

        self.vnet1_prefix = self.vnet1_subnets[0].split('/')[0]
        self.vnet1_prefix_len = int(self.vnet1_subnets[0].split('/')[1])
        self.vnet2_prefix = self.vnet2_subnets[0].split('/')[0]
        self.vnet2_prefix_len = int(self.vnet2_subnets[0].split('/')[1])

	if config_option == 'openstack':
            self.vn_nets=  {'vnet1': self.vnet1_subnets, 'vnet2': self.vnet2_subnets}
        else:
            self.vn_nets = {
            'vnet1': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(
                subnet=SubnetType(self.vnet1_prefix, self.vnet1_prefix_len))]))],
            'vnet2': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(
                subnet=SubnetType(self.vnet2_prefix, self.vnet2_prefix_len))]))]
                           }

        ##
        # Define network policies
        self.policy_list=  ['policy0']
        self.vn_policy=  {'vnet1': ['policy0'], 'vnet2': ['policy0']}

        self.vn_of_vm= {'vm1': 'vnet1', 'vm2': 'vnet1', 'vm3': 'vnet2'}

        #Define the vm to compute node mapping to pin a vm to a particular
        #compute node or else leave empty.
        self.vm_node_map = {}

        ##
        # Define network policy rules
        self.rules= {}
        # Multiple policies are defined with different action for the test traffic streams..
        self.policy_test_order= ['policy0']
	if config_option == 'openstack':
            self.rules['policy0']= [
            {'direction': '<>', 'protocol': 'any', 'dest_network': 'any', 'source_network': 'any', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
	else:
            self.rules['policy0'] = [
            PolicyRuleType(direction='<>', protocol='any', dst_addresses=[AddressType(virtual_network='any')], src_addresses=[AddressType(
                virtual_network='any')], dst_ports=[PortType(-1, -1)], action_list=ActionListType(simple_action='pass'), src_ports=[PortType(-1, -1)])
            ]

        #Define the security_group and its rules
        # Define security_group name
        self.sg_list=['sg1']
        self.sg_names = self.sg_list[:]
        ##
        #Define security_group with vm
        self.sg_of_vm = {}
        for key in self.vn_of_vm:
           self.sg_of_vm[key] = []
        self.sg_of_vm['vm1'] = [self.sg_list[0]]; self.sg_of_vm['vm2'] = [self.sg_list[0]]; self.sg_of_vm['vm3'] = [self.sg_list[0]];
        ##Define the security group rules
        self.sg_rules={}
        for sg in self.sg_list:
            self.sg_rules[sg] = []
        self.sg_rules[self.sg_list[0]] = [get_sg_rule('egress',af=self.af_test,
            proto='any'),
                {'direction': '>',
                 'protocol': 'udp',
                 'src_addresses':[{'security_group': self.domain + ':'+ self.project+ ':'+ self.sg_list[0]}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],}]

	return self
        # end build_topo

    #1VN 2 VM
    def build_topo2(self, domain= 'default-domain', project= 'admin', compute_node_list= None, username= None, password= None,config_option='openstack'):
        print "building dynamic topo"
        ##
        # Domain and project defaults: Do not change until support for non-default is tested!
        self.domain= domain; self.project= project; self.username= username; self.password= password
        ##
        # Define VN's in the project:
        self.vnet_list=  ['vnet1']
        ##
        # Define network info for each VN:
        self.vnet1_subnets = get_random_cidrs(self.af_test)

        self.vnet1_prefix = self.vnet1_subnets[0].split('/')[0]
        self.vnet1_prefix_len = int(self.vnet1_subnets[0].split('/')[1])

	if config_option == 'openstack':
            self.vn_nets=  {'vnet1': self.vnet1_subnets}
        else:
            self.vn_nets = {
            'vnet1': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(
                subnet=SubnetType(self.vnet1_prefix, self.vnet1_prefix_len))]))]
                           }

        ##
        # Define network policies
        self.policy_list=  ['policy0']
        self.vn_policy=  {'vnet1': ['policy0']}

        self.vn_of_vm= {'vm1': 'vnet1', 'vm2': 'vnet1'}

        #Define the vm to compute node mapping to pin a vm to a particular
        #compute node or else leave empty.
        self.vm_node_map = {}
        if compute_node_list is not None:
            if len(compute_node_list) == 2:
                self.vm_node_map = {'vm1':'CN0', 'vm2':'CN1'}
            elif len(compute_node_list) > 2:
               self.vm_node_map = {'vm1':'CN0', 'vm2':'CN1'}

        #Logic to create a vm to Compute node mapping.
        if self.vm_node_map:
            CN = []
            for cn in self.vm_node_map.keys():
                if self.vm_node_map[cn] not in CN:
                    CN.append(self.vm_node_map[cn])
            my_node_dict = {}
            if compute_node_list is not None:
                if len(compute_node_list) >= len(CN):
                    my_node_dict = dict(zip(CN, compute_node_list))

            if my_node_dict:
                for key in my_node_dict:
                    for key1 in self.vm_node_map:
                        if self.vm_node_map[key1] == key:
                            self.vm_node_map[key1] = my_node_dict[key]

        ##
        # Define network policy rules
        self.rules= {}
        # Multiple policies are defined with different action for the test traffic streams..
        self.policy_test_order= ['policy0']
	if config_option == 'openstack':
            self.rules['policy0']= [
            {'direction': '<>', 'protocol': 'any', 'dest_network': 'any', 'source_network': 'any', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        else:
            self.rules['policy0'] = [
            PolicyRuleType(direction='<>', protocol='any', dst_addresses=[AddressType(virtual_network='any')], src_addresses=[AddressType(
                virtual_network='any')], dst_ports=[PortType(-1, -1)], action_list=ActionListType(simple_action='pass'), src_ports=[PortType(-1, -1)])
            ]

        #Define the security_group and its rules
        # Define security_group name
        self.sg_list=['sg1', 'sg-ingress']
        self.sg_names = self.sg_list[:]
        ##
        #Define security_group with vm
        self.sg_of_vm = {}
        for key in self.vn_of_vm:
           self.sg_of_vm[key] = []
	self.sg_of_vm['vm1'] = [self.sg_list[0]]
	self.sg_of_vm['vm2'] = [self.sg_list[1]]
        ##Define the security group rules
        self.sg_rules={}
        for sg in self.sg_list:
            self.sg_rules[sg] = []
        self.sg_rules[self.sg_list[0]] = [get_sg_rule('egress',af=self.af_test,
                    proto='udp')]

        self.sg_rules[self.sg_list[1]] = [get_sg_rule('ingress',af=self.af_test,
                    proto='udp')]

        return self
        # end build_topo2

# end class sdn_topo_icmp_error_handling

class sdn_topo_mx_with_si():
    def build_topo(self, domain= 'default-domain', project= 'admin',
			compute_node_list= None, username= None,
			password= None, public_vn_info=None,config_option='openstack'):
        print "building dynamic topo"
        ##
        # Domain and project defaults: Do not change until support for non-default is tested!
        self.domain= domain; self.project= project; self.username= username; self.password= password
        ##
        # Define VN's in the project:
        self.vnet_list=  ['vnet1','public']
        ##
        # Define network info for each VN:
	if config_option == 'openstack':
            self.vn_nets=  {'vnet1': ['9.9.9.0/24'], 'public': public_vn_info['subnet']}
	else:
             self.vn_nets = {
            'vnet1': [(NetworkIpam(),
                       VnSubnetsType([
                        IpamSubnetType(
                         subnet=SubnetType(
                                 '9.9.9.0',
                                 24))
                                     ])
                      )],
            'public': [(NetworkIpam(),
                        VnSubnetsType([
                         IpamSubnetType(
                          subnet=SubnetType(
                                  public_vn_info['subnet'][0].split('/')[0],
                                  int(public_vn_info['subnet'][0].split('/')[1])
                                           )
                                       )])
                      )]
                           }


	#Define diff. VN params
	self.vn_params = {self.vnet_list[0]:{'router_asn':public_vn_info['router_asn'],
					     'rt_number':public_vn_info['rt_number']
					    }
			 }

        if_details = {
            'management' : { 'shared_ip_enable' : False,
                             'static_route_enable': False },
            'left' : { 'shared_ip_enable': False,
                       'static_route_enable' : False},
            'right' : { 'shared_ip_enable': False,
                       'static_route_enable' : False}}
        # define service templates
        self.st_list = ['st_trans_firewall']
        self.st_params = {self.st_list[0]: {'svc_img_name': 'tiny_trans_fw', 'svc_type': 'firewall',
                                            'if_details' : if_details,
                                            'svc_mode': 'transparent',
                                            'svc_scaling': False, 'flavor': 'm1.tiny',
                                            }}

        # define service instance
        self.si_list = ['si_trans_firewall']
        self.si_params = {
            self.si_list[0]: {'if_details' : if_details,
                              'svc_template': self.st_list[0],
                              'left_vn': None, 'right_vn': None
                             }}

        #
        # Define network policies
        self.policy_list=  ['policy0', 'pol-si']
        self.vn_policy=  {self.vnet_list[0]: ['policy0'], self.vnet_list[1]: ['policy0']}

        self.vn_of_vm= {'vm1': 'vnet1', 'vm2': 'public'}

        #Define the vm to compute node mapping to pin a vm to a particular
        #compute node or else leave empty.
        self.vm_node_map = {}

        ##
        # Define network policy rules
        self.rules= {}
        self.policy_test_order= ['policy0']
	if config_option == 'openstack':
            self.rules['pol-si']= [{'direction': '<>', 'protocol': 'any', 'dest_network': self.vnet_list[0],
				'source_network': self.vnet_list[1], 'dst_ports': 'any',
				'simple_action': 'pass', 'src_ports': 'any',
				'action_list': {'simple_action':'pass', 'apply_service': [':'.join([self.domain,
								      self.project,
								      self.si_list[0]])
								 ]}
				}]

            self.rules['policy0']= [{'direction': '<>', 'protocol': 'any', 'dest_network': self.vnet_list[0],
                                'source_network': self.vnet_list[1], 'dst_ports': 'any',
                                'simple_action': 'pass', 'src_ports': 'any'
                                }]
	else:
            self.rules['pol-si'] = [
            PolicyRuleType(direction='<>', protocol='any',
				dst_addresses=[AddressType(virtual_network=':'.join([self.domain,self.project,self.vnet_list[0]]))],
				src_addresses=[AddressType(virtual_network=':'.join([self.domain,self.project,self.vnet_list[1]]))],
				dst_ports=[PortType(-1, -1)], action_list=ActionListType(simple_action='pass',
				apply_service=[':'.join([self.domain, self.project, self.si_list[0]])]),
				src_ports=[PortType(-1, -1)])
            ]
            self.rules['policy0'] = [
            PolicyRuleType(direction='<>', protocol='any',
				dst_addresses=[AddressType(virtual_network=':'.join([self.domain,self.project,self.vnet_list[0]]))],
				src_addresses=[AddressType(virtual_network=':'.join([self.domain,self.project,self.vnet_list[1]]))],
				dst_ports=[PortType(-1, -1)], action_list=ActionListType(simple_action='pass'),
				src_ports=[PortType(-1, -1)])
            ]


        #Define the security_group and its rules
        # Define security_group name
        self.sg_list=['sg1']
        self.sg_names = self.sg_list[:]

        ##
        #Define security_group with vm
        self.sg_of_vm = {}
        for key in self.vn_of_vm:
           self.sg_of_vm[key] = []
        self.sg_of_vm['vm1'] = [self.sg_list[0]]; self.sg_of_vm['vm2'] = [self.sg_list[0]]
        ##Define the security group rules
        self.sg_rules={}
        for sg in self.sg_list:
            self.sg_rules[sg] = []
        self.sg_rules[self.sg_list[0]] = [
                {'direction': '>',
                'protocol': 'udp',
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'src_addresses': [{'security_group': 'local'}],
                 },
                {'direction': '>',
                 'protocol': 'udp',
                 'src_addresses':[{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],}]

        return self
        # end build_topo

################################################################################
class sdn_topo_flow_to_sg_rule_mapping():
    def __init__(self, af_test='v4'):
        self.af_test = af_test

        #2 VN and 2 VM
    def build_topo(self, domain= 'default-domain', project= 'admin',
                     compute_node_list= None, username= None,
                     password= None,no_of_vm=2,
                     config_option='openstack'):
        #no_of_vm must be 2 or 3
        print "building dynamic topo"
        ##
        # Domain and project defaults: Do not change until support for non-default is tested!
        self.domain= domain; self.project= project; self.username= username; self.password= password
        ##
        # Define VN's in the project:
        self.vnet_list=  ['vnet1','vnet2']
        ##
        # Define network info for each VN:
        self.vnet1_subnets = get_random_cidrs(self.af_test)
        self.vnet2_subnets = get_random_cidrs(self.af_test)

        self.vnet1_prefix = self.vnet1_subnets[0].split('/')[0]
        self.vnet1_prefix_len = int(self.vnet1_subnets[0].split('/')[1])
        self.vnet2_prefix = self.vnet2_subnets[0].split('/')[0]
        self.vnet2_prefix_len = int(self.vnet2_subnets[0].split('/')[1])

        if config_option == 'openstack':
            self.vn_nets=  {'vnet1': self.vnet1_subnets,
                            'vnet2': self.vnet2_subnets}
        else:
            self.vn_nets = {
            'vnet1': [(NetworkIpam(), VnSubnetsType(
                                        [IpamSubnetType(
                                          subnet=SubnetType(
                                                  self.vnet1_prefix,
                                                  self.vnet1_prefix_len))]))],
            'vnet2': [(NetworkIpam(), VnSubnetsType(
                                       [IpamSubnetType(
                                         subnet=SubnetType(
                                                  self.vnet2_prefix,
                                                  self.vnet2_prefix_len))]))]
                           }

        ##
        # Define network policies
        self.policy_list=  ['policy0']
        self.vn_policy=  {'vnet1': ['policy0'], 'vnet2': ['policy0']}

        if no_of_vm == 3:
            self.vn_of_vm= {'vm1': 'vnet1', 'vm2': 'vnet1', 'vm3': 'vnet2'}
        if no_of_vm == 2:
            self.vn_of_vm= {'vm1': 'vnet1', 'vm2': 'vnet2'}

        #Define the vm to compute node mapping to pin a vm to a particular
        #compute node or else leave empty.
        self.vm_node_map = {}
        if compute_node_list is not None:
            if len(compute_node_list) == 2:
                self.vm_node_map = {'vm1':'CN0', 'vm2':'CN1'}
            elif len(compute_node_list) > 2:
               self.vm_node_map = {'vm1':'CN0', 'vm2':'CN1'}
        if no_of_vm == 3:self.vm_node_map['vm3'] = 'CN0'

        #Logic to create a vm to Compute node mapping.
        if self.vm_node_map:
            CN = []
            for cn in self.vm_node_map.keys():
                if self.vm_node_map[cn] not in CN:
                    CN.append(self.vm_node_map[cn])
            my_node_dict = {}
            if compute_node_list is not None:
                if len(compute_node_list) >= len(CN):
                    my_node_dict = dict(zip(CN, compute_node_list))

            if my_node_dict:
                for key in my_node_dict:
                    for key1 in self.vm_node_map:
                        if self.vm_node_map[key1] == key:
                            self.vm_node_map[key1] = my_node_dict[key]

        ##
        # Define network policy rules
        self.rules= {}
        # Multiple policies are defined with different action for the test traffic streams..
        self.policy_test_order= ['policy0']
        if config_option == 'openstack':
            self.rules['policy0']= [
            {'direction': '<>', 'protocol': 'any', 'dest_network': 'any',
             'source_network': 'any', 'dst_ports': 'any',
             'simple_action': 'pass', 'src_ports': 'any'}]
        else:
            self.rules['policy0'] = [
            PolicyRuleType(direction='<>', protocol='any',
             dst_addresses=[AddressType(virtual_network='any')],
             src_addresses=[AddressType(virtual_network='any')],
             dst_ports=[PortType(-1, -1)],
             action_list=ActionListType(simple_action='pass'),
             src_ports=[PortType(-1, -1)])
            ]

        #Define the security_group and its rules
        # Define security_group name
        self.sg_list=['sg1']
        self.sg_names = self.sg_list[:]
        ##
        #Define security_group with vm
        self.sg_of_vm = {}
        for key in self.vn_of_vm:
           self.sg_of_vm[key] = []
        ##Define the security group rules
        self.sg_rules={}
        for sg in self.sg_list:
            self.sg_rules[sg] = []
        self.sg_rules[self.sg_list[0]] = [
                get_sg_rule('egress',af=self.af_test,
                    proto='udp'),
                {'direction': '>',
                 'protocol': 'udp',
                 'src_addresses':[{'security_group': self.domain + ':'+ self.project+ ':'+ self.sg_list[0]}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],}]

        return self
        # end build_topo

    def build_topo2(self, domain= 'default-domain', project= 'admin',
                      compute_node_list= None, username= None,
                      password= None,no_of_vm=2,
                      config_option='openstack'):
        #no_of_vm must be 2 or 3
        print "building dynamic topo"
        ##
        # Domain and project defaults: Do not change until support for non-default is tested!
        self.domain= domain; self.project= project; self.username= username; self.password= password
        ##
        # Define VN's in the project:
        self.vnet_list=  ['vnet1','vnet2']
        ##
        # Define network info for each VN:
        self.vnet1_subnets = get_random_cidrs(self.af_test)
        self.vnet2_subnets = get_random_cidrs(self.af_test)

        self.vnet1_prefix = self.vnet1_subnets[0].split('/')[0]
        self.vnet1_prefix_len = int(self.vnet1_subnets[0].split('/')[1])
        self.vnet2_prefix = self.vnet2_subnets[0].split('/')[0]
        self.vnet2_prefix_len = int(self.vnet2_subnets[0].split('/')[1])

        if config_option == 'openstack':
            self.vn_nets=  {'vnet1': self.vnet1_subnets, 'vnet2': self.vnet2_subnets}
        else:
            self.vn_nets = {
            'vnet1': [(NetworkIpam(), VnSubnetsType(
                                        [IpamSubnetType(
                                          subnet=SubnetType(
                                                  self.vnet1_prefix,
                                                  self.vnet1_prefix_len))]))],
            'vnet2': [(NetworkIpam(), VnSubnetsType(
                                       [IpamSubnetType(
                                         subnet=SubnetType(
                                                  self.vnet2_prefix,
                                                  self.vnet2_prefix_len))]))]
                           }

        ##
        # Define network policies
        self.policy_list=  ['policy0']
        self.vn_policy=  {'vnet1': ['policy0'], 'vnet2': ['policy0']}

        if no_of_vm == 3:
            self.vn_of_vm= {'vm1': 'vnet1', 'vm2': 'vnet1', 'vm3': 'vnet2'}
        if no_of_vm == 2:
            self.vn_of_vm= {'vm1': 'vnet1', 'vm2': 'vnet2'}

        #Define the vm to compute node mapping to pin a vm to a particular
        #compute node or else leave empty.
        self.vm_node_map = {}
        if compute_node_list is not None:
            if len(compute_node_list) == 2:
                self.vm_node_map = {'vm1':'CN0', 'vm2':'CN1'}
            elif len(compute_node_list) > 2:
               self.vm_node_map = {'vm1':'CN0', 'vm2':'CN1'}
        if no_of_vm == 3:self.vm_node_map['vm3'] = 'CN0'
        #Logic to create a vm to Compute node mapping.
        if self.vm_node_map:
            CN = []
            for cn in self.vm_node_map.keys():
                if self.vm_node_map[cn] not in CN:
                    CN.append(self.vm_node_map[cn])
            my_node_dict = {}
            if compute_node_list is not None:
                if len(compute_node_list) >= len(CN):
                    my_node_dict = dict(zip(CN, compute_node_list))

            if my_node_dict:
                for key in my_node_dict:
                    for key1 in self.vm_node_map:
                        if self.vm_node_map[key1] == key:
                            self.vm_node_map[key1] = my_node_dict[key]

        ##
        # Define network policy rules
        self.rules= {}
        # Multiple policies are defined with different action for the test traffic streams..
        self.policy_test_order= ['policy0']
        if config_option == 'openstack':
            self.rules['policy0']= [
            {'direction': '<>', 'protocol': 'any', 'dest_network': 'any',
             'source_network': 'any', 'dst_ports': 'any',
             'simple_action': 'pass', 'src_ports': 'any'}]
        else:
            self.rules['policy0'] = [
            PolicyRuleType(direction='<>', protocol='any',
             dst_addresses=[AddressType(virtual_network='any')],
             src_addresses=[AddressType(virtual_network='any')],
             dst_ports=[PortType(-1, -1)],
             action_list=ActionListType(simple_action='pass'),
             src_ports=[PortType(-1, -1)])
            ]

        #Define the security_group and its rules
        # Define security_group name
        self.sg_list=['sg1', 'sg2']
        self.sg_names = self.sg_list[:]
        ##
        #Define security_group with vm
        self.sg_of_vm = {}
        for key in self.vn_of_vm:
           self.sg_of_vm[key] = []
        self.sg_of_vm['vm1'] = [self.sg_list[0], self.sg_list[1]]; self.sg_of_vm['vm2'] = [self.sg_list[0], self.sg_list[1]]
        ##Define the security group rules
        self.sg_rules={}
        for sg in self.sg_list:
            self.sg_rules[sg] = []
        self.sg_rules[self.sg_list[0]] = [
                get_sg_rule('egress',af=self.af_test,
                    proto='udp'),
                get_sg_rule('ingress',af=self.af_test,
                    proto='udp'),
                get_sg_rule('egress',af=self.af_test,
                    proto='icmp'),
                get_sg_rule('ingress',af=self.af_test,
                    proto='icmp')]

        self.sg_rules[self.sg_list[1]] = [
                get_sg_rule('egress',af=self.af_test,
                    proto='tcp'),
                get_sg_rule('ingress',af=self.af_test,
                    proto='tcp')]

        return self
        # end build_topo2
