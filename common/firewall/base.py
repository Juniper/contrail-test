from builtins import range
from common.neutron.base import BaseNeutronTest
from tcutils.util import get_random_name, retry
from vn_test import VNFixture
from vm_test import VMFixture
from project_test import ProjectFixture
from port_fixture import PortFixture
from firewall_rule import FirewallRuleFixture
from firewall_policy import FirewallPolicyFixture
from firewall_group import FirewallGroupFixture
from application_policy_set import ApplicationPolicySetFixture
from address_group import AddressGroupFixture
from service_group import ServiceGroupFixture
from collections import defaultdict
from collections import OrderedDict as dict
from vnc_api.vnc_api import NoIdError, BadRequest
import random
import copy

class BaseFirewallTest(BaseNeutronTest):
    @classmethod
    def setUpClass(cls):
        cls.tags = dict(); cls.vns = dict(); cls.vms = dict()
        cls.sec_groups = dict(); cls.policys = dict()
        super(BaseFirewallTest, cls).setUpClass()
        cls.project_name = cls.inputs.project_name
        cls.domain_name = cls.inputs.domain_name
        cls.vnc_h = cls.connections.orch.vnc_h
        cls.api_type = 'contrail'
        try:
            cls.create_common_objects()
        except:
            cls.tearDownClass()
            raise
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.cleanup_common_objects()
        super(BaseFirewallTest, cls).tearDownClass()
    # end tearDownClass

    @classmethod
    def create_common_objects(cls):
        ''' Create tags under both global and local scope
            Site: svl, blr
            deployment: prod, dev
            application: hr, eng
            tier: web, logic, db
        '''
        cls.tags['global'] = defaultdict(dict)
        cls.tags['local'] = defaultdict(dict)
        for site in ['svl', 'blr']:
            cls.tags['global']['site'][site] = cls.create_only_tag('site', site, 'global')
            cls.tags['local']['site'][site] = cls.create_only_tag('site', site)
        for deploy in ['prod', 'dev']:
            cls.tags['global']['deployment'][deploy] = \
                cls.create_only_tag('deployment', deploy, 'global')
            cls.tags['local']['deployment'][deploy] = cls.create_only_tag('deployment', deploy)
        for app in ['hr', 'eng']:
            cls.tags['global']['application'][app] = \
                cls.create_only_tag('application', app, 'global')
            cls.tags['local']['application'][app] = cls.create_only_tag('application', app)
        for tier in ['web', 'logic', 'db']:
            cls.tags['global']['tier'][tier] = cls.create_only_tag('tier', tier, 'global')
            cls.tags['local']['tier'][tier] = cls.create_only_tag('tier', tier)

    @classmethod
    def cleanup_common_objects(cls):
        if getattr(cls, 'vms', None):
            for obj in cls.vms.values():
                obj.cleanUp()
        if getattr(cls, 'vns', None):
            for obj in cls.vns.values():
                obj.cleanUp()
        for scopes in cls.tags.values():
            for tag_types in scopes.values():
                for obj in tag_types.values():
                    cls.vnc_h.delete_tag(id=obj.uuid)
        if getattr(cls, 'save_af', None):
            cls.inputs.set_af(cls.save_af)

    @classmethod
    def create_only_tag(cls, tag_type, tag_value, scope='local', **kwargs):
        connections = kwargs.pop('connections', None) or cls.connections
        project_name = connections.project_name
        domain_name = connections.domain_name
        project_fqname = [domain_name, project_name]
        name = get_random_name(project_name)
        if scope == 'local':
            parent_type = 'project'; fqname = list(project_fqname)
        else:
            parent_type = None; fqname = []
        fqname.append(name)
        vnc_h = connections.orch.vnc_h
        uuid = vnc_h.check_and_create_tag(fqname, tag_type, tag_value, parent_type)
        cls.logger.info('Created Tag %s - %s %s=%s'%(uuid, project_fqname
             if scope == 'local' else 'global', tag_type, tag_value))
        return vnc_h.read_tag(id=uuid)

    def create_tag(self, *args, **kwargs):
        connections = kwargs.pop('connections', None) or self.connections
        obj = self.create_only_tag(*args, **kwargs)
        if kwargs.pop('cleanup', True):
            self.addCleanup(self.delete_tag, obj.uuid, connections=connections)
        return obj

    def delete_tag(self, uuid, **kwargs):
        connections = kwargs.pop('connections', None) or self.connections
        vnc_h = connections.orch.vnc_h
        self.logger.info('Deleting Tag %s'%(uuid))
        return vnc_h.delete_tag(id=uuid)

    def enable_security_draft_mode(self, SCOPE1=None, SCOPE2=None,
                                   project_fqname=None, **kwargs):
        connections = kwargs.pop('connections', None) or self.connections
        vnc_h = connections.orch.vnc_h
        if SCOPE1 == 'global':
            project_fqname = None
        elif SCOPE1 == 'local':
            project_fqname = self.project.project_fq_name
            if SCOPE2 == 'global':
                self.logger.info('Enable security draft mode on global')
                vnc_h.enable_security_draft_mode()
        self.logger.info('Enable security draft mode on %s'%(
            project_fqname if project_fqname else 'global'))
        vnc_h.enable_security_draft_mode(project_fqname)

    def disable_security_draft_mode(self, SCOPE1=None, SCOPE2=None,
                                    project_fqname=None, **kwargs):
        connections = kwargs.pop('connections', None) or self.connections
        retry = kwargs.get('retry', 1)
        vnc_h = connections.orch.vnc_h
        while retry:
            try:
                if SCOPE1 == 'global':
                    project_fqname = None
                elif SCOPE1 == 'local':
                    project_fqname = self.project.project_fq_name
                    if SCOPE2 == 'global':
                        self.logger.info('Disable security draft mode on global')
                        vnc_h.disable_security_draft_mode()
                self.logger.info('Disable security draft mode on %s'%(
                    project_fqname if project_fqname else 'global'))
                vnc_h.disable_security_draft_mode(project_fqname)
                break
            except BadRequest as e:
                retry = retry - 1
                if not retry:
                    raise
                self.sleep(5)

    def discard(self, SCOPE1=None, SCOPE2=None, project_fqname=None, **kwargs):
        connections = kwargs.pop('connections', None) or self.connections
        vnc_h = connections.orch.vnc_h
        if SCOPE1 == 'global':
            project_fqname = None
        elif SCOPE1 == 'local':
            project_fqname = self.project.project_fq_name
        self.logger.info('discard security drafts on %s'%(
            project_fqname if project_fqname else 'global'))
        vnc_h.discard_security_draft(project_fqname)
        if SCOPE1 == 'local' and SCOPE2 == 'global':
            self.logger.info('discard security drafts on global')
            self.sleep(kwargs.get('interval') or 2)
            vnc_h.discard_security_draft()

    def commit(self, SCOPE1=None, SCOPE2=None, project_fqname=None, **kwargs):
        connections = kwargs.pop('connections', None) or self.connections
        vnc_h = connections.orch.vnc_h
        if SCOPE1 == 'global':
            project_fqname = None
        elif SCOPE1 == 'local':
            project_fqname = self.project.project_fq_name
        self.logger.info('commit security drafts on %s'%(
            project_fqname if project_fqname else 'global'))
        vnc_h.commit_security_draft(project_fqname)
        if SCOPE1 == 'local' and SCOPE2 == 'global':
            self.logger.info('commit security drafts on global')
            self.sleep(kwargs.get('interval') or 2)
            vnc_h.commit_security_draft()

    def list_security_drafts(self, SCOPE1=None, SCOPE2=None, project_fqname=None, **kwargs):
        drafts = defaultdict(list)
        connections = kwargs.pop('connections', None) or self.connections
        vnc_h = connections.orch.vnc_h
        objs = list()
        if SCOPE1 == 'global':
            project_fqname = None
        elif SCOPE1 == 'local':
            project_fqname = self.project.project_fq_name
            if SCOPE2 == 'global':
                try:
                    objs.append(vnc_h.list_security_drafts())
                except NoIdError:
                    pass
        try:
            objs.append(vnc_h.list_security_drafts(project_fqname))
        except NoIdError:
            pass
        for obj in objs:
            for ag in obj.get_address_groups() or []:
                drafts['address-group'].append(ag['to'])
            for sg in obj.get_service_groups() or []:
                drafts['service-group'].append(sg['to'])
            for fwr in obj.get_firewall_rules() or []:
                drafts['firewall-rule'].append(fwr['to'])
            for fwp in obj.get_firewall_policys() or []:
                drafts['firewall-policy'].append(fwp['to'])
            for aps in obj.get_application_policy_sets() or []:
                drafts['application-policy-set'].append(aps['to'])
        return drafts

    def validate_draft(self, fixtures_draft_states, SCOPE1=None,
                       SCOPE2=None, project_fqname=None, **kwargs):
        self.logger.info('Validating drafts on SCOPE1: %s, SCOPE2: %s,'
                         ' project: %s'%(SCOPE1, SCOPE2, project_fqname))
        drafts = self.list_security_drafts(SCOPE1, SCOPE2,
                                           project_fqname, **kwargs)
        copy_of_drafts = copy.deepcopy(drafts)
        if (drafts and not fixtures_draft_states) or \
           (fixtures_draft_states and not drafts):
            assert False, "exp %s and got %s"%(fixtures_draft_states, drafts)
        # Compare fqname against states created, updated, deleted
        for state, fixtures in fixtures_draft_states.items():
            for fixture in fixtures:
                fqname = list(fixture.fq_name)
                if len(fqname) == 2:
                    fqname[0] = 'draft-policy-management'
                else:
                    fqname.insert(-1, 'draft-policy-management')
                d1, obj_type, d3 = self._get_obj_from_fixture(fixture)
                assert fqname in drafts[obj_type]
                draft_obj = fixture.get_draft()
                assert draft_obj.draft_mode_state == state
                drafts[obj_type].remove(fqname)
        for obj_type, objs in drafts.items():
            assert not objs, "Unexpected drafts %s"%drafts
        self.logger.debug('Validated drafts %s'%copy_of_drafts)

    def _get_port(self, uuid, **kwargs):
        connections = kwargs.pop('connections', None) or self.connections
        return self.useFixture(PortFixture(uuid=uuid, connections=connections))

    def _get_obj_from_fixture(self, fixture):
        obj = None; object_type = None; uuid = None
        if type(fixture) == VNFixture:
            obj = fixture.api_vn_obj
        elif type(fixture) == VMFixture:
            uuid = fixture.vm_id
            object_type = 'virtual-machine'
        elif type(fixture) == ProjectFixture:
            obj = fixture.project_obj
        elif type(fixture) == PortFixture:
            obj = fixture.vmi_obj
        elif type(fixture) == AddressGroupFixture:
            uuid = fixture.uuid
            object_type = 'address-group'
        elif type(fixture) == ServiceGroupFixture:
            uuid = fixture.uuid
            object_type = 'service-group'
        elif type(fixture) == ApplicationPolicySetFixture:
            uuid = fixture.uuid
            object_type = 'application-policy-set'
        elif type(fixture) == FirewallPolicyFixture:
            uuid = fixture.uuid
            object_type = 'firewall-policy'
        elif type(fixture) == FirewallRuleFixture:
            uuid = fixture.uuid
            object_type = 'firewall-rule'
        return (obj, object_type, uuid)

    def add_labels(self, fixture, labels, **kwargs):
        connections = kwargs.pop('connections', None) or self.connections
        vnc_h = connections.orch.vnc_h
        obj, object_type, uuid = self._get_obj_from_fixture(fixture)
        is_global = False if getattr(labels[0], 'parent_type', None) == 'project' else True
        tags = [label.tag_value for label in labels]
        vnc_h.add_labels(tags, is_global, obj, object_type, uuid)
        self.logger.info('Add %s labels %s to %s'%('global' if is_global
                         else '', tags, obj.uuid if obj else uuid))
        self.addCleanup(self.delete_labels, fixture, labels, **kwargs)

    def delete_labels(self, fixture, labels, **kwargs):
        connections = kwargs.pop('connections', None) or self.connections
        vnc_h = connections.orch.vnc_h
        obj, object_type, uuid = self._get_obj_from_fixture(fixture)
        is_global = False if getattr(labels[0], 'parent_type', None) == 'project' else True
        labels = [label.tag_value for label in labels]
        self.logger.info('Delete %s labels %s to %s'%('global' if is_global
                         else '', labels, obj.uuid if obj else uuid))
        vnc_h.delete_labels(labels, is_global, obj, object_type, uuid)

    def set_tag(self, fixture, tag, **kwargs):
        connections = kwargs.pop('connections', None) or self.connections
        vnc_h = connections.orch.vnc_h
        obj, object_type, uuid = self._get_obj_from_fixture(fixture)
        is_global = False if getattr(tag, 'parent_type', None) == 'project' else True
        vnc_h.set_tag(tag.tag_type_name, tag.tag_value, is_global,
                      obj, object_type, uuid)
        self.logger.info('Set %s tag %s=%s to %s'%('global' if is_global
                         else '', tag.tag_type_name, tag.tag_value,
                         obj.uuid if obj else uuid))
        self.addCleanup(self.unset_tag, fixture, tag, **kwargs)

    def unset_tag(self, fixture, tag, **kwargs):
        connections = kwargs.pop('connections', None) or self.connections
        vnc_h = connections.orch.vnc_h
        obj, object_type, uuid = self._get_obj_from_fixture(fixture)
        vnc_h.unset_tag(tag.tag_type_name, obj, object_type, uuid)
        self.logger.info('Unset tag type %s from %s'%(tag.tag_type_name,
                         obj.uuid if obj else uuid))

    def create_fw_policy(self, scope=None, rules=None, **kwargs):
        connections = kwargs.pop('connections', None) or self.connections
        api_type = kwargs.pop('api_type', self.api_type)
        return self.useFixture(FirewallPolicyFixture(scope=scope,
               rules=rules, connections=connections, api_type=api_type,
               **kwargs))

    def add_fw_rule(self, fwp_fixture, rule_uuid, seq_no):
        return fwp_fixture.add_firewall_rules([{'uuid': rule_uuid,
                                               'seq_no': seq_no}])

    def remove_fw_rule(self, fwp_fixture, rule_uuid):
        return fwp_fixture.remove_firewall_rule(rule_uuid)

    def create_fw_rule(self, scope=None, **kwargs):
        connections = kwargs.pop('connections', None) or self.connections
        api_type = kwargs.pop('api_type', self.api_type)
        return self.useFixture(FirewallRuleFixture(scope=scope,
               connections=connections, api_type=api_type, **kwargs))

    def _get_vmi_uuid(self, fixture):
        if type(fixture) == VMFixture:
            return list(fixture.get_vmi_ids().values())[0]
        elif type(fixture) == PortFixture:
            return fixture.uuid

    def get_ip_address(self, fixture):
        if type(fixture) == VMFixture:
            return fixture.vm_ip
        elif type(fixture) == PortFixture:
            return fixture.get_ip_addresses()[0]

    @property
    def default_fwg(self):
        if not getattr(self, '_default_fwg', None):
            self._default_fwg = self.create_fw_group(name='default')
        return self._default_fwg

    def create_fw_group(self, vm_fixtures=None, port_fixtures=None,
                        ingress_policy=None, egress_policy=None,
                        verify=True, **kwargs):
        connections = kwargs.pop('connections', None) or self.connections
        ingress_policy_id = ingress_policy.uuid if ingress_policy else None
        egress_policy_id = egress_policy.uuid if egress_policy else None
        ports = [self._get_vmi_uuid(fixture) for fixture in 
                 (vm_fixtures or list()) + (port_fixtures or list())]
        # A port can only be associated to only one FW-Group
        # By default default FWG will have all ports associated
        # so disassociate from default FWG before associating to new FWG
        if ports and kwargs.get('name') != 'default':
            self.default_fwg.delete_ports(ports)
        fixture = self.useFixture(FirewallGroupFixture(connections=connections,
                               ingress_policy_id=ingress_policy_id,
                               egress_policy_id=egress_policy_id,
                               ports=ports, **kwargs))
        if verify:
            fixture.verify_on_setup()
        return fixture

    def create_aps(self, scope='local', policies=None, application=None, **kwargs):
        '''
            :param policies : List of policy uuid and seq no
            eg: [{'policy': uuid, 'seq_no': <int>}]
        '''
        connections = kwargs.pop('connections', None) or self.connections
        obj = self.useFixture(ApplicationPolicySetFixture(scope=scope,
              policies=policies, connections=connections, **kwargs))
        if application:
            obj.add_tag(application)
        return obj

    def create_service_group(self, scope='local', services=None, **kwargs):
        '''
            :param services : List of services tuple
            eg: [(<protocol>, (<sp_start, sp_end>), (<dp_start, dp_end>))]
        '''
        connections = kwargs.pop('connections', None) or self.connections
        return self.useFixture(ServiceGroupFixture(scope=scope,
               services=services, connections=connections))

    def create_address_group(self, scope='local', vn_fixtures=None,
                  subnets=None, labels=None, **kwargs):
        connections = kwargs.pop('connections', None) or self.connections
        subnets = subnets or []
        for vn_fixture in vn_fixtures or []:
            subnets.extend(vn_fixture.get_cidrs())
        obj = self.useFixture(AddressGroupFixture(scope=scope,
               subnets=subnets, connections=connections))
        if labels:
           obj.add_labels(labels)
        return obj

    def _verify_traffic(self, vm1, vm2, vm3, exp=True, dport=None, sport=1111):
        if exp:
            self._verify_ping(vm1, vm2, vm3, exp=exp)
        dport = dport or random.randint(8000, 8010)
        #Validate tcp 8000 web to logic
        self.verify_traffic(vm1, vm2, 'tcp', sport=sport, dport=dport, expectation=exp)
        #Validate udp and other tcp ports are blocked
        if exp:
            self.verify_traffic(vm1, vm2, 'udp', sport=sport, dport=dport, expectation=not exp)
            self.verify_traffic(vm1, vm2, 'tcp', sport=dport, dport=sport, expectation=not exp)
        #Validate udp 8000 web to logic
        self.verify_traffic(vm2, vm3, 'udp', sport=sport, dport=dport, expectation=exp)
        #Validate tcp and other udp ports are blocked
        if exp:
            self.verify_traffic(vm2, vm3, 'tcp', sport=sport, dport=dport, expectation=not exp)
            self.verify_traffic(vm2, vm3, 'udp', sport=dport, dport=sport, expectation=not exp)

    def _verify_ping(self, vm1, vm2, vm3=None, af=None, exp=True):
        assert vm1.ping_with_certainty(dst_vm_fixture=vm2, count=2,
                                       af=af, expectation=exp)
        if vm3:
            assert vm1.ping_with_certainty(dst_vm_fixture=vm3, count=2,
                                           af=af, expectation=exp)
            assert vm2.ping_with_certainty(dst_vm_fixture=vm3, count=2,
                                           af=af, expectation=exp)

    def create_n_security_objects(self, n_fw_rules=20, n_fw_policys=20,
                                  n_sgs=20, n_ags=20, n_aps=20, scope='global',
                                  connections=None):
        objs_dict = defaultdict(list)
        for i in range (n_fw_rules):
            objs_dict['fw_rules'].append(self.create_fw_rule(
                scope, protocol='tcp', connections=connections))
        for i in range (n_fw_policys):
            objs_dict['fw_policys'].append(self.create_fw_policy(
                scope, connections=connections))
        for i in range (n_sgs):
            objs_dict['sgs'].append(self.create_service_group(
                scope, connections=connections))
        for i in range (n_ags):
            objs_dict['ags'].append(self.create_address_group(
                scope, connections=connections))
        for i in range (n_aps):
            objs_dict['aps'].append(self.create_aps(
                scope, connections=connections))
        return objs_dict

    def cleanup_n_security_objects(self, objs_dict, remove_cleanup=False):
        for obj_type, objs in objs_dict.items():
            for obj in objs:
                self.perform_cleanup(obj, remove_cleanup=False)

