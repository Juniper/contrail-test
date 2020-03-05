from common.firewall.base import FirewallBasic, FirewallDraftBasic
import test
from tcutils.wrappers import preposttest_wrapper

class TestFirewallBasic(FirewallBasic):
    @test.attr(type=['vcenter'])
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

class TestFirewallDraftBasic(FirewallDraftBasic):
    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_mixed_draft_mode(self):
        SCOPE1 = 'local'; SCOPE2 = 'global'
        self._test_draft_mode(SCOPE1, SCOPE2)
