import os
import copy, traceback
from quantum_test import *
from nova_test import *
from policy_test import *
from vn_test import *
import string
def comp_rules_from_policy_to_system(self):
    """ Comparing Policy rule to system rule(agent) . 
    """
    #Initializing the connections to quantum/api/nova/agent fixtures from self
    self.connections= ContrailConnections(self.inputs)
    self.agent_inspect= self.connections.agent_inspect
    self.quantum_fixture= self.connections.quantum_fixture
    self.nova_fixture = self.connections.nova_fixture
    self.api_s_inspect=self.connections.api_server_inspect
    self.logger= self.inputs.logger
    self.project_name=self.inputs.project_name

    result= True; msg=[]
    ##
    #Step 1 :Get all projects 
    project_names,project_ids,project_domains=get_project_list(self)
    for pr in range(len(project_names))  :
        #Step 2:Check VMs are exist for selected project
        pro_vm_list=self.nova_fixture.get_vm_list(project_id=project_ids[pr] )
        if pro_vm_list:
           #Arragenging all VM's  
           vm_list=[]
           old_vn=''
           for i in range(len(pro_vm_list)):
               vm=str(pro_vm_list[i].name)
               vm_list.append(vm)
    
           #Step 2:Verify quantum rules for each VM.
           for vm in range(len(vm_list)):
               policys_list=[]
               vn_list=[]  
        
               # Step 3 :Get All VNs of selected VM
               vns_of_vm=pro_vm_list[vm].networks.keys()
               for i in range(len(vns_of_vm)):
                   vn_obj=str(vns_of_vm[i])
                   vn_list.append(vn_obj)
               #Verifying the quntum rules for each VN
               for vn in vn_list:
                   if old_vn != vn :
                      #step 4:Get the policys associated with vn from API server 
                      policys_list=self.api_s_inspect.get_cs_vn_policys(project = project_names[pr],domain=project_domains[pr], vn= vn, refresh= True) 
                      if  policys_list == [] :
                          break
                      else:
                          pass
                      self.logger.info("Order of the policy's list:%s"%(policys_list))
                      user_rules_tx= {}
                      rules_by_vn= {}
                      rules_by_vn[vn]= []
                      
                      #Step 5 :Aggregating  all  attached policys rules for each network.
                      for policy in policys_list :
                   
                          #Get the rules from quantum client
                          policy_detail=self.quantum_fixture.get_policy_if_present(project_names[pr],policy)
                          
                          # Total no of rules for each policy
                          no_of_rules=policy_detail['policy']['entries']['policy_rule']
                   
                          #Traslation of  quantum rules to ACES 
                          fq_name=[project_domains[pr],project_names[pr],vn]
                          fq_vn=':'.join(fq_name)  
                          self.logger.info( "Traslation of quantum rules to ACES format") 
                          updated_quantum_rules,uni_rule=tx_quantum_rules_to_aces(no_of_rules,fq_vn)
                          user_rules_tx[policy]= updated_quantum_rules 
                          # Step 5b: Aggregate rules by network
                          self.logger.info( "vn is %s, vn_policy is %s" %(vn, policy))
                          rules_by_vn[vn] += user_rules_tx[policy]
               
                      #Step 6:Remove the duplicate rules if the multilple policies have same rule
                      rules_by_vn[vn]=trim_duplicate_rules(rules_by_vn[vn]) 
               
                      # Step 7:Translate quantum- ACEs to system format and update ACE IDs
                      if rules_by_vn[vn] != []:
                         rules_by_vn[vn]= tx_quntum_def_aces_to_system (fq_vn, rules_by_vn[vn],uni_rule)
                         rules_by_vn[vn]= policy_test_utils.update_rule_ace_id (rules_by_vn[vn])
                      self.logger.debug("VN: %s, expected ACE's is " %(vn))
                      for r in rules_by_vn[vn]: self.logger.info("%s" %(json.dumps(r, sort_keys=True)))
                      # end building VN ACE's from user rules
               
                      # Step 8:Get actual from vna in compute nodes [referred as cn] and compare with quntum rules and update the result
                      rules_by_all_vn=rules_by_vn[vn]
                      project_name=project_names[pr]  
                      result,msg =comp_user_rules_to_system_rules(self,vn,rules_by_all_vn,policys_list,pro_vm_list,vm_list,vm,project_name)
                      self.logger.info ("Verify policy rules for other vn if it is present")
                      old_vn=vn
                   else:
                      pass
        else:  
               self.logger.info ("Skipping the policy rule comparison since VM's are not exist for selected project:%s"%(project_names[pr]))
    self.logger.info ("Policy rules comparison with system for all Virtual networks are done")
    return (result,msg) 
 
    #end  comp_rules_from_policy_to_system


