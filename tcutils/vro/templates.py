class WfTemplate:
    
    def get_create_connection_template(params):
        create_connection = {'parameters': [{'description': 'Connection name',
           'name': 'name',
           'type': 'string',
           'value': {'string': {'value': params['name']}}},
          {'description': 'Controller host',
           'name': 'host',
           'type': 'string',
           'value': {'string': {'value': params['controller_ip']}}},
          {'description': 'Controller port',
           'name': 'port',
           'type': 'number',
           'value': {'number': {'value': params['port']}}},
          ]}
        return create_connection
    
    def get_delete_connection_template(params):
        delete_connection = {'parameters': [{'scope': 'local', 
            'type': 'Contrail:Connection',
            'name': 'item', 
            'value': {'sdk-object': {'type': 'Contrail:Connection', 
                        'id': params['Connection']}}}
            ]}
        return delete_connection
    
    def get_create_policy_template(params):
        #parent Contrail:Project ='api_123,Project:356f64e8-xx-xx'
        create_policy = {'parameters': [{'name': 'name',
           'scope': 'local',
           'type': 'string',
           'value': {'string': {'value': params['policy_name']}}},
          {'name': 'parent',
           'scope': 'local',
           'type': 'Contrail:Project',
           'value': {'sdk-object': {'id': params['Project'],
             'type': 'Contrail:Project'}}}]}
        return create_policy
    
    def get_delete_policy_template(params):
        #parent 'Contrail:NetworkPolicy='api_123,NetworkPolicy:12eacd94-d63e
        delete_policy = {'parameters': [{'name': 'item',
            'scope': 'local',
            'type': 'Contrail:NetworkPolicy',
            'value': {'sdk-object': {'id': params['NetworkPolicy'],
                      'type': 'Contrail:NetworkPolicy'}}}]}
        return delete_policy
    
    def get_add_policy_rules_template(params):
        #id: Contrail:NetworkPolicy='Controller,NetworkPolicy:12eacd94-XX-XX,
        #'simple_action': pass,deny
        #'protocol':
        #'direction': '>,<>'
        #'src_address_type']='Network,cidr,policy'
        #
        params
            
        policy_rules = {'parameters': [{'name': 'item',
        'scope': 'local',
        'type': 'Contrail:NetworkPolicy',
        'value': {'sdk-object': {'id':params['NetworkPolicy'], 
         'type': 'Contrail:NetworkPolicy'}}},
        {'name': 'simpleAction',
        'scope': 'local',
        'type': 'string',
        'value': {'string': {'value': params['simple_action']}}},
        {'name': 'protocol',
        'scope': 'local',
        'type': 'string',
        'value': {'string': {'value': params['protocol']}}},
        {'name': 'direction',
        'scope': 'local',
        'type': 'string',
        'value': {'string': {'value': params['direction']}}}]}
        if params.get('src_address_type') == 'Network':
            policy_rules['parameters'].append({'name': 'srcAddressType',
                                                'scope': 'local',
                                                'type': 'string',
                                                'value': {'string': {'value': 'Network'}}})
            if params.get('source_network') == 'any':
                policy_rules['parameters'].append({'name': 'srcVirtualNetworkType',
                                                   'scope': 'local',
                                                   'type': 'string',
                                                   'value': {'string': {'value': 'any'}}})
            else:
                policy_rules['parameters'].append({'name': 'srcVirtualNetworkType',
                                                   'scope': 'local',
                                                   'type': 'string',
                                                   'value': {'string': {'value': 'reference'}}})
                policy_rules['parameters'].append({'name': 'srcVirtualNetwork',
                                                    'scope': 'local',
                                                    'type': 'Contrail:VirtualNetwork',
                                                    'value': {'sdk-object': {'id':params['source_network'], 
                                                    'type': 'Contrail:VirtualNetwork'}}})
        if params.get('dest_address_type') == 'Network':
            policy_rules['parameters'].append({'name': 'dstAddressType',
                                                'scope': 'local',
                                                'type': 'string',
                                                'value': {'string': {'value': 'Network'}}})
            if params.get('dest_network') == 'any':
                policy_rules['parameters'].append({'name': 'dstVirtualNetworkType',
                                                   'scope': 'local',
                                                   'type': 'string',
                                                   'value': {'string': {'value': 'any'}}})
            else:
                policy_rules['parameters'].append({'name': 'dstVirtualNetworkType',
                                                   'scope': 'local',
                                                   'type': 'string',
                                                   'value': {'string': {'value': 'reference'}}})
                policy_rules['parameters'].append({'name': 'dstVirtualNetwork',
                                                    'scope': 'local',
                                                    'type': 'Contrail:VirtualNetwork',
                                                    'value': {'sdk-object': {'id':params['dest_network'], 
                                                    'type': 'Contrail:VirtualNetwork'}}})                                           
        if params.get('src_ports'):
            policy_rules['parameters'].append({'name': 'srcPorts',
                                               'scope': 'local',
                                               'type': 'string',
                                               'value': {'string': {'value': params['src_ports']}}})
        if params.get('dst_ports'):
            policy_rules['parameters'].append({'name': 'dstPorts',
                                               'scope': 'local',
                                               'type': 'string',
                                               'value': {'string': {'value': params['dst_ports']}}})
        return policy_rules
 
    def get_remove_policy_rules_template(params):
        pass
    
    #virtual_network
    def get_add_network_policy_to_vn_template(self, params):
        pol_to_vn = {'parameters': [{'name': 'item',
           'scope': 'local',
           'type': 'Contrail:VirtualNetwork',
           'value': {'sdk-object': {'id': params['VirtualNetwork'],
             'type': 'Contrail:VirtualNetwork'}}},
            {'name': 'child',
           'scope': 'local',
           'type': 'Contrail:NetworkPolicy',
           'value': {'sdk-object': {'id': params['NetworkPolicy'],
             'type': 'Contrail:NetworkPolicy'}}}]}
        return pol_to_vn
    def get_remove_network_policy_from_vn_template(self, params):
        pol_from_vn = {'parameters': [{'name': 'item',
           'scope': 'local',
           'type': 'Contrail:VirtualNetwork',
           'value': {'sdk-object': {'id': params['VirtualNetwork'],
             'type': 'Contrail:VirtualNetwork'}}},
            {'name': 'child',
           'scope': 'local',
           'type': 'Contrail:NetworkPolicy',
           'value': {'sdk-object': {'id': params['NetworkPolicy'],
             'type': 'Contrail:NetworkPolicy'}}}]}
        return pol_from_vn
    
    def get_edit_vn_template(self):
        pass
    
    #port
    def get_add_fip_to_port_template(self, params):
        fip_to_port = {'parameters': [{'name': 'item',
           'scope': 'local',
           'type': 'Contrail:Port',
           'value': {'sdk-object': {'id': params['Port'], 'type': 'Contrail:Port'}}},
           {'name': 'child',
           'scope': 'local',
           'type': 'Contrail:FloatingIp',
           'value': {'sdk-object': {'id': params['FloatingIp'],
             'type': 'Contrail:FloatingIp'}}},
           {'name': 'fixedIpAddress',
           'scope': 'local',
           'type': 'boolean',
           'value': {'boolean': {'value': True}}}]}
        return fip_to_port
    
    def get_remove_fip_from_port_template(self, params):
        fip_to_port = {'parameters': [{'name': 'item',
           'scope': 'local',
           'type': 'Contrail:Port',
           'value': {'sdk-object': {'id': params['Port'], 'type': 'Contrail:Port'}}},
           {'name': 'child',
           'scope': 'local',
           'type': 'Contrail:FloatingIp',
           'value': {'sdk-object': {'id': params['FloatingIp'],
             'type': 'Contrail:FloatingIp'}}}]}
        return fip_to_port
    
    def get_add_sg_to_port_template(self, params):
        sg_to_port = {'parameters': [{'name': 'item',
           'scope': 'local',
           'type': 'Contrail:Port',
           'value': {'sdk-object': {'id': params['Port'],
             'type': 'Contrail:Port'}}},
            {'name': 'child',
           'scope': 'local',
           'type': 'Contrail:SecurityGroup',
           'value': {'sdk-object': {'id': params['SecurityGroup'],
             'type': 'Contrail:SecurityGroup'}}}]}
        return sg_to_port

    def get_remove_sg_from_port_template(self, params):
        sg_from_port = {'parameters': [{'name': 'item',
           'scope': 'local',
           'type': 'Contrail:Port',
           'value': {'sdk-object': {'id': params['Port'],
             'type': 'Contrail:Port'}}},
            {'name': 'child',
           'scope': 'local',
           'type': 'Contrail:SecurityGroup',
           'value': {'sdk-object': {'id': params['SecurityGroup'],
             'type': 'Contrail:SecurityGroup'}}}]}
        return sg_from_port
    
    #FIP
    def get_create_fip_template(self, params):
        fip = {'parameters': [{'name': 'parent',
            'scope': 'local',
            'type': 'Contrail:FloatingIpPool',
            'value': {'sdk-object': {'id': params['FloatingIpPool'],
                'type': 'Contrail:FloatingIpPool'}}},
            {'name': 'projects',
             'scope': 'local',
             'type': 'Array/Contrail:Project',
             'value': {'array': {'elements': [{'sdk-object': {'id': params['Project'],
                'type': 'Contrail:Project'}}]}}},
            {'name': 'address',
             'scope': 'local',
             'type': 'string',
             'value': {'string': {'value': ''}}}]}
    
    def get_delete_fip_template(self, params):
        fip = {'parameters': [{'name': 'item',
               'scope': 'local',
               'type': 'Contrail:FloatingIp',
               'value': {'sdk-object': {'id': params['FloatingIp'],
                 'type': 'Contrail:FloatingIp'}}}]}
        return fip
    
    #FIP_pool
    def get_create_fip_pool_template(self, params):
        fip_pool = {'parameters': [{'description': 'Connection name',
           'name': 'name',
           'type': 'string',
           'value': {'string': {'value': params['pool_name']}}},
            {'name': 'parent',
           'scope': 'local',
           'type': 'Contrail:Project',
           'value': {'sdk-object': {'id': params['VirtualNetwork'],
           'type': 'Contrail:VirtualNetwork'}}}]}
    
    def get_delete_fip_pool_template(self, params):
        fip_pool = {'parameters': [{'name': 'item',
           'scope': 'local',
           'type': 'Contrail:FloatingIpPool',
           'value': {'sdk-object': {'id': params['FolatingIpPool'],
            'type': 'Contrail:FloatingIpPool'}}}]}
        return fip_pool
    
    def get_edit_fip_pool_template(self):
        pass
    
    #Security_group
    
    def get_create_sg_template(self, params):
        create_sg = {'parameters': [{'name': 'name',
           'scope': 'local',
           'type': 'string',
           'value': {'string': {'value': params['sg_name']}}},
          {'name': 'parent',
           'scope': 'local',
           'type': 'Contrail:Project',
           'value': {'sdk-object': {'id': params['Project'],
                    'type': 'Contrail:Project'}}}]}
        return create_sg
    
    def get_edit_sg_template(self):
        pass
    
    def get_add_rule_to_sg_template(self):
        #ether_type:{'IPv4','IPv6'}
        #direction:{ingress,egress}
        #address_type:{'CIDR','Security Group'}
        #protocol{'icmp','tcp',etc}
        #ports:{'any','range(10-20)'
        sg_rules = {'parameters': [{'name': 'parent',
           'scope': 'local',
           'type': 'Contrail:SecurityGroup',
           'value': {'sdk-object': {'id': params['SecurityGroup'],
             'type': 'Contrail:SecurityGroup'}}},
          {'name': 'direction',
           'scope': 'local',
           'type': 'string',
           'value': {'string': {'value': params['direction']}}},
          {'name': 'ethertype',
           'scope': 'local',
           'type': 'string',
           'value': {'string': {'value': 'IPv4'}}}]}
        if params.get('addressType') == 'CIDR':
            sg_rules['parameters'].append({'name': 'addressType',
                'scope': 'local',
                'type': 'string',
                'value': {'string': {'value': 'CIDR'}}},
                {'name': 'addressCidr',
                'scope': 'local',
                'type': 'string',
                'value': {'string': {'value': params['address_cidr']}}})
        else:
            sg_rules['parameters'].append({'name': 'addressType',
                'scope': 'local',
                'type': 'string',
                'value': {'string': {'value': 'Security Group'}}},
                {'name': 'addressSecurityGroup',
                'scope': 'local',
                'type': 'Contrail:SecurityGroup',
                'value': {'sdk-object': {'id':params['addressSecurityGroup'],
                 'type': 'Contrail:SecurityGroup'}}})
                                          
        sg_rules['parameters'].append({'name': 'protocol',
               'scope': 'local',
               'type': 'string',
               'value': {'string': {'value': params['protocol']}}},
                {'name': 'ports',
               'scope': 'local',
               'type': 'string',
               'value': {'string': {'value': params['ports']}}})
        return sg_rules
    
    def get_remove_rule_from_sg_template(self):
        pass
    
    def get_delete_sg_template(self, params):
        delete_sg = {'parameters': [{'name': 'item',
            'scope': 'local',
            'type': 'Contrail:SecurityGroup',
            'value': {'sdk-object': {'id': params['SecurityGroup'],
                      'type': 'Contrail:SecurityGroup'}}}]}
        return delete_sg
    
    #Service Template
    def get_create_st_template(self, params):
        #parent:Connection
        #service_mode:{'transparent','in_network','in_network_nat'}
        #service_type:{'firewall','analyzer'}
        #virtualization_type:{'physical','virtual_machine'}
        #vrouter_instance_type:{'livbirt-qemu','docker'}
        create_st = {'parameters': [{'name': 'parent',
               'scope': 'local',
               'type': 'Contrail:Connection',
               'value': {'sdk-object': {'id': params['Connection'],
                 'type': 'Contrail:Connection'}}},
              {'name': 'name',
               'scope': 'local',
               'type': 'string',
               'value': {'string': {'value': params['st_name']}}},
              {'name': 'version',
               'scope': 'local',
               'type': 'number',
               'value': {'number': {'value': 2}}},
              {'name': 'serviceMode',
               'scope': 'local',
               'type': 'string',
               'value': {'string': {'value': params['svc_mode']}}},
              {'name': 'serviceType',
               'scope': 'local',
               'type': 'string',
               'value': {'string': {'value': params['svc_type']}}},
              {'name': 'serviceVirtualizationType',
               'scope': 'local',
               'type': 'string',
               'value': {'string': {'value': 'virtual-machine'}}},
              {'name': 'interfaceType',
               'scope': 'local',
               'type': 'Array/string',
               'value': {'array': {'elements': [{'string': {'value': 'management'}},
                  {'string': {'value': 'left'}},
                  {'string': {'value': 'right'}}]}}}]}
              
        return create_st
                
    def get_delete_st_template(self, params):
        delete_st = {'parameters': [{'name': 'item',
                'scope': 'local',
                'type': 'Contrail:ServiceTemplate',
                'value': {'sdk-object': {'id': params['ServiceTemplate'],
                          'type': 'Contrail:ServiceTemplate'}}}]}
        return delete_st

    #Service Instance 
    def get_create_si_template(self, params):
        si = {'parameters': [{'name': 'parent',
               'scope': 'local',
               'type': 'Contrail:Project',
               'value': {'sdk-object': {'id': params['Project'],
                 'type': 'Contrail:Project'}}},
              {'name': 'name',
               'scope': 'local',
               'type': 'string',
               'value': {'string': {'value': params['name']}}},
              {'name': 'serviceTemplate',
               'scope': 'local',
               'type': 'Contrail:ServiceTemplate',
               'value': {'sdk-object': {'id': params['ServiceTemplate'],
                 'type': 'Contrail:ServiceTemplate'}}},
              {'name': 'virtualRouterId',
               'scope': 'local',
               'type': 'string',
               'value': {'string': {'value': ''}}},
              {'name': 'interface0',
               'scope': 'local',
               'type': 'Contrail:VirtualNetwork',
               'value': {'sdk-object': {'id': params['MgmtVirtualNetwork'],
                 'type': 'Contrail:VirtualNetwork'}}},
              {'name': 'interface1',
               'scope': 'local',
               'type': 'Contrail:VirtualNetwork',
               'value': {'sdk-object': {'id': params['LeftVirtualnetwork'],
                 'type': 'Contrail:VirtualNetwork'}}},
              {'name': 'interface2',
               'scope': 'local',
               'type': 'Contrail:VirtualNetwork',
               'value': {'sdk-object': {'id': params['RightVirtualNetwork'],
                 'type': 'Contrail:VirtualNetwork'}}}]}
        return si
    
    def get_delete_si_template(self, params):
        si = {'parameters': [{'name': 'item',
               'scope': 'local',
               'type': 'Contrail:ServiceTemplate',
               'value': {'sdk-object': {'id': params['ServiceTemplate'],
                 'type': 'Contrail:ServiceTemplate'}}}]}
        return si

    def get_add_port_tuple_template(self, params):
        
        port_tuple = {'parameters': [{'name': 'name',
               'scope': 'local',
               'type': 'string',
               'value': {'string': {'value': params['name']}}},
              {'name': 'parent',
               'scope': 'local',
               'type': 'Contrail:ServiceTemplate',
               'value': {'sdk-object': {'id': params['ServiceInstance'],
                 'type': 'Contrail:SeriviceInstance'}}},
              {'name': 'port0',
               'scope': 'local',
               'type': 'Contrail:Port',
               'value': {'sdk-object': {'id': params['MgmtInterface'],
                 'type': 'Contrail:Port'}}},
              {'name': 'port1',
               'scope': 'local',
               'type': 'Contrail:Port',
               'value': {'sdk-object': {'id': params['LeftInterface'],
                 'type': 'Contrail:Port'}}},
              {'name': 'port2',
               'scope': 'local',
               'type': 'Contrail:Port',
               'value': {'sdk-object': {'id': params['RightInterface'],
                 'type': 'Contrail:Port'}}}]}

    def get_remove_port_tuple_template(self, params):
        port_tuple = {'parameters': [{'name': 'item',
               'scope': 'local',
               'type': 'Contrail:PortTuple',
               'value': {'sdk-object': {'id': params['PortTuple'],
                 'type': 'Contrail:PortTuple'}}},
              {'name': 'parent',
               'scope': 'local',
               'type': 'Contrail:ServiceInstance',
               'value': {'sdk-object': {'id': params['ServiceInstance'],
                 'type': 'Contrail:ServiceInstance'}}}]}
        return port_tuple 
    
    workflow_name_dict = {
        'create_connection' : 'Create Contrail controller connection',
        'delete_connection' : 'Delete Contrail controller connection',
        'create_poject' : 'Create Project',
        'create_vn' : 'Create virtual network',
        'create_policy': 'Create network policy',
        'add_policy_rules': 'Add rule to network policy',
        'remove_policy_rules': 'Remove network policy rule',
        'delete_policy': 'Delete Network policy',
        'add_policy_to_vn': 'Add network policy to virtual network',
        'remove_policy_from_vn': 'Remove network policy from virtual network',
        'edit_vn': 'Edit virtual network',
        'add_fip_to_port': 'Add floating IP to port',
        'remove_fip_from_port': 'Remove floating IP from port',
        'add_sg_to_port': 'Add security group to port',
        'remove_sg_from_port': 'Remove security from port',
        'create_fip': 'Create floating IP',
        'delete_fip': 'Delete floating IP',
        'create_fip_pool': 'Create floating IP pool',
        'delete_fip_pool': 'Delete floating IP pool',
        'edit_fip_pool': 'Delete floating IP pool',
        'create_sg': 'Create security group',
        'add_rule_to_sg': 'Add rule to security group',
        'remove_rule_from_sg': 'Remove security group rule',
        'delete_sg': 'Delete security group',
        'create_st': 'Create service template',
        'delete_st': 'Delete service template',
        'create_si': 'Delete service instance',
        'delete_si': 'Delete service instance',
        'add_port_tuple': 'Add port tuple to service instance',
        'remove_port_tuple': 'Remove port tuple from service instance'         
    }
    
    workflow_name_template = {'create_connection': get_create_connection_template,
        'delete_connection': get_delete_connection_template,
        'create_policy': get_create_policy_template, 
        'add_policy_rules': get_add_policy_rules_template, 
        'remove_policy_rules': get_remove_policy_rules_template, 
        'delete_policy': get_delete_policy_template, 
        'add_policy_to_vn': get_add_network_policy_to_vn_template, 
        'remove_policy_from_vn': get_remove_network_policy_from_vn_template, 
        'edit_vn': get_edit_vn_template, 
        'add_fip_to_port': get_add_fip_to_port_template, 
        'remove_fip_from_port': get_remove_fip_from_port_template, 
        'add_sg_to_port': get_add_sg_to_port_template, 
        'remove_sg_from_port': get_remove_sg_from_port_template, 
        'create_fip': get_create_fip_template, 
        'delete_fip': get_delete_fip_template, 
        'create_fip_pool': get_create_fip_pool_template, 
        'delete_fip_pool': get_delete_fip_pool_template, 
        'edit_fip_pool': get_edit_fip_pool_template, 
        'create_sg': get_create_sg_template, 
        'add_rule_to_sg': get_add_rule_to_sg_template, 
        'remove_rule_from_sg': get_remove_rule_from_sg_template, 
        'delete_sg': get_delete_sg_template, 
        'create_st': get_create_st_template, 
        'delete_st': get_delete_st_template, 
        'create_si': get_create_si_template, 
        'delete_si': get_delete_si_template, 
        'add_port_tuple': get_add_port_tuple_template, 
        'remove_port_tuple': get_remove_port_tuple_template
    }
    
    if __name__ == '__main__':
        param_dict = {'wf_name':'create_connection','host_name':'c54','host_ip':'123','port':123}
        temp = _workflow_name_template[param_dict['wf_name']](param_dict)
        #temp = template(param_dict)
        print temp
        
    
