from tcutils.util import get_random_cidr

ecmp_pt_env = {
    "parameters":
    {"domain": "default-domain",
     "dst_port_end": -1,
     "protocol": "any",
     "service_template_properties_version": 2,
     "svm2_name": "pt_svm2",
     "image": "cirros-0.3.0-x86_64-uec",
     "dst_port_start": -1,
     "service_template_properties_service_type": "firewall",
     "service_template_properties_service_mode": "in-network-nat",
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_3":
     '%s' % get_random_cidr().split('/')[0],
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_2":
     "%s" % get_random_cidr().split('/')[0],
     "simple_action": "pass",
     "flavor": "m1.tiny",
     "src_port_start": -1,
     "right_vn_fqdn": "",
     "service_template_properties_ordered_interfaces": "true",
     "left_vn": "left_vn",
     "network_ipam_refs_data_ipam_subnets_addr_from_start_true": "true",
     "left_vn_fqdn": "",
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_3": 24,
     "service_template_properties_interface_type_service_interface_type_3":
     "right",
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_1": 24,
     "service_template_properties_interface_type_service_interface_type_1":
     "management",
     "src_port_end": -1,
     "direction": "<>",
     "service_template_properties_flavor": "m1.medium",
     "service_template_properties_image_name": "vsrx",
     "service_template_properties_interface_type_service_interface_type_2":
     "left",
     "service_instance_name": "pt_instance",
     "right_vn": "right_vn",
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_2": 24,
     "service_instance_fq_name": "",
     "service_template_name": "pt_template",
     "management_network": "management_vn",
     "left_vm_name": "left_vm",
     "right_vm_name": "right_vm",
     "service_instance_properties_ha_mode": "active-active",
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_1":
     "%s" % get_random_cidr().split('/')[0],
     "policy_name": "pt_policy",
     "svm1_name": "pt_svm1"}
}

pt_multi_inline_env = {
    "parameters":
    {"svc_vn_mgmt_prefix": "%s" % get_random_cidr().split('/')[0],
     "svc_vn_prefix_len": 24,
     "domain": "default-domain",
     "dst_port_end": -1,
     "protocol": "any",
     "service_template_properties_version": 2,
     "svm2_name": "pt_svm2",
     "svc_vn_right": "svc_vn_right",
     "service_template1_properties_image_name": "vsrx-bridge",
     "service_instance1_name": "pt_instance1",
     "service_template_properties_service_type": "firewall",
     "service_template2_properties_service_mode": "in-network-nat",
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_3":
     "%s" % get_random_cidr().split('/')[0],
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_2":
     "%s" % get_random_cidr().split('/')[0],
     "simple_action": "pass",
     "flavor": "m1.tiny",
     "src_port_start": -1,
     "service_template1_properties_service_mode": "transparent",
     "service_template1_name": "pt_template1",
     "right_vn_fqdn": "",
     "service_template_properties_ordered_interfaces": "true",
     "network_ipam_refs_data_ipam_subnets_addr_from_start_true": "true",
     "svc_vn_left_prefix": "%s" % get_random_cidr().split('/')[0],
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_3": 24,
     "service_template_properties_interface_type_service_interface_type_3":
     "right",
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_1": 24,
     "service_template_properties_interface_type_service_interface_type_1":
     "management",
     "image": "cirros-0.3.0-x86_64-uec",
     "src_port_end": -1,
     "service_instance2_fq_name": "",
     "service_template2_properties_image_name": "vsrx",
     "service_template2_name": "pt_template2",
     "left_vn_fqdn": "",
     "service_template_properties_interface_type_service_interface_type_2":
     "left",
     "right_vn": "right_vn",
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_2": 24,
     "svc_vn_mgmt": "svc_vn_mgmt",
     "left_vm_name": "left_vm",
     "policy_name": "pt_policy",
     "dst_port_start": -1,
     "left_vn": "left_vn",
     "management_network": "management_vn",
     "service_instance1_fq_name": "",
     "right_vm_name": "right_vm",
     "service_template_properties_flavor": "m1.medium",
     "svc_vn_right_prefix": "%s" % get_random_cidr().split('/')[0],
     "service_instance2_name": "pt_instance2",
     "svc_vn_left": "svc_vn_left",
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_1":
     "%s" % get_random_cidr().split('/')[0],
     "direction": "<>",
     "svm1_name": "pt_svm1"}
}

