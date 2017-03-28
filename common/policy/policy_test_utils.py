''' This module provides utils for Policy tests '''
import inspect
import copy
import json
import fixtures
from tcutils.topo.topo_helper import topology_helper
from vnc_api.vnc_api import *
from vnc_api.gen.resource_test import *
import re


def update_rule_ace_id(rules_list):
    ''' After combining multiple policies, renumber ace_id of the rules by
    index of rules in the combined list
    Return updated rules_list.
    '''
    for rule in rules_list:
        rule['ace_id'] = str(rules_list.index(rule) + 1)
    return rules_list


def remove_dup_rules(rules_list):
    ''' After combining multiple policies, there can be duplicate rules.
    Leave only one copy and remove duplicate rules.
    Return updated rules_list.
    XXX For now tested for permit_all rules only.
    TODO: handle duplicate rules within a policy and duplicate rules
    across policies, in case of both policies attached to a VN.
    '''
    print "==>", inspect.getframeinfo(inspect.currentframe())[2]
    new_list = []
    while len(rules_list) > 0:
        match = None
        ref_rule = rules_list.pop(0)
        new_list.append(ref_rule)
        match = compare_dict(ref_rule, rules_list)
        if match:
            print "matching idx are", match
            for i in reversed(match):
                rules_list.pop(i)
            # end for
        # end if
    # end for
    # print "length of list after removing dup is ", len(new_list)
    return new_list


def compare_dict(ref_dict, test_dict_l):
    ''' Comapare a rule with the rules_list. Return a list of indices
    that match the ref_dict'''
    matching_idx = []
    for idx, rule in enumerate(test_dict_l):
        match = 0
        for key in filter(lambda x: x != 'ace_id', ref_dict):
            if ref_dict[key] != rule[key]:
                match = 0
                break
            else:
                match = 1
        # end for
        if match == 1:
            matching_idx.append(idx)
    return matching_idx


def move_matching_rule_to_bottom(rules_list, rule={}, vn=None):
    ''' check if permit_all exists.. if yes, pop the rule out and append the
    rule to the end of the list.
    Return updated rules_list'''
    print "==>", inspect.getframeinfo(inspect.currentframe())[2]
    idx = check_if_rule_present(rules_list, rule)
    if idx:
        permit_all_rule = rules_list.pop(idx)
        rules_list.append(permit_all_rule)
    return rules_list


def check_rule_in_rules(rule, rules):
    '''check if 5-tuple of given rule exists in given rule-set..Return True if rule exists; else False'''
    #print ("check rule %s in rules" %(json.dumps(rule, sort_keys=True)))
    match_keys = ['src', 'proto_l', 'dst', 'src_port_l', 'dst_port_l']
    for r in rules:
        match = True
        for k in match_keys:
            if r[k] != rule[k]:
                # print ("current rule not matching due to key %s, move on.." %k)
                match = False
                break
        if match == True:
            break
    return match


def check_if_rule_present(rules_list, rule={}, vn=None):
    ''' if present, return index of the rule, else return None '''
    print "==>", inspect.getframeinfo(inspect.currentframe())[2]
    match_rule = rule
    for rule in rules_list:
        match = 1
        for key in match_rule:
            if match_rule[key] != rule[key]:
                match = 0
                break
            # endif
        # end for key
        if match:
            return rules_list.index(rule)
    return None


def trim_realign_rules(rules_list):
    ''' remove duplicate rules & move permit_all rule to bottom
    Return updated rules_list'''
    new_list = remove_dup_rules(rules_list)
    permit_all_rule = {'proto_l': {'max': '255', 'min': '0'}, 'src_port_l': {
        'max': '65535', 'min': '0'}, 'dst_port_l': {'max': '65535', 'min': '0'}, 'action_l': ['pass']}
    final_list = move_matching_rule_to_bottom(new_list, rule=permit_all_rule)
    return final_list


