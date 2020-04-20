import test
from tcutils.wrappers import preposttest_wrapper
from common.neutron.base import BaseNeutronTest
from common.firewall.base import BaseFirewallTest
from collections import OrderedDict as dict
from tcutils import gevent_lib
from tcutils.util import get_an_ip
from common.openstack_libs import neutron_exception

class BaseFwaaSTest(BaseFirewallTest):
    @classmethod
    def setUpClass(cls):
        super(BaseFwaaSTest, cls).setUpClass()
        cls.api_type = 'neutron'
        cls.neutron_h = cls.connections.quantum_h

    def is_test_applicable(self):
        if self.inputs.get_build_sku()[0] < 'r':
            return False, 'FWaaSv2 needs atleast rocky, current sku %s'%(
                self.inputs.get_build_sku())
        return True, None
 
    @classmethod
    def create_common_objects(cls):
        ''' Create class specific objects
            1) Create VNs HR and ENG
            2) Create VMs Web, Logic, DB in each VN
            3) Create Network-Policy to interconnect VNs (for route leaking)
        '''
        cls.vns = dict(); cls.vms = dict(); cls.policys = dict()
        cls.save_af = cls.inputs.get_af()
        cls.inputs.set_af(cls.af)
        for vn in ['hr', 'eng']:
            cls.vns[vn] = cls.create_only_vn()
            for vm in ['web', 'logic', 'db']:
                cls.vms[vn+'_'+vm] = cls.create_only_vm(vn_fixture=cls.vns[vn],
                    image_name='cirros-traffic')
        cls.policys['hr_eng'] = cls.setup_only_policy_between_vns(cls.vns['hr'], cls.vns['eng'])
        assert cls.check_vms_active(iter(cls.vms.values()), do_assert=False)

    def _test_fwaas_basic(self):
        ''' Allow/Restrict traffic between VMs
            1. Allow ICMP between HR-Web, HR-Logic and HR-DB
            2. Allow TCP src ports ANY and dst ports 8000:8010 between HR-Web and HR-Logic
            3. Allow UDP src ports 35300 and dst ports 8008 between HR-Logic and HR-DB
            4. Add FwG for all HR and ENG VMs
            5. Implicit deny Rule validation with ICMP between Eng-VMs failing
        '''
        ip_version = 4 if (self.inputs.get_af() == 'v4') else 6
        icmp_fwr = self.create_fw_rule(
            source={'subnet': self.vns['hr'].get_cidrs()[0]},
            destination={'subnet': self.vns['hr'].get_cidrs()[0]},
            protocol='icmp', ip_version=ip_version)
        tcp_fwr = self.create_fw_rule(
            source={'subnet': self.get_ip_address(self.vms['hr_web'])},
            destination={'subnet': self.get_ip_address(self.vms['hr_logic'])},
            protocol='tcp', dports=('8000', '8010'), ip_version=ip_version)
        udp_fwr = self.create_fw_rule(
            source={'subnet': self.get_ip_address(self.vms['hr_logic'])},
            destination={'subnet': self.get_ip_address(self.vms['hr_db'])},
            protocol='udp', sports=('30000', '65535'), dports=('8008', ),
            ip_version=ip_version)
        rules = list(map(lambda x: {'uuid': x.uuid}, [icmp_fwr, tcp_fwr, udp_fwr]))
        fwp = self.create_fw_policy(rules=rules)
        fwg = self.create_fw_group(vm_fixtures=self.vms.values(),
                                   ingress_policy=fwp, egress_policy=fwp)
        # Validate list firewall groups
        assert fwg.uuid in [group['id'] for group in
                            self.neutron_h.list_firewall_groups()]
        # Validate list firewall policy
        assert fwp.uuid in [policy['id'] for policy in
                            self.neutron_h.list_firewall_policies()]
        # Validate list firewall rules
        fw_rules = [rule['id'] for rule in self.neutron_h.list_firewall_rules()]
        assert icmp_fwr.uuid in fw_rules
        assert tcp_fwr.uuid in fw_rules
        assert udp_fwr.uuid in fw_rules
        assert self.check_vms_booted(self.vms.itervalues(), do_assert=False)

        # Validating TCP and UDP flows matching allow and implicit deny
        self._verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
            self.vms['hr_db'], sport=35300, dport=8008)
        # Validate ICMP allow
        assert self.vms['hr_web'].ping_with_certainty(self.vms['hr_logic'].vm_ip, count=2)
        # Validate ICMP implicit deby
        assert self.vms['eng_web'].ping_with_certainty(self.vms['eng_logic'].vm_ip, count=2, expectation=False)
        assert self.vms['hr_web'].ping_with_certainty(self.vms['eng_logic'].vm_ip, count=2, expectation=False)
        # Validating implicit deny for tcp
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                          'tcp', expectation=False, sport=35300, dport=8002)

