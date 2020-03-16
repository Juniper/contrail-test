from common.policygen.base import BasePolicyGenTest
import time
import datetime
from tcutils.wrappers import preposttest_wrapper
from common.policygen.base import MatchOp

TRAFFIC_TIME = 5
WAIT_INTERVAL = 1

def utc_timestamp_usec():
    epoch = datetime.datetime.utcfromtimestamp(0)
    now = datetime.datetime.utcnow()
    delta = now - epoch
    return (delta.microseconds +
            (delta.seconds + delta.days * 24 * 3600) * 10 ** 6)

class TestPolicyGen(BasePolicyGenTest):
    @classmethod
    def setUpClass(cls):
        super(TestPolicyGen, cls).setUpClass()

    def _assign_tags (self, scope1='global', scope2='global'):
        self.set_tag(self.vns['hr'], self.tags[scope1]['application']['hr'])
        self.set_tag(self.vns['eng'], self.tags[scope1]['application']['eng'])
        self.set_tag(self.vms['hr_web'], self.tags[scope1]['tier']['web'])
        self.set_tag(self.vms['hr_logic'], self.tags[scope1]['tier']['logic'])
        self.set_tag(self.vms['hr_db'], self.tags[scope1]['tier']['db'])
        self.set_tag(self.vms['eng_web'], self.tags[scope1]['tier']['web'])
        self.set_tag(self.vms['eng_logic'], self.tags[scope2]['tier']['logic'])
        self.set_tag(self.vms['eng_db'], self.tags[scope2]['tier']['db'])
        self.set_tag(self.vms['hr_web'],
                        self.tags[scope1]['deployment']['dev'])
        self.set_tag(self.vms['eng_web'],
                        self.tags[scope1]['deployment']['dev'])
        self.set_tag(self.vms['hr_logic'],
                        self.tags[scope1]['deployment']['prod'])
        self.set_tag(self.vms['eng_logic'],
                        self.tags[scope1]['deployment']['prod'])
        self.set_tag(self.vms['hr_db'],
                        self.tags[scope1]['deployment']['prod'])
        self.set_tag(self.vms['eng_db'],
                        self.tags[scope1]['deployment']['prod'])
        self.set_tag(self.vms['hr_web'], self.tags[scope2]['site']['svl'])
        self.set_tag(self.vms['eng_web'], self.tags[scope2]['site']['svl'])
        self.set_tag(self.vms['hr_logic'], self.tags[scope2]['site']['blr'])
        self.set_tag(self.vms['eng_logic'], self.tags[scope2]['site']['blr'])
        self.set_tag(self.vms['hr_db'], self.tags[scope2]['site']['svl'])
        self.set_tag(self.vms['eng_db'], self.tags[scope2]['site']['svl'])

    @preposttest_wrapper
    def test_no_traffic(self):
        self._assign_tags()
        self.sleep(WAIT_INTERVAL)
        start_time = utc_timestamp_usec()
        self.sleep(TRAFFIC_TIME)
        end_time = utc_timestamp_usec()
        query_params = {'start_time': start_time, 'end_time': end_time}
        result = self.policy_gen.generate_policy(query_params)
        untagged = len(self.remove_unwanted_flows(result['untagged-flows']))
        aps = len(result['application-policy-sets'])
        msg = "no traffic expected, untagged:%d, aps:%d" % (untagged, aps)
        assert not untagged and not aps, msg

    @preposttest_wrapper
    def test_no_time_overlap(self):
        self._assign_tags()
        traffic_obj1 = self.start_traffic(self.vms['hr_web'],
                                self.vms['hr_logic'], 'tcp', 9000, 9100)
        self.sleep(TRAFFIC_TIME)
        self.stop_traffic(traffic_obj1)
        start_time = utc_timestamp_usec()
        self.sleep(TRAFFIC_TIME)
        end_time = utc_timestamp_usec()
        query_params = {'start_time': start_time, 'end_time': end_time}
        result = self.policy_gen.generate_policy(query_params)
        assert self.verify_generated_rules(result, query=query_params,
                                            not_expected=[traffic_obj1])

    @preposttest_wrapper
    def test_partial_time_overlap(self):
        self._assign_tags()
        traffic_obj1 = self.start_traffic(self.vms['hr_web'],
                                self.vms['hr_logic'],'tcp', 9001, 9101)
        start_time_1 = utc_timestamp_usec()
        self.sleep(TRAFFIC_TIME)
        end_time_1 = utc_timestamp_usec()
        self.stop_traffic(traffic_obj1)
        self.sleep(WAIT_INTERVAL)
        traffic_obj2 = self.start_traffic(self.vms['hr_logic'],
                                self.vms['hr_db'],'tcp', 10001, 11001)
        start_time_2 = utc_timestamp_usec()
        self.sleep(TRAFFIC_TIME)
        end_time_2 = utc_timestamp_usec()
        self.stop_traffic(traffic_obj2)
        query_params = {'start_time': start_time_1, 'end_time': end_time_1}
        result1 = self.policy_gen.generate_policy(query_params)
        query_params = {'start_time': start_time_2, 'end_time': end_time_2}
        result2 = self.policy_gen.generate_policy(query_params)
        assert self.verify_generated_rules(result1, query=query_params,
                    expected=[[traffic_obj1]], not_expected=[traffic_obj2])
        assert self.verify_generated_rules(result2, query=query_params,
                    expected=[[traffic_obj2]], not_expected=[traffic_obj1])

    @preposttest_wrapper
    def test_full_time_overlap(self):
        self._assign_tags()
        traffic_obj1 = self.start_traffic(self.vms['hr_web'],
                                self.vms['hr_logic'], 'tcp', 9002, 9102)
        start_time = utc_timestamp_usec()
        self.sleep(TRAFFIC_TIME)
        self.stop_traffic(traffic_obj1)
        traffic_obj2 = self.start_traffic(self.vms['hr_logic'],
                                self.vms['hr_db'], 'tcp', 10002, 11002)
        self.sleep(TRAFFIC_TIME)
        self.stop_traffic(traffic_obj2)
        end_time = utc_timestamp_usec()
        query_params = {'start_time': start_time, 'end_time': end_time}
        result = self.policy_gen.generate_policy(query_params)
        assert self.verify_generated_rules(result, query=query_params,
                    expected=[[traffic_obj1], [traffic_obj2]])

    @preposttest_wrapper
    def test_no_consolidate(self):
        self._assign_tags()
        traffic_obj1 = self.start_traffic(self.vms['eng_web'],
                                self.vms['eng_logic'], 'tcp', 9003, 9103)
        traffic_obj2 = self.start_traffic(self.vms['eng_web'],
                                self.vms['eng_logic'], 'tcp', 10003, 11003)
        start_time = utc_timestamp_usec()
        self.sleep(TRAFFIC_TIME)
        end_time = utc_timestamp_usec()
        self.stop_traffic(traffic_obj1)
        self.stop_traffic(traffic_obj2)
        query_params = {'start_time': start_time,
                        'end_time': end_time,
                        'consolidate': False}
        result = self.policy_gen.generate_policy(query_params)
        assert self.verify_generated_rules(result, query=query_params,
                        expected=[[traffic_obj1], [traffic_obj2]])

    @preposttest_wrapper
    def test_consolidate(self):
        self._assign_tags()
        traffic_obj1 = self.start_traffic(self.vms['eng_web'],
                                self.vms['eng_logic'], 'tcp', 9004, 9104)
        traffic_obj2 = self.start_traffic(self.vms['eng_web'],
                                self.vms['eng_logic'], 'tcp', 10004, 11004)
        start_time = utc_timestamp_usec()
        self.sleep(TRAFFIC_TIME)
        end_time = utc_timestamp_usec()
        self.stop_traffic(traffic_obj1)
        self.stop_traffic(traffic_obj2)
        query_params = {'start_time': start_time,
                        'end_time': end_time,
                        'consolidate': True}
        result = self.policy_gen.generate_policy(query_params)
        assert self.verify_generated_rules(result, query=query_params,
                        expected=[(traffic_obj1, traffic_obj2)])

    @preposttest_wrapper
    def test_project_tags(self):
        self._assign_tags('local', 'local')
        traffic_obj1 = self.start_traffic(self.vms['eng_web'],
                                self.vms['eng_logic'], 'tcp', 9005, 9105)
        traffic_obj2 = self.start_traffic(self.vms['eng_web'],
                                self.vms['eng_logic'], 'tcp', 10005, 11005)
        start_time = utc_timestamp_usec()
        self.sleep(TRAFFIC_TIME)
        end_time = utc_timestamp_usec()
        self.stop_traffic(traffic_obj1)
        self.stop_traffic(traffic_obj2)
        query_params = {'start_time': start_time,
                        'end_time': end_time,
                        'consolidate': True}
        result = self.policy_gen.generate_policy(query_params)
        assert self.verify_generated_rules(result, query=query_params,
                        expected=[[traffic_obj1, traffic_obj2]])

    @preposttest_wrapper
    def test_global_and_project_tags(self):
        self._assign_tags('global', 'local')
        traffic_obj1 = self.start_traffic(self.vms['eng_web'],
                                self.vms['eng_logic'], 'tcp', 9006, 9106)
        traffic_obj2 = self.start_traffic(self.vms['eng_web'],
                                self.vms['eng_logic'], 'tcp', 10006, 11006)
        start_time = utc_timestamp_usec()
        self.sleep(TRAFFIC_TIME)
        end_time = utc_timestamp_usec()
        self.stop_traffic(traffic_obj1)
        self.stop_traffic(traffic_obj2)
        query_params = {'start_time': start_time,
                        'end_time': end_time,
                        'consolidate': True}
        result = self.policy_gen.generate_policy(query_params)
        assert self.verify_generated_rules(result, query=query_params,
                        expected=[[traffic_obj1, traffic_obj2]])

    @preposttest_wrapper
    def test_multi_protocol(self):
        self._assign_tags()
        traffic_obj1 = self.start_traffic(self.vms['eng_web'],
                                self.vms['eng_logic'], 'tcp', 9007, 9107)
        traffic_obj2 = self.start_traffic(self.vms['hr_logic'],
                                self.vms['hr_db'], 'udp', 10007, 11007)
        traffic_obj3 = self.start_traffic(self.vms['eng_db'],
                                self.vms['eng_logic'], 'icmp', 0, 0)
        start_time = utc_timestamp_usec()
        self.sleep(TRAFFIC_TIME)
        end_time = utc_timestamp_usec()
        self.stop_traffic(traffic_obj1)
        self.stop_traffic(traffic_obj2)
        self.stop_traffic(traffic_obj3)
        query_params = {'start_time': start_time, 'end_time': end_time}
        result = self.policy_gen.generate_policy(query_params)
        assert self.verify_generated_rules(result, query=query_params,
                        expected=[[traffic_obj1], [traffic_obj2],
                                    [traffic_obj3]])

    @preposttest_wrapper
    def test_user_specified_aps_name(self):
        self._assign_tags()
        traffic_obj1 = self.start_traffic(self.vms['hr_web'],
                                self.vms['hr_logic'], 'tcp', 9009, 9109)
        traffic_obj2 = self.start_traffic(self.vms['hr_logic'],
                                self.vms['hr_db'], 'udp', 10009, 11009)
        traffic_obj3 = self.start_traffic(self.vms['eng_web'],
                                self.vms['eng_logic'], 'tcp', 9008, 9108)
        traffic_obj4 = self.start_traffic(self.vms['eng_logic'],
                                self.vms['eng_db'], 'tcp', 10008, 11008)
        start_time = utc_timestamp_usec()
        self.sleep(TRAFFIC_TIME)
        end_time = utc_timestamp_usec()
        self.stop_traffic(traffic_obj1)
        self.stop_traffic(traffic_obj2)
        self.stop_traffic(traffic_obj3)
        self.stop_traffic(traffic_obj4)
        query_params = {'start_time': start_time, 'end_time': end_time,
                        'aps': [{'application': 'application=hr',
                                    'name': 'myhr'},
                                {'application': 'application=eng',
                                    'name': 'myeng'}]}
        result = self.policy_gen.generate_policy(query_params)
        assert self.verify_generated_rules(result, query=query_params,
                        expected=[[traffic_obj1], [traffic_obj2],
                                    [traffic_obj3], [traffic_obj4]])

    @preposttest_wrapper
    def test_cross_app_traffic(self):
        self._assign_tags('local','local')
        traffic_obj1 = self.start_traffic(self.vms['hr_web'],
                                self.vms['eng_web'], 'tcp', 9010, 9110)
        traffic_obj2 = self.start_traffic(self.vms['eng_logic'],
                                self.vms['hr_logic'], 'udp', 10011, 11011)
        start_time = utc_timestamp_usec()
        self.sleep(TRAFFIC_TIME)
        end_time = utc_timestamp_usec()
        self.stop_traffic(traffic_obj1)
        self.stop_traffic(traffic_obj2)
        hr_tag = ':'.join(self.tags['local']['application']['hr'].fq_name)
        eng_tag = ':'.join(self.tags['local']['application']['eng'].fq_name)
        query_params = {'start_time': start_time, 'end_time': end_time,
                        'aps': [{'application': hr_tag,
                                    'name': 'myhr'},
                                {'application': eng_tag,
                                    'name': 'myeng'}]}
        result = self.policy_gen.generate_policy(query_params)
        assert self.verify_generated_rules(result, query=query_params,
                        expected=[[traffic_obj1], [traffic_obj2]])

    @preposttest_wrapper
    def test_query_where_clause(self):
        self._assign_tags()
        traffic_obj1 = self.start_traffic(self.vms['hr_web'],
                                self.vms['hr_logic'], 'tcp', 9012, 9112)
        traffic_obj2 = self.start_traffic(self.vms['hr_logic'],
                                self.vms['hr_db'], 'tcp', 9013, 9113)
        traffic_obj3 = self.start_traffic(self.vms['eng_web'],
                                self.vms['eng_logic'], 'udp', 10012, 11012)
        traffic_obj4 = self.start_traffic(self.vms['eng_logic'],
                                self.vms['eng_db'],'udp', 10012, 11012)
        start_time = utc_timestamp_usec()
        self.sleep(TRAFFIC_TIME)
        end_time = utc_timestamp_usec()
        self.stop_traffic(traffic_obj1)
        self.stop_traffic(traffic_obj2)
        self.stop_traffic(traffic_obj3)
        self.stop_traffic(traffic_obj4)
        query_params = {
            'start_time': start_time, 'end_time': end_time,
            'where':[[{'name':'tier', 'value':'tier=web', 'op':MatchOp.EQUAL},
                      {'name':'application', 'value':'application=hr',
                            'op':MatchOp.EQUAL}],
                     [{'name':'remote_tier',
                        'value':self.tags['global']['tier']['db'].tag_id,
                            'op':MatchOp.EQUAL},
                      {'name':'application', 'value':'application=eng',
                            'op':MatchOp.EQUAL}]]}
        result = self.policy_gen.generate_policy(query_params)
        assert self.verify_generated_rules(result, query=query_params,
                        expected=[[traffic_obj1], [traffic_obj4]],
                        not_expected=[traffic_obj2, traffic_obj3])

