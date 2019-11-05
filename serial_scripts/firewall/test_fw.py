import test
from tcutils.wrappers import preposttest_wrapper
from common.firewall.base import BaseFirewallTest, BaseFirewallTest_1, FirewallBasic, FirewallDraftBasic
from collections import OrderedDict as dict
from tcutils import gevent_lib
from tcutils.util import get_an_ip
from vnc_api.vnc_api import BadRequest

class TestFirewallBasic(FirewallBasic):
    @preposttest_wrapper
    def test_local_scope(self):
        '''
        Validate local scope APS, FwP, FwR, ServiceGroup, AG, Tag
        Steps involved are same as test_global_scope
        '''
        self._create_objects('local', 'local')
        self._verify_traffic(self.vms['eng_web'], self.vms['eng_logic'], self.vms['eng_db'])
        self._verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], self.vms['hr_db'], exp=False)
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'], self.vms['hr_db'])

    @preposttest_wrapper
    def test_application_policy_set(self):
        '''
            Test Application policy set
            1) Create a mixture of local and global objects
            2) Remove application tag associated to the HR APS
            3) Add tag back and remove all FWPs associated to the HR APS
            4) Update application tag associated to APS
            5) Check if global APS gets precedence over local APS
            6) Check if apply-all global aps gets precedence over local and global aps
            7) Delete APS and check the behavior
        '''
        SCOPE1 = 'local'; SCOPE2 = 'global'
        self._create_objects(SCOPE1, SCOPE2)
        self._verify_traffic(self.vms['eng_web'], self.vms['eng_logic'], self.vms['eng_db'])
        self._verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], self.vms['hr_db'], exp=False)
        self._verify_ping(self.vms['hr_web'], self.vms['eng_logic'], self.vms['hr_db'])
        #Delete application association
        self.aps_hr.delete_tag(self.tags[SCOPE1]['application']['hr'])
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_db'], 'tcp',
                            sport=1111, dport=8005)
        #Delete all policies associated
        self.aps_hr.add_tag(self.tags[SCOPE1]['application']['hr'])
        self.aps_hr.delete_policies([{'uuid': self.fwp_hr.uuid, 'seq_no': 20}])
        self._verify_ping(self.vms['hr_web'], self.vms['eng_logic'], self.vms['hr_db'])
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_db'], 'tcp',
                            sport=1111, dport=8005)
        #Add back policies and Add subnets of hr network to ag
        self.aps_hr.add_policies([{'uuid': self.fwp_hr.uuid, 'seq_no': 20}])
        self.ag.add_subnets(self.vns['hr'].get_cidrs())
        self._verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], self.vms['hr_db'])
        self._verify_traffic(self.vms['eng_web'], self.vms['eng_logic'], self.vms['eng_db'])
        self._verify_ping(self.vms['eng_web'], self.vms['hr_logic'], self.vms['eng_db'])
        #Change application tag
        new_app_tag = self.create_tag('application', 'new_tag', SCOPE2)
        self.aps_hr.add_tag(new_app_tag)
        self.addCleanup(self.aps_hr.delete_tag, new_app_tag)
        self.set_tag(self.vns['hr'], new_app_tag)
        self._verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], self.vms['hr_db'])

        #Have both global and local aps for the same application, check precedence
        site_ep = {'tags': ['%s=%s'%('global:site', 'blr')]}
        new_fwr_1 = self.create_fw_rule(scope=SCOPE2, action='deny',
                             protocol='tcp',
                             dports=(8005, 8006), source=site_ep, destination=site_ep)
        new_fwr_2 = self.create_fw_rule(scope=SCOPE2, action='deny',
                             service_groups=[self.sg_icmp.uuid],
                             source=site_ep, destination=site_ep)
        rules = [{'uuid': new_fwr_1.uuid, 'seq_no': 10}, {'uuid': new_fwr_2.uuid, 'seq_no': 20}]
        new_fwp = self.create_fw_policy(scope=SCOPE2, rules=rules)
        policies = [{'uuid': new_fwp.uuid, 'seq_no': 1}]
        new_aps = self.create_aps(SCOPE2, policies=policies, application=new_app_tag)
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'],
                          self.vms['hr_db'], exp=False)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'tcp',
                            sport=1111, dport=8005, expectation=False)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'tcp',
                            sport=1111, dport=8009, expectation=True)
        rules = [{'uuid': new_fwr_2.uuid, 'seq_no': 20}]
        new_fwp.remove_firewall_rules(rules=rules)
        self._verify_ping(self.vms['eng_web'], self.vms['hr_logic'], self.vms['eng_db'])
        self._verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                             self.vms['hr_db'], dport=8002)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'tcp',
                            sport=1111, dport=8005, expectation=False)

        # Add Global application policy set and check the order
        global_aps = self.create_aps(name='default-application-policy-set',
                           scope='global')
        global_fwr = self.create_fw_rule(scope=SCOPE2, action='pass',
                          protocol='tcp', dports=(8005, 8005),
                          source=site_ep, destination=site_ep)
        global_fwr_icmp = self.create_fw_rule(scope=SCOPE2, action='deny',
                          protocol='icmp', source=site_ep, destination=site_ep)
        rules = [{'uuid': global_fwr.uuid, 'seq_no': 1},
                 {'uuid': global_fwr_icmp.uuid, 'seq_no': 2}]
        global_fwp = self.create_fw_policy(scope=SCOPE2, rules=rules)
        policies = [{'uuid': global_fwp.uuid, 'seq_no': 1}]
        global_aps.add_policies(policies)
        self.addCleanup(global_aps.delete_policies, policies)
        self._verify_ping(self.vms['eng_web'], self.vms['hr_logic'],
                          self.vms['eng_db'], exp=False)
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_logic'], 'tcp',
                            sport=1111, dport=8005)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'tcp',
                            sport=1111, dport=8006, expectation=False)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'tcp',
                            sport=1111, dport=8007)
        #Delete APS
        self.perform_cleanup(new_aps)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'tcp',
                            sport=1111, dport=8005)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'tcp',
                            sport=1111, dport=8006)

    @preposttest_wrapper
    def test_policy_order(self):
        '''
           Test Firewall policy order in APS
           1) add a policy with lowest seq no to the APS
           2) insert a policy with highest seq no to the APS
        '''
        SCOPE1 = 'local'; SCOPE2 = 'global'
        self._create_objects(SCOPE1, SCOPE2)
        site_ep = {'tags': ['%s=%s'%('global:site', 'blr')]}
        new_fwr = self.create_fw_rule(scope=SCOPE2, action='deny',
                             protocol='tcp',
                             dports=(8005, 8006), source=site_ep, destination=site_ep)
        new_fwr_2 = self.create_fw_rule(scope=SCOPE2, action='deny',
                             service_groups=[self.sg_icmp.uuid],
                             source=site_ep, destination=site_ep)
        rules = [{'uuid': new_fwr.uuid, 'seq_no': 10}, {'uuid': new_fwr_2.uuid, 'seq_no': 20}]
        new_fwp = self.create_fw_policy(scope=SCOPE2, rules=rules)
        policies = [{'uuid': new_fwp.uuid, 'seq_no': 10}]
        self.aps_eng.add_policies(policies)
        self.addCleanup(self.aps_eng.delete_policies, policies)
        self._verify_ping(self.vms['eng_web'], self.vms['eng_logic'],
                          self.vms['eng_db'], exp=False)
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'], 'tcp',
                            sport=1111, dport=8005, expectation=False)
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'], 'tcp',
                            sport=1111, dport=8009, expectation=True)
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'], self.vms['hr_db'])
        policies = [{'uuid': new_fwp.uuid, 'seq_no': 30}]
        self.aps_eng.add_policies(policies)
        self._verify_ping(self.vms['eng_web'], self.vms['eng_logic'], self.vms['eng_db'])
        self._verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                             self.vms['eng_db'], dport=8005)
    @preposttest_wrapper
    def test_rule_order(self):
        '''
           Test Firewall rule order in APS
           1) add a rule with lowest seq no to the FWP
           2) Delete the rule from fwp
           3) insert a rule with seq no in between icmp and tcp rules to the FWP
           4) insert a rule with highest seq no to the FWP
           5) Delete all rules and check whether traffic is being dropped
        '''
        SCOPE1 = 'local'; SCOPE2 = 'global'
        self._create_objects(SCOPE1, SCOPE2)
        site_ep = {'tags': ['%s=%s'%('global:site', 'blr')]}
        new_fwr = self.create_fw_rule(scope=SCOPE2, action='deny',
                             protocol='tcp',
                             dports=(8005, 8006), source=site_ep, destination=site_ep)
        new_fwr_2 = self.create_fw_rule(scope=SCOPE2, action='deny',
                             service_groups=[self.sg_icmp.uuid],
                             source=site_ep, destination=site_ep)
        # Insert with lowest seq no
        rules = [{'uuid': new_fwr.uuid, 'seq_no': 10}, {'uuid': new_fwr_2.uuid, 'seq_no': 11}]
        self.fwp_eng.add_firewall_rules(rules=rules)
        self.addCleanup(self.fwp_eng.remove_firewall_rules, rules)
        self._verify_ping(self.vms['eng_web'], self.vms['eng_logic'],
                          self.vms['eng_db'], exp=False)
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'], 'tcp',
                            sport=1111, dport=8005, expectation=False)
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'], 'tcp',
                            sport=1111, dport=8009, expectation=True)
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'], self.vms['hr_db'])
        # Delete rule
        self.fwp_eng.remove_firewall_rules(rules)
        self._verify_ping(self.vms['eng_web'], self.vms['eng_logic'], self.vms['eng_db'])
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'], 'tcp',
                            sport=1111, dport=8005)
        # Insert between icmp and tcp
        rules = [{'uuid': new_fwr.uuid, 'seq_no': 25}, {'uuid': new_fwr_2.uuid, 'seq_no': 26}]
        self.fwp_eng.add_firewall_rules(rules=rules)
        self._verify_ping(self.vms['eng_web'], self.vms['eng_logic'], self.vms['eng_db'])
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'], 'tcp',
                            sport=1111, dport=8005, expectation=False)
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'], 'tcp',
                            sport=1111, dport=8007, expectation=True)
        # Insert at the end
        rules = [{'uuid': new_fwr.uuid, 'seq_no': 99}, {'uuid': new_fwr_2.uuid, 'seq_no': 98}]
        self.fwp_eng.add_firewall_rules(rules=rules)
        self._verify_ping(self.vms['eng_web'], self.vms['eng_logic'], self.vms['eng_db'])
        self._verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                             self.vms['eng_db'], dport=8005)
        # Delete all FW Rules
        rules = [{'uuid': self.fwr_icmp.uuid, 'seq_no': 20},
                 {'uuid': self.fwr_eng_tcp.uuid, 'seq_no': 30},
                 {'uuid': self.fwr_eng_udp.uuid, 'seq_no': 40},
                 {'uuid': new_fwr_2.uuid, 'seq_no': 98},
                 {'uuid': new_fwr.uuid, 'seq_no': 99}]
        self.fwp_eng.remove_firewall_rules(rules)
        self._verify_ping(self.vms['eng_web'], self.vms['eng_logic'],
                          self.vms['eng_db'], exp=False)
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'], 'tcp',
                            sport=1111, dport=8005, expectation=False)

    @preposttest_wrapper
    def test_address_group(self):
        '''
           Address Group related tests
           1) Delete AG Label from ENG vms
           2) Add CIDR of HR VN to AG
           3) ReAssociate AG Label to ENG Logic Tier VM
           4) Delete AG Label from AG
           5) Delete CIDR of HR VN from AG
           6) FWR between with both EP1 and EP2 being AGs
           7) FWR with both EP1 and EP2 being same AG
           8) Add AG with multiple CIDR and multiple Labels
        '''
        SCOPE1 = 'local'; SCOPE2 = 'global'
        self._create_objects(SCOPE1, SCOPE2)
        #Disassociate AG Label from web-tier and logic-tier VM
        self.delete_labels(self.vms['eng_web'], [self.ag_label])
        self.delete_labels(self.vms['eng_logic'], [self.ag_label])
        self._verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                             self.vms['eng_db'], exp=False)
        #Add subnet to HR application
        self.ag.add_subnets(self.vns['hr'].get_cidrs())
        self._verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], self.vms['hr_db'])
        self._verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                             self.vms['eng_db'], exp=False)
        #ReAssociate AG label to logic-tier VM
        self.add_labels(self.vms['eng_logic'], [self.ag_label])
        self._verify_traffic(self.vms['eng_web'], self.vms['eng_logic'], self.vms['eng_db'])
        #Delete AG Label from AG
        self.delete_labels(self.ag, [self.ag_label])
        self._verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], self.vms['hr_db'])
        self._verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                             self.vms['eng_db'], exp=False)
        #Delete subnet
        self.ag.delete_subnets(self.vns['hr'].get_cidrs())
        self._verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], self.vms['hr_db'], exp=False)
        #Create new AG and add fwr between AGs
        self.ag.add_subnets(self.vns['eng'].get_cidrs())
        self.ag.add_subnets(self.vms['hr_logic'].get_vm_ips())
        web_label = self.create_tag('label', 'web', SCOPE2)
        db_label = self.create_tag('label', 'db', SCOPE2)
        new_ag = self.create_address_group(SCOPE1, labels=[web_label, db_label])
        self.add_labels(self.vms['hr_web'], [web_label])
        self.add_labels(self.vms['hr_db'], [db_label])
        ep1 = {'address_group':self.ag.fq_name_str}
        ep2 = {'address_group':new_ag.fq_name_str}
        fwr = self.create_fw_rule(scope=SCOPE1, source=ep1, destination=ep2, protocol='any')
        rules = [{'uuid': fwr.uuid, 'seq_no': 10}]
        self.fwp_hr.add_firewall_rules(rules)
        self.addCleanup(self.fwp_hr.remove_firewall_rules, rules)
        rules = [{'uuid': self.fwr_icmp.uuid, 'seq_no': 20},
                 {'uuid': self.fwr_hr_tcp.uuid, 'seq_no': 30},
                 {'uuid': self.fwr_hr_udp.uuid, 'seq_no': 40}]
        self.fwp_hr.remove_firewall_rules(rules)
        self._verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                             self.vms['eng_db'])
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'])
        self._verify_ping(self.vms['hr_logic'], self.vms['hr_db'])
        self._verify_ping(self.vms['hr_web'], self.vms['hr_db'], exp=False)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'tcp',
             sport=1111, dport=8006)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'udp',
             sport=1111, dport=8006)
        #Both EP1 and EP2 as same AG
        fwr.update(source=ep2, destination=ep2)
        self._verify_ping(self.vms['hr_web'], self.vms['hr_db'])
        self._verify_ping(self.vms['hr_logic'], self.vms['hr_db'], exp=False)
        self._verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                             self.vms['hr_db'], exp=False)
        # Add labels
        fwr.update(source=ep1, destination=ep1)
        self.add_labels(self.ag, [web_label, db_label])
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'tcp',
             sport=1111, dport=8002)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'udp',
             sport=1111, dport=8002)
        self._verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                             self.vms['eng_db'])

    @preposttest_wrapper
    def test_service_group(self):
        '''
           Service Group related tests
           1) Add another service to SG
           2) Delete the same and validate
           3) Disassociate SG from FWR and validate
           4) Add back SG and validate
           5) Have empty SG and validate
        '''
        SCOPE1 = 'local'; SCOPE2 = 'global'
        self._create_objects(SCOPE1, SCOPE2)
        # Add TCP Service for 8085 port
        self.sg_icmp.add_services([('tcp', (0,65535), (8085, 8085))])
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'], 'tcp',
                            sport=1111, dport=8085)
        self._verify_ping(self.vms['hr_web'], self.vms['eng_logic'], self.vms['hr_db'])
        # Delete the TCP service for 8085 port
        self.sg_icmp.delete_services([('tcp', (0,65535), (8085, 8085))])
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'], 'tcp',
                            sport=1111, dport=8085, expectation=False)
        # Disassociate SG from FWR
        try:
            self.fwr_icmp.remove_service_groups([self.sg_icmp.uuid])
            assert False, 'Remove of SG from FWRule should have failed'
        except BadRequest as e:
            self.logger.info("Got BadRequest exception as expected during "
                             "disassociation of SG from FW-Rule")
            pass
        self.fwr_icmp.update(protocol='udp', dports=(8085, 8085), service_groups=list())
        self._verify_ping(self.vms['hr_web'], self.vms['eng_logic'], self.vms['hr_db'], exp=False)
        # Associate back the SG to FWR and Empty the SG and ping should fail
        try:
            self.fwr_icmp.add_service_groups([self.sg_icmp.uuid])
            assert False, 'Associatin of SG to FWRule should have failed'
        except BadRequest as e:
            self.logger.info("Got BadRequest exception as expected during "
                             "association of SG to FW-Rule")
        self.fwr_icmp.update(service_groups=[self.sg_icmp.uuid])
        self._verify_ping(self.vms['hr_web'], self.vms['eng_logic'], self.vms['hr_db'])
        # Empty the SG and ping should fail
        self.sg_icmp.delete_services([('icmp', (0,65535), (0,65535))])
        self._verify_ping(self.vms['hr_web'], self.vms['eng_logic'], self.vms['hr_db'], exp=False)

    @preposttest_wrapper
    def test_rule_match_tag_type(self):
        '''
           Tests to validate the match keyword on FWRule
           1) Update the ICMP rule to match on application tag-type
           2) Update the rule to match on site tag-type
           3) Update the rule to match on tier tag-type
           4) Update the rule to match on deployment tag-type
           5) Match based on multiple tag types (tier and deployment)
           6) reset Match condtn to be empty
        '''
        SCOPE1 = 'global'; SCOPE2 = 'global'
        self._create_objects(SCOPE1, SCOPE2)
        self.ag.add_subnets(self.vns['hr'].get_cidrs())
        self._verify_ping(self.vms['eng_web'], self.vms['hr_logic'], self.vms['eng_db'])
        # update rule to match on application tag type
        self.fwr_icmp.update(match=['application'])
        self._verify_ping(self.vms['eng_web'], self.vms['hr_logic'], exp=False)
        self._verify_ping(self.vms['hr_logic'], self.vms['eng_db'], exp=False)
        self._verify_ping(self.vms['eng_web'], self.vms['eng_logic'],
                          self.vms['eng_db'])
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'],
                          self.vms['hr_db'])

        # change match to site
        self.fwr_icmp.update(match=['site'])
        self._verify_ping(self.vms['hr_web'], self.vms['eng_logic'],
                          self.vms['hr_db'])
        self._verify_ping(self.vms['eng_web'], self.vms['eng_logic'],
                          self.vms['eng_db'])

        # change match to tier
        web_tier = self.create_tag('tier', 'new-web-tier', SCOPE1)
        self.set_tag(self.vms['eng_web'], web_tier)
        self.set_tag(self.vms['hr_web'], web_tier)
        self.fwr_icmp.update(match=['tier'])
        self._verify_ping(self.vms['eng_web'], self.vms['hr_web'])
        self._verify_ping(self.vms['eng_web'], self.vms['eng_logic'], exp=False)

        self.set_tag(self.vms['hr_web'], self.tags[SCOPE1]['tier']['web'])
        self.set_tag(self.vms['eng_web'], self.tags[SCOPE2]['tier']['web'])
        # change match to deployment tag-type
        self.fwr_icmp.update(match=['deployment'])
        self._verify_ping(self.vms['hr_web'], self.vms['eng_logic'], self.vms['hr_db'])

        # Multiple match tags tier and deployment
        self.fwr_icmp.update(match=['tier', 'deployment'])
        self._verify_ping(self.vms['eng_web'], self.vms['hr_web'])
        self._verify_ping(self.vms['hr_logic'], self.vms['hr_web'], exp=False)
        self.set_tag(self.vns['hr'], self.tags[SCOPE1]['deployment']['prod'])
        self._verify_ping(self.vms['eng_web'], self.vms['hr_web'], exp=False)
        self._verify_ping(self.vms['hr_logic'], self.vms['hr_web'], exp=False)

        # change match to None
        self.fwr_icmp.update(match='None')
        self._verify_ping(self.vms['hr_web'], self.vms['eng_logic'],
                          self.vms['hr_db'])
        self._verify_ping(self.vms['eng_web'], self.vms['eng_logic'],
                          self.vms['eng_db'])

    @preposttest_wrapper
    def test_endpoint_type(self):
        '''
           Tests to validate the endpoint type keyword on FWRule
            (Site and Tier EPs covered by default hence ignoring them)
           1) Update the ICMP rule EPs as labels
           2) Update the rule with multiple labels for an EP
           3) Update the rule with Application tag as EP
           4) Update the rule with Deployment tag as EP
           5) Update the rule with VN FQName as EP
           6) Update the rule with both VN FQName and tag as EPs
           7) Update the rule with Any EP
        '''
        SCOPE1 = 'global'; SCOPE2 = 'global'
        self._create_objects(SCOPE1, SCOPE2)
        # Match on label as EndPoint
        label1 = self.create_tag('label', 'label1', SCOPE2)
        label2 = self.create_tag('label', 'label2', SCOPE2)
        self.add_labels(self.vms['eng_web'], [label1, label2])
        self.add_labels(self.vms['eng_logic'], [label1, label2])
        self.add_labels(self.vms['eng_db'], [label1])
        self.add_labels(self.vms['hr_web'], [label2])
        self.add_labels(self.vms['hr_logic'], [label1])
        web_ep = {'tags': ['global:label=label1']}
        logic_ep = {'tags': ['global:label=label2']}
        any_ep = {'any': True}
        self.fwr_icmp.update(source=web_ep, destination=logic_ep)
        # needed to reset the refs of labels/tags in FWR
        self.addCleanup(self.fwr_icmp.update, source=any_ep, destination=any_ep)
        self._verify_ping(self.vms['eng_web'], self.vms['eng_logic'],
                                 self.vms['eng_db'])
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'])
        self._verify_ping(self.vms['eng_db'], self.vms['hr_logic'], exp=False)
        # Match on multiple labels as EP
        ep1 = {'tags': ['global:label=label1', 'global:label=label2']}
        ep2 = {'tags': ['global:label=label1']}
        self.fwr_icmp.update(source=ep1, destination=ep2)
        self._verify_ping(self.vms['eng_web'], self.vms['eng_logic'],
                                 self.vms['eng_db'])
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'],
                                 self.vms['hr_db'], exp=False)
        # match on Application tag as EP
        ep1 = {'tags': ['global:label=label1', 'global:label=label2', 'global:application=eng']}
        ep2 = {'tags': ['global:label=label1', 'global:application=hr']}
        self.fwr_icmp.update(source=ep1, destination=ep2)
        self._verify_ping(self.vms['hr_web'], self.vms['eng_web'], exp=False)
        self._verify_ping(self.vms['eng_logic'], self.vms['eng_web'], exp=False)
        self._verify_ping(self.vms['eng_logic'], self.vms['hr_logic'])
        # match on Deployment tag as EP
        self.set_tag(self.vns['eng'], self.tags[SCOPE1]['deployment']['prod'])
        ep1 = {'tags': ['global:deployment=prod']}
        ep2 = {'tags': ['global:deployment=dev']}
        self.fwr_icmp.update(source=ep1, destination=ep2, match=['site'])
        self._verify_ping(self.vms['hr_web'], self.vms['eng_web'])
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'], exp=False)
        # match on VN FQName
        ep1 = {'virtual_network': self.vns['hr'].vn_fq_name}
        self.fwr_icmp.update(source=ep1, destination=ep1)
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'],
                                 self.vms['hr_db'])
        self._verify_ping(self.vms['eng_web'], self.vms['hr_logic'],
                                 self.vms['eng_db'], exp=False)
        # Match on both VN FQName and tag
        ep2 = {'tags': ['global:application=eng']}
        self.fwr_icmp.update(source=ep1, destination=ep2)
        self._verify_ping(self.vms['hr_web'], self.vms['eng_logic'])
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'], exp=False)
        # match on Any
        self.fwr_icmp.update(source=any_ep, destination=any_ep)
        self._verify_ping(self.vms['hr_web'], self.vms['eng_logic'],
                                 self.vms['hr_db'])

    @preposttest_wrapper
    def test_tag_import_order(self):
        '''
            Test the order in which the tags gets assigned to VMI
            Expect the same to be in Project -> VN -> VM -> VMI order
            Labels will be the summation in the order
            Steps:
                1) Create project, vn, vm and vmi tags and apply respectively
                2) Create project, vn, vm and vmi labels and apply respectively
                3) Verify VMI gets precedence over all
                4) Verify VM gets precedence over project and VN
                5) Verify VN gets precedence over project
                6) Verify label acts as summation
        '''
        SCOPE1 = 'local'; SCOPE2 = 'local'
        self._create_objects(SCOPE1, SCOPE2)
        vmi_id = self.vms['hr_web'].get_vmi_id(self.vms['hr_web'].vn_fq_name)
        port_fixture = self._get_port(vmi_id)
        project_tag = self.create_tag('deployment', 'project', SCOPE2)
        vn_tag = self.create_tag('deployment', 'vn', SCOPE2)
        vm_tag = self.create_tag('deployment', 'vm', SCOPE2)
        vmi_tag = self.create_tag('deployment', 'vmi', SCOPE2)
        project_label = self.create_tag('label', 'project', SCOPE2)
        vn_label = self.create_tag('label', 'vn', SCOPE2)
        vm_label = self.create_tag('label', 'vm', SCOPE2)
        vmi_label = self.create_tag('label', 'vmi', SCOPE2)
        project_ep = {'tags': ['deployment=project']}
        vn_ep = {'tags': ['deployment=vn']}
        vm_ep = {'tags': ['deployment=vm']}
        vmi_ep = {'tags': ['deployment=vmi']}
        self.addCleanup(self.set_tag, self.project,
                        self.tags[SCOPE1]['deployment']['dev'])
        any_ep = {'any': True}
        self.addCleanup(self.fwr_icmp.update, source=any_ep, destination=any_ep)
        self.set_tag(self.project, project_tag)
        self.set_tag(self.vns['hr'], vn_tag)
        self.set_tag(self.vms['hr_web'], vm_tag)
        self.set_tag(port_fixture, vmi_tag)

        # Check VMI gets precedence over all
        self.fwr_icmp.update(source=project_ep, destination=vmi_ep, match='None')
        self._verify_ping(self.vms['hr_web'], self.vms['eng_db'])
        self._verify_ping(self.vms['hr_web'], self.vms['hr_db'], exp=False)
        # Check VM gets precedence over VN and project
        self.fwr_icmp.update(source=project_ep, destination=vm_ep)
        self._verify_ping(self.vms['hr_web'], self.vms['eng_db'], exp=False)
        self.unset_tag(port_fixture, vmi_tag)
        self._verify_ping(self.vms['hr_web'], self.vms['eng_db'])
        self._verify_ping(self.vms['hr_web'], self.vms['hr_db'], exp=False)
        # Check VN gets precedence over project
        self.fwr_icmp.update(source=project_ep, destination=vn_ep)
        self._verify_ping(self.vms['hr_web'], self.vms['eng_db'], exp=False)
        self.unset_tag(self.vms['hr_web'], vm_tag)
        self._verify_ping(self.vms['hr_web'], self.vms['eng_db'])
        self._verify_ping(self.vms['hr_web'], self.vms['hr_db'], exp=False)

        # Check label summation
        project_ep = {'tags': ['label=project']}
        vn_ep = {'tags': ['label=vn']}
        vm_ep = {'tags': ['label=vm']}
        vmi_ep = {'tags': ['label=vmi']}
        self.add_labels(self.project, [project_label])
        self.add_labels(self.vns['hr'], [vn_label])
        self.add_labels(self.vms['hr_logic'], [vm_label])
        self.add_labels(port_fixture, [vmi_label])

        self.fwr_icmp.update(source=project_ep, destination=vmi_ep)
        self._verify_ping(self.vms['hr_db'], self.vms['hr_web'], exp=False)
        self.fwr_icmp.update(source=vn_ep, destination=vmi_ep)
        self._verify_ping(self.vms['hr_db'], self.vms['hr_web'])
        self.fwr_icmp.update(source=vm_ep, destination=vmi_ep)
        self._verify_ping(self.vms['hr_db'], self.vms['hr_web'], exp=False)
        self._verify_ping(self.vms['hr_logic'], self.vms['hr_web'])
