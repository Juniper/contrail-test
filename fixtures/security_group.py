import fixtures

from vnc_api.vnc_api import NoIdError
from vnc_api.gen.cfixture import ContrailFixture
from vnc_api.gen.resource_xsd import PolicyEntriesType
from vnc_api.gen.resource_test import SecurityGroupTestFixtureGen,\
    ProjectTestFixtureGen, DomainTestFixtureGen

from tcutils.util import retry


class SecurityGroupFixture(ContrailFixture):

    def __init__(
        self, inputs, connections, domain_name, project_name, secgrp_name,
            secgrp_id=None, secgrp_entries=None):
        self.logger = inputs.logger
        self.vnc_lib_h = connections.vnc_lib
        self.api_s_inspect = connections.api_server_inspect
        self.inputs = inputs
        self.domain_name = domain_name
        self.project_name = project_name
        self.secgrp_name = secgrp_name
        self.secgrp_id = secgrp_id
        self.secgrp_entries = PolicyEntriesType(secgrp_entries)
        self.already_present = False
        self.domain_fq_name = [self.domain_name]
        self.project_fq_name = [self.domain_name, self.project_name]
        self.secgrp_fq_name = [self.domain_name,
                               self.project_name, self.secgrp_name]
	self.cn_inspect = connections.cn_inspect

    def setUp(self):
        self.logger.debug("Creating Security group: %s", self.secgrp_fq_name)
        super(SecurityGroupFixture, self).setUp()
        project = ProjectTestFixtureGen(self.vnc_lib_h, self.project_name)
        project.setUp()
        sec_grp_check = self.sec_grp_exist()
        if sec_grp_check:
            self.already_present = True
            self.logger.info(
                'Security group  %s already present, not creating security group' %
                (self.secgrp_name))
        else:
            self.secgrp_fix = self.useFixture(
                SecurityGroupTestFixtureGen(conn_drv=self.vnc_lib_h,
                                            security_group_name=self.secgrp_name,
                                            parent_fixt=project,
                                            security_group_id=self.secgrp_id,
                                            security_group_entries=self.secgrp_entries))
            self.secgrp_id = self.secgrp_fix._obj.uuid
            self.logger.info("Created security-group name:%s" %
                             self.secgrp_name)

    def cleanUp(self):
        self.logger.debug("Deleting Security group: %s", self.secgrp_fq_name)
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if self.already_present:
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if do_cleanup:
            self.secgrp_fix.cleanUp()
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

    def replace_rules(self, rules):
        """Replace all the rules of this security group with the  rules list."""
        self.logger.info(
            "Replace all the rules of this security group %s with the new rules" %
            self.secgrp_name)
        self.logger.debug(rules)
        secgrp_entries = PolicyEntriesType(rules)
        self.secgrp_fix._obj.set_security_group_entries(secgrp_entries)
        self.vnc_lib_h.security_group_update(self.secgrp_fix._obj)

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
        try:
            secgrp = self.vnc_lib_h.security_group_read(
                fq_name=self.secgrp_fq_name)
            self.logger.debug(
                "Security group: %s created succesfully", self.secgrp_fq_name)
        except NoIdError:
            errmsg = "Security group: %s not created." % self.secgrp_fq_name
            self.logger.warn(errmsg)
            return False, errmsg

        retval, msg = self.verify_secgrp_in_api_server()
        if not retval:
            return False, errmsg
        retval = self.verify_secgrp_in_control_nodes()
        if not retval:
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

    def sec_grp_exist(self):
        try:
            secgroup = self.vnc_lib_h.security_group_read(
                fq_name=self.secgrp_fq_name)
            self.secgrp_id = secgroup.uuid
        except NoIdError:
            return False
        return True

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

