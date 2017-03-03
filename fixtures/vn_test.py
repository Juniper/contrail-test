import fixtures
from ipam_test import *
from project_test import *
from tcutils.util import *
from vnc_api.vnc_api import *
from netaddr import *
from time import sleep
from contrail_fixtures import *
import inspect
from common.policy import policy_test_utils
import threading
import sys
from quantum_test import NetworkClientException
from tcutils.test_lib.contrail_utils import get_interested_computes
from cfgm_common.exceptions import PermissionDenied
try:
    from webui_test import *
except ImportError:
    pass

class NotPossibleToSubnet(Exception):

    """Raised when a given network/prefix is not possible to be subnetted to
       required numer of subnets.
    """
    pass
from openstack import OpenstackOrchestrator
from vcenter import VcenterOrchestrator

#@contrail_fix_ext ()
class VNFixture(fixtures.Fixture):

    ''' Fixture to create and verify and delete VNs.

        Deletion of the VN upon exit can be disabled by setting fixtureCleanup=no
        If a VN with the vn_name is already present, it is not deleted upon exit. Use fixtureCleanup=force to force a delete.

        vn_fixture= VNFixture(...)
        vn_fixture.obj      : VN object dict from the stack
        vn_fixture.vn_id    : UUID of the VN
        vn_fixture.vn_name  : Name of the VN
        vn_fixture.vn_fq_name : FQ name of the VN
    '''
    def __init__(self, connections, inputs=None, vn_name=None, policy_objs=[],
                 subnets=[], router_asn='64512', project_name=None,
                 rt_number=None, ipam_fq_name=None, option='quantum',
                 forwarding_mode=None, vxlan_id=None, shared=False,
                 router_external=False, clean_up=True,
                 af=None, empty_vn=False, enable_dhcp=True,
                 dhcp_option_list=None, disable_gateway=False,
                 uuid=None, sriov_enable=False, sriov_vlan=None,
                 sriov_provider_network=None,*args,**kwargs):
        self.connections = connections
        self.inputs = inputs or connections.inputs
        self.logger = self.connections.logger
        self.orchestrator = kwargs.get('orch', self.connections.orch)
        self.quantum_h = self.connections.quantum_h
        self.vnc_lib_h = self.connections.get_vnc_lib_h()
        self.api_s_inspect = self.connections.api_server_inspect
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.analytics_obj = self.connections.analytics_obj
        self.domain_name = self.connections.domain_name
        if self.domain_name == 'Default':
            self.domain_name = 'default-domain'
        self.project_name = project_name or self.connections.project_name
        self.vn_name = vn_name or get_random_name(self.project_name)
        self.project_id = self.connections.get_project_id()
        self.uuid = uuid
        self.obj = None
        self.ipam_fq_name = ipam_fq_name or NetworkIpam().get_fq_name()
        self.policy_objs = self.convert_policy_objs_vnc_to_neutron(policy_objs)
        self.af = self.get_af_from_subnet(subnets=subnets) or af or self.inputs.get_af()
        if self.inputs.get_af() == 'v6' and self.af == 'v4':
            raise v4OnlyTestException("Skipping Test. v4 specific testcase")
        #Forcing v4 subnet creation incase of v6. Reqd for ssh to host
        if ('v6' in self.af) or ('dual' == self.inputs.get_af()):
            self.af = 'dual'
        if isinstance(self.orchestrator,VcenterOrchestrator)  and subnets and (len(subnets) != 1):
           raise Exception('vcenter: Multiple subnets not supported')
        if not subnets and not empty_vn:
            subnets = get_random_cidrs(stack=self.af)
        if subnets and self.get_af_from_subnet(subnets=subnets) == 'v6':
            subnets.extend(get_random_cidrs(stack='v4'))
        #Force add v6 subnet for dual stack testing when only v4 subnet is passed
        if self.af == 'dual' and subnets and self.get_af_from_subnet(subnets=subnets) == 'v4':
            subnets.extend(get_random_cidrs(stack='v6'))
        self.vn_subnets = subnets
        self._parse_subnets()
        if self.inputs.verify_thru_gui():
            self.browser = self.connections.browser
            self.browser_openstack = self.connections.browser_openstack
            self.webui = WebuiTest(self.connections, self.inputs)
        self.router_asn = router_asn
        self.rt_number = rt_number
        self.option = option
        self.forwarding_mode = forwarding_mode
        self.vxlan_id = vxlan_id
        self.shared = shared
        self.router_external = router_external
        self.clean_up = clean_up
        self.lock = threading.Lock()
        self.created = False
        self.verify_is_run = False
        self.verify_result = True
        self.verify_not_in_result = True
        self.api_verification_flag = True
        self.cn_verification_flag = True
        self.policy_verification_flag = None
        self.pol_verification_flag = None
        self.op_verification_flag = True
        self.not_in_agent_verification_flag = True
        self.not_in_api_verification_flag = True
        self.not_in_cn_verification_flag = True
        self.project_obj = None
        self.vn_fq_name = None
        self.enable_dhcp = enable_dhcp
        self.sriov_enable = sriov_enable
        self.sriov_vlan = sriov_vlan
        self.sriov_provider_network = sriov_provider_network
        self.dhcp_option_list = dhcp_option_list
        self.disable_gateway = disable_gateway
        self.vn_port_list=[]
        self.vn_with_route_target = []
        self.ri_ref = None
        self.api_s_routing_instance = None
        self._vrf_ids = {}
        self._interested_computes = []
        self.vn_network_id = None
        self.mac_learning_enabled = kwargs.get('mac_learning_enabled', None)
        self.mac_limit_control = kwargs.get('mac_limit_control', None)
        self.mac_move_control = kwargs.get('mac_move_control', None)
        self.mac_aging_time = kwargs.get('mac_aging_time', None)
        self.pbb_evpn_enable = kwargs.get('pbb_evpn_enable', None)
        self.pbb_etree_enable = kwargs.get('pbb_etree_enable', None)
        self.layer2_control_word = kwargs.get('layer2_control_word', None)
    # end __init__

    def convert_policy_objs_vnc_to_neutron(self, policy_objs):
        objs = list()
        for policy_obj in policy_objs:
            if isinstance(policy_obj, NetworkPolicy):
                dct = {'fq_name': policy_obj.fq_name,
                       'id': policy_obj.uuid,
                       'name': policy_obj.name,
                      }
                objs.append({'policy': dct})
            else:
                objs.append(policy_obj)
        return objs


    def read(self):
        if self.uuid:
            self.obj = self.orchestrator.get_vn_obj_from_id(self.uuid)
            self.api_vn_obj = self.vnc_lib_h.virtual_network_read(id=self.uuid)
            self.vn_name = self.api_vn_obj.name
            self.vn_fq_name = self.api_vn_obj.get_fq_name_str()
            self.fq_name = self.api_vn_obj.get_fq_name()
            ipam = self.api_vn_obj.get_network_ipam_refs()
            if ipam:
                subnets = [x.subnet.ip_prefix+'/'+\
                           str(x.subnet.ip_prefix_len)
                           for x in ipam[0]['attr'].ipam_subnets]
                self.vn_subnets = subnets
                self._parse_subnets()
            else:
                subnets = None
                self.vn_subnets = []
            self.logger.debug('Fetched VN: %s(%s) with subnets %s'
                             %(self.vn_fq_name, self.uuid, subnets))
    # end read

    def get_dns_ip(self, ipam_fq_name = None):
        if not ipam_fq_name:
            ipam_fq_name=self.ipam_fq_name
        self.api_vn_obj = self.vnc_lib_h.virtual_network_read(id=self.uuid)
        ipams = self.api_vn_obj.get_network_ipam_refs()
        if ipams:
            for ipam in ipams:
                if ipam["to"] == ipam_fq_name:
                    dns_server_address = ipam['attr'].ipam_subnets[0].dns_server_address
                    break
                else:
                    dns_server_address = None
            self.logger.debug('DNS IP of IPAM associated with configured VN %s is %s'
                             %(self.vn_fq_name, dns_server_address))
        if not dns_server_address:
            self.logger.error("DNS server for mentioned IPAM not found.")
        return dns_server_address

    def get_uuid(self):
        return self.uuid

    @property
    def vn_id(self):
        return self.get_uuid()

    def get_vrf_name(self):
        return self.vn_fq_name + ':' + self.vn_name

    def get_vrf_ids(self, refresh=False):
        if not getattr(self, '_vrf_ids', None) or refresh:
            vrf_id_dict = {}
            for ip in self.inputs.compute_ips:
                inspect_h = self.agent_inspect[ip]
                vrf_id = inspect_h.get_vna_vrf_id(self.vn_fq_name)
                if vrf_id:
                    vrf_id_dict.update({ip:vrf_id})
            self._vrf_ids = vrf_id_dict
        return self._vrf_ids
	# end get_vrf_ids

    @property
    def vrf_ids(self):
        return self.get_vrf_ids()

    def get_vrf_id(self, node_ip, refresh=False):
        vrf_ids = self.get_vrf_ids(refresh=refresh)
        if vrf_ids.get(node_ip):
            return vrf_ids.get(node_ip)
    # end get_vrf_id

    @property
    def interested_computes(self):
        return self.get_interested_computes()

    def get_interested_computes(self, refresh=False):
        ''' Query control node to get a list of compute nodes
            interested in the VNs vrf
        '''
        if getattr(self, '_interested_computes', None) and not refresh:
            return self._interested_computes
        self._interested_computes = get_interested_computes(self.connections,
                                                            [self.vn_fq_name])
        return self._interested_computes
    # end get_interested_computes

    @property
    def ri_name(self):
        return self.get_vrf_name()

    @property
    def vrf_name(self):
        return self.get_vrf_name()

    def _parse_subnets(self):
        # If the list is just having cidrs
        if self.vn_subnets and (type(self.vn_subnets[0]) is str or
                                type(self.vn_subnets[0]) is unicode):
            self.vn_subnets = [{'cidr': x} for x in self.vn_subnets]
    # end _parse_subnets

    def get_cidrs(self, af=None):
        subnets = [x['cidr'] for x in self.vn_subnets]
        if af == 'dual':
            return subnets
        if self.af == 'dual' and self.inputs.get_af() == 'v6':
            af = 'v6'
        if not af:
            return subnets
        return [x for x in subnets if af == get_af_type(x)]

    def get_name(self):
        return self.vn_name

    def get_vn_fq_name(self):
        return self.vn_fq_name

    def get_af_from_subnet(self, subnets):
        af = None
        if subnets:
           if type(subnets[0]) is dict:
               subnets = [subnet['cidr'] for subnet in subnets]
           af = get_af_from_cidrs(cidrs= subnets)
        return af

    def _create_vn_orch(self):
        try:
            self.obj = self.orchestrator.get_vn_obj_if_present(self.vn_name,
                                         project_id=self.project_id)
            if not self.obj:
                self.obj = self.orchestrator.create_vn(
                                                self.vn_name,
                                                self.vn_subnets,
                                                ipam_fq_name=self.ipam_fq_name,
                                                shared=self.shared,
                                                router_external=self.router_external,
                                                enable_dhcp=self.enable_dhcp,
                                                sriov_enable=self.sriov_enable,
                                                sriov_vlan=self.sriov_vlan,
                                                sriov_provider_network=self.sriov_provider_network,
                                                disable_gateway=self.disable_gateway)
                if self.obj:
                    self.logger.info('Created VN %s' %(self.vn_name))
                    self.created = True #Introducing this flag to make sure if
                                        #vn was created by this fixture object,
                                        #delete it on cleanup.
            else:
                self.logger.debug('VN %s already present, not creating it' %
                                  (self.vn_name))
                self.created = False

            # It is possible that VN may not be created due to quota limits
            # In such cases, self.obj would not be set
            if self.obj:
                self.uuid = self.orchestrator.get_vn_id(self.obj)
                self.vn_fq_name = ':'.join(
                    self.vnc_lib_h.id_to_fq_name(self.uuid))
                self.api_vn_obj = self.vnc_lib_h.virtual_network_read(id=self.uuid)
                self.logger.debug('VN %s UUID is %s' % (self.vn_name, self.uuid))
                return True
        except NetworkClientException as e:
            with self.lock:
                self.logger.exception(
                    "Got exception as %s while creating %s" % (e, self.vn_name))
            # We shall retry if it is Service Unavailable
            if '503' in str(e) or '504' in str(e):
                return False
            raise NetworkClientException(message=str(e))

    def get_vn_list_in_project(self, project_uuid):

        return self.vnc_lib_h.virtual_networks_list(parent_id=project_uuid)

    def verify_if_vn_already_present(self, vn_obj, project):

        to_be_created_vn_fq_name = vn_obj.get_fq_name()
        vn_list = self.get_vn_list_in_project(project.uuid)
        if not vn_list:
            return False
        else:
            for elem in vn_list['virtual-networks']:
                if(elem['fq_name'] == to_be_created_vn_fq_name):
                    return True
                else:
                    continue
        return False

    def get_vn_uid(self, vn_obj, project_uuid):

        uid = None
        try:
            to_be_created_vn_fq_name = vn_obj.get_fq_name()
            vn_list = self.get_vn_list_in_project(project_uuid)
            for elem in vn_list['virtual-networks']:
                if(elem['fq_name'] == to_be_created_vn_fq_name):
                    uid = elem['uuid']
        except Exception as e:
            self.logger.exception("API exception %s" % (e))
        finally:
            return uid

    def _create_vn_api(self, vn_name, project_obj):
        if isinstance(self.orchestrator,VcenterOrchestrator) :
           raise Exception('vcenter: no support for VN creation through VNC-api')
        try:
            self.api_vn_obj = VirtualNetwork(
                name=vn_name, parent_obj=project_obj)
            if not self.verify_if_vn_already_present(self.api_vn_obj, project_obj):
                if self.shared:
                    self.api_vn_obj.is_shared = self.shared
                self.uuid = self.vnc_lib_h.virtual_network_create(
                    self.api_vn_obj)
                with self.lock:
                    self.logger.info("Created VN %s, UUID :%s" % (self.vn_name,
                        self.uuid))
                self.created = True
            else:
                with self.lock:
                    self.logger.debug("VN %s already present" % (self.vn_name))
                self.uuid = self.get_vn_uid(
                    self.api_vn_obj, project_obj.uuid)
                self.created = False
            ipam = self.vnc_lib_h.network_ipam_read(
                fq_name=self.ipam_fq_name)
            ipam_sn_lst = []
            # The dhcp_option_list and enable_dhcp flags will be modified for all subnets in an ipam
            for net in self.vn_subnets:
                network, prefix = net['cidr'].split('/')
                ipam_sn = IpamSubnetType(
                    subnet=SubnetType(network, int(prefix)))
                if self.dhcp_option_list:
                   ipam_sn.set_dhcp_option_list(DhcpOptionsListType(params_dict=self.dhcp_option_list))
                if not self.enable_dhcp:
                   ipam_sn.set_enable_dhcp(self.enable_dhcp)
                ipam_sn_lst.append(ipam_sn)
            self.api_vn_obj.add_network_ipam(ipam, VnSubnetsType(ipam_sn_lst))
            self.vnc_lib_h.virtual_network_update(self.api_vn_obj)
            self.vn_fq_name = self.api_vn_obj.get_fq_name_str()
        except PermissionDenied:
            self.logger.info('Permission denied to create VirtualNetwork')
            raise
        except Exception as e:
            with self.lock:
                self.logger.exception(
                    'Api exception while creating network %s' % (self.vn_name))
        self.obj = self.orchestrator.get_vn_obj_from_id(self.uuid)
        if self.obj is None:
            raise ValueError('could not find %s in neutron/quantum' % (self.vn_name))

    def get_api_obj(self):
        return self.api_vn_obj

    def getObj(self):
        return self.api_vn_obj

    def setUp(self):
        super(VNFixture, self).setUp()
        self.create()

    def create(self):
        self.project_obj = self.connections.vnc_lib_fixture.get_project_obj()
        if self.uuid:
            return self.read()
        if self.inputs.is_gui_based_config():
            self.webui.create_vn(self)
        elif (self.option == 'contrail'):
            self._create_vn_api(self.vn_name, self.project_obj)
        else:
            self._create_vn_orch()
        if not self.obj:
             self.logger.debug('VN %s not present' % (self.vn_name))
             return

        # Bind policies if any
        if self.policy_objs:
            if isinstance(self.policy_objs[0], NetworkPolicy):
                policy_fq_names = [obj.fq_name for obj in self.policy_objs]
            else:
                policy_fq_names = [
                   self.quantum_h.get_policy_fq_name(x) for x in self.policy_objs]
            self.bind_policies(policy_fq_names, self.uuid)
        else:
            # Update self.policy_objs to pick acls which are already
            # bound to the VN
            if self.obj:
                self.update_vn_object()
        # end if

        # Configure route target
        if self.rt_number is not None:
            self.add_route_target()
            self.vn_with_route_target.append(self.uuid)

        # Configure forwarding mode
        if self.forwarding_mode is not None:
            self.add_forwarding_mode(
                self.project_obj.fq_name, self.vn_name, self.forwarding_mode)

        # Configure vxlan_id
        if self.vxlan_id is not None:
            self.set_vxlan_id()

        # Populate the VN Subnet details
        if isinstance(self.orchestrator,OpenstackOrchestrator):
            self.vn_subnet_objs = self.quantum_h.get_subnets_of_vn(self.uuid)
    # end setUp

    def create_subnet(self, vn_subnet, ipam_fq_name):
        if isinstance(self.orchestrator,VcenterOrchestrator) :
            raise Exception('vcenter: subnets not supported')
        self.quantum_h.create_subnet(vn_subnet, self.uuid, ipam_fq_name)
        self.vn_subnets.append([{'cidr': vn_subnet}])

    def create_subnet_af(self, af, ipam_fq_name):
        if 'v4' in af or 'dual' in af:
            self.create_subnet(vn_subnet= get_random_cidr(af='v4'),
                               ipam_fq_name= ipam_fq_name)
        if 'v6' in af or 'dual' in af:
            self.create_subnet(vn_subnet= get_random_cidr(af='v6'),
                               ipam_fq_name= ipam_fq_name)

    def create_port(self, net_id, subnet_id=None, ip_address=None,
                    mac_address=None, no_security_group=False,
                    security_groups=[], extra_dhcp_opts=None, sriov=False):
        if isinstance(self.orchestrator,VcenterOrchestrator) :
            raise Exception('vcenter: ports not supported')
        fixed_ips = [{'subnet_id': subnet_id, 'ip_address': ip_address}]
        port_rsp = self.quantum_h.create_port(
            net_id,
            fixed_ips,
            mac_address,
            no_security_group,
            security_groups,
            extra_dhcp_opts,
            sriov)
        self.vn_port_list.append(port_rsp['id'])
        return port_rsp

    def delete_port(self, port_id, quiet=False):
        if isinstance(self.orchestrator,VcenterOrchestrator) :
            raise Exception('vcenter: ports not supported')
        is_port_present=self.quantum_h.get_port(port_id)
        if is_port_present is not None:
            self.quantum_h.delete_port(port_id)

    def update_port(self, port_id, port_dict):
        if isinstance(self.orchestrator,VcenterOrchestrator) :
            raise Exception('vcenter: ports not supported')
        port_rsp = self.quantum_h.update_port(port_id, port_dict)
        return port_rsp

    def verify_on_setup_without_collector(self):
        # once api server gets restarted policy list for vn in not reflected in
        # vn uve so removing that check here
        result = True
        if not self.verify_vn_in_api_server():
            result = result and False
            self.logger.error(
                "One or more verifications in API Server for VN %s failed" % (self.vn_name))
        if not self.verify_vn_in_control_nodes():
            result = result and False
            self.logger.error(
                "One or more verifications in Control-nodes for VN %s failed" % (self.vn_name))
        if not self.verify_vn_policy_in_api_server():
            result = result and False
            self.logger.error(ret['msg'])
        if not self.verify_vn_in_opserver():
            result = result and False
            self.logger.error(
                "One or more verifications in OpServer for VN %s failed" % (self.vn_name))

        self.verify_is_run = True
        self.verify_result = result
        return result

    def verify_on_setup(self):
        result = True
        if not self.verify_vn_in_api_server():
            result = result and False
            self.logger.error(
                "One or more verifications in API Server for VN %s failed" % (self.vn_name))
            return result
        if not self.verify_vn_in_control_nodes():
            result = result and False
            self.logger.error(
                "One or more verifications in Control-nodes for VN %s failed" % (self.vn_name))
            return result
        if not self.verify_vn_policy_in_api_server():
            result = result and False
            self.logger.error(ret['msg'])
        if not self.verify_vn_in_opserver():
            result = result and False
            self.logger.error(
                "One or more verifications in OpServer for VN %s failed" % (self.vn_name))
            return result
        if self.inputs.verify_thru_gui():
            self.webui.verify_vn(self)
        if self.policy_objs:
            self.verify_vn_policy_in_vn_uve()
        if not self.policy_verification_flag['result']:
            result = result and False
            self.logger.error(
                "One or more verifications of policy for VN %s failed" % (self.vn_name))
        if self.policy_objs:
            if not self.pol_verification_flag:
                result = result and False
                self.logger.error("Attached policy not shown in vn uve %s" %
                                 (self.vn_name))
        if not self.verify_vn_in_agent():
            result = result and False
            self.logger.error('One or more verifications in agent for VN %s'
                'failed' % (self.vn_name))

        self.verify_is_run = True
        self.verify_result = result
        return result
    # end verify

    @retry(delay=5, tries=10)
    def verify_vn_in_api_server(self):
        """ Checks for VN in API Server.

        False If VN Name is not found
        False If all Subnet prefixes are not found
        """
        self.api_verification_flag = True
        self.api_s_vn_obj = self.api_s_inspect.get_cs_vn(
            domain=self.domain_name, project=self.project_name,
            vn=self.vn_name, refresh=True)
        if not self.api_s_vn_obj:
            self.logger.debug("VN %s is not found in API-Server" %
                             (self.vn_name))
            self.api_verification_flag = self.api_verification_flag and False
            return False
        if self.api_s_vn_obj['virtual-network']['uuid'] != self.uuid:
            self.logger.warn(
                "VN Object ID %s in API-Server is not what was created" % (self.uuid))
            self.api_verification_flag = self.api_verification_flag and False
            return False

        subnets = self.api_s_vn_obj[
            'virtual-network']['network_ipam_refs'][0]['attr']['ipam_subnets']
        for vn_subnet in self.vn_subnets:
            subnet_found = False
            vn_subnet_cidr = str(IPNetwork(vn_subnet['cidr']).ip)
            for subnet in subnets:
                if subnet['subnet']['ip_prefix'] == vn_subnet_cidr:
                    subnet_found = True
            if not subnet_found:
                self.logger.warn(
                    "VN Subnet IP %s not found in API-Server for VN %s" %
                    (vn_subnet_cidr, self.vn_name))
                self.api_verification_flag = self.api_verification_flag and False
                return False
        # end for
        self.api_s_route_targets = self.api_s_inspect.get_cs_route_targets(
            vn_id=self.uuid)
        if not self.api_s_route_targets:
            errmsg = "Route targets not yet found in API-Server for VN %s" % self.vn_name
            self.logger.error(errmsg)
            self.api_verification_flag = self.api_verification_flag and False
            return False
        self.rt_names = self.api_s_inspect.get_cs_rt_names(
            self.api_s_route_targets)

        if not self.rt_names:
            self.logger.debug(
                'RT names not yet present for VN %s', self.vn_name)
            return False

        if self.rt_number:
            if not any(item.endswith(self.rt_number) for item in self.rt_names):
                self.logger.debug('RT %s is not found in API Server RT list %s ' %(
                    self.rt_number, self.rt_names))
                self.api_verification_flag = self.api_verification_flag and False
                return False

        self.api_s_routing_instance = self.api_s_inspect.get_cs_routing_instances(
            vn_id=self.uuid)
        if not self.api_s_routing_instance:
            msg = "Routing Instances not found in API-Server for VN %s" % self.vn_name
            self.logger.warn(msg)
            self.api_verification_flag = self.api_verification_flag and False
            return False
        self.ri_ref = self.api_s_routing_instance['routing_instances'][0]['routing-instance']
        if not self.verify_network_id():
            return False
        self.api_verification_flag = self.api_verification_flag and True
        self.logger.info("Verifications in API Server for VN %s passed" %
                         (self.vn_name))
        return True
    # end verify_vn_in_api_server

    def verify_network_id(self):
        ''' Verify basic VN network id allocation
            Currently just checks if it is not 0
        '''
        self.api_vn_obj = self.vnc_lib_h.virtual_network_read(id=self.uuid)
        self.vn_network_id = getattr(self.api_vn_obj, 'virtual_network_network_id', None)
        if not self.vn_network_id:
            self.logger.warn('VN id not seen in api-server for Vn %s' %(
                self.vn_id))
            return False
        if int(self.vn_network_id) == int(0):
            self.logger.warn('VN id for Vn %s is set to 0. This is incorrect' %(
                self.vn_network_id))
            return False
        self.logger.info('Verified VN network id %s for VN %s' % (
            self.vn_network_id, self.vn_id))
        return True
    # end verify_network_id

    @retry(delay=5, tries=10)
    def verify_vn_policy_in_vn_uve(self):
        ''' verify VN's policy name in vn uve'''
        result = True
        # Expectation for this verification is not valid anymore with
        # multi-cfgm, skipping this verification
        self.pol_verification_flag = result
        return result
        try:
            for ip in self.inputs.collector_ips:
                self.policy_in_vn_uve = self.analytics_obj.get_vn_uve_attched_policy(
                    ip, vn_fq_name=self.vn_fq_name)
                self.logger.debug("Attached policy in vn %s uve %s" %
                                 (self.vn_name, self.policy_in_vn_uve))
                policy_list = []
                for elem in self.policy_objs:
                    policy = elem['policy']['fq_name']
                    policy_name = str(policy[0]) + ':' + \
                        (str(policy[1])) + ':' + (str(policy[2]))
                    policy_list.append(policy_name)
                for pol in policy_list:
                    if pol in self.policy_in_vn_uve:
                        result = result and True
                    else:
                        result = result and False
        except Exception as e:
            self.logger.exception('Got exception as %s' % (e))
            result = result and False
        finally:
            self.pol_verification_flag = result
            return result

    def verify_vn_policy_not_in_vn_uve(self):
        ''' verify VN's policy name not in vn uve'''
        result = True
        # Expectation for this verification is not valid anymore with
        # multi-cfgm, skipping this verification
        self.pol_verification_flag = result
        return result
        for ip in self.inputs.collector_ips:
            self.policy_in_vn_uve = self.analytics_obj.get_vn_uve_attched_policy(
                ip, vn_fq_name=self.vn_fq_name)
            if self.policy_in_vn_uve:
                self.logger.debug("Attached policy not deleted in vn %s uve" %
                                 (self.vn_name))
                result = result and False
            else:
                result = result and True
        return result

    def get_policy_attached_to_vn(self):
        vn_policys = []
        for p in self.policy_objs:
            vn_policys.append(p['policy']['name'])
        return vn_policys

    def get_allowed_peer_vns_by_policy(self):
        ''' This is allowed list and not actual peer list, which is based on action by both peers'''
        pol_name_list = []
        allowed_peer_vns = []
        vn = self.vnc_lib_h.virtual_network_read(id=self.uuid)
        if vn:
            pol_list_ref = vn.get_network_policy_refs()
            if pol_list_ref:
                for pol in pol_list_ref:
                    pol_name_list.append(str(pol['to'][2]))
        if pol_name_list:
            for pol in pol_name_list:
                pol_object = self.api_s_inspect.get_cs_policy(
                    domain=self.domain_name, project=self.project_name, policy=pol, refresh=True)
                pol_rules = pol_object[
                    'network-policy']['network_policy_entries']['policy_rule']
                self.logger.debug(
                    "vn: %s, inspecting following rules for route verification: %s" %
                    (self.vn_fq_name, pol_rules))
                for rule in pol_rules:
                    # Only for those rules, where local vn is listed, pick the peer...
                    # Also, local vn can appear as source or dest vn
                    rule_vns = []
                    src_vn = rule['src_addresses'][0][
                        'virtual_network']
                    rule_vns.append(src_vn)
                    dst_vn = rule['dst_addresses'][0][
                        'virtual_network']
                    rule_vns.append(dst_vn)
                    if self.vn_fq_name in rule_vns:
                        rule_vns.remove(self.vn_fq_name)
                        # Consider peer VN route only if the action is set to
                        # pass
                        if rule['action_list']['simple_action'] == 'pass':
                            self.logger.debug(
                                "Local VN: %s, Peer VN %s is a valid peer" % (self.vn_fq_name, rule_vns[0]))
                            allowed_peer_vns.append(rule_vns[0])
                        else:
                            self.logger.debug("Local VN: %s, skip route to VN %s as the action is not set to allow" % (
                                self.vn_fq_name, rule_vns[0]))
                    elif 'any' in rule_vns:
                        if rule['action_list']['simple_action'] == 'pass':
                            self.logger.debug(
                                "any VN is a valid pair for this vn %s" % (self.vn_fq_name))
                            allowed_peer_vns.append('any')
                    else:
                        self.logger.debug(
                            "Local VN: %s, skip the VNs in this rule as the local VN is not listed & the rule is a no-op: %s" %
                            (self.vn_fq_name, rule_vns))
        return allowed_peer_vns

    def verify_vn_policy_in_api_server(self):
        ''' verify VN's policy data in api-server with data in quantum database'''
        if isinstance(self.orchestrator,VcenterOrchestrator) :
            self.policy_verification_flag = {'result': True, 'msg': None}
            return self.policy_verification_flag

        me = inspect.getframeinfo(inspect.currentframe())[2]
        result = True
        err_msg = []
        out = None
        self.logger.debug(
            "====Verifying policy data for %s in API_Server ======" %
            (self.vn_name))
        self.api_s_vn_obj = self.api_s_inspect.get_cs_vn(
            domain=self.domain_name, project=self.project_name,
            vn=self.vn_name, refresh=True)
        try:
            vn_pol = self.api_s_vn_obj[
                'virtual-network']['network_policy_refs']
        except:
            self.logger.debug("=>VN %s has no policy to be verified" %
                              (self.vn_name))
            self.policy_verification_flag = {'result': result, 'msg': err_msg}
            return {'result': result, 'msg': err_msg}

        # vn_pol is a list of dicts with policy info
        # check no. of policies in api-s and quantum db for vn
        if len(vn_pol) != len(self.policy_objs):
            msg = "VN: " + self.vn_name + \
                ", No. of policies not same between api-s and quantum db"
            self.logger.error(msg)
            err_msg.append(msg)
            self.logger.debug("Data in API-S: \n")
            for policy in vn_pol:
                self.logger.debug('%s, %s' % (policy['to'], policy['uuid']))
            self.logger.debug("Data in Neutron: \n")
            for policy in self.policy_objs:
                self.logger.debug('%s, %s' %
                                  (policy['policy']['id'], policy['policy']['fq_name']))

        # Compare attached policy_fq_names & uuid's
        for policy in vn_pol:
            fqn = policy['to']
            id = policy['uuid']
            self.logger.debug(
                "==>Verifying data for policy with id: %s, fqn: %s" % (id, fqn))
            # check if policy with this id exists in quantum
            d = policy_test_utils.get_dict_with_matching_key_val(
                'id', id, self.policy_objs, 'policy')
            if d['state'] == None:
                err_msg.append(d['ret'])
            else:
                out = policy_test_utils.compare_args(
                    'policy_fqn', fqn, d['ret']['policy']['fq_name'],
                    logger=self.logger)
                if out:
                    err_msg.append(out)

        if err_msg:
            result = False
            err_msg.insert(0, me + ":" + self.vn_name)
        self.logger.info("VN %s Policy verification: %s, status: %s" % (
            self.vn_name, me, result))
        self.policy_verification_flag = {'result': result, 'msg': err_msg}
        return {'result': result, 'msg': err_msg}

   # end verify_vn_policy_in_api_server

    @retry(delay=5, tries=3)
    def verify_vn_not_in_api_server(self):
        '''Verify that VN is removed in API Server.

        '''
        if self.api_s_inspect.get_cs_ri_by_id(self.ri_ref['uuid']):
            self.logger.warn("RI %s is still found in API-Server" % self.ri_ref['name'])
            self.not_in_api_verification_flag = False
            return False
        if self.api_s_inspect.get_cs_vn(domain=self.domain_name, 
                                        project=self.project_name, 
                                        vn=self.vn_name, refresh=True):
            self.logger.debug("VN %s is still found in API-Server" %
                             (self.vn_name))
            self.not_in_api_verification_flag = False
            return False
        self.logger.info("Validated that VN %s is not found in API Server" % (
            self.vn_name))
        self.not_in_api_verification_flag = True
        return True
    # end verify_vn_not_in_api_server

    @retry(delay=5, tries=25)
    def verify_vn_in_agent(self):
        # No real verification for now, collect vrfs so that they can be
        # verified during cleanup
        self.get_vrf_ids(refresh=True)
        if not self.vrf_ids:
            self.logger.debug('Do not have enough data to verify VN in agent')
        self.logger.debug('VRF ids for VN %s: %s' % (self.vn_name,
                                                     self.vrf_ids))
        if self.inputs.many_computes:
            self.get_interested_computes(refresh=True)
        return True
    # end verify_vn_in_agent

    @retry(delay=5, tries=25)
    def verify_vn_in_control_nodes(self):
        """ Checks for VN details in Control-nodes.

        False if RT does not match the RT from API-Server for each of control-nodes
        """
        self.api_s_route_targets = self.api_s_inspect.get_cs_route_targets(
            vn_id=self.uuid)

        self.cn_verification_flag = True
        for cn in self.inputs.bgp_ips:
            cn_config_vn_obj = self.cn_inspect[cn].get_cn_config_vn(
                vn_name=self.vn_name, project=self.project_name, domain=self.domain_name)
            if not cn_config_vn_obj:
                self.logger.warn('Control-node %s does not have VN %s info ' %
                                 (cn, self.vn_name))
                self.cn_verification_flag = self.cn_verification_flag and False
                return False
            self.logger.debug("Control-node %s : VN object is : %s" %
                              (cn, cn_config_vn_obj))
            if self.vn_fq_name not in cn_config_vn_obj['node_name']:
                self.logger.debug(
                    'IFMAP View of Control-node does not yet have the VN detail',
                    ' of %s' % (self.vn_fq_name))
                self.cn_verification_flag = self.cn_verification_flag and False
                return False
            # TODO UUID verification to be done once the API is available
            cn_object = self.cn_inspect[
                cn].get_cn_routing_instance(ri_name=self.ri_name)
            if not cn_object:
                self.logger.debug(
                    'No Routing Instance found in CN %s with name %s' %
                    (cn, self.ri_name))
                self.cn_verification_flag = self.cn_verification_flag and False
                return False
            try:
                rt_names = self.api_s_inspect.get_cs_rt_names(
                    self.api_s_route_targets)
                if cn_object['export_target'][0] not in rt_names:
                    self.logger.debug(
                        "Route target %s for VN %s is not found in Control-node %s" %
                        (rt_names, self.vn_name, cn))
                    self.cn_verification_flag = self.cn_verification_flag and False
                    return False
            except Exception as e:
                self.logger.exception(
                    "Got exception from control node verification as %s" % (e))
                self.cn_verification_flag = self.cn_verification_flag and False
                return False
        # end for
        self.logger.info(
            'On all control nodes, Config, RI and RT verification for VN %s '
            'passed' % (self.vn_name))
        self.cn_verification_flag = self.cn_verification_flag and True
        return True
    # end verify_vn_in_control_node

    def verify_vn_policy_not_in_api_server(self, policy_name):
        ''' verify VN's policy data in removed api-server'''
        self.logger.debug(
            "====Verifying policy %s data removed from %s in API_Server ======" %
            (policy_name, self.vn_name))
        found = False

        # Get VN object from API Server
        vn = self.vnc_lib_h.virtual_network_read(id=self.uuid)
        # Get the policy list from VN
        pol_ref = vn.get_network_policy_refs()

        if not pol_ref:
            self.logger.info("=> VN %s has no reference policys" %
                             (self.vn_name))
            return found
        # If we have more policies with VN and iterate it.
        for pol in pol_ref:
            policy = self.vnc_lib_h.network_policy_read(id=pol['uuid'])
            if (str(policy.name) == policy_name):
                found = True
                self.logger.debug("Policy info is found in API-Server")
                break
        if not found:
            self.logger.debug("Policy info is not found in API-Server")
        return found
    # end verify_vn_policy_not_in_api_server

    @retry(delay=5, tries=20)
    def verify_vn_not_in_control_nodes(self):
        '''Verify that VN details are not in any Control-node

        '''
        result = True
        self.not_in_cn_verification_flag = True
        for cn in self.inputs.bgp_ips:
            cn_object = self.cn_inspect[
                cn].get_cn_routing_instance(ri_name=self.ri_name)
            if cn_object:
                self.logger.debug(
                    "Routing instance for VN %s is still found in Control-node %s" % (self.vn_name, cn))
                result = result and False
                self.not_in_cn_verification_flag = result
        # end for
        if self.cn_inspect[cn].get_cn_config_vn(vn_name=self.vn_name,
                                project=self.project_name, domain=self.domain_name):
            self.logger.debug("Control-node config DB still has VN %s" %
                             (self.vn_name))
            result = result and False
            self.not_in_cn_verification_flag = result

        if result:
            self.logger.info(
                "Validated that Routing instances and Config db in "\
                "Control-nodes does not have VN %s info" % (self.vn_name))
        return result
    # end verify_vn_not_in_control_nodes

    @retry(delay=2, tries=20)
    def verify_vn_not_in_vrouter(self):
        ''' Validate that route table is deleted in  local vrouter
        '''
        compute_ips = self.inputs.compute_ips
        # If large number of compute nodes, try to query less number of them
        if self.inputs.many_computes:
            compute_ips = self.interested_computes
        if not compute_ips:
            self.logger.debug('No interested compute node info present.'
                              ' Skipping VN cleanup check in vrouter')
            return True
        for compute_ip in compute_ips:
            if not compute_ip in self.vrf_ids.keys():
                continue
            inspect_h = self.agent_inspect[compute_ip]
            vrf_id = self.vrf_ids[compute_ip]
            # Check again if agent does not have this vrf by chance
            curr_vrf = inspect_h.get_vna_vrf_by_id(vrf_id)
            if curr_vrf:
                if curr_vrf.get('name') == self.vrf_name:
                    self.logger.warn('VRF %s is still seen in agent %s' % (
                        curr_vrf, compute_ip))
                    return False
                else:
                    self.logger.info('VRF id %s already used by some other vrf '
                        '%s, will have to skip vrouter verification on %s' %(
                        vrf_id, curr_vrf.get('name'), compute_ip))
                    return True
                # endif
            else:
                self.logger.debug('VRF %s is not seen in agent %s' % (vrf_id,
                                   compute_ip))

            # Agent has deleted this vrf. Check in kernel too that it is gone
            vrouter_route_table = inspect_h.get_vrouter_route_table(
                    vrf_id)
            if vrouter_route_table:
                self.logger.warn('Vrouter on Compute node %s still has vrf '
                    ' %s for VN %s. Check introspect logs' %(
                        compute_ip, vrf_id,self.vn_name))
                return False
            self.logger.debug('Vrouter %s does not have vrf %s for VN %s' %(
                compute_ip, vrf_id, self.vn_name))
        # endif
        self.logger.info('Validated that all vrouters do not '
            ' have the route table for VN %s' %(self.vn_fq_name))
        return True
    # end verify_vn_not_in_vrouter

    @retry(delay=5, tries=30)
    def verify_vn_not_in_agent(self):
        ''' Verify that VN is removed in all agent nodes.
        '''
        for compute_ip in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[compute_ip]
            vn = inspect_h.get_vna_vn(
                domain=self.domain_name, project=self.project_name, vn_name=self.vn_name)
            if vn:
                self.logger.debug('VN %s is still found in %s ' %
                                 (self.vn_name, compute_ip))
                return False
                self.not_in_agent_verification_flag = False
            vrf_objs = inspect_h.get_vna_vrf_objs(
                domain=self.domain_name, project=self.project_name, vn_name=self.vn_name)
            if len(vrf_objs['vrf_list']) != 0:
                self.logger.debug(
                    'VRF %s for VN %s is still found in agent %s' %
                    (str(self.ri_name), self.vn_name, compute_ip))
                self.not_in_agent_verification_flag = False
                return False
            self.logger.debug('VN %s is not present in Agent %s ' %
                             (self.vn_name, compute_ip))

            # Check in vrouter that route table for the vrf is empty
        # end for
        self.not_in_agent_verification_flag = True
        self.logger.info('Validated that VN %s is not in any agent' % (
            self.vn_name))
        return True
    # end verify_vn_not_in_agent

    def verify_vn_in_opserver(self):
        '''Verify vn in the opserver'''

        self.logger.debug("Verifying the vn in opserver")
        res = self.analytics_obj.verify_vn_link(self.vn_fq_name)
        self.op_verification_flag = res
        return res

    def del_host_route(self, prefix):
        prefix = [prefix] if type(prefix) is str else prefix
        self.del_host_routes(prefixes=[prefix])
    # end del_host_route

    def del_host_routes(self, prefixes):
        vnc_lib = self.vnc_lib_h
        self.logger.info('Deleting %s from host_routes via %s in %s' %
                         (prefixes, self.ipam_fq_name[-1], self.vn_name))
        vn_obj = vnc_lib.virtual_network_read(
            fq_name=self.vn_fq_name.split(':'))
        for subnet in vn_obj.get_network_ipam_refs()[0]['attr'].get_ipam_subnets():
            for prefix in prefixes:
                if IPNetwork(subnet.subnet.ip_prefix).version == IPNetwork(prefix).version:
                    subnet.get_host_routes().delete_route(RouteTableType(RouteType(prefix)))
        vn_obj._pending_field_updates.add('network_ipam_refs')
        vnc_lib.virtual_network_update(vn_obj)
    # end delete_host_routes

    def add_host_route(self, prefix):
        prefix = [prefix] if type(prefix) is str else prefix
        self.add_host_routes(prefixes=[prefix])
    # end add_host_route

    def add_host_routes(self, prefixes):
        vnc_lib = self.vnc_lib_h
        self.logger.info('Adding %s as host_route via %s in %s' %
                         (prefixes, self.ipam_fq_name[-1], self.vn_name))
        vn_obj = vnc_lib.virtual_network_read(
            fq_name=self.vn_fq_name.split(':'))
        for subnet in vn_obj.get_network_ipam_refs()[0]['attr'].get_ipam_subnets():
            list_of_prefix = []
            for prefix in prefixes:
                if IPNetwork(subnet.subnet.ip_prefix).version == IPNetwork(prefix).version:
                    list_of_prefix.append(RouteType(prefix=prefix, next_hop=subnet.default_gateway))
            subnet.set_host_routes(RouteTableType(list_of_prefix))
        vn_obj._pending_field_updates.add('network_ipam_refs')
        vnc_lib.virtual_network_update(vn_obj)
    # end add_host_routes

    def add_route_target(self, routing_instance_name=None, router_asn=None,
            route_target_number=None):
        routing_instance_name = routing_instance_name or self.ri_name
        router_asn = router_asn or self.router_asn
        route_target_number = route_target_number or self.rt_number
        vnc_lib = self.vnc_lib_h

        rt_inst_fq_name = routing_instance_name.split(':')
        rtgt_val = "target:%s:%s" % (router_asn, route_target_number)
        net_obj = vnc_lib.virtual_network_read(fq_name=rt_inst_fq_name[:-1])
        route_targets = net_obj.get_route_target_list()
        if route_targets and (rtgt_val not in route_targets.get_route_target()):
            route_targets.add_route_target(rtgt_val)
        else:
            route_targets = RouteTargetList([rtgt_val])
        net_obj.set_route_target_list(route_targets)

        vnc_lib.virtual_network_update(net_obj)
    # end add_route_target

    def del_route_target(self, routing_instance_name=None, router_asn=None,
            route_target_number=None):

        result = True
        routing_instance_name = routing_instance_name or self.ri_name
        router_asn = router_asn or self.router_asn
        route_target_number = route_target_number or self.rt_number
        vnc_lib = self.vnc_lib_h

        rt_inst_fq_name = routing_instance_name.split(':')
        rtgt_val = "target:%s:%s" % (router_asn, route_target_number)
        net_obj = vnc_lib.virtual_network_read(fq_name=rt_inst_fq_name[:-1])

        if rtgt_val not in net_obj.get_route_target_list().get_route_target():
            self.logger.error("%s not configured for VN %s" %
                              (rtgt_val, rt_inst_fq_name[:-1]))
            result = False
