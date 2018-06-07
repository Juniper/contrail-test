
#from tcutils.vro_api_utils import VroUtilBase
from tcutils.vro.vro_inspect_utils import VroInspectUtils
from tcutils.vro.templates import WfTemplate
from vcenter import VcenterOrchestrator
from tcutils.util import *

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
        #self.wf_name = wf_name
        self.vro_user_name = self.inputs.vcenter_username
        self.vro_password = self.inputs.vcenter_password
        #self.params = params
        #self.api_url = BaseApiUrl(ip, port,'/vco/api/workflows/')
        self.wf_util = VroInspectUtils(self.ip, self.port, self.vro_user_name, self.vro_password )
        #self.wf_id = self.get_work_flow_id()
        self.wf_template = WfTemplate()
        #self.vco_user_name = useri  #self.inputs.vco_user_name
        #self.vco_password = pwd  #self.inputs.vco_password
        self.status = None
        self.output_params = None
        self.header = None
        self.connection = self._create_connection('vro',self.inputs.cfgm_ips[0])
        
    
    def getName(self, name):
        return self.wf_template.workflow_name_dict[name]
    
    def getOutputParams(self):
        return self.output_params
    
    def get_post_body(self,wf_name, params=None):
        return self.wf_template.workflow_name_template[wf_name](params)
    
    def get_work_flow_id(self, name): 
        return self.wf_util.get_wf_id(name)
    
    def execute(self, wf_id, payload=None):
        header,output_params =  self.wf_util.execute(wf_id,payload)
        return header,output_params
    
    def get_wf_object_ids(self,name=None,parent_type = None):
        return self.wf_util.get_parent(name,parent_type)
    
    def get_object_id(self, output, type=None):
        object_id = output['value']['sdk-object']['id']
        object_id = id.split(',')
        for id in object:
            if type in id:
                return id.split(':')[1]
        
    
    @retry(delay=3, tries=5)
    def verify_wf_status(self, wf_name, obj_name, location):
        wf_path = location + 'state'
        result = self.wf_util.get_wf_status(wf_path)
        if result != 'completed':
            self.logger.info('%s Workflow %s status %s'%(wf_name,obj_name,result))
            return False
        self.logger.info('%s Workflow %s status %s'%(wf_name,obj_name,result))
        return True
    
    #WORKFLOWS
    
    #Connection Workflows
    
    def _create_connection(self, name, controller, port='8082'):
        conn_id = self.get_wf_object_ids(name,'Connection')
        if conn_id:
            return conn_id
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
        assert self.verify_wf_status(wf_name,name,header['location'])
        if rules:
            self.add_policy_rules(create_pol,rules)
        
    
    def add_policy_rules(self,create_pol, rules):
        wf_name = 'add_policy_rules'
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        pol_id = self.get_wf_object_ids(create_pol['policy_name'],'NetworkPolicy')
        for rule in rules:
            params = rule
            params['NetworkPolicy'] = pol_id
            if rule.get('source_network'):
                network_id = self.get_wf_object_ids(
                        rule['source_network'],'VirtualNetwork')
                params['source_network'] = network_id
                params['src_address_type'] = 'Network'
            if rule.get('dest_network'):
                network_id = self.get_wf_object_ids(
                        rule['dest_network'],'VirtualNetwork')
                params['dest_network'] = network_id
                params['dest_address_type'] = 'Network'
            if rule.get('src_ports'):
                if type(rule['src_ports']) == list and len(rule['src_ports']) > 1:
                    params['src_ports'] = str(rule['src_ports'][0]) + '-' + str(rule['src_ports'][0])
                #else:
                #    params['src_ports'] = rule['src_ports']
            if rule.get('dst_ports'):
                if type(rule['dst_ports']) == list and len(rule['dst_ports']) > 1:
                    params['dst_ports'] = str(rule['dst_ports'][0]) + '-' + str(rule['dst_ports'][0])
                #else:
                #    params['dst_ports'] = rule['dst_ports']
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
            policy_name = policy.split(':')[-1]
            params = {}
            wf_id = self.get_work_flow_id(self.getName(wf_name))
            vn_id = self.get_wf_object_ids(policy_name,'VirtualNetwork')
            pol_id = self.get_wf_object_ids(vn_name,'NetworkPolicy')
            params['VirtualNetwork'] = pol_id
            params['NetworkPolicy'] = pol_id
            payload = self.get_post_body(wf_name, params)
            header,output_params = self.execute(wf_id, payload)
            assert self.verify_wf_status(wf_name,name,header['location'])
    
    
    def remove_network_policy_from_vn(self,vn_name, policy_names):
        wf_name = 'remove_policy_from_vn'
        for policy in policy_names:
            policy_name = policy.split(':')[-1]
            params = {}
            wf_id = self.get_work_flow_id(self.getName(wf_name))
            pol_id = self.get_wf_object_ids(name,'NetworkPolicy')
            params['NetworkPolicy'] = pol_id
            payload = self.get_post_body(wf_name, params)
            header,output_params = self.execute(wf_id, payload)
            assert self.verify_wf_status(wf_name,name,header['location'])
    
    def edit_virtual_network(self):
        pass
    
    #port workflows
    def add_fip_to_port(self, port_uuid, fip_uuid):
        add_fip_to_port = {}
        wf_name = 'add_fip_to_port'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        fip_id = self.get_wf_object_ids(fip,'FloatingIp')
        port_id = self.get_wf_object_ids(port,'Port')
        params['FloatingIp'] = fip_id
        params['Port'] = port_id
        add_fip_to_port = params
        payload = self.get_post_body(wf_name, params)
        header,output = self.execute(wf_id, payload)
        assert self.verify_wf_status(wf_name, header['location'])
        if output:
            add_fip_to_port['output'] = output
    
    def remove_fip_from_port(self, port_uuid, fip_uuid):
        remove_fip_from_port = {}
        wf_name = 'remove_fip_from_port'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        fip_id = self.get_wf_object_ids(fip,'FloatingIp')
        port_id = self.get_wf_object_ids(port,'Port')
        params['FloatingIp'] = fip_id
        params['Port'] = port_id
        remove_fip_to_port = params
        payload = self.get_post_body(wf_name, params)
        header,output = self.execute(wf_id, payload)
        assert self.verify_wf_status(header['location'])
        if output:
            remove_fip_to_port['output'] = output
    
    def add_sg_to_port(self, port_uuid, sg):
        wf_name = 'add_sg_to_port'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        port_id = self.get_wf_object_ids(policy_name,'Port')
        sg_id = self.get_wf_object_ids(vn_name,'SecurityGroup')
        params['Port'] = port_id
        params['SecurityGroup'] = sg_id
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        assert self.verify_wf_status(wf_name,name,header['location'])
    
    def remove_sg_from_port(self, port_uuid, sg):
        wf_name = 'remove_sg_from_port'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        port_id = self.get_wf_object_ids(policy_name,'Port')
        sg_id = self.get_wf_object_ids(vn_name,'SecurityGroup')
        params['Port'] = port_id
        params['SecurityGroup'] = sg_id
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        assert self.verify_wf_status(wf_name,name,header['location'])
    
    #FIP workflows
    def create_fip(self, pool_name, project='vCenter'):
        wf_name = 'create_fip'
        fip = {}
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        fip_pool_id = self.get_wf_object_ids(pool_name,'FloatingIpPool')
        project_id = self.get_wf_object_ids(project,'Project')
        params['FloatingIpPool'] = fip_pool_id
        params['Project'] = project_id
        fip = params
        payload = self.get_post_body(wf_name, params)
        header,output = self.execute(wf_id, payload)
        assert self.verify_wf_status(header['location'])
        if output:
            fip_pool['output'] = output
    
    def delete_fip(self, fip_id):
        wf_name = 'delete_fip'
        fip = {}
        params = {}
        if not fip:
            #fetch fip
            pass
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        fip_id = self.get_wf_object_ids(fip_id,'FloatingIp')
        params['FloatingIp'] = fip_id
        fip = params
        payload = self.get_post_body(wf_name, params)
        header,output = self.execute(wf_id, payload)
        assert self.verify_wf_status(header['location'])
        if output:
            fip_pool['output'] = output
        pass
    
    #FIP_pool workflows
    def create_fip_pool(self, pool_name, vn_name):
        wf_name = 'create_fip_pool'
        fip_pool = {}
        params = {'fip_pool_name': pool_name}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        network_id = self.get_wf_object_ids(vn_name,'VirtualNetwork')
        params['VirtualNetwork'] = network_id
        fip_pool = params
        payload = self.get_post_body(wf_name, params)
        header,output = self.execute(wf_id, payload)
        assert self.verify_wf_status(header['location'])
        if output:
            fip_pool['output'] = output
    
    def delete_fip_pool(self, pool_name):
        wf_name = 'delete_fip_pool'
        fip_pool = {}
        params = {'fip_pool_name': pool_name}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        fip_pool_id = self.get_wf_object_ids(vn_name,'FloatingIpPool')
        params['FloatingIpPool'] = fip_pool_id
        fip_pool = params
        payload = self.get_post_body(wf_name, params)
        header,output = self.execute(wf_id, payload)
        assert self.verify_wf_status(header['location'])
        if output:
            fip_pool['output'] = output
    
    def edit_fip_pool(self):
        pass
    
    #Security_group Workflows
    
    def create_security_group(self, sg_name, rules, project='vCenter'):
        wf_name = 'create_sg'
        create_sg = {}
        params = {'sg_name': name}
        params['Project'] = self.get_wf_object_ids(project,'Project')
        create_sg['wf_id'] = self.get_work_flow_id(self.getName(wf_name))
        create_sg['wf_name'] = wf_name
        create_sg.update(params)
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(create_sg['wf_id'], payload)
        assert self.verify_wf_status(header['location'])
        if rules:
            self.add_sg_rules(create_sg, rules)
        if output_params:
            sg_id = self.get_object_id(output_params, 'SecurityGroup')
            
    def edit_sg(self):
        pass
    
    def add_rule_to_sg(self,create_sg, sg_rules):
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
        wf_name = 'add_sg_rules'
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        sg_id = self.get_wf_object_ids(create_sg['sg_name'],'SecurityGroup')
        for rule in rules:
            params = {}
            params['protocol'] = rule['protocol']
            
            params['SecurityGroup'] = sg_id
            if rule.get('security_group'):
                params['security_group'] = self.get_wf_object_ids(rule['security_group'],'SecurityGroup')
            if rule['src_addresses'][0].get('security_group') == 'local':
                params['direction'] = 'egress'
                if type(rule['src_ports']) == list and len(rule['src_ports']) > 1:
                    min = rule['dst_ports'][0]['start_port']
                    max = rule['dst_ports'][0]['end_port']
                    max = '65535' if max == -1 else max
                    params['ports'] = str(min) + '-' + str(max)
            else:
                params['direction'] = 'ingress'
                if type(rule['dst_ports']) == list and len(rule['dst_ports']) > 1:
                    min = rule['dst_ports'][0]['start_port']
                    max = rule['dst_ports'][0]['end_port']
                    max = '65535' if max == -1 else max
                    params['ports'] = str(min) + '-' + str(max)
            if params['direction'] == 'egress':
                for addr in rule['dst_addresses']:
                    if addr.has_key('subnet') and addr['subnet'] != None:
                        params['addressType'] = 'CIDR'
                        params['address_cidr'] = addr['subnet']['ip_prefix'] + '/' + str(addr['subnet']['ip_prefix_len'])
                        payload = self.get_post_body(wf_name, params)
                        header,output_params = self.execute(wf_id, payload)
                        assert self.verify_wf_status(header['location'])
                    #need to add addressType = SecurityGroup
            else:
                for addr in rule['src_addresses']:
                    if addr.has_key('subnet') and  addr['subnet'] != None:
                        params['addressType'] = 'CIDR'
                        params['address_cidr'] = addr['subnet']['ip_prefix'] + '/' + str(addr['subnet']['ip_prefix_len'])
                        payload = self.get_post_body(wf_name, params)
                        header,output_params = self.execute(wf_id, payload)
                        assert self.verify_wf_status(header['location'])
    
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
        self.verify_wf_status(header['location'])
    
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
        self.verify_wf_status(header['location'])
    
    def delete_st(self, st_name):
        wf_name = 'delete_st'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        st_id = self.get_wf_object_ids(st_name,'ServiceTemplate')
        params['ServiceTemplate'] = st_id
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        self.verify_wf_status(header['location'])
    
    #Service Instance Workflows
    
    def create_si(self, si_name, st_name, if_details, project='vCenter'):
        wf_name = 'create_si'
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        project_id = self.get_wf_object_ids(project,'Project')
        st_id = self.get_wf_object_ids(st_name,'ServiceTemplate')
        params['Project'] = project_id
        params['ServiceTemplate'] = st_id
        params['si_name'] = si_name
        for itf in self.if_details:
                virtual_network = None
                if itf == 'left':
                    params['LeftVirtualNetwork'] = left_vn_name
                elif itf == 'right':
                    params['RightVirtualNetwork'] = right_vn_name
                elif itf == 'management':
                    params['MgmtVirtualNetwork'] = mgmt_vn_name
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        assert self.verify_wf_status(header['location'])
    
    def delete_si(self, si_name):
        wf_name = 'delete_si'
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        si_id = self.get_wf_object_ids(si_name,'ServiceInstance')
        params['ServiceInstance'] = si_id
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        assert self.verify_wf_status(header['location'])
    
    def add_port_tuple(self, si_name, pt_details):
        wf_name = 'add_port_tuple'
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        si_id = self.get_wf_object_ids(si_name,'ServiceInstance')
        params['pt_name'] = pt_details['name']
        params['ServiceInstance'] = si_id
        for itf in self.if_details:
                if itf == 'left':
                    params['LeftInterface'] = left_vn_name
                elif itf == 'right':
                    params['RightInterface'] = right_vn_name
                elif itf == 'management':
                    params['MgmtInterface'] = mgmt_vn_name
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        assert self.verify_wf_status(header['location'])
    
    def remove_port_tuple(self, si_name, pt_details):
        wf_name = 'remove_port_tuple'
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        pt_id = self.get_wf_object_ids(pt_details['name'],'PortTuple')
        si_id = self.get_wf_object_ids(si_name,'ServiceInstance')
        params['PortTuple'] = pt_id
        params['ServiceInstance'] = si_id
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        assert self.verify_wf_status(header['location'])
     
class Inputs():
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

        

