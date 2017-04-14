import test_v1
from common import isolated_creds
from project_test import *
import domain_test
from vn_test import *

class BaseDomainTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BaseDomainTest, cls).setUpClass()
        cls.orch = cls.connections.orch
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.api_s_inspect = cls.connections.api_server_inspect
        cls.analytics_obj = cls.connections.analytics_obj
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseDomainTest, cls).tearDownClass()
    # end tearDownClass
# end BaseDomainTest class

    def create_project(self,domain_name,project_name,username, password):
        
        return self.useFixture(ProjectFixture(
            domain_name=domain_name,
            project_name=project_name,
            auth=self.admin_connections.auth,
            username=username,
            password=password,
            connections=self.admin_connections))

    def create_domain(self,domain_name=None,connections=None):
        try:
            domain = domain_test.DomainFixture(connections=connections or self.admin_connections ,
                                                   domain_name=domain_name)
            domain.setUp()
            return domain
        except Exception as e:
                self.logger.exception("Exception while creating domain")

    def create_vn(self,project_fix,connections,vn_name,subnet):
        return self.useFixture(
            VNFixture(
                project_name=project_fix.project_name,
                connections=connections,
                vn_name=vn_name,
                subnet=subnet,
                inputs=self.inputs))

    def read_vn(self, connections, uuid):
        try:
            obj = connections.orch.get_vn_obj_from_id(uuid)
        except PermissionDenied:
            obj = None
        if obj:
            self.logger.info('Read VN %s'%uuid)
        else:
            self.logger.info('Permission Denied to read VN %s'%uuid)
        return obj
