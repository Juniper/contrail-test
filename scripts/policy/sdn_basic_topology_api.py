'''*******AUTO-GENERATED TOPOLOGY*********'''
from vnc_api.vnc_api import *


class sdn_basic_config_api ():

    def __init__(self, domain='default-domain', project='admin', username=None, password=None):
        #
        # Domain and project defaults: Do not change until support for
        # non-default is tested!
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = ['vnet0', 'vnet1', 'vnet2', 'vnet3', 'vnet4']
        #
        # Define network info for each VN:
        self.vn_nets = {
            'vnet0': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(subnet=SubnetType('10.1.1.0', 24)), IpamSubnetType(subnet=SubnetType('11.1.1.0', 24))]))],
            'vnet1': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(subnet=SubnetType('12.1.1.0', 24)), IpamSubnetType(subnet=SubnetType('13.1.1.0', 24))]))],
            'vnet2': [],
            'vnet3': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(subnet=SubnetType('14.1.1.0', 24))]))],
            'vnet4': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(subnet=SubnetType('15.1.1.0', 24))]))]
        }

        #
        # Define network policies
        self.policy_list = ['policy0', 'policy1', 'policy2', 'policy3']
        # commenting out multiple policy associated to single vn untill PR 1181 is fixed
        #self.vn_policy=  {'vnet0': ['policy0'], 'vnet1': ['policy1'], 'vnet2': [], 'vnet3': ['policy2'], 'vnet4': ['policy0', 'policy1', 'policy2', 'policy3']}
        self.vn_policy = {'vnet0': ['policy0'], 'vnet1': ['policy1'],
                          'vnet2': [], 'vnet3': ['policy2'], 'vnet4': ['policy3']}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'vmc0': 'vnet0', 'vmc1': 'vnet1'}
        #
        # Define network policy rules
        self.rules = {}

        self.rules['policy0'] = [
            PolicyRuleType(direction='>', protocol='icmp', dst_addresses=[AddressType(virtual_network='any')], src_addresses=[AddressType(
                virtual_network='local')], dst_ports=[PortType(80, 80)], action_list=ActionListType(simple_action='deny'), src_ports=[PortType(-1, -1)]),
            PolicyRuleType(direction='>', protocol='tcp', dst_addresses=[AddressType(virtual_network='any')], src_addresses=[AddressType(
                virtual_network='local')], dst_ports=[PortType(80, 80)], action_list=ActionListType(simple_action='deny'), src_ports=[PortType(-1, -1)])
        ]

        self.rules['policy1'] = [
            PolicyRuleType(direction='>', protocol='icmp', dst_addresses=[AddressType(virtual_network='any')], src_addresses=[AddressType(
                virtual_network='local')], dst_ports=[PortType(80, 80)], action_list=ActionListType(simple_action='pass'), src_ports=[PortType(-1, -1)]),
            PolicyRuleType(direction='>', protocol='tcp', dst_addresses=[AddressType(virtual_network='any')], src_addresses=[AddressType(
                virtual_network='local')], dst_ports=[PortType(80, 80)], action_list=ActionListType(simple_action='pass'), src_ports=[PortType(-1, -1)])
        ]

        self.rules['policy2'] = []

        self.rules['policy3'] = [
            PolicyRuleType(direction='<>', protocol='udp', dst_addresses=[AddressType(virtual_network='any')], src_addresses=[AddressType(
                virtual_network='local')], dst_ports=[PortType(80, 80)], action_list=ActionListType(simple_action='pass'), src_ports=[PortType(-1, -1)]),
            PolicyRuleType(direction='>', protocol='any', dst_addresses=[AddressType(virtual_network='any')], src_addresses=[AddressType(
                virtual_network='local')], dst_ports=[PortType(80, 80)], action_list=ActionListType(simple_action='pass'), src_ports=[PortType(80, 100)])
        ]
        # end __init__


class sdn_multiple_vn_single_policy_config_api ():

    def __init__(self, domain='default-domain', project='admin', username=None, password=None):
        #
        # Domain and project defaults: Do not change until support for
        # non-default is tested!
        self.domain = domain
        self.project = project
        self.username = username
        self.password = password
        #
        # Define VN's in the project:
        self.vnet_list = ['vnet0', 'vnet1', 'vnet2', 'vnet3', 'vnet4']
        #
        # Define network info for each VN:
        self.vn_nets = {
            'vnet0': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(subnet=SubnetType('10.1.1.0', 24))]))],
            'vnet1': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(subnet=SubnetType('11.1.1.0', 24))]))],
            'vnet2': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(subnet=SubnetType('12.1.1.0', 24))]))],
            'vnet3': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(subnet=SubnetType('13.1.1.0', 24))]))],
            'vnet4': [(NetworkIpam(), VnSubnetsType([IpamSubnetType(subnet=SubnetType('14.1.1.0', 24))]))],
        }
        #
        # Define network policies
        self.policy_list = ['policy0']
        self.vn_policy = {'vnet0': ['policy0'], 'vnet1': ['policy0'], 'vnet2': [
            'policy0'], 'vnet3': ['policy0'], 'vnet4': ['policy0']}
        #
        # Define VM's
        # VM distribution on available compute nodes is handled by nova
        # scheduler or contrail vm naming scheme
        self.vn_of_vm = {'vmc0': 'vnet0', 'vmc1': 'vnet1',
                         'vmc2': 'vnet2', 'vmc3': 'vnet3', 'vmc4': 'vnet4'}
        #
        # Define network policy rules
        self.rules = {}
        self.rules['policy0'] = [
            PolicyRuleType(direction='<>', protocol='icmp', dst_addresses=[AddressType(virtual_network='any')], src_addresses=[AddressType(
                virtual_network='local')], dst_ports=[PortType(-1, -1)], action_list=ActionListType(simple_action='pass'), src_ports=[PortType(-1, -1)]),
        ]

        # end __init__

if __name__ == '__main__':
    print "Currently topology limited to one domain/project.."
    print "Based on need, can be extended to cover config for multiple domain/projects"
    print "Running unit test for this module ..."
    my_topo = sdn_basic_config_api(domain='default-domain', project='admin')
    x = my_topo.__dict__
    print "\nprinting keys of topology dict:"
    for key, value in x.iteritems():
        print key
    print
    # print "keys & values:"
    # for key, value in x.iteritems(): print key, "-->", value
    # Use topology_helper to extend/derive data from user-defined topology to help verifications.
    # ex. get list of all vm's from topology; get list of vn's associated to a
    # policy
    import topo_helper
    topo_h = topo_helper.topology_helper(my_topo)
    #vmc_list= topo_h.get_vmc_list()
    policy_vn = topo_h.get_policy_vn()
    print "printing derived topo data - vn's associated to a policy: \n", policy_vn
#
