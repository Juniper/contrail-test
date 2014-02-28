from cloudclient import CloudClient
from network_handler import NetworkHandler
import os
from contrail_test_init import ContrailTestInit
from netaddr import IPNetwork


class CloudstackHandler(NetworkHandler):
    def __init__(self, username, password, connections, cfgm_ip ):
        self.client= CloudClient( cfgm_ip, username, password )
        self.cfgm_ip= cfgm_ip
        self.username= username
        self.password= password
        self.connections= connections
        self.inputs= connections.inputs

    def create_network(self, vn_name, vn_subnets, ipam_fq_name, project_id=None):
        offeringid= self.get_offering_id()
        zoneid = self.get_zone('default')
        for vn_subnet in vn_subnets:
            block= IPNetwork(vn_subnet)
            gateway= list(block)[-2]
            netmask= block.netmask
            print gateway , netmask, zoneid, offeringid,  vn_name
            net_req_args = { 'gateway': gateway, 'netmask': netmask,
                    'zoneid': zoneid, 'networkofferingid': offeringid,
                    'name' : vn_name, 'displaytext': vn_name }
            if project_id:
                net_req_args['projectid'] = project_id
            response= self.client.request('createNetwork', net_req_args )
            self.logger.debug( "Create network response: " + str(response))
            return response['createnetworkresponse']['network']
    #end create_network

    def get_offering_id(self):
        resp= self.client.request('listNetworkOfferings', {'name':'Juniper\ Contrail\ Network\ Offering'})
        id= resp ['listnetworkofferingsresponse']['networkoffering'][0]['id']
        return id
    #end get_offering_id

    def get_zone(self, name):
        resp= self.client.request('listZones', {'name': name} )
        print "Zone : " + str(resp)
        id= resp['listzonesresponse']['zone'][0]['id']
        return id
    #end get_zone

    def list_domains(self):
        response = self.client.request('listDomains')
        for domain in response['listdomainsresponse']['domain']:
            print domain['name']
            print domain['id']
    #end list_domains

    def get_networks(self):
        response = self.client.request('listNetworks')
        print response
        if 'network' in response['listnetworksresponse']:
            return response['listnetworksresponse']['network']
        return []

    def get_vn_obj_if_present(self, vn_name):
        vns= self.get_networks()
        for vn in vns:
            if vn['name']== vn_name:
                return vn
        return None

    # In CS, object is a dict
    def get_vnid_from_obj( self, obj ) :
        return obj['id']

#    def get_vn_fq_name (self, obj):
#        return ':'.join(['default-domain','default-project', obj['name']] )

    def delete_vn( self, vn_id):
        response= self.client.request('deleteNetwork',{'id': vn_id } )
        return response

    def getTemplate(self, tmpl_name):
        response = self.client.request('listTemplates',
                                {'templatefilter': 'executable',
                                 'name': tmpl_name})
        return response['listtemplatesresponse']['template'][0]['id']
    #end getTemplate

    def install_vm_template(iself, bits, name, osTypeId, vmTemplateUrl):
    #check system_VM status
        params = {
                'bits': bits,
                'templateName':  name,
                'osTypeId': osTypeId,
                'url' : vmTemplateUrl,
                }
        result = self.client.request('createTemplate', params)
        print result
        return True
    # end install_vm_template_new


if __name__ == "__main__":
    from connections import ContrailConnections
    if 'PARAMS_FILE' in os.environ :
        ini_file= os.environ.get('PARAMS_FILE')
    else:
        ini_file= 'params.ini'
    x= ContrailTestInit( ini_file)
    x.setUp()
    connections= ContrailConnections(x)
    cs_obj= CloudstackHandler( 'admin', 'password',connections, x.cfgm_ip)
#    cs_obj.create_network('vn1',['10.1.1.0/24'], None)
    import pdb; pdb.set_trace()


