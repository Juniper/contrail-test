import testtools


class ParametrizedTestCase(testtools.TestCase):

    """ TestCase classes that want to be parametrized should
        inherit from this class.
        Test cases based on this class can take advantage of
        receiving different topology[scenarios] for running the test.
        Refer to custom_sanity_tests.py for sample tests.
    """

    def __init__(self, methodName='runTest', topology=None):
        super(ParametrizedTestCase, self).__init__(methodName)
        self.topology = topology

    @staticmethod
    def parametrize(feature_test_class, topology=None):
        """ Create a suite containing all tests taken from the given
            subclass, passing 'topolgy' as parameter.
        """
        testloader = unittest.TestLoader()
        testnames = testloader.getTestCaseNames(feature_test_class)
        suite = unittest.TestSuite()
        for name in testnames:
            suite.addTest(feature_test_class(name, topology=topology))
        return suite
