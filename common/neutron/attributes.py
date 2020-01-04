from common.neutron.neutron_util import *
from tcutils.util import *
import string

network = {
    'id': {
        'perm': 'r',
        'default': 'generated',
        'type': 'uuid-str',
        'required': 'false',
    },
    'name': {
        'perm': 'cru',
        'default': 'none',
        'type': 'string',
        'required': 'false',
    },
    'admin_state_up': {
        'perm': 'cru',
        'default': 'none',
        'type': 'boolean',
        'required': 'false',
    },
    'status': {
        'perm': 'r',
        'default': 'none',
        'type': 'string',
        'required': 'false',
    },
    'subnets': {
        'perm': 'r',
        'default': 'empty list',
        'type': 'list(uuid-str)',
        'required': 'false',
    },
    'shared': {
        'perm': 'cru',
        'default': 'false',
        'type': 'boolean',
        'required': 'false',
    },
    'tenant_id': {
        'perm': 'cr',
        'default': 'none',
        'type': 'uuid-str',
        'required': 'false',
    },
    'router:external': {
        'perm': 'cru',
        'default': 'false',
        'type': 'boolean',
        'required': 'false',
    },
}

subnet = {
    'id': {
        'perm': 'r',
        'default': 'generated',
        'type': 'uuid-str',
        'required': 'false',
    },
    'name': {
        'perm': 'cru',
        'default': 'none',
        'type': 'string',
        'required': 'false',
    },
    'network_id': {
        'perm': 'cr',
        'default': 'none',
        'type': 'uuid-str',
        'required': 'true',
    },
    'ip_version': {
        'perm': 'cr',
        'default': '4',
        'type': 'int-46',
        'required': 'true',
    },
    'cidr': {
        'perm': 'cr',
        'default': 'none',
        'type': 'cidr-string',
        'required': 'true',
    },
    'gateway_ip': {
        #'perm':'crud',
        'perm': 'cr',  # gateway update and delete are not supported
        'default': 'none',
        'type': 'gw-ip',
        'required': 'false',
    },
    'dns_nameservers': {
        'perm': 'cru',
        'default': '[]',
        'type': 'list-ip',
        'required': 'false',
    },
    'allocation_pools': {
        'perm': 'cr',
        'default': 'none',
        'type': 'list-pool-dict',
        'required': 'false',
    },
    'host_routes': {
        'perm': 'cru',
        'default': '[]',
        'type': 'list-route-dict',
        'required': 'false',
    },
    'enable_dhcp': {
        'perm': 'cru',
        'default': 'true',
        'type': 'boolean',
        'required': 'false',
    },
    'tenant_id': {
        'perm': 'cr',
        'default': 'none',
        'type': 'uuid-str',
        'required': 'false',
    },
}

port = {
    'id': {
        'perm': 'r',
        'default': 'generated',
        'type': 'uuid-str',
        'required': 'false',
    },
    'network_id': {
        'perm': 'cr',
        'default': 'none',
        'type': 'uuid-str',
        'required': 'true',
    },
    'name': {
        'perm': 'cr',
        'default': 'none',
        'type': 'string',
        'required': 'false',
    },
    'admin_state_up': {
        'perm': 'cru',
        'default': 'true',
        'type': 'boolean',
        'required': 'false',
    },
    'status': {
        'perm': 'r',
        'default': 'none',
        'type': 'string',
        'required': 'false',
    },
    'mac_address': {
        'perm': 'cr',
        'default': 'generated',
        'type': 'mac-string',
        'required': 'false',
    },
    'fixed_ips': {
        'perm': 'cr',
        'default': 'generated',
        'type': 'list-fixed-ip-dict',
        'required': 'false',
    },
    'device_id': {
        # TODO Bug 1337457
        #            'perm':'crud',
        'perm': 'r',
        'default': 'none',
        'type': 'uuid-str',
        'required': 'false',
    },
    'device_owner': {
        # 'perm':'crud', # TODO Bug 1337457
        'perm': 'r',
        'default': 'none',
        'type': 'string',
        'required': 'false',
    },
    'tenant_id': {
        'perm': 'cr',
        'default': 'none',
        'type': 'uuid-str',
        'required': 'false',
    },
    'security_groups': {
        'perm': 'crud',
        'default': 'none',
        'type': 'list-sg-str',
        'required': 'false',
    },

}

router = {
    'id': {
        'perm': 'r',
        'default': 'generated',
        'type': 'uuid-str',
        'required': 'false',
    },
    'name': {
        'perm': 'cru',
        'default': 'none',
        'type': 'string',
        'required': 'false',
    },
    'admin_state_up': {
        'perm': 'cru',
        'default': 'true',
        'type': 'boolean',
        'required': 'false',
    },
    'status': {
        'perm': 'r',
        'default': 'none',
        'type': 'string',
        'required': 'false',
    },
    'tenant_id': {
        'perm': 'cr',
        'default': 'none',
        'type': 'uuid-str',
        'required': 'false',
    },
    # Igore external_gateway_info since its not supported
}


