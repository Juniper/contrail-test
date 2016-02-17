import test
import fixtures
from common import isolated_creds

class BaseSriovTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseSriovTest, cls).setUpClass()
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
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        #cls.isolated_creds.delete_user()
        cls.isolated_creds.delete_tenant()
        super(BaseSriovTest, cls).tearDownClass()
    #end tearDownClass 

    def bringup_interface_forcefully(self, vm_fixture, intf='eth1'):
        cmd = 'ifconfig %s up'%(intf)
        for i in range (5):
          cmd_to_pass = [cmd]
          vm_fixture.run_cmd_on_vm(cmds=cmd_to_pass, as_sudo=True, timeout=60)
          vm_fixture.run_cmd_on_vm(cmds=['ifconfig'], as_sudo=True, timeout=60)
          output = vm_fixture.return_output_cmd_dict['ifconfig']
          if output and 'eth1' in output:
              break
          else:
              time.sleep(3)

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
        #    if fix.cleanUp in cleanup:
            self._cleanups.remove(cleanup)
            #break
