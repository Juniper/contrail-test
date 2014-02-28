from cloudclient import CloudClient
from network_handler import NetworkHandler
import os
from contrail_test_init import ContrailTestInit
from netaddr import IPNetwork


class CloudstackNetworkHandler(NetworkHandler):
    def __init__(self, username, password, connections, cfgm_ip):
        self.client= CloudClient( cfgm_ip, username, password )
        self.cfgm_ip= cfgm_ip
        self.username= username
        self.password= password
        self.connections= connections
        self.inputs= connections.inputs
        self.logger= self.inputs.logger
        self.vnc_lib_h = self.connections.vnc_lib

    def create_network(self, vn_name, vn_subnets, ipam_fq_name, project_id=None, vpc_id = None):
        if vpc_id:
            offering_dict = {'name': 'Juniper\ Contrail\ VPC\ Network\ Offering'}
            offeringid= self.get_offering_id(offering_dict)
        else:
            offeringid= self.get_offering_id()
        zoneid = self.get_zone('default')
        for vn_subnet in vn_subnets:
            block= IPNetwork(vn_subnet)
            gateway= list(block)[-2]
            netmask= block.netmask
            print gateway , netmask, zoneid, offeringid,  vn_name
            try:
                args= {
                        'gateway': gateway, 'netmask': netmask,
                        'zoneid': zoneid, 'networkofferingid': offeringid,
                        'name' : vn_name, 'displaytext': vn_name }
                if vpc_id:
                    args['vpcid'] = vpc_id
                project_fq_name = self.vnc_lib_h.id_to_fq_name(project_id)
                if not 'default-project' in project_fq_name :
                    args['projectid']= project_id
                response= self.client.request('createNetwork', args )
                self.logger.debug( "Create network response: " + str(response))
            except CloudClient.Error,e:
                self.logger.exception("Exception while creating network")
                return None
            return response['createnetworkresponse']['network']
    #end create_network

    def get_offering_id(self, key = None):
        if key:
            resp = self.client.request('listNetworkOfferings', key)
        else:
            resp= self.client.request('listNetworkOfferings', {'name':'Juniper\ Contrail\ Network\ Offering'})
        id= resp ['listnetworkofferingsresponse']['networkoffering'][0]['id']
        return id
    #end get_offering_id

    def get_zone(self, name):
        resp= self.client.request('listZones', {'name': name} )
        id= resp['listzonesresponse']['zone'][0]['id']
        return id
    #end get_zone

    def list_domains(self):
        response = self.client.request('listDomains')
        for domain in response['listdomainsresponse']['domain']:
            print domain['name']
            print domain['id']
    #end list_domains

    def get_networks(self, project_id=None):
        args={}
        if project_id:
            args['projectid']= project_id
        response = self.client.request('listNetworks',args)
        print response
        if 'network' in response['listnetworksresponse']:
            return response['listnetworksresponse']['network']
        return []

    def get_vn_obj_if_present(self, vn_name, project_id=None):
        vns= self.get_networks(project_id)
        for vn in vns:
            if vn['name']== vn_name:
                return vn
        return None

    # In CS, object is a dict
    def get_vn_id_from_obj( self, obj ) :
        return obj['id']

    def get_vn_fq_name (self, obj):
        return ':'.join(['default-domain','default-project', obj['name']] )

    def get_vn_name( self, obj ):
        return obj['name']

    def delete_vn( self, vn_id):
        response=None
        try:
            response= self.client.request('deleteNetwork',{'id': vn_id } )
        except CloudClient.Error,e:
            self.logger.exception("Exception while deleting network ID %s" %( vn_id ))
            return None
        return response
    #end delete_vn

if __name__ == "__main__":
    from connections import ContrailConnections
    if 'PARAMS_FILE' in os.environ :
        ini_file= os.environ.get('PARAMS_FILE')
    else:
        ini_file= 'params.ini'
    x= ContrailTestInit( ini_file)
    x.setUp()
    connections= ContrailConnections(x)
    cs_obj= CloudstackNetworkHandler( 'admin', 'password',connections, x.cfgm_ip)
#    cs_obj.create_network('vn1',['10.1.1.0/24'], None)
    import pdb; pdb.set_trace()


