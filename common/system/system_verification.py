from tcutils.test_lib.test_utils import assertEqual

def system_vna_verify_policy(self, policy_fixt, topo, state):
    # Verify all policies in all compute nodes..
    self.logger.info("Starting Verifications after %s" % (state))
    ret = policy_fixt.verify_policy_in_vna(topo)
    assertEqual(ret['result'], True, ret['msg'])
# end of system_vna_verify_policy


def all_policy_verify(
        self,
        config_topo,
        topo,
        state='unspecified',
        fixture_only='no'):
    '''Call all policy related verifications..
    Useful to debug failures... call this on failure..
    Verify & assert on fail'''
    self.logger.info("Starting Verifications after %s" % (state))
    # calling policy fixture verifications
    for policy_name, policy_fixt in config_topo['policy'].items():
        ret = policy_fixt.verify_on_setup()
        assertEqual(ret['result'], True, ret['msg'])
    # calling vn-policy verification
    for vn_name, vn_fixt in config_topo['vn'].items():
        ret = vn_fixt.verify_vn_policy_in_api_server()
        assertEqual(ret['result'], True, ret['msg'])
    if fixture_only == 'no':
        # This is not a fixture verfication,
        # requires runtime[config_topo] & user-def[topo] topology to be in sync to verify
        # calling vna-acl verification
        # pick any policy configured
        policy_fixt = config_topo['policy'][str(topo.policy_list[0])]
        system_vna_verify_policy(self, policy_fixt, topo, state)
# end of all_policy_verify


def verify_system_parameters(self, verification_obj):
    for projects in verification_obj['data'][1]:
        for poj_obj in verification_obj['data'][1][projects]['project']:
            # for each project in the topology verify the project parameters.
            assert verification_obj['data'][1][projects][
                'project'][poj_obj].verify_on_setup()
        for vn_obj in verification_obj['data'][1][projects]['vn']:
            # for each vn in all the projects in the topology verify the vn
            # parameters.
            assert verification_obj['data'][1][
                projects]['vn'][vn_obj].verify_on_setup()
        for vm_obj in verification_obj['data'][1][projects]['vm']:
            # for each vm in all the projects in the topology verify the vm
            # parameters.
            assert verification_obj['data'][1][
                projects]['vm'][vm_obj].verify_on_setup()
        for policy_obj in verification_obj['data'][1][projects]['policy']:
            # for each policy in all the projects in the topology verify the
            # policies.
            assert verification_obj['data'][1][projects][
                'policy'][policy_obj].verify_on_setup()
# end verify_system_parameters

def get_comp_node_by_vn(self, vn_fq_name):
    vn_fq_name=vn_fq_name.split(":")
    sing_comp_node_vn_list={}
    domain= vn_fq_name[-3]
    project=vn_fq_name[-2]
    vn= vn_fq_name[-1]
    #Get the list of vn names  from each compute node
    for compute_ip in self.inputs.compute_ips  :
        no_of_vns=self.agent_inspect[compute_ip].get_vna_vn_list( domain=domain, project=project)['VNs']
        vn_list=[]
        for i in range(len(no_of_vns)) :
            x=no_of_vns[i]['name']
            x=x.split(":")
            vn_list.append(x[-1])
        sing_comp_node_vn_list[compute_ip]= vn_list
    #Get the compute node list for each vn
    vn_comp_node_list={}
    vn_list=sing_comp_node_vn_list.values()
    for i in range(len(vn_list)) :
        compute_ips=[]
        for j in range(len(vn_list[i])):
            for compute_ip in sing_comp_node_vn_list.keys() :
                if vn_list[i][j] in sing_comp_node_vn_list[compute_ip] :
                   compute_ips.append(compute_ip)
            vn_comp_node_list[vn_list[i][j]]=compute_ips
    #Compare the vn  from the compute nodes
    vn_comp_nodes ={}
    for vn_list in vn_comp_node_list.keys() :
        if vn_list == vn :
           vn_comp_nodes[vn_list]= vn_comp_node_list[vn_list]
    return vn_comp_nodes[vn]
    #end of get_comp_node_by_vn

