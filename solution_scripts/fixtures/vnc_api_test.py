from vnc_api.vnc_api import *

class VncLibHelper():

    def __init__(self, domain, project, cfgm_ip, api_port, inputs, username='admin', password='contrail123', auth_host=None):
        self.project = project
        self.domain = domain
        self.inputs = inputs
        self.logger = inputs.logger
        self.obj = VncApi(
            username=username, password=password, tenant_name=self.project,
            api_server_host=cfgm_ip, api_server_port=api_port, auth_host=auth_host)

    def get_handle(self):
        return self.obj
    # end get_handle

    def project_read(self, id=None, fq_name=None):
        return self.obj.project_read(id=id, fq_name=fq_name)

    def get_forwarding_mode(self, vn_fq_name):
        vnc_lib = self.obj
        # Figure out VN
        vni_list = vnc_lib.virtual_networks_list(
            parent_fq_name=self.project)['virtual-networks']
        for vni_record in vni_list:
            if (vni_record['fq_name'][0] == vn_fq_name.split(":")[0] and
                vni_record['fq_name'][1] == vn_fq_name.split(":")[1] and
                    vni_record['fq_name'][2] == vn_fq_name.split(":")[2]):
                vni_obj = vnc_lib.virtual_network_read(id=vni_record['uuid'])
                vni_obj_properties = vni_obj.get_virtual_network_properties()
                if vni_obj_properties:
                    fw_mode = vni_obj_properties.get_forwarding_mode()
                else:
                    fw_mode = None
                return fw_mode
    # end get_forwarding_mode

    def get_vn_subnet_dhcp_flag(self, vn_fq_name):
        vnc_lib = self.obj
        # Figure out VN
        vni_list = vnc_lib.virtual_networks_list(
            parent_fq_name=self.project)['virtual-networks']
        for vni_record in vni_list:
            if (vni_record['fq_name'][0] == vn_fq_name.split(":")[0] and
                vni_record['fq_name'][1] == vn_fq_name.split(":")[1] and
                    vni_record['fq_name'][2] == vn_fq_name.split(":")[2]):
                vni_obj = vnc_lib.virtual_network_read(id=vni_record['uuid'])
                subnets = vni_obj.network_ipam_refs[0]['attr']
                ipam = subnets.get_ipam_subnets()
                enable_dhcp = ipam[0].get_enable_dhcp()
                return enable_dhcp

    # get_vn_subnet_dhcp_flag

    def set_rpf_mode(self, vn_fq_name, mode):
        vnc_lib = self.obj
        # Figure out VN
        vni_list = vnc_lib.virtual_networks_list(
            parent_fq_name=self.project)['virtual-networks']
        for vni_record in vni_list:
            if (vni_record['fq_name'][0] == vn_fq_name.split(":")[0] and
                vni_record['fq_name'][1] == vn_fq_name.split(":")[1] and
                    vni_record['fq_name'][2] == vn_fq_name.split(":")[2]):
                vni_obj = vnc_lib.virtual_network_read(id=vni_record['uuid'])
                vni_obj_properties = vni_obj.get_virtual_network_properties() or VirtualNetworkType()
                vni_obj_properties.set_rpf(mode)
                vni_obj.set_virtual_network_properties(vni_obj_properties)
                vnc_lib.virtual_network_update(vni_obj)

    # end set_rpf_mode

    def id_to_fq_name(self, id):
        return self.obj.id_to_fq_name(id)

    def security_group_read(self, sg_name):
        sg_fq_name = [self.domain, self.project, sg_name]
        return self.obj.security_group_read(fq_name=sg_fq_name)

    def get_sg_rules(self, sg_name):
        sg_obj = self.security_group_read(sg_name)
        try:
            rules = sg_obj.get_security_group_entries().get_policy_rule()
        except AttributeError:
            self.logger.warn('Unable to fetch rules from SG %s'%sg_name)
            rules = list()
        return rules

    def set_sg_rules(self, sg_name, rules):
        rule_list = PolicyEntriesType(policy_rule=rules)
        sg_obj = self.security_group_read(sg_name)
        sg_obj.set_security_group_entries(rule_list)
        self.obj.security_group_update(sg_obj)

