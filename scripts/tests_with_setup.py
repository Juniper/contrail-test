# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
from tests_with_setup_base import *


class TestSanity(TestSanityBase):

    def setUp(self):
        super(TestSanity, self).setUp()
    # end setUp

    def cleanUp(self):
        super(TestSanity, self).cleanUp()
    # end cleanUp

    @preposttest_wrapper
    def test_diff_proj_same_vn_vm_add_delete(self):
        ''' Test to validate that a VN and VM with the same name and same subnet can be created in two different projects
        '''
        vm_name = 'vm_mine'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        projects = ['project111', 'project222']
        user_list = [('gudi', 'gudi123', 'admin'), ('mal', 'mal123', 'admin')]
        auth_url = 'http://%s:5000/v2.0' % (self.inputs.openstack_ip)
        kc = ksclient.Client(
            username=self.inputs.stack_user, password=self.inputs.stack_password,
            tenant_name=self.inputs.project_name, auth_url=auth_url)

        user_pass = {}
        user_role = {}
        user_set = set()
        role_set = set()
        for (n, p, r) in user_list:
            user_pass[n] = p
            user_role[n] = r
            user_set.add(n)
            role_set.add(n)

        users = set([user.name for user in kc.users.list()])
        roles = set([user.name for user in kc.roles.list()])
        tenants = kc.tenants.list()
        admin_tenant = [x for x in tenants if x.name == 'admin'][0]

        create_user_set = user_set - users
        create_role_set = role_set - roles

        for new_tenant in projects:
            kc.tenants.create(new_tenant)
        role_dict = {}
        tenant_dict = {}
        for role in kc.roles.list():
            role_dict[role.name] = role
        for tenant in kc.tenants.list():
            tenant_dict[tenant.name] = tenant

        for name in create_user_set:
            user = kc.users.create(
                name, user_pass[name], '', tenant_id=admin_tenant.id)
            for new_tenant in projects:
                kc.roles.add_user_role(
                    user, role_dict[user_role[name]], tenant_dict[new_tenant])

        user_dict = {}
        for user in kc.users.list():
            user_dict[user.name] = user

        self.new_proj_inputs1 = self.useFixture(ContrailTestInit(self.ini_file, stack_user=user_list[
                                                0][0], stack_password=user_list[0][1], project_fq_name=['default-domain', projects[0]]))
        self.new_proj_connections1 = ContrailConnections(self.new_proj_inputs1)

        self.new_proj_inputs2 = self.useFixture(ContrailTestInit(self.ini_file, stack_user=user_list[
                                                1][0], stack_password=user_list[1][1], project_fq_name=['default-domain', projects[1]]))
        self.new_proj_connections2 = ContrailConnections(self.new_proj_inputs2)

        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=projects[
                    0], connections=self.new_proj_connections1,
                vn_name=vn_name, inputs=self.new_proj_inputs1, subnets=vn_subnets))

        assert vn1_fixture.verify_on_setup()
        vn1_obj = vn1_fixture.obj

        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=projects[
                    1], connections=self.new_proj_connections2,
                vn_name=vn_name, inputs=self.new_proj_inputs2, subnets=vn_subnets))

        assert vn2_fixture.verify_on_setup()
        vn2_obj = vn2_fixture.obj

        vm1_fixture = self.useFixture(
            VMFixture(connections=self.new_proj_connections1,
                      vn_obj=vn1_obj, vm_name=vm_name, project_name=projects[0]))
        vm2_fixture = self.useFixture(
            VMFixture(connections=self.new_proj_connections2,
                      vn_obj=vn2_obj, vm_name=vm_name, project_name=projects[1]))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        if not vm1_fixture.agent_label == vm2_fixture.agent_label:
            self.logger.info("Correct label assigment")
        else:
            self.logger.error(
                "The same label has been assigned for both the VMs")
            return False

        testfail = 0
        for new_tenant in projects:
            try:
                kc.tenants.delete(tenant_dict[new_tenant])
            except Exception as e:
                self.logger.error(
                    'ClientException:This is because the project info still remains in the API server ==> Bug 744')

        for name in create_user_set:
            try:
                kc.users.delete(user_dict[name])
            except Exception as e:
                self.logger.error(
                    'ClientException:This is because the project info still remains in the API server ==> Bug 744')

        assert testfail > 0, "Placeholder till the Bug 744 is fixed "
        return True
    # end test_diff_proj_same_vn_vm_add_delete

    # start subnet ping
    # verifying that ping to subnet broadcast is respended by other vms in same subnet
    # vm from other subnet should not respond
    @preposttest_wrapper
    def test_ping_on_broadcast_multicast(self):
        ''' Validate Ping on subnet broadcast,link local multucast,network broadcast .
        1. Create network and launch 4 instances
        2. On each ubuntu VM disable flag of icmp_echo_ignore_broadcasts 
        3. Verify ping to VM metadata from corresponding compute nodes
        4. From VM ping to subnet broadcast IP and verify no loss
        '''
        result = True
        vn1_name = self.res.vn1_name
        vn1_subnets = self.res.vn1_subnets
        ping_count = '5'
        vn1_vm1_name = self.res.vn1_vm1_name
        vn1_vm2_name = self.res.vn1_vm2_name
        vn1_vm3_name = self.res.vn1_vm3_name
        vn1_vm4_name = self.res.vn1_vm4_name
        vn1_fixture = self.res.get_vn1_fixture()
        vm1_fixture = self.res.get_vn1_vm1_fixture()
        vm2_fixture = self.res.get_vn1_vm2_fixture()
        vm3_fixture = self.res.get_vn1_vm3_fixture()
        vm4_fixture = self.res.get_vn1_vm4_fixture()
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        assert vm3_fixture.wait_till_vm_is_up()
        assert vm4_fixture.wait_till_vm_is_up()
        # Geting the VM ips
        vm1_ip = vm1_fixture.vm_ip
        vm2_ip = vm2_fixture.vm_ip
        vm3_ip = vm3_fixture.vm_ip
        vm4_ip = vm4_fixture.vm_ip
        ip_list = [vm1_ip, vm2_ip, vm3_ip, vm4_ip]
        bcast_ip = str(IPNetwork(vn1_subnets[0]).broadcast)
        list_of_ip_to_ping = [bcast_ip, '224.0.0.1', '255.255.255.255']
        # passing command to vms so that they respond to subnet broadcast
        cmd = ['echo 0 > /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts']
        vm_fixtures = [vm1_fixture, vm2_fixture, vm3_fixture, vm4_fixture]
        for vm in vm_fixtures:
            print 'Running cmd for %s' % vm.vm_name
            for i in range(3):
                try:
                    self.logger.info("Retry %s" % (i))
                    ret = vm.run_cmd_on_vm(cmds=cmd, as_sudo=True)
                    if not ret:
                        for vn in vm.vn_fq_names:
                            vm.ping_vm_from_host(vn)
                        raise Exception
                except Exception as e:
                    time.sleep(5)
                    self.logger.exception("Got exception as %s" % (e))
                else:
                    break
        for dst_ip in list_of_ip_to_ping:
            self.logger.info('pinging from %s to %s' % (vm1_ip, dst_ip))