class TestPolicyGenUntagged(BasePolicyGenTest):
    @classmethod
    def setUpClass(cls):
        super(TestPolicyGenUntagged, cls).setUpClass()

    def _assign_tags (self, scope1='global', scope2='global'):
        self.set_tag(self.vns['hr'], self.tags[scope1]['application']['hr'])
        self.set_tag(self.vms['hr_web'], self.tags[scope1]['tier']['web'])
        self.set_tag(self.vms['hr_web'],
                self.tags[scope1]['deployment']['dev'])
        self.set_tag(self.vms['hr_web'], self.tags[scope2]['site']['svl'])
        self.set_tag(self.vms['hr_logic'], self.tags[scope1]['tier']['logic'])
        self.set_tag(self.vms['hr_logic'],
                self.tags[scope1]['deployment']['prod'])
        self.set_tag(self.vms['hr_db'], self.tags[scope1]['tier']['db'])
        self.set_tag(self.vms['hr_db'], self.tags[scope2]['site']['svl'])
        self.set_tag(self.vms['eng_logic'], self.tags[scope2]['site']['blr'])
        self.set_tag(self.vms['eng_logic'],
                self.tags[scope1]['deployment']['prod'])
        self.set_tag(self.vms['eng_db'], self.tags[scope2]['site']['svl'])
        self.set_tag(self.vms['eng_db'],
                self.tags[scope1]['deployment']['prod'])

    @preposttest_wrapper
    def test_untagged(self):
        self._assign_tags()
        traffic_obj1 = self.start_traffic(self.vms['hr_web'],
                                self.vms['hr_logic'], 'tcp', 9910, 9911)
        traffic_obj2 = self.start_traffic(self.vms['eng_web'],
                                self.vms['hr_web'], 'udp', 9920, 9921)
        traffic_obj3 = self.start_traffic(self.vms['hr_logic'],
                                self.vms['hr_db'], 'icmp', 0, 0)
        traffic_obj4 = self.start_traffic(self.vms['eng_logic'],
                                self.vms['eng_db'], 'icmp', 0, 0)
        start_time = utc_timestamp_usec()
        self.sleep(TRAFFIC_TIME)
        end_time = utc_timestamp_usec()
        self.stop_traffic(traffic_obj1)
        self.stop_traffic(traffic_obj2)
        self.stop_traffic(traffic_obj3)
        self.stop_traffic(traffic_obj4)
        query_params = {'start_time': start_time, 'end_time': end_time}
        result = self.policy_gen.generate_policy(query_params)
        assert self.verify_generated_rules(result, query=query_params,
                        expected_untagged = [traffic_obj1, traffic_obj2,
                                            traffic_obj3, traffic_obj4])

    @preposttest_wrapper
    def test_query_select_tags(self):
        self._assign_tags()
        traffic_obj1 = self.start_traffic(self.vms['hr_logic'],
                                self.vms['hr_db'], 'tcp', 9930, 9931)
        traffic_obj2 = self.start_traffic(self.vms['eng_logic'],
                                self.vms['eng_db'], 'udp', 9940, 9941)
        start_time = utc_timestamp_usec()
        self.sleep(TRAFFIC_TIME)
        end_time = utc_timestamp_usec()
        self.stop_traffic(traffic_obj1)
        self.stop_traffic(traffic_obj2)
        query_params1 = {'start_time': start_time, 'end_time': end_time, 'tags': ['application', 'tier']}
        result1 = self.policy_gen.generate_policy(query_params1)
        query_params2 = {'start_time': start_time, 'end_time': end_time, 'tags': ['application', 'deployment', 'site']}
        result2 = self.policy_gen.generate_policy(query_params2)
        assert self.verify_generated_rules(result1, query=query_params1,
                        expected=[[traffic_obj1]], expected_untagged=[traffic_obj2])
        assert self.verify_generated_rules(result2, query=query_params2,
                        expected_untagged=[traffic_obj2, traffic_obj1])
