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
    def test_broadcast_udp_w_chksum(self):
        ''' Validate Broadcast UDP stream with checksum check enabled .

        '''
        vn1_name = get_random_name('vn30')
        vn1_subnets = ['30.1.1.0/24']
        vn1_vm1_name = get_random_name('vm1')
        vn1_vm2_name = get_random_name('vm2')
        vn1_vm3_name = get_random_name('vm3')
        vn1_vm4_name = get_random_name('vm4')
        result = True
        list_of_ips = ['30.1.1.255', '224.0.0.1', '255.255.255.255']
	vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        assert vn1_fixture.verify_on_setup()

        vm1_fixture = self.create_vm(vn1_fixture,vm_name=vn1_vm1_name,
                flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        vm2_fixture = self.create_vm(vn1_fixture,vm_name=vn1_vm2_name,
                flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        vm2_fixture = self.create_vm(vn1_fixture,vm_name=vn1_vm3_name,
                flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        vm2_fixture = self.create_vm(vn1_fixture,vm_name=vn1_vm4_name,
                flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()
        #self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj )
        #self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj )
        #self.nova_fixture.wait_till_vm_is_up( vm3_fixture.vm_obj )
        #self.nova_fixture.wait_till_vm_is_up( vm4_fixture.vm_obj )

        out1 = vm1_fixture.wait_till_vm_is_up()
        if out1 == False:
            return {'result': out1, 'msg': "%s failed to come up" % vm1_fixture.vm_name}
        else:
            self.logger.info('Installing Traffic package on %s ...' %
                             vm1_fixture.vm_name)
            vm1_fixture.install_pkg("Traffic")

        out2 = vm2_fixture.wait_till_vm_is_up()
        if out2 == False:
            return {'result': out2, 'msg': "%s failed to come up" % vm2_fixture.vm_name}
        else:
            self.logger.info('Installing Traffic package on %s ...' %
                             vm2_fixture.vm_name)
            vm2_fixture.install_pkg("Traffic")

        out3 = vm3_fixture.wait_till_vm_is_up()
        if out3 == False:
            return {'result': out3, 'msg': "%s failed to come up" % vm3_fixture.vm_name}
        else:
            self.logger.info('Installing Traffic package on %s ...' %
                             vm3_fixture.vm_name)
            vm3_fixture.install_pkg("Traffic")

        out4 = vm4_fixture.wait_till_vm_is_up()
        if out4 == False:
            return {'result': out4, 'msg': "%s failed to come up" % vm4_fixture.vm_name}
        else:
            self.logger.info('Installing Traffic package on %s ...' %
                             vm4_fixture.vm_name)
            vm4_fixture.install_pkg("Traffic")

        # Starting Multicast_UDP
        for ips in list_of_ips:
            self.logger.info("-" * 80)
            self.logger.info('Sending UDP packets to %s' % ips)
            self.logger.info("-" * 80)
            stream = Stream(protocol="ip", proto="udp",
                            src=vm1_fixture.vm_ip, dst=ips, dport=9000)
            profile = ContinuousProfile(
                stream=stream, listener=ips, capfilter="udp port 8000", chksum=True)

            tx_vm_node_ip = self.inputs.host_data[
                self.nova_fixture.get_nova_host_of_vm(vm1_fixture.vm_obj)]['host_ip']
            rx1_vm_node_ip = self.inputs.host_data[
                self.nova_fixture.get_nova_host_of_vm(vm2_fixture.vm_obj)]['host_ip']
            rx2_vm_node_ip = self.inputs.host_data[
                self.nova_fixture.get_nova_host_of_vm(vm3_fixture.vm_obj)]['host_ip']
            rx3_vm_node_ip = self.inputs.host_data[
                self.nova_fixture.get_nova_host_of_vm(vm4_fixture.vm_obj)]['host_ip']

            tx_local_host = Host(
                tx_vm_node_ip, self.inputs.username, self.inputs.password)
            rx1_local_host = Host(
                rx1_vm_node_ip, self.inputs.username, self.inputs.password)
            rx2_local_host = Host(
                rx2_vm_node_ip, self.inputs.username, self.inputs.password)
            rx3_local_host = Host(
                rx3_vm_node_ip, self.inputs.username, self.inputs.password)

            send_host = Host(vm1_fixture.local_ip,
                             vm1_fixture.vm_username, vm1_fixture.vm_password)
            recv_host1 = Host(vm2_fixture.local_ip,
                              vm2_fixture.vm_username, vm2_fixture.vm_password)
            recv_host2 = Host(vm3_fixture.local_ip,
                              vm3_fixture.vm_username, vm3_fixture.vm_password)
            recv_host3 = Host(vm4_fixture.local_ip,
                              vm4_fixture.vm_username, vm4_fixture.vm_password)

            sender = Sender("sendudp", profile, tx_local_host,
                            send_host, self.inputs.logger)
            receiver1 = Receiver("recvudp", profile,
                                 rx1_local_host, recv_host1, self.inputs.logger)
            receiver2 = Receiver("recvudp", profile,
                                 rx2_local_host, recv_host2, self.inputs.logger)
            receiver3 = Receiver("recvudp", profile,
                                 rx3_local_host, recv_host3, self.inputs.logger)

            receiver1.start()
            receiver2.start()
            receiver3.start()
            sender.start()

            # Poll to make sure traffic flows, optional
            sender.poll()
            receiver1.poll()
            receiver2.poll()
            receiver3.poll()
            sender.stop()
            receiver1.stop()
            receiver2.stop()
            receiver3.stop()
            self.logger.info(
                '%s sent %s packets to %s. %s received %s packets out of which %s are Corrupted' %
                (vm1_fixture.vm_name, sender.sent, ips, vm2_fixture.vm_name, receiver1.recv, receiver1.corrupt))
            self.logger.info(
                '%s sent %s packets to %s. %s received %s packets out of which %s are Corrupted' %
                (vm1_fixture.vm_name, sender.sent, ips, vm3_fixture.vm_name, receiver2.recv, receiver2.corrupt))
            self.logger.info(
                '%s sent %s packets to %s. %s received %s packets out of which %s are Corrupted' %
                (vm1_fixture.vm_name, sender.sent, ips, vm4_fixture.vm_name, receiver3.recv, receiver3.corrupt))

            corrupt_list = [receiver1.corrupt,
                            receiver2.corrupt, receiver3.corrupt]
            for i in corrupt_list:
                if(i > 0):
                    result = False
            if(sender.sent == receiver1.recv == receiver2.recv == receiver3.recv):
                self.logger.info("Packets seen on all the receivers")
            else:
                self.logger.error("Packet Drops seen")
                result = False
            print result
        msg = "Packets not Broadcasted"
        self.assertEqual(result, True, msg)
        return True
    # end broadcast_udp_w_chksum

    @preposttest_wrapper
    def test_bulk_add_delete(self):
        '''
        Validate adding multiple vms in bulk and deleting them in one shot
        '''
        vn1_name = "bulk_test_vn1"
        vn1_name = get_random_name(vn1_name)
        vn1_subnets = ['101.1.1.0/24']
	vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        assert vn1_fixture.verify_on_setup(), "Verification of VN %s failed" % (
            vn1_name)

        # Create 15 VMs in bulk
        vm_count = 15
        vmx_fixture = self.useFixture(
            VMFixture(project_name=self.inputs.project_name,
                      connections=self.connections, vn_obj=vn1_fixture.obj,
                      vm_name=vn1_name, count=vm_count, image_name='cirros-0.3.0-x86_64-uec',
                      flavor='m1.tiny'))
        assert vmx_fixture.verify_vm_launched(), 'One or more VMs do not seem' \
            ' to have got launched. Please check logs'

        # Delete all vms now
        self.remove_from_cleanups(vmx_fixture)
        vmx_fixture.cleanUp(), 'Cleanup failed for atleast one VM, Check logs'
        assert vmx_fixture.verify_vm_not_in_nova(), 'Atleast 1 VM not deleted ' \
            ' in Nova, Pls check logs'

        return True
    # end test_bulk_add_delete

    @preposttest_wrapper
    def test_disassociate_vn_from_vm(self):
        ''' Test to validate that disassociating a VN from a VM fails.
        '''
        vm1_name = get_random_name('vm_mine')
        vn_name = get_random_name('vn222')
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        try:
            self.logger.info(' Will try deleting the VN now')
            self.vnc_lib.virtual_network_delete(id=vn_obj['network']['id'])
            assert vn_fixture.verify_on_setup()
            assert vm1_fixture.verify_on_setup()
        except RefsExistError as e:
            self.logger.info(
                'RefsExistError:Check passed that the VN cannot be disassociated/deleted when the VM exists')

        return True
    # end test_disassociate_vn_from_vm

    @preposttest_wrapper
    def test_duplicate_vn_add(self):
        '''Test to validate adding a Duplicate VN creation and deletion.
        '''
        vn_obj1 = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn22', inputs=self.inputs, subnets=['22.1.1.0/24']))
        assert vn_obj1.verify_on_setup()
        assert vn_obj1

        vn_obj2 = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn22', inputs=self.inputs, subnets=['22.1.1.0/24']))
        assert vn_obj2.verify_on_setup()
        assert vn_obj2, 'Duplicate VN cannot be created'
        if (vn_obj1.vn_id == vn_obj2.vn_id):
            self.logger.info('Same obj created')
        else:
            self.logger.error('Different objs created.')
        return True
    # end test_duplicate_vn_add

    @preposttest_wrapper
    def test_host_route_add_delete(self):
        ''' Test to validate that host_route is sent to the  VM via DHCP.
        '''
        vm1_name = get_random_name('va_mine')
        vm2_name = get_random_name('vm_yours')
        vn_name = get_random_name('vn222')
        vn_subnets = ['11.1.1.0/24']
        host_rt = ['1.1.1.1/32', '0.0.0.0/0']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_fixture.add_host_routes(host_rt)
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name, flavor='contrail_flavor_small', image_name='ubuntu-traffic'))
        assert vm1_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        route_cmd = 'route -n'
        vm1_fixture.run_cmd_on_vm(cmds=[route_cmd], as_sudo=True)
        output = vm1_fixture.return_output_cmd_dict[route_cmd]
        self.logger.info('%s' % output)
        for rt in host_rt:
            if (rt.split('/')[0]) in output:
                self.logger.info('Route to %s found in the route-table' % rt)
                result = True
            else:
                self.logger.info(
                    'Route to %s not found in the route-table' % rt)
                result = False
        assert result, 'No Host-Route in the route-table'

        vn_fixture.del_host_routes(host_rt)
        vn_obj = vn_fixture.obj
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm2_name, project_name=self.inputs.project_name, flavor='contrail_flavor_small', image_name='ubuntu-traffic'))
        assert vm2_fixture.verify_on_setup()
        vm2_fixture.wait_till_vm_is_up()
        new_route_cmd = 'route -n'
        vm2_fixture.run_cmd_on_vm(cmds=[new_route_cmd], as_sudo=True)
        new_output = vm2_fixture.return_output_cmd_dict[new_route_cmd]
        self.logger.info('%s' % new_output)
        for rt in host_rt:
            route_ip = rt.split('/')[0]
            if "0.0.0.0" in rt:
                self.logger.info('Skip verifying default route')
                continue
            if re.search(r'\broute_ip\b', new_output):
                self.logger.info('Route to %s found in the route-table' % rt)
                new_result = False
            else:
                self.logger.info(
                    'Route to %s not found in the route-table' % rt)
                new_result = True
        assert new_result, 'Host-Route still found in the route-table'

        return True
    # end test_host_route_add_delete

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_ipam_add_delete(self):
        '''Test to validate IPAM creation, association of a VN and creating VMs in the VN. Ping b/w the VMs should be successful.
        '''
        #project_obj = self.useFixture(
        #    ProjectFixture(vnc_lib_h=self.vnc_lib, connections=self.connections))
        ipam_obj = self.useFixture(
            IPAMFixture(project_obj=self.project, name=get_random_name('my-ipam')))
        assert ipam_obj.verify_on_setup()
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name = get_random_name('vn22'), inputs=self.inputs, subnets=['22.1.1.0/24'], ipam_fq_name=ipam_obj.fq_name))
        assert vn_fixture.verify_on_setup()

        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,project_name = self.inputs.project_name,
                                                vn_obj=vn_fixture.obj, vm_name=get_random_name('vm1')))
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,project_name = self.inputs.project_name,
                                                vn_obj=vn_fixture.obj, vm_name=get_random_name('vm2')))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)

        return True
    # end test_ipam_add_delete

    @preposttest_wrapper
    def test_multiple_metadata_service_scale(self):
        ''' Test to metadata service scale.
        '''

        vm1_name=get_random_name('vm_min')
        vn_name=get_random_name('vn1111')
        ts = time.time()
        vn_name = '%s_%s'%(inspect.stack()[0][3],str(ts))
        vn_subnets=['111.1.1.0/24']
        vn_fixture= self.useFixture(VNFixture(project_name= self.project.project_name, connections= self.connections,
                     vn_name=vn_name, inputs= self.inputs, subnets= vn_subnets))
        vn_obj= vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name,
                                                image_name='cirros-0.3.0-x86_64-uec', flavor='m1.tiny'))

        text = """#!/bin/sh
echo "Hello World.  The time is now $(date -R)!" | tee /tmp/output.txt
               """
        try:
            with open ("/tmp/metadata_script.txt" , "w") as f:
                f.write(text)
        except Exception as e:
            self.logger.exception("Got exception while creating /tmp/metadata_script.txt as %s"%(e))


        vm1_name = get_random_name('vm_mine')
        vn_name = get_random_name('vn222')
        ts = time.time()
        vn_name = get_random_name('vn')
        vn_subnets=['11.1.1.0/24']
        vn_count_for_test=20
        if (len(self.inputs.compute_ips) == 1):
            vn_count_for_test=2
        try:
            vm_fixture = self.useFixture(
                create_multiple_vn_and_multiple_vm_fixture(
                    connections=self.connections,
                    vn_name=vn_name, vm_name=vm1_name, inputs=self.inputs, project_name=self.inputs.project_name,
                    subnets=vn_subnets, vn_count=vn_count_for_test, vm_count=1, subnet_count=1, userdata='/tmp/metadata_script.txt',
                    image_name='cirros-0.3.0-x86_64-uec', flavor='m1.tiny'))
            compute_ip=[]
            time.sleep(30)
        except Exception as e:
            self.logger.exception("Got exception as %s"%(e))
        try:
            assert vm_fixture.verify_vms_on_setup()
            assert vm_fixture.verify_vns_on_setup()
        except Exception as e:
            self.logger.exception("Got exception as %s"%(e))

        cmd = 'ls /tmp/'
        result = True
        for vmobj in vm_fixture.vm_obj_dict.values():
            ret = vmobj.run_cmd_on_vm(cmds = [cmd])
            for elem in ret.values():
                if 'output.txt' in elem:
                    result = result and True
                    break
            if not result:
                self.logger.warn("metadata_script.txt did not get executed in the vm")
                result = result and False
            else:
                self.logger.info("Printing the output.txt :")
                cmd = 'cat /tmp/output.txt'
                ret = vmobj.run_cmd_on_vm(cmds = [cmd])
                self.logger.info("%s" %(ret.values()))
                for elem in ret.values():
                    if 'Hello World' in elem:
                        result = result and True
                    else:
                        self.logger.warn("metadata_script.txt did not get executed in the vm...output.txt does not contain proper output")
                        result = result and False
        assert result
        return True

    @preposttest_wrapper
    def test_policy_between_vns_diff_proj(self):
        ''' Test to validate that policy to deny and pass under different projects should behave accordingly.
        '''
        vm_names = ['vm_100', 'vm_200', 'vm_300', 'vm_400']
        vn_names = ['vn_100', 'vn_200', 'vn_300', 'vn_400']
        vn_subnets = [['10.1.1.0/24'], ['20.1.1.0/24'],
                      ['30.1.1.0/24'], ['40.1.1.0/24']]
        projects = ['project111', 'project222']
        policy_names = ['policy1', 'policy2', 'policy3', 'policy4']
        rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': vn_names[0],
                'dest_network': vn_names[1],
            },
        ]
        rev_rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'icmp',
                'source_network': vn_names[1],
                'dest_network': vn_names[0],
            },
        ]
        rules1 = [
            {
                'direction': '<>', 'simple_action': 'deny',
                'protocol': 'icmp',
                'source_network': vn_names[2],
                'dest_network': vn_names[3],
            },
        ]
        rev_rules1 = [
            {
                'direction': '<>', 'simple_action': 'deny',
                'protocol': 'icmp',
                'source_network': vn_names[3],
                'dest_network': vn_names[2],
            },
        ]

        user_list = [('gudi', 'gudi123', 'admin'), ('mal', 'mal123', 'admin')]
        user1_fixture= self.useFixture(UserFixture(connections=self.connections,
            username=user_list[0][0], password=user_list[0][1]))
        project_fixture1 = self.useFixture(
            ProjectFixture(
                project_name=projects[
                    0], vnc_lib_h=self.vnc_lib, username=user_list[0][0],
                password=user_list[0][1], connections=self.connections))
        user1_fixture.add_user_to_tenant(projects[0], user_list[0][0] , user_list[0][2])
        project_inputs1 = self.useFixture(
            ContrailTestInit(
                self.ini_file, stack_user=project_fixture1.username,
                stack_password=project_fixture1.password, project_fq_name=['default-domain', projects[0]],logger = self.logger))
        project_connections1 = ContrailConnections(project_inputs1,self.logger)

        user2_fixture= self.useFixture(UserFixture(connections=self.connections,
            username=user_list[1][0], password=user_list[1][1]))
        project_fixture2 = self.useFixture(
            ProjectFixture(
                project_name=projects[
                    1], vnc_lib_h=self.vnc_lib, username=user_list[1][0],
                password=user_list[1][1], connections=self.connections))
        user2_fixture.add_user_to_tenant(projects[1], user_list[1][0] , user_list[1][2])
        project_inputs2 = self.useFixture(
            ContrailTestInit(
                self.ini_file, stack_user=project_fixture2.username,
                stack_password=project_fixture2.password, project_fq_name=['default-domain', projects[1]], logger = self.logger))
        project_connections2 = ContrailConnections(project_inputs2 , self.logger)

        self.logger.info(
            'We will now create policy to allow in project %s and check that ping passes between the VMs' % (projects[0]))

        policy1_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_names[
                    0], rules_list=rules, inputs=project_inputs1,
                connections=project_connections1))
        policy2_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_names[
                    1], rules_list=rev_rules, inputs=project_inputs1,
                connections=project_connections1))

        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=projects[0], connections=project_connections1,
                vn_name=vn_names[0], inputs=project_inputs1, subnets=vn_subnets[0], policy_objs=[policy1_fixture.policy_obj]))
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=projects[0], connections=project_connections1,
                vn_name=vn_names[1], inputs=project_inputs1, subnets=vn_subnets[1], policy_objs=[policy2_fixture.policy_obj]))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(
            VMFixture(connections=project_connections1,
                      vn_obj=vn1_fixture.obj, vm_name=vm_names[0], project_name=projects[0]))
        vm2_fixture = self.useFixture(
            VMFixture(connections=project_connections1,
                      vn_obj=vn2_fixture.obj, vm_name=vm_names[1], project_name=projects[0]))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)

        self.logger.info(
            'We will now create policy to deny in project %s and check that ping fails between the VMs' % (projects[1]))

        policy3_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_names[
                    2], rules_list=rules1, inputs=project_inputs2,
                connections=project_connections2))
        policy4_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_names[
                    3], rules_list=rev_rules1, inputs=project_inputs2,
                connections=project_connections2))

        vn3_fixture = self.useFixture(
            VNFixture(
                project_name=projects[1], connections=project_connections2,
                vn_name=vn_names[2], inputs=project_inputs2, subnets=vn_subnets[2], policy_objs=[policy3_fixture.policy_obj]))
        vn4_fixture = self.useFixture(
            VNFixture(
                project_name=projects[1], connections=project_connections2,
                vn_name=vn_names[3], inputs=project_inputs2, subnets=vn_subnets[3], policy_objs=[policy4_fixture.policy_obj]))
        assert vn3_fixture.verify_on_setup()
        assert vn4_fixture.verify_on_setup()

        vm3_fixture = self.useFixture(
            VMFixture(connections=project_connections2,
                      vn_obj=vn3_fixture.obj, vm_name=vm_names[2], project_name=projects[1]))
        vm4_fixture = self.useFixture(
            VMFixture(connections=project_connections2,
                      vn_obj=vn4_fixture.obj, vm_name=vm_names[3], project_name=projects[1]))
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()

        vm3_fixture.wait_till_vm_is_up()
        vm4_fixture.wait_till_vm_is_up()
        assert not vm4_fixture.ping_to_ip(vm3_fixture.vm_ip)
        return True
    # end test_policy_between_vns_diff_proj

    @preposttest_wrapper
    def test_diff_proj_same_vn_vm_add_delete(self):
        ''' Test to validate that a VN and VM with the same name and same subnet can be created in two different projects
        '''
        vm_name = 'vm_mine'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        projects = ['project111', 'project222']
        user_list = [('gudi', 'gudi123', 'admin'), ('mal', 'mal123', 'admin')]

        user1_fixture= self.useFixture(
            UserFixture(
                connections=self.connections, username=user_list[0][0], password=user_list[0][1]))
        project_fixture1 = self.useFixture(
            ProjectFixture(
                project_name=projects[
                    0], vnc_lib_h=self.vnc_lib, username=user_list[0][0],
                password=user_list[0][1], connections=self.connections))
        user1_fixture.add_user_to_tenant(projects[0], user_list[0][0] , user_list[0][2])
        project_inputs1 = self.useFixture(
            ContrailTestInit(
                self.ini_file, stack_user=project_fixture1.username,
                stack_password=project_fixture1.password, project_fq_name=['default-domain', projects[0]] , logger = self.logger))
        project_connections1 = ContrailConnections(project_inputs1 , self.logger)

        user2_fixture= self.useFixture(
            UserFixture(
                connections=self.connections, username=user_list[1][0], password=user_list[1][1]))        
        project_fixture2 = self.useFixture(
            ProjectFixture(
                project_name=projects[
                    1], vnc_lib_h=self.vnc_lib, username=user_list[1][0],
                password=user_list[1][1], connections=self.connections))
        user2_fixture.add_user_to_tenant(projects[1], user_list[1][0] , user_list[1][2])
        project_inputs2 = self.useFixture(
            ContrailTestInit(
                self.ini_file, stack_user=project_fixture2.username,
                stack_password=project_fixture2.password, project_fq_name=['default-domain', projects[1]], logger = self.logger))
        project_connections2 = ContrailConnections(project_inputs2 , self.logger)

        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=projects[0], connections=project_connections1,
                vn_name=vn_name, inputs=project_inputs1, subnets=vn_subnets))

        assert vn1_fixture.verify_on_setup()
        vn1_obj = vn1_fixture.obj

        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=projects[1], connections=project_connections2,
                vn_name=vn_name, inputs=project_inputs2, subnets=vn_subnets))

        assert vn2_fixture.verify_on_setup()
        vn2_obj = vn2_fixture.obj

        vm1_fixture = self.useFixture(
            VMFixture(connections=project_connections1,
                      vn_obj=vn1_obj, vm_name=vm_name, project_name=projects[0]))
        vm2_fixture = self.useFixture(
            VMFixture(connections=project_connections2,
                      vn_obj=vn2_obj, vm_name=vm_name, project_name=projects[1]))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        if not vm1_fixture.agent_label == vm2_fixture.agent_label:
            self.logger.info("Correct label assigment")
        else:
            self.logger.error(
                "The same label has been assigned for both the VMs")
            return False
        return True
    # end test_diff_proj_same_vn_vm_add_delete

