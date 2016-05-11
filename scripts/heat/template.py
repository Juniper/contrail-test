vn = {
  u'description': u'HOT template to create network\n',
  u'heat_template_version': u'2013-05-23',
  u'outputs': {
    u'net_id': {
      u'description' : u'ID of the network',
      u'value': {u'get_attr': [u'network', u'fq_name'] }
    }
  },
  u'parameters': {
    u'name': {
      u'description': 'Name of the network',
      u'type': u'string'},
    u'ipam': {
      u'description': 'IPAM Name or ID',
      u'type': u'string'},
    u'subnet': {
      u'description': 'Subnet for VN',
      u'type': u'string'},
    u'prefix': {
      u'description': 'Subnet prefix length',
      u'type': u'number'},
    u'transit': {
      u'description': 'Allow transit',
      u'type': u'boolean'}
  },
  u'resources': {
    u'network': {
      u'type': u'OS::ContrailV2::VirtualNetwork',
      u'properties':{
        u'name': {u'get_param': u'name'},
        u'virtual_network_properties': {
          u'virtual_network_properties_allow_transit' : {u'get_param': u'transit'}
        },
        u'network_ipam_refs': [{u'get_param': u'ipam'}],
        u'network_ipam_refs_data': [{
          u'network_ipam_refs_data_ipam_subnets':
            [{u'network_ipam_refs_data_ipam_subnets_subnet': {
                u'network_ipam_refs_data_ipam_subnets_subnet_ip_prefix': {u'get_param': u'subnet'},
                u'network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len': {u'get_param': u'prefix'}
              },
              u'network_ipam_refs_data_ipam_subnets_addr_from_start' : u'True'
            }]
        }]
      }
    }
  }
}

vn_dual = {
  u'description': u'HOT template to create network\n',
  u'heat_template_version': u'2013-05-23',
  u'outputs': {
    u'net_id': {
      u'description' : u'ID of the network',
      u'value': {u'get_attr': [u'network',  u'fq_name']}
    }
  },
  u'parameters': {
    u'name': {
      u'description': 'Name of the network',
      u'type': u'string'},
    u'ipam': {
      u'description': 'IPAM Name or ID',
      u'type': u'string'},
    u'subnet': {
      u'description': 'Subnet for VN',
      u'type': u'string'},
    u'prefix': {
      u'description': 'Subnet prefix length',
      u'type': u'number'},
    u'subnet2': {
      u'description': 'Subnet for VN',
      u'type': u'string'},
    u'prefix2': {
      u'description': 'Subnet prefix length',
      u'type': u'number'},
    u'transit': {
      u'description': 'Allow transit',
      u'type': u'boolean'}
  },
  u'resources': {
    u'network': {
      u'type': u'OS::ContrailV2::VirtualNetwork',
      u'properties':{
        u'name': {u'get_param': u'name'},
        u'virtual_network_properties': {
          u'virtual_network_properties_allow_transit' : {u'get_param': u'transit'}
        },
        u'network_ipam_refs': [{u'get_param': u'ipam'}],
        u'network_ipam_refs_data': [{
          u'network_ipam_refs_data_ipam_subnets':
            [{u'network_ipam_refs_data_ipam_subnets_subnet': {
                u'network_ipam_refs_data_ipam_subnets_subnet_ip_prefix': {u'get_param': u'subnet'},
                u'network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len': {u'get_param': u'prefix'}
              },
              u'network_ipam_refs_data_ipam_subnets_addr_from_start' : u'True'
             },
             {u'network_ipam_refs_data_ipam_subnets_subnet': {
                u'network_ipam_refs_data_ipam_subnets_subnet_ip_prefix': {u'get_param': u'subnet2'},
                u'network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len': {u'get_param': u'prefix2'}
              },
              u'network_ipam_refs_data_ipam_subnets_addr_from_start' : u'True'
             }
            ]
        }]
      }
    }
  }
}

