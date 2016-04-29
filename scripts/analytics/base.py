import test_v1
from common import isolated_creds
from vn_test import *
from vm_test import *
import fixtures

class AnalyticsBaseTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(AnalyticsBaseTest, cls).setUpClass()
        cls.orch = cls.connections.orch
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        resource_class = cls.__name__ + 'Resource'
        cls.res = ResourceFactory.createResource(resource_class)
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.res.cleanUp()
        super(AnalyticsBaseTest, cls).tearDownClass()
    #end tearDownClass

class ResourceFactory:
    factories = {}
    def createResource(id):
        if not ResourceFactory.factories.has_key(id):
            ResourceFactory.factories[id] = \
              eval(id + '.Factory()')
        return ResourceFactory.factories[id].create()
    createResource = staticmethod(createResource)


class BaseResource(fixtures.Fixture):
    
    def setUp(self,inputs,connections):
        super(BaseResource , self).setUp()
        self.inputs = inputs
        self.connections = connections
        self.setup_common_objects(self.inputs , self.connections)

    def cleanUp(self):
        super(BaseResource, self).cleanUp() 

    def setup_common_objects(self, inputs , connections):
  
	self.inputs = inputs
	self.connections = connections
        (self.vn1_name, self.vn1_subnets)= (get_random_name("vn1"), ["192.168.1.0/24"])
        (self.vn2_name, self.vn2_subnets)= (get_random_name("vn2"), ["192.168.2.0/24"])
        (self.fip_vn_name, self.fip_vn_subnets)= (get_random_name("fip_vn"), ['100.1.1.0/24'])
        (self.vn1_vm1_name, self.vn1_vm2_name)=(get_random_name('vn1_vm1'), get_random_name('vn1_vm2'))
        self.vn2_vm1_name= get_random_name('vn2_vm1')
        self.vn2_vm2_name= get_random_name('vn2_vm2')
        self.fvn_vm1_name= get_random_name('fvn_vm1')

        # Configure 3 VNs, one of them being Floating-VN
        self.vn1_fixture=self.useFixture( VNFixture(project_name= self.inputs.project_name,
                            connections= self.connections, inputs= self.inputs,
                            vn_name= self.vn1_name, subnets= self.vn1_subnets))

        self.vn2_fixture=self.useFixture( VNFixture(project_name= self.inputs.project_name,
                            connections= self.connections, inputs= self.inputs,
                            vn_name= self.vn2_name, subnets= self.vn2_subnets))

        self.fvn_fixture=self.useFixture( VNFixture(project_name= self.inputs.project_name,
                            connections= self.connections, inputs= self.inputs,
                            vn_name= self.fip_vn_name, subnets= self.fip_vn_subnets))

        # Making sure VM falls on diffrent compute host
        host_list = self.connections.orch.get_hosts()
        compute_1 = host_list[0]
        compute_2 = host_list[0]
        if len(host_list) > 1:
            compute_1 = host_list[0]
            compute_2 = host_list[1]
        # Configure 6 VMs in VN1, 1 VM in VN2, and 1 VM in FVN
        self.vn1_vm1_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,
                                connections= self.connections, vn_obj= self.vn1_fixture.obj,
                                vm_name= self.vn1_vm1_name,image_name='ubuntu-traffic',
				flavor='contrail_flavor_medium', node_name=compute_1))

        self.vn1_vm2_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,
                                connections= self.connections, vn_obj= self.vn1_fixture.obj,
                                vm_name= self.vn1_vm2_name , image_name='ubuntu-traffic',
				flavor='contrail_flavor_medium'))

        self.vn2_vm2_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,
                            connections= self.connections, vn_obj= self.vn2_fixture.obj,
                            vm_name= self.vn2_vm2_name, image_name='ubuntu-traffic', flavor='contrail_flavor_medium',
                            node_name=compute_2))
#
        self.fvn_vm1_fixture=self.useFixture(VMFixture(project_name= self.inputs.project_name,
                                connections= self.connections, vn_obj= self.fvn_fixture.obj,
                                vm_name= self.fvn_vm1_name))
    
        self.verify_common_objects()
    #end setup_common_objects

    def verify_common_objects(self):
        assert self.vn1_fixture.verify_on_setup()
        assert self.vn2_fixture.verify_on_setup()
        assert self.fvn_fixture.verify_on_setup()
        assert self.vn1_vm1_fixture.verify_on_setup()
        assert self.vn2_vm2_fixture.verify_on_setup()
    #end verify_common_objects

class AnalyticsBasicTestSanityResource (BaseResource):

    def setUp(self,inputs,connections):
        pass
        #super(AnalyticsTestSanityResource , self).setUp(inputs,connections)

    def cleanUp(self):
        pass
        #super(AnalyticsTestSanityResource, self).cleanUp()

    class Factory:
        def create(self): return AnalyticsBasicTestSanityResource()


class AnalyticsTestSanityResource (BaseResource):

    def setUp(self,inputs,connections):
        pass
        #super(AnalyticsTestSanity1Resource , self).setUp(inputs,connections)

    def cleanUp(self):
        pass
        #super(AnalyticsTestSanity1Resource, self).cleanUp()

    class Factory:
        def create(self): return AnalyticsTestSanityResource()


class AnalyticsTestSanity1Resource (BaseResource):

    def setUp(self,inputs,connections):
        pass
        #super(AnalyticsTestSanity1Resource , self).setUp(inputs,connections)

    def cleanUp(self):
        pass
        #super(AnalyticsTestSanity1Resource, self).cleanUp()

    class Factory:
        def create(self): return AnalyticsTestSanity1Resource()


class AnalyticsTestSanity2Resource (BaseResource):

    def setUp(self,inputs,connections):
        pass
        #super(AnalyticsTestSanity2Resource , self).setUp(inputs,connections)

    def cleanUp(self):
        pass
        #super(AnalyticsTestSanity2Resource, self).cleanUp()

    class Factory:
        def create(self): return AnalyticsTestSanity2Resource()

class AnalyticsTestSanity3Resource (BaseResource):

    def setUp(self,inputs,connections):
        pass
        #super(AnalyticsTestSanity3Resource , self).setUp(inputs,connections)

    def cleanUp(self):
        pass
        #super(AnalyticsTestSanity3Resource, self).cleanUp()

    class Factory:
        def create(self): return AnalyticsTestSanity3Resource()

class AnalyticsTestSanityWithResourceResource(BaseResource):

    def setUp(self,inputs,connections):
        super(AnalyticsTestSanityWithResourceResource , self).setUp(inputs,connections)

    def cleanUp(self):
        super(AnalyticsTestSanityWithResourceResource, self).cleanUp()

    class Factory:
        def create(self): return AnalyticsTestSanityWithResourceResource()
#End resource

