from time import sleep
from vn_test import *
from vm_test import *
from quantum_test import *
from vnc_api_test import *
from vnc_api.vnc_api import *
from nova_test import *
from string import Template
import re
from tcutils.tcpdump_utils import *
from tcutils.wrappers import preposttest_wrapper
from contrailapi import ContrailVncApi
from bms_fixture import BMSFixture
from physical_router_fixture import PhysicalRouterFixture
from router_fixture import LogicalRouterFixture
from svc_template_fixture import SvcTemplateFixture
from svc_instance_fixture import SvcInstanceFixture
from common.contrail_fabric.base import BaseFabricTest
import ipaddress


class BaseL3PnfTest(BaseFabricTest):

    def setUp(self):
        for device_name, device_dict in self.inputs.physical_routers_data.items():
            if device_dict['role'] == 'spine':
                self.rb_roles[device_name] = ['Route-Reflector', 'null']
            if device_dict['role'] == 'pnf':
                self.rb_roles[device_name] = ['PNF-Servicechain']
            if device_dict['role'] == 'border_leaf':
                self.rb_roles[device_name] = [
                    'CRB-MCAST-Gateway', 'PNF-Servicechain']
            if device_dict['role'] == 'erb_leaf':
                self.rb_roles[device_name] = ['ERB-UCAST-Gateway']
        super(BaseL3PnfTest, self).setUp()
        self.pnf_vnc_handle = ContrailVncApi(self.vnc_lib, self.logger)

    def create_and_extend_lr(self, vn_fixture, devices):
        vn_ids = [vn_fixture.uuid]
        lr = self.useFixture(LogicalRouterFixture(
            connections=self.connections,
            connected_networks=vn_ids))
        for device in devices:
            lr.add_physical_router(device.uuid)
        return lr

    def create_l3pnf(self, left_lr, right_lr, left_attachment_point, right_attachment_point, pnf_left_intf, pnf_right_intf, left_svc_vlan='1000',
                     right_svc_vlan='2000',
                     left_svc_asn_srx='65000',
                     left_svc_asn_qfx='65100',
                     right_svc_asn_qfx='65200'):
        virtualization_type = 'physical-device'
        sas_id = self.pnf_vnc_handle.create_service_appliance_set(
            virtualization_type=virtualization_type)
        self.addCleanup(
            self.pnf_vnc_handle.delete_service_appliance_set, sas_id)
        st_name = get_random_name('pnf_st')
        if_details = {}
        if_details['left'] = {}
        if_details['right'] = {}
        st_fixture = self.useFixture(SvcTemplateFixture(
            self.connections,
            st_name, 'firewall', if_details, virtualization_type=virtualization_type, service_appliance_set=sas_id))
        assert st_fixture.verify_on_setup()
        sa_id = self.pnf_vnc_handle.create_service_appliance(
            sas_id, left_attachment_point, right_attachment_point, pnf_left_intf, pnf_right_intf, virtualization_type=virtualization_type)
        self.addCleanup(self.pnf_vnc_handle.delete_service_appliance, sa_id)
        si_name = get_random_name('pnf_si')
        si_fixture = self.useFixture(SvcInstanceFixture(
            self.connections,
            si_name,
            st_fixture.st_obj,
            if_details,
            virtualization_type=virtualization_type,
            left_svc_vlan=left_svc_vlan,
            right_svc_vlan=right_svc_vlan,
            left_svc_asn_srx=left_svc_asn_srx,
            left_svc_asn_qfx=left_svc_asn_qfx,
            right_svc_asn_qfx=right_svc_asn_qfx))
        si_id = si_fixture.si_obj.uuid
        pt_id = self.pnf_vnc_handle.create_port_tuple(si_id, left_lr, right_lr)
        self.addCleanup(self.pnf_vnc_handle.delete_port_tuple, pt_id)
        self.logger.info("waiting for the configs to be pushed correctly")
        time.sleep(120)
