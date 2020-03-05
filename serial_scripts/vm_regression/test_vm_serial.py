from __future__ import absolute_import
from builtins import str
from builtins import range
from .base import BaseVnVmTest
import traffic_tests
from vn_test import *
from vm_test import *
from floating_ip import *
from policy_test import *
from compute_node_test import ComputeNodeFixture
from user_test import UserFixture
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from common import isolated_creds
import inspect
from tcutils.util import skip_because, is_almost_same
from tcutils.tcpdump_utils import start_tcpdump_for_intf,\
     stop_tcpdump_for_intf, verify_tcpdump_count
import test
from tcutils.contrail_status_check import ContrailStatusChecker
from tcutils.traffic_utils.hping_traffic import Hping3

class TestBasicVMVN0(BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicVMVN0, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBasicVMVN0, cls).tearDownClass()
    
    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter',address_family = 'v6')
    def test_bring_up_vm_with_control_node_down(self):
        '''
        Description: Create VM when there is not active control node. Verify VM comes up fine when all control nodes are back
        Test steps:
                   1. Create a VN.
                   2. Shutdown the control node and spawn some VMs.
                   3. The VMS info should get deleted from the agents after 2 minutes.
                   4. The Tap intf corresponding to the VM should go to ERROR state.
                   5. Bring up the control nodes.
        Pass criteria: The VMs should be back to ACTIVE state, so should the Tap interfaces.
        Maintainer : ganeshahv@juniper.net
        '''
        if len(set(self.inputs.bgp_ips)) < 2:
            raise self.skipTest(
                "Skipping Test. At least 2 control node required to run the test")
        result = True
        vn1_name = get_random_name('vn30')
        vn1_subnets = ['30.1.1.0/24']

        # Collecting all the control node details
        controller_list = []
        for entry in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[entry]
            agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
            for entry in agent_xmpp_status:
                controller_list.append(entry['controller_ip'])
        controller_list = set(controller_list)

        # Stop all the control node
        for entry in controller_list:
            self.logger.info('Stoping the Control service in  %s' % (entry))
            self.inputs.stop_service('contrail-control', [entry],
                                     container='control')
            self.addCleanup(self.inputs.start_service,
                            'contrail-control', [entry],
                            container='control')
        sleep(30)

        vn1_vm1_name = get_random_name('vm1')
        vn1_vm2_name = get_random_name('vm2')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name)
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name)


        vm1_fixture.verify_vm_launched()
        vm2_fixture.verify_vm_launched()
        vm1_node_ip = self.inputs.host_data[
            self.nova_h.get_nova_host_of_vm(vm1_fixture.vm_obj)]['host_ip']
        vm2_node_ip = self.inputs.host_data[
            self.nova_h.get_nova_host_of_vm(vm2_fixture.vm_obj)]['host_ip']
        inspect_h1 = self.agent_inspect[vm1_node_ip]
        inspect_h2 = self.agent_inspect[vm2_node_ip]
        self.logger.info(
            'Checking TAP interface is created for all VM and  should be in Error state')
        vm1_tap_intf = None
        vm2_tap_intf = None
        vm1_tap_intf = inspect_h1.get_vna_tap_interface_by_ip(
            vm1_fixture.vm_ip)
        if vm1_tap_intf is []:
            self.logger.error('TAP interface is not created for VM %s' %
                              (vn1_vm1_name))
            result = result and False
        else:
            if vm1_tap_intf[0]['vrf_name'] != '--ERROR--':
                self.logger.error(
                    'TAP interface VRF info should be Error . But currently in %s' %
                    (vm1_tap_intf[0]['vrf_name']))
                result = result and False

        vm2_tap_intf = inspect_h2.get_vna_tap_interface_by_ip(
            vm2_fixture.vm_ip)
        if vm2_tap_intf is []:
            self.logger.error('TAP interface is not created for VM %s' %
                              (vn1_vm2_name))
            result = result and False
        else:
            if vm2_tap_intf[0]['vrf_name'] != '--ERROR--':
                self.logger.error(
                    'TAP interface VRF info should be Error . But currently in %s' %
                    (vm2_tap_intf[0]['vrf_name']))
                result = result and False

        self.logger.info('Waiting for 120 sec for cleanup to begin')
        sleep(120)
        # Check agent should not have any VN info
        for entry in self.inputs.compute_ips:
            inspect_h = self.agent_inspect[entry]
            self.logger.info('Checking VN info in agent %s.' % (entry))
            if inspect_h.get_vna_vn(domain=self.project.domain_name, 
                           project=self.project.project_name, 
                           vn_name=vn1_fixture.vn_name):
                self.logger.error(
                    'Agent should not have any VN info present when control node is down')
                result = result and False

        # Start all the control node
        for entry in controller_list:
            self.logger.info('Starting the Control service in  %s' % (entry))
            self.inputs.start_service('contrail-control', [entry],
                                      container='control')
        sleep(10)

        self.logger.info('Checking the VM came up properly or not')
        assert vn1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm1_fixture.verify_on_setup()

        # Check ping between VM
        assert vm2_fixture.ping_to_ip(vm1_fixture.vm_ip)
        if not result:
            self.logger.error(
                'Test to verify cleanup of agent after control nodes stop Failed')
            assert result
        return True

    # end test_bring_up_vm_with_control_node_down
    
    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter',address_family = 'v6')
    def test_ipam_persistence_across_restart_reboots(self):
        '''
        Description: Test to validate IPAM persistence across restarts and reboots of nodes.
        Test steps:
                   1. Create a IPAM.
                   2. Create a VN and launch VMs in it.
                   3. Restart the contrail-vrouter-agent and contrail-control services.
        Pass criteria: The VMs should be back to ACTIVE state and the ping between them should PASS.
        Maintainer : ganeshahv@juniper.net
        '''
        ipam_obj=self.useFixture( IPAMFixture(connections= self.connections, name = get_random_name('my-ipam')))
        assert ipam_obj.verify_on_setup()

        ts = time.time()
        vn_name = get_random_name('vn')
        vn_fixture=self.useFixture( VNFixture(project_name= self.project.project_name, connections= self.connections,
                                 vn_name= vn_name, inputs= self.inputs, subnets=['22.1.1.0/24'], ipam_fq_name = ipam_obj.fq_name))
        assert vn_fixture.verify_on_setup()

        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,project_name = self.inputs.project_name,
                                                vn_obj=vn_fixture.obj, vm_name = get_random_name('vm1')))
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,project_name = self.inputs.project_name,
                                                vn_obj=vn_fixture.obj, vm_name = get_random_name('vm2')))

        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        self.nova_h.wait_till_vm_is_up( vm1_fixture.vm_obj )
        self.nova_h.wait_till_vm_is_up( vm2_fixture.vm_obj )
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip)
        self.logger.info('Will restart the services now')
        for compute_ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter-agent',[compute_ip],
                                        container='agent')
        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('contrail-control',[bgp_ip],
                                        container='control')

        cluster_status, error_nodes = ContrailStatusChecker().wait_till_contrail_cluster_stable()
        assert cluster_status, 'Cluster is not stable after restart'
        self.logger.info('Will check if the ipam persists and ping b/w VMs is still successful')
        assert ipam_obj.verify_on_setup()
        msg = 'VM verification failed after process restarts'
        assert vm1_fixture.verify_on_setup(), msg
        assert vm2_fixture.verify_on_setup(), msg
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip)
        return True
    
    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter',address_family = 'v6')
    def test_multistep_vm_add_delete_with_stop_start_service(self):
        '''
        Description: Test to validate VMs addition deletion after service restarts.
        Test steps:
                   1. Create a VN and launch a VM in it.
                   2. Stop the contrail-vrouter-agent service and check the VM's status.
                   3. Launch one more VM.
                   4. Start the contrail-vrouter-agent service.
        Pass criteria: The VMs should be in ACTIVE state after the contrail-vrouter-agent service is UP.
        Maintainer : ganeshahv@juniper.net
        '''
        vn_name = get_random_name('vn1')
        vn_subnets = ['10.10.10.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        self.logger.info('Launching VM')

        vm1_fixture = VMFixture(connections=self.connections,
                                vn_obj=vn_obj, vm_name=get_random_name('vm1') , project_name=self.inputs.project_name)
        vm1_fixture.setUp()
        assert vm1_fixture.verify_vm_launched()

        self.logger.info('vm1 launched successfully.Stopping vrouter service')
        for compute_ip in self.inputs.compute_ips:
            self.inputs.stop_service('contrail-vrouter-agent', [compute_ip],
                                     container='agent')
            self.addCleanup(self.inputs.start_service,
                            'contrail-vrouter-agent', [compute_ip],
                            container='agent')
        self.logger.info('Trying to delete vm1')
        assert not vm1_fixture.cleanUp()
        self.logger.info(
            'vm1 is not deleted as expected.Trying to launch a new VM vm2')
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name = get_random_name ('vm2'), project_name=self.inputs.project_name))
        assert vm2_fixture.verify_vm_launched()
        self.logger.info('Checking if vm2 has booted up')
        assert not self.nova_h.wait_till_vm_is_up(vm2_fixture.vm_obj)
        self.logger.info(
            'vm2 has not booted up as expected.Starting vrouter service')
        for compute_ip in self.inputs.compute_ips:
            self.inputs.start_service('contrail-vrouter-agent', [compute_ip],
                                      container='agent')
        vm2_fixture.wait_till_vm_is_up()
        self.logger.info('vm2 is up now as expected')
        assert vm2_fixture.verify_on_setup()

        return True
    # end test_multistep_vm_add_delete_with_stop_start_service
    
    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter',address_family = 'v6')
    def test_multistep_vm_delete_with_stop_start_service(self):
        '''
        Description: Test to validate VM's deletion attempt fails when the contrail-vrouter-agent service is down.
        Test steps:
                   1. Create a VN and launch a VM in it.
                   2. Stop the contrail-vrouter-agent service and check the VM's status.
                   3. Try deleting the VM.
                   4. Start the contrail-vrouter-agent service.
        Pass criteria: The VM's deletion should fail and it should come back to ACTIVE state after the contrail-vrouter-agent service is UP.
        Maintainer : ganeshahv@juniper.net
        '''
        vn_name = get_random_name('vn1')
        vn_subnets = ['10.10.10.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        self.logger.info('Launching VM')
        vm1_fixture = VMFixture(connections=self.connections,
                                vn_obj=vn_obj, vm_name = get_random_name('vm1'), project_name=self.inputs.project_name)
        vm1_fixture.setUp()
        vm1_fixture.verify_vm_launched()
        self.logger.info('VM launched successfully.Stopping vrouter service')
        for compute_ip in self.inputs.compute_ips:
            self.inputs.stop_service('contrail-vrouter-agent', [compute_ip],
                                     container='agent')
        #    self.addCleanup( sleep(10))
            self.addCleanup(self.inputs.start_service,
                            'contrail-vrouter-agent', [compute_ip],
                            container='agent')
        self.logger.info('Trying to delete the VM')
        assert not vm1_fixture.cleanUp()
        self.logger.info('VM is not deleted as expected')
        for compute_ip in self.inputs.compute_ips:
            self.logger.info('Starting Vrouter Service')
            self.inputs.start_service('contrail-vrouter-agent', [compute_ip],
                                      container='agent')
            sleep(10)
        return True
    # end test_multistep_vm_delete_with_stop_start_service
    
    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter')
    def test_nova_com_sch_restart_with_multiple_vn_vm(self):
        '''
        Description: Test to validate that multiple VM creation and deletion after service restarts.
        Test steps:
                   1. Create multiple VNs and VMs in them.
                   2. Restart the openstack-nova-compute and openstack-nova-scheduler services.
        Pass criteria: The VMs should all be UP and running after the restarts.
        Maintainer : ganeshahv@juniper.net
        '''
        vm1_name = get_random_name('vm_mine')
        vn_name = get_random_name('vn222')
        vn_subnets = ['11.1.1.0/24']
        vn_count_for_test = 20
        if (len(self.inputs.compute_ips) == 1):
            vn_count_for_test = 5
        vm_fixture = self.useFixture(
            create_multiple_vn_and_multiple_vm_fixture(
                connections=self.connections,
                vn_name=vn_name, vm_name=vm1_name, inputs=self.inputs, project_name=self.inputs.project_name,
                subnets=vn_subnets, vn_count=vn_count_for_test, vm_count=1, subnet_count=1, image_name='cirros',
                flavor='m1.tiny'))
        time.sleep(100)
        try:
            assert vm_fixture.verify_vms_on_setup()
            assert vm_fixture.verify_vns_on_setup()
        except Exception as e:
            self.logger.exception("Got exception as %s" % (e))

        compute_ip = []
        for vmobj in list(vm_fixture.vm_obj_dict.values()):
            vm_host_ip = vmobj.vm_node_ip
            if vm_host_ip not in compute_ip:
                compute_ip.append(vm_host_ip)
        self.inputs.restart_service('openstack-nova-compute', compute_ip,
                                    container='nova-compute')
        self.inputs.restart_service('openstack-nova-scheduler', compute_ip,
                                    container='nova-scheduler')
        sleep(30)
        for vmobj in list(vm_fixture.vm_obj_dict.values()):
            assert vmobj.verify_on_setup()
        return True
    # end test_nova_com_sch_restart_with_multiple_vn_vm

    @retry(delay=5, tries=30)
    def verification_after_process_restart_in_policy_between_vns(self):
        result=True
        try:
            self.analytics_obj.verify_process_and_connection_infos_agent()
            self.analytics_obj.verify_process_and_connection_infos_control_node()
            self.analytics_obj.verify_process_and_connection_infos_config()
        except:
            result=False
        return result
    
    @test.attr(type=['cb_sanity', 'sanity'])
    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter',address_family = 'v6')
    def test_process_restart_in_policy_between_vns(self):
        ''' Test to validate that with policy having rule to check icmp fwding between VMs on different VNs , ping between VMs should pass
        with process restarts
            1. Pick 2 VN's from resource pool which has one VM each
            2. Create policy with icmp allow rule between those VN's and bind it networks
            3. Ping from one VM to another VM
            4. Restart process 'vrouter' and 'control' on setup
            5. Ping again between VM's after process restart
        Pass criteria: Step 2,3,4 and 5 should pass
        '''
        vn1_name = get_random_name('vn1')
        vn1_subnets = ["192.168.1.0/24"]
        vn2_name = get_random_name('vn2')
        vn2_subnets = ["192.168.2.0/24"]
        policy1_name = 'policy1'
        policy2_name = 'policy2'
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': vn1_name,
                'dest_network': vn2_name,
            },
        ]
        rev_rules = [
            {  
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': vn2_name,
                'dest_network': vn1_name,
            },
        ]
        policy1_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy1_name, rules_list=rules, inputs=self.inputs,
                connections=self.connections))
        policy2_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy2_name, 
                rules_list=rev_rules, inputs=self.inputs,
                connections=self.connections))
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets, option='contrail')
        assert vn1_fixture.verify_on_setup()
        vn1_fixture.bind_policies(
            [policy1_fixture.policy_fq_name], vn1_fixture.vn_id)
        self.addCleanup(vn1_fixture.unbind_policies,
                        vn1_fixture.vn_id, [policy1_fixture.policy_fq_name])
        vn2_fixture = self.create_vn(vn2_name, vn2_subnets, option='contrail')
        assert vn2_fixture.verify_on_setup()
        vn2_fixture.bind_policies(
            [policy2_fixture.policy_fq_name], vn2_fixture.vn_id)
        self.addCleanup(vn2_fixture.unbind_policies,
                        vn2_fixture.vn_id, [policy2_fixture.policy_fq_name])
        vn1_vm1_name = get_random_name('vn1_vm1')
        vn2_vm1_name = get_random_name('vn2_vm1')
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name)
        vm2_fixture = self.create_vm(vn2_fixture, vn2_vm1_name)
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip)

        for compute_ip in self.inputs.compute_ips:
            if compute_ip in self.inputs.dpdk_ips:
                self.inputs.stop_service('contrail-vrouter-agent', [compute_ip],
                                         container='agent')
                self.inputs.restart_service('contrail-vrouter-agent-dpdk', [compute_ip],
                                            container='agent-dpdk')
                self.inputs.start_service('contrail-vrouter-agent', [compute_ip],
                                          container='agent')
            else:
                self.inputs.restart_service('contrail-vrouter-agent', [compute_ip],
                                        container='agent')
        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('contrail-control', [bgp_ip],
                                        container='control')
        for cfgm_ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('contrail-api', [cfgm_ip],
                                        container='api-server')

        # Wait for cluster to be stable
        cs_obj = ContrailStatusChecker(self.inputs)
        clusterstatus, error_nodes = cs_obj.wait_till_contrail_cluster_stable()
        assert clusterstatus, (
            'Hash of error nodes and services : %s' % (error_nodes))

        assert self.verification_after_process_restart_in_policy_between_vns()
        for cfgm_name in self.inputs.cfgm_names:
            assert self.analytics_obj.verify_cfgm_uve_module_state\
                        (self.inputs.collector_names[0],
                        cfgm_name,'contrail-api')

        vn1_vm2_name = get_random_name('vn1_vm2')
        vn2_vm2_name = get_random_name('vn2_vm2')

        vn3_name = get_random_name('vn3')
        vn3_subnets = ["192.168.4.0/24"]
        vn3_fixture = self.create_vn(vn3_name, vn3_subnets, option='contrail')
        assert vn1_fixture.verify_on_setup()

        vm3_fixture = self.create_vm(vn1_fixture, vn1_vm2_name)
        assert vm3_fixture.verify_on_setup()
        vm4_fixture = self.create_vm(vn2_fixture, vn2_vm2_name)
        assert vm4_fixture.verify_on_setup()
        vm3_fixture.wait_till_vm_is_up()
        vm4_fixture.wait_till_vm_is_up()
        assert vm3_fixture.ping_with_certainty(vm4_fixture.vm_ip)