vms = {
  u'description': u'HOT template to deploy server into an existing neutron tenant network\n',
  u'heat_template_version': u'2013-05-23',
  u'outputs': {
    u'server1_ip': {
      u'description': u'IP address of the left_vm',
      u'value': {u'get_attr': [u'server1', u'first_address']}},
    u'server2_ip': {
      u'description': u'IP address of the right_vm',
      u'value': {u'get_attr': [u'server2', u'first_address']}}
  },
  u'parameters': {
    u'flavor': {
      u'description': u'Flavor to use for servers',
      u'type': u'string'},
    u'image': {
      u'description': u'Name of image to use for servers',
      u'type': u'string'},
    u'left_vm_name': {
      u'description': u'Name of left server',
      u'type': u'string'},
    u'left_net_id': {
      u'description': u'ID of the left network',
      u'type': u'string'},
    u'right_vm_name': {
      u'description': u'Name of right server',
      u'type': u'string'},
    u'right_net_id': {
      u'description': u'ID of the right network',
      u'type': u'string'}
  },
  u'resources': {
    u'server1': {
      u'properties': {
        u'flavor': {u'get_param': u'flavor'},
        u'image': {u'get_param': u'image'},
        u'name': {u'get_param': u'left_vm_name'},
        u'networks': [{u'port': {u'get_resource': u'server1_port'}}]
      },
      u'type': u'OS::Nova::Server'
    },
    u'server1_port': {
      u'properties': {u'network_id': {u'get_param': u'left_net_id'}},
      u'type': u'OS::Neutron::Port'
    },
    u'server2': {
      u'properties': {
        u'flavor': {u'get_param': u'flavor'},
        u'image': {u'get_param': u'image'},
        u'name': {u'get_param': u'right_vm_name'},
        u'networks': [{u'port': {u'get_resource': u'server2_port'}}]
      },
      u'type': u'OS::Nova::Server'
   },
   u'server2_port': {
     u'properties': {u'network_id': {u'get_param': u'right_net_id'}},
     u'type': u'OS::Neutron::Port'
   }
 }
}

svc_rule = {
  u'network_policy_entries_policy_rule_direction': '',
  u'network_policy_entries_policy_rule_protocol': '',
  u'network_policy_entries_policy_rule_src_addresses':[
    {u'network_policy_entries_policy_rule_src_addresses_virtual_network': ''}
  ],
  u'network_policy_entries_policy_rule_dst_addresses':[
    {u'network_policy_entries_policy_rule_dst_addresses_virtual_network': ''}
  ],
  u'network_policy_entries_policy_rule_src_ports' : [
    {u'network_policy_entries_policy_rule_src_ports_start_port' : -1,
     u'network_policy_entries_policy_rule_src_ports_end_port' : -1}
  ],
  u'network_policy_entries_policy_rule_dst_ports' : [
    {u'network_policy_entries_policy_rule_dst_ports_start_port' : -1,
     u'network_policy_entries_policy_rule_dst_ports_end_port' : -1}
  ],
  u'network_policy_entries_policy_rule_action_list' : {
    u'network_policy_entries_policy_rule_action_list_simple_action' : 'pass',
    u'network_policy_entries_policy_rule_action_list_apply_service': ''
  }
}

svc_chain = {
  u'description': u'HOT template to create a policy between two virtual network and apply a service.',
  u'heat_template_version': u'2013-05-23',
  u'outputs': {
    u'policy_fqname': {
      u'description': u'FQN of the network policy',
      u'value': {u'get_attr': [u'policy', u'fq_name']}
    }
  },
  u'parameters': {
    u'policy_name': {
      u'description': u'Policy Name',
      u'type': u'string'},
  },
  u'resources': {
    u'policy': {
      u'type': u'OS::ContrailV2::NetworkPolicy',
      u'properties': {
        u'name': {u'get_param': u'policy_name'},
        u'network_policy_entries': {
          u'network_policy_entries_policy_rule': []
        }
      }
    }
  }
}

