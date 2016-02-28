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
try:
    from webui_test import *
except ImportError:
    pass

class NotPossibleToSubnet(Exception):

    """Raised when a given network/prefix is not possible to be subnetted to
       required numer of subnets.
    """
    pass


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
                 subnets=[], project_name=None, router_asn='64512',
                 rt_number=None, ipam_fq_name=None, option='quantum',
                 forwarding_mode=None, vxlan_id=None, shared=False,
                 router_external=False, clean_up=True, project_obj= None,
                 af=None, empty_vn=False, enable_dhcp=True,
                 dhcp_option_list=None, disable_gateway=False, uuid=None):
        self.connections = connections
        self.inputs = inputs or connections.inputs
        self.logger = self.connections.logger
        self.orch = self.connections.orch
        self.quantum_h = self.connections.quantum_h
        self.vnc_lib_h = self.connections.get_vnc_lib_h()
        self.api_s_inspect = self.connections.api_server_inspect
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.analytics_obj = self.connections.analytics_obj
        self.domain_name = self.connections.domain_name
        self.project_name = project_name or self.connections.project_name
        self.vn_name = vn_name or get_random_name(self.project_name)
        self.project_id = self.connections.get_project_id()
        self.uuid = uuid
        self.obj = None
        self.ipam_fq_name = ipam_fq_name or NetworkIpam().get_fq_name()
        self.policy_objs = policy_objs
        self.af = self.get_af_from_subnet(subnets=subnets) or af or self.inputs.get_af()
        if self.inputs.get_af() == 'v6' and self.af == 'v4':
            raise v4OnlyTestException("Skipping Test. v4 specific testcase")
        #Forcing v4 subnet creation incase of v6. Reqd for ssh to host
        self.af = 'dual' if 'v6' in self.af else self.af
        if self.inputs.orchestrator == 'vcenter' and subnets and (len(subnets) != 1):
           raise Exception('vcenter: Multiple subnets not supported')
        if not subnets and not empty_vn:
            subnets = get_random_cidrs(stack=self.af)
        if subnets and self.get_af_from_subnet(subnets=subnets) == 'v6':
            subnets.extend(get_random_cidrs(stack='v4'))
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
        self.already_present = False
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
        self.project_obj = project_obj
        self.vn_fq_name = None
        self.enable_dhcp = enable_dhcp
        self.dhcp_option_list = dhcp_option_list
        self.disable_gateway = disable_gateway
        self.vn_port_list=[]
        self.vn_with_route_target = []
    # end __init__

    def read(self):
        if self.uuid:
            self.obj = self.orch.get_vn_obj_from_id(self.uuid)
            self.api_vn_obj = self.vnc_lib_h.virtual_network_read(id=self.uuid)
            self.vn_name = self.api_vn_obj.name
            self.vn_fq_name = self.api_vn_obj.get_fq_name_str()
            self.fq_name = self.api_vn_obj.get_fq_name()
            ipam = get_network_ipam_refs()
            if ipam:
                subnets = [x['subnet']['ip_prefix']+'/'+\
                           x['subnet']['ip_prefix_len'] 
                           for x in ipam[0]['attr']['ipam_subnets']]
                self.vn_subnets = subnets
                self._parse_subnets()
            else:
                subnets = None
                self.vn_subnets = []
            self.logger.debug('Fetched VN: %s(%s) with subnets %s'
                             %(self.vn_fq_name, self.uuid, subnets))

    def get_uuid(self):
        return self.uuid

    @property
    def vn_id(self):
        return self.get_uuid()

    def get_vrf_name(self):
        return self.vn_fq_name + ':' + self.vn_name

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

    @retry(delay=10, tries=10)
    def _create_vn_orch(self):
        try:
            self.obj = self.orch.get_vn_obj_if_present(self.vn_name,
                                         project_id=self.project_id)
            if not self.obj:
                self.obj = self.orch.create_vn(
                                                self.vn_name,
                                                self.vn_subnets,
                                                ipam_fq_name=self.ipam_fq_name,
                                                shared=self.shared,
                                                router_external=self.router_external,
                                                enable_dhcp=self.enable_dhcp,
                                                disable_gateway=self.disable_gateway)
                self.logger.info('Created VN %s' %(self.vn_name))
            else:
                self.already_present = True
                self.logger.debug('VN %s already present, not creating it' %
                                  (self.vn_name))
            self.uuid = self.orch.get_vn_id(self.obj)
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

    def _create_vn_api(self, vn_name, project):
        if self.inputs.orchestrator == 'vcenter':
           raise Exception('vcenter: no support for VN creation through VNC-api')
        try:
            self.api_vn_obj = VirtualNetwork(
                name=vn_name, parent_obj=project.project_obj)
            if not self.verify_if_vn_already_present(self.api_vn_obj, project.project_obj):
                self.uuid = self.vnc_lib_h.virtual_network_create(
                    self.api_vn_obj)
                with self.lock:
                    self.logger.info("Created VN %s, UUID :%s" % (self.vn_name,
                        self.uuid))
            else:
                with self.lock:
                    self.logger.debug("VN %s already present" % (self.vn_name))
                self.uuid = self.get_vn_uid(
                    self.api_vn_obj, project.project_obj.uuid)
            ipam = self.vnc_lib_h.network_ipam_read(
                fq_name=self.ipam_fq_name)
            ipam_sn_lst = []
            # The dhcp_option_list and enable_dhcp flags will be modified for all subnets in an ipam
            for net in self.vn_subnets:
                network, prefix = net['cidr'].split('/')
                ipam_sn = IpamSubnetType(
                    subnet=SubnetType(network, int(prefix)))
                if self.dhcp_option_list:
                   ipam_sn.set_dhcp_option_list(self.dhcp_option_list)
                if not self.enable_dhcp:
                   ipam_sn.set_enable_dhcp(self.enable_dhcp)
                ipam_sn_lst.append(ipam_sn)
            self.api_vn_obj.add_network_ipam(ipam, VnSubnetsType(ipam_sn_lst))
            self.vnc_lib_h.virtual_network_update(self.api_vn_obj)
            self.vn_fq_name = self.api_vn_obj.get_fq_name_str()
            self.obj = self.quantum_h.get_vn_obj_if_present(self.vn_name,
                                                                  self.project_id)
            if self.obj is None:
                raise ValueError('could not find %s in neutron/quantum' % (self.vn_name))

        except Exception as e:
            with self.lock:
                self.logger.exception(
                    'Api exception while creating network %s' % (self.vn_name))

    def get_api_obj(self):
        return self.api_vn_obj

    def getObj(self):
        return self.api_vn_obj

    def setUp(self):
        super(VNFixture, self).setUp()
        self.create()

    def create(self):
        if self.uuid:
            return self.read()
        if not self.project_obj:
            self.project_obj = self.useFixture(ProjectFixture(
                                   vnc_lib_h=self.vnc_lib_h,
                                   project_name=self.project_name,
                                   connections=self.connections))
        self.project_id = self.project_obj.uuid
        if self.inputs.is_gui_based_config():
            self.webui.create_vn(self)
        elif (self.option == 'api'):
            self._create_vn_api(self.vn_name, self.project_obj)
        else:
            self._create_vn_orch()

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
            self.update_vn_object()
        # end if

        # Configure route target
        if self.rt_number is not None:
            self.add_route_target()
            self.vn_with_route_target.append(self.uuid)

        # Configure forwarding mode
        if self.forwarding_mode is not None:
            self.add_forwarding_mode(
                self.project_obj.project_fq_name, self.vn_name, self.forwarding_mode)

        # Configure vxlan_id
        if self.vxlan_id is not None:
            self.set_vxlan_id()

        # Populate the VN Subnet details
        if self.inputs.orchestrator == 'openstack':
            self.vn_subnet_objs = self.quantum_h.get_subnets_of_vn(self.uuid)
    # end setUp

    def create_subnet(self, vn_subnet, ipam_fq_name):
        if self.inputs.orchestrator == 'vcenter':
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
                    security_groups=[], extra_dhcp_opts=None):
        if self.inputs.orchestrator == 'vcenter':
            raise Exception('vcenter: ports not supported')
        fixed_ips = [{'subnet_id': subnet_id, 'ip_address': ip_address}]
        port_rsp = self.quantum_h.create_port(
            net_id,
            fixed_ips,
            mac_address,
            no_security_group,
            security_groups,
            extra_dhcp_opts)
        self.vn_port_list.append(port_rsp['id'])
        return port_rsp
 
    def delete_port(self, port_id, quiet=False):
        if self.inputs.orchestrator == 'vcenter':
            raise Exception('vcenter: ports not supported')
        is_port_present=self.quantum_h.get_port(port_id)
        if is_port_present is not None:
            self.quantum_h.delete_port(port_id)


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
            project=self.project_name, vn=self.vn_name, refresh=True)
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
        self.api_verification_flag = self.api_verification_flag and True
        self.logger.info("Verifications in API Server for VN %s passed" %
                         (self.vn_name))
        self.api_s_routing_instance = self.api_s_inspect.get_cs_routing_instances(
            vn_id=self.uuid)
        return True
    # end verify_vn_in_api_server

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
        if self.inputs.orchestrator == 'vcenter':
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
            project=self.project_name, vn=self.vn_name, refresh=True)
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
                    'policy_fqn', fqn, d['ret']['policy']['fq_name'])
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
        if self.api_s_inspect.get_cs_vn(project=self.project_name, vn=self.vn_name, refresh=True):
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
    def verify_vn_in_control_nodes(self):
        """ Checks for VN details in Control-nodes.

        False if RT does not match the RT from API-Server for each of control-nodes
        """
        self.api_s_route_targets = self.api_s_inspect.get_cs_route_targets(
            vn_id=self.uuid)

        self.cn_verification_flag = True
        for cn in self.inputs.bgp_ips:
            cn_config_vn_obj = self.cn_inspect[cn].get_cn_config_vn(
                vn_name=self.vn_name, project=self.project_name)
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
        if self.cn_inspect[cn].get_cn_config_vn(vn_name=self.vn_name, project=self.project_name):
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

    @retry(delay=5, tries=30)
    def verify_vn_not_in_agent(self):
        ''' Verify that VN is removed in all agent nodes.
        '''
        for compute_ip in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[compute_ip]
            vn = inspect_h.get_vna_vn(
                project=self.project_name, vn_name=self.vn_name)
            if vn:
                self.logger.debug('VN %s is still found in %s ' %
                                 (self.vn_name, compute_ip))
                return False
                self.not_in_agent_verification_flag = False
            vrf_objs = inspect_h.get_vna_vrf_objs(
                project=self.project_name, vn_name=self.vn_name)
            if len(vrf_objs['vrf_list']) != 0:
                self.logger.debug(
                    'VRF %s for VN %s is still found in agent %s' %
                    (str(self.ri_name), self.vn_name, compute_ip))
                self.not_in_agent_verification_flag = False
                return False
            self.logger.debug('VN %s is not present in Agent %s ' %
                             (self.vn_name, compute_ip))
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
        if self.inputs.orchestrator == 'vcenter':
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
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if self.already_present:
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
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
            elif (self.option == 'api'):
                self.logger.debug("Deleting VN %s using Api server" %
                                 self.vn_name)
                self.vnc_lib_h.virtual_network_delete(id=self.uuid)
            else:
                for i in range(12):
                    if not self.orch.delete_vn(self.obj):
                        # This might be due to caching issues.
                        self.logger.warn("%s. Deleting the VN %s failed" %
                                         (i, self.vn_name))
                        self.logger.info("%s. Retry deleting the VN %s " %
                                         (i, self.vn_name))
                        sleep(5)
                    else:
                        break
            if self.verify_is_run or verify:
                assert self.verify_vn_not_in_api_server(), ('VN %s is still',
                    ' seen in API Server' % (self.vn_name))
                assert self.verify_vn_not_in_agent(), ('VN %s is still ',
                    'seen in one or more agents' %(self.vn_name))
                assert self.verify_vn_not_in_control_nodes(), ('VN %s: ',
                    'is still seen in Control nodes' % (self.vn_name))
        else:
            self.logger.info('Skipping deletion of the VN %s ' %
                             (self.vn_name))
    # end cleanUp

    def get_obj(self):
        return self.vn_obj
    # end get_obj

    def bind_policies(self, policy_fq_names, vn_id):
        if self.inputs.orchestrator == 'vcenter':
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
        if self.inputs.orchestrator == 'openstack':
            self.obj = self.quantum_h.get_vn_obj_from_id(self.uuid)
        self.policy_objs = []
        if not self.policy_objs:
            for policy_fq_name in self.get_current_policies_bound():
                policy_obj = self.orch.get_policy(policy_fq_name)
                self.policy_objs.append(policy_obj)
    # end update_vn_object

    def unbind_policies(self, vn_id, policy_fq_names=[]):
        if self.inputs.orchestrator == 'vcenter':
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
        if self.inputs.orchestrator == 'vcenter':
           raise Exception('vcenter: subnets not supported')
        self.quantum_h.update_subnet(subnet_id, subnet_dict)
        self.vn_subnet_objs = self.quantum_h.get_subnets_of_vn(self.uuid)

    def get_subnets(self):
        if self.inputs.orchestrator == 'vcenter':
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
                self._vn_subnets.update({vn_name: self._subnet(network=net)})

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

