import fixtures
from vnc_api.vnc_api import *
import inspect
from quantum_test import *


class VN_Policy_Fixture(fixtures.Fixture):

      '''Fixture to take care of linking VN & Policies. Has methods to attach & detach policies to/from VN.
         Useful when VNs are created without policy and attached later..
         Fixture will take care of cleanup in reverse order.
         Ex. createVN, createPolicy, attachVNPolicy, test, cleanup [detachVNPolicy, delete Policy, deleteVN]
      '''
    def __init__(self, connections, vn_name, vn_obj,topo, project_name, policy_obj=[]):
        self.connections= connections
        self.inputs= self.connections.inputs
        self.quantum_fixture= self.connections.quantum_fixture
        self.project_name=project_name
        self.vnc_lib= self.connections.vnc_lib
        self.api_s_inspect= self.connections.api_server_inspect
        self.logger= self.inputs.logger
        self.topo= topo
        self.policy_obj=policy_obj
        self.vn_obj=vn_obj
        self.skip_verify='no'
        self.vn=vn_name
        self.already_present= False
        
    #end __init__

    def setUp (self):
        super(VN_Policy_Fixture, self).setUp()
        policy_of_vn=self.api_s_inspect.get_cs_vn_policys(project=self.project_name,vn=self.vn,refresh=True)
        if policy_of_vn :
           for policy in policy_of_vn :
               if policy in self.topo.vn_policy[self.vn] :
                  self.logger.info ("Policy:%s already Associated to VN:%s'"%(policy,self.vn))
                  self.already_present= True
        else:
           if self.policy_obj[self.vn] :
              self.logger.info ("Setup step: Associating the policy to VN'")
              policy_fq_names= [ self.quantum_fixture.get_policy_fq_name( x ) for x in self.policy_obj[self.vn]]
              self.vn_obj[self.vn].bind_policies( policy_fq_names, self.vn_obj[self.vn].vn_id)
	      self.logger.info ('Associated Policy:%s to %s'%(policy_fq_names,self.vn))
        return self
    #end attachPolicytoVN

    #end setUp


    def cleanUp(self):
        super(VN_Policy_Fixture, self).cleanUp()
        do_cleanup= True
        if self.inputs.fixture_cleanup == 'no' : do_cleanup = False
        if self.already_present : do_cleanup= False
        if self.inputs.fixture_cleanup == 'force' : do_cleanup = True
        if do_cleanup:
           self.detach_Policy_VN()
        else :
           self.logger.info( 'Skipping policy detach from VN %s' %(self.vn) )
    #end cleanUp

    def detach_Policy_VN(self):
        self.logger.info ('Detaching the Policy for VN :%s '%(self.vn)) 
        policy_fq_names=[]
        if self.policy_obj[self.vn] :
           policy_of_vn=self.api_s_inspect.get_cs_vn_policys(project=self.project_name,vn=self.vn,refresh=True)
           if policy_of_vn :
              for policy in policy_of_vn :
                  policy_fq_names.append(self.api_s_inspect.get_cs_policy(project=self.project_name,policy=policy)['network-policy']['fq_name'])
              self.vn_obj[self.vn].unbind_policies(self.vn_obj[self.vn].vn_id,policy_fq_names)
              self.logger.info ('Detached Policy:%s from %s'%(policy_fq_names,self.vn))
    #end of detach_policy_VN
