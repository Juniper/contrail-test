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

class TestNetworkPolicy(BaseK8sTest):

    @classmethod
    def setUpClass(cls):
        super(TestNetworkPolicy, cls).setUpClass()
        cls.namespace = NamespaceFixture(cls._connections,isolation = True)
        cls.namespace.setUp()
        cls.namespace.verify_on_setup()
	namespace = cls.namespace.name
        cls.hbs = HbsFixture(cls._connections, name="hbs",namespace = namespace)
        cls.hbs.setUp()
        cls.hbs.verify_on_setup()

    def setUp(self):
        super(TestNetworkPolicy, self).setUp()

    @classmethod
    def tearDownClass(cls):
        super(TestNetworkPolicy, cls).tearDownClass()
	cls.hbs.cleanUp()
        cls.namespace.cleanUp()

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
			    connections=proj_connection, inputs=proj_inputs, vn_name = vn1_name)
        vn1_dict = {"domain": vn1.domain_name,
                   "project" : vn1.project_name,
                   "name": vn1.vn_name}

	if vn2_name != None:
             vn2 = self.setup_vn(project_name =project_name,
			         connections=proj_connection, inputs=proj_inputs, vn_name = vn2_name)
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
        pod2 = self.setup_busybox_pod(namespace=namespace_name,
		 custom_isolation=True,
		 fq_network_name = (vn2_dict or vn1_dict),
		 compute_node_selector=compute_selector_2)
        assert pod2.verify_on_setup()
        assert pod1.ping_with_certainty(pod2.pod_ip)
	self.addCleanup(self.perform_cleanup, pod1)
	self.addCleanup(self.perform_cleanup, pod2)
	
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
		project_fq_name = ['default-domain', project_name]
		tag_obj = self.read_project_obj(project_fq_name=project_fq_name)
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
            self.set_tag(tag_type=tag_type, tag_value=tagv,
		         obj=tag_obj)
            self.set_tag(tag_type='application', tag_value=app_tag_name,
		         obj=tag_obj)

        # Create FW rule
        site_ep1 = {'tags': ['%s=%s'%(tag_type, tag_value)]}
	if tag2_value != None:
        	site_ep2 = {'tags': ['%s=%s'%(tag_type, tag2_value)]}
	else:
		site_ep2 = None
	fwr_fqname = ['default-domain', project_name, 'my_fwr']
	fwr_uuid = self.vnc_h.create_firewall_rule(fq_name=fwr_fqname,
			 parent_type='project', service_groups=[], protocol='icmp',
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

        #import pdb; pdb.set_trace()
        assert pod1.ping_with_certainty(pod2.pod_ip, expectation=True, count='5', hbf_enabled=True)

	# Cleanups
	for tag_obj in tag_obj_list:
       		self.addCleanup(self.vnc_h.unset_tag,
			 tag_type=tag_type, obj=tag_obj)
   		self.addCleanup(self.vnc_h.unset_tag,
			 tag_type='application', obj=tag_obj)
	'''
       	self.addCleanup(self.vnc_h.delete_tag, id=tag1)
	if tag2_value != None:
        	self.addCleanup(self.vnc_h.delete_tag, id=tag2)
       	self.addCleanup(self.vnc_h.delete_tag, id=apptag)
	'''

        return policy1_fixture, pod1, pod2, fwp_obj, project_name
 
    ''' Test 16 '''
    @preposttest_wrapper
    def test_intra_vn_intra_compute_tag_tier_tagat_vn(self):
	self.run_test(vn1_name='myvn',
		tag_type='tier',
		tag_value='myweb',
		tag_obj_name='vn')
    # end intra_vn_intra_compute_tag_tier_tagat_vn

    @test.attr(type=['openshift_1', 'ci_contrail_go_k8s_sanity'])
    @preposttest_wrapper
    def test_intra_vn_intra_compute_tag_deployment_tagat_vn(self):
	self.run_test(vn1_name='myvn',
		tag_type='deployment',
		tag_value='hr',
		tag_obj_name='vn')
    # end intra_vn_intra_compute_tag_deployment_tagat_vn

    @preposttest_wrapper
    def test_intra_vn_intra_compute_tag_site_tagat_vn(self):
	self.run_test(vn1_name='myvn',
		tag_type='site',
		tag_value='BLR',
		tag_obj_name='vn')
    # end intra_vn_intra_compute_tag_site_tagat_vn

    @preposttest_wrapper
    def test_intra_vn_intra_compute_tag_label_tagat_vn(self):
	self.run_test(vn1_name='myvn',
		tag_type='label',
		tag_value='MYVN',
		tag_obj_name='vn')
    # end intra_vn_intra_compute_tag_label_tagat_vn
    ''' Test 16 End '''

    ''' Test 17 '''
    @preposttest_wrapper
    def test_intra_vn_inter_compute_tag_tier_tagat_vn(self):
	self.run_test(vn1_name='myvn',
		tag_type='tier',
		tag_value='myweb',
		tag_obj_name='vn',
		inter_compute=True)
    # end intra_vn_inter_compute_tag_tier_tagat_vn

    @preposttest_wrapper
    def test_intra_vn_inter_compute_tag_deployment_tagat_vn(self):
	self.run_test(vn1_name='myvn',
		tag_type='deployment',
		tag_value='hr',
		tag_obj_name='vn',
		inter_compute=True)
    # end intra_vn_inter_compute_tag_deployment_tagat_vn

    @preposttest_wrapper
    def test_intra_vn_inter_compute_tag_site_tagat_vn(self):
	self.run_test(vn1_name='myvn',
		tag_type='site',
		tag_value='BLR',
		tag_obj_name='vn',
		inter_compute=True)
    # end intra_vn_inter_compute_tag_site_tagat_vn

    @preposttest_wrapper
    def test_intra_vn_inter_compute_tag_label_tagat_vn(self):
	self.run_test(vn1_name='myvn',
		tag_type='label',
		tag_value='MYVN',
		tag_obj_name='vn',
		inter_compute=True)
    # end intra_vn_inter_compute_tag_label_tagat_vn
    ''' Test 17 End '''

    ''' Test 18 '''
    @preposttest_wrapper
    def test_inter_vn_intra_compute_tag_tier_tagat_vmi(self):
	self.run_test(vn1_name='myvn',
                vn2_name="myvn2",
		tag_type='tier',
		tag_value='myweb',
		tag2_value='myapp',
		tag_obj_name='vmi')
    # end test_inter_vn_intra_compute_tag_tier_tagat_vmi

    @preposttest_wrapper
    def test_inter_vn_intra_compute_tag_deployment_tagat_vmi(self):
	self.run_test(vn1_name='myvn',
                vn2_name="myvn2",
		tag_type='deployment',
		tag_value='hr',
		tag2_value='mkt',
		tag_obj_name='vmi')
    # end test_inter_vn_intra_compute_tag_deployment_tagat_vmi

    @preposttest_wrapper
    def test_inter_vn_intra_compute_tag_site_tagat_vmi(self):
	self.run_test(vn1_name='myvn',
                vn2_name="myvn2",
		tag_type='site',
		tag_value='BLR',
		tag2_value='SVL',
		tag_obj_name='vmi')
    # end test_inter_vn_intra_compute_tag_site_tagat_vmi

    @preposttest_wrapper
    def test_inter_vn_intra_compute_tag_label_tagat_vmi(self):
	self.run_test(vn1_name='myvn',
                vn2_name="myvn2",
		tag_type='label',
		tag_value='MYVMI1',
		tag2_value='MYVMI2',
		tag_obj_name='vmi')
    # end test_inter_vn_intra_compute_tag_label_tagat_vmi
    ''' Test Case 18 End '''

    ''' Test 19 '''
    @preposttest_wrapper
    def test_inter_vn_inter_compute_tag_tier_tagat_vmi(self):
	self.run_test(vn1_name='myvn',
                vn2_name="myvn2",
		tag_type='tier',
		tag_value='myweb',
		tag2_value='myapp',
		tag_obj_name='vmi',
		inter_compute=True)
    # end test_inter_vn_inter_compute_tag_tier_tagat_vmi

    @preposttest_wrapper
    def test_inter_vn_inter_compute_tag_deployment_tagat_vmi(self):
	self.run_test(vn1_name='myvn',
                vn2_name="myvn2",
		tag_type='deployment',
		tag_value='hr',
		tag2_value='mkt',
		tag_obj_name='vmi',
		inter_compute=True)
    # end test_inter_vn_inter_compute_tag_deployment_tagat_vmi

    @preposttest_wrapper
    def test_inter_vn_inter_compute_tag_site_tagat_vmi(self):
	self.run_test(vn1_name='myvn',
                vn2_name="myvn2",
		tag_type='site',
		tag_value='BLR',
		tag2_value='SVL',
		tag_obj_name='vmi',
		inter_compute=True)
    # end test_inter_vn_inter_compute_tag_site_tagat_vmi

    @preposttest_wrapper
    def test_inter_vn_inter_compute_tag_label_tagat_vmi(self):
	self.run_test(vn1_name='myvn',
                vn2_name="myvn2",
		tag_type='label',
		tag_value='MYVMI1',
		tag2_value='MYVMI2',
		tag_obj_name='vmi',
		inter_compute=True)
    # end test_inter_vn_inter_compute_tag_label_tagat_vmi
    ''' Test Case 19 End '''

    ''' Test 20 '''
    @preposttest_wrapper
    def test_intra_vn_intra_compute_tag_tier_tagat_vmi(self):
	self.run_test(vn1_name='myvn',
		tag_type='tier',
		tag_value='myweb',
		tag2_value='myapp',
		tag_obj_name='vmi')
    # end test_intra_vn_intra_compute_tag_tier_tagat_vmi

    @preposttest_wrapper
    def test_intra_vn_intra_compute_tag_deployment_tagat_vmi(self):
	self.run_test(vn1_name='myvn',
		tag_type='deployment',
		tag_value='hr',
		tag2_value='mkt',
		tag_obj_name='vmi')
    # end test_intra_vn_intra_compute_tag_deployment_tagat_vmi

    @preposttest_wrapper
    def test_intra_vn_intra_compute_tag_site_tagat_vmi(self):
	self.run_test(vn1_name='myvn',
		tag_type='site',
		tag_value='BLR',
		tag2_value='SVL',
		tag_obj_name='vmi')
    # end test_intra_vn_intra_compute_tag_site_tagat_vmi

    @preposttest_wrapper
    def test_intra_vn_intra_compute_tag_label_tagat_vmi(self):
	self.run_test(vn1_name='myvn',
		tag_type='label',
		tag_value='MYVMI1',
		tag2_value='MYVMI2',
		tag_obj_name='vmi')
    # end test_intra_vn_intra_compute_tag_label_tagat_vmi
    ''' Test Case 20 End '''

    ''' Test 21 '''
    @preposttest_wrapper
    def test_intra_vn_inter_compute_tag_tier_tagat_vmi(self):
	self.run_test(vn1_name='myvn',
		tag_type='tier',
		tag_value='myweb',
		tag2_value='myapp',
		tag_obj_name='vmi',
		inter_compute=True)
    # end test_intra_vn_inter_compute_tag_tier_tagat_vmi

    @preposttest_wrapper
    def test_intra_vn_inter_compute_tag_deployment_tagat_vmi(self):
	self.run_test(vn1_name='myvn',
		tag_type='deployment',
		tag_value='hr',
		tag2_value='mkt',
		tag_obj_name='vmi',
		inter_compute=True)
    # end test_intra_vn_inter_compute_tag_deployment_tagat_vmi

    @preposttest_wrapper
    def test_intra_vn_inter_compute_tag_site_tagat_vmi(self):
	self.run_test(vn1_name='myvn',
		tag_type='site',
		tag_value='BLR',
		tag2_value='SVL',
		tag_obj_name='vmi',
		inter_compute=True)
    # end test_intra_vn_inter_compute_tag_site_tagat_vmi

    @preposttest_wrapper
    def test_intra_vn_inter_compute_tag_label_tagat_vmi(self):
	self.run_test(vn1_name='myvn',
		tag_type='label',
		tag_value='MYVMI1',
		tag2_value='MYVMI2',
		tag_obj_name='vmi',
		inter_compute=True)
    # end test_intra_vn_inter_compute_tag_label_tagat_vmi
    ''' Test Case 21 End '''

    ''' Test 22 '''
    @preposttest_wrapper
    def test_inter_vn_intra_compute_tag_tier_tagat_project(self):
	self.run_test(vn1_name='myvn1',
		vn2_name="myvn2",
		tag_type='tier',
		tag_value='myweb',
		tag_obj_name='project')
    # end test_inter_vn_intra_compute_tag_tier_tagat_project
    ''' Test 22 End '''

    ''' Test 23 '''
    @preposttest_wrapper
    def test_inter_vn_inter_compute_tag_tier_tagat_project(self):
        self.run_test(vn1_name='myvn1',
                vn2_name="myvn2",
                tag_type='tier',
                tag_value='myweb',
                tag_obj_name='project',
		inter_compute=True)
    # end test_inter_vn_inter_compute_tag_tier_tagat_project
    ''' Test 23 End '''

    ''' Test 24 '''
    @preposttest_wrapper
    def test_inter_vn_inter_compute_tag_tier_tagat_vn(self):
	self.run_test(vn1_name='myvn1',
                vn2_name="myvn2",
		tag_type='tier',
		tag_value='myweb',
		tag_obj_name='vn',
		inter_compute=True)
    # end test_inter_vn_inter_compute_tag_tier_tagat_vn

    @preposttest_wrapper
    def test_inter_vn_inter_compute_tag_deployment_tagat_vn(self):
	self.run_test(vn1_name='myvn1',
                vn2_name="myvn2",
		tag_type='deployment',
		tag_value='hr',
		tag_obj_name='vn',
		inter_compute=True)
    # end test_inter_vn_inter_compute_tag_deployment_tagat_vn

    @preposttest_wrapper
    def test_inter_vn_inter_compute_tag_site_tagat_vn(self):
	self.run_test(vn1_name='myvn1',
                vn2_name="myvn2",
		tag_type='site',
		tag_value='BLR',
		tag_obj_name='vn',
		inter_compute=True)
    # end test_inter_vn_inter_compute_tag_site_tagat_vn

    @preposttest_wrapper
    def test_inter_vn_inter_compute_tag_label_tagat_vn(self):
	self.run_test(vn1_name='myvn1',
                vn2_name="myvn2",
		tag_type='label',
		tag_value='MYVN',
		tag_obj_name='vn',
		inter_compute=True)
    # end test_inter_vn_inter_compute_tag_label_tagat_vn
    ''' Test 24 End '''

    ''' Test case 28 '''
    @preposttest_wrapper
    def test_policy_at_firewall_and_network_level(self):
        policy_fix, pod1, pod2, fwp_obj_uuid, project_name = self.run_test(vn1_name='myvn11',
                vn2_name="myvn22",tag_type='tier', tag_value='myweb11',tag2_value='myweb22',
                tag_obj_name='vmi', cleanup=False)
        #import pdb;pdb.set_trace()
        fwr_uuid=fwp_obj_uuid.get_firewall_rule_refs()[0]['uuid']

        rule_obj = self.vnc_h.firewall_rule_read(id=fwr_uuid)
        rule_obj.set_action_list(ActionListType(host_based_service=True,
                                      simple_action="deny"))
        self.vnc_h.firewall_rule_update(rule_obj)

        # Expect ping to fail, as fw policy is set to deny
        assert pod1.ping_with_certainty(pod2.pod_ip, expectation=False)

        self.vnc_h.update_firewall_rule(uuid=fwr_uuid, action='pass')
        assert pod1.ping_with_certainty(pod2.pod_ip, expectation=True, count='5', hbf_enabled=True)

        policy_entries = policy_fix.get_entries()
        policy_id = policy_fix.get_id()
        policy_entries.policy_rule[0].action_list.simple_action = 'deny'
        p_rules = policy_entries
        policy_fix.update_policy(policy_id, p_rules)

        # Expect ping to fail as network policy action is deny
        assert pod1.ping_with_certainty(pod2.pod_ip, expectation=False)

        #self.perform_cleanup(pod1)
        #self.perform_cleanup(pod2)
    # end test_policy_at_firewall_network_level
    ''' Test 28 End '''

    @preposttest_wrapper
    def intra_vn_tag_tier_tagat_project(self):
	self.run_test(vn1_name='myvn',
		tag_type='tier',
		tag_value='myweb',
		tag_obj_name='project')
    # end intra_vn_tag_tier_tagat_project

    @preposttest_wrapper
    def test_tag_at_vmi_intra_vn(self):
        self.run_test(vn1_name='myvn1',
                tag_type='tier',
                tag_value='myweb',
                tag_obj_name='vmi')

    # end test_tag_at_vmi_intra_vn

    @preposttest_wrapper
    def test_tag_at_vmi_inter_vn(self):
        '''
        Test ping between 2 PODs
        '''
        self.run_test(vn1_name='myvn1',
                vn2_name="myvn2",
                tag_type='tier',
                tag_value='myweb',
                tag_obj_name='vmi')

    # end test_tag_at_vmi_inter_vn

    ''' Test 29 '''
    @preposttest_wrapper
    def test_fwp_tag_priority_order_vmi_vn(self):
        policy_fix, pod1, pod2, fwp_obj, project_name = self.run_test(vn1_name='myvn1',
                vn2_name="myvn2",
                tag_type='tier',
                tag_value='myweb1',
                tag_obj_name='vn', tag2_value='myweb2', cleanup=False)
        # Create application tag
	# Create tag
        tag_type = 'tier'
        tag_value1 = 'myweb3'
        tag_value2 = 'myweb4'
        fq_name1 = ['default-domain', project_name,
			 '%s=%s'%(tag_type, tag_value1)]
        fq_name2 = ['default-domain', project_name,
			 '%s=%s'%(tag_type, tag_value2)]
        tier_tag_1 = self.create_tag(fq_name=fq_name1,
		 tag_type=tag_type, tag_value=tag_value1, parent_type='project')
        tier_tag_2 = self.create_tag(fq_name=fq_name2,
                 tag_type=tag_type, tag_value=tag_value2, parent_type='project')

        tag_obj1 = self.read_virtual_machine_interface(id=pod1.vmi_objs[0].uuid)
        tag_obj2 = self.read_virtual_machine_interface(id=pod2.vmi_objs[0].uuid)

        self.set_tag(tag_type=tag_type, tag_value=tag_value1,
		         obj=tag_obj1)
        self.set_tag(tag_type=tag_type, tag_value=tag_value2,
                         obj=tag_obj2)
        self.set_tag(tag_type='application', tag_value='myk8s',
                         obj=tag_obj1)
        self.set_tag(tag_type='application', tag_value='myk8s',
                         obj=tag_obj2)
        site_ep1 = {'tags': ['%s=%s'%(tag_type, tag_value1)]}
        site_ep2 = {'tags': ['%s=%s'%(tag_type, tag_value2)]}
	fwr_fqname = ['default-domain', project_name, 'my_fwr_tier']
	fwr_uuid = self.vnc_h.create_firewall_rule(fq_name=fwr_fqname,
			 parent_type='project', service_groups=[], protocol='icmp',
                         source=site_ep1, destination=site_ep2 ,action='deny',
			 direction = "<>")
	rule_obj = self.vnc_h.firewall_rule_read(id=fwr_uuid)
	#rule_obj.set_action_list(ActionListType(host_based_service=True,simple_action="deny"))
        #self.vnc_h.firewall_rule_update(rule_obj)
	'''
        self.addCleanup(self.vnc_h.unset_tag,
                         tag_type=tag_type, obj=tag_obj1)
        self.addCleanup(self.vnc_h.unset_tag,
                         tag_type=tag_type, obj=tag_obj2)
        self.addCleanup(self.vnc_h.unset_tag,
                         tag_type='application', obj=tag_obj1)
        self.addCleanup(self.vnc_h.unset_tag,
                         tag_type='application', obj=tag_obj2)
	'''
        self.addCleanup(self.vnc_h.delete_tag, id=tier_tag_1)
        self.addCleanup(self.vnc_h.delete_tag, id=tier_tag_2)
        self.addCleanup(self.vnc_h.delete_firewall_rule, id=fwr_uuid)

        # To fw policy add the rule to deny traffic at vmi
        rules = [{'uuid': fwr_uuid, 'seq_no': 21}]
        self.vnc_h.add_firewall_rules(fwp_obj.uuid, rules)


        # Expect ping to fail as tier tag vmis drop traffic
        assert pod1.ping_with_certainty(pod2.pod_ip, expectation=False)

        # Reset fw rule to allow traffic for tier tag expect ping to pass
        rule_obj.set_action_list(ActionListType(host_based_service=True,simple_action="pass"))
        self.vnc_h.firewall_rule_update(rule_obj)

        assert pod1.ping_with_certainty(pod2.pod_ip, expectation=True, count='5', hbf_enabled=True)
        self.vnc_h.remove_firewall_rules(fwp_obj.uuid, rules)
        self.vnc_h.unset_tag(tag_type=tag_type, obj=tag_obj1)
        self.vnc_h.unset_tag(tag_type=tag_type, obj=tag_obj2)
        self.vnc_h.unset_tag(tag_type='application', obj=tag_obj1)
        self.vnc_h.unset_tag(tag_type='application', obj=tag_obj2)
    # end test_ping_inter_vn
    ''' Test case 29 End '''
