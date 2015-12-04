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

    def __init__(self, name=None, connections=None, project_obj=None,
                 ipamtype=IpamType("dhcp"), vdns_obj=None, uuid=None):
        self.name = name
        self.connections = connections or project_obj.connections
        self.inputs = self.connections.inputs
        self.logger = self.connections.logger
        self.api_s_inspect = self.connections.api_server_inspect
        self.ipamtype = ipamtype
        self.already_present = False
        self.cn_inspect = self.connections.cn_inspect
        self.agent_inspect = self.connections.agent_inspect
        self.project_name = self.connections.project_name
        self.vnc = self.connections.get_vnc_lib_h()
        self.vdns_obj = vdns_obj
        self.ipam_id = uuid
        self.verify_is_run = False
        self.ri_name = None
        self.fq_name = [self.connections.domain_name, self.project_name, self.name]
        if self.inputs.verify_thru_gui():
            self.browser = self.connections.browser
            self.browser_openstack = self.connections.browser_openstack
            self.webui = WebuiTest(self.connections, self.inputs)
        if self.inputs.orchestrator == 'vcenter':
            # Overide for vcenter, IP allocation is in vcenter
            # represented as 'vCenter-ipam' in contrail-cfgm
            self.name = 'vCenter-ipam'
    # end __init__

    def read(self):
        if self.ipam_id:
            self.obj = self.vnc.network_ipam_read(id=self.ipam_id)
            self.fq_name = self.obj.get_fq_name()
            self.name = self.fq_name[-1]
            self.project_name = self.fq_name[-2]
            self.logger.info('Found IPAM %s(%s)'%(self.fq_name, self.ipam_id))
            self.already_present = True

    def setUp(self):
        super(IPAMFixture, self).setUp()
        self.create()
    # end setup

    def create(self):
        if self.ipam_id:
            return self.read()
        if not self.name:
            self.fq_name = NetworkIpam().get_fq_name()
            self.name = str(self.fq_name[2])

        for ipam in self.vnc.network_ipams_list()['network-ipams']:
            if self.name == ipam['fq_name'][2] and self.project_name == ipam['fq_name'][1]:
                self.fq_name = ipam['fq_name']
                self.already_present = True
                self.ipam_id = ipam['uuid']
                self.obj = NetworkIpam(name=self.name, parent_type='project',
                                       fq_name=self.fq_name,
                                       network_ipam_mgmt=self.ipamtype)
                self.logger.info('IPAM %s already present.Not creating it' %
                                 self.name)
                break
        if not self.already_present:
            self.obj = NetworkIpam(name=self.name, parent_type='project',
                                   fq_name=self.fq_name,
                                   network_ipam_mgmt=self.ipamtype)
            if self.inputs.is_gui_based_config():
                self.webui.create_ipam(self)
            else:
                self.vnc.network_ipam_create(self.obj)
            for ipam in self.vnc.network_ipams_list()['network-ipams']:
                if self.name == ipam['fq_name'][2] and self.project_name == ipam['fq_name'][1]:
                    self.fq_name = ipam['fq_name']
                    self.ipam_id = ipam['uuid']
                    break
        self.obj = self.vnc.network_ipam_read(fq_name=self.fq_name)
        if self.vdns_obj:
            self.obj.add_virtual_DNS(self.vdns_obj)
        if self.ipamtype:
            self.old_ipam_type = self.obj.get_network_ipam_mgmt()
            self.obj.set_network_ipam_mgmt(self.ipamtype)
        self.vnc.network_ipam_update(self.obj)

    def getObj(self):
        return self.obj

    def update_vdns(self, vdns_obj):
        self.obj = self.vnc.network_ipam_read(id=self.ipam_id)
        vdns_server = IpamDnsAddressType(virtual_dns_server_name=vdns_obj.get_fq_name_str())
        ipam_mgmt_obj = IpamType(ipam_dns_method='virtual-dns-server', ipam_dns_server=vdns_server)
        self.obj.set_network_ipam_mgmt(ipam_mgmt_obj)
        self.obj.add_virtual_DNS(vdns_obj)
        self.vnc.network_ipam_update(self.obj)

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
            if self.vdns_obj:
                self.obj.del_virtual_DNS(self.vdns_obj)
            if self.ipamtype:
                self.obj.set_network_ipam_mgmt(self.old_ipam_type)
            self.vnc.network_ipam_update(self.obj)
            self.logger.info('Skipping the deletion of IPAM %s' % self.fq_name)

        # end cleanUp

    @retry(delay=5, tries=3)
    def verify_ipam_in_api_server(self):
        """ Checks for IPAM:in API Server.

        False If IPAM Name is not found
        False If all Subnet prefixes are not found
        """
        self.api_s_vn_obj = self.api_s_inspect.get_cs_ipam(
            project=self.project_name, ipam=self.name, refresh=True)
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
            cn_config_vn_obj = self.cn_inspect[cn].get_cn_config_ipam(
                ipam=self.name, project=self.project_name)
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
            cn_object = self.cn_inspect[
                cn].get_cn_routing_instance(ri_name=self.ri_name)
            if cn_object:
                self.logger.warn(
                    "Routing instance for IPAM %s is still found in Control-node %s" % (self.name, cn))
                result = result and False
        # end for
        if self.cn_inspect[cn].get_cn_config_ipam(ipam=self.name, project=self.project_name):
            self.logger.warn("Control-node config DB still has  IPAM %s" %
                             (self.name))
            result = result and False

        if result:
            self.logger.info("IPAM:%s is not found in control node" %
                             (self.name))
        return result
        # end verify_ipam_not_in_control_nodes

# end IPAMFixture