def get_project_list(self):
    all_projects=self.api_s_inspect.get_cs_domain()['domain']['projects']
    project_names=[]
    project_ids=[]
    project_domains=[] 
    for i in range(len(all_projects)) :
	pro_domain=str(all_projects[i]['to'][0])
        pro_name=str(all_projects[i]['to'][1])
        pro_id=str(all_projects[i]['uuid'])
        if all(x != pro_name for x in ('default-project' ,'invisible_to_admin', 'service')):
           if  pro_name.startswith('vpc') :
              pass
           else:
              project_names.append(pro_name)
	      project_ids.append(pro_id)
	      project_domains.append(pro_domain)
        else:
            pass
    return (project_names, project_ids,project_domains)

def tx_quantum_rules_to_aces(no_of_rules,fq_vn):
    ''' Generating the quantum rules to aces '''
    total_rules=len(no_of_rules)
    user_rules_tx=[]
    uni_rule={}
   #step 1: Getting all tuples list from quantum rules :
    for i in range(total_rules):
        temp_rule={}
        temp_rule['direction']=str(no_of_rules[i]['direction'])
        temp_rule['proto_l']=str(no_of_rules[i]['protocol'])
        dest=str(no_of_rules[i]['dst_addresses'][0]['virtual_network'])
        if  dest == 'any' :
            temp_rule['dst']='any'
        elif dest =='local' :
            temp_rule['dst']= fq_vn
        else:
            #dst_ntw=string.split(dest,':')
            #temp_rule['dst']=dst_ntw[2]
            temp_rule['dst']=dest
        temp_rule['simple_action']=str(no_of_rules[i]['action_list']['simple_action'])
        temp_rule['action_l']=[str(no_of_rules[i]['action_list']['simple_action'])]
        source_addr=str(no_of_rules[i]['src_addresses'][0]['virtual_network'])
        if   source_addr == 'any' :
             temp_rule['src']='any'
        elif source_addr == 'local':
              temp_rule['src']= fq_vn
        else:
            #src_addr=string.split(source_addr,':')
            #temp_rule['src']=src_addr[2]
            temp_rule['src']=source_addr
        if    ((no_of_rules[i]['src_ports'][0]['start_port']) == -1 and (no_of_rules[i]['src_ports'][0]['end_port']) == -1) :
               temp_rule['src_port_l']={'max': '65535', 'min': '0'}
        else:
               a=str(no_of_rules[i]['src_ports'][0]['start_port'])
               b=str(no_of_rules[i]['src_ports'][0]['end_port'])
               temp_rule['src_port_l']={'max':a,'min':b}
        if    ((no_of_rules[i]['dst_ports'][0]['start_port']) == -1 and (no_of_rules[i]['dst_ports'][0]['end_port']) == -1) :
              temp_rule['dst_port_l']={'max': '65535', 'min': '0'}
        else:
              a=str(no_of_rules[i]['dst_ports'][0]['start_port'])
              b=str(no_of_rules[i]['dst_ports'][0]['end_port'])
              temp_rule['dst_port_l']={'max':a,'min':b}
        user_rules_tx.append(temp_rule)

    # step 2 :protocol value mapping
    for rule in user_rules_tx:
        if rule['proto_l'] == 'any': rule['proto_l']= {'max': '255', 'min': '0'}
        else: rule['proto_l'] = {'max': str(rule['proto_l']),
                'min': str(rule['proto_l'])}

    # step 3: expanding rules if bidir rule
    for rule in user_rules_tx:
            if rule['direction'] == '<>' :
                rule['direction'] = '>'
                pos= user_rules_tx.index(rule)
                new_rule= copy.deepcopy(rule)
                # update newly copied rule: swap address/ports & insert
                new_rule['src'], new_rule['dst']= new_rule['dst'], new_rule['src']
                new_rule['src_port_l'], new_rule['dst_port_l']= new_rule['dst_port_l'], new_rule['src_port_l'],
                user_rules_tx.insert(pos+1, new_rule)
    #step 4: if the rules are  unidirectional 
    for rule in user_rules_tx :
        if rule['direction'] == '>' :
           if (rule['src'] != rule ['dst']) :
              uni_rule= copy.deepcopy(rule)
              # update newly copied rule: swap address and insert 'any' to  protocol and src/dst ports
              uni_rule['src'], uni_rule['dst']= uni_rule['dst'], uni_rule['src']
              uni_rule['src_port_l'], uni_rule['dst_port_l']={'max': '65535', 'min': '0'},{'max': '65535', 'min': '0'}
              uni_rule['proto_l']= {'max': '255', 'min': '0'}
              uni_rule['simple_action']= 'deny'
              uni_rule['action_l']=  ['deny']
              break
    return (user_rules_tx,uni_rule)

