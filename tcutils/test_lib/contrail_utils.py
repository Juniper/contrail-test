'''
Contrail feature specific utility methods
'''

import os
import ast


def get_ri_name(vn_fq_name):
    '''
    Return RI name given a VN fq name
    vn_fq_name can be a list or a string(colon separated)
    '''
    if type(vn_fq_name) == list:
        vn_name = vn_fq_name[-1]
        return vn_fq_name + vn_name
    else:
        vn_name = vn_fq_name.split(':')[-1]
        return vn_fq_name + ':' + vn_name
# end get_ri_name


def get_interested_computes(connections, vn_fq_names=[]):
    '''
    Returns a list of compute node ips interested in one or more VNs
    '''
    peers = []
    inputs = connections.inputs
    for control_node in inputs.bgp_ips:
        for vn_fq_name in vn_fq_names:
            inspect_h = connections.cn_inspect[control_node]
            peers.extend(inspect_h.get_cn_ri_membership(vn_fq_name=vn_fq_name))

    # peers can include control-only nodes, we need only compute
    computes = list(set(peers) &
                    set(inputs.compute_names))
    interested_computes = [self.inputs.host_data[x]['host_ip']
                                 for x in computes]
    return interested_computes
# end get_interested_computes


def check_xmpp_is_stable(inputs, connections, orig_flap_dict=None):
    '''
    Returns (boolean, flap_dict)

    flap_dict : [ '<compute_ip>': [ 'controller_ip_1': <flap_count>,
                                    'controller_ip_2': <flap_count>]
                  ....
                ]
    If orig_flap_dict is passed, compares it with flap_dict and returns
        True if same
    If orig_flap_dict is not passed, returns (True, flap_dict)
    '''
    orig_flap_dict = orig_flap_dict or {}
    flap_dict = {}
    logger = inputs.logger

    xmpp_check_env = os.getenv('DO_XMPP_CHECK', None)
    if xmpp_check_env is None:
        do_xmpp_check = False
    else:
        do_xmpp_check = bool(ast.literal_eval(xmpp_check_env))

    if not do_xmpp_check:
        logger.debug('Skipping xmpp flap check')
        return (True, {})

    result = True
    for ip in inputs.compute_ips:
        flap_dict[ip] = {}
        agent_inspect = connections.agent_inspect[ip]
        if not agent_inspect:
            continue
        xmpp_status = agent_inspect.get_vna_xmpp_connection_status()
        for entry in xmpp_status:
            if entry['state'] != 'Established':
                logger.warn('XMPP flap count of %s is %s' %(
                    ip, entry['cfg_controller']))
                logger.debug(entry)
                result = result and False
            flap_dict[ip][entry['controller_ip']] = entry['flap_count']
    # end for ip
    if orig_flap_dict:
        if orig_flap_dict != flap_dict:
            logger.error('XMPP status is %s, Expected: %s' %(
                flap_dict, orig_flap_dict))
            result = result and False
        else:
            logger.debug('No XMPP flaps were noticed during the test')
    else:
        logger.debug('Nothing to compare xmpp stats %s with' %(
            flap_dict))

    return (result, flap_dict)
# end check_xmpp_is_stable