svc_tmpl_v2 = {
  u'description': u'HOT template to create a service template \n',
  u'heat_template_version': u'2013-05-23',
  u'outputs': {
    u'service_template_fq_name': {
      u'description': u'FQ name of the service template',
      u'value': {u'get_attr': [u'service_template', u'fq_name']}}
  },
  u'parameters': {
    u'flavor': {
      u'description': u'Flavor',
      u'type': u'string'},
    u'service_scaling': {
      u'description': u'Flag to enable scaling',
      u'type': u'string'},
    u'image': {
      u'description': u'Name of the image',
      u'type': u'string'},
    u'mode': {
      u'description': u'service mode',
      u'type': u'string'},
    u'name': {
      u'description': u'Name of service template',
      u'type': u'string'},
    u'type': {
      u'description': u'service type',
      u'type': u'string'},
    u'left_shared': {
      u'description': u'Shared IP enabled for left vn',
      u'type': u'string'},
    u'right_shared': {
      u'description': u'Shared IP enabled for right vn',
      u'type': u'string'},
    u'left_static': {
      u'description': u'Static IP enabled for left vn',
      u'type': u'string'},
    u'right_static': {
      u'description': u'Static IP enabled for right vn',
      u'type': u'string'}
  },
  u'resources': {
    u'service_template': {
      u'properties': {
        u'name': {u'get_param': u'name'},
        u'domain': u'default-domain',
        u'service_template_properties': {
          u'service_template_properties_version': u'1',
          u'service_template_properties_image_name': {u'get_param': u'image'},
          u'service_template_properties_service_scaling': {u'get_param': u'service_scaling'},
          u'service_template_properties_service_mode': {u'get_param': u'mode'},
          u'service_template_properties_service_type': {u'get_param': u'type'},
          u'service_template_properties_flavor': {u'get_param': u'flavor'},
          u'service_template_properties_interface_type':[
            {u'service_template_properties_interface_type_service_interface_type': u'management',
             u'service_template_properties_interface_type_shared_ip': u'False',
             u'service_template_properties_interface_type_static_route_enable': u'False'},
            {u'service_template_properties_interface_type_service_interface_type': u'left',
             u'service_template_properties_interface_type_shared_ip': {u'get_param': u'left_shared'},
             u'service_template_properties_interface_type_static_route_enable': {u'get_param': u'left_static'}},
            {u'service_template_properties_interface_type_service_interface_type': u'right',
             u'service_template_properties_interface_type_shared_ip': {u'get_param': u'right_shared'},
             u'service_template_properties_interface_type_static_route_enable': {u'get_param': u'right_static'}}
          ]
        }
     },
     u'type': u'OS::ContrailV2::ServiceTemplate'
   }
 }
}

svc_tmpl_pt_v2 = {
  u'description': u'HOT template to create a service template \n',
  u'heat_template_version': u'2013-05-23',
  u'outputs': {
    u'service_template_fq_name': {
      u'description': u'FQ name of the service template',
      u'value': {u'get_attr': [u'service_template', u'fq_name']}}
  },
  u'parameters': {
    u'mode': {
      u'description': u'service mode',
      u'type': u'string'},
    u'name': {
      u'description': u'Name of service template',
      u'type': u'string'},
    u'type': {
      u'description': u'service type',
      u'type': u'string'},
  },
  u'resources': {
    u'service_template': {
      u'properties': {
        u'name': {u'get_param': u'name'},
        u'domain': u'default-domain',
        u'service_template_properties': {
          u'service_template_properties_version': u'2',
          u'service_template_properties_service_mode': {u'get_param': u'mode'},
          u'service_template_properties_service_type': {u'get_param': u'type'},
          u'service_template_properties_interface_type':[
            {u'service_template_properties_interface_type_service_interface_type': u'management'},
            {u'service_template_properties_interface_type_service_interface_type': u'left'},
            {u'service_template_properties_interface_type_service_interface_type': u'right'},
          ]
        }
     },
     u'type': u'OS::ContrailV2::ServiceTemplate'
   }
 }
}

