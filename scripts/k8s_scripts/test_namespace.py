
from common.k8s.base import BaseK8sTest
from k8s.namespace import NamespaceFixture
from tcutils.wrappers import preposttest_wrapper

class TestNamespace(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestNamespace, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestNamespace, cls).tearDownClass()

    @preposttest_wrapper
    def test_namespace_1(self):
        ''' Create and delete a namespace 
        '''
        namespace = self.useFixture(NamespaceFixture(self.connections))
        assert namespace.verify_on_setup()

    # end test_namespace_1
        

