'''*******AUTO-GENERATED TOPOLOGY*********'''


class sdn_basic_policy_topo_with_3_project ():

    def __init__(self, domain='default-domain'):
        print "building dynamic topo"
        self.project_list = ['project1', 'project2', 'project3', 'admin']
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
        self.vnet_list = ['vnet1']
        #
        # Define network info for each VN:
        self.vn_nets = {'vnet1': ['10.1.1.0/24', '11.1.1.0/24']}
        #
        # Define netowrk IPAM for each VN, if not defined default-user-created
        # ipam will be created and used
        self.vn_ipams = {'vnet1': 'project1-ipam'}
        #
        # Define network policies
        self.policy_list = ['policy1', 'policy4']
        self.vn_policy = {'vnet1': ['policy1', 'policy4']}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'vmc1': 'vnet1'}
        #
        # Define network policy rules
        self.rules = {}
        self.rules[
            'policy1'] = [{'direction': '<>', 'protocol': 'icmp', 'dest_network': 'default-domain:project2:vnet2',
                           'source_network': 'default-domain:project1:vnet1', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules[
            'policy4'] = [{'direction': '<>', 'protocol': 'tcp', 'dest_network': 'default-domain:project3:vnet3',
                           'source_network': 'default-domain:project1:vnet1', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        # Define the security_group and its rules
        # Define security_group name
        self.sg_list = ['test_sg_p1']
        #
        # Define security_group with vm
        self.sg_of_vm = {'vmc1': ['test_sg_p1']}
        # Define the security group rules
        import uuid
        uuid_1 = uuid.uuid1().urn.split(':')[2]
        uuid_2 = uuid.uuid1().urn.split(':')[2]
        self.sg_rules = {}
        self.sg_rules['test_sg_p1'] = [
            {'direction': '>',
                'protocol': 'any',
                'dst_addresses': [{'security_group': 'local', 'subnet': None}],
                'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                'src_ports': [{'start_port': 0, 'end_port': 65535}],
                'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                'rule_uuid': uuid_1
             }, {'direction': '>',
                 'protocol': 'any',
                 'src_addresses': [{'security_group': 'local', 'subnet': None}],
                 'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                 'src_ports': [{'start_port': 0, 'end_port': 65535}],
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}], 'rule_uuid': uuid_2}, ]
        return self

    def build_topo_project2(self, domain='default-domain', project='project2', username='project2', password='project123'):
        #
        # Topo for project: project2
        # Define Domain and project
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = ['vnet2']
        #
        # Define network info for each VN:
        self.vn_nets = {'vnet2': ['12.1.1.0/24', '13.1.1.0/24']}
        #
        # Define netowrk IPAM for each VN, if not defined default-user-created
        # ipam will be created and used
        self.vn_ipams = {}
        #
        # Define network policies
        self.policy_list = ['policy2', 'policy5']
        self.vn_policy = {'vnet2': ['policy2', 'policy5']}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'vmc2': 'vnet2'}
        #
        # Define network policy rules
        self.rules = {}
        self.rules[
            'policy2'] = [{'direction': '<>', 'protocol': 'icmp', 'dest_network': 'default-domain:project1:vnet1',
                           'source_network': 'default-domain:project2:vnet2', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules[
            'policy5'] = [{'direction': '<>', 'protocol': 'icmp', 'dest_network': 'default-domain:admin:vnet-admin',
                           'source_network': 'default-domain:project2:vnet2', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        #
        # Define the security_group and its rules
        # Define security_group name
        self.sg_list = ['test_sg_p2']
        #
        # Define security_group with vm
        self.sg_of_vm = {'vmc2': ['test_sg_p2']}
        #
        # Define the security_group rules
        import uuid
        uuid_1 = uuid.uuid1().urn.split(':')[2]
        uuid_2 = uuid.uuid1().urn.split(':')[2]
        self.sg_rules = {}
        self.sg_rules['test_sg_p2'] = [
            {'direction': '>',
                'protocol': 'any',
                'dst_addresses': [{'security_group': 'local', 'subnet': None}],
                'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                'src_ports': [{'start_port': 0, 'end_port': 65535}],
                'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                'rule_uuid': uuid_1
             }, {'direction': '>',
                 'protocol': 'any',
                 'src_addresses': [{'security_group': 'local', 'subnet': None}],
                 'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                 'src_ports': [{'start_port': 0, 'end_port': 65535}],
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'rule_uuid': uuid_2}, ]

        return self

    def build_topo_project3(self, domain='default-domain', project='project3', username='project3', password='project123'):
        #
        # Topo for project: project3
        # Define Domain and project
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = ['vnet3']
        #
        # Define network info for each VN:
        self.vn_nets = {'vnet3': ['99.9.9.0/24']}
        #
        # Define netowrk IPAM for each VN, if not defined default-user-created
        # ipam will be created and used
        self.vn_ipams = {'vnet3': 'project3-ipam'}
        #
        # Define network policies
        self.policy_list = ['policy3']
        self.vn_policy = {'vnet3': ['policy3']}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'vmc3': 'vnet3'}
        #
        # Define network policy rules
        self.rules = {}
        self.rules[
            'policy3'] = [{'direction': '<>', 'protocol': 'tcp', 'dest_network': 'default-domain:project1:vnet1',
                           'source_network': 'default-domain:project3:vnet3', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        #
        # Define the security_group and its rules
        # Define security_group name
        self.sg_list = ['test_sg_p3']
        #
        # Define security_group with vm
        self.sg_of_vm = {'vmc3': ['test_sg_p3']}
        #
        # Define the security_group rules
        import uuid
        uuid_1 = uuid.uuid1().urn.split(':')[2]
        uuid_2 = uuid.uuid1().urn.split(':')[2]
        self.sg_rules = {}
        self.sg_rules['test_sg_p3'] = [
            {'direction': '>',
                'protocol': 'any',
                'dst_addresses': [{'security_group': 'local', 'subnet': None}],
                'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                'src_ports': [{'start_port': 0, 'end_port': 65535}],
                'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                'rule_uuid': uuid_1
             }, {'direction': '>',
                 'protocol': 'any',
                 'src_addresses': [{'security_group': 'local', 'subnet': None}],
                 'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                 'src_ports': [{'start_port': 0, 'end_port': 65535}],
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'rule_uuid': uuid_2
                 }, ]
        return self

    def build_topo_admin(self, domain='default-domain', project='admin', username=None, password=None):
        #
        # Topo for project: admin
        # Define Domain and project
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = ['vnet-admin']
        #
        # Define network info for each VN:
        self.vn_nets = {'vnet-admin': ['33.3.3.0/24']}
        #
        # Define netowrk IPAM for each VN, if not defined default-user-created
        # ipam will be created and used
        self.vn_ipams = {'vnet-admin': 'admin-ipam'}
        #
        # Define network policies
        self.policy_list = ['policy-admin']
        self.vn_policy = {'vnet-admin': ['policy-admin']}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'vmc-admin': 'vnet-admin'}
        #
        # Define network policy rules
        self.rules = {}
        self.rules[
            'policy-admin'] = [{'direction': '<>', 'protocol': 'icmp', 'dest_network': 'default-domain:project2:vnet2',
                                'source_network': 'default-domain:admin:vnet-admin', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        #
        # Define the security_group and its rules
        # Define security_group name
        self.sg_list = ['test_sg_admin']
        #
        # Define security_group with vm
        self.sg_of_vm = {'vmc-admin': ['test_sg_admin']}
        #
        # Define the security_group rules
        import uuid
        uuid_1 = uuid.uuid1().urn.split(':')[2]
        uuid_2 = uuid.uuid1().urn.split(':')[2]
        self.sg_rules = {}
        self.sg_rules['test_sg_admin'] = [
            {'direction': '>',
                'protocol': 'any',
                'dst_addresses': [{'security_group': 'local', 'subnet': None}],
                'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                'src_ports': [{'start_port': 0, 'end_port': 65535}],
                'src_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                'rule_uuid': uuid_1
             }, {'direction': '>',
                 'protocol': 'any',
                 'src_addresses': [{'security_group': 'local', 'subnet': None}],
                 'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                 'src_ports': [{'start_port': 0, 'end_port': 65535}],
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}],
                 'rule_uuid': uuid_2
                 }, ]
        return self
    # end sdn_basic_policy_topo_with_3_project


class sdn_basic_policy_topo_with_fip ():

    def __init__(self, domain='default-domain', compute_node_list=None):
        print "building dynamic topo"
        self.project_list = ['project1', 'project2', 'project3', 'admin']

        # Define the vm to compute node mapping to pin a vm to a particular
        # compute node or else leave empty.
        #self.vm_node_map = {}
        self.vm_node_map = {'vmc1': 'CN0', 'vmc2':
                            'CN1', 'vmc3': 'CN0', 'vmc-admin': 'CN1'}

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
        self.vnet_list = ['vnet1']
        #
        # Define network info for each VN:
        self.vn_nets = {'vnet1': ['10.1.1.0/24', '11.1.1.0/24']}
        #
        # Define netowrk IPAM for each VN, if not defined default-user-created
        # ipam will be created and used
        self.vn_ipams = {'vnet1': 'project1-ipam'}
        #
        # Define network policies
        self.policy_list = ['policy1', 'policy4']
        self.vn_policy = {'vnet1': ['policy1', 'policy4']}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'vmc1': 'vnet1'}
        #
        # Define network policy rules
        self.rules = {}
        self.rules[
            'policy1'] = [{'direction': '<>', 'protocol': 'icmp', 'dest_network': 'default-domain:project2:vnet2',
                           'source_network': 'default-domain:project1:vnet1', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules[
            'policy4'] = [{'direction': '<>', 'protocol': 'tcp', 'dest_network': 'default-domain:project3:vnet3',
                           'source_network': 'default-domain:project1:vnet1', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        return self

    def build_topo_project2(self, domain='default-domain', project='project2', username='project2', password='project123'):
        #
        # Topo for project: project2
        # Define Domain and project
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = ['vnet2']
        #
        # Define network info for each VN:
        self.vn_nets = {'vnet2': ['12.1.1.0/24', '13.1.1.0/24']}
        #
        # Define netowrk IPAM for each VN, if not defined default-user-created
        # ipam will be created and used
        self.vn_ipams = {}
        #
        # Define network policies
        self.policy_list = ['policy2', 'policy5']
        self.vn_policy = {'vnet2': ['policy2', 'policy5']}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'vmc2': 'vnet2'}
        #
        # Define network policy rules
        self.rules = {}
        self.rules[
            'policy2'] = [{'direction': '<>', 'protocol': 'icmp', 'dest_network': 'default-domain:project1:vnet1',
                           'source_network': 'default-domain:project2:vnet2', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules[
            'policy5'] = [{'direction': '<>', 'protocol': 'icmp', 'dest_network': 'default-domain:admin:vnet-admin',
                           'source_network': 'default-domain:project2:vnet2', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        return self

    def build_topo_project3(self, domain='default-domain', project='project3', username='project3', password='project123'):
        #
        # Topo for project: project3
        # Define Domain and project
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = ['vnet3']
        #
        # Define network info for each VN:
        self.vn_nets = {'vnet3': ['99.9.9.0/24']}
        #
        # Define netowrk IPAM for each VN, if not defined default-user-created
        # ipam will be created and used
        self.vn_ipams = {'vnet3': 'project3-ipam'}
        #
        # Define network policies
        self.policy_list = ['policy3']
        self.vn_policy = {'vnet3': ['policy3']}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'vmc3': 'vnet3'}
        #
        # Define network policy rules
        self.rules = {}
        self.rules[
            'policy3'] = [{'direction': '<>', 'protocol': 'tcp', 'dest_network': 'default-domain:project1:vnet1',
                           'source_network': 'default-domain:project3:vnet3', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        return self

    def build_topo_admin(self, domain='default-domain', project='admin', username=None, password=None):
        #
        # Topo for project: admin
        # Define Domain and project
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = ['vnet-admin']
        #
        # Define network info for each VN:
        self.vn_nets = {'vnet-admin': ['33.3.3.0/24']}
        #
        # Define netowrk IPAM for each VN, if not defined default-user-created
        # ipam will be created and used
        self.vn_ipams = {'vnet-admin': 'admin-ipam'}
        #
        # Define network policies
        self.policy_list = ['policy-admin']
        self.vn_policy = {'vnet-admin': ['policy-admin']}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'vmc-admin': 'vnet-admin'}
        #
        # Define network policy rules
        self.rules = {}
        self.rules[
            'policy-admin'] = [{'direction': '<>', 'protocol': 'icmp', 'dest_network': 'default-domain:project2:vnet2',
                                'source_network': 'default-domain:admin:vnet-admin', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        #
        # Define public VN
        self.public_vn = 'public-vn'
        return self
   # end sdn_basic_policy_topo_with_fip

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
