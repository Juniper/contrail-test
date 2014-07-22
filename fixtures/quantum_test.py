import fixtures
from contrail_fixtures import contrail_fix_ext
from util import get_plain_uuid, get_dashed_uuid

try:
    from quantumclient.quantum import client
    from quantumclient.client import HTTPClient
    from quantumclient.common.exceptions import QuantumClientException as CommonNetworkClientException
except ImportError:
    from neutronclient.neutron import client
    from neutronclient.client import HTTPClient
    from neutronclient.common.exceptions import NeutronClientException as CommonNetworkClientException


class NetworkClientException(CommonNetworkClientException):

    def __init__(self, **kwargs):
        message = kwargs.get('message')
        self.status_code = kwargs.get('status_code', 0)
        if message:
            self.message = message
        super(NetworkClientException, self).__init__(**kwargs)

    def __str__(self):
        return repr(self.message)


class QuantumFixture(fixtures.Fixture):

    def __init__(self, username, password, project_id, inputs, cfgm_ip, openstack_ip):
        httpclient = None
        self.quantum_port = '9696'
        self.username = username
        self.password = password
        self.project_id = None
        self.project_id = project_id
        self.cfgm_ip = cfgm_ip
        self.openstack_ip = openstack_ip
        self.inputs = inputs
        self.obj = None
        self.auth_url = 'http://' + openstack_ip + ':5000/v2.0'
        self.logger = self.inputs.logger
    # end __init__

    def setUp(self):
        super(QuantumFixture, self).setUp()
        project_id = get_plain_uuid(self.project_id)
        try:
            httpclient = HTTPClient(username=self.username,
                                    tenant_id= project_id,
                                    password=self.password,
                                    auth_url=self.auth_url)
            httpclient.authenticate()
        except CommonNetworkClientException, e:
            self.logger.exception('Exception while connection to Quantum')
            raise e
        OS_URL = 'http://%s:%s/' % (self.cfgm_ip, self.quantum_port)
        OS_TOKEN = httpclient.auth_token
        self.obj = client.Client('2.0', endpoint_url=OS_URL, token=OS_TOKEN)
        self.project_id = httpclient.auth_tenant_id
    # end setUp

    def cleanUp(self):
        super(QuantumFixture, self).cleanUp()

    def get_handle(self):
        return self.obj
    # end get_handle

    def create_network(self, vn_name, vn_subnets, ipam_fq_name, shared=False, router_external=False):
        """Create network given a name and a list of subnets.
        """
        try:
            net_req = {}
            net_req['name'] = vn_name
            if shared:
               net_req['shared'] = shared
            if router_external:
               net_req['router:external'] = router_external
            net_rsp = self.obj.create_network({'network': net_req})
            self.logger.debug('Response for create_network : ' + repr(net_rsp))

            vn_id = net_rsp['network']['id']
            net_id = net_rsp['network']['id']
            for subnet in vn_subnets:
                subnet = unicode(subnet)
                net_rsp = self.create_subnet(
                    unicode(subnet), net_id, ipam_fq_name)
            # end for
            return self.obj.show_network(network=net_id)
        except CommonNetworkClientException, e:
            self.logger.exception(
                'Quantum Exception while creating network %s' % (vn_name))
            return None

    def create_subnet(self, cidr, net_id, ipam_fq_name=None):

        subnet_req = {'network_id': net_id,
                      'cidr': cidr,
                      'ip_version': 4,
                      'contrail:ipam_fq_name': ipam_fq_name,
                     }
        subnet_rsp = self.obj.create_subnet({'subnet': subnet_req})
        self.logger.debug('Response for create_subnet : ' + repr(subnet_rsp))
        return subnet_rsp
    # end _create_subnet

    def create_port(self, net_id, fixed_ip=None,):
        port_req = {
           'network_id': net_id,
        }
        if fixed_ip:
            port_req['fixed_ips'] = [{'ip_address':fixed_ip}]
        port_rsp = self.obj.create_port({'port': port_req})
        self.logger.debug( 'Response for create_port : ' + repr(port_rsp) )
        return port_rsp['port']
    #end _create_port   

    def delete_port(self, port_id,):
        port_rsp = self.obj.delete_port(port_id)
        self.logger.debug( 'Response for delete_port : ' + repr(port_rsp) )
        return port_rsp
    #end delete_port  

    def get_vn_obj_if_present(self, vn_name, project_id=None):
        if not project_id:
            project_id = get_dashed_uuid(self.project_id)
        try:
            net_rsp = self.obj.list_networks()
            for (x, y, z) in [(network['name'], network['id'], network['tenant_id']) for network in net_rsp['networks']]:
                dashed_tenant_id = get_dashed_uuid(z)
                if vn_name == x and project_id in dashed_tenant_id:
                    net_id = y
                    return self.obj.show_network(network=net_id)
        except CommonNetworkClientException, e:
            self.logger.exception(
                "Some exception while doing Quantum net-list")
            raise NetworkClientException(message=str(e))
        return None
    # end get_vn_obj_if_present

    def get_vn_obj_from_id(self, id):
        try:
            return self.obj.show_network(network=id)
        except CommonNetworkClientException, e:
            self.logger.exception(
                "Some exception while doing Quantum net-list")
            return None
        return None

    def delete_vn(self, vn_id):
        result = True
        try:
            net_rsp = self.obj.delete_network(vn_id)
            self.logger.debug('Response for deleting network %s' %
                              (str(net_rsp)))
        except CommonNetworkClientException, e:
            self.logger.exception(
                'Quantum exception while deleting a VN %s' % (vn_id))
            result = False

        return result
    # end _delete_vn

    def list_networks(self, args):
        try:
            net_rsp = self.obj.list_networks(args)
            return net_rsp
        except CommonNetworkClientException, e:
            self.logger.debug("Exception while viewing Network list")
            return []
    # end list_networks

    def create_floatingip(self, fip_pool_vn_id, project_id):
        fip_req = {'floatingip': {'floating_network_id': fip_pool_vn_id,
                                  'tenant_id': project_id}}
        fip_resp = self.obj.create_floatingip(fip_req)
        return fip_resp
    # end create_floatingip

    def delete_floatingip(self, fip_id):
        fip_resp = self.obj.delete_floatingip(fip_id)
        return fip_resp
    # end delete_floatingip

    def list_floatingips(self, tenant_id):
        self.obj.list_floatingips(tenant_id=tenant_id)
    # end

    def get_floatingip(self, fip_id):
        return self.obj.show_floatingip(fip_id)
    # end get_floatingip

    def get_port_id(self, vm_id):
        ''' Returns the Quantum port-id of a VM.
        
        '''
        try:
            port_rsp = self.obj.list_ports(device_id=[vm_id])
            port_id = port_rsp['ports'][0]['id']
            return port_id
        except Exception, e:
            self.logger.error('Error occured while getting port-id of a VM ')
            return None
    # end

    def update_floatingip(self, fip_id, update_dict):
        return self.obj.update_floatingip(fip_id, update_dict)
    # end update_floatingip

    def get_vn_id(self, vn_name):
        net_id = None
        net_rsp = self.obj.list_networks()
        for (x, y, z) in [(network['name'], network['id'], network['tenant_id']) for network in net_rsp['networks']]:
            if vn_name == x and self.project_id in z:
                net_id = y
                break
        return net_id
    # end get_vn_id

    def create_policy(self, policy_dict):
        policy_rsp = None
        try:
            policy_rsp = self.obj.create_policy(policy_dict)
        except CommonNetworkClientException, e:
            self.logger.error(
                "Quantum Exception while creating policy" + str(e))
        return policy_rsp
    # end create_policy

    def update_policy(self, policy_id, policy_entries):
        '''policy_data format {'policy': {'entries': new_policy_entries}}'''
        policy_rsp = None
        try:
            policy_rsp = self.obj.update_policy(policy_id, policy_entries)
        except CommonNetworkClientException, e:
            self.logger.error(
                "Quantum Exception while creating policy" + str(e))
        self.logger.info("policy_rsp for policy_id %s after update is %s" %
                         (policy_id, policy_rsp))
        return policy_rsp
    # end update_policy

    def get_policy_if_present(self, project_name=None, policy_name=None):
        policy_rsp = None
        try:
            policy_rsp = self.obj.list_policys()
            for (x, y, z) in [(policy['name'], policy['id'], policy['fq_name']) for policy in policy_rsp['policys']]:
                if policy_name == x:
                    if project_name:
                        if project_name in z:
                            policy_id = y
                            return self.obj.show_policy(policy=policy_id)
                    else:
                        policy_id = y
                        return self.obj.show_policy(policy=policy_id)
        except CommonNetworkClientException, e:
            self.logger.exception(
                "Some exception while doing Quantum policy-listing")
        return None

    # end get_policy_if_present

    def list_policys(self):
        policy_list = None
        try:
            policy_list = self.obj.list_policys()
        except CommonNetworkClientException, e:
            self.logger.error(
                "Quantum Exception while listing policies" + str(e))
        return policy_list
    # end list_policys

    def delete_policy(self, policy_id):
        result = True
        try:
            self.obj.delete_policy(policy_id)
        except CommonNetworkClientException, e:
            result = False
            self.logger.error(
                "Quantum Exception while deleting policy" + str(e))
        return result
    # end delete_policy

    def get_policy_fq_name(self, policy_obj):
        return policy_obj['policy']['fq_name']
    # end get_policy_fq_name

    def update_network(self, vn_id, network_dict):
        net_rsp = None
        try:
            net_rsp = self.obj.update_network(vn_id, network_dict)
        except CommonNetworkClientException, e:
            self.logger.error(
                "Quantum Exception while updating network" + str(e))
        return net_rsp
    # end update_network

    def list_security_groups(self, *args, **kwargs):
        return self.obj.list_security_groups(*args, **kwargs)
    # end


# end QuantumFixture
