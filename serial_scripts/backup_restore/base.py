import test
from common.connections import ContrailConnections
from common.contrail_test_init import ContrailTestInit
from common import isolated_creds
from upgrade.verify import BaseResource

class BackupRestoreBaseTest(test.BaseTestCase):
    
    @classmethod
    def setUpClass(cls):
        super(BackupRestoreBaseTest, cls).setUpClass()
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

    @classmethod
    def tearDownClass(cls):
        cls.res.cleanUp()
        cls.isolated_creds.delete_tenant()
        super(BackupRestoreBaseTest, cls).tearDownClass()
    #end tearDownClass
    
class ResourceFactory:
    factories = {}
    def createResource(id):
        if not ResourceFactory.factories.has_key(id):
            ResourceFactory.factories[id] = \
              eval(id + '.Factory()')
        return ResourceFactory.factories[id].create()
    createResource = staticmethod(createResource)


class TestBackupRestoreResource(BaseResource):
    
    def setUp(self,inputs,connections, logger):
        super(TestBackupRestoreResource, self).setUp(inputs,connections, logger)

    def cleanUp(self):
        super(TestBackupRestoreResource, self).cleanUp()

    class Factory:
        def create(self): return TestBackupRestoreResource()

    def runTest(self):
        pass

#End resource   