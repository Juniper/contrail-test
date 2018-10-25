import fixtures
from vnc_api.vnc_api import NoIdError
from kubernetes.client.rest import ApiException

from common import log_orig as contrail_logging
from tcutils.util import get_random_name, retry


class NetworkPolicyFixture(fixtures.Fixture):
    '''
    '''

    def __init__(self,
                 connections,
                 name=None,
                 namespace='default',
                 metadata=None,
                 spec=None):
        self.logger = connections.logger or contrail_logging.getLogger(
            __name__)
        self.name = name or metadata.get('name') or get_random_name('service')
        self.namespace = namespace
        self.k8s_client = connections.k8s_client
        self.vnc_api_h = connections.vnc_lib
        self.metadata = {} if metadata is None else metadata
        self.spec = {} if spec is None else spec
        self.v1_networking = self.k8s_client.v1_networking
        self.agent_inspect = connections.agent_inspect
        self.connections = connections
        self.inputs = connections.inputs
        if self.inputs.slave_orchestrator == 'kubernetes':
            prefix = 'default-policy-management:%s' % self.connections.project_name
            self.k8s_default_network_policies = [prefix + '-allowall',
                                            prefix + '-Ingress',
                                            prefix + '-denyall']
            self.k8s_defaut_aps = prefix
        else:
            self.k8s_default_network_policies = ['default-policy-management:k8s-allowall',
                                                'default-policy-management:k8s-Ingress',
                                                'default-policy-management:k8s-denyall']
            self.k8s_defaut_aps = "default-policy-management:k8s"
        
        self.already_exists = None

    def setUp(self):
        super(NetworkPolicyFixture, self).setUp()
        self.create()

    def verify_on_setup(self):
        if not self.verify_network_policy_in_k8s():
            self.logger.error('Network Policy %s verification in kubernetes failed'
                              % (self.name))
            return False
        if not self.verify_network_policy_in_kube_manager():
            self.logger.error('Network Policy %s verification in Kube Manager failed'
                              % (self.name))
            return False
        if not self.verify_default_policies_in_agent():
            self.logger.error('Default k8s Policy verification in Agent failed')
            return False
        if not self.verify_firewall_policy_in_agent():
            self.logger.error('Network Policy %s verification in Agent failed'
                              % (self.name))
            return False
        self.logger.info('Network Policy %s verification passed' % (self.name))
        return True
    # end verify_on_setup

    def cleanUp(self):
        self.delete()
        super(NetworkPolicyFixture, self).cleanUp()

    def _populate_attr(self):
        self.uuid = self.obj.metadata.uid
        self.spec_obj = self.obj.spec
        self.metadata_obj = self.obj.metadata
        self.kind = self.obj.kind

    def read(self):
        try:
            self.obj = self.v1_networking.read_namespaced_network_policy(
                self.name, self.namespace)
            self._populate_attr()
            if self.already_exists is None:
                self.already_exists = True
            return self.obj
        except ApiException as e:
            self.logger.debug('Network policy %s not present' % (self.name))
            return None
    # end read

    def create(self):
        policy_exists = self.read()
        if policy_exists:
            return policy_exists
        self.already_exists = False
        self.obj = self.k8s_client.create_network_policy(
            self.namespace,
            name=self.name,
            metadata=self.metadata,
            spec=self.spec)
        self._populate_attr()
    # end create

    def delete(self):
        if not self.already_exists:
            return self.k8s_client.delete_network_policy(self.namespace,
                                                         self.name)
    # end delete

    def update(self, metadata=None, spec=None):
        self.metadata = metadata or self.metadata
        self.spec = spec or self.spec
        self.obj = self.k8s_client.update_network_policy(
            self.name,
            self.namespace,
            metadata=self.metadata,
            spec=self.spec)
        self._populate_attr()
    # end update
    
    @retry(delay=2, tries=60)
    def verify_network_policy_in_k8s(self):
        if self.read():
            self.logger.info("Network policy found in k8s")
        else:
            self.logger.warn('Network policy not Found in K8s')
            return False
        return True
    # end verify_ingress_in_k8s
    
    @retry(delay=2, tries=60)
    def verify_network_policy_in_kube_manager(self):
        km_h = self.connections.get_kube_manager_h()
        self.np_info = km_h.get_network_policy_info(np_uuid = self.uuid)
        if self.np_info:
            self.logger.info('Network Policy %s with uuid %s found in kube manager' 
                             % (self.name, self.uuid))
        else:
            self.logger.warn('Network Policy %s with uuid %s not found in kube manager' 
                             % (self.name, self.uuid))
            return False
        return True
    # end verify_ingress_in_k8s

    @retry(delay=2, tries=15)
    def verify_firewall_policy_in_agent(self):
        km_h = self.connections.get_kube_manager_h()
        for nodeip in self.inputs.compute_ips:
           agent_h = self.agent_inspect[nodeip]
           self.np_info = km_h.get_network_policy_info(np_uuid = self.uuid)
           fw_polify_fq_name = self.np_info['vnc_firewall_policy_fqname']
           fwPolicy = agent_h.get_fw_policy(policy_fq_name = fw_polify_fq_name)
           if fwPolicy:
                self.logger.info("Network policy with name %s found in agent"
                             % self.name)
                return True
        self.logger.warn("Network policy with name %s not found in agent"
                         % self.name)
        return False
    #end verify_firewall_policy_in_agent


    @retry(delay=2, tries=15)
    def verify_default_policies_in_agent(self):
        km_h = self.connections.get_kube_manager_h()
        for nodeip in self.inputs.compute_ips:
           agent_h = self.agent_inspect[nodeip]
           default_aps = agent_h.get_aps(aps_fq_name = self.k8s_defaut_aps)
           if default_aps:
               aps_fw_policy_uuid = [elem['firewall_policy'] for elem in default_aps['firewall_policy_list']]
               for elem in self.k8s_default_network_policies :
                  fw_policy = agent_h.get_fw_policy(policy_fq_name = elem)
                  if  fw_policy:
                      self.logger.info("Network policy with name %s found in agent"
                                     % elem)
                      if fw_policy['uuid'] in aps_fw_policy_uuid:
                         self.logger.info("Network policy with name %s associated with default ks8"
                                      % elem)
                         return True
        self.logger.warn("Default APS %s for k8s not found in any agent"
                             % self.k8s_defaut_aps)
        return False
    #end verify_default_policies_in_agent