def compare_rules_list(user_rules_tx, system_rules, exp_name='user_rules_tx', act_name='system_rules'):
    ''' Compares 2 list of rules [as dictionary] returns a dictionary with keys
    as result & msg_list.
    For success, return is empty. For failure, result is set to False & msg has
    the error info. '''
    print "-" * 40
    proto_map = {'1': 'icmp', '6': 'tcp', '17': 'udp'}
    result = True
    ret = {}
    msg = []
    # Check for empty policy, 0 rule_list
    if len(user_rules_tx) == 0:
        if len(system_rules) == 0:
            print "empty policy check pass.."
            return ret
    # For non-zero rule policies, continue checking num rules
    if len(system_rules) != len(user_rules_tx):
        msg = "No of rules in system: %s is not same as expected: %s " % (
            len(system_rules), len(user_rules_tx))
        print "expected: "
        for r in user_rules_tx:
            print json.dumps(r, sort_keys=True)
        print "-" * 40
        print "got: "
        for r in system_rules:
            print json.dumps(r, sort_keys=True)
        ret['state'] = 'False'
        ret['msg'] = msg
        return ret
    # If num_rules are ok, compare rule contents
    # i. build key list to be checked
    non_port_keys = []
    port_keys = []
    rule_keys = list(user_rules_tx[0].keys())
    for k in rule_keys:
        if k.find('port') == -1:
            non_port_keys.append(k)
        else:
            port_keys.append(k)
        if k.find('proto') != -1:
            proto_key = k
            for i in range(len(system_rules)):
                if isinstance(system_rules[i][k], dict):
                    if system_rules[i][k]['min'] in proto_map:
                        system_rules[i][k]['min'] = proto_map[
                            system_rules[i][k]['min']]
                    if system_rules[i][k]['max'] in proto_map:
                        system_rules[i][k]['max'] = proto_map[
                            system_rules[i][k]['max']]
                elif system_rules[i][k] in proto_map:
                    system_rules[i][k] = proto_map[system_rules[i][k]]

    # ii. match non_port_key values first
    for i in range(len(user_rules_tx)):
        match = None
        for k in non_port_keys:
            if user_rules_tx[i][k] != system_rules[i][k]:
                if k == 'action_l':
                    match, mesg = compare_action_list(user_rules_tx[i][k], system_rules[i][k])
                    if not match:
                        msg.append(mesg)
                else:
                    msg.append("Rule mismatch found: value for key: %s not matching: expected- %s, got- %s"
                           % (k, user_rules_tx[i][k], system_rules[i][k]))
                match = False
        if match != False:
        # iii. if good, check port keys.. need special handling for icmp proto
        # skip src/dst port check for icmp proto
        # icmp in policy rules can appear in following formats in different
        # datasets
            icmp_names = [{'max': '1', 'min': '1'}, '1',
                          {'max': 'icmp', 'min': 'icmp'}, 'icmp']
            if user_rules_tx[i][proto_key] not in icmp_names:
                for k in port_keys:
                    if user_rules_tx[i][k] != system_rules[i][k]:
                        msg.append(
                            "key: %s not matching between expected & system rules - %s, %s" %
                            (k, user_rules_tx[i][k], system_rules[i][k]))
    if msg != []:
        result = False
        print "-" * 40
        print "Compare failed..!, msg is: ", msg
        ret['state'] = 'False'
        ret['msg'] = msg
        print "-" * 40
    return ret

# end compare_rules_list


def compare_args(key, a, b, exp_name='expected', act_name='actual'):
    ''' For a given key, compare values a, b got from 2 different databases.
    If instance is dict and not matching, call compare_rules_list to get details'''
    ret = None
    if a != b:
        ret = key + " not matching --->expected: " + \
            str(a) + " --->got: " + str(b)
    if a != b and isinstance(a, dict):
        ret = compare_rules_list(a, b, exp_name, act_name)
    if a != b and isinstance(a, list):
        ret = compare_rules_list(a, b, exp_name, act_name)
    return ret

# This procedure compare list1 is exists in list2 or not.


def compare_list(self, list1, list2):
    diff_list = []
    compare = True
    for item in list1:
        if not item in list2:
            diff_list.append(item)
            compare = False
    if not compare:
        self.logger.info("List compare failed: expected is %s and actual is %s" % (list1, list2))
    return compare
# end compare_list


def get_dict_with_matching_key_val(key, value, dict_l, scope):

    match = 0
    for d in dict_l:
        if d[scope][key] == value:
            print "match found"
            match = 1
            return {'state': 1, 'ret': d}
    if not match:
        msg = "No matching rule found with key: " + key + "value: " + value
        print msg
        return {'state': None, 'ret': msg}


def get_policy_not_in_vn(initial_policy_list, complete_policy_list):
    ret = list(set(complete_policy_list) - set(initial_policy_list))
    if len(ret) > 0:
        return ret[0]
    else:
        return None