class TestBasicVMVN1(BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicVMVN1, cls).setUpClass()

    @preposttest_wrapper
    def test_no_frag_in_vm(self):
        ''' Validate that VM should not fragment packets and that Vrouter does it.
        '''
        vn1_name = get_random_name('vn30')
        vn1_subnets = ['30.1.1.0/24']
        vn1_vm1_name = get_random_name('vm1')
        vn1_vm2_name = get_random_name('vm2')
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name=vn1_vm1_name))
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name=vn1_vm2_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        out1 = vm1_fixture.wait_till_vm_is_up()
        if out1 == False:
            return {'result': out1, 'msg': "%s failed to come up" % vm1_fixture.vm_name}
        else:
            self.logger.info('Will install Traffic package on %s' %
                             vm1_fixture.vm_name)
            vm1_fixture.install_pkg("Traffic")

        out2 = vm2_fixture.wait_till_vm_is_up()
        if out2 == False:
            return {'result': out2, 'msg': "%s failed to come up" % vm2_fixture.vm_name}
        else:
            sleep(10)
            self.logger.info('Will install Traffic package on %s' %
                             vm2_fixture.vm_name)
            vm2_fixture.install_pkg("Traffic")

        # vm1_fixture.install_pkg("Traffic")
        # vm2_fixture.install_pkg("Traffic")
        result = True
        msg = []
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['icmp']
        total_streams = {}
        total_streams['icmp'] = 1
        dpi = 9100
        packet_size = 2000
        cmd_to_increase_mtu = ['ifconfig eth0 mtu 3000']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu)
        vm2_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu)
        for proto in traffic_proto_l:
            traffic_obj[proto] = {}
            startStatus[proto] = {}
            traffic_obj[proto] = self.useFixture(
                traffic_tests.trafficTestFixture(self.connections))
            startStatus[proto] = traffic_obj[proto].startTraffic(
                num_streams=total_streams[proto], start_port=dpi,
                tx_vm_fixture=vm1_fixture, rx_vm_fixture=vm2_fixture, stream_proto=proto, packet_size=packet_size)
            self.logger.info("Status of start traffic : %s, %s, %s" %
                             (proto, vm1_fixture.vm_ip, startStatus[proto]))
            cmd_to_tcpdump = [
                'nohup tcpdump -i eth0 icmp -vvv -c 10 > /tmp/out.log']
            vm1_fixture.run_cmd_on_vm(cmds=cmd_to_tcpdump)
            i = 'cat /tmp/out.log'
            cmd_to_output = ['cat /tmp/out.log']
            vm1_fixture.run_cmd_on_vm(cmds=cmd_to_output)
            output = vm1_fixture.return_output_cmd_dict[i]
            print output
            if 'DF' in output:
                result = False
        return result
    # end test_no_frag_in_vm


