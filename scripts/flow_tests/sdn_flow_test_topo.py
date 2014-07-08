'''*******AUTO-GENERATED TOPOLOGY*********'''


class sdn_flow_test_topo_single_project ():

    def __init__(self, domain='default-domain', compute_node_list=None):
        print "building dynamic topo"
        self.project_list = ['project1']

        # Define the vm to compute node mapping to pin a vm to a particular
        # compute node or else leave empty.
        #self.vm_node_map = {}
        self.vm_node_map = {}
        if compute_node_list is not None:
            if len(compute_node_list) == 2:
                self.vm_node_map = {
                    'vmc1': 'CN0', 'vmc2': 'CN0', 'vmc3': 'CN0', 'vmc4': 'CN0', 'vmc8': 'CN0', 'vmc9': 'CN0',
                    'vmc5': 'CN1', 'vmc6': 'CN1', 'vmc7': 'CN1', 'vmd10': 'CN1', 'vmd11': 'CN1'}
            elif len(compute_node_list) > 2:
                self.vm_node_map = {
                    'vmc1': 'CN0', 'vmc2': 'CN0', 'vmc3': 'CN0', 'vmc4': 'CN0',
                    'vmc5': 'CN1', 'vmc6': 'CN1', 'vmc7': 'CN1',
                    'vmc8': 'CN2', 'vmc9': 'CN2', 'vmd10': 'CN2', 'vmd11': 'CN2'}

        # Logic to create a vm to Compute node mapping.
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

        #
        # Define traffic profile.
        self.traffic_profile = {'TrafficProfile1': {'src_vm': 'vmc1', 'dst_vm': 'vmc2', 'num_flows': 300000, 'num_pkts': 2000000},  # Intra VN,Intra Node
                                # Intra VN,Inter Node
                                'TrafficProfile2': {'src_vm': 'vmc4', 'dst_vm': 'vmc7', 'num_flows': 300000, 'num_pkts': 2000000},
                                # Inter VN,Intra Node,Pol
                                'TrafficProfile3': {'src_vm': 'vmc3', 'dst_vm': 'vmc4', 'num_flows': 300000, 'num_pkts': 2000000},
                                # Inter VN,Inter Node,Pol
                                'TrafficProfile4': {'src_vm': 'vmc3', 'dst_vm': 'vmc7', 'num_flows': 300000, 'num_pkts': 2000000},
                                # Inter VN,Intra Node,FIP
                                'TrafficProfile5': {'src_vm': 'vmc5', 'dst_vm': 'vmc6', 'num_flows': 100000, 'num_pkts': 2000000},
                                'TrafficProfile6': {'src_vm': 'vmc8', 'dst_vm': 'vmc5', 'num_flows': 100000, 'num_pkts': 2000000}}  # Inter VN,Inter Node,FIP
        #
        # A master list of all the vm static routes defined.
        self.vm_static_route_master = {
            'vmc1': '111.1.1.0/28', 'vmc2': '111.2.1.0/28', 'vmc3': '111.3.1.0/28',
            'vmc4': '111.4.1.0/28', 'vmc5': '111.5.1.0/28', 'vmc7': '111.7.1.0/28', 'vmc8': '111.8.1.0/28'}
        self.vm_static_route_test = {}

        #
        # Define FIP pool
        self.fip_pools = {'project1': {
            'p1-vn3-pool1': {'host_vn': 'vnet3', 'target_projects': ['project1']},
            'p1-vn4-pool2': {'host_vn': 'vnet4', 'target_projects': ['project1']},
            'p1-vn5-pool3': {'host_vn': 'vnet5', 'target_projects': ['project1']},
        }
        }
        #self.fvn_vm_map = {'vnet3':['vmc6', 'vmc8'], 'vnet4':['vmc5'], 'vnet5':['vmc5']}
        self.fvn_vm_map = {'project1': {
            'vnet3': {'project1': ['vmc6', 'vmc8']},
            'vnet4': {'project1': ['vmc5']},
            'vnet5': {'project1': ['vmc5']},
        }
        }
    # end __init__

    def build_topo_project1(self, domain='default-domain', project='project1', username='juniper', password='juniper123'):
        #
        # Topo for project: project1
        # Define Domain and project
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = ['vnet1', 'vnet2', 'vnet3', 'vnet4', 'vnet5', 'vnet6']
        #
        # Define network info for each VN:
        self.vn_nets = {
            'vnet1': ['10.1.1.0/30', '10.1.1.4/30', '10.1.1.8/30'], 'vnet2': ['10.2.1.0/30', '10.2.1.4/30'], 'vnet3': ['10.3.1.0/30', '10.3.1.4/30', '10.3.1.8/30'],
            'vnet4': ['10.4.1.0/30', '10.4.1.4/30', '10.5.1.8/30'], 'vnet5': ['10.5.1.0/30', '10.5.1.4/30', '10.5.1.8/30'], 'vnet6': ['10.6.1.0/30', '10.6.1.4/30']}
        #
        # Define netowrk IPAM for each VN, if not defined default-user-created
        # ipam will be created and used
        self.vn_ipams = {'vnet1': 'ipam1', 'vnet2': 'ipam2', 'vnet3':
                         'ipam3', 'vnet4': 'ipam4', 'vnet5': 'ipam5', 'vnet6': 'ipam6'}
        #
        # Define network policies
        self.policy_list = ['policy1', 'policy2']
        self.vn_policy = {'vnet1': ['policy1'], 'vnet2': ['policy1'],
                          'vnet3': [], 'vnet4': ['policy2'], 'vnet5': [], 'vnet6': []}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {
            'vmc1': 'vnet1', 'vmc2': 'vnet1', 'vmc3': 'vnet1', 'vmc4': 'vnet2', 'vmc5': 'vnet3',
            'vmc6': 'vnet4', 'vmc7': 'vnet2', 'vmc8': 'vnet5', 'vmc9': 'vnet4', 'vmd10': 'vnet6'}
        #
        # Define static route behind vms.
        self.vm_static_route = {
            'vmc1': '111.1.1.0/28', 'vmc2': '111.2.1.0/28', 'vmc3': '111.3.1.0/28',
            'vmc4': '111.4.1.0/28', 'vmc5': '111.5.1.0/28', 'vmc7': '111.7.1.0/28', 'vmc8': '111.8.1.0/28'}
        self.vm_static_route_test.update(self.vm_static_route)

        #
        # Define network policy rules
        self.rules = {}
        self.rules['policy1'] = [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'default-domain:project1:vnet2', 'source_network':
                'default-domain:project1:vnet1', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'default-domain:project1:vnet1', 'source_network': 'default-domain:project1:vnet2', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules[
            'policy2'] = [{'direction': '<>', 'protocol': 'udp', 'dest_network': 'default-domain:project2:vnet7',
                           'source_network': 'default-domain:project1:vnet4', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]

        # Define security_group name
        self.sg_list = ['test_sg_p1']
        #
        # Define security_group with vm
        self.sg_of_vm = {
            'vmc1': 'test_sg_p1', 'vmc2': 'test_sg_p1', 'vmc3': 'test_sg_p1', 'vmc4': 'test_sg_p1', 'vmc5': 'test_sg_p1',
            'vmc6': 'test_sg_p1', 'vmc7': 'test_sg_p1', 'vmc8': 'test_sg_p1', 'vmc9': 'test_sg_p1', 'vmd10': 'test_sg_p1'}
        # Define the security_group rules
        import uuid
        uuid_1 = uuid.uuid1().urn.split(':')[2]
        uuid_2 = uuid.uuid1().urn.split(':')[2]
        uuid_3 = uuid.uuid1().urn.split(':')[2]
        self.sg_rules = {}
        self.sg_rules['test_sg_p1'] = [
            {'direction': '>',
                'protocol': 'any', 'rule_uuid': uuid_1,
                'dst_addresses': [{'security_group': 'local'}],
                'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                'src_ports': [{'start_port': 0, 'end_port': 65535}],
                'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
             }, {'direction': '>',
                 'protocol': 'any', 'rule_uuid': uuid_2,
                 'src_addresses': [{'security_group': 'local'}],
                 'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                 'src_ports': [{'start_port': 0, 'end_port': 65535}],
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 }, {'direction': '>',
                     'protocol': 'any', 'rule_uuid': uuid_3,
                     'src_addresses': [{'security_group': 'default-domain:project1:test_sg_p1'}],
                     'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                     'src_ports': [{'start_port': 0, 'end_port': 65535}],
                     'dst_addresses': [{'security_group': 'local'}]}]

        return self
    # end build_topo_project1

# end sdn_flow_test_topo_single_project

################################################################################
class sdn_4vn_xvm_config ():
    def __init__(self):
        print "building dynamic topo"
    # end __init__

    def build_topo_admin (self, domain= 'default-domain', project= 'admin', compute_node_list= None, username= None, password= None):
        ##
        # Domain and project defaults: Do not change until support for non-default is tested!
        self.domain= domain; self.project= project; self.username= username; self.password= password
        ##
        # Define VN's in the project:
        self.vnet_list=  ['vnet1','vnet2', 'vnet3', 'vnet4']
        ##
        # Define network info for each VN:
        self.vn_nets=  {'vnet1': ['10.1.1.0/24', '11.1.1.0/24'], 'vnet2': ['10.1.2.0/24', '11.1.2.0/24'], 'vnet3': ['10.1.3.0/24', '11.1.3.0/24'], 'vnet4': ['10.1.4.0/24', '11.1.4.0/24']}
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
        self.rules['policy0']= [
            {'direction': '<>', 'protocol': 'any', 'dest_network': 'any', 'source_network': 'any', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules['policy1']= [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet1', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'vnet2', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules['policy100']= [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'any', 'source_network': 'any', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]

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
               {'direction' : '>',
                 'protocol' : 'udp',
                 'dst_addresses': [{'security_group': 'local', 'subnet' : None}],
                 'dst_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'src_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'src_addresses': [{'subnet' : {'ip_prefix' : '0.0.0.0', 'ip_prefix_len' : 0}}],
                 'rule_uuid': uuid_1
               },{'direction' : '>',
                 'protocol' : 'any',
                 'src_addresses': [{'security_group': 'local', 'subnet' : None}],
                 'dst_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'src_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'dst_addresses': [{'subnet' : {'ip_prefix' : '0.0.0.0', 'ip_prefix_len' : 0}}],'rule_uuid': uuid_2}]

        self.sg_rules[self.sg_list[4]]=[
               {'direction' : '>',
                 'protocol' : 'udp',
                 'dst_addresses': [{'security_group': 'local', 'subnet' : None}],
                 'dst_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'src_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'src_addresses': [{'security_group': self.domain + ':'+ self.project+ ':'+ self.sg_list[4]}],
                 'rule_uuid': uuid_1
               },{'direction' : '>',
                 'protocol' : 'any',
                 'src_addresses': [{'security_group': 'local', 'subnet' : None}],
                 'dst_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'src_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'dst_addresses': [{'subnet' : {'ip_prefix' : '0.0.0.0', 'ip_prefix_len' : 0}}],'rule_uuid': uuid_2}]

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

        return self
        # end build_topo
# end class sdn_4vn_xvm_config
################################################################################


if __name__ == '__main__':
    print "Currently topology limited to one domain/project.."
    print "Based on need, can be extended to cover config for multiple domain/projects"
    print "Running unit test for this module ..."
    my_topo = sdn_basic_policy_topo_with_3_project(domain='default-domain')
    x = my_topo.__dict__
    print "\nprinting keys of topology dict:"
    for key, value in x.iteritems():
        print key
    print
    # print "keys & values:"
    # for key, value in x.iteritems(): print key, "-->", value
    # Use topology_helper to extend/derive data from user-defined topology to help verifications.
    # ex. get list of all vm's from topology; get list of vn's associated to a
    # policy
    import topo_helper
    topo_h = topo_helper.topology_helper(my_topo)
    #vmc_list= topo_h.get_vmc_list()
    policy_vn = topo_h.get_policy_vn()
    print "printing derived topo data - vn's associated to a policy: \n", policy_vn
#
