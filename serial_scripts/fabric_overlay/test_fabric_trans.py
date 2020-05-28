from tcutils.util import retry
from tcutils.wrappers import preposttest_wrapper
from common.contrail_fabric.base import BaseFabricTest
import random

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

    def setUp(self):
        for device, device_dict in list(self.inputs.physical_routers_data.items()):
            if 'dc_gw' in (device_dict.get('rb_roles') or []):
                if device_dict['role'] == 'spine':
                    self.rb_roles[device] = ['DC-Gateway', 'Route-Reflector']
                    if 'qfx' in device_dict.get('model', 'qfx'):
                        self.rb_roles[device].append('CRB-Gateway')
                elif device_dict['role'] == 'leaf':
                    self.rb_roles[device] = ['DC-Gateway', 'CRB-Access']
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

    @preposttest_wrapper
    def test_logical_router(self):
        self._verify_log_entry("Existing Fabric Onboarding")
        self._verify_log_entry("Role Assignment")
        vn = self.create_vn(vn_subnets=self.inputs.public_subnets[:1])
        lr = self.create_logical_router([vn], is_public_lr=True)
        assert self._verify_log_entry(
            "Logical Router",op_list=["Create", "Update"], obj_name=lr.name)

    @preposttest_wrapper
    def test_virtual_port_group(self):
        target_node = random.choice(self.get_bms_nodes())
        interfaces = self.inputs.bms_data[target_node]['interfaces'][:1]
        vn1 = self.create_vn()
        vn2 = self.create_vn()
        self.create_logical_router([vn1, vn2])
        vpg = self.create_vpg(interfaces)
        try:
            bms = self.create_bms(bms_name=target_node, interfaces=interfaces,
                              port_group_name=vpg.name, vlan_id=10,
                              vn_fixture=vn1)
        except Exception as ex:
            self.logger.info("Ignoring BMS creation error: {}".format(ex))

        assert self._verify_log_entry(
            "Virtual Port Group", op_list=["Create"], obj_name=vpg.name)
