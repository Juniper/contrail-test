import test_v1
from common.connections import ContrailConnections
from common import isolated_creds
from common import create_public_vn

class BaseSvc_FwTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BaseSvc_FwTest, cls).setUpClass()
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        if cls.inputs.admin_username:
            public_creds = cls.admin_isolated_creds
        else:
            public_creds = cls.isolated_creds
        cls.public_vn_obj = create_public_vn.PublicVn(
            public_creds,
            cls.inputs,
            ini_file=cls.ini_file,
            logger=cls.logger)
        cls.public_vn_obj.configure_control_nodes()                
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseSvc_FwTest, cls).tearDownClass()
    #end tearDownClass 

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            if fix.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break
    #end remove_from_cleanups