class TestBasicVMVN2(BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicVMVN2, cls).setUpClass()

    def runTest(self):
        pass
    #end runTes
 
    @preposttest_wrapper
    def test_ping_on_broadcast_multicast_with_frag(self):
        ''' Validate Ping on subnet broadcast,link local multucast,network broadcastwith packet sizes > MTU and see that fragmentation and assembly work fine .

        '''
        vn1_name = get_random_name('vn30')
        vn1_subnets = ['30.1.1.0/24']
        ping_count = '5'
        vn1_vm1_name = get_random_name('vm1')
        vn1_vm2_name = get_random_name('vm2')
        vn1_vm3_name = get_random_name('vm3')
        vn1_vm4_name = get_random_name('vm4')
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
        vm3_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm3_name))
        vm4_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm4_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        vm3_fixture.wait_till_vm_is_up()
        vm4_fixture.wait_till_vm_is_up()

        # Geting the VM ips
        vm1_ip = vm1_fixture.vm_ip
        vm2_ip = vm2_fixture.vm_ip
        vm3_ip = vm3_fixture.vm_ip
        vm4_ip = vm4_fixture.vm_ip
        ip_list = [vm1_ip, vm2_ip, vm3_ip, vm4_ip]
        list_of_ip_to_ping = ['30.1.1.255', '224.0.0.1', '255.255.255.255']
        # passing command to vms so that they respond to subnet broadcast
        cmd_list_to_pass_vm = [
            'echo 0 > /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm2_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm3_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm4_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        for dst_ip in list_of_ip_to_ping:
            print 'pinging from %s to %s' % (vm1_ip, dst_ip)
# pinging from Vm1 to subnet broadcast
            ping_output = vm1_fixture.ping_to_ip(
                dst_ip, return_output=True, count=ping_count,  size='3000', other_opt='-b')
            self.logger.info(
                'The packet is not fragmanted because of the smaller MTU')
            expected_result = 'Message too long'
            assert (expected_result in ping_output)

        self.logger.info('Will change the MTU of the VMs and try again')
        cmd_to_increase_mtu = ['ifconfig eth0 mtu 9000']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True)
        vm2_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True)
        vm3_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True)
        vm4_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True)

        for dst_ip in list_of_ip_to_ping:
            print 'pinging from %s to %s' % (vm1_ip, dst_ip)
# pinging from Vm1 to subnet broadcast
            ping_output = vm1_fixture.ping_to_ip(
                dst_ip, return_output=True, count=ping_count,  size='3000', other_opt='-b')
            expected_result = 'Message too long'
            assert (expected_result not in ping_output)

# getting count of ping response from each vm
            string_count_dict = {}
            string_count_dict = get_string_match_count(ip_list, ping_output)
            print string_count_dict
            for k in ip_list:
                # this is a workaround : ping utility exist as soon as it gets
                # one response
                assert (string_count_dict[k] >= (int(ping_count) - 1))
        return True
    # end test_ping_on_broadcast_multicast_with_frag

    @preposttest_wrapper
    def test_ping_on_broadcast_multicast(self):
        ''' Validate Ping on subnet broadcast,link local multucast,network broadcast .

        '''
        result = True
        vn1_name = get_random_name('vn1')
        vn1_subnets = ["192.168.1.0/24"]
        ping_count = '5'
        vn1_vm1_name = get_random_name('vn1_vm1')
        vn1_vm2_name = get_random_name('vn1_vm2')
        vn1_vm3_name = get_random_name('vn1_vm3')
        vn1_vm4_name = get_random_name('vn1_vm4')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name)
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name)
        vm3_fixture = self.create_vm(vn1_fixture, vn1_vm3_name)
        vm4_fixture = self.create_vm(vn1_fixture, vn1_vm4_name)
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

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_ping_within_vn(self):
        ''' Validate Ping between two VMs within a VN.

        '''
        vn1_name = get_random_name('vn30')
        vn1_subnets = ['30.1.1.0/24']
        vn1_vm1_name = get_random_name('vm1')
        vn1_vm2_name = get_random_name('vm2')
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
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)
        assert vm2_fixture.ping_to_ip(vm1_fixture.vm_ip)
        return True
    # end test_ping_within_vn

    @preposttest_wrapper
    def test_ping_on_broadcast_multicast_with_frag(self):
        ''' Validate Ping on subnet broadcast,link local multucast,network broadcastwith packet sizes > MTU and see that fragmentation and assembly work fine .

        '''
        vn1_name = get_random_name('vn30')
        vn1_subnets = ['30.1.1.0/24']
        ping_count = '5'
        vn1_vm1_name = 'vm1'
        vn1_vm2_name = 'vm2'
        vn1_vm3_name = 'vm3'
        vn1_vm4_name = 'vm4'
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
        vm3_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm3_name))
        vm4_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm4_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        vm3_fixture.wait_till_vm_is_up()
        vm4_fixture.wait_till_vm_is_up()

        # Geting the VM ips
        vm1_ip = vm1_fixture.vm_ip
        vm2_ip = vm2_fixture.vm_ip
        vm3_ip = vm3_fixture.vm_ip
        vm4_ip = vm4_fixture.vm_ip
        ip_list = [vm1_ip, vm2_ip, vm3_ip, vm4_ip]
        list_of_ip_to_ping = ['30.1.1.255', '224.0.0.1', '255.255.255.255']
        # passing command to vms so that they respond to subnet broadcast
        cmd_list_to_pass_vm = [
            'echo 0 > /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm2_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm3_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm4_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        for dst_ip in list_of_ip_to_ping:
            print 'pinging from %s to %s' % (vm1_ip, dst_ip)
# pinging from Vm1 to subnet broadcast
            ping_output = vm1_fixture.ping_to_ip(
                dst_ip, return_output=True, count=ping_count,  size='3000', other_opt='-b')
            self.logger.info(
                'The packet is not fragmanted because of the smaller MTU')
            expected_result = 'Message too long'
            assert (expected_result in ping_output)

        self.logger.info('Will change the MTU of the VMs and try again')
        cmd_to_increase_mtu = ['ifconfig eth0 mtu 9000']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True)
        vm2_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True)
        vm3_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True)
        vm4_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True)

        for dst_ip in list_of_ip_to_ping:
            print 'pinging from %s to %s' % (vm1_ip, dst_ip)
# pinging from Vm1 to subnet broadcast
            ping_output = vm1_fixture.ping_to_ip(
                dst_ip, return_output=True, count=ping_count,  size='3000', other_opt='-b')
            expected_result = 'Message too long'
            assert (expected_result not in ping_output)

# getting count of ping response from each vm
            string_count_dict = {}
            string_count_dict = get_string_match_count(ip_list, ping_output)
            print string_count_dict
            for k in ip_list:
                # this is a workaround : ping utility exist as soon as it gets
                # one response
                assert (string_count_dict[k] >= (int(ping_count) - 1))
        return True
    # end test_ping_on_broadcast_multicast_with_frag

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_ping_within_vn_two_vms_two_different_subnets(self):
        ''' Validate Ping between two VMs within a VN-2 vms in 2 different subnets.
            Validate ping to subnet broadcast not responded back by other vm
            Validate ping to network broadcast (all 255) is responded back by other vm

        '''
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
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)
        assert vm2_fixture.ping_to_ip(vm1_fixture.vm_ip)
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
    #test_ping_within_vn_two_vms_two_different_subnets 
    
    @preposttest_wrapper
    def itest_policy_between_vns_diff_proj(self):
        ''' Test to validate that policy to deny and pass under different projects should behave accordingly.
        '''
        vm_names=['vm_100', 'vm_200', 'vm_300', 'vm_400']
        vn_names=['vn_100', 'vn_200', 'vn_300', 'vn_400']
        vn_subnets=[['10.1.1.0/24'], ['20.1.1.0/24'], ['30.1.1.0/24'],['40.1.1.0/24']]
        projects=['project111', 'project222']
        policy_names= ['policy1','policy2', 'policy3', 'policy4']
        rules= [
            {
               'direction'     : '<>', 'simple_action' : 'pass',
               'protocol'      : 'icmp',
               'source_network': vn_names[0],
               'dest_network'  : vn_names[1],
             },
                ]
        rev_rules= [
            {
               'direction'     : '<>', 'simple_action' : 'pass',
               'protocol'      : 'icmp',
               'source_network': vn_names[1],
               'dest_network'  : vn_names[0],
             },
                ]
        rules1= [
            {
               'direction'     : '<>', 'simple_action' : 'deny',
               'protocol'      : 'icmp',
               'source_network': vn_names[2],
               'dest_network'  : vn_names[3],
             },
                ]
        rev_rules1= [
            {
               'direction'     : '<>', 'simple_action' : 'deny',
               'protocol'      : 'icmp',
               'source_network': vn_names[3],
               'dest_network'  : vn_names[2],
            },
                ]

        user_list = [('gudi', 'gudi123', 'admin'), ('mal', 'mal123', 'admin')]
        user1_fixture= self.useFixture(UserFixture(connections=self.connections,
            username=user_list[0][0], password=user_list[0][1]))
        project_fixture1 = self.useFixture(ProjectFixture(project_name = projects[0],vnc_lib_h= self.vnc_lib,username=user_list[0][0],
            password= user_list[0][1],connections= self.connections))
        user1_fixture.add_user_to_tenant(projects[0], user_list[0][0] , user_list[0][2])
        project_inputs1= self.useFixture(ContrailTestInit(self.ini_file, stack_user=project_fixture1.username,
            stack_password=project_fixture1.password,project_fq_name=['default-domain',projects[0]],logger = self.logger))
        project_connections1= ContrailConnections(project_inputs1,self.logger)

        user2_fixture= self.useFixture(UserFixture(connections=self.connections,
            username=user_list[1][0], password=user_list[1][1]))
        project_fixture2 = self.useFixture(ProjectFixture(project_name = projects[1],vnc_lib_h= self.vnc_lib,username=user_list[1][0],
            password= user_list[1][1],connections= self.connections))
        user2_fixture.add_user_to_tenant(projects[1], user_list[1][0] , user_list[1][2])
        project_inputs2= self.useFixture(ContrailTestInit(self.ini_file, stack_user=project_fixture2.username,
            stack_password=project_fixture2.password,project_fq_name=['default-domain',projects[1]],logger = self.logger))
        project_connections2= ContrailConnections(project_inputs2 , self.logger)

        self.logger.info('We will now create policy to allow in project %s and check that ping passes between the VMs'%(projects[0]))

        policy1_fixture= self.useFixture( PolicyFixture( policy_name= policy_names[0], rules_list= rules, inputs= project_inputs1,
            connections= project_connections1 ))
        policy2_fixture= self.useFixture( PolicyFixture( policy_name= policy_names[1], rules_list= rev_rules, inputs= project_inputs1,
            connections= project_connections1 ))

        vn1_fixture= self.useFixture(VNFixture(project_name= projects[0], connections= project_connections1,
            vn_name=vn_names[0], inputs= project_inputs1, subnets= vn_subnets[0], policy_objs=[policy1_fixture.policy_obj]))
        vn2_fixture= self.useFixture(VNFixture(project_name= projects[0], connections= project_connections1,
            vn_name=vn_names[1], inputs= project_inputs1, subnets= vn_subnets[1], policy_objs=[policy2_fixture.policy_obj]))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(
            VMFixture(connections=project_connections1,
                      vn_obj=vn1_fixture.obj, vm_name=vm_names[0], project_name=projects[0]))
        vm2_fixture = self.useFixture(
            VMFixture(connections=project_connections1,
                      vn_obj=vn2_fixture.obj, vm_name=vm_names[1], project_name=projects[0]))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        self.nova_fixture.wait_till_vm_is_up( vm1_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vm2_fixture.vm_obj )
        assert vm1_fixture.ping_to_ip( vm2_fixture.vm_ip )
        self.logger.info('We will now create policy to deny in project %s and check that ping fails between the VMs'%(projects[1]))

        policy3_fixture= self.useFixture( PolicyFixture( policy_name= policy_names[2], rules_list= rules1, inputs= project_inputs2,
                                    connections= project_connections2 ))
        policy4_fixture= self.useFixture( PolicyFixture( policy_name= policy_names[3], rules_list= rev_rules1, inputs= project_inputs2,
                                    connections= project_connections2 ))

        vn3_fixture= self.useFixture(VNFixture(project_name= projects[1], connections= project_connections2,
                     vn_name=vn_names[2], inputs= project_inputs2, subnets= vn_subnets[2], policy_objs=[policy3_fixture.policy_obj]))
        vn4_fixture= self.useFixture(VNFixture(project_name= projects[1], connections= project_connections2,
                     vn_name=vn_names[3], inputs= project_inputs2, subnets= vn_subnets[3], policy_objs=[policy4_fixture.policy_obj]))
        assert vn3_fixture.verify_on_setup()
        assert vn4_fixture.verify_on_setup()
        vm3_fixture = self.useFixture(
            VMFixture(connections=project_connections2,
                      vn_obj=vn3_fixture.obj, vm_name=vm_names[2], project_name=projects[1]))
        vm4_fixture = self.useFixture(
            VMFixture(connections=project_connections2,
                      vn_obj=vn4_fixture.obj, vm_name=vm_names[3], project_name=projects[1]))

        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()

        self.nova_fixture.wait_till_vm_is_up( vm3_fixture.vm_obj )
        self.nova_fixture.wait_till_vm_is_up( vm4_fixture.vm_obj )
        assert not vm4_fixture.ping_to_ip( vm3_fixture.vm_ip )
        return True
    #end test_policy_between_vns_diff_proj


    @preposttest_wrapper
    def test_release_ipam(self):
        '''Test to validate that IPAM cannot be deleted until the VM associated with it is deleted.
        '''
        #project_obj = self.useFixture(
        #    ProjectFixture(vnc_lib_h=self.vnc_lib, connections=self.connections))
        ipam_obj = self.useFixture(
            IPAMFixture(project_obj=self.project, name='my-ipam'))
        assert ipam_obj.verify_on_setup()

        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn22', inputs=self.inputs, subnets=['22.1.1.0/24'], ipam_fq_name=ipam_obj.fq_name))
        assert vn_fixture.verify_on_setup()

        try:
            self.vnc_lib.network_ipam_delete(vn_fixture.ipam_fq_name)
        except RefsExistError as e:
            self.logger.info(
                'RefsExistError:Check passed that the IPAM cannot be released when the VN is associated to it.')

        vm1_fixture = self.useFixture(VMFixture(connections=self.connections, project_name = self.inputs.project_name,
                                                vn_obj=vn_fixture.obj, vm_name='vm1'))
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections, project_name = self.inputs.project_name,
                                                vn_obj=vn_fixture.obj, vm_name='vm2'))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)

        try:
            self.vnc_lib.network_ipam_delete(vn_fixture.ipam_fq_name)
        except RefsExistError as e:
            self.logger.info(
                'RefsExistError:Check passed that the IPAM cannot be released when the VN is associated to it, which has VMs on it.')

        return True
    # end test_release_ipam

    @preposttest_wrapper
    def test_shutdown_vm(self):
        ''' Test to validate that VN is unaffected after the VMs in it are shutdown.
        '''
        vm1_name = 'vm_mine'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        cmd_to_shutdown_vm = ['shutdown -h now']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_shutdown_vm, as_sudo=True)
        assert vn_fixture.verify_on_setup()
        return True
    # end test_shutdown_vm