#        ep1 = {'tags': ['label=project', 'label=vn', 'label=vm', 'label=vmi']}
#        self.fwr_icmp.update(source=project_ep, destination=ep1, match=None)
#        self._verify_ping(self.vms['hr_web'], self.vms['hr_db'])
#        self._verify_ping(self.vms['hr_db'], self.vms['hr_logic'], exp=False)

    @preposttest_wrapper
    def test_policy_application(self):
        '''
            Test a deny rule in either of NWP or FWP or SG drops the packet
            Steps:
                1) Create SG with rule to drop from ENG Web to DB VM
                2) Create NP with drop rule from ENG to HR for ICMP
                3) Create FWP with drop rule from ENG Logic to ENG DB
                4) Apply new SG with default FWP and NP(pass actions) and verify
                5) Apply new NP with default SG and FWP and verify
                6) Apply all newly created rules and verify
        '''
        self._create_objects('global', 'global')
        cidr = self.vms['hr_web'].get_vm_ips()[0]+'/32'
        sg_rule = self._get_secgrp_rule(protocol='tcp', dst_ports=(8004, 8006),
                                        cidr=cidr, direction='ingress')
        sg1 = self.create_security_group(rules=[sg_rule])
        default_sg = self.get_default_sg()
        self.vms['eng_db'].remove_security_group(default_sg.uuid)
        # Apply SG to HR DB
        self.vms['eng_db'].add_security_group(sg1.uuid)
        self.addCleanup(self.vms['eng_db'].remove_security_group, sg1.uuid)
        any_ep = {'any': True}
        self.fwr_hr_tcp.update(source=any_ep, destination=any_ep)
        self.fwr_eng_tcp.update(source=any_ep, destination=any_ep)
        # Traffic from eng-web to db-vm should fail
        # Traffic from hr-web to db-vm should pass
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_db'], 'tcp',
             sport=1111, dport=8006, expectation=False)
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             sport=1111, dport=8006)

        # Test NWP in conjuction with FWP
        hr_vn = self.vns['hr'].vn_fq_name
        eng_vn = self.vns['eng'].vn_fq_name
        nwp_rule1 = self._get_network_policy_rule(protocol='icmp', src_vn=hr_vn,
                         dst_vn=eng_vn, action='deny')
        nwp_rule2 = self._get_network_policy_rule(protocol='tcp', src_vn=hr_vn,
                         dst_vn=eng_vn, dst_ports=(8006, 8007), action='deny')
        nwp_rule3 = self._get_network_policy_rule(protocol='tcp', src_vn=hr_vn,
                         dst_vn=eng_vn, action='pass')
        nwp = self.create_policy(rules=[nwp_rule1, nwp_rule2, nwp_rule3])
        self.apply_policy(nwp, [self.vns['hr'], self.vns['eng']])
        # ICMP Traffic from eng db to hr db should fail
        self._verify_ping(self.vms['eng_db'], self.vms['hr_db'], exp=False)
        self._verify_ping(self.vms['eng_web'], self.vms['eng_logic'])
        # 8005 should work and 8006 should fail
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             sport=1111, dport=8006, expectation=False)
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             sport=1111, dport=8005)
        new_fwr = self.create_fw_rule(scope='global', action='deny',
                             protocol='tcp', dports=(8005, 8005))
        rules = [{'uuid': new_fwr.uuid, 'seq_no': 10}]
        self.fwp_eng.add_firewall_rules(rules=rules)
        self.addCleanup(self.fwp_eng.remove_firewall_rules, rules)
        self.fwp_hr.add_firewall_rules(rules=rules)
        self.addCleanup(self.fwp_hr.remove_firewall_rules, rules)
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             sport=1111, dport=8005, expectation=False)
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             sport=1111, dport=8006, expectation=False)
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             sport=1111, dport=8004)

