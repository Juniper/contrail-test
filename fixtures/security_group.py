import fixtures

from vnc_api.vnc_api import NoIdError
from vnc_api.gen.cfixture import ContrailFixture
from vnc_api.gen.resource_xsd import PolicyEntriesType
from vnc_api.gen.resource_test import SecurityGroupTestFixtureGen,\
    ProjectTestFixtureGen, DomainTestFixtureGen

from tcutils.util import retry
try:
    from webui_test import *
except ImportError:
    pass

class SecurityGroupFixture(ContrailFixture):

    def __init__(
        self, inputs, connections, domain_name=None, project_name=None, secgrp_name=None,
	    uuid=None, secgrp_entries=None,option='orch'):
	#option <'orch' or 'contrail'>
        self.connections = connections
        self.inputs = connections.inputs
        self.logger = connections.logger
        self.vnc_lib_h = connections.get_vnc_lib_h()
        self.api_s_inspect = connections.api_server_inspect
        self.domain_name = self.inputs.domain_name
        self.project_name = self.inputs.project_name
        self.secgrp_name = secgrp_name
        self.secgrp_id = uuid
        self.secgrp_entries = secgrp_entries
        self.already_present = True
        self.domain_fq_name = [self.domain_name]
        self.project_fq_name = [self.domain_name, self.project_name]
        self.project_id = self.connections.get_project_id()
        self.secgrp_fq_name = [self.domain_name,
                               self.project_name, self.secgrp_name]
        self.cn_inspect = self.connections.cn_inspect
        self.orch = self.connections.orch
        self.option = option
        self.verify_is_run = False
        if self.inputs.verify_thru_gui():
            self.webui = WebuiTest(self.connections, self.inputs)

    def read(self):
        if self.secgrp_id:
            obj = self.orch.get_security_group(self.secgrp_id)
            self.secgrp_fq_name = obj.get_fq_name()
            self.secgrp_name = obj.name

    def setUp(self):
        super(SecurityGroupFixture, self).setUp()
        self.create()

    def create(self):
        self.secgrp_id = self.secgrp_id or self.get_sg_id()
        if self.secgrp_id:
            self.read()
            self.logger.info('SG %s(%s) already present, not creating SG'%
                            (self.secgrp_name, self.secgrp_id))
        else:
            self.logger.debug("Creating Security group: %s"%self.secgrp_fq_name)
            self.already_present = False
            if self.inputs.is_gui_based_config():
                self.webui.create_security_group(self)
            else:
                self.secgrp_id = self.orch.create_security_group(
                                                 sg_name=self.secgrp_name,
                                                 parent_fqname=self.project_fq_name,
                                                 sg_entries=self.secgrp_entries,
                                                 option=self.option)
            self.logger.info("Created security-group name:%s" %
                             self.secgrp_name)

    def get_uuid(self):
        return self.secgrp_id

    def get_fq_name(self):
        return self.secgrp_fq_name

    def delete_all_rules(self, sg_id):
        #deletes all the rules of the sg sg_id
        self.orch.delete_security_group_rules(sg_id=sg_id, project_id=self.project_id, option=self.option)

    def create_sg_rule(self, sg_id, secgrp_rules=None):
        return self.orch.set_security_group_rules(sg_id=sg_id, sg_entries=secgrp_rules, option=self.option)

    def cleanUp(self):
        super(SecurityGroupFixture, self).cleanUp()
        self.delete()

    def delete(self, verify=False):
        self.logger.debug("Deleting Security group: %s", self.secgrp_fq_name)
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if self.already_present:
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if do_cleanup:
            if self.inputs.is_gui_based_config():
                self.webui.delete_security_group(self)
            else:
                self.orch.delete_security_group(sg_id=self.secgrp_id, option=self.option)
            if self.verify_is_run or verify:
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
        self.orch.set_security_group_rules(sg_id=self.secgrp_id, sg_entries=rules, option=self.option)

    @retry(delay=2, tries=5)
    def verify_secgrp_in_api_server(self):
        """Validate security group information in API-Server."""
	#verify if sg present in api
        self.api_s_secgrp_obj = self.api_s_inspect.get_cs_secgrp(
            domain=self.domain_name, project=self.project_name,
            secgrp=self.secgrp_name, refresh=True)
        if not self.api_s_secgrp_obj:
            errmsg = "Security group %s not found in the API Server" % self.secgrp_name
            self.logger.warn(errmsg)
            return False, errmsg
        else:
            self.logger.info(
                "Security group %s found in the API Server", self.secgrp_name)

	#verify if sg acls present in api
        self.api_s_acls = self.api_s_inspect.get_secgrp_acls_href(
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
        self.verify_is_run = True
        try:
            secgrp = self.vnc_lib_h.security_group_read(
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
        self.api_s_secgrp_obj = self.api_s_inspect.get_cs_secgrp(
            domain=self.domain_name, project=self.project_name,
            secgrp=self.secgrp_name, refresh=True)
        if self.api_s_secgrp_obj:
            errmsg = "Security group %s still found in the API Server" % self.secgrp_name
            self.logger.warn(errmsg)
            return False, errmsg
        else:
            self.logger.info(
                "Security group %s removed from the API Server", self.secgrp_name)

	#verify if sg acls removed from api
        self.api_s_acls = self.api_s_inspect.get_secgrp_acls_href(
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
            secgroup = self.vnc_lib_h.security_group_read(
                fq_name=self.secgrp_fq_name)
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

    def get_sg_id(self):
        try:
            secgroup = self.vnc_lib_h.security_group_read(
                fq_name=self.secgrp_fq_name)
            self.secgrp_id = secgroup.uuid
        except NoIdError:
            return None
        return self.secgrp_id

    @retry(delay=2, tries=5)
    def verify_secgrp_in_control_nodes(self):
        """Validate security group information in control nodes."""

        for cn in self.inputs.bgp_ips:
	    #verify if sg present in control nodes
            cn_secgrp_obj = self.cn_inspect[cn].get_cn_sec_grp(
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
            cn_secgrp_obj = self.cn_inspect[cn].get_cn_sec_grp_acls(
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
            cn_secgrp_obj = self.cn_inspect[cn].get_cn_sec_grp(
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
            cn_secgrp_obj = self.cn_inspect[cn].get_cn_sec_grp_acls(
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
    try:
        secgroup = connections.vnc_lib.security_group_read(
            fq_name=fq_name_list)
        secgrp_id = secgroup.uuid
    except NoIdError:
        return False
    return secgrp_id

def list_sg_rules(connections,sg_id):
    sg_info = show_secgrp(connections,sg_id)

    return sg_info['security_group']['security_group_rules']

def show_secgrp(connections,sg_id):
    sg_info = connections.quantum_h.show_security_group(sg_id)

    return sg_info