def get_matching_perm_attributes(obj, conditions):
    return_list = []
    for (attr, value) in obj.items():
        needed = True
        for (cond_attr, cond_value) in conditions.items():
            if not cond_value in value[cond_attr]:
                needed = needed and False
        if needed:
            return_list.append(attr)
    return return_list


def get_network_c_reqd_attributes1():
    c_reqd_attributes = []
    for (attr, value) in network.items():
        if 'c' in value['perm'] and 'true' in value['required']:
            c_reqd_attributes.append(attr)
    return c_reqd_attributes
# end get_network_c_reqd_attributes


def get_network_create_required_attributes():
    return get_matching_perm_attributes(network, conditions={'perm': 'c', 'required': 'true'})


def get_subnet_create_required_attributes():
    return get_matching_perm_attributes(subnet, conditions={'perm': 'c', 'required': 'true'})


def get_port_create_required_attributes():
    return get_matching_perm_attributes(port, conditions={'perm': 'c', 'required': 'true'})


def get_router_create_required_attributes():
    return get_matching_perm_attributes(router, conditions={'perm': 'c', 'required': 'true'})


def get_other_network_create_attributes():
    all_attributes = get_matching_perm_attributes(network,
                                                  conditions={'perm': 'c', })
    must = get_network_create_required_attributes()
    return list(set(all_attributes) - set(must))


def get_other_subnet_create_attributes():
    all_attributes = get_matching_perm_attributes(subnet,
                                                  conditions={'perm': 'c', })
    must = get_subnet_create_required_attributes()
    return list(set(all_attributes) - set(must))


def get_other_port_create_attributes():
    all_attributes = get_matching_perm_attributes(port,
                                                  conditions={'perm': 'c', })
    must = get_port_create_required_attributes()
    return list(set(all_attributes) - set(must))


def get_other_router_create_attributes():
    all_attributes = get_matching_perm_attributes(router,
                                                  conditions={'perm': 'c', })
    must = get_router_create_required_attributes()
    return list(set(all_attributes) - set(must))


def get_network_read_attributes():
    return get_matching_perm_attributes(network,
                                        conditions={'perm': 'r', })


def get_subnet_read_attributes():
    return get_matching_perm_attributes(subnet,
                                        conditions={'perm': 'r', })


def get_port_read_attributes():
    return get_matching_perm_attributes(port,
                                        conditions={'perm': 'r', })


def get_router_read_attributes():
    return get_matching_perm_attributes(router,
                                        conditions={'perm': 'r', })


def get_network_update_attributes():
    return get_matching_perm_attributes(network,
                                        conditions={'perm': 'u', })


def get_subnet_update_attributes():
    return get_matching_perm_attributes(subnet,
                                        conditions={'perm': 'u', })


def get_port_update_attributes():
    return get_matching_perm_attributes(port,
                                        conditions={'perm': 'u', })


def get_router_update_attributes():
    return get_matching_perm_attributes(router,
                                        conditions={'perm': 'u', })


def get_random_value(obj, attribute, dep_attribute1=None, dep_attribute2=None):
    item = obj[attribute]['type']
    if item == 'string':
        return attribute + '-' + get_random_string()
    elif 'boolean' == item:
        return str(get_random_boolean())
    elif 'uuid-str' == item:
        return get_uuid()
    elif 'int-46' == item:
        # IPv4 always
        return '4'
    elif 'cidr-string' == item:
        return get_random_cidr('16')
    elif 'gw-ip' == item:
        return get_random_ip(dep_attribute1)
    elif 'list-string' == item:
        return get_random_string_list(
            max_list_length=4, prefix=attribute + '-',
            length=8)
    elif 'list-pool-dict' == item:
        # eg: allocation_pool
        return get_pool_dict_list(dep_attribute1)
    elif 'list-route-dict' == item:
        # host routes
        return get_route_dict_list(dep_attribute1)
    elif 'mac-string' == item:
        return get_random_mac()
    elif 'list-fixed-ip-dict' == item:
        return get_fixed_ip_dict_list(dep_attribute1, dep_attribute2)
    elif 'list-ip' == item:
        return get_random_ip_list(max_list_length=4)


if __name__ == "__main__":
    import pdb
    pdb.set_trace()
#    print get_network_c_reqd_attributes1()
    print get_network_create_required_attributes()
    print get_other_network_create_attributes()

    # for i in util.combos(get_other_network_create_attributes()):
    #    print i
    print get_fixed_ip_dict_list('some_uuid', '10.1.1.0/24')
    print get_pool_dict_list('10.1.1.0/24')
