class sdn_single_vm_policy_config ():
    def __init__(self, domain= 'default-domain', project= 'admin', username= None, password= None):
        ##
        # Domain and project defaults: Do not change until support for non-default is tested!
        self.domain= domain; self.project= project; self.username= username; self.password= password
        ##
        # Define VN's in the project:
        self.vnet_list=  ['vnet0']
        ##
        # Define network info for each VN:
        self.vn_nets=  {'vnet0': ['10.1.1.0/30']}
        ##
        # Define network policies
        self.policy_list=  ['policy0', 'policy1', 'policy2']
        self.vn_policy=  {'vnet0': ['policy0', 'policy1']}
        ##
        # Define VM's
        # VM distribution on available compute nodes is handled by nova scheduler or contrail vm naming scheme
        self.vn_of_vm=  {'vmc0': 'vnet0'}
        ##
        # Define network policy rules
        self.rules= {}

        self.rules['policy0']= [{'direction': '>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [0, 0]}, {'direction': '>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [1, 1]}, {'direction': '>', 'protocol': 'tcp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [2, 2]}]

        self.rules['policy1']= [{'direction': '>', 'protocol': 'icmp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'}, {'direction': '>', 'protocol': 'icmp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'}, {'direction': '>', 'protocol': 'icmp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': 'any'}]

        self.rules['policy2']= [{'direction': '>', 'protocol': 'udp', 'dest_network': 'vnet0', 'source_network': 'vnet0', 'dst_ports': 'any', 'simple_action': 'deny', 'src_ports': [10, 10]}] 
        # end __init__
# end class
