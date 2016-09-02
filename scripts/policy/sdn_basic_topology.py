'''*******AUTO-GENERATED TOPOLOGY*********'''
from tcutils.util import get_random_name

class sdn_basic_config ():

    def __init__(self, domain='default-domain', project='admin', username=None, password=None):
        #
        # Domain and project defaults: Do not change until support for
        # non-default is tested!
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = [get_random_name('vnet0'), get_random_name('vnet1'),
                          get_random_name('vnet2'), get_random_name('vnet3')]
        #
        # Define network info for each VN:
        if self.project == 'vCenter':
            # For vcenter, only one subnet per VN is supported
            self.vn_nets = {
                self.vnet_list[0]: ['10.1.1.0/24'],
                self.vnet_list[1]: ['12.1.1.0/24'],
                self.vnet_list[2]: ['14.1.1.0/24'],
                self.vnet_list[3]: ['16.1.1.0/24']
            }
        else:
            self.vn_nets = {
                self.vnet_list[0]: ['10.1.1.0/24', '11.1.1.0/24'],
                self.vnet_list[1]: ['12.1.1.0/24', '13.1.1.0/24'],
                self.vnet_list[2]: ['14.1.1.0/24', '15.1.1.0/24'],
                self.vnet_list[3]: ['16.1.1.0/24', '17.1.1.0/24']
            }
        #
        # Define network policies
        self.policy_list = list()
        self.vn_policy = dict()
        for i in range(8):
            self.policy_list.append(get_random_name('policy%d'%i))
        for i,vn in enumerate(self.vnet_list):
            self.vn_policy[vn] = [self.policy_list[i*2],
                                  self.policy_list[(i*2)+1]]
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {get_random_name('vmc0'): self.vnet_list[0],
                         get_random_name('vmc1'): self.vnet_list[1]}
        #
        # Define network policy rules
        self.rules = {}

        self.rules[self.policy_list[0]] = [
            {'direction': '>', 'protocol': 'any',
             'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[0],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]},
            {'direction': '>', 'protocol': 'any',
             'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[0],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [1, 1]},
            {'direction': '>', 'protocol': 'any',
             'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[0],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]},
            {'direction': '>', 'protocol': 'any',
             'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[0],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 3]}]

        self.rules[self.policy_list[1]] = [
            {'direction': '>', 'protocol': 'any',
             'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[0],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]},
            {'direction': '>', 'protocol': 'any',
             'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[0],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [1, 1]},
            {'direction': '>', 'protocol': 'any',
             'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[0],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]},
            {'direction': '>', 'protocol': 'any',
             'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[0],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 3]}]

        self.rules[self.policy_list[2]] = [
            {'direction': '>', 'protocol': 'udp',
             'dest_network': self.vnet_list[1], 'source_network': self.vnet_list[1],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]},
            {'direction': '>', 'protocol': 'udp',
             'dest_network': self.vnet_list[1], 'source_network': self.vnet_list[1],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [1, 1]},
            {'direction': '>', 'protocol': 'udp',
             'dest_network': self.vnet_list[1], 'source_network': self.vnet_list[1],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]},
            {'direction': '>', 'protocol': 'udp',
             'dest_network': self.vnet_list[1], 'source_network': self.vnet_list[1],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 3]}]

        self.rules[self.policy_list[3]] = [
            {'direction': '>', 'protocol': 'icmp',
             'dest_network': self.vnet_list[1], 'source_network': self.vnet_list[1],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]},
            {'direction': '>', 'protocol': 'icmp',
             'dest_network': self.vnet_list[1], 'source_network': self.vnet_list[1],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [1, 1]},
            {'direction': '>', 'protocol': 'icmp',
             'dest_network': self.vnet_list[1], 'source_network': self.vnet_list[1],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]},
            {'direction': '>', 'protocol': 'icmp',
             'dest_network': self.vnet_list[1], 'source_network': self.vnet_list[1],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 3]}]

        self.rules[self.policy_list[4]] = [
            {'direction': '>', 'protocol': 'udp',
             'dest_network': self.vnet_list[2], 'source_network': self.vnet_list[2],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]},
            {'direction': '>', 'protocol': 'udp',
             'dest_network': self.vnet_list[2], 'source_network': self.vnet_list[2],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [1, 1]},
            {'direction': '>', 'protocol': 'udp',
             'dest_network': self.vnet_list[2], 'source_network': self.vnet_list[2],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]},
            {'direction': '>', 'protocol': 'udp',
             'dest_network': self.vnet_list[2], 'source_network': self.vnet_list[2],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 3]}]

        self.rules[self.policy_list[5]] = [
            {'direction': '>', 'protocol': 'tcp',
             'dest_network': self.vnet_list[2], 'source_network': self.vnet_list[2],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]},
            {'direction': '>', 'protocol': 'tcp',
             'dest_network': self.vnet_list[2], 'source_network': self.vnet_list[2],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [1, 1]},
            {'direction': '>', 'protocol': 'tcp',
             'dest_network': self.vnet_list[2], 'source_network': self.vnet_list[2],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]},
            {'direction': '>', 'protocol': 'tcp',
             'dest_network': self.vnet_list[2], 'source_network': self.vnet_list[2],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 3]}]

        self.rules[self.policy_list[6]] = [
            {'direction': '>', 'protocol': 'icmp',
             'dest_network': self.vnet_list[3], 'source_network': self.vnet_list[3],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]},
            {'direction': '>', 'protocol': 'icmp',
             'dest_network': self.vnet_list[3], 'source_network': self.vnet_list[3],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [1, 1]},
            {'direction': '>', 'protocol': 'icmp',
             'dest_network': self.vnet_list[3], 'source_network': self.vnet_list[3],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]},
            {'direction': '>', 'protocol': 'icmp',
             'dest_network': self.vnet_list[3], 'source_network': self.vnet_list[3],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 3]}]

        self.rules[self.policy_list[7]] = [
            {'direction': '>', 'protocol': 'any',
             'dest_network': self.vnet_list[3], 'source_network': self.vnet_list[3],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]},
            {'direction': '>', 'protocol': 'any',
             'dest_network': self.vnet_list[3], 'source_network': self.vnet_list[3],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [1, 1]},
            {'direction': '>', 'protocol': 'any',
             'dest_network': self.vnet_list[3], 'source_network': self.vnet_list[3],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]},
            {'direction': '>', 'protocol': 'any',
             'dest_network': self.vnet_list[3], 'source_network': self.vnet_list[3],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 3]}]

        # end __init__

if __name__ == '__main__':
    print "Currently topology limited to one domain/project.."
    print "Based on need, can be extended to cover config for multiple domain/projects"
    print "Running unit test for this module ..."
    my_topo = sdn_basic_config(domain='default-domain', project='admin')
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
