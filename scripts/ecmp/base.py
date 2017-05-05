import test_v1
from common.connections import ContrailConnections
from common import isolated_creds
from tcutils.util import retry

class BaseECMPTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BaseECMPTest, cls).setUpClass()
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.orch = cls.connections.orch
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseECMPTest, cls).tearDownClass()
    #end tearDownClass 

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
        #    if fix.cleanUp in cleanup:
            self._cleanups.remove(cleanup)
            #break
    #end remove_from_cleanups


    @retry(delay=1, tries=30)
    def get_svm_count(self, expected_count):
        svms = self.get_svms_in_si(
            self.si_fixtures[0], self.inputs.project_name)
        svms = sorted(set(svms))
        svms = filter(None, svms)
        if len(svms) == expected_count:
            self.logger.info('The Service VMs in the Service Instance %s are %s' % (
                self.si_fixtures[0].si_name, svms))
            return True, svms
        self.logger.warn('The SVMs count has not decreased..retrying')
        return False, False
    # end test_ecmp_with_svm_deletion
