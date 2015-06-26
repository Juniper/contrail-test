import os
import time
from tcutils.wrappers import preposttest_wrapper
from ceilometer_tests import base
from ceilometer import ceilometer_client
from openstack import OpenstackAuth

import test


class CeilometerTest(
        base.CeilometerBaseTest):

    @classmethod
    def setUpClass(cls):
        super(CeilometerTest, cls).setUpClass()
        cls.res.setUp(cls.inputs, cls.connections)
        cls.auth = OpenstackAuth(cls.inputs.stack_user,
                              cls.inputs.stack_password,
                              cls.inputs.project_name, cls.inputs, cls.logger)
        cls.auth_url = cls.auth.auth_url
        cls.c_url = 'http://%s:8777/'%cls.inputs.openstack_ip
        cls.cclient = ceilometer_client.CeilometerClient(cls.auth_url, 
                                 cls.inputs.stack_user,
                                 cls.inputs.stack_password,
                                 'admin',
                                 cls.c_url,
                                 insecure = True)
        cls.cclient = cls.cclient.get_cclient() 

    @classmethod
    def tearDownClass(cls):
        cls.res.cleanUp()
        super(CeilometerTest, cls).tearDownClass()
    # end tearDownClass

    def runTest(self):
        pass
    # end runTest

    @preposttest_wrapper
    def test_meters(self):
        """Verifying ceilometer meters"""
        tenant_id = self.auth.get_project_id('default_domain',
                                              'admin')
        tenant_id = "".join(tenant_id.split('-')) 
        q = ceilometer_client.make_query(tenant_id = tenant_id)
        result = None
        result =  ceilometer_client.resource_list(self.cclient,query=q) 
        if not result:
            self.logger.error("Ceilometer resource list did not work...")
            assert False
        if result:
            self.logger.info("Ceilometer resource list did  work...")
            assert True
        return True
            
