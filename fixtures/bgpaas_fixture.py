import vnc_api_test
from cfgm_common.exceptions import NoIdError
from tcutils.util import get_random_name, retry
try:
    from webui_test import *
except ImportError:
    pass


class BGPaaSFixture(vnc_api_test.VncLibFixture):
    '''Fixture to handle BGPaaS object
    '''

    def __init__(self, **kwargs):
        super(BGPaaSFixture, self).__init__(self, **kwargs)
        self.name = kwargs.get('name') or get_random_name('BGPaaS')
        self.uuid = kwargs.get('uuid', None)
        self.asn = kwargs.get('autonomous_system') or 64512
        self.ip = kwargs.get('bgpaas_ip_address') or None
        self.shared = kwargs.get('bgpaas_shared') or 'false'
        self.address_families = ['inet', 'inet6']
        self.created = False
#	if self.inputs.verify_thru_gui():
#            self.browser = self.connections.browser
#            self.browser_openstack = self.connections.browser_openstack
#            self.webui = WebuiTest(self.connections, self.inputs)

    def setUp(self):
        super(BGPaaSFixture, self).setUp()
        self.fq_name = [self.domain, self.project_name, self.name]
        self.create()

    def cleanUp(self):
        super(BGPaaSFixture, self).cleanUp()
        do_cleanup = True
        if (self.created == False or self.inputs.fixture_cleanup == 'no') and\
           self.inputs.fixture_cleanup != 'force':
            self.logger.info('Skipping deletion of BGPaaS %s :'
                             % (self.fq_name))
            do_cleanup = False
        if do_cleanup:
            if self.inputs.is_gui_based_config():
                self.webui.delete_bgpaas(self)
            else:
                self.delete()

    def read(self):
        self.logger.debug('Fetching info about BGPaaS %s' % self.uuid)
        obj = self.vnc_h.get_bgpaas(id=self.uuid)
        self.name = obj.name
        self.fq_name = obj.get_fq_name()

    def create(self):
        if not self.uuid:
            try:
                obj = self.vnc_h.get_bgpaas(fq_name=self.fq_name)
                self.uuid = obj.uuid
            except NoIdError:
                pass
        if self.uuid:
            self.read()
        else:
            self.logger.info('Creating BGPaaS %s' % self.name)
            if self.inputs.is_gui_based_config():
                self.webui.create_bgpaas(self)
            else:
                self.uuid = self.vnc_h.create_bgpaas(self.fq_name,
                                                     bgpaas_shared=self.shared,
                                                     autonomous_system=self.asn,
                                                     bgpaas_ip_address=self.ip,
                                                     address_families=self.address_families
                                                     )
            self.created = True
        self.logger.info('BGPaaS: %s(%s)'
                         % (self.name, self.uuid))

    def delete(self):
        self.logger.info('Deleting BGPaaS %s(%s)' % (self.name, self.uuid))
        self.vnc_h.delete_bgpaas(id=self.uuid)
        if getattr(self, 'verify_is_run', False):
            assert self.verify_on_cleanup()

    def update_properties(self):
        self.vnc_h.update_bgpaas(self.uuid)

    def verify_on_setup(self):
        self.verify_is_run = True
        ret = self.verify_in_api_server()
        self.logger.info('BGPaaS(%s): verify_on_setup %s' % (self.uuid,
                                                             'passed' if ret else 'failed'))
        return ret

    def verify_on_cleanup(self):
        ret = self.verify_not_in_api_server()
        self.logger.info('BGPaaS(%s): verify_on_cleanup %s' % (self.uuid,
                                                               'passed' if ret else 'failed'))
        return ret

    @retry(delay=2, tries=5)
    def verify_in_api_server(self):
        api_h = self.connections.api_server_inspect
        api_obj = api_h.get_bgpaas(self.uuid)
        if self.asn != api_obj.autonomous_system():
            self.logger.warn('BGPaaS ASN didnt match. Exp: %s Act: %s' % (
                self.asn, api_obj.asn))
            return False
        if self.shared != api_obj.bgpaas_shared():
            self.logger.warn('BGPaaS shared attribute didnt match. Exp: %s Act: %s' % (
                self.shared, api_obj.shared))
            return False
        if self.ip != api_obj.bgpaas_ip_address():
            self.logger.warn('BGPaaS IP didnt match. Exp: %s Act: %s' % (
                self.ip, api_obj.ip))
            return False
        self.logger.info(
            'verify_in_api_server passed for BGPaaS obj %s' % self.uuid)
        return True

    @retry(delay=2, tries=5)
    def verify_not_in_api_server(self):
        api_h = self.connections.api_server_inspect
        if api_h.get_bgpaas(self.uuid, refresh=True):
            self.logger.warn(
                'BGPaaS: %s is still found in api server' % self.uuid)
            return False
        self.logger.debug('BGPaaS: %s deleted from api server' % self.uuid)
        return True

    @retry(delay=2, tries=5)
    def verify_in_agent(self, agent):
        self.logger.info('Check BGPaaS obj %s on agent %s' %
                         (self.uuid, agent))
        agent_h = self.connections.agent_inspect[agent]
        agent_obj = agent_h.get_bgpaas(self.uuid)
        if self.shared != agent_obj.is_shared:
            self.logger.warn('BGPaaS shared attribute didnt match. Exp: %s Act: %s' % (
                self.shared, agent_obj.shared))
            return False
        if self.ip != agent_obj.vm_bgp_peer_ip:
            self.logger.warn('BGPaaS IP didnt match. Exp: %s Act: %s' % (
                self.ip, agent_obj.ip))
            return False
        self.logger.info(
            'verify_in_agent passed for BGPaaS obj %s' % self.uuid)
        return True

    @retry(delay=2, tries=5)
    def verify_not_in_agent(self, agent):
        agent_h = self.connections.agent_inspect[agent]
        if agent_h.get_bgpaas(self.uuid):
            self.logger.warn('BGPaaS: %s is still found in agent %s' % (
                             self.uuid, agent))
            return False
        return True

    @retry(delay=5, tries=10)
    def verify_not_in_control_node(self, bgpaas_vm):
        for ctrl_node in bgpaas_vm.get_control_nodes():
            result = True
            cn_bgp_entry = self.connections.get_control_node_inspect_handle(
                ctrl_node).get_cn_bgp_neigh_entry(encoding='BGP')
            for entry in cn_bgp_entry:
                if entry['router_type'] == 'bgpaas-client' and entry['state'] == 'Established':
                    self.logger.error(
                        'BGPaaS session still seen in control-node %s' % ctrl_node)
                    result = False
        return result

    @retry(delay=5, tries=20)
    def verify_in_control_node(self, bgpaas_vm):
        for ctrl_node in bgpaas_vm.get_control_nodes():
            result = False
            cn_bgp_entry = self.connections.get_control_node_inspect_handle(
                ctrl_node).get_cn_bgp_neigh_entry(encoding='BGP')
            for entry in cn_bgp_entry:
                if entry['router_type'] == 'bgpaas-client' and entry['state'] == 'Established':
                    self.logger.info(
                        'BGPaaS session seen in control-node %s' % ctrl_node)
                    result = True
        result = result and True
        return result

    def attach_vmi(self, vmi):
        result = self.vnc_h.attach_vmi_to_bgpaas(self.uuid, vmi)
        return result

    def detach_vmi(self, vmi):
        result = self.vnc_h.detach_vmi_from_bgpaas(self.uuid, vmi)
        return result

    def attach_shc(self, shc_id):
        result = self.vnc_h.attach_shc_to_bgpaas(self.uuid, shc_id)
        return result

    def detach_shc(self, shc_id):
        result = self.vnc_h.detach_shc_from_bgpaas(self.uuid, shc_id)
        return result
