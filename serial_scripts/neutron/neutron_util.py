import string
import random
import itertools
import uuid
from netaddr import IPAddress, IPNetwork
from tcutils.util import get_random_ip, get_random_cidr


def get_pool_dict_list(cidr, max_length=4):
    # Assuming a /24 subnet in cidr
    final_list = []
    cidr_object = IPNetwork(cidr)
    subnets_list = list(cidr_object.subnet(29))
    random.shuffle(subnets_list)
    list_length = random.randint(1, max_length)

    for i in range(0, list_length):
        subnet = subnets_list[i]
        pool_dict = {'start': str(subnet[0]), 'end': str(subnet[-1])}
        final_list.append(pool_dict)
    return final_list


def get_route_dict_list(cidr, max_length=4):
    list_length = random.randint(1, max_length)
    final_list = []

    for i in range(0, list_length):
        route_dict = {'destination': get_random_cidr(),
                      'nexthop': str(get_random_ip(cidr))}
        final_list.append(route_dict)
    return final_list


def get_fixed_ip_dict_list(subnet_id, cidr, max_length=1):
    # Need to test separately for a list of fixed ips
    list_length = random.randint(1, max_length)
    final_list = []
    for i in range(0, list_length):
        fixed_ip_dict = {}
        random_ip = get_random_ip(cidr)
        if subnet_id is not None:
            fixed_ip_dict['subnet_id'] = subnet_id
        fixed_ip_dict['ip_address'] = random_ip
        final_list.append(fixed_ip_dict)
    return final_list


def get_random_ip_list(max_list_length=4):
    list_length = random.randint(1, max_list_length)
    final_list = []
    for i in range(0, list_length):
        cidr = get_random_cidr()
        random_ip = get_random_ip(cidr)
        final_list.append(random_ip)
    return final_list


def combos(list_obj):
    all_combos = []
    for i in range(1, len(list_obj)):
        all_combos += itertools.combinations(list_obj, i)
    for j in all_combos:
        yield j
