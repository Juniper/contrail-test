import fixtures
from vn_test import *
from project_test import *
from tcutils.util import *
from vnc_api.vnc_api import *
from netaddr import *
from time import sleep
from contrail_fixtures import *
import inspect
from common.policy import policy_test_utils
try:
    from webui_test import *
except ImportError:
    pass

class IPAMFixture(fixtures.Fixture):

    def __init__(self, name=None, project_obj=None, ipamtype=IpamType("dhcp"), vdns_obj= None):
        self.connections = project_obj.connections
        self.name = name
        self.inputs = project_obj.inputs
        # This variable of ProjectFixture Class is used for IPAM creation
        self.project_obj = project_obj.project_obj
        # This object is used for accesing vnc_lib_h , without which IPAM won't
        # be created.
        self.project_fixture_obj = project_obj
        self.logger = self.project_fixture_obj.inputs.logger
        self.api_s_inspect = self.connections.api_server_inspect
        self.fq_name = None
        self.ipamtype = ipamtype
        self.already_present = False
        self.ipam_id = None
        self.cn_inspect = self.connections.cn_inspect
        self.agent_inspect = self.connections.agent_inspect
        self.verify_is_run = False
        self.project_name = project_obj.project_name
        self.ri_name = None
        if self.inputs.verify_thru_gui():
            self.browser = self.connections.browser
            self.browser_openstack = self.connections.browser_openstack
            self.webui = WebuiTest(self.connections, self.inputs)
        self.vdns_obj = vdns_obj
    # end __init__

    def setUp(self):
        super(IPAMFixture, self).setUp()
        if not self.name:
            self.fq_name = NetworkIpam().get_fq_name()
            self.name = str(self.fq_name[2])

        ipam_list = self.project_fixture_obj.vnc_lib_h.network_ipams_list()[
            'network-ipams']
        for ipam in ipam_list:
            if self.name in ipam['fq_name'] and self.project_name in ipam['fq_name']:
                self.fq_name = ipam['fq_name']
                self.already_present = True
                self.ipam_id = ipam['uuid']
                self.obj = NetworkIpam(
                    name=self.name, parent_obj=self.project_obj, network_ipam_mgmt=self.ipamtype)
                self.logger.info('IPAM %s already present.Not creating it' %
                                 self.name)
                break
        if not self.already_present:
            self.obj = NetworkIpam(
                name=self.name, parent_obj=self.project_obj, network_ipam_mgmt=self.ipamtype)
            if self.vdns_obj:
                self.obj.add_virtual_DNS(self.vdns_obj)
            if self.inputs.is_gui_based_config():
                self.webui.create_ipam(self)
            else:
                self.project_fixture_obj.vnc_lib_h.network_ipam_create(
                    self.obj)
            ipam_list = self.project_fixture_obj.vnc_lib_h.network_ipams_list()[
                'network-ipams']
            for ipam in ipam_list:
                if self.name in ipam['fq_name']:
                    self.fq_name = ipam['fq_name']
                    self.ipam_id = ipam['uuid']
                    break
        # end setup

    def verify_on_setup(self):
        result = True
        if not self.verify_ipam_in_api_server():
            result = result and False
            self.logger.error(
                "One or more verifications in API Server for IPAM: %s failed" % (self.name))
        if not self.verify_ipam_in_control_nodes():
            result = result and False
            self.logger.error(
                "One or more verifications in Control-nodes for IPAM: %s failed" % (self.name))
        self.verify_is_run = True
        return result
        # end verify

    def cleanUp(self):
        super(IPAMFixture, self).cleanUp()
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if self.already_present:
            do_cleanup = False
        if do_cleanup:
            if self.inputs.is_gui_based_config():
                self.webui.delete_ipam(self)
            else:
                self.project_fixture_obj.vnc_lib_h.network_ipam_delete(
                    self.fq_name)
            if self.verify_is_run:
                assert self.verify_ipam_not_in_api_server()
                assert self.verify_ipam_not_in_control_nodes()
        else:
            self.logger.info('Skipping the deletion of IPAM %s' % self.fq_name)

        # end cleanUp

    @retry(delay=5, tries=3)
    def verify_ipam_in_api_server(self):
        """ Checks for IPAM:in API Server.

        False If IPAM Name is not found
        False If all Subnet prefixes are not found
        """
        self.api_s_vn_obj = self.api_s_inspect.get_cs_ipam(
            project=self.project_obj.name, ipam=self.name, refresh=True)
        if not self.api_s_vn_obj:
            self.logger.warn("IPAM %s is not found in API-Server" %
                             (self.name))
            return False
        if self.api_s_vn_obj['network-ipam']['uuid'] != self.ipam_id:
            self.logger.warn("IPAM Object ID %s not found in API-Server" %
                             (self.ipam_id))
            return False
        self.logger.info("Verifications in API Server for IPAM: %s passed" %
                         (self.name))
        return True
        # end Verify_ipam_in_api_server

    @retry(delay=5, tries=3)
    def verify_ipam_not_in_api_server(self):
        '''Verify that IPAM is removed in API Server.

        '''
        try:
            if self.project_fixture_obj.vnc_lib_h.network_ipam_read(self.fq_name):
                self.logger.warn("IPAM %s is still found in API-Server" %
                                 (self.name))
                return False
        except NoIdError:
            self.logger.info("IPAM: %s is not found in API Server" %
                             (self.name))
            return True
        # end verify_ipam_not_in_api_server

    @retry(delay=5, tries=3)
    def verify_ipam_in_control_nodes(self):
        # Checks for IPAM  details in Control-nodes.
        fqname = str(":".join(self.fq_name))
        self.ri_name = fqname + ':' + self.name
        for cn in self.inputs.bgp_ips:
            cn_config_vn_obj = self.cn_inspect[cn].get_cn_config_ipam(
                ipam=self.name, project=self.project_obj.name)
            if not cn_config_vn_obj:
                self.logger.warn(
                    'Control-node %s does not have IPAM %s info ' %
                    (cn, self.name))
                return False
            self.logger.debug("Control-node %s : IPAM object is : %s" %
                              (cn, cn_config_vn_obj))
            if fqname not in cn_config_vn_obj['node_name']:
                self.logger.warn(
                    'IFMAP View of Control-node is not having the IPAM  detail of %s' % (fqname))
                return False
        self.logger.info('Verifications in Control node for IPAM: %s passed' %
                         (self.name))
        return True
        # end verify_ipam_in_control_nodes

    @retry(delay=5, tries=10)
    def verify_ipam_not_in_control_nodes(self):
        # Verify that IPAM details are not in any Control-node
        fqname = str(":".join(self.fq_name))
        self.ri_name = fqname + ':' + self.name
        result = True
        for cn in self.inputs.bgp_ips:
            cn_object = self.cn_inspect[
                cn].get_cn_routing_instance(ri_name=self.ri_name)
            if cn_object:
                self.logger.warn(
                    "Routing instance for IPAM %s is still found in Control-node %s" % (self.name, cn))
                result = result and False
        # end for
        if self.cn_inspect[cn].get_cn_config_ipam(ipam=self.name, project=self.project_obj.name):
            self.logger.warn("Control-node config DB still has  IPAM %s" %
                             (self.name))
            result = result and False

        if result:
            self.logger.info("IPAM:%s is not found in control node" %
                             (self.name))
        return result
        # end verify_ipam_not_in_control_nodes

# end IPAMFixture