class TestFirewall_1(BaseFirewallTest_1):
    @preposttest_wrapper
    def test_unidirection_rule(self):
        '''
           Tests to validate the unidirectional attribute
           Steps:
               1) Update TCP FWR to be of unidirection
               2) TCP traffic from eng-logic to eng-db should be fine
               3) new session from eng-db to eng-logic should be fine
               4) Update TCP FWR to be of bidirection
               5) new session from db to logic should be fine
        '''
        SCOPE1 = 'local'; SCOPE2 = 'global'
        self._create_objects(SCOPE1, SCOPE2)
        self.scope1_sg.delete_services([('tcp', (0,65535), (8000,8010))])
        self.scope1_sg.add_services([('tcp', (0,65535), (0, 65535))])
        self.fwr_hr_tcp.update(direction='>')
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                           'tcp', sport=1111, dport=8005, expectation=True)
        self.verify_traffic(self.vms['hr_logic'], self.vms['hr_web'],
                           'tcp', sport=8005, dport=1112, expectation=False)
        self.fwr_hr_tcp.update(direction='<>')
        self.verify_traffic(self.vms['hr_logic'], self.vms['hr_web'],
                           'tcp', sport=8005, dport=1112)

    def test_floating_ip(self):
        SCOPE1 = 'global'; SCOPE2 = 'global'
        fvn = self.create_vn()
        fvm = self.create_vm(vn_fixture=fvn)
        fip_pool = self.create_fip_pool(fvn.uuid)
        fip_ip, fip_id = self.create_and_assoc_fip(fip_pool, self.vms['hr_logic'])
        self._create_objects(SCOPE1, SCOPE2)

        # Validate regular FIP works
        assert self.check_vms_booted([fvm], do_assert=False)
        assert fvm.ping_with_certainty(fip_ip)

        vmi_tag = self.create_tag('deployment', 'vmi', SCOPE2)
        # Create FWR, FWP, APS for public network
        fvn_tag = self.create_tag('application', 'fvn', SCOPE1)
        self.set_tag(fvn, fvn_tag)
        fvn_ep = {'tags': ['global:application=fvn']}
        #web_ep = {'tags': ['global:tier=web']}
        logic_ep = {'tags': ['global:tier=logic']}
        any_ep = {'any': True}
        rule1 = self.create_fw_rule(scope=SCOPE1,
                      protocol='tcp', dports=(8085, 8085),
                      source=fvn_ep, destination=fvn_ep, match='None')
        rules = [{'uuid': rule1.uuid, 'seq_no': 10}]
        fvn_policy = self.create_fw_policy(scope=SCOPE1, rules=rules)
        fvn_aps = self.create_aps(SCOPE1, policies=[{'uuid': fvn_policy.uuid,
                                 'seq_no': 20}], application=fvn_tag)
        self.fwp_hr.add_firewall_rules(rules=rules)
        self.addCleanup(self.fwp_hr.remove_firewall_rules, rules)

        # Tag of FVN not applied to FIP IP
        self.verify_traffic(fvm, self.vms['hr_logic'],
            'tcp', sport=1111, dport=8085, fip_ip=fip_ip, expectation=False)
        assert fvm.ping_with_certainty(fip_ip, expectation=False)

        # Tag of Private-VM gets applied for FIP IP
        rule1.update(destination=logic_ep)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
            'tcp', sport=1111, dport=8007, expectation=True)
        self.verify_traffic(fvm, self.vms['hr_logic'],
            'tcp', sport=1111, dport=8085, fip_ip=fip_ip)
        # Tag of Private-VMI gets applied for FIP IP
        vmi_id = self.vms['hr_logic'].get_vmi_id(self.vms['hr_logic'].vn_fq_name)
        port_fixture = self._get_port(vmi_id)
        self.set_tag(port_fixture, vmi_tag)
        vmi_ep = {'tags': ['deployment=vmi']}
        rule1.update(destination=vmi_ep, action='deny')
        self.fwr_hr_tcp.update(match='None')
        self.verify_traffic(fvm, self.vms['hr_logic'],
            'tcp', sport=1112, dport=8085, fip_ip=fip_ip, expectation=False)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
            'tcp', sport=1112, dport=8007, expectation=True)