#end of tx_quantum_rules_to_aces

def trim_duplicate_rules(rules_by_vn) :
    temp_rule=rules_by_vn 
    for i, left in enumerate(temp_rule):
        for j ,right in enumerate(temp_rule):
            if left != right :
               if ((left['src'] == right['src']) and (left['dst'] == right['dst']) and (left['src_port_l'] ==right['src_port_l']) and                                                                 (left['dst_port_l'] ==right['dst_port_l']) and (left['proto_l'] ==right['proto_l'])):
                   temp_rule.pop(j)
               else:  
                   pass
    return temp_rule 
#end of trim_duplicate_rules



def comp_user_rules_to_system_rules(self,vn,rules_by_all_vn,policy,all_vms,vm_list,vm,project_name ):
    # Step 1:Get actual from vna in compute nodes [referred as cn]
    result = True
    cn_vna_rules_by_vn= {}   #{'vn1':[{...}, {..}], 'vn2': [{..}]}
    err_msg= {}       #To capture error {compute: {vn: error_msg}}
    for compNode in self.inputs.compute_ips:
        self.logger.info ("Verify rules expected in CN if VN-VM in CN")
        self.logger.info("CN: %s, Check for expected data" %(compNode))
        inspect_h= self.agent_inspect[compNode]
        got_vm_name=inspect_h.get_vna_tap_interface_by_vm(str(all_vms[vm].id)) 
        if got_vm_name :
           print "checking for vn %s in compute %s" %(vn, compNode)
           vn_fq_name= inspect_h.get_vna_vn(vn_name= vn,project=project_name)['name']
           vna_acl= inspect_h.get_vna_acl_by_vn (vn_fq_name)
           if vna_acl:
              cn_vna_rules_by_vn[vn]= vna_acl['entries']    # system_rules
           else:
              cn_vna_rules_by_vn[vn]= []                
           # compare with test input & assert on failure
           ret= policy_test_utils.compare_rules_list( rules_by_all_vn, cn_vna_rules_by_vn[vn])
           if ret:
              result= ret['state']; msg= ret['msg']
              err_msg[compNode]= {vn: msg}
              self.logger.error("CN: %s, VN: %s, test result not expected, \
              msg: %s" %(compNode, vn, msg))
              self.logger.debug ("expected rules: ")
              for r in  rules_by_all_vn: self.logger.debug (r)
              self.logger.debug ("actual rules from system: ")
              for r in cn_vna_rules_by_vn[vn]: self.logger.debug (r)
              result=False    
           else:
              self.logger.info("CN: %s, VN: %s, result of expected rules check passed" %(compNode, vn))
              self.logger.info("Done the rule verification for vm:%s with attached policy:%s and vn:%s "%(vm_list[vm],policy,vn))
        else:
           pass
    return (result ,err_msg)
