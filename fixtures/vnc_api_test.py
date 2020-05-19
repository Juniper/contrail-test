from future import standard_library
standard_library.install_aliases()
from builtins import str
import fixtures
import os
import uuid

from vnc_api.vnc_api import *
from vnc_api.exceptions import NoIdError

from contrailapi import ContrailVncApi
from tcutils.util import get_dashed_uuid
from openstack import OpenstackAuth, OpenstackOrchestrator
from vcenter import VcenterAuth, VcenterOrchestrator
from common import log_orig as contrail_logging
from configparser import ConfigParser, DuplicateSectionError

_VNC_API_LIB_INI_ = '/etc/contrail/vnc_api_lib.ini'

class TestVncApi(VncApi):
    def __init__(self, *args, **kwargs):
        super(TestVncApi, self).__init__(*args, **kwargs)

    def _http_put(self, uri, body, headers):
        if self._base_url not in uri:
            uri = self._base_url + uri.lstrip('/')
        return super(TestVncApi, self)._http_put(uri,
            body, headers)

    def _http_delete(self, uri, body, headers):
        if self._base_url not in uri:
            uri = self._base_url + uri.lstrip('/')
        return super(TestVncApi, self)._http_delete(uri,
            body, headers)

    def _http_post(self, uri, body, headers):
        if self._base_url not in uri:
            uri = self._base_url + uri.lstrip('/')
        return super(TestVncApi, self)._http_post(uri,
            body, headers)

    def _http_get(self, uri, headers=None, query_params=None):
        if self._base_url not in uri:
            uri = self._base_url + uri.lstrip('/')
        return super(TestVncApi, self)._http_get(uri,
            headers=headers, query_params=query_params)

