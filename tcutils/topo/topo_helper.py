''' Take logical topology object and provide methods to extend/derive data from user topology to help verifications '''


class topology_helper ():

    def __init__(self, topology_obj):
        self.topo_dict = topology_obj.__dict__
        self.vnet_list = self.topo_dict['vnet_list']
        self.vn_policy = self.topo_dict['vn_policy']
        self.policy_list = self.topo_dict['policy_list']
        self.rules = self.topo_dict['rules']
        if 'si_list' in self.topo_dict:
            self.si_list = self.topo_dict['si_list']
        else:
            self.si_list = []
        self.vmc_list = []
        self.policy_vn = {}
        self.pol_si = {}
        self.si_pol = {}


    def get_vmc_list(self):
        vn_vm_l = self.topo_dict['vn_of_vm']
        for key, value in vn_vm_l.iteritems():
            self.vmc_list.append(key)
        return self.vmc_list

    def get_policy_vn(self):
        for policy in self.policy_list:
            self.policy_vn[policy] = []
            for vn in self.vnet_list:
                if policy in self.vn_policy[vn]:
                    self.policy_vn[policy].append(vn)
                    # print "added vn %s to list for policy %s" %(vn, policy)
                # print "completed parsing vn %s policy list" %(vn)
            # print "completed building vn list for policy %s, list is %s"
            # %(policy, self.policy_vn[policy])
        return self.policy_vn

    def get_vm_of_vn(self):
        '''return vm list by vn; data of format {vn1: [vmc1, vmc2], vn2: [vmc3, vmc4]}'''
        self.vm_of_vn = {}
        # self.vn_of_vm=  {'vmc0': 'vnet0', 'vmc1': 'vnet1'} format...
        vn_vm_l = self.topo_dict['vn_of_vm']
        for vn in self.vnet_list:
            self.vm_of_vn[vn] = []
        for k, v in vn_vm_l.items():
            self.vm_of_vn[v].append(k)
        return self.vm_of_vn
# end