def xlate_cn_rules(rules_list):
    ''' Take rules from control node and translate to quantum rules data format to compare..'''
    new_rule_list = []
    for rule in rules_list:
        new_rule = {}
        for key, value in rule.items():
            key = key.replace('-', '_')
            if type(value) == dict:
                value = replace_key(value)
            new_rule[key] = value
        # Ignore following for now...
        new_rule['src_addresses']['subnet'] = None
        new_rule['dst_addresses']['subnet'] = None
        new_rule['src_addresses'] = [new_rule['src_addresses']]
        new_rule['dst_addresses'] = [new_rule['dst_addresses']]
        new_rule['dst_ports']['end_port'] = int(
            new_rule['dst_ports']['end_port'])
        new_rule['dst_ports']['start_port'] = int(
            new_rule['dst_ports']['start_port'])
        new_rule['src_ports']['end_port'] = int(
            new_rule['src_ports']['end_port'])
        new_rule['src_ports']['start_port'] = int(
            new_rule['src_ports']['start_port'])
        new_rule['dst_ports'] = [new_rule['dst_ports']]
        new_rule['src_ports'] = [new_rule['src_ports']]
        if new_rule['action_list']['mirror_to']['analyzer_name'] != None:
            new_rule['action_list']['mirror_to']['udp_port'] = None
        else:
            new_rule['action_list']['mirror_to'] = None
        new_rule['action_list']['gateway_name'] = None
        if new_rule['action_list'].has_key('apply_service'):
            new_rule['action_list']['apply_service'] = [new_rule['action_list']['apply_service']]
        else:
            new_rule['action_list']['apply_service'] = []
        new_rule['rule_sequence']['major'] = int(
            new_rule['rule_sequence']['major'])
        new_rule['rule_sequence']['minor'] = int(
            new_rule['rule_sequence']['minor'])
        new_rule['rule_sequence'] = None
        # appending each rule to new list
        new_rule_list.append(new_rule)
    print "after xlate: ", new_rule_list
    return new_rule_list

# end of def xlate_cn_rules


def replace_key(d):
    new = {}
    for k, v in d.iteritems():
        if isinstance(v, dict):
            v = replace_key(v)
        new[k.replace('-', '_')] = v
    return new

# end of replace_key


def update_topo(topo, test_vn, new_policy):
    ''' Purpose of this def is to update & return topology object as needed.
    Example:  Need to modify VN's policy list..  This change requires update
    of every [affected] policy's VN list as well.
    Reference info of how data is maintained:
    vn_policy=  {'vnet0': ['policy0', 'policy1'], 'vnet1': ['policy2', 'policy3']}
    policy_vn= {'policy0': ['vnet0']}
    '''
    n_topo = copy.deepcopy(topo)
    # i] remove test_vn from currently associated policies
    topo_helper_obj = topology_helper(n_topo)
    n_topo.policy_vn = topo_helper_obj.get_policy_vn()
    for p in topo.vn_policy[test_vn]:
        n_topo.policy_vn[p].remove(test_vn)
    # ii] update vn_policy[test_vn] and policy_vn[new_policy] with new info
    n_topo.vn_policy[test_vn] = [new_policy]
    n_topo.policy_vn[new_policy].append(test_vn)
    return n_topo


def get_policy_peer_vns(self, vnet_list, vn_fixture):
    ''' For each VN, get the allowed peers based on rule action to the peer VN's.
    Every VN pair needs to allow for route exchange to happen..
    vnet_list is the vn pair for which policy peering is inspected
    input vnet_list as vn_name & not fqdn.
    return dict, with key as vn_name and value as again vn_name'''

    vn_policys_peer_vns = {}  # allowed peer vns for a vn
    for vn in vnet_list:
        vn_policys_peer_vns[vn] = vn_fixture[
            vn].get_allowed_peer_vns_by_policy()
    print "vn_policys_peer_vns is: ", vn_policys_peer_vns

    all_vns = []     # Build all vns list to replace any
    for i, j in vn_fixture.items():
        x = j.vn_fq_name
        all_vns.append(x)

    actual_peer_vns_by_policy = {}   # return dict with policy peer vn list
    # allowed vn peers any any keyword expanded
    final_vn_policys_peer_vns = {}
    # Expanding any keyword to all created VNs
    for vn in vnet_list:
        final_vn_policys_peer_vns[vn] = []
        vppvns = vn_policys_peer_vns[vn]
        for vppvn in vppvns:
            if vppvn != 'any':
                final_vn_policys_peer_vns[vn].append(vppvn)
            else:
                final_vn_policys_peer_vns[vn].extend(all_vns)
        final_vn_policys_peer_vns[vn] = list(
            set(final_vn_policys_peer_vns[vn]))

    print "final_vn_policys_peer_vns: ", final_vn_policys_peer_vns
    for vn in vnet_list:
        actual_peer_vns_by_policy[vn] = []
        fqvn = vn_fixture[vn].vn_fq_name
        if final_vn_policys_peer_vns[vn] != []:
            for pvn in final_vn_policys_peer_vns[vn]:
                #get pvn name based on fqdn format- domain:project:vn
                m = re.match(r"(\S+):(\S+):(\S+)", pvn)
                if m:
                    m = re.search(r"(\S+):(\S+):(\S+)", pvn)
                    pvn_name = m.group(3)
                else:
                    pvn_name = pvn
                self.logger.info("vn %s sees %s as peer vn" %(vn, pvn))
                if fqvn in final_vn_policys_peer_vns[pvn_name]:
                    self.logger.info(
                        "peer vn %s sees vn %s as peer, add if not already in the actual peer list" %(pvn_name, fqvn))
                    if pvn not in actual_peer_vns_by_policy[vn]:
                        actual_peer_vns_by_policy[vn].append(pvn)
        self.logger.info("vn %s has following vn's as actual peers -%s" %(vn, actual_peer_vns_by_policy[vn]))

    return actual_peer_vns_by_policy

