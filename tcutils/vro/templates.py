from __future__ import print_function
from builtins import object
class WfTemplate(object):

    def get_create_connection_template(self, params):
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

    def get_delete_connection_template(self, params):
        delete_connection = {'parameters': [{'scope': 'local',
            'type': 'Contrail:Connection',
            'name': 'item',
            'value': {'sdk-object': {'type': 'Contrail:Connection',
                                     'id': params['Connection']}}}
            ]}
        return delete_connection

    def get_create_policy_template(self, params):
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

    def get_delete_policy_template(self, params):
        #parent 'Contrail:NetworkPolicy='api_123,NetworkPolicy:12eacd94-d63e
        delete_policy = {'parameters': [{'name': 'item',
            'scope': 'local',
            'type': 'Contrail:NetworkPolicy',
            'value': {'sdk-object': {'id': params['NetworkPolicy'],
                      'type': 'Contrail:NetworkPolicy'}}}]}
        return delete_policy

    def get_add_policy_rules_template(self, params):
        #id: Contrail:NetworkPolicy='Controller,NetworkPolicy:12eacd94-XX-XX,
        #'simple_action': pass,deny
        #'protocol':
        #'direction': '>,<>'
        #'src_address_type']='Network,cidr,policy'
        #
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
        if params.get('src_address_type') == 'Policy':
            policy_rules['parameters'].append({'name': 'srcAddressType',
                                                'scope': 'local',
                                                'type': 'string',
                                                'value': {'string': {'value': 'Policy'}}})
            policy_rules['parameters'].append({'name': 'srcNetworkPolicy',
                                                'scope': 'local',
                                                'type': 'Contrail:NetworkPolicy',
                                                'value': {'sdk-object': {'id':params['source_policy'],
                                                'type': 'Contrail:NetworkPolicy'}}})
        if params.get('dest_address_type') == 'Policy':
            policy_rules['parameters'].append({'name': 'dstAddressType',
                                                'scope': 'local',
                                                'type': 'string',
                                                'value': {'string': {'value': 'Policy'}}})
            policy_rules['parameters'].append({'name': 'dstNetworkPolicy',
                                                'scope': 'local',
                                                'type': 'Contrail:NetworkPolicy',
                                                'value': {'sdk-object': {'id':params['dest_policy'],
                                                'type': 'Contrail:NetworkPolicy'}}})
        if params.get('ServiceInstance'):
            policy_rules['parameters'].append({'name': 'defineServices',
                                                'scope': 'local',
                                                'type': 'boolean',
                                                'value': {'boolean': {'value': 'true'}}})
            policy_rules['parameters'].append({'name': 'services',
                                                'scope': 'local',
                                                'type': 'Array/Contrail:ServiceInstance',
                                                'value': {'array': {'elements': params['ServiceInstance']}}})
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

    def get_create_vn_template(self, params):
        create_vn = {'parameters': [{'name': 'name',
                   'scope': 'local',
                   'type': 'string',
                   'value': {'string': {'value': params['vn_name']}}},
                  {'name': 'parent',
                   'scope': 'local',
                   'type': 'Contrail:Project',
                   'value': {'sdk-object': {'id': params['Project'],
                     'type': 'Contrail:Project'}}}]}
        return create_vn

    def get_delete_vn_template(self, params):
        delete_vn = {'parameters': [{'name': 'item',
           'scope': 'local',
           'type': 'Contrail:VirtualNetwork',
           'value': {'sdk-object': {'id': params['VirtualNetwork'],
             'type': 'Contrail:VirtualNetwork'}}}]}
        return delete_vn
       
    def get_edit_vn_template():
        pass
        
    def get_add_ipam_to_vn_template():
        pass
    
    def get_add_subnet_to_vn_template(self, params):
        add_sub ={'parameters': [{'name': 'parent',
               'scope': 'local',
               'type': 'Contrail:VirtualNetwork',
               'value': {'sdk-object': {'id': params['VirtualNetwork'],
                 'type': 'Contrail:VirtualNetwork'}}},
              {'name': 'ipam',
               'scope': 'local',
               'type': 'Contrail:NetworkIpam',
               'value': {'sdk-object': {
                 'id': params['NetworkIpam'],
                 'type': 'Contrail:NetworkIpam'}}},
              {'name': 'subnet',
               'scope': 'local',
               'type': 'string',
               'value': {'string': {'value': params['subnet']}}},
              {'name': 'allocationPools', 'scope': 'local', 'type': 'Array/string'},
              {'name': 'allocUnit', 'scope': 'local', 'type': 'number'},
              {'name': 'addrFromStart',
               'scope': 'local',
               'type': 'boolean',
               'value': {'boolean': {'value': True}}},
              {'name': 'dnsServerAddress',
               'scope': 'local',
               'type': 'string',
               'value': {'string': {'value': ''}}},
              {'name': 'defaultGateway',
               'scope': 'local',
               'type': 'string',
               'value': {'string': {'value': params['gateway']}}},
              {'name': 'enableDhcp',
               'scope': 'local',
               'type': 'boolean',
               'value': {'boolean': {'value': True}}}]}
        return add_sub
    def get_add_tag_to_vn_template():
        pass
    
    def get_remove_ipam_from_vn_template():
        pass
    
    def get_remove_subnet_from_vn_template():
        pass
    
    def get_remove_tag_from_vn_template():
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
    
    def get_add_shc_to_port_template():
        pass
    
    def get_remove_shc_from_port_template():
        pass
    
    def get_add_tag_to_port_template():
        pass
    
    def get_remove_tag_from_port_template():
        pass

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
        return fip

    def get_delete_fip_template(self, params):
        fip = {'parameters': [{'name': 'item',
               'scope': 'local',
               'type': 'Contrail:FloatingIp',
               'value': {'sdk-object': {'id': params['FloatingIp'],
                 'type': 'Contrail:FloatingIp'}}}]}
        return fip
    
    #FIP_pool
    def get_create_fip_pool_template(self, params):
        fip_pool = {'parameters': [{
           'name': 'name',
           'type': 'string',
           'value': {'string': {'value': params['pool_name']}}},
            {'name': 'parent',
           'scope': 'local',
           'type': 'Contrail:VirtualNetwork',
           'value': {'sdk-object': {'id': params['VirtualNetwork'],
           'type': 'Contrail:VirtualNetwork'}}}]}
        return fip_pool

    def get_delete_fip_pool_template(self, params):
        fip_pool = {'parameters': [{'name': 'item',
           'scope': 'local',
           'type': 'Contrail:FloatingIpPool',
           'value': {'sdk-object': {'id': params['FloatingIpPool'],
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

    def get_edit_sg_template(self, params):
        pass

    def get_edit_sg_rule_template(self, params):
        return self.get_add_rule_to_sg_template(params)
   
    def get_add_rule_to_sg_template(self, params):
        #ether_type:{'IPv4','IPv6'}
        #direction:{ingress,egress}
        #address_type:{'CIDR','Security Group'}
        #protocol{'icmp','tcp',etc}
        #ports:{'any','range(10-20)'
        sg_rules = {'parameters': [{'name': 'item',
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
                'value': {'string': {'value': 'CIDR'}}})
            sg_rules['parameters'].append({'name': 'addressCidr',
                'scope': 'local',
                'type': 'string',
                'value': {'string': {'value': params['address_cidr']}}})
        else:
            sg_rules['parameters'].append({'name': 'addressType',
                'scope': 'local',
                'type': 'string',
                'value': {'string': {'value': 'Security Group'}}})
            sg_rules['parameters'].append({'name': 'addressSecurityGroup',
                'scope': 'local',
                'type': 'Contrail:SecurityGroup',
                'value': {'sdk-object': {'id':params['addressSecurityGroup'],
                 'type': 'Contrail:SecurityGroup'}}})
                                          
        sg_rules['parameters'].append({'name': 'protocol',
               'scope': 'local',
               'type': 'string',
               'value': {'string': {'value': params['protocol']}}})
        sg_rules['parameters'].append({'name': 'ports',
               'scope': 'local',
               'type': 'string',
               'value': {'string': {'value': params['ports']}}})
        return sg_rules

    def get_remove_rule_from_sg_template(self, params):
        rm_rule = {'parameters': [{'name': 'item',
            'scope': 'local',
            'type': 'Contrail:SecurityGroup',
            'value': {'sdk-object': {'id': params['SecurityGroup'],
                      'type': 'Contrail:SecurityGroup'}}},
            {'name': 'rule',
            'scope': 'local',
            'type': 'string',
            'value': {'string': {'value': params['rule']}}}]}      
        return rm_rule
    
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
               'value': {'string': {'value': params['si_name']}}},
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
               'value': {'sdk-object': {'id': params['LeftVirtualNetwork'],
                 'type': 'Contrail:VirtualNetwork'}}},
              {'name': 'interface1',
               'scope': 'local',
               'type': 'Contrail:VirtualNetwork',
               'value': {'sdk-object': {'id': params['RightVirtualNetwork'],
                 'type': 'Contrail:VirtualNetwork'}}},
              {'name': 'interface2',
               'scope': 'local',
               'type': 'Contrail:VirtualNetwork',
               'value': {'sdk-object': {'id': params['MgmtVirtualNetwork'],
                 'type': 'Contrail:VirtualNetwork'}}}]}
        return si

    def get_delete_si_template(self, params):
        si = {'parameters': [{'name': 'item',
               'scope': 'local',
               'type': 'Contrail:ServiceInstance',
               'value': {'sdk-object': {'id': params['ServiceInstance'],
                 'type': 'Contrail:ServiceInstance'}}}]}
        return si

    def get_add_port_tuple_template(self, params):
        port_tuple = {'parameters': [{'name': 'name',
               'scope': 'local',
               'type': 'string',
               'value': {'string': {'value': params['pt_name']}}},
              {'name': 'parent',
               'scope': 'local',
               'type': 'Contrail:ServiceInstance',
               'value': {'sdk-object': {'id': params['ServiceInstance'],
                 'type': 'Contrail:ServiceInstance'}}},
              {'name': 'port0',
               'scope': 'local',
               'type': 'Contrail:Port',
               'value': {'sdk-object': {'id': params['LeftInterface'],
                 'type': 'Contrail:Port'}}},
              {'name': 'port1',
               'scope': 'local',
               'type': 'Contrail:Port',
               'value': {'sdk-object': {'id': params['RightInterface'],
                 'type': 'Contrail:Port'}}},
              {'name': 'port2',
               'scope': 'local',
               'type': 'Contrail:Port',
               'value': {'sdk-object': {'id': params['MgmtInterface'],
                 'type': 'Contrail:Port'}}}]}
        return port_tuple

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

    #Address group
    def get_add_label_to_ag_template():
        pass
    
    def get_add_subnet_to_ag_template():
        pass
    
    def get_create_global_ag_template():
        pass
    
    def get_create_project_ag_template():
        pass
    
    def get_delete_ag_template():
        pass
    
    def get_remove_label_from_ag_template():
        pass
    
    def get_remove_subnet_from_ag_template():
        pass
    
    #Application Policy Set
    def get_create_global_aps_template():
        pass
    
    def get_create_project_aps_template():
        pass
    
    def get_add_fwp_to_aps_template():
        pass
    
    def get_add_tag_to_aps_template():
        pass
    
    def get_delete_aps_template():
        pass
    
    def get_remove_fwp_from_aps_template():
        pass
    
    def get_remove_tag_from_aps_template():
        pass
    
    #Firewall Policy
    def get_create_global_fwp_template():
        pass
    
    def get_create_project_fwp_template():
        pass
    
    def get_add_rule_to_fwp_template():
        pass
    
    def get_remove_rule_from_fwp_template():
        pass
    
    def get_delete_fwp_template():
        pass
    
    #Firewall rules
    def get_create_project_fw_rule_template():
        pass
    
    def get_create_global_fw_rule_template():
        pass
    
    def get_delete_fw_rule_template():
        pass
    
    def get_edit_fw_rule_template():
        pass
    
    #Service Groups
    def get_create_global_svg_template():
        pass
    
    def get_create_project_svg_template():
        pass
    
    def get_add_service_to_svg_template():
        pass
    
    def get_edit_service_of_svg_template():
        pass
    
    def get_remove_service_from_svg_template():
        pass
    
    def get_delete_svg_template():
        pass
    
    #Tag
    def get_create_global_tag_template():
        pass
    
    def get_create_project_tag_template():
        pass
    
    def get_delete_tag_template():
        pass
    
    #Tag Type
    def get_create_tag_type_template():
        pass
    
    def get_delete_tag_type_template():
        pass

    workflow_name_dict = {
        'create_connection' : 'Create Contrail controller connection',
        'delete_connection' : 'Delete Contrail controller connection',
        #'create_project' : 'Create Project',
        'create_vn' : 'Create virtual network',
        'delete_vn' : 'Delete virtual network',
        'create_policy': 'Create network policy',
        'add_policy_rules': 'Add rule to network policy',
        'remove_policy_rules': 'Remove network policy rule',
        'delete_policy': 'Delete Network policy',
        'add_policy_to_vn': 'Add network policy to virtual network',
        'remove_policy_from_vn': 'Remove network policy from virtual network',
        'edit_vn': 'Edit virtual network',
        'add_ipam_to_vn': 'Add network IPAM to virtual network',
        'add_subnet_to_vn': 'Add subnet to virtual network',
        'add_tag_to_vn': 'Add tag to virtual network',
        'remove_ipam_from_vn': 'Remove network IPAM from virtual network',
        'remove_subnet_from_vn': 'Remove subnet from virtual network',
        'remove_tag_from_vn': 'Remove tag from from virtual network',
        'add_fip_to_port': 'Add floating IP to port',
        'remove_fip_from_port': 'Remove floating IP from port',
        'add_sg_to_port': 'Add security group to port',
        'remove_sg_from_port': 'Remove security group from port',
        'add_shc_to_port': 'Add service health check to port',
        'remove_shc_from_port': 'Remove service health check from port',
        'add_tag_to_port': 'Add tag to port',
        'remove_tag_from_port': 'Remove tag from port',
        'create_fip': 'Create floating IP',
        'delete_fip': 'Delete floating IP',
        'create_fip_pool': 'Create floating IP pool',
        'delete_fip_pool': 'Delete floating IP pool',
        'edit_fip_pool': 'Delete floating IP pool',
        'create_sg': 'Create security group',
        'add_rule_to_sg': 'Add rule to security group',
        'remove_rule_from_sg': 'Remove rule from security group',
        'edit_sg_rule': 'Edit rule of security group',
        'delete_sg': 'Delete security group',
        'create_st': 'Create service template',
        'delete_st': 'Delete service template',
        'create_si': 'Create service instance',
        'delete_si': 'Delete service instance',
        'add_port_tuple': 'Add port tuple to service instance',
        'remove_port_tuple': 'Remove port tuple from service instance',
        'add_label_to_ag': 'Add label to Address Group',
        'add_subnet_to_ag': 'Add subnet to address group',
        'create_global_ag': 'Create global address group',
        'create_project_ag': 'Create address group in project',
        'create_global_ag': 'Create global address group',
        'create_project_ag': 'Create address group in project',
        'delete_ag': 'Delete address group',
        'remove_label_from_ag': 'Remove label from Address Group',
        'remove_subnet_from_ag': 'Remove subnet from address group',
        'create_global_aps': 'Create global application policy set',
        'create_project_aps': 'Create application policy set in project',
        'add_fwp_to_aps': 'Add firewall policy to application policy set',
        'add_tag_to_aps': 'Add tag to application policy set',
        'delete_aps': 'Delete application policy set',
        'remove_fwp_from_aps': 'Remove firewall policy from application policy set',
        'remove_tag_from_aps': 'Remove tag from application policy set',
        'create_global_fwp': 'Create global firewall policy',
        'create_project_fwp': 'Create firewall policy in project',
        'add_rule_to_fwp': 'Add firewall rule to firewall policy',
        'remove_rule_from_fwp': 'Remove rule from firewall policy',
        'delete_fwp': 'Delete firewall policy',
        'create_project_fw_rule': 'Create firewall rule in project',
        'create_global_fw_rule': 'Create global firewall rule',
        'delete_fw_rule': 'Delete firewall rule',
        'edit_fw_rule': 'Edit firewall rule',
        'create_global_svg': 'Create global service group',
        'create_project_svg': 'Create service group in project',
        'add_service_to_svg': 'Add service to service group',
        'edit_service_of_svg': 'Edit service of service group',
        'remove_service_from_svg': 'Remove service from service group',
        'delete_svg': 'Delete service group',
        'create_global_tag': 'Create global tag',
        'create_project_tag': 'Create tag in project',
        'delete_tag': 'Delete tag',
        'create_tag_type': 'Create tag type',
        'delete_tag_type': 'Delete tag type'
        
    }

    workflow_name_template = {
        'create_connection': get_create_connection_template,
        'delete_connection': get_delete_connection_template,
        #'create_poject': get_create_project_template,
        'create_policy': get_create_policy_template,
        'add_policy_rules': get_add_policy_rules_template,
        'remove_policy_rules': get_remove_policy_rules_template,
        'delete_policy': get_delete_policy_template,
        'create_vn': get_create_vn_template,
        'delete_vn': get_delete_vn_template,
        'add_policy_to_vn': get_add_network_policy_to_vn_template,
        'remove_policy_from_vn': get_remove_network_policy_from_vn_template,
        'edit_vn': get_edit_vn_template,
        'add_ipam_to_vn': get_add_ipam_to_vn_template,
        'add_subnet_to_vn': get_add_subnet_to_vn_template,
        'add_tag_to_vn': get_add_tag_to_vn_template,
        'remove_ipam_from_vn': get_remove_ipam_from_vn_template,
        'remove_subnet_from_vn': get_remove_subnet_from_vn_template,
        'remove_tag_from_vn': get_remove_tag_from_vn_template,
        'add_fip_to_port': get_add_fip_to_port_template,
        'remove_fip_from_port': get_remove_fip_from_port_template,
        'add_sg_to_port': get_add_sg_to_port_template,
        'remove_sg_from_port': get_remove_sg_from_port_template,
        'add_shc_to_port': get_add_shc_to_port_template,
        'remove_shc_from_port': get_remove_shc_from_port_template,
        'add_tag_to_port': get_add_tag_to_port_template,
        'remove_tag_from_port': get_remove_tag_from_port_template,
        'create_fip': get_create_fip_template,
        'delete_fip': get_delete_fip_template,
        'create_fip_pool': get_create_fip_pool_template,
        'delete_fip_pool': get_delete_fip_pool_template,
        'edit_fip_pool': get_edit_fip_pool_template,
        'create_sg': get_create_sg_template,
        'add_rule_to_sg': get_add_rule_to_sg_template,
        'remove_rule_from_sg': get_remove_rule_from_sg_template,
        'edit_sg_rule': get_edit_sg_rule_template,
        'edit_sg': get_edit_sg_template,
        'delete_sg': get_delete_sg_template,
        'create_st': get_create_st_template,
        'delete_st': get_delete_st_template,
        'create_si': get_create_si_template,
        'delete_si': get_delete_si_template,
        'add_port_tuple': get_add_port_tuple_template,
        'remove_port_tuple': get_remove_port_tuple_template,
        'add_label_to_ag': get_add_label_to_ag_template,
        'add_subnet_to_ag': get_add_subnet_to_ag_template,
        'create_global_ag': get_create_global_ag_template,
        'create_project_ag': get_create_project_ag_template,
        'delete_ag': get_delete_ag_template, 
        'remove_label_from_ag': get_remove_label_from_ag_template,
        'remove_subnet_from_ag': get_remove_subnet_from_ag_template,
        'create_global_aps': get_create_global_aps_template,
        'create_project_aps': get_create_project_aps_template,
        'add_fwp_to_aps': get_add_fwp_to_aps_template,
        'add_tag_to_aps': get_add_tag_to_aps_template,
        'delete_aps': get_delete_aps_template,
        'remove_fwp_from_aps': get_remove_fwp_from_aps_template,
        'remove_tag_from_aps': get_remove_tag_from_aps_template,
        'create_global_fwp': get_create_global_fwp_template,
        'create_project_fwp': get_create_project_fwp_template,
        'add_rule_to_fwp': get_add_rule_to_fwp_template,
        'remove_rule_from_fwp': get_remove_rule_from_fwp_template,
        'delete_fwp': get_delete_fwp_template,
        'create_project_fw_rule': get_create_project_fw_rule_template,
        'create_global_fw_rule': get_create_global_fw_rule_template,
        'delete_fw_rule': get_delete_fw_rule_template,
        'edit_fw_rule': get_edit_fw_rule_template,
        'create_global_svg': get_create_global_svg_template,
        'create_project_svg': get_create_project_svg_template,
        'add_service_to_svg': get_add_service_to_svg_template,
        'edit_service_of_svg': get_edit_service_of_svg_template,
        'remove_service_from_svg': get_remove_service_from_svg_template,
        'delete_svg': get_delete_svg_template,
        'create_global_tag': get_create_global_tag_template,
        'create_project_tag': get_create_project_tag_template,
        'delete_tag': get_delete_tag_template,
        'create_tag_type': get_create_tag_type_template,
        'delete_tag_type': get_delete_tag_type_template
    }
    
    if __name__ == '__main__':
        param_dict = {'wf_name':'create_connection','host_name':'c54','host_ip':'123','port':123}
        temp = _workflow_name_template[param_dict['wf_name']](param_dict)
        #temp = template(param_dict)
        print(temp)
