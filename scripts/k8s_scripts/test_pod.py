
from common.k8s.base import BaseK8sTest
from k8s.pod import PodFixture
from tcutils.wrappers import preposttest_wrapper

class TestPod(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestPod, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestPod, cls).tearDownClass()

    @preposttest_wrapper
    def test_add_delete_pod(self):
        ''' 
        Test add and delete of  POD 
        '''
        pod  = self.useFixture(PodFixture(self.connections))
        assert pod.verify_on_setup()

    # end test_add_delete_pod
        

