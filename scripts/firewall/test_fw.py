import test
from tcutils.wrappers import preposttest_wrapper
from common.firewall.base import BaseFirewallTest
from collections import OrderedDict as dict

class TestFirewallBasic(BaseFirewallTest):
    @classmethod
    def setUpClass(cls):
        try:
            super(TestFirewallBasic, cls).setUpClass()
            cls.create_objects()
        except:
            cls.tearDownClass()
            raise

    @classmethod
    def create_objects(cls):
        ''' Create class specific objects
            1) Create VNs HR and ENG
            2) Create VMs Web, Logic, DB in each VN
            3) Create Network-Policy to interconnect VNs (for route leaking)
        '''
        cls.vns = dict(); cls.vms = dict(); cls.policys = dict()
        for vn in ['hr', 'eng']:
            cls.vns[vn] = cls.create_only_vn()
            for vm in ['web', 'logic', 'db']:
                cls.vms[vn+'_'+vm] = cls.create_only_vm(vn_fixture=cls.vns[vn])
        cls.policys['hr_eng'] = cls.setup_only_policy_between_vns(cls.vns['hr'],
                                                                 cls.vns['eng'])

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, 'policys', None) and 'hr_eng' in cls.policys:
            cls.vns['hr'].unbind_policies()
            cls.vns['eng'].unbind_policies()
            cls.policys['hr_eng'].cleanUp()
        super(TestFirewallBasic, cls).tearDownClass()

    def _create_objects(self, SCOPE1='local', SCOPE2='global'):
        '''
        Validate global scope APS, FwP, FwR, ServiceGroup, AG, Tag
        Steps:
            1. Associate global scope tag respectively,
               a. App tags to VNs
               b. Tier tags to VMs
               c. Site and deployment tags to Project
            2. Create AG and associate a scoped label
            3. Create SG with dst tcp 8000, icmp echo
            4. Create FWR bw web-Tier and Logic-Tier and SG (default match)
            5. Create another FWR bw Logic-Tier and DB-Tier for udp 8000 (default match)
            6. Create FwPolicy and attach both the rules
            7. Create APS with FwPolicy associated
            8. Validate with traffic EngApp able to communicate based on rules
            9. Validate that HRApp isnt able to communicate with itself
            10. Remove application tag from HRApp and should be able to communicate
        '''
        if SCOPE1 == 'global':
            SCOPE2 = 'global'
        ICMP = 'icmp' if (self.inputs.get_af() == 'v4') else 'icmp6'

        hr_app_tag = self.tags[SCOPE1]['application']['hr']
        eng_app_tag = self.tags[SCOPE2]['application']['eng']
        self.set_tag(self.vns['hr'], hr_app_tag)
        self.set_tag(self.vns['eng'], eng_app_tag)
        self.set_tag(self.vms['hr_web'], self.tags[SCOPE1]['tier']['web'])
        self.set_tag(self.vms['hr_logic'], self.tags[SCOPE1]['tier']['logic'])
        self.set_tag(self.vms['hr_db'], self.tags[SCOPE1]['tier']['db'])
        self.set_tag(self.vms['eng_web'], self.tags[SCOPE2]['tier']['web'])
        self.set_tag(self.vms['eng_logic'], self.tags[SCOPE2]['tier']['logic'])
        self.set_tag(self.vms['eng_db'], self.tags[SCOPE2]['tier']['db'])
        self.set_tag(self.project, self.tags[SCOPE1]['deployment']['dev'])
        self.set_tag(self.project, self.tags[SCOPE2]['site']['blr'])

        self.ag_label = self.create_tag('label', 'ag', SCOPE2)
        self.ag = self.create_address_group(SCOPE2, labels=[self.ag_label])
        services = [('tcp', (0,65535), (8000,8010))]
        self.scope1_sg = self.scope2_sg = self.create_service_group(SCOPE1, services)
        if SCOPE1 != SCOPE2:
            self.scope2_sg = self.create_service_group(SCOPE2, services)
        services = [('icmp', (0,65535), (0,65535))]
        self.sg_icmp = self.create_service_group(SCOPE2, services)

        logic_ep = {'address_group': self.ag.fq_name_str}
        prefix = 'global:' if SCOPE2 == 'global' else ''
        site_ep = {'tags': ['%s=%s'%(prefix+'site', 'blr')]}
        eng_web_ep = hr_web_ep = {'tags': ['%s=%s'%(prefix+'tier', 'web')]}
        eng_db_ep = hr_db_ep = {'tags': ['%s=%s'%(prefix+'tier', 'db')]}
        if SCOPE1 != SCOPE2:
            prefix = 'global:' if SCOPE1 == 'global' else ''
            hr_web_ep = {'tags': ['%s=%s'%(prefix+'tier', 'web')]}
            hr_db_ep = {'tags': ['%s=%s'%(prefix+'tier', 'db')]}
        self.fwr_icmp = self.create_fw_rule(scope=SCOPE2,
                             service_groups=[self.sg_icmp.uuid],
                             source=site_ep, destination=site_ep)
        self.fwr_eng_tcp = self.fwr_hr_tcp = self.create_fw_rule(scope=SCOPE2,
                             service_groups=[self.scope2_sg.uuid],
                             source=eng_web_ep, destination=logic_ep)
        self.fwr_eng_udp = self.fwr_hr_udp = self.create_fw_rule(scope=SCOPE2,
                             protocol='udp', dports=(8000,8010),
                             source=logic_ep, destination=eng_db_ep)
        if SCOPE1 != SCOPE2:
            self.fwr_hr_tcp = self.create_fw_rule(scope=SCOPE1,
                             service_groups=[self.scope1_sg.uuid],
                             source=hr_web_ep, destination=logic_ep)
            self.fwr_hr_udp = self.create_fw_rule(scope=SCOPE1, protocol='udp',
                             dports=(8000,8010), source=logic_ep,
                             destination=hr_db_ep)
        rules = [{'uuid': self.fwr_icmp.uuid, 'seq_no': 20},
                 {'uuid': self.fwr_hr_tcp.uuid, 'seq_no': 30},
                 {'uuid': self.fwr_hr_udp.uuid, 'seq_no': 40}]
        self.fwp_hr = self.fwp_eng = self.create_fw_policy(scope=SCOPE1, rules=rules)
        if SCOPE1 != SCOPE2:
            rules = [{'uuid': self.fwr_icmp.uuid, 'seq_no': 20},
                     {'uuid': self.fwr_eng_tcp.uuid, 'seq_no': 30},
                     {'uuid': self.fwr_eng_udp.uuid, 'seq_no': 40}]
            self.fwp_eng = self.create_fw_policy(scope=SCOPE2, rules=rules)
        self.aps_hr = self.create_aps(SCOPE1, policies=[{'uuid': self.fwp_hr.uuid, 'seq_no': 20}],
                                      application=hr_app_tag)
        self.aps_eng = self.create_aps(SCOPE2, policies=[{'uuid': self.fwp_eng.uuid, 'seq_no': 20}],
                                       application=eng_app_tag)
        for vm, obj in self.vms.iteritems():
            if vm.startswith('eng'):
                self.add_labels(obj, [self.ag_label])

        assert self.check_vms_booted(self.vms.itervalues(), do_assert=False)

    @preposttest_wrapper
    def test_global_scope(self):
        '''
        Validate global scope APS, FwP, FwR, ServiceGroup, AG, Tag
        Steps:
            1. Associate global scope tag respectively,
               a. App tags to VNs
               b. Tier tags to VMs
               c. Site and deployment tags to Project
            2. Create AG and associate a scoped label
            3. Create SG for icmp
            4. Create SG for tcp ports 8000-8010
            5. Associate AG Label to ENG vms
            6. Create FWR with ICMP SG with site EP
            7. Create FWR bw web-Tier and AG-Label for tcp SG
            8. Create FWR bw AG-Label and DB-Tier for udp ports 8000-8010
            9. Create FwPolicy and attach all the rules
            10. Create APS with FwPolicy associated
            11. Validate the FWRules with traffic
        '''
        self._create_objects('global', 'global')
        self._verify_traffic(self.vms['eng_web'], self.vms['eng_logic'], self.vms['eng_db'])
        self._verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], self.vms['hr_db'], exp=False)
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'], self.vms['hr_db'])

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
        new_fwr = self.create_fw_rule(scope=SCOPE2, action='deny',
                             service_groups=[self.sg_icmp.uuid], protocol='tcp',
                             dports=(8005, 8006), source=site_ep, destination=site_ep)
        rules = [{'uuid': new_fwr.uuid, 'seq_no': 10}]
        new_fwp = self.create_fw_policy(scope=SCOPE2, rules=rules)
        policies = [{'uuid': new_fwp.uuid, 'seq_no': 1}]
        new_aps = self.create_aps(SCOPE2, policies=policies, application=new_app_tag)
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'],
                          self.vms['hr_db'], exp=False)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'tcp',
                            sport=1111, dport=8005, expectation=False)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'tcp',
                            sport=1111, dport=8009, expectation=True)
        new_fwr.remove_service_groups([self.sg_icmp.uuid])
        self._verify_ping(self.vms['eng_web'], self.vms['hr_logic'], self.vms['eng_db'])
        self._verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                             self.vms['hr_db'], dport=8002)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'tcp',
                            sport=1111, dport=8005, expectation=False)

        # Add Global application policy set and check the order
        global_aps = self.create_aps(name='global-application-policy-set',
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
                             service_groups=[self.sg_icmp.uuid], protocol='tcp',
                             dports=(8005, 8006), source=site_ep, destination=site_ep)
        rules = [{'uuid': new_fwr.uuid, 'seq_no': 10}]
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
                             service_groups=[self.sg_icmp.uuid], protocol='tcp',
                             dports=(8005, 8006), source=site_ep, destination=site_ep)
        # Insert with lowest seq no
        rules = [{'uuid': new_fwr.uuid, 'seq_no': 10}]
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
        rules = [{'uuid': new_fwr.uuid, 'seq_no': 25}]
        self.fwp_eng.add_firewall_rules(rules=rules)
        self._verify_ping(self.vms['eng_web'], self.vms['eng_logic'], self.vms['eng_db'])
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'], 'tcp',
                            sport=1111, dport=8005, expectation=False)
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'], 'tcp',
                            sport=1111, dport=8007, expectation=True)
        # Insert at the end
        rules = [{'uuid': new_fwr.uuid, 'seq_no': 99}]
        self.fwp_eng.add_firewall_rules(rules=rules)
        self._verify_ping(self.vms['eng_web'], self.vms['eng_logic'], self.vms['eng_db'])
        self._verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                             self.vms['eng_db'], dport=8005)
        # Delete all FW Rules
        rules = [{'uuid': self.fwr_icmp.uuid, 'seq_no': 20},
                 {'uuid': self.fwr_eng_tcp.uuid, 'seq_no': 30},
                 {'uuid': self.fwr_eng_udp.uuid, 'seq_no': 40},
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
                 {'uuid': self.fwr_eng_tcp.uuid, 'seq_no': 30},
                 {'uuid': self.fwr_eng_udp.uuid, 'seq_no': 40}]
        self.fwp_hr.remove_firewall_rules(rules)
        self._verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                             self.vms['eng_db'])
        self._verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                             self.vms['hr_db'])
        #Both EP1 and EP2 as same AG
        fwr.update(source=ep1, destination=ep1)
        self._verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                             self.vms['hr_db'], exp=False)
        # Add labels
        self.add_labels(self.ag, [web_label, db_label])
        self._verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                             self.vms['hr_db'])
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
        self.fwr_icmp.remove_service_groups([self.sg_icmp.uuid])
        self._verify_ping(self.vms['hr_web'], self.vms['eng_logic'], self.vms['hr_db'])
        # Associate back the SG to FWR and Empty the SG and ping should fail
        self.fwr_icmp.add_service_groups([self.sg_icmp.uuid])
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
        self.fwr_icmp.update(source=project_ep, destination=vm_ep, match=None)
        self._verify_ping(self.vms['hr_web'], self.vms['eng_db'], exp=False)
        self.unset_tag(port_fixture, vmi_tag)
        self._verify_ping(self.vms['hr_web'], self.vms['eng_db'])
        self._verify_ping(self.vms['hr_web'], self.vms['hr_db'], exp=False)
        # Check VN gets precedence over project
        self.fwr_icmp.update(source=project_ep, destination=vn_ep, match=None)
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
        self.add_labels(self.vms['hr_web'], [vm_label])
        self.add_labels(port_fixture, [vmi_label])

        self.fwr_icmp.update(source=project_ep, destination=vmi_ep, match=None)
        self._verify_ping(self.vms['hr_web'], self.vms['hr_db'])
        self.fwr_icmp.update(source=project_ep, destination=vm_ep, match=None)
        self._verify_ping(self.vms['hr_web'], self.vms['hr_db'])
        self.fwr_icmp.update(source=project_ep, destination=vn_ep, match=None)
        self._verify_ping(self.vms['hr_logic'], self.vms['hr_db'])
        ep1 = {'tags': ['label=project', 'label=vn', 'label=vm', 'label=vmi']}
        self.fwr_icmp.update(source=project_ep, destination=ep1, match=None)
        self._verify_ping(self.vms['hr_web'], self.vms['hr_db'])
        self._verify_ping(self.vms['hr_db'], self.vms['hr_logic'], exp=False)

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

