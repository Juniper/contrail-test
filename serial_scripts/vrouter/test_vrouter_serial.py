from tcutils.commands import *
from tcutils.util import retry
from tcutils.wrappers import preposttest_wrapper
from common.vrouter.base import BaseVrouterTest
from tcutils.contrail_status_check import ContrailStatusChecker
from common.neutron.base import *
import sys

class TestVrouter(BaseNeutronTest):
    
    @classmethod
    def setUpClass(cls):
        super(TestVrouter, cls).setUpClass()
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(TestVrouter, cls).tearDownClass()
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
        cmd_stop = 'service contrail-vrouter-agent stop'
        cmd_start = 'service contrail-vrouter-agent start'
        v_agent_status =" contrail-status|grep contrail-vrouter-agent | awk 'FNR == 1 {print $2 }' "
        verify_Xconnect ="vif --list | grep Flags:X"
        compute_ip=self.inputs.compute_ips[0]
        self.inputs.run_cmd_on_server(compute_ip,cmd_stop)
        status=self.inputs.run_cmd_on_server(compute_ip,issue_cmd= v_agent_status)
        self.logger.debug('Contrail-vrouter-agent service is %s',status)
        self.logger.info('Verify Xconnect mode ')
        status=self.inputs.run_cmd_on_server(compute_ip,issue_cmd=verify_Xconnect)
        if not status:
            result = result and False
        else:
            self.logger.info('Xconnect mode got enabled')
        self.inputs.run_cmd_on_server(compute_ip,issue_cmd=cmd_start)
        status = ContrailStatusChecker(self.inputs)
        status.wait_till_contrail_cluster_stable()
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
        if not self.is_test_applicable():
            self.logger.info('Skipping test_case need multi_interface testbed')
            return True
        result = True
        cmd_vr_stop = 'service supervisor-vrouter stop'
        cmd_vr_start = 'service supervisor-vrouter start'
        cmd_vr_unload = 'modprobe -r vrouter'
        cmd_vr_reload = 'modprobe -a vrouter'
        vn1_fixture = self.create_vn()
        vm1_fixture = self.create_vm(vn1_fixture,
                                              image_name='ubuntu')
        vm2_fixture = self.create_vm(vn1_fixture,
                                              image_name='ubuntu')
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        compute_ip = vm1_fixture.vm_node_ip
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip)
        self.inputs.run_cmd_on_server(compute_ip,issue_cmd=cmd_vr_stop)
        self.inputs.run_cmd_on_server(compute_ip,issue_cmd=cmd_vr_unload)
        status = self.inputs.run_cmd_on_server(compute_ip,issue_cmd = 'lsmod | grep vrouter')
        if status:
            result = result and False
            self.logger.info('Vrouter kernal module failed to unload')
        else:
            self.logger.info('Vrouter kernal module unloaded successfully')
        self.logger.info('Reloading vrouter kernal module')
        self.inputs.run_cmd_on_server(compute_ip,issue_cmd=cmd_vr_reload)
        status = self.inputs.run_cmd_on_server(compute_ip,issue_cmd = 'lsmod | grep vrouter')
        if not status:
            result = result and False
            self.logger.info('Vrouter kernal module failed to reload')
        else:
            self.logger.info('Vrouter kernal module reloaded successfully')
        self.inputs.run_cmd_on_server(compute_ip,issue_cmd=cmd_vr_start)
        status = ContrailStatusChecker(self.inputs)
        status.wait_till_contrail_cluster_stable()
        assert result,'Vrouter kernal module failed to unload and reload'
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip)
    
    def is_test_applicable(self):
        contrail_fab_path='/opt/contrail/utils'
        sys.path.insert(0, contrail_fab_path)
        from fabfile.testbeds import testbed
        return getattr(testbed,'control_data',None)