class TestFirewall_2(BaseFirewallTest_1):
    def test_subinterface(self):
        SCOPE1 = 'local'; SCOPE2 = 'local'
        self._create_objects(SCOPE1, SCOPE2)
        port1 = self.setup_vmi(uuid=self.vms['hr_web'].get_vmi_id(self.vns['hr'].vn_fq_name))
        port2 = self.setup_vmi(uuid=self.vms['hr_logic'].get_vmi_id(self.vns['hr'].vn_fq_name))
        port3 = self.setup_vmi(uuid=self.vms['hr_db'].get_vmi_id(self.vns['hr'].vn_fq_name))
        subintf_vn = self.create_vn()
        subint1 = self.setup_vmi(subintf_vn.uuid,
                                 parent_vmi=port1.vmi_obj,
                                 vlan_id='10',
                                 api_type='contrail',
                                 mac_address=port1.mac_address)
        subint2 = self.setup_vmi(subintf_vn.uuid,
                                 parent_vmi=port2.vmi_obj,
                                 vlan_id='10',
                                 api_type='contrail',
                                 mac_address=port2.mac_address)
        subint3 = self.setup_vmi(subintf_vn.uuid,
                                 parent_vmi=port3.vmi_obj,
                                 vlan_id='10',
                                 api_type='contrail',
                                 mac_address=port3.mac_address)
        subint1_ip = subint1.get_ip_addresses()[0]
        subint2_ip = subint2.get_ip_addresses()[0]
        subint3_ip = subint3.get_ip_addresses()[0]
        self.vms['hr_web'].setup_subintf(device='eth0', vlan='10')
        self.vms['hr_logic'].setup_subintf(device='eth0', vlan='10')
        self.vms['hr_db'].setup_subintf(device='eth0', vlan='10')
        assert self.vms['hr_web'].ping_with_certainty(subint2_ip)
        #Attach tag to VN
        self.set_tag(subintf_vn, self.tags[SCOPE1]['application']['hr'])
        #Check project tags got pushed to subintf vmis
        assert self.vms['hr_web'].ping_with_certainty(subint2_ip)

        #Disassociate AG Label from VM for VN label to take effect
        self.delete_labels(self.vms['hr_web'], [self.ag_label])
        self.delete_labels(self.vms['hr_logic'], [self.ag_label])
        self.delete_labels(self.vms['hr_db'], [self.ag_label])
        #Add subnet to HR application
        self.ag.add_subnets(self.vns['hr'].get_cidrs())

        #Check VN tags got pushed to subintf vmis
        vn_label = self.create_tag('label', 'sub-intf-vn', SCOPE1)
        self.add_labels(subintf_vn, [vn_label])
        ep = {'tags': ['label=sub-intf-vn']}
        new_fwr = self.create_fw_rule(scope=SCOPE1,
                      protocol='icmp', action='deny',
                      source=ep, destination=ep)
        rules = [{'uuid': new_fwr.uuid, 'seq_no': 10}]
        self.fwp_hr.add_firewall_rules(rules=rules)
        self.addCleanup(self.fwp_hr.remove_firewall_rules, rules)
        assert self.vms['hr_web'].ping_with_certainty(subint2_ip, expectation=False)
        #Check VM tags
        web_ep = {'tags': ['%s=%s'%('tier', 'web')]}
        db_ep = {'tags': ['%s=%s'%('tier', 'db')]}
        new_fwr.update(action='deny', source=web_ep, destination=db_ep)
        assert self.vms['hr_web'].ping_with_certainty(subint2_ip)
        assert self.vms['hr_web'].ping_with_certainty(subint3_ip, expectation=False)
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'])
        self._verify_ping(self.vms['hr_web'], self.vms['hr_db'], exp=False)
        #Check tags attached to SubIntf VMI
        tier_tag = self.create_tag('tier', 'sub-intf-vmi', SCOPE1)
        self.set_tag(subint1, tier_tag)
        self.set_tag(subint2, tier_tag)
        ep = {'tags': ['%s=%s'%('tier', 'sub-intf-vmi')]}
        new_fwr.update(action='deny', source=ep, destination=ep)
        any_ep = {'any': True}
        self.addCleanup(new_fwr.update, source=any_ep, destination=any_ep)
        assert self.vms['hr_web'].ping_with_certainty(subint2_ip, expectation=False)
        assert self.vms['hr_web'].ping_with_certainty(subint3_ip)
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'], self.vms['hr_db'])