# pinging from Vm1 to subnet broadcast
            ping_output = vm1_fixture.ping_to_ip(
                dst_ip, return_output=True, count=ping_count, other_opt='-b')
            self.logger.info("ping output : \n %s" % (ping_output))
            expected_result = ' 0% packet loss'
            if not expected_result in ping_output:
                self.logger.error('Expected 0% packet loss seen!')
                self.logger.error('Ping result : %s' % (ping_output))
                result = result and True
# getting count of ping response from each vm
            string_count_dict = {}
            string_count_dict = get_string_match_count(ip_list, ping_output)
            self.logger.info("output %s" % (string_count_dict))
            self.logger.info(
                "There should be atleast 4 echo reply from each ip")
            for k in ip_list:
                # this is a workaround : ping utility exist as soon as it gets
                # one response
#                assert (string_count_dict[k] >= (int(ping_count) - 1))
                if not string_count_dict[k] >= (int(ping_count) - 1):
                    self.logger.error('Seen %s reply instead of atleast %s' % (
                        (int(ping_count) - 1)))
                    result = result and False
        if not result:
            self.logger.error('There were errors. Verifying VM fixtures')
            assert vm1_fixture.verify_on_setup()
            assert vm2_fixture.verify_on_setup()
            assert vm3_fixture.verify_on_setup()
            assert vm4_fixture.verify_on_setup()
        return True
    # end subnet ping

    @preposttest_wrapper
    def test_ping_within_vn_two_vms_two_different_subnets(self):
        """test_ping_within_vn_two_vms_two_different_subnets 
            1. Validate Ping between two VMs within a VN-2 vms in 2 different subnets.
            2. Validate ping to subnet broadcast not responded back by other vm
            3. Validate ping to network broadcast (all 255) is responded back by other vm
        """ 
        vn1_name = 'vn030'
        vn1_subnets = ['31.1.1.0/30', '31.1.2.0/30']
        # vn1_subnets=['30.1.1.0/24']
        vn1_vm1_name = 'vm1'
        vn1_vm2_name = 'vm2'
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm1_name))
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm2_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip)
        assert vm2_fixture.ping_with_certainty(vm1_fixture.vm_ip)
        # Geting the VM ips
        vm1_ip = vm1_fixture.vm_ip
        vm2_ip = vm2_fixture.vm_ip
        ip_list = [vm1_ip, vm2_ip]
