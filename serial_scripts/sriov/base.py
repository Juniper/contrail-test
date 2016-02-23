import test
import time
import struct
import socket
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
        cls.quantum_h= cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
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
    def get_sriov_enabled_compute_list(self):
        sriov_host_name_list=[]      
        sriov_host_list=self.inputs.sriov_data[0].keys()
        for item in sriov_host_list:
            sriov_host_name_list.append(self.inputs.host_data[item.split('@')[1]]['name'])
        return sriov_host_name_list

    def get_sriov_physnets(self,compute_name):
        host_key=self.inputs.host_data[compute_name]['username'] + '@' + self.inputs.host_data[compute_name]['ip'] 
        physnets_list={}
        physnets_list=self.inputs.sriov_data[0][host_key][0]['physnets']
        return physnets_list
    
    def get_sriov_vf_number(self,compute_name):
        host_key=self.inputs.host_data[compute_name]['username'] + '@' + self.inputs.host_data[compute_name]['ip']
        vf_number=None
        vf_number=self.inputs.sriov_data[0][host_key][0]['VF']
        return vf_number
 
    def get_sriov_pf(self,compute_name):
        host_key=self.inputs.host_data[compute_name]['username'] + '@' + self.inputs.host_data[compute_name]['ip']
        pf_intf=None
        pf_intf=self.inputs.sriov_data[0][host_key][0]['interface']
        return pf_intf

    def ip_increment(self,base_ip,increase_by): 
        ip2int = lambda ipstr: struct.unpack('!I', socket.inet_aton(ipstr))[0]
        ip_num=ip2int(base_ip)
        ip_num=ip_num + int(increase_by)
        int2ip = lambda n: socket.inet_ntoa(struct.pack('!I', n))
        new_ip=int2ip(ip_num)
        return new_ip

    def vm_force_delete(self,vm_obj):
        cmd= 'source /etc/contrail/openstackrc;nova force-delete %s' %(vm_obj.vm_id)
        status=self.inputs.run_cmd_on_server(self.inputs.cfgm_ip, cmd)
        return status

    def get_sriov_mac(self,vm_fix,interface):
        intf_cmd='ifconfig %s| grep HWaddr'%(interface)
        output=vm_fix.run_cmd_on_vm(cmds=[intf_cmd], as_sudo=True)
        return output[intf_cmd].split(" ")[15]

    def get_vf_in_use(self,vm_fix,interface,mac):
        host = self.inputs.get_host_ip(vm_fix.vm_node_ip)
        cmd='ip link show dev %s| grep %s'%(interface,mac)
        output=self.inputs.run_cmd_on_server(host, cmd)
        return output.split(" ")[1]
 
    def set_mtu_on_vf(self,vm_fix,intf,vf_num,vlan_num,mtu):
        host = self.inputs.get_host_ip(vm_fix.vm_node_ip)
        cmd='ip link set %s vf %s vlan %s mtu %s'%(intf,vf_num,vlan_num,mtu)
        output=self.inputs.run_cmd_on_server(host, cmd) 
        return output
         

    def remove_from_cleanups(self, fix):                                                                                                                           
        for cleanup in self._cleanups:                                                                                                                             
            if fix.cleanUp in cleanup:                                                                                                                             
                self._cleanups.remove(cleanup)                                                                                                                     
                break                                                                                                                                              
    #end remove_from_cleanups 
       
     