#end of comp_user_rules_to_system_rules



  
def tx_quntum_def_aces_to_system(test_vn, user_rules_tx,uni_rule):
    '''convert ACEs derived from user rules to system format:
    1. For every user rule, add deny rule; skip adding duplicates
    2. For non-empty policy, add permit-all at the end
    3. add ace_id, rule_type
    4. Update VN to FQDN format
    5. remove direction and simple_action fields @end..
    '''
    if user_rules_tx == []: return user_rules_tx
    any_proto_port_rule= {'direction': '>','proto_l': {'max': '255', 'min': '0'}, 'src_port_l': {'max': '65535', 'min': '0'}, 
        'dst_port_l': {'max': '65535', 'min': '0'}}

    # step 0: check & build allow_all for local VN if rules are defined in policy
    test_vn_allow_all_rule = copy.copy(any_proto_port_rule)
    test_vn_allow_all_rule['simple_action']= 'pass'
    test_vn_allow_all_rule['action_l']= ['pass']
    test_vn_allow_all_rule['src'], test_vn_allow_all_rule['dst']= test_vn, test_vn
        
    # check the rule for any protocol with same network exist and for deny  rule 
    test_vn_deny_all_rule = copy.copy(any_proto_port_rule)
    test_vn_deny_all_rule['simple_action']= 'deny'
    test_vn_deny_all_rule['action_l']= ['deny']
    test_vn_deny_all_rule['src'], test_vn_deny_all_rule['dst']= test_vn, test_vn

    # step 1: check & add permit-all rule for same  VN  but not for 'any' network 
    last_rule = copy.copy(any_proto_port_rule)
    last_rule['simple_action'], last_rule['action_l']= 'pass', ['pass']
    last_rule['src'], last_rule['dst']= 'any', 'any'
        
    # check any rule exist in policy : 
    final_user_rule=get_any_rule_if_exist(last_rule,user_rules_tx)
       
    # step 2: check & add deny_all for every user-created rule
    system_added_rules= []
    for rule in user_rules_tx:
        pos= len(user_rules_tx)
        new_rule= copy.deepcopy(rule)
        new_rule['proto_l']= {'max': '255', 'min': '0'}; new_rule['direction']= '>'
        new_rule['src_port_l'], new_rule['dst_port_l']= {'max': '65535', 'min': '0'}, {'max': '65535', 'min': '0'}
        new_rule['simple_action']= 'deny'; new_rule['action_l']= ['deny']
        system_added_rules.append(new_rule)

    #step to check any one of the rule is any protocol and source and dst ntw is test vn then check for the duplicate rules
    final_any_rules=get_any_rule_if_src_dst_same_ntw_exist(test_vn_allow_all_rule,test_vn_deny_all_rule,user_rules_tx)
    if final_any_rules :
       user_rules_tx=final_any_rules
    else:
       pass 

    # Skip adding rules if they already exist...
    #print json.dumps(system_added_rules, sort_keys=True)
    if  not policy_test_utils.check_rule_in_rules( test_vn_allow_all_rule, user_rules_tx): user_rules_tx.append(test_vn_allow_all_rule) 
    for rule in system_added_rules:
        if not policy_test_utils.check_rule_in_rules(rule, user_rules_tx): user_rules_tx.append(rule)
        
    # step 3: check & add permit-all rule for same  VN  but not for 'any' network 
    last_rule = copy.copy(any_proto_port_rule)
    last_rule['simple_action'], last_rule['action_l']= 'pass', ['pass']
    last_rule['src'], last_rule['dst']= 'any', 'any'
        
    # if rule is unidirectional then append the deny rule if src and dst is different
    if uni_rule : 
       user_rules_tx.append(uni_rule)
    else: 
       pass

    #if the first rule is not 'any rule ' then append the last rule defined above.
    for rule in user_rules_tx :
        any_rule_flag=True
        if ((rule['src'] == 'any') and (rule['dst'] == 'any')):
           any_rule_flag=False
        else: 
           pass 
    if any_rule_flag :
       user_rules_tx.append(last_rule)
    else:
       pass  
    #triming the duplicate rules 
    user_rules_tx= policy_test_utils.remove_dup_rules(user_rules_tx) 
    # triming the protocol with any option for rest of the fileds 
    tcp_any_rule= {'proto_l':{'max': 'tcp', 'min': 'tcp'},'src': 'any', 'dst': 'any', 'src_port_l': {'max': '65535', 'min': '0'}, 'dst_port_l': {'max': '65535', 'min': '0'}}
    udp_any_rule= {'proto_l':{'max': 'udp', 'min': 'udp'},'src': 'any', 'dst': 'any', 'src_port_l': {'max': '65535', 'min': '0'}, 'dst_port_l': {'max': '65535', 'min': '0'}}
    icmp_any_rule= {'proto_l':{'max':'icmp','min': 'icmp'},'src': 'any', 'dst': 'any', 'src_port_l':{'max': '65535', 'min': '0'}, 'dst_port_l': {'max': '65535', 'min': '0'}}
    icmp_match ,index_icmp =check_5tuple_in_rules(icmp_any_rule,user_rules_tx)
    tcp_match ,index_tcp =check_5tuple_in_rules(tcp_any_rule,user_rules_tx)
    udp_match ,index_udp =check_5tuple_in_rules(udp_any_rule,user_rules_tx)
    if icmp_match :
       for rule in user_rules_tx[index_icmp+1:len( user_rules_tx)] :
           if rule['proto_l'] == {'max': 'icmp', 'min': 'icmp'} :
              user_rules_tx.remove(rule)  
           else: 
              pass
    if tcp_match :
       for rule in user_rules_tx[index_tcp+1:len( user_rules_tx)]:
           if rule['proto_l'] == {'max': 'tcp', 'min': 'tcp'} :
              user_rules_tx.remove(rule)  
           else: 
              pass
    if udp_match :
       for rule in user_rules_tx[index_udp+1:len( user_rules_tx)]:
           if rule['proto_l'] == {'max': 'udp', 'min': 'udp'} :
              user_rules_tx.remove(rule)  
           else: 
              pass
    # if any rule is exist the it will execute 
    if final_user_rule :
       user_rules_tx=final_user_rule
    else:
       pass
    # step 4: add ace_id, type, src to all rules
    for rule in user_rules_tx :
        rule['ace_id'] = str(user_rules_tx.index(rule) + 1)
        rule['rule_type']= 'Terminal' #currently checking policy aces only
        #if rule['src'] != 'any' :
        #    m = re.match(r"(\S+):(\S+):(\S+)", rule['src'])
        #    if not m: rule['src'] = ':'.join(self.inputs.project_fq_name) + ':' + rule['src']
        #if rule['dst'] != 'any':
        #    m = re.match(r"(\S+):(\S+):(\S+)", rule['dst'])
        #    if not m: rule['dst'] = ':'.join(self.inputs.project_fq_name) + ':' + rule['dst']
        try: del rule['direction']
        except: continue
        try: del rule['simple_action']
        except: continue

    return user_rules_tx

