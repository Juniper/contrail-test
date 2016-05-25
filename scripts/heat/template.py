ecmp_pt = {
    "outputs":
    {"left_vn_FQDN": {"description": "FQDN of the left VN",
                      "value":
                      {"get_attr": ["template_VirtualNetwork_2", "fq_name"]}},
     "left_VM_ID": {"description": "ID of the left VM",
                    "value": {"get_attr": ["template_leftVM", "show", "id"]}},
     "right_vn_FQDN": {"description": "FQDN of the right VN",
                       "value":
                       {"get_attr": ["template_VirtualNetwork_3", "fq_name"]}},
     "right_VM_ID": {"description": "ID of the right VM",
                     "value":
                     {"get_attr": ["template_rightVM", "show", "id"]}},
     "si_fqdn": {"description": "FQDN of the SI",
                 "value":
                 {"get_attr": ["template_ServiceInstance", "fq_name"]}}},
    "heat_template_version": "2015-04-30",
    "parameters":
    {"domain": {"type": "string",
                "description": "Name of the Domain"},
     "dst_port_end": {"type": "number",
                      "description": "End of the Destination Port Range"},
     "protocol": {"type": "string",
                  "description": "Protocol"},
     "service_template_properties_version":
     {"type": "string",
      "description": "Indicates service version"},
     "svm2_name": {"type": "string",
                   "description": "Name of SVM2"},
     "image": {"type": "string",
               "description": "Name of the end VM image"},
     "direction": {"type": "string",
                   "description": "Direction of the Policy"},
     "service_template_properties_ordered_interfaces":
     {"type": "string",
      "description": "Indicates service interfaces are ordered"},
     "service_template_properties_service_mode":
     {"type": "string",
      "description": "service mode"},
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_3":
     {"type": "string",
      "description": "subnet prefix for right network"},
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_2":
     {"type": "string",
      "description": "subnet prefix for left network"},
     "simple_action": {"type": "string",
                       "description": "Pass or Deny"},
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_1":
     {"type": "string",
      "description": "subnet prefix for mgmt network"},
     "flavor": {"type": "string",
                "description": "Flavor of the end VMs"},
     "src_port_start": {"type": "number",
                        "description": "Start of the Source Port Range"},
     "right_vn_fqdn": {"type": "string",
                       "description": "FQ Name of the right network"},
     "service_template_properties_service_type": {"type": "string",
                                                  "description": "service type"
                                                  },
     "service_template_name": {"type": "string",
                               "description":
                               "Service template for port tuple",
                               "label": "Service template fq name"},
     "network_ipam_refs_data_ipam_subnets_addr_from_start_true":
     {"type": "boolean",
      "description": "Address allocation from start of the pool"},
     "service_template_properties_image_name": {"type": "string",
                                                "description":
                                                "Name of the image"},
     "service_template_properties_interface_type_service_interface_type_2": {
         "type": "string",
         "description": "service_interface_type for the ServiceTemplate"
     },
     "service_template_properties_interface_type_service_interface_type_3": {
         "type": "string",
         "description": "service_interface_type for the ServiceTemplate"
     },
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_1":
     {"type": "string",
      "description": "subnet prefix len for mgmt network"},
     "service_template_properties_interface_type_service_interface_type_1": {
         "type": "string",
         "description": "service_interface_type for the ServiceTemplate"
     },
     "src_port_end": {"type": "number",
                      "description": "End of the Source Port Range"},
     "dst_port_start": {"type": "number",
                        "description": "Start of the Destination Port Range"},
     "service_template_properties_flavor": {"type": "string",
                                            "description": "Flavor"},
     "left_vn_fqdn": {"type": "string",
                      "description": "FQ Name of the left network"},
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_3": {
         "type": "string",
         "description": "subnet prefix len for right network"
     },
     "service_instance_name": {"type": "string",
                               "description":
                               "Service instance for port tuple",
                               "label": "Service instance name"},
     "right_vn": {"type": "string",
                  "description": "Name of right network to be created"},
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_2": {
         "type": "string",
         "description": "subnet prefix len for left network"
     },
     "service_instance_fq_name": {"type": "string",
                                  "description":
                                  "Service instance FQDN for port tuple",
                                  "label": "Service instance fq name"},
     "left_vn": {"type": "string",
                 "description": "Name of left network to be created"},
     "management_network": {"type": "string",
                            "description":
                            "Name of management network to be created"},
     "left_vm_name": {"type": "string",
                      "description": "Name of the left VM"},
     "right_vm_name": {"type": "string",
                       "description": "Name of the right VM"},
     "service_instance_properties_ha_mode": {"type": "string",
                                             "description":
                                             "HA Mode of the Service Instance"
                                             },
     "policy_name": {"type": "string",
                     "description": "Name of the Policy"},
     "svm1_name": {"type": "string",
                   "description": "Name of SVM1"}},
    "resources":
    {"template_VirtualMachineInterface_5":
     {"type": "OS::ContrailV2::VirtualMachineInterface",
      "properties":
      {"name": {"get_param": "right_vm_name"},
       "virtual_network_refs":
       [{"list_join":
         [":", {"get_attr": ["template_VirtualNetwork_3", "fq_name"]}]}]}},
     "template_VirtualMachineInterface_4":
     {"type": "OS::ContrailV2::VirtualMachineInterface",
      "properties":
      {"name": {"get_param": "left_vm_name"},
       "virtual_network_refs":
       [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_2",
                                          "fq_name"]}]}]}},
     "template_VirtualMachineInterface_1":
     {"depends_on": ["template_PortTuple1"],
      "type": "OS::ContrailV2::VirtualMachineInterface",
      "properties":
      {"virtual_machine_interface_properties":
       {"virtual_machine_interface_properties_service_interface_type":
        {"get_param":
         "service_template_properties_interface_type_service_interface_type_1"}
        },
       "port_tuple_refs": [{"get_resource": "template_PortTuple1"}],
       "virtual_network_refs":
       [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_1",
                                          "fq_name"]}]}]}},
     "template_VirtualMachineInterface_3":
     {"depends_on": ["template_PortTuple1"],
      "type": "OS::ContrailV2::VirtualMachineInterface",
      "properties":
      {"virtual_machine_interface_properties":
       {"virtual_machine_interface_properties_service_interface_type":
        {"get_param":
         "service_template_properties_interface_type_service_interface_type_3"}
        },
       "port_tuple_refs": [{"get_resource": "template_PortTuple1"}],
       "virtual_network_refs":
       [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_3",
                                          "fq_name"]}]}]}},
     "template_VirtualMachineInterface_2":
     {"depends_on": ["template_PortTuple1"],
      "type": "OS::ContrailV2::VirtualMachineInterface",
      "properties":
      {"virtual_machine_interface_properties":
       {"virtual_machine_interface_properties_service_interface_type":
        {"get_param":
         "service_template_properties_interface_type_service_interface_type_2"}
        },
       "port_tuple_refs": [{"get_resource": "template_PortTuple1"}],
       "virtual_network_refs":
       [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_2",
                                          "fq_name"]}]}]}},
     "template_NetworkIpam_3": {"type": "OS::ContrailV2::NetworkIpam",
                                "properties":
                                {"name": {"get_param": "right_vn"}}},
     "template_NetworkIpam_2": {"type": "OS::ContrailV2::NetworkIpam",
                                "properties":
                                {"name": {"get_param": "left_vn"}}},
     "template_NetworkIpam_1": {"type": "OS::ContrailV2::NetworkIpam",
                                "properties":
                                {"name": {"get_param": "management_network"}}},
     "template_PortTuple1": {
         "depends_on": ["template_ServiceInstance"],
         "type": "OS::ContrailV2::PortTuple",
         "properties":
         {"service_instance":
          {"list_join": [":", {"get_attr": ["template_ServiceInstance",
                                            "fq_name"]}]}}
     },
     "template_PortTuple2": {
         "depends_on": ["template_ServiceInstance"],
         "type": "OS::ContrailV2::PortTuple",
         "properties":
         {"service_instance":
          {"list_join": [":", {"get_attr": ["template_ServiceInstance",
                                            "fq_name"]}]}}
     },
     "template_InstanceIp_3": {
         "depends_on":
         ["template_VirtualMachineInterface_3", "template_VirtualNetwork_3"],
         "type": "OS::ContrailV2::InstanceIp",
         "properties":
         {"virtual_machine_interface_refs":
          [{"get_resource": "template_VirtualMachineInterface_3"}],
          "virtual_network_refs":
          [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_3",
                                             "fq_name"]}]}]}
     },
     "template_InstanceIp_2": {
         "depends_on":
         ["template_VirtualMachineInterface_2", "template_VirtualNetwork_2"],
         "type": "OS::ContrailV2::InstanceIp",
         "properties":
         {"virtual_machine_interface_refs":
          [{"get_resource": "template_VirtualMachineInterface_2"}],
          "virtual_network_refs":
          [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_2",
                                             "fq_name"]}]}]}
     },
     "template_InstanceIp_1": {
         "depends_on":
         ["template_VirtualMachineInterface_1", "template_VirtualNetwork_1"],
         "type": "OS::ContrailV2::InstanceIp",
         "properties":
         {"virtual_machine_interface_refs":
          [{"get_resource": "template_VirtualMachineInterface_1"}],
          "virtual_network_refs":
          [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_1",
                                             "fq_name"]}]}]}
     },
     "instance1": {
         "depends_on": ["template_InstanceIp_1", "template_InstanceIp_2",
                        "template_InstanceIp_3"],
         "type": "OS::Nova::Server",
         "properties":
         {"image": {"get_param": "service_template_properties_image_name"},
          "name": {"get_param": "svm1_name"},
          "flavor": {"get_param": "service_template_properties_flavor"},
          "networks":
          [{"port": {"get_resource": "template_VirtualMachineInterface_1"}},
           {"port": {"get_resource": "template_VirtualMachineInterface_2"}},
           {"port": {"get_resource": "template_VirtualMachineInterface_3"}}]}
     },
     "template_InstanceIp_5": {
         "depends_on":
         ["template_VirtualMachineInterface_5", "template_VirtualNetwork_3"],
         "type": "OS::ContrailV2::InstanceIp",
         "properties":
         {"virtual_machine_interface_refs":
          [{"get_resource": "template_VirtualMachineInterface_5"}],
          "virtual_network_refs":
          [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_3",
                                             "fq_name"]}]}]}
     },
     "template_InstanceIp_4": {
         "depends_on":
         ["template_VirtualMachineInterface_4", "template_VirtualNetwork_2"],
         "type": "OS::ContrailV2::InstanceIp",
         "properties":
         {"virtual_machine_interface_refs":
          [{"get_resource": "template_VirtualMachineInterface_4"}],
          "virtual_network_refs":
          [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_2",
                                             "fq_name"]}]}]}
     },
     "template_VirtualNetwork_1": {
         "depends_on": ["template_NetworkIpam_1"],
         "type": "OS::ContrailV2::VirtualNetwork",
         "properties":
         {"network_ipam_refs": [{"get_resource": "template_NetworkIpam_1"}],
          "name": {"get_param": "management_network"},
          "network_ipam_refs_data": [{"network_ipam_refs_data_ipam_subnets": [{
              "network_ipam_refs_data_ipam_subnets_subnet":
              {"network_ipam_refs_data_ipam_subnets_subnet_ip_prefix":
               {"get_param":
                "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_1"},
               "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len":
               {"get_param":
                "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_1"}},
              "network_ipam_refs_data_ipam_subnets_addr_from_start":
              {"get_param":
               "network_ipam_refs_data_ipam_subnets_addr_from_start_true"}
          }]}]}
     },
     "template_VirtualNetwork_2": {
         "depends_on": ["template_NetworkIpam_2", "template_NetworkPolicy"],
         "type": "OS::ContrailV2::VirtualNetwork",
         "properties":
         {"network_policy_refs_data":
          [{"network_policy_refs_data_sequence":
            {"network_policy_refs_data_sequence_minor": 0,
             "network_policy_refs_data_sequence_major": 0}}],
          "network_ipam_refs": [{"get_resource": "template_NetworkIpam_2"}],
          "name": {"get_param": "left_vn"},
          "network_ipam_refs_data": [{"network_ipam_refs_data_ipam_subnets": [{
              "network_ipam_refs_data_ipam_subnets_subnet":
              {"network_ipam_refs_data_ipam_subnets_subnet_ip_prefix":
               {"get_param":
                "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_2"},
               "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len":
               {"get_param":
                "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_2"}},
              "network_ipam_refs_data_ipam_subnets_addr_from_start":
              {"get_param":
               "network_ipam_refs_data_ipam_subnets_addr_from_start_true"}
          }]}],
          "network_policy_refs":
          [{"list_join": [":", {"get_attr": ["template_NetworkPolicy",
                                             "fq_name"]}]}]}
     },
     "template_VirtualNetwork_3": {
         "depends_on": ["template_NetworkIpam_3", "template_NetworkPolicy"],
         "type": "OS::ContrailV2::VirtualNetwork",
         "properties":
         {"network_policy_refs_data":
          [{"network_policy_refs_data_sequence":
            {"network_policy_refs_data_sequence_minor": 0,
             "network_policy_refs_data_sequence_major": 0}}],
          "network_ipam_refs": [{"get_resource": "template_NetworkIpam_3"}],
          "name": {"get_param": "right_vn"},
          "network_ipam_refs_data": [{"network_ipam_refs_data_ipam_subnets": [{
              "network_ipam_refs_data_ipam_subnets_subnet":
              {"network_ipam_refs_data_ipam_subnets_subnet_ip_prefix":
               {"get_param":
                "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_3"},
               "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len":
               {"get_param":
                "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_3"}},
              "network_ipam_refs_data_ipam_subnets_addr_from_start":
              {"get_param":
               "network_ipam_refs_data_ipam_subnets_addr_from_start_true"}
          }]}],
          "network_policy_refs":
          [{"list_join": [":", {"get_attr": ["template_NetworkPolicy",
                                             "fq_name"]}]}]}
     },
     "instance2": {
         "depends_on": ["template_InstanceIp_21", "template_InstanceIp_22",
                        "template_InstanceIp_23"],
         "type": "OS::Nova::Server",
         "properties":
         {"image": {"get_param": "service_template_properties_image_name"},
          "name": {"get_param": "svm2_name"},
          "flavor": {"get_param": "service_template_properties_flavor"},
          "networks":
          [{"port": {"get_resource": "template_VirtualMachineInterface_21"}},
           {"port": {"get_resource": "template_VirtualMachineInterface_22"}},
           {"port": {"get_resource": "template_VirtualMachineInterface_23"}}]}
     },
     "template_leftVM": {
         "depends_on": ["template_InstanceIp_4"],
         "type": "OS::Nova::Server",
         "properties":
         {"image": {"get_param": "image"},
          "name": {"get_param": "left_vm_name"},
          "flavor": {"get_param": "flavor"},
          "networks":
          [{"port": {"get_resource": "template_VirtualMachineInterface_4"}}]}
     },
     "template_NetworkPolicy":
     {"type": "OS::ContrailV2::NetworkPolicy",
      "properties":
      {"network_policy_entries":
       {"network_policy_entries_policy_rule":
        [{"network_policy_entries_policy_rule_src_ports":
          [{"network_policy_entries_policy_rule_src_ports_end_port":
            {"get_param": "src_port_end"},
            "network_policy_entries_policy_rule_src_ports_start_port":
            {"get_param": "src_port_start"}}],
          "network_policy_entries_policy_rule_protocol":
          {"get_param": "protocol"},
          "network_policy_entries_policy_rule_src_addresses":
          [{"network_policy_entries_policy_rule_src_addresses_virtual_network":
            {"get_param": "left_vn_fqdn"}}],
          "network_policy_entries_policy_rule_direction":
          {"get_param": "direction"},
          "network_policy_entries_policy_rule_dst_ports": [
              {"network_policy_entries_policy_rule_dst_ports_end_port":
               {"get_param": "dst_port_end"},
               "network_policy_entries_policy_rule_dst_ports_start_port":
               {"get_param": "dst_port_start"}}
          ],
          "network_policy_entries_policy_rule_action_list":
          {"network_policy_entries_policy_rule_action_list_apply_service":
           [{"get_param": "service_instance_fq_name"}],
           "network_policy_entries_policy_rule_action_list_simple_action":
           {"get_param": "simple_action"}},
          "network_policy_entries_policy_rule_dst_addresses":
          [{"network_policy_entries_policy_rule_dst_addresses_virtual_network":
            {"get_param": "right_vn_fqdn"}}]}]},
       "name": {"get_param": "policy_name"}}},
     "template_ServiceInstance": {
         "depends_on": ["template_ServiceTemplate"],
         "type": "OS::ContrailV2::ServiceInstance",
         "properties":
         {"service_template_refs":
          [{"get_resource": "template_ServiceTemplate"}],
          "service_instance_properties":
          {"service_instance_properties_ha_mode":
           {"get_param": "service_instance_properties_ha_mode"},
           "service_instance_properties_interface_list":
           [{"service_instance_properties_interface_list_virtual_network":
             {"list_join": [":", {"get_attr": ["template_VirtualNetwork_1",
                                               "fq_name"]}]}},
            {"service_instance_properties_interface_list_virtual_network":
             {"list_join": [":", {"get_attr": ["template_VirtualNetwork_2",
                                               "fq_name"]}]}},
            {"service_instance_properties_interface_list_virtual_network":
             {"list_join": [":", {"get_attr": ["template_VirtualNetwork_3",
                                               "fq_name"]}]}}]},
          "name": {"get_param": "service_instance_name"}}
     },
     "template_InstanceIp_22": {
         "depends_on":
         ["template_VirtualMachineInterface_22", "template_VirtualNetwork_2"],
         "type": "OS::ContrailV2::InstanceIp",
         "properties":
         {"virtual_machine_interface_refs":
          [{"get_resource": "template_VirtualMachineInterface_22"}],
          "virtual_network_refs":
          [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_2",
                                             "fq_name"]}]}]}
     },
     "template_InstanceIp_23": {
         "depends_on":
         ["template_VirtualMachineInterface_23", "template_VirtualNetwork_3"],
         "type": "OS::ContrailV2::InstanceIp",
         "properties":
         {"virtual_machine_interface_refs":
          [{"get_resource": "template_VirtualMachineInterface_23"}],
          "virtual_network_refs":
          [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_3",
                                             "fq_name"]}]}]}
     },
     "template_InstanceIp_21": {
         "depends_on":
         ["template_VirtualMachineInterface_21", "template_VirtualNetwork_1"],
         "type": "OS::ContrailV2::InstanceIp",
         "properties":
         {"virtual_machine_interface_refs":
          [{"get_resource": "template_VirtualMachineInterface_21"}],
          "virtual_network_refs":
          [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_1",
                                             "fq_name"]}]}]}
     },
     "template_ServiceTemplate":
     {"type": "OS::ContrailV2::ServiceTemplate",
      "properties":
      {"domain": {"get_param": "domain"},
       "name": {"get_param": "service_template_name"},
       "service_template_properties":
       {"service_template_properties_image_name":
        {"get_param": "service_template_properties_image_name"},
        "service_template_properties_interface_type":
        [{"service_template_properties_interface_type_service_interface_type":
          {"get_param":
           "service_template_properties_interface_type_service_interface_type_1"
           }},
         {"service_template_properties_interface_type_service_interface_type":
          {"get_param":
           "service_template_properties_interface_type_service_interface_type_2"
           }},
         {"service_template_properties_interface_type_service_interface_type":
          {"get_param":
           "service_template_properties_interface_type_service_interface_type_3"
           }}],
        "service_template_properties_version":
        {"get_param": "service_template_properties_version"},
        "service_template_properties_service_type":
        {"get_param": "service_template_properties_service_type"},
        "service_template_properties_service_mode":
        {"get_param": "service_template_properties_service_mode"},
        "service_template_properties_ordered_interfaces":
        {"get_param": "service_template_properties_ordered_interfaces"}}}},
     "template_rightVM": {
         "depends_on": ["template_InstanceIp_5"],
         "type": "OS::Nova::Server",
         "properties":
         {"image": {"get_param": "image"},
          "name": {"get_param": "right_vm_name"},
          "flavor": {"get_param": "flavor"},
          "networks":
          [{"port": {"get_resource": "template_VirtualMachineInterface_5"}}]}
     },
     "template_VirtualMachineInterface_21":
     {"depends_on": ["template_PortTuple2"],
      "type": "OS::ContrailV2::VirtualMachineInterface",
      "properties":
      {"virtual_machine_interface_properties":
       {"virtual_machine_interface_properties_service_interface_type":
        {"get_param":
         "service_template_properties_interface_type_service_interface_type_1"}
        },
       "port_tuple_refs": [{"get_resource": "template_PortTuple2"}],
       "virtual_network_refs":
       [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_1",
                                          "fq_name"]}]}]}},
     "template_VirtualMachineInterface_22":
     {"depends_on": ["template_PortTuple2"],
      "type": "OS::ContrailV2::VirtualMachineInterface",
      "properties":
      {"virtual_machine_interface_properties":
       {"virtual_machine_interface_properties_service_interface_type":
        {"get_param":
         "service_template_properties_interface_type_service_interface_type_2"}
        },
       "port_tuple_refs": [{"get_resource": "template_PortTuple2"}],
       "virtual_network_refs":
       [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_2",
                                          "fq_name"]}]}]}},
     "template_VirtualMachineInterface_23":
     {"depends_on": ["template_PortTuple2"],
      "type": "OS::ContrailV2::VirtualMachineInterface",
      "properties":
      {"virtual_machine_interface_properties":
       {"virtual_machine_interface_properties_service_interface_type":
        {"get_param":
         "service_template_properties_interface_type_service_interface_type_3"}
        },
       "port_tuple_refs": [{"get_resource": "template_PortTuple2"}],
       "virtual_network_refs":
       [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_3",
                                          "fq_name"]}]}]}}}
}
pt_multi_inline = {
    "outputs":
    {"left_VM_ID": {"description": "ID of the left VM",
                    "value": {"get_attr": ["template_leftVM", "show", "id"]}},
     "si2_fqdn": {"description": "FQDN of the SI2",
                  "value":
                  {"get_attr": ["template_ServiceInstance2", "fq_name"]}},
     "si_fqdn": {"description": "FQDN of the SI",
                 "value":
                 {"get_attr": ["template_ServiceInstance", "fq_name"]}},
     "left_vn_FQDN": {"description": "FQDN of the left VN",
                      "value":
                      {"get_attr": ["template_VirtualNetwork_2", "fq_name"]}},
     "right_vn_FQDN": {"description": "FQDN of the right VN",
                       "value":
                       {"get_attr": ["template_VirtualNetwork_3", "fq_name"]}},
     "right_VM_ID": {"description": "ID of the right VM",
                     "value":
                     {"get_attr": ["template_rightVM", "show", "id"]}}},
    "heat_template_version": "2015-04-30",
    "parameters":
    {"svc_vn_mgmt_prefix":
     {"type": "string",
      "description": "Subnet prefix for the network svc_vn_mgmt"},
     "svc_vn_prefix_len":
     {"type": "string",
      "description": "Subnet prefix len for the svc_vn network"},
     "domain": {"type": "string",
                "description": "Name of the Domain"},
     "dst_port_end": {"type": "number",
                      "description": "End of the Destination Port Range"},
     "protocol": {"type": "string",
                  "description": "Protocol"},
     "service_template_properties_version":
     {"type": "string",
      "description": "Indicates service version"},
     "svm2_name": {"type": "string",
                   "description": "Name of the SVM2"},
     "svc_vn_right": {"type": "string",
                      "description":
                      "Name of the right network for transparent SI"},
     "service_template1_properties_image_name":
     {"type": "string",
      "description": "Name of the ST1 image"},
     "service_instance1_name": {"type": "string",
                                "description":
                                "Service instance1 for port tuple",
                                "label": "Service instance1 name"},
     "service_template_properties_service_type":
     {"type": "string",
      "description": "service type"},
     "service_template2_properties_service_mode":
     {"type": "string",
      "description": "service template2 mode"},
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_3":
     {"type": "string",
      "description": "subnet prefix for right network"},
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_2":
     {"type": "string",
      "description": "subnet prefix for left network"},
     "simple_action": {"type": "string",
                       "description": "Pass or Deny"},
     "flavor": {"type": "string",
                "description": "Flavor of the end VMs"},
     "src_port_start": {"type": "number",
                        "description": "Start of the Source Port Range"},
     "service_template1_properties_service_mode": {"type": "string",
                                                   "description":
                                                   "service template1 mode"},
     "service_template1_name": {"type": "string",
                                "description":
                                "Service template1 for port tuple",
                                "label": "Service template fq name"},
     "right_vn_fqdn": {"type": "string",
                       "description": "FQ Name of the right network"},
     "service_template_properties_ordered_interfaces":
     {"type": "string",
      "description": "Indicates service interfaces are ordered"},
     "network_ipam_refs_data_ipam_subnets_addr_from_start_true":
     {"type": "boolean",
      "description": "Address allocation from start of the pool"},
     "svc_vn_left_prefix": {"type": "string",
                            "description":
                            "Subnet prefix for the network svc_vn_left"},
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_3":
     {"type": "string",
      "description": "subnet prefix len for right network"},
     "service_template_properties_interface_type_service_interface_type_3": {
         "type": "string",
         "description": "service_interface_type for the ServiceTemplate"
     },
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_1": {
         "type": "string",
         "description": "subnet prefix len for mgmt network"
     },
     "service_template_properties_interface_type_service_interface_type_1": {
         "type": "string",
         "description": "service_interface_type for the ServiceTemplate"
     },
     "image": {"type": "string",
               "description": "Name of the end VM image"},
     "src_port_end": {"type": "number",
                      "description": "End of the Source Port Range"},
     "service_instance2_fq_name": {"type": "string",
                                   "description":
                                   "Service instance2 FQDN for port tuple",
                                   "label": "Service instance2 fq name"},
     "service_template2_properties_image_name": {"type": "string",
                                                 "description":
                                                 "Name of the ST2 image"},
     "service_template2_name": {"type": "string",
                                "description":
                                "Service template2 for port tuple",
                                "label": "Service template fq name"},
     "left_vn_fqdn": {"type": "string",
                      "description": "FQ Name of the left network"},
     "service_template_properties_interface_type_service_interface_type_2": {
         "type": "string",
         "description": "service_interface_type for the ServiceTemplate"
     },
     "right_vn": {"type": "string",
                  "description": "Name of right network to be created"},
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_2": {
         "type": "string",
         "description": "subnet prefix len for left network"
     },
     "svc_vn_mgmt": {"type": "string",
                     "description":
                     "Name of the mgmt network for transparent SI"},
     "left_vm_name": {"type": "string",
                      "description": "Name of the left VM"},
     "policy_name": {"type": "string",
                     "description": "Name of the Policy"},
     "dst_port_start": {"type": "number",
                        "description": "Start of the Destination Port Range"},
     "left_vn": {"type": "string",
                 "description": "Name of left network to be created"},
     "management_network": {"type": "string",
                            "description":
                            "Name of management network to be created"},
     "service_instance1_fq_name": {"type": "string",
                                   "description":
                                   "Service instance1 FQDN for port tuple",
                                   "label": "Service instance1 fq name"},
     "right_vm_name": {"type": "string",
                       "description": "Name of the right VM"},
     "service_template_properties_flavor": {"type": "string",
                                            "description": "Flavor"},
     "svc_vn_right_prefix": {"type": "string",
                             "description":
                             "Subnet prefix for the network svc_vn_right"},
     "service_instance2_name": {"type": "string",
                                "description":
                                "Service instance2 for port tuple",
                                "label": "Servic instance2 name"},
     "svc_vn_left": {"type": "string",
                     "description":
                     "Name of the left network for transparent SI"},
     "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_1": {
         "type": "string",
         "description": "subnet prefix for mgmt network"
     },
     "direction": {"type": "string",
                   "description": "Direction of the Policy"},
     "svm1_name": {"type": "string",
                   "description": "Name of the SVM1"}},
    "resources":
    {"template_VirtualMachineInterface_5":
     {"type": "OS::ContrailV2::VirtualMachineInterface",
      "properties":
      {"name": {"get_param": "right_vm_name"},
       "virtual_network_refs":
       [{"list_join":
         [":", {"get_attr": ["template_VirtualNetwork_3", "fq_name"]}]}]}},
     "template_VirtualMachineInterface_4":
     {"type": "OS::ContrailV2::VirtualMachineInterface",
      "properties":
      {"name": {"get_param": "left_vm_name"},
       "virtual_network_refs":
       [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_2",
                                          "fq_name"]}]}]}},
     "template_VirtualMachineInterface_1":
     {"depends_on": ["template_PortTuple1"],
      "type": "OS::ContrailV2::VirtualMachineInterface",
      "properties":
      {"virtual_machine_interface_properties":
       {"virtual_machine_interface_properties_service_interface_type":
        {"get_param":
         "service_template_properties_interface_type_service_interface_type_1"}
        },
       "port_tuple_refs": [{"get_resource": "template_PortTuple1"}],
       "virtual_network_refs":
       [{"list_join": [":", {"get_attr": ["template_svc_vn_mgmt", "fq_name"]}]}
        ]}},
     "template_ServiceInstance2":
     {"depends_on": ["template_ServiceTemplate2"],
      "type": "OS::ContrailV2::ServiceInstance",
      "properties":
      {"service_template_refs":
       [{"get_resource": "template_ServiceTemplate2"}],
       "service_instance_properties":
       {"service_instance_properties_interface_list":
        [{"service_instance_properties_interface_list_virtual_network":
          {"list_join": [":", {"get_attr": ["template_VirtualNetwork_1",
                                            "fq_name"]}]}},
         {"service_instance_properties_interface_list_virtual_network":
          {"list_join": [":", {"get_attr": ["template_VirtualNetwork_2",
                                            "fq_name"]}]}},
         {"service_instance_properties_interface_list_virtual_network":
          {"list_join": [":", {"get_attr": ["template_VirtualNetwork_3",
                                            "fq_name"]}]}}]},
       "name": {"get_param": "service_instance2_name"}}},
     "template_VirtualMachineInterface_3":
     {"depends_on": ["template_PortTuple1"],
      "type": "OS::ContrailV2::VirtualMachineInterface",
      "properties":
      {"virtual_machine_interface_properties":
       {"virtual_machine_interface_properties_service_interface_type":
        {"get_param":
         "service_template_properties_interface_type_service_interface_type_3"}
        },
       "port_tuple_refs": [{"get_resource": "template_PortTuple1"}],
       "virtual_network_refs":
       [{"list_join": [":", {"get_attr": ["template_svc_vn_right", "fq_name"]}]
         }]}},
     "template_svc_vn_left_ipam": {"type": "OS::ContrailV2::NetworkIpam",
                                   "properties":
                                   {"name": {"get_param": "svc_vn_left"}}},
     "template_PortTuple1": {
         "depends_on": ["template_ServiceInstance"],
         "type": "OS::ContrailV2::PortTuple",
         "properties":
         {"service_instance":
          {"list_join": [":", {"get_attr": ["template_ServiceInstance",
                                            "fq_name"]}]}}
     },
     "template_PortTuple2": {
         "depends_on": ["template_ServiceInstance2"],
         "type": "OS::ContrailV2::PortTuple",
         "properties":
         {"service_instance":
          {"list_join": [":", {"get_attr": ["template_ServiceInstance2",
                                            "fq_name"]}]}}
     },
     "template_VirtualNetwork_1":
     {"depends_on": ["template_NetworkIpam_1"],
      "type": "OS::ContrailV2::VirtualNetwork",
      "properties":
      {"network_ipam_refs": [{"get_resource": "template_NetworkIpam_1"}],
       "name": {"get_param": "management_network"},
       "network_ipam_refs_data": [{"network_ipam_refs_data_ipam_subnets": [
           {"network_ipam_refs_data_ipam_subnets_subnet":
            {"network_ipam_refs_data_ipam_subnets_subnet_ip_prefix":
             {"get_param":
              "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_1"},
             "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len":
             {"get_param":
              "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_1"}},
            "network_ipam_refs_data_ipam_subnets_addr_from_start":
            {"get_param":
             "network_ipam_refs_data_ipam_subnets_addr_from_start_true"}}
       ]}]}},
     "template_VirtualNetwork_2":
     {"depends_on": ["template_NetworkIpam_2", "template_NetworkPolicy"],
      "type": "OS::ContrailV2::VirtualNetwork",
      "properties":
      {"network_policy_refs_data":
       [{"network_policy_refs_data_sequence":
         {"network_policy_refs_data_sequence_minor": 0,
          "network_policy_refs_data_sequence_major": 0}}],
       "network_ipam_refs": [{"get_resource": "template_NetworkIpam_2"}],
       "name": {"get_param": "left_vn"},
       "network_ipam_refs_data": [{"network_ipam_refs_data_ipam_subnets": [
           {"network_ipam_refs_data_ipam_subnets_subnet":
            {"network_ipam_refs_data_ipam_subnets_subnet_ip_prefix":
             {"get_param":
              "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_2"},
             "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len":
             {"get_param":
              "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_2"}},
            "network_ipam_refs_data_ipam_subnets_addr_from_start":
            {"get_param":
             "network_ipam_refs_data_ipam_subnets_addr_from_start_true"}}
       ]}],
       "network_policy_refs":
       [{"list_join": [":", {"get_attr": ["template_NetworkPolicy", "fq_name"]}
                       ]}]}},
     "template_VirtualNetwork_3": {
         "depends_on": ["template_NetworkIpam_3", "template_NetworkPolicy"],
         "type": "OS::ContrailV2::VirtualNetwork",
         "properties":
         {"network_policy_refs_data":
          [{"network_policy_refs_data_sequence":
            {"network_policy_refs_data_sequence_minor": 0,
             "network_policy_refs_data_sequence_major": 0}}],
          "network_ipam_refs": [{"get_resource": "template_NetworkIpam_3"}],
          "name": {"get_param": "right_vn"},
          "network_ipam_refs_data": [{"network_ipam_refs_data_ipam_subnets": [{
              "network_ipam_refs_data_ipam_subnets_subnet":
              {"network_ipam_refs_data_ipam_subnets_subnet_ip_prefix":
               {"get_param":
                "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_3"},
               "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len":
               {"get_param":
                "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len_3"}},
              "network_ipam_refs_data_ipam_subnets_addr_from_start":
              {"get_param":
               "network_ipam_refs_data_ipam_subnets_addr_from_start_true"}
          }]}],
          "network_policy_refs":
          [{"list_join": [":", {"get_attr": ["template_NetworkPolicy",
                                             "fq_name"]}]}]}
     },
     "template_svc_vn_left": {
         "depends_on": ["template_svc_vn_left_ipam"],
         "type": "OS::ContrailV2::VirtualNetwork",
         "properties":
         {"network_ipam_refs": [{"get_resource": "template_svc_vn_left_ipam"}],
          "name": {"get_param": "svc_vn_left"},
          "network_ipam_refs_data": [{"network_ipam_refs_data_ipam_subnets": [
              {"network_ipam_refs_data_ipam_subnets_subnet":
               {"network_ipam_refs_data_ipam_subnets_subnet_ip_prefix":
                {"get_param": "svc_vn_left_prefix"},
                "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len":
                {"get_param": "svc_vn_prefix_len"}},
               "network_ipam_refs_data_ipam_subnets_addr_from_start":
               {"get_param":
                "network_ipam_refs_data_ipam_subnets_addr_from_start_true"}}
          ]}]}
     },
     "template_leftVM": {
         "depends_on": ["template_InstanceIp_4"],
         "type": "OS::Nova::Server",
         "properties":
         {"image": {"get_param": "image"},
          "name": {"get_param": "left_vm_name"},
          "flavor": {"get_param": "flavor"},
          "networks":
          [{"port": {"get_resource": "template_VirtualMachineInterface_4"}}]}
     },
     "template_svc_vn_mgmt_ipam": {"type": "OS::ContrailV2::NetworkIpam",
                                   "properties":
                                   {"name": {"get_param": "svc_vn_mgmt"}}},
     "template_svc_vn_right": {
         "depends_on": ["template_svc_vn_right_ipam"],
         "type": "OS::ContrailV2::VirtualNetwork",
         "properties":
         {"network_ipam_refs":
          [{"get_resource": "template_svc_vn_right_ipam"}],
          "name": {"get_param": "svc_vn_right"},
          "network_ipam_refs_data": [{"network_ipam_refs_data_ipam_subnets": [
              {"network_ipam_refs_data_ipam_subnets_subnet":
               {"network_ipam_refs_data_ipam_subnets_subnet_ip_prefix":
                {"get_param": "svc_vn_right_prefix"},
                "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len":
                {"get_param": "svc_vn_prefix_len"}},
               "network_ipam_refs_data_ipam_subnets_addr_from_start":
               {"get_param":
                "network_ipam_refs_data_ipam_subnets_addr_from_start_true"}}
          ]}]}
     },
     "template_ServiceInstance": {
         "depends_on": ["template_ServiceTemplate1"],
         "type": "OS::ContrailV2::ServiceInstance",
         "properties":
         {"service_template_refs":
          [{"get_resource": "template_ServiceTemplate1"}],
          "service_instance_properties":
          {"service_instance_properties_interface_list":
           [{"service_instance_properties_interface_list_virtual_network":
             {"list_join": [":", {"get_attr": ["template_svc_vn_mgmt",
                                               "fq_name"]}]}},
            {"service_instance_properties_interface_list_virtual_network":
             {"list_join": [":", {"get_attr": ["template_svc_vn_left",
                                               "fq_name"]}]}},
            {"service_instance_properties_interface_list_virtual_network":
             {"list_join": [":", {"get_attr": ["template_svc_vn_right",
                                               "fq_name"]}]}}]},
          "name": {"get_param": "service_instance1_name"}}
     },
     "template_VirtualMachineInterface_2":
     {"depends_on": ["template_PortTuple1"],
      "type": "OS::ContrailV2::VirtualMachineInterface",
      "properties":
      {"virtual_machine_interface_properties":
       {"virtual_machine_interface_properties_service_interface_type":
        {"get_param":
         "service_template_properties_interface_type_service_interface_type_2"}
        },
       "port_tuple_refs": [{"get_resource": "template_PortTuple1"}],
       "virtual_network_refs":
       [{"list_join": [":", {"get_attr": ["template_svc_vn_left", "fq_name"]}]}
        ]}},
     "template_svc_vn_mgmt": {
         "depends_on": ["template_svc_vn_mgmt_ipam"],
         "type": "OS::ContrailV2::VirtualNetwork",
         "properties":
         {"network_ipam_refs": [{"get_resource": "template_svc_vn_mgmt_ipam"}],
          "name": {"get_param": "svc_vn_mgmt"},
          "network_ipam_refs_data": [{"network_ipam_refs_data_ipam_subnets": [
              {"network_ipam_refs_data_ipam_subnets_subnet":
               {"network_ipam_refs_data_ipam_subnets_subnet_ip_prefix":
                {"get_param": "svc_vn_mgmt_prefix"},
                "network_ipam_refs_data_ipam_subnets_subnet_ip_prefix_len":
                {"get_param": "svc_vn_prefix_len"}},
               "network_ipam_refs_data_ipam_subnets_addr_from_start":
               {"get_param":
                "network_ipam_refs_data_ipam_subnets_addr_from_start_true"}}
          ]}]}
     },
     "template_VirtualMachineInterface_21":
     {"depends_on": ["template_PortTuple2"],
      "type": "OS::ContrailV2::VirtualMachineInterface",
      "properties":
      {"virtual_machine_interface_properties":
       {"virtual_machine_interface_properties_service_interface_type":
        {"get_param":
         "service_template_properties_interface_type_service_interface_type_1"}
        },
       "port_tuple_refs": [{"get_resource": "template_PortTuple2"}],
       "virtual_network_refs":
       [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_1",
                                          "fq_name"]}]}]}},
     "template_VirtualMachineInterface_22":
     {"depends_on": ["template_PortTuple2"],
      "type": "OS::ContrailV2::VirtualMachineInterface",
      "properties":
      {"virtual_machine_interface_properties":
       {"virtual_machine_interface_properties_service_interface_type":
        {"get_param":
         "service_template_properties_interface_type_service_interface_type_2"}
        },
       "port_tuple_refs": [{"get_resource": "template_PortTuple2"}],
       "virtual_network_refs":
       [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_2",
                                          "fq_name"]}]}]}},
     "template_VirtualMachineInterface_23":
     {"depends_on": ["template_PortTuple2"],
      "type": "OS::ContrailV2::VirtualMachineInterface",
      "properties":
      {"virtual_machine_interface_properties":
       {"virtual_machine_interface_properties_service_interface_type":
        {"get_param":
         "service_template_properties_interface_type_service_interface_type_3"}
        },
       "port_tuple_refs": [{"get_resource": "template_PortTuple2"}],
       "virtual_network_refs":
       [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_3",
                                          "fq_name"]}]}]}},
     "template_NetworkIpam_3": {"type": "OS::ContrailV2::NetworkIpam",
                                "properties":
                                {"name": {"get_param": "right_vn"}}},
     "template_NetworkIpam_2": {"type": "OS::ContrailV2::NetworkIpam",
                                "properties":
                                {"name": {"get_param": "left_vn"}}},
     "template_NetworkIpam_1": {"type": "OS::ContrailV2::NetworkIpam",
                                "properties":
                                {"name": {"get_param": "management_network"}}},
     "template_InstanceIp_3": {
         "depends_on":
         ["template_VirtualMachineInterface_3", "template_svc_vn_right"],
         "type": "OS::ContrailV2::InstanceIp",
         "properties":
         {"virtual_machine_interface_refs":
          [{"get_resource": "template_VirtualMachineInterface_3"}],
          "virtual_network_refs":
          [{"list_join": [":", {"get_attr": ["template_svc_vn_right", "fq_name"
                                             ]}]}]}
     },
     "template_InstanceIp_2": {
         "depends_on":
         ["template_VirtualMachineInterface_2", "template_svc_vn_left"],
         "type": "OS::ContrailV2::InstanceIp",
         "properties":
         {"virtual_machine_interface_refs":
          [{"get_resource": "template_VirtualMachineInterface_2"}],
          "virtual_network_refs":
          [{"list_join": [":", {"get_attr": ["template_svc_vn_left", "fq_name"]
                                }]}]}
     },
     "template_InstanceIp_1": {
         "depends_on":
         ["template_VirtualMachineInterface_1", "template_svc_vn_mgmt"],
         "type": "OS::ContrailV2::InstanceIp",
         "properties":
         {"virtual_machine_interface_refs":
          [{"get_resource": "template_VirtualMachineInterface_1"}],
          "virtual_network_refs":
          [{"list_join": [":", {"get_attr": ["template_svc_vn_mgmt", "fq_name"]
                                }]}]}
     },
     "instance1": {
         "depends_on": ["template_InstanceIp_1", "template_InstanceIp_2",
                        "template_InstanceIp_3"],
         "type": "OS::Nova::Server",
         "properties":
         {"image": {"get_param": "service_template1_properties_image_name"},
          "name": {"get_param": "svm1_name"},
          "flavor": {"get_param": "service_template_properties_flavor"},
          "networks":
          [{"port": {"get_resource": "template_VirtualMachineInterface_1"}},
           {"port": {"get_resource": "template_VirtualMachineInterface_2"}},
           {"port": {"get_resource": "template_VirtualMachineInterface_3"}}]}
     },
     "template_InstanceIp_5": {
         "depends_on":
         ["template_VirtualMachineInterface_5", "template_VirtualNetwork_3"],
         "type": "OS::ContrailV2::InstanceIp",
         "properties":
         {"virtual_machine_interface_refs":
          [{"get_resource": "template_VirtualMachineInterface_5"}],
          "virtual_network_refs":
          [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_3",
                                             "fq_name"]}]}]}
     },
     "template_InstanceIp_4": {
         "depends_on":
         ["template_VirtualMachineInterface_4", "template_VirtualNetwork_2"],
         "type": "OS::ContrailV2::InstanceIp",
         "properties":
         {"virtual_machine_interface_refs":
          [{"get_resource": "template_VirtualMachineInterface_4"}],
          "virtual_network_refs":
          [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_2",
                                             "fq_name"]}]}]}
     },
     "instance2": {
         "depends_on": ["template_InstanceIp_21", "template_InstanceIp_22",
                        "template_InstanceIp_23"],
         "type": "OS::Nova::Server",
         "properties":
         {"image": {"get_param": "service_template2_properties_image_name"},
          "name": {"get_param": "svm2_name"},
          "flavor": {"get_param": "service_template_properties_flavor"},
          "networks":
          [{"port": {"get_resource": "template_VirtualMachineInterface_21"}},
           {"port": {"get_resource": "template_VirtualMachineInterface_22"}},
           {"port": {"get_resource": "template_VirtualMachineInterface_23"}}]}
     },
     "template_NetworkPolicy":
     {"type": "OS::ContrailV2::NetworkPolicy",
      "properties":
      {"network_policy_entries":
       {"network_policy_entries_policy_rule":
        [{"network_policy_entries_policy_rule_src_ports":
          [{"network_policy_entries_policy_rule_src_ports_end_port":
            {"get_param": "src_port_end"},
            "network_policy_entries_policy_rule_src_ports_start_port":
            {"get_param": "src_port_start"}}],
          "network_policy_entries_policy_rule_protocol":
          {"get_param": "protocol"},
          "network_policy_entries_policy_rule_src_addresses":
          [{"network_policy_entries_policy_rule_src_addresses_virtual_network":
            {"get_param": "left_vn_fqdn"}}],
          "network_policy_entries_policy_rule_direction":
          {"get_param": "direction"},
          "network_policy_entries_policy_rule_dst_ports": [
              {"network_policy_entries_policy_rule_dst_ports_end_port":
               {"get_param": "dst_port_end"},
               "network_policy_entries_policy_rule_dst_ports_start_port":
               {"get_param": "dst_port_start"}}
          ],
          "network_policy_entries_policy_rule_action_list":
          {"network_policy_entries_policy_rule_action_list_apply_service":
           [{"get_param": "service_instance1_fq_name"},
            {"get_param": "service_instance2_fq_name"}],
           "network_policy_entries_policy_rule_action_list_simple_action":
           {"get_param": "simple_action"}},
          "network_policy_entries_policy_rule_dst_addresses":
          [{"network_policy_entries_policy_rule_dst_addresses_virtual_network":
            {"get_param": "right_vn_fqdn"}}]}]},
       "name": {"get_param": "policy_name"}}},
     "template_InstanceIp_22": {
         "depends_on":
         ["template_VirtualMachineInterface_22", "template_VirtualNetwork_2"],
         "type": "OS::ContrailV2::InstanceIp",
         "properties":
         {"virtual_machine_interface_refs":
          [{"get_resource": "template_VirtualMachineInterface_22"}],
          "virtual_network_refs":
          [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_2",
                                             "fq_name"]}]}]}
     },
     "template_InstanceIp_23": {
         "depends_on":
         ["template_VirtualMachineInterface_23", "template_VirtualNetwork_3"],
         "type": "OS::ContrailV2::InstanceIp",
         "properties":
         {"virtual_machine_interface_refs":
          [{"get_resource": "template_VirtualMachineInterface_23"}],
          "virtual_network_refs":
          [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_3",
                                             "fq_name"]}]}]}
     },
     "template_InstanceIp_21": {
         "depends_on":
         ["template_VirtualMachineInterface_21", "template_VirtualNetwork_1"],
         "type": "OS::ContrailV2::InstanceIp",
         "properties":
         {"virtual_machine_interface_refs":
          [{"get_resource": "template_VirtualMachineInterface_21"}],
          "virtual_network_refs":
          [{"list_join": [":", {"get_attr": ["template_VirtualNetwork_1",
                                             "fq_name"]}]}]}
     },
     "template_ServiceTemplate1":
     {"type": "OS::ContrailV2::ServiceTemplate",
      "properties":
      {"domain": {"get_param": "domain"},
       "name": {"get_param": "service_template1_name"},
       "service_template_properties":
       {"service_template_properties_image_name":
        {"get_param": "service_template1_properties_image_name"},
        "service_template_properties_interface_type":
        [{"service_template_properties_interface_type_service_interface_type":
          {"get_param":
           "service_template_properties_interface_type_service_interface_type_1"
           }},
         {"service_template_properties_interface_type_service_interface_type":
          {"get_param":
           "service_template_properties_interface_type_service_interface_type_2"
           }},
         {"service_template_properties_interface_type_service_interface_type":
          {"get_param":
           "service_template_properties_interface_type_service_interface_type_3"
           }}],
        "service_template_properties_version":
        {"get_param": "service_template_properties_version"},
        "service_template_properties_service_type":
        {"get_param": "service_template_properties_service_type"},
        "service_template_properties_service_mode":
        {"get_param": "service_template1_properties_service_mode"},
        "service_template_properties_ordered_interfaces":
        {"get_param": "service_template_properties_ordered_interfaces"}}}},
     "template_ServiceTemplate2":
     {"type": "OS::ContrailV2::ServiceTemplate",
      "properties":
      {"domain": {"get_param": "domain"},
       "name": {"get_param": "service_template2_name"},
       "service_template_properties":
       {"service_template_properties_image_name":
        {"get_param": "service_template2_properties_image_name"},
        "service_template_properties_interface_type":
        [{"service_template_properties_interface_type_service_interface_type":
          {"get_param":
           "service_template_properties_interface_type_service_interface_type_1"
           }},
         {"service_template_properties_interface_type_service_interface_type":
          {"get_param":
           "service_template_properties_interface_type_service_interface_type_2"
           }},
         {"service_template_properties_interface_type_service_interface_type":
          {"get_param":
           "service_template_properties_interface_type_service_interface_type_3"
           }}],
        "service_template_properties_version":
        {"get_param": "service_template_properties_version"},
        "service_template_properties_service_type":
        {"get_param": "service_template_properties_service_type"},
        "service_template_properties_service_mode":
        {"get_param": "service_template2_properties_service_mode"},
        "service_template_properties_ordered_interfaces":
        {"get_param": "service_template_properties_ordered_interfaces"}}}},
     "template_svc_vn_right_ipam": {"type": "OS::ContrailV2::NetworkIpam",
                                    "properties":
                                    {"name": {"get_param": "svc_vn_right"}}},
     "template_rightVM": {
         "depends_on": ["template_InstanceIp_5"],
         "type": "OS::Nova::Server",
         "properties":
         {"image": {"get_param": "image"},
          "name": {"get_param": "right_vm_name"},
          "flavor": {"get_param": "flavor"},
          "networks":
          [{"port": {"get_resource": "template_VirtualMachineInterface_5"}}]}
     }}
}

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
  u'action_list': {u'apply_service': ''},
  u'direction': '',
  u'dst_addresses': '',
  u'dst_ports': '',
  u'protocol': '',
  u'src_addresses': '',
  u'src_ports': ''
}