class FirewallBasic(BaseFirewallTest):
    @classmethod
    def setUpClass(cls):
        super(FirewallBasic, cls).setUpClass()
        try:
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
                cls.vms[vn+'_'+vm] = cls.create_only_vm(vn_fixture=cls.vns[vn],
                                                        image_name='cirros-traffic')
        cls.policys['hr_eng'] = cls.setup_only_policy_between_vns(cls.vns['hr'],
                                                                 cls.vns['eng'])
        assert cls.check_vms_active(iter(cls.vms.values()), do_assert=False)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, 'policys', None) and 'hr_eng' in cls.policys:
            cls.vns['hr'].unbind_policies()
            cls.vns['eng'].unbind_policies()
            cls.policys['hr_eng'].cleanUp()
        super(FirewallBasic, cls).tearDownClass()

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
        for vm, obj in self.vms.items():
            if vm.startswith('eng'):
                self.add_labels(obj, [self.ag_label])

        assert self.check_vms_booted(iter(self.vms.values()), do_assert=False)

class BaseFirewallTest_1(BaseFirewallTest):
    @classmethod
    def setUpClass(cls):
        super(BaseFirewallTest_1, cls).setUpClass()
        try:
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
        kwargs = dict()
        image_name = getattr(cls, 'image_name', 'cirros-traffic')
        if image_name:
            kwargs['image_name'] = image_name
        for vn in ['hr']:
            cls.vns[vn] = cls.create_only_vn()
            for vm in ['web', 'logic', 'db']:
                cls.vms[vn+'_'+vm] = cls.create_only_vm(vn_fixture=cls.vns[vn],
                                     **kwargs)
        assert cls.check_vms_active(iter(cls.vms.values()), do_assert=False)

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
        draft = True if getattr(self, 'draft', None) is True else False

        hr_app_tag = self.tags[SCOPE1]['application']['hr']
        self.set_tag(self.vns['hr'], hr_app_tag)
        self.set_tag(self.vms['hr_web'], self.tags[SCOPE1]['tier']['web'])
        self.set_tag(self.vms['hr_logic'], self.tags[SCOPE1]['tier']['logic'])
        self.set_tag(self.vms['hr_db'], self.tags[SCOPE1]['tier']['db'])
        self.set_tag(self.project, self.tags[SCOPE1]['deployment']['dev'])
        self.set_tag(self.project, self.tags[SCOPE2]['site']['blr'])

        if not getattr(self, 'ag_label', None):
            self.ag_label = self.create_tag('label', 'ag', SCOPE2)
        self.ag = self.create_address_group(SCOPE2, labels=[self.ag_label])
        services = [('tcp', (0,65535), (8000,8010))]
        self.scope1_sg = self.create_service_group(SCOPE1, services)
        services = [('icmp', (0,65535), (0,65535))]
        self.sg_icmp = self.create_service_group(SCOPE2, services)

        if draft:
            fqname = list(self.ag.fq_name)
            if SCOPE2 == 'global':
                fqname[0] = 'draft-policy-management'
            else:
                fqname.insert(-1, 'draft-policy-management')
            logic_ep = {'address_group': ':'.join(fqname)}
        else:
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
        rules = [{'uuid': self.fwr_icmp.uuid, 'seq_no': 20}]
        self.fwp_icmp = self.create_fw_policy(scope=SCOPE2, rules=rules)
        rules = [{'uuid': self.fwr_hr_tcp.uuid, 'seq_no': 30},
                 {'uuid': self.fwr_hr_udp.uuid, 'seq_no': 40}]
        self.fwp_hr = self.create_fw_policy(scope=SCOPE1, rules=rules)
        policies = [{'uuid': self.fwp_hr.uuid, 'seq_no': 20},
                    {'uuid': self.fwp_icmp.uuid, 'seq_no': 30}]
        self.aps_hr = self.create_aps(SCOPE1, policies=policies,
                                      application=hr_app_tag)
        for vm, obj in self.vms.items():
            if vm.startswith('hr'):
                self.add_labels(obj, [self.ag_label])

        assert self.check_vms_booted(iter(self.vms.values()), do_assert=False)


