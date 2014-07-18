import traffic_tests
from vn_test import *
from vm_test import *
from floating_ip import *
from policy_test import *
from user_test import UserFixture
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
from tcutils.pkgs.Traffic.traffic.core.stream import Stream
from tcutils.pkgs.Traffic.traffic.core.profile import create, ContinuousProfile
from tcutils.pkgs.Traffic.traffic.core.helpers import Host
from tcutils.pkgs.Traffic.traffic.core.helpers import Sender, Receiver
from base import BaseVnVmTest
from common import isolated_creds
import inspect

import test

class TestBasicVMVN0(BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicVMVN0, cls).setUpClass()
    
    @preposttest_wrapper
    def test_bring_up_vm_with_control_node_down(self):
        ''' Create VM when there is not active control node. Verify VM comes up fine when all control nodes are back

        '''
        if len(set(self.inputs.bgp_ips)) < 2:
            raise self.skipTest(
                "Skiping Test. At least 2 control node required to run the test")
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
            self.inputs.stop_service('contrail-control', [entry])
            self.addCleanup(self.inputs.start_service,
                            'contrail-control', [entry])
        sleep(30)

        vn1_vm1_name = get_random_name('vm1')
        vn1_vm2_name = get_random_name('vm2')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name)
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name)


        vm1_fixture.verify_vm_launched()
        vm2_fixture.verify_vm_launched()
        vm1_node_ip = self.inputs.host_data[
            self.nova_fixture.get_nova_host_of_vm(vm1_fixture.vm_obj)]['host_ip']
        vm2_node_ip = self.inputs.host_data[
            self.nova_fixture.get_nova_host_of_vm(vm2_fixture.vm_obj)]['host_ip']
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
            if inspect_h.get_vna_vn_list()['VNs'] != []:
                self.logger.error(
                    'Agent should not have any VN info present when control node is down')
                result = result and False

        # Start all the control node
        for entry in controller_list:
            self.logger.info('Starting the Control service in  %s' % (entry))
            self.inputs.start_service('contrail-control', [entry])
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
    def test_ipam_persistence_across_restart_reboots(self):
        '''Test to validate IPAM persistence across restarts and reboots of nodes.
        '''
        #project_obj = self.useFixture(ProjectFixture(vnc_lib_h= self.vnc_lib, connections= self.connections))
        ipam_obj=self.useFixture( IPAMFixture(project_obj= self.project, name = get_random_name('my-ipam')))
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

        self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj )
        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )
        self.logger.info('Will restart the services now')
        for compute_ip in self.inputs.compute_ips:
            pass
            self.inputs.restart_service('contrail-vrouter',[compute_ip])
        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('contrail-control',[bgp_ip])
            pass
        sleep(30)

        self.logger.info('Will check if the ipam persists and ping b/w VMs is still successful')

        assert ipam_obj
        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )
        return True
    
    @preposttest_wrapper
    def test_multistep_vm_add_delete_with_stop_start_service(self):
        ''' Test to validate VMs addition deletion after service restarts.
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
        vm1_fixture.verify_vm_launched()

        self.logger.info('vm1 launched successfully.Stopping vrouter service')
        for compute_ip in self.inputs.compute_ips:
            self.inputs.stop_service('contrail-vrouter', [compute_ip])
            self.addCleanup(self.inputs.start_service,
                            'contrail-vrouter', [compute_ip])
        self.logger.info('Trying to delete vm1')
        assert not vm1_fixture.cleanUp()
        self.logger.info(
            'vm1 is not deleted as expected.Trying to launch a new VM vm2')
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name = get_random_name ('vm2'), project_name=self.inputs.project_name))
        vm2_fixture.verify_vm_launched()
        self.logger.info('Checking if vm2 has booted up')
        assert not self.nova_fixture.wait_till_vm_is_up(vm2_fixture.vm_obj)
        self.logger.info(
            'vm2 has not booted up as expected.Starting vrouter service')
        for compute_ip in self.inputs.compute_ips:
            self.inputs.start_service('contrail-vrouter', [compute_ip])
        vm2_fixture.wait_till_vm_is_up()
        self.logger.info('vm2 is up now as expected')
        assert vm2_fixture.verify_on_setup()

        return True
    # end test_multistep_vm_add_delete_with_stop_start_service
    
    @preposttest_wrapper
    def test_multistep_vm_delete_with_stop_start_service(self):
        ''' Test to validate VMs addition deletion after service restarts.
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
            self.inputs.stop_service('contrail-vrouter', [compute_ip])
        #    self.addCleanup( sleep(10))
            self.addCleanup(self.inputs.start_service,
                            'contrail-vrouter', [compute_ip])
        self.logger.info('Trying to delete the VM')
        assert not vm1_fixture.cleanUp()
        self.logger.info('VM is not deleted as expected')
        for compute_ip in self.inputs.compute_ips:
            self.logger.info('Starting Vrouter Service')
            self.inputs.start_service('contrail-vrouter', [compute_ip])
            sleep(10)
        return True
    # end test_multistep_vm_delete_with_stop_start_service
    
    @preposttest_wrapper
    def test_nova_com_sch_restart_with_multiple_vn_vm(self):
        ''' Test to validate that multiple VM creation and deletion passes.
        '''
        vm1_name = get_random_name('vm_mine')
        vn_name = get_random_name('vn222')
        vn_subnets = ['11.1.1.0/24']
        vn_count_for_test = 32
        if (len(self.inputs.compute_ips) == 1):
            vn_count_for_test = 5
        vm_fixture = self.useFixture(
            create_multiple_vn_and_multiple_vm_fixture(
                connections=self.connections,
                vn_name=vn_name, vm_name=vm1_name, inputs=self.inputs, project_name=self.inputs.project_name,
                subnets=vn_subnets, vn_count=vn_count_for_test, vm_count=1, subnet_count=1, image_name='cirros-0.3.0-x86_64-uec',
                flavor='m1.tiny'))
        time.sleep(100)
        try:
            assert vm_fixture.verify_vms_on_setup()
            assert vm_fixture.verify_vns_on_setup()
        except Exception as e:
            self.logger.exception("Got exception as %s" % (e))

        compute_ip = []
        for vmobj in vm_fixture.vm_obj_dict.values():
            vm_host_ip = vmobj.vm_node_ip
            if vm_host_ip not in compute_ip:
                compute_ip.append(vm_host_ip)
        self.inputs.restart_service('openstack-nova-compute', compute_ip)
        self.inputs.restart_service('openstack-nova-scheduler', compute_ip)
        sleep(30)
        for vmobj in vm_fixture.vm_obj_dict.values():
            assert vmobj.verify_on_setup()
        return True
    # end test_nova_com_sch_restart_with_multiple_vn_vm
    
    @test.attr(type=['sanity'])
    @preposttest_wrapper
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
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        assert vn1_fixture.verify_on_setup()
        vn1_fixture.bind_policies(
            [policy1_fixture.policy_fq_name], vn1_fixture.vn_id)
        self.addCleanup(vn1_fixture.unbind_policies,
                        vn1_fixture.vn_id, [policy1_fixture.policy_fq_name])
        vn2_fixture = self.create_vn(vn2_name, vn2_subnets)
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
            pass		
            self.inputs.restart_service('contrail-vrouter', [compute_ip])
        for bgp_ip in self.inputs.bgp_ips:
            pass
            self.inputs.restart_service('contrail-control', [bgp_ip])
        self.logger.info('Sleeping for 10 seconds')
        sleep(10)
        vn1_vm2_name = get_random_name('vn1_vm2')
        vn2_vm2_name = get_random_name('vn2_vm2')
        vm3_fixture = self.create_vm(vn1_fixture, vn1_vm2_name)
        assert vm3_fixture.verify_on_setup()
        vm4_fixture = self.create_vm(vn2_fixture, vn2_vm2_name)
        assert vm4_fixture.verify_on_setup()
        vm3_fixture.wait_till_vm_is_up()
        vm4_fixture.wait_till_vm_is_up()
        assert vm3_fixture.ping_with_certainty(vm4_fixture.vm_ip)

