from builtins import object
import time
from common.firewall.base import BaseFirewallTest

class MatchOp(object):
    # operator for use in where-clause, copies from opserver_util.py
    EQUAL=1
    NOT_EQUAL=2
    IN_RANGE=3
    NOT_IN_RANGE=4
    LEQ=5
    GEQ=6
    PREFIX=7
    REGEX_MATCH=8
    CONTAINS=9

class BasePolicyGenTest(BaseFirewallTest):

    proto_name_to_nr = {'icmp': 1, 'tcp': 6, 'udp': 17}

    @classmethod
    def setUpClass(cls):
        super(BasePolicyGenTest, cls).setUpClass()
        try:
            cls.create_vns_vms()
        except:
            cls.tearDownClass()
            raise
        cls.policy_gen = cls.connections.policy_generator_handle

    def is_test_applicable(self):
        if not self.inputs.policy_generator_ips:
            return(False, 'Policy Generator not present')
        return (True, None)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, 'policys', None) and 'hr_eng' in cls.policys:
            cls.vns['hr'].unbind_policies()
            cls.vns['eng'].unbind_policies()
            cls.policys['hr_eng'].cleanUp()
        if getattr(cls, 'restore_rate', None):
            cls.vnc_h.set_flow_export_rate(cls.restore_rate)
        super(BasePolicyGenTest, cls).tearDownClass()

    @classmethod
    def create_vns_vms(cls):
        ''' create class specific objects
            1) create VNs HR and ENG
            2) create VMs Web, Logic, DB in each VN
            3) create Network-Policy to interconnect VNs (for route leaking)
        '''
        cls.vns = dict(); cls.vms = dict(); cls.policys = dict()
        cls.vm_vn_map = dict()
        for vn in ['hr', 'eng']:
            cls.vns[vn] = cls.create_only_vn()
            for vm in ['web', 'logic', 'db']:
                cls.vms[vn+'_'+vm] = vm_fix = cls.create_only_vm(
                                                    vn_fixture=cls.vns[vn])
                cls.vm_vn_map[vm_fix.vm_name] = cls.vns[vn]
        cls.policys['hr_eng'] = cls.setup_only_policy_between_vns(
                                        cls.vns['hr'], cls.vns['eng'])
        assert cls.check_vms_active(iter(cls.vms.values()), do_assert=False)
        time.sleep(60)
        assert cls.check_vms_booted(iter(cls.vms.values()), do_assert=False)
        cls.restore_rate = cls.vnc_h.get_flow_export_rate()
        cls.vnc_h.set_flow_export_rate(10)

    def remove_unwanted_flows(self, flows):
        ''' remove flows that aren't of interest
            traffic from/to DNS ip, metadata ip
        '''
        # TODO: assumes flow contains local_ip & remote_ip
        flows = [flow for flow in flows
                    if '169.254' not in flow['local_ip'] and
                       '169.254' not in flow['remote_ip']]
        metadata_ips = set([vn.get_an_ip() for vn in list(self.vns.values())])
        flows = [flow for flow in flows
                    if flow['local_ip'] not in metadata_ips and
                       flow['remote_ip'] not in metadata_ips]
        return flows

    def verify_traffic_not_in_untagged_flows(self, untagged, traffics):
        ''' verify that traffic from/to properly tagged workloads
            are not present in untagged flows
        '''
        # TODO: assumes flow contains local_ip & remote_ip
        if not untagged:
            return True
        for traf in traffics:
            for flow in untagged:
                if (traf.src_ip == flow['local_ip'] and
                    traf.dst_ip == flow['remote_ip'] and
                    self.proto_name_to_nr[traf.proto] == flow['protocol'] and
                    traf.dport == flow['server_port']):
                    self.logger.error('unexpected traffic is seen untagged')
                    msg = "flow:%s %s:%s - %s:%s" % (traffic_obj.proto,
                            traffic_obj.src_ip, traffic_obj.sport,
                            traffic_obj.dst_ip, traffic_obj.dport)
                    self.logger.error(msg)
                    return False
        return True

    def get_tags_for_untagged(self, query, traffic):
        ''' contruct tags expected for traffic from/to 
            untagged or partially tagged endpoints
        '''
        src_tags = self.get_tags(traffic.sender_vm, query['tags'])
        dst_tags = self.get_tags(traffic.receiver_vm, query['tags'])
        ret_tags = {tag.tag_type_name: self.get_fqname_for_tag(tag)
                    for tag in src_tags}
        ret_tags.update({'remote_' + tag.tag_type_name:
                            self.get_fqname_for_tag(tag) for tag in dst_tags})
        ret_tags.update({tag_name: '__UNKNOWN__' for tag_name in query['tags']
                            if tag_name not in ret_tags})
        ret_tags.update({'remote_' + tag_name: '__UNKNOWN__'
                            for tag_name in query['tags']
                                if 'remote_' + tag_name not in ret_tags})
        return ret_tags

    def verify_traffic_in_untagged_flows(self, untagged, query, traffics):
        ''' verify that traffic from/to untagged or partially tagged
            endpoints are present in untagged flows
        '''
        # TODO: assumes flow contains local_ip & remote_ip
        if not untagged and traffics:
            self.logger.error('untagged traffic is expected')
            return False
        for traf in traffics:
            traf_dict = self.get_tags_for_untagged(query, traf)
            traf_dict.update({'local_ip': traf.src_ip,
                              'remote_ip': traf.dst_ip,
                              'protocol': self.proto_name_to_nr[traf.proto],
                              'server_port': traf.dport
                              })
            for flow in untagged:
                self.logger.debug('untagged: %s' % flow)
                if traf_dict == flow:
                    break
            else:
                self.logger.error('expected traffic not seen untagged')
                self.logger.error(traf_dict)
                return False
        if len(untagged) != len(traffics):
            self.logger.error('mismatch in number of flow expected')
            return False
        return True

    def get_tags(self, vm, select_tags):
        ''' construct expected tags for traffic between fully tagged endpoints
        '''
        vn = self.vm_vn_map[vm.vm_name]
        vm_tags = self.vnc_h.get_tags(object_type='virtual-machine',
                                        uuid=vm.vm_id)
        vn_tags = self.vnc_h.get_tags(object_type='virtual-network',
                                        uuid=vn.vn_id)
        return [tag for tag in vm_tags+vn_tags
                if tag.tag_type_name in select_tags]

    def get_traffic_desc(self, traffic):
        return '%s:any:%s' % (traffic.proto.upper(), traffic.dport)

    def get_fqname_for_tag(self, tag):
        if not tag:
            return '__UNKNOWN__'
        fq_name = ':'.join(tag.fq_name)
        if not getattr(tag, 'parent_type', None):
            return 'global:' + fq_name
        else:
            return fq_name

    def get_fqname_for_tags(self, tags):
        return [self.get_fqname_for_tag(tag) for tag in tags]

    def get_src_dst_match_tags(self, query, traffic):
        ''' returns 3-element tuple
            [1] tags unique to src
            [2] tags unique to dst
            [3] tags common for both src & dst
        '''
        src_tags = self.get_tags(traffic.sender_vm, query['tags'])
        dst_tags = self.get_tags(traffic.receiver_vm, query['tags'])
        src_tag_strs = set(self.get_fqname_for_tags(src_tags))
        dst_tag_strs = set(self.get_fqname_for_tags(dst_tags))
        match_tags = list(src_tag_strs & dst_tag_strs)
        match_tags = [t.split(':')[-1].split('=')[0] for t in match_tags]
        return (list(src_tag_strs - dst_tag_strs),
               list(dst_tag_strs - src_tag_strs),
               match_tags)

    def get_app_tag(self, traffic):
        tags = self.get_tags(traffic.sender_vm, 'application')
        return tags[0] if tags else None

    def verify_flows_not_in_aps_rules(self, aps_list, query, not_expected):
        ''' verify that appplication-policy-set doesn't contain rules for
            traffic not expected to be reported by policy-generator
        '''
        for traf in not_expected:
            svc = self.get_traffic_desc(traf)
            src, dst, match = self.get_src_dst_match_tags(query, traf)
            src.sort()
            dst.sort()
            match.sort()
            app = self.get_fqname_for_tag(self.get_app_tag(traf))
            app = app if not app.startswith('global:') else app[7:]
            for aps in aps_list:
                if aps['application-policy-set']['application'] == app:
                    for policy in aps['application-policy-set']\
                                        ['firewall_policies']:
                        for rule in policy['firewall_policy']\
                                        ['firewall-rules']:
                            det = rule['firewall-rule']
                            det['endpoint_1']['tags'].sort()
                            det['endpoint_2']['tags'].sort()
                            det['match_tags']['tag_list_list'].sort()
                            if (det['endpoint_1']['tags'] == src and
                                det['endpoint_2']['tags'] == dst and
                                det['match_tags']['tag_list_list'] == match and
                                svc in det['services']):
                                self.logger.error('unexpected traffic seen')
                                msg = "flow:%s %s:%s - %s:%s" % (
                                    traff.proto,
                                    traf.src_ip, traf.sport,
                                    traf.dst_ip, traf.dport)
                                self.logger.error(msg)
                                self.logger.error(det)
                                return False
        return True

    def verify_flows_in_aps_rules(self, aps_list, query, grouped_traffics):
        ''' verify that appplication-policy-set contains rules for
            traffic expected to be reported by policy-generator
        '''
        class found(object):
            pass
        for traffics in grouped_traffics:
            if not traffics:
                continue
            src, dst, match = self.get_src_dst_match_tags(query, traffics[0])
            src.sort()
            dst.sort()
            match.sort()
            svc_list = [self.get_traffic_desc(traf) for traf in traffics]
            svc_list.sort()
            app = self.get_fqname_for_tag(self.get_app_tag(traffics[0]))
            app = app if not app.startswith('global:') else app[7:]
            try:
                for aps in aps_list:
                    if aps['application-policy-set']['application'] == app:
                        for policy in aps['application-policy-set']\
                                            ['firewall_policies']:
                            for rule in policy['firewall_policy']\
                                            ['firewall-rules']:
                                det = rule['firewall-rule']
                                det['endpoint_1']['tags'].sort()
                                det['endpoint_2']['tags'].sort()
                                det['match_tags']['tag_list_list'].sort()
                                det['services'].sort()
                                if (det['endpoint_1']['tags'] == src and
                                    det['endpoint_2']['tags'] == dst and
                                    det['match_tags']['tag_list_list'] == match and
                                    svc_list == det['services']):
                                    raise found
                return False
            except found:
                pass
        return True

    def verify_aps(self, aps_list, query):
        app_name_list = []
        app_tag_list = []
        for aps in aps_list:
            tag = aps['application-policy-set']['application']
            name = aps['application-policy-set']['name']
            q_aps = [i['name'] for i in query.get('aps',[])
                        if i['application'] == tag]
            if q_aps:
                if name != q_aps[0]:
                    self.logger.error('expected name:%s, got:%s',
                                        q_aps[0], name)
                    return False
            # validate for unique aps entries
            if tag in app_tag_list:
                self.logger.error('%s not unique aps', tag)
                return False
            # validate for unique aps name
            if name in app_name_list:
                self.logger.error('%s not unique aps-name', name)
                return False
            app_name_list.append(name)
            app_tag_list.append(tag)
            # ensure only on one policy entry for each aps
            nr_policies = len(aps['application-policy-set']
                                    ['firewall_policies'])
            if nr_policies != 1:
                self.logger.error('more than one policy')
                return False
        return True

    def verify_generated_rules(self, result, query, expected=[[]], not_expected=[], expected_untagged=[]):
        query['tags'] = query.get('tags', ['application', 'tier', 'site', 'deployment'])
        untagged = self.remove_unwanted_flows(result['untagged-flows'])
        self.logger.info('untagged: %s' % untagged)
        self.logger.info('aps: %s' % result['application-policy-sets'])
        self.logger.info('verifying untagged')
        assert self.verify_traffic_not_in_untagged_flows(untagged, not_expected), 'unexpected traffic seen in untagged flows'
        assert self.verify_traffic_in_untagged_flows(untagged, query, expected_untagged), 'expected traffic not seen in untagged flows'
        self.logger.info('verifying aps')
        assert self.verify_flows_not_in_aps_rules(result['application-policy-sets'], query, not_expected + expected_untagged), 'unexpected traffic seen in aps'
        assert self.verify_flows_in_aps_rules(result['application-policy-sets'], query, expected), 'expected traffic not seen in aps'
        assert self.verify_aps(result['application-policy-sets'], query)
        return True