svc_rule_v2 = {
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
  u'description':
  u'HOT template to create a policy between two virtual network and apply a service. Attach the network policy to two virtual networks\n',
  u'heat_template_version': u'2013-05-23',
  u'parameters': {
    u'policy_name': {u'description': u'Policy Name', u'type': u'string'},
    u'dst_vn_id': {
      u'description': u'ID of the destination network',
      u'type': u'string'
    },
    u'src_vn_id': {
      u'description': u'ID of the source network',
      u'type': u'string'
    },
  },
  u'resources': {
    u'private_policy': {
      u'properties': {
        u'entries': {
          u'policy_rule': [],
        },
        u'name': {u'get_param': u'policy_name'}
      },
      u'type': u'OS::Contrail::NetworkPolicy'
    },
    u'private_policy_attach_net1': {
      u'properties': {
        u'network': {u'get_param': u'src_vn_id'},
        u'policy': {u'get_attr': [u'private_policy', u'fq_name']}
      },
      u'type': u'OS::Contrail::AttachPolicy'
    },
    u'private_policy_attach_net2': {
      u'properties': {
        u'network': {u'get_param': u'dst_vn_id'},
        u'policy': {u'get_attr': [u'private_policy', u'fq_name']}
      },
      u'type': u'OS::Contrail::AttachPolicy'
    }
  }
}

