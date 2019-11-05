import test
from tcutils.wrappers import preposttest_wrapper
from common.neutron.base import BaseNeutronTest
from common.firewall.base import BaseFirewallTest
from collections import OrderedDict as dict
from tcutils import gevent_lib
from tcutils.util import get_an_ip

class TestFwaasBasic(BaseFirewallTest):
    @classmethod
    def setUpClass(cls):
        super(TestFwaasBasic, cls).setUpClass()
        cls.api_type = 'neutron'

    def is_test_applicable(self):
        if self.inputs.get_build_sku() != 'rocky':
            return False, 'This testsuite is specific to rocky'
        return True, None
 
    @classmethod
    def create_common_objects(cls):
        ''' Create class specific objects
            1) Create VNs HR and ENG
            2) Create VMs Web, Logic, DB in each VN
            3) Create Network-Policy to interconnect VNs (for route leaking)
        '''
        cls.vns = dict(); cls.vms = dict(); cls.policys = dict()
        for vn in ['hr', 'eng']:
#        for vn in ['hr']:
            cls.vns[vn] = cls.create_only_vn()
            for vm in ['web', 'logic', 'db']:
                cls.vms[vn+'_'+vm] = cls.create_only_vm(vn_fixture=cls.vns[vn])
        cls.policys['hr_eng'] = cls.setup_only_policy_between_vns(cls.vns['hr'], cls.vns['eng'])
        assert cls.check_vms_active(iter(cls.vms.values()), do_assert=False)

#    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_fwaas_basic(self):
        ''' Allow/Restrict traffic between VMs
            1. Allow ICMP between HR-Web, HR-Logic and HR-DB
            2. Allow TCP src ports ANY and dst ports 8000:8010 between HR-Web and HR-Logic
            3. Allow UDP src ports 35300 and dst ports 8008 between HR-Logic and HR-DB
            4. Add FwG for all HR and ENG VMs
            5. Implicit deny Rule validation with ICMP between Eng-VMs failing
        '''
        icmp_fwr = self.create_fw_rule(
            source={'subnet': self.vns['hr'].get_cidrs()[0]},
            destination={'subnet': self.vns['hr'].get_cidrs()[0]},
            protocol='icmp')
        tcp_fwr = self.create_fw_rule(
            source={'subnet': self.get_ip_address(self.vms['hr_web'])},
            destination={'subnet': self.get_ip_address(self.vms['hr_logic'])},
            protocol='tcp', dports=('8000', '8010'))
        udp_fwr = self.create_fw_rule(
            source={'subnet': self.get_ip_address(self.vms['hr_logic'])},
            destination={'subnet': self.get_ip_address(self.vms['hr_db'])},
            protocol='udp', sports=('35300', ), dports=('8008', ))
        rules = list([{'uuid': x.uuid} for x in [icmp_fwr, tcp_fwr, udp_fwr]])
        fwp = self.create_fw_policy(rules=rules)
        fwg = self.create_fw_group(vm_fixtures=list(self.vms.values()),
                                   ingress_policy=fwp, egress_policy=fwp)
        assert self.check_vms_booted(iter(self.vms.values()), do_assert=False)

        self._verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
            self.vms['hr_db'], sport=35300, dport=8008)
        self._verify_ping(self.vms['eng_web'], self.vms['eng_logic'],
                          self.vms['hr_web'], exp=False)
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                          'tcp', expectation=False, sport=35300, dport=8002)
        # Insert deny udp all rule between HR-DB and HR-Logic
        udp_fwr_deny = self.create_fw_rule(action='deny', protocol='udp')
        fwp.insert_firewall_rule(udp_fwr_deny.uuid)
        self.addCleanup(fwp.remove_firewall_rules, [{'uuid': udp_fwr_deny.uuid}])
        self.verify_traffic(self.vms['hr_logic'], self.vms['hr_db'],
                          'udp', expectation=False, sport=35300, dport=8008)
        # Remove deny udp all rule
        fwp.remove_firewall_rules([{'uuid': udp_fwr_deny.uuid}])
        self.remove_from_cleanups(fwp.remove_firewall_rules, [{'uuid': udp_fwr_deny.uuid}])
        self.verify_traffic(self.vms['hr_logic'], self.vms['hr_db'],
                            'udp', sport=35300, dport=8008)

    @preposttest_wrapper
    def test_fwaas_rule_properties(self):
        proj1 = self.create_project()
