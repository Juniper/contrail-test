

class FlowScaleTopology ():

    def __init__(
            self,
            compute_node_list=None,
            domain='default-domain',
            project='admin',
            username=None,
            password=None):
        #
        # Domain and project defaults: Do not change until support for
        # non-default is tested!
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password

        # Define the vm to compute node mapping to pin a vm to a particular
        # compute node or else leave empty.
        #self.vm_node_map = {}
        self.vm_node_map = {}
        if compute_node_list is not None:
            if len(compute_node_list) >= 2:
                self.vm_node_map = {
                    'vmc1': 'CN0',
                    'vmc2': 'CN1'}

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
        self.traffic_profile = {'1to2': {'src_vm': 'vmc1', 'dst_vm': 'vmc2', 'num_flows': 500000, 'num_pkts': 5000000}}

        #
        # Define VN's in the project:
        self.vnet_list = ['vnet1']
        #
        # Define network info for each VN:
        self.vn_nets = {
            'vnet1': ['10.1.1.0/24']}
        #
        # Define netowrk IPAM for each VN, if not defined default-user-created
        # ipam will be created and used
        self.vn_ipams = {
            'vnet1': 'ipam1'}
        #
        # Define network policies
        self.policy_list = []
        self.vn_policy = {'vnet1': []}
        #
        # Define network policy rules
        self.rules = {}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {
            'vmc1': 'vnet1',
            'vmc2': 'vnet1'}
    # end __init__

# end FlowScaleTopology