class TestBasicVMVN3(BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicVMVN3, cls).setUpClass()

    def runTest(self):
        pass
    #end runTes 
    
    @preposttest_wrapper
    def test_traffic_bw_vms_diff_pkt_size(self):
        ''' Test to validate TCP, ICMP, UDP traffic of different packet sizes b/w VMs created within a VN.
        '''
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/29']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        # Get all compute host
        host_list = []
        for host in self.inputs.compute_ips:
            host_list.append(self.inputs.host_data[host]['name'])
        print host_list
        if len(set(self.inputs.compute_ips)) > 1:
            self.logger.info("Multi-Node Setup")
            vm1_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vm1', node_name=host_list[1]))
            assert vm1_fixture.verify_on_setup()
            vm2_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vm2', node_name=host_list[0]))
            assert vm2_fixture.verify_on_setup()
        else:
            self.logger.info("Single-Node Setup")
            vm1_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vm1'))
            vm2_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vm2'))
            assert vm1_fixture.verify_on_setup()
            assert vm2_fixture.verify_on_setup()

        out1 = vm1_fixture.wait_till_vm_is_up()
        if out1 == False:
            return {'result': out1, 'msg': "%s failed to come up" % vm1_fixture.vm_name}
        else:
            self.logger.info('Will install Traffic package on %s' %
                             vm1_fixture.vm_name)
            vm1_fixture.install_pkg("Traffic")

        out2 = vm2_fixture.wait_till_vm_is_up()
        if out2 == False:
            return {'result': out2, 'msg': "%s failed to come up" % vm2_fixture.vm_name}
        else:
            self.logger.info('Will install Traffic package on %s' %
                             vm2_fixture.vm_name)
            vm2_fixture.install_pkg("Traffic")
        result = True
        msg = []
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['tcp', 'icmp', 'udp']
        total_streams = {}
        total_streams['icmp'] = 1
        total_streams['udp'] = 2
        total_streams['tcp'] = 2
        dpi = 9100
        proto = 'udp'
        packet_sizes = [40, 64, 254, 748, 1350]
        cmd_to_increase_mtu = ['ifconfig eth0 mtu 16436']
        for packet_size in packet_sizes:
            if packet_size > 1400:
                self.logger.info('Increasing the MTU of the eth0 of VM')
                vm1_fixture.run_cmd_on_vm(
                    cmds=cmd_to_increase_mtu)
                vm2_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu)
            self.logger.info("-" * 80)
            self.logger.info("PACKET SIZE = %sB" % packet_size)
            self.logger.info("-" * 80)
            for proto in traffic_proto_l:
                traffic_obj[proto] = {}
                startStatus[proto] = {}
                traffic_obj[proto] = self.useFixture(
                    traffic_tests.trafficTestFixture(self.connections))
                # def startTraffic (self, name=name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
                # packet_size= 100, start_sport= 8000,
                # total_single_instance_streams= 20):
                startStatus[proto] = traffic_obj[proto].startTraffic(
                    num_streams=total_streams[proto], start_port=dpi,
                    tx_vm_fixture=vm1_fixture, rx_vm_fixture=vm2_fixture, stream_proto=proto, packet_size=packet_size)
                self.logger.info("Status of start traffic : %s, %s, %s" %
                                 (proto, vm1_fixture.vm_ip, startStatus[proto]))
                if startStatus[proto]['status'] != True:
                    msg.append(startStatus[proto])
                    result = False
            #self.assertEqual(out['result'], True, out['msg'])
            self.logger.info("-" * 80)
            # Poll live traffic
            traffic_stats = {}
            self.logger.info("Poll live traffic and get status..")
            for proto in traffic_proto_l:
                traffic_stats = traffic_obj[proto].getLiveTrafficStats()
                err_msg = ["Traffic disruption is seen: details: "] + \
                    traffic_stats['msg']
            self.assertEqual(traffic_stats['status'], True, err_msg)
            self.logger.info("-" * 80)
            # Stop Traffic
            self.logger.info("Proceed to stop traffic..")
            self.logger.info("-" * 80)
            for proto in traffic_proto_l:
                stopStatus[proto] = {}
                stopStatus[proto] = traffic_obj[proto].stopTraffic()
                if stopStatus[proto] != []:
                    msg.append(stopStatus[proto])
                    result = False
                self.logger.info(
                    "Status of stop traffic for proto %s and packet size of %sB is %s" %
                    (proto, packet_size, stopStatus[proto]))
            self.logger.info("-" * 80)
            print result
            self.logger.info('Sleeping for 20s')
            sleep(10)
        self.assertEqual(result, True, msg)

        return True
    # end test_traffic_bw_vms_diff_pkt_size

    def runTest(self):
        pass
    #end runTes 