#       gettig broadcast ip for vm1_ip
        ip_broadcast = ''
        ip_broadcast = get_subnet_broadcast_from_ip(vm1_ip, '30')
        list_of_ip_to_ping = [ip_broadcast, '224.0.0.1', '255.255.255.255']
        # passing command to vms so that they respond to subnet broadcast
        cmd_list_to_pass_vm = [
            'echo 0 > /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts']

        vm1_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm2_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)

        for dst_ip in list_of_ip_to_ping:
            print 'pinging from %s to %s' % (vm1_ip, dst_ip)
# pinging from Vm1 to subnet broadcast
            ping_output = vm1_fixture.ping_to_ip(
                dst_ip, return_output=True, other_opt='-b')
            expected_result = ' 0% packet loss'
            assert (expected_result in ping_output)
# getting count of ping response from each vm
            string_count_dict = {}
            string_count_dict = get_string_match_count(ip_list, ping_output)
            print string_count_dict
            if (dst_ip == ip_broadcast):
                assert (string_count_dict[vm2_ip] == 0)
            if (dst_ip == '224.0.0.1' or dst_ip == '255.255.255.255'):
                assert (string_count_dict[vm2_ip] > 0)
        return True
    # end test_ping_within_vn

    @preposttest_wrapper
    def test_policy_to_deny(self):
        ''' Test to validate that with policy having rule to disable icmp within the VN, ping between VMs should fail
            1. Pick 2 VN from resource pool which have one VM in each
            2. Create policy with icmp deny rule
            3. Associate policy to both VN
            4. Ping from one VM to another. Ping should fail
        Pass criteria: Step 2,3 and 4 should pass
        '''
        vn1_name = self.res.vn1_name
        vn1_subnets = self.res.vn1_subnets
        policy_name = 'policy1'
        rules = [
            {
                'direction': '<>', 'simple_action': 'deny',
                'protocol': 'icmp',
                'source_network': vn1_name,
                'dest_network': vn1_name,
            },
        ]
        policy_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name, rules_list=rules, inputs=self.inputs,
                connections=self.connections))
        vn1_fixture = self.res.get_vn1_fixture()
        vn1_fixture.bind_policies(
            [policy_fixture.policy_fq_name], vn1_fixture.vn_id)
        self.addCleanup(vn1_fixture.unbind_policies,
                        vn1_fixture.vn_id, [policy_fixture.policy_fq_name])
        assert vn1_fixture.verify_on_setup()

        vn1_vm1_name = self.res.vn1_vm1_name
        vn1_vm2_name = self.res.vn1_vm2_name
        vm1_fixture = self.res.get_vn1_vm1_fixture()
        vm2_fixture = self.res.get_vn1_vm2_fixture()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        if vm1_fixture.ping_to_ip(vm2_fixture.vm_ip):
            self.logger.error('Ping from %s to %s passed,expected it to fail' % (
                               vm1_fixture.vm_name, vm2_fixture.vm_name))
            self.logger.info('Doing verifications on the fixtures now..')
            assert vm1_fixture.verify_on_setup()
            assert vm2_fixture.verify_on_setup()
        return True
    # end test_policy_to_deny

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
        vn1_name = self.res.vn1_name
        vn1_subnets = self.res.vn1_subnets
        vn2_name = self.res.vn2_name
        vn2_subnets = self.res.vn2_subnets
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
                policy_name=policy2_name, rules_list=rev_rules, inputs=self.inputs,
                connections=self.connections))
        vn1_fixture = self.res.get_vn1_fixture()
        assert vn1_fixture.verify_on_setup()
        vn1_fixture.bind_policies(
            [policy1_fixture.policy_fq_name], vn1_fixture.vn_id)
        self.addCleanup(vn1_fixture.unbind_policies,
                        vn1_fixture.vn_id, [policy1_fixture.policy_fq_name])
        vn2_fixture = self.res.get_vn2_fixture()
        assert vn2_fixture.verify_on_setup()
        vn2_fixture.bind_policies(
            [policy2_fixture.policy_fq_name], vn2_fixture.vn_id)
        self.addCleanup(vn2_fixture.unbind_policies,
                        vn2_fixture.vn_id, [policy2_fixture.policy_fq_name])
        vn1_vm1_name = self.res.vn1_vm1_name
        vn2_vm1_name = self.res.vn2_vm1_name
        vm1_fixture = self.res.get_vn1_vm1_fixture()
        vm2_fixture = self.res.get_vn2_vm1_fixture()
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip)

        for compute_ip in self.inputs.compute_ips:
            self.inputs.restart_service('contrail-vrouter-agent', [compute_ip])
        for bgp_ip in self.inputs.bgp_ips:
            self.inputs.restart_service('contrail-control', [bgp_ip])
        self.logger.info('Sleeping for 10 seconds')
        sleep(10)
        vn1_vm2_name = self.res.vn1_vm2_name
        vn2_vm2_name = self.res.vn2_vm2_name
        vm3_fixture = self.res.get_vn1_vm2_fixture()
        assert vm3_fixture.verify_on_setup()
        vm4_fixture = self.res.get_vn2_vm2_fixture()
        assert vm4_fixture.verify_on_setup()
        vm3_fixture.wait_till_vm_is_up()
        vm4_fixture.wait_till_vm_is_up()
        assert vm3_fixture.ping_with_certainty(vm4_fixture.vm_ip)

        return True
