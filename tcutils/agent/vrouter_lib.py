from common import log_orig as contrail_logging


def is_nh_local(nh):
    if 'LOCAL' in nh.get('flags'):
        return True
    else:
        return False


def is_nh_of_local_interface(inspect_h, nh, intf_name, logger=None):
    '''
    '''
    logger = logger or contrail_logging.getLogger(__name__)
    if is_nh_local(nh):
        vif_index = nh.get('encap_oif_id')
        vif_dict = inspect_h.get_vrouter_virtual_interface(vif_index)
        if vif_dict['name'] == intf_name:
            logger.debug('NH %s does indeed point to local interface' % (
                nh, intf_name))
            return True
        else:
            logger.debug('NH %s does not point to local interface' % (
                nh, intf_name))
            return False
        # endif
    # endif
# end is_nh_of_local_interface


def validate_route_tunnel_and_label(nh, tunnel_dest_ip, label, logger=None):
    '''
    '''
    logger = logger or contrail_logging.getLogger(__name__)
    nh_tunnel_dest = nh.get('tun_dip')
    nh_label = label
    if tunnel_dest_ip != nh_tunnel_dest or label != nh_label:
        logger.warn('Mismatch in nh validation, Expected Tunnel, label'
                    ': %s, %s; Got %s, %s' % (tunnel_dest_ip, label,
                                              nh_tunnel_dest, nh_label))
        return False
    else:
        logger.debug('Remote Nh validation passed. Expected Tunnel, label'
                     ': %s, %s; Got %s,%s' % (tunnel_dest_ip, label,
                                              nh_tunnel_dest, nh_label))
        return True
# end validate_route_tunnel_and_label


def validate_route_in_vrouter(route, inspect_h=None, intf_name=None,
                              tunnel_dest_ip=None, label=None, logger=None):
    '''
        Args tunnel_dest_ip and label are expected to be set while
        validating remote nh.
        If local nh, inspect_h and tap interface name needs to be set
    '''
    logger = logger or contrail_logging.getLogger(__name__)
    nh = route.get('nh')
    if not nh:
        logger.debug('Need nh details in %s to validate route' % (route))
        result = False

    if is_nh_local(nh):
        result = is_nh_of_local_interface(inspect_h, intf_name, logger)
    else:
        result = validate_route_tunnel_and_label(nh, tunnel_dest_ip,
                                                 route['label'], logger)
    return result
# end validate_route_in_vrouter


def validate_local_route_in_vrouter(route, inspect_h, intf_name, logger=None):
    return validate_route_in_vrouter(route, inspect_h=inspect_h,
                                     intf_name=intf_name, logger=logger)


def validate_remote_route_in_vrouter(route, tunnel_dest_ip, label, logger=None):
    return validate_route_in_vrouter(route, tunnel_dest_ip=tunnel_dest_ip,
                                     label=label, logger=logger)
