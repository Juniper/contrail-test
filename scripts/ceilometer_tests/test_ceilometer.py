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
        cls.res.setUp(cls.inputs, cls.connections, cls.public_vn_obj)
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
    def test_resources_by_admin_tenant(self):
        """Verifying ceilometer resources - admin tenant"""
        tenant_id = self.auth.get_project_id('admin')
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
            
    @preposttest_wrapper
    def test_resources_by_user_tenant(self):
        """Verifying ceilometer resources - user tenant"""
        tenant_id = self.auth.get_project_id(self.inputs.project_name)
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
        r1 = None
        for resource in result:
            if (resource.resource_id == self.res.vm1_fixture.vm_id):
                self.logger.info("VM shown as resource list ")
                r1 = True
            else:
                continue
        if not r1:
            self.logger.error("VM NOT shown as resource list ")
            assert False 
        return True

    @test.attr(type=['sanity']) 
    @preposttest_wrapper
    def test_sample_floating_ip_transmit_packets(self):
        """
        Verifying ceilometer sample - ip.floating.transmit.packets
        Verifying ceilometer sample - ip.floating.receive.packets
        Verifying ceilometer sample - ip.floating.transmit.bytes
        Verifying ceilometer sample - ip.floating.receive.bytes"""

        self.logger.info('Sleeping for 1 mins for sample to be collected...')
        time.sleep(60)
        self.logger.info('Starting verification...')
        tenant_id = self.auth.get_project_id(self.inputs.project_name)
        tenant_id = "".join(tenant_id.split('-')) 
        q = ceilometer_client.make_query(resource_id = self.res.vm1_fixture.vm_id)
        result = None
        #result =  ceilometer_client.sample_list(self.cclient,'ip.floating.transmit.packets',\
        #                                    query = q) 
        meters = ['ip.floating.transmit.packets','ip.floating.receive.packets',\
                    'ip.floating.transmit.bytes','ip.floating.receive.bytes']
        for m in meters:
            result =  ceilometer_client.sample_list(self.cclient,m)
            if not result:
                self.logger.error("Ceilometer sample list did not work...")
                assert False
            if result:
                self.logger.info("Ceilometer sample list did  work for meter %s..."%(m))
                assert True
            r1 = None
            for sample in result:
                metadata = sample.resource_metadata
                if (metadata['device_id'] == self.res.vm1_fixture.vm_id):
                    r1 = sample
                else:
                    continue
            if not r1:
                self.logger.error("%s meter did not show up in sample list "%(m))
                assert False
            else:
                self.logger.info("%s meter volumn %s"%(m,r1.counter_volume)) 
        return True

