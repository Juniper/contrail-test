from common.k8s.base import BaseK8sTest
from tcutils.wrappers import preposttest_wrapper
from tcutils.contrail_status import * 
from tcutils.contrail_status_check import ContrailStatusChecker

import test

class TestOcBasic(BaseK8sTest):

    @test.attr(type=['openshift_1'])
    @preposttest_wrapper
    def test_oc_basic_sanity(self):
        '''
        Run basic OC sanity checks.
          1. Verify desired and available counts of kube-system daemonsets
          2. Verify all kube-system pods are in running state 
          3. Verify contrail-status are active for all contrail processes
        '''
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

        self.logger.info('Checking contrail status')
        assert self.inputs.verify_state(),'contrail-status \
            is not good,some processess are already down'
    # end test_oc_basic_sanity 
