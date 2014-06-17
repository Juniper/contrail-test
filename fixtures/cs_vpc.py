import fixtures
from contrail_fixtures import *


class CSVPCFixture(fixtures.Fixture ):
    '''create and delete vpc object for cloudstack
        get Juniper offering of the VPC ID,
        create VPC using the offering ID
        '''
    def __init__(self, vpc_name, cidr, connections, vnc_lib_h,
                 project_name='admin', zone='default'):
        self.connections = connections
        self.inputs=connections.inputs
        self.vnc_lib_h= vnc_lib_h
        self.project_name=project_name
        self.domain_name='default-domain'
        self.logger= self.inputs.logger
        self.already_present= False
        self.project_id = None
        self.vpc_offering_id = None
        self.vpc_name = vpc_name
        self.vpc_id = None
        self.cidr = cidr
        self.zone_name = zone
        self.zone_id = None
        self.acllists = []
        self.aclrules = {}
    #end __init__

    def get_provider_vpcid(self, keyword):
        try:
            response = self.connections.cstack_handle.client.request(
                           'listVPCOfferings', {'keyword': keyword})
            self.logger.debug(response)
            result = response['listvpcofferingsresponse']
            if not result:
                self.logger.error('%s not found, listVPCOffering response is %s' %(keyword, response))
                return
            return result['vpcoffering'][0]['id']
        except NoIdError,e:
            self.logger.error(('%s not found') %keyword)
            return
    #end get_provider_vpcid

    def create_vpc(self):
        params = { 'name': self.vpc_name }
        try:
            response = self.connections.cstack_handle.client.request(
                                                  'listVPCs', params)
            self.logger.debug(response)
            id = response['queryasyncjobresultresponse']['jobresult']['vpc']['id']
            self.logger.info('Reusing the existing VPC '+self.vpc_name)
            return id
        except:
            self.logger.info('Creating VPC '+self.vpc_name)
        params = { 'displaytext': self.vpc_name,
                   'cidr': self.cidr,
                   'vpcofferingid': self.vpc_offering_id,
                   'zoneid': self.zoneid,
                   'name': self.vpc_name
                 }
        try:
            response = self.connections.cstack_handle.client.request(
                                                  'createVPC', params)
            self.logger.debug(response)
            result = response['queryasyncjobresultresponse']
            if not result:
                self.logger.error('no response, createVPC response is %s' %(
                                                                   response))
                return
            return result['jobresult']['vpc']['id']
        except:
            self.logger.error(('%s not found') %self.vpc_name)
            return
    #end create_vpc

    def setUp(self):
        super(CSVPCFixture, self).setUp()
        self.vpc_offering_id = self.get_provider_vpcid(
                               'Juniper Contrail VPC Offering')
        self.zoneid = self.connections.cstack_handle.get_zone(self.zone_name)
        self.displaytext = self.vpc_name
        if not self.vpc_offering_id:
            self.logger.error('vpc_id is null')
            return
        try:
            self.vpc_id = self.create_vpc()
        except:
            self.logger.error('vpc create failed')
            return
    #end setUp

    def delete_vpc(self):
        try:
            for acllist in self.acllists:
                self.delete_acllist(acllist)
            self.logger.info('Deleting VPC %s' %(self.vpc_name))
            response = self.connections.cstack_handle.client.request(
                                     'deleteVPC', {'id': self.vpc_id})
            result = response['queryasyncjobresultresponse']
            if not result:
                self.logger.error('delete VPC failed, response is %s' %response)
                return False
            print result
            return result['jobresult']['success']
        except:
            self.logger.error(('deletion of VPC %s failed') %self.vpc_name)
            return
    #end delete_vpc

    def restart_vpc(self):
        try:
            self.logger.info('Restarting VPC %s' %(self.vpc_name) )
            response = self.connections.cstack_handle.client.request(
                                    'restartVPC', {'id': self.vpc_id})
            result = response['queryasyncjobresultresponse']
            if not result:
                self.logger.error('restart VPC failed, response is %s' %response)
                return False
            print result
            return result['jobresult']['success']
        except:
            self.logger.error(('Restart of VPC %s failed.') %(self.vpc_name))
            return False
    #end restart_vpc

    def cleanUp(self):
        super(CSVPCFixture, self).cleanUp()
        self.logger.info('Deleting VPC %s' %(self.vpc_name) )
        assert self.delete_vpc(), "Delete vpc %s failed"%(self.vpc_name)
    #end cleanUp

    def create_acllist(self, vpc_id, acllistname):
        params = {'description' : acllistname,
                  'name' : acllistname,
                  'vpcid' : vpc_id}
        try:
            result = self.connections.cstack_handle.client.request(
                                     'createNetworkACLList', params)
            self.logger.info("create neworkacllist command result - %s" %result)
            acllist = result['queryasyncjobresultresponse']['jobresult']['networkacllist']['id']
            self.acllists.append(acllist)
            self.aclrules[acllist] = []
            return acllist
        except:
            self.logger.error(('create acl list - %s failed') %acllistname)
            return
    #end create_acllist

    def create_aclrule(self, number, protocol, aclid, cidrlist, traffictype,
                       action, icmpcode=None, icmptype=None,
                       startport=None, endport=None):
        params = {'number' : number,
                  'protocol' : protocol,
                  'aclid' : aclid,
                  'cidrlist' : cidrlist,
                  'traffictype' : traffictype,
                  'action' : action}
        if protocol == 'icmp':
            params.update({'icmpcode': icmpcode})
            params.update({'icmptype': icmptype})
        elif protocol == 'tcp' or protocol == 'udp':
            params.update({'startport': startport})
            params.update({'endport': endport})

        try:
            result = self.connections.cstack_handle.client.request(
                                         'createNetworkACL', params)
            self.logger.info("create acl rule command result is %s" %result)
            ruleid = result['queryasyncjobresultresponse']['jobresult']['networkacl']['id']
            self.aclrules[aclid].append(ruleid)
            return ruleid
        except :
            self.logger.error('create acl rule failed ')
            return
    #end create_aclrule

    def modify_aclrule(self, number, protocol, ruleid, cidrlist, traffictype,
                       action, icmpcode=None, icmptype=None,
                       startport=None, endport=None):
        params = {'number' : number,
                  'protocol' : protocol,
                  'id' : ruleid,
                  'cidrlist' : cidrlist,
                  'traffictype' : traffictype,
                  'action' : action}
        if protocol == 'icmp':
            params.update({'icmpcode': icmpcode})
            params.update({'icmptype': icmptype})
        elif protocol == 'tcp' or protocol == 'udp':
            params.update({'startport': startport})
            params.update({'endport': endport})

        try:
            result = self.connections.cstack_handle.client.request(
                                     'updateNetworkACLItem', params)
            self.logger.info("modify acl rule command result is %s" %result)
            return result['queryasyncjobresultresponse']['jobresult']['networkacl']['id']
        except:
            self.logger.error('modify acl rule failed')
            return False
    #end modify_aclrule

    def delete_aclrule(self, ruleid):
        try:
            result = self.connections.cstack_handle.client.request(
                                 'deleteNetworkACL', {'id': ruleid})
            self.logger.info("delete acl rule command result is %s" %result)
            print result
            status = result['queryasyncjobresultresponse']['jobresult']['success']
            if status:
                next((self.aclrules[key] for key in self.aclrules if ruleid in self.aclrules[key]), [ruleid]).remove(ruleid)
            return status
        except:
            self.logger.error('delete acl rule failed')
            return

    def bind_acl_nw(self, acl_id, network_id=None):
        params = {'aclid' : acl_id,
                  'networkid' : network_id}
        try:
            result = self.connections.cstack_handle.client.request(
                                    'replaceNetworkACLList', params)
            self.logger.info("replace neworkacllist command result is %s" %result)
            print result
            return result['queryasyncjobresultresponse']['jobresult']['success']
        except:
            self.logger.error('replace acl on network failed')
            return
    #end bind_acl_nw

    def delete_acllist(self, acl_id):
        params = {'id' : acl_id }
        try:
            for rule in self.aclrules[acl_id]:
                self.delete_aclrule(rule)
            result = self.connections.cstack_handle.client.request(
                                     'deleteNetworkACLList', params)
            self.logger.info("delete neworkacllist command result is %s" %result)
            print result
            if acl_id in self.acllists:
                self.acllists.remove(acl_id)
            return result['queryasyncjobresultresponse']['jobresult']['success']
        except:
            self.logger.error('delete acl on network failed')
            return
    #end unbind_acl_nw

#end CSVPCFixture

