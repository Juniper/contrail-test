import test_v1
import re
from common.connections import ContrailConnections
from common import isolated_creds
from vm_test import VMFixture
from vn_test import VNFixture

class BaseVnVmTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BaseVnVmTest, cls).setUpClass()
        cls.inputs.set_af('v4')
        cls.orch = cls.connections.orch
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
        cls.api_s_inspect = cls.connections.api_server_inspect
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseVnVmTest, cls).tearDownClass()
    #end tearDownClass 

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
            if fix.cleanUp in cleanup:
                self._cleanups.remove(cleanup)
                break
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

    def create_vn(self, *args, **kwargs):
        return self.useFixture(
                VNFixture(project_name=self.inputs.project_name,
                          connections=self.connections,
                          inputs=self.inputs,
                          *args, **kwargs
                          ))

    def create_vm(self, vn_fixture=None, image_name='ubuntu', *args, **kwargs):
        if vn_fixture:
            vn_obj = vn_fixture.obj
        else:
            vn_obj = None
        return self.useFixture(
                VMFixture(
                    project_name=self.inputs.project_name,
                    connections=self.connections,
                    vn_obj=vn_obj,
                    image_name=image_name,
                    *args, **kwargs
                    ))

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

    def verify_eth1_ip_from_vm(self, vm_fix):
        i = 'ifconfig eth1'
        cmd_to_pass5 = [i]
        out = vm_fix.run_cmd_on_vm(cmds=cmd_to_pass5, as_sudo=True, timeout=60)
        output = vm_fix.return_output_cmd_dict[i]
        match = re.search('inet addr:(.+?)  Bcast:', output)
        if match:
           return True
        else:
           return False

    def get_two_different_compute_hosts(self):
        host_list = self.connections.orch.get_hosts()
        self.compute_1 = host_list[0]
        self.compute_2 = host_list[0]
        if len(host_list) > 1:
            self.compute_1 = host_list[0]
            self.compute_2 = host_list[1]   
