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
from tcutils.contrail_status_check import ContrailStatusChecker
from k8s.hbs import HbsFixture

class TestHbsFirewall(BaseK8sTest):
    @classmethod
    def setUpClass(cls):
        super(TestHbsFirewall, cls).setUpClass()
        cls.namespace = NamespaceFixture(cls._connections,isolation = True)
        cls.namespace.setUp()
        cls.namespace.verify_on_setup()
        namespace = cls.namespace.name
        cls.hbs = HbsFixture(cls._connections, name="hbs",namespace = namespace)
        assert cls._connections.k8s_client.set_label_for_hbf_nodes( \
            node_selector='computenode'), "Error : could not label the nodes"
        cls.hbs.setUp()
        cls.hbs.verify_on_setup()


    def setUp(self):
        super(TestHbsFirewall, self).setUp()

    @classmethod
    def tearDownClass(cls):
        super(TestHbsFirewall, cls).tearDownClass()
        cls.namespace.cleanUp()
        assert cls._connections.k8s_client.set_label_for_hbf_nodes(labels={"type":None}), \
              "Error : could not label the nodes"
    def run_test(self,
		vn1_name,
		tag_type,
		tag_value,
		tag_obj_name,
		vn2_name=None,
		tag2_value=None,
		inter_compute=False,
                cleanup=True):
        project_name = "k8s-" + self.namespace.name
        isolated_creds = IsolatedCreds(
            self.inputs,
            project_name,
            input_file=self.input_file,
            logger=self.logger)
        self.remove_from_cleanups(isolated_creds.cleanUp)
        proj_fix = self.create_project(project_name=project_name,
                                       cleanup=False, connections=self.connections)
        proj_inputs = isolated_creds.get_inputs(proj_fix)
        proj_connection = isolated_creds.get_connections(proj_inputs)

	# Create VNs
        vn1 = self.setup_vn(project_name =project_name,
                         connections=proj_connection, inputs=proj_inputs,
			 vn_name = vn1_name)
        vn1_dict = {"domain": vn1.domain_name,
                   "project" : vn1.project_name,
                   "name": vn1.vn_name}

        if vn2_name != None:
             vn2 = self.setup_vn(project_name = project_name,
                         connections=proj_connection, inputs=proj_inputs,
			 vn_name = vn2_name)
             vn2_dict = {"domain": vn2.domain_name,
                   	"project" : vn2.project_name,
                   	"name": vn2.vn_name}

             # Attach policy btw vn1 and vn2 to allow all traffic
             pol_rules_vn1_vn2 = [
                 {
                     'direction': '<>', 'simple_action': 'pass',
                     'protocol': 'any', 'src_ports': 'any',
                     'dst_ports': 'any',
                     'source_network': vn1_name,
                     'dest_network': vn2_name,
                 },
             ]

             policy1_name = 'p1_vn1_vn2'
             policy1_fixture = self.useFixture(
                 PolicyFixture(
                     policy_name=policy1_name,
                     rules_list=pol_rules_vn1_vn2,
                     inputs=proj_inputs,
                     connections=proj_connection))

             policy_attach_fix1 = self.useFixture(AttachPolicyFixture(
                        proj_inputs, proj_connection, vn1, policy1_fixture))
             policy_attach_fix1 = self.useFixture(AttachPolicyFixture(
                        proj_inputs, proj_connection, vn2, policy1_fixture))
        else:
            vn2_dict = None
            vn2 = None
            policy1_fixture = None
        # Create 2 pods
        namespace_name = self.namespace.name
        compute_label_list, compute_count = self.connections.k8s_client.get_kubernetes_compute_labels()
        compute_selector_1 = {'computenode': compute_label_list[0]} 
        if inter_compute and compute_count >= 2:
             compute_selector_2 = {'computenode': compute_label_list[1]}
        else:
             compute_selector_2 = compute_selector_1

        pod1 = self.setup_busybox_pod(namespace=namespace_name,
		 custom_isolation=True, fq_network_name=vn1_dict,
		 compute_node_selector=compute_selector_1)
        assert pod1.verify_on_setup()
        self.addCleanup(self.perform_cleanup, pod1)
        pod2 = self.setup_busybox_pod(namespace=namespace_name,
		 custom_isolation=True,
		 fq_network_name = (vn2_dict or vn1_dict),
		 compute_node_selector=compute_selector_2)
        assert pod2.verify_on_setup()
        self.addCleanup(self.perform_cleanup, pod2)
        assert pod1.ping_with_certainty(pod2.pod_ip)

        pod3 = self.setup_busybox_pod(namespace=namespace_name,
                 custom_isolation=True, fq_network_name=vn1_dict,
                 compute_node_selector=compute_selector_1)
        assert pod3.verify_on_setup()
        self.addCleanup(self.perform_cleanup, pod3)
        pod4 = self.setup_busybox_pod(namespace=namespace_name,
                custom_isolation=True,
                fq_network_name = (vn2_dict or vn1_dict),
                compute_node_selector=compute_selector_2)
        assert pod4.verify_on_setup()
        self.addCleanup(self.perform_cleanup, pod4)
        assert pod3.ping_with_certainty(pod4.pod_ip)

	# Create tags
        fq_name1 = ['default-domain', project_name,
                    '%s=%s'%(tag_type, tag_value)]
        tag1 = self.create_tag(fq_name=fq_name1,
                               tag_type=tag_type, tag_value=tag_value,
                               parent_type='project')
        self.addCleanup(self.vnc_h.delete_tag, id=tag1)
        if tag2_value != None:
       	     fq_name2 = ['default-domain', project_name,
                         '%s=%s'%(tag_type, tag2_value)]
             tag2 = self.create_tag(fq_name=fq_name1,
                                    tag_type=tag_type, tag_value=tag2_value,
                                    parent_type='project')
             self.addCleanup(self.vnc_h.delete_tag, id=tag2)
        app_tag_name = 'myk8s'
        fq_name3 = ['default-domain', project_name,
			 '%s=%s'%('application', 'myk8s')]
        apptag = self.create_tag(fq_name=fq_name3,
                                 tag_type='application',
                                 tag_value=app_tag_name, parent_type='project')
        self.addCleanup(self.vnc_h.delete_tag, id=apptag)

        # Apply tag
        tag_obj_list = []
        tag_value_list = []
        if tag_obj_name == 'project':
            project_name_fq = ['default-domain', project_name]
            tag_obj = self.read_project_obj(project_fq_name=project_name_fq)
            tag_obj_list.append(tag_obj)
            tag_value_list.append(tag_value)
        elif tag_obj_name == 'vmi':
            tag_obj1 = self.read_virtual_machine_interface(
                       id=pod1.vmi_objs[0].uuid)
            tag_obj_list.append(tag_obj1)
            tag_value_list.append(tag_value)
            tag_obj2 = self.read_virtual_machine_interface(
                       id=pod2.vmi_objs[0].uuid)
            tag_obj_list.append(tag_obj2)
            tag_value_list.append(tag2_value or tag_value)
        elif tag_obj_name == 'vn':
            vn_name = ['default-domain', project_name, '%s'%(vn1_name)]
            tag_obj = self.read_virtual_network(fq_name=vn_name)
            tag_obj_list.append(tag_obj)
            tag_value_list.append(tag_value)
            if vn2_name:
                vn_name = ['default-domain', project_name, '%s'%(vn2_name)]
                tag_obj = self.read_virtual_network(fq_name=vn_name)
                tag_obj_list.append(tag_obj)
                tag_value_list.append(tag2_value or tag_value)
        for tag_obj, tagv in zip(tag_obj_list, tag_value_list):
            self.set_tag(tag_type=tag_type, tag_value=tagv, obj=tag_obj)
            self.set_tag(tag_type='application', tag_value=app_tag_name, obj=tag_obj)

        # Only add application tag to pod3 and pod4 vmi, used for checking negative case
        pod3_vmi = self.read_virtual_machine_interface(
                   id=pod3.vmi_objs[0].uuid)
        pod4_vmi = self.read_virtual_machine_interface(
                   id=pod4.vmi_objs[0].uuid)
        self.set_tag(tag_type='application', tag_value=app_tag_name,
                     obj=pod3_vmi)
        self.set_tag(tag_type='application', tag_value=app_tag_name,
                     obj=pod4_vmi)
        self.addCleanup(self.vnc_h.unset_tag,
                        tag_type='application', obj=pod3_vmi)
        self.addCleanup(self.vnc_h.unset_tag,
                        tag_type='application', obj=pod4_vmi)
        # Create FW rule
        site_ep1 = {'tags': ['%s=%s'%(tag_type, tag_value)]}
        if tag2_value != None:
            site_ep2 = {'tags': ['%s=%s'%(tag_type, tag2_value)]}
        else:
            site_ep2 = None
        fwr_fqname = ['default-domain', project_name, 'my_fwr']
        fwr_uuid = self.vnc_h.create_firewall_rule(fq_name=fwr_fqname,
                                                   parent_type='project', 
                                                   service_groups=[], protocol='icmp',
                                                   source=site_ep1,
                                                   destination=(site_ep2 or site_ep1), action='pass',
                                                   direction = "<>")

        rule_obj = self.vnc_h.firewall_rule_read(id=fwr_uuid)
        rule_obj.set_action_list(ActionListType(host_based_service=True,simple_action="pass"))
        self.vnc_h.firewall_rule_update(rule_obj)
        self.addCleanup(self.vnc_h.delete_firewall_rule, id=fwr_uuid)

        # Create FW policy and add the rule
        rules = [{'uuid': fwr_uuid, 'seq_no': 20}]
        fwp_policy_fqname = ['default-domain', project_name, 'fw_pol']
        fwp_uuid = self.vnc_h.create_firewall_policy(
                                    parent_type='project',
                                    fq_name=fwp_policy_fqname,
                                    rules=rules)
        fwp_obj = self.vnc_h.read_firewall_policy(fq_name=fwp_policy_fqname)
        self.addCleanup(self.vnc_h.delete_firewall_policy, id=fwp_uuid)

        # Create an APS and add the policy
        aps_fqname = ['default-domain', project_name, 'myaps']
        aps_uuid = self.vnc_h.create_application_policy_set(
                         fq_name=aps_fqname,
                         parent_type='project',
                         policies=[{'uuid': fwp_uuid, 'seq_no': 20}])
        self.addCleanup(self.vnc_h.delete_application_policy_set, id=aps_uuid)
        self.vnc_h.set_tag('application', app_tag_name,
                           False, None, 'application-policy-set', aps_uuid)

        assert pod1.ping_with_certainty(pod2.pod_ip, expectation=True, count='5', hbf_enabled=True)
        assert pod3.ping_with_certainty(pod4.pod_ip, expectation=False, count='5', hbf_enabled=True)

	# Cleanups
        for tag_obj in tag_obj_list:
            self.addCleanup(self.vnc_h.unset_tag,
                            tag_type=tag_type, obj=tag_obj)
            self.addCleanup(self.vnc_h.unset_tag,
                            tag_type='application', obj=tag_obj)
        return pod1, pod2, pod3, pod4, self.namespace.name

    '''
       TEST CASE 30
    '''
    @preposttest_wrapper
    def test_hbs_with_contrail_apiserver_restart(self):
        pod1, pod2, pod3, pod4 , namespace_name = self.run_test(vn1_name='myvn',
                                 vn2_name="myvn2", tag_type='tier', tag_value='web_api',
                                 tag2_value='db_api', tag_obj_name='vmi', inter_compute=True)
        self.inputs.restart_service("contrail-api",
                                    self.inputs.cfgm_ips,
                                    container = "api-server")
        time.sleep(200)
        cluster_status, error_nodes = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        # some services go to initializing , seems like setup so removing assert for now
        #assert cluster_status, 'All nodes and services not up. Failure nodes are: %s' % (
        #            error_nodes)

        assert pod1.ping_with_certainty(pod2.pod_ip, expectation=True, count='5', hbf_enabled=True)
        assert pod2.ping_with_certainty(pod1.pod_ip, expectation=True, count='5', hbf_enabled=True)
        assert pod3.ping_with_certainty(pod4.pod_ip, expectation=False, count='5', hbf_enabled=True)
        assert pod4.ping_with_certainty(pod3.pod_ip, expectation=False, count='5', hbf_enabled=True) 
        #self.setup_csrx(namespace_name=namespace_name, delete=True)
    # test_hbs_with_contrail_apiserver_restart

    '''
       TEST CASE 33
    '''
    @preposttest_wrapper
    def test_hbs_with_vrouter_agent_restart(self):
        pod1, pod2, pod3, pod4, namespace_name = self.run_test(vn1_name='myvn',
                               vn2_name="myvn2", tag_type='tier', tag_value='web_agent',
                               tag2_value='db_agent', tag_obj_name='vmi', inter_compute=True)
        self.restart_vrouter_agent()
        time.sleep(200)
        cluster_status, error_nodes = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        #assert cluster_status, 'All nodes and services not up. Failure nodes are: %s' % (
        #            error_nodes)

        assert pod1.ping_with_certainty(pod2.pod_ip, expectation=True, count='5', hbf_enabled=True)
        assert pod2.ping_with_certainty(pod1.pod_ip, expectation=True, count='5', hbf_enabled=True)
        assert pod3.ping_with_certainty(pod4.pod_ip, expectation=False, count='5', hbf_enabled=True)
        assert pod4.ping_with_certainty(pod3.pod_ip, expectation=False, count='5', hbf_enabled=True)
        #self.setup_csrx(namespace_name=namespace_name, delete=True)

    # end test_hbs_with_vrouter_agent_restart

    '''
      TEST CASE 34
    '''
    @preposttest_wrapper
    def test_hbs_with_kube_manager_restart_on_master(self):
        pod1, pod2, pod3, pod4, namespace_name = self.run_test(vn1_name='myvn',
                vn2_name="myvn2", tag_type='tier', tag_value='web_km',
                tag2_value='db_km', tag_obj_name='vmi', inter_compute=True)
        self.restart_kube_manager()
        time.sleep(200)
        cluster_status, error_nodes = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        #assert cluster_status, 'All nodes and services not up. Failure nodes are: %s' % (
        #            error_nodes)

        assert pod1.ping_with_certainty(pod2.pod_ip, expectation=True, count='5', hbf_enabled=True)
        assert pod2.ping_with_certainty(pod1.pod_ip, expectation=True, count='5', hbf_enabled=True)
        assert pod3.ping_with_certainty(pod4.pod_ip, expectation=False, count='5', hbf_enabled=True)
        assert pod4.ping_with_certainty(pod3.pod_ip, expectation=False, count='5', hbf_enabled=True)

        #self.setup_csrx(namespace_name=namespace_name, delete=True)

    # test_hbs_with_kube_manager_restart_on_master

    '''
      TEST CASE 35
    '''
    @preposttest_wrapper
    def test_hbs_with_kubelet_restart_on_computes(self):
        pod1, pod2, pod3, pod4, namespace_name = self.run_test(vn1_name='myvn',
                vn2_name="myvn2",
                tag_type='tier',
                tag_value='web_let',
                tag2_value='db_let',
                tag_obj_name='vmi',
                inter_compute=True)
        self.inputs.restart_service(service_name = "kubelet",
                                    host_ips = self.inputs.compute_ips)
        time.sleep(200)
        cluster_status, error_nodes = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        #assert cluster_status, 'All nodes and services not up. Failure nodes are: %s' % (
        #            error_nodes)

        assert pod1.ping_with_certainty(pod2.pod_ip, expectation=True, count='5', hbf_enabled=True)
        assert pod2.ping_with_certainty(pod1.pod_ip, expectation=True, count='5', hbf_enabled=True)
        assert pod3.ping_with_certainty(pod4.pod_ip, expectation=False, count='5', hbf_enabled=True)
        assert pod4.ping_with_certainty(pod3.pod_ip, expectation=False, count='5', hbf_enabled=True)

        #self.setup_csrx(namespace_name=namespace_name, delete=True)

    # end test_hbs_with_kubelet_restart_on_computes

    '''
       TEST CASE 32
    '''
    @preposttest_wrapper
    @skip_because(bug='1234')
    def test_hbs_with_docker_restart_on_slave(self):
        pod1, pod2, pod3, pod4, namespace_name = self.run_test(vn1_name='myvn',
                vn2_name="myvn2",
                tag_type='tier',
                tag_value='web_slave',
                tag2_value='db_slave',
                tag_obj_name='vmi',
                inter_compute=True)
        self.inputs.restart_service(service_name = "docker",
                                    host_ips = self.inputs.k8s_slave_ips)
        time.sleep(200)
        cluster_status, error_nodes = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        #assert cluster_status, 'All nodes and services not up. Failure nodes are: %s' % (
        #            error_nodes)
        # adding big sleep as after docker restart ping is successful only after a big delay, need to debug
        assert pod1.ping_with_certainty(pod2.pod_ip, expectation=True, count='5', hbf_enabled=True)
        assert pod2.ping_with_certainty(pod1.pod_ip, expectation=True, count='5', hbf_enabled=True)
        assert pod3.ping_with_certainty(pod4.pod_ip, expectation=False, count='5', hbf_enabled=True)
        assert pod4.ping_with_certainty(pod3.pod_ip, expectation=False, count='5', hbf_enabled=True)

        #self.setup_csrx(namespace_name=namespace_name, delete=True)

    # end test_hbs_with_docker_restart_on_slave

    '''
       TEST CASE 31
    '''
    @preposttest_wrapper
    def test_hbs_with_docker_restart_on_kube_master(self):
        pod1, pod2, pod3, pod4, namespace_name = self.run_test(vn1_name='myvn',
                vn2_name="myvn2",
                tag_type='tier',
                tag_value='web_kube',
                tag2_value='db_kube',
                tag_obj_name='vmi',
                inter_compute=True)
        self.inputs.restart_service(service_name = "docker",
                                            host_ips = [self.inputs.k8s_master_ip])
        time.sleep(200)
        cluster_status, error_nodes = ContrailStatusChecker(self.inputs).wait_till_contrail_cluster_stable()
        #assert cluster_status, 'All nodes and services not up. Failure nodes are: %s' % (
        #            error_nodes)

        assert pod1.ping_with_certainty(pod2.pod_ip, expectation=True, count='5', hbf_enabled=True)
        assert pod2.ping_with_certainty(pod1.pod_ip, expectation=True, count='5', hbf_enabled=True)
        assert pod3.ping_with_certainty(pod4.pod_ip, expectation=False, count='5', hbf_enabled=True)
        assert pod4.ping_with_certainty(pod3.pod_ip, expectation=False, count='5', hbf_enabled=True)

        #self.setup_csrx(namespace_name=namespace_name, delete=True)

    # end test_hbs_with_docker_restart_on_kube_master