#        net_obj.get_route_target_list().get_route_target().remove(rtgt_val)
        route_targets = net_obj.get_route_target_list()
        route_targets.delete_route_target(rtgt_val)
        if route_targets.get_route_target():
            net_obj.set_route_target_list(route_targets)
        else:
            net_obj.set_route_target_list(None)
        vnc_lib.virtual_network_update(net_obj)
        return result
    # end del_route_target

    def verify_vn_route_target(self, policy_peer_vns):
        ''' For expected rt_import data, we need to inspect policy attached to both the VNs under test..
        Both VNs need to have rule in policy with action as pass to other VN..
        This data needs to come from calling test code as policy_peer_vns'''
        self.logger.debug("Verifying RT for vn %s, RI name is %s" %
                         (self.vn_fq_name, self.ri_name))
        self.policy_peer_vns = policy_peer_vns
        compare = False
        for i in range(len(self.inputs.bgp_ips)):
            cn = self.inputs.bgp_ips[i]
            self.logger.debug("Checking VN RT in control node %s" % cn)
            cn_ref = self.cn_inspect[cn]
            vn_ri = cn_ref.get_cn_routing_instance(ri_name=self.ri_name)
            act_rt_import = vn_ri['import_target']
            act_rt_export = vn_ri['export_target']
            self.logger.debug("act_rt_import is %s, act_rt_export is %s" %
                             (act_rt_import, act_rt_export))
            exp_rt = self.get_rt_info()
            self.logger.debug("exp_rt_import is %s, exp_rt_export is %s" %
                             (exp_rt['rt_import'], exp_rt['rt_export']))
            compare_rt_export = policy_test_utils.compare_list(
                self, exp_rt['rt_export'], act_rt_export)
            compare_rt_import = policy_test_utils.compare_list(
                self, exp_rt['rt_import'], act_rt_import)
            self.logger.debug(
                "compare_rt_export is %s, compare_rt_import is %s" % (compare_rt_export, compare_rt_import))
            if (compare_rt_export and compare_rt_import):
                compare = True
            else:
                self.logger.error(
                    "For VN %s, verify_vn_route_target failed in control node ",
                    "%s" % (self.vn_name, cn))
                return False
        return compare
    # end verify_route_target

    def get_matching_vrf(self, vrf_objs, vrf_name):
        return [x for x in vrf_objs if x['name'] == vrf_name][0]
    # end get_matching_vrf

    def get_rt_info(self):
        vn = self.vnc_lib_h.virtual_network_read(fq_name_str=self.vn_fq_name)
        pol_name_list = []
        rt_import_list = []
        rt_export_list = []

        rt_list1 = self.api_s_inspect.get_cs_route_targets(vn_id=vn.uuid)
        rt_name1 = self.api_s_inspect.get_cs_rt_names(rt_obj=rt_list1)
        rt_export_list = rt_name1
        rt_import_list.append(rt_name1[0])

        # Get the valid peer VN list for route exchange from calling code as it needs
        # to be looked from outside of VN fixture...
        dst_vn_name_list = self.policy_peer_vns
        print "VN list for RT import is %s" % dst_vn_name_list

        # Get the RT for each VN found in policy list
        if dst_vn_name_list:
            for vn_name in dst_vn_name_list:
                vn_obj = self.vnc_lib_h.virtual_network_read(
                    fq_name_str=vn_name)
                rt_list = self.api_s_inspect.get_cs_route_targets(
                    vn_id=vn_obj.uuid)
                rt_names = self.api_s_inspect.get_cs_rt_names(rt_obj=rt_list)
                for rt_name in rt_names:
                    rt_import_list.append(rt_name)

        return {'rt_export': rt_export_list, 'rt_import': rt_import_list}
    # end  get_rt_info

    def add_subnet(self, subnet):
        if isinstance(self.orchestrator,VcenterOrchestrator) :
            raise Exception('vcenter: subnets not supported')
        # Get the Quantum details
        quantum_obj = self.quantum_h.get_vn_obj_if_present(self.vn_name,
                                                                 self.project_id)
        #cidr = unicode(subnet)
        if type(subnet) is str:
            cidr = {'cidr': subnet}

        #ipam_fq_name = quantum_obj['network']['contrail:subnet_ipam'][0]['ipam_fq_name']
        ipam_fq_name = None
        net_id = quantum_obj['network']['id']

        # Create subnet
        self.quantum_h.create_subnet(cidr, net_id, ipam_fq_name)
    # end add_subnet

    def set_vxlan_id(self, vxlan_id=None):
        if not vxlan_id:
            vxlan_id = self.vxlan_id

        self.logger.debug('Updating VxLAN id of VN %s to %s' % (
            self.vn_fq_name, vxlan_id))
        vnc_lib = self.vnc_lib_h
        vn_obj = vnc_lib.virtual_network_read(id=self.uuid)
        vn_properties_obj = vn_obj.get_virtual_network_properties() \
            or  VirtualNetworkType()
        vn_properties_obj.set_vxlan_network_identifier(int(vxlan_id))
        vn_obj.set_virtual_network_properties(vn_properties_obj)
        vnc_lib.virtual_network_update(vn_obj)

    # end set_vxlan_id

    def get_vxlan_id(self):
        vnc_lib_fixture = self.connections.vnc_lib_fixture
        vxlan_mode = vnc_lib_fixture.get_vxlan_mode()
        vn_obj = self.vnc_lib_h.virtual_network_read(id=self.uuid)
        if vxlan_mode == 'automatic':
            return vn_obj.get_virtual_network_network_id()
        else:
            vn_prop_obj = vn_obj.get_virtual_network_properties()
            return vn_prop_obj['vxlan_network_identifier']
        return None
    # end get_vxlan_id

    def add_forwarding_mode(self, project_fq_name, vn_name, forwarding_mode):
        vnc_lib = self.vnc_lib_h
        # Figure out VN
        vni_list = vnc_lib.virtual_networks_list(
            parent_fq_name=project_fq_name)['virtual-networks']
        for vni_record in vni_list:
            if (vni_record['fq_name'][0] == project_fq_name[0] and
                vni_record['fq_name'][1] == project_fq_name[1] and
                    vni_record['fq_name'][2] == vn_name):
                vni_obj = vnc_lib.virtual_network_read(id=vni_record['uuid'])
                # if (vxlan_id is not None):
                # vni_obj_properties.set_vxlan_network_identifier(int(vxlan_id))
                if (forwarding_mode is not None):
                    vni_obj_properties = vni_obj.get_virtual_network_properties(
                    ) or VirtualNetworkType()
                    vni_obj_properties.set_forwarding_mode(forwarding_mode)
                    vni_obj.set_virtual_network_properties(vni_obj_properties)
                    vnc_lib.virtual_network_update(vni_obj)

    def cleanUp(self):
        super(VNFixture, self).cleanUp()
        self.delete()

    def delete(self, verify=False):
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if self.created:
            do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if self.clean_up == False:
            do_cleanup = False

        if do_cleanup:
            # Cleanup the route target if created
            if self.uuid in self.vn_with_route_target:
                self.logger.debug('Deleting RT for VN %s ' % (self.vn_name))
                self.del_route_target()
            self.logger.info("Deleting VN %s " % self.vn_name)
            if len(self.vn_port_list)!=0:
                for each_port_id in self.vn_port_list:
                    self.delete_port(port_id=each_port_id)
            if self.inputs.is_gui_based_config():
                self.webui.delete_vn(self)
            elif (self.option == 'contrail'):
                self.logger.debug("Deleting VN %s using Api server" %
                                 self.vn_name)
                self.vnc_lib_h.virtual_network_delete(id=self.uuid)
            else:
                for i in range(12):
                    if not self.orchestrator.delete_vn(self.obj):
                        # This might be due to caching issues.
                        self.logger.warn("%s. Deleting the VN %s failed" %
                                         (i, self.vn_name))
                        self.logger.info("%s. Retry deleting the VN %s " %
                                         (i, self.vn_name))
                        sleep(5)
                    else:
                        break
            if self.verify_is_run or verify:
                assert self.verify_vn_not_in_api_server(), ('VN %s is still'
                    ' seen in API Server' % (self.vn_name))
                assert self.verify_vn_not_in_agent(), ('VN %s is still '
                    'seen in one or more agents' %(self.vn_name))
                if self.vrf_ids:
                    assert self.verify_vn_not_in_vrouter(),('VRF cleanup'
                        ' verification failed')
                assert self.verify_vn_not_in_control_nodes(), ('VN %s: '
                    'is still seen in Control nodes' % (self.vn_name))
        else:
            self.logger.info('Skipping deletion of the VN %s ' %
                             (self.vn_name))
    # end cleanUp

    def get_obj(self):
        return self.vn_obj
    # end get_obj

    def bind_policies(self, policy_fq_names, vn_id):
        if  isinstance(self.orchestrator,VcenterOrchestrator) or self.option == 'contrail':
            self.api_vn_obj = self.vnc_lib_h.virtual_network_read(id=self.uuid)
            self.api_vn_obj.set_network_policy_list([],True)
            self.vnc_lib_h.virtual_network_update(self.api_vn_obj)
            for seq, policy in enumerate(policy_fq_names):
                policy_obj = self.vnc_lib_h.network_policy_read(fq_name=policy)
                self.api_vn_obj.add_network_policy(policy_obj,
                    VirtualNetworkPolicyType(sequence=SequenceType(major=seq, minor=0)))
            net_rsp = self.vnc_lib_h.virtual_network_update(self.api_vn_obj)
        else:
            net_rsp = {}
            project_name = self.project_name
            if len(policy_fq_names) != 0:
                project_name = policy_fq_names[0][1]
                net_req = {'contrail:policys': policy_fq_names}
                net_rsp = self.quantum_h.update_network(
                    vn_id, {'network': net_req})
                self.logger.debug(
                    'Response for mapping policy(s) with vn ' + str(net_rsp))
        # Update VN obj
        self.update_vn_object()
        return net_rsp
    # end bind_policy

    def get_current_policies_bound(self):
        self.api_vn_obj = self.vnc_lib_h.virtual_network_read(id=self.uuid)
        api_policy_refs = self.api_vn_obj.get_network_policy_refs()
        if not api_policy_refs:
            return []
        api_policy_fq_names = [item['to'] for item in api_policy_refs]
        return api_policy_fq_names
    # end get_current_policies_bound

    def update_vn_object(self):
        if isinstance(self.orchestrator,OpenstackOrchestrator) :
            self.obj = self.quantum_h.get_vn_obj_from_id(self.uuid)
        self.policy_objs = []
        if not self.policy_objs:
            for policy_fq_name in self.get_current_policies_bound():
                policy_obj = self.orchestrator.get_policy(policy_fq_name)
                self.policy_objs.append(policy_obj)
    # end update_vn_object

    def unbind_policies(self, vn_id, policy_fq_names=[]):
        if isinstance(self.orchestrator,VcenterOrchestrator) or self.option == 'contrail':
            if policy_fq_names == []:
                self.api_vn_obj.set_network_policy_list([],True)
                net_rsp = self.vnc_lib_h.virtual_network_update(self.api_vn_obj)
            else:
                for policy in policy_fq_names:
                    policy_obj = self.vnc_lib_h.network_policy_read(fq_name=policy)
                    self.api_vn_obj.del_network_policy(policy_obj)
                    net_rsp = self.vnc_lib_h.virtual_network_update(self.api_vn_obj)
        else:
            policys = self.get_current_policies_bound()
            policys_to_remain = policys
            for policy_name in policy_fq_names:
                if not policy_name in policys:
                    self.logger.error('Policy %s is not bound to VN ID %s ' %
                                      (policy_name, vn_id))
                    return None
                else:
                    policys_to_remain.remove(policy_name)
            # If no policy is passed, unbind all policys
            if len(policy_fq_names) == 0:
                policys_to_remain = []
            net_req = {'contrail:policys': policys_to_remain}
            net_rsp = self.quantum_h.update_network(
                vn_id, {'network': net_req})

        self.policy_objs= []
        self.update_vn_object()
        return net_rsp
    # end unbind_policy

    def update_subnet(self, subnet_id, subnet_dict):
        if isinstance(self.orchestrator,VcenterOrchestrator):
           raise Exception('vcenter: subnets not supported')
        self.quantum_h.update_subnet(subnet_id, subnet_dict)
        self.vn_subnet_objs = self.quantum_h.get_subnets_of_vn(self.uuid)

    def get_subnets(self):
        if isinstance(self.orchestrator,VcenterOrchestrator):
           raise Exception('vcenter: subnets not supported')
        return self.quantum_h.get_subnets_of_vn(self.uuid)

    def add_to_router(self, physical_router_id):
        pr = self.vnc_lib_h.physical_router_read(id=physical_router_id)
        vn_obj = self.vnc_lib_h.virtual_network_read(id = self.uuid)
        pr.add_virtual_network(vn_obj)
    # end add_to_router

    def delete_from_router(self, physical_router_id):
        pr = self.vnc_lib_h.physical_router_read(id=physical_router_id)
        vn_obj = self.vnc_lib_h.virtual_network_read(id = self.uuid)
        pr.delete_virtual_network(vn_obj)
    # end delete_from_router

    def set_unknown_unicast_forwarding(self, enable=True):
        vn_obj = self.vnc_lib_h.virtual_network_read(id = self.uuid)
        vn_obj.set_flood_unknown_unicast(enable)
        self.vnc_lib_h.virtual_network_update(vn_obj)
        self.logger.info('Setting flood_unknown_unicast flag of VN %s to %s'
            '' % (self.vn_name, enable))
    # end set_unknown_unicast_forwarding

    def get_an_ip(self, cidr=None, index=2):
        if not cidr:
            cidr = self.vn_subnet_objs[0]['cidr']
        return get_an_ip(cidr, index)
    # end get_an_ip

    def set_pbb_evpn_enable(self, pbb_evpn_enable=None):
        ''' Configure PBB EVPN on virtual network '''
        self.logger.debug('Updating PBB EVPN on VN %s to %s' % (
            self.vn_fq_name, pbb_evpn_enable))
        vn_obj = self.vnc_lib_h.virtual_network_read(id = self.uuid)
        vn_obj.set_pbb_evpn_enable(pbb_evpn_enable)
        self.vnc_lib_h.virtual_network_update(vn_obj)
    # end set_pbb_evpn_enable

    def set_pbb_etree_enable(self, pbb_etree_enable=None):
        ''' Configure PBB etree on virtual network '''
        self.logger.debug('Updating PBB etree on VN %s to %s' % (
            self.vn_fq_name, pbb_etree_enable))
        vn_obj = self.vnc_lib_h.virtual_network_read(id = self.uuid)
        vn_obj.set_pbb_etree_enable(pbb_etree_enable)
        self.vnc_lib_h.virtual_network_update(vn_obj)
    # end set_pbb_etree_enable

    def set_layer2_control_word(self, layer2_control_word=None):
        ''' Configure Layer2 control word on virtual network
            This configuration knob controls the insertion of 4-octet control word
            between bottom of MPLS label stack and L2 payload.'''
        self.logger.debug('Updating Layer2 control word on VN %s to %s' % (
            self.vn_fq_name, layer2_control_word))
        vn_obj = self.vnc_lib_h.virtual_network_read(id = self.uuid)
        vn_obj.set_layer2_control_word(layer2_control_word)
        self.vnc_lib_h.virtual_network_update(vn_obj)
    # end set_layer2_control_word

    def set_mac_learning_enabled(self, mac_learning_enabled=None):
        ''' Configure MAC Learning on virtual network '''
        self.logger.debug('Updating MAC Learning on VN %s to %s' % (
            self.vn_fq_name, mac_learning_enabled))
        vn_obj = self.vnc_lib_h.virtual_network_read(id = self.uuid)
        vn_obj.set_mac_learning_enabled(mac_learning_enabled)
        self.vnc_lib_h.virtual_network_update(vn_obj)
    # end set_mac_learning_enabled

    def set_mac_limit_control(self, mac_limit_control=None):
        ''' Configure MAC Limit Control on virtual network '''
        self.logger.debug('Updating MAC Limit control on VN %s to %s' % (
            self.vn_fq_name, mac_limit_control))
        vn_obj = self.vnc_lib_h.virtual_network_read(id = self.uuid)
        vn_obj.set_mac_limit_control(mac_limit_control)
        self.vnc_lib_h.virtual_network_update(vn_obj)
    # end set_mac_limit_control

    def set_mac_move_control(self, mac_move_control=None):
        ''' Configure MAC Move on virtual network '''
        self.logger.debug('Updating MAC Move on VN %s to %s' % (
            self.vn_fq_name, mac_move_control))
        vn_obj = self.vnc_lib_h.virtual_network_read(id = self.uuid)
        vn_obj.set_mac_move_control(mac_move_control)
        self.vnc_lib_h.virtual_network_update(vn_obj)
    # end set_mac_move_control

    def set_mac_aging_time(self, mac_aging_time=None):
        ''' Configure MAC Aging on virtual network '''
        self.logger.debug('Updating MAC Aging on VN %s to %s' % (
            self.vn_fq_name, mac_aging_time))
        vn_obj = self.vnc_lib_h.virtual_network_read(id = self.uuid)
        vn_obj.set_mac_aging_time(mac_aging_time)
        self.vnc_lib_h.virtual_network_update(vn_obj)
    # end set_mac_aging_time

    def get_pbb_evpn_enable(self):
        ''' Get PBB EVPN on virtual network '''
        vn_obj = self.vnc_lib_h.virtual_network_read(id = self.uuid)
        pbb_evpn_enable = vn_obj.get_pbb_evpn_enable()
        self.logger.debug('PBB EVPN on VN %s is %s' % (
            self.vn_fq_name, pbb_etree_enable))
        return pbb_evpn_enable
    # end get_pbb_evpn_enable

    def get_pbb_etree_enable(self):
        ''' Get PBB etree on virtual network '''
        vn_obj = self.vnc_lib_h.virtual_network_read(id = self.uuid)
        pbb_etree_enable = vn_obj.get_pbb_etree_enable()
        self.logger.debug('PBB etree on VN %s is %s' % (
            self.vn_fq_name, pbb_etree_enable))
        return pbb_etree_enable
    # end get_pbb_etree_enable

    def get_layer2_control_word(self):
        ''' Get Layer2 control word on virtual network '''
        vn_obj = self.vnc_lib_h.virtual_network_read(id = self.uuid)
        layer2_control_word = vn_obj.get_layer2_control_word()
        self.logger.debug('Layer2 control word on VN %s is %s' % (
            self.vn_fq_name, layer2_control_word))
        return layer2_control_word
    # end get_layer2_control_word

    def get_mac_learning_enabled(self):
        ''' Get MAC Learning on virtual network '''
        vn_obj = self.vnc_lib_h.virtual_network_read(id = self.uuid)
        mac_learning_enabled = vn_obj.get_mac_learning_enabled()
        self.logger.debug('MAC Learning on VN %s is %s' % (
            self.vn_fq_name, mac_learning_enabled))
        return mac_learning_enabled
    # end get_mac_learning_enabled

    def get_mac_limit_control(self):
        ''' Get MAC Limit Control on virtual network '''
        vn_obj = self.vnc_lib_h.virtual_network_read(id = self.uuid)
        mac_limit_control = vn_obj.get_mac_limit_control()
        self.logger.debug('MAC Limit control on VN %s is %s' % (
            self.vn_fq_name, mac_limit_control))
        return mac_limit_control
    # end get_mac_limit_control

    def get_mac_move_control(self):
        ''' Get MAC Move on virtual network '''
        vn_obj = self.vnc_lib_h.virtual_network_read(id = self.uuid)
        mac_move_control = vn_obj.get_mac_move_control()
        self.logger.debug('MAC Move on VN %s is %s' % (
            self.vn_fq_name, mac_move_control))
        return mac_move_control
    # end get_mac_move_control

    def get_mac_aging_time(self):
        ''' Get MAC Aging on virtual network '''
        vn_obj = self.vnc_lib_h.virtual_network_read(id = self.uuid)
        mac_aging_time = vn_obj.get_mac_aging_time()
        self.vnc_lib_h.virtual_network_update(vn_obj)
        self.logger.debug('MAC Aging on VN %s is %s' % (
            self.vn_fq_name, mac_aging_time))
        return mac_aging_time
    # end get_mac_aging_time

    def add_bridge_domain(self, bd_obj=None):
        ''' Adding bridge doamin to VN '''
        self.logger.info('Adding bridge domain %s to VN %s' % (bd_obj,self.uuid))
        vn_obj = self.vnc_lib_h.virtual_network_read(id = self.uuid)
        vn_obj.add_bridge_domain(bd_obj)
        self.vnc_lib_h.virtual_network_update(vn_obj)
    # end add_bridge_domain

    def del_bridge_domain(self, bd_obj=None):
        ''' Deleting bridge doamin from  VN '''
        self.logger.info('Deleting bridge domain %s from VN %s' % (bd_obj,self.uuid))
        vn_obj = self.vnc_lib_h.virtual_network_read(id = self.uuid)
        vn_obj.del_bridge_domain(bd_obj)
        self.vnc_lib_h.virtual_network_update(vn_obj)
    # end del_bridge_domain


