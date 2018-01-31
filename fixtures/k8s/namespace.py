import re
import time
import fixtures
from kubernetes.client.rest import ApiException
from kubernetes import client
from vnc_api.vnc_api import NoIdError

from common import log_orig as contrail_logging
from tcutils.util import get_random_name, retry, get_lock


class NamespaceFixture(fixtures.Fixture):
    '''
    '''

    def __init__(self, connections, name=None, isolation=False):
        self.connections = connections
        self.logger = connections.logger or contrail_logging.getLogger(
            __name__)
        self.name = name or get_random_name('namespace')
        self.k8s_client = connections.k8s_client
        self.vnc_api_h = connections.vnc_lib
        self.isolation = isolation

        self.already_exists = False
        self.api_s_obj = None
        self.project_name = None
        self.project_fq_name = None
        self.inputs = self.connections.inputs
        self.project_isolation = True
        self.verify_is_run = False

    def setUp(self):
        super(NamespaceFixture, self).setUp()
        self.create()

    def verify_on_setup(self):
        if not self.verify_namespace_is_active():
            self.logger.error('Namespace %s verification failed' % (
                self.name))
            return False
       
        if self.inputs.slave_orchestrator == 'kubernetes':
            self.logger.info('Skipping Namespace API server validation in nested mode')
        else: 
            if not self.verify_namespace_in_contrail_api():
                self.logger.error('Namespace %s not seen in Contrail API' % (
                self.name))
                return False
            self.logger.info('Namespace %s verification passed' % (self.name))
        self.verify_is_run = True
        return True
        # end verify_on_setup

    @retry(delay=1, tries=10)
    def verify_namespace_is_active(self):
        if self.status != 'Active':
            self.logger.warn('Namespace %s is not Active yet, It is %s' % (
                             self.name, self.status))
            return False
        return True
    # end verify_namespace_is_active

    def _read_cluster_project(self):
        project = None
        m = None
        cmd = 'grep "^[ \t]*cluster_project" /etc/contrail/contrail-kubernetes.conf'
        cp_line = self.inputs.run_cmd_on_server(self.inputs.kube_manager_ips[0],
                cmd, container='contrail-kube-manager')
        if 'cluster_project' in cp_line:
            m = re.match('[ ]*cluster_project.*?=[ ]*(.*)?', cp_line)
            if m:
                project = eval(m.group(1)).get('project')
                self.project_isolation = False
            else:
                project = None
        else:
            project = None
        return project
    # end _read_cluster_project

    def get_project_name_for_namespace(self):
        # Check if cluster_project is defined, return that
        # Else, return self.name

        # Get lock in case some other api is setting the config
        with get_lock('kube_manager_conf'):
            project = self._read_cluster_project()
            if project:
                return project
            else:
                return self.name

    @retry(delay=1, tries=10)
    def verify_namespace_in_contrail_api(self):
        self.project_name = self.get_project_name_for_namespace()
        self.project_fq_name = '%s:%s' %(self.inputs.admin_domain,
                                         self.project_name)
        try:
            self.api_s_obj = self.vnc_api_h.project_read(
                fq_name_str=self.project_fq_name)
        except NoIdError:
            self.logger.warn('Project %s for Namespace %s UUID %s is not seen '
                'in contrail-api' % (self.project_fq_name, self.name, self.uuid))
            return False
        self.logger.info('Project %s for Namespace %s is seen in contrail-api'
            '' % (self.project_fq_name, self.name))
        self.logger.debug('Project uuid in Contrail is %s' %(
            self.api_s_obj.uuid))
        return True
    # end verify_namespace_in_contrail_api

    def cleanUp(self):
        super(NamespaceFixture, self).cleanUp()
        self.delete()

    def _populate_attr(self):
        self.uuid = self.obj.metadata.uid
        self.status = self.obj.status.phase
        self.labels = self.obj.metadata.labels

    def read(self):
        try:
            self.obj = self.k8s_client.v1_h.read_namespace(self.name)
            self._populate_attr()
            self.already_exists = True
            return self.obj
        except ApiException as e:
            self.logger.debug('Namespace %s not present' % (self.name))
            return None
    # end read

    def create(self):
        ns_exists = self.read()
        if ns_exists:
            self.logger.info('Namespace %s already exists' % (self.name))
            return ns_exists
        body = client.V1Namespace()
        body.metadata = client.V1ObjectMeta(name=self.name)
        if self.isolation:
            body.metadata.annotations = {"opencontrail.org/isolation": "true"}
        self.obj = self.k8s_client.v1_h.create_namespace(body)
        self._populate_attr()
        self.logger.info('Created namespace %s' % (self.name))
        if self.inputs.deployer=='openshift':
            for kube_manager_ip in self.inputs.kube_manager_ips:
                openshift_command = 'oadm policy add-scc-to-user anyuid -n %s -z default' % (self.name)
                output = self.inputs.run_cmd_on_server(kube_manager_ip,openshift_command)
        # TODO
        # Need to remove
        time.sleep(3)
    # end create

    def delete(self):
        if not self.already_exists:
            body = client.V1DeleteOptions()
            self.logger.info('Deleting namespace %s' % (self.name))
            self.k8s_client.v1_h.delete_namespace(self.name, body)
            assert self.verify_on_cleanup()
    # end delete

    def verify_on_cleanup(self):
        if not self.verify_is_run:
            self.logger.debug('No need to do namespace deletion check')
            return True
        assert self.verify_ns_is_not_in_k8s(), ('Namespace deletion '
                                                'verification in k8s failed')
        if self.inputs.slave_orchestrator == 'kubernetes':
            self.logger.info('Skipping Namespace API server validation in nested mode')
        else:
            assert self.verify_ns_is_not_in_contrail_api(), ('Namespace deletion '
            'verification in contrail-api failed')
        return True
    # end verify_on_cleanup

    @retry(delay=2, tries=30)
    def verify_ns_is_not_in_k8s(self):
        if self.k8s_client.is_namespace_present(self.name):
            self.logger.debug('Namespace %s still in k8s' % (self.name))
            return False
        else:
            self.logger.debug('Namespace %s is not in k8s' % (self.name))
            return True
    # end verify_ns_is_not_in_k8s

    @retry(delay=2, tries=30)
    def verify_ns_is_not_in_contrail_api(self):
        if not self.project_isolation:
            self.logger.debug('No need to check project deletion in contrail-api')
            return True
        try:
            api_s_obj = self.vnc_api_h.project_read(
                fq_name_str=self.project_fq_name)
            self.logger.warn('Project %s for Namespace %s is still seen in'
                ' contrail-api' % (self.project_fq_name, self.name))
            return False
        except NoIdError:
            self.logger.info('Project %s for Namespace %s UUID %s is deleted '
                'from contrail-api' % (self.project_fq_name, self.name,
                                       self.uuid))
            return True
    # end verify_ns_is_not_in_contrail_api

    def enable_isolation(self):
        return self.k8s_client.set_isolation(self.name)

    def disable_isolation(self):
        return self.k8s_client.set_isolation(self.name, False)

    def set_labels(self, label_dict):
        self.obj = self.k8s_client.set_namespace_label(self.name, label_dict)
        self._populate_attr()
    # end set_labels
   
    def enable_service_isolation(self):
        return self.k8s_client.set_service_isolation(self.name, enable=True)

    def disable_service_isolation(self):
        return self.k8s_client.set_service_isolation(self.name, enable=False)
