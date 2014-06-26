'''*******AUTO-GENERATED TOPOLOGY*********'''


class sdn_webui_config ():

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
        self.vnet_list = ['vnet0', 'vnet1',
                          'vnet2', 'vnet3', 'left_vn', 'right_vn']
        #
        # Define network info for each VN:
        self.vn_nets = {
            'left_vn': ['31.1.1.0/24'], 'right_vn': ['41.2.2.0/24'], 'vnet0': ['10.1.1.0/30', '11.1.1.0/30'],
            'vnet1': ['12.1.1.0/30', '13.1.1.0/30'], 'vnet2': ['14.1.1.0/30', '15.1.1.0/30'], 'vnet3': ['16.1.1.0/30', '17.1.1.0/30']}
        #
        # Define network policies
        self.policy_list = ['allow_tcp', 'policy0',
                            'policy1', 'policy2', 'policy3']
        self.vn_policy = {'left_vn': ['allow_tcp'], 'right_vn': ['allow_tcp'], 'vnet0': ['policy0', 'policy1'], 'vnet1': [
            'policy2', 'policy3'], 'vnet2': ['policy2', 'policy3'], 'vnet3': ['policy2', 'policy3']}
        #
        # Define ipams ##
        self.vn_ipams = {'vnet1': 'ipam1', 'vnet2': 'ipam2', 'vnet3': 'ipam3'}
        #
        # define service templates ##
        self.st_list = ['tcp_svc_template']
        self.st_params = {'tcp_svc_template': {'svc_img_name': 'vsrx-bridge',  'svc_type': 'firewall', 'if_list':
                                               [['management', False, False], ['left', False, False], ['right', False, False]],  'svc_mode': 'transparent', 'svc_scaling': False, 'flavor': 'm1.medium', 'ordered_interfaces': True}}

        # define service instance
        self.si_list = ['svcinst1']
        self.si_params = {
            'svcinst1': {'if_list': [['management', False, False], ['left', False, False],
                                     ['right', False, False]], 'svc_template': 'tcp_svc_template', 'left_vn': None, 'right_vn': None}}
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'left_vm': 'left_vn',
                         'right_vm': 'right_vn', 'vmc0': 'vnet0'}
        #
        # Define VN to VM mappings for each of the floating ip pools to be
        # created.
        self.fvn_vm_map = {'vnet3': ['vmc0']}
        # Define network policy rules
        self.rules = {}

        self.rules[
            'allow_tcp'] = [{'direction': '<>', 'protocol': 'tcp', 'dest_network': 'right_vn',
                             'source_network': 'left_vn', 'dst_ports': [9000, 9001], 'simple_action': 'pass', 'src_ports': [8000, 8001]}]

        self.rules['policy0'] = [{'direction': '>', 'protocol': 'any', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [4, 5]}, {'direction': '>', 'protocol': 'any', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [
            1, 2]}, {'direction': '>', 'protocol': 'any', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 3]}, {'direction': '>', 'protocol': 'any', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 4]}]

        self.rules['policy1'] = [{'direction': '>', 'protocol': 'any', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [4, 5]}, {'direction': '>', 'protocol': 'any', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [
            1, 2]}, {'direction': '>', 'protocol': 'any', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 3]}, {'direction': '>', 'protocol': 'any', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 4]}]

        self.rules['policy2'] = [{'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet1', 'source_network': 'vnet1', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [4, 5]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet1', 'source_network': 'vnet1', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [
            1, 2]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet1', 'source_network': 'vnet1', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 3]}, {'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet1', 'source_network': 'vnet1', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 4]}]

        self.rules['policy3'] = [{'direction': '>', 'protocol': 'icmp', 'dest_network': 'vnet1', 'source_network': 'vnet1', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [4, 5]}, {'direction': '>', 'protocol': 'icmp', 'dest_network': 'vnet1', 'source_network': 'vnet1', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [
            1, 2]}, {'direction': '>', 'protocol': 'icmp', 'dest_network': 'vnet1', 'source_network': 'vnet1', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 3]}, {'direction': '>', 'protocol': 'icmp', 'dest_network': 'vnet1', 'source_network': 'vnet1', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [3, 4]}]


        # end __init__

if __name__ == '__main__':
    print "Currently topology limited to one domain/project.."
    print "Based on need, can be extended to cover config for multiple domain/projects"
    print "Running unit test for this module ..."
    my_topo = sdn_webui_config(domain='default-domain', project='admin')
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
