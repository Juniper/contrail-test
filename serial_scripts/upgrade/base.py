import test_v1
from common.connections import ContrailConnections
from common.contrail_test_init import ContrailTestInit
from common import isolated_creds
from verify import BaseResource

class UpgradeBaseTest(test_v1.BaseTestCase_v1):
    
    @classmethod
    def setUpClass(cls):
        super(UpgradeBaseTest, cls).setUpClass()
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
        super(UpgradeBaseTest, cls).tearDownClass()
    #end tearDownClass
    
class ResourceFactory:
    factories = {}
    def createResource(id):
        if not ResourceFactory.factories.has_key(id):
            ResourceFactory.factories[id] = \
              eval(id + '.Factory()')
        return ResourceFactory.factories[id].create()
    createResource = staticmethod(createResource)


class UpgradeTestSanityWithResourceResource(BaseResource):

    def setUp(self,inputs,connections, logger):
        super(UpgradeTestSanityWithResourceResource, self).setUp(inputs,connections, logger)

    def cleanUp(self):
        super(UpgradeTestSanityWithResourceResource, self).cleanUp()

    class Factory:
        def create(self): return UpgradeTestSanityWithResourceResource()

    def runTest(self):
        pass

#End resource

