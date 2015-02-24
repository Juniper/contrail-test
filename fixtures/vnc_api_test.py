import fixtures
from vnc_api.vnc_api import *
#from contrail_fixtures import contrail_fix_ext

#@contrail_fix_ext (ignore_verify=True, ignore_verify_on_setup=True)


class VncLibFixture(fixtures.Fixture):

    def __init__(self, domain, project, cfgm_ip, api_port, inputs, username='admin', password='contrail123'):
        self.username = username
        self.password = password
        self.project = project
        self.domain = domain
        self.api_server_port = api_port
        self.cfgm_ip = cfgm_ip
        self.inputs = inputs
        self.logger = inputs.logger
        self.obj = None
    # end __init__

    def setUp(self):
        super(VncLibFixture, self).setUp()
        self.obj = VncApi(
            username=self.username, password=self.password, tenant_name=self.project,
            api_server_host=self.cfgm_ip, api_server_port=self.api_server_port)
    # end setUp

    def cleanUp(self):
        super(VncLibFixture, self).cleanUp()

    def get_handle(self):
        return self.obj
    # end get_handle

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

    def id_to_fq_name(self, id):
        return self.obj.id_to_fq_name(id)

# end VncLibFixture1