class VncLibFixture(fixtures.Fixture):
    ''' Wrapper for VncApi

    :param domain   : default is default-domain
    :param project_name  : default is admin
    :param cfgm_ip  : default is 127.0.0.1
    :param api_port : default is 8082
    :param connections   : ContrailConnections object. default is None
    :param username : default is admin
    :param password : default is contrail123
    :param auth_server_ip : default is 127.0.0.1
    :param project_id     : defualt is None
    :param logger         : logger object
    :param use_ssl        : default False (use https to connect to API server)
    '''
    def __init__(self, *args, **kwargs):
        self.username = os.getenv('OS_USERNAME') or \
                        kwargs.get('username', 'admin')
        self.password = os.getenv('OS_PASSWORD') or \
                        kwargs.get('password', 'contrail123')
        self.project_name = kwargs.get('project_name', 'admin')
        self.orch_domain = self.domain = kwargs.get('domain', 'Default')
        if self.domain == 'Default':
            self.domain = 'default-domain'
        self.api_server_port = kwargs.get('api_server_port', '8082')
        self.logger = kwargs.get('logger', None)
        self.connections = kwargs.get('connections', None)
        self.orchestrator = kwargs.get('orchestrator', 'openstack')
        self.vnc_api_h = None
        self.inputs = kwargs.get('inputs', self.connections.inputs
                                           if self.connections else None)
        self.neutron_handle = None
        self.cfgm_ip = kwargs.get('cfgm_ip',self.inputs.cfgm_ip \
                          if self.inputs else '127.0.0.1')
        self.api_server_url = kwargs.get('api_server_url')
        self.auth_server_ip = self.inputs.auth_ip if self.inputs else \
                        kwargs.get('auth_server_ip', '127.0.0.1')
        self.auth_port = self.inputs.auth_port if self.inputs else \
                        kwargs.get('auth_port', '5000')
        self.auth_url = self.inputs.auth_url if self.inputs else \
                        os.getenv('OS_AUTH_URL') or \
                        'http://%s:5000/v2.0'%self.auth_server_ip
        self.auth_protocol = self.inputs.auth_protocol if self.inputs else \
                        kwargs.get('auth_protocol', 'http')
        self.project_id = kwargs.get('project_id', None)
        self.certfile = kwargs.get('certfile', None)
        self.keyfile = kwargs.get('keyfile', None)
        self.cacert = kwargs.get('cacert', None)
        self.insecure = kwargs.get('insecure') or self.inputs.insecure \
                        if self.inputs else False
        self.use_ssl = kwargs.get('use_ssl') or \
            self.inputs.api_protocol == 'https' if self.inputs else False
        self.apicertfile = kwargs.get('apicertfile') or \
            self.inputs.apicertfile if self.inputs else None
        self.apikeyfile = kwargs.get('apikeyfile') or \
            self.inputs.apikeyfile if self.inputs else None
        self.apicafile = kwargs.get('apicafile') or \
            self.inputs.apicafile if self.inputs else None
        self.authn_url = self.inputs.authn_url if self.inputs else \
                         kwargs.get('authn_url', None)
        self.timeout = kwargs.get('timeout',60)
        if self.connections:
            self.logger = self.connections.logger
            self.project_name = self.connections.project_name
            self.orch_domain = self.domain = self.connections.domain_name #juju deployment CEM-15443
            self.inputs = self.connections.inputs
            self.neutron_handle = self.connections.quantum_h
            self.vnc_api_h = self.connections.vnc_lib
            self.username = self.connections.username
            self.password = self.connections.password
            self.domain = self.connections.domain_name
            self.cfgm_ip = self.inputs.cfgm_ip
            self.auth_server_ip = self.inputs.auth_ip
            self.auth_client = self.connections.auth
            self.project_id = self.connections.project_id
            self.vnc_h = self.orch.vnc_h if self.orch else kwargs.get('vnc_h', None)
    # end __init__

    # Create tmp ini file as workaround for insecure
    def _update_vnc_api_ini(self, insecure=True):
        config = ConfigParser()
        config.read(_VNC_API_LIB_INI_)
        try:
            config.add_section('global')
        except DuplicateSectionError:
            pass
        config.set('global', 'insecure', str(insecure))
        try:
            config.add_section('auth')
        except DuplicateSectionError:
            pass
        config.set('auth', 'insecure', str(insecure))
        with open(_VNC_API_LIB_INI_, 'w') as fd:
            config.write(fd)

    def setUp(self):
        super(VncLibFixture, self).setUp()
        if not self.connections:
            self.logger = self.logger or contrail_logging.getLogger(__name__)
            if self.insecure:
                self._update_vnc_api_ini(insecure=True)
            self.vnc_api_h = TestVncApi(
                              username=self.username,
                              password=self.password,
                              tenant_name=self.project_name,
                              domain_name=self.orch_domain,
                              api_server_host=self.cfgm_ip,
                              api_server_port=self.api_server_port,
                              api_server_url=self.api_server_url,
                              auth_host=self.auth_server_ip,
                              auth_port=self.auth_port,
                              auth_protocol=self.auth_protocol,
                              api_server_use_ssl=self.use_ssl,
                              apicertfile=self.apicertfile,
                              apikeyfile=self.apikeyfile,
                              apicafile=self.apicafile,
                              auth_url=self.authn_url,
                              timeout=self.timeout)
            if self.orchestrator == 'openstack':
                self.auth_client = OpenstackAuth(
                                    self.username,
                                    self.password,
                                    self.project_name,
                                    domain_name=self.orch_domain,
                                    auth_url=self.auth_url,
                                    certfile=self.certfile,
                                    keyfile=self.keyfile,
                                    cacert=self.cacert,
                                    insecure=self.insecure,
                                    logger=self.logger,
                                    scope='project')
            elif self.orchestrator == 'vcenter':
                self.auth_client = VcenterAuth(self.username,
                                                self.password,
                                                self.project_name,
                                                self.inputs
                                                )
        if self.orch:
            self.vnc_h = self.orch.vnc_h
        else:
            self.vnc_h = ContrailVncApi(self.vnc_api_h, self.logger)
    # end setUp

    def get_project_id(self):
        if not self.project_id:
            self.project_id = self.vnc_api_h.project_read(
                fq_name=[self.domain, self.project_name]).uuid
        return self.project_id


    def cleanUp(self):
        super(VncLibFixture, self).cleanUp()

    def get_handle(self):
        return self.vnc_api_h
    # end get_handle

    def get_contrail_api_handle(self):
        return self.vnc_h


    @property
    def admin_h(self):
        if not getattr(self, '_admin_h', None):
            self._admin_h = VncLibFixture(username=self.inputs.admin_username,
                                          password=self.inputs.admin_password,
                                          project_name=self.inputs.admin_tenant,
                                          domain=self.inputs.admin_domain,
                                          inputs=self.inputs,
                                          cfgm_ip=self.cfgm_ip,
                                          api_server_port=self.api_server_port,
                                          auth_server_ip=self.auth_server_ip,
                                          orchestrator=self.orchestrator,
                                          logger=self.logger)
            self._admin_h.setUp()
        return self._admin_h

    # fallback to ContrailApi when attr is not found and handle permission denied
    def __getattr__(self, attr):
        # WA to avoid recursive getattr calls
        if attr == '_orch' or attr == 'vnc_h' or attr == '_admin_h':
            return None
        if not hasattr(self.vnc_h, attr):
            raise AttributeError('%s object has no attribute %s'%(
                                 self.__class__.__name__, attr))
        act_attr = getattr(self.vnc_h, attr)
        if callable(act_attr):
            def hook(*args, **kwargs):
                try:
                    act_attr = getattr(self.vnc_h, self._attr)
                    return act_attr(*args, **kwargs)
                except PermissionDenied:
                    act_attr = getattr(self.admin_h.vnc_h, self._attr)
                    return act_attr(*args, **kwargs)
            self._attr = attr
            return hook
        else:
            return act_attr

    @property
    def orch(self):
        if not getattr(self, '_orch', None):
            self._orch = self.get_orch_h()
        return self._orch

    def get_orch_h(self):
        if self.connections:
            return self.connections.orch
        else:
            if self.orchestrator == 'openstack':
                return OpenstackOrchestrator(
                    vnclib=self.vnc_api_h,
                    logger=self.logger,
                    auth_h=self.auth_client,
                    inputs=self.inputs)
            elif self.orchestrator == 'vcenter':
                vcenter_dc = self.inputs.vcenter_dc if self.inputs else \
                             os.getenv('VCENTER_DC', None)
                return VcenterOrchestrator(user=self.username,
                    pwd=self.password,
                    host=self.inputs.vcenter_server,
                    port=self.inputs.vcenter_port,
                    dc_name=vcenter_dc,
                    vnc=self.vnc_api_h,
                    inputs=self.inputs,
                    logger=self.logger)
        return

    def get_neutron_handle(self):
        if self.neutron_handle:
            return self.neutron_handle
        else:
            self.neutron_handle = self.orch.get_network_handler()
            return self.neutron_handle
    # end get_neutron_handle

    def get_project_obj(self, project_fqname=None):
        if project_fqname:
            return self.vnc_api_h.project_read(fq_name=project_fqname)
        elif self.connections:
            project_id = self.connections.project_id
        elif self.get_project_id():
            project_id = self.project_id
        else:
            project_id = self.vnc_api_h.project_read(
                fq_name_str='default-domain:default-project').uuid
        try:
            parent_obj = self.vnc_api_h.project_read(id=project_id)
        except PermissionDenied:
            parent_obj = self.admin_h.vnc_api_h.project_read(id=project_id)
        return parent_obj
    # end get_parent_obj

    def get_forwarding_mode(self, vn_fq_name):
        vnc_lib = self.vnc_api_h
        # Figure out VN
        vni_list = vnc_lib.virtual_networks_list(
            parent_id=self.get_project_id())['virtual-networks']
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
        vnc_lib = self.vnc_api_h
        # Figure out VN
        vni_list = vnc_lib.virtual_networks_list(
            parent_id=self.get_project_id())['virtual-networks']
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
        vnc_lib = self.vnc_api_h
        # Figure out VN
        vni_list = self.vnc_api_h.virtual_networks_list(
            parent_id=self.get_project_id())['virtual-networks']
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
        return self.vnc_api_h.id_to_fq_name(id)

    def set_vxlan_mode(self, vxlan_mode='automatic'):
        ''' one of automatic or configured
        '''
        fq_name = [ 'default-global-system-config',
                    'default-global-vrouter-config']
        vrouter_config = self.vnc_api_h.global_vrouter_config_read(fq_name=fq_name)
        vrouter_config.set_vxlan_network_identifier_mode(vxlan_mode)
        self.vnc_api_h.global_vrouter_config_update(vrouter_config)

    def get_vxlan_mode(self):
        fq_name = [ 'default-global-system-config',
                    'default-global-vrouter-config']
        vrouter_config = self.vnc_api_h.global_vrouter_config_read(fq_name=fq_name)
        return vrouter_config.get_vxlan_network_identifier_mode()
    # end

    def get_global_asn(self, gsc_id=None):
        gsc_id = gsc_id or self.vnc_api_h.get_default_global_system_config_id()
        gsc_obj = self.vnc_api_h.global_system_config_read(id=gsc_id)
        return gsc_obj.get_autonomous_system()
    # end get_global_asn

    def set_global_asn(self, asn, gsc_id=None):
        gsc_id = gsc_id or self.vnc_api_h.get_default_global_system_config_id()
        gsc_obj = self.vnc_api_h.global_system_config_read(id=gsc_id)
        gsc_obj.set_autonomous_system(int(asn))
        self.vnc_api_h.global_system_config_update(gsc_obj)
    # end set_global_asn

    def get_global_forwarding_mode(self):
        fq_name = [ 'default-global-system-config',
                    'default-global-vrouter-config']
        try:
            gsc_obj = self.vnc_api_h.global_vrouter_config_read(fq_name=fq_name)
        except PermissionDenied:
            gsc_obj = self.admin_h.vnc_api_h.global_vrouter_config_read(fq_name=fq_name)
        return gsc_obj.get_forwarding_mode()
    # end get_global_forwarding_mode

    def get_active_forwarding_mode(self,vn_fq_name):
        ''' Returns l2 or l3 or l2_l3
        Returns Vn's forwarding mode if set.
        If VN forwarding mode is not set, returns global forwarding mode
        If global forwarding mode too is not set, returns 'l2_l3' since this is the default.
        '''
        gl_fw_mode = self.get_global_forwarding_mode()
        vn_fw_mode = self.get_forwarding_mode(vn_fq_name)
        if vn_fw_mode:
            return vn_fw_mode
        elif gl_fw_mode:
            return gl_fw_mode
        else:
            return 'l2_l3'
    #end get_active_forwarding_mode

    def set_global_forwarding_mode(self,forwarding_mode):
        fq_name = [ 'default-global-system-config',
                    'default-global-vrouter-config']
        gsc_obj = self.vnc_api_h.global_vrouter_config_read(fq_name=fq_name)
        gsc_obj.set_forwarding_mode(forwarding_mode)
        self.vnc_api_h.global_vrouter_config_update(gsc_obj)
    #end set_global_forwarding_mode

    def get_flow_export_rate(self):
        fq_name = [ 'default-global-system-config',
                    'default-global-vrouter-config']
        gv_obj = self.vnc_api_h.global_vrouter_config_read(fq_name=fq_name)
        rate = gv_obj.get_flow_export_rate()
        return rate
    # end get_flow_export_rate

    def set_flow_export_rate(self, value):
        '''
        Set flow export rate in default global vrouter config
        value : Value of flow export rate to be set
        '''
        fq_name = [ 'default-global-system-config',
                    'default-global-vrouter-config']
        gv_obj = self.vnc_api_h.global_vrouter_config_read(fq_name=fq_name)
        gv_obj.set_flow_export_rate(int(value) if (value is not None) else None)
        self.vnc_api_h.global_vrouter_config_update(gv_obj)
        self.logger.info('Setting flow export rate: %s' % (value))
        return True
    # end set_flow_export_rate

    def get_global_mac_limit_control(self):
        gsc_id = self.vnc_api_h.get_default_global_system_config_id()
        gsc_obj = self.vnc_api_h.global_system_config_read(id=gsc_id)
        return gsc_obj.get_mac_limit_control()
    # end get_global_mac_limit_control

    def set_global_mac_limit_control(self, mac_limit_control=None):
        gsc_id = self.vnc_api_h.get_default_global_system_config_id()
        gsc_obj = self.vnc_api_h.global_system_config_read(id=gsc_id)
        gsc_obj.set_mac_limit_control(mac_limit_control)
        self.vnc_api_h.global_system_config_update(gsc_obj)
    # end set_global_mac_limit_control

    def get_global_mac_move_control(self):
        gsc_id = self.vnc_api_h.get_default_global_system_config_id()
        gsc_obj = self.vnc_api_h.global_system_config_read(id=gsc_id)
        return gsc_obj.get_mac_move_control()
    # end get_global_mac_move_control

    def set_global_mac_move_control(self, mac_move_control=None):
        gsc_id = self.vnc_api_h.get_default_global_system_config_id()
        gsc_obj = self.vnc_api_h.global_system_config_read(id=gsc_id)
        gsc_obj.set_mac_move_control(mac_move_control)
        self.vnc_api_h.global_system_config_update(gsc_obj)
    # end set_global_mac_move_control

    def get_global_mac_aging_time(self):
        gsc_id = self.vnc_api_h.get_default_global_system_config_id()
        gsc_obj = self.vnc_api_h.global_system_config_read(id=gsc_id)
        return gsc_obj.get_mac_aging_time()
    # end get_global_mac_aging_time

    def set_global_mac_aging_time(self, mac_aging_time=None):
        gsc_id = self.vnc_api_h.get_default_global_system_config_id()
        gsc_obj = self.vnc_api_h.global_system_config_read(id=gsc_id)
        gsc_obj.set_mac_aging_time(mac_aging_time)
        self.vnc_api_h.global_system_config_update(gsc_obj)
    # end set_global_mac_aging_time

    def get_global_igmp_config(self):
        gsc_id = self.vnc_api_h.get_default_global_system_config_id()
        gsc_obj = self.vnc_api_h.global_system_config_read(id=gsc_id)
        return gsc_obj.get_igmp_enable()
    # end get_global_igmp_enable

    def set_global_igmp_config(self, igmp_enable=True):
        gsc_id = self.vnc_api_h.get_default_global_system_config_id()
        gsc_obj = self.vnc_api_h.global_system_config_read(id=gsc_id)
        gsc_obj.set_igmp_enable(igmp_enable)
        self.vnc_api_h.global_system_config_update(gsc_obj)
    # end set_global_igmp_enable

    def set_global_slo_flag(self, enable=True):
        '''
        Enable/disable SLO in default global vrouter config
        '''
        fq_name = [ 'default-global-system-config',
                    'default-global-vrouter-config']
        gv_obj = self.vnc_api_h.global_vrouter_config_read(fq_name=fq_name)
        gv_obj.set_enable_security_logging(enable)
        self.vnc_api_h.global_vrouter_config_update(gv_obj)
        self.logger.info('Setting global SLO flag to : %s' % (
            'True' if enable else 'False'))
        return True

    def get_global_slo_flag(self):
        '''
        Get SLO flag from default global vrouter config
        '''
        fq_name = [ 'default-global-system-config',
                    'default-global-vrouter-config']
        gv_obj = self.vnc_api_h.global_vrouter_config_read(fq_name=fq_name)
        value = gv_obj.get_enable_security_logging()
        return value
# end VncLibFixture
