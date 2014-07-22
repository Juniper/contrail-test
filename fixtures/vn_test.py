from netaddr import IPNetwork

import fixtures
from ipam_test import *
from project_test import *
from util import *
from vnc_api.vnc_api import *
from netaddr import *
from time import sleep
from contrail_fixtures import *
import inspect
import policy_test_utils
import threading
import sys
from quantum_test import NetworkClientException
from webui_test import *


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
# def __init__(self, connections, vn_name, inputs, policy_objs= [],
# subnets=[], project_name= 'admin', router_asn='64512', rt_number=None,
# ipam_fq_name=None, option = 'api'):

    def __init__(self, connections, vn_name, inputs, policy_objs=[], subnets=[], project_name='admin', router_asn='64512', rt_number=None, ipam_fq_name=None, option='quantum', forwarding_mode=None, vxlan_id=None, shared=False, router_external=False, clean_up=True):
        self.connections = connections
        self.inputs = inputs
        self.quantum_fixture = self.connections.quantum_fixture
        self.vnc_lib_h = self.connections.vnc_lib
        self.api_s_inspect = self.connections.api_server_inspect
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.vn_name = vn_name
        self.vn_subnets = subnets
        if self.inputs.webui_verification_flag:
            self.browser = self.connections.browser
            self.browser_openstack = self.connections.browser_openstack
            self.webui = WebuiTest(self.connections, self.inputs)
        self.project_name = project_name
        self.project_obj = None
        self.project_id = None
        self.obj = None
        self.vn_id = None
        self.ipam_fq_name = ipam_fq_name or NetworkIpam().get_fq_name()
        self.policy_objs = policy_objs
        self.logger = inputs.logger
        self.already_present = False
        self.verify_is_run = False
        self.router_asn = router_asn
        self.rt_number = rt_number
        self.option = option
        self.forwarding_mode = forwarding_mode
        self.vxlan_id = vxlan_id
        self.shared = shared
        self.router_external = router_external
        self.clean_up = clean_up
        #self.analytics_obj=AnalyticsVerification(inputs= self.inputs,connections= self.connections)
        self.analytics_obj = self.connections.analytics_obj
        self.lock = threading.Lock()
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
    # end __init__

    @retry(delay=10, tries=10)
    def _create_vn_quantum(self):
        try:
            self.obj = self.quantum_fixture.get_vn_obj_if_present(self.vn_name,
                                                                  self.project_id)
            if not self.obj:
                self.obj = self.quantum_fixture.create_network(
                    self.vn_name, self.vn_subnets, self.ipam_fq_name, self.shared, self.router_external)
                self.logger.debug('Created VN %s' %(self.vn_name))
            else:
                self.already_present = True
                self.logger.debug('VN %s already present, not creating it' %
                                  (self.vn_name))
            self.vn_id = self.obj['network']['id']
#            self.vn_fq_name=':'.join(self.obj['network']['contrail:fq_name'])
            self.vn_fq_name = ':'.join(
                self.vnc_lib_h.id_to_fq_name(self.vn_id))
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

