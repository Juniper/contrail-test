import json

import fixtures
from kubernetes.client.rest import ApiException

from vnc_api.vnc_api import NoIdError
from common import log_orig as contrail_logging
from tcutils.util import get_random_name, retry


class PodFixture(fixtures.Fixture):
    '''
    '''

    def __init__(self,
                 connections,
                 name=None,
                 namespace='default',
                 metadata=None,
                 spec=None,
                 shell=None):
        self.logger = connections.logger or contrail_logging.getLogger(
            __name__)
        self.inputs = connections.inputs
        self.name = name or metadata.get('name') or get_random_name('pod')
        self.namespace = namespace
        self.k8s_client = connections.k8s_client
        self.metadata = {} if metadata is None else metadata
        self.spec = {} if spec is None else spec
        self.already_exists = None
        self.shell = shell or '/bin/sh'
        self._shell_arg = '%s -l -c' % (self.shell)

        self.connections = connections
        self.vnc_lib = connections.get_vnc_lib_h()
        self.agent_inspect = connections.agent_inspect

        self.api_vm_obj = None
        self.vmi_objs = []
        self.tap_intfs = []
        self.host_ip = None
        self.compute_ip = None
        self.vmi_objs = []
        self.vmi_uuids = []
        self.vn_names = []
        self.vn_fq_names = []
    # end __init__

    def setUp(self):
        super(PodFixture, self).setUp()
        self.create()

    def verify_on_setup(self):

        if not self.verify_pod_is_running(self.name, self.namespace):
            self.logger.error('Pod %s is not in running state'
                              % (self.name))
            return False
        if not self.verify_pod_in_contrail_api():
            self.logger.error('Pod %s not seen in Contrail API'
                              % (self.name))
            return False
        if not self.verify_pod_in_contrail_control():
            self.logger.error('Pod %s not seen in Contrail control'
                              % (self.name))
            return False
        if not self.verify_pod_in_contrail_agent():
            self.logger.error('Pod %s not seen in Contrail agent' % (
                self.name))
            return False
        self.logger.info('Pod %s verification passed' % (self.name))
        return True
    # end verify_on_setup

    def cleanUp(self):
        super(PodFixture, self).cleanUp()
        self.delete()

    @retry(delay=3, tries=20)
    def _get_uuid(self):
        self.obj = self.k8s_client.read_pod(self.name, self.namespace)
        if not self.obj.metadata.uid:
            self.logger.debug('Pod %s uuid not yet populated' % (self.name))
            return (False, None)
        return (True, self.obj.metadata.uid)
    # end _get_uuid

    @retry(delay=3, tries=20)
    def _get_pod_node_name(self):
        self.obj = self.k8s_client.read_pod(self.name, self.namespace)
        if not self.obj.spec.node_name:
            self.logger.debug('Node for Pod %s not yet populated' % (self.name))
            return (False, None)
        return (True, self.obj.spec.node_name)
    # end _get_pod_node_name

    def _populate_attr(self):
        (ret_val, self.uuid) = self._get_uuid()
        (ret_val, self.nodename) = self._get_pod_node_name()
        self.status = self.obj.status.phase
        self.labels = self.obj.metadata.labels
        self.logger.debug('Pod : %s UUID is %s' %(self.name, self.uuid))

    def read(self):
        try:
            self.obj = self.k8s_client.read_pod(self.name, self.namespace)
            self._populate_attr()
            self.already_exists = True
            return self.obj
        except ApiException as e:
            self.logger.debug('Pod %s not present' % (self.name))
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

    def delete_only(self):
        if not self.already_exists:
            resp = self.k8s_client.delete_pod(self.namespace, self.name)
            return resp
    # end delete_only

    def delete(self):
        if not self.already_exists:
            resp = self.delete_only()

            assert self.verify_on_cleanup()
    # end delete

    def verify_on_cleanup(self):
        assert self.verify_pod_not_in_contrail_api(), ('Pod %s cleanup checks'
                                                       ' in contrail-api failed' % (self.name))
        assert self.verify_pod_not_in_contrail_agent(), ('Pod %s cleanup checks'
                                                         ' in agent failed' % (self.name))
        return True
        self.logger.info('Verifications on pod %s cleanup passed')
    # end verify_on_cleanup

    def verify_pod_not_in_contrail_api(self):
        # TODO
        return True

    @retry(delay=5, tries=10)
    def verify_pod_not_in_contrail_agent(self):
        if not self.host_ip:
            self.logger.debug('Pod %s may not have launched at all..no need to '
                              'check further in agent' % (self.name))
            return True

        compute_mgmt_ip = self.inputs.host_data[self.compute_ip]['ip']
        inspect_h = self.agent_inspect[compute_mgmt_ip]

        # Check that VM object is removed in agent
        agent_vm = inspect_h.get_vna_vm(self.uuid)
        if agent_vm:
            self.logger.warn('Pod uuid %s is still seen in agent %s VM list' % (
                self.uuid, self.compute_ip))
            return False
        self.logger.debug('Pod %s is not in agent %s VM list' % (self.uuid,
                                                                 self.compute_ip))

        # Check that tap intf is removed in agent
        for tap_intf in self.tap_intfs:
            vmi_dict = inspect_h.get_vna_tap_interface_by_vmi(
                tap_intf['uuid'])
            if vmi_dict:
                self.logger.warn('VMI %s of Pod %s is still seen in '
                                 'agent %s' % (tap_intf['uuid'], self.name, self.compute_ip))
                self.logger.debug(vmi_dict)
                return False
            self.logger.debug('VMI %s is removed from agent %s' % (
                tap_intf['uuid'], self.compute_ip))
        # TODO
        # Will have a common set of methods for validating across vm_test.py
        # and pod.py soon
        self.logger.info(
            'Verified that pod %s is removed in agent' % (self.name))
        return True
    # end verify_pod_not_in_contrail_agent

    def set_labels(self, label_dict):
        self.obj = self.k8s_client.set_pod_label(self.namespace, self.name,
                                                 label_dict)
        self._populate_attr()
    # end set_labels

    @retry(delay=5, tries=60)
    def verify_pod_is_running(self, name, namespace):
        result = False
        pod_status = self.k8s_client.read_pod_status(name, namespace)
        if pod_status.status.phase != "Running":
            self.logger.debug('Pod %s not in running state.'
                              'Currently in %s' % (self.name,
                                                   pod_status.status.phase))
        else:
            self.logger.info('Pod %s is in running state.'
                             'Got IP %s' % (self.name,
                                            pod_status.status.pod_ip))
            self.pod_ip = pod_status.status.pod_ip
            self.host_ip = pod_status.status.host_ip
            self.set_compute_ip()
            result = True
        return result

    @retry(delay=5, tries=60)
    def verify_pod_is_not_in_k8s(self):
        result = False
        try:
            pod_status = self.k8s_client.read_pod_status(self.name,
                self.namespace)
            self.logger.debug('Pod %s is still present k8s, '
                              'Currently in %s state' % (self.name,
                                                   pod_status.status.phase))
            return False
        except ApiException as e:
            if e.reason == "Not Found":
                self.logger.debug('Pod %s is deleted in k8s' %(self.name))
                return True
            else:
                self.logger.exception('Error while verifying pod deletion: %s' %(
                    self.name))
                return False
        return result
    # end verify_pod_is_not_in_k8s

    def wait_till_pod_is_up(self):
        return self.verify_pod_is_running(self.name, self.namespace)

    @retry(delay=1, tries=10)
    def verify_pod_in_contrail_api(self):
        try:
            self.api_vm_obj = self.vnc_lib.virtual_machine_read(id=self.uuid)
            api_vmi_refs = self.api_vm_obj.get_virtual_machine_interface_back_refs()
            for vmi_ref in api_vmi_refs:
                x = self.vnc_lib.virtual_machine_interface_read(
                    id=vmi_ref['uuid'])
                self.vmi_objs.append(x)
                self.vmi_uuids.append(vmi_ref['uuid'])
                self.vn_names.append(x.routing_instance_refs[0][u'to'][2])
                self.vn_fq_names.append(x.virtual_network_refs[0][u'to'])
                self.logger.debug('Pod %s has vmi %s' % (self.name, x.uuid))
        except NoIdError:
            self.logger.debug('VM uuid %s not in api-server' % (self.uuid))
            return False
        self.logger.info('Verified pod %s in contrail-api' % (self.name))

        return True
    # end verify_pod_in_contrail_api

    @retry(delay=1, tries=10)
    def verify_pod_in_contrail_control(self):
        # TODO
        return True
    # verify_pod_in_contrail_control

    def set_compute_ip(self):
        if self.inputs.slave_orchestrator == 'kubernetes':
            self.compute_ip = self.get_compute_for_pod_in_nested(
                project_id=self.connections.get_project_id(),
                vm_name=self.nodename)
        else:
            self.compute_ip = self.host_ip
    # end set_compute_ip

    @retry(delay=2, tries=10)
    def verify_pod_in_contrail_agent(self):
        self.set_compute_ip()

        compute_mgmt_ip = self.inputs.host_data[self.compute_ip]['ip']
        inspect_h = self.agent_inspect[compute_mgmt_ip]

        self.tap_intfs = inspect_h.get_vna_tap_interface_by_vm(vm_id=self.uuid)
        if not self.tap_intfs:
            self.logger.warn('No tap intf seen for pod %s in %s' % (self.uuid))
            return False
        agent_vmi_ids = [x['uuid'] for x in self.tap_intfs]
        if set(agent_vmi_ids) != set(self.vmi_uuids):
            self.logger.warn('Mismatch in agent and config vmis for pod %s'
                             '. Agent : %s, Config: %s' % (self.name, agent_vmi_ids,
                                                           self.vmi_uuids))
            return False

        for tap_intf in self.tap_intfs:
            if tap_intf['active'] != 'Active':
                self.logger.warn('VMI is not active. Details: %s' % (tap_intf))
                return False
            self.logger.debug('VMI %s is active in agent %s' % (tap_intf['uuid'],
                                                                self.compute_ip))
        self.logger.info('Verified Pod %s in agent %s' % (self.name,
                                                          self.compute_ip))
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

    def run_cmd_on_pod(self, cmd, mode='api', shell=None):
        if not shell:
            shell = self._shell_arg
        if mode == 'api':
            output = self.k8s_client.exec_cmd_on_pod(self.name, cmd,
                                                     namespace=self.namespace, shell=shell)
        else:
            output = self.run_kubectl_cmd_on_master(self.name, cmd, shell)
        self.logger.debug('[Pod %s] Cmd: %s, Output: %s' % (self.name,
                                                            cmd, output))
        return output
    # run_cmd_on_pod

    @retry(delay=1, tries=10)
    def ping_with_certainty(self, *args, **kwargs):
        expectation = kwargs.get('expectation', True)
        ret_val = self.ping_to_ip(*args, **kwargs)
        return ret_val
    # end ping_with_certainty

    def ping_to_ip(self, ip, count='3', expectation=True):
        """Ping from a POD to an IP specified.

        This method logs into the POD from kubernets master using kubectl and runs ping test to an IP.
        """
        output = ''
        cmd = "ping -c %s %s" % (count, ip)
        try:
            output = self.run_cmd_on_pod(cmd)
        except Exception, e:
            self.logger.exception(
                'Exception occured while trying ping from pod')
            return False

        expected_result = ' 0% packet loss'
        result = expectation == (expected_result in output)
        if not result:
            self.logger.warn("Ping check to IP %s from pod %s failed. "
                             "Expectation: %s, Got: %s" % (ip, self.name,
                                                           expectation, result, ))
            return False
        else:
            self.logger.info('Ping check to IP %s from pod %s with '
                             'expectation %s passed' % (ip, self.name, expectation))
        return True
    # end ping_to_ip

    def modify_pod_label(self, label_name, label_value):
        '''
        Modify the label of POD
        '''
        self.logger.debug('Current POD %s labels is/are %s' %
                          (self.name, self.read().metadata.labels))
        kubectl_command = 'kubectl label --overwrite pods %s %s=%s' % (
            self.name, label_name, label_value)

        output = self.inputs.run_cmd_on_server(self.inputs.cfgm_ip,
                                               kubectl_command)

        self.logger.debug('Modified POD %s labels is/are %s' %
                          (self.name, self.read().metadata.labels))

        if label_name in self.read().metadata.labels:
            if self.read().metadata.labels[label_name] != label_value:
                self.logger.error(
                    'Label value is not set properly')
                return False
        else:
            self.logger.error(
                'Label key is not present in modified labels')
            return False
        return output
    # end modify_pod_label

    def get_compute_for_pod_in_nested(self, project_id, vm_name):
        returnVal = None
        if self.inputs.slave_orchestrator == 'kubernetes':
            self.vm_obj = self.connections.orch.get_vm_if_present(vm_name,
                                                                  project_id=project_id)
            returnVal = self.inputs.get_host_ip(
                self.connections.orch.get_host_of_vm(self.vm_obj))
        return returnVal