def compare_action_list(user_action_l, system_action_l):

    mesg = None; ret = False
    for item_u in user_action_l:
        ret = False
        #[TBD]may need to change the index below if multiple SI in system_action_l
        if item_u['simple_action'] != system_action_l[0]:
            ret = False
            break
        else:
            ret = True
        if item_u.has_key('apply_service') and item_u['apply_service'] != []:

            for si in item_u['apply_service']:
                si = si.replace(':','_')
                ret = False
                if si in system_action_l[2]:
                    ret = True
    if not ret:
        mesg = "user action list does not match in system,user action list:%s, \
                        system action list:%s" % (user_action_l,system_action_l)

    return (ret, mesg)

if __name__ == '__main__':
    ''' Unit test to invoke policy utils.. '''

    input_data = [
        {'proto_l': {'max': '6', 'min': '6'}, 'src': 'default-domain:admin:vnet0', 'ace_id': '1', 'dst': 'default-domain:admin:vnet0', 'action_l': ['deny'], 'rule_type': 'Terminal', 'src_port_l': {'max': '0', 'min': '0'}, 'dst_port_l': {'max': '65535', 'min': '0'}}, {'proto_l': {'max': '6', 'min': '6'}, 'src': 'default-domain:admin:vnet0', 'ace_id': '2', 'dst': 'default-domain:admin:vnet0', 'action_l': ['deny'], 'rule_type': 'Terminal', 'src_port_l': {'max': '1', 'min': '1'}, 'dst_port_l': {'max': '65535', 'min': '0'}}, {'proto_l': {'max': '6', 'min': '6'}, 'src': 'default-domain:admin:vnet0', 'ace_id': '3', 'dst': 'default-domain:admin:vnet0', 'action_l': [
            'deny'], 'rule_type': 'Terminal', 'src_port_l': {'max': '2', 'min': '2'}, 'dst_port_l': {'max': '65535', 'min': '0'}}, {'proto_l': {'max': '6', 'min': '6'}, 'src': 'default-domain:admin:vnet0', 'ace_id': '4', 'dst': 'default-domain:admin:vnet0', 'action_l': ['deny'], 'rule_type': 'Terminal', 'src_port_l': {'max': '3', 'min': '3'}, 'dst_port_l': {'max': '65535', 'min': '0'}}, {'rule_type': 'Terminal', 'src': 'default-domain:admin:vnet0', 'dst_port_l': {'max': '65535', 'min': '0'}, 'src_port_l': {'max': '65535', 'min': '0'}, 'ace_id': '5', 'dst': 'default-domain:admin:vnet0', 'action_l': ['pass'], 'proto_l': {'max': '255', 'min': '0'}},
        {'proto_l': {'max': '17', 'min': '17'}, 'src': 'default-domain:admin:vnet0', 'ace_id': '1', 'dst': 'default-domain:admin:vnet0', 'action_l': ['deny'], 'rule_type': 'Terminal', 'src_port_l': {'max': '0', 'min': '0'}, 'dst_port_l': {'max': '65535', 'min': '0'}}, {'proto_l': {'max': '17', 'min': '17'}, 'src': 'default-domain:admin:vnet0', 'ace_id': '2', 'dst': 'default-domain:admin:vnet0', 'action_l': ['deny'], 'rule_type': 'Terminal', 'src_port_l': {'max': '1', 'min': '1'}, 'dst_port_l': {'max': '65535', 'min': '0'}}, {'proto_l': {'max': '17', 'min': '17'}, 'src': 'default-domain:admin:vnet0', 'ace_id': '3', 'dst': 'default-domain:admin:vnet0', 'action_l': ['deny'], 'rule_type': 'Terminal', 'src_port_l': {'max': '2', 'min': '2'}, 'dst_port_l': {'max': '65535', 'min': '0'}}, {'proto_l': {'max': '17', 'min': '17'}, 'src': 'default-domain:admin:vnet0', 'ace_id': '4', 'dst': 'default-domain:admin:vnet0', 'action_l': ['deny'], 'rule_type': 'Terminal', 'src_port_l': {'max': '3', 'min': '3'}, 'dst_port_l': {'max': '65535', 'min': '0'}}, {'rule_type': 'Terminal', 'src': 'default-domain:admin:vnet0', 'dst_port_l': {'max': '65535', 'min': '0'}, 'src_port_l': {'max': '65535', 'min': '0'}, 'ace_id': '5', 'dst': 'default-domain:admin:vnet0', 'action_l': ['pass'], 'proto_l': {'max': '255', 'min': '0'}}]

    system_data = [{'rule_type': 'Terminal', 'src': 'default-domain:admin:vnet0', 'proto_l': {'max': '6', 'min': '6'}, 'ace_id': '1', 'dst': 'default-domain:admin:vnet0', 'action_l': ['deny'], 'src_port_l': {'max': '0', 'min': '0'}, 'dst_port_l': {'max': '65535', 'min': '0'}}, {'rule_type': 'Terminal', 'src': 'default-domain:admin:vnet0', 'proto_l': {'max': '6', 'min': '6'}, 'ace_id': '2', 'dst': 'default-domain:admin:vnet0', 'action_l': ['deny'], 'src_port_l': {'max': '1', 'min': '1'}, 'dst_port_l': {'max': '65535', 'min': '0'}}, {'rule_type': 'Terminal', 'src': 'default-domain:admin:vnet0', 'proto_l': {'max': '6', 'min': '6'}, 'ace_id': '3', 'dst': 'default-domain:admin:vnet0', 'action_l': ['deny'], 'src_port_l': {'max': '2', 'min': '2'}, 'dst_port_l': {'max': '65535', 'min': '0'}}, {'rule_type': 'Terminal', 'src': 'default-domain:admin:vnet0', 'proto_l': {'max': '6', 'min': '6'}, 'ace_id': '4', 'dst': 'default-domain:admin:vnet0', 'action_l': ['deny'], 'src_port_l': {'max': '3', 'min': '3'}, 'dst_port_l': {'max': '65535', 'min': '0'}}, {'rule_type': 'Terminal', 'src': 'default-domain:admin:vnet0', 'proto_l': {'max': '17', 'min': '17'}, 'ace_id': '5', 'dst':
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                'default-domain:admin:vnet0', 'action_l': ['deny'], 'src_port_l': {'max': '0', 'min': '0'}, 'dst_port_l': {'max': '65535', 'min': '0'}}, {'rule_type': 'Terminal', 'src': 'default-domain:admin:vnet0', 'proto_l': {'max': '17', 'min': '17'}, 'ace_id': '6', 'dst': 'default-domain:admin:vnet0', 'action_l': ['deny'], 'src_port_l': {'max': '1', 'min': '1'}, 'dst_port_l': {'max': '65535', 'min': '0'}}, {'rule_type': 'Terminal', 'src': 'default-domain:admin:vnet0', 'proto_l': {'max': '17', 'min': '17'}, 'ace_id': '7', 'dst': 'default-domain:admin:vnet0', 'action_l': ['deny'], 'src_port_l': {'max': '2', 'min': '2'}, 'dst_port_l': {'max': '65535', 'min': '0'}}, {'rule_type': 'Terminal', 'src': 'default-domain:admin:vnet0', 'proto_l': {'max': '17', 'min': '17'}, 'ace_id': '8', 'dst': 'default-domain:admin:vnet0', 'action_l': ['deny'], 'src_port_l': {'max': '3', 'min': '3'}, 'dst_port_l': {'max': '65535', 'min': '0'}}, {'rule_type': 'Terminal', 'src': 'default-domain:admin:vnet0', 'proto_l': {'max': '255', 'min': '0'}, 'ace_id': '9', 'dst': 'default-domain:admin:vnet0', 'action_l': ['pass'], 'src_port_l': {'max': '65535', 'min': '0'}, 'dst_port_l': {'max': '65535', 'min': '0'}}]

    updated_list = trim_realign_rules(input_data)
    if updated_list == system_data:
        print "Data compare of user-defined combined rules with system data successful!"
    else:
        print "Data compare after update failed!"
        compare_rules_list(system_data, updated_list)

# end __main__
