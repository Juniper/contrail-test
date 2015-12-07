'''*******AUTO-GENERATED TOPOLOGY*********'''


class sdn_webui_config ():

    def __init__(
            self,
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
        #
        # Define VN's in the project:
        self.vnet_list = ['vnet0', 'vnet1',
                          'vnet2', 'vnet3', 'left_vn', 'right_vn']
        #
        # Define network info for each VN:
        self.vn_nets = {
            'left_vn': ['31.1.1.0/24'],
            'right_vn': ['41.2.2.0/24'],
            'vnet0': [
                '10.1.1.0/24',
                '11.1.1.0/24'],
            'vnet1': [
                '12.1.1.0/24',
                '13.1.1.0/24'],
            'vnet2': [
                '14.1.1.0/24',
                '15.1.1.0/24'],
            'vnet3': [
                '16.1.1.0/24',
                '17.1.1.0/24']}
        #
        # Define network policies
        self.policy_list = ['allow_tcp', 'policy0',
                            'policy1', 'policy2', 'policy3']
        self.vn_policy = {
            'left_vn': ['allow_tcp'], 'right_vn': ['allow_tcp'], 'vnet0': [
                'policy0', 'policy1'], 'vnet1': [
                'policy2', 'policy3'], 'vnet2': [
                'policy2', 'policy3'], 'vnet3': [
                    'policy2', 'policy3']}
        #
        # Define ipams ##
        self.vn_ipams = {'vnet1': 'ipam1', 'vnet2': 'ipam2', 'vnet3': 'ipam3'}

        # Define ports ##
        self.port_list = ['port1', 'port2']
        self.port_params = {
            'port1': {
                'port_name': 'port1',
                'net': 'vnet0',
                'mac': 'fe:78:c5:1d:2f:b6',
                'subnet': '11.1.1.0/24',
                'state': 'Up',
                'fixed_ip': '11.1.1.55',
                'fip': '',
                'sg': '',
                'device_owner': ''},
            'port2': {
                'port_name': 'port2',
                'net': 'vnet0',
                'mac': '',
                'subnet': '10.1.1.0/24',
                'state': 'Up',
                'fixed_ip': '',
                'fip': '',
                'sg': '',
                'device_owner': ''}}

        # Define Routers
        self.router_list = {
            'router1': {
                'state': 'Up',
                'gateway': None,
                'snat': True,
                'networks': [
                    'vnet0',
                    'vnet1']},
            'router2': {
                'state': 'Down',
                'gateway': None,
                'snat': True,
                'networks': [
                    'vnet0',
                    'vnet1']}}
        # define dns_servers #
        self.dns_server_list = ['dserver1']
        self.dns_server_params = {
            'dserver1': {
                'domain_name': 'domain1',
                'rr_order': 'Random',
                'fip_record': 'VM Name',
                'ipam_list': [
                    'ipam3',
                    'ipam2'],
                'dns_forwarder': '20.1.1.2',
                'ttl': '500'}}

        # define dns_records #
        self.dns_record_list = ['drecord1']
        self.dns_record_params = {
            'drecord1': {
                'host_name': 'host1',
                'server_name': 'dserver1',
                'ip_address': '25.1.1.1',
                'type': '',
                'dns_class': '',
                'ttl': '500'}}

        # Define the security_group and its rules
        # Define security_group name
        self.sg_list = ['sg_allow_udp', 'sg_allow_udp_sg', 'sg_allow_icmp']
        self.sg_names = self.sg_list[:]
        # Define the security group rules
        import uuid
        uuid_1 = uuid.uuid1().urn.split(':')[2]
        uuid_2 = uuid.uuid1().urn.split(':')[2]
        self.sg_rules = {}
        for sg in self.sg_list:
            self.sg_rules[sg] = []
        self.sg_rules[self.sg_list[0]] = [
            {'direction': '>',
                'protocol': 'udp',
             'dst_addresses': [{'security_group': 'local', 'subnet': None}],
             'dst_ports': [{'start_port': 50, 'end_port': 15000}],
             'src_ports': [{'start_port': 50, 'end_port': 20000}],
             'src_addresses': [{'subnet': {'ip_prefix': '50.2.0.0', 'ip_prefix_len': 9}}],
             'rule_uuid': uuid_1, 'eth_type': 'IPv4'
             }, {'direction': '>',
                 'protocol': 'any',
                 'src_addresses': [{'security_group': 'local', 'subnet': None}],
                 'dst_ports': [{'start_port': 0, 'end_port': 5000}],
                 'src_ports': [{'start_port': 25, 'end_port': 6000}],
                 'dst_addresses': [{'subnet': {'ip_prefix': '20.1.0.0', 'ip_prefix_len': 16}}], 'rule_uuid': uuid_2, 'eth_type': 'IPv4'}]

        self.sg_rules[self.sg_list[1]] = [
            {'direction': '>',
                'protocol': 'udp',
             'dst_addresses': [{'security_group': 'local', 'subnet': None}],
             'dst_ports': [{'start_port': 0, 'end_port': 65535}],
             'src_ports': [{'start_port': 0, 'end_port': 65535}],
             'src_addresses': [{'subnet': {'ip_prefix': '100.2.1.0', 'ip_prefix_len': 24}}],
             'rule_uuid': uuid_1, 'eth_type': 'IPv4'
             }, {'direction': '>',
                 'protocol': 'any',
                 'src_addresses': [{'security_group': 'local', 'subnet': None}],
                 'dst_ports': [{'start_port': 0, 'end_port': 65535}],
                 'src_ports': [{'start_port': 0, 'end_port': 65535}],
                 'dst_addresses': [{'subnet': {'ip_prefix': '0.0.0.0', 'ip_prefix_len': 0}}], 'rule_uuid': uuid_2, 'eth_type': 'IPv4'}]

        # define service templates ##
        self.st_list = ['tcp_svc_template']
        self.st_params = {'tcp_svc_template': {'svc_img_name': 'vsrx-bridge',
                                               'svc_type': 'firewall',
                                               'if_list': [['management',
                                                            False,
                                                            False],
                                                           ['left',
                                                            False,
                                                            False],
                                                           ['right',
                                                            False,
                                                            False]],
                                               'svc_mode': 'transparent',
                                               'svc_scaling': False,
                                               'flavor': 'm1.medium',
                                               'ordered_interfaces': True}}

        # define service instance
        self.si_list = ['svcinst1']
        self.si_params = {
            'svcinst1': {
                'if_list': [
                    [
                        'management', False, False], [
                        'left', False, False], [
                        'right', False, False]], 'svc_template': 'tcp_svc_template', 'left_vn': None, 'right_vn': None}}
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'left_vm': 'left_vn',
                         'right_vm': 'right_vn', 'vmc0': 'vnet0'}
        #
        # Define VN to VM mappings for each of the floating ip pools to be
        # created.
        self.fvn_vm_map = {'admin': {
            'vnet3': {'admin': ['vmc0']}}}
        # Define network policy rules
        self.rules = {}

        self.rules['allow_tcp'] = [
            {
                'direction': '<>',
                'protocol': 'tcp',
                'dest_network': 'right_vn',
                'source_network': 'left_vn',
                'dst_ports': [
                    9000,
                    9001],
                'simple_action': 'pass',
                'src_ports': [
                    8000,
                    8001]}]

        self.rules['policy0'] = [{'direction': '>',
                                  'protocol': 'any',
                                  'dest_network': 'vnet0',
                                  'source_network': 'vnet0',
                                  'dst_ports': 'any',
                                  'simple_action': 'deny',
                                  'src_ports': [4,
                                                5]},
                                 {'direction': '>',
                                  'protocol': 'any',
                                  'dest_network': 'vnet0',
                                  'source_network': 'vnet0',
                                  'dst_ports': 'any',
                                  'simple_action': 'deny',
                                  'src_ports': [1,
                                                2]},
                                 {'direction': '>',
                                  'protocol': 'any',
                                  'dest_network': 'vnet0',
                                  'source_network': 'vnet0',
                                  'dst_ports': 'any',
                                  'simple_action': 'deny',
                                  'src_ports': [2,
                                                3]},
                                 {'direction': '>',
                                  'protocol': 'any',
                                  'dest_network': 'vnet0',
                                  'source_network': 'vnet0',
                                  'dst_ports': 'any',
                                  'simple_action': 'deny',
                                  'src_ports': [3,
                                                4]}]

        self.rules['policy1'] = [{'direction': '>',
                                  'protocol': 'any',
                                  'dest_network': 'vnet0',
                                  'source_network': 'vnet0',
                                  'dst_ports': 'any',
                                  'simple_action': 'deny',
                                  'src_ports': [4,
                                                5]},
                                 {'direction': '>',
                                  'protocol': 'any',
                                  'dest_network': 'vnet0',
                                  'source_network': 'vnet0',
                                  'dst_ports': 'any',
                                  'simple_action': 'deny',
                                  'src_ports': [1,
                                                2]},
                                 {'direction': '>',
                                  'protocol': 'any',
                                  'dest_network': 'vnet0',
                                  'source_network': 'vnet0',
                                  'dst_ports': 'any',
                                  'simple_action': 'deny',
                                  'src_ports': [2,
                                                3]},
                                 {'direction': '>',
                                  'protocol': 'any',
                                  'dest_network': 'vnet0',
                                  'source_network': 'vnet0',
                                  'dst_ports': 'any',
                                  'simple_action': 'deny',
                                  'src_ports': [3,
                                                4]}]

        self.rules['policy2'] = [{'direction': '>',
                                  'protocol': 'udp',
                                  'dest_network': 'vnet1',
                                  'source_network': 'vnet1',
                                  'dst_ports': 'any',
                                  'simple_action': 'deny',
                                  'src_ports': [4,
                                                5]},
                                 {'direction': '>',
                                  'protocol': 'udp',
                                  'dest_network': 'vnet1',
                                  'source_network': 'vnet1',
                                  'dst_ports': 'any',
                                  'simple_action': 'deny',
                                  'src_ports': [1,
                                                2]},
                                 {'direction': '>',
                                  'protocol': 'udp',
                                  'dest_network': 'vnet1',
                                  'source_network': 'vnet1',
                                  'dst_ports': 'any',
                                  'simple_action': 'deny',
                                  'src_ports': [2,
                                                3]},
                                 {'direction': '>',
                                  'protocol': 'udp',
                                  'dest_network': 'vnet1',
                                  'source_network': 'vnet1',
                                  'dst_ports': 'any',
                                  'simple_action': 'deny',
                                  'src_ports': [3,
                                                4]}]

        self.rules['policy3'] = [{'direction': '>',
                                  'protocol': 'icmp',
                                  'dest_network': 'vnet1',
                                  'source_network': 'vnet1',
                                  'dst_ports': 'any',
                                  'simple_action': 'deny',
                                  'src_ports': [4,
                                                5]},
                                 {'direction': '>',
                                  'protocol': 'icmp',
                                  'dest_network': 'vnet1',
                                  'source_network': 'vnet1',
                                  'dst_ports': 'any',
                                  'simple_action': 'deny',
                                  'src_ports': [1,
                                                2]},
                                 {'direction': '>',
                                  'protocol': 'icmp',
                                  'dest_network': 'vnet1',
                                  'source_network': 'vnet1',
                                  'dst_ports': 'any',
                                  'simple_action': 'deny',
                                  'src_ports': [2,
                                                3]},
                                 {'direction': '>',
                                  'protocol': 'icmp',
                                  'dest_network': 'vnet1',
                                  'source_network': 'vnet1',
                                  'dst_ports': 'any',
                                  'simple_action': 'deny',
                                  'src_ports': [3,
                                                4]}]

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
