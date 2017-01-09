import fixtures
from vnc_api.vnc_api import *
from tcutils.util import retry

try:
    from webui_test import *
except ImportError:
    pass

class SecurityGroupFixture(fixtures.Fixture):

    def __init__(self, connections, secgrp_name,
	         secgrp_id=None, secgrp_entries=None, option='neutron'):
	#option <'neutron' or 'contrail'>
        self.connections = connections
        self.inputs = self.connections.inputs
        self.logger = self.inputs.logger
        self.domain_name = self.inputs.domain_name
        self.project_name = self.inputs.project_name
        self.secgrp_name = secgrp_name
        self.secgrp_id = secgrp_id
        self.secgrp_rules = secgrp_entries
        self.secgrp_entries = PolicyEntriesType(secgrp_entries)
        self.already_present = False
        self.domain_fq_name = [self.domain_name]
        self.project_fq_name = [self.domain_name, self.project_name]
        self.secgrp_fq_name = [self.domain_name,
                               self.project_name, self.secgrp_name]
        self.secgrp_rule_q = []
        self.option = option
        if self.inputs.verify_thru_gui():
            self.webui = WebuiTest(self.connections, self.inputs)
        if self.option == 'neutron':
            self.quantum_h = self.connections.get_network_h()
        self.vnc = self.connections.get_vnc_lib_h().get_handle()

    def setUp(self):
        self.logger.debug("Creating Security group: %s", self.secgrp_fq_name)
        super(SecurityGroupFixture, self).setUp()
        sec_grp_check = self.sec_grp_exist()
        if sec_grp_check:
            self.already_present = True
            self.logger.info(
                'Security group  %s already present, not creating security group' %
                (self.secgrp_name))
        else:
            if self.option == 'neutron':
                secgrp_q = self.quantum_h.create_security_group(self.secgrp_name)
                if not secgrp_q:
                    self.logger.error("security group creation failed through quantum")
                    return False
                self.secgrp_id = secgrp_q['id']
                self.delete_default_egress_rule(self.secgrp_id)
                secgrp_rules = self.create_sg_rule_quantum(self.secgrp_id,secgrp_rules=self.secgrp_rules)
                if not secgrp_rules:
                    return False
            elif self.inputs.is_gui_based_config():
                self.webui.create_security_group(self)
            else:
                obj = SecurityGroup(name=self.secgrp_name,
                                    parent_type='project',
                                    fq_name=self.secgrp_fq_name,
                                    security_group_id=self.secgrp_id,
                                    security_group_entries=self.secgrp_entries)
                self.vnc.security_group_create(obj)
                self.obj = self.vnc.security_group_read(id=obj.uuid)
                self.secgrp_id = self.obj.uuid
            self.logger.info("Created security-group name:%s" %
                             self.secgrp_name)

    def get_uuid(self):
        return self.secgrp_id

    def delete_default_egress_rule(self, sg_id):
        #currently this method can be only used before adding any custom rule to sg
        rules = self.quantum_h.list_security_group_rules(
                                tenant_id=self.quantum_h.project_id)
        for rule in rules['security_group_rules']:
            if rule['security_group_id'] == sg_id and rule['remote_ip_prefix'] == '0.0.0.0/0':
                self.quantum_h.delete_security_group_rule(rule['id'])
                break

    def delete_all_rules(self, sg_id):
        #deletes all the rules of the sg sg_id
        rules = self.quantum_h.list_security_group_rules(
                                tenant_id=self.quantum_h.project_id)
        for rule in rules['security_group_rules']:
            if rule['security_group_id'] == sg_id:
                self.quantum_h.delete_security_group_rule(rule['id'])

    def create_sg_rule_quantum(self, sg_id, secgrp_rules=None):
        if secgrp_rules:
            for rule in secgrp_rules:
                remote_group_id=None;remote_ip_prefix=None
                if rule['protocol'] == 'any':
                    proto = None
                else:
                    proto = rule['protocol']
                if rule['src_addresses'][0].has_key('security_group'):
                    if rule['src_addresses'][0]['security_group'] == 'local':
                        direction = 'egress'
                        port_range_min = rule['src_ports'][0]['start_port']
                        port_range_max = rule['src_ports'][0]['end_port']
                    else:
                        if rule['dst_addresses'][0]['security_group'] != None:
                            remote_group_id = get_secgrp_id_from_name(
                                                        self.connections,
                                                        rule['src_addresses'][0]['security_group'])
                if rule['dst_addresses'][0].has_key('security_group'):
                    if rule['dst_addresses'][0]['security_group'] == 'local':
                        direction = 'ingress'
                        port_range_min = rule['dst_ports'][0]['start_port']
                        port_range_max = rule['dst_ports'][0]['end_port']
                    else:
                        if rule['dst_addresses'][0]['security_group'] != None:
                            remote_group_id = get_secgrp_id_from_name(
                                                        self.connections,
                                                        rule['dst_addresses'][0]['security_group'])
                if (port_range_min == 0 and port_range_max == -1) \
                    or (port_range_min == 0 and port_range_max == 65535):
                    port_range_min = None;port_range_max = None
                if direction == 'ingress':
                    try:
                        for addr in rule['src_addresses']:
                            if addr.has_key('subnet') and  addr['subnet'] != None:
                                remote_ip_prefix = addr['subnet']['ip_prefix'] + '/' + str(addr['subnet']['ip_prefix_len'])
                                rule_dict = self.quantum_h.create_security_group_rule(
                                                 sg_id,direction=direction,
                                                 port_range_min=port_range_min,
                                                 port_range_max=port_range_max,
                                                 protocol=proto,
                                                 remote_group_id=remote_group_id,
                                                 remote_ip_prefix=remote_ip_prefix)
                                if rule_dict:
                                    self.secgrp_rule_q.append(rule_dict)
                                else:
                                    return False
                    except:
                        self.logger.error("error while creating sg rule through quantum")
                        return False
                if direction == 'egress':
                    try:
                        for addr in rule['dst_addresses']:
                            if addr.has_key('subnet') and addr['subnet'] != None:
                                remote_ip_prefix = addr['subnet']['ip_prefix'] + '/' + str(addr['subnet']['ip_prefix_len'])
                                rule_dict = self.quantum_h.create_security_group_rule(
                                                 sg_id,direction=direction,
                                                 port_range_min=port_range_min,
                                                 port_range_max=port_range_max,
                                                 protocol=proto,
                                                 remote_group_id=remote_group_id,
                                                 remote_ip_prefix=remote_ip_prefix)
                                if rule_dict:
                                    self.secgrp_rule_q.append(rule_dict)
                                else:
                                    return False
                    except:
                        self.logger.error("error while creating sg rule through quantum")
                        return False
                #when remote is security group
                if remote_group_id:
                    rule_dict = self.quantum_h.create_security_group_rule(
                                            sg_id,direction=direction,
                                            port_range_min=port_range_min,
                                            port_range_max=port_range_max,
                                            protocol=proto,
                                            remote_group_id=remote_group_id,
                                            remote_ip_prefix=remote_ip_prefix)
                    if rule_dict:
                        self.secgrp_rule_q.append(rule_dict)
                    else:
                        return False

            return True

    def cleanUp(self):
        super(SecurityGroupFixture, self).cleanUp()
        self.delete()

    def delete(self):
        self.logger.debug("Deleting Security group: %s", self.secgrp_fq_name)
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if self.already_present:
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if do_cleanup:
            if self.option == 'neutron':
                self.quantum_h.delete_security_group(self.secgrp_id)
            elif self.inputs.is_gui_based_config():
                self.webui.delete_security_group(self)
            else:
                self.vnc.security_group_delete(id=self.secgrp_id)
            result, msg = self.verify_on_cleanup()
            assert result, msg
        else:
            self.logger.info('Skipping deletion of security_group %s' %
                             (self.secgrp_fq_name))

    def add_rule(self, rule):
        """Add a rule to this security group."""
        pass

    def delete_rule(self, rule):
        """Remove a rule from this security group."""
        pass

    def replace_rules(self, rules,exp='pass'):
        """Replace all the rules of this security group with the  rules list."""
        self.logger.info(
            "Replace all the rules of this security group %s with the new rules" %
            self.secgrp_name)
        self.logger.debug(rules)
        if self.option == 'neutron':
	    #delete existing rules then add new rules
	    self.delete_all_rules(self.secgrp_id)
            secgrp_rules = self.create_sg_rule_quantum(self.secgrp_id,secgrp_rules=rules)
            if exp == 'pass':
                assert secgrp_rules
                self.secgrp_rules = rules
        else:
            secgrp_entries = PolicyEntriesType(rules)
            self.obj.set_security_group_entries(secgrp_entries)
            self.vnc.security_group_update(self.obj)

    @retry(delay=2, tries=5)
    def verify_secgrp_in_api_server(self):
        """Validate security group information in API-Server."""
	#verify if sg present in api
        api_server_inspect_handles = self.connections.get_api_server_inspect_handles()
        for api_s_inspect in api_server_inspect_handles.values():
            self.api_s_secgrp_obj = api_s_inspect.get_cs_secgrp(
                                    domain=self.domain_name,
                                    project=self.project_name,
                                    secgrp=self.secgrp_name, refresh=True)
            if not self.api_s_secgrp_obj:
                errmsg = "Security group %s not found in the API Server" % self.secgrp_name
                self.logger.warn(errmsg)
                return False, errmsg
            else:
                self.logger.info(
                    "Security group %s found in the API Server", self.secgrp_name)

	    #verify if sg acls present in api
            self.api_s_acls = api_s_inspect.get_secgrp_acls_href(
                domain=self.domain_name, project=self.project_name,
                secgrp=self.secgrp_name, refresh=True)
            if not self.api_s_acls:
                errmsg = "ACLs for Security group %s not found in the API Server" % self.secgrp_name
                self.logger.warn(errmsg)
                return False, errmsg
            else:
                self.logger.info(
                    "ACLs for Security group %s found in the API Server", self.secgrp_name)

        return True, None

    def verify_on_setup(self):
        try:
            secgrp = self.vnc.security_group_read(
                fq_name=self.secgrp_fq_name)
            self.logger.debug(
                "Security group: %s created succesfully", self.secgrp_fq_name)
        except NoIdError:
            errmsg = "Security group: %s not created." % self.secgrp_fq_name
            self.logger.warn(errmsg)
            return False, errmsg

        retval, errmsg = self.verify_secgrp_in_api_server()
        if not retval:
            return False, errmsg
        retval = self.verify_secgrp_in_control_nodes()
        if not retval:
            errmsg = "Security group: %s not found in control node." % self.secgrp_fq_name
            return False, errmsg
	
        return True, None

    @retry(delay=2, tries=5)
    def verify_secgrp_not_in_api_server(self):
        """Validate security group information in API-Server."""
	#verify if sg is removed from api
        api_server_inspect_handles = self.connections.get_api_server_inspect_handles()
        for api_s_inspect in api_server_inspect_handles.values():
            self.api_s_secgrp_obj = api_s_inspect.get_cs_secgrp(
                                    domain=self.domain_name,
                                    project=self.project_name,
                                    secgrp=self.secgrp_name, refresh=True)
            if self.api_s_secgrp_obj:
                errmsg = "Security group %s still found in the API Server" % self.secgrp_name
                self.logger.warn(errmsg)
                return False, errmsg
            else:
                self.logger.info(
                    "Security group %s removed from the API Server", self.secgrp_name)

	    #verify if sg acls removed from api
            self.api_s_acls = api_s_inspect.get_secgrp_acls_href(
                              domain=self.domain_name, project=self.project_name,
                              secgrp=self.secgrp_name, refresh=True)
            if self.api_s_acls:
                errmsg = "ACLs for Security group %s still found in the API Server" % self.secgrp_name
                self.logger.warn(errmsg)
                self.logger.debug("ACLs found for SG %s are: %s" %(self.secgrp_name, self.api_s_acls))
                return False, errmsg
            else:
                self.logger.info(
                    "ACLs for Security group %s removed from the API Server", self.secgrp_name)
        return True, None

    def verify_on_cleanup(self):
        try:
            secgroup = self.vnc.security_group_read(fq_name=self.secgrp_fq_name)
            errmsg = "Security group: %s still not removed" % self.secgrp_fq_name
            self.logger.warn(errmsg)
            return False, errmsg
        except NoIdError:
            self.logger.info("Security group: %s deleted successfully." %
                             self.secgrp_fq_name)

	errmsg = "Security group: %s still not removed" % self.secgrp_fq_name
        retval, msg = self.verify_secgrp_not_in_api_server()
        if not retval:
            return False, errmsg
        retval = self.verify_secgrp_not_in_control_nodes()
        if not retval:
            return False, errmsg

        return True, None

    def sec_grp_exist(self):
        try:
            secgroup = self.vnc.security_group_read(fq_name=self.secgrp_fq_name)
            self.secgrp_id = secgroup.uuid
        except NoIdError:
            return False
        return True

    @retry(delay=2, tries=5)
    def verify_secgrp_in_control_nodes(self):
        """Validate security group information in control nodes."""

        for cn in self.inputs.bgp_ips:
	    #verify if sg present in control nodes
            cn_inspect = self.connections.get_control_node_inspect_handle(cn)
            cn_secgrp_obj = cn_inspect.get_cn_sec_grp(
		domain=self.domain_name,
                project=self.project_name,
                secgrp=self.secgrp_name)
	    if not cn_secgrp_obj:
                self.logger.warn(
                        'security group %s not present in Control-node %s' %
                        (self.secgrp_name, cn))
		return False
            else:
                self.logger.info(
                    "Security group %s found in the control node %s" % (self.secgrp_name, cn))

	    #verify if sg acls present in control nodes
            cn_secgrp_obj = cn_inspect.get_cn_sec_grp_acls(
                domain=self.domain_name,
                project=self.project_name,
                secgrp=self.secgrp_name)
            if not cn_secgrp_obj:
                self.logger.warn(
                        'security group %s ACLs not present in Control-node %s' %
                        (self.secgrp_name, cn))
                return False
            else:
                self.logger.info(
                    "Security group %s ACLs found in the control node %s" % (self.secgrp_name, cn))


	return True


    @retry(delay=2, tries=15)
    def verify_secgrp_not_in_control_nodes(self):
        """Validate security group not present in control nodes."""
        #verify if sg present in control nodes
        for cn in self.inputs.bgp_ips:
            cn_inspect = self.connections.get_control_node_inspect_handle(cn)
            cn_secgrp_obj = cn_inspect.get_cn_sec_grp(
                domain=self.domain_name,
                project=self.project_name,
                secgrp=self.secgrp_name)
            if cn_secgrp_obj:
                self.logger.warn(
                        'security group %s present in Control-node %s' %
                        (self.secgrp_name, cn))
                return False
	    else:
                self.logger.info(
                        'security group %s removed from Control-node %s' %
                        (self.secgrp_name, cn))

            #verify if sg acls removed from control nodes
            cn_secgrp_obj = cn_inspect.get_cn_sec_grp_acls(
                domain=self.domain_name,
                project=self.project_name,
                secgrp=self.secgrp_name)
            if cn_secgrp_obj:
                self.logger.warn(
                        'security group %s ACLs still present in Control-node %s' %
                        (self.secgrp_name, cn))
                return False
            else:
                self.logger.info(
                    "Security group %s ACLs removed from the control node %s" % (self.secgrp_name, cn))

	return True

def get_secgrp_id_from_name(connections,secgrp_fq_name):
    fq_name_list = secgrp_fq_name.split(':')
    vnc = connections.get_vnc_lib_h().get_handle()
    try:
        secgroup = vnc.security_group_read(fq_name=fq_name_list)
        secgrp_id = secgroup.uuid
    except NoIdError:
        return False
    return secgrp_id

def list_sg_rules(connections,sg_id):
    sg_info = show_secgrp(connections,sg_id)

    return sg_info['security_group']['security_group_rules'] 

def show_secgrp(connections,sg_id):
    neutron = connections.get_network_h()
    sg_info = neutron.show_security_group(sg_id)

    return sg_info 