#        self.api_vn_obj = VirtualNetwork(name = self.vn_name, parent_obj= self.project_obj.project_obj)
        try:
            self.api_vn_obj = VirtualNetwork(
                name=vn_name, parent_obj=project.project_obj)
            if not self.verify_if_vn_already_present(self.api_vn_obj, project.project_obj):
                self.vn_id = self.vnc_lib_h.virtual_network_create(
                    self.api_vn_obj)
                with self.lock:
                    self.logger.info("Created VN %s using api-server" % (
                                     self.vn_name))
            else:
                with self.lock:
                    self.logger.info("VN %s already present" % (self.vn_name))
                self.vn_id = self.get_vn_uid(
                    self.api_vn_obj, project.project_obj.uuid)
            ipam = self.vnc_lib_h.network_ipam_read(
                fq_name=self.ipam_fq_name)
            ipam_sn_lst = []
            for net in self.vn_subnets:
                ipam_sn = None
                network, prefix = net.split('/')
                ipam_sn = IpamSubnetType(
                    subnet=SubnetType(network, int(prefix)))
                ipam_sn_lst.append(ipam_sn)
            self.api_vn_obj.add_network_ipam(ipam, VnSubnetsType(ipam_sn_lst))
            self.vnc_lib_h.virtual_network_update(self.api_vn_obj)
            self.vn_fq_name = self.api_vn_obj.get_fq_name_str()
            self.obj = self.quantum_fixture.get_vn_obj_if_present(self.vn_name,
                                                                  self.project_id)
        except Exception as e:
            with self.lock:
                self.logger.exception(
                    'Api exception while creating network %s' % (self.vn_name))

    def get_api_obj(self):

        return self.api_vn_obj

    def setUp(self):
        super(VNFixture, self).setUp()
        with self.lock:
            self.logger.info("Creating vn %s.." % (self.vn_name))
        self.project_obj = self.useFixture(ProjectFixture(
            vnc_lib_h=self.vnc_lib_h, project_name=self.project_name, connections=self.connections))
        self.project_id = self.project_obj.uuid
        if self.inputs.webui_config_flag:
            self.webui.create_vn_in_webui(self)
        elif (self.option == 'api'):
            self._create_vn_api(self.vn_name, self.project_obj)
        else:
            self._create_vn_quantum()

        # Bind policies if any
        if self.policy_objs:
            policy_fq_names = [
                self.quantum_fixture.get_policy_fq_name(x) for x in self.policy_objs]
            self.bind_policies(policy_fq_names, self.vn_id)
        else:
            # Update self.policy_objs to pick acls which are already
            # bound to the VN
            self.update_vn_object()
        # end if
        self.ri_name = self.vn_fq_name + ':' + self.vn_name
        self.vrf_name = self.vn_fq_name + ':' + self.vn_name

        # Configure route target
        self.vn_with_route_target = []
        if self.rt_number is not None:
            self.add_route_target(
                self.ri_name, self.router_asn, self.rt_number)
            self.vn_with_route_target.append(self.vn_id)

        # Configure forwarding mode
        if self.forwarding_mode is not None:
            self.add_forwarding_mode(
                self.project_obj.project_fq_name, self.vn_name, self.forwarding_mode)

        # Configure vxlan_id
        if self.vxlan_id is not None:
            self.add_vxlan_id(self.project_obj.project_fq_name,
                              self.vn_name, self.vxlan_id)
    # end setUp

    def create_subnet(self, vn_subnet, ipam_fq_name):
        self.quantum_fixture.create_subnet(
            vn_subnet, self.vn_id, ipam_fq_name)

    def verify_on_setup_without_collector(self):
        # once api server gets restarted policy list for vn in not reflected in
        # vn uve so removing that check here
        result = True
        t_api = threading.Thread(target=self.verify_vn_in_api_server, args=())
        t_api.start()
        time.sleep(1)
        t_api.join()
        t_cn = threading.Thread(
            target=self.verify_vn_in_control_nodes, args=())
        t_cn.start()
        time.sleep(1)
        t_pol_api = threading.Thread(
            target=self.verify_vn_policy_in_api_server, args=())
        t_pol_api.start()
        time.sleep(1)
        t_op = threading.Thread(target=self.verify_vn_in_opserver, args=())
        t_op.start()
        time.sleep(1)
        t_cn.join()
        t_pol_api.join()
        t_op.join()
        if not self.api_verification_flag:
            result = result and False
            self.logger.error(
                "One or more verifications in API Server for VN %s failed" % (self.vn_name))
        if not self.cn_verification_flag:
            result = result and False
            self.logger.error(
                "One or more verifications in Control-nodes for VN %s failed" % (self.vn_name))
        if not self.policy_verification_flag['result']:
            result = result and False
            self.logger.error(ret['msg'])
        if not self.op_verification_flag:
            result = result and False
            self.logger.error(
                "One or more verifications in OpServer for VN %s failed" % (self.vn_name))

        self.verify_is_run = True
        self.verify_result = result
        return result

    def verify_on_setup(self):
        result = True
        if self.inputs.webui_verification_flag:
            self.webui.verify_vn_in_webui(self)
        t_api = threading.Thread(target=self.verify_vn_in_api_server, args=())
