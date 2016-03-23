from compute_node_test import *
from tcutils.commands import *
from tcutils.util import retry
import base
class TestVrouter(base.BaseVrouterTest):
    @classmethod
    def setUpClass(cls):
        super(TestVrouter, cls).setUpClass()
    # end setUpClass

    def cleanUp(cls):
        super(TestVrouter, cls).cleanUp()
    # end cleanUp

    @preposttest_wrapper
    def test_vrouter_xconnect(self):
        '''Test vrouter cross connect mode by taking vrouter agent down
           1)get compute node ip
           2)stop vrouter_agent
           3)Try to ssh to compute node from cfgm
           4)Verify Xconnect mode
           5)start vrouter-agent'''
        v_agent_stop= 'service contrail-vrouter-agent stop'
        v_agent_start='service contrail-vrouter-agent start'
        v_agent_status =" contrail-status|grep contrail-vrouter-agent | awk 'FNR == 1 {print $2 }' "
        verify_Xconnect ="vif --list | grep Flags:X"
        compute_ip=self.inputs.compute_ips[0]
        compute_user = self.inputs.host_data[compute_ip]['username']
        compute_password = self.inputs.host_data[compute_ip]['password']
        with settings(
            host_string='%s@%s' % (
                compute_user, compute_ip),
                password = compute_password, warn_only=True, abort_on_prompts=False, debug=True):
            self.logger.info('Stop contrail-vrouter_agent service')
            status = run('%s' %v_agent_stop)
            self.logger.debug("%s" % status)
        self.logger.info('ssh to compute node to verify xconnect mode')
        session = ssh(compute_ip, compute_user, compute_password)
        status=execute_cmd_out(session,v_agent_status,self.logger)
        status=status[0].strip('\n')
        if not 'inactive' in status:
            self.logger.info('contrail-vrouter-agent failed to stop')
            return False
        else:
            self.logger.info('contrail-vrouter-agent service is %s',status)
            self.logger.info('verify Xconnect mode ')
            status=execute_cmd_out(session, verify_Xconnect, self.logger)
            if status[0]:
                self.logger.info('Xconnect mode got enabled')
            else:
                self.logger.info('Xconnect mode not enabled')
                return False
            status=execute_cmd_out(session,v_agent_start, self.logger)
            self.logger.info('%s',status[0])
            return True
   
    def test_vrouter_module_unload_reload(self):
        pass
    
