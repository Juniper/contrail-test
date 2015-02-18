'''*******AUTO-GENERATED TOPOLOGY*********'''


class SystestTopoSingleProject ():

    def __init__(
            self,
            compute_node_list=None,
            domain='default-domain',
            project=None,
            username=None,
            password=None):
        self.project_list = ['project2']

        # Define the vm to compute node mapping to pin a vm to a particular
        # compute node or else leave empty.
        #self.vm_node_map = {}
        self.vm_node_map = {}
        if compute_node_list is not None:
            if len(compute_node_list) == 2:
                self.vm_node_map = {
                    'vmc1': 'CN0', 'vmc2': 'CN0',
                }

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
            'TrafficProfile1': {
                'src_vm': 'vmc1',
                'dst_vm': 'vmc2',
                'num_flows': 9000,
                'num_pkts': 90000}}
        #
        # A master list of all the vm static routes defined.
        self.vm_static_route_master = {
            'vmc1': '111.1.1.0/28', 'vmc2': '111.2.1.0/28'
        }
        self.vm_static_route_test = {}

        #
        # Define FIP pool
        self.fip_pools = {}
        self.fvn_vm_map = {}
    # end __init__

    def build_topo_project2(
            self,
            domain='default-domain',
            project='project2',
            username='juniper',
            password='juniper123'):
        #
        # Topo for project: project2
        # Define Domain and project
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = ['vnet1']
        #
        # Define network info for each VN:
        self.vn_nets = {
            'vnet1': ['10.1.1.0/28', '10.1.1.16/28', '10.1.1.32/28']}
        #
        # Define netowrk IPAM for each VN, if not defined default-user-created
        # ipam will be created and used
        self.vn_ipams = {'vnet1': 'ipam1'}
        #
        # Define network policies
        self.policy_list = ['policy1', 'policy-si-1', 'policy-si-2']
        self.vn_policy = {'vnet1': ['policy1', 'policy-si-1']
                          }
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {
            'vmc1': 'vnet1', 'vmc2': 'vnet1'
        }
        #
        # Define static route behind vms.
        self.vm_static_route = {
            'vmc1': '111.1.1.0/28', 'vmc2': '111.2.1.0/28'}
        self.vm_static_route_test.update(self.vm_static_route)

        # Define Service template & instances
        self.st_list = ['st_trans_left', 'st_inNet_left']
        self.si_list = ['si-mirror-1', 'si-mirror-2']

        #
        # Define network policy rules
        self.rules = {}
        self.rules['policy1'] = [{'direction': '<>',
                                  'protocol': 'udp',
                                  'dest_network': 'default-domain:project2:vnet1',
                                  'source_network': 'local',
                                  'dst_ports': 'any',
                                  'simple_action': 'pass',
                                  'src_ports': 'any'}]
        self.rules['policy-si-1'] = [{'direction': '<>',
                                      'protocol': 'udp',
                                      'dest_network': 'any',
                                      'source_network': 'any',
                                      'dst_ports': 'any',
                                      'simple_action': 'pass',
                                      'src_ports': 'any',
                                      'action_list': {'simple_action': 'pass',
                                                       'mirror_to': {'analyzer_name': ':'.join([self.domain,
                                                                                                self.project,
                                                                                                self.si_list[0]])}}}]
        self.rules['policy-si-2'] = [{'direction': '<>',
                                      'protocol': 'udp',
                                      'dest_network': 'any',
                                      'source_network': 'any',
                                      'dst_ports': 'any',
                                      'simple_action': 'pass',
                                      'src_ports': 'any',
                                      'action_list': {'simple_action': 'pass',
                                                       'mirror_to': {'analyzer_name': ':'.join([self.domain,
                                                                                                self.project,
                                                                                                self.si_list[1]])}}}]

        # ST and SI topology
        self.st_params = {}
        self.si_params = {}

        self.st_params[
            self.st_list[0]] = {
            'svc_img_name': 'analyzer',
            'svc_type': 'analyzer',
            'if_list': [
                [
                    'left',
                    False,
                    False]],
            'svc_mode': 'transparent',
                'svc_scaling': False,
                'flavor': 'm1.medium',
            'ordered_interfaces': True}
        self.st_params[
            self.st_list[1]] = {
            'svc_img_name': 'analyzer',
            'svc_type': 'analyzer',
            'if_list': [
                [
                    'left',
                    False,
                    False]],
            'svc_mode': 'in-network',
                'svc_scaling': False,
                'flavor': 'm1.medium',
            'ordered_interfaces': True}

        self.si_params[
            self.si_list[0]] = {
            'svc_template': self.st_list[0],
            'if_list': self.st_params[
                self.st_list[0]]['if_list'],
            'left_vn': None}
        self.si_params[
            self.si_list[1]] = {
            'svc_template': self.st_list[1],
            'if_list': self.st_params[
                self.st_list[1]]['if_list'],
            'left_vn': None}

        self.pol_si = {
            self.policy_list[1]: self.si_list[0],
            self.policy_list[2]: self.si_list[1]}
        self.si_pol = {
            self.si_list[0]: self.policy_list[1],
            self.si_list[1]: self.policy_list[2]}

        # Define security_group name
        self.sg_list = ['test_sg_p1']
        #
        # Define security_group with vm
        self.sg_of_vm = {
            'vmc1': ['test_sg_p1'], 'vmc2': ['test_sg_p1']}
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
