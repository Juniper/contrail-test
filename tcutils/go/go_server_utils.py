import logging as LOG

from tcutils.verification_util import *
#from go_api_results import *

LOG.basicConfig(format='%(levelname)s: %(message)s', level=LOG.DEBUG)


class GoApiInspect(VerificationUtilBase):

    def __init__(self, ip, inputs, port='9091', protocol='https',
                 insecure=True, logger=LOG):
        super(GoApiInspect, self).__init__(ip, port, logger=logger,
            args=inputs, protocol=protocol, insecure=insecure)

    def get_cluster_id(self, name=None):
        ''' get cluster id '''
        dct = self.dict_get('contrail-clusters')
        ids = [cluster['uuid'] for cluster in dct['contrail-clusters'] \
                   if not name or name == cluster['fq_name'][-1]]
        return ids[0] if ids else None
