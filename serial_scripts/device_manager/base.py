import test_v1
from common.device_connection import NetconfConnection
import physical_device_fixture
from physical_router_fixture import PhysicalRouterFixture
from tcutils.contrail_status_check import *
from fabric.api import run, hide, settings
from vn_test import VNFixture
from vm_test import VMFixture
from vnc_api.vnc_api import *
from tcutils.util import get_random_name
from scripts.securitygroup.verify import VerifySecGroup
from common import isolated_creds
from time import sleep
import os
import re

class BaseDM(VerifySecGroup):

    @classmethod
    def setUpClass(cls):
        super(BaseDM, cls).setUpClass()
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseDM, cls).tearDownClass()
    # end tearDownClass

    def setUp(self):
        super(BaseDM, self).setUp()

    def tearDown(self):
        super(BaseDM, self).tearDown()

    def config_basic(self):

        self.create_physical_dev()
        self.create_vn()
  
    def create_physical_dev(self):

        #mx config using device manager
        self.phy_router_fixture = {}
        if self.inputs.ext_routers:
#            if self.inputs.use_devicemanager_for_md5:
                j = 0
                self.mx_handle = {}
                for i in range(len(self.inputs.physical_routers_data.values())):
                    router_params = self.inputs.physical_routers_data.values()[i]
                    if router_params['model'] == 'mx':
                        self.phy_router_fixture[j] = self.useFixture(PhysicalRouterFixture(
                            router_params['name'], router_params['mgmt_ip'],
                            model=router_params['model'],
                            vendor=router_params['vendor'],
                            asn=router_params['asn'],
                            ssh_username=router_params['ssh_username'],
                            ssh_password=router_params['ssh_password'],
                            mgmt_ip=router_params['mgmt_ip'],
                            connections=self.connections))
                        self.mx_handle[j] = self.phy_router_fixture[j].get_connection_obj('juniper',
                            host=router_params['mgmt_ip'],
                            username=router_params['ssh_username'],
                            password=router_params['ssh_password'],
                            logger=[self.logger])

                        j += 1

    def create_vn(self):

        self.vn1_name = "test_vn"
        self.vn1_net = ['1.1.1.0/24']
        self.vn1_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=self.vn1_name, inputs=self.inputs, subnets=self.vn1_net))
        assert self.vn1_fixture.verify_on_setup()

    def get_output_from_node(self, cmd):
        i = 0
        self.output_from_mx = {}
        for dev_handle in self.mx_handle.values():
            self.output_from_mx[i] = dev_handle.handle.cli(cmd)
            i += 1

    def check_mx_output(self, cmd):
        self.get_output_from_node(cmd)
        i = 0
        for i in range(len(self.output_from_mx)):
            if 'invalid command' in self.output_from_mx[i]:
                return False, str(self.phy_router_fixture[i].name)
        return True, 'all mx have correct output' 

    def delete_vn_from_devices(self):

        for dev_fixture in self.phy_router_fixture.values():
            dev_fixture.delete_virtual_network(str(self.vn1_fixture.uuid))

    def delete_physical_devices(self):

        for dev_fixture in self.phy_router_fixture.values():
            dev_fixture.delete_device()

    def unbind_dev_from_router(self):

        for dev_fixture in self.phy_router_fixture.values():
            bgp_fq_name = ['default-domain', 'default-project','ip-fabric', '__default__', str(dev_fixture.name)]
            bgp_router = self.vnc_lib.bgp_router_read(fq_name=bgp_fq_name)
            dev_fixture.unbind_bgp_router(bgp_router)

    def does_mx_have_config(self, cmd):

        for i in range(1,13):
            self.op, self.bad_mx = self.check_mx_output(cmd)
            if not self.op:
                sleep(10)
            else:
                break
        self.iteration = i

    def is_dm_going_through(self):

        assert not (self.iteration == 12), "DM VN config not pushed even after 120 sec"
        assert self.op, "DM config on %s not going through. Check the MX" % self.bad_mx

    def is_dm_removed(self):

        assert not (self.iteration == 12), "DM VN config not removed even after 120 sec"
        assert self.op, "DM config on %s not removed. Check the MX" % self.bad_mx

    def remove_nc_config(self):
        for dev_fixture in self.phy_router_fixture.values():
            physical_dev = self.vnc_lib.physical_router_read(id = dev_fixture.phy_device.uuid)
            physical_dev.set_physical_router_vnc_managed(False)
            physical_dev._pending_field_updates
            self.vnc_lib.physical_router_update(physical_dev)

    def add_nc_config(self):

        for dev_fixture in self.phy_router_fixture.values():
            physical_dev = self.vnc_lib.physical_router_read(id = dev_fixture.phy_device.uuid)
            physical_dev.set_physical_router_vnc_managed(True)
            physical_dev._pending_field_updates
            self.vnc_lib.physical_router_update(physical_dev)

    def bind_dev_to_router(self):

        for dev_fixture in self.phy_router_fixture.values():
            bgp_fq_name = ['default-domain', 'default-project','ip-fabric', '__default__', str(dev_fixture.name)]
            bgp_router = self.vnc_lib.bgp_router_read(fq_name=bgp_fq_name)
            dev_fixture.add_bgp_router(bgp_router)

    def add_vn_to_device(self):

        for dev_fixture in self.phy_router_fixture.values():
            dev_fixture.add_virtual_network(str(self.vn1_fixture.uuid))

    def change_vtep(self):

        for dev_fixture in self.phy_router_fixture.values():
            physical_dev = self.vnc_lib.physical_router_read(id = dev_fixture.phy_device.uuid)
            physical_dev.set_physical_router_dataplane_ip(unicode('10.20.30.40'))
            physical_dev._pending_field_updates
            self.vnc_lib.physical_router_update(physical_dev)

    def change_vn_forwarding_mode(self, mode):

        self.vn1_fixture.add_forwarding_mode(project_fq_name=self.inputs.project_fq_name, vn_name=self.vn1_name, forwarding_mode = mode)

    def change_global_vn_config(self, mode):

        global_vrouter_id = self.vnc_lib.get_default_global_vrouter_config_id()
        global_config = self.vnc_lib.global_vrouter_config_read(id=global_vrouter_id)
        global_config.set_forwarding_mode(mode)
        self.vnc_lib.global_vrouter_config_update(global_config)

    def remove_global_vn_config(self):

        global_vrouter_id = self.vnc_lib.get_default_global_vrouter_config_id()
        global_config = self.vnc_lib.global_vrouter_config_read(id=global_vrouter_id)
        global_config.set_forwarding_mode('l2_l3')
        self.vnc_lib.global_vrouter_config_update(global_config)

    def add_vn_RT(self, value):

        self.vn1_fixture.add_route_target(self.vn1_fixture.ri_name, self.inputs.router_asn, value)

    def del_vn_RT(self, value):

        self.vn1_fixture.del_route_target(self.vn1_fixture.ri_name, self.inputs.router_asn, value)