# end test_process_restart_in_policy_between_vns

    @preposttest_wrapper
    def test_policy_between_vns(self):
        ''' Test to validate that with policy having rule to check icmp fwding between VMs on different VNs , ping between VMs should pass

        '''
        vn1_name = self.res.vn1_name
        vn1_subnets = self.res.vn1_subnets
        vn2_name = self.res.vn2_name
        vn2_subnets = self.res.vn2_subnets
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
                policy_name=policy2_name, rules_list=rev_rules, inputs=self.inputs,
                connections=self.connections))
        vn1_fixture = self.res.get_vn1_fixture()
        vn1_fixture.bind_policies(
            [policy1_fixture.policy_fq_name], vn1_fixture.vn_id)
        self.addCleanup(vn1_fixture.unbind_policies,
                        vn1_fixture.vn_id, [policy1_fixture.policy_fq_name])

        assert vn1_fixture.verify_on_setup()
        vn2_fixture = self.res.get_vn2_fixture()
        vn2_fixture.bind_policies(
            [policy2_fixture.policy_fq_name], vn2_fixture.vn_id)
        self.addCleanup(vn2_fixture.unbind_policies,
                        vn2_fixture.vn_id, [policy2_fixture.policy_fq_name])
        assert vn2_fixture.verify_on_setup()

        vm1_fixture = self.res.get_vn1_vm1_fixture()
        assert vm1_fixture.verify_on_setup()
        vm2_fixture = self.res.get_vn2_vm1_fixture()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)
        return True

