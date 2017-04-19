
from common.k8s.base import BaseK8sTest
from k8s.namespace import NamespaceFixture
from tcutils.util import get_random_name
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

    @preposttest_wrapper
    def test_many_add_delete_ns(self):
        '''
        Delete and add namespace multiple times, validate that there are
        no validation errors

        #TODO
        #Need to add verifications in namespace to make this test more
        meaningful

        '''
        name = get_random_name('ns')
        for i in range(0,10):
            namespace = self.useFixture(
                NamespaceFixture(self.connections, name=name))
            assert namespace.verify_on_setup()
            self.perform_cleanup(namespace)
        # end for
    # end test_many_add_delete_ns