svc_tmpl_nomgmt_v2 = {
  u'description': u'HOT template to create a service template \n',
  u'heat_template_version': u'2013-05-23',
  u'outputs': {
    u'service_template_fq_name': {
      u'description': u'FQ name of the service template',
      u'value': {u'get_attr': [u'service_template', u'fq_name']}}
  },
  u'parameters': {
    u'flavor': {
      u'description': u'Flavor',
      u'type': u'string'},
    u'service_scaling': {
      u'description': u'Flag to enable scaling',
      u'type': u'string'},
    u'image': {
      u'description': u'Name of the image',
      u'type': u'string'},
    u'mode': {
      u'description': u'service mode',
      u'type': u'string'},
    u'name': {
      u'description': u'Name of service template',
      u'type': u'string'},
    u'type': {
      u'description': u'service type',
      u'type': u'string'},
    u'left_shared': {
      u'description': u'Shared IP enabled for left vn',
      u'type': u'string'},
    u'right_shared': {
      u'description': u'Shared IP enabled for right vn',
      u'type': u'string'},
    u'left_static': {
      u'description': u'Static IP enabled for left vn',
      u'type': u'string'},
    u'right_static': {
      u'description': u'Static IP enabled for right vn',
      u'type': u'string'}
  },
  u'resources': {
    u'service_template': {
      u'properties': {
        u'name': {u'get_param': u'name'},
        u'domain': u'default-domain',
        u'service_template_properties': {
          u'service_template_properties_version': u'1',
          u'service_template_properties_image_name': {u'get_param': u'image'},
          u'service_template_properties_service_scaling': {u'get_param': u'service_scaling'},
          u'service_template_properties_service_mode': {u'get_param': u'mode'},
          u'service_template_properties_service_type': {u'get_param': u'type'},
          u'service_template_properties_flavor': {u'get_param': u'flavor'},
          u'service_template_properties_interface_type':[
            {u'service_template_properties_interface_type_service_interface_type': u'left',
             u'service_template_properties_interface_type_shared_ip': {u'get_param': u'left_shared'},
             u'service_template_properties_interface_type_static_route_enable': {u'get_param': u'left_static'}},
            {u'service_template_properties_interface_type_service_interface_type': u'right',
             u'service_template_properties_interface_type_shared_ip': {u'get_param': u'right_shared'},
             u'service_template_properties_interface_type_static_route_enable': {u'get_param': u'right_static'}}
          ]
        }
     },
     u'type': u'OS::ContrailV2::ServiceTemplate'
   }
 }
}

svc_tmpl_nomgmt_pt_v2 = {
  u'description': u'HOT template to create a service template \n',
  u'heat_template_version': u'2013-05-23',
  u'outputs': {
    u'service_template_fq_name': {
      u'description': u'FQ name of the service template',
      u'value': {u'get_attr': [u'service_template', u'fq_name']}}
  },
  u'parameters': {
    u'mode': {
      u'description': u'service mode',
      u'type': u'string'},
    u'name': {
      u'description': u'Name of service template',
      u'type': u'string'},
    u'type': {
      u'description': u'service type',
      u'type': u'string'},
  },
  u'resources': {
    u'service_template': {
      u'properties': {
        u'name': {u'get_param': u'name'},
        u'domain': u'default-domain',
        u'service_template_properties': {
          u'service_template_properties_version': u'2',
          u'service_template_properties_service_mode': {u'get_param': u'mode'},
          u'service_template_properties_service_type': {u'get_param': u'type'},
          u'service_template_properties_interface_type':[
            {u'service_template_properties_interface_type_service_interface_type': u'left'},
            {u'service_template_properties_interface_type_service_interface_type': u'right'},
          ]
        }
     },
     u'type': u'OS::ContrailV2::ServiceTemplate'
   }
 }
}

