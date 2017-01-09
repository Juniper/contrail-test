'''*******AUTO-GENERATED TOPOLOGY*********'''


class systest_topo_single_project ():

    def __init__(self, compute_node_list=None, domain='default-domain', project=None, username=None, password=None):
        self.project_list = ['project2']

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
        self.traffic_profile = {'TrafficProfile1': {'src_vm': 'vmc1', 'dst_vm': 'vmc2', 'num_flows': 9000, 'num_pkts': 90000},  # Intra VN,Intra Node
                                # Intra VN,Inter Node
                                'TrafficProfile2': {'src_vm': 'vmc4', 'dst_vm': 'vmc7', 'num_flows': 9000, 'num_pkts': 90000},
                                # Inter VN,Intra Node,Pol
                                'TrafficProfile3': {'src_vm': 'vmc3', 'dst_vm': 'vmc4', 'num_flows': 9000, 'num_pkts': 90000},
                                # Inter VN,Inter Node,Pol
                                'TrafficProfile4': {'src_vm': 'vmc3', 'dst_vm': 'vmc7', 'num_flows': 9000, 'num_pkts': 90000},
                                # Inter VN,Intra Node,FIP
                                'TrafficProfile5': {'src_vm': 'vmc5', 'dst_vm': 'vmc6', 'num_flows': 9000, 'num_pkts': 90000},
                                'TrafficProfile6': {'src_vm': 'vmc8', 'dst_vm': 'vmc5', 'num_flows': 9000, 'num_pkts': 90000}}  # Inter VN,Inter Node,FIP
        #self.traffic_profile = {'TrafficProfile1': {'src_vm': 'vmc1', 'dst_vm': 'vmc2', 'num_flows': 9000, 'num_pkts': 90000},  # Intra VN,Intra Node
        #                        'TrafficProfile6': {'src_vm': 'vmc8', 'dst_vm': 'vmc5', 'num_flows': 9000, 'num_pkts': 90000}}  # Inter VN,Inter Node,FIP
        #
        # A master list of all the vm static routes defined.
        self.vm_static_route_master = {
            'vmc1': '111.1.1.0/28', 'vmc2': '111.2.1.0/28', 'vmc3': '111.3.1.0/28',
            'vmc4': '111.4.1.0/28', 'vmc5': '111.5.1.0/28', 'vmc7': '111.7.1.0/28', 'vmc8': '111.8.1.0/28'}
        self.vm_static_route_test = {}

        #
        # Define FIP pool
        self.fip_pools = {'project2': {
            'p1-vn3-pool1': {'host_vn': 'vnet3', 'target_projects': ['project2']},
            'p1-vn4-pool2': {'host_vn': 'vnet4', 'target_projects': ['project2']},
            'p1-vn5-pool3': {'host_vn': 'vnet5', 'target_projects': ['project2']},
        }
        }
        #self.fvn_vm_map = {'vnet3':['vmc6', 'vmc8'], 'vnet4':['vmc5'], 'vnet5':['vmc5']}
        self.fvn_vm_map = {'project2': {
            'vnet3': {'project2': ['vmc6', 'vmc8']},
            'vnet4': {'project2': ['vmc5']},
            'vnet5': {'project2': ['vmc5']},
        }
        }
    # end __init__

    def build_topo_project2(self, domain='default-domain', project='project2', username='juniper', password='juniper123'):
        #
        # Topo for project: project2
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
        self.policy_list = ['policy1', 'policy-si-1', 'policy-si-2']
        self.vn_policy = {'vnet1': ['policy1', 'policy-si-1'], 'vnet2': ['policy1'],
                          'vnet3': ['policy-si-2'], 'vnet4': [], 'vnet5': [], 'vnet6': []}
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

        ## Define Service template & instances
        self.st_list = ['st_trans_left', 'st_inNet_left']
        self.si_list = ['si-mirror-1', 'si-mirror-2']

        #
        # Define network policy rules
        self.rules = {}
        self.rules['policy1'] = [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'default-domain:project2:vnet2', 'source_network':
                'default-domain:project2:vnet1', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'default-domain:project2:vnet1', 'source_network': 'default-domain:project2:vnet2', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules['policy-si-1'] = [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'any', 'source_network': 'any', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any', 'action_list': {'simple_action':'pass', 'mirror_to': {'analyzer_name' : ':'.join([self.domain,self.project,self.si_list[0]])}}}]
        self.rules['policy-si-2'] = [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'any', 'source_network': 'any', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any', 'action_list': {'simple_action':'pass', 'mirror_to': {'analyzer_name' : ':'.join([self.domain,self.project,self.si_list[1]])}}}]

         #ST and SI topology
        self.st_params = {}
        self.si_params = {}

        self.st_params[self.st_list[0]]={'svc_img_name': 'analyzer', 'svc_type':'analyzer', 'if_list':[['left', False, False]], 'svc_mode':'transparent', 'svc_scaling':False, 'flavor':'contrail_flavor_2cpu', 'ordered_interfaces': True}
        self.st_params[self.st_list[1]] = {'svc_img_name': 'analyzer', 'svc_type':'analyzer', 'if_list':[['left', False, False]], 'svc_mode':'in-network', 'svc_scaling':False, 'flavor':'contrail_flavor_2cpu', 'ordered_interfaces': True}

        self.si_params[self.si_list[0]] = {'svc_template':self.st_list[0], 'if_list':self.st_params[self.st_list[0]]['if_list'], 'left_vn':None}
        self.si_params[self.si_list[1]] = {'svc_template':self.st_list[1], 'if_list':self.st_params[self.st_list[1]]['if_list'], 'left_vn':None}

        self.pol_si= {self.policy_list[1]:self.si_list[0], self.policy_list[2]:self.si_list[1]}
        self.si_pol = {self.si_list[0]:self.policy_list[1], self.si_list[1]:self.policy_list[2]}

        # Define security_group name
        self.sg_list = ['test_sg_p1']
        #
        # Define security_group with vm
        self.sg_of_vm = {
            'vmc1': ['test_sg_p1'], 'vmc2': ['test_sg_p1'], 'vmc3': ['test_sg_p1'], 'vmc4': ['test_sg_p1'], 'vmc5': ['test_sg_p1'],
            'vmc6': ['test_sg_p1'], 'vmc7': ['test_sg_p1'], 'vmc8': ['test_sg_p1'], 'vmc9': ['test_sg_p1'], 'vmd10': ['test_sg_p1']}
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
                     'src_addresses': [{'security_group': 'default-domain:project2:test_sg_p1'}],
                     'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                     'src_ports': [{'start_port': 0, 'end_port': 65535}],
                     'dst_addresses': [{'security_group': 'local'}]}]

        return self
    # end build_topo_project2

# end sdn_flow_test_topo_single_project
