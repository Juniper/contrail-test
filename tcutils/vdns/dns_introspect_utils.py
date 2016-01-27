import logging as LOG

from tcutils.verification_util import *

LOG.basicConfig(format='%(levelname)s: %(message)s', level=LOG.DEBUG)


class DnsAgentInspect (VerificationUtilBase):

    def __init__(self, ip, logger=LOG):
        super(DnsAgentInspect, self).__init__(
            ip, 8092, XmlDrv, logger=logger)

    def get_dnsa_dns_list(self, domain='default-domain'):
        '''
            method: get_dnsa_dns_list returns a list
            returns None if not found, a dict w/ attrib. eg:
        '''
        path = 'Snh_ShowAgentXmppDnsData?'
        xpath = './data/list/AgentDnsData'
        dns_agent = self.dict_get(path)
        dns_agents = EtreeToDict(xpath).get_all_entry(dns_agent)

        dns_data = {}
        for data in dns_agents:
            dns_data.update({data['agent']: data['agent_data']})
        return dns_data
    # end of get_dnsa_dns_list

    def get_dnsa_config(self, domain='default-domain'):
        '''
        method: get_dnsa_config returns a list 
        returns None if not found, a dict w/ attrib.
        '''
        path = 'Snh_ShowVirtualDnsServers?'
        xpath = './virtual_dns_servers/list/VirtualDnsServersSandesh/virtual_dns'
        virtual_dns = self.dict_get(path)
        virtual_dns_data = EtreeToDict(xpath).get_all_entry(virtual_dns)

        if type(virtual_dns_data) == type(dict()):
            virtual_dns_data = [virtual_dns_data]

        return_vdns_data = []
        for vdata in virtual_dns_data:
            dns_data = {}
            dns_data['virtual_dns'] = vdata
            # get the record data
            record_data = self.get_rec_data(
                vdns_server=vdata['VirtualDnsTraceData']['name'])
            dns_data['records'] = record_data
            return_vdns_data.append(dns_data)
        return return_vdns_data

    def get_rec_data(self, vdns_server):
        path = 'Snh_ShowVirtualDnsRecords?x=%s' % vdns_server
        xpath = './records'
        rec_data = self.dict_get(path)
        return_data = EtreeToDict(xpath).get_all_entry(rec_data)
        return return_data['records']
    # end of get_dnsa_config