svc_inst_v2 = {
  u'description': u'HOT template to create service instance.\n',
  u'heat_template_version': u'2013-05-23',
  u'outputs': {
    u'service_instance_fq_name': {
      u'description': u'FQ name of the service template',
      u'value': {u'get_attr': [u'service_instance', u'fq_name']}
    },
  },
  u'parameters': {
    u'left_net_id': {
      u'description': u'ID of the left network',
      u'type': u'string'},
    u'right_net_id': {
      u'description': u'ID of the right network',
      u'type': u'string'},
    u'service_instance_name': {
      u'description': u'service instance name',
      u'type': u'string'},
    u'max_instances': {
      u'description': u'Number of service VMs',
      u'type': u'number'},
    u'ha': {
      u'description': u'High-availability mode',
      u'type': u'string'},
    u'service_template_fq_name': {
      u'description': u'service template name or ID',
      u'type': u'string'}
  },
  u'resources': {
    u'service_instance': {
      u'properties': {
        u'name': {u'get_param': u'service_instance_name'},
        u'service_instance_properties': {
          u'service_instance_properties_scale_out': {
            u'service_instance_properties_scale_out_max_instances': {u'get_param': u'max_instances'}},
          u'service_instance_properties_ha_mode': {u'get_param': u'ha'},
          u'service_instance_properties_management_virtual_network': u'',
          u'service_instance_properties_left_virtual_network': {u'get_param': u'left_net_id'},
          u'service_instance_properties_right_virtual_network': {u'get_param': u'right_net_id'}
        },
        u'service_template_refs': [{u'get_param': u'service_template_fq_name'}]
      },
      u'type': u'OS::ContrailV2::ServiceInstance'
    }
  }
}

svc_inst_dual_v2 = svc_inst_v2

svc_inst_nomgmt_v2 = {
  u'description': u'HOT template to create service instance.\n',
  u'heat_template_version': u'2013-05-23',
  u'outputs': {
    u'service_instance_fq_name': {
      u'description': u'FQ name of the service template',
      u'value': {u'get_attr': [u'service_instance', u'fq_name']}
    },
  },
  u'parameters': {
    u'left_net_id': {
      u'description': u'ID of the left network',
      u'type': u'string'},
    u'right_net_id': {
      u'description': u'ID of the right network',
      u'type': u'string'},
    u'service_instance_name': {
      u'description': u'service instance name',
      u'type': u'string'},
    u'max_instances': {
      u'description': u'Number of service VMs',
      u'type': u'string'},
    u'ha': {
      u'description': u'High-availability mode',
      u'type': u'string'},
    u'service_template_fq_name': {
      u'description': u'service template name or ID',
      u'type': u'string'}
  },
  u'resources': {
    u'service_instance': {
      u'properties': {
        u'name': {u'get_param': u'service_instance_name'},
        u'service_instance_properties': {
          u'service_instance_properties_scale_out': {
            u'service_instance_properties_scale_out_max_instances': {u'get_param': u'max_instances'}},
          u'service_instance_properties_ha_mode': {u'get_param': u'ha'},
          u'service_instance_properties_left_virtual_network': {u'get_param': u'left_net_id'},
          u'service_instance_properties_right_virtual_network': {u'get_param': u'right_net_id'}
        },
        u'service_template_refs': [{u'get_param': u'service_template_fq_name'}]
      },
      u'type': u'OS::ContrailV2::ServiceInstance'
    }
  }
}

svc_inst_nomgmt_dual_v2 = svc_inst_nomgmt_v2

