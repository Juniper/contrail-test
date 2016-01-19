import fixtures
from vnc_api import vnc_api
import inspect
from quantum_test import *
try:
    from webui_test import *
except ImportError:
    pass

class VN_Policy_Fixture(fixtures.Fixture):

    """ Fixture to take care of linking VN & Policies. Has methods to attach & detach policies to/from VN.
          Useful when VNs are created without policy and attached later..
          Fixture will take care of cleanup in reverse order.
          Ex. createVN, createPolicy, attachVNPolicy, test, cleanup [detachVNPolicy, delete Policy, deleteVN]
    """

    def __init__(self, connections, vn_name, vn_obj, vn_policys, project_name, options='openstack', policy_obj=[]):

        self.connections = connections
        self.inputs = self.connections.inputs
        self.quantum_h = self.connections.quantum_h
        self.project_name = project_name
        self.vnc_lib = self.connections.vnc_lib
        self.api_s_inspect = self.connections.api_server_inspect
        self.logger = self.inputs.logger
        self.vn_policys = vn_policys
        self.policy_obj = policy_obj
        self.vn_obj = vn_obj
        self.skip_verify = 'no'
        self.vn = vn_name
        self.already_present = False
        self.option = options if self.inputs.orchestrator == 'openstack' else 'contrail'
        if self.inputs.verify_thru_gui():                                                                                    
            self.browser = self.connections.browser                                                                          
            self.browser_openstack = self.connections.browser_openstack                                                      
            self.webui = WebuiTest(self.connections, self.inputs)  
    # end __init__

    def setUp(self):
        super(VN_Policy_Fixture, self).setUp()
        policy_of_vn = self.api_s_inspect.get_cs_vn_policys(
            project=self.project_name, vn=self.vn, refresh=True)
        if policy_of_vn:
            for policy in policy_of_vn:
                if policy in self.vn_policys:
                    self.logger.info(
                        "Policy:%s already Associated to VN:%s'" %
                        (policy, self.vn))
                    self.already_present = True
        else:
            if self.policy_obj[self.vn]:
                self.logger.debug("Setup step: Associating the policy to VN'")
                if self.option == 'openstack':
                    policy_fq_names = [
                        self.quantum_h.get_policy_fq_name(x) for x in self.policy_obj[self.vn]]
                    if self.inputs.is_gui_based_config():
                        self.webui.bind_policies(self)
                    else:
                        self.vn_obj[self.vn].bind_policies(
                            policy_fq_names, self.vn_obj[self.vn].vn_id)
                    self.logger.debug('Associated Policy:%s to %s' %
                                     (policy_fq_names, self.vn))
                elif self.option == 'contrail':
                    ref_tuple = []
                    vn_update_rsp = None
                    vnc_obj = self.vn_obj[self.vn].getObj()
                    policys = self.policy_obj[self.vn]
                    for seq, conf_policy in enumerate(policys):
                        vnc_obj.add_network_policy(conf_policy,
                           vnc_api.VirtualNetworkPolicyType(
                              sequence=vnc_api.SequenceType(major=seq, minor=0)))
                    vn_update_rsp = self.vnc_lib.virtual_network_update(vnc_obj)
                    self.logger.info('Associated Policy to %s' % (self.vn))
        return self
    # end attachPolicytoVN

    # end setUp

    def cleanUp(self):
        super(VN_Policy_Fixture, self).cleanUp()
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if self.already_present:
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if do_cleanup:
            self.detach_Policy_VN()
        else:
            self.logger.debug('Skipping policy detach from VN %s' % (self.vn))
    # end cleanUp

    def detach_Policy_VN(self):
        self.logger.debug('Detaching the Policy for VN :%s ' % (self.vn))
        policy_fq_names = []
        if self.policy_obj[self.vn]:
            policy_of_vn = self.api_s_inspect.get_cs_vn_policys(
                project=self.project_name, vn=self.vn, refresh=True)
            if policy_of_vn:
                if self.option == 'openstack':
                    for policy in policy_of_vn:
                        policy_fq_names.append(self.api_s_inspect.get_cs_policy(
                            project=self.project_name, policy=policy)['network-policy']['fq_name'])
                    if self.inputs.is_gui_based_config():
                        self.webui.detach_policies(self)
                    else:
                        self.vn_obj[self.vn].unbind_policies(
                            self.vn_obj[self.vn].vn_id, policy_fq_names)
                    self.logger.debug('Detached Policy:%s from %s' %
                                     (policy_fq_names, self.vn))
                elif self.option == 'contrail':
                    vn_update_rsp = None
                    vnc_obj = self.vn_obj[self.vn].getObj()
                    for conf_policy in self.policy_obj[self.vn]:
                        vnc_obj.del_network_policy(conf_policy)
                    vn_update_rsp = self.vnc_lib.virtual_network_update(vnc_obj)
                    self.logger.info('Detached Policy from %s' % (self.vn))

    # end of detach_policy_VN
