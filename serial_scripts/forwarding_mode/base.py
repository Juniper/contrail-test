import test
from common.connections import ContrailConnections
from common import isolated_creds
from vm_test import VMFixture
from vn_test import VNFixture


class BaseForwardingMode(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseForwardingMode, cls).setUpClass()
        cls.isolated_creds = isolated_creds.IsolatedCreds(cls.__name__, \
                cls.inputs, ini_file = cls.ini_file, \
                logger = cls.logger)
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant() 
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.inputs.set_af('v4')
        cls.connections = cls.isolated_creds.get_conections() 
        cls.orch = cls.connections.orch
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib_fixture=cls.connections.vnc_lib_fixture
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        cls.api_s_inspect = cls.connections.api_server_inspect
        cls.gl_forwarding_mode = None
        
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.isolated_creds.delete_tenant()
        super(BaseForwardingMode, cls).tearDownClass()
        cls.vnc_lib_fixture.set_global_forwarding_mode(None)
    #end tearDownClass 

    def create_vn(self, *args, **kwargs):
        return self.useFixture(
                VNFixture(project_name=self.inputs.project_name,
                          connections=self.connections,
                          inputs=self.inputs,
                          *args, **kwargs
                          ))

    def create_vm(self, vn_fixture, image_name='ubuntu', *args, **kwargs):
        return self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_obj=vn_fixture.obj,
                    image_name=image_name,
                    *args, **kwargs
                    ))
    