class TestFirewall_3(BaseFirewallTest_1):
    image_name = 'ubuntu-keepalive'
    def test_allowed_address_pair(self):
        SCOPE1 = 'global'; SCOPE2 = 'global'
        self._create_objects(SCOPE1, SCOPE2)
        port1 = self.vms['hr_web'].get_vmi_id(self.vns['hr'].vn_fq_name)
        port2 = self.vms['hr_logic'].get_vmi_id(self.vns['hr'].vn_fq_name)
        vIP = get_an_ip(self.vns['hr'].get_cidrs()[0], offset=10)
        for port in [port1, port2]:
            self.config_aap(port, vIP, contrail_api=True)
        self.config_keepalive(self.vms['hr_web'], vIP, '50', '10')
        self.config_keepalive(self.vms['hr_logic'], vIP, '50', '20')
        assert self.vms['hr_db'].ping_with_certainty(vIP)
        any_ep = {'any': True}
        new_fwr = self.create_fw_rule(scope=SCOPE1,
                      protocol='udp', dports=(8085, 8085),
                      source=any_ep, destination=any_ep)
        rules = [{'uuid': new_fwr.uuid, 'seq_no': 10}]
        self.fwp_hr.add_firewall_rules(rules=rules)
        self.addCleanup(self.fwp_hr.remove_firewall_rules, rules)
        self.verify_traffic(self.vms['hr_db'], self.vms['hr_logic'],
            'udp', sport=1111, dport=8005, fip_ip=vIP, expectation=True)
        self.verify_traffic(self.vms['hr_db'], self.vms['hr_logic'],
            'udp', sport=1111, dport=8085, fip_ip=vIP, expectation=True)
        self.verify_traffic(self.vms['hr_db'], self.vms['hr_web'],
            'udp', sport=1111, dport=8085, fip_ip=vIP, expectation=False)
        #Flip the master
        self.service_keepalived(self.vms['hr_logic'], 'stop')
        self.sleep(30)
        self.verify_traffic(self.vms['hr_db'], self.vms['hr_web'],
            'udp', sport=1111, dport=8085, fip_ip=vIP)
        self.verify_traffic(self.vms['hr_db'], self.vms['hr_logic'],
            'udp', sport=1112, dport=8085, fip_ip=vIP, expectation=False)

