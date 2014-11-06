from tcutils.verification_util import *


class VnaVnListResult (Result):

    '''
        VnaVnListResult to provide access to vna_introspect_utils.get_vna_vn_list
        dict contrains:
    '''

    def vn_list(self):
        return self.xpath('VNs')

    def vn_items(self):
        for v in self.vn_list():
            yield VnaVnResult(v)


class VnaVrfRouteEntryResult (Result):
    pass


class VnaVrfIdResult (Result):
    pass


class VnaVrfRouteResult (Result):

    '''
        VnaVrfRouteResult to provide access to vna_introspect_utils.get_vna_vrf_id
        dict contrains:

    '''

    def route_items(self):
        for r in self['routes']:
            yield VnaVrfRouteEntryResult(r)

    def first_route(self):
        if self['routes']:
            return VnaVrfRouteEntryResult(self['routes'][0])

    def filter(self):
        if self['ip'] and self['prefix']:
            r = filter(lambda x: x['src_ip'] == self['ip'] and str(
                self['prefix']) == x['src_plen'], self['routes'])
            self['routes'] = r


class VnaVrfListResult (Result):
    pass


class VnaItfResult (Result):

    '''
        VnaItfResult to provide access to vna_introspect_utils.get_vna_tap_interface_*
        dict contrains:

    '''

    def tapif(self):
        return self['name']

    def vm(self):
        return self['vm_uuid']

    def ip(self):
        return self['ip_addr']

    def vn(self):
        return self['vn_name']

    def vrf(self):
        return self['vrf_name']

    def floating_ip_list(self):
        return map(lambda x: x['ip_addr'], self['fip_list'])

    def floating_ip_vrf_list(self):
        return map(lambda x: x['vrf_name'], self['fip_list'])


class VnaVnResult (Result):

    '''
        VnaVnResult to provide access to vna_introspect_utils.get_vna_vn
        dict contrains:

            {'acl_uuid': '00000000-0000-0000-0000-000000000000',
             'ipam_data': None,
             'mirror_acl_uuid': '00000000-0000-0000-0000-000000000000',
             'name': 'default-domain:admin:front-end',
             'uuid': '75b38b78-554e-40fe-96ca-e7137b8d9974',
             'vrf_name': 'default-domain:admin:front-end:front-end'}
    '''

    def vrf_name(self):
        return self.xpath('vrf_name')

    def name(self):
        return self.xpath('name')

    def mirror_acl_uuid(self):
        return self.xpath('mirror_acl_uuid')

    def ipam_data(self):
        return self.xpath('ipam_data')

    def acl(self):
        return self.xpath('acl_uuid')

    def uuid(self):
        return self.xpath('uuid')


class VnaACLResult (Result):

    '''
        VnaACLResult to provide access to vna_introspect_utils.get_vna_acl_by_vn
    '''


class VnaFlowResult (Result):

    '''
        VnaFlowResult to provide access to vna_introspect_utils.get_vna_flow_by_vn
    '''