class TestBasicVMVN4(BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicVMVN4, cls).setUpClass()

    @preposttest_wrapper
    def test_traffic_bw_vms_diff_pkt_size_w_chksum(self):
        ''' Test to validate ICMP, UDP traffic of different packet sizes b/w VMs created within a VN and validate UDP checksum.
        '''
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/29']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        # Get all compute host
        host_list = []
        for host in self.inputs.compute_ips:
            host_list.append(self.inputs.host_data[host]['name'])
        print host_list
        if len(set(self.inputs.compute_ips)) > 1:
            self.logger.info("Multi-Node Setup")
            vm1_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vm1', node_name=host_list[1]))
            assert vm1_fixture.verify_on_setup()
            vm2_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vm2', node_name=host_list[0]))
            assert vm2_fixture.verify_on_setup()
        else:
            self.logger.info("Single-Node Setup")
            vm1_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vm1'))
            vm2_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vm2'))
            assert vm1_fixture.verify_on_setup()
            assert vm2_fixture.verify_on_setup()

        out1 = vm1_fixture.wait_till_vm_is_up()
        if out1 == False:
            return {'result': out1, 'msg': "%s failed to come up" % vm1_fixture.vm_name}
        else:
            self.logger.info('Will install Traffic package on %s' %
                             vm1_fixture.vm_name)
            vm1_fixture.install_pkg("Traffic")

        out2 = vm2_fixture.wait_till_vm_is_up()
        if out2 == False:
            return {'result': out2, 'msg': "%s failed to come up" % vm2_fixture.vm_name}
        else:
            self.logger.info('Will install Traffic package on %s' %
                             vm2_fixture.vm_name)
            vm2_fixture.install_pkg("Traffic")

        result = True
        msg = []
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['icmp', 'udp']
        total_streams = {}
        total_streams['icmp'] = 1
        total_streams['udp'] = 2
        dpi = 9100
        proto = 'udp'
        packet_sizes = [40, 64, 254, 748, 1350]
        cmd_to_increase_mtu = ['ifconfig eth0 mtu 16436']
        for packet_size in packet_sizes:
            if packet_size > 1400:
                self.logger.info('Increasing the MTU of the eth0 of VM')
                vm1_fixture.run_cmd_on_vm(
                    cmds=cmd_to_increase_mtu)
                vm2_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu)
            self.logger.info("-" * 80)
            self.logger.info("PACKET SIZE = %sB" % packet_size)
            self.logger.info("-" * 80)
            for proto in traffic_proto_l:
                name = proto
                traffic_obj[proto] = {}
                startStatus[proto] = {}
                traffic_obj[proto] = self.useFixture(
                    traffic_tests.trafficTestFixture(self.connections))
                # def startTraffic (self, name=name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
                # packet_size= 100, start_sport= 8000,
                # total_single_instance_streams= 20):
                startStatus[proto] = traffic_obj[proto].startTraffic(
                    num_streams=total_streams[proto], start_port=dpi,
                    tx_vm_fixture=vm1_fixture, rx_vm_fixture=vm2_fixture, stream_proto=proto, packet_size=packet_size, chksum=True)
                self.logger.info("Status of start traffic : %s, %s, %s" %
                                 (proto, vm1_fixture.vm_ip, startStatus[proto]))
                if startStatus[proto]['status'] != True:
                    msg.append(startStatus[proto])
                    result = False
            #self.assertEqual(out['result'], True, out['msg'])
            self.logger.info("-" * 80)
            # Poll live traffic
            traffic_stats = {}
            self.logger.info("Poll live traffic and get status..")
            for proto in traffic_proto_l:
                traffic_stats = traffic_obj[proto].getLiveTrafficStats()
                err_msg = ["Traffic disruption is seen: details: "] + \
                    traffic_stats['msg']
            self.assertEqual(traffic_stats['status'], True, err_msg)
            self.logger.info("-" * 80)
            # Stop Traffic
            self.logger.info("Proceed to stop traffic..")
            self.logger.info("-" * 80)
            for proto in traffic_proto_l:
                stopStatus[proto] = {}
                stopStatus[proto] = traffic_obj[proto].stopTraffic()
                if stopStatus[proto] != []:
                    msg.append(stopStatus[proto])
                    result = False
                for rcv_count in range(0, total_streams[proto]):
                    if traffic_obj[proto].receiver[rcv_count].corrupt > 0:
                        self.logger.error(
                            "In Stream %s of %s, %s packets are corrupted" %
                            (rcv_count, proto, traffic_obj[proto].receiver[rcv_count].corrupt))
                        result = False
                    else:
                        self.logger.info(
                            "In Stream %s of %s, No packets are corrupted" % (rcv_count, proto))
                self.logger.info(
                    "Status of stop traffic for proto %s and packet size of %sB is %s" %
                    (proto, packet_size, stopStatus[proto]))
            self.logger.info("-" * 80)
            print result
            sleep(5)
        self.assertEqual(result, True, msg)

        return True
    # end test_traffic_bw_vms_diff_pkt_size_w_chksum

    @preposttest_wrapper
    def test_traffic_bw_vms(self):
        ''' Test to validate TCP, ICMP, UDP traffic b/w VMs created within a VN .
        '''
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/29']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj

        # Get all compute host
        host_list = []
        for host in self.inputs.compute_ips:
            host_list.append(self.inputs.host_data[host]['name'])
        print host_list

        if len(set(self.inputs.compute_ips)) > 1:

            self.logger.info("Multi-Node Setup")
            vm1_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vm1', node_name=host_list[1]))
            assert vm1_fixture.verify_on_setup()
            vm2_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vm2', node_name=host_list[0]))
            assert vm2_fixture.verify_on_setup()
        else:
            self.logger.info("Single-Node Setup")
            vm1_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vm1'))
            vm2_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vm2'))
            assert vm1_fixture.verify_on_setup()
            assert vm2_fixture.verify_on_setup()

        out1 = vm1_fixture.wait_till_vm_is_up()
        if out1 == False:
            return {'result': out1, 'msg': "%s failed to come up" % vm1_fixture.vm_name}
        else:
            sleep(10)
            self.logger.info('Will install Traffic package on %s' %
                             vm1_fixture.vm_name)
            vm1_fixture.install_pkg("Traffic")

        out2 = vm2_fixture.wait_till_vm_is_up()
        if out2 == False:
            return {'result': out2, 'msg': "%s failed to come up" % vm2_fixture.vm_name}
        else:
            sleep(10)
            self.logger.info('Will install Traffic package on %s' %
                             vm2_fixture.vm_name)
            vm2_fixture.install_pkg("Traffic")

        #self.logger.info('Will install Traffic package')
        # vm1_fixture.install_pkg("Traffic")
        # vm2_fixture.install_pkg("Traffic")
        #self.logger.info('Installed Traffic package')

        result = True
        msg = []
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['tcp', 'icmp', 'udp']
        total_streams = {}
        total_streams['icmp'] = 1
        total_streams['udp'] = 2
        total_streams['tcp'] = 2
        dpi = 9100
        proto = 'udp'
        for proto in traffic_proto_l:
            traffic_obj[proto] = {}
            startStatus[proto] = {}
            traffic_obj[proto] = self.useFixture(
                traffic_tests.trafficTestFixture(self.connections))
            # def startTraffic (self, name=name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
            # packet_size= 100, start_sport= 8000,
            # total_single_instance_streams= 20):
            startStatus[proto] = traffic_obj[proto].startTraffic(
                num_streams=total_streams[proto], start_port=dpi,
                tx_vm_fixture=vm1_fixture, rx_vm_fixture=vm2_fixture, stream_proto=proto)
            self.logger.info("Status of start traffic : %s, %s, %s" %
                             (proto, vm1_fixture.vm_ip, startStatus[proto]))
            if startStatus[proto]['status'] != True:
                msg.append(startStatus[proto])
                result = False
        #self.assertEqual(out['result'], True, out['msg'])
        self.logger.info("-" * 80)
        # Poll live traffic
        traffic_stats = {}
        self.logger.info("Poll live traffic and get status..")
        for proto in traffic_proto_l:
            traffic_stats = traffic_obj[proto].getLiveTrafficStats()
            err_msg = ["Traffic disruption is seen: details: "] + \
                traffic_stats['msg']
        self.assertEqual(traffic_stats['status'], True, err_msg)
        self.logger.info("-" * 80)
        # Stop Traffic
        self.logger.info("Proceed to stop traffic..")
        self.logger.info("-" * 80)
        for proto in traffic_proto_l:
            stopStatus[proto] = {}
            stopStatus[proto] = traffic_obj[proto].stopTraffic()
            if stopStatus[proto] != []:
                msg.append(stopStatus[proto])
                result = False
            self.logger.info("Status of stop traffic for proto %s is %s" %
                             (proto, stopStatus[proto]))
        self.logger.info("-" * 80)
        self.assertEqual(result, True, msg)
        return True
    # end test_traffic_bw_vms

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_vm_add_delete(self):
        ''' Test to validate that a VM creation and deletion passes.
        '''
        vm1_name = 'vm_mine'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name, flavor='contrail_flavor_small', image_name='ubuntu-traffic'))
        assert vm1_fixture.verify_on_setup()
        return True
    # end test_vm_add_delete
    
    @preposttest_wrapper
    def test_vm_add_delete_in_2_vns(self):
        ''' Test to validate that a VM can be associated to more than one VN.
        '''
        vm1_name = 'vm_mine1'
        vn1_name = 'vn222'
        vn1_subnets = ['11.1.1.0/24']
        vn2_name = 'vn223'
        vn2_subnets = ['22.1.1.0/24']
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn2_name, inputs=self.inputs, subnets=vn2_subnets))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_objs=[vn1_fixture.obj, vn2_fixture.obj], vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        return True
    # end test_vm_add_delete_in_2_vns
 
    @preposttest_wrapper
    def test_vm_add_delete_in_2_vns_chk_ips(self):
        ''' Test to validate that a VM can be associated to more than a VN and it gets the IPs as well.
        '''
        vm1_name = 'vm_mine1'
        vn1_name = 'vn222'
        vn1_subnets = ['11.1.1.0/24']
        vn2_name = 'vn223'
        vn2_subnets = ['22.1.1.0/24']
        text = """#!/bin/sh
                ifconfig eth1 22.1.1.253 netmask 255.255.255.0
                """
        try:
            with open("/tmp/metadata_script.txt", "w") as f:
                f.write(text)
        except Exception as e:
            self.logger.exception(
                "Got exception while creating /tmp/metadata_script.txt as %s" % (e))

        list_of_ips = []
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn2_name, inputs=self.inputs, subnets=vn2_subnets))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()

        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_objs=[vn1_fixture.obj, vn2_fixture.obj], vm_name=vm1_name, project_name=self.inputs.project_name, image_name='cirros-0.3.0-x86_64-uec', flavor='m1.tiny', userdata='/tmp/metadata_script.txt'))
        assert vm1_fixture.verify_on_setup()
        list_of_ips = vm1_fixture.vm_ips
        cmd = '/sbin/ifconfig -a'
        ret = vm1_fixture.run_cmd_on_vm(cmds=[cmd])
        for elem in ret.values():
            for ips in list_of_ips:
                if ips not in elem:
                    self.logger.error(
                        "IP %s not assigned to any eth intf of %s" %
                        (ips, vm1_fixture.vm_name))
                else:
                    self.logger.info('IP %s assigned' % ips)
        return True
    # end test_vm_add_delete_in_2_vns_chk_ips

    @preposttest_wrapper
    def test_vm_arp(self):
        ''' Test to validate that the fool-proof way is to not answer
        for arp request from the guest for the address the tap i/f is
        "configured" for.
        '''
        vm1_name = 'vm_mine'
        vm2_name = 'vm_yours'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, image_name='ubuntu-traffic', vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, image_name='ubuntu-traffic', vm_name=vm2_name, project_name=self.inputs.project_name))
        assert vm2_fixture.verify_on_setup()

        i = 'arping -c 10 %s' % vm1_fixture.vm_ip
        cmd_to_output = [i]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_output, as_sudo=True)
        output = vm1_fixture.return_output_cmd_dict[i]
        print output
        result = True
        if not '100%' in output:
            self.logger.error(
                'Arping to the VMs own address should have failed')
            result = False
        else:
            self.logger.info('Arping to the VMs own address fails')

        j = 'arping -c 10 %s' % vm2_fixture.vm_ip
        cmd_to_output = [j]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_output, as_sudo=True)
        output1 = vm1_fixture.return_output_cmd_dict[j]
        print output1
        if not '0%' in output:
            self.logger.error(
                'Arping to the other VMs address should have passed')
            result = False
        else:
            self.logger.info('Arping to the other VMs address passes')

        assert result, "ARPing Failure"
        return True
    # end test_vm_arp

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_vm_file_trf_scp_tests(self):
        '''
         Description: Test to validate File Transfer using scp between VMs. Files of different sizes.
         Test steps:
                1. Creating vm's - vm1 and vm2 and a Vn - vn222
                2. Transfer file from vm1 to vm2 with diferrent file sizes using scp
                3. file sizes - 1000,1101,1202,1303,1373, 1374,2210, 2845, 3000, 10000, 10000003
                4. verify files present in vm2 match with the size of the file sent.
         Pass criteria: File in vm2 should match with the transferred file size from vm1

         Maintainer : ganeshahv@juniper.net
        '''
        vm1_name = 'vm1'
        vm2_name = 'vm2'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        file = 'somefile'
        y = 'ls -lrt %s' % file
        cmd_to_check_file = [y]
        x = 'sync'
        cmd_to_sync = [x]
        create_result = True
        transfer_result = True
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.wait_till_vm_is_up()
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm2_name, project_name=self.inputs.project_name))
        assert vm2_fixture.wait_till_vm_is_up()

        # ssh and tftp taking sometime to be up and runnning
        #sleep(self.scp_test_starup_wait)
        vm1_fixture.put_pub_key_to_vm()
        vm2_fixture.put_pub_key_to_vm()
        for size in self.scp_test_file_sizes:
            self.logger.info("-" * 80)
            self.logger.info("FILE SIZE = %sB" % size)
            self.logger.info("-" * 80)

            self.logger.info('Transferring the file from %s to %s using scp' %
                             (vm1_fixture.vm_name, vm2_fixture.vm_name))
            file_transfer_result = vm1_fixture.check_file_transfer(vm2_fixture,
                                                                   size=size)

            if file_transfer_result:
                self.logger.info(
                    'File of size %sB transferred via scp properly' % size)
            else:
                transfer_result = False
                self.logger.error(
                    'File of size %sB not transferred via scp ' % size)
                break

        assert transfer_result, 'File not transferred via scp '
        return transfer_result
    # end test_vm_file_trf_scp_tests

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_vm_file_trf_tftp_tests(self):
        '''
         Description:  Test to validate File Transfer using tftp between VMs. Files of different sizes.
         Test steps:
                1. Creating vm's - vm1 and vm2 and a Vn - vn222
                2. Transfer file from vm1 to vm2 with diferrent file sizes using tftp
                3. file sizes - 1000,1101,1202,1303,1373, 1374,2210, 2845, 3000, 10000, 10000003
                4. verify files present in vm2 match with the size of the file sent.
          Pass criteria: File in vm2 should match with the transferred file size from vm1
         
          Maintainer : ganeshahv@juniper.net
        '''
        vm1_name='vm1'
        vm2_name='vm2'
        vn_name='vn222'
        ts = time.time()
        vn_name = '%s_%s'%(inspect.stack()[0][3],str(ts))
        vn_subnets=['11.1.1.0/24']
        file_sizes=['1000', '1101', '1202', '1303', '1373', '1374', '2210', '2845', '3000', '10000', '10000003']
        file= 'testfile'
        y = 'ls -lrt /var/lib/tftpboot/%s'%file
        cmd_to_check_file = [y]
        z = 'ls -lrt /var/lib/tftpboot/%s'%file
        cmd_to_check_tftpboot_file = [z]
        x = 'sync'
        cmd_to_sync = [x]
        create_result= True
        transfer_result= True
        vn_fixture= self.useFixture(VNFixture(project_name= self.project.project_name, connections= self.connections,
                     vn_name=vn_name, inputs= self.inputs, subnets= vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj= vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                            vn_obj=vn_obj, flavor='contrail_flavor_small', 
                            image_name='ubuntu-traffic', vm_name=vm1_name, 
                            project_name=self.inputs.project_name))
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                            vn_obj=vn_obj, flavor='contrail_flavor_small', 
                            image_name='ubuntu-traffic', vm_name=vm2_name, 
                            project_name=self.inputs.project_name))
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        #ssh and tftp taking sometime to be up and runnning
        for size in file_sizes:
            self.logger.info ("-"*80)
            self.logger.info("FILE SIZE = %sB"%size)
            self.logger.info ("-"*80)
            self.logger.info('Transferring the file from %s to %s using tftp'%(vm1_fixture.vm_name, vm2_fixture.vm_name))

            vm1_fixture.check_file_transfer(dest_vm_fixture = vm2_fixture, mode = 'tftp', size= size )
            self.logger.info('Checking if the file exists on %s'%vm2_fixture.vm_name)
            vm2_fixture.run_cmd_on_vm( cmds= cmd_to_check_file );
            output= vm2_fixture.return_output_cmd_dict[y]
            print output
            if size in output:
                self.logger.info('File of size %sB transferred via tftp properly'%size)
            else:
                transfer_result= False
                self.logger.error('File of size %sB not transferred via tftp '%size)

        if not transfer_result:
            self.logger.error('Tftp transfer failed, lets verify basic things')
            assert vm1_fixture.verify_on_setup()
            assert vm2_fixture.verify_on_setup()
            assert transfer_result
        return transfer_result
    #end test_vm_file_trf_tftp_tests