# end test_process_restart_in_policy_between_vns
    
    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter',address_family = 'v6')
    def test_process_restart_with_multiple_vn_vm(self):
        '''
        Description: Test to validate that multiple VM creation and deletion after service restarts.
        Test steps:
                   1. Create multiple VNs and VMs in them.
                   2. Restart the contrail-vrouter-agent  service.
        Pass criteria: The VMs should all be UP and running after the restarts.
        Maintainer : ganeshahv@juniper.net
        '''
        vm1_name = 'vm_mine'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_count_for_test = 20
        if (len(self.inputs.compute_ips) == 1):
            vn_count_for_test = 10
        if self.inputs.is_ci_setup():
            vn_count_for_test = 3
        vm_fixture = self.useFixture(
            create_multiple_vn_and_multiple_vm_fixture(
                connections=self.connections,
                vn_name=vn_name, vm_name=vm1_name, inputs=self.inputs, project_name=self.inputs.project_name,
                subnets=vn_subnets, vn_count=vn_count_for_test, vm_count=1, subnet_count=1, image_name='cirros',
                flavor='m1.tiny'))
        time.sleep(100)
        try:
            assert vm_fixture.wait_till_vms_are_up()
            assert vm_fixture.verify_vns_on_setup()
        except Exception as e:
            self.logger.exception("Got exception as %s" % (e))
        compute_ip = []
        for vmobj in list(vm_fixture.vm_obj_dict.values()):
            vm_host_ip = vmobj.vm_node_ip
            if vm_host_ip not in compute_ip:
                compute_ip.append(vm_host_ip)
        self.inputs.restart_service('contrail-vrouter-agent', compute_ip,
									container='agent')
        sleep(50)
        for vmobj in list(vm_fixture.vm_obj_dict.values()):
            assert vmobj.verify_on_setup()
        return True
    #end test_process_restart_with_multiple_vn_vm
    
    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter',address_family = 'v6')
    def test_kill_service_verify_core_generation(self):
        '''
        Description: Test to Validate core is generated for services on SIGQUIT
        Test steps:
                   1. Issue commands to generate cores for multipe process.
        Pass criteria: Verify core generation is successful.
        Maintainer : sandipd@juniper.net
        '''
        compute_ip = self.inputs.compute_ips[0]
        compute_user = self.inputs.host_data[compute_ip]['username']
        compute_pwd = self.inputs.host_data[compute_ip]['password']
        cfgm_ip = self.inputs.cfgm_ips[0]
        cfgm_user = self.inputs.host_data[cfgm_ip]['username']
        cfgm_pwd = self.inputs.host_data[cfgm_ip]['password']
        collector_ip = self.inputs.collector_ips[0]
        collector_user = self.inputs.host_data[collector_ip]['username']
        collector_pwd = self.inputs.host_data[collector_ip]['password']
        control_ip = self.inputs.bgp_ips[0]
        control_user = self.inputs.host_data[control_ip]['username']
        control_pwd = self.inputs.host_data[control_ip]['password']
        result = True
        err_msg = []
        # Format <service_name> : [<process_name>,
        # <role_on_which_process_running>]
        service_list = {
            'contrail-control': 'control',
            'contrail-vrouter-agent': 'compute',
            'contrail-query-engine': 'collector',
            'contrail-collector': 'collector',
            'contrail-analytics-api': 'collector',
            'contrail-api': 'cfgm',
            'contrail-svc-monitor': 'cfgm'
        }

        for service, role in service_list.items():
            cmd = 'service %s status |  awk \"{print $4}\" | cut -f 1 -d\',\'' % service
            self.logger.info("service:%s, role:%s" % (service, role))
            if role == 'cfgm':
                container = 'controller'
                login_ip = cfgm_ip
                login_user = cfgm_user
                login_pwd = cfgm_pwd
            elif role == 'compute':
                container = 'compute'
                login_ip = compute_ip
                login_user = compute_user
                login_pwd = compute_pwd
            elif role == 'control':
                container = 'controller'
                login_ip = control_ip
                login_user = control_user
                login_pwd = control_pwd
            elif role == 'collector':
                container = 'analytics'
                login_ip = collector_ip
                login_user = collector_user
                login_pwd = collector_pwd
            else:
                self.logger.error("invalid role:%s" % role)
                result = result and False
                assert result, "Invalid role:%s specified for service:%s" % (
                    role, service)

            pid = self.inputs.run_cmd_on_server(login_ip,cmd,login_user,
                                                   login_pwd,container=container)
            pid = int(pid.split(' ')[-1])
            self.logger.info("service:%s, pid:%s" % (service, pid))
            cmd1 = 'kill -3 %s' % pid
            output = self.inputs.run_cmd_on_server(login_ip,cmd1,login_user,
                                                   login_pwd,container=container)
            cmd_list_cores = "ls -lrt /var/crashes/core.*%s*" % (pid)
            
            sleep(10)
            output =  self.inputs.run_cmd_on_server(login_ip,cmd_list_cores,login_user,
                                                   login_pwd,container=container)
            if "No such file or directory" in output:
                self.logger.error(
                    "core is not generated for service:%s" % service)
                err_msg.append("core is not generated for service:%s" %
                               service)
                result = result and False
            else:
                # remove core after generation
                cmd_rm_cores = "rm -f /var/crashes/core.*%s*" % (pid)
                output =  self.inputs.run_cmd_on_server(login_ip,cmd_rm_cores,login_user,
                                                   login_pwd,container=container)
        assert result, "core generation validation test failed: %s" % err_msg
        return True
    # end test_kill_service_verify_core_generation


    @test.attr(type=['cb_sanity', 'sanity'])
    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter',address_family = 'v6')
    def test_control_node_switchover(self):
        ''' Stop the control node and check peering with agent fallback to other control node.
            1. Pick one VN from respource pool which has 2 VM's in it
            2. Verify ping between VM's
            3. Find active control node in cluster by agent inspect
            4. Stop control service on active control node
            5. Verify agents are connected to new active control-node using xmpp connections
            6. Bring back control service on previous active node
            7. Verify ping between VM's again after bringing up control serveice
        Pass criteria: Step 2,5 and 7 should pass
        '''
        if len(set(self.inputs.bgp_ips)) < 2:
            self.logger.info(
                "Skipping Test. At least 2 control node required to run the test")
            raise self.skipTest(
                "Skipping Test. At least 2 control node required to run the test")
        result = True
        vn1_name = get_random_name('vn1')
        vn1_subnets = ['192.168.1.0/24']
        vn1_vm1_name = get_random_name('vn1_vm1')
        vn1_vm2_name = get_random_name('vn1_vm2')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name)
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name)
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)
        assert vm2_fixture.ping_to_ip(vm1_fixture.vm_ip)

        # Figuring the active control node
        active_controller = None
        self.agent_inspect = self.connections.agent_inspect
        inspect_h = self.agent_inspect[vm1_fixture.vm_node_ip]
        agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                active_controller = entry['controller_ip']
        active_controller_host_ip = self.inputs.host_data[
            active_controller]['host_ip']
        self.logger.info('Active control node from the Agent %s is %s' %
                         (vm1_fixture.vm_node_ip, active_controller_host_ip))

        # Stop on Active node
        self.logger.info('Stoping the Control service in  %s' %
                         (active_controller_host_ip))
        self.inputs.stop_service(
            'contrail-control', [active_controller_host_ip],
            container='control')
        sleep(5)

        # Check the control node shifted to other control node
        new_active_controller = None
        new_active_controller_state = None
        inspect_h = self.agent_inspect[vm1_fixture.vm_node_ip]
        agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            if entry['cfg_controller'] == 'Yes':
                new_active_controller = entry['controller_ip']
                new_active_controller_state = entry['state']
        new_active_controller_host_ip = self.inputs.host_data[
            new_active_controller]['host_ip']
        self.logger.info('Active control node from the Agent %s is %s' %
                         (vm1_fixture.vm_node_ip, new_active_controller_host_ip))
        if new_active_controller_host_ip == active_controller_host_ip:
            self.logger.error(
                'Control node switchover fail. Old Active controlnode was %s and new active control node is %s' %
                (active_controller_host_ip, new_active_controller_host_ip))
            result = False

        if new_active_controller_state != 'Established':
            self.logger.error(
                'Agent does not have Established XMPP connection with Active control node')
            result = result and False

        # Start the control node service again
        self.logger.info('Starting the Control service in  %s' %
                         (active_controller_host_ip))
        self.inputs.start_service(
            'contrail-control', [active_controller_host_ip],
            container='control')

        # Check the BGP peering status from the currently active control node
        sleep(5)
        as4_ext_routers_dict = dict(self.inputs.as4_ext_routers)
        cn_bgp_entry = self.cn_inspect[
            new_active_controller_host_ip].get_cn_bgp_neigh_entry()
        for entry in cn_bgp_entry:
            if entry['peer'] in as4_ext_routers_dict:
                continue
            if entry['state'] != 'Established':
                result = result and False
                self.logger.error(
                    'With Peer %s peering is not Established. Current State %s ' %
                    (entry['peer'], entry['state']))

        assert vm1_fixture.verify_on_setup(), 'VM Verification failed'
        assert vm2_fixture.verify_on_setup(), 'VM Verification failed'
        # Check the ping
        self.logger.info('Checking the ping between the VM again')
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)
        assert vm2_fixture.ping_to_ip(vm1_fixture.vm_ip)

        if not result:
            self.logger.error('Switchover of control node failed')
            assert result
        return True

    # end test_control_node_switchover

    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter',address_family = 'v6')
    def test_max_vm_flows(self):
        ''' Test to validate setting up of the max_vm_flows parameter in agent
            config file has expected effect on the flows in the system.
            1. Set VM flow cache time and max_vm_flows to 0.1% of max system
               flows(512K) i.e about 500 flows
            2. Create 2 VN's and connect them using a policy.
            3. Launch 2 VM's in the respective VN's.
            4. Start traffic with connections exceeding the VM flow limit
            5. Check the flows are limited to about 500 flows
        '''
        result = True

        # Set VM flow cache time to 20 and max_vm_flows to 0.1% of max system
        # flows(512K).
        comp_node_fixt = {}
        flow_cache_timeout = 20
        max_system_flows = 0
        max_vm_flows = 0.1
        compute_ips = [self.inputs.compute_ips[0], self.inputs.compute_ips[0]]
        compute_names = [self.inputs.compute_names[0], self.inputs.compute_names[0]]
        if len(self.inputs.compute_ips) > 1:
            compute_ips[1] = self.inputs.compute_ips[1]
            compute_names[1] = self.inputs.compute_names[1]

        for cmp_node in compute_ips:
            comp_node_fixt[cmp_node] = self.useFixture(ComputeNodeFixture(
                self.connections, cmp_node))
            comp_node_fixt[cmp_node].set_flow_aging_time(
                flow_cache_timeout)
            comp_node_fixt[cmp_node].get_config_per_vm_flow_limit()
            comp_node_fixt[cmp_node].set_per_vm_flow_limit(
                max_vm_flows)
            if max_system_flows < comp_node_fixt[
                cmp_node].max_system_flows:
                max_system_flows = comp_node_fixt[
                    cmp_node].max_system_flows
        self.addCleanup(self.cleanup_test_max_vm_flows_vrouter_config,
            compute_ips,
            comp_node_fixt)

        # Define resources for this test.
        vn1_name = get_random_name('VN1')
        vn1_subnets = ['10.1.1.0/24']
        vn2_name = get_random_name('VN2')
        vn2_subnets = ['10.2.1.0/24']
        vn1_vm1_name = get_random_name('VM1')
        vn2_vm2_name = get_random_name('VM2')
        policy1_name = 'policy1'
        policy2_name = 'policy2'
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any',
                'source_network': vn1_name,
                'dest_network': vn2_name,
            },
        ]
        rev_rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any',
                'source_network': vn2_name,
                'dest_network': vn1_name,
            },
        ]

        # Create 2 VN's and connect them using a policy.
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        assert vn1_fixture.verify_on_setup()
        vn2_fixture = self.create_vn(vn2_name, vn2_subnets)
        assert vn2_fixture.verify_on_setup()

        policy1_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy1_name,
                rules_list=rules, inputs=self.inputs,
                connections=self.connections))
        policy2_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy2_name,
                rules_list=rev_rules, inputs=self.inputs,
                connections=self.connections))

        vn1_fixture.bind_policies(
            [policy1_fixture.policy_fq_name], vn1_fixture.vn_id)
        self.addCleanup(vn1_fixture.unbind_policies,
                        vn1_fixture.vn_id, [policy1_fixture.policy_fq_name])
        vn2_fixture.bind_policies(
            [policy2_fixture.policy_fq_name], vn2_fixture.vn_id)
        self.addCleanup(vn2_fixture.unbind_policies,
                        vn2_fixture.vn_id, [policy2_fixture.policy_fq_name])

        # Launch 2 VM's in the respective VN's.
        vm1_fixture = self.create_vm(vn1_fixture,vm_name=vn1_vm1_name,
                flavor='contrail_flavor_small', image_name='ubuntu-traffic',
                node_name=compute_names[0])
        vm2_fixture = self.create_vm(vn2_fixture,vm_name=vn2_vm2_name,
                flavor='contrail_flavor_small', image_name='ubuntu-traffic',
                node_name=compute_names[1])
        assert vm1_fixture.wait_till_vm_is_up(), 'VM1 does not seem to be up'
        assert vm2_fixture.wait_till_vm_is_up(), 'VM2 does not seem to be up'
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip, count=1), \
            'Ping from VM1 to VM2 FAILED'

        # Set num_flows to fixed, smaller value but > 1% of
        # system max flows
        max_system_flows = max_system_flows
        vm_flow_limit = int((max_vm_flows/100.0)*max_system_flows)
        num_flows = vm_flow_limit + 30
        interval = 'u10000'
        proto = 'udp'
        # Try UDP echo 
        dest_port = 7

        hping_h = Hping3(vm1_fixture, vm2_fixture.vm_ip,
                         destport=dest_port,
                         count=num_flows,
                         interval=interval,
                         udp=True)
        time.sleep(flow_cache_timeout*2)
        # No need to stop hping
        hping_h.start(wait=False)
        time.sleep(5)

        computes = [comp_node_fixt[vm1_fixture.vm_node_ip],
                    comp_node_fixt[vm2_fixture.vm_node_ip]]
        for compute in computes:
            (fwd_flow_cnt, rev_flow_cnt) = compute.get_flow_count(
                source_ip=vm1_fixture.vm_ip,
                dest_ip=vm2_fixture.vm_ip,
                dest_port=dest_port,
                proto=proto)
            current_flow_cnt = fwd_flow_cnt + rev_flow_cnt
            msg = 'VM flow count : Expected:%s, Seen: %s' % (vm_flow_limit,
                                                           current_flow_cnt)
            assert is_almost_same(current_flow_cnt, vm_flow_limit, 25), msg
            self.logger.info('On compute %s, %s..OK' % (compute.ip, msg))
    # end test_max_vm_flows

    @test.attr(type=['sanity', 'vcenter_compute', 'vcenter'])
    @skip_because(dpdk_cluster=True)
    @preposttest_wrapper
    def test_underlay_broadcast_traffic_handling(self):
        ''' Test the underlay brocast traffic handling by vrouter. (Bug-1545229).
            1. Send broadcast traffic from one compute node.
            2. Other compute in same subnet should receive that traffic.
            3. Receiving compute should treat this traffic as underlay. 
            4. Compute should not replicate the packet and send the copy back.  
        Pass criteria: Step 3-4 should pass
        Maintainer : chhandak@juniper.net
        '''
        if (len(self.inputs.compute_ips) < 2):
             raise self.skipTest(
                "Skipping Test. At least 2 compute node required to run the test")
        result = True

        # Find ignore brocast exiting value 
        ignore_broadcasts={}
        cmd='cat /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts'
        for item in self.inputs.compute_ips:
            ignore_broadcasts[item]=self.inputs.run_cmd_on_server(
                item, cmd,
                self.inputs.host_data[item]['username'],
                self.inputs.host_data[item]['password'])

        # Set ignore brocast to false 
        cmd='echo "0" > /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts'
        for item in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(
                item, cmd,
                self.inputs.host_data[item]['username'],
                self.inputs.host_data[item]['password'])

        # Find the Brocast address from first compute
        cmd='ifconfig | grep %s' %(self.inputs.host_data[item]['host_control_ip'])
        output=self.inputs.run_cmd_on_server(
                item, cmd,
                self.inputs.host_data[item]['username'],
                self.inputs.host_data[item]['password'])
        try:
            broadcast_address=output.split(" ")[3].split(":")[1] #Handling for ubuntu
        except Exception as e:
            broadcast_address = output.split(" ")[-1] #Handling for centos

        # Start tcpdump on receiving compute
        inspect_h = self.agent_inspect[self.inputs.compute_ips[1]]
        comp_intf = inspect_h.get_vna_interface_by_type('eth')
        for intf in comp_intf:
            if 'crypt' not in intf:
                comp_intf = intf
                break
        self.logger.info('Agent interface name: %s' % comp_intf)
        compute_ip = self.inputs.compute_ips[1]
        compute_user = self.inputs.host_data[self.inputs.compute_ips[1]]['username']
        compute_password = self.inputs.host_data[self.inputs.compute_ips[1]]['password']
        filters = "host %s" %(broadcast_address)

        (session, pcap) = start_tcpdump_for_intf(compute_ip, compute_user,
            compute_password, comp_intf, filters, self.logger)

        sleep(5)

        # Ping broadcast address
        self.logger.info(
            'Pinging broacast address %s from compute %s' %(broadcast_address,\
                                     self.inputs.host_data[self.inputs.compute_ips[0]]['host_control_ip']))
        packet_count = 10
        cmd='ping -c %s -b %s' %(packet_count, broadcast_address)
        output=self.inputs.run_cmd_on_server(
                self.inputs.compute_ips[0], cmd,
                self.inputs.host_data[item]['username'],
                self.inputs.host_data[item]['password'],
                container='agent')
        sleep(5)
        
        # Stop tcpdump
        stop_tcpdump_for_intf(session, pcap, self.logger)

        # Set back the ignore_broadcasts to original value
        for item in self.inputs.compute_ips:
            cmd='echo "%s" > /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts' %(ignore_broadcasts[item])
            self.inputs.run_cmd_on_server(
                item, cmd,
                self.inputs.host_data[item]['username'],
                self.inputs.host_data[item]['password'])

        # Analyze pcap
        assert verify_tcpdump_count(self, session, pcap, exp_count=packet_count), "There should only be %s\
                                     packet from source %s on compute %s" %(packet_count, broadcast_address, compute_ip)
        self.logger.info(
            'Packet count matched: Compute %s has receive only %s packet from source IP %s.\
                                      No duplicate packet seen' %(compute_ip, packet_count, broadcast_address))
        return result 

    # end test_underlay_brodcast_traffic_handling 

