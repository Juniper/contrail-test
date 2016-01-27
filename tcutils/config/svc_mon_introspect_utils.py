import logging as LOG

from tcutils.verification_util import *
from svc_mon_results import *

LOG.basicConfig(format='%(levelname)s: %(message)s', level=LOG.DEBUG)


class SvcMonInspect(VerificationUtilBase):

    def __init__(self, ip, logger=LOG, args=None):
        super(SvcMonInspect, self).__init__(
            ip, 8088, XmlDrv, logger=logger, args=args)
        self._cache = {
            'si': {},
        }

    def update_cache(self, otype, fq_path, d):
        self._cache[otype]['::'.join(fq_path)] = d

    def try_cache(self, otype, fq_path, refresh):
        p = None
        try:
            if not (refresh or self.get_force_refresh()):
                p = self._cache[otype]['::'.join(fq_path)]
        except KeyError:
            pass
        return p

    def get_service_instance(self, name, refresh=False):
        '''
            method: get_service_instance find a service instance by name
            returns CsSvcInstance object, None if not found

        '''
        obj = self.try_cache('si', [name], refresh)
        if not obj:
            # cache miss
            xml_data = self.dict_get('Snh_ServiceInstanceList?si_name=%s'%name)
            instances = xml_data.xpath('./si_names/list/ServiceInstance')
            if instances:
                obj = CsSvcInstance(instances[0])
                self.update_cache('si', [name], obj)
        return obj

