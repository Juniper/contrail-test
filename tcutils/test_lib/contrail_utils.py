'''
Contrail feature specific utility methods
'''


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
    computes = list(set(peers) & \
                    set(inputs.compute_names))
    interested_computes = [self.inputs.host_data[x]['host_ip'] \
                                 for x in computes ]
    return interested_computes
# end get_interested_computes
