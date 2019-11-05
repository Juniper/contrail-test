'''*******AUTO-GENERATED TOPOLOGY*********'''
from __future__ import print_function


from builtins import object
class sdn_webui_config(object):

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
        self.link_local_service_list = ['link_service1', 'link_service2']
        self.link_local_service_params = {
            'link_service1': {
                'service_name': 'link_service1',
                'service_ip': '30.0.0.7',
                'service_port' : '30',
                'address_type': 'IP',
                'fabric_ip' : ['10.9.0.9', '10.8.0.10'],
                'fabric_port' : '10'},
            'link_service2': {
                'service_name': 'link_service2',
                'service_ip': '40.0.0.7',
                'service_port' : '34',
                'address_type': 'DNS',
                'fabric_ip' : '11.9.0.9',
                'fabric_port' : '11'}}

        # Define Virtual Routers
        self.vrouter_list = ['vrouter1', 'vrouter2', 'vrouter3']
        self.vrouter_params = {
            'vrouter1': {
                'type': 'Embedded',
                'ip': '90.1.0.5'},
            'vrouter2': {
                'type': 'TOR Agent',
                'ip': '80.1.0.5'},
            'vrouter3': {
                'type': 'TOR Service Node',
                'ip' : '70.1.0.5'}}

        # Define Service Appliance Sets
        self.svc_appl_set_list = ['svc_appl_set1']
        self.svc_appl_set_params = {
            'svc_appl_set1': {
                'load_balancer': 'lbdriver1',
                'ha_mode': 'HA',
                'key': 'testkey',
                'value': 'testvalue'}}

        # Define Service Appliance Sets
        self.svc_appliances_list = ['svc_appl1']
        self.svc_appliances_params = {
            'svc_appl1': {
                'svc_appl_set': 'svc_appl_set1',
                'svc_appl_ip': '60.1.1.7',
                'user_name': 'svcappl1',
                'password': 'svcappl1',
                'key': 'testkey',
                'value': 'testvalue'}}

        # Define Alarms
        self.alarms_list = ['vn_acl_project', 'vn_acl_global']
        self.alarms_params = {
            'vn_acl_project': {
                'uve_keys': ['virtual-network'],
                'alarm_severity': 'major',
                'operand1': 'UveVirtualNetworkConfig.total_acl_rules',
                'operand2': '2',
                'operation': '<=',
                'parent_type': 'project'},
            'vn_acl_global': {
                'uve_keys': ['virtual-network'],
                'alarm_severity': 'minor',
                'operand1': 'UveVirtualNetworkConfig.total_acl_rules',
                'operand2': '3',
                'operation': '<=',
                'parent_type': 'global'}}

        # Define RBAC
        self.rbac_list = ['rbac_acl_global', 'rbac_acl_domain', 'rbac_acl_project']
        self.rbac_params = {
            'rbac_acl_global': {
                'parent_type': 'global',
                'rules': {
                    'rule_object': 'virtual-networks',
                    'rule_field': 'network_policy_refs',
                    'perms': [{'role': 'admin', 'crud': 'Create, Read'}]}},
            'rbac_acl_domain': {
                'parent_type': 'domain',
                'rules': {
                    'rule_object': 'virtual-machines',
                    'rule_field': 'display_name',
                    'perms': [{'role': 'Member', 'crud': 'Read, Delete'}]}},
            'rbac_acl_project': {
                'parent_type': 'project',
                'rules': {
                    'rule_object': 'network-policys',
                    'rule_field': 'id_perms',
                    'perms': [{'role': 'admin', 'crud': 'Create, Update'}]}}}

        # Definde LogStatistic
        self.log_stat_list = ['stats_log']
        self.log_stat_params = {
            'stats_log': {
                'regexp': 'error'}}

        # Define Flow Aging
        self.flow_age_proto_list = ['6 (TCP)', '17 (UDP)', '1 (ICMP)']
        self.flow_age_proto_params = {
            '6 (TCP)': {
                'port': '5',
                'timeout': '240'},
            '17 (UDP)': {
                'port': '9',
                'timeout': '180'},
            '1 (ICMP)': {
                'port': '1',
                'timeout': '120'}}

        # Define Interface Route Table
        self.intf_route_table_list = ['intf_rt1']
        self.intf_route_table_params = {
            'intf_rt1': {
                'prefixes': '100.1.1.0/24',
                'community': 'accept-own'}}

        #Define parameters for attaching Interface Route Table to port
        self.port_intf_params = {
            'port1': 'intf_rt1'}

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
        self.st_list = ['tcp_svc_template', 'nat_svc_template', 'svc_template_v2']
        self.st_params = {'tcp_svc_template': {'svc_img_name': 'tiny_trans_fw',
                                               'service_type': 'firewall',
                                               'if_details': {
                                                    'management' : {'shared_ip_enable' : False,
                                                                    'static_route_enable' : False
                                                                    },
                                                    'left' : {'shared_ip_enable' : False,
                                                              'static_route_enable' : False
                                                              },
                                                    'right' : {'shared_ip_enable' : False,
                                                               'static_route_enable' : False
                                                               }
                                                              },
                                               'service_mode': 'transparent',
                                               'svc_scaling': False,
                                               'flavor': 'm1.tiny',
                                               'version': 1
                                               },
                          'nat_svc_template': {'svc_img_name': 'tiny_nat_fw',
                                               'service_type': 'firewall',
                                               'if_details': {
                                                    'left' : {'shared_ip_enable' : False,
                                                              'static_route_enable' : False
                                                              },
                                                    'right' : {'shared_ip_enable' : False,
                                                               'static_route_enable' : False
                                                               }
                                                              },
                                               'service_mode': 'In-Network Nat',
                                               'svc_scaling': False,
                                               'flavor': 'contrail_flavor_tiny',
                                               'version': 1
                                               },
                          'svc_template_v2': {'svc_img_name': None,
                                               'service_type': 'firewall',
                                               'if_details': {
                                                    'left' : {'shared_ip_enable' : False,
                                                              'static_route_enable' : False
                                                              },
                                                    'right' : {'shared_ip_enable' : False,
                                                               'static_route_enable' : False
                                                               }
                                                              },
                                               'service_mode': 'transparent',
                                               'svc_scaling': False,
                                               'flavor': None,
                                               'version': 2
                                               }
                         }

        # define service instance
        self.si_list = ['svcinst1_v2']
        self.si_params = {
            'svcinst1_v2': {
                'if_details': {
                    'left' : {'vn_name' : 'left_vn'},
                    'right' : {'vn_name' : 'right_vn'}
                              },
                'svc_template' : 'svc_template_v2'
                }
            }

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

        #Define parameters for attaching service health check template to SI
        self.si_shc_list = ['svc_health_check1']
        self.si_shc_params = {
            'svcinst3_v2' : {
                'right': 'svc_health_check1'
            }}

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

        #Define Global QoS parameters
        self.qos_glob_list = ['qos_glob1', 'qos_glob2']
        self.qos_glob_params = {
            'qos_glob1': {
                'qos_config_type': 'vHost',
                'default_fc_id': '2',
                'dscp_mapping': {'cs1 (001000)': '4'},
                'exp_mapping': {'ef (010)': '1'},
                'dot1p_mapping': {'af11 (100)': '3'}},
            'qos_glob2': {
                'qos_config_type': 'Fabric',
                'default_fc_id': '3',
                'dscp_mapping': {'nc2/cs7 (111000)': '1'},
                'exp_mapping': {'af12 (101)': '2'},
                'dot1p_mapping': {'be1 (001)': '4'}}
                }

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
                'auth_key': '123',
                'set_netconf' : False}}

        #Define OVSDB managed ToR
        self.pr_tor_list = ['phy_rtr_tor1']
        self.pr_tor_params = {
            'phy_rtr_tor1': {
                'mgmt_ip': '21.1.1.5',
                'vendor': 'Juniper',
                'model': 'mx',
                'tunnel_ip': '32.1.1.15',
                'tor_agent': 'vrouter2',
                'tor_agent_opt': 'test_tor',
                'tsn': 'vrouter3',
                'tsn_opt': 'test_tsn',
                'set_tor': True}}

        #Define Netconf managed Physical Router
        self.netconf_pr_list = ['netconf_phy_rtr1']
        self.netconf_pr_params = {
            'netconf_phy_rtr1': {
                'mgmt_ip': '22.1.1.5',
                'vendor': 'Juniper',
                'model': 'mx',
                'tunnel_ip': '33.1.1.15',
                'ssh_username': 'root',
                'ssh_password': 'netconf@123',
                'set_netconf': True}}

        #Define VCPE router
        self.vcpe_list = ['vcpe_phy_rtr1']
        self.vcpe_params = {
            'vcpe_phy_rtr1': {
                'mgmt_ip': '23.1.1.5',
                'tunnel_ip': '34.1.1.15',
                'set_vcpe': True}}

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

        #Define Network Route Table parameters
        self.nrt_list = ['rtbl1', 'rtbl2']
        self.nrt_params = {
            'rtbl1': {
                'prefix': '17.1.1.0/24',
                'nh_type': 'ip-address',
                'nexthop': '15.1.1.3' },
            'rtbl2': {
                'prefix': '15.1.1.0/24',
                'nh_type': 'ip-address',
                'nexthop': '17.1.1.3' }}

        #Define parameters for attaching Network Route Table to VN
        self.vn_nrt_list = ['rtbl1', 'rtbl2']
        self.vn_nrt_params = {
            'vnet2': 'rtbl1',
            'vnet3': 'rtbl2' }

        #Define Routing Policy parameters
        self.rp_list = ['rpol1', 'rpol2']
        self.rp_params = {
            'rpol1': {
                'term_from': 'prefix',
                'prefix': '41.2.2.0/24',
                'match_type': 'orlonger',
                'term_then': 'action',
                'action': 'Accept' },
            'rpol2': {
                'term_from': 'protocol',
                'match_type': 'bgp',
                'term_then': 'local-preference',
                'lp_value': 200 }}

        #Define parameters for attaching Routing Policy to SI
        self.si_rp_list = ['rpol1', 'rpol2']
        self.si_rp_params = {
            'svcinst2' : {
                'left': 'rpol1',
                'right': 'rpol2'
            }}

        #Define Route Aggregate parameters
        self.ragg_list = ['ragg1', 'ragg2']
        self.ragg_params = {
            'ragg1': [
                {'prefix': '32.1.1.0/24'},
                {'prefix': '33.1.1.0/24'}
                ],
            'ragg2': [
                {'prefix': '34.1.1.0/24'},
                {'prefix': '35.1.1.0/24'}
                ]}

        #Define parameters for attaching Route Aggregate to SI
        self.si_ra_list = ['ragg1', 'ragg2']
        self.si_ra_params = {
            'svcinst2' : {
                'left': 'ragg1',
                'right': 'ragg2'
            }}

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
        self.global_asn_num = '65532'
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
    print("Currently topology limited to one domain/project..")
    print("Based on need, can be extended to cover config for multiple domain/projects")
    print("Running unit test for this module ...")
    my_topo = sdn_webui_config(domain='default-domain', project='admin')
    x = my_topo.__dict__
    print("\nprinting keys of topology dict:")
    for key, value in x.items():
        print(key)
    print()
    # print "keys & values:"
    # for key, value in x.iteritems(): print key, "-->", value
    # Use topology_helper to extend/derive data from user-defined topology to help verifications.
    # ex. get list of all vm's from topology; get list of vn's associated to a
    # policy
    import topo_helper
    topo_h = topo_helper.topology_helper(my_topo)
    #vmc_list= topo_h.get_vmc_list()
    policy_vn = topo_h.get_policy_vn()
    print("printing derived topo data - vn's associated to a policy: \n", policy_vn)
#
