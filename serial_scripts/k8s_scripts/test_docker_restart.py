from common.k8s.base import BaseK8sTest
from tcutils.wrappers import preposttest_wrapper
from tcutils.contrail_status import * 
from tcutils.contrail_status_check import ContrailStatusChecker

import test
import socket

class TestOcDockerRestart(BaseK8sTest):

    def is_test_applicable(self):
        if len(self.inputs.cfgm_ips) < 3 or \
                len(self.inputs.kube_manager_ips) < 3:
            return (False, 'Skipping tests since controller/KM has less than 3 '
                    'nodes')
        else:
            return (True, None)
    ## end-of is_test_applicable


    def post_restart_verifications(self):
	
        self.logger.info('Checking contrail status')
        assert self.inputs.verify_state(retries=15, rfsh=True),'contrail-status \
            is not good,some processess are already down'

        self.logger.info('Verify status of daemonsets')
        if not self.verify_daemonset_status(namespace='contrail-system'):
            daemonset_status = self.get_daemonset_status()
            self.logger.debug('Daemonset status information: ')
            self.logger.debug(daemonset_status)
            assert False, "One or more daemonsets were not in desired state"
        self.logger.info("All daemonsets are in expected states")

        self.logger.info('Verifyng status of pods')
        err_msg = "One of more pods not in Running state"
        assert self.verify_pods_status(namespace='kube-system'), err_msg
        assert self.verify_pods_status(namespace='contrail-system'), err_msg
        assert self.verify_pods_status(namespace='default'), err_msg
        assert self.verify_pods_status(namespace='kube-proxy-and-dns'), err_msg
        assert self.verify_pods_status(namespace='kube-service-catalog'), err_msg
        assert self.verify_pods_status(namespace='openshift-console'), err_msg
        assert self.verify_pods_status(namespace='openshift-infra'), err_msg
        assert self.verify_pods_status(namespace='openshift-logging'), err_msg
        assert self.verify_pods_status(namespace='openshift-metrics-server'), err_msg
        assert self.verify_pods_status(namespace='openshift-monitoring'), err_msg
        assert self.verify_pods_status(namespace='openshift-node'), err_msg
        assert self.verify_pods_status(namespace='openshift-template-service-broker'), err_msg
        assert self.verify_pods_status(namespace='openshift-web-console'), err_msg
        assert self.verify_pods_status(namespace='openshift-ansible-service-broker'), err_msg

    ## end-of post_restart_verifications


    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_oc_docker_restart_k8s_backup(self):
        '''
        This tests valid only on HA setup with events on non-test container host and test-logic ensures this
	        1  Execute Docker restart on the host which has "contrail-kube-manager" in backup state
            2. Verify desired and available counts of kube-system daemonsets
            3. Verify all Openshift Sytem pods are in running state 
            4. Verify contrail-status are active for all contrail processes
        '''

        contrail_k8s_backup_nodes = self.inputs.get_contrail_status(svc='contrail-kube-manager', state='backup')
        if len(contrail_k8s_backup_nodes) != 2:
            assert False, "This is not HA setup"

    	# Avoid restarting Docker on test-container node
        if contrail_k8s_backup_nodes[0] != socket.gethostbyaddr(socket.gethostname())[2][0]:
            restart_node = contrail_k8s_backup_nodes[0]
        else:
            restart_node = contrail_k8s_backup_nodes[1]
    	
        # Restart the docker host
        self.inputs.run_cmd_on_server(restart_node, 'systemctl restart docker')

        # Verifications after restart
        self.post_restart_verifications()

    ## end-of test_oc_docker_restart_k8s_backup 


    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_oc_docker_restart_k8s_active(self):
        '''
        This tests valid only on HA setup with events on non-test container host and test-logic ensures this
          1  Execute Docker restart on the host which has "contrail-kube-manager" in active state
          2. Verify desired and available counts of kube-system daemonsets
          3. Verify all Openshift Sytem pods are in running state
          4. Verify contrail-status are active for all contrail processes
        '''
        
        contrail_k8s_active_node = self.inputs.get_contrail_status(svc='contrail-kube-manager', state='active')
        if len(contrail_k8s_active_node) != 1:
            assert False, "This is not in Active-Backup mode"

        # Avoid restarting Docker on test-container node
        if contrail_k8s_active_node[0] != socket.gethostbyaddr(socket.gethostname())[2][0]:
            restart_node = contrail_k8s_active_node[0]
        else:
            self.inputs.restart_service('contrail-kube-manager', contrail_k8s_active_node,container='contrail-kube-manager',verify_service=False)
            contrail_k8s_active_node = self.inputs.get_contrail_status(svc='contrail-kube-manager', state='active')
            if len(contrail_k8s_active_node) != 1:
                assert False, "This is not in Active-Backup mode"
            if contrail_k8s_active_node[0] != socket.gethostbyaddr(socket.gethostname())[2][0]:
                restart_node = contrail_k8s_active_node[0]
            else:
                assert False, "restart contrail-kube-manager Failed"

        # Restart the docker host
        self.inputs.run_cmd_on_server(restart_node, 'systemctl restart docker')

    	# Verifications after restart
        self.post_restart_verifications()

    ## end-of test_oc_docker_restart_k8s_active 


    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_oc_docker_restart_dm_backup(self):
        '''
        This tests valid only on HA setup with events on non-test container host and test-logic ensures this
          1  Execute Docker restart on the host which has "device-manager" in backup state
          2. Verify desired and available counts of kube-system daemonsets
          3. Verify all Openshift Sytem pods are in running state 
          4. Verify contrail-status are active for all contrail processes
        '''

        contrail_dm_backup_nodes = self.inputs.get_contrail_status(svc='device-manager', state='backup')
        if len(contrail_dm_backup_nodes) != 2:
            assert False, "This is not HA setup"

        # Avoid restarting Docker on test-container node
        if contrail_dm_backup_nodes[0] != socket.gethostbyaddr(socket.gethostname())[2][0]:
            restart_node = contrail_dm_backup_nodes[0]
        else:
            restart_node = contrail_dm_backup_nodes[1]

        # Restart the docker host
        self.inputs.run_cmd_on_server(restart_node, 'systemctl restart docker')

        # Verifications after restart
        self.post_restart_verifications()

    ## end-of test_oc_docker_restart_dm_backup 


    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_oc_docker_restart_dm_active(self):
        '''
        This tests valid only on HA setup with events on non-test container host and test-logic ensures this
          1  Execute Docker restart on the host which has "device-manager" in active state
          2. Verify desired and available counts of kube-system daemonsets
          3. Verify all Openshift Sytem pods are in running state
          4. Verify contrail-status are active for all contrail processes
        '''
        
        contrail_dm_active_node = self.inputs.get_contrail_status(svc='device-manager', state='active')
        if len(contrail_dm_active_node) != 1:
            assert False, "This is not in Active-Backup mode"

        # Avoid restarting Docker on test-container node
        if contrail_dm_active_node[0] != socket.gethostbyaddr(socket.gethostname())[2][0]:
            restart_node = contrail_dm_active_node[0]
        else:
            self.inputs.restart_service('device-manager', contrail_dm_active_node,container='device-manager',verify_service=False)
            contrail_dm_active_node = self.inputs.get_contrail_status(svc='device-manager', state='active')
            if len(contrail_dm_active_node) != 1:
                assert False, "This is not in Active-Backup mode"
            if contrail_dm_active_node[0] != socket.gethostbyaddr(socket.gethostname())[2][0]:
                restart_node = contrail_dm_active_node[0]
            else:
                assert False, "restart device-manager Failed"

        # Restart the docker host
        self.inputs.run_cmd_on_server(restart_node, 'systemctl restart docker')

    	# Verifications after restart
        self.post_restart_verifications()

    ## end-of test_oc_docker_restart_dm_active 


    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_oc_docker_restart_schema_backup(self):
        '''
        This tests valid only on HA setup with events on non-test container host and test-logic ensures this
          1  Execute Docker restart on the host which has "schema" in backup state
          2. Verify desired and available counts of kube-system daemonsets
          3. Verify all Openshift Sytem pods are in running state 
          4. Verify contrail-status are active for all contrail processes
        '''

        contrail_schema_backup_nodes = self.inputs.get_contrail_status(svc='schema', state='backup')
        if len(contrail_schema_backup_nodes) != 2:
            assert False, "This is not HA setup"

        # Avoid restarting Docker on test-container node
        if contrail_schema_backup_nodes[0] != socket.gethostbyaddr(socket.gethostname())[2][0]:
            restart_node = contrail_schema_backup_nodes[0]
        else:
            restart_node = contrail_schema_backup_nodes[1]

        # Restart the docker host
        self.inputs.run_cmd_on_server(restart_node, 'systemctl restart docker')

        # Verifications after restart
        self.post_restart_verifications()

    ## end-of test_oc_docker_restart_schema_backup 


    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_oc_docker_restart_schema_active(self):
        '''
        This tests valid only on HA setup with events on non-test container host and test-logic ensures this
          1  Execute Docker restart on the host which has "schema" in active state
          2. Verify desired and available counts of kube-system daemonsets
          3. Verify all Openshift Sytem pods are in running state
          4. Verify contrail-status are active for all contrail processes
        '''
        
        contrail_schema_active_node = self.inputs.get_contrail_status(svc='schema', state='active')
        if len(contrail_schema_active_node) != 1:
            assert False, "This is not in Active-Backup mode"

        # Avoid restarting Docker on test-container node
        if contrail_schema_active_node[0] != socket.gethostbyaddr(socket.gethostname())[2][0]:
            restart_node = contrail_schema_active_node[0]
        else:
            self.inputs.restart_service('schema', contrail_schema_active_node,container='schema',verify_service=False)
            contrail_schema_active_node = self.inputs.get_contrail_status(svc='schema', state='active')
            if len(contrail_schema_active_node) != 1:
                assert False, "This is not in Active-Backup mode"
            if contrail_schema_active_node[0] != socket.gethostbyaddr(socket.gethostname())[2][0]:
                restart_node = contrail_schema_active_node[0]
            else:
                assert False, "restart schema Failed"

        # Restart the docker host
        self.inputs.run_cmd_on_server(restart_node, 'systemctl restart docker')

    	# Verifications after restart
        self.post_restart_verifications()

    ## end-of test_oc_docker_restart_schema_active 

