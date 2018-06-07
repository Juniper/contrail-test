
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
        self.connection_name = None
    
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
    
    @retry(delay=3, tries=5)
    def verify_wf_status(self,location):
        wf_path = location + 'state'
        result = self.wf_util.get_wf_status(wf_path)
        if result != 'completed':
            self.logger.info('Work flow status %s'%result)
            return False
        self.logger.info('Work flow status %s'%result)
        return True
    
    #WORKFLOWS
    
    #Connection Workflows
    
    def create_connection(self):
        pass
    
    def delete_connection(self):
        pass
    
    #Policy Workflows
    def create_policy(self,name, rules, project='vCenter'):
        wf_name = 'create_policy'
        create_pol = {}
        params = {'policy_name': name}
        params['Project'] = self.get_wf_object_ids(project,'Project')
        create_pol['wf_id'] = self.get_work_flow_id(self.getName(wf_name))
        create_pol['wf_name'] = wf_name
        create_pol.upadte(params)
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(create_pol['wf_id'], payload)
        assert self.verify_wf_status(header['location'])
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
            assert self.verify_wf_status(header['location'])
            
    def delete_policy(self, policy_name):
        wf_name = 'delete_policy'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        pol_id = self.get_wf_object_ids(policy_name,'NetworkPolicy')
        params['NetworkPolicy'] = pol_id
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        self.verify_wf_status(header['location'])
        
        pass
    
    def remove_policy_rules(self):
        pass
    
    #virtual_network_workflows
    def add_network_policy_to_vn(self):
        pass
    
    def remove_network_policy_frmo_vn(self):
        pass
    
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
        self.verify_wf_status(header['location'])
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
        self.verify_wf_status(header['location'])
        if output:
            remove_fip_to_port['output'] = output
    
    def add_sg_to_port(self):
        pass
    
    def remove_sg_from_port(self):
        pass
    
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
        self.verify_wf_status(header['location'])
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
        self.verify_wf_status(header['location'])
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
        self.verify_wf_status(header['location'])
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
        self.verify_wf_status(header['location'])
        if output:
            fip_pool['output'] = output
    
    def edit_fip_pool(self):
        pass
    
    #Security_group Workflows
    
    def create_sg(self, sg_name, rules, project='vCenter'):
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
    
    def edit_sg(self):
        pass
    
    def _add_rule_to_sg(self,create_sg, sg_rules):
        #ether_type:{'IPv4','IPv6'}
        #direction:{ingress,egress}
        #address_type:{'CIDR','Security Group'}
        #protocol{'icmp','tcp',etc}
        #ports:{'any','range(10-20)'
        wf_name = 'add_sg_rules'
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        sg_id = self.get_wf_object_ids(create_sg['sg_name'],'SecurityGroup')
        for rule in rules:
            params = rule
            params['SecurityGroup'] = sg_id
            if rule.get('security_group'):
                params['security_group'] = self.get_wf_object_ids(rule['security_group'],'SecurityGroup')
            if rule.get('ports'):
                if type(rule['ports']) == list and len(rule['ports']) > 1:
                    params['ports'] = str(rule['ports'][0]) + '-' + str(rule['ports'][0])
            payload = self.get_post_body(wf_name, params)
            header,output_params = self.execute(wf_id, payload)
            assert self.verify_wf_status(header['location'])
    
    def remove_rule_from_sg(self):
        pass
    
    def delete_sg(self, sg_name):
        wf_name = 'delete_sg'
        params = {}
        wf_id = self.get_work_flow_id(self.getName(wf_name))
        sg_id = self.get_wf_object_ids(sg_name,'SecurityGroup')
        params['SecurityGroup'] = sg_id
        payload = self.get_post_body(wf_name, params)
        header,output_params = self.execute(wf_id, payload)
        self.verify_wf_status(header['location'])
    
    #Service Template workflows
    def create_st(self,st):
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
        create_st = params
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
    
    def create_si(self):
        pass
    
    def delete_si(self):
        pass
    
    def add_port_tuple_to_si(self):
        pass
    
    def remove_port_tuple_from_si(self):
        pass
     
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

        