#        t_api.daemon = True
        t_api.start()
        time.sleep(1)
        t_api.join()
        t_cn = threading.Thread(
            target=self.verify_vn_in_control_nodes, args=())
        t_cn.start()
        time.sleep(1)
        t_pol_api = threading.Thread(
            target=self.verify_vn_policy_in_api_server, args=())
        t_pol_api.start()
        time.sleep(1)
        if self.policy_objs:
            t_pol_op = threading.Thread(
                target=self.verify_vn_policy_in_vn_uve, args=())
            t_pol_op.daemon = True
            t_pol_op.start()
            time.sleep(1)
            t_pol_op.join()
        t_op = threading.Thread(target=self.verify_vn_in_opserver, args=())
        t_op.start()
        time.sleep(1)
        t_cn.join()
        t_pol_api.join()
        t_op.join()
        if not self.api_verification_flag:
            result = result and False
            self.logger.error(
                "One or more verifications in API Server for VN %s failed" % (self.vn_name))
        if not self.cn_verification_flag:
            result = result and False
            self.logger.error(
                "One or more verifications in Control-nodes for VN %s failed" % (self.vn_name))
        if not self.policy_verification_flag['result']:
            result = result and False
            self.logger.error(
                "One or more verifications of policy for VN %s failed" % (self.vn_name))
        if self.policy_objs:
            if not self.pol_verification_flag:
                result = result and False
                self.logger.warn("Attached policy not shown in vn uve %s" %
                                 (self.vn_name))
        if not self.op_verification_flag:
            result = result and False
            self.logger.error(
                "One or more verifications in OpServer for VN %s failed" % (self.vn_name))

        self.verify_is_run = True
        self.verify_result = result
        return result
    # end verify

    @retry(delay=5, tries=3)
    def verify_vn_in_api_server(self):
        """ Checks for VN in API Server.

        False If VN Name is not found
        False If all Subnet prefixes are not found
        """
        self.api_verification_flag = True
        self.api_s_vn_obj = self.api_s_inspect.get_cs_vn(
            project=self.project_name, vn=self.vn_name, refresh=True)
        if not self.api_s_vn_obj:
            self.logger.warn("VN %s is not found in API-Server" %
                             (self.vn_name))
            self.api_verification_flag = self.api_verification_flag and False
            return False
        if self.api_s_vn_obj['virtual-network']['uuid'] != self.vn_id:
            self.logger.warn(
                "VN Object ID %s in API-Server is not what was created" % (self.vn_id))
            self.api_verification_flag = self.api_verification_flag and False
            return False

        subnets = self.api_s_vn_obj[
            'virtual-network']['network_ipam_refs'][0]['attr']['ipam_subnets']
        for vn_subnet in self.vn_subnets:
            subnet_found = False
            for subnet in subnets:
                if subnet['subnet']['ip_prefix'] == str(IPNetwork(vn_subnet).ip):
                    subnet_found = True
            if not subnet_found:
                self.logger.warn(
                    "VN Subnet IP %s not found in API-Server for VN %s" %
                    (IPNetwork(vn_subnet).ip, self.vn_name))
                self.api_verification_flag = self.api_verification_flag and False
                return False
        # end for
        self.api_s_route_targets = self.api_s_inspect.get_cs_route_targets(
            vn_id=self.vn_id)
        if not self.api_s_route_targets:
            errmsg = "Route targets not found in API-Server for VN %s" % self.vn_name
            self.logger.error(errmsg)
            self.api_verification_flag = self.api_verification_flag and False
            return False
        self.rt_names = self.api_s_inspect.get_cs_rt_names(
            self.api_s_route_targets)
        self.api_verification_flag = self.api_verification_flag and True
        self.logger.info("Verifications in API Server for VN %s passed" %
                         (self.vn_name))
        self.api_s_routing_instance = self.api_s_inspect.get_cs_routing_instances(
            vn_id=self.vn_id)
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
                self.logger.info("Attached policy in vn %s uve %s" %
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
                self.logger.warn("Attached policy not deleted in vn %s uve" %
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
        vn = self.vnc_lib_h.virtual_network_read(id=self.vn_id)
        if vn:
            pol_list_ref = vn.get_network_policy_refs()
            if pol_list_ref:
                for pol in pol_list_ref:
                    pol_name_list.append(str(pol['to'][2]))
        if pol_name_list:
            for pol in pol_name_list:
                pol_object = self.api_s_inspect.get_cs_policy(
                    policy=pol, refresh=True)
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
                        self.logger.info(
                            "Local VN: %s, skip the VNs in this rule as the local VN is not listed & the rule is a no-op: %s" %
                            (self.vn_fq_name, rule_vns))
        return allowed_peer_vns

    def verify_vn_policy_in_api_server(self):
        ''' verify VN's policy data in api-server with data in quantum database'''
        me = inspect.getframeinfo(inspect.currentframe())[2]
        result = True
        err_msg = []
        out = None
        self.logger.info(
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
            self.logger.debug("Data in Quantum: \n")
            for policy in self.policy_objs:
                self.logger.debug('%s, %s' %
                                  (policy['policy']['id'], policy['policy']['fq_name']))

        # Compare attached policy_fq_names & uuid's
        for policy in vn_pol:
            fqn = policy['to']
            id = policy['uuid']
            self.logger.info(
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
        self.logger.info("verification: %s, status: %s" % (me, result))
        self.policy_verification_flag = {'result': result, 'msg': err_msg}
        return {'result': result, 'msg': err_msg}

   # end verify_vn_policy_in_api_server

    @retry(delay=5, tries=3)
    def verify_vn_not_in_api_server(self):
        '''Verify that VN is removed in API Server.

        '''
        if self.api_s_inspect.get_cs_vn(project=self.project_name, vn=self.vn_name, refresh=True):
            self.logger.warn("VN %s is still found in API-Server" %
                             (self.vn_name))
            self.not_in_api_verification_flag = False
            return False
        self.logger.info("VN %s is not found in API Server" % (self.vn_name))
        self.not_in_api_verification_flag = True
        return True
    # end verify_vn_not_in_api_server

    @retry(delay=5, tries=5)
    def verify_vn_in_control_nodes(self):
        """ Checks for VN details in Control-nodes.

        False if RT does not match the RT from API-Server for each of control-nodes
        """
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
                self.logger.warn(
                    'IFMAP View of Control-node is not having the VN detail of %s' % (self.vn_fq_name))
                self.cn_verification_flag = self.cn_verification_flag and False
                return False
            # TODO UUID verification to be done once the API is available
            cn_object = self.cn_inspect[
                cn].get_cn_routing_instance(ri_name=self.ri_name)
            if not cn_object:
                self.logger.warn(
                    'No Routing Instance found in CN %s with name %s' %
                    (cn, self.ri_name))
                self.cn_verification_flag = self.cn_verification_flag and False
                return False
            try:
                rt_names = self.api_s_inspect.get_cs_rt_names(
                    self.api_s_route_targets)
                if cn_object['export_target'][0] not in rt_names:
                    self.logger.warn(
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
            'Control-node Config, RI and RT verification for VN %s passed' %
            (self.vn_name))
        self.cn_verification_flag = self.cn_verification_flag and True
        return True
    # end verify_vn_in_control_node

    def verify_vn_policy_not_in_api_server(self, policy_name):
        ''' verify VN's policy data in removed api-server'''
        self.logger.info(
            "====Verifying policy %s data removed from %s in API_Server ======" %
            (policy_name, self.vn_name))
        found = False

        # Get VN object from API Server
        vn = self.vnc_lib_h.virtual_network_read(id=self.vn_id)
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
                self.logger.info("Policy info is found in API-Server")
                break
        if not found:
            self.logger.info("Policy info is not found in API-Server")
        return found
    # end verify_vn_policy_not_in_api_server

    @retry(delay=5, tries=10)
    def verify_vn_not_in_control_nodes(self):
        '''Verify that VN details are not in any Control-node

        '''
        result = True
        self.not_in_cn_verification_flag = True
        for cn in self.inputs.bgp_ips:
            cn_object = self.cn_inspect[
                cn].get_cn_routing_instance(ri_name=self.ri_name)
            if cn_object:
                self.logger.warn(
                    "Routing instance for VN %s is still found in Control-node %s" % (self.vn_name, cn))
                result = result and False
                self.not_in_cn_verification_flag = result
        # end for
        if self.cn_inspect[cn].get_cn_config_vn(vn_name=self.vn_name, project=self.project_name):
            self.logger.warn("Control-node config DB still has VN %s" %
                             (self.vn_name))
            #import pdb; pdb.set_trace()
            result = result and False
            self.not_in_cn_verification_flag = result

        if result:
            self.logger.info(
                "Routing instances and Config db in Control-nodes does not have VN %s info" % (self.vn_name))
        return result
    # end verify_vn_not_in_control_nodes

    @retry(delay=5, tries=3)
    def verify_vn_not_in_agent(self):
        ''' Verify that VN is removed in all agent nodes.
        '''
        for compute_ip in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[compute_ip]
            vn = inspect_h.get_vna_vn(
                project=self.project_name, vn_name=self.vn_name)
            print vn
            if vn:
                self.logger.warn('VN %s is still found in %s ' %
                                 (self.vn_name, compute_ip))
                return False
                self.not_in_agent_verification_flag = False
            vrf_objs = inspect_h.get_vna_vrf_objs(
                project=self.project_name, vn_name=self.vn_name)
            if len(vrf_objs['vrf_list']) != 0:
                self.logger.warn(
                    'VRF %s for VN %s is still found in agent %s' %
                    (str(self.vrf_name), self.vn_name, compute_ip))
                self.not_in_agent_verification_flag = False
                return False
            self.logger.info('VN %s is not present in Agent %s ' %
                             (self.vn_name, compute_ip))
        # end for
        self.not_in_agent_verification_flag = True
        return True
    # end verify_vn_not_in_agent

    def verify_vn_in_opserver(self):
        '''Verify vn in the opserver'''

        self.logger.info("Verifying the vn in opserver")
        res = self.analytics_obj.verify_vn_link(self.vn_fq_name)
        self.op_verification_flag = res
        return res

    def del_host_route(self, prefix):
        vnc_lib = self.vnc_lib_h
        vn_obj = vnc_lib.virtual_network_read(
            fq_name=self.vn_fq_name.split(':'))
        if prefix == vn_obj.get_network_ipam_refs()[0]['attr'].get_host_routes().route[0].get_prefix():
            self.logger.info('Deleting %s from the host_routes via %s in %s' %
                             (prefix, self.ipam_fq_name[-1], self.vn_name))
            vn_obj.get_network_ipam_refs()[0]['attr'].get_host_routes().delete_route(
                vn_obj.get_network_ipam_refs()[0]['attr'].get_host_routes().route[0])
        else:
            self.logger.error('No such host_route seen')
        vnc_lib.virtual_network_update(vn_obj)
    # end add_host_route

    def del_host_routes(self, prefixes):
        vnc_lib = self.vnc_lib_h
        vn_obj = vnc_lib.virtual_network_read(
            fq_name=self.vn_fq_name.split(':'))
        for prefix in prefixes:
            if prefix == vn_obj.get_network_ipam_refs()[0]['attr'].get_host_routes().route[0].get_prefix():
                self.logger.info(
                    'Deleting %s from the host_routes via %s in %s' %
                    (prefix, self.ipam_fq_name[-1], self.vn_name))
                vn_obj.get_network_ipam_refs()[0]['attr'].get_host_routes().delete_route(
                    vn_obj.get_network_ipam_refs()[0]['attr'].get_host_routes().route[0])
                vn_obj._pending_field_updates.add('network_ipam_refs')
                vnc_lib.virtual_network_update(vn_obj)
            else:
                self.logger.error('No such host_route seen')
    # end delete_host_routes

    def add_host_route(self, prefix):
        vnc_lib = self.vnc_lib_h
        self.logger.info('Adding %s as host_route via %s in %s' %
                         (prefix, self.ipam_fq_name[-1], self.vn_name))
        vn_obj = vnc_lib.virtual_network_read(
            fq_name=self.vn_fq_name.split(':'))
        vn_obj.get_network_ipam_refs()[0]['attr'].set_host_routes(
            RouteTableType([RouteType(prefix=prefix)]))
        vnc_lib.virtual_network_update(vn_obj)
    # end add_host_route

    def add_host_routes(self, prefixes):
        list_of_prefix = []
        vnc_lib = self.vnc_lib_h
        self.logger.info('Adding %s as host_route via %s in %s' %
                         (prefixes, self.ipam_fq_name[-1], self.vn_name))
        vn_obj = vnc_lib.virtual_network_read(
            fq_name=self.vn_fq_name.split(':'))
        for prefix in prefixes:
            list_of_prefix.append(RouteType(prefix=prefix))
        vn_obj.get_network_ipam_refs()[0]['attr'].set_host_routes(
            RouteTableType(list_of_prefix))
        vn_obj._pending_field_updates.add('network_ipam_refs')
        vnc_lib.virtual_network_update(vn_obj)
    # end add_host_routes

    def add_route_target(self, routing_instance_name, router_asn, route_target_number):
        vnc_lib = self.vnc_lib_h

        rt_inst_fq_name = routing_instance_name.split(':')
        rtgt_val = "target:%s:%s" % (router_asn, route_target_number)
        net_obj = vnc_lib.virtual_network_read(fq_name=rt_inst_fq_name[:-1])
        route_targets = net_obj.get_route_target_list()
        if route_targets:
            route_targets.add_route_target(rtgt_val)
        else:
            route_targets = RouteTargetList([rtgt_val])
        net_obj.set_route_target_list(route_targets)

        vnc_lib.virtual_network_update(net_obj)
    # end add_route_target

    def del_route_target(self, routing_instance_name, router_asn, route_target_number):

        result = True
        vnc_lib = self.vnc_lib_h

        rt_inst_fq_name = routing_instance_name.split(':')
        rtgt_val = "target:%s:%s" % (router_asn, route_target_number)
        net_obj = vnc_lib.virtual_network_read(fq_name=rt_inst_fq_name[:-1])

        if rtgt_val not in net_obj.get_route_target_list().get_route_target():
            self.logger.error("%s not configured for VN %s" %
                              (rtgt_val, rt_inst_fq_name[:-1]))
            result = False

        net_obj.get_route_target_list().get_route_target().remove(rtgt_val)
        vnc_lib.virtual_network_update(net_obj)
        return result
    # end del_route_target

    def verify_vn_route_target(self, policy_peer_vns):
        ''' For expected rt_import data, we need to inspect policy attached to both the VNs under test..
        Both VNs need to have rule in policy with action as pass to other VN..
        This data needs to come from calling test code as policy_peer_vns'''
        self.policy_peer_vns = policy_peer_vns
        compare = False
        cn = self.inputs.bgp_ips[0]
        cn_ref = self.cn_inspect[cn]
        vn_ri = cn_ref.get_cn_routing_instance(ri_name=self.ri_name)
        act_rt_import = vn_ri['import_target']
        act_rt_export = vn_ri['export_target']
        exp_rt = self.get_rt_info()
        compare_rt_export = policy_test_utils.compare_list(
            exp_rt['rt_export'], act_rt_export)
        compare_rt_import = policy_test_utils.compare_list(
            exp_rt['rt_import'], act_rt_import)

        if (compare_rt_export and compare_rt_import):
            compare = True
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
        # Get the Quantum details
        quantum_obj = self.quantum_fixture.get_vn_obj_if_present(self.vn_name,
                                                                 self.project_id)
        cidr = unicode(subnet)
        #ipam_fq_name = quantum_obj['network']['contrail:subnet_ipam'][0]['ipam_fq_name']
        ipam_fq_name = None
        net_id = quantum_obj['network']['id']

        # Create subnet
        self.quantum_fixture.create_subnet(cidr, net_id, ipam_fq_name)
    # end add_subnet

    def set_vxlan_network_identifier_mode(self, mode):
        vnc_lib = self.vnc_lib_h
        # Set vxlan identifier mode using gloabl vrouter config
        conf_obj = GlobalVrouterConfig(vxlan_network_identifier_mode=mode)
        vnc_lib.global_vrouter_config_update(conf_obj)
    # end set_vxlan_network_identifier_mode

    def add_vxlan_id(self, project_fq_name, vn_name, vxlan_id):
        vnc_lib = self.vnc_lib_h
        # First set vxlan identifier mode to configured but it should be
        # changed back to automatic
        self.set_vxlan_network_identifier_mode(mode='configured')
        # Figure out VN

        vni_list = vnc_lib.virtual_networks_list(
            parent_fq_name=project_fq_name)['virtual-networks']
        for vni_record in vni_list:
            if (vni_record['fq_name'][0] == project_fq_name[0] and
                vni_record['fq_name'][1] == project_fq_name[1] and
                    vni_record['fq_name'][2] == vn_name):
                vni_obj = vnc_lib.virtual_network_read(id=vni_record['uuid'])
                if (vxlan_id is not None):
                    # Update vxlan id as provided
                    vni_obj_properties = vni_obj.get_virtual_network_properties(
                    ) or VirtualNetworkType()
                    vni_obj_properties.set_vxlan_network_identifier(
                        int(vxlan_id))
                    vni_obj.set_virtual_network_properties(vni_obj_properties)
                    vnc_lib.virtual_network_update(vni_obj)
    # end add_vxlan_id

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
            if self.vn_id in self.vn_with_route_target:
                self.logger.info('Deleting RT for VN %s ' % (self.vn_name))
                self.del_route_target(
                    self.ri_name, self.router_asn, self.rt_number)
            self.logger.info("Deleting the VN %s " % self.vn_name)
            if self.inputs.webui_config_flag:
                self.webui.vn_delete_in_webui(self)
            elif (self.option == 'api'):
                self.logger.info("Deleting the VN %s using Api server" %
                                 self.vn_name)
                self.vnc_lib_h.virtual_network_delete(id=self.vn_id)
            else:
                for i in range(12):
                    if not self.quantum_fixture.delete_vn(self.vn_id):
                        # This might be due to caching issues.
                        self.logger.warn("%s. Deleting the VN %s failed" %
                                         (i, self.vn_name))
                        self.logger.info("%s. Retry deleting the VN %s " %
                                         (i, self.vn_name))
                        sleep(10)
                    else:
                        break
            if self.verify_is_run:
                t_api = threading.Thread(
                    target=self.verify_vn_not_in_api_server, args=())
                #t_api.daemon = True
                t_api.start()
                time.sleep(1)
                t_cn = threading.Thread(
                    target=self.verify_vn_not_in_control_nodes, args=())
                t_cn.start()
                time.sleep(1)
                t_agent = threading.Thread(
                    target=self.verify_vn_not_in_agent, args=())
                #t_agent.daemon = True
                t_agent.start()
                time.sleep(1)
                self.logger.info(
                    'Printing Not in API verification flag VN %s %s ' %
                    (self.vn_name, self.not_in_api_verification_flag))
                self.logger.info(
                    'Printing Not in Control Node verification flag VN %s %s ' %
                    (self.vn_name, self.not_in_cn_verification_flag))
                self.logger.info(
                    'Printing Not in Agent verification flag VN %s %s' %
                    (self.vn_name, self.not_in_agent_verification_flag))
                self.verify_not_in_result = self.not_in_api_verification_flag and self.not_in_cn_verification_flag and self.not_in_agent_verification_flag
                #assert self.not_in_api_verification_flag
                #assert self.not_in_cn_verification_flag
                #assert self.not_in_agent_verification_flag
                # t_api.join()
                self.logger.info('Printing verify not in result VN %s %s' %
                                 (self.vn_name, self.verify_not_in_result))
                t_cn.join()
                t_agent.join()
                t_api.join()
                assert self.verify_vn_not_in_api_server()
                assert self.verify_vn_not_in_agent()
                assert self.verify_vn_not_in_control_nodes()
        else:
            self.logger.info('Skipping the deletion of the VN %s ' %
                             (self.vn_name))
    # end cleanUp

    def get_obj(self):
        return self.vn_obj
    # end get_obj

    def bind_policies(self, policy_fq_names, vn_id):
        net_rsp = {}
        project_name = self.project_name
        if len(policy_fq_names) != 0:
            project_name = policy_fq_names[0][1]
            net_req = {'contrail:policys': policy_fq_names}
            net_rsp = self.quantum_fixture.update_network(
                vn_id, {'network': net_req})
            self.logger.debug(
                'Response for mapping policy(s) with vn ' + str(net_rsp))
        # Update VN obj
        self.update_vn_object()
        return net_rsp
    # end bind_policy

    def get_current_policies_bound(self):
        self.api_vn_obj = self.vnc_lib_h.virtual_network_read(id=self.vn_id)
        api_policy_refs = self.api_vn_obj.get_network_policy_refs()
        if not api_policy_refs:
            return []
        api_policy_fq_names = [item['to'] for item in api_policy_refs]
        return api_policy_fq_names
    # end get_current_policies_bound

    def update_vn_object(self):
        self.obj = self.quantum_fixture.get_vn_obj_from_id(self.vn_id)
        self.policy_objs = []
        policies_bound = self.get_current_policies_bound()
        for policy_fq_name in self.get_current_policies_bound():
            self.policy_objs.append(
                self.quantum_fixture.get_policy_if_present(policy_fq_name[1], policy_fq_name[2]))
    # end update_vn_object

    def unbind_policies(self, vn_id, policy_fq_names=[]):
        current_obj = self.quantum_fixture.obj.show_network(network=vn_id)
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
        net_rsp = self.quantum_fixture.update_network(
            vn_id, {'network': net_req})

        self.update_vn_object()
        return net_rsp
    # end unbind_policy
# end VNFixture


class MultipleVNFixture(fixtures.Fixture):

    """ Fixture to create, verify and delete multiple VNs and multiple subnets
        each.

        Deletion of the VN upon exit can be disabled by setting
        fixtureCleanup=no. If a VN with the vn_name is already present, it is
        not deleted upon exit. Use fixtureCleanup=force to force a delete.
    """

    def __init__(self, connections, inputs, vn_count=1, subnet_count=1,
                 vn_name_net={},  project_name='admin'):
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
                                        'vn2' : ['30.1.1.0/30', '30.1.2.0/30']})
        Creates VN's vn1 and vn2, with 20 subnets in vn1 and 2 subnets in vn2.
        """
        self.inputs = inputs
        self.connections = connections
        self.project_name = project_name
        self.vn_count = vn_count
        self.subnet_count = subnet_count
        self.vn_name_net = vn_name_net
        self.logger = inputs.logger
        self._vn_subnets = self._find_subnets()

    def _subnet(self, network='10.0.0.0/8', subnet_count=None, roll_over=False):
        vn_count = self.vn_count
        if not subnet_count:
            subnet_count = self.vn_count * self.subnet_count
        net, prefix = network.split('/')
        for subnet_prefix in range((int(prefix) + 1), 31):
            subnets = list(IPNetwork(network).subnet(subnet_prefix))
            if len(subnets) >= subnet_count:
                return map(lambda subnet: subnet.__str__(),
                           subnets[:subnet_count])

        if not roll_over:
            max_subnets = len(list(IPNetwork(network).subnet(30)))
            raise NotPossibleToSubnet("Network prefix  %s can be subnetted "
                                      "only to maximum of %s subnets" % (network, max_subnets))

        octets = net.split('.')
        first_octet = int(octets[0])
        octests = octets[1:]
        next_net = octets.insert(0, first_octet + 1)
        count = subnet_count - len(subnets)
        self.logger.debug("Rolling over to next network prefix %s.", next_net)
        subnets += self._subnet(network=next_net, subnet_count=count)
        return map(lambda subnet: subnet.__str__(), subnets[:count])

    def _find_subnets(self):
        vn_subnets = {}
        if not self.vn_name_net:
            subnets = self._subnet(roll_over=True)
            start = 0
            end = self.subnet_count
            for i in range(self.vn_count):
                vn_subnets.update({'vn%s' % (i + 1): subnets[start:end]})
                start = start + self.subnet_count
                end = end + self.subnet_count
            return vn_subnets
        for vn_name, net in self.vn_name_net.items():
            if type(net) is list:
                vn_subnets.update({vn_name: net})
            else:
                vn_subnets.update(
                    {vn_name: self._subnet(net, self.subnet_count)})
        return vn_subnets

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