svc_inst_nomgmt_pt_v2 = {
  u'description': u'HOT template to create service instance.\n',
  u'heat_template_version': u'2013-05-23',
  u'outputs': {
    u'service_instance_fq_name': {
      u'description': u'FQ name of the service template',
      u'value': {u'get_attr': [u'service_instance', u'fq_name']}
    },
  },
  u'parameters': {
    u'flavor': {
      u'description': u'Flavor',
      u'type': u'string'},
    u'image': {
      u'description': u'Name of image to use for servers',
      u'type': u'string'},
    u'left_net_id': {
      u'description': u'ID of the left network',
      u'type': u'string'},
    u'right_net_id': {
      u'description': u'ID of the right network',
      u'type': u'string'},
    u'svm_name': {
      u'description': u'service instance name',
      u'type': u'string'},
    u'service_instance_name': {
      u'description': u'service instance name',
      u'type': u'string'},
    u'service_template_fq_name': {
      u'description': u'service template name or ID',
      u'type': u'string'}
  },
  u'resources': {
    u'pt': {
      u'type': u'OS::ContrailV2::PortTuple',
      u'depends_on': [ u'service_instance' ],
      u'properties': {
        u'name': { u'get_attr': [ u'random_key_1', u'value' ] },
        u'service_instance': { u'list_join': [':', { u'get_attr': [ u'service_instance', u'fq_name' ] } ] }
      },
    },
    u'svm_left_vmi': {
      u'type': u'OS::ContrailV2::VirtualMachineInterface',
      u'depends_on': [ 'pt' ],
      u'properties': {
        u'name': { u'get_attr': [ u'random_key_2', u'value' ] },
        u'virtual_network_refs': [{ u'get_param': u'left_net_id' }],
        u'port_tuple_refs': [{ u'get_resource': u'pt' }],
        u'virtual_machine_interface_properties': {
          u'virtual_machine_interface_properties_service_interface_type': u'left',
        }
      }
    },
    u'svm_right_vmi': {
      u'type': u'OS::ContrailV2::VirtualMachineInterface',
      u'depends_on': [ u'pt' ],
      u'properties': {
        u'name': { u'get_attr': [ u'random_key_3', u'value' ] },
        u'virtual_network_refs': [{ u'get_param': u'right_net_id' }],
        u'port_tuple_refs': [{ u'get_resource': u'pt' }],
        u'virtual_machine_interface_properties': {
          u'virtual_machine_interface_properties_service_interface_type': u'right',
        },
      }
    },
    u'svm_left_ip1': {
      u'type': u'OS::ContrailV2::InstanceIp',
      u'depends_on': [ 'svm_left_vmi' ],
      u'properties': {
        u'name': { u'get_attr': [ u'random_key_4', u'value' ] },
        u'virtual_machine_interface_refs': [{ u'get_resource': u'svm_left_vmi' }],
        u'virtual_network_refs': [{ u'get_param': u'left_net_id' }],
        u'instance_ip_family': 'v4',
        u'service_instance_ip' : True,
      }
    },
    u'svm_right_ip1': {
      u'type': u'OS::ContrailV2::InstanceIp',
      u'depends_on': [ 'svm_right_vmi' ],
      u'properties': {
        u'name': { u'get_attr': [ u'random_key_5', u'value' ] },
        u'virtual_machine_interface_refs': [{ u'get_resource': u'svm_right_vmi' }],
        u'virtual_network_refs': [{ u'get_param': u'right_net_id' }],
        u'instance_ip_family' : 'v4',
        u'service_instance_ip' : True,
      }
    },
    u'svm': {
      u'type': u'OS::Nova::Server',
      u'depends_on': [ u'svm_left_ip1', u'svm_right_ip1'],
      u'properties': {
        u'name': { u'get_param': u'svm_name' },
        u'image': { u'get_param':  u'image' },
        u'flavor': { u'get_param': u'flavor' },
        u'networks':
          [{ u'port': { u'get_resource': u'svm_left_vmi' }},
           { u'port': { u'get_resource': u'svm_right_vmi' }},]
      }
    },
    u'service_instance': {
      u'properties': {
        u'name': {u'get_param': u'service_instance_name'},
        u'service_instance_properties': {
          u'service_instance_properties_left_virtual_network': {u'get_param': u'left_net_id'},
          u'service_instance_properties_right_virtual_network': {u'get_param': u'right_net_id'}
        },
        u'service_template_refs': [{u'get_param': u'service_template_fq_name'}]
      },
      u'type': u'OS::ContrailV2::ServiceInstance'
    },
    u'random_key_1': {
      u'type': u'OS::Heat::RandomString',
      u'properties': {
        u'length': 16,
      }
    },
    u'random_key_2': {
      u'type': u'OS::Heat::RandomString',
      u'properties': {
        u'length': 16,
      }
    },
    u'random_key_3': {
      u'type': u'OS::Heat::RandomString',
      u'properties': {
        u'length': 16,
      }
    },
    u'random_key_4': {
      u'type': u'OS::Heat::RandomString',
      u'properties': {
        u'length': 16,
      }
    },
    u'random_key_5': {
      u'type': u'OS::Heat::RandomString',
      u'properties': {
        u'length': 16,
      }
    },
    u'random_key_6': {
      u'type': u'OS::Heat::RandomString',
      u'properties': {
        u'length': 16,
      }
    },
    u'random_key_7': {
      u'type': u'OS::Heat::RandomString',
      u'properties': {
        u'length': 16,
      }
    },
  }
}

