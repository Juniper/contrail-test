import test_v1
from svc_hc_fixture import HealthCheckFixture
from tcutils.util import get_random_name

class BaseHC(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BaseHC, cls).setUpClass()
        cls.project_name = cls.inputs.project_name
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
    #end setUpClass

    def create_hc(self, hc_type='link-local', probe_type='PING',
                  delay=3, timeout=5, max_retries=2,
                  http_url='local-ip', verify=True):
        hc_fixture = self.useFixture(HealthCheckFixture(
                     connections=self.connections,
                     name=get_random_name(self.project_name),
                     hc_type=hc_type, delay=delay,
                     probe_type=probe_type, timeout=timeout, 
                     max_retries=max_retries, http_url=http_url))
        if verify:
            hc_fixture.verify_on_setup()
        return hc_fixture

