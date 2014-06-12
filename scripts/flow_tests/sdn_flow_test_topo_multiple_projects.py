class multi_project_topo ():
    def __init__(self, domain= 'default-domain', compute_node_list= None):
        print "building dynamic topo"
        self.project_list= ['project1', 'project2']

        #Define the vm to compute node mapping to pin a vm to a particular
        #compute node or else leave empty.
        self.vm_node_map = {'vmc1':'CN0', 'vmc2':'CN1', 'vmc3':'CN0', 'vmc4':'CN1'}

        #Logic to create a vm to Compute node mapping.
        if self.vm_node_map:
            CN = []
            for cn in self.vm_node_map.keys():
                if self.vm_node_map[cn] not in CN:
                    CN.append(self.vm_node_map[cn])
            my_node_dict = {}
            if compute_node_list is not None:
                if len(compute_node_list) >= len(CN):
                    my_node_dict = dict(zip(CN, compute_node_list))
        
            if my_node_dict:
                for key in my_node_dict:
                    for key1 in self.vm_node_map:
                        if self.vm_node_map[key1] == key:
                            self.vm_node_map[key1] = my_node_dict[key]

        ##
        # Define traffic profile.
        # PROJ1--VN1[vmc1]--FIP-NAT--PROJ2-->VN4[vmc4]
        # PROJ1--VN1[vmc1]--FIP-NAT--PROJ1-->VN2[vmc2]
        self.traffic_profile= {'TrafficProfile1':{'src_vm':'vmc1', 'dst_vm':'vmc4', 'num_flows':300000, 'num_pkts':2000000},
                               'TrafficProfile2':{'src_vm':'vmc1', 'dst_vm':'vmc2', 'num_flows':300000, 'num_pkts':2000000},
                                }
        ##
        # A master list of all the vm static routes defined.
        self.vm_static_route_master={'vmc1':'111.1.1.0/28', 'vmc2':'111.2.1.0/28', 'vmc3':'111.3.1.0/28', 'vmc4':'111.4.1.0/28', 'vmc7':'111.7.1.0/28'} 
        self.vm_static_route_test={} 

        ##
        # Define FIP pool
        self.fip_pools= {'project1': {'p1-vn1-pool1': {'host_vn': 'vnet1', 'target_projects': ['project1', 'project2']}}, 
                        'project2': {'p2-vn3-pool2': {'host_vn': 'vnet3', 'target_projects': ['project2']}}
                        }
        self.fvn_vm_map = {'project1': {'vnet1':{'project1': ['vmc2'], 'project2': ['vmc4']}},
                            'project2': {'vnet3':{'project2': ['vmc4']}},
                            }
        # self.fvn_vm_map = {'vnet3':['vmc6', 'vmc8'], 'vnet4':['vmc5'], 'vnet5':['vmc5']}
    # end __init__

    def build_topo_project1 (self, domain= 'default-domain', project= 'project1', username= 'juniper', password= 'juniper123'):
        ##
        # Topo for project: project1
        # Define Domain and project 
        self.domain= domain; self.project= project; self.username= username; self.password= password
        ##
        # Define VN's in the project:
        self.vnet_list= ['vnet1', 'vnet2']
        ##
        # Define network info for each VN:
        self.vn_nets= {'vnet1': ['10.1.1.0/30', '10.1.1.4/30', '10.1.1.8/30'], 'vnet2': ['10.2.1.0/30', '10.2.1.4/30']}
        ##
        # Define netowrk IPAM for each VN, if not defined default-user-created ipam will be created and used
        self.vn_ipams= {'vnet1': 'ipam1', 'vnet2': 'ipam2'}
        ##
        # Define network policies
        self.policy_list= ['policy1', 'policy2']
        self.vn_policy= {'vnet1': ['policy1', 'policy2'], 'vnet2': ['policy1']}
        ##
        # Define VM's
        # VM distribution on available compute nodes is handled by nova scheduler or contrail vm naming scheme
        # vm name to be unique across projects for now.. 
        self.vn_of_vm= {'vmc1': 'vnet1', 'vmc2': 'vnet2'}
        ##
        # Define static route behind vms.
        self.vm_static_route= {'vmc1':'111.1.1.0/28', 'vmc2':'111.2.1.0/28'}
        self.vm_static_route_test.update(self.vm_static_route)

        ##
        # Define network policy rules
        self.rules= {}
        self.rules['policy1']= [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'default-domain:project2:vnet3', 'source_network': 'default-domain:project1:vnet1', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'default-domain:project1:vnet2', 'source_network': 'default-domain:project1:vnet1', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]
        self.rules['policy2']= [
            {'direction': '<>', 'protocol': 'udp', 'dest_network': 'default-domain:project1:vnet1', 'source_network': 'default-domain:project1:vnet2', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'}]

        ## Define security_group name
        self.sg_list=['test_sg_p1']
        ##
        #Define security_group with vm
        # vmc1: test_sg_p1, vmc2: default
        self.sg_of_vm= {'vmc1': 'test_sg_p1', 'vmc2': 'test_sg_p1'}
        #Define the security_group rules
        import uuid
        uuid_1= uuid.uuid1().urn.split(':')[2]
        uuid_2= uuid.uuid1().urn.split(':')[2]
        uuid_3= uuid.uuid1().urn.split(':')[2]
        self.sg_rules={}
        self.sg_rules['test_sg_p1']=[
               {'direction' : '>',
                 'protocol' : 'any', 'rule_uuid': uuid_1,
                 'dst_addresses': [{'security_group': 'local'}],
                 'dst_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'src_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'src_addresses': [{'subnet' : {'ip_prefix' : '0.0.0.0', 'ip_prefix_len' : 0}}],
               },{'direction' : '>',
                 'protocol' : 'any', 'rule_uuid': uuid_2,
                 'src_addresses': [{'security_group': 'local'}],
                 'dst_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'src_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'dst_addresses': [{'subnet' : {'ip_prefix' : '0.0.0.0', 'ip_prefix_len' : 0}}],
               },{'direction' : '>',
                 'protocol' : 'any', 'rule_uuid': uuid_3,
                 'src_addresses': [{'security_group': 'default-domain:project1:test_sg_p1'}],
                 'dst_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'src_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'dst_addresses': [{'security_group': 'local'}]}]

        return self
    #end build_topo_project1

    def build_topo_project2 (self, domain= 'default-domain', project= 'project2', username= 'tiger', password= 'juniper123'):
        ##
        # Topo for project: project2
        # Define Domain and project 
        self.domain= domain; self.project= project; self.username= username; self.password= password
        ##
        # Define VN's in the project:
        self.vnet_list= ['vnet3', 'vnet4']
        ##
        # Define network info for each VN:
        self.vn_nets= {'vnet4': ['10.1.1.0/30', '10.1.1.4/30', '10.1.1.8/30'], 'vnet3': ['20.2.1.0/30', '20.2.1.4/30']}
        ##
        # Define netowrk IPAM for each VN, if not defined default-user-created ipam will be created and used
        self.vn_ipams= {'vnet3': 'ipam3', 'vnet4': 'ipam4'}
        ##
        # Define network policies
        self.policy_list= ['policy3']
        self.vn_policy= {'vnet3': ['policy3'], 'vnet4': []}
        ##
        # Define VM's
        # VM distribution on available compute nodes is handled by nova scheduler or contrail vm naming scheme
        # vm name to be unique across projects for now.. 
        self.vn_of_vm= {'vmc3': 'vnet3', 'vmc4': 'vnet4'}
        ##
        # Define static route behind vms.
        self.vm_static_route= {'vmc3':'111.3.1.0/28', 'vmc4':'111.4.1.0/28'}
        self.vm_static_route_test.update(self.vm_static_route)

        ##
        # Define network policy rules
        self.rules= {}
        self.rules['policy3']= [
            {'direction': '<>', 'protocol': 'udp', 'source_network': 'default-domain:project2:vnet3', 'dest_network': 'default-domain:project1:vnet1', 'dst_ports': 'any', 'simple_action': 'pass', 'src_ports': 'any'},
            ]

        ## Define security_group name
        self.sg_list=['test_sg_p2']
        ##
        #Define security_group with vm
        # vmc4: test_sg_p2, vmc3: default
        self.sg_of_vm= {'vmc3': 'test_sg_p2', 'vmc4': 'test_sg_p2'}
        #Define the security_group rules
        import uuid
        uuid_1= uuid.uuid1().urn.split(':')[2]
        uuid_2= uuid.uuid1().urn.split(':')[2]
        uuid_3= uuid.uuid1().urn.split(':')[2]
        self.sg_rules={}
        self.sg_rules['test_sg_p2']=[
               {'direction' : '>',
                 'protocol' : 'any', 'rule_uuid': uuid_1,
                 'dst_addresses': [{'security_group': 'local'}],
                 'dst_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'src_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'src_addresses': [{'subnet' : {'ip_prefix' : '0.0.0.0', 'ip_prefix_len' : 0}}],
               },{'direction' : '>',
                 'protocol' : 'any', 'rule_uuid': uuid_2,
                 'src_addresses': [{'security_group': 'local'}],
                 'dst_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'src_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'dst_addresses': [{'subnet' : {'ip_prefix' : '0.0.0.0', 'ip_prefix_len' : 0}}],
               },{'direction' : '>',
                 'protocol' : 'any', 'rule_uuid': uuid_3,
                 'src_addresses': [{'security_group': 'default-domain:project1:test_sg_p2'}],
                 'dst_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'src_ports': [{'start_port' : 0, 'end_port' : 65535}],
                 'dst_addresses': [{'security_group': 'local'}]}]

        return self
    #end build_topo_project2

#end sdn_flow_test_topo_multi_project
 
if __name__ == '__main__':
    print "Currently topology limited to one domain/project.."
    print "Based on need, can be extended to cover config for multiple domain/projects"
    print "Running unit test for this module ..."
    my_topo= sdn_basic_policy_topo_with_3_project(domain= 'default-domain')
    x= my_topo.__dict__
    print "\nprinting keys of topology dict:"
    for key, value in x.iteritems(): print key
    print
    #print "keys & values:"
    #for key, value in x.iteritems(): print key, "-->", value
    # Use topology_helper to extend/derive data from user-defined topology to help verifications.
    # ex. get list of all vm's from topology; get list of vn's associated to a policy
    import topo_helper
    topo_h= topo_helper.topology_helper(my_topo)
    #vmc_list= topo_h.get_vmc_list()
    policy_vn= topo_h.get_policy_vn()
    print "printing derived topo data - vn's associated to a policy: \n", policy_vn
################################################################################
