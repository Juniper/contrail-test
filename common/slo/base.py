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

    def create_slo(self, parent_obj, rate=None, sg_obj=None, vn_policy_obj=None
            ):
        '''
            parent_obj: global-vrouter-config or tenant
        '''
        sg_refs = None
        vn_policy_refs = None
        if sg_obj:
            ref_data = SecurityLoggingObjectRuleListType()
            sg_refs = [{'obj':sg_obj, 'ref_data':ref_data}]

        if vn_policy_obj:
            ref_data = SecurityLoggingObjectRuleListType()
            vn_policy_refs  = [{'obj':vn_policy_obj, 'ref_data':ref_data}]

        slo_fixture = self.useFixture(
            SLOFixture(
                parent_obj=parent_obj, connections=self.connections,
                sg_refs=sg_refs, vn_policy_refs=vn_policy_refs, rate=rate))

        slo_fixture.verify_on_setup()
        return slo_fixture

    def add_slo_to_vn(self, slo_fixture, vn_fixture, cleanup=True):
        '''Add the SLO to VN'''
        slo_ref_list_old = vn_fixture.get_slo_list()
        vn_fixture.add_slo(slo_fixture.obj)

        if cleanup:
            self.addCleanup(vn_fixture.set_slo_list, slo_ref_list_old)
