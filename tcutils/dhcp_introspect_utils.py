import logging as LOG

from tcutils.verification_util import *

LOG.basicConfig(format='%(levelname)s: %(message)s', level=LOG.DEBUG)


class DhcpInspect (VerificationUtilBase):

    def __init__(self, ip, port=8085, logger=LOG, args=None):
        super(DhcpInspect, self).__init__(
            ip, port, XmlDrv, logger=logger, args=args)

    def is_dhcp_offered(self,mac_addr):
        path = 'Snh_DhcpInfo'
        mac = mac_addr.lower()
        xpath="//Dhcpv4Hdr[chaddr[starts-with(text(),'%s')] and dhcp_options[contains(text(),'Offer')]]"%mac.replace(":"," ")
        dhcp_stats_list = self.dict_get(path)
        dhcp_entries = EtreeToDict(xpath).get_all_entry(dhcp_stats_list)

        if len(dhcp_entries):
           return True
        else:
           return False

if __name__ == '__main__':
    va = DhcpInspect('10.100.10.100',8085)
    print va.is_dhcp_offered("00:11:22:33:44:55")