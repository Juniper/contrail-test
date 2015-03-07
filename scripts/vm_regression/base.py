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

    def get_default_gateway_interface(self,vm_fixture):
        cmd = "route"+ r" -" +"n"
        output = vm_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=False)
        output = output.values()[0].split('\r')
        output = output[1:]
        for elem in output:
            elem = elem.rstrip()
            if ('0.0.0.0' in elem.split()[0]):
                return elem.split()[-1]
        return None

    def get_all_vm_interfaces(self,vm_fixture):
        intf_list = []
        cmd = "route"+ r" -" +"n"
        output = vm_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=False)
        output = output.values()[0].split('\r')
        output = output[2:]
        for elem in output:
            elem = elem.rstrip()
            try:
                if (elem.split()[-1] not in intf_list):
                    intf_list.append(elem.split()[-1])
            except Exception as e:
                pass
        return intf_list



    def trim_command_output_from_vm(self, output):
        output = output.replace("\r", "")
        output = output.replace("\t", "")
        output = output.replace("\n", " ")
        return output
    # end trim_command_output_from_vm

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

