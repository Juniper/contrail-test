import test_v1
from common.connections import ContrailConnections
from common.contrail_test_init import ContrailTestInit
from common import isolated_creds
from upgrade.verify import BaseResource

class ResetConfigBaseTest(test_v1.BaseTestCase):
    
    @classmethod
    def setUpClass(cls):
        super(ResetConfigBaseTest, cls).setUpClass()
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
        resource_class = cls.__name__ + 'Resource'
        cls.res = ResourceFactory.createResource(resource_class)
    #end setUpClass
    
class ResourceFactory:
    factories = {}
    def createResource(id):
        if not ResourceFactory.factories.has_key(id):
            ResourceFactory.factories[id] = \
              eval(id + '.Factory()')
        return ResourceFactory.factories[id].create()
    createResource = staticmethod(createResource)


class TestResetConfigResource(BaseResource):
    
    def setUp(self,inputs,connections, logger):
        super(TestResetConfigResource, self).setUp(inputs,connections, logger)

    class Factory:
        def create(self): return TestResetConfigResource()

    def runTest(self):
        pass
  
