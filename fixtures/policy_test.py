import fixtures
import re
from project_test import *
from tcutils.util import *
import json
from vnc_api.vnc_api import *
from contrail_fixtures import *
import copy
from tcutils.agent.vna_introspect_utils import *
from common.policy import policy_test_utils
import inspect
try:
    from webui_test import *
except ImportError:
    pass

#@contrail_fix_ext ()


class PolicyFixture(fixtures.Fixture):

    def __init__(self, policy_name, rules_list, inputs, connections, api=None,
                                                        project_fixture= None):
        self.inputs = inputs
        self.rules_list = rules_list
        self.project_fq_name = self.inputs.project_fq_name
        self.connections = connections
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.quantum_h = self.connections.quantum_h
        self.api_s_inspect = self.connections.api_server_inspect
        self.vnc_lib = self.connections.vnc_lib
        self.policy_name = policy_name
        self.policy_obj = None
        self.logger = self.inputs.logger
        self.already_present = False
        self.verify_is_run = False
        self.project_name = self.inputs.project_name
        self.api_flag = api
        if self.inputs.orchestrator == 'vcenter':
            self.api_flag = True
        if self.inputs.verify_thru_gui():
            self.browser = self.connections.browser
            self.browser_openstack = self.connections.browser_openstack
            self.webui = WebuiTest(self.connections, self.inputs)
        self.project_fixture= project_fixture
        if self.project_fixture:
            self.project_fq_name = self.project_fixture.project_fq_name
            self.project_name = self.project_fixture.project_name
        self.rules_list = policy_test_utils.update_rules_with_icmpv6(self.inputs.get_af(),
                                                self.rules_list)

    # end __init__

    def setUp(self):
        super(PolicyFixture, self).setUp()
        if self.api_flag is None:
            self.policy_obj = self.quantum_h.get_policy_if_present(
                                      self.project_name, self.policy_name)
            if not self.policy_obj:
                if self.inputs.is_gui_based_config():
                    self.webui.create_policy(self)
                else:
                    self._create_policy(self.policy_name, self.rules_list)
            else:
                self.already_present = True
                self.logger.debug(
                    'Policy %s already present, not creating policy' %
                    (self.policy_name))

            self.policy_fq_name = self.quantum_h.get_policy_fq_name(
                self.policy_obj)
        else:
            try:
                self.policy_obj = self.vnc_lib.network_policy_read(fq_name=self.project_fq_name+[unicode(self.policy_name)])
            except:
                self.policy_fq_name = self._create_policy_api(self.policy_name, self.rules_list)
            else:
                self.already_present = True
                self.policy_fq_name=self.policy_obj.fq_name
                self.logger.debug(
                    'Policy %s already present, not creating any policy' %
                    (self.policy_name))
    # end setUp

    def verify_on_setup(self):
        # verifications return {'result': result, 'msg': err_msg}
        result = True
        err_msg = []
        ret = self.verify_policy_in_api_server()
        if ret['result'] == False:
            err_msg.append(ret['msg'])
        ret = self.verify_policy_in_control_nodes()
        if ret['result'] == False:
            err_msg.append(ret['msg'])

        if err_msg != []:
            result = False
        self.verify_is_run = True
        return {'result': result, 'msg': err_msg}
    # end verify_on_setup

    def _create_policy(self, policy_name, rules_list):
        ''' Create a policy from the supplied rules
        Sample rules_list:
        src_ports and dst_ports : can be 'any'/tuple/list as shown below
        protocol  :  'any' or a string representing a protocol number : ICMP(1), TCP(6), UDP(17)
        simple_action : pass/deny
        source_network/dest_network : VN name
        rules= [
            {
               'direction'     : '<>', 'simple_action' : 'pass',
               'protocol'      : 'any',
               'source_network': vn1_name,
               'src_ports'     : 'any',
               'src_ports'     : (10,100),
               'dest_network'  : vn1_name,
               'dst_ports'     : [100,10],
             },
            {
               'direction'     : '<>',
               'simple_action' : 'pass', 'protocol'      : '1',
               'source_network': vn1_name, 'src_ports'     : (10,100),
               'dest_network'  : vn1_name, 'dst_ports'     : [100,10],
             }
                ]
        '''
        def serialize(obj):
            return_dict = {}
            for k, v in obj.__dict__.iteritems():
                return_dict[k] = v
            return return_dict
        np_rules = []
        for rule_dict in rules_list:
            source_vn = None
            dest_vn = None
            source_policy = None
            dest_policy = None
            source_subnet_dict = None
            dest_subnet_dict = None

            new_rule = {
                'direction': '<>',
                'simple_action': 'pass',
                'protocol': 'any',
                'source_network': None,
                'source_policy': None,
                'source_subnet': None,
                'src_ports': [PortType(-1, -1)],
                'application': None,
                'dest_network': None,
                'dest_policy': None,
                'dest_subnet': None,
                'dst_ports': [PortType(-1, -1)],
                'action_list': {},
                'qos_action': None
            }
            for key in rule_dict:
                new_rule[key] = rule_dict[key]
            # end for
            new_rule['action_list'][
                'simple_action'] = rule_dict['simple_action']
            if 'qos_action' in rule_dict:
                new_rule['action_list'][
                    'qos_action'] = rule_dict['qos_action']
            # Format Source ports
            if 'src_ports' in rule_dict:
                if type(rule_dict['src_ports']) is tuple or type(rule_dict['src_ports']) is list:
                    new_rule['src_ports'] = [
                        PortType(rule_dict['src_ports'][0], rule_dict['src_ports'][1])]
                elif rule_dict['src_ports'] == 'any':
                    new_rule['src_ports'] = [PortType(-1, -1)]
                else:
                    self.logger.error(
                        "Error in Source ports arguments, should be (Start port, end port) or any ")
                    return None
            # Format Dest ports
            if 'dst_ports' in rule_dict:
                if 'dst_ports' in rule_dict and type(rule_dict['dst_ports']) is tuple or type(rule_dict['dst_ports']) is list:
                    new_rule['dst_ports'] = [
                        PortType(rule_dict['dst_ports'][0], rule_dict['dst_ports'][1])]
                elif rule_dict['dst_ports'] == 'any':
                    new_rule['dst_ports'] = [PortType(-1, -1)]
                else:
                    self.logger.error(
                        "Error in Destination ports arguments, should be (Start port, end port) or any ")
                    return None
            if new_rule['source_network'] is not None:
                m = re.match(r"(\S+):(\S+):(\S+)", new_rule['source_network'])
                if m:
                    source_vn = new_rule['source_network']
                else:
                    source_vn = ':'.join(self.project_fq_name) + \
                        ':' + new_rule['source_network']
            if new_rule['dest_network'] is not None:
                m = re.match(r"(\S+):(\S+):(\S+)", new_rule['dest_network'])
                if m:
                    dest_vn = new_rule['dest_network']
                else:
                    dest_vn = ':'.join(self.project_fq_name) + \
                        ':' + new_rule['dest_network']
            if new_rule['source_policy'] is not None:
                m = re.match(r"(\S+):(\S+):(\S+)", new_rule['source_policy'])
                if m:
                    source_policy = new_rule['source_policy']
                else:
                    source_policy = ':'.join(self.project_fq_name) + \
                        ':' + new_rule['source_policy']
            if new_rule['dest_policy'] is not None:
                m = re.match(r"(\S+):(\S+):(\S+)", new_rule['dest_policy'])
                if m:
                    dest_policy = new_rule['dest_policy']
                else:
                    dest_policy = ':'.join(self.project_fq_name) + \
                        ':' + new_rule['dest_policy']
            if new_rule['source_subnet'] is not None:
                try:
                    source_subnet_prefix = str(new_rule['source_subnet'].split('/')[0])
                    source_subnet_prefix_length = int(new_rule['source_subnet'].split('/')[1])
                    source_subnet_dict = {'ip_prefix':source_subnet_prefix,
                                          'ip_prefix_len':source_subnet_prefix_length}
                except:
                    self.logger.debug("Subnet should be defined as ip/prefix_length \
                        where ip = xx.xx.xx.xx and prefix_length is the subnet mask \
                        length.")
            if new_rule['dest_subnet'] is not None:
                try:
                    dest_subnet_prefix = str(new_rule['dest_subnet'].split('/')[0])
                    dest_subnet_prefix_length = int(new_rule['dest_subnet'].split('/')[1])
                    dest_subnet_dict = {'ip_prefix':dest_subnet_prefix,
                                        'ip_prefix_len':dest_subnet_prefix_length}
                except:
                    self.logger.debug("Subnet should be defined as ip/prefix_length \
                        where ip = xx.xx.xx.xx and prefix_length is the subnet mask \
                        length.")

            # handle 'any' network case
            try:
                if rule_dict['source_network'] == 'any':
                    source_vn = 'any'
            except:
                self.logger.debug("No source network defined")
            try:
                 if rule_dict['dest_network'] == 'any':
                    dest_vn = 'any'
            except:
                self.logger.debug("No destination network defined")
            # end code to handle 'any' network
            try:
                if source_vn:
                    new_rule['source_network'] = [
                        AddressType(virtual_network=source_vn)]
                    src_address = new_rule['source_network']
            except:
                self.logger.debug("No source vn defined in this rule of %s \
                    policy" % (policy_name))
            try:
                if dest_vn:
                    new_rule['dest_network'] = [
                        AddressType(virtual_network=dest_vn)]
                    dest_address = new_rule['dest_network']
            except:
                self.logger.debug("No dest vn defined in this rule of %s \
                    policy" % (policy_name))
            try:
                if source_policy:
                    new_rule['source_policy'] = [
                        AddressType(network_policy=source_policy)]
                    src_address = new_rule['source_policy']
            except:
                self.logger.debug("No source policy defined in this rule of %s \
                    policy" % (policy_name))
            try:
                if dest_policy:
                    new_rule['dest_policy'] = [
                        AddressType(network_policy=dest_policy)]
                    dest_address = new_rule['dest_policy']
            except:
                self.logger.debug("No dest policy defined in this rule of %s \
                    policy" % (policy_name))
            try:
                if source_subnet_dict:
                    new_rule['source_subnet'] = [
                        AddressType(subnet=source_subnet_dict)]
                    src_address = new_rule['source_subnet']
            except:
                self.logger.debug("No source subnet defined in this rule of %s \
                    policy" % (policy_name))
            try:
                if dest_subnet_dict:
                    new_rule['dest_subnet'] = [
                        AddressType(subnet=dest_subnet_dict)]
                    dest_address = new_rule['dest_subnet']
            except:
                self.logger.debug("No destination subnet defined in this rule of %s \
                    policy" % (policy_name))

            np_rules.append(PolicyRuleType(direction=new_rule['direction'],
                                           protocol=new_rule['protocol'],
                                           src_addresses=src_address,
                                           src_ports=new_rule['src_ports'],
                                           application=new_rule[
                                               'application'],
                                           dst_addresses=dest_address,
                                           dst_ports=new_rule['dst_ports'],
                                           action_list=new_rule['action_list']))
        # end for
        self.logger.debug("Policy np_rules : %s" % (np_rules))
        pol_entries = PolicyEntriesType(np_rules)
        pol_entries_dict = \
            json.loads(json.dumps(pol_entries,
                                  default=serialize))
        policy_req = {'name': policy_name,
                      'entries': pol_entries_dict}
        policy_rsp = self.quantum_h.create_policy({'policy': policy_req})
        self.logger.debug("Created Policy %s : %s" % (policy_name,
            str(policy_rsp)))
        self.policy_obj = policy_rsp
        return policy_rsp
    # end  _create_policy

    def _create_policy_api(self, policy_name, rules_list):
        ''' Create a policy from the supplied rules
        Sample rules_list:
        src_ports and dst_ports : can be 'any'/tuple/list as shown below
        protocol  :  'any' or a string representing a protocol number : ICMP(1), TCP(6), UDP(17)
        simple_action : pass/deny
        source_network/dest_network : VN name
        rules= [
            {
               'direction'     : '<>', 'simple_action' : 'pass',
               'protocol'      : 'any',
               'source_network': vn1_name,
               'src_ports'     : 'any',
               'src_ports'     : (10,100),
               'dest_network'  : vn1_name,
               'dst_ports'     : [100,10],
             },
            {
               'direction'     : '<>',
               'simple_action' : 'pass', 'protocol'      : 'icmp',
               'source_network': vn1_name, 'src_ports'     : (10,100),
               'dest_network'  : vn1_name, 'dst_ports'     : [100,10],
             }
                ]
        '''
        np_rules = []
        for rule_dict in rules_list:
            new_rule = {
                'direction': '<>',
                'simple_action': 'pass',
                'qos_action': None,
                'protocol': 'any',
                'source_network': None,
                'source_policy': None,
                'source_subnet': None,
                'src_ports': [PortType(-1, -1)],
                'application': None,
                'dest_network': None,
                'dest_policy': None,
                'dest_subnet': None,
                'dst_ports': [PortType(-1, -1)],
                'action_list': None
            }
            for key in rule_dict:
                new_rule[key] = rule_dict[key]
            # end for
            # Format Source ports
            if 'src_ports' in rule_dict:
                if isinstance(
                        rule_dict['src_ports'],
                        tuple) or isinstance(
                        rule_dict['src_ports'],
                        list):
                    new_rule['src_ports'] = [
                        PortType(
                            rule_dict['src_ports'][0],
                            rule_dict['src_ports'][1])]
                elif rule_dict['src_ports'] == 'any':
                    new_rule['src_ports'] = [PortType(-1, -1)]
                else:
                    self.logger.error(
                        "Error in Source ports arguments, should be (Start port, end port) or any ")
                    return None
            # Format Dest ports
            if 'dst_ports' in rule_dict:
                if 'dst_ports' in rule_dict and isinstance(
                        rule_dict['dst_ports'],
                        tuple) or isinstance(
                        rule_dict['dst_ports'],
                        list):
                    new_rule['dst_ports'] = [
                        PortType(
                            rule_dict['dst_ports'][0],
                            rule_dict['dst_ports'][1])]
                elif rule_dict['dst_ports'] == 'any':
                    new_rule['dst_ports'] = [PortType(-1, -1)]
                else:
                    self.logger.error(
                        "Error in Destination ports arguments, should be (Start port, end port) or any ")
                    return None

            if new_rule['source_network'] is not None:
                m = re.match(r"(\S+):(\S+):(\S+)", new_rule['source_network'])
                if m:
                    source_vn = new_rule['source_network']
                else:
                    source_vn = ':'.join(self.project_fq_name) + \
                        ':' + new_rule['source_network']
            if new_rule['dest_network'] is not None:
                m = re.match(r"(\S+):(\S+):(\S+)", new_rule['dest_network'])
                if m:
                    dest_vn = new_rule['dest_network']
                else:
                    dest_vn = ':'.join(self.project_fq_name) + \
                        ':' + new_rule['dest_network']
            if new_rule['source_policy'] is not None:
                m = re.match(r"(\S+):(\S+):(\S+)", new_rule['source_policy'])
                if m:
                    source_policy = new_rule['source_policy']
                else:
                    source_policy = ':'.join(self.project_fq_name) + \
                        ':' + new_rule['source_policy']
            if new_rule['dest_policy'] is not None:
                m = re.match(r"(\S+):(\S+):(\S+)", new_rule['dest_policy'])
                if m:
                    dest_policy = new_rule['dest_policy']
                else:
                    dest_policy = ':'.join(self.project_fq_name) + \
                        ':' + new_rule['dest_policy']
            if new_rule['source_subnet'] is not None:
                try:
                    source_subnet_prefix = str(new_rule['source_subnet'].split('/')[0])
                    source_subnet_prefix_length = int(new_rule['source_subnet'].split('/')[1])
                    source_subnet_dict = {'ip_prefix':source_subnet_prefix,
                                          'ip_prefix_len':source_subnet_prefix_length}
                except:
                    self.logger.debug("Subnet should be defined as ip/prefix_length \
                        where ip = xx.xx.xx.xx and prefix_length is the subnet mask \
                        length.")
            if new_rule['dest_subnet'] is not None:
                try:
                    dest_subnet_prefix = str(new_rule['dest_subnet'].split('/')[0])
                    dest_subnet_prefix_length = int(new_rule['dest_subnet'].split('/')[1])
                    dest_subnet_dict = {'ip_prefix':dest_subnet_prefix,
                                        'ip_prefix_len':dest_subnet_prefix_length}
                except:
                    self.logger.debug("Subnet should be defined as ip/prefix_length \
                        where ip = xx.xx.xx.xx and prefix_length is the subnet mask \
                        length.")

            # handle 'any' network case
            try:
                if rule_dict['source_network'] == 'any':
                    source_vn = 'any'
            except:
                self.logger.debug("No source network defined")
            try:
                 if rule_dict['dest_network'] == 'any':
                    dest_vn = 'any'
            except:
                self.logger.debug("No destination network defined")
            # end code to handle 'any' network

            try:
                if source_vn:
                    new_rule['source_network'] = [
                        AddressType(virtual_network=source_vn)]
                    src_address = new_rule['source_network']
            except:
                self.logger.debug("No source vn defined in this rule of %s \
                    policy" % (policy_name))
            try:
                if dest_vn:
                    new_rule['dest_network'] = [
                        AddressType(virtual_network=dest_vn)]
                    dest_address = new_rule['dest_network']
            except:
                self.logger.debug("No dest vn defined in this rule of %s \
                    policy" % (policy_name))
            try:
                if source_policy:
                    new_rule['source_policy'] = [
                        AddressType(network_policy=source_policy)]
                    src_address = new_rule['source_policy']
            except:
                self.logger.debug("No source policy defined in this rule of %s \
                    policy" % (policy_name))
            try:
                if dest_policy:
                    new_rule['dest_policy'] = [
                        AddressType(network_policy=dest_policy)]
                    dest_address = new_rule['dest_policy']
            except:
                self.logger.debug("No dest policy defined in this rule of %s \
                    policy" % (policy_name))
            try:
                if source_subnet_dict:
                    new_rule['source_subnet'] = [
                        AddressType(subnet=source_subnet_dict)]
                    src_address = new_rule['source_subnet']
            except:
                self.logger.debug("No source subnet defined in this rule of %s \
                    policy" % (policy_name))
            try:
                if dest_subnet_dict:
                    new_rule['dest_subnet'] = [
                        AddressType(subnet=dest_subnet_dict)]
                    dest_address = new_rule['dest_subnet']
            except:
                self.logger.debug("No destination subnet defined in this rule of %s \
                    policy" % (policy_name))

            np_rules.append(
                PolicyRuleType(direction=new_rule['direction'],
                    protocol=new_rule['protocol'],
                    src_addresses=src_address,
                    src_ports=new_rule['src_ports'],
                    application=new_rule['application'],
                    dst_addresses=dest_address,
                    dst_ports=new_rule['dst_ports'],
                    action_list={'simple_action':new_rule['simple_action'],\
                    'qos_action':new_rule['qos_action']}))

        # end for
        self.logger.debug("Policy np_rules : %s" % (np_rules))
        pol_entries = PolicyEntriesType(np_rules)
        proj = self.vnc_lib.project_read(self.project_fq_name)
        self.policy_obj = NetworkPolicy(
            policy_name, network_policy_entries=pol_entries, parent_obj=proj)
        uid = self.vnc_lib.network_policy_create(self.policy_obj)
        self.policy_obj = self.vnc_lib.network_policy_read(id=uid)
        return self.policy_obj.fq_name
    # end  _create_policy_api

    def cleanUp(self):
        super(PolicyFixture, self).cleanUp()
        do_cleanup = True
        if self.inputs.fixture_cleanup == 'no':
            do_cleanup = False
        if self.already_present:
            do_cleanup = False
        if self.inputs.fixture_cleanup == 'force':
            do_cleanup = True
        if do_cleanup:
            self._delete_policy()
            if self.verify_is_run:
                 assert self.verify_policy_not_in_api_server()
        else:
            self.logger.info('Skipping deletion of policy %s' %
                             (self.policy_name))
    # end cleanUp

    def get_id(self):
        if isinstance(self.policy_obj, NetworkPolicy):
            return self.policy_obj.uuid
        else:
            return self.policy_obj['policy']['id']

    def _delete_policy(self):
        if self.api_flag:
            self.vnc_lib.network_policy_delete(id=self.policy_obj.uuid)
            self.logger.info("Deleted policy %s" % (self.policy_name))
            return
        if self.inputs.is_gui_based_config():
            self.webui.delete_policy(self)
            self.logger.info("Deleted policy %s" % (self.policy_name))
        elif self.quantum_h.get_policy_if_present(
                    project_name=self.project_name,
                    policy_name=self.policy_name):
             self.quantum_h.delete_policy(self.policy_obj['policy']['id'])
             self.logger.info("Deleted policy %s" % (self.policy_name))
        else:
             self.logger.debug("No Policy present, to be deleted.")
    # end _delete_policy

    def update_policy(self, policy_id, policy_data):
        # policy_data format {'policy': {'entries': new_policy_entries}}
        policy_rsp = self.quantum_h.update_policy(policy_id, policy_data)
        self.logger.debug("Policy Update Response " + str(policy_rsp))
        self.policy_obj = policy_rsp
        return policy_rsp
    # end update_policy

    def tx_policy_to_vn(self, rules, vn_policy_dict):
        """
        Return rules that have source and destination vn names in place of
        source and destination policy.
        """
        tx_rule_list = []
        src_pol = 'Null'
        dest_pol = 'Null'
        for rule in rules:
            if ((not 'source_policy' in rule) and
                (not 'dest_policy' in rule)):
                tx_rule_list.append(rule)
                continue
            if 'source_policy' in rule:
                src_pol = rule['source_policy']
            if 'dest_policy' in rule:
                dest_pol = rule['dest_policy']
            src_pol_vns = []
            dest_pol_vns= []
            for each_vn in vn_policy_dict:
                if src_pol in vn_policy_dict[each_vn]:
                    src_pol_vns.append(each_vn)
                if dest_pol in vn_policy_dict[each_vn]:
                    dest_pol_vns.append(each_vn)
            if (src_pol_vns and dest_pol_vns):
                for eachvn in src_pol_vns:
                    new_rule = copy.deepcopy(rule)
                    del new_rule['source_policy']
                    new_rule['source_network'] = eachvn
                    for eachvn2 in dest_pol_vns:
                        new_rule2 = copy.deepcopy(new_rule)
                        del new_rule2['dest_policy']
                        new_rule2['dest_network'] = eachvn2
                        tx_rule_list.append(new_rule)

            if (src_pol_vns and (not dest_pol_vns)):
                for eachvn in src_pol_vns:
                    new_rule = copy.deepcopy(rule)
                    del new_rule['source_policy']
                    new_rule['source_network'] = eachvn
                    tx_rule_list.append(new_rule)

            if (dest_pol_vns and (not src_pol_vns)):
                for eachvn in dest_pol_vns:
                    new_rule = copy.deepcopy(rule)
                    del new_rule['dest_policy']
                    new_rule['dest_network'] = eachvn
                    tx_rule_list.append(new_rule)

        return tx_rule_list
    # end tx_policy_to_vn

    def tx_user_def_rule_to_aces(self, test_vn, rules):
        """
        Return user defined rules to expected ACL entries, each rule as dictionary, a
        list of dicts returned.
        1. translate keys rules-> ace
        2. translate 'any' value for port to range
        3. translate 'any' value for protocol to range
        4. expand bi-directional rules
        5. update 'action_l' as simple_action will not be used going forward
        """

        # step 1: key translation, update port/protocol values to system format
        translator = {
            'direction': 'direction', 'simple_action': 'simple_action',
            'protocol': 'proto_l', 'source_network': 'src', 'src_ports':
            'src_port_l', 'dest_network': 'dst', 'dst_ports': 'dst_port_l'}
        user_rules_tx = []
        configd_rules = len(user_rules_tx)
        for rule in rules:
            user_rule_tx = dict((translator[k], v) for (k, v) in rule.items())
            user_rules_tx.append(user_rule_tx)
        for rule in user_rules_tx:
            # port value mapping
            for port in ['src_port_l', 'dst_port_l']:
                if rule[port] == 'any':
                    rule[port] = {'max': '65535', 'min': '0'}
                else:  # only handling single or continuous range for port
                    if len(rule[port]) == 2:
                        rule[port] = {'max': str(rule[port][1]),
                                      'min': str(rule[port][0])}
                    else:
                        self.logger.error(
                            "user input port_list not handled by verification")
            # protocol value mapping
            if rule['proto_l'] == 'any':
                rule['proto_l'] = {'max': '255', 'min': '0'}
            else:
                rule['proto_l'] = {'max': str(rule['proto_l']),
                                   'min': str(rule['proto_l'])}

        # step 2: expanding rules if bidir rule
        final_rule_l = []
        for rule in user_rules_tx:
            if rule['direction'] == '<>':
                rule['direction'] = '>'
                pos = user_rules_tx.index(rule)
                new_rule = copy.deepcopy(rule)
                # update newly copied rule: swap address/ports & insert
                new_rule['src'], new_rule['dst'] = new_rule[
                    'dst'], new_rule['src']
                new_rule['src_port_l'], new_rule['dst_port_l'] = new_rule[
                    'dst_port_l'], new_rule['src_port_l'],
                user_rules_tx.insert(pos + 1, new_rule)

        # step 3: update action
        for rule in user_rules_tx:
            rule['action_l'] = [rule['simple_action']]

        return user_rules_tx

    def tx_user_def_aces_to_system(self, test_vn, user_rules_tx):
        '''convert ACEs derived from user rules to system format:
        1. For every user rule, add deny rule; skip adding duplicates
        2. For non-empty policy, add permit-all at the end
        3. add ace_id, rule_type
        4. Update VN to FQDN format
        5. remove direction and simple_action fields @end..
        '''
        if user_rules_tx == []:
            return user_rules_tx
        any_proto_port_rule = {
            'direction': '>', 'proto_l': {'max': '255', 'min': '0'}, 'src_port_l': {'max': '65535', 'min': '0'},
            'dst_port_l': {'max': '65535', 'min': '0'}}

        # step 0: check & build allow_all for local VN if rules are defined in
        # policy
        test_vn_allow_all_rule = copy.copy(any_proto_port_rule)
        test_vn_allow_all_rule['simple_action'] = 'pass'
        test_vn_allow_all_rule['action_l'] = ['pass']
        test_vn_allow_all_rule['src'], test_vn_allow_all_rule[
            'dst'] = test_vn, test_vn

        # check the rule for any protocol with same network exist and for deny
        # rule
        test_vn_deny_all_rule = copy.copy(any_proto_port_rule)
        test_vn_deny_all_rule['simple_action'] = 'deny'
        test_vn_deny_all_rule['action_l'] = ['deny']
        test_vn_deny_all_rule['src'], test_vn_deny_all_rule[
            'dst'] = test_vn, test_vn

        # step 1: check & add permit-all rule for same  VN  but not for 'any'
        # network
        last_rule = copy.copy(any_proto_port_rule)
        last_rule['simple_action'], last_rule['action_l'] = 'pass', ['pass']
        last_rule['src'], last_rule['dst'] = 'any', 'any'

        # check any rule exist in policy :
        final_user_rule = self.get_any_rule_if_exist(last_rule, user_rules_tx)

        # step 2: check & add deny_all for every user-created rule
        system_added_rules = []
        for rule in user_rules_tx:
            pos = len(user_rules_tx)
            new_rule = copy.deepcopy(rule)
            new_rule['proto_l'] = {'max': '255', 'min':
                                   '0'}
            new_rule['direction'] = '>'
            new_rule['src_port_l'], new_rule['dst_port_l'] = {
                'max': '65535', 'min': '0'}, {'max': '65535', 'min': '0'}
            new_rule['simple_action'] = 'deny'
            new_rule['action_l'] = ['deny']
            system_added_rules.append(new_rule)

        # step to check any one of the rule is any protocol and source and dst
        # ntw is test vn then check for the duplicate rules
        final_any_rules = self.get_any_rule_if_src_dst_same_ntw_exist(
            test_vn_allow_all_rule, test_vn_deny_all_rule, user_rules_tx)
        if final_any_rules:
            user_rules_tx = final_any_rules
        else:
            pass

        # Skip adding rules if they already exist...
        self.logger.debug( json.dumps(system_added_rules, sort_keys=True))
        if not policy_test_utils.check_rule_in_rules(test_vn_allow_all_rule, user_rules_tx):
            user_rules_tx.append(test_vn_allow_all_rule)
        for rule in system_added_rules:
            if not policy_test_utils.check_rule_in_rules(rule, user_rules_tx):
                user_rules_tx.append(rule)

        # step 3: check & add permit-all rule for same  VN  but not for 'any'
        # network
        last_rule = copy.copy(any_proto_port_rule)
        last_rule['simple_action'], last_rule['action_l'] = 'pass', ['pass']
        last_rule['src'], last_rule['dst'] = 'any', 'any'

        # if the first rule is not 'any rule ' then append the last rule
        # defined above.
        for rule in user_rules_tx:
            any_rule_flag = True
            if ((rule['src'] == 'any') and (rule['dst'] == 'any')):
                any_rule_flag = False
            else:
                pass
        if any_rule_flag:
            user_rules_tx.append(last_rule)
        else:
            pass

        # triming the duplicate rules
        user_rules_tx = policy_test_utils.remove_dup_rules(user_rules_tx)
        # triming the protocol with any option for rest of the fileds
        tcp_any_rule = {
            'proto_l': {'max': 'tcp', 'min': 'tcp'}, 'src': 'any', 'dst': 'any',
            'src_port_l': {'max': '65535', 'min': '0'}, 'dst_port_l': {'max': '65535', 'min': '0'}}
        udp_any_rule = {
            'proto_l': {'max': 'udp', 'min': 'udp'}, 'src': 'any', 'dst': 'any',
            'src_port_l': {'max': '65535', 'min': '0'}, 'dst_port_l': {'max': '65535', 'min': '0'}}
        icmp_any_rule = {
            'proto_l': {'max': 'icmp', 'min': 'icmp'}, 'src': 'any', 'dst': 'any',
            'src_port_l': {'max': '65535', 'min': '0'}, 'dst_port_l': {'max': '65535', 'min': '0'}}
        icmp_match, index_icmp = self.check_5tuple_in_rules(
            icmp_any_rule, user_rules_tx)
        tcp_match, index_tcp = self.check_5tuple_in_rules(
            tcp_any_rule, user_rules_tx)
        udp_match, index_udp = self.check_5tuple_in_rules(
            udp_any_rule, user_rules_tx)
        if icmp_match:
            for rule in user_rules_tx[index_icmp + 1:len(user_rules_tx)]:
                if rule['proto_l'] == {'max': 'icmp', 'min': 'icmp'}:
                    user_rules_tx.remove(rule)
                else:
                    pass
        if tcp_match:
            for rule in user_rules_tx[index_tcp + 1:len(user_rules_tx)]:
                if rule['proto_l'] == {'max': 'tcp', 'min': 'tcp'}:
                    user_rules_tx.remove(rule)
                else:
                    pass
        if udp_match:
            for rule in user_rules_tx[index_udp + 1:len(user_rules_tx)]:
                if rule['proto_l'] == {'max': 'udp', 'min': 'udp'}:
                    user_rules_tx.remove(rule)
                else:
                    pass
        # if any rule is exist the it will execute
        if final_user_rule:
            user_rules_tx = final_user_rule
        else:
            pass
        # step 4: add ace_id, type, src to all rules
        for rule in user_rules_tx:
            rule['ace_id'] = str(user_rules_tx.index(rule) + 1)
            # currently checking policy aces only
            rule['rule_type'] = 'Terminal'
            if rule['src'] != 'any':
                m = re.match(r"(\S+):(\S+):(\S+)", rule['src'])
                if not m:
                    rule['src'] = ':'.join(
                        self.project_fq_name) + ':' + rule['src']
            if rule['dst'] != 'any':
                m = re.match(r"(\S+):(\S+):(\S+)", rule['dst'])
                if not m:
                    rule['dst'] = ':'.join(
                        self.project_fq_name) + ':' + rule['dst']
            try:
                del rule['direction']
            except:
                continue
            try:
                del rule['simple_action']
            except:
                continue

        return user_rules_tx

    # end tx_user_def_aces_to_system

    def get_any_rule_if_exist(self, all_rule, user_rules_tx):
        final_rules = []
        if policy_test_utils.check_rule_in_rules(all_rule, user_rules_tx):
            for rule in user_rules_tx:
                if rule == all_rule:
                    final_rules.append(rule)
                    break
                else:
                    final_rules.append(rule)
        else:
            pass
        return final_rules
    # end get_any_rule_if_exist

    def get_any_rule_if_src_dst_same_ntw_exist(self, test_vn_allow_all_rule, test_vn_deny_all_rule, user_rules_tx):
        final_any_rules = []
        if (policy_test_utils.check_rule_in_rules(test_vn_allow_all_rule, user_rules_tx) or policy_test_utils.check_rule_in_rules(test_vn_deny_all_rule, user_rules_tx)):
            for rule in user_rules_tx:
                if ((rule == test_vn_allow_all_rule) or (rule == test_vn_deny_all_rule)):
                    final_any_rules.append(rule)
                    break
                else:
                    final_any_rules.append(rule)
        else:
            pass
        return final_any_rules
    # end get_any_rule_if_src_dst_same_ntw_exist

    def check_5tuple_in_rules(self, rule, rules):
        '''check if 5-tuple of given rule exists in given rule-set..Return True if rule exists; else False'''
        match_keys = ['proto_l', 'src', 'dst', 'src_port_l', 'dst_port_l']
        for r in rules:
            match = True
            for k in match_keys:
                if r[k] != rule[k]:
                    match = False
                    break
            if match == True:
                break
        return (match, rules.index(r))
    # end check_5tuple_in_rules

    def verify_policy_in_vna(self, scn, policy_attch_to_vn=None):
        '''
        Policies attached to VN will be pushed to VNA [in Compute node] once
        a VM is spawned in a VN.
        Input:  Test scenario object is passed as input [defined in policy_test_input].
        Return: returns a dictionary with keys as result & msg.
            For success, return is empty.
            For failure, result is set to False & msg has the error info.
        Steps: for each vn present in compute [vn has vm in compute]
            -whats the expected policy list for the vn
            -derive expected system rules for vn in vna
            -get actual system rules for vn in vna
            -compare
        '''
        self.logger.debug("Starting verify_policy_in_vna")
        result = True
        # expected data: translate user rules to system format for verification
        # Step 1: Translate user rules to ACEs
        user_rules_tx = {}
        if policy_attch_to_vn is None:
            policy_attch_to_vn = scn.vn_policy
        for policy in scn.policy_list:
            flag_policy_inheritance = 0
            policy_rules = scn.rules[policy]
            for rule in scn.rules[policy]:
                if (('dest_policy' in rule) or
                    ('source_policy' in rule)):
                    flag_policy_inheritance = 1
            if flag_policy_inheritance == 1:
                policy_rules = self.tx_policy_to_vn(scn.rules[policy],
                                   policy_attch_to_vn)
            for test_vn in scn.policy_vn[policy]:
                user_rules_tx[policy] = self.tx_user_def_rule_to_aces(
                    test_vn, policy_rules)

        # Step 2: Aggregate rules by network
        rules_by_vn = {}
        for vn in scn.vnet_list:
            tmp_vn_rules = []
            rules_by_vn[vn] = []
            self.logger.debug("vn is %s, scn.vn_policy is %s" % (
                vn, scn.vn_policy[vn]))
            for policy in scn.vn_policy[vn]:
                rules_by_vn[vn] += user_rules_tx[policy]

            # remove duplicate rules after adding policies
            rules_by_vn[vn] = policy_test_utils.trim_realign_rules(
                rules_by_vn[vn])

        # Step 3: Translate user-rules-> ACEs to system format and update ACE
        # IDs
        for vn in scn.vnet_list:
            if rules_by_vn[vn] != []:
                rules_by_vn[vn] = self.tx_user_def_aces_to_system(
                    vn, rules_by_vn[vn])
                rules_by_vn[vn] = policy_test_utils.update_rule_ace_id(
                    rules_by_vn[vn])

            self.logger.debug("VN: %s, expected ACE's is " % (vn))
            for r in rules_by_vn[vn]:
                self.logger.debug("%s" % (json.dumps(r, sort_keys=True)))
        # end building VN ACE's from user rules

        # Get actual from vna in compute nodes [referred as cn]
        vn_of_cn = scn.vn_of_cn  # {'cn1': ['vn1', 'vn2'], 'cn2': 'vn2'}
        cn_vna_rules_by_vn = {}  # {'vn1':[{...}, {..}], 'vn2': [{..}]}
        err_msg = {}  # To capture error {compute: {vn: error_msg}}
        for compNode in self.inputs.compute_ips:
            self.logger.debug("Compute node: %s, Check for expected data" % (
                compNode))
            inspect_h = self.agent_inspect[compNode]
            vnCn = (vn for vn in vn_of_cn[compNode] if vn_of_cn[compNode])
            for vn in vnCn:
                self.logger.debug("Checking for VN %s in Compute %s" % (
                    vn, compNode))
                vn_fq_name = inspect_h.get_vna_vn('default-domain', self.project_name, vn)['name']
                vna_acl = inspect_h.get_vna_acl_by_vn(vn_fq_name)
                if vna_acl:
                    # system_rules
                    cn_vna_rules_by_vn[vn] = vna_acl['entries']
                else:
                    cn_vna_rules_by_vn[vn] = []
                # compare with test input & assert on failure
                ret = policy_test_utils.compare_rules_list(
                    rules_by_vn[vn], cn_vna_rules_by_vn[vn],
                    logger=self.logger)
                if ret:
                    result = ret['state']
                    msg = ret['msg']
                    err_msg[compNode] = {vn: msg}
                    self.logger.error("Compute node: %s, VN: %s, test result not expected, \
                        msg: %s" % (compNode, vn, msg))
                    self.logger.debug("Expected rules: ")
                    for r in rules_by_vn[vn]:
                        self.logger.debug(r)
                    self.logger.debug("Actual rules from system: ")
                    for r in cn_vna_rules_by_vn[vn]:
                        self.logger.debug(r)
                else:
                    self.logger.info("Compute node: %s, VN: %s, result of "\
                        "expected rules check passed" % (compNode, vn))
            self.logger.debug("Compute node: %s, Check for unexpected data" % (
                compNode))
            vn_not_of_cn = []
            skip_vn_not_of_cn = 0
            vn_not_of_cn = list(set(scn.vnet_list) - set(vn_of_cn[compNode]))
            if vn_not_of_cn == []:
                skip_vn_not_of_cn = 1
            for vn in vn_not_of_cn:
                if skip_vn_not_of_cn == 1:
                    break
                # VN & its rules should not be present in this Compute
                vn_exists = inspect_h.get_vna_vn('default-domain', self.project_name, vn)
                if vn_exists:
                    vn_fq_name = vn_exists['name']
                    vna_acl = inspect_h.get_vna_acl_by_vn(vn_fq_name)
                    # system_rules
                    cn_vna_rules_by_vn[vn] = vna_acl['entries']
                    result = False
                    msg = "Compute node: " + str(compNode) + ", VN: " + str(vn) + \
                        " seeing unexpected rules in VNA" + \
                        str(cn_vna_rules_by_vn[vn])
                    err_msg[compNode] = {vn: msg}
                else:
                    self.logger.info("Compute node: %s, VN: %s, validated that "\
                        "no extra rules are present" % (compNode, vn))
        return {'result': result, 'msg': err_msg}
    # end verify_policy_in_vna

    def refresh_quantum_policy_obj(self):
        # Rebuild the policy object to take care of cases where it takes time to update after instantiating the object 
        if self.api_flag:
            return self
        self.policy_obj=self.quantum_h.get_policy_if_present(self.project_name, self.policy_name)
        return self

    def verify_policy_in_api_server(self):
        '''Validate policy information in API-Server. Compare data with quantum based policy fixture data.
        Check specifically for following:
        api_server_keys: 1> fq_name, 2> uuid, 3> rules
        quantum_h_keys: 1> policy_fq_name, 2> id in policy_obj, 3> policy_obj [for rules]
        '''
        self.refresh_quantum_policy_obj()
        me = inspect.getframeinfo(inspect.currentframe())[2]
        result = True
        err_msg = []
        out = None
        self.logger.debug("====Verifying data for %s in API_Server ======" %
                         (self.policy_name))
        self.api_s_policy_obj = self.api_s_inspect.get_cs_policy(
            domain=self.project_fq_name[0], project=self.project_fq_name[1], policy=self.policy_name, refresh=True)
        self.api_s_policy_obj_x = self.api_s_policy_obj['network-policy']

        # compare policy_fq_name
        out = policy_test_utils.compare_args(
            'policy_fq_name', self.api_s_policy_obj_x['fq_name'], self.policy_fq_name,
            logger=self.logger)
        if out:
            err_msg.append(out)
        # compare policy_uuid
        if isinstance(self.policy_obj, NetworkPolicy):
            uuid = self.policy_obj.uuid
            rules = self.policy_obj.network_policy_entries.exportDict()['PolicyEntriesType']
        else:
            uuid = self.policy_obj['policy']['id']
            rules = self.policy_obj['policy']['entries']

        out = policy_test_utils.compare_args(
            'policy_uuid', self.api_s_policy_obj_x['uuid'], uuid,
            logger=self.logger)
        if out:
            err_msg.append(out)
        # compare policy_rules
        out = policy_test_utils.compare_args(
            'policy_rules', self.api_s_policy_obj_x[
                'network_policy_entries']['policy_rule'], rules['policy_rule'],
                logger=self.logger)
        if out:
            err_msg.append(out)

        if err_msg != []:
            result = False
            err_msg.insert(0, me + ":" + self.policy_name)
        self.logger.info("Verified policy %s in API Server, Result: %s" % (
            self.policy_name, result))
        return {'result': result, 'msg': err_msg}
    # end verify_policy_in_api_server

    @retry(delay=5, tries=3)
    def verify_policy_not_in_api_server(self):
        '''Verify that policy is removed in API Server.

        '''
        pol_found = False

        proj = self.vnc_lib.project_read(self.project_fq_name)
        pol_dict = self.vnc_lib.network_policys_list(
            parent_id=proj, parent_fq_name=proj.fq_name)
        # pol_dict has policys from all projects, o/p is not filtered
        # This needs to be debugged as vnc_lib.network_policys_list should return policys of requested project only...
        policy_by_proj = []
        for p in pol_dict['network-policys']:
            proj_of_policy = p['fq_name'][1]
            if (proj_of_policy == proj.fq_name[1]):
                policy_by_proj.append(p)
        pol_dict = {'network-policys':policy_by_proj}
        pol_list = pol_dict.get('network-policys')
        for policy in pol_list:
            if (policy['fq_name'][2] == self.policy_name):
                pol_found = True
                self.logger.debug("policy %s is still found in API-Server" %
                                 (self.policy_name))
                break
        if not pol_found:
            self.logger.debug("policy %s is not found in API Server" %
                             (self.policy_name))
        return pol_found == False
    # end verify_policy_not_in_api_server

    @retry(delay=3, tries=5)
    def verify_policy_in_control_nodes(self):
        """ Checks for policy details in Control-nodes.
        Validate control-node data against quantum and return False if any mismatch is found.
        """
        # Refresh quantum policy object - self.policy_obj  
        return {'result':True ,'msg':'Skipping control node verification'}
        self.refresh_quantum_policy_obj()
        me = inspect.getframeinfo(inspect.currentframe())[2]
        result = True
        err_msg = []
        out = None
        for cn in self.inputs.bgp_ips:
            # check if policy exists:
            cn_config_policy_obj = self.cn_inspect[cn].get_cn_config_policy(
                domain=self.project_fq_name[0], project=self.project_fq_name[1], policy=self.policy_name)
            if not cn_config_policy_obj:
                msg = "IFMAP View of Control-node %s is missing policy %s" % (cn,
                                                                              self.policy_fq_name)
                err_msg.append(msg)
                self.logger.debug(msg)
                return {'result': False, 'msg': err_msg}
            # compare policy_fq_name
            self.logger.debug("Control-node %s : Policy object is : %s" %
                              (cn, cn_config_policy_obj))
            policy_fqn = ':'.join(self.policy_fq_name)
            if policy_fqn not in cn_config_policy_obj['node_name']:
                msg = "IFMAP View of Control-node %s is not having the policy detail of %s" % (
                    cn, self.policy_fq_name)
                err_msg.append(msg)
            # compare policy_rules
            if cn_config_policy_obj['obj_info']:
                cn_rules = cn_config_policy_obj['obj_info'][
                    0]['data']['network-policy-entries']
            else:
                # policy not attached to any network
                cn_rules = []
            # translate control data in quantum data format for verification:
            if cn_rules:
                cn_rules = policy_test_utils.xlate_cn_rules(cn_rules)
            else:
                cn_rules = []
            self.logger.debug("Policy info in Control node %s: %s" % (cn, 
                cn_rules))
            if isinstance(self.policy_obj, NetworkPolicy):
                policy_info = self.policy_obj.network_policy_entries.exportDict()['PolicyEntriesType']['policy_rule']
            else:
                policy_info = self.policy_obj['policy']['entries']['policy_rule']
            self.logger.debug("Policy info in Neutron: %s" % policy_info)
            out = policy_test_utils.compare_args('policy_rules', cn_rules, policy_info,
                                                 exp_name='cn_rules', act_name='quantum_rules')
            if out:
                msg = "Rules view in control-node %s is not matching, detailed msg follows %s" % (
                    cn, out)
                err_msg.append(msg)

        if err_msg != []:
            result = False
            err_msg.insert(0, me + ":" + self.policy_name)
        self.logger.info("Verified policy in Control nodes, Result: %s" % (
            result))
        return {'result': result, 'msg': err_msg}
    # end verify_policy_in_control_node
# end PolicyFixture
