from common.k8s.base import BaseK8sTest

from k8s.network_policy import NetworkPolicyFixture
from tcutils.wrappers import preposttest_wrapper
from test import BaseTestCase

from k8s.namespace import NamespaceFixture
from k8s.pod import PodFixture
from tcutils.util import get_random_name, get_random_cidr
import time
import test
from tcutils.util import skip_because, Singleton
import gevent
from gevent import greenlet
from firewall_rule import FirewallRuleFixture
from application_policy_set import ApplicationPolicySetFixture
from firewall_policy import FirewallPolicyFixture
from common.isolated_creds import IsolatedCreds
from policy_test import PolicyFixture
from common.policy.config import AttachPolicyFixture
from vnc_api.vnc_api import *
from k8s.namespace import NamespaceFixture
from k8s.hbs import HbsFixture


class TestHbsTraffic(BaseK8sTest):
    @classmethod
    def setUpClass(cls):
        super(TestHbsTraffic, cls).setUpClass()
        cls.namespace = NamespaceFixture(cls._connections,isolation = True)
        cls.namespace.setUp()
        cls.namespace.verify_on_setup()
        namespace = cls.namespace.name
        cls.hbs = HbsFixture(cls._connections, name="hbs",namespace = namespace)
        assert cls._connections.k8s_client.set_label_for_hbf_nodes( \
            node_selector='computenode'), "Error : could not label the nodes"
        cls.hbs.setUp()
        cls.hbs.verify_on_setup()

    def setupProjectNetworksAndPolicies(self):
        self.project_name = "k8s-" + self.namespace.name
        self.namespace_name = self.namespace.name
        isolated_creds = IsolatedCreds(self.inputs, self.project_name,
                                       input_file=self.input_file,
                                       logger=self.logger)
        self.remove_from_cleanups(isolated_creds.cleanUp)
        self.proj_fix = self.create_project(self.project_name, cleanup=False,
                                            connections=self.connections)
        self.proj_inputs = isolated_creds.get_inputs(self.proj_fix)
        self.proj_connection = isolated_creds.get_connections(self.proj_inputs)

        self.vn1 = self.setup_vn(project_name=self.project_name,
                                 connections=self.proj_connection, inputs=self.proj_inputs, vn_name="vn1")
        self.logger.info(self.vn1.domain_name)
        self.logger.info(self.vn1.project_name)
        self.vn1_dict = {"domain": self.vn1.domain_name,
                         "project": self.vn1.project_name,
                         "name": self.vn1.vn_name}
        self.vn2 = self.setup_vn(project_name=self.project_name,
                                 connections=self.proj_connection, inputs=self.proj_inputs, vn_name="vn2")
        self.logger.info(self.vn2.domain_name)
        self.logger.info(self.vn2.project_name)
        self.vn2_dict = {"domain": self.vn2.domain_name,
                         "project": self.vn2.project_name,
                         "name": self.vn2.vn_name}

        # Define policy
        r1 = [{'direction': '<>', 'simple_action': 'pass', 'protocol': 'any',
               'src_ports': 'any', 'dst_ports': 'any',
               'source_network': "vn1", 'dest_network': "vn2", }]
        # Create Policy
        self.nw_policy_fix = self.useFixture(PolicyFixture(policy_name="p1",
                                             rules_list=r1,
                                             inputs=self.proj_inputs,
                                             connections=self.proj_connection))
        self.attach_v1_fix = self.useFixture(AttachPolicyFixture(
                                 self.proj_inputs, self.proj_connection,
                                 self.vn1, self.nw_policy_fix))
        self.attach_v2_fix = self.useFixture(AttachPolicyFixture(
                                 self.proj_inputs, self.proj_connection,
                                 self.vn2, self.nw_policy_fix))

    def setupTagsAndFWRules(self):
        # Create Tags
        webtag_fqdn = ['default-domain', self.project_name, 'tier=webtier']
        webtier_tag = self.create_tag(fq_name=webtag_fqdn, tag_type='tier',
                                      tag_value='webtier',
                                      parent_type='project')
        self.addCleanup(self.vnc_h.delete_tag, id=webtier_tag)

        apptag_fqdn = ['default-domain', self.project_name, 'tier=apptier']
        apptier_tag = self.create_tag(fq_name=apptag_fqdn, tag_type='tier',
                                      tag_value='apptier',
                                      parent_type='project')
        self.addCleanup(self.vnc_h.delete_tag, id=apptier_tag)

        self.app_tag_name = 'myk8s'
        app_fqdn = ['default-domain', self.project_name, 'application=%s'\
                    % (self.app_tag_name)]
        app_tag = self.create_tag(fq_name=app_fqdn, tag_type='application',
                                  tag_value=self.app_tag_name,
                                  parent_type='project')
        self.addCleanup(self.vnc_h.delete_tag, id=app_tag)

        # Associate tags with VM interfaces
        id_val = self.apod1.vmi_objs[0].uuid
        obj_val = self.read_virtual_machine_interface(id=id_val)
        self.set_tag(tag_type="tier", tag_value="webtier", obj=obj_val)
        self.set_tag(tag_type='application', tag_value=self.app_tag_name,
                     obj=obj_val)

        id_val = self.apod2.vmi_objs[0].uuid
        obj_val = self.read_virtual_machine_interface(id=id_val)
        self.set_tag(tag_type="tier", tag_value="apptier", obj=obj_val)
        self.set_tag(tag_type='application', tag_value=self.app_tag_name,
                     obj=obj_val)

        # Create FW rule
        self.endpoint1 = {'tags': ['tier=webtier']}
        self.endpoint2 = {'tags': ['tier=apptier']}

        self.fw1_fqname = ['default-domain', self.project_name, 'hbs_fw']
        self.fw1_uuid = self.vnc_h.create_firewall_rule(
                            fq_name=self.fw1_fqname, parent_type='project',
                            service_groups=[], protocol='any',
                            source=self.endpoint1, action='pass',
                            destination=self.endpoint2, direction="<>")
        self.rule1_obj = self.vnc_h.firewall_rule_read(id=self.fw1_uuid)
        self.rule1_obj.set_action_list(ActionListType(host_based_service=True,
                                                      simple_action="pass"))
        self.vnc_h.firewall_rule_update(self.rule1_obj)
        self.addCleanup(self.vnc_h.delete_firewall_rule, id=self.fw1_uuid)

        # Create FW policy and add the rule
        self.rules = [{'uuid': self.fw1_uuid, 'seq_no': 20}]
        self.fwp_policy_fqname = ['default-domain',
                                  self.project_name, 'hbs_fw_pol']
        self.fwp_uuid = self.vnc_h.create_firewall_policy(
                                                parent_type='project',
                                                fq_name=self.fwp_policy_fqname,
                                                rules=self.rules)
        self.fwp_obj = self.vnc_h.read_firewall_policy(
                                                fq_name=self.fwp_policy_fqname)
        self.addCleanup(self.vnc_h.delete_firewall_policy, id=self.fwp_uuid)

        # Create an APS and add the policy
        self.aps_fqname = ['default-domain', self.project_name, 'hbs-app']
        self.aps_uuid = self.vnc_h.create_application_policy_set(
                            fq_name=self.aps_fqname, parent_type='project',
                            policies=[{'uuid': self.fwp_uuid, 'seq_no': 20}])
        self.addCleanup(self.vnc_h.delete_application_policy_set,
                        id=self.aps_uuid)
        self.vnc_h.set_tag('application', self.app_tag_name, False,
                           None, 'application-policy-set', self.aps_uuid)

    def setupPods(self, inter_compute=False, inter_vn=False, proto=None):
        self.pods = []
        kc = self.connections.k8s_client
        compute_label_list, compute_count = kc.get_kubernetes_compute_labels()
        self.cs1 = {'computenode': compute_label_list[0]}
        if inter_compute is True:
            self.cs2 = {'computenode': compute_label_list[1]}
        else:
            self.cs2 = self.cs1

        self.vns1 = self.vns2 = self.vn1_dict
        if inter_vn is True:
            self.vns2 = self.vn2_dict

        self.apod1 = self.setup_busybox_pod(namespace=self.namespace_name,
                                            name="apod1",
                                            custom_isolation=True,
                                            fq_network_name=self.vns1,
                                            compute_node_selector=self.cs1)
        self.pods.append(self.apod1)
        assert self.apod1.verify_on_setup()
        self.apod1_dict = self.apod1.__dict__

        if proto is "TCP":
            labels = {'app': "webns1"}
            self.apod2 = self.setup_nginx_pod(namespace=self.namespace_name,
                                              name="apod2", labels=labels,
                                              compute_node_selector=self.cs2,
                                              fq_network_name=self.vns2,
                                              custom_isolation=True)
        else:
            self.apod2 = self.setup_busybox_pod(namespace=self.namespace_name,
                                                name="apod2",
                                                custom_isolation=True,
                                                fq_network_name=self.vns2,
                                                compute_node_selector=self.cs2)
        self.pods.append(self.apod2)
        assert self.apod2.verify_on_setup()
        self.apod2_dict = self.apod2.__dict__

        self.logger.info("pod1-compute-ip:%s pod2-compute-ip:%s" % (
                 self.apod1.compute_ip, self.apod2.compute_ip))

    def setUp(self):
        super(TestHbsTraffic, self).setUp()

    def unsetTags(self):
        # Disassociate tags with VM interfaces
        for index in range(0, len(self.pods)):
            id_val = self.pods[index].vmi_objs[0].uuid
            obj_val = self.read_virtual_machine_interface(id=id_val)
            self.addCleanup(self.vnc_h.unset_tag, tag_type="tier", obj=obj_val)
            self.addCleanup(self.vnc_h.unset_tag, tag_type="application", obj=obj_val)

    def tearDown(self):
        self.logger.info("TEARDOWN")
        super(TestHbsTraffic, self).tearDown()

    @classmethod
    def tearDownClass(cls):
        print("TEARDOWN CLASS")
        super(TestHbsTraffic, cls).tearDownClass()
        assert cls._connections.k8s_client.set_label_for_hbf_nodes(labels={"type":None}), \
              "Error : could not label the nodes"
        cls.namespace.cleanUp()

    def verifyTraffic(self, traffic_type, inter_compute=False):
        # Send Traffic
        if traffic_type is "ICMP":
            assert self.apod1.ping_with_certainty(self.apod2.pod_ip,
                                                  expectation=True, count='5',
                                                  hbf_enabled=True)
            # Verify Flow Information
            if inter_compute is False:
                pod1_vif_id = int(self.apod1_dict['tap_intfs'][0]['index'])
                pod2_vif_id = int(self.apod2_dict['tap_intfs'][0]['index'])
                fflow = self.inputs.run_cmd_on_server(
                                    self.apod1.compute_ip,
                                    "flow --match %s:0" % (self.apod2.pod_ip),
                                    container='agent')
                rflow = self.inputs.run_cmd_on_server(
                                    self.apod1.compute_ip,
                                    "flow --match %s:0" % (self.apod1.pod_ip),
                                    container='agent')
                if pod1_vif_id < pod2_vif_id:
                    assert 'HbsLeft' in fflow
                    assert 'HbsRight' in rflow
                else:
                    assert 'HbsLeft' in rflow
                    assert 'HbsRight' in fflow
            else:
                fflow = self.inputs.run_cmd_on_server(
                                    self.apod1.compute_ip,
                                    "flow --match %s" % (self.apod1.pod_ip),
                                    container='agent')
                rflow = self.inputs.run_cmd_on_server(
                                    self.apod2.compute_ip,
                                    "flow --match %s" % (self.apod2.pod_ip),
                                    container='agent')

                assert 'HbsRight' in fflow
                assert 'HbsLeft' in rflow
        else:
            # TCP flow check using wget
            url = 'http://%s' % (self.apod2.pod_ip)
            assert self.validate_wget(self.apod1, url)
    @preposttest_wrapper
    def test_IcmpIntraVnIntraCompute(self):
        self.setupProjectNetworksAndPolicies()
        self.setupPods()
        self.setupTagsAndFWRules()
        self.verifyTraffic("ICMP")
        self.unsetTags()
    @preposttest_wrapper
    def test_IcmpIntraVnInterCompute(self):
        self.setupProjectNetworksAndPolicies()
        self.setupPods(inter_compute=True)
        self.setupTagsAndFWRules()
        self.verifyTraffic("ICMP", inter_compute=True)
        self.unsetTags()

    @preposttest_wrapper
    def test_IcmpInterVnIntraCompute(self):
        self.setupProjectNetworksAndPolicies()
        self.setupPods(inter_vn=True)
        self.setupTagsAndFWRules()
        self.verifyTraffic("ICMP")
        self.unsetTags()

    @preposttest_wrapper
    def test_IcmpInterVnInterCompute(self):
        self.setupProjectNetworksAndPolicies()
        self.setupPods(inter_compute=True, inter_vn=True)
        self.setupTagsAndFWRules()
        self.verifyTraffic("ICMP", inter_compute=True)
        self.unsetTags()

    @preposttest_wrapper
    def test_TcpIntraVnIntraCompute(self):
        self.setupProjectNetworksAndPolicies()
        self.setupPods(proto="TCP")
        self.setupTagsAndFWRules()
        self.verifyTraffic("TCP")
        self.unsetTags()

    @preposttest_wrapper
    def test_TcpIntraVnInterCompute(self):
        self.setupProjectNetworksAndPolicies()
        self.setupPods(inter_compute=True, proto="TCP")
        self.setupTagsAndFWRules()
        self.verifyTraffic("TCP", inter_compute=True)
        self.unsetTags()

    @preposttest_wrapper
    def test_TcpInterVnIntraCompute(self):
        self.setupProjectNetworksAndPolicies()
        self.setupPods(inter_vn=True, proto="TCP")
        self.setupTagsAndFWRules()
        self.verifyTraffic("TCP")
        self.unsetTags()

    @preposttest_wrapper
    def test_TcpInterVnInterCompute(self):
        self.setupProjectNetworksAndPolicies()
        self.setupPods(inter_compute=True, inter_vn=True, proto="TCP")
        self.setupTagsAndFWRules()
        self.verifyTraffic("TCP", inter_compute=True)
        self.unsetTags()