class TestFirewallDraft_1(FirewallDraftBasic):
    @preposttest_wrapper
    def test_global_draft_mode(self):
        SCOPE1 = 'global'; SCOPE2 = 'global'
        self._test_draft_mode(SCOPE1, SCOPE2)

    @preposttest_wrapper
    def test_local_draft_mode(self):
        SCOPE1 = 'local'; SCOPE2 = 'local'
        self._test_draft_mode(SCOPE1, SCOPE2)

class TestFirewallDraftMisc(BaseFirewallTest):
    @preposttest_wrapper
    def test_misc_draft_mode_1(self):
        SCOPE1 = 'local'; SCOPE2 = 'global'
        # Test regular mode after enable/disable of draft without commit/discard
        self.enable_security_draft_mode(SCOPE1, SCOPE2)
        self.addCleanup(self.disable_security_draft_mode, SCOPE1, SCOPE2, retry=3)
        self.addCleanup(self.discard, SCOPE1, SCOPE2)
        services = [('tcp', (0,65535), (8000,8010))]
        sg = self.create_service_group(SCOPE2, services)
        any_ep = {'any': True}
        fwr = self.create_fw_rule(SCOPE1, source=any_ep, destination=any_ep,
                                  protocol='udp', dports=(8000,8010))
        fixture_states = {'created': [sg, fwr]}
        self.validate_draft(fixture_states, SCOPE1, SCOPE2)
        fwr.update(service_groups=[sg.uuid])
        self.validate_draft(fixture_states, SCOPE1, SCOPE2)
        self.perform_cleanup(fwr)
        self.validate_draft({'created': [sg]}, SCOPE1, SCOPE2)
        self.perform_cleanup(sg)
        self.validate_draft({}, SCOPE1, SCOPE2)
        self.disable_security_draft_mode(SCOPE1, SCOPE2)
        self.remove_from_cleanups(self.discard, SCOPE1, SCOPE2)

        sg = self.create_service_group(SCOPE2, services)
        fwr = self.create_fw_rule(SCOPE1, source=any_ep, destination=any_ep,
                                  service_groups=[sg.uuid])
        self.validate_draft({}, SCOPE1, SCOPE2)
        fwr.update(service_groups=[], protocol='tcp', dports=(8000,8010))
        self.validate_draft({}, SCOPE1, SCOPE2)
        self.perform_cleanup(fwr)
        self.perform_cleanup(sg)

    @preposttest_wrapper
    def test_misc_draft_mode_2(self):
        SCOPE1 = 'local'; SCOPE2 = 'global'
        services = [('tcp', (0,65535), (8000,8010))]
        any_ep = {'any': True}
        # Test regular mode after enable/disable of draft with commit/discard
        self.enable_security_draft_mode(SCOPE1, SCOPE2)
        self.addCleanup(self.disable_security_draft_mode, SCOPE1, SCOPE2, retry=3)
        self.addCleanup(self.discard, SCOPE1, SCOPE2)
        sg = self.create_service_group(SCOPE2, services)
        fwr = self.create_fw_rule(SCOPE1, source=any_ep, destination=any_ep,
                                  protocol='udp', dports=(8000,8010))
        fixture_states = {'created': [sg, fwr]}
        self.validate_draft(fixture_states, SCOPE1, SCOPE2)
        self.commit(SCOPE1, SCOPE2)
        self.validate_draft({}, SCOPE1, SCOPE2)
        fwr.update(service_groups=[sg.uuid])
        self.validate_draft({'updated': [fwr]}, SCOPE1, SCOPE2)
        self.discard(SCOPE1, SCOPE2)
        self.validate_draft({}, SCOPE1, SCOPE2)
        self.perform_cleanup(fwr)
        self.validate_draft({'deleted': [fwr]}, SCOPE1, SCOPE2)
        self.commit(SCOPE1, SCOPE2)
        self.validate_draft({}, SCOPE1, SCOPE2)
        self.disable_security_draft_mode(SCOPE1, SCOPE2)
        self.remove_from_cleanups(self.discard, SCOPE1, SCOPE2)

        fwr = self.create_fw_rule(SCOPE1, source=any_ep, destination=any_ep,
                                  service_groups=[sg.uuid])
        self.validate_draft({}, SCOPE1, SCOPE2)
        fwr.update(service_groups=[], protocol='tcp', dports=(8000,8010))
        self.validate_draft({}, SCOPE1, SCOPE2)
        self.perform_cleanup(fwr)
        self.perform_cleanup(sg)

    @preposttest_wrapper
    def test_misc_draft_mode_3(self):
        # Test switch between draft modes without commit on a existing resource
        SCOPE1 = 'local'; SCOPE2 = 'global'
        services = [('tcp', (0,65535), (8000,8010))]
        any_ep = {'any': True}
        sg = self.create_service_group(SCOPE2, services)
        fwr = self.create_fw_rule(SCOPE1, source=any_ep, destination=any_ep,
                                  protocol='udp', dports=(8000,8010))
        self.enable_security_draft_mode(SCOPE1, SCOPE2)
        self.addCleanup(self.disable_security_draft_mode, SCOPE1, SCOPE2, retry=3)
        self.addCleanup(self.discard, SCOPE1, SCOPE2)
        self.perform_cleanup(fwr)
        self.perform_cleanup(sg)
        self.validate_draft({'deleted': [sg, fwr]}, SCOPE1, SCOPE2)
        fwr.update(service_groups=[sg.uuid])
        sg.add_services([('tcp', (0,65535), (8010, 8020))])
        self.validate_draft({'updated': [fwr, sg]}, SCOPE1, SCOPE2)
        self.perform_cleanup(fwr)
        self.perform_cleanup(sg)
        self.validate_draft({'deleted': [fwr, sg]}, SCOPE1, SCOPE2)
        self.commit(SCOPE1, SCOPE2)

    @preposttest_wrapper
    def test_draft_mode_scope(self):
        # Draft on global mode shouldnt affect local mode
        # As well as draft on project1 shouldnt affect project2
        self.enable_security_draft_mode()
        self.addCleanup(self.disable_security_draft_mode, retry=3)
        self.addCleanup(self.commit)
        any_ep = {'any': True}
        services = [('tcp', (0,65535), (8000,8010))]
        sg_global = self.create_service_group('global', services)
        fwr_global = self.create_fw_rule('global', source=any_ep, destination=any_ep,
                                         service_groups=[sg_global.uuid])
        sg_local = self.create_service_group('local', services)
        fwr_local = self.create_fw_rule('local', source=any_ep, destination=any_ep,
                                         service_groups=[sg_local.uuid])
        fixture_states = {'created': [sg_global, fwr_global]}
        self.validate_draft(fixture_states, 'local', 'global')

        # Draft on project1 shouldnt affect project2 security objects
        proj1 = self.create_project()
        self.add_user_to_project(project_name=proj1.project_name)
        proj1_conn = proj1.get_project_connections()
        self.enable_security_draft_mode(project_fqname=proj1.project_fq_name)
        self.addCleanup(self.disable_security_draft_mode,
                        project_fqname=proj1.project_fq_name, retry=3)
        self.addCleanup(self.commit, project_fqname=proj1.project_fq_name)
        sg_proj1 = self.create_service_group('local', services, connections=proj1_conn)
        fwr_proj1 = self.create_fw_rule('local', source=any_ep, destination=any_ep,
                                         service_groups=[sg_proj1.uuid],
                                         connections=proj1_conn)
        fixture_states = {'created': [sg_global, fwr_global]}
        self.validate_draft(fixture_states, 'local', 'global')
        fixture_states = {'created': [sg_proj1, fwr_proj1]}
        self.validate_draft(fixture_states, project_fqname=proj1.project_fq_name)
        self.commit(project_fqname=proj1.project_fq_name)
        self.validate_draft({}, project_fqname=proj1.project_fq_name)
        fixture_states = {'created': [sg_global, fwr_global]}
        self.validate_draft(fixture_states, 'local', 'global')
        self.commit()
        self.validate_draft({}, 'local', 'global')

    @preposttest_wrapper
    def test_parallel_commit_discard_across_scopes(self):
        # Do parallel commit across projects and scopes
        SCOPE1='local'; SCOPE2='global'
        self.enable_security_draft_mode(SCOPE1, SCOPE2)
        self.addCleanup(self.disable_security_draft_mode, SCOPE1, SCOPE2, retry=3)
        self.addCleanup(self.commit, SCOPE1, SCOPE2)
        proj1 = self.create_project()
        self.add_user_to_project(project_name=proj1.project_name)
        proj1_conn = proj1.get_project_connections()
        self.enable_security_draft_mode(project_fqname=proj1.project_fq_name)
        self.addCleanup(self.disable_security_draft_mode,
                        project_fqname=proj1.project_fq_name, retry=3)
        self.addCleanup(self.commit, project_fqname=proj1.project_fq_name)

        local_objs = self.create_n_security_objects(scope=SCOPE1)
        global_objs = self.create_n_security_objects(scope=SCOPE2)
        proj_objs = self.create_n_security_objects(scope='local', connections=proj1_conn)
        objs = sum(list(local_objs.values()) + list(global_objs.values()), [])
        self.validate_draft({'created': objs}, SCOPE1, SCOPE2)
        objs = sum(list(proj_objs.values()), [])
        self.validate_draft({'created': objs}, project_fqname=proj1.project_fq_name)
        fn_and_args = [(self.commit, set(), dict()),
                       (self.commit, (SCOPE1,), dict()),
                       (self.commit, set(), {'project_fqname': proj1.project_fq_name})]
        greenlets = gevent_lib.exec_in_parallel(fn_and_args)
        gevent_lib.get_results(greenlets, raise_exception=True)

        self.validate_draft({}, project_fqname=proj1.project_fq_name)
        self.validate_draft({}, SCOPE1, SCOPE2)
        # Do parallel discard across projects and scopes
        self.cleanup_n_security_objects(local_objs)
        self.cleanup_n_security_objects(global_objs)
        self.cleanup_n_security_objects(proj_objs)
        objs = sum(list(local_objs.values()) + list(global_objs.values()), [])
        self.validate_draft({'deleted': objs}, SCOPE1, SCOPE2)
        objs = sum(list(proj_objs.values()), [])
        self.validate_draft({'deleted': objs}, project_fqname=proj1.project_fq_name)
        fn_and_args = [(self.discard, set(), dict()),
                       (self.discard, (SCOPE1,), dict()),
                       (self.discard, set(), {'project_fqname': proj1.project_fq_name})]
        greenlets = gevent_lib.exec_in_parallel(fn_and_args)
        gevent_lib.get_results(greenlets, raise_exception=True)

    @preposttest_wrapper
    def test_parallel_commit_discard_same_scope(self):
        # Do parallel commit in the same scope
        SCOPE1='local'; SCOPE2='global'
        self.enable_security_draft_mode(SCOPE1, SCOPE2)
        self.addCleanup(self.disable_security_draft_mode, SCOPE1, SCOPE2, retry=3)
        self.addCleanup(self.commit, SCOPE1, SCOPE2)

        local_objs = self.create_n_security_objects(scope=SCOPE1)
        global_objs = self.create_n_security_objects(scope=SCOPE2)
        objs = sum(list(local_objs.values()) + list(global_objs.values()), [])
        self.validate_draft({'created': objs}, SCOPE1, SCOPE2)
        fn_and_args = [(self.commit, set(), dict()),
                       (self.commit, set(), dict())]
        greenlets = gevent_lib.exec_in_parallel(fn_and_args)
        got_200 = got_exception = False
        for greenlet in greenlets:
            try:
                gevent_lib.get_async_output(greenlet)
                got_200 = True
            except BadRequest as e:
                got_exception = True
        assert got_200 and got_exception, 'Parallel commits failed on global'
        fn_and_args = [(self.commit, (SCOPE1,), dict()),
                       (self.commit, (SCOPE1,), dict())]
        greenlets = gevent_lib.exec_in_parallel(fn_and_args)
        got_200 = got_exception = False
        for greenlet in greenlets:
            try:
                gevent_lib.get_async_output(greenlet)
                got_200 = True
            except BadRequest as e:
                got_exception = True
        assert got_200 and got_exception, 'Parallel commits failed on local'
        self.validate_draft({}, SCOPE1, SCOPE2)
        # Do parallel discard in the same scope
        self.cleanup_n_security_objects(local_objs)
        self.cleanup_n_security_objects(global_objs)
        objs = sum(list(local_objs.values()) + list(global_objs.values()), [])
        self.validate_draft({'deleted': objs}, SCOPE1, SCOPE2)
        fn_and_args = [(self.discard, set(), dict()),
                       (self.discard, set(), dict())]
        greenlets = gevent_lib.exec_in_parallel(fn_and_args)
        got_200 = got_exception = False
        for greenlet in greenlets:
            try:
                gevent_lib.get_async_output(greenlet)
                got_200 = True
            except BadRequest as e:
                got_exception = True
        assert got_200 and got_exception, 'Parallel discards failed on global'

        fn_and_args = [(self.discard, (SCOPE1,), dict()),
                       (self.discard, (SCOPE1,), dict())]
        greenlets = gevent_lib.exec_in_parallel(fn_and_args)
        got_200 = got_exception = False
        for greenlet in greenlets:
            try:
                gevent_lib.get_async_output(greenlet)
                got_200 = True
            except BadRequest as e:
                got_exception = True
        assert got_200 and got_exception, 'Parallel discards failed on local'
        self.validate_draft({}, SCOPE1, SCOPE2)

    @preposttest_wrapper
    def test_discard_while_commit_in_progress(self):
        SCOPE1='local'; SCOPE2='global'
        self.enable_security_draft_mode(SCOPE1, SCOPE2)
        self.addCleanup(self.disable_security_draft_mode, SCOPE1, SCOPE2, retry=3)
        self.addCleanup(self.commit, SCOPE1, SCOPE2)

        local_objs = self.create_n_security_objects(scope=SCOPE1)
        global_objs = self.create_n_security_objects(scope=SCOPE2)
        objs = sum(list(local_objs.values()) + list(global_objs.values()), [])
        self.validate_draft({'created': objs}, SCOPE1, SCOPE2)
        fn_and_args = [(self.commit, set(), dict()),
                       (self.commit, (SCOPE1,), dict())]
        greenlets_commit = gevent_lib.exec_in_parallel(fn_and_args)
        fn_and_args = [(self.discard, set(), dict()),
                       (self.discard, (SCOPE1,), dict())]
        greenlets_discard = gevent_lib.exec_in_parallel(fn_and_args)
        for greenlet in greenlets_discard:
            try:
                gevent_lib.get_async_output(greenlet)
                assert False, 'Revert didnt fail while commit is in progress'
            except BadRequest as e:
                self.logger.info('Revert failed as expected while commit is in progress')
        gevent_lib.get_results(greenlets_commit, raise_exception=True)

    @preposttest_wrapper
    def test_commit_while_discard_in_progress(self):
        SCOPE1='local'; SCOPE2='global'
        self.enable_security_draft_mode(SCOPE1, SCOPE2)
        self.addCleanup(self.disable_security_draft_mode, SCOPE1, SCOPE2, retry=3)
        self.addCleanup(self.commit, SCOPE1, SCOPE2)

        local_objs = self.create_n_security_objects(scope=SCOPE1)
        global_objs = self.create_n_security_objects(scope=SCOPE2)
        objs = sum(list(local_objs.values()) + list(global_objs.values()), [])
        self.validate_draft({'created': objs}, SCOPE1, SCOPE2)
        fn_and_args = [(self.discard, set(), dict()),
                       (self.discard, (SCOPE1,), dict())]
        greenlets_discard = gevent_lib.exec_in_parallel(fn_and_args)
        fn_and_args = [(self.commit, set(), dict()),
                       (self.commit, (SCOPE1,), dict())]
        greenlets_commit = gevent_lib.exec_in_parallel(fn_and_args)
        for greenlet in greenlets_commit:
            try:
                gevent_lib.get_async_output(greenlet)
                assert False, 'Commit didnt fail while discard is in progress'
            except BadRequest as e:
                self.logger.info('Commit failed as expected while discard is in progress')
        gevent_lib.get_results(greenlets_discard, raise_exception=True)

    @preposttest_wrapper
    def test_CRUD_while_discard_in_progress(self):
        SCOPE1='local'; SCOPE2='global'
        fwp_local = self.create_fw_policy('local')
        fwp_global = self.create_fw_policy('global')
        sg_local = self.create_service_group('local')
        sg_global = self.create_service_group('global')
        services = [('tcp', (0,65535), (8085, 8085))]
        self.enable_security_draft_mode(SCOPE1, SCOPE2)
        self.addCleanup(self.disable_security_draft_mode, SCOPE1, SCOPE2, retry=3)
        self.addCleanup(self.commit, SCOPE1, SCOPE2)

        local_objs = self.create_n_security_objects(scope=SCOPE1)
        global_objs = self.create_n_security_objects(scope=SCOPE2)
        objs = sum(list(local_objs.values()) + list(global_objs.values()), [])
        self.validate_draft({'created': objs}, SCOPE1, SCOPE2)
        fn_and_args = [(self.discard, set(), dict()),
                       (self.discard, (SCOPE1,), dict())]
        greenlets_discard = gevent_lib.exec_in_parallel(fn_and_args)
        fn_and_args = [(self.perform_cleanup, (fwp_local,), dict()),
                       (self.perform_cleanup, (fwp_global,), dict()),
                       (self.create_address_group, ('local',), dict()),
                       (self.create_address_group, ('global',), dict()),
                       (sg_local.add_services, (services,), dict()),
                       (sg_global.add_services, (services,), dict())]
        self.sleep(1)
        greenlets = gevent_lib.exec_in_parallel(fn_and_args)
        for greenlet in greenlets:
            try:
                gevent_lib.get_async_output(greenlet)
                assert False, 'CRUD should have failed while discard is in progress'
            except BadRequest as e:
                self.logger.info('CRUD failed as expected while discard is in progress')
        gevent_lib.get_results(greenlets_discard, raise_exception=True)

    @preposttest_wrapper
    def test_CRUD_while_discard_in_progress_diff_project(self):
        SCOPE1='local'; SCOPE2='global'
        proj1 = self.create_project()
        self.add_user_to_project(project_name=proj1.project_name)
        proj1_conn = proj1.get_project_connections()
        fwp_proj = self.create_fw_policy('local', connections=proj1_conn)
        sg_proj = self.create_service_group('local', connections=proj1_conn)
        services = [('tcp', (0,65535), (8085, 8085))]
        self.enable_security_draft_mode(SCOPE1, SCOPE2)
        self.addCleanup(self.disable_security_draft_mode, SCOPE1, SCOPE2, retry=3)
        self.addCleanup(self.commit, SCOPE1, SCOPE2)

        local_objs = self.create_n_security_objects(scope=SCOPE1)
        global_objs = self.create_n_security_objects(scope=SCOPE2)
        objs = sum(list(local_objs.values()) + list(global_objs.values()), [])
        self.validate_draft({'created': objs}, SCOPE1, SCOPE2)
        fn_and_args = [(self.discard, set(), dict()),
                       (self.discard, (SCOPE1,), dict())]
        greenlets_discard = gevent_lib.exec_in_parallel(fn_and_args)
        fn_and_args = [(self.perform_cleanup, (fwp_proj,), dict()),
                       (self.create_address_group, ('local',),
                        {'connections': proj1_conn}),
                       (sg_proj.add_services, (services,), dict())]
        self.sleep(1)
        greenlets = gevent_lib.exec_in_parallel(fn_and_args)
        gevent_lib.get_results(greenlets, raise_exception=True)
        gevent_lib.get_results(greenlets_discard, raise_exception=True)

    @preposttest_wrapper
    def test_CRUD_while_commit_in_progress(self):
        SCOPE1='local'; SCOPE2='global'
        fwp_local = self.create_fw_policy('local')
        fwp_global = self.create_fw_policy('global')
        sg_local = self.create_service_group('local')
        sg_global = self.create_service_group('global')
        services = [('tcp', (0,65535), (8085, 8085))]
        self.enable_security_draft_mode(SCOPE1, SCOPE2)
        self.addCleanup(self.disable_security_draft_mode, SCOPE1, SCOPE2, retry=3)
        self.addCleanup(self.commit, SCOPE1, SCOPE2)
        self.addCleanup(self.sleep, 30)

        local_objs = self.create_n_security_objects(scope=SCOPE1)
        global_objs = self.create_n_security_objects(scope=SCOPE2)
        objs = sum(list(local_objs.values()) + list(global_objs.values()), [])
        self.validate_draft({'created': objs}, SCOPE1, SCOPE2)
        fn_and_args = [(self.commit, set(), dict()),
                       (self.commit, (SCOPE1,), dict())]
        greenlets_commit = gevent_lib.exec_in_parallel(fn_and_args)
        fn_and_args = [(self.perform_cleanup, (fwp_local,), dict()),
                       (self.perform_cleanup, (fwp_global,), dict()),
                       (self.create_address_group, ('local',), dict()),
                       (self.create_address_group, ('global',), dict()),
                       (sg_local.add_services, (services,), dict()),
                       (sg_global.add_services, (services,), dict())]
        self.sleep(1)
        greenlets = gevent_lib.exec_in_parallel(fn_and_args)
        for greenlet in greenlets:
            try:
                gevent_lib.get_async_output(greenlet)
                assert False, 'CRUD should have failed while commit is in progress'
            except BadRequest as e:
                self.logger.info('CRUD failed as expected while commit is in progress')
        gevent_lib.get_results(greenlets_commit, raise_exception=True)

    @preposttest_wrapper
    def test_CRUD_while_commit_in_progress_diff_project(self):
        SCOPE1='local'; SCOPE2='global'
        proj1 = self.create_project()
        self.add_user_to_project(project_name=proj1.project_name)
        proj1_conn = proj1.get_project_connections()
        fwp_proj = self.create_fw_policy('local', connections=proj1_conn)
        sg_proj = self.create_service_group('local', connections=proj1_conn)
        services = [('tcp', (0,65535), (8085, 8085))]
        self.enable_security_draft_mode(SCOPE1, SCOPE2)
        self.addCleanup(self.disable_security_draft_mode, SCOPE1, SCOPE2, retry=3)
        self.addCleanup(self.commit, SCOPE1, SCOPE2)

        local_objs = self.create_n_security_objects(scope=SCOPE1)
        global_objs = self.create_n_security_objects(scope=SCOPE2)
        objs = sum(list(local_objs.values()) + list(global_objs.values()), [])
        self.validate_draft({'created': objs}, SCOPE1, SCOPE2)
        fn_and_args = [(self.commit, set(), dict()),
                       (self.commit, (SCOPE1,), dict())]
        greenlets_commit = gevent_lib.exec_in_parallel(fn_and_args)
        fn_and_args = [(self.perform_cleanup, (fwp_proj,), dict()),
                       (self.create_address_group, ('local',),
                        {'connections': proj1_conn}),
                       (sg_proj.add_services, (services,), dict())]
        self.sleep(1)
        greenlets = gevent_lib.exec_in_parallel(fn_and_args)
        gevent_lib.get_results(greenlets, raise_exception=True)
        gevent_lib.get_results(greenlets_commit, raise_exception=True)
