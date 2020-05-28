from tcutils.util import retry, get_random_name, skip_because
from tcutils.wrappers import preposttest_wrapper
from common.contrail_fabric.base import BaseFabricTest
import random
from time import sleep
from svc_template_fixture import SvcTemplateFixture
from svc_instance_fixture import SvcInstanceFixture

role_map = {
    'crb_access': {
        'leaf': ['CRB-Access']
    },
    'crb-gateway': {
        'spine': ['CRB-Gateway', 'Route-Reflector'],
        'leaf': ['CRB-Gateway']
    },
    'dc_gw': {
        'spine': ['DC-Gateway', 'CRB-Gateway', 'Route-Reflector'],
        'leaf': ['DC-Gateway', 'CRB-Access']
    },
    'dci_gw': {
        'spine': ['DCI-Gateway', 'DC-Gateway', 'Route-Reflector'],
        'leaf': ['DCI-Gateway', 'DC-Gateway']
    },
    'pnf_service_chain': {
        'spine': ['CRB-MCAST-Gateway', 'PNF-Servicechain', 'Route-Reflector'],
        'leaf': ['PNF-Servicechain'],
        'pnf': ['PNF-Servicechain'],
    }
}

class TestFabricTrans(BaseFabricTest):
    def is_test_applicable(self):
        result, msg = super(TestFabricTrans, self).is_test_applicable()
        if result:
            msg = 'No device with dc_gw rb_role in the provided fabric topology'
            for device_dict in list(self.inputs.physical_routers_data.values()):
                if 'dc_gw' in (device_dict.get('rb_roles') or []):
                    break
            else:
                return False, msg
            msg = 'No public subnets or public host specified in test inputs yaml'
            if self.inputs.public_subnets and self.inputs.public_host:
                return (True, None)
        return False, msg

    def calculate_rb_roles(self):
        for device, device_dict in list(self.inputs.physical_routers_data.items()):
            rb_roles = set()
            for rb_role in (device_dict.get('rb_roles') or []):
                if rb_role in role_map:
                    map_e = role_map[rb_role]
                    roles = map_e.get(device_dict['role'])
                    if roles:
                        rb_roles.update(roles)
            self.rb_roles[device] = list(rb_roles)

    def setUp(self):
        self.static_ip = True
        self.calculate_rb_roles()
        super(TestFabricTrans, self).setUp()

    def _find_obj_log_entry(self, log_entries, obj_type, op_list, obj_name):
        td_list = []
        for op in op_list:
            td_list.append("{} '{}' {}".format(obj_type, obj_name, op))
        for log_entry in log_entries:
            if log_entry.get('log_entry.transaction_descr') in td_list:
                self.logger.info(
                    "Found log_entry: {}".format(log_entry.get(
                        'log_entry.transaction_descr')))
                return True
        return False

    def _find_job_log_entry(self, log_entries, job_descr):
        for log_entry in log_entries:
            if log_entry.get('log_entry.transaction_descr') == job_descr:
                self.logger.info("Found log_entry: {}".format(job_descr))
                return True
        return False

    @retry(delay=1, tries=60)
    def _verify_log_entry(self, trans_type, op_list=None, obj_name=None):
        res = self.analytics_obj.ops_inspect[
            self.inputs.collector_ips[0]].post_query(
            'StatTable.JobLog.log_entry',
            start_time='now-10m',
            end_time='now',
            select_fields=[
                'T',
                'log_entry.message',
                'log_entry.status',
                'log_entry.transaction_id',
                'log_entry.transaction_descr'],
            where_clause="(log_entry.status=STARTING)",
            sort=['T']
        )
        if op_list:
            if self._find_obj_log_entry(res, trans_type, op_list, obj_name):
                return True
        else:
            if self._find_job_log_entry(res, trans_type):
                return True

        return False

    def _get_bms_node(self, devices=None, role=None, rb_role=None):
        #return random.choice(self.get_bms_nodes())
        return self.get_bms_nodes(devices=devices, role=role, rb_role=rb_role)[1]

    @preposttest_wrapper
    def test_bgp_router(self):
        self._verify_log_entry("Existing Fabric Onboarding")
        self._verify_log_entry("Role Assignment")

        pr_fixture = self.devices[0]
        vnc = pr_fixture.vnc_h._vnc
        pr_obj = vnc.physical_router_read(id=pr_fixture.uuid)
        bgp_uuid = pr_obj.bgp_router_refs[0].get('uuid')
        bgp_obj = vnc.bgp_router_read(id=bgp_uuid)
        bgp_rtr_params = bgp_obj.bgp_router_parameters
        bgp_rtr_params.set_hold_time(100)
        bgp_obj.set_bgp_router_parameters(bgp_rtr_params)
        vnc.bgp_router_update(bgp_obj)
        status = self._verify_log_entry(
            "Bgp Router", op_list=["Update"], obj_name=bgp_obj.name)
        assert status, "BGP Router '{}' Update log missing".format(bgp_obj.name)

    @preposttest_wrapper
    def test_logical_router(self):
        vn = self.create_vn(vn_subnets=self.inputs.public_subnets[:1])
        lr = self.create_logical_router([vn], is_public_lr=True)
        status = self._verify_log_entry(
            "Logical Router", op_list=["Create", "Update"], obj_name=lr.name)
        assert status, "Logical Router '{}' log missing".format(lr.name)

        # Delete LR
        self.perform_cleanup(lr)
        status = self._verify_log_entry(
            "Logical Router", op_list=["Delete"], obj_name=lr.name)
        assert status, "Logical Router '{}' Delete log missing".format(lr.name)

    @preposttest_wrapper
    def test_virtual_port_group(self):
        target_node = self._get_bms_node()
        interfaces = self.inputs.bms_data[target_node]['interfaces'][:1]
        vn1 = self.create_vn()
        vn2 = self.create_vn()
        self.create_logical_router([vn1, vn2])
        vpg = self.create_vpg(interfaces)
        bms = self.create_bms(bms_name=target_node, interfaces=interfaces,
                          port_group_name=vpg.name, vlan_id=10,
                          vn_fixture=vn1, static_ip=self.static_ip)
        status = self._verify_log_entry(
            "Virtual Port Group", op_list=["Create"], obj_name=vpg.name)
        assert status, "VPG '{}' Create log missing".format(vpg.name)

        # Update VPG
        vn2_subnet = vn2.get_cidrs()[0]
        sg_rule_1 = self._get_secgrp_rule(protocol='tcp', dst_ports=(8004, 8006),
            cidr=vn2_subnet, direction='egress')
        sg_rule_2 = self._get_secgrp_rule(protocol='udp', dst_ports=(8004, 8006),
            cidr=vn2_subnet, direction='egress')
        sg1 = self.create_security_group(rules=[sg_rule_1, sg_rule_2])
        vpg.add_security_groups([sg1.uuid])
        status = self._verify_log_entry(
            "Virtual Port Group", op_list=["Update"], obj_name=vpg.name)
        assert status, "VPG '{}' Update log missing".format(vpg.name)

        vpg.delete_security_groups([sg1.uuid])

        # VPG delete
        self.perform_cleanup(bms)
        self.perform_cleanup(vpg)
        status = self._verify_log_entry(
            "Virtual Port Group", op_list=["Delete"], obj_name=vpg.name)
        assert status, "VPG '{}' Delete log missing".format(vpg.name)

    @preposttest_wrapper
    def test_security_group(self):
        vn1 = self.create_vn()
        vn2 = self.create_vn()
        vm1 = self.create_vm(vn_fixture=vn2, image_name='cirros-traffic')
        lr = self.create_logical_router([vn1, vn2])
        vn1_subnet = vn1.get_cidrs()[0]
        vn2_subnet = vn2.get_cidrs()[0]

        sg_rule_1 = self._get_secgrp_rule(protocol='tcp', dst_ports=(8004, 8006),
            cidr=vn2_subnet, direction='egress')
        sg_rule_2 = self._get_secgrp_rule(protocol='udp', dst_ports=(8004, 8006),
            cidr=vn2_subnet, direction='egress')
        sg_rule_3 = self._get_secgrp_rule(protocol='icmp', direction='egress')
        sg_rule_4 = self._get_secgrp_rule(protocol='udp', dst_ports=(0, 65535),
            cidr=vn1_subnet, direction='egress')

        sg1 = self.create_security_group(rules=[sg_rule_1, sg_rule_2])
        sg2 = self.create_security_group(rules=[sg_rule_3, sg_rule_4])

        bms = self._get_bms_node()
        bms1 = self.create_bms(
            bms_name=bms, vn_fixture=vn1, vlan_id=10, static_ip=self.static_ip)
        bms2 = self.create_bms(
            bms_name=bms, vn_fixture=vn2, vlan_id=20, static_ip=self.static_ip,
            bond_name=bms1.bond_name, port_group_name=bms1.port_group_name)
        bms1.add_security_groups([sg1.uuid])
        bms2.add_security_groups([sg2.uuid])

        rules = [
                {'direction': '<>',
                 'protocol': 'tcp',
                 'src_addresses': [{'security_group': 'local'}],
                 'src_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_ports': [{'start_port': 0, 'end_port': -1}],
                 'dst_addresses': [{'security_group': 'local'}],
                 }]
        sg1.create_sg_rule(sg1.uuid, rules)
        sg2.create_sg_rule(sg2.uuid, rules)
        status = self._verify_log_entry(
            "Security Group", op_list=["Update"], obj_name=sg2.secgrp_name)
        assert status, "Security Group '{}' Update log missing".format(sg2.secgrp_name)

    @skip_because(function='filter_bms_nodes', rb_role='dci_gw')
    @preposttest_wrapper
    def test_dci(self):
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')
        vn = self.create_vn()
        vn1 = self.create_vn()
        self.bms1 = self.create_bms(bms_name=random.choice(
            self.get_bms_nodes(devices=self.devices)),
            vn_fixture=vn, tor_port_vlan_tag=10, fabric_fixture=self.fabric,
            static_ip=self.static_ip)
        self.bms2 = self.create_bms(bms_name=random.choice(
            self.get_bms_nodes(devices=self.devices2)),
            vn_fixture=vn1, tor_port_vlan_tag=10, fabric_fixture=self.fabric2,
            static_ip=self.static_ip)
        devices = list()
        for device in self.devices:
            if 'dci_gw' in self.inputs.get_prouter_rb_roles(device.name):
                 devices.append(device)
        lr = self.create_logical_router([vn], devices=devices)
        devices = list()
        for device in self.devices2:
            if 'dci_gw' in self.inputs.get_prouter_rb_roles(device.name):
                 devices.append(device)
        lr1 = self.create_logical_router([vn1], devices=devices)

        dci_name = get_random_name('dci')
        dci_uuid = self.vnc_h.create_dci(dci_name, lr.uuid, lr1.uuid)

        status = self._verify_log_entry(
            "DCI", op_list=["Create"], obj_name=dci_name)
        assert status, "DCI '{}' Create log missing".format(dci_name)

        # Update DCI
        dci_obj = self.vnc_h._vnc.data_center_interconnect_read(id=dci_uuid)
        lr_obj = self.vnc_h._vnc.logical_router_read(id=lr.uuid)
        dci_obj.del_logical_router(lr_obj)
        self.vnc_h._vnc.data_center_interconnect_update(dci_obj)
        status = self._verify_log_entry(
            "DCI", op_list=["Update"], obj_name=dci_name)
        assert status, "DCI '{}' Update log missing".format(dci_name)

        dci_obj.add_logical_router(lr_obj)
        self.vnc_h._vnc.data_center_interconnect_update(dci_obj)
        sleep(30)

        # Delete DCI
        self.vnc_h.delete_dci(dci_name)
        status = self._verify_log_entry(
            "DCI", op_list=["Delete"], obj_name=dci_name)
        assert status, "DCI '{}' Delete log missing".format(dci_name)

    @skip_because(function='filter_bms_nodes', rb_role='dci_gw')
    @preposttest_wrapper
    def test_dci_single_fabric(self):
        self.inputs.set_af('dual')
        self.addCleanup(self.inputs.set_af, 'v4')
        vn = self.create_vn()
        vn1 = self.create_vn()
        bms = self._get_bms_node()
        self.bms1 = self.create_bms(bms_name=bms,
            vn_fixture=vn, tor_port_vlan_tag=10, fabric_fixture=self.fabric,
            static_ip=self.static_ip)
        self.bms2 = self.create_bms(bms_name=bms, fabric_fixture=self.fabric,
            vn_fixture=vn1, tor_port_vlan_tag=20,
            static_ip=self.static_ip)
        device = self.devices[0]
        lr = None
        if 'dci_gw' in self.inputs.get_prouter_rb_roles(device.name):
            lr = self.create_logical_router([vn], devices=[device])
        device = self.devices[1]
        lr1 = None
        if 'dci_gw' in self.inputs.get_prouter_rb_roles(device.name):
            lr1 = self.create_logical_router([vn], devices=[device])

        dci_name = get_random_name('dci')
        dci_uuid = self.vnc_h.create_dci(dci_name, lr.uuid, lr1.uuid)

        status = self._verify_log_entry(
            "DCI", op_list=["Create"], obj_name=dci_name)
        assert status, "DCI '{}' Create log missing".format(dci_name)

        # Update DCI
        dci_obj = self.vnc_h._vnc.data_center_interconnect_read(id=dci_uuid)
        lr_obj = self.vnc_h._vnc.logical_router_read(id=lr.uuid)
        dci_obj.del_logical_router(lr_obj)
        self.vnc_h._vnc.data_center_interconnect_update(dci_obj)
        status = self._verify_log_entry(
            "DCI", op_list=["Update"], obj_name=dci_name)
        assert status, "DCI '{}' Update log missing".format(dci_name)

        dci_obj.add_logical_router(lr_obj)
        self.vnc_h._vnc.data_center_interconnect_update(dci_obj)
        sleep(30)

        # Delete DCI
        self.vnc_h.delete_dci(dci_name)
        status = self._verify_log_entry(
            "DCI", op_list=["Delete"], obj_name=dci_name)
        assert status, "DCI '{}' Delete log missing".format(dci_name)

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
        sa_obj = self.vnc_h._vnc.service_appliance_read(id=sa_id)
        sa_name = sa_obj.name

        status = self._verify_log_entry(
            "Service Appliance", op_list=["Create"], obj_name=sa_name)
        assert status, "SA '{}' Create log missing".format(sa_name)

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

        status = self._verify_log_entry(
            "Service Instance", op_list=["Create"], obj_name=si_name)
        assert status, "SI '{}' Create log missing".format(si_name)

        # Delete SI
        self.vnc_h.delete_port_tuple(pt_id)
        status = self._verify_log_entry(
            "Service Instance", op_list=["Delete"], obj_name=si_name)
        assert status, "SI '{}' Delete log missing".format(si_name)

        # Delete SA
        self.vnc_h.delete_service_appliance(sa_id)
        status = self._verify_log_entry(
            "Service Appliance", op_list=["Delete"], obj_name=sa_name)
        assert status, "SA '{}' Delete log missing".format(sa_name)

    @skip_because(function='filter_bms_nodes', rb_role='pnf_service_chain')
    @preposttest_wrapper
    def test_pnf(self):
        self.left_vn = self.create_vn()
        self.right_vn = self.create_vn()
        pnf = self.pnfs[0]
        pnf_dict = self.inputs.physical_routers_data[pnf.name]
        for device in self.devices:
            if device.name == pnf_dict['left_qfx']:
                self.left_border_leaf = device
            if device.name == pnf_dict['right_qfx']:
                self.right_border_leaf = device
        bms_node = self._get_bms_node(role='pnf') # TODO: hack
        left_bms_name = right_bms_name = bms_node
        left_bms = self.create_bms(bms_name=left_bms_name,
            vlan_id=None, tor_port_vlan_tag=101,
            vn_fixture=self.left_vn, static_ip=self.static_ip)
        right_bms = self.create_bms(bms_name=right_bms_name,
            vlan_id=None, tor_port_vlan_tag=102,
            vn_fixture=self.right_vn, static_ip=self.static_ip)
        self.left_lr = self.create_logical_router([self.left_vn],
            devices=self.get_associated_prouters(left_bms_name)+\
                    [self.left_border_leaf])
        self.right_lr = self.create_logical_router([self.right_vn],
            devices=self.get_associated_prouters(right_bms_name)+\
                    [self.right_border_leaf])
        self.bms_fixtures = [left_bms, right_bms]
        self.create_l3pnf(self.left_lr, self.right_lr, pnf,
                          left_svc_vlan='1000', right_svc_vlan='2000',
                          left_svc_asn_srx='65000', left_svc_asn_qfx='65100',
                          right_svc_asn_qfx='65200')