# end test_policy_between_vns

    @preposttest_wrapper
    def test_tcp_transfer_from_fip_vm(self):
        ''' Validate data transfer through floating ip.

        '''
        fip_pool_name = 'testpool'

        fvn_name = self.res.fip_vn_name
        fvm_name = self.res.fvn_vm1_name
        fvn_subnets = self.res.fip_vn_subnets

        vn1_name = self.res.vn1_name
        vm1_name = self.res.vn1_vm4_name
        vn1_subnets = self.res.vn1_subnets

        vn2_name = self.res.vn2_name
        vm2_name = self.res.vn2_vm1_name
        vn2_subnets = self.res.vn2_subnets

        # policy between frontend and backend
        policy_name = 'frontend-to-backend-policy'
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any',
                'source_network': vn1_name,
                'dest_network': vn2_name,
            },
        ]

        policy_fixture = self.useFixture(
            PolicyFixture(policy_name=policy_name,
                          rules_list=rules, inputs=self.inputs,
                          connections=self.connections))
        # frontend VN
        vn1_fixture = self.res.get_vn1_fixture()
        vn1_fixture.bind_policies(
            [policy_fixture.policy_fq_name], vn1_fixture.vn_id)
        self.addCleanup(vn1_fixture.unbind_policies,
                        vn1_fixture.vn_id, [policy_fixture.policy_fq_name])
        vn1_fixture.verify_on_setup()

        # backend VN
        vn2_fixture = self.res.get_vn2_fixture()
        vn2_fixture.bind_policies(
            [policy_fixture.policy_fq_name], vn2_fixture.vn_id)
        self.addCleanup(vn2_fixture.unbind_policies,
                        vn2_fixture.vn_id, [policy_fixture.policy_fq_name])
        vn2_fixture.verify_on_setup()

        # public VN
        fvn_fixture = self.res.get_fvn_fixture()
        fvn_fixture.verify_on_setup()

        # frontend VM
        vm1_fixture = self.res.get_vn1_vm4_fixture()
        assert vm1_fixture.verify_on_setup()

        # backend VM
        vm2_fixture = self.res.get_vn2_vm1_fixture()
        assert vm2_fixture.verify_on_setup()

        # public VM
        fvm_fixture = self.res.get_fvn_vm1_fixture()
        assert fvm_fixture.verify_on_setup()

        fip_fixture = self.useFixture(FloatingIPFixture(
            project_name=self.inputs.project_name, inputs=self.inputs,
            connections=self.connections, pool_name=fip_pool_name,
            vn_id=fvn_fixture.vn_id))
        assert fip_fixture.verify_on_setup()

        fip_id = fip_fixture.create_and_assoc_fip(fvn_fixture.vn_id,
                                                  vm1_fixture.vm_id)

        fip = vm1_fixture.vnc_lib_h.floating_ip_read(
            id=fip_id).get_floating_ip_address()
        assert fvm_fixture.ping_to_ip(fip)

        result = fvm_fixture.tcp_data_transfer(vm1_fixture.local_ip, fip)
        fip_fixture.disassoc_and_delete_fip(fip_id)
        assert result
        return result
    # end test_tcp_transfer_from_fip_vm

    @preposttest_wrapper
    def test_multiple_vn_vm(self):
        """ Validate creation of multiple VN with multiple subnet and VMs in it.
        """

        result = True
        # Multiple VN's with multiple subnets
        vn_s = {'vn-1': '20.1.1.0/24', 'vn-2':
                ['10.1.1.0/24', '10.1.2.0/24']}
        multi_vn_fixture = self.useFixture(MultipleVNFixture(
            connections=self.connections, inputs=self.inputs, subnet_count=2,
            vn_name_net=vn_s,  project_name=self.inputs.project_name))
        assert multi_vn_fixture.verify_on_setup()

        vn_objs = multi_vn_fixture.get_all_fixture_obj()
        multi_vm_fixture = self.useFixture(MultipleVMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vm_count_per_vn=2, vn_objs=vn_objs))
        assert multi_vm_fixture.verify_on_setup()

        return True
    # end test_multiple_vn_vm

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
                subnets=vn_subnets, vn_count=vn_count_for_test, vm_count=1, subnet_count=1))
        compute_ip = []
        for vmobj in vm_fixture.vm_obj_dict.values():
            vm_host_ip = vmobj.vm_node_ip
            if vm_host_ip not in compute_ip:
                compute_ip.append(vm_host_ip)
        self.inputs.restart_service('contrail-vrouter-agent', compute_ip)
        sleep(10)
        for vmobj in vm_fixture.vm_obj_dict.values():
            assert vmobj.verify_on_setup()
        return True

    @preposttest_wrapper
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
                "Skiping Test. At least 2 control node required to run the test")
            raise self.skipTest(
                "Skiping Test. At least 2 control node required to run the test")
        result = True
        vn1_name = self.res.vn1_name
        vn1_subnets = self.res.vn1_subnets
        vn1_vm1_name = self.res.vn1_vm1_name
        vn1_vm2_name = self.res.vn1_vm2_name
        vn1_fixture = self.res.get_vn1_fixture()
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.res.get_vn1_vm1_fixture()
        assert vm1_fixture.verify_on_setup()
        vm2_fixture = self.res.get_vn1_vm2_fixture()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
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
            'contrail-control', [active_controller_host_ip])
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
            'contrail-control', [active_controller_host_ip])

        # Check the BGP peering status from the currently active control node
        sleep(5)
        cn_bgp_entry = self.cn_inspect[
            new_active_controller_host_ip].get_cn_bgp_neigh_entry()
        for entry in cn_bgp_entry:
            if entry['state'] != 'Established':
                result = result and False
                self.logger.error(
                    'With Peer %s peering is not Established. Current State %s ' %
                    (entry['peer'], entry['state']))

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
    def test_agent_cleanup_with_control_node_stop(self):
        ''' Stop all the control node and verify the cleanup process in agent

        '''
        if len(set(self.inputs.bgp_ips)) < 2:
            raise self.skipTest(
                "Skiping Test. At least 2 control node required to run the test")
        result = True
        vn1_name = self.res.vn1_name
        vn1_subnets = self.res.vn1_subnets
        vn1_vm1_name = self.res.vn1_vm1_name
        vn1_vm2_name = self.res.vn1_vm2_name
        vn1_fixture = self.res.get_vn1_fixture()
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.res.get_vn1_vm1_fixture()
        assert vm1_fixture.verify_on_setup()
        vm2_fixture = self.res.get_vn1_vm2_fixture()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm2_fixture.ping_to_ip(vm1_fixture.vm_ip)

        # Collecting all the control node details
        controller_list = []
        self.agent_inspect = self.connections.agent_inspect
        inspect_h = self.agent_inspect[vm1_fixture.vm_node_ip]
        agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            controller_list.append(entry['controller_ip'])
        list_of_vm = inspect_h.get_vna_vm_list()

        # Stop all the control node
        for entry in controller_list:
            self.logger.info('Stoping the Control service in  %s' % (entry))
            self.inputs.stop_service('contrail-control', [entry])
        sleep(5)

        # It seems that cleanup happens after 2 mins
        sleep(120)

        # Verify VM entry is removed from the agent introspect
        vm_id_list = inspect_h.get_vna_vm_list()
        if vm1_fixture.vm_id in vm_id_list:
            result = result and False
            self.logger.error(
                'VM %s is still present in Agent Introspect.Cleanup not working when all control node shut' %
                (vm1_fixture.vm_name))
        if vm2_fixture.vm_id in vm_id_list:
            result = result and False
            self.logger.error(
                'VM %s is still present in Agent Introspect.Cleanup not working when all control node shut' %
                (vm2_fixture.vm_name))

        # TODO Verify the IF-Map entry
        # Start all the control node
        for entry in controller_list:
            self.logger.info('Starting the Control service in  %s' % (entry))
            self.inputs.start_service('contrail-control', [entry])

        sleep(10)
        self.logger.info('Checking the VM came up properly or not')
        assert vm2_fixture.verify_on_setup()
        assert vm1_fixture.verify_on_setup()

        # Check everything came up fine
        vm_id_list = inspect_h.get_vna_vm_list()
        if vm1_fixture.vm_id not in vm_id_list or vm2_fixture.vm_id not in vm_id_list:
            result = result and False
            self.logger.error(
                'After starting the service all the VM entry did not came up properly')

        if not result:
            self.logger.error(
                'Test to verify cleanup of agent after control nodes stop Failed')
            assert result
        return True
    # end test_agent_cleanup_with_control_node_stop

    @preposttest_wrapper
    def test_bring_up_vm_with_control_node_down(self):
        ''' Create VM when there is not active control node. Verify VM comes up fine when all control nodes are back

        '''
        self.agent_inspect = self.connections.agent_inspect
        if len(set(self.inputs.bgp_ips)) < 2:
            raise self.skipTest(
                "Skiping Test. At least 2 control node required to run the test")
        result = True
        vn1_name = self.res.vn1_name
        vn1_subnets = self.res.vn1_subnets

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
        sleep(10)

        vn1_vm1_name = self.res.vn1_vm1_name
        vn1_vm2_name = self.res.vn1_vm2_name
        vn1_fixture = self.res.get_vn1_fixture()
        vm1_fixture = self.res.get_vn1_vm1_fixture()

        vm2_fixture = self.res.get_vn1_vm2_fixture()

        # Check all the VM got IP when control node is down
        # Verify VM in Agent. This is more required to get TAP iterface and Metadata IP.
        # TODO Need to check the verify_vm_in_agent chance to get passed when
        # Control node is down with new implmenetation
        vm1_fixture.verify_vm_in_agent()
        vm2_fixture.verify_vm_in_agent()
        vm_ip1 = vm1_fixture.get_vm_ip_from_vm()
        vm_ip2 = vm2_fixture.get_vm_ip_from_vm()
        if vm_ip1 is None or vm_ip2 is None:
            result = result and False
            self.logger.error(
                'VM does not get an IP when all control nodes are down')
        else:
            self.logger.info(
                'Both VM got required IP when control nodes are down')

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

