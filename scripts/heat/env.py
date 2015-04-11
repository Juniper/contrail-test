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