class TestBasicVMVN5(BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicVMVN5, cls).setUpClass()

    def runTest(self):
        pass
    #end runTes 

    @preposttest_wrapper
    def test_vm_gw_tests(self):
        ''' Test to validate gateway IP assignments the VM interface.
        '''
        vm1_name = 'vm_mine'
        vm2_name = 'vm_yours'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name))

        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm2_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)

        self.logger.info(
            'Adding a static GW and checking that ping is still successful after the change')
        cmd_to_add_gw = ['route add default gw 11.1.1.254']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_gw)
        assert vm1_fixture.verify_on_setup()
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)
        self.logger.info(
            'Adding a static GW, pointing to the metadata IP and checking that ping succeeds')
        i = 'route add default gw %s' % vm1_fixture.local_ip
        cmd_to_change_gw = [i]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_change_gw)
        assert vm1_fixture.verify_on_setup()
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)
        return True
    # end test_vm_gw_tests
    
    @preposttest_wrapper
    def test_vm_in_2_vns_chk_ping(self):
        ''' Test to validate that a VM can be associated to more than a VN and ping to a network goes from the respective intf.
        '''
        vm1_name = 'vm_mine1'
        vn1_name = 'vn222'
        vn1_subnets = ['11.1.1.0/24']
        vn2_name = 'vn223'
        vn2_subnets = ['22.1.1.0/24']
        vm2_name = 'vm_vn222'
        vm3_name = 'vm_vn223'
        list_of_ips = []
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn2_name, inputs=self.inputs, subnets=vn2_subnets))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_objs=[vn1_fixture.obj, vn2_fixture.obj], vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn1_fixture.obj, vm_name=vm2_name, project_name=self.inputs.project_name))
        assert vm2_fixture.verify_on_setup()
        vm3_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn2_fixture.obj, vm_name=vm3_name, project_name=self.inputs.project_name))
        assert vm3_fixture.verify_on_setup()
        list_of_ips = vm1_fixture.vm_ips
        i = 'ifconfig eth1 %s netmask 255.255.255.0' % list_of_ips[1]
        cmd_to_output = [i]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_output, as_sudo=True)
        output = vm1_fixture.return_output_cmd_dict[i]
        print output

        j = 'ifconfig -a'
        cmd_to_output1 = [j]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_output1)
        output1 = vm1_fixture.return_output_cmd_dict[j]
        print output1

        for ips in list_of_ips:
            if ips not in output1:
                result = False
                self.logger.error("IP %s not assigned to any eth intf of %s" %
                                  (ips, vm1_fixture.vm_name))
                assert result, "PR 1018"
            else:
                self.logger.info("IP %s is assigned to eth intf of %s" %
                                 (ips, vm1_fixture.vm_name))

        self.logger.info('-' * 80)
        self.logger.info('Will ping to the two VMs from the Multi-NIC VM')
        self.logger.info('-' * 80)
        result = True
        if not vm1_fixture.ping_to_ip(vm2_fixture.vm_ip):
            result = False
            assert result, "Ping to %s Fail" % vm2_fixture.vm_ip
        else:
            self.logger.info('Ping to %s Pass' % vm2_fixture.vm_ip)
        if not vm1_fixture.ping_to_ip(vm3_fixture.vm_ip):
            result = False
            assert result, "Ping to %s Fail" % vm3_fixture.vm_ip
        else:
            self.logger.info('Ping to %s Pass' % vm3_fixture.vm_ip)

        cmd_to_add_file = ['touch batchfile']
        cmd_to_exec_file = ['sh batchfile | tee > out.log']
        cmd_to_delete_file = ['rm -rf batchfile']
        ping_vm2 = 'ping %s' % vm2_fixture.vm_ip
        cmd_to_ping_vm2 = [ping_vm2]
        ping_vm3 = 'ping %s' % vm3_fixture.vm_ip
        cmd_to_ping_vm3 = [ping_vm3]

        self.logger.info('-' * 80)
        self.logger.info(
            'Will shut down eth1 and hence ping to the second n/w should fail, while the ping to the first n/w is unaffected. The same is not done for eth0 as it points to the default GW')
        self.logger.info('-' * 80)
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_file)
        cmd_to_add_cmd_to_file = [
            "echo 'ifconfig -a; sudo ifconfig eth1 down; ifconfig -a; ping -c 5 %s > ping_output_after_shutdown.log; sudo ifconfig eth1 up; ifconfig -a ' > batchfile" % vm3_fixture.vm_ip]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_cmd_to_file)
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_exec_file)
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_delete_file)

        i = 'cat ping_output_after_shutdown.log'
        cmd_to_view_output = ['cat ping_output_after_shutdown.log']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_view_output)
        output = vm1_fixture.return_output_cmd_dict[i]
        print output

        if not '100% packet loss' in output:
            result = False
            self.logger.error('Ping to %s Pass' % vm3_fixture.vm_ip)
        else:
            self.logger.info('Ping to %s Fail' % vm3_fixture.vm_ip)
        if not vm1_fixture.ping_to_ip(vm2_fixture.vm_ip):
            result = False
            assert result, "Ping to %s Fail" % vm2_fixture.vm_ip
        else:
            self.logger.info('Ping to %s Pass' % vm2_fixture.vm_ip)

        self.logger.info('-' * 80)
        self.logger.info(
            'Will unshut eth1 and hence ping to the second n/w should pass, while the ping to the first n/w is still unaffected. The same is not done for eth0 as it points to the default GW')
        self.logger.info('-' * 80)
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_file)
        cmd_to_add_cmd_to_file = [
            "echo 'ifconfig -a; sudo ifconfig eth1 up; sleep 10; sudo ifconfig -a; ping -c 5 %s > ping_output.log' > batchfile" % vm3_fixture.vm_ip]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_cmd_to_file)
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_exec_file)
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_delete_file)

        j = 'cat ping_output.log'
        cmd_to_view_output = ['cat ping_output.log']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_view_output)
        output1 = vm1_fixture.return_output_cmd_dict[j]
        print output1

        if not '0% packet loss' in output1:
            result = False
            self.logger.error('Ping to %s Fail' % vm3_fixture.vm_ip)
        else:
            self.logger.info('Ping to %s Pass' % vm3_fixture.vm_ip)
        if not vm1_fixture.ping_to_ip(vm2_fixture.vm_ip):
            result = False
            assert result, "Ping to %s Fail" % vm2_fixture.vm_ip
        else:
            self.logger.info('Ping to %s Pass' % vm2_fixture.vm_ip)

        return True
        #end test_vm_in_2_vns_chk_ping

    @preposttest_wrapper
    def test_vm_intf_tests(self):
        ''' Test to validate Loopback and eth0 intfs up/down events.
        '''
        vm1_name = 'vm_mine'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        self.logger.info('Shutting down Loopback intf')
        cmd_to_intf_down = ['ifdown lo ']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_intf_down, as_sudo=True)
        assert vm1_fixture.verify_on_setup()
        self.logger.info('Bringing up Loopback intf')
        cmd_to_intf_up = ['ifup lo']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_intf_up, as_sudo=True)
        assert vm1_fixture.verify_on_setup()
        cmd_to_create_file = ['touch batchfile']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_create_file)
        cmd_to_add_cmd_to_file = [
            "echo 'ifconfig; route; sudo ifdown eth0; ifconfig; route; sleep 10; sudo ifup eth0;  ifconfig; route ' > batchfile"]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_cmd_to_file)
        cmd_to_exec_file = ['sh batchfile | tee > out.log']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_exec_file)
        assert vm1_fixture.verify_on_setup()
        return True
    # end test_vm_intf_tests

    @preposttest_wrapper
    def test_vm_multi_intf_in_same_vn_chk_ping(self):
        ''' Test to validate that a multiple interfaces of the same VM can be associated to the same VN and ping is successful.
        '''
        #raise self.skipTest("Skiping Test. Will enable after infra changes to support them have been made")
        vm1_name = 'vm_mine1'
        vn1_name = 'vn222'
        vn1_subnets = ['11.1.1.0/24']
        vm2_name = 'vm_yours'
        list_of_ips = []
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        # In latest release we dont support adding same VN
        # Converting test to negative, accept execption and mark as PASS
        try:
            vm1_fixture = self.useFixture(
                VMFixture(connections=self.connections,
                          vn_objs=[vn1_fixture.obj, vn1_fixture.obj, vn1_fixture.obj, vn1_fixture.obj, vn1_fixture.obj], vm_name=vm1_name, project_name=self.inputs.project_name))
        except Exception as e:
            self.logger.exception(
                "Got exception while creating multi_intf_vm_in_same_vn as %s" % (e))
            return True

        assert vm1_fixture.verify_on_setup()
        try:
            vm2_fixture = self.useFixture(
                VMFixture(connections=self.connections,
                          vn_objs=[vn1_fixture.obj, vn1_fixture.obj, vn1_fixture.obj, vn1_fixture.obj, vn1_fixture.obj], vm_name=vm2_name, project_name=self.inputs.project_name))
        except Exception as e:
            self.logger.exception(
                "Got exception while creating multi_intf_vm_in_same_vn as %s" % (e))
            return True

        assert vm2_fixture.verify_on_setup()
        list_of_vm1_ips = vm1_fixture.vm_ips
        list_of_vm2_ips = vm2_fixture.vm_ips

        self.logger.info('Will ping to the two VMs from the Multi-NIC VM')
        self.logger.info('-' * 80)
        result = True
        for vm2_ip in list_of_vm2_ips:
            if not vm1_fixture.ping_to_ip(vm2_ip):
                result = False
                assert result, "Ping to %s from %s Fail" % (
                    vm2_ip, vm1_fixture.vm_name)
            else:
                self.logger.info('Ping to %s from %s Pass' %
                                 (vm2_ip, vm1_fixture.vm_name))

        for vm1_ip in list_of_vm1_ips:
            if not vm2_fixture.ping_to_ip(vm1_ip):
                result = False
                assert result, "Ping to %s from %s Fail" % (
                    vm1_ip, vm2_fixture.vm_name)
            else:
                self.logger.info('Ping to %s from %s Pass' %
                                 (vm2_ip, vm2_fixture.vm_name))
        return True
    # end test_vm_multi_intf_in_same_vn_chk_ping

    @preposttest_wrapper
    def test_vm_multiple_flavors(self):
        ''' Test to validate creation and deletion of VMs of all flavors.
        '''
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj

        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm_tiny', flavor='m1.tiny', project_name=self.inputs.project_name, image_name='cirros-0.3.0-x86_64-uec'))

        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm_small', flavor='m1.small', project_name=self.inputs.project_name))

        vm3_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm_medium', flavor='m1.medium', project_name=self.inputs.project_name))

        vm4_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm_large', flavor='m1.large', project_name=self.inputs.project_name))

        vm5_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm_xlarge', flavor='m1.xlarge', project_name=self.inputs.project_name))

        for a in range(1, 6):
            wait = eval('vm%d_fixture.wait_till_vm_is_up()' %
                 a)
            assert 'wait'

        for i in range(1, 5):
            for j in range(i + 1, 6):
                ping = eval('vm%d_fixture.ping_to_ip ( vm%d_fixture.vm_ip )' %
                            (i, j))
                assert 'ping'

        return True
    # end test_vm_multiple_flavors

    @preposttest_wrapper
    def test_vm_static_ip_tests(self):
        ''' Test to validate Static IP to the VM interface.
        '''
        vm1_name = 'vm_mine'
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()

        self.logger.info('Adding the same address as a Static IP')
        cmd = 'ifconfig eth0 %s netmask 255.255.255.0' % vm1_fixture.vm_ip
        cmd_to_add_static_ip = [cmd]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_static_ip, as_sudo=True)
        assert vm1_fixture.verify_on_setup()
        result = True

        self.logger.info('Adding a different address as a Static IP')
        cmd_to_add_file = ['touch batchfile']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_file)

        self.logger.info(
            'WIll add a different address and revert back to the original IP')
        cmd_to_add_cmd_to_file = [
            "echo 'ifconfig; route; sudo ifconfig eth0 10.10.10.10 netmask 255.255.255.0; ifconfig; route; sudo ifconfig eth0 11.1.1.253 netmask 255.255.255.0; ifconfig; route; sudo ifdown eth0; sleep 5; sudo ifup eth0; ifconfig; route' > batchfile"]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_cmd_to_file)

        cmd_to_exec_file = ['sh batchfile | tee > out.log']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_exec_file)

        i = 'cat out.log'
        cmd_to_view_output = ['cat out.log']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_view_output)

        output = vm1_fixture.return_output_cmd_dict[i]
        print output
        if '10.10.10.10' not in output:
            result = False
        assert vm1_fixture.verify_on_setup()
        return result
    # end test_vm_static_ip_tests

    @preposttest_wrapper
    def test_vm_vn_block_exhaustion(self):
        ''' Test to validate that a VMs cannot be created after the IP-Block is exhausted.
        '''
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/29']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        self.logger.info(
            'out of /29 block, we can have 5 usable addresses. Only 5 VMs should get launched properly.')

        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm1', project_name=self.inputs.project_name))

        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm2', project_name=self.inputs.project_name))

        vm3_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm3', project_name=self.inputs.project_name))

        vm4_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm4', project_name=self.inputs.project_name))

        vm5_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm5', project_name=self.inputs.project_name))

        self.logger.info(
            'The 6th VM should go into ERROR state as it is unable to get any ip. The ip-block is exhausted')

        sleep(15)
        vm6_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name='vm6', project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()
        assert vm5_fixture.verify_on_setup()
        assert not vm6_fixture.verify_on_setup()

        return True
    # end test_vm_vn_block_exhaustion

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_vn_add_delete(self):
        '''Test to validate VN creation and deletion.
        '''
        vn_obj = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn22', inputs=self.inputs, subnets=['22.1.1.0/24']))
        assert vn_obj.verify_on_setup()
        assert vn_obj
        return True
    #end test_vn_add_delete

    @preposttest_wrapper
    def test_vn_in_agent_with_vms_add_delete(self):
        ''' Test to validate VN's existence and removal in agent with deletion of associated VMs.
        '''
        vn_name = 'vn1'
        vn_subnets = ['10.10.10.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        self.logger.info('Launching VMs')

        vm1_fixture = VMFixture(connections=self.connections,
                                vn_obj=vn_obj, vm_name='vm1', project_name=self.inputs.project_name)
        vm1_fixture.setUp()
        vm1_fixture.verify_vm_launched()

        vm2_fixture = VMFixture(connections=self.connections,
                                vn_obj=vn_obj, vm_name='vm2', project_name=self.inputs.project_name)
        vm2_fixture.setUp()
        vm2_fixture.verify_vm_launched()
        self.logger.info('vm1 and vm2 launched successfully.')
        sleep(10)
        # for compute_ip in self.inputs.compute_ips:
        self.logger.info('Deleting vm2')
        vm2_fixture.cleanUp()
        self.logger.info('Checking if vn is still present in agent')
        assert not vn_fixture.verify_vn_not_in_agent()
        self.logger.info('VN is present in agent as expected.Now deleting vm1')
        vm1_fixture.cleanUp()
        self.logger.info('Checking if VN is removed from agent')
       # assert vn_fixture.verify_vn_not_in_agent()
        self.logger.info('VN is not present in agent as expected')

        return True
    # end test_vn_in_agent_with_vms_add_delete

    @preposttest_wrapper
    def test_vn_name_with_spl_characters(self):
        '''Test to validate VN name with special characters is allowed.
        '''
        vn1_obj = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn.1', inputs=self.inputs, subnets=['22.1.1.0/29']))
        assert vn1_obj.verify_on_setup()
        assert vn1_obj

        vn2_obj = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn,2', inputs=self.inputs, subnets=['33.1.1.0/30']))
        assert vn2_obj.verify_on_setup()
        assert vn2_obj

        vn3_obj = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn&3', inputs=self.inputs, subnets=['44.1.1.0/29']))
        self.logger.info(
            "VN names with '&' are allowed via API, but not through Openstack ==> Bug 1023")
        assert not vn3_obj.verify_on_setup()
        if vn3_obj:
            self.logger.error('Bug 1023 needs to be fixed')

        vn4_obj = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn_4', inputs=self.inputs, subnets=['55.1.1.0/31']))
        assert vn4_obj.verify_on_setup()
        assert vn4_obj

        return True
    # end test_vn_name_with_spl_characters

class TestBasicVMVN6(BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicVMVN6, cls).setUpClass()

    def runTest(self):
        pass
    #end runTes 

    @preposttest_wrapper
    def test_vn_subnet_types(self):
        """ Validate various type of subnets associated to VNs.
        """

        # vn-1 : 0.0.0.0/0 to be given once PR 802 is fixed
        reserved_ip_vns = {'vn-2': '169.254.1.1/24', 'vn-3': '251.2.2.1/24'}
        overlapping_vns = {'vn-5': ['10.1.1.0/24', '10.1.1.0/24'], 'vn-6':
                           ['11.11.11.0/30', '11.11.11.8/29'], 'vn-7': '10.1.1.1/24'}
        # vn-4 is added here bcoz the check has been implemented already for
        # 127 and not for 0
        non_usable_block_vns = {'vn-4': '127.0.0.1/8', 'vn-8':
                                '100.100.100.0/31', 'vn-9': '200.200.200.1/32'}

        res_vn_fixture = self.useFixture(
            MultipleVNFixture(connections=self.connections, inputs=self.inputs,
                              subnet_count=2, vn_name_net=reserved_ip_vns,  project_name=self.inputs.project_name))
        ovlap_vn_fixture = self.useFixture(MultipleVNFixture(
            connections=self.connections, inputs=self.inputs, subnet_count=2, vn_name_net=overlapping_vns,  project_name=self.inputs.project_name))
        try:
            non_usable_vn_fixture = self.useFixture(MultipleVNFixture(
                connections=self.connections, inputs=self.inputs, subnet_count=2, vn_name_net=non_usable_block_vns,  project_name=self.inputs.project_name))
        except NotPossibleToSubnet as e:
            self.logger.info(
                'Subnets like vn-4, vn-8 and vn-8 cannot be created as IPs cannot be assigned')
        if not res_vn_fixture.verify_on_setup:
            self.logger.error(
                'Reserved Addresses cannot be assigned --> Bug 803')
        assert ovlap_vn_fixture.verify_on_setup(
        ), 'Overlap in address space not taken care of '
        return True
    # end test_subnets_vn

    @preposttest_wrapper
    def test_vn_vm_no_ip(self):
        '''Test to check that VMs launched in a VN with no subnet, will go to error state.
        '''
        vn_obj = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn22', inputs=self.inputs))
        #assert vn_obj.verify_on_setup()
        assert vn_obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj.obj, vm_name='vm222', project_name=self.inputs.project_name))
        self.logger.info('The VM should not get an IP')
        assert not vm1_fixture.verify_on_setup()
        return True
    # end test_vn_vm_no_ip
    
    @preposttest_wrapper
    def test_vn_vm_no_ip_assign(self):
        '''Test to check that VM launched in a VN with no subnet gets ip assigned after subnet is assigned to the VN and VM is made active.
        '''
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn22', inputs=self.inputs))
        assert vn_fixture

        result = True
        vn_obj = self.quantum_fixture.get_vn_obj_if_present('vn22')
        vn_id = vn_obj['network']['id']
        subnet = '20.20.20.0/24'
        self.logger.info('VN launched with no ip block.Launching VM now.')
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_fixture.obj, vm_name='vm222', project_name=self.inputs.project_name))
        self.project_fixture = self.useFixture(ProjectFixture(
            vnc_lib_h=self.vnc_lib, project_name=self.inputs.project_name, connections=self.connections))
        vm_obj = self.nova_fixture.get_vm_if_present(
            'vm222', self.project_fixture.uuid)

        self.logger.info('The VM should not get any IP')
        assert not vm1_fixture.verify_on_setup()
        self.logger.info('Now assigning IP block to VN')
        ipam = vn_fixture.ipam_fq_name
        vn_fixture.create_subnet(subnet, ipam)
        vnnow_obj = self.quantum_fixture.get_vn_obj_if_present('vn22')
        subnet_created = vnnow_obj['network'][
            'contrail:subnet_ipam'][0]['subnet_cidr']
        if subnet_created != subnet:
            self.logger.error('ip block is not assigned to VN')
            result = False
            assert result
        else:
            self.logger.info(
                'ip block is assigned to the VN.Chcking VM state')
            vm_obj.get()
            state = vm_obj.status
            if state == 'ACTIVE':
                self.logger.error('VM status is %s.Should not be active' %
                                  (state))
                result = False
                assert result
            else:
                self.logger.info('VM status is not ACTIVE as expected.')
            # vm_obj.reset_state('active')
            # vm_obj.get()
            # state_new=vm_obj.status
            # if state_new!='ACTIVE':
            #    self.logger.error ('VM is not active')
            #    result = False
            #    assert result
            # else:
            #    self.logger.info ('VM status is ACTIVE as expected.VM should get ip if bug 954 is fixed')
            #    result = self.nova_fixture.get_vm_ip(vm_obj, 'vn22')
            #    assert result
            return result
   # end test_vn_vm_no_ip_assign

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
            vm_count_per_vn=4, vn_objs=vn_objs, image_name='cirros-0.3.0-x86_64-uec',
            flavor='m1.tiny'))
        assert multi_vm_fixture.verify_on_setup()

        return True
    # end test_multiple_vn_vm

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_ping_on_broadcast_multicast_with_frag(self):
        ''' Validate Ping on subnet broadcast,link local multucast,network broadcastwith packet sizes > MTU and see that fragmentation and assembly work fine .

        '''
        vn1_name = 'vn30'
        vn1_subnets = ['30.1.1.0/24']
        ping_count = '5'
        vn1_vm1_name = 'vm1'
        vn1_vm2_name = 'vm2'
        vn1_vm3_name = 'vm3'
        vn1_vm4_name = 'vm4'
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
        vm3_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm3_name))
        vm4_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm4_name))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        vm3_fixture.wait_till_vm_is_up()
        vm4_fixture.wait_till_vm_is_up()

        # Geting the VM ips
        vm1_ip = vm1_fixture.vm_ip
        vm2_ip = vm2_fixture.vm_ip
        vm3_ip = vm3_fixture.vm_ip
        vm4_ip = vm4_fixture.vm_ip
        ip_list = [vm1_ip, vm2_ip, vm3_ip, vm4_ip]
        list_of_ip_to_ping = ['30.1.1.255', '224.0.0.1', '255.255.255.255']
        # passing command to vms so that they respond to subnet broadcast
        cmd_list_to_pass_vm = [
            'echo 0 > /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm2_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm3_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm4_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        for dst_ip in list_of_ip_to_ping:
            print 'pinging from %s to %s' % (vm1_ip, dst_ip)
# pinging from Vm1 to subnet broadcast
            ping_output = vm1_fixture.ping_to_ip(
                dst_ip, return_output=True, count=ping_count,  size='3000', other_opt='-b')
            self.logger.info(
                'The packet is not fragmanted because of the smaller MTU')
            expected_result = 'Message too long'
            assert (expected_result in ping_output)

        self.logger.info('Will change the MTU of the VMs and try again')
        cmd_to_increase_mtu = ['ifconfig eth0 mtu 9000']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True)
        vm2_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True)
        vm3_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True)
        vm4_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True)

        for dst_ip in list_of_ip_to_ping:
            print 'pinging from %s to %s' % (vm1_ip, dst_ip)