# end test_process_restart_in_policy_between_vns
    
    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_process_restart_with_multiple_vn_vm(self):
        ''' Test to validate that multiple VM creation and deletion passes.
        '''
        vm1_name = 'vm_mine'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_count_for_test = 32
        if (len(self.inputs.compute_ips) == 1):
            vn_count_for_test = 10
        vm_fixture = self.useFixture(
            create_multiple_vn_and_multiple_vm_fixture(
                connections=self.connections,
                vn_name=vn_name, vm_name=vm1_name, inputs=self.inputs, project_name=self.inputs.project_name,
                subnets=vn_subnets, vn_count=vn_count_for_test, vm_count=1, subnet_count=1, image_name='cirros-0.3.0-x86_64-uec',
                flavor='m1.tiny'))
        time.sleep(100)
        try:
            assert vm_fixture.wait_till_vms_are_up()
            assert vm_fixture.verify_vns_on_setup()
        except Exception as e:
            self.logger.exception("Got exception as %s" % (e))
        compute_ip = []
        for vmobj in vm_fixture.vm_obj_dict.values():
            vm_host_ip = vmobj.vm_node_ip
            if vm_host_ip not in compute_ip:
                compute_ip.append(vm_host_ip)
        self.inputs.restart_service('contrail-vrouter', compute_ip)
        sleep(50)
        for vmobj in vm_fixture.vm_obj_dict.values():
            assert vmobj.verify_on_setup()
        return True
    #end test_process_restart_with_multiple_vn_vm