#end tx_user_def_aces_to_system
    
def get_any_rule_if_exist(all_rule,user_rules_tx):
    final_rules=[]
    if policy_test_utils.check_rule_in_rules(all_rule, user_rules_tx):
       for rule in user_rules_tx :
           if rule == all_rule:
              final_rules.append(rule)
              break  
           else:
              final_rules.append(rule)
    else: 
       pass
    return final_rules    
#end get_any_rule_if_exist

def get_any_rule_if_src_dst_same_ntw_exist(test_vn_allow_all_rule,test_vn_deny_all_rule,user_rules_tx):
    final_any_rules=[]
    if (policy_test_utils.check_rule_in_rules(test_vn_allow_all_rule, user_rules_tx) or policy_test_utils.check_rule_in_rules(test_vn_deny_all_rule, user_rules_tx)):
       for rule in user_rules_tx :
           if ((rule == test_vn_allow_all_rule) or (rule == test_vn_deny_all_rule)):
              final_any_rules.append(rule)
              break  
           else:
              final_any_rules.append(rule)
    else: 
        pass
    return final_any_rules
#end get_any_rule_if_src_dst_same_ntw_exist    

def check_5tuple_in_rules(rule, rules):
    '''check if 5-tuple of given rule exists in given rule-set..Return True if rule exists; else False'''
    #print ("check rule %s in rules" %(json.dumps(rule, sort_keys=True)))
    match_keys = ['proto_l','src', 'dst', 'src_port_l', 'dst_port_l']
    for r in rules :
        match= True
        for k in match_keys:
            if r[k] != rule[k]:
               match= False; break; #print ("current rule not matching due to key %s, move on.." %k)
        if match == True: break
    return (match, rules.index(r))
#end check_5tuple_in_rules