# pinging from Vm1 to subnet broadcast
            ping_output = vm1_fixture.ping_to_ip(
                dst_ip, return_output=True, count=ping_count,  size='3000', other_opt='-b')
            expected_result = 'Message too long'
            assert (expected_result not in ping_output)

# getting count of ping response from each vm
            string_count_dict = {}
            string_count_dict = get_string_match_count(ip_list, ping_output)
            print string_count_dict
            for k in ip_list:
                # this is a workaround : ping utility exist as soon as it gets
                # one response
                assert (string_count_dict[k] >= (int(ping_count) - 1))
        return True
    # end test_ping_on_broadcast_multicast_with_frag

    @preposttest_wrapper
    def test_traffic_bw_vms_diff_pkt_size(self):
        ''' Test to validate TCP, ICMP, UDP traffic of different packet sizes b/w VMs created within a VN.
        '''
        vn_name = 'vn222'
        vn_subnets = ['11.1.1.0/29']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        # Get all compute host
        host_list = []
        for host in self.inputs.compute_ips:
            host_list.append(self.inputs.host_data[host]['name'])
        print host_list
        if len(set(self.inputs.compute_ips)) > 1:
            self.logger.info("Multi-Node Setup")
            vm1_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vm1', node_name=host_list[1]))
            assert vm1_fixture.verify_on_setup()
            vm2_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vm2', node_name=host_list[0]))
            assert vm2_fixture.verify_on_setup()
        else:
            self.logger.info("Single-Node Setup")
            vm1_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vm1'))
            vm2_fixture = self.useFixture(
                VMFixture(project_name=self.inputs.project_name,
                          connections=self.connections, vn_obj=vn_fixture.obj, flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name='vm2'))
            assert vm1_fixture.verify_on_setup()
            assert vm2_fixture.verify_on_setup()

        out1 = vm1_fixture.wait_till_vm_is_up()
        if out1 == False:
            return {'result': out1, 'msg': "%s failed to come up" % vm1_fixture.vm_name}
        else:
            self.logger.info('Will install Traffic package on %s' %
                             vm1_fixture.vm_name)
            vm1_fixture.install_pkg("Traffic")

        out2 = vm2_fixture.wait_till_vm_is_up()
        if out2 == False:
            return {'result': out2, 'msg': "%s failed to come up" % vm2_fixture.vm_name}
        else:
            self.logger.info('Will install Traffic package on %s' %
                             vm2_fixture.vm_name)
            vm2_fixture.install_pkg("Traffic")
        result = True
        msg = []
        traffic_obj = {}
        startStatus = {}
        stopStatus = {}
        traffic_proto_l = ['tcp', 'icmp', 'udp']
        total_streams = {}
        total_streams['icmp'] = 1
        total_streams['udp'] = 2
        total_streams['tcp'] = 2
        dpi = 9100
        proto = 'udp'
        packet_sizes = [40, 64, 254, 748, 1350]
        cmd_to_increase_mtu = ['ifconfig eth0 mtu 16436']
        for packet_size in packet_sizes:
            if packet_size > 1400:
                self.logger.info('Increasing the MTU of the eth0 of VM')
                vm1_fixture.run_cmd_on_vm(
                    cmds=cmd_to_increase_mtu)
                vm2_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu)
            self.logger.info("-" * 80)
            self.logger.info("PACKET SIZE = %sB" % packet_size)
            self.logger.info("-" * 80)
            for proto in traffic_proto_l:
                traffic_obj[proto] = {}
                startStatus[proto] = {}
                traffic_obj[proto] = self.useFixture(
                    traffic_tests.trafficTestFixture(self.connections))
                # def startTraffic (self, name=name, num_streams= 1, start_port= 9100, tx_vm_fixture= None, rx_vm_fixture= None, stream_proto= 'udp', \
                # packet_size= 100, start_sport= 8000,
                # total_single_instance_streams= 20):
                startStatus[proto] = traffic_obj[proto].startTraffic(
                    num_streams=total_streams[proto], start_port=dpi,
                    tx_vm_fixture=vm1_fixture, rx_vm_fixture=vm2_fixture, stream_proto=proto, packet_size=packet_size)
                self.logger.info("Status of start traffic : %s, %s, %s" %
                                 (proto, vm1_fixture.vm_ip, startStatus[proto]))
                if startStatus[proto]['status'] != True:
                    msg.append(startStatus[proto])
                    result = False
            #self.assertEqual(out['result'], True, out['msg'])
            self.logger.info("-" * 80)
            # Poll live traffic
            traffic_stats = {}
            self.logger.info("Poll live traffic and get status..")
            for proto in traffic_proto_l:
                traffic_stats = traffic_obj[proto].getLiveTrafficStats()
                err_msg = ["Traffic disruption is seen: details: "] + \
                    traffic_stats['msg']
            self.assertEqual(traffic_stats['status'], True, err_msg)
            self.logger.info("-" * 80)
            # Stop Traffic
            self.logger.info("Proceed to stop traffic..")
            self.logger.info("-" * 80)
            for proto in traffic_proto_l:
                stopStatus[proto] = {}
                stopStatus[proto] = traffic_obj[proto].stopTraffic()
                if stopStatus[proto] != []:
                    msg.append(stopStatus[proto])
                    result = False
                self.logger.info(
                    "Status of stop traffic for proto %s and packet size of %sB is %s" %
                    (proto, packet_size, stopStatus[proto]))
            self.logger.info("-" * 80)
            print result
            self.logger.info('Sleeping for 20s')
            sleep(10)
        self.assertEqual(result, True, msg)

        return True
    # end test_traffic_bw_vms_diff_pkt_size

    @test.attr(type=['sanity'])
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
        vn1_name = get_random_name('vn1')
        vn1_subnets = ['192.168.1.0/24']
        vn1_vm1_name = get_random_name('vn1_vm1')
        vn1_vm2_name = get_random_name('vn1_vm2')
        vn1_fixture = self.create_vn(vn1_name, vn1_subnets)
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn1_fixture, vn1_vm1_name)
        assert vm1_fixture.wait_till_vm_is_up()
        vm2_fixture = self.create_vm(vn1_fixture, vn1_vm2_name)
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
        raise self.skipTest("Skiping a failing test")
        if len(set(self.inputs.bgp_ips)) < 2:
            raise self.skipTest(
                "Skiping Test. At least 2 control node required to run the test")
        result = True
        vn1_name = get_random_name('vn30')
        vn1_subnets = ['30.1.1.0/24']
        vn1_vm1_name = get_random_name('vm1')
        vn1_vm2_name = get_random_name('vm2')
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

        assert vm2_fixture.ping_to_ip(vm1_fixture.vm_ip)
        # Collecting all the control node details
        controller_list = []
        inspect_h = self.agent_inspect[vm1_fixture.vm_node_ip]
        agent_xmpp_status = inspect_h.get_vna_xmpp_connection_status()
        for entry in agent_xmpp_status:
            controller_list.append(entry['controller_ip'])
        list_of_vm = inspect_h.get_vna_vm_list()

        # Stop all the control node
        for entry in controller_list:
            self.logger.info('Stoping the Control service in  %s' % (entry))
            self.inputs.stop_service('contrail-control', [entry])
            self.addCleanup(self.inputs.start_service,
                            'contrail-control', [entry])
            sleep(5)

        # Wait for cleanup to begin
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
            sleep(30)
        # Check everything came up fine
        vm_id_list = inspect_h.get_vna_vm_list()
        if vm1_fixture.vm_id not in vm_id_list or vm2_fixture.vm_id not in vm_id_list:
            result = result and False
            self.logger.error(
                'After starting the service all the VM entry did not came up properly')

        self.logger.info('Checking the VM came up properly or not')
        assert vm2_fixture.verify_on_setup()
        assert vm1_fixture.verify_on_setup()
        if not result:
            self.logger.error(
                'Test to verify cleanup of agent after control nodes stop Failed')
            assert result
        return True
    # end test_agent_cleanup_with_control_node_stop

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_metadata_service(self):
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
        vn_name = get_random_name('vn2_metadata')
        vm1_name = get_random_name('vm_in_vn2_metadata')
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name,
                                                image_name='cirros-0.3.0-x86_64-uec', userdata='/tmp/metadata_script.txt',
                                                flavor='m1.tiny'))

        assert vm1_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()

        cmd = 'ls /tmp/'
        for i in range(3):
            try:
                self.logger.info("Retry %s" % (i))
                ret = vm1_fixture.run_cmd_on_vm(cmds=[cmd])
