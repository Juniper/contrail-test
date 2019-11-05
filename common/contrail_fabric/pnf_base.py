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

    def is_test_applicable(self):
        result, msg = super(BaseL3PnfTest, self).is_test_applicable()
        if result:
            msg = 'No device with pnf_service_chain rb_role in the provided topology'
            msg_erb = 'No device with erb_ucast_gw rb_role in the provided topology'
            erb = pnf = False
            for device_dict in list(self.inputs.physical_routers_data.values()):
                if 'pnf_service_chain' in (device_dict.get('rb_roles') or []):
                    pnf = True; msg = msg_erb
                elif 'erb_ucast_gw' in (device_dict.get('rb_roles') or []):
                    erb = True
                if erb and pnf:
                    return True, None
        return False, msg

    def setUp(self):
        for device_name, device_dict in list(self.inputs.physical_routers_data.items()):
            if 'pnf_service_chain' in (device_dict.get('rb_roles') or []):
                if device_dict['role'] == 'spine':
                    self.rb_roles[device_name] = ['Route-Reflector',
                        'CRB-MCAST-Gateway', 'PNF-Servicechain']
                elif device_dict['role'] == 'leaf':
                    self.rb_roles[device_name] = ['CRB-MCAST-Gateway',
                        'PNF-Servicechain']
            elif device_dict['role'] == 'spine':
                self.rb_roles[device_name] = ['Route-Reflector', 'null']
            elif device_dict['role'] == 'pnf':
                self.rb_roles[device_name] = ['PNF-Servicechain']
            elif 'erb_ucast_gw' in (device_dict.get('rb_roles') or []):
                self.rb_roles[device_name] = ['ERB-UCAST-Gateway']
        super(BaseL3PnfTest, self).setUp()

    def create_l3pnf(self, left_lr, right_lr,
                     pnf_device, 
                     left_svc_vlan='1000',
                     right_svc_vlan='2000',
                     left_svc_asn_srx='65000',
                     left_svc_asn_qfx='65100',
                     right_svc_asn_qfx='65200'):
        virtualization_type = 'physical-device'
        device_dict = self.inputs.physical_routers_data[pnf_device.name]
        left_intf = device_dict['local_left_intf']
        right_intf = device_dict['local_right_intf']
        left_qfx = device_dict['left_qfx']
        right_qfx = device_dict['right_qfx']
        left_qfx_intf = device_dict['left_qfx_intf']
        right_qfx_intf = device_dict['right_qfx_intf']
        sas_id = self.vnc_h.create_service_appliance_set(
            virtualization_type=virtualization_type)
        self.addCleanup(self.vnc_h.delete_service_appliance_set, sas_id)
        st_name = get_random_name('pnf_st')
        if_details = {'left': dict(), 'right': dict()}
        st_fixture = self.useFixture(SvcTemplateFixture(
            self.connections, st_name, 'firewall', if_details,
            virtualization_type=virtualization_type,
            service_appliance_set=sas_id))
        sa_id = self.vnc_h.create_service_appliance_pnf(
            sas_id, pnf_device.name, left_intf, right_intf,
            left_qfx, left_qfx_intf, right_qfx, right_qfx_intf,
            virtualization_type=virtualization_type)
        self.addCleanup(self.vnc_h.delete_service_appliance, sa_id)
        si_name = get_random_name('pnf_si')
        si_fixture = self.useFixture(SvcInstanceFixture(
            self.connections, si_name, st_fixture.st_obj,
            if_details, virtualization_type=virtualization_type,
            left_svc_vlan=left_svc_vlan, right_svc_vlan=right_svc_vlan,
            left_svc_asn_srx=left_svc_asn_srx,
            left_svc_asn_qfx=left_svc_asn_qfx,
            right_svc_asn_qfx=right_svc_asn_qfx))
        si_id = si_fixture.si_obj.uuid
        pt_id = self.vnc_h.create_port_tuple_pnf(si_id, left_lr, right_lr)
        self.addCleanup(self.vnc_h.delete_port_tuple, pt_id)
        self.logger.info("waiting for the configs to be pushed")
        self.sleep(120)
