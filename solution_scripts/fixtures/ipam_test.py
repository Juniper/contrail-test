import fixtures
from vn_test import *
from project_test import *
from tcutils.util import *
from vnc_api.vnc_api import *
from netaddr import *
from contrail_fixtures import *
import inspect
from common.policy import policy_test_utils
try:
    from webui_test import *
except ImportError:
    pass

class IPAMFixture(fixtures.Fixture):

    def __init__(self, name=None, connections=None, project_obj=None, ipamtype=IpamType("dhcp"), vdns_obj=None, uuid=None):
        if not connections:
            connections = project_obj.connections
        self.name = name
        self.inputs = connections.inputs
        self.logger = self.inputs.logger
        self.connections = connections
        self.ipamtype = ipamtype
        if project_obj:
            project_name = project_obj.project_name
        else:
            project_name = self.inputs.project_name
        self.project_name = project_name
        self.ri_name = None
        self.already_present = False
        self.verify_is_run = False
        self.vdns_obj = vdns_obj
        self.fq_name = [self.inputs.domain_name, self.project_name, self.name]
        self.vnc = self.connections.get_vnc_lib_h().get_handle()
        if self.inputs.verify_thru_gui():
            self.browser = self.connections.browser
            self.browser_openstack = self.connections.browser_openstack
            self.webui = WebuiTest(self.connections, self.inputs)
        if uuid:
            self.obj = self.vnc.network_ipam_read(id=uuid)
            self.fq_name = self.obj.get_fq_name()
            self.name = self.fq_name[-1]
            self.project_name = self.fq_name[-2]
            self.ipam_id = uuid
        if self.inputs.orchestrator == 'vcenter':
            # Overide for vcenter, IPAM is created in vcenter and
            # represented as 'vCenter-ipam' in contrail-cfgm
            self.name = 'vCenter-ipam'
    # end __init__

    def setUp(self):
        super(IPAMFixture, self).setUp()
        if not self.name:
            self.fq_name = NetworkIpam().get_fq_name()
            self.name = str(self.fq_name[2])

        ipam_list = self.vnc.network_ipams_list()['network-ipams']
        print ipam_list, self.name, self.project_name
        for ipam in ipam_list:
            if self.name in ipam['fq_name'] and self.project_name in ipam['fq_name']:
                self.fq_name = ipam['fq_name']
                self.already_present = True
                self.ipam_id = ipam['uuid']
                self.obj = NetworkIpam(name=self.name, parent_type='project',
                           fq_name=self.fq_name, network_ipam_mgmt=self.ipamtype)
                self.logger.info('IPAM %s already present.Not creating it' %
                                 self.name)
                break
        if not self.already_present:
            self.obj = NetworkIpam(name=self.name, parent_type='project',
                       fq_name=self.fq_name,  network_ipam_mgmt=self.ipamtype)
            if self.inputs.is_gui_based_config():
                self.webui.create_ipam(self)
            else:
                if self.vdns_obj:
                    vdns_server = IpamDnsAddressType(virtual_dns_server_name=self.vdns_obj.get_fq_name_str())
                    ipam_mgmt_obj = IpamType(ipam_dns_method='virtual-dns-server', ipam_dns_server=vdns_server)
                    self.obj.set_network_ipam_mgmt(ipam_mgmt_obj)
                    self.obj.add_virtual_DNS(self.vdns_obj)
                self.vnc.network_ipam_create(self.obj)
            ipam_list = self.vnc.network_ipams_list()['network-ipams']
            for ipam in ipam_list:
                if self.name in ipam['fq_name']:
                    self.fq_name = ipam['fq_name']
                    self.ipam_id = ipam['uuid']
                    break
        # end setup

    def get_uuid(self):
        return self.ipam_id

    def get_fq_name(self):
        return self.fq_name

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
        self.delete()

    def delete(self, verify=False):
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
                self.vnc.network_ipam_delete(self.fq_name)
            if self.verify_is_run or verify:
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
        api_server_inspect_handles = self.connections.get_api_server_inspect_handles()
        for api_s_inspect in api_server_inspect_handles.values():
            api_s_vn_obj = api_s_inspect.get_cs_ipam(project=self.project_name,
                                                  ipam=self.name, refresh=True)
            if not api_s_vn_obj:
                self.logger.warn("IPAM %s is not found in API-Server" %
                             (self.name))
                return False
            if api_s_vn_obj['network-ipam']['uuid'] != self.ipam_id:
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
        if self.inputs.orchestrator == 'vcenter':
            # vcenter IPAM object is never deleted
            return True
        try:
            if self.vnc.network_ipam_read(self.fq_name):
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
            cn_inspect = self.connections.get_control_node_inspect_handle(cn)
            cn_config_vn_obj = cn_inspect.get_cn_config_ipam(ipam=self.name,
                                          project=self.project_name)
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
        if self.inputs.orchestrator == 'vcenter':
            # vcenter IPAM object is never deleted
            return True
        fqname = str(":".join(self.fq_name))
        self.ri_name = fqname + ':' + self.name
        result = True
        for cn in self.inputs.bgp_ips:
            cn_inspect = self.connections.get_control_node_inspect_handle(cn)
            cn_object = cn_inspect.get_cn_routing_instance(ri_name=self.ri_name)
            if cn_object:
                self.logger.warn(
                    "Routing instance for IPAM %s is still found in Control-node %s" % (self.name, cn))
                result = result and False
        # end for
        if cn_inspect.get_cn_config_ipam(ipam=self.name, project=self.project_name):
            self.logger.warn("Control-node config DB still has  IPAM %s" %
                             (self.name))
            result = result and False

        if result:
            self.logger.info("IPAM:%s is not found in control node" %
                             (self.name))
        return result
        # end verify_ipam_not_in_control_nodes

# end IPAMFixture
