from common.neutron.base import *
from tcutils.commands import *
from tcutils.util import retry
from tcutils.wrappers import preposttest_wrapper
from tcutils.contrail_status_check import ContrailStatusChecker

class TestVrouterDetach(BaseNeutronTest):
    
    @classmethod
    def setUpClass(cls):
        super(TestVrouterDetach, cls).setUpClass()
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestVrouterDetach, cls).tearDownClass()
    #end tearDownClass

    @preposttest_wrapper
    def test_vrouter_xconnect(self):
        '''Test vrouter cross connect mode by taking vrouter agent down
        1. get compute node ip
        2. stop vrouter_agent
        3. Try to ssh to compute node from cfgm
        4. Verify Xconnect mode
        5. start vrouter-agent'''
        result = True
        verify_Xconnect ="vif --list | grep Flags:X"
        compute_ip = self.inputs.compute_ips[0]
        self.inputs.stop_service('contrail-vrouter-agent',[compute_ip],container='agent')
        self.logger.info('Verify Xconnect mode ')
        output=self.inputs.run_cmd_on_server(compute_ip,issue_cmd=verify_Xconnect)
        if not output:
            result = result and False
        else:
            self.logger.info('Xconnect mode got enabled')
        self.inputs.start_service('contrail-vrouter-agent',[compute_ip],container='agent')
        status = ContrailStatusChecker(self.inputs)
        status.wait_till_contrail_cluster_stable([compute_ip])
        assert result,'Xconnect mode not enabled'
    #end test_vrouter_xconnect
  
    @preposttest_wrapper
    def test_vrouter_kernal_module_unload_reload(self):
        '''
        1. create Vn and two vms
        2. Verify ping between vms ping should pass
        3. Stop Vrouter services and Unload Vrouter Kernal Module and verify status
        4. Reload Vrouter Module and start Vrouter Services
        5. Verify ping between vms ping should pass
        '''
        compute_ip = self.inputs.compute_ips[0]
        compute_control_ip = self.inputs.compute_control_ips[0]
        if compute_ip == compute_control_ip:
            raise self.skipTest(
                    'Skipping Test. Need multi_interface testbed')
        result = True
        cmd_vr_unload = 'modprobe -r vrouter'
        cmd_vr_reload = 'modprobe -a vrouter'
        vn1_fixture = self.create_vn()
        vm1_fixture = self.create_vm(vn1_fixture,
                                              image_name='cirros')
        vm2_fixture = self.create_vm(vn1_fixture,
                                              image_name='cirros')
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        compute_ip = vm1_fixture.vm_node_ip
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip)
        self.inputs.stop_service('supervisor-vrouter', host_ips=[compute_ip],
                                 container='agent')
        self.inputs.run_cmd_on_server(compute_ip, issue_cmd=cmd_vr_unload)
        status = self.inputs.run_cmd_on_server(compute_ip,issue_cmd = 'lsmod | grep vrouter')
        if status:
            result = result and False
            self.logger.info('Vrouter kernel module failed to unload')
        else:
            self.logger.info('Vrouter kernel module unloaded successfully')
        self.logger.info('Reloading vrouter kernel module')
        self.inputs.run_cmd_on_server(compute_ip, issue_cmd=cmd_vr_reload)
        status = self.inputs.run_cmd_on_server(compute_ip,issue_cmd = 'lsmod | grep vrouter')
        if not status:
            result = result and False
            self.logger.error('Vrouter kernel module failed to reload')
        else:
            self.logger.info('Vrouter kernel module reloaded successfully')
        self.inputs.start_service('supervisor-vrouter', host_ips=[compute_ip],
                                  container='agent')
        status = ContrailStatusChecker(self.inputs)
        status.wait_till_contrail_cluster_stable()
        assert result,'Vrouter kernel module failed to unload and reload'

        #Get the latest metadata ip of the instance after vrouter reload
        vm1_fixture.get_local_ip(refresh=True)
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip)
    #end  test_vrouter_kernal_module_unload_reload
