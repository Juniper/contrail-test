'''*******AUTO-GENERATED TOPOLOGY*********'''

import sys
from tcutils.util import get_random_name

class sdn_single_vm_policy_config ():

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
        self.vnet_list = [get_random_name('vnet0')]
        #
        # Define network info for each VN:
        self.vn_nets = {self.vnet_list[0]: ['10.1.1.0/24']}
        #
        # Define network policies
        self.policy_list = list()
        for i in range(3):
            self.policy_list.append(get_random_name('policy%d'%i))
        self.vn_policy = {self.vnet_list[0]: self.policy_list[:2]}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {get_random_name('vmc0'): self.vnet_list[0]}
        #
        # Define network policy rules
        self.rules = {}

        self.rules[self.policy_list[0]] = [
            {'direction': '>', 'protocol': 'tcp',
             'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[0],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]},
            {'direction': '>', 'protocol': 'tcp',
             'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[0],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [1, 1]},
            {'direction': '>', 'protocol': 'tcp',
             'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[0],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]}]

        self.rules[self.policy_list[1]] = [
            {'direction': '>', 'protocol': 'icmp',
             'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[0],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'}]

        self.rules[self.policy_list[2]] = [
            {'direction': '>', 'protocol': 'udp',
             'dest_network': self.vnet_list[0], 'source_network': self.vnet_list[0],
             'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [10, 10]}]
        # end __init__

if __name__ == '__main__':
    print "Currently topology limited to one domain/project.."
    print "Based on need, can be extended to cover config for multiple domain/projects"
    print
    my_topo = sdn_single_vm_policy_config(
        domain='default-domain', project='admin')
    x = my_topo.__dict__
    # print "keys only:"
    # for key, value in x.iteritems(): print key
    # print
    # print "keys & values:"
    # for key, value in x.iteritems(): print key, "-->", value
    import topo_helper
    topo_h = topo_helper.topology_helper(my_topo)
    #vmc_list= topo_h.get_vmc_list()
    policy_vn = topo_h.get_policy_vn()
    vmc_list = topo_h.get_vmc_list()
    policy_vn = topo_h.get_policy_vn()
    # To unit test topology:
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        topo_h.test_module()
#
