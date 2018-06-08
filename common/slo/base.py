from common.sessionlogging.base import *
from slo_fixture import SLOFixture
from vnc_api.vnc_api import *

class SloBase(SessionLoggingBase):

    @classmethod
    def setUpClass(cls):
        super(SloBase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(SloBase, cls).tearDownClass()

    def create_slo(self, parent_obj=None, rate=None, sg_obj=None,
            vn_policy_obj=None, rules_list=None):
        '''
            parent_obj: global-vrouter-config or tenant
            rules_list: list of dict of rule uuid and slo rate, {'uuid':<uuid>,
                'rate':<rate>}
        '''
        sg_refs = None
        vn_policy_refs = None
        slo_rule_list_obj = None
        if sg_obj:
            ref_data = SecurityLoggingObjectRuleListType()
            sg_refs = [{'obj':sg_obj, 'ref_data':ref_data}]

        if vn_policy_obj:
            ref_data = SecurityLoggingObjectRuleListType()
            vn_policy_refs  = [{'obj':vn_policy_obj, 'ref_data':ref_data}]

        if rules_list:
            slo_rule_entry_list = []
            for rule in rules_list:
                slo_rule_entry = SecurityLoggingObjectRuleEntryType(
                    rule_uuid=rule['uuid'], rate=rule['rate'])
                slo_rule_entry_list.append(slo_rule_entry)
            slo_rule_list_obj = SecurityLoggingObjectRuleListType(
                rule=slo_rule_entry_list)

        slo_fixture = self.useFixture(
            SLOFixture(
                parent_obj=parent_obj, connections=self.connections,
                sg_refs=sg_refs, vn_policy_refs=vn_policy_refs, rate=rate,
                rules=slo_rule_list_obj))

        slo_fixture.verify_on_setup()
        return slo_fixture

    def update_slo(self, slo_obj, new_rules_list):
        '''
            rules_list: list of dict of rule uuid and slo rate, {'uuid':<uuid>,
                'rate':<rate>}
        '''
        slo_rule_list_obj = None

        if new_rules_list:
            slo_rule_entry_list = []
            for rule in new_rules_list:
                slo_rule_entry = SecurityLoggingObjectRuleEntryType(
                    rule_uuid=rule['uuid'], rate=rule['rate'])
                slo_rule_entry_list.append(slo_rule_entry)
            slo_rule_list_obj = SecurityLoggingObjectRuleListType(
                rule=slo_rule_entry_list)

        slo_obj.security_logging_object_rules = slo_rule_list_obj
        self.vnc_h.security_logging_object_update(slo_obj)

    def add_slo_to_vn(self, slo_fixture, vn_fixture, cleanup=True):
        '''Add the SLO to VN'''
        slo_ref_list_old = vn_fixture.get_slo_list()
        vn_fixture.add_slo(slo_fixture.obj)

        if cleanup:
            self.addCleanup(vn_fixture.set_slo_list, slo_ref_list_old)

    def add_slo_to_vmi(self, slo_fixture, vmi_id, cleanup=True):
        '''Add the SLO to VMI'''
        vmi_obj = self.vnc_h.virtual_machine_interface_read(id=vmi_id)
        slo_ref_list_old = vmi_obj.get_security_logging_object_refs()
        vmi_obj.add_security_logging_object(slo_fixture.obj)

        self.vnc_h.virtual_machine_interface_update(vmi_obj)
        if cleanup:
            self.addCleanup(self.set_slo_list_to_vmi, slo_ref_list_old, vmi_id)

    def set_slo_list_to_vmi(self, slo_obj_list, vmi_id):
        '''Set SLO list to VMI'''
        vmi_obj = self.vnc_h.virtual_machine_interface_read(id=vmi_id)
        vmi_obj.set_security_logging_object_list(slo_obj_list)

        self.vnc_h.virtual_machine_interface_update(vmi_obj)

    def set_global_slo_flag(self, enable=True, cleanup=True):
        '''
        Enable/disable SLO in default global vrouter config
        '''
        vnc_lib_fixture = self.connections.vnc_lib_fixture
        current_value = vnc_lib_fixture.get_global_slo_flag()
        if current_value == enable:
            return True
        vnc_lib_fixture.set_global_slo_flag(enable)
        if cleanup:
            self.addCleanup(vnc_lib_fixture.set_global_slo_flag, current_value)
