import fixtures
from kubernetes.client.rest import ApiException

from common import log_orig as contrail_logging
from tcutils.util import get_random_name, retry


class PodFixture(fixtures.Fixture):
    '''
    '''

    def __init__(self,
                 connections,
                 name=None,
                 namespace='default',
                 metadata={},
                 spec={}):
        self.logger = connections.logger or contrail_logging.getLogger(
            __name__)
        self.inputs = connections.inputs
        self.name = name or get_random_name('pod')
        self.namespace = namespace
        self.k8s_client = connections.k8s_client
        self.metadata = metadata
        self.spec = spec
        self.already_exists = None

    def setUp(self):
        super(PodFixture, self).setUp()
        self.create()

    def verify_on_setup(self):

        if not self.verify_pod_is_running(self.name, self.namespace):
            self.logger.error('POD %s is not in running state'
                              % (self.name))
            return False
        if not self.verify_pod_in_contrail_api():
            self.logger.error('POD %s not seen in Contrail API'
                              % (self.name))
            return False
        if not self.verify_pod_in_contrail_control():
            self.logger.error('POD %s not seen in Contrail control'
                              % (self.name))
            return False
        if not self.verify_pod_in_contrail_agent():
            self.logger.error('POD %s not seen in Contrail agent' % (
                self.name))
            return False
        self.logger.info('Pod %s verification passed' % (self.name))
        return True
    # end verify_on_setup

    def cleanUp(self):
        super(PodFixture, self).cleanUp()
        self.delete()

    def _populate_attr(self):
        self.uuid = self.obj.metadata.uid
        self.status = self.obj.status.phase

    def read(self):
        try:
            self.obj = self.k8s_client.read_pod(self.name, self.namespace)
            self._populate_attr()
            self.already_exists = True
            return self.obj
        except ApiException as e:
            self.logger.debug('POD %s not present' % (self.name))
            return None
    # end read

    def create(self):
        pod = self.read()
        if pod:
            return pod
        self.obj = self.k8s_client.create_pod(
            self.namespace,
            self.name,
            self.metadata,
            self.spec)
        self._populate_attr()
    # end create

    def delete(self):
        if not self.already_exists:
            resp = self.k8s_client.delete_pod(self.namespace, self.name)
    # end delete

    @retry(delay=5, tries=60)
    def verify_pod_is_running(self, name, namespace):
        result = False
        pod_status = self.k8s_client.read_pod_status(name, namespace)
        if pod_status.status.phase != "Running":
            self.logger.debug('POD %s not in running state.'
                               'Currently in %s' % (self.name,
                                                   pod_status.status.phase))
        else:
            self.logger.info('POD %s is in running state.'
                             'Got IP %s' % (self.name,
                                            pod_status.status.pod_ip))
            self.pod_ip = pod_status.status.pod_ip
            self.host_ip = pod_status.status.host_ip
            result = True
        return result

    @retry(delay=1, tries=10)
    def verify_pod_in_contrail_api(self):
        # TODO
        return True
    # end verify_pod_in_contrail_api

    @retry(delay=1, tries=10)
    def verify_pod_in_contrail_control(self):
        # TODO
        return True
    # verify_pod_in_contrail_control

    @retry(delay=1, tries=10)
    def verify_pod_in_contrail_agent(self):
        # TODO
        return True
    # verify_pod_in_contrail_agent

    def run_kubectl_cmd_on_master(self, pod_name, cmd, shell='/bin/bash -l -c'):
        kubectl_command = 'kubectl exec %s --namespace=%s -i -t -- %s "%s"' % (
            pod_name, self.namespace, shell, cmd)

        # TODO Currently using  config node IP as Kubernetes master
        # This need to be changed
        output = self.inputs.run_cmd_on_server(self.inputs.cfgm_ip,
                                               kubectl_command)
        return output

    def run_cmd(self, cmd, **kwargs):
        return self.run_cmd_on_pod(cmd, **kwargs)

    def run_cmd_on_pod(self, cmd, mode='api', shell='/bin/bash -l -c'):
        if mode == 'api':
            output = self.k8s_client.exec_cmd_on_pod(self.name, cmd,
                namespace=self.namespace, shell=shell)
        else:
            output = self.run_kubectl_cmd_on_master(self.name, cmd, shell)
        return output
    # run_cmd_on_pod

    def ping_to_ip(self, ip, return_output=False, count='5', expectation=True):
        """Ping from a POD to an IP specified.

        This method logs into the POD from kubernets master using kubectl and runs ping test to an IP.
        """
        output = ''
        cmd = "ping -c %s %s" % (count, ip)
        try:
            output = self.run_cmd_on_pod(cmd)
            if return_output is True:
                return output
        except Exception, e:
            self.logger.exception(
                'Exception occured while trying ping from POD')
            return False

        expected_result = ' 0% packet loss'
        try:
            if expected_result not in output:
                self.logger.warn("Ping to IP %s from POD %s failed" %
                                 (ip, self.name))
                if not expectation:
                    return False
            else:
                self.logger.info('Ping to IP %s from POD %s passed' %
                                 (ip, self.name))
            return True
        except Exception as e:
            self.logger.warn("Got exception in ping_to_ip:%s" % (e))
            return False
      # end ping_to_ip
