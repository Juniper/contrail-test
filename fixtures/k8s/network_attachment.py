import json
import fixtures
from kubernetes.client.rest import ApiException
from vnc_api.vnc_api import NoIdError
from common import log_orig as contrail_logging
from tcutils.util import get_random_name, retry
from pprint import pprint


class NetworkAttachmentFixture(fixtures.Fixture):
    '''
    This fixture is to create ,delete and describe the custom resources ,network attachment  definitions
    in k8s world
    '''
    def __init__(self,
                 connections,
                 name=None,
                 namespace='default',
                 metadata=None,
                 spec=None):
        self.logger = connections.logger or contrail_logging.getLogger(
            __name__)
        self.inputs = connections.inputs
        self.name = name or metadata.get('name') or get_random_name('nad')
        self.namespace = namespace
        self.k8s_client = connections.k8s_client
        self.metadata = {} if metadata is None else metadata
        self.spec = {} if spec is None else spec
        self.already_exists = None
        self.connections = connections
        self.vnc_lib = connections.get_vnc_lib_h()
        self.agent_inspect = connections.agent_inspect
    # end __init__

    def setUp(self):
        super(NetworkAttachmentFixture, self).setUp()
        self.create()

    def verify_on_setup(self):
        '''
        Verify the Network Attachemnt Definitions are reflecting
        in contrail system
        '''
        if not self.verify_nad_is_created(self.name, self.namespace):
            self.logger.error('Network Attachment %s is not created'
                              % (self.name))
            return False
        if not self.verify_nad_in_k8s():
            self.logger.error('Network Attachment %s not seen in Contrail Kube Manager' % (
                self.name))
            return False
        self.logger.info('Network Attachment  %s verification passed' % (self.name))
        return True
    # end verify_on_setup

    def cleanUp(self):
        self.delete()
        super(NetworkAttachmentFixture, self).cleanUp()

    @retry(delay=3, tries=20)
    def _get_uuid(self):
        self.obj = self.k8s_client.read_custom_resource_object(name=self.name, namespace=self.namespace)
        if not self.obj.metadata.uid:
            self.logger.debug('nad %s uuid not yet populated' % (self.name))
            return (False, None)
        return (True, self.obj.metadata.uid)
    # end _get_uuid

    def _populate_attr(self):
        (ret_val, self.uuid) = self._get_uuid()
        self.annotations = self.obj.metadata.annotations
        self.logger.debug('NAD : %s UUID is %s' %(self.name, self.uuid))

    def read(self):
        output = self.run_kubectl_cmd_on_master( self.name, self.namespace)
        if output :
          return output
        return None
    # end read

    def create(self):
        self.obj = self.k8s_client.create_custom_resource_object(
            namespace=self.namespace,
            name=self.name,
            metadata=self.metadata,
            spec=self.spec)
    # end create

    def delete_only(self):
        if not self.already_exists:
            resp = self.k8s_client.delete_custom_resource_object(name=self.name, namespace=self.namespace)
            return resp
    # end delete_only

    def delete(self):
        if not self.already_exists:
            resp = self.delete_only()
            assert self.verify_on_cleanup()
    # end delete

    def verify_on_cleanup(self):
        assert self.verify_nad_is_not_in_k8s(), ('Network Attachement Definition %s cleanup checks'
                                                         ' in kube manager failed' % (self.name))
        return True
        self.logger.info('Verifications on pod %s cleanup passed')
    # end verify_on_cleanup


    @retry(delay=5, tries=60)
    def verify_nad_is_created(self, name, namespace):
        result = False
        output = self.run_kubectl_cmd_on_master(self.name, namespace=self.namespace)
        nad = self.k8s_client.read_custom_resource_object(name=name, namespace=namespace)
        if not nad:
            self.logger.debug('Network Attachement Definitions  %s not created.')
        else:
            self.logger.info('Network Attachement Definition created %s '
                             % (self.name))
            result = True
        return result

    @retry(delay=5, tries=12)
    def verify_nad_is_not_in_k8s(self):
        output = self.run_kubectl_cmd_on_master(self.name, namespace=self.namespace)
        pprint (output)
        if 'not found' in output:
            self.logger.info('Network Attachement  %s not found in kubernetes'
                             % (self.name))
            return True
        else:
            self.logger.warn('Network Attachement %s  found in kube manager'
                             % (self.name))
        return False
    # end verify_nad_is_not_in_k8s

    @retry(delay=2, tries=10)
    def verify_nad_in_k8s(self):
        output = self.run_kubectl_cmd_on_master(self.name, namespace=self.namespace)
        pprint (output)
        if self.name in output:
            self.logger.info('Network Attachement  %s found in kubernetes'
                             % (self.name))
        else:
            self.logger.warn('Network Attachement %s not found in kube manager' 
                             % (self.name))
            return False
        return True
    # verify_nad_in_kube_manager

    def run_kubectl_cmd_on_master(self, nad_name, namespace='default', operation="get"):
        kubectl_command = 'kubectl %s network-attachment-definition %s -n %s' % (operation,nad_name,namespace)
        output = self.inputs.run_cmd_on_server(self.inputs.k8s_master_ip,
                                               kubectl_command)
        return output
