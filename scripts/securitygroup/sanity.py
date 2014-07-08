from securitygroup.sanity_base import SecurityGroupSanityTestsBase


class SecurityGroupSanityTests(SecurityGroupSanityTestsBase):

    def setUp(self):
        super(SecurityGroupSanityTests, self).setUp()

    def cleanUp(self):
        super(SecurityGroupSanityTests, self).cleanUp()

    # Any new testcases outside of SecurityGroupSanityTestsBase tests go here

if __name__ == '__main__':
    unittest.main()