left_net = {
  u'parameters': {
    u'name': u'vn-left',
    u'ipam': u'default-domain:default-project:default-network-ipam',
    u'subnet': u'10.10.10.0', u'prefix': 24,
    u'transit': u'False'
  }
}

right_net = {
  u'parameters': {
    u'name': u'vn-right',
    u'ipam': u'default-domain:default-project:default-network-ipam',
    u'subnet': u'20.20.20.0', u'prefix': 24,
    u'transit': u'False'
  }
}

transit_net = {
  u'parameters': {
    u'name': u'transit-vn',
    u'ipam': u'default-domain:default-project:default-network-ipam',
    u'subnet': u'30.30.30.0', u'prefix': 24,
    u'transit': u'True'
  }
}

vms = {
  u'parameters': {
    u'right_vm_name': u'right-vm', u'right_net_id': u'',
    u'left_vm_name': u'left-vm', u'left_net_id': u'',
    u'image': u'ubuntu-traffic', u'flavor': u'm1.medium'
  }
}

svc_tmpl = {
  u'parameters': {
    u'name': u'st1',
    u'service_interface_type_list': u'management,left,right',
    u'image': u'vsrx',
    u'static_routes_list': u'False,False,False',
    u'mode': u'in-network-nat',
    u'flavor': u'm1.medium',
    u'service_scaling': 'False',
    u'type': u'firewall',
    u'shared_ip_list': u'False,False,False'
  }
}

svc_tmpl_nomgmt = {
  u'parameters': {
    u'name': u'st1',
    u'service_interface_type_list': u'left,right',
    u'image': u'ubuntu-in-net',
    u'static_routes_list': u'False,False',
    u'mode': u'in-network',
    u'flavor': u'm1.medium',
    u'service_scaling': 'False',
    u'type': u'firewall',
    u'shared_ip_list': u'False,False'
  }
}

svc_tmpl_v2 = {
  u'parameters': {
    u'name': u'',
    u'image': u'vsrx', u'flavor': u'm1.medium',
    u'mode': u'in-network-nat', u'type': u'firewall',
    u'service_scaling': u'False',
    u'left_shared': u'False', u'left_static': u'False',
    u'right_static': u'False', u'right_shared': u'False'
  }
}

svc_tmpl_nomgmt_v2 = {
  u'parameters': {
    u'name': u'',
    u'image': u'ubuntu-in-net', u'flavor': u'm1.medium',
    u'mode': u'in-network', u'type': u'firewall',
    u'service_scaling': u'False',
    u'left_shared': u'False', u'left_static': u'False',
    u'right_static': u'False', u'right_shared': u'False'
  }
}

svc_tmpl_pt_v2 = {
  u'parameters': {
    u'name': u'',
    u'mode': u'in-network-nat', u'type': u'firewall',
  }
}

svc_tmpl_nomgmt_pt_v2 = svc_tmpl_pt_v2

svc_inst = {
  u'parameters': {
    u'service_template_fq_name': u'default-domain:st1',
    u'left_net_id': u'3f162ab2-85ff-4ad0-8161-9ae4633e7359',
    u'service_instance_name': u'si1',
    u'max_instances': u'1',
    u'right_net_id': u'e6f9e85b-5816-4818-bea6-089262c63f5d'
  }
}

svc_inst_nomgmt = svc_inst

svc_inst_v2 = {
  u'parameters': {
    u'service_template_fq_name': u'', u'service_instance_name': u'',
    u'max_instances': 1, u'ha': u'active-active',
    u'left_net_id': u'', u'right_net_id': u''
  }
}

svc_inst_dual_v2 = svc_inst_v2

svc_inst_nomgmt_v2 = svc_inst_v2

svc_inst_nomgmt_dual_v2 = svc_inst_v2

svc_inst_nomgmt_pt_v2 = {
  u'parameters': {
    u'image': u'ubuntu-in-net', u'flavor': u'm1.medium', u'svm_name': 'svm',
    u'service_template_fq_name': u'', u'service_instance_name': u'',
    u'left_net_id': u'', u'right_net_id': u''
  }
}

svc_inst_nomgmt_pt_dual_v2 = svc_inst_nomgmt_pt_v2

svc_chain = {
  u'parameters': {
    u'policy_name': u'',
    u'src_vn_id': u'',
    u'dst_vn_id': u'',
  }
}

svc_chain_v2 = {
  u'parameters': {
    u'policy_name': u'',
  }
}
