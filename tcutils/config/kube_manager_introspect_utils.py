import logging as LOG

from tcutils.verification_util import *

LOG.basicConfig(format='%(levelname)s: %(message)s', level=LOG.DEBUG)


class KubeManagerInspect(VerificationUtilBase):

    def __init__(self, ip, logger=LOG, args=None, port=8108):
        super(KubeManagerInspect, self).__init__(
            ip, port, XmlDrv, logger=logger, args=args)
        self.ip = ip

