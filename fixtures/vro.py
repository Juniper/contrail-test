from __future__ import division

#from tcutils.vro_api_utils import VroUtilBase
from builtins import str
from builtins import range
from builtins import object
from past.utils import old_div
from tcutils.vro.vro_inspect_utils import VroInspectUtils
from tcutils.vro.templates import WfTemplate
from vcenter import VcenterOrchestrator
from tcutils.util import *
from copy import copy
from netaddr import *

class VroWorkflows(VcenterOrchestrator):
    def __init__(self, inputs, user, pwd, host, port, dc_name, vnc,logger=None):
        super(VroWorkflows,self).__init__(user=user,
                            pwd= pwd,
                            host=host,
                            port=port,
                            dc_name=dc_name,
                            vnc=vnc,
                            inputs=inputs,
                            logger=logger)
        self.inputs = inputs
        self.ip = self.inputs.vro_ip
        self.port = self.inputs.vro_port
        self.vro_user_name = self.inputs.vcenter_username
        self.vro_password = self.inputs.vcenter_password
        self.wf_util = VroInspectUtils(self.ip, self.port, self.vro_user_name, self.vro_password )
        self.wf_template = WfTemplate()
        self.status = None
        self.output_params = None
        self.header = None
        self.connection_name = 'vro'
        self.connection = self._create_connection(self.connection_name,self.inputs.cfgm_ips[0])
        self.project = self.inputs.project_name

    def getName(self, name):
        return self.wf_template.workflow_name_dict[name]

    def getOutputParams(self):
        return self.output_params

    def get_post_body(self,wf_name, params=None):
        return self.wf_template.workflow_name_template[wf_name](self.wf_template, params)

    def get_work_flow_id(self, name):
        return self.wf_util.get_wf_id(name)

    def execute(self, wf_id, payload=None):
        try:
            header,output_params =  self.wf_util.execute(wf_id,payload)
            return header,output_params
        except:
            self.logger.info('Failed to execute %s' %wf_id)

    def get_wf_object_ids(self,name=None,parent_type = None):
        return self.wf_util.get_parent(name,parent_type)

    def get_id(self, res):
        obj_type = res['type'].split(':')[-1]
        id_types = res['value']['sdk-object']['id'].split(',')
        for type in id_types:
            if obj_type in type:
                return type.split(':')[-1]
    
    def get_wf_output(self, location):
        result = self.wf_util.get_wf_output(location)
        if result:
            return [self.get_id(result)]
    
    @retry(delay=3, tries=5)
    def verify_wf_status(self, wf_name, obj_name, location):
        wf_path = location + 'state'
        result = self.wf_util.get_wf_status(wf_path)
        if result != 'completed':
            self.logger.info('%s Workflow %s status %s'%(wf_name,obj_name,result))
            return False
        self.logger.info('%s Workflow %s status %s'%(wf_name,obj_name,result))
        return True

    def get_sg_rules(self, sg_name):
        rules = self.wf_util.get_obj_entry_from_catalog('SecurityGroup', sg_name, 'entriesView')
        #all rules u get as a single string
        #form rules by splitting the string
        rules = rules.split()
        no_of_rules = old_div(len(rules),6)
        sg_rules = []
        for i in range(no_of_rules):
            min = 6*i
            max = 6*(i+1)
            rule = '0: protocol ' + ' '.join(rules[min:min+2]) + ' ports ' + ' '.join(rules[min+2:min+4]) + ' ports ' +  ' '.join(rules[min+4:max])
            sg_rules.append(rule)
        return sg_rules
            
        
    #WORKFLOWS
    
    #Connection Workflows
    
    def _create_connection(self, name, controller, port='8082'):
        try:
            conn_id = self.get_wf_object_ids(name,'Connection')
            if conn_id:
                return conn_id
        except:
            wf_name = 'create_connection'
            wf_id = self.get_work_flow_id(self.getName(wf_name))
            params = {'name': name, 'controller_ip': controller, 'port':port}
            payload = self.get_post_body(wf_name, params)
            header,output_params = self.execute(wf_id, payload)
            assert self.verify_wf_status(wf_name, name, header['location'])
            return self.get_wf_object_ids(name,'Connection')

    def _delete_connection(self, conn_name='vro'):
        wf_name = 'delete_connection'
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        conn_id = self.get_wf_object_ids(conn_name,'Connection')
        params = {'Connection':conn_id}
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        assert self.verify_wf_status(wf_name,conn_name,header['location'])

    #Policy Workflows
    def create_policy(self,name, rules, project='vCenter'):
        wf_name = 'create_policy'
        create_pol = {}
        params = {'policy_name': name}
        params['Project'] = self.get_wf_object_ids(project,'Project')
        create_pol['wf_id'] = self.get_work_flow_id(self.getName(wf_name))
        create_pol['wf_name'] = wf_name
        create_pol.update(params)
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(create_pol['wf_id'], payload)
        result = self.verify_wf_status(wf_name,name,header['location'])
        assert result,'Create policy failed'
        if rules:
            self.add_policy_rules(create_pol,rules)

    def add_policy_rules(self,create_pol, rules):
        wf_name = 'add_policy_rules'
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        pol_id = self.get_wf_object_ids(create_pol['policy_name'],'NetworkPolicy')
        rules_list = copy(rules)
        for rule in rules_list:
            params = {}
            params = rule
            params['NetworkPolicy'] = pol_id
            if rule.get('source_network'):
                if rule['source_network'] == 'any':
                    params['source_network'] = 'any'
                else:
                    rule['source_network'] = rule['source_network'].split(':')[-1]
                    network_id = self.get_wf_object_ids(
                            rule['source_network'],'VirtualNetwork')
                    params['source_network'] = network_id
                params['src_address_type'] = 'Network'
            if rule.get('dest_network'):
                if rule['dest_network'] == 'any':
                    params['dest_network'] = 'any'
                else:
                    rule['dest_network'] = rule['dest_network'].split(':')[-1]
                    network_id = self.get_wf_object_ids(
                            rule['dest_network'],'VirtualNetwork')
                    params['dest_network'] = network_id
                params['dest_address_type'] = 'Network'
            if rule.get('src_ports'):
                if type(rule['src_ports']) == list and len(rule['src_ports']) > 1:
                    params['src_ports'] = str(rule['src_ports'][0]) + '-' + str(rule['src_ports'][1])
            else:
                    params['src_ports'] = 'any'
            if rule.get('dst_ports'):
                if type(rule['dst_ports']) == list and len(rule['dst_ports']) > 1:
                    params['dst_ports'] = str(rule['dst_ports'][0]) + '-' + str(rule['dst_ports'][1])
            else:
                params['dst_ports'] = 'any'
            if rule.get('source_policy'):
                pol_id = self.get_wf_object_ids(
                        rule['source_policy'],'NetworkPolicy')
                params['source_policy'] = pol_id
                params['src_address_type'] = 'Policy'
            if rule.get('dest_policy'):
                pol_id = self.get_wf_object_ids(
                        rule['dest_policy'],'NetworkPolicy')
                params['dest_policy'] = pol_id
                params['dest_address_type'] = 'Policy'
            if rule.get('action_list'):
                if rule['action_list'].get('simple_action'):
                    params['simple_action'] = rule['action_list']['simple_action']
                if rule['action_list'].get('apply_service'):
                    params['ServiceInstance'] = []
                    for si in rule['action_list']['apply_service']:
                        si_name = si.split(':')[-1]
                        si_id = self.get_wf_object_ids(si_name,'ServiceInstance')
                        params['ServiceInstance'].append({'sdk-object': {'id': si_id,
                                                'type': 'Contrail:ServiceInstance'}})
            payload = self.get_post_body(wf_name, params)
            header,output_params = self.execute(wf_id, payload)
            assert self.verify_wf_status(wf_name, create_pol['policy_name'], header['location'])
    
    def delete_policy(self, name):
        wf_name = 'delete_policy'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        pol_id = self.get_wf_object_ids(name,'NetworkPolicy')
        params['NetworkPolicy'] = pol_id
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        assert self.verify_wf_status(wf_name,name,header['location'])
    
    def remove_policy_rules(self):
        pass

    #virtual_network_workflows
    def add_network_policy_to_vn(self, vn_name, policy_names):
        #need to handle if there are more than one policy
        wf_name = 'add_policy_to_vn'
        for policy in policy_names:
            if type(policy) == list:
                policy_name = policy[-1]
            else:
                policy_name = policy
            params = {}
            wf_id = self.get_work_flow_id(self.getName(wf_name))
            vn_id = self.get_wf_object_ids(vn_name,'VirtualNetwork')
            pol_id = self.get_wf_object_ids(policy_name,'NetworkPolicy')
            params['VirtualNetwork'] = vn_id
            params['NetworkPolicy'] = pol_id
            payload = self.get_post_body(wf_name, params)
            header,output_params = self.execute(wf_id, payload)
            assert self.verify_wf_status(wf_name,policy_name,header['location'])

    def remove_network_policy_from_vn(self,vn_name, policy_names):
        wf_name = 'remove_policy_from_vn'
        for policy in policy_names:
            if type(policy) == list:
                policy_name = policy[-1]
            else:
                policy_name = policy
            params = {}
            wf_id = self.get_work_flow_id(self.getName(wf_name))
            vn_id = self.get_wf_object_ids(vn_name,'VirtualNetwork')
            pol_id = self.get_wf_object_ids(policy_name,'NetworkPolicy')
            params['VirtualNetwork'] = vn_id
            params['NetworkPolicy'] = pol_id
            payload = self.get_post_body(wf_name, params)
            header,output_params = self.execute(wf_id, payload)
            assert self.verify_wf_status(wf_name,policy_name,header['location'])

    def edit_virtual_network(self):
        pass
    
    def create_vn_vro(self, vn_name, subnets=None, **kwargs):
        wf_name = 'create_vn'
        vn = kwargs
        params = {'vn_name': vn_name}
        params['Project'] = self.get_wf_object_ids(self.project,'Project')
        vn['wf_id'] = self.get_work_flow_id(self.getName(wf_name))
        vn['wf_name'] = wf_name
        vn.update(params)
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(vn['wf_id'], payload)
        assert self.verify_wf_status(wf_name,vn_name,header['location'])
        if subnets:
            self.add_subnet_to_vn(vn,subnets)
            
    def add_subnet_to_vn(self,vn, subnets):
        wf_name = 'add_subnet_to_vn'
        params={}
        if vn.get('ipam_fq_name'):
            if type(vn['ipam_fq_name']) is string:
                ipam = vn['ipam_fq_name'].split(':')[-1]
            elif type(vn['ipam_fq_name']) is list:
                ipam = vn['ipam_fq_name'][-1]
        else:
            ipam = 'vCenter-ipam'
        params['NetworkIpam'] = self.get_wf_object_ids(ipam,'NetworkIpam')
        params['VirtualNetwork'] = self.get_wf_object_ids(vn['vn_name'],'VirtualNetwork')
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        #if vn.get('enable_dhcp') == False :
            #params['enable_dhcp'] = 'No'
        for subnet in subnets:
            params['subnet'] = subnet['cidr']
            params['gateway'] = IPNetwork(params['subnet'])[1].__str__()
            payload = self.get_post_body(wf_name, params)
            header,output_params = self.execute(wf_id, payload)
            assert self.verify_wf_status(wf_name,subnet['cidr'],header['location'])
    
    def add_tag_to_vn(self,vn_name,tag):
        pass
    
    def delete_tag_from_vn(self,vn_name,tag):
        pass
            
    def delete_vn_vro(self, vn_name):
        wf_name = 'delete_vn'
        vn_id = self.get_wf_object_ids(vn_name,'VirtualNetwork')
        params = {'VirtualNetwork': vn_id}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        assert self.verify_wf_status(wf_name,vn_name,header['location'])
        return True

    #port workflows
    def assoc_floating_ip(self, fip_id, port_id):
        wf_name = 'add_fip_to_port'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        fip = self.get_wf_object_ids(fip_id,'FloatingIp')
        port = self.get_wf_object_ids(port_id,'Port')
        params['FloatingIp'] = fip
        params['Port'] = port   
        payload = self.get_post_body(wf_name, params)
        header,output = self.execute(wf_id, payload)
        assert self.verify_wf_status(wf_name, port_id, header['location'])

    def disassoc_floating_ip(self, fip_id, port_id):
        wf_name = 'remove_fip_from_port'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        fip = self.get_wf_object_ids(fip_id,'FloatingIp')
        port = self.get_wf_object_ids(port_id,'Port')
        params['FloatingIp'] = fip
        params['Port'] = port
        payload = self.get_post_body(wf_name, params)
        header,output = self.execute(wf_id, payload)
        assert self.verify_wf_status(wf_name, port_id, header['location'])

    def add_security_group(self, port_uuid, sg):
        wf_name = 'add_sg_to_port'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        port_id = self.get_wf_object_ids(port_uuid,'Port')
        sg_id = self.get_wf_object_ids(sg,'SecurityGroup')
        params['Port'] = port_id
        params['SecurityGroup'] = sg_id
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        assert self.verify_wf_status(wf_name, port_uuid, header['location'])

    def remove_security_group(self, port_uuid, sg):
        wf_name = 'remove_sg_from_port'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        port_id = self.get_wf_object_ids(port_uuid,'Port')
        sg_id = self.get_wf_object_ids(sg,'SecurityGroup')
        params['Port'] = port_id
        params['SecurityGroup'] = sg_id
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        assert self.verify_wf_status(wf_name, port_uuid, header['location'])
    
    def add_tag_to_port(self,port, type, tag):
        pass
    
    def remove_tag_from_port(self,port, tag):
        pass
    
    def add_shc_to_port(self):
        pass
    
    def remove_shc_from_port(self):
        pass

    #FIP workflows
    def create_floating_ip(self, pool_name, project='vCenter'):
        wf_name = 'create_fip'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        fip_pool_id = self.get_wf_object_ids(pool_name,'FloatingIpPool')
        project_id = self.get_wf_object_ids(project,'Project')
        params['FloatingIpPool'] = fip_pool_id
        params['Project'] = project_id
        payload = self.get_post_body(wf_name, params)
        header,output = self.execute(wf_id, payload)
        assert self.verify_wf_status(wf_name, pool_name, header['location'])
        output = self.get_wf_output(header['location'])
        return output

    def delete_floating_ip(self, fip_id):
        wf_name = 'delete_fip'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        fip = self.get_wf_object_ids(fip_id,'FloatingIp')
        params['FloatingIp'] = fip
        payload = self.get_post_body(wf_name, params)
        header,output = self.execute(wf_id, payload)
        assert self.verify_wf_status(wf_name, fip_id, header['location'])

    #FIP_pool workflows
    def create_fip_pool(self, pool_name, vn):
        wf_name = 'create_fip_pool'
        params = {'pool_name': pool_name}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        network_id = self.get_wf_object_ids(vn,'VirtualNetwork')
        params['VirtualNetwork'] = network_id
        payload = self.get_post_body(wf_name, params)
        header,output = self.execute(wf_id, payload)
        assert self.verify_wf_status(wf_name,pool_name,header['location'])

    def delete_fip_pool(self, pool_name):
        wf_name = 'delete_fip_pool'
        params = {'fip_pool_name': pool_name}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        fip_pool_id = self.get_wf_object_ids(pool_name,'FloatingIpPool')
        params['FloatingIpPool'] = fip_pool_id
        payload = self.get_post_body(wf_name, params)
        header,output = self.execute(wf_id, payload)
        assert self.verify_wf_status(wf_name,pool_name,header['location'])

    def edit_fip_pool(self):
        pass

    #Security_group Workflows

    def create_security_group(self, sg_name, rules, project='vCenter'):
        wf_name = 'create_sg'
        create_sg = {}
        params = {'sg_name': sg_name}
        params['Project'] = self.get_wf_object_ids(project,'Project')
        create_sg['wf_id'] = self.get_work_flow_id(self.getName(wf_name))
        create_sg['wf_name'] = wf_name
        create_sg.update(params)
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(create_sg['wf_id'], payload)
        sg_id = self.verify_wf_status(wf_name,sg_name,header['location'])
        assert sg_id,'Create security group failed'
        if rules:
            self.add_rule_to_sg(sg_name, rules)
        return sg_id

    def edit_sg(self):
        pass
    
    def edit_sg_rule(self,sg_name, sg_rules):
        wf_name = 'edit_sg_rule'
        self.add_edit_sg_rules(wf_name, sg_name, sg_rules)
    
    def set_sg_rules(self, sg_name, sg_rules):
        #remove existing rules and set new rules
        wf_name = 'remove_rule_from_sg'
        rules = self.get_sg_rules(sg_name)
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        sg_id = self.get_wf_object_ids(sg_name,'SecurityGroup')
        for rule in rules:
            params = {}
            params['SecurityGroup'] = sg_id
            params['rule'] = rule
            payload = self.get_post_body(wf_name, params)
            header,output_params = self.execute(wf_id, payload)
            self.verify_wf_status(wf_name, sg_name, header['location'])
        self.add_rule_to_sg(sg_name, sg_rules)
             
    def add_rule_to_sg(self,sg_name, sg_rules):
        wf_name = 'add_rule_to_sg'
        self.add_edit_sg_rules(wf_name, sg_name, sg_rules)

    def add_edit_sg_rules(self,wf_name, sg_name, sg_rules):
        #ether_type:{'IPv4','IPv6'}
        #direction:{ingress,egress}
        #address_type:{'CIDR','Security Group'}
        #protocol{'icmp','tcp',etc}
        #ports:{'any','range(10-20)'
        #if ingress:_security
            #src_add:cidr,securitygroup
            #dst_add:local    
            #take src_ports
        #if eggress:
            #src_add:local
            #dst_add:cidr,sg
            #ports:dst_port
        wf_name = wf_name
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        sg_id = self.get_wf_object_ids(sg_name,'SecurityGroup')
        for rule in sg_rules:
            params = {}
            params['protocol'] = rule['protocol']
            params['SecurityGroup'] = sg_id
            if rule.get('security_group'):
                params['security_group'] = self.get_wf_object_ids(rule['security_group'],'SecurityGroup')
            if rule['src_addresses'][0].get('security_group') == 'local':
                params['direction'] = 'egress'
                if type(rule['src_ports']) == list and len(rule['src_ports']) >= 1:
                    min = rule['dst_ports'][0]['start_port']
                    max = rule['dst_ports'][0]['end_port']
                    max = '65535' if max == -1 else max
                    params['ports'] = str(min) + '-' + str(max)
            else:
                params['direction'] = 'ingress'
                if type(rule['dst_ports']) == list and len(rule['dst_ports']) >= 1:
                    min = rule['dst_ports'][0]['start_port']
                    max = rule['dst_ports'][0]['end_port']
                    max = '65535' if max == -1 else max
                    params['ports'] = str(min) + '-' + str(max)
            if params['direction'] == 'egress':
                for addr in rule['dst_addresses']:
                    if 'subnet' in addr and addr['subnet'] != None:
                        params['addressType'] = 'CIDR'
                        params['address_cidr'] = addr['subnet']['ip_prefix'] + '/' + str(addr['subnet']['ip_prefix_len'])
                        payload = self.get_post_body(wf_name, params)
                        header,output_params = self.execute(wf_id, payload)
                        assert self.verify_wf_status(wf_name, sg_name, header['location'])
                    #need to add addressType = SecurityGroup
            else:
                for addr in rule['src_addresses']:
                    if 'subnet' in addr and  addr['subnet'] != None:
                        params['addressType'] = 'CIDR'
                        params['address_cidr'] = addr['subnet']['ip_prefix'] + '/' + str(addr['subnet']['ip_prefix_len'])
                        payload = self.get_post_body(wf_name, params)
                        header,output_params = self.execute(wf_id, payload)
                        assert self.verify_wf_status(wf_name, sg_name, header['location'])

    def remove_rule_from_sg(self):
        pass

    def delete_security_group(self, sg_name):
        wf_name = 'delete_sg'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        sg_id = self.get_wf_object_ids(sg_name,'SecurityGroup')
        params['SecurityGroup'] = sg_id
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        self.verify_wf_status(wf_name,sg_name,header['location'])

    #Service Template workflows
    def create_st(self, st):
        #parent:Connection
        #service_mode:{'transparent','in_network','in_network_nat'}
        #service_type:{'firewall','analyzer'}
        #virtualization_type:{'physical','virtual_machine'}
        #vrouter_instance_type:{'livbirt-qemu','docker'}
        wf_name = 'create_st'
        create_st = {}
        params = st
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        params['Connection'] = self.get_wf_object_ids(self.connection_name,'Connection')
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        self.verify_wf_status(wf_name,st['st_name'],header['location'])

    def delete_st(self, st_name):
        wf_name = 'delete_st'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        st_id = self.get_wf_object_ids(st_name,'ServiceTemplate')
        params['ServiceTemplate'] = st_id
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        self.verify_wf_status(wf_name,st_name,header['location'])

    #Service Instance Workflows

    def create_si(self, si_name, st_name, if_details, project='vCenter'):
        wf_name = 'create_si'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        project_id = self.get_wf_object_ids(project,'Project')
        st_id = self.get_wf_object_ids(st_name.name,'ServiceTemplate')
        params['Project'] = project_id
        params['ServiceTemplate'] = st_id
        params['si_name'] = si_name
        for itf in list(if_details.keys()):
                if itf == 'left':
                    left_vn_name = if_details['left']['vn_name'].split(':')[-1]
                    left_vn_id = self.get_wf_object_ids(left_vn_name,'VirtualNetwork')
                    params['LeftVirtualNetwork'] = left_vn_id
                    
                elif itf == 'right':
                    right_vn_name = if_details['right']['vn_name'].split(':')[-1]
                    right_vn_id = self.get_wf_object_ids(right_vn_name,'VirtualNetwork')
                    params['RightVirtualNetwork'] = right_vn_id
                elif itf == 'management':
                    mgmt_vn_name = if_details['management']['vn_name'].split(':')[-1]
                    mgmt_vn_id = self.get_wf_object_ids(mgmt_vn_name,'VirtualNetwork')
                    params['MgmtVirtualNetwork'] = mgmt_vn_id
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        self.verify_wf_status(wf_name,si_name,header['location'])

    def delete_si(self, si_name):
        wf_name = 'delete_si'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        si_id = self.get_wf_object_ids(si_name,'ServiceInstance')
        params['ServiceInstance'] = si_id
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        self.verify_wf_status(wf_name,si_name,header['location'])

    def add_port_tuple(self, si_name, if_details, pt_details):
        wf_name = 'add_port_tuple'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        si_id = self.get_wf_object_ids(si_name,'ServiceInstance')
        params['pt_name'] = pt_details['name']
        params['ServiceInstance'] = si_id
        si_id_only = si_id.split(',')[-1]
        for itf in pt_details:
                if itf == 'left':
                    left_vn_name = if_details['left']['vn_name'].split(':')[-1]
                    left_vn_id = self.get_wf_object_ids(left_vn_name,'VirtualNetwork')
                    left_vn_id = left_vn_id.split(',')[-1]
                    left_intf = pt_details['left']
                    left_intf_id = self.get_wf_object_ids(left_intf,'Port')
                    params['LeftInterface'] = ','.join([left_intf_id,si_id_only,left_vn_id])
                elif itf == 'right':
                    right_vn_name = if_details['right']['vn_name'].split(':')[-1]
                    right_vn_id = self.get_wf_object_ids(right_vn_name,'VirtualNetwork')
                    right_vn_id = right_vn_id.split(',')[-1]
                    right_intf = pt_details['right']
                    right_intf_id = self.get_wf_object_ids(right_intf,'Port')
                    params['RightInterface'] = ','.join([right_intf_id,si_id_only,right_vn_id])
                elif itf == 'management':
                    mgmt_vn_name = if_details['management']['vn_name'].split(':')[-1]
                    mgmt_vn_id = self.get_wf_object_ids(mgmt_vn_name,'VirtualNetwork')
                    mgmt_vn_id = mgmt_vn_id.split(',')[-1]
                    mgmt_intf = pt_details['management']
                    mgmt_intf_id = self.get_wf_object_ids(mgmt_intf,'Port')
                    params['MgmtInterface'] = ','.join([mgmt_intf_id,si_id_only,mgmt_vn_id])
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        self.verify_wf_status(wf_name,params['pt_name'],header['location'])

    def remove_port_tuple(self, si_name, pt_details):
        wf_name = 'remove_port_tuple'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        pt_id = self.get_wf_object_ids(pt_details['name'],'PortTuple')
        si_id = self.get_wf_object_ids(si_name,'ServiceInstance')
        params['PortTuple'] = pt_id
        params['ServiceInstance'] = si_id
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        self.verify_wf_status(wf_name,pt_details['name'],header['location'])
    
    #contrail security 
    def create_ag(self, ag, scope='global', project = 'vCenter'):
        params['ag_name'] = ag
        if scope == 'local':
            wf_name = 'create_project_ag'
            params['Project'] = self.get_wf_object_ids(project,'Project')
        else:
            wf_name = 'create_local_ag'
            params['Connection'] = self.get_wf_object_ids(self.connection_name,'Connection')
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        self.verify_wf_status(wf_name,name,header['location'])
            
    def add_label_to_ag(self,):
        pass
    
    def add_subnet_to_ag():
        pass
    
    #def create_global_ag():
    #    pass
    
    #def create_project_ag():
    #    pass
    
    def delete_ag():
        pass
    
    def remove_label_from_ag():
        pass
    
    def remove_subnet_from_ag():
        pass
    
    def create_global_aps():
        pass
    
    def create_project_aps():
        pass
    
    def add_fwp_to_aps():
        pass
    
    def add_tag_to_aps():
        pass
    
    def delete_aps():
        pass
    
    def remove_fwp_from_aps():
        pass
    
    def remove_tag_from_aps():
        pass
    
    def create_global_fwp():
        pass
    
    def create_project_fwp():
        pass
    
    def add_rule_to_fwp():
        pass
    
    def remove_rule_from_fwp():
        pass
    
    def delete_fwp():
        pass
    
    def create_project_fw_rule():
        pass
    
    def create_global_fw_rule():
        pass
    
    def delete_fw_rule():
        pass
    
    def edit_fw_rule():
        pass
    
    def create_global_svg():
        pass
    
    def create_project_svg():
        pass
    
    def add_service_to_svg():
        pass
    
    def edit_service_of_svg():
        pass
    
    def remove_service_from_svg():
        pass
    
    def delete_svg():
        pass
    
    def create_global_tag():
        pass
    
    def create_project_tag():
        pass
    
    def delete_tag():
        pass
    
    def create_tag_type():
        pass
    
    def delete_tag_type():
        pass

class Inputs(object):
    def __init__(self):
        self.user = 'administrator@vsphere.local'
        self.pwd = 'Contrail123!'

def main():
    '''name = 'create_policy'
    inputs = Inputs()
    params = {'host_name':'nodec545454','host_ip':'nodec54','port':8082}
    wf = WorkflowBase(inputs,'10.204.217.125', '8281', name, params)'''
    #wf_name = 'create_policy'
    wf_name = 'add_policy_rules'
    inputs = Inputs()
    #params[id]: Contrail:NetworkPolicy='Controller,NetworkPolicy:12eacd94-XX-XX,
    #params['action']
    #params['protocol']
    #params['direction']='>,<>'
    #params['src_address_type']='Network,cidr,policy'
    #params = {'host_name':'nodec545454','host_ip':'nodec54','port':8082}
    wf = WorkflowBase(inputs,'10.204.217.125', '8281', wf_name)
    params = {'action':'pass','protocol':'any','direction':'>','src_address_type':'Network'}
    params.update(wf.get_wf_object_ids('test_policy','NetworkPolicy'))
    import pdb;pdb.set_trace()
    wf.execute(params)
if __name__ == '__main__' :
  main()
