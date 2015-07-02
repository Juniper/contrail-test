'''*******AUTO-GENERATED TOPOLOGY*********'''


class sdn_single_vm_multiple_policy_config ():

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
        self.vnet_list = ['vnet0']
        #
        # Define network info for each VN:
        if self.project == 'vCenter':
            # For vcenter, only one subnet per VN is supported
            self.vn_nets = {'vnet0': ['10.1.1.0/24']}
        else:
            self.vn_nets = {'vnet0': ['10.1.1.0/24', '11.1.1.0/24']}
        #
        # Define network policies
        self.policy_list = ['policy0', 'policy1', 'policy2', 'policy3',
                            'policy4', 'policy5', 'policy6', 'policy7', 'policy8', 'policy9']
        self.vn_policy = {
            'vnet0': ['policy0', 'policy1', 'policy2', 'policy3',
                      'policy4', 'policy5', 'policy6', 'policy7', 'policy8', 'policy9']}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'vmc0': 'vnet0'}
        #
        # Define network policy rules
        self.rules = {}

        self.rules['policy0'] = [{'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [
            1, 1]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 3]}]

        self.rules['policy1'] = [{'direction': '>', 'protocol': 'icmp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]}, {'direction': '>', 'protocol': 'icmp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [
            1, 1]}, {'direction': '>', 'protocol': 'icmp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]}, {'direction': '>', 'protocol': 'icmp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 3]}]

        self.rules['policy2'] = [{'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [
            1, 1]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 3]}]

        self.rules['policy3'] = [{'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [
            1, 1]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 3]}]

        self.rules['policy4'] = [{'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [
            1, 1]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 3]}]

        self.rules['policy5'] = [{'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [
            1, 1]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 3]}]

        self.rules['policy6'] = [{'direction': '>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]}, {'direction': '>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [
            1, 1]}, {'direction': '>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]}, {'direction': '>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 3]}]

        self.rules['policy7'] = [{'direction': '>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]}, {'direction': '>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [
            1, 1]}, {'direction': '>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]}, {'direction': '>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 3]}]

        self.rules['policy8'] = [{'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [
            1, 1]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 3]}]

        self.rules['policy9'] = [{'direction': '>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]}, {'direction': '>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [
            1, 1]}, {'direction': '>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]}, {'direction': '>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 3]}]
        # end __init__

if __name__ == '__main__':
    print "Currently topology limited to one domain/project.."
    print "Based on need, can be extended to cover config for multiple domain/projects"
    print
    my_topo = sdn_single_vm_multiple_policy_config(
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
#
