from common.neutron.base import BaseNeutronTest
from tcutils.util import get_random_name
from vn_test import VNFixture
from vm_test import VMFixture
from project_test import ProjectFixture
from port_fixture import PortFixture
from firewall_rule import FirewallRuleFixture
from firewall_policy import FirewallPolicyFixture
from application_policy_set import ApplicationPolicySetFixture
from address_group import AddressGroupFixture
from service_group import ServiceGroupFixture
from tcutils.traffic_utils.base_traffic import BaseTraffic, SCAPY
from collections import defaultdict
import random

class BaseFirewallTest(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        cls.tags = dict(); cls.vns = dict(); cls.vms = dict()
        cls.sec_groups = dict(); cls.policys = dict()
        super(BaseFirewallTest, cls).setUpClass()
        cls.project_name = cls.inputs.project_name
        cls.domain_name = cls.inputs.domain_name
        cls.vnc_h = cls.connections.orch.vnc_h
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
        connections = kwargs.get('connections') or cls.connections
        project_name = connections.project_name
        domain_name = connections.domain_name
        name = get_random_name(project_name)
        if scope == 'local':
            parent_type = 'project'; fqname = [domain_name, project_name]
        else:
            parent_type = None; fqname = []
        fqname.append(name)
        vnc_h = connections.orch.vnc_h
        uuid = vnc_h.create_tag(fqname, tag_type, tag_value, parent_type)
        return vnc_h.read_tag(id=uuid)

    def create_tag(self, *args, **kwargs):
        connections = kwargs.get('connections') or self.connections
        obj = self.create_only_tag(*args, **kwargs)
        if kwargs.pop('cleanup', True):
            self.addCleanup(self.delete_tag, obj.uuid, connections=connections)
        return obj

    def delete_tag(self, uuid, **kwargs):
        connections = kwargs.get('connections') or self.connections
        vnc_h = connections.orch.vnc_h
        return vnc_h.delete_tag(id=uuid)

    def _get_port(self, uuid, **kwargs):
        connections = kwargs.get('connections') or self.connections
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
        return (obj, object_type, uuid)

    def add_labels(self, fixture, labels, **kwargs):
        connections = kwargs.get('connections') or self.connections
        vnc_h = connections.orch.vnc_h
        obj, object_type, uuid = self._get_obj_from_fixture(fixture)
        is_global = False if getattr(labels[0], 'parent_type', None) == 'project' else True
        tags = [label.tag_value for label in labels]
        vnc_h.add_labels(tags, is_global, obj, object_type, uuid)
        self.addCleanup(self.delete_labels, fixture, labels, **kwargs)

    def delete_labels(self, fixture, labels, **kwargs):
        connections = kwargs.get('connections') or self.connections
        vnc_h = connections.orch.vnc_h
        obj, object_type, uuid = self._get_obj_from_fixture(fixture)
        is_global = False if getattr(labels[0], 'parent_type', None) == 'project' else True
        labels = [label.tag_value for label in labels]
        vnc_h.delete_labels(labels, is_global, obj, object_type, uuid)

    def set_tag(self, fixture, tag, **kwargs):
        connections = kwargs.get('connections') or self.connections
        vnc_h = connections.orch.vnc_h
        obj, object_type, uuid = self._get_obj_from_fixture(fixture)
        is_global = False if getattr(tag, 'parent_type', None) == 'project' else True
        vnc_h.set_tag(tag.tag_type_name, tag.tag_value, is_global,
                      obj, object_type, uuid)
        self.addCleanup(self.unset_tag, fixture, tag, **kwargs)

    def unset_tag(self, fixture, tag, **kwargs):
        connections = kwargs.get('connections') or self.connections
        vnc_h = connections.orch.vnc_h
        obj, object_type, uuid = self._get_obj_from_fixture(fixture)
        vnc_h.unset_tag(tag.tag_type_name, obj, object_type, uuid)

    def create_fw_policy(self, scope, rules=None, **kwargs):
        connections = kwargs.get('connections') or self.connections
        return self.useFixture(FirewallPolicyFixture(scope=scope,
               rules=rules, connections=connections))

    def add_fw_rule(self, fwp_fixture, rule_uuid, seq_no):
        return fwp_fixture.add_firewall_rules([{'uuid': rule_uuid,
                                               'seq_no': seq_no}])

    def remove_fw_rule(self, fwp_fixture, rule_uuid):
        return fwp_fixture.remove_firewall_rule(rule_uuid)

    def create_fw_rule(self, scope, **kwargs):
        connections = kwargs.get('connections') or self.connections
        return self.useFixture(FirewallRuleFixture(scope=scope,
               connections=connections, **kwargs))

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
        connections = kwargs.get('connections') or self.connections
        return self.useFixture(ServiceGroupFixture(scope=scope,
               services=services, connections=connections))

    def create_address_group(self, scope='local', vn_fixtures=None,
                  subnets=None, labels=None, **kwargs):
        connections = kwargs.get('connections') or self.connections
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
        msg = "transferred between %s and %s, proto %s sport %s and dport %s"%(
               traffic_obj.src_ip, traffic_obj.dst_ip, traffic_obj.proto,
               traffic_obj.sport, traffic_obj.dport)
        if not expectation:
            assert sent or traffic_obj.proto == 'tcp', "Packets not %s"%msg
            assert not recv, "Packets %s"%msg
        else:
            assert sent and recv, "Packets not %s"%msg
            if recv*100/float(sent) < 90:
                assert False, "Packets not %s"%msg
        return True

    def verify_traffic(self, src_vm_fixture, dst_vm_fixture, proto, sport=0,
                       dport=0, src_vn_fqname=None, dst_vn_fqname=None,
                       af=None, fip_ip=None, expectation=True):
        traffic_obj = self.start_traffic(src_vm_fixture, dst_vm_fixture, proto,
                                  sport, dport, src_vn_fqname=src_vn_fqname,
                                  dst_vn_fqname=dst_vn_fqname, af=af,
                                  fip_ip=fip_ip)
        #self.sleep(10)
        return self.stop_traffic(traffic_obj, expectation)

    def _verify_traffic(self, vm1, vm2, vm3, exp=True, dport=None):
        dport = dport or random.randint(8000, 8010)
        #Validate tcp 8000 web to logic
        self.verify_traffic(vm1, vm2, 'tcp', sport=1111, dport=dport, expectation=exp)
        #Validate udp and other tcp ports are blocked
        if exp:
            self.verify_traffic(vm1, vm2, 'udp', sport=1111, dport=dport, expectation=not exp)
            self.verify_traffic(vm1, vm2, 'tcp', sport=dport, dport=1111, expectation=not exp)
        #Validate udp 8000 web to logic
        self.verify_traffic(vm2, vm3, 'udp', sport=1111, dport=dport, expectation=exp)
        #Validate tcp and other udp ports are blocked
        if exp:
            self.verify_traffic(vm2, vm3, 'tcp', sport=1111, dport=dport, expectation=not exp)
            self.verify_traffic(vm2, vm3, 'udp', sport=dport, dport=1111, expectation=not exp)
            self._verify_ping(vm1, vm2, vm3, exp=exp)

    def _verify_ping(self, vm1, vm2, vm3=None, af=None, exp=True):
        assert vm1.ping_to_vn(vm2, af=af, expectation=exp)
        if vm3:
            assert vm1.ping_to_vn(vm3, af=af, expectation=exp)
            assert vm2.ping_to_vn(vm3, af=af, expectation=exp)