svc_inst_nomgmt_pt_dual_v2 = {
  u'description': u'HOT template to create service instance.\n',
  u'heat_template_version': u'2013-05-23',
  u'outputs': {
    u'service_instance_fq_name': {
      u'description': u'FQ name of the service template',
      u'value': {u'get_attr': [u'service_instance', u'fq_name']}
    },
    u'svm_id': {
      u'description': u'FQ name of the service template',
      u'value': {u'get_attr': [u'svm', u'show', u'id']}
    },
  },
  u'parameters': {
    u'flavor': {
      u'description': u'Flavor',
      u'type': u'string'},
    u'image': {
      u'description': u'Name of image to use for servers',
      u'type': u'string'},
    u'left_net_id': {
      u'description': u'ID of the left network',
      u'type': u'string'},
    u'right_net_id': {
      u'description': u'ID of the right network',
      u'type': u'string'},
    u'svm_name': {
      u'description': u'service instance name',
      u'type': u'string'},
    u'service_instance_name': {
      u'description': u'service instance name',
      u'type': u'string'},
    u'service_template_fq_name': {
      u'description': u'service template name or ID',
      u'type': u'string'}
  },
  u'resources': {
    u'pt': {
      u'type': u'OS::ContrailV2::PortTuple',
      u'depends_on': [ u'service_instance' ],
      u'properties': {
        u'name': { u'get_attr': [ u'random_key_1', u'value' ] },
        u'service_instance': { u'list_join': [':', { u'get_attr': [ u'service_instance', u'fq_name' ] } ] }
      },
    },
    u'svm_left_vmi': {
      u'type': u'OS::ContrailV2::VirtualMachineInterface',
      u'depends_on': [ 'pt' ],
      u'properties': {
        u'name': { u'get_attr': [ u'random_key_2', u'value' ] },
        u'virtual_network_refs': [{ u'get_param': u'left_net_id' }],
        u'port_tuple_refs': [{ u'get_resource': u'pt' }],
        u'virtual_machine_interface_properties': {
          u'virtual_machine_interface_properties_service_interface_type': u'left',
        }
      }
    },
    u'svm_right_vmi': {
      u'type': u'OS::ContrailV2::VirtualMachineInterface',
      u'depends_on': [ u'pt' ],
      u'properties': {
        u'name': { u'get_attr': [ u'random_key_3', u'value' ] },
        u'virtual_network_refs': [{ u'get_param': u'right_net_id' }],
        u'port_tuple_refs': [{ u'get_resource': u'pt' }],
        u'virtual_machine_interface_properties': {
          u'virtual_machine_interface_properties_service_interface_type': u'right',
        },
      }
    },
    u'svm_left_ip1': {
      u'type': u'OS::ContrailV2::InstanceIp',
      u'depends_on': [ 'svm_left_vmi' ],
      u'properties': {
        u'name': { u'get_attr': [ u'random_key_4', u'value' ] },
        u'virtual_machine_interface_refs': [{ u'get_resource': u'svm_left_vmi' }],
        u'virtual_network_refs': [{ u'get_param': u'left_net_id' }],
        u'instance_ip_family': 'v6',
        u'service_instance_ip' : True,
      }
    },
    u'svm_right_ip1': {
      u'type': u'OS::ContrailV2::InstanceIp',
      u'depends_on': [ 'svm_right_vmi' ],
      u'properties': {
        u'name': { u'get_attr': [ u'random_key_5', u'value' ] },
        u'virtual_machine_interface_refs': [{ u'get_resource': u'svm_right_vmi' }],
        u'virtual_network_refs': [{ u'get_param': u'right_net_id' }],
        u'instance_ip_family' : 'v6',
        u'service_instance_ip' : True,
      }
    },
    u'svm_left_ip2': {
      u'type': u'OS::ContrailV2::InstanceIp',
      u'depends_on': [ 'svm_left_vmi' ],
      u'properties': {
        u'name': { u'get_attr': [ u'random_key_6', u'value' ] },
        u'virtual_machine_interface_refs': [{ u'get_resource': u'svm_left_vmi' }],
        u'virtual_network_refs': [{ u'get_param': u'left_net_id' }],
        u'instance_ip_family': 'v4',
        u'service_instance_ip' : True,
      }
    },
    u'svm_right_ip2': {
      u'type': u'OS::ContrailV2::InstanceIp',
      u'depends_on': [ 'svm_right_vmi' ],
      u'properties': {
        u'name': { u'get_attr': [ u'random_key_7', u'value' ] },
        u'virtual_machine_interface_refs': [{ u'get_resource': u'svm_right_vmi' }],
        u'virtual_network_refs': [{ u'get_param': u'right_net_id' }],
        u'instance_ip_family' : 'v4',
        u'service_instance_ip' : True,
      }
    },
    u'svm': {
      u'type': u'OS::Nova::Server',
      u'depends_on': [ u'svm_left_ip1', u'svm_right_ip1', u'svm_left_ip2', u'svm_right_ip2' ],
      u'properties': {
        u'name': { u'get_param': u'svm_name' },
        u'image': { u'get_param':  u'image' },
        u'flavor': { u'get_param': u'flavor' },
        u'networks':
          [{ u'port': { u'get_resource': u'svm_left_vmi' }},
           { u'port': { u'get_resource': u'svm_right_vmi' }},]
      }
    },
    u'service_instance': {
      u'properties': {
        u'name': {u'get_param': u'service_instance_name'},
        u'service_instance_properties': {
          u'service_instance_properties_left_virtual_network': {u'get_param': u'left_net_id'},
          u'service_instance_properties_right_virtual_network': {u'get_param': u'right_net_id'}
        },
        u'service_template_refs': [{u'get_param': u'service_template_fq_name'}]
      },
      u'type': u'OS::ContrailV2::ServiceInstance'
    },
    u'random_key_1': {
      u'type': u'OS::Heat::RandomString',
      u'properties': {
        u'length': 16,
      }
    },
    u'random_key_2': {
      u'type': u'OS::Heat::RandomString',
      u'properties': {
        u'length': 16,
      }
    },
    u'random_key_3': {
      u'type': u'OS::Heat::RandomString',
      u'properties': {
        u'length': 16,
      }
    },
    u'random_key_4': {
      u'type': u'OS::Heat::RandomString',
      u'properties': {
        u'length': 16,
      }
    },
    u'random_key_5': {
      u'type': u'OS::Heat::RandomString',
      u'properties': {
        u'length': 16,
      }
    },
    u'random_key_6': {
      u'type': u'OS::Heat::RandomString',
      u'properties': {
        u'length': 16,
      }
    },
    u'random_key_7': {
      u'type': u'OS::Heat::RandomString',
      u'properties': {
        u'length': 16,
      }
    },
  }
}
