''' 
Generate test topology based on user input.
SDN test cases can be built based on this topology.
'''
import sys
import copy
from random import choice

class basic_topo():
    def __init__(self):
        #set domain, project to defaults
        self.domain= 'default-domain'; self.project= 'admin'
        self.vmc_list= []; self.vnet_list= []
        self.policy_list= []; self.net_list= []
        self.vn_nets= {}; self.vn_of_cn= {}
        self.vm_of_cn= {}; self.vn_of_vm= {}
        self.vn_policy= {}; self.policy_vn= {}
        # seed for topology - user can enter as needed:
        begin_oct= 10; base_net= '.1.1.0/30'
        numPolicyPerVN= 2; numRules= 4
        numVM= 2; numNetsPerVn= 2
        numVNsPerVM= 1 # for now, leave it to 1, infra support needed for >1
        numVN= numVM * numVNsPerVM
        numNets= numVN * numNetsPerVn 
        numPolicies= numVN * numPolicyPerVN
        # end topology seed section

        # Generate policy names based on user data
        type= 'policy'
        for i in range (numPolicies):
            name= type + str(i)
            self.policy_list.append(name)

        # Generate networks based on user data
        for i in range (numNets):
            net=str(begin_oct) + base_net
            begin_oct += 1
            self.net_list.append(net)

        # Generate VN names based on user data
        type= 'vnet'
        for i in range (numVN):
            name= type + str(i)
            self.vnet_list.append(name)

        # Generate VM names based on user data
        type= 'vmc'
        for i in range (numVM):
            name= type + str(i)
            self.vmc_list.append(name)

        # associate nets to VN
        dup_net_list= copy.copy(self.net_list)
        for vn in self.vnet_list:
            self.vn_nets[vn]= []
            for j in range (numNetsPerVn):
                net= dup_net_list.pop(0)
                self.vn_nets[vn].append(net)

        # associate VN's to VM
        dup_vnet_list= copy.copy(self.vnet_list)
        for vm in self.vmc_list:
            self.vn_of_vm[vm]= []
            for j in range (numVNsPerVM):
                vn= dup_vnet_list.pop(0)
                self.vn_of_vm[vm].append(vn)
            # for now return a single element until infra support is added to handle list
            self.vn_of_vm[vm]= self.vn_of_vm[vm][0]

        # associate policies to VN
        dup_policy_list= copy.copy(self.policy_list)
        for vn in self.vnet_list:
            self.vn_policy[vn]= []
            for j in range (numPolicyPerVN):
                policy_mem= dup_policy_list.pop(0)
                self.vn_policy[vn].append(policy_mem)

        # There can be multple VNs associated to same policy, build the list of VNs by policy
        self.policy_vn= {}
        for policy in self.policy_list:
            self.policy_vn[policy]= []
            for vn in self.vnet_list:
                if policy in self.vn_policy[vn]: self.policy_vn[policy].append(vn)
        # end of vn and policy for loops

        # Generate m different rules for each policy
        self.rules= {}
        for i in range (len(self.policy_list)):
            #proto_opts= [6, 17, 1, 'any']
            proto_opts= ['6', '17', '1']
            proto= choice(proto_opts)
            policy= 'policy' + str(i)
            self.rules[policy]= []
            policy_vn= self.policy_vn[policy]
            for j in range (numRules):
                rule_base= {'direction': '>', 'protocol': proto, 
                    'source_network': policy_vn[0],
                    'src_ports': [j, j], 'dest_network': policy_vn[0], 
                    'dst_ports': 'any', 'simple_action': 'deny'}
                self.rules['policy' + str(i)].append(rule_base)
           
        # end __init__

    def print_topology(self, topology_name):
        print "'''*******AUTO-GENERATED TOPOLOGY*********'''"
        print "class %s ():" %(topology_name)
        print "\tdef __init__(self, domain= 'default-domain', project= 'admin'):"
        print "\t\t##"
        print "\t\t# Domain and project defaults: Do not change until support for non-default is tested!"
        print "\t\tself.domain= domain; self.project= project"
        print "\t\t##"
        print "\t\t# Define VN's in the project:"
        print "\t\tself.vnet_list= ", self.vnet_list
        print "\t\t##"
        print "\t\t# Define network info for each VN:"
        print "\t\tself.vn_nets= ", self.vn_nets
        print "\t\t##"
        print "\t\t# Define network policies"
        print "\t\tself.policy_list= ", self.policy_list
        print "\t\tself.vn_policy= ", self.vn_policy
        print "\t\t##"
        print "\t\t# Define VM's"
        print "\t\t# VM distribution on available compute nodes is handled by nova scheduler or contrail vm naming scheme"
        print "\t\tself.vn_of_vm= ", self.vn_of_vm
        print "\t\t##"
        print "\t\t# Define network policy rules"
        print "\t\tself.rules= {}"
        for policy in self.policy_list:
            print "\n\t\tself.rules[\'%s\']= %s" %(policy, self.rules[policy])
        # end for
        print "\t\t# end __init__"
        print 
        print "if __name__ == '__main__':"
        print "\tprint \"Currently topology limited to one domain/project..\""
        print "\tprint \"Based on need, can be extended to cover config for multiple domain/projects\""
        print "\tprint"
        print "\tmy_topo= basic_topo(domain= 'default-domain', project= 'admin')"
        print "\tx= my_topo.__dict__"
        print "\t#print \"keys only:\""
        print "\t#for key, value in x.iteritems(): print key"
        print "\t#print"
        print "\t#print \"keys & values:\""
        print "\t#for key, value in x.iteritems(): print key, \"-->\", value"
        print "\timport topo_helper"
        print "\ttopo_h= topo_helper.topology_helper(my_topo)"
        print "\t#vmc_list= topo_h.get_vmc_list()"
        print "\tpolicy_vn= topo_h.get_policy_vn()"
        print "#" * 80
            
# end class    

if __name__ == '__main__':
    p= basic_topo()
    # Run main with print option to display generated topology, redirect to a file, say topo.py, to capture topology
    if len(sys.argv) > 1 and sys.argv[1] == 'print': 
        p.print_topology('basic_topo')
    else:    
        print "\nUsage: <%s print> to display generated topology" %(sys.argv[0])
        print "\nprinting created topology attribs: \n"
        print p.policy_list, p.vmc_list, p.vnet_list, p.vn_nets, p.vn_policy, p.vn_of_vm

# end __main__        