class TestFirewall_1(BaseFirewallTest):
    @classmethod
    def setUpClass(cls):
        try:
            super(TestFirewall_1, cls).setUpClass()
            cls.create_objects()
        except:
            cls.tearDownClass()
            raise

    @classmethod
    def create_objects(cls):
        ''' Create class specific objects
            1) Create VNs HR and ENG
            2) Create VMs Web, Logic, DB in each VN
            3) Create Network-Policy to interconnect VNs (for route leaking)
        '''
        cls.vns = dict(); cls.vms = dict(); cls.policys = dict()
        for vn in ['hr']:
            cls.vns[vn] = cls.create_only_vn()
            for vm in ['web', 'logic', 'db']:
                cls.vms[vn+'_'+vm] = cls.create_only_vm(vn_fixture=cls.vns[vn])

    def _create_objects(self, SCOPE1='local', SCOPE2='global'):
        '''
        Validate global scope APS, FwP, FwR, ServiceGroup, AG, Tag
        Steps:
            1. Associate global scope tag respectively,
               a. App tags to VNs
               b. Tier tags to VMs
               c. Site and deployment tags to Project
            2. Create AG and associate a scoped label
            3. Create SG with dst tcp 8000, icmp echo
            4. Create FWR bw web-Tier and Logic-Tier and SG (default match)
            5. Create another FWR bw Logic-Tier and DB-Tier for udp 8000 (default match)
            6. Create FwPolicy and attach both the rules
            7. Create APS with FwPolicy associated
            8. Validate with traffic EngApp able to communicate based on rules
            9. Validate that HRApp isnt able to communicate with itself
            10. Remove application tag from HRApp and should be able to communicate
        '''
        if SCOPE1 == 'global':
            SCOPE2 = 'global'
        ICMP = 'icmp' if (self.inputs.get_af() == 'v4') else 'icmp6'

        hr_app_tag = self.tags[SCOPE1]['application']['hr']
        self.set_tag(self.vns['hr'], hr_app_tag)
        self.set_tag(self.vms['hr_web'], self.tags[SCOPE1]['tier']['web'])
        self.set_tag(self.vms['hr_logic'], self.tags[SCOPE1]['tier']['logic'])
        self.set_tag(self.vms['hr_db'], self.tags[SCOPE1]['tier']['db'])
        self.set_tag(self.project, self.tags[SCOPE1]['deployment']['dev'])
        self.set_tag(self.project, self.tags[SCOPE2]['site']['blr'])

        self.ag_label = self.create_tag('label', 'ag', SCOPE2)
        self.ag = self.create_address_group(SCOPE2, labels=[self.ag_label])
        services = [('tcp', (0,65535), (8000,8010))]
        self.scope1_sg = self.scope2_sg = self.create_service_group(SCOPE1, services)
        if SCOPE1 != SCOPE2:
            self.scope2_sg = self.create_service_group(SCOPE2, services)
        services = [('icmp', (0,65535), (0,65535))]
        self.sg_icmp = self.create_service_group(SCOPE2, services)

        logic_ep = {'address_group': self.ag.fq_name_str}
        prefix = 'global:' if SCOPE2 == 'global' else ''
        site_ep = {'tags': ['%s=%s'%(prefix+'site', 'blr')]}
        prefix = 'global:' if SCOPE1 == 'global' else ''
        hr_web_ep = {'tags': ['%s=%s'%(prefix+'tier', 'web')]}
        hr_db_ep = {'tags': ['%s=%s'%(prefix+'tier', 'db')]}
        self.fwr_icmp = self.create_fw_rule(scope=SCOPE2,
                             service_groups=[self.sg_icmp.uuid],
                             source=site_ep, destination=site_ep)
        self.fwr_hr_tcp = self.create_fw_rule(scope=SCOPE1,
                             service_groups=[self.scope1_sg.uuid],
                             source=hr_web_ep, destination=logic_ep)
        self.fwr_hr_udp = self.create_fw_rule(scope=SCOPE1, protocol='udp',
                             dports=(8000,8010), source=logic_ep,
                             destination=hr_db_ep)
        rules = [{'uuid': self.fwr_icmp.uuid, 'seq_no': 20},
                 {'uuid': self.fwr_hr_tcp.uuid, 'seq_no': 30},
                 {'uuid': self.fwr_hr_udp.uuid, 'seq_no': 40}]
        self.fwp_hr = self.create_fw_policy(scope=SCOPE1, rules=rules)
        self.aps_hr = self.create_aps(SCOPE1, policies=[{'uuid': self.fwp_hr.uuid, 'seq_no': 20}],
                                      application=hr_app_tag)
        for vm, obj in self.vms.iteritems():
            if vm.startswith('hr'):
                self.add_labels(obj, [self.ag_label])

        assert self.check_vms_booted(self.vms.itervalues(), do_assert=False)

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