svc_chain_v2 = {
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

svc_tmpl = {
  u'description': u'HOT template to create a service template \n',
  u'heat_template_version': u'2013-05-23',
  u'outputs': {
    u'service_template_fq_name': {
      u'description': u'FQ name of the service template',
      u'value': {u'get_attr': [u'service_template', u'fq_name']}
    }
  },
  u'parameters': {
    u'flavor': {
      u'description': u'Flavor',
      u'type': u'string'
    },
    u'service_scaling': {
      u'description': u'Flag to enable scaling',
      u'type': u'string'
    },
    u'image': {
      u'description': u'Name of the image',
      u'type': u'string'
    },
    u'mode': {
      u'description': u'service mode',
      u'type': u'string'
    },
    u'name': {
      u'description': u'Name of service template',
      u'type': u'string'
    },
    u'service_interface_type_list': {
      u'description': u'List of interface types',
      u'type': u'string'
    },
    u'shared_ip_list': {
      u'description': u'List of shared ip enabled-disabled',
      u'type': u'string'
    },
    u'static_routes_list': {
      u'description': u'List of static routes enabled-disabled',
      u'type': u'string'
    },
    u'type': {
      u'description': u'service type',
      u'type': u'string'
    }
  },
  u'resources': {
    u'service_template': {
      u'properties': {
        u'flavor': {u'get_param': u'flavor'},
        u'service_scaling': {u'get_param': u'service_scaling'},
        u'image_name': {u'get_param': u'image'},
        u'name': {u'get_param': u'name'},
        u'service_interface_type_list': {u'Fn::Split': [u',', {u'Ref': u'service_interface_type_list'}]},
        u'service_mode': {u'get_param': u'mode'},
        u'service_type': {u'get_param': u'type'},
        u'shared_ip_list': {u'Fn::Split': [u',', {u'Ref': u'shared_ip_list'}]},
        u'static_routes_list': {u'Fn::Split': [u',', {u'Ref': u'static_routes_list'}]}
      },
      u'type': u'OS::Contrail::ServiceTemplate'
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

svc_inst = {
  u'description': u'HOT template to create service instance.\n',
  u'heat_template_version': u'2013-05-23',
  u'outputs': {
    u'num_active_service_instance_vms': {
      u'description': u'Number of active service VMs',
      u'value': {u'get_attr': [u'service_instance', u'active_service_vms']}
    },
    u'service_instance_fq_name': {
      u'description': u'FQ name of the service template',
      u'value': {u'get_attr': [u'service_instance', u'fq_name']}
    },
    u'service_instance_uuid': {
      u'description': u'UUID of the service template',
      u'value': {u'get_attr': [u'service_instance', u'show']}
    },
    u'service_instance_vms': {
      u'description': u'List of service VMs', u'value': {u'get_attr': [u'service_instance', u'virtual_machines']}
    }
  },
  u'parameters': {
    u'left_net_id': {
      u'description': u'ID of the left network\n',
      u'type': u'string'
    },
    u'right_net_id': {
      u'description': u'ID of the right network\n',
      u'type': u'string'
    },
    u'service_instance_name': {
      u'description': u'service instance name',
      u'type': u'string'
    },
    u'max_instances': {
      u'description': u'Number of service VMs',
      u'type': u'string'
    },
    u'service_template_fq_name': {
      u'description': u'service template name or ID',
      u'type': u'string'
    }
  },
  u'resources': {
    u'service_instance': {
      u'properties': {
        u'interface_list': [
          {u'virtual_network': u'auto'}, 
          {u'virtual_network': {u'get_param': u'left_net_id' }},
          {u'virtual_network': {u'get_param': u'right_net_id'}}
        ],
        u'name': {u'get_param': u'service_instance_name'},
        u'scale_out': {u'max_instances': {u'get_param': u'max_instances'}},
        u'service_template': {u'get_param': u'service_template_fq_name'}
      },
      u'type': u'OS::Contrail::ServiceInstance'
    }
  }
}

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
