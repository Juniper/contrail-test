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
from tcutils.traffic_utils.base_traffic import BaseTraffic, SCAPY
from collections import defaultdict
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
            for obj in cls.vms.itervalues():
                obj.cleanUp()
        if getattr(cls, 'vns', None):
            for obj in cls.vns.itervalues():
                obj.cleanUp()
        for scopes in cls.tags.itervalues():
            for tag_types in scopes.itervalues():
                for obj in tag_types.itervalues():
                    cls.vnc_h.delete_tag(id=obj.uuid)

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
        import pdb;pdb.set_trace()
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
        for state, fixtures in fixtures_draft_states.iteritems():
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
        for obj_type, objs in drafts.iteritems():
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
        return self.useFixture(FirewallPolicyFixture(scope=scope,
               rules=rules, connections=connections, api_type=self.api_type,
               **kwargs))

    def add_fw_rule(self, fwp_fixture, rule_uuid, seq_no):
        return fwp_fixture.add_firewall_rules([{'uuid': rule_uuid,
                                               'seq_no': seq_no}])

    def remove_fw_rule(self, fwp_fixture, rule_uuid):
        return fwp_fixture.remove_firewall_rule(rule_uuid)

    def create_fw_rule(self, scope=None, **kwargs):
        connections = kwargs.pop('connections', None) or self.connections
        return self.useFixture(FirewallRuleFixture(scope=scope,
               connections=connections, api_type=self.api_type, **kwargs))

    def _get_vmi_uuid(self, fixture):
        if type(fixture) == VMFixture:
            return fixture.get_vmi_ids().values()[0]
        elif type(fixture) == PortFixture:
            return fixture.uuid

    def get_ip_address(self, fixture):
        if type(fixture) == VMFixture:
            return fixture.get_vm_ips()[0]
        elif type(fixture) == PortFixture:
            return fixture.get_ip_addresses()[0]

    @property
    def default_fwg(self):
        if not getattr(self, '_default_fwg', None):
            self._default_fwg = self.create_fw_group(name='default')
        return self._default_fwg

    def create_fw_group(self, vm_fixtures=None, port_fixtures=None,
                        ingress_policy=None, egress_policy=None, **kwargs):
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
        fixture = self.useFixture(FirewallGroupFixture(connections=self.connections,
                               ingress_policy_id=ingress_policy_id,
                               egress_policy_id=egress_policy_id,
                               ports=ports, **kwargs))
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

    def start_traffic(self, src_vm_fixture, dst_vm_fixture, proto, sport,
                      dport, src_vn_fqname=None, dst_vn_fqname=None,
                      af=None, fip_ip=None):
        traffic_obj = BaseTraffic.factory(tool=SCAPY, proto=proto)
        assert traffic_obj.start(src_vm_fixture, dst_vm_fixture, proto, sport,
                                 dport, sender_vn_fqname=src_vn_fqname,
                                 receiver_vn_fqname=dst_vn_fqname, af=af,
                                 fip=fip_ip)
        return traffic_obj

    def stop_traffic(self, traffic_obj, expectation=True):
        sent, recv = traffic_obj.stop()
        if sent is None:
            return False
        msg = "transferred between %s and %s, proto %s sport %s and dport %s"%(
               traffic_obj.src_ip, traffic_obj.dst_ip, traffic_obj.proto,
               traffic_obj.sport, traffic_obj.dport)
        if not expectation:
            assert sent or traffic_obj.proto == 'tcp', "Packets not %s"%msg
            assert recv < 5, "Packets %s"%msg
        else:
            assert sent and recv, "Packets not %s"%msg
            if recv*100/float(sent) < 90:
                assert False, "Packets not %s"%msg
        return True

    @retry(delay=60, tries=1)
    def verify_traffic(self, src_vm_fixture, dst_vm_fixture, proto, sport=0,
                       dport=0, src_vn_fqname=None, dst_vn_fqname=None,
                       af=None, fip_ip=None, expectation=True):
        traffic_obj = self.start_traffic(src_vm_fixture, dst_vm_fixture, proto,
                                  sport, dport, src_vn_fqname=src_vn_fqname,
                                  dst_vn_fqname=dst_vn_fqname, af=af,
                                  fip_ip=fip_ip)
        self.sleep(5)
        return self.stop_traffic(traffic_obj, expectation)

    def _verify_traffic(self, vm1, vm2, vm3, exp=True, dport=None, sport=1111):
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
            self._verify_ping(vm1, vm2, vm3, exp=exp)

    def _verify_ping(self, vm1, vm2, vm3=None, af=None, exp=True):
        assert vm1.ping_to_vn(vm2, af=af, expectation=exp)
        if vm3:
            assert vm1.ping_to_vn(vm3, af=af, expectation=exp)
            assert vm2.ping_to_vn(vm3, af=af, expectation=exp)

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
        for obj_type, objs in objs_dict.iteritems():
            for obj in objs:
                self.perform_cleanup(obj, remove_cleanup=False)
