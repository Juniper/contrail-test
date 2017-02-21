'''*******AUTO-GENERATED TOPOLOGY*********'''


class sdn_webui_config ():

    def __init__(
            self,
            domain='default-domain',
            project='admin',
            username='admin',
            password='contrail123'):
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

        # Define Link Local Service
        self.link_local_service_list = ['link_service1']
        self.link_local_service_params = {
            'link_service1': {
                'service_name': 'link_service1',
                'service_ip': '30.0.0.7',
                'service_port' : '30',
                'address_type': 'IP',
                'fabric_ip' : ['10.9.0.9', '10.8.0.10'],
                'fabric_port' : '10'}}

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
        self.st_params = {'tcp_svc_template': {'svc_img_name': 'tiny_trans_fw',
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
                                               'flavor': 'm1.tiny',
                                               }}

        # define service instance
        self.si_list = ['svcinst1']
        self.si_params = {
            'svcinst1': {
                'if_list': [
                    [
                        'management', False, False], [
                        'left', False, False], [
                        'right', False, False]], 'svc_template': 'tcp_svc_template', 'left_vn': None, 'right_vn': None}}

        # define service health check
        self.shc_list = ['svc_health_check1']
        self.shc_params = {
            'svc_health_check1': {
                'probe_type': 'PING',
                'http_url': 'local-ip',
                'delay': 3,
                'timeout': 5,
                'max_retries': 2,
                'hc_type': 'link-local'}}

        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'left_vm': 'left_vn',
                         'right_vm': 'right_vn', 'vmc0': 'vnet0'}

        # Define FIP pool
        self.fip_pools = {project: {
            'p1-vn3-pool1': {'host_vn': 'vnet3', 'target_projects': [project]}}}

        # Define VN to VM mappings for each of the floating ip pools to be
        # created.
        self.fvn_vm_map = {project: {
            'vnet3': {project: ['vmc0']}}}

        self.fvn_vm_map_dict = {'vnet3': ['vmc0']}

        #Define BGP as a Service parameters
        self.bgpaas_list = ['bgpaas1']
        self.bgpaas_params = {
            'bgpaas1': {
                'autonomous_system': 65000,
                'ip_address': '10.1.1.5',
                'hold_time': 60,
                'loop_count': 2 }}

        #Define QoS parameters
        self.qos_list = ['qos1']
        self.qos_params = {
            'qos1': {
                'default_fc_id': '1',
                'dscp_mapping': {'af11 (001010)': '2'},
                'exp_mapping': {'be1 (001)': '3'},
                'dot1p_mapping': {'ef1 (011)': '4'}}}
        
        #Define parameters for attaching Qos config to VN
        self.vn_qos_list = ['qos1']
        self.vn_qos_params = {
            'vnet1': 'qos1' }
        
        #Define Physical Router parameters
        self.pr_list = ['phy_rtr1']
        self.pr_params = {
            'phy_rtr1': {
                'mgmt_ip': '20.1.1.5',
                'vendor': 'Juniper',
                'model': 'mx',
                'ssh_username': 'root',
                'ssh_password': 'Embe1mpls',
                'tunnel_ip': '30.1.1.15',
                'router_type': 'BGP Router',
                'source_port': '15',
                'hold_time': '180',
                'auth_type': 'md5',
                'auth_key': '123' }}

        #Define Physical Interface parameters
        self.pif_list = ['ge-0/0/0']
        self.pif_params = {
            'ge-0/0/0': {
                'int_type': 'Physical' }}

        #Define Forwarding Class parameters
        self.fc_list = ['1', '2', '3', '4']
        self.fc_params = {
            '1': {
                'fc_id': 1,
                'dscp': 'ef (101110)',
                'dot1p': 'be (000)',
                'exp': 'af12 (101)',
                'queue_num': 1},
            '2': {
                'fc_id': 2,
                'dscp': 'af12 (001100)',
                'dot1p': 'ef (010)',
                'exp': 'be1 (001)',
                'queue_num': 2},
            '3': {
                'fc_id': 3,
                'dscp': 'cs1 (001000)',
                'dot1p': 'nc1/cs6 (110)',
                'exp': 'nc2/cs7 (111)',
                'queue_num': 3},
            '4': {
                'fc_id': 4,
                'dscp': 'nc1/cs6 (110000)',
                'dot1p': 'af12 (101)',
                'exp': 'af11 (100)',
                'queue_num': 4}}
        
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

        self.subnet_edit = "20.20.20.0"
        self.subnet_adv_option = "20.20.20.0/24"
        self.asn_ip = "20.20.20.3"
        self.invalid_asn_ip = "20,20,20,3"
        self.asn_num = "65534"
        self.invalid_asn_num = "65534ab"
        self.target_num = "4294967295"
        self.invalid_target_num = "4294967295abc"
        self.mask = "24"
        self.subnet_sip = "20.20.20.5"
        self.subnet_eip = "20.20.20.20"
        self.subnet_dns_ip = "20.20.20.2"
        self.subnet_gate_ip = "20.20.20.1"
        self.subnet_default_gate_ip = "0.0.0.0"
        self.host_prefix = "1.1.1.1/24"
        self.host_nexthop = "2.2.2.2"
        self.phy_net = "phy1"
        self.vlan_id = "4094"
        self.fpool = "pool1"
        self.invalid_vlan_id = "4094abcd49494"
        self.dns_ip = "1.1.1.1"
        self.invalid_dns_ip = "1,1,1,1"
        self.vn_disp_name = "vn-test"
        self.vn_disp_name_spl_char = "vn1~`!@#$%^&*()_+}{|:\"?><,./;\'[]\=-"
        self.vn_disp_name_spl_char_ops = "vn1~`!@#$%^&*()_+}{|:\\\"?><,./;\'[]\\\\=-"
        self.vn_name_beg_spl_char = "~!@#$%^&*()_+|}{\"?><,./;\'[]\=-`vn1"
        self.vn_name_end_spl_char = "vn1~!@#$%^&*()_+|}{\"?><,./;\'[]\=-`"
        self.vn_name_mid_spl_char = "vn1~!@#$%^&*()_+|}{\"?><,./;\'[]\=-`vn1"
        self.port_name = 'port1'
        self.dhcp_option_code = '15'
        self.dhcp_option_value = '16'
        self.invalid_ip_mask = '8,8,8,8/32'
        self.invalid_mac = '02,87,2a,82,8d,bc'
        self.invalid_port = '6ab'
        self.port_advanced_option = {
            'analyzer_name': 'ana1',
            'allowed_address_pair_mac': '02:87:2a:82:8d:bc',
            'analyzer_ip': '7.7.7.7',
            'analyzer_mac': '02:87:2a:82:8d:32',
            'allowed_address_pair_ip': '5.5.5.5/32',
            'subnet_ip': '10.1.1.9',
            'port': '5',
            'vtep_dst_ip_address': '9.9.9.9',
            'vtep_dst_mac_address': '02:87:2a:82:8d:de',
            'vxlan_id': '10'
        }
        self.fat_flow_values = {'TCP':'5', 'ICMP':'2', 'UDP':'4', 'SCTP':'7'}
        self.sub_interface_name = 'port1-subinterface1'
        self.orig_bgp_asn = '64512'
        self.bgp_restart_time = '120'
        self.invalid_bgp_restart_time = ['60abc', '60abc!@#$%^~&*()_+|}:;/.,<>?']
        self.orig_bgp_restart_time = '60'
        self.bgp_llgr_time = '600'
        self.orig_bgp_llgr_time = '300'
        self.invalid_bgp_llgr_time = ['300abc', '300abc!@#$%^~&*()_+|}:;/.,<>?']
        self.bgp_end_rib = '60'
        self.orig_bgp_end_rib = '30'
        self.invalid_bgp_end_rib = ['30abc', '30abc!@#$%^~&*()_+|}:;/.,<>?']
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