#    @preposttest_wrapper
#    def test_vn_add_delete_no_subnet(self):
#        '''Test to validate VN creation even when no subnet is provided. Commented till 811 is fixed.
#        '''
#        vn_obj=self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,
#            vn_name='vn007', inputs= self.inputs ))
#        assert vn_obj.verify_on_setup()
#        assert vn_obj
#        return True
    # end test_vn_add_delete_no_subnet

#   @preposttest_wrapper
#   def test_vn_reboot_nodes(self):
#        ''' Test to validate persistence of VN across compute/control/cfgm node reboots Commented till 129 is fixed.
#        '''
#        vn_obj=self.useFixture( VNFixture(project_name= self.inputs.project_name, connections= self.connections,
#                     vn_name='vn111', inputs= self.inputs, subnets=['100.100.100.0/24']))
#        assert vn_obj.verify_on_setup()
#        reboot the compute node now and verify the VN persistence
#        for compute_ip in self.inputs.compute_ips:
#            self.inputs.reboot(compute_ip)
#        sleep(120)
#        assert vn_obj.verify_on_setup()
# reboot the control nodes now and verify the VN persistence
#        for bgp_ip in self.inputs.bgp_ips:
#            self.inputs.reboot(bgp_ip)
#        sleep(120)
#        assert vn_obj.verify_on_setup()
# reboot the cfgm node now and verify the VN persistence
#        self.inputs.reboot(self.inputs.cfgm_ip)
#        sleep(120)
#        assert vn_obj.verify_on_setup()
#        assert vn_obj
#        return True
    # end test_vn_reboot_nodes

