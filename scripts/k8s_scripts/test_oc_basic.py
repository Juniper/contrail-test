from common.k8s.base import BaseK8sTest
from tcutils.wrappers import preposttest_wrapper
from tcutils.contrail_status import * 
from tcutils.contrail_status_check import ContrailStatusChecker

import test

class TestOcBasic(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestOcBasic, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestOcBasic, cls).tearDownClass()

    def parallel_cleanup(self):
        parallelCleanupCandidates = ["PodFixture"]
        self.delete_in_parallel(parallelCleanupCandidates)
    
    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_oc_basic_sanity(self):
        '''
        Run basic OC sanity checks.
          1. Verify desired and available counts of kube-system daemonsets
          2. Verify all kube-system pods are in running state 
          3. Verify contrail-status are active for all contrail processes
          4. Checking whether contrail docker containers are up
        '''
        self.logger.info('Verify status of daemonsets')
        if not self.verify_daemonset_status(namespace='kube-system'):
            daemon_set_status = self.get_daemon_set_status()
            self.logger.debug('Daemonset status information: ')
            self.logger.debug(daemon_set_status)
            assert False, "One or more daemonsets were not in desired state"
        self.logger.info("All daemonsets are in expected states")

        self.logger.info('Verifyng status of pods')
        err_msg = "One of more pods not in Running state"
        assert self.verify_pods_status(namespace='kube-system'), err_msg

        self.logger.info('Checking contrail status')
        roles_list = ["control", "config-database", "kubernetes", "database", "analytics", "webui",
                     "config"]
        services=[]
        status_dict = contrail_status(
            self.inputs, [self.inputs.k8s_master_ip], roles_list)
        self.logger.debug('Contrail status dict: ')
        self.logger.debug(status_dict)
        all_containers_active = True
        for item in status_dict[self.inputs.k8s_master_ip].keys():
            if status_dict[self.inputs.k8s_master_ip][item]["status"] != 'active':
                self.logger.error("Container {} not in active status. Status is {}".format(
                    item, status_dict[self.inputs.k8s_master_ip][item]["status"]))
                all_containers_active = False
                continue
            self.logger.info("Container {} is in active state".format(item))
        if not all_containers_active:
            self.logger.info("Following containers are not in active state")
            self.logger.info([x for x in status_dict[self.inputs.k8s_master_ip] \
                if status_dict[self.inputs.k8s_master_ip][x]["status"] != 'active']) 
        assert all_containers_active, "One of more containers not in active state"
    # end test_oc_basic_sanity 