#                if 'Connection refused' in ret:
                if not ret:
                    raise Exception
            except Exception as e:
                time.sleep(5)
                self.logger.exception("Got exception as %s" % (e))
            else:
                break
        self.logger.info("ret : %s" % (ret))
        result = False
        for elem in ret.values():
            if 'output.txt' in elem:
                result = True
                break
        if not result:
            self.logger.warn(
                "metadata_script.txt did not get executed in the vm")
        else:
            self.logger.info("Printing the output.txt :")
            cmd = 'cat /tmp/output.txt'
            ret = vm1_fixture.run_cmd_on_vm(cmds=[cmd])
            self.logger.info("%s" % (ret.values()))
            for elem in ret.values():
                if 'Hello World' in elem:
                    result = True
                else:
                    self.logger.warn(
                        "metadata_script.txt did not get executed in the vm...output.txt does not contain proper output")
                    result = False

        assert result
        return True

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_generic_link_local_service(self):
        '''
         Description: Test to validate generic linklocal service - running nova list from vm.
            1.Create generic link local service to be able to wget to jenkins
            2.Create a vm
            3.Try wget to jenkins - passes if successful else fails

         Maintainer: sandipd@juniper.net
        '''

        vn_name = get_random_name('vn2_metadata')
        vm1_name = get_random_name('nova_client_vm')
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        #assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name,
                                                image_name='ubuntu-traffic'))

        assert vm1_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()

        metadata_args = "--admin_user admin \
         --admin_password contrail123 --linklocal_service_name generic_link_local\
         --linklocal_service_ip 169.254.1.1\
         --linklocal_service_port 8090\
         --ipfabric_service_ip %s\
         --ipfabric_service_port 5000\
         --oper add" % (self.inputs.openstack_ip)

        if not self.inputs.devstack:
            cmd = "python /opt/contrail/utils/provision_linklocal.py %s" % (metadata_args)
        else:
            cmd = "python /opt/stack/contrail/controller/src/config/utils/provision_linklocal.py %s" % (
                metadata_args)

        link_local_args = "--admin_user admin \
         --admin_password contrail123 --linklocal_service_name vim\
         --linklocal_service_ip 169.254.1.2\
         --linklocal_service_port 80\
         --ipfabric_dns_service_name www.vim.org\
         --ipfabric_service_port 80\
         --oper add"

        if not self.inputs.devstack:
            cmd = "python /opt/contrail/utils/provision_linklocal.py %s" % (link_local_args)
        else:
            cmd = "python /opt/stack/contrail/controller/src/config/utils/provision_linklocal.py %s" % (
                link_local_args)

        args = shlex.split(cmd)
        process = Popen(args, stdout=PIPE)
        stdout, stderr = process.communicate()
        if stderr:
            self.logger.warn(
                "Linklocal service could not be created, err : \n %s" % (stderr))
        else:
            self.logger.info("%s" % (stdout))
        cmd = 'wget http://169.254.1.2:80'

        for i in range(3):
            try:
                self.logger.info("Retry %s" % (i))
                ret = vm1_fixture.run_cmd_on_vm(cmds=[cmd])
#                if 'Connection refused' in ret:
                if not ret:
                    raise Exception
            except Exception as e:
                time.sleep(5)
                self.logger.exception("Got exception as %s" % (e))
            else:
                break
        if ret:
            if '200 OK' in str(ret):
                self.logger.info("Generic metadata worked")
                result = True
            if 'Connection timed out' in str(ret):
                self.logger.warn("Generic metadata did NOT work")
                result = False

        link_local_args = "--admin_user admin \
         --admin_password contrail123 --linklocal_service_name vim\
         --linklocal_service_ip 169.254.1.2\
         --linklocal_service_port 80\
         --ipfabric_dns_service_name www.vim.org\
         --ipfabric_service_port 80\
         --oper delete"

        if not self.inputs.devstack:
            cmd = "python /opt/contrail/utils/provision_linklocal.py %s" % (link_local_args)
        else:
            cmd = "python /opt/stack/contrail/controller/src/config/utils/provision_linklocal.py %s" % (
                link_local_args)

        args = shlex.split(cmd)
        process = Popen(args, stdout=PIPE)
        stdout, stderr = process.communicate()
        if stderr:
            self.logger.warn(
                "Linklocal service could not be deleted, err : \n %s" % (stderr))
        else:
            self.logger.info("%s" % (stdout))
        assert result
        return True
    # end test_generic_link_local_service