# end VNFixture


class MultipleVNFixture(fixtures.Fixture):

    """ Fixture to create, verify and delete multiple VNs and multiple subnets
        each.

        Deletion of the VN upon exit can be disabled by setting
        fixtureCleanup=no. If a VN with the vn_name is already present, it is
        not deleted upon exit. Use fixtureCleanup=force to force a delete.
    """

    def __init__(self, connections, inputs, vn_count=1, subnet_count=1,
                 vn_name_net={},  project_name=None, af=None):
        """
        vn_count     : Number of VN's to be created.
        subnet_count : Subnet per each VN's
        vn_name_net  : Dictionary of VN name as key and a network with prefix to
                       be subnetted(subnet_count)as value  or list of subnets to
                       be created in that VN as value.

        Example Usage:
        1. vn_fixture = MultipleVnFixture(conn, inputs, vn_count=10,
                                          subnet_count=20)
        Creates 10 VN's with name vn1, vn2...vn10 with 20 subnets each.
        Dynamicaly identifies the subnet's and stores them as class attributes
        for future use.

        2. vn_fixture = MultipleVnFixture(conn, inputs, subnet_count=20,
                                        vn_name_net={'vn1' : '10.1.1.0/24',
                                        'vn2' : ['30.1.1.0/24', '30.1.2.0/24']})
        Creates VN's vn1 and vn2, with 20 subnets in vn1 and 2 subnets in vn2.
        """
        self.inputs = inputs
        self.connections = connections
        if not project_name:
            project_name = self.inputs.project_name
        self.stack = af or self.inputs.get_af()
        self.project_name = project_name
        self.vn_count = vn_count
        self.subnet_count = subnet_count
        self.vn_name_net = vn_name_net
        self.logger = inputs.logger
        self._vn_subnets = {}
        self._find_subnets()

    def _subnet(self, af='v4', network=None, roll_over=False):
        if not network:
            while True:
                network=get_random_cidr(af=af, mask=SUBNET_MASK[af]['min'])
                for rand_net in self.random_networks:
                    if not cidr_exclude(network, rand_net):
                       break
                else:
                    break
        net, plen = network.split('/')
        plen = int(plen)
        max_plen = SUBNET_MASK[af]['max']
        reqd_plen = max_plen - (int(self.subnet_count) - 1).bit_length()
        if plen > reqd_plen:
            if not roll_over:
                max_subnets = 2 ** (max_plen - plen)
                raise NotPossibleToSubnet("Network prefix %s can be subnetted "
                      "only to maximum of %s subnets" % (network, max_subnets))
            network = '%s/%s'%(net, reqd_plen)

        subnets = list(IPNetwork(network).subnet(plen))
        return map(lambda subnet: subnet.__str__(), subnets[:])

    def _find_subnets(self):
        if not self.vn_name_net:
            self.random_networks = []
            for i in range(self.vn_count):
                subnets = []
                if 'v4' in self.stack or 'dual' in self.stack:
                    subnets.extend(self._subnet(af='v4'))
                if 'v6' in self.stack or 'dual' in self.stack:
                    subnets.extend(self._subnet(af='v6'))
                self._vn_subnets.update({'vn%s' % (i + 1): subnets[:]})
                self.random_networks.extend(subnets)
            return
        for vn_name, net in self.vn_name_net.items():
            if type(net) is list:
                self._vn_subnets.update({vn_name: net})
            else:
                self._vn_subnets.update({vn_name: self._subnet(network=net, af=self.stack)})

    def setUp(self):
        super(MultipleVNFixture, self).setUp()
        self._vn_fixtures = []
        for vn_name, subnets in self._vn_subnets.items():
            vn_fixture = self.useFixture(VNFixture(inputs=self.inputs,
                                                   connections=self.connections,
                                                   project_name=self.project_name,
                                                   vn_name=vn_name, subnets=subnets))
            self._vn_fixtures.append((vn_name, vn_fixture))

    def verify_on_setup(self):
        result = True
        for vn_name, vn_fixture in self._vn_fixtures:
            result &= vn_fixture.verify_on_setup()

        return result

    def get_all_subnets(self):
        return self._vn_subnets

    def get_all_fixture_obj(self):
        return map(lambda (name, fixture): (name, fixture.obj), self._vn_fixtures)

