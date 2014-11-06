import test
from common.connections import ContrailConnections
from common import isolated_creds
from vm_test import VMFixture
from vn_test import VNFixture

class BaseVnVmTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseVnVmTest, cls).setUpClass()
        cls.isolated_creds = isolated_creds.IsolatedCreds(cls.__name__, \
				cls.inputs, ini_file = cls.ini_file, \
				logger = cls.logger)
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant() 
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.connections = cls.isolated_creds.get_conections() 
        #cls.connections= ContrailConnections(cls.inputs)
        cls.quantum_fixture= cls.connections.quantum_fixture
        cls.nova_fixture = cls.connections.nova_fixture
        cls.vnc_lib= cls.connections.vnc_lib
#        cls.logger= cls.inputs.logger
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        cls.api_s_inspect = cls.connections.api_server_inspect
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        #cls.isolated_creds.delete_user()
        cls.isolated_creds.delete_tenant()
        super(BaseVnVmTest, cls).tearDownClass()
    #end tearDownClass 

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
        #    if fix.cleanUp in cleanup:
            self._cleanups.remove(cleanup)
            #break
   #end remove_from_cleanups

    def create_vn(self, vn_name, vn_subnets):
        return self.useFixture(
                VNFixture(project_name=self.inputs.project_name,
                          connections=self.connections,
                          inputs=self.inputs,
                          vn_name=vn_name,
                          subnets=vn_subnets))
    
    def create_vm(self, vn_fixture, vm_name, node_name=None,
                    flavor='contrail_flavor_small',
                    image_name='ubuntu-traffic'):
        return self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_obj=vn_fixture.obj,
                    vm_name=vm_name,
                    image_name=image_name,
                    flavor=flavor,
                    node_name=node_name))

