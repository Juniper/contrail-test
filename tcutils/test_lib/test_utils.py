# Add common test utils, which can be used by all test scripts..
from netaddr import IPNetwork

def assertEqual(a, b, error_msg):
    '''Assert with error msg'''
    assert (a == b), error_msg

def get_ip_list_from_prefix(prefix):

    return map(str, IPNetwork(prefix).iter_hosts())

def get_min_max_ip_from_prefix(prefix):

    ip_list = get_ip_list_from_prefix(prefix)
    min_ip = ip_list[0]
    max_ip = ip_list[-1]
    return [min_ip, max_ip]

