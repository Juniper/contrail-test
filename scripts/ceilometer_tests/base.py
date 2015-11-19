import test
from common import isolated_creds
from vn_test import *
from vm_test import *
import fixtures
from tcutils.util import Singleton
from common import create_public_vn
from openstack import OpenstackAuth

class CeilometerBaseTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(CeilometerBaseTest, cls).setUpClass()
        cls.auth = OpenstackAuth(cls.inputs.stack_user,
                              cls.inputs.stack_password,
                              cls.inputs.project_name, cls.inputs, cls.logger)
        if not cls.auth.verify_service_enabled('ceilometer'):
            inst = cls()
            raise inst.skipTest(
                "Skipping Test.Ceilometer not enabled in the setup")
        cls.isolated_creds = isolated_creds.IsolatedCreds(cls.__name__, cls.inputs, ini_file = cls.ini_file, logger = cls.logger)
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant() 
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.connections = cls.isolated_creds.get_conections() 
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        cls.public_vn_obj = create_public_vn.PublicVn(
             cls.__name__,
             cls.__name__,
             cls.inputs,
             ini_file=cls.ini_file,
             logger=cls.logger)
        cls.public_vn_obj.configure_control_nodes()

        resource_class = cls.__name__ + 'Resource'
        cls.res = ResourceFactory.createResource(resource_class)
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.res.cleanUp()
        cls.isolated_creds.delete_tenant()
        super(CeilometerBaseTest, cls).tearDownClass()
    #end tearDownClass

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            if fix.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break
    #end remove_from_cleanups

class ResourceFactory:
    factories = {}
    def createResource(id):
        if not ResourceFactory.factories.has_key(id):
            ResourceFactory.factories[id] = \
              eval(id + '.Factory()')
        return ResourceFactory.factories[id].create()
    createResource = staticmethod(createResource)


class BaseResource(fixtures.Fixture):
   
#    __metaclass__ = Singleton
     
    def setUp(self,inputs,connections,public_vn_obj):
        super(BaseResource , self).setUp()
        self.inputs = inputs
        self.connections = connections
        self.public_vn_obj = public_vn_obj
        self.setup_common_objects(self.inputs , self.connections)

    def cleanUp(self):
        super(BaseResource, self).cleanUp() 

    def setup_common_objects(self, inputs , connections):
  
    	self.inputs = inputs
        #self.inputs.set_af('dual')
        self.connections = connections
        self.logger = self.inputs.logger
        fip_pool_name = self.inputs.fip_pool_name
        fvn_name = 'public'
        fip_subnets = [self.inputs.fip_pool]
        vm1_name = 'vm200'
        vn1_name = 'vn200'
        vn1_subnets = ['11.1.1.0/24']
        self.vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name=vn1_name,
                inputs=inputs,
                subnets=vn1_subnets))
        assert self.vn1_fixture.verify_on_setup()
        self.vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=self.vn1_fixture.obj,
                vm_name=vm1_name))
        assert self.vm1_fixture.verify_on_setup()

        # Adding further projects to floating IP.
        self.logger.info('Adding project %s to FIP pool %s' %
                         (self.inputs.project_name, fip_pool_name))
        project_obj = self.public_vn_obj.fip_fixture.assoc_project\
                        (self.inputs.project_name)

        fip_id = self.public_vn_obj.fip_fixture.create_and_assoc_fip(
            self.public_vn_obj.public_vn_fixture.vn_id, self.vm1_fixture.vm_id, project_obj)
        self.addCleanup(self.public_vn_obj.fip_fixture.disassoc_and_delete_fip, fip_id)

        assert self.public_vn_obj.fip_fixture.verify_fip(fip_id, self.vm1_fixture,
                self.public_vn_obj.public_vn_fixture)

        self.vm1_fixture.wait_till_vm_up()
        assert self.vm1_fixture.ping_with_certainty('8.8.8.8')
        assert self.vm1_fixture.ping_to_ip('8.8.8.8',count = '10')
        # Removing further projects from floating IP pool. For cleanup
        self.logger.info('Removing project %s to FIP pool %s' %
                    (self.inputs.project_name, fip_pool_name))
        project_obj = self.public_vn_obj.fip_fixture.deassoc_project\
                    (self.inputs.project_name)
    
    #end setup_common_objects


class CeilometerTestResource (BaseResource): 

    def setUp(self,inputs,connections,public_vn_obj):
        super(CeilometerTestResource , self).setUp(inputs,connections,public_vn_obj)

    def cleanUp(self):
        super(CeilometerTestResource, self).cleanUp()

    class Factory:
        def create(self): return CeilometerTestResource()


#End resource


