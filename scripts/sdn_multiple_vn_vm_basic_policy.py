'''*******AUTO-GENERATED TOPOLOGY*********'''


class sdn_multiple_vn_vm_basic_config ():

    def __init__(self, domain='default-domain', project='admin', username=None, password=None):
        #
        # Domain and project defaults: Do not change until support for
        # non-default is tested!
        self.domain = domain
        self.project = project, self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = ['vnet0', 'vnet1']
        #
        # Define network info for each VN:
        self.vn_nets = {'vnet0': ['10.1.1.0/30', '11.1.1.0/30'],
                        'vnet1': ['12.1.1.0/30', '13.1.1.0/30']}
        #
        # Define network policies
        self.policy_list = ['policy0', 'policy1']
        self.vn_policy = {'vnet0': ['policy0'], 'vnet1': ['policy0']}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'vmc0': 'vnet0', 'vmc1': 'vnet1'}
        #
        # Define network policy rules
        self.rules = {}

        self.rules[
            'policy0'] = [{'direction': '<>', 'protocol': 'any', 'dest_network': 'vnet0',
                           'source_network': 'vnet1', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules[
            'policy1'] = [{'direction': '<>', 'protocol': 'any', 'dest_network': 'any',
                           'source_network': 'any', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]

        # end __init__

if __name__ == '__main__':
    print "Currently topology limited to one domain/project.."
    print "Based on need, can be extended to cover config for multiple domain/projects"
    print "Running unit test for this module ..."
    my_topo = sdn_multiple_vn_vm_basic_config(
        domain='default-domain', project='admin')
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
