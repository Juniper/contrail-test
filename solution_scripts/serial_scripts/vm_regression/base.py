import test
from common.connections import ContrailConnections
from common import isolated_creds
from vm_test import VMFixture
from vn_test import VNFixture
import os

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
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
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

    def create_vn(self, vn_name, vn_subnets, option = 'quantum'):
        return self.useFixture(
                VNFixture(project_name=self.inputs.project_name,
                          connections=self.connections,
                          inputs=self.inputs,
                          vn_name=vn_name,
                          subnets=vn_subnets,
                          option = option))
    
    def create_vm(self, vn_fixture, vm_name, node_name=None,
                    flavor='contrail_flavor_small',
                    image_name='ubuntu-traffic'):
        image_name = os.environ['ci_image'] if os.environ.has_key('ci_image') else 'ubuntu-traffic'
        return self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_obj=vn_fixture.obj,
                    vm_name=vm_name,
                    image_name=image_name,
                    flavor=flavor,
                    node_name=node_name))

    def cleanup_test_max_vm_flows_vrouter_config(self,
            compute_ips,
            compute_fixtures):
        for cmp_node in compute_ips:
            compute_fixtures[cmp_node].set_per_vm_flow_limit(100)
            compute_fixtures[cmp_node].set_flow_aging_time(
                compute_fixtures[
                    cmp_node].default_values['DEFAULT']['flow_cache_timeout'])
            compute_fixtures[cmp_node].sup_vrouter_process_restart()
        return True

