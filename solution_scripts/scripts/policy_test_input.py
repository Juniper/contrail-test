''' 
Generate Policy test scenarios based on user input.
Policy test cases can be built based on this topology.
'''
import copy
from random import choice


class PolicyTestBasicConfig_1():

    def __init__(self):
        self.vmc_list = []
        self.vnet_list = []
        self.policy_list = []
        self.vn_subnets = {}
        self.vn_policy = {}
        self.vn_of_cn = {}
        self.vm_of_cn = {}
        self.vn_of_vm = {}
        begin_oct = 10
        base_net = '.1.1.0/24'
        numEntity = 1
        numRules = 4
        # For a given no., generate n policies, VN & VM's, attach policies to VN's
        # & launch VM instances in the VN's.
        for type in ['policy', 'vnet', 'vmc']:
            for i in range(numEntity):
                net = str(begin_oct) + base_net
                name = type + str(i)
                policy_list_name = 'policy_list_' + name
                vnet_list_name = 'vnet_list_' + name
                policy_list_name = []
                vnet_list_name = []
                if type == 'policy':
                    self.policy_list.append(name)
                elif type == 'vnet':
                    self.vnet_list.append(name)
                    vnet_list_name.append(net)
                    self.vn_subnets[name] = vnet_list_name
                    begin_oct += 1
                    policy_list_name.append(self.policy_list[i])
                    self.vn_policy[name] = policy_list_name
                elif type == 'vmc':
                    self.vmc_list.append(name)
                    self.vn_of_vm[name] = self.vnet_list[i]
        print self.policy_list, self.vmc_list, self.vnet_list, self.vn_subnets, \
            self.vn_policy, self.vn_of_vm
        # Generate m different rules for each policy
        self.rules = {}
        for j in range(len(self.policy_list)):
            proto_opts = [6, 17, 1, 'any']
            proto = choice(proto_opts)
            self.rules['policy' + str(j)] = []
            for i in range(numRules):
                rule_base = {'direction': '>', 'protocol': proto,
                             'source_network': self.vnet_list[j],
                             'src_ports': [i, i], 'dest_network': self.vnet_list[j],
                             'dst_ports': 'any', 'simple_action': 'deny'}
                self.rules['policy' + str(j)].append(rule_base)
        # There can be multple policies for a VN, build the list of policies by
        # VN
        self.policy_vn = {}
        for policy in self.policy_list:
            self.policy_vn[policy] = []
            for vn in self.vnet_list:
                if policy in self.vn_policy[vn]:
                    self.policy_vn[policy].append(vn)
                    # print "added vn %s to list for policy %s" %(vn, policy)
                # print "completed parsing vn %s policy list" %(vn)
            # print "completed building vn list for policy %s, list is %s" %(policy, self.policy_vn[policy])
        # end __init__
# end class

if __name__ == '__main__':
    PolicyTestBasicConfig_1()
