import logging as LOG
from tcutils.verification_util import *

LOG.basicConfig(format='%(levelname)s: %(message)s', level=LOG.DEBUG)

def _extract_name(name):
    if ':' in name:
        return name.split(':')[2]
    return name

class SvcmonInspect (VerificationUtilBase):

    def __init__(self, ip, logger=LOG):
        super(SvcmonInspect, self).__init__(ip, 8088, XmlDrv, logger=logger)

    def _get_si(self, name):
        name = _extract_name(name)
        xt = self.dict_get('Snh_ServiceInstanceList?si_name=' + name)
        xt = xt.xpath('si_names/list/ServiceInstance')
        if xt == []:
            return None
        assert len(xt) == 1, "Expecting only one SI instance"
        return xt[0]

    def _get_type_and_state(self, xt):
        si_name = xt.xpath('name')[0].text
        si_type = xt.xpath('si_type')[0].text
        si_state = xt.xpath('si_state')[0].text
        return (si_name, si_type, si_state)

    def _get_vms(self, xt):
        vms = []
        for vm in xt.xpath('vm_list/list/ServiceInstanceVM'):
            vm_dict = dict()
            vm_dict['name'] = vm.xpath('name')[0].text
            vm_dict['vr_name'] = vm.xpath('vr_name')[0].text
            vm_dict['ha'] = vm.xpath('ha')[0].text
            vms.append(vm_dict)
        return vms

    def _get_vns(self, xt):
        vns = {'left':None, 'right':None, 'mgmt':None}
        vn_e = xt.xpath('left_vn/list/element')
        if vn_e:
            vns['left'] = {'name':vn_e[0].text, 'uuid':vn_e[1].text}
        vn_e = xt.xpath('right_vn/list/element')
        if vn_e:
            vns['right'] = {'name':vn_e[0].text, 'uuid':vn_e[1].text}
        vn_e = xt.xpath('management_vn/list/element')
        if vn_e:
            vns['mgmt'] = {'name':vn_e[0].text, 'uuid':vn_e[1].text}
        return vns

    def get_si_info(self, name):
        si = dict()
        sixt = self._get_si(name)
        if not sixt:
            return None
        si['name'], si['type'], si['state'] = self._get_type_and_state(sixt)
        si['vms'] = self._get_vms(sixt)
        si['vns'] = self._get_vns(sixt)
        return si
