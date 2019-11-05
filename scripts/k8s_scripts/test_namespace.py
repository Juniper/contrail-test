from builtins import range
import test
from common.k8s.base import BaseK8sTest
from k8s.namespace import NamespaceFixture
from tcutils.util import get_random_name, retry
from tcutils.wrappers import preposttest_wrapper

class TestNamespace(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestNamespace, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestNamespace, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)

    @test.attr(type=['openshift_1', 'ci_contrail_go_k8s_sanity'])
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
        @retry(delay=3, tries=2)
        def check_namespace_creation():
            namespace = self.useFixture(
                NamespaceFixture(self.connections, name=name))
            result = namespace.verify_on_setup()
            self.perform_cleanup(namespace)
            return result
        for i in range(0,10):
           assert check_namespace_creation()
        # end for
    # end test_many_add_delete_ns
