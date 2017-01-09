
class sdn_headless_vrouter_topo ():

    def __init__(self, domain='default-domain', compute_node_list=None):
        print "building dynamic topo"
        self.project_list = ['project1']
        # Define the vm to compute node mapping to pin a vm to a particular
        # compute node or else leave empty.
        #self.vm_node_map = {}
        self.vm_node_map = {}
        if compute_node_list is not None:
            if len(compute_node_list) >= 2:
                self.vm_node_map = {'VM11': 'CN0', 'VM21': 'CN1'}

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

    def build_topo_project1(
            self,
            domain='default-domain',
            project='project1',
            username='juniper',
            password='juniper123'):
        #
        # Topo for project: project1
        # Define Domain and project
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = ['vnet1', 'vnet2']
        #
        # Define network info for each VN:
        self.vn_nets = {'vnet1': ['10.1.1.0/24'], 'vnet2': ['10.2.1.0/24']}
        #
        # Define netowrk IPAM for each VN, if not defined default-user-created
        # ipam will be created and used
        self.vn_ipams = {'vnet1': 'ipam1', 'vnet2': 'ipam2'}
        #
        # Define network policies
        self.policy_list = ['policy1']
        self.vn_policy = {'vnet1': ['policy1'], 'vnet2': ['policy1']}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'VM11': 'vnet1', 'VM21': 'vnet2'}
        #
        # Define network policy rules
        self.rules = {}
        self.rules['policy1'] = [{'direction': '<>',
                                  'protocol': 'icmp',
                                  'dest_network': 'default-domain:project1:vnet2',
                                  'source_network': 'default-domain:project1:vnet1',
                                  'dst_ports': 'any',
                                  'simple_action': 'pass',
                                  'src_ports': 'any'},
                                 {'direction': '<>',
                                  'protocol': 'icmp',
                                  'dest_network': 'default-domain:project1:vnet1',
                                  'source_network': 'default-domain:project1:vnet2',
                                  'dst_ports': 'any',
                                  'simple_action': 'pass',
                                  'src_ports': 'any'}]

        return self
    # end build_topo_project1

# end sdn_flow_test_topo_single_project

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