class TestFwaasV6(BaseFwaaSTest):
    af = 'v6'
    @preposttest_wrapper
    def test_fwaas_v6(self):
        self._test_fwaas_basic()

class TestFwaas(BaseFwaaSTest):
    af = 'v4'
#    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_fwaas_basic(self):
        self._test_fwaas_basic()

    @preposttest_wrapper
    def test_fwaas_api_restart(self):
        self._test_fwaas_basic()

        self.inputs.restart_container(self.inputs.cfgm_ips, 'api-server')
        self.sleep(15)

        # Validating TCP and UDP flows matching allow and implicit deny
        self._verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
            self.vms['hr_db'], sport=35300, dport=8008)
        # Validate ICMP allow
        assert self.vms['hr_web'].ping_with_certainty(self.vms['hr_logic'].vm_ip, count=2)
        # Validate ICMP implicit deby
        assert self.vms['eng_web'].ping_with_certainty(self.vms['eng_logic'].vm_ip, count=2, expectation=False)
        assert self.vms['hr_web'].ping_with_certainty(self.vms['eng_logic'].vm_ip, count=2, expectation=False)
        # Validating implicit deny for tcp
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                          'tcp', expectation=False, sport=35300, dport=8002)

    @preposttest_wrapper
    def test_fwaas_policy(self):
        ''' Allow/Restrict traffic between VMs
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
            protocol='udp', sports=('30000', '65535'), dports=('8008', ))
        rules = list([{'uuid': x.uuid} for x in [icmp_fwr, tcp_fwr, udp_fwr]])
        fwp = self.create_fw_policy(rules=rules)
        fwg = self.create_fw_group(vm_fixtures=list(self.vms.values()),
                                   ingress_policy=fwp, egress_policy=fwp)

        # Validating TCP and UDP flows matching allow and implicit deny
        self._verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
            self.vms['hr_db'], sport=35300, dport=8008)
        # Insert deny udp all rule after tcp allow rule
        udp_fwr_deny = self.create_fw_rule(action='deny', protocol='udp')
        fwp.insert_firewall_rule(udp_fwr_deny.uuid, insert_after=tcp_fwr.uuid)
        self.addCleanup(fwp.remove_firewall_rules, [{'uuid': udp_fwr_deny.uuid}])
        self.verify_traffic(self.vms['hr_logic'], self.vms['hr_db'],
                          'udp', expectation=False, sport=35300, dport=8008)
        # Remove deny udp all rule
        self.perform_cleanup(fwp.remove_firewall_rules, [{'uuid': udp_fwr_deny.uuid}])
        self.verify_traffic(self.vms['hr_logic'], self.vms['hr_db'],
                            'udp', sport=35300, dport=8008)
        # Insert deny tcp all rule before udp allow rule
        tcp_fwr_deny = self.create_fw_rule(action='deny',
            source={'subnet': self.get_ip_address(self.vms['hr_web'])},
            destination={'subnet': self.get_ip_address(self.vms['hr_logic'])},
            protocol='tcp', sports=('30000', '65535'), dports=('8005', ))
        fwp.insert_firewall_rule(tcp_fwr_deny.uuid, insert_before=udp_fwr.uuid)
        self.addCleanup(fwp.remove_firewall_rules, [{'uuid': tcp_fwr_deny.uuid}])
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                            'tcp', sport=35300, dport=8005)
        # Remove tcp allow rule
        fwp.remove_firewall_rules([{'uuid': tcp_fwr.uuid}])
        # explicit deny
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                            'tcp', sport=35300, dport=8005, expectation=False)
        # implicit deny
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                            'tcp', sport=35353, dport=8005, expectation=False)
        # Insert at top
        icmp_fwr_deny = self.create_fw_rule(action='deny', protocol='icmp',
            source={'subnet': self.get_ip_address(self.vms['hr_web'])})
        fwp.insert_firewall_rule(icmp_fwr_deny.uuid, insert_before=icmp_fwr.uuid)
        self.addCleanup(fwp.remove_firewall_rules, [{'uuid': icmp_fwr_deny.uuid}])
        assert self.vms['hr_web'].ping_with_certainty(self.vms['hr_logic'].vm_ip,
            count=2, expectation=False)
        # Delete at top
        self.perform_cleanup(fwp.remove_firewall_rules, [{'uuid': icmp_fwr_deny.uuid}])
        assert self.vms['hr_web'].ping_with_certainty(self.vms['hr_logic'].vm_ip, count=2)
        # Insert allow tcp all rule after udp allow rule
        tcp_fwr_allow = self.create_fw_rule(protocol='tcp', dports=('8010', ))
        fwp.insert_firewall_rule(tcp_fwr_allow.uuid, insert_after=udp_fwr.uuid)
        self.addCleanup(fwp.remove_firewall_rules, [{'uuid': tcp_fwr_allow.uuid}])
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                            'tcp', sport=35300, dport=8010)
        # Remove tcp allow rule
        self.perform_cleanup(fwp.remove_firewall_rules, [{'uuid': tcp_fwr_allow.uuid}])
        # explicit deny
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                            'tcp', sport=35300, dport=8010, expectation=False)
        tcp_fwr_allow_2 = self.create_fw_rule(protocol='tcp', sports=('30000', '60000'))
        fwp.insert_firewall_rule(tcp_fwr_allow_2.uuid)
        self.addCleanup(fwp.remove_firewall_rules, [{'uuid': tcp_fwr_allow_2.uuid}])
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                            'tcp', sport=35300, dport=8010)
        # Remove tcp allow rule
        self.perform_cleanup(fwp.remove_firewall_rules, [{'uuid': tcp_fwr_allow_2.uuid}])
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                            'tcp', sport=35300, dport=8010, expectation=False)

        # Firewall policy update of rules
        fwp.update(rules=[{'uuid': tcp_fwr_allow_2.uuid}])
        self.addCleanup(fwp.remove_firewall_rules, [{'uuid': tcp_fwr_allow_2.uuid}])
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                            'tcp', sport=35300, dport=8010)
        assert self.vms['hr_web'].ping_with_certainty(self.vms['hr_logic'].vm_ip, count=2, expectation=False)

        # Firewall policy update name
        fwp.update(name=fwp.name+'-new')
        assert fwp.get_object()['name'] == fwp.name+'-new'
        assert fwp.get_object()['audited'] == True, "Possibly due to CEM-8735"
        fwp.update(audited=False)
        assert fwp.get_object()['audited'] == False
        #self.verify_traffic(self.vms['hr_logic'], self.vms['hr_db'],
        #                    'udp', sport=35300, dport=8008, expectation=False)

    @preposttest_wrapper
    def test_fwaas_shared(self):
        proj2 = self.create_project()
        self.add_user_to_project(project_name=proj2.project_name)
        proj2_conn = proj2.get_project_connections()
        proj2_vn = self.create_vn(connections=proj2_conn)
        proj2_vm1 = self.create_vm(connections=proj2_conn, vn_fixture=proj2_vn, image_name='cirros-traffic')
        proj2_vm2 = self.create_vm(connections=proj2_conn, vn_fixture=proj2_vn, image_name='cirros-traffic')
        tcp_fwr = self.create_fw_rule(protocol='tcp', dports=('443', '443'))
        fwp = self.create_fw_policy(rules=[{'uuid': tcp_fwr.uuid}], shared=True)
        fwg = self.create_fw_group(vm_fixtures=list(self.vms.values()),
                                   egress_policy=fwp)
        default_fwg2 = self.create_fw_group(name='default', connections=proj2_conn)
        default_fwg2.update(ports=[])
        proj2_fwg = self.create_fw_group(vm_fixtures=[proj2_vm1, proj2_vm2],
            connections=proj2_conn, egress_policy=fwp)
        self.check_vms_booted(list(self.vms.values())+[proj2_vm1, proj2_vm2])
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                          'tcp', dport=443)
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                          'tcp', expectation=False, dport=8143)
        self.verify_traffic(proj2_vm1, proj2_vm2, 'tcp', dport=443)
        self.verify_traffic(proj2_vm1, proj2_vm2, 'tcp', dport=8143, expectation=False)

        #FwG shared
        self.setup_policy_between_vns(proj2_vn, self.vns['eng'])
        self.perform_cleanup(proj2_fwg)
        fwg.update(shared=True)
        self.verify_traffic(self.vms['eng_web'], proj2_vm1, 'tcp', dport=443, expectation=False)
# Below test is commented because of a neutron bug
#        fwg_shared = self.create_fw_group(uuid=fwg.uuid, connections=proj2_conn, verify=False)
#        fwg_shared.add_ports([self._get_vmi_uuid(fixture) for fixture in [proj2_vm1, proj2_vm2]])
#        self.verify_traffic(self.vms['eng_web'], proj2_vm1, 'tcp', dport=443)
#        self.verify_traffic(self.vms['eng_web'], proj2_vm1, 'tcp', dport=8143, expectation=False)

        fwp.update(shared=False)
        # Creation should fail?
        proj2_fwg = self.create_fw_group(vm_fixtures=[proj2_vm1, proj2_vm2],
            connections=proj2_conn, ingress_policy=fwp, egress_policy=fwp)
        self.verify_traffic(proj2_vm1, proj2_vm2, 'tcp', dport=443)
        self.verify_traffic(proj2_vm1, proj2_vm2, 'tcp', dport=8143, expectation=False)
        fwp.update(shared=True)
#        proj2_fwg = self.create_fw_group(vm_fixtures=[proj2_vm1, proj2_vm2],
#            connections=proj2_conn, ingress_policy=fwp, egress_policy=fwp)
#        self.verify_traffic(proj2_vm1, proj2_vm2, 'tcp', dport=443)
#        self.verify_traffic(proj2_vm1, proj2_vm2, 'tcp', dport=8143, expectation=False)

    @preposttest_wrapper
    def test_fwaas_group(self):
        icmp_fwr = self.create_fw_rule(protocol='icmp')
        tcp_fwr = self.create_fw_rule(
            source={'subnet': self.get_ip_address(self.vms['eng_web'])},
            destination={'subnet': self.get_ip_address(self.vms['eng_logic'])},
            protocol='tcp', dports=('8000', '8010'))
        rules = list(map(lambda x: {'uuid': x.uuid}, [icmp_fwr, tcp_fwr]))
        fwp = self.create_fw_policy(rules=rules)
        fwp1 = self.create_fw_policy(rules=[{'uuid': icmp_fwr.uuid}])
        fwg = self.create_fw_group(vm_fixtures=[self.vms['hr_web'], self.vms['hr_logic']],
                                    ingress_policy=fwp)
        fwg1 = self.create_fw_group(vm_fixtures=[self.vms['eng_web'], self.vms['eng_logic']],
                                    ingress_policy=fwp1)
        assert self.vms['hr_web'].ping_with_certainty(self.vms['hr_logic'].vm_ip, count=2)
        assert self.vms['eng_web'].ping_with_certainty(self.vms['eng_logic'].vm_ip, count=2)
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                          'tcp', expectation=False, sport=35300, dport=8002)
        fwg1.update(ingress_policy_id=fwp.uuid, egress_policy_id=fwp.uuid)
        assert self.vms['eng_web'].ping_with_certainty(self.vms['eng_logic'].vm_ip, count=2)
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                          'tcp', sport=35300, dport=8002)
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                          'udp', expectation=False, sport=35300, dport=8008)
        # Remove VMI associations from FwGroup
        ports = [self._get_vmi_uuid(fixture) for fixture in [self.vms['eng_web'],
                                                         self.vms['eng_logic']]]
        fwg1.update(ports=list())
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                          'udp', sport=35300, dport=8008)
        # Add back VMI association
        fwg1.update(ports=ports)
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                            'udp', expectation=False, sport=35300, dport=8008)
        #Negative
        try:
            fwg1.update(ingress_policy_id=fwp1.uuid, egress_policy_id=fwp.uuid)
            assert False, 'ingress and egress policy has to be same uuid'
        except neutron_exception.BadRequest:
            pass
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                            'udp', expectation=False, sport=35300, dport=8002)

        assert fwg1.get_object()['admin_state_up'] == True
        fwg1.update(admin_state=False)
        assert fwg1.get_object()['admin_state_up'] == False
        try:
            self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                                'udp', sport=35300, dport=8002)
        except AssertionError:
           assert False, "Possibly due to CEM-8725"
        fwg1.update(admin_state=True)
        assert fwg1.get_object()['admin_state_up'] == True
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                            'udp', expectation=False, sport=35300, dport=8002)
        #Same VMI part of two groups not supported yet
        self.perform_cleanup(fwg1)
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_logic'],
                            'udp', sport=35300, dport=8002)

    @preposttest_wrapper
    def test_fwaas_validate_default(self):
        proj1 = self.create_project()
        proj2 = self.create_project()
        self.add_user_to_project(project_name=proj1.project_name)
        proj1_conn = proj1.get_project_connections()
        self.add_user_to_project(project_name=proj2.project_name)
        proj2_conn = proj2.get_project_connections()

        proj1_vn = self.create_vn(connections=proj1_conn)
        proj2_vn = self.create_vn(connections=proj2_conn)
        proj1_vm1 = self.create_vm(connections=proj1_conn, vn_fixture=proj1_vn,
            image_name='cirros-traffic')
        proj2_vm1 = self.create_vm(connections=proj2_conn, vn_fixture=proj2_vn,
            image_name='cirros-traffic')
        self.setup_policy_between_vns(proj2_vn, proj1_vn)
        assert self.check_vms_booted([proj1_vm1, proj2_vm1])
        proj1_vm1.disassociate_security_groups()
        proj2_vm1.disassociate_security_groups()
        self.verify_traffic(proj1_vm1, proj2_vm1, 'tcp', dport=443, expectation=False)

        tcp_fwr = self.create_fw_rule(protocol='tcp', dports=('443', '443'), shared=True)
        fwp = self.create_fw_policy(rules=[{'uuid': tcp_fwr.uuid}], shared=True)
        default_fwg1 = self.create_fw_group(name='default', connections=proj1_conn)
        default_fwg2 = self.create_fw_group(name='default', connections=proj2_conn)
        default_fwg1.update(ingress_policy_id=fwp.uuid, egress_policy_id=fwp.uuid)
        self.addCleanup(default_fwg1.update, ingress_policy_id=None, egress_policy_id=None)
        default_fwg2.update(ingress_policy_id=fwp.uuid, egress_policy_id=fwp.uuid)
        self.addCleanup(default_fwg2.update, ingress_policy_id=None, egress_policy_id=None)
        self.verify_traffic(proj1_vm1, proj2_vm1, 'tcp', dport=443)
        default_fwg2.update(ingress_policy_id=None, egress_policy_id=None)
        self.verify_traffic(proj1_vm1, proj2_vm1, 'tcp', dport=443)
        self.verify_traffic(proj1_vm1, proj2_vm1, 'tcp', dport=8143, expectation=False)

        fwp2 = self.create_fw_policy(rules=[{'uuid': tcp_fwr.uuid}],
            connections=proj2_conn)
        default_fwg2.update(ingress_policy_id=fwp2.uuid, egress_policy_id=fwp2.uuid)
        self.addCleanup(default_fwg2.update, ingress_policy_id=None, egress_policy_id=None)
        self.verify_traffic(proj1_vm1, proj2_vm1, 'tcp', dport=443)
        self.verify_traffic(proj1_vm1, proj2_vm1, 'tcp', dport=8143, expectation=False)

    @preposttest_wrapper
    def test_fwaas_rule_properties(self):
        tcp_fwr = self.create_fw_rule(
            source={'subnet': self.get_ip_address(self.vms['hr_web'])},
            destination={'subnet': self.get_ip_address(self.vms['hr_logic'])},
            protocol='tcp', dports=('8000', '8010'))
        fwp = self.create_fw_policy(rules=[{'uuid': tcp_fwr.uuid}])
        fwg = self.create_fw_group(vm_fixtures=[self.vms['hr_web']],
                                   ingress_policy=fwp, egress_policy=fwp)

        # Validating TCP and UDP flows matching allow and implicit deny
        fwr_2 = self.create_fw_rule(
            source={'firewall_group_id': fwg.uuid},
            destination={'subnet': self.get_ip_address(self.vms['hr_logic'])},
            protocol='tcp', dports=('8008', ))
        fwp2 = self.create_fw_policy(rules=[{'uuid': fwr_2.uuid}])
        fwg2 = self.create_fw_group(vm_fixtures=[self.vms['hr_logic']],
                                   ingress_policy=fwp2, egress_policy=fwp2)
        # Validating TCP and UDP flows matching allow and implicit deny
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                          'tcp', dport=8008)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                          'tcp', dport=8002, expectation=False)

        tcp_fwr.update(action='deny')
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                          'tcp', dport=8008, expectation=False)
        tcp_fwr.update(action='pass')
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                          'tcp', dport=8008)
        tcp_fwr.update(dports=('8080', '8090'))
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                          'tcp', dport=8008, expectation=False)

        fwg3 = self.create_fw_group(vm_fixtures=[self.vms['eng_web'],
                                                 self.vms['eng_logic']])
        #Firewall group without any policies is allow all
        assert self.vms['eng_web'].ping_with_certainty(self.vms['eng_logic'].vm_ip,
            count=2)
        #Firewall Group with fwp with empty rules
        fwp3 = self.create_fw_policy(rules=[])
        fwg3.update(ingress_policy_id=fwp3.uuid, egress_policy_id=fwp3.uuid)
        self.addCleanup(fwg3.update, ingress_policy_id=None, egress_policy_id=None)
        assert self.vms['eng_web'].ping_with_certainty(self.vms['eng_logic'].vm_ip,
            count=2, expectation=False)

        icmp_fwr = self.create_fw_rule(
            source={'firewall_group_id': fwg3.uuid},
            destination={'firewall_group_id': fwg3.uuid},
            protocol='icmp')
        fwp3.update(rules=[{'uuid': icmp_fwr.uuid}])
        self.addCleanup(fwp3.remove_firewall_rules, [{'uuid': icmp_fwr.uuid}])
        assert self.vms['eng_web'].ping_with_certainty(self.vms['eng_logic'].vm_ip, count=2)
        assert icmp_fwr.get_object()['enabled'] == True
        icmp_fwr.update(enabled=False)
        assert icmp_fwr.get_object()['enabled'] == False
        assert self.vms['eng_web'].ping_with_certainty(self.vms['eng_logic'].vm_ip,
            count=2, expectation=False), "Possibly due to CEM-8725"

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
        # SG
        default_sg = self.get_default_sg()
        cidr = self.vms['hr_web'].get_vm_ips()[0]+'/32'
        sg_rule = self._get_secgrp_rule(protocol='tcp', dst_ports=(8003, 8007),
                                        cidr=cidr, direction='ingress')
        sg1 = self.create_security_group(rules=[sg_rule])
        self.vms['eng_db'].remove_security_group(default_sg.uuid)
        self.vms['eng_db'].add_security_group(sg1.uuid)
        self.addCleanup(self.vms['eng_db'].remove_security_group, sg1.uuid)

        #Network Policy
        hr_vn = self.vns['hr'].vn_fq_name
        eng_vn = self.vns['eng'].vn_fq_name
        nwp_rule1 = self._get_network_policy_rule(protocol='tcp',
            src_vn=hr_vn, dst_vn=eng_vn, dst_ports=(8000, 8005), action='pass')
        nwp = self.create_policy(rules=[nwp_rule1])
        self.apply_policy(nwp, [self.vns['hr'], self.vns['eng']])

        #Contrail Security
        any_ep = {'any': True}
        app_tag = self.create_tag('application', 'app', 'global')
        self.set_tag(self.vns['hr'], app_tag)
        self.set_tag(self.vns['eng'], app_tag)
        cs_fwr = self.create_fw_rule(scope='global', protocol='tcp',
            dports=(8003, 8004), source=any_ep, destination=any_ep,
            api_type='contrail', match='None')
        rules = [{'uuid': cs_fwr.uuid, 'seq_no': 10}]
        cs_fwp = self.create_fw_policy(scope='global', rules=rules,
            api_type='contrail')
        policies = [{'uuid': cs_fwp.uuid, 'seq_no': 10}]
        cs_aps = self.create_aps('global', policies=policies,
            application=app_tag)

        #FwaaSv2
        tcp_fwr = self.create_fw_rule(
            source={'subnet': self.vns['hr'].get_cidrs()[0]},
            destination={'subnet': self.vns['eng'].get_cidrs()[0]},
            protocol='tcp', dports=('8004', '8008'))
        fwp = self.create_fw_policy(rules=[{'uuid': tcp_fwr.uuid}])
        fwg = self.create_fw_group(vm_fixtures=list(self.vms.values()),
                                   ingress_policy=fwp, egress_policy=fwp)

        self.verify_traffic(self.vms['eng_web'], self.vms['eng_db'], 'tcp',
             dport=8004, expectation=False)
        # TCP port 8004 allowed by all
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             dport=8004)
        # port 8005 denied by contrail-security
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             dport=8005, expectation=False)
        # port 8003 denied by fwaasv2
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             dport=8003, expectation=False)
        # Delete Contrail security
        self.perform_cleanup(cs_aps)
        # TCP port 8004 allowed by all
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             dport=8004)
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             dport=8005)
        # port 8003 denied by fwaasv2
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             dport=8003, expectation=False)
        # port 8006 denied by nwp
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             dport=8006, expectation=False)
        # Delete Network policy
        self.perform_cleanup(self.vns['hr'].unbind_policies,
            policy_fq_names=[nwp.policy_fq_name])
        self.perform_cleanup(self.vns['eng'].unbind_policies,
            policy_fq_names=[nwp.policy_fq_name])
        self.perform_cleanup(nwp)
        # Add allow all network policy for leaking routes
        self.setup_policy_between_vns(self.vns['hr'], self.vns['eng'])
        # TCP port 8004 allowed by all
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             dport=8004)
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             dport=8006)
        # port 8003 denied by fwaasv2
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             dport=8003, expectation=False)
        # port 8008 denied by SG
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             dport=8008, expectation=False)
        # Delete Security group
        self.perform_cleanup(self.vms['eng_db'].remove_security_group, sg1.uuid)
        self.vms['eng_db'].add_security_group(default_sg.uuid)
        # TCP port 8004 allowed by all
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             dport=8004)
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             dport=8008)
        # port 8003 denied by fwaasv2
        self.verify_traffic(self.vms['hr_web'], self.vms['eng_db'], 'tcp',
             dport=8003, expectation=False)
        self.verify_traffic(self.vms['eng_web'], self.vms['eng_db'], 'tcp',
             dport=8006, expectation=False)

    @preposttest_wrapper
    def test_fwaas_objects_quota(self):
        quota_dict = {
            'firewall_group': 5,
            'firewall_policy': 5,
            'firewall_rule': 5,
            }
        quota_rsp = self.connections.quantum_h.update_quota(
            self.connections.project_id,
            quota_dict)
        quota_show_dict = self.connections.quantum_h.show_quota(
            self.connections.project_id)
        admin_quota_dict = self.admin_connections.quantum_h.show_quota(
            self.admin_connections.project_id)
        for obj, limit in quota_dict.iteritems():
            assert limit == quota_show_dict['quota'][obj], 'Failed to update quota for %s'%obj
            assert limit != admin_quota_dict['quota'][obj], \
                'Update on Project1 quota shouldnt be reflected on other projects'
            if obj == 'firewall_rule':
                count = limit - 2
            elif obj == 'firewall_policy':
                count = limit - 1
            elif obj == 'firewall_group':
                count = limit - 1
            for index in range(count):
                if obj == 'firewall_rule':
                    self.create_fw_rule(protocol='tcp', dports=(str(8000+index), ))
                elif obj == 'firewall_policy':
                    self.create_fw_policy()
                elif obj == 'firewall_group':
                    fwg = self.create_fw_group()
            else:
                if obj == 'firewall_rule':
                    try:
                        self.create_fw_rule(protocol='tcp', dports=(str(8000+index), ))
                        assert False, 'Firewall rule creation should have failed'
                    except:
                        pass
                elif obj == 'firewall_policy':
                    try:
                        self.create_fw_policy()
                        assert False, 'Firewall policy creation should have failed'
                    except:
                        pass
                elif obj == 'firewall_group':
                    try:
                        fwg = self.create_fw_group()
                        assert False, 'Firewall group creation should have failed'
                    except:
                        pass
