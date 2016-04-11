left_net_env = {u'parameters': {u'left_net_gateway': u'10.10.10.1', u'left_net_name': u'vn-left',
                                u'left_net_pool_end': u'10.10.10.253', u'left_net_pool_start': u'10.10.10.2', u'left_net_cidr': u'10.10.10.0/24'}}

right_net_env = {u'parameters': {u'right_net_name': u'vn-right', u'right_net_pool_end': u'20.20.20.253',
                                 u'right_net_gateway': u'20.20.20.1', u'right_net_cidr': u'20.20.20.0/24', u'right_net_pool_start': u'20.20.20.2'}}

vms_env = {u'parameters': {u'right_net_id': u'e6f9e85b-5816-4818-bea6-089262c63f5d', u'left_net_id':
                           u'3f162ab2-85ff-4ad0-8161-9ae4633e7359', u'image': u'ubuntu-traffic', u'flavor': u'm1.medium'}}

svc_temp_env = {u'parameters': {u'name': u'st1', u'service_interface_type_list': u'management,left,right', u'image': u'vsrx', u'static_routes_list':
                                u'False,False,False', u'mode': u'in-network-nat', u'flavor': u'm1.medium',  u'service_scaling': 'False', u'type': u'firewall', u'shared_ip_list': u'False,False,False'}}

svc_inst_env = {u'parameters': {u'service_template_fq_name': u'default-domain:st1', u'left_net_id': u'3f162ab2-85ff-4ad0-8161-9ae4633e7359',
                                u'service_instance_name': u'si1', u'max_instances': u'1', u'right_net_id': u'e6f9e85b-5816-4818-bea6-089262c63f5d'}}

svc_chain_env = {u'parameters': {u'direction': u'<>', u'dst_port_end': -1, u'protocol': u'any', u'dst_port_start': -1, u'policy_name': u'pol1', u'dst_vn_id':
                                 u'e6f9e85b-5816-4818-bea6-089262c63f5d', u'src_vn_id': u'3f162ab2-85ff-4ad0-8161-9ae4633e7359', u'apply_service': u'default-domain:admin:si1', u'src_port_end': -1, u'src_port_start': -1}}

transit_net_env = {"parameters": {"transit_net_cidr": "30.30.30.0/24",
                                  "transit_net_name": "transit-vn", "allow_transit": "True"}}

svc_port_tuple_env = {"parameters": {"svm_name": "pt_svm", "dst_port_end": -1, "protocol": "any", "service_template_properties_version": 2, "image": "cirros", "domain": "default-domain", "service_template_properties_ordered_interfaces": "true", "service_template_properties_service_mode": "in-network-nat", "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_3": "3.3.3.0", "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_2": "2.2.2.0", "simple_action": "pass", "flavor": "m1.tiny", "src_port_start": -1, "right_vn_fqdn": "", "service_template_properties_service_type": "firewall", "left_vn": "left_vn", "network_ipam_refs_data_ipam_subnets_addr_from_start_true": "true", "left_vn_fqdn": "", "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_3": 24, "service_template_properties_interface_type_service_interface_type_3": "right", "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_1": 24, "service_template_properties_interface_type_service_interface_type_1": "management", "src_port_end": -1, "direction": "<>", "service_template_properties_flavor": "m1.medium", "service_template_properties_image_name": "vsrx", "service_template_properties_interface_type_service_interface_type_2": "left", "service_instance_name": "pt_instance", "right_vn": "right_vn", "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_2": 24, "service_instance_fq_name": "", "dst_port_start": -1, "service_template_name": "pt_template", "management_network": "management_vn", "left_vm_name": "left_vm", "right_vm_name": "right_vm", "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_1": "1.1.1.0", "policy_name": "pt_policy"}}
