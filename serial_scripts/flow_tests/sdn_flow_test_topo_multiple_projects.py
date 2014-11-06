class multi_project_topo ():

    def __init__(self, domain='default-domain', compute_node_list=None):
        self.project_list = ['project1', 'project2']

        # Define the vm to compute node mapping to pin a vm to a particular
        # compute node or else leave empty.
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
        self.traffic_profile = {
            'TrafficProfile1': {'src_vm': 'vmc3', 'dst_vm': 'vmd11', 'num_flows': 50000, 'num_pkts': 100000, 'src_proj': 'project1', 'dst_proj': 'project2'}}
        #
        # A master list of all the vm static routes defined.
        self.vm_static_route_master = {
            'vmc1': '111.1.1.0/28', 'vmc2': '111.2.1.0/28',
            'vmc3': '111.3.1.0/28', 'vmc4': '111.4.1.0/28', 'vmc7': '111.7.1.0/28'}
        self.vm_static_route_test = {}

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
            'vnet1': ['10.1.1.0/24'], 'vnet2': ['10.2.1.0/24'], 'vnet3': ['10.3.1.0/24'],
            'vnet4': ['10.4.1.0/24'], 'vnet5': ['10.5.1.0/24'], 'vnet6': ['10.6.1.0/24']}
        #
        # Define netowrk IPAM for each VN, if not defined default-user-created
        # ipam will be created and used
        self.vn_ipams = {'vnet1': 'ipam1', 'vnet2': 'ipam2', 'vnet3':
                         'ipam3', 'vnet4': 'ipam4', 'vnet5': 'ipam5', 'vnet6': 'ipam6'}
        #
        # Define network policies
        self.policy_list = ['policy1', 'policy2']
        self.vn_policy = {'vnet1': ['policy1', 'policy2'], 'vnet2': ['policy1'],
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
        self.vm_static_route = {'vmc1': '111.1.1.0/28', 'vmc2': '111.2.1.0/28',
                                'vmc3': '111.3.1.0/28', 'vmc4': '111.4.1.0/28', 'vmc7': '111.7.1.0/28'}
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
                           'source_network': 'default-domain:project1:vnet1', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        return self
    # end build_topo_project1

    def build_topo_project2(self, domain='default-domain', project='project2', username='project2-user', password='juniper123'):
        #
        # Topo for project: project2
        # Define Domain and project
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = ['vnet7']
        #
        # Define network info for each VN:
        self.vn_nets = {'vnet7': ['10.7.1.0/24']}
        #
        # Define netowrk IPAM for each VN, if not defined default-user-created
        # ipam will be created and used
        self.vn_ipams = {'vnet7': 'ipam7'}
        #
        # Define network policies
        self.policy_list = ['policy3']
        self.vn_policy = {'vnet7': ['policy3']}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'vmd11': 'vnet7'}
        #
        # Define network policy rules
        self.rules = {}
        self.rules[
            'policy3'] = [{'direction': '<>', 'protocol': 'udp', 'dest_network': 'default-domain:project1:vnet1',
                           'source_network': 'default-domain:project2:vnet7', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        return self
    # end build_topo_project2

# end multi_project_topo