# end TestBasicVMVN0

class TestMetadataSSL(BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(TestMetadataSSL, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestMetadataSSL, cls).tearDownClass()

    def restore_cert_key_agent(self):
        cmd='cp /etc/contrail/ssl/certs/server.pem.bkup /etc/contrail/ssl/certs/server.pem;\
             cp /etc/contrail/ssl/private/server-privkey.pem.bkup /etc/contrail/ssl/private/server-privkey.pem'
        for compute_node in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_node, cmd)
    # end restore_cert_key_agent

    def restore_cert_key_nova(self):
        if self.inputs.get_build_sku() in ['mitaka', 'newton']:
            cmd='cp /etc/nova/ssl/private/novakey.pem.bkup /etc/nova/ssl/private/novakey.pem;\
                 cp /etc/nova/ssl/certs/nova.pem.bkup /etc/nova/ssl/certs/nova.pem'
        else:
            cmd='docker exec -it nova-api cp /etc/nova/ssl/private/novakey.pem.bkup /etc/nova/ssl/private/novakey.pem;\
                 docker exec -it nova-api cp /etc/nova/ssl/certs/nova.pem.bkup /etc/nova/ssl/certs/nova.pem'
        for openstack_node in self.inputs.openstack_ips:
            self.inputs.run_cmd_on_server(openstack_node, cmd)
    # end restore_cert_key_nova

    def restore_conf(self):
        if self.inputs.get_build_sku() in ['mitaka', 'newton']:
            cmd='cp /etc/nova/nova.conf.bkup /etc/nova/nova.conf; service nova-api restart'
        else:
            cmd='docker exec -it nova-api cp /etc/nova/nova.conf.bkup /etc/nova/nova.conf;\
                 docker exec -it nova-api service nova-api restart'
        for openstack_node in self.inputs.openstack_ips:
            self.inputs.run_cmd_on_server(openstack_node, cmd)

        cmd='cp /etc/contrail/contrail-vrouter-agent.conf.bkup\
             /etc/contrail/contrail-vrouter-agent.conf;\
             service contrail-vrouter-agent restart'
        for compute_node in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_node, cmd)
    # end restore_conf

    def metadata_service_test(self):
        '''
        Description: Test to validate metadata service on VM creation.

               1.Verify from global-vrouter-config if metadata configures or not - fails otherwise
               2.Create a shell script which writes  'hello world ' in a file in /tmp and save the script on the nova api node
               3.Create a vm with userdata pointing to that script - script should get executed during vm boot up
               4.Go to the vm and verify if the file with 'hello world ' written saved in /tmp of the vm - fails otherwise
            Maintainer: sandipd@juniper.net
        '''

        gvrouter_cfg_obj = self.api_s_inspect.get_global_vrouter_config()
        ln_svc = gvrouter_cfg_obj.get_link_local_service()
        if ln_svc:
            self.logger.info(
                "Metadata configured in global_vrouter_config as %s" %
                (str(ln_svc)))
        else:
            self.logger.warn(
                "Metadata NOT configured in global_vrouter_config")
            result = False
            assert result
            return True

        text = """#!/bin/sh
echo "Hello World.  The time is now $(date -R)!" | tee /tmp/output.txt
               """
        try:
            with open("/tmp/metadata_script.txt", "w") as f:
                f.write(text)
        except Exception as e:
            self.logger.exception(
                "Got exception while creating /tmp/metadata_script.txt as %s" % (e))

        img_name = self.inputs.get_ci_image() or 'ubuntu-traffic'
        vn_name = get_random_name('vn2_metadata')
        vm1_name = get_random_name('vm_in_vn2_metadata')
        vn_fixture = self.create_vn(vn_name=vn_name, vn_subnets = ['10.1.1.0/24'])#, af='v4')
        vm1_fixture = self.create_vm(vn_fixture=vn_fixture, vm_name=vm1_name,
                                     image_name=img_name,
                                     userdata='/tmp/metadata_script.txt')
        assert vm1_fixture.verify_on_setup()
        assert vm1_fixture.wait_till_vm_is_up()

        cmd = 'ls /tmp/'
        result = False
        for i in range(3):
            self.logger.debug("Retry %s" % (i))
            ret = vm1_fixture.run_cmd_on_vm(cmds=[cmd])
            self.logger.debug("ret : %s" % (ret))
            for elem in list(ret.values()):
                if 'output.txt' in elem:
                    result = True
                    break
            if result:
                break
            time.sleep(2)
        if not result:
            self.logger.warn(
                "metadata_script.txt did not get executed in the vm")
            self.logger.debug('%s' %vm1_fixture.get_console_output())
        else:
            self.logger.debug("Printing the output.txt :")
            cmd = 'cat /tmp/output.txt'
            ret = vm1_fixture.run_cmd_on_vm(cmds=[cmd])
            self.logger.info("%s" % (list(ret.values())))
            for elem in list(ret.values()):
                if 'Hello World' in elem:
                    result = True
                else:
                    self.logger.warn(
                        "metadata_script.txt did not get executed in the vm...output.txt does not contain proper output")
                    result = False
        assert result
        return True
    #end metadata_service_test 

    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter', metadata_ssl = 'False')
    def test_metadata_ssl_service_without_ca_cert(self):
        '''
        Description: Test to validate metadata ssl service on VM creation without ca cert.
            Maintainer: ritam@juniper.net
        '''

        #Back up conf files.
        if self.inputs.get_build_sku() in ['mitaka', 'newton']:
            cmd='cp /etc/nova/nova.conf /etc/nova/nova.conf.bkup'
        else:
            cmd='docker exec -it nova-api cp /etc/nova/nova.conf /etc/nova/nova.conf.bkup'
        for openstack_node in self.inputs.openstack_ips:
            self.inputs.run_cmd_on_server(openstack_node, cmd)

        cmd='cp /etc/contrail/contrail-vrouter-agent.conf /etc/contrail/contrail-vrouter-agent.conf.bkup'
        for compute_node in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_node, cmd)

        #Add cleanup routine.
        self.addCleanup(self.restore_conf)

        #Change config
        if self.inputs.get_build_sku() in ['mitaka', 'newton']:
            cmd='openstack-config --del /etc/nova/nova.conf DEFAULT ssl_ca_file;\
                 openstack-config --del /etc/nova/nova.conf ssl ca_file;\
                 service nova-api restart'
        else:
            cmd='openstack-config --del /etc/kolla/nova-api/nova.conf DEFAULT ssl_ca_file;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf ssl ca_file;\
                 docker restart nova-api'
        for openstack_node in self.inputs.openstack_ips:
            self.inputs.run_cmd_on_server(openstack_node, cmd)

        #Validate metadata ssl service.
        try:
            self.metadata_service_test()
            self.logger.info('Metadata ssl test passed without ca cert.')
            result=True
        except Exception as e:
            self.logger.error('Metadata ssl test failed without ca cert.')
            result=False
        return result
    # end test_metadata_ssl_service_without_ca_cert

    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter', metadata_ssl = 'False')
    def test_metadata_failure_with_ssl_disabled_on_nova(self):
        '''
        Description: Test to validate metadata ssl service failure on VM creation without
                     ssl encryption configuration on nova side.
            Maintainer: ritam@juniper.net
        '''

        #Back up conf files.
        if self.inputs.get_build_sku() in ['mitaka', 'newton']:
            cmd='cp /etc/nova/nova.conf /etc/nova/nova.conf.bkup'
        else:
            cmd='docker exec -it nova-api cp /etc/nova/nova.conf /etc/nova/nova.conf.bkup'
        for openstack_node in self.inputs.openstack_ips:
            self.inputs.run_cmd_on_server(openstack_node, cmd)

        cmd='cp /etc/contrail/contrail-vrouter-agent.conf /etc/contrail/contrail-vrouter-agent.conf.bkup'
        for compute_node in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_node, cmd)

        #Add cleanup routine.
        self.addCleanup(self.restore_conf)

        #Change config
        if self.inputs.get_build_sku() in ['mitaka', 'newton']:
            cmd='openstack-config --del /etc/nova/nova.conf DEFAULT enabled_ssl_apis;\
                 openstack-config --del /etc/nova/nova.conf DEFAULT nova_metadata_protocol;\
                 openstack-config --del /etc/nova/nova.conf DEFAULT nova_metadata_insecure;\
                 openstack-config --del /etc/nova/nova.conf DEFAULT ssl_cert_file;\
                 openstack-config --del /etc/nova/nova.conf DEFAULT ssl_key_file;\
                 openstack-config --del /etc/nova/nova.conf DEFAULT ssl_ca_file;\
                 openstack-config --del /etc/nova/nova.conf ssl cert_file;\
                 openstack-config --del /etc/nova/nova.conf ssl key_file;\
                 openstack-config --del /etc/nova/nova.conf ssl ca_file;\
                 service nova-api restart'
        else:
            cmd='openstack-config --del /etc/kolla/nova-api/nova.conf DEFAULT enabled_ssl_apis;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf DEFAULT nova_metadata_protocol;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf DEFAULT nova_metadata_insecure;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf DEFAULT ssl_cert_file;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf DEFAULT ssl_key_file;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf DEFAULT ssl_ca_file;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf ssl cert_file;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf ssl key_file;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf ssl ca_file;\
                 docker restart nova-api'
        for openstack_node in self.inputs.openstack_ips:
            self.inputs.run_cmd_on_server(openstack_node, cmd)

        #Validate metadata ssl service.
        try:
            self.metadata_service_test()
            self.logger.info('Metadata ssl test passed without any ssl config in nova.')
            result=False
        except Exception as e:
            self.logger.error('Metadata ssl test failed without any ssl config in nova.')
            result=True
        return result
    # end test_metadata_failure_with_ssl_disabled_on_nova

    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter', metadata_ssl = 'False')
    def test_metadata_failure_without_cert_key_in_nova(self):
        '''
        Description: Test to validate metadata ssl service failure on VM creation without
                     cert and key file configuration on nova side.
            Maintainer: ritam@juniper.net
        '''

        #Back up conf files.
        if self.inputs.get_build_sku() in ['mitaka', 'newton']:
            cmd='cp /etc/nova/nova.conf /etc/nova/nova.conf.bkup'
        else:
            cmd='docker exec -it nova-api cp /etc/nova/nova.conf /etc/nova/nova.conf.bkup'
        for openstack_node in self.inputs.openstack_ips:
            self.inputs.run_cmd_on_server(openstack_node, cmd)

        cmd='cp /etc/contrail/contrail-vrouter-agent.conf /etc/contrail/contrail-vrouter-agent.conf.bkup'
        for compute_node in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_node, cmd)

        #Add cleanup routine.
        self.addCleanup(self.restore_conf)

        #Change config
        if self.inputs.get_build_sku() in ['mitaka', 'newton']:
            cmd='openstack-config --del /etc/nova/nova.conf DEFAULT ssl_cert_file;\
                 openstack-config --del /etc/nova/nova.conf DEFAULT ssl_key_file;\
                 openstack-config --del /etc/nova/nova.conf ssl cert_file;\
                 openstack-config --del /etc/nova/nova.conf ssl key_file;\
                 service nova-api restart'
        else:
            cmd='openstack-config --del /etc/kolla/nova-api/nova.conf DEFAULT ssl_cert_file;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf DEFAULT ssl_key_file;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf ssl cert_file;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf ssl key_file;\
                 docker restart nova-api'
        for openstack_node in self.inputs.openstack_ips:
            self.inputs.run_cmd_on_server(openstack_node, cmd)

        #Validate metadata ssl service.
        try:
            self.metadata_service_test()
            self.logger.info('Metadata ssl test passed with wrong cert file content in nova.')
            result=False
        except Exception as e:
            self.logger.error('Metadata ssl test failed with wrong cert file content in nova.')
            result=True
        return result
    # end test_metadata_failure_without_cert_key_in_nova

    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter', metadata_ssl = 'False')
    def test_metadata_failure_with_wrong_cert_in_nova(self):
        '''
        Description: Test to validate metadata ssl service failure on VM creation with
                     wrong cert file contents on nova side.
            Maintainer: ritam@juniper.net
        '''

        #Back up cert key files.
        if self.inputs.get_build_sku() in ['mitaka', 'newton']:
            cmd='cp /etc/nova/ssl/private/novakey.pem /etc/nova/ssl/private/novakey.pem.bkup;\
                 cp /etc/nova/ssl/certs/nova.pem /etc/nova/ssl/certs/nova.pem.bkup'
        else:
            cmd='docker exec -it nova-api cp /etc/nova/ssl/private/novakey.pem /etc/nova/ssl/private/novakey.pem.bkup;\
                 docker exec -it nova-api cp /etc/nova/ssl/certs/nova.pem /etc/nova/ssl/certs/nova.pem.bkup'
        for openstack_node in self.inputs.openstack_ips:
            self.inputs.run_cmd_on_server(openstack_node, cmd)

        #Add cleanup routine.
        self.addCleanup(self.restore_cert_key_nova)

        #Change ciert file
        if self.inputs.get_build_sku() in ['mitaka', 'newton']:
            cmd="sed -i '8i this ia a garbage value inserted in line 8' /etc/nova/ssl/private/novakey.pem"
        else:
            cmd="sed -i '8i this ia a garbage value inserted in line 8' /etc/nova/ssl/private/novakey.pem"
        for openstack_node in self.inputs.openstack_ips:
            self.inputs.run_cmd_on_server(openstack_node, cmd)

        #Validate metadata ssl service.
        try:
            self.metadata_service_test()
            self.logger.info('Metadata ssl test passed with wrong key file content in nova.')
            result=False
        except Exception as e:
            self.logger.error('Metadata ssl test failed with wrong key file content in nova.')
            result=True
        return result
    # end test_metadata_failure_with_wrong_cert_in_nova

    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter', metadata_ssl = 'False')
    def test_metadata_failure_with_wrong_key_in_nova(self):
        '''
        Description: Test to validate metadata ssl service failure on VM creation with
                     wrong key file contents on nova side.
            Maintainer: ritam@juniper.net
        '''

        #Back up cert key files.
        if self.inputs.get_build_sku() in ['mitaka', 'newton']:
            cmd='cp /etc/nova/ssl/private/novakey.pem /etc/nova/ssl/private/novakey.pem.bkup;\
                 cp /etc/nova/ssl/certs/nova.pem /etc/nova/ssl/certs/nova.pem.bkup'
        else:
            cmd='docker exec -it nova-api cp /etc/nova/ssl/private/novakey.pem /etc/nova/ssl/private/novakey.pem.bkup;\
                 docker exec -it nova-api cp /etc/nova/ssl/certs/nova.pem /etc/nova/ssl/certs/nova.pem.bkup'
        for openstack_node in self.inputs.openstack_ips:
            self.inputs.run_cmd_on_server(openstack_node, cmd)

        #Add cleanup routine.
        self.addCleanup(self.restore_cert_key_nova)

        #Change ciert file
        if self.inputs.get_build_sku() in ['mitaka', 'newton']:
            cmd="sed -i '8i this ia a garbage value inserted in line 8' /etc/nova/ssl/private/novakey.pem"
        else:
            cmd="sed -i '8i this ia a garbage value inserted in line 8' /etc/nova/ssl/private/novakey.pem"
        for openstack_node in self.inputs.openstack_ips:
            self.inputs.run_cmd_on_server(openstack_node, cmd)

        #Validate metadata ssl service.
        try:
            self.metadata_service_test()
            self.logger.info('Metadata ssl test passed without any cert key file config in nova.')
            result=False
        except Exception as e:
            self.logger.error('Metadata ssl test failed without any cert key config in nova.')
            result=True
        return result
    # end test_metadata_failure_with_wrong_key_in_nova

    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter', metadata_ssl = 'False')
    def test_metadata_with_ssl_disabled(self):
        '''
        Description: Test to validate metadata service works with ssl configs
                     disabled on both nova and agent side.
            Maintainer: ritam@juniper.net
        '''

        #Back up conf files.
        if self.inputs.get_build_sku() in ['mitaka', 'newton']:
            cmd='cp /etc/nova/nova.conf /etc/nova/nova.conf.bkup'
        else:
            cmd='docker exec -it nova-api cp /etc/nova/nova.conf /etc/nova/nova.conf.bkup'
        for openstack_node in self.inputs.openstack_ips:
            self.inputs.run_cmd_on_server(openstack_node, cmd)

        cmd='cp /etc/contrail/contrail-vrouter-agent.conf /etc/contrail/contrail-vrouter-agent.conf.bkup'
        for compute_node in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_node, cmd)

        #Add cleanup routine.
        self.addCleanup(self.restore_conf)

        #Change config
        cmd='openstack-config --del /etc/contrail/contrail-vrouter-agent.conf METADATA metadata_use_ssl;\
             openstack-config --del /etc/contrail/contrail-vrouter-agent.conf METADATA metdata_client_cert_type;\
             openstack-config --del /etc/contrail/contrail-vrouter-agent.conf METADATA metadata_client_cert;\
             openstack-config --del /etc/contrail/contrail-vrouter-agent.conf METADATA metadata_client_key;\
             service contrail-vrouter-agent restart'
        for compute_node in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_node, cmd)

        if self.inputs.get_build_sku() in ['mitaka', 'newton']:
            cmd='openstack-config --del /etc/nova/nova.conf DEFAULT enabled_ssl_apis;\
                 openstack-config --del /etc/nova/nova.conf DEFAULT nova_metadata_protocol;\
                 openstack-config --del /etc/nova/nova.conf DEFAULT nova_metadata_insecure;\
                 openstack-config --del /etc/nova/nova.conf DEFAULT ssl_cert_file;\
                 openstack-config --del /etc/nova/nova.conf DEFAULT ssl_key_file;\
                 openstack-config --del /etc/nova/nova.conf DEFAULT ssl_ca_file;\
                 openstack-config --del /etc/nova/nova.conf ssl cert_file;\
                 openstack-config --del /etc/nova/nova.conf ssl key_file;\
                 openstack-config --del /etc/nova/nova.conf ssl ca_file;\
                 service nova-api restart'
        else:
            cmd='openstack-config --del /etc/kolla/nova-api/nova.conf DEFAULT enabled_ssl_apis;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf DEFAULT nova_metadata_protocol;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf DEFAULT nova_metadata_insecure;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf DEFAULT ssl_cert_file;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf DEFAULT ssl_key_file;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf DEFAULT ssl_ca_file;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf ssl cert_file;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf ssl key_file;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf ssl ca_file;\
                 docker restart nova-api'
        for openstack_node in self.inputs.openstack_ips:
            self.inputs.run_cmd_on_server(openstack_node, cmd)

        #Validate metadata ssl service.
        try:
            self.metadata_service_test()
            self.logger.info('Metadata ssl test passed without any ssl encryption.')
            result=True
        except Exception as e:
            self.logger.error('Metadata ssl test failed without any ssl encryption.')
            result=False
        return result
    # end test_metadata_with_ssl_disabled

    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter', metadata_ssl = 'False')
    def test_metadata_with_wrong_cert_in_agent(self):
        '''
        Description: Test to validate metadata service fails with wrong cert
                     contents on agent side.
            Maintainer: ritam@juniper.net
        '''

        #Back up cert key files.
        cmd='cp /etc/contrail/ssl/certs/server.pem /etc/contrail/ssl/certs/server.pem.bkup;\
             cp /etc/contrail/ssl/private/server-privkey.pem /etc/contrail/ssl/private/server-privkey.pem.bkup'
        for compute_node in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_node, cmd)

        #Add cleanup routine.
        self.addCleanup(self.restore_cert_key_agent)

        #Change config
        cmd="sed -i '8i this ia a garbage value inserted in line 8' /etc/contrail/ssl/certs/server.pem"
        for compute_node in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_node, cmd)

        #Validate metadata ssl service.
        try:
            self.metadata_service_test()
            self.logger.info('Metadata ssl test passed with wrong cert on agent.')
            result=False
        except Exception as e:
            self.logger.error('Metadata ssl test failed with wrong cert on agent.')
            result=True
        return result
    # end test_metadata_with_wrong_cert_in_agent

    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter', metadata_ssl = 'False')
    def test_metadata_with_wrong_key_in_agent(self):
        '''
        Description: Test to validate metadata service fails with wrong key
                     contents on agent side.
            Maintainer: ritam@juniper.net
        '''

        #Back up cert key files.
        cmd='cp /etc/contrail/ssl/certs/server.pem /etc/contrail/ssl/certs/server.pem.bkup;\
             cp /etc/contrail/ssl/private/server-privkey.pem /etc/contrail/ssl/private/server-privkey.pem.bkup'
        for compute_node in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_node, cmd)

        #Add cleanup routine.
        self.addCleanup(self.restore_cert_key_agent)

        #Change config
        cmd="sed -i '8i this ia a garbage value inserted in line 8' /etc/contrail/ssl/private/server-privkey.pem"
        for compute_node in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_node, cmd)

        #Validate metadata ssl service.
        try:
            self.metadata_service_test()
            self.logger.info('Metadata ssl test passed with wrong key on agent.')
            result=False
        except Exception as e:
            self.logger.error('Metadata ssl test failed with wrong key on agent.')
            result=True
        return result
    # end test_metadata_with_wrong_key_in_agent

    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter', metadata_ssl = 'False')
    def test_metadata_with_ssl_flag_not_set_in_agent(self):
        '''
        Description: Test to validate metadata service fails when metadata_use_ssl flag
                     is not set on the agent side.
            Maintainer: ritam@juniper.net
        '''

        #Back up conf files.
        if self.inputs.get_build_sku() in ['mitaka', 'newton']:
            cmd='cp /etc/nova/nova.conf /etc/nova/nova.conf.bkup'
        else:
            cmd='docker exec -it nova-api cp /etc/nova/nova.conf /etc/nova/nova.conf.bkup'
        for openstack_node in self.inputs.openstack_ips:
            self.inputs.run_cmd_on_server(openstack_node, cmd)

        cmd='cp /etc/contrail/contrail-vrouter-agent.conf /etc/contrail/contrail-vrouter-agent.conf.bkup'
        for compute_node in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_node, cmd)

        #Add cleanup routine.
        self.addCleanup(self.restore_conf)

        #Change config
        cmd='openstack-config --del /etc/contrail/contrail-vrouter-agent.conf METADATA metadata_use_ssl;\
             service contrail-vrouter-agent restart'
        for compute_node in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_node, cmd)

        #Validate metadata ssl service.
        try:
            self.metadata_service_test()
            self.logger.info('Metadata ssl test passed without ssl flag set on agent.')
            result=False
        except Exception as e:
            self.logger.error('Metadata ssl test failed without ssl flag set on agent.')
            result=True
        return result
    # end test_metadata_with_ssl_flag_not_set_in_agent

    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter', metadata_ssl = 'False')
    def test_metadata_with_ssl_disabled_only_on_agent(self):
        '''
        Description: Test to validate metadata service fails when agent sends insecure
                     request to ssl encrypted nova/metadata service.
            Maintainer: ritam@juniper.net
        '''

        #Back up conf files.
        if self.inputs.get_build_sku() in ['mitaka', 'newton']:
            cmd='cp /etc/nova/nova.conf /etc/nova/nova.conf.bkup'
        else:
            cmd='docker exec -it nova-api cp /etc/nova/nova.conf /etc/nova/nova.conf.bkup'
        for openstack_node in self.inputs.openstack_ips:
            self.inputs.run_cmd_on_server(openstack_node, cmd)

        cmd='cp /etc/contrail/contrail-vrouter-agent.conf /etc/contrail/contrail-vrouter-agent.conf.bkup'
        for compute_node in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_node, cmd)

        #Add cleanup routine.
        self.addCleanup(self.restore_conf)

        #Change config
        cmd='openstack-config --del /etc/contrail/contrail-vrouter-agent.conf METADATA metadata_use_ssl;\
             openstack-config --del /etc/contrail/contrail-vrouter-agent.conf METADATA metdata_client_cert_type;\
             openstack-config --del /etc/contrail/contrail-vrouter-agent.conf METADATA metadata_client_cert;\
             openstack-config --del /etc/contrail/contrail-vrouter-agent.conf METADATA metadata_client_key;\
             service contrail-vrouter-agent restart'
        for compute_node in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_node, cmd)

        #Validate metadata ssl service.
        try:
            self.metadata_service_test()
            self.logger.info('Metadata ssl test passed without any ssl encryption on agent side.')
            result=False
        except Exception as e:
            self.logger.error('Metadata ssl test failed without any ssl encryption on agent side.')
            result=True
        return result
    # end test_metadata_with_ssl_disabled_only_on_agent

    @preposttest_wrapper
    @skip_because(orchestrator = 'vcenter', metadata_ssl = 'False')
    def test_metadata_no_ca_cert(self):
        '''
        Description: Test to validate metadata service fails when agent sends insecure
                     request to ssl encrypted nova/metadata service. Here nova uses
                     cert key files for encryption and no ca-cert.
            Maintainer: ritam@juniper.net
        '''

        #Back up conf files.
        if self.inputs.get_build_sku() in ['mitaka', 'newton']:
            cmd='cp /etc/nova/nova.conf /etc/nova/nova.conf.bkup'
        else:
            cmd='docker exec -it nova-api cp /etc/nova/nova.conf /etc/nova/nova.conf.bkup'
        for openstack_node in self.inputs.openstack_ips:
            self.inputs.run_cmd_on_server(openstack_node, cmd)

        cmd='cp /etc/contrail/contrail-vrouter-agent.conf /etc/contrail/contrail-vrouter-agent.conf.bkup'
        for compute_node in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_node, cmd)

        #Add cleanup routine.
        self.addCleanup(self.restore_conf)

        #Change config
        cmd='openstack-config --del /etc/contrail/contrail-vrouter-agent.conf METADATA metadata_use_ssl;\
             openstack-config --del /etc/contrail/contrail-vrouter-agent.conf METADATA metdata_client_cert_type;\
             openstack-config --del /etc/contrail/contrail-vrouter-agent.conf METADATA metadata_client_cert;\
             openstack-config --del /etc/contrail/contrail-vrouter-agent.conf METADATA metadata_client_key;\
             service contrail-vrouter-agent restart'
        for compute_node in self.inputs.compute_ips:
            self.inputs.run_cmd_on_server(compute_node, cmd)

        if self.inputs.get_build_sku() in ['mitaka', 'newton']:
            cmd='openstack-config --del /etc/nova/nova.conf DEFAULT ssl_ca_file;\
                 openstack-config --del /etc/nova/nova.conf ssl ca_file;\
                 service nova-api restart'
        else:
            cmd='openstack-config --del /etc/kolla/nova-api/nova.conf DEFAULT ssl_ca_file;\
                 openstack-config --del /etc/kolla/nova-api/nova.conf ssl ca_file;\
                 docker restart nova-api'
        for openstack_node in self.inputs.openstack_ips:
            self.inputs.run_cmd_on_server(openstack_node, cmd)

        #Validate metadata ssl service.
        try:
            self.metadata_service_test()
            self.logger.info('Metadata ssl test passed without any ssl encryption on agent side and no ca-cert on nova.')
            result=False
        except Exception as e:
            self.logger.error('Metadata ssl test failed without any ssl encryption on agent side and no ca-cert on nova.')
            result=True
        return result
    # end test_metadata_no_ca_cert

# end TestMetadataSSL