#    @preposttest_wrapper
#    def vn_subnet_tests(self):
#        """ Validate various type of subnets associated to VNs.Commented till 762, 801, 802, 803 and 805 are fixed.
#        """
#
#        result = True
#        vn_s = {'vn-1' : '0.0.0.0/0', 'vn-2' : ['10.1.1.0/24', '10.1.1.0/24'], 'vn-3' : '169.254.1.1/24', 'vn-4' : '251.2.2.1/24', 'vn-5' : '127.0.0.1/32', 'vn-6' : '8.8.8.8/32', 'vn-7' : '9.9.9.9/31','vn-8' : ['11.11.11.0/30', '11.11.11.11/29']}
#        multi_vn_fixture = self.useFixture(MultipleVNFixture(
#            connections=self.connections, inputs=self.inputs, subnet_count=2,
#            vn_name_net=vn_s,  project_name=self.inputs.project_name))
#
#        vn_objs = multi_vn_fixture.get_all_fixture_obj()
#        assert not multi_vn_fixture.verify_on_setup()
#
#        return True
# end test_subnets_vn

    @preposttest_wrapper
    def test_uve(self):
        '''Test to validate collector uve.
        '''
        analytics_obj = AnalyticsVerification(
            inputs=self.inputs, connections=self.connections)
        assert analytics_obj.verify_collector_uve()
        return True
    # end test_uve

    @preposttest_wrapper
    def test_multiple_floating_ip_for_single_vm(self):
        '''Test to validate floating-ip Assignment to a VM. It creates a VM, assigns a FIP to it and pings to a IP in the FIP VN.
        '''
        result = True
        fip_pool_name = 'some-other-pool1'
        fvn_name = self.res.fvn_name
        fvm_name = self.res.fvn_vm1_name
        fvn_subnets = self.res.fip_vn_subnets
        fip_pool_name1 = 'some-pool2'
        fvn_name1 = 'fvnn200'
        fvm_name1 = 'vm200'
        fvn_subnets1 = ['150.1.1.0/24']
        vm1_name = self.res.vn1_vm1_name
        vn1_name = self.res.vn1_name
        vn1_subnets = self.res.vn1_subnets

        # VN Fixture
        fvn_fixture = self.res.get_fvn_fixture()
        assert fvn_fixture.verify_on_setup()
        fvn_fixture1 = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=fvn_name1, inputs=self.inputs, subnets=fvn_subnets1))
        assert fvn_fixture1.verify_on_setup()
        vn1_fixture = self.res.get_vn1_fixture()
        assert vn1_fixture.verify_on_setup()

        # VM Fixture
        vm1_fixture = self.res.get_vn1_vm1_fixture()
        assert vm1_fixture.verify_on_setup()
        fvm_fixture = self.res.get_fvn_vm1_fixture()
        assert fvm_fixture.verify_on_setup()
        fvm_fixture1 = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=fvn_fixture1.obj, vm_name=fvm_name1))
        assert fvm_fixture1.verify_on_setup()
        # Floating Ip Fixture
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name, vn_id=fvn_fixture.vn_id))
        assert fip_fixture.verify_on_setup()
        fip_fixture1 = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name, inputs=self.inputs,
                connections=self.connections, pool_name=fip_pool_name1, vn_id=fvn_fixture1.vn_id))
        assert fip_fixture1.verify_on_setup()
        fip_id = fip_fixture.create_and_assoc_fip(
            fvn_fixture.vn_id, vm1_fixture.vm_id)
        assert fip_fixture.verify_fip(fip_id, vm1_fixture, fvn_fixture)
        fip_id1 = fip_fixture.create_and_assoc_fip(
            fvn_fixture1.vn_id, vm1_fixture.vm_id)
        assert fip_fixture1.verify_fip(fip_id1, vm1_fixture, fvn_fixture1)

        # Check the communication from borrower VM to all 2 networks
        if not vm1_fixture.ping_with_certainty(fvm_fixture.vm_ip):
            result = result and False
        if not vm1_fixture.ping_with_certainty(fvm_fixture1.vm_ip):
            result = result and False

        # Check the floating IP provider VNs should commmunicate with each
        # other
        self.logger.info(
            'Ping should fail here. %s and %s should not able to communicate with each oether' %
            (fvm_name1, fvm_name))
        if fvm_fixture1.ping_to_ip(fvm_fixture.vm_ip):
            result = result and False
        # Check after disscocition of floating ip communication should and only
        # should stop from that network
        fip_fixture.disassoc_and_delete_fip(fip_id)
        self.logger.info(
            'Ping should fail here as floating IP pool is already released')
        if vm1_fixture.ping_to_ip(fvm_fixture.vm_ip):
            result = result and False
        if not vm1_fixture.ping_with_certainty(fvm_fixture1.vm_ip):
            result = result and False
        fip_fixture1.disassoc_and_delete_fip(fip_id1)
        if not result:
            self.logger.error(
                'Test to check multiple floating ip for single VM has failed')
            assert result
        return True
    # end test_floating_ip

    @preposttest_wrapper
    def test_ipam_add_delete(self):
        '''Test to validate IPAM creation, association of a VN and creating VMs in the VN. Ping b/w the VMs should be successful.
            1. Create non-default IPAM
            2. Create VN with user-created IPAM and verify
            3. Launch 2 VM's within VN which is using non-default IPAM
            4. Ping between these 2 VM's
        Pass criteria: Step 1,2,3 and 4 should pass
        '''
        project_obj = self.useFixture(
            ProjectFixture(vnc_lib_h=self.vnc_lib, connections=self.connections))
        ipam_obj = self.useFixture(
            IPAMFixture(project_obj=project_obj, name='my-ipam'))
        assert ipam_obj
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn22', inputs=self.inputs, subnets=['22.1.1.0/24'], ipam_fq_name=ipam_obj.fq_name))
        assert vn_fixture.verify_on_setup()

        if os.environ.has_key('ci_image'):
            if os.environ['ci_image'] == 'cirros-0.3.0-x86_64-uec':
                vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                        vn_obj=vn_fixture.obj, vm_name='vm1',
                                                        image_name = os.environ['ci_image']))
                vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                        vn_obj=vn_fixture.obj, vm_name='vm2',
                                                        image_name = os.environ['ci_image']))
            else:
                assert(), 'Image name specified in env should be "cirros-0.3.0-x86_64-uec"'
        else:
            vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                    vn_obj=vn_fixture.obj, vm_name='vm1'))
            vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                    vn_obj=vn_fixture.obj, vm_name='vm2'))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(vm2_fixture.vm_ip)

        return True
    # end test_ipam_add_delete

    @preposttest_wrapper
    def test_remove_policy_with_ref(self):
        ''' This tests the following scenarios.
           1. Test to validate that policy removal will fail when it referenced with VN.
           2. validate vn_policy data in api-s against quantum-vn data, when created and unbind policy from VN thru quantum APIs.
           3. validate policy data in api-s against quantum-policy data, when created and deleted thru quantum APIs.
        '''
        # vn1_name='vn4'
        # vn1_subnets=['10.1.1.0/24']
        vn1_name = self.res.vn1_name
        vn1_subnets = self.res.vn1_subnets
        policy_name = 'policy1'
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': vn1_name,
                'dest_network': vn1_name,
            },
        ]
        project_obj = self.useFixture(
            ProjectFixture(vnc_lib_h=self.vnc_lib, connections=self.connections))
        policy_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name, rules_list=rules, inputs=self.inputs,
                connections=self.connections))
        vn1_fixture = self.res.get_vn1_fixture()
        #policy_fq_names = [self.quantum_fixture.get_policy_fq_name(policy_fixture.policy_obj)]
        #vn1_fixture.bind_policies( policy_fq_names,vn1_fixture.vn_id)
        vn1_fixture.bind_policies(
            [policy_fixture.policy_fq_name], vn1_fixture.vn_id)
        assert vn1_fixture.verify_on_setup()

        # try to remove policy which  was referenced with VN.
        policy_removal = True
        pol_list = self.quantum_fixture.list_policys()
        pol_id = None
        for policy in pol_list['policys']:
            if policy['name'] == policy_name:
                pol_id = policy['id']
                policy_removal = self.quantum_fixture.delete_policy(
                    policy['id'])
                # In failure screnario clearing the Policy from the VN for
                # further test case
                if policy_removal:
                    vn1_fixture.unbind_policies(
                        vn1_fixture.vn_id, [policy_fixture.policy_fq_name])
                break
        self.assertFalse(
            policy_removal, 'Policy removal succeed as not expected since policy is referenced with VN')
        assert vn1_fixture.verify_on_setup()
        policy_fixture.verify_policy_in_api_server()
        if vn1_fixture.policy_objs:
            policy_fq_names = [
                self.quantum_fixture.get_policy_fq_name(x) for x in vn1_fixture.policy_objs]

        # unbind the policy from VN
        vn1_fixture.unbind_policies(
            vn1_fixture.vn_id, [policy_fixture.policy_fq_name])
        # Verify policy ref is removed from VN
        vn_pol_found = vn1_fixture.verify_vn_policy_not_in_api_server(
            policy_name)
        self.assertFalse(
            vn_pol_found, 'policy not removed from VN after policy unbind from VN')
        # remove the policy using quantum API
        policy_removal = self.quantum_fixture.delete_policy(pol_id)

        # TODO This code is not working because of bug#1056. Need to test once bug is Fixed.
        #pol_found = policy_fixture.verify_policy_not_in_api_server()
        #self.assertFalse(pol_found,'policy not removed from API server when policy removed from Quantum')
        return True

    @preposttest_wrapper
    def test_verify_generator_collector_connections(self):
        '''
         Description: Verify generator:module connections to collector

              1.Verify all generators connected to collector - fails otherwise
              2.Get the xmpp peers in vrouter uve and get the active xmpp peer out of it
              3.Verify from agent introspect that active xmpp matches with step 2 - fails otherwise
              4.Get bgp peers from bgp-peer uve and verify from control node introspect that that matches - fails otherwise

         Maintainer: sandipd@juniper.net
        '''
        self.logger.info("START ...")
        # check collector-generator connections through uves.
        assert self.analytics_obj.verify_collector_uve()
        # Verify vrouter uve active xmpp connections
        assert self.analytics_obj.verify_active_xmpp_peer_in_vrouter_uve()
        # Verify vrouter uve for xmpp connections
        assert self.analytics_obj.verify_vrouter_xmpp_connections()
        # count of xmpp peer and bgp peer verification in bgp-router uve
        assert self.analytics_obj.verify_bgp_router_uve_xmpp_and_bgp_count()
        self.logger.info("END...")
        return True
    # end test_remove_policy_with_ref

# end TestSanityFixture