class FirewallDraftBasic(BaseFirewallTest_1):
    draft = True
    def _test_draft_mode(self, SCOPE1, SCOPE2):
        # Revert the created draft objects
        self.enable_security_draft_mode(SCOPE1, SCOPE2)
        self.addCleanup(self.disable_security_draft_mode, SCOPE1, SCOPE2, retry=3)
        self.addCleanup(self.discard, SCOPE1, SCOPE2)
        self._create_objects(SCOPE1, SCOPE2)
        self.addCleanup(self.commit, SCOPE1, SCOPE2)
        fixture_states = {
            'created': [self.ag, self.scope1_sg, self.sg_icmp,
                        self.fwr_icmp, self.fwr_hr_tcp, self.fwr_hr_udp,
                        self.fwp_icmp, self.fwp_hr, self.aps_hr],
            'deleted': [],
            'updated': []
        }
        self.validate_draft(fixture_states, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'udp',
                            sport=1111, dport=8005)
        self.discard(SCOPE1, SCOPE2)
        self.validate_draft({}, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'udp',
                            sport=1111, dport=8005)
        # Disable draft mode
        self._create_objects(SCOPE1, SCOPE2)
        fixture_states = {
            'created': [self.ag, self.scope1_sg, self.sg_icmp,
                        self.fwr_icmp, self.fwr_hr_tcp, self.fwr_hr_udp,
                        self.fwp_icmp, self.fwp_hr, self.aps_hr]
        }
        self.validate_draft(fixture_states, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'udp',
                            sport=1111, dport=8005)
        try:
            self.disable_security_draft_mode(SCOPE1, SCOPE2)
            assert False, "Disable draft mode with drafts should raise exception"
        except:
            pass
        self.validate_draft(fixture_states, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'udp',
                            sport=1111, dport=8005)
        # Commit the created draft objects
        self.commit(SCOPE1, SCOPE2)
        self.validate_draft({}, SCOPE1, SCOPE2)
        self._verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], self.vms['hr_db'])

        # Update security group objects
        # FWPolicy
        rules = [{'uuid': self.fwr_icmp.uuid, 'seq_no': 20}]
        self.fwp_icmp.remove_firewall_rules(rules=rules)
        fixture_states = {'updated': [self.fwp_icmp]}
        self.validate_draft(fixture_states, SCOPE1, SCOPE2)
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'], self.vms['hr_db'])
        self.discard(SCOPE1, SCOPE2)
        self.validate_draft({}, SCOPE1, SCOPE2)
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'], self.vms['hr_db'])
        self.fwp_icmp.remove_firewall_rules(rules=rules)
        self.validate_draft(fixture_states, SCOPE1, SCOPE2)
        self.commit(SCOPE1, SCOPE2)
        self.validate_draft({}, SCOPE1, SCOPE2)
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'],
                          self.vms['hr_db'], exp=False)
        # SG
        self.scope1_sg.delete_services([('tcp', (0,65535), (8000,8010))])
        self.scope1_sg.add_services([('tcp', (0,65535), (8000, 9000))])
        fixture_states = { 'updated': [self.scope1_sg]}
        self.validate_draft(fixture_states, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                            'tcp', sport=1111, dport=8085, expectation=False)
        self.commit(SCOPE1, SCOPE2)
        self.validate_draft({}, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
                            'tcp', sport=1111, dport=8085, expectation=True)
        # FWRule
        logic_ep = {'address_group': self.ag.fq_name_str}
        self.fwr_hr_tcp.update(direction='>', destination=logic_ep)
        fixture_states = { 'updated': [self.fwr_hr_tcp]}
        self.validate_draft(fixture_states, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'tcp',
                            sport=1111, dport=8005)
        self.verify_traffic(self.vms['hr_logic'], self.vms['hr_web'], 'tcp',
                            sport=1111, dport=8005, expectation=True)
        self.commit(SCOPE1, SCOPE2)
        self.validate_draft({}, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'tcp',
                            sport=1111, dport=8005)
        self.verify_traffic(self.vms['hr_logic'], self.vms['hr_web'], 'tcp',
                            sport=1111, dport=8005, expectation=False)
        #AG
        self.delete_labels(self.ag, [self.ag_label])
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'tcp',
                            sport=1111, dport=8005, expectation=False)
        self.ag.add_subnets(self.vns['hr'].get_cidrs())
        fixture_states = { 'updated': [self.ag]}
        self.validate_draft(fixture_states, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'tcp',
                            sport=1111, dport=8005, expectation=False)
        self.commit(SCOPE1, SCOPE2)
        self.validate_draft({}, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'tcp',
                            sport=1111, dport=8005)
        #APS
        policies = [{'uuid': self.fwp_hr.uuid, 'seq_no': 20},
                    {'uuid': self.fwp_icmp.uuid, 'seq_no': 30}]
        self.aps_hr.delete_policies(policies)
        fixture_states = { 'updated': [self.aps_hr]}
        self.validate_draft(fixture_states, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_db'], 'tcp',
                            sport=1111, dport=7005, expectation=False)
        self.commit(SCOPE1, SCOPE2)
        self.validate_draft({}, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_db'], 'tcp',
                            sport=1111, dport=7005, expectation=True)

        self.aps_hr.add_policies(policies)
        rules = [{'uuid': self.fwr_icmp.uuid, 'seq_no': 20}]
        self.fwp_icmp.add_firewall_rules(rules=rules)
        self.commit(SCOPE1, SCOPE2)
        # Delete security objects
        # SG
        self.fwr_icmp.update(protocol='udp', dports=(8085, 8085), service_groups=list())
        self.perform_cleanup(self.sg_icmp)
        fixture_states = { 'deleted': [self.sg_icmp], 'updated': [self.fwr_icmp]}
        self.validate_draft(fixture_states, SCOPE1, SCOPE2)
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'],
                          self.vms['hr_db'])
        self.discard(SCOPE1, SCOPE2)
        self.validate_draft({}, SCOPE1, SCOPE2)
        self.fwr_icmp.update(protocol='udp', dports=(8085, 8085), service_groups=list())
        self.perform_cleanup(self.sg_icmp)
        self.commit(SCOPE1, SCOPE2)
        self.validate_draft({}, SCOPE1, SCOPE2)
        self._verify_ping(self.vms['hr_web'], self.vms['hr_logic'],
                          self.vms['hr_db'], exp=False)
        # FWRule
        rules = [{'uuid': self.fwr_hr_udp.uuid, 'seq_no': 40}]
        self.fwp_hr.remove_firewall_rules(rules=rules)
        self.perform_cleanup(self.fwr_hr_udp)
        fixture_states = { 'deleted': [self.fwr_hr_udp],
                           'updated': [self.fwp_hr]}
        self.validate_draft(fixture_states, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_logic'], self.vms['hr_db'],
            'udp', sport=1111, dport=8005, expectation=True)
        self.commit(SCOPE1, SCOPE2)
        self.validate_draft({}, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_logic'], self.vms['hr_db'],
            'udp', sport=1111, dport=8005, expectation=False)
        # FWPolicy
        policies = [{'uuid': self.fwp_icmp.uuid, 'seq_no': 30}]
        self.aps_hr.delete_policies(policies)
        self.perform_cleanup(self.fwp_icmp)
        fixture_states = { 'deleted': [self.fwp_icmp],
                           'updated': [self.aps_hr]}
        self.validate_draft(fixture_states, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
            'udp', sport=1111, dport=8085, expectation=True)
        self.commit(SCOPE1, SCOPE2)
        self.validate_draft({}, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
            'udp', sport=1111, dport=8085, expectation=False)
        # AG
        rules = [{'uuid': self.fwr_hr_tcp.uuid, 'seq_no': 30}]
        self.fwp_hr.remove_firewall_rules(rules=rules)
        self.perform_cleanup(self.fwr_hr_tcp)
        self.perform_cleanup(self.ag)
        fixture_states = { 'deleted': [self.fwr_hr_tcp, self.ag],
                           'updated': [self.fwp_hr]}
        self.validate_draft(fixture_states, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
            'tcp', sport=1111, dport=8005, expectation=True)
        self.commit(SCOPE1, SCOPE2)
        self.validate_draft({}, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
            'tcp', sport=1111, dport=8005, expectation=False)
        # APS
        self.perform_cleanup(self.aps_hr)
        fixture_states = { 'deleted': [self.aps_hr]}
        self.validate_draft(fixture_states, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'],
            'tcp', sport=1111, dport=8005, expectation=False)
        self.commit(SCOPE1, SCOPE2)
        self.validate_draft({}, SCOPE1, SCOPE2)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'tcp',
                            sport=1111, dport=8005)
        self.verify_traffic(self.vms['hr_web'], self.vms['hr_logic'], 'udp',
                            sport=1111, dport=8005)

