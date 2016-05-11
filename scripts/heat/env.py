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
  }
}
