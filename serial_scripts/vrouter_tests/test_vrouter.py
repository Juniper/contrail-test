from tcutils.commands import *
from tcutils.util import retry
from tcutils.wrappers import preposttest_wrapper
import base

class TestVrouter(base.BaseVrouterTest):
    
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
           1)get compute node ip
           2)stop vrouter_agent
           3)Try to ssh to compute node from cfgm
           4)Verify Xconnect mode
           5)start vrouter-agent'''
        v_agent= 'contrail-vrouter-agent'
        v_agent_status =" contrail-status|grep contrail-vrouter-agent | awk 'FNR == 1 {print $2 }' "
        verify_Xconnect ="vif --list | grep Flags:X"
        compute_ip=self.inputs.compute_ips[0]
        compute_user = self.inputs.host_data[compute_ip]['username']
        compute_password = self.inputs.host_data[compute_ip]['password']
        self.inputs.stop_service(v_agent,[compute_ip])
        self.logger.info('SSH to compute node to verify xconnect mode')
        session = ssh(compute_ip, compute_user, compute_password)
        status=execute_cmd_out(session,v_agent_status,self.logger)
        status=status[0].strip('\n')
        if not 'inactive' in status:
            assert False,'Contrail-vrouter-agent failed to stop'
        else:
            self.logger.debug('Contrail-vrouter-agent service is %s',status)
            self.logger.debug('Verify Xconnect mode ')
            status=execute_cmd_out(session, verify_Xconnect, self.logger)
            assert status[0],'Xconnect mode not enabled'
            self.logger.info('Xconnect mode got enabled')
            self.inputs.start_service(v_agent,[compute_ip])
            result=self.inputs.verify_service_state(compute_ip,v_agent,compute_user,compute_password)
            assert result,'Contrail-vrouter-agent service is inactive'
            self.logger.info('Verify vrouter Xconnect mode test passed')
    #end test_vrouter_xconnect

    def test_vrouter_module_unload_reload(self):
        pass
    
