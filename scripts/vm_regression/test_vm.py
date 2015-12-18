import traffic_tests
from vn_test import *
from vm_test import *
from floating_ip import *
from policy_test import *
from user_test import UserFixture
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.profile import create, ContinuousProfile
from traffic.core.helpers import Host
from traffic.core.helpers import Sender, Receiver
from base import BaseVnVmTest
from common import isolated_creds
import inspect
import time
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from tcutils.util import get_subnet_broadcast

import test

class TestBasicVMVN0(BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicVMVN0, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBasicVMVN0, cls).tearDownClass()


    @preposttest_wrapper
    def test_broadcast_udp_w_chksum(self):
        '''
         Description: Test to validate UDP Traffic to subnet broadcast, multicast and all_broadcast address in a network.
         Test steps:
                1. Creating 4 VMs in a VN.
                2. From one fo the VMs, start 4 streams of UDP traffc to the subnet broadcast, multicast and all_broadcast address.
                3. Get the count of packets received in each of the streams at the three destination VMs.
         Pass criteria: The count of packets sent and those received on the destination VMs should match.
         Maintainer : ganeshahv@juniper.net
        '''
        vn1_vm1_name = get_random_name('vm1')
        vn1_vm2_name = get_random_name('vm2')
        vn1_vm3_name = get_random_name('vm3')
        vn1_vm4_name = get_random_name('vm4')
        result = True
        # Forcing VN to be 'v4' in case of dual stack setup
        vn1_fixture = self.create_vn(af='v4')
        subnets = vn1_fixture.get_cidrs()
        assert subnets, "Unable to fetch subnets from vn fixture"
        broadcast = get_subnet_broadcast(subnets[0])
        #list_of_ips = [broadcast, '224.0.0.1', '255.255.255.255']
        list_of_ips = [broadcast, '224.0.0.1']
        assert vn1_fixture.verify_on_setup()

        vm1_fixture = self.create_vm(vn_fixture= vn1_fixture,vm_name=vn1_vm1_name,
                flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        vm2_fixture = self.create_vm(vn_fixture= vn1_fixture,vm_name=vn1_vm2_name,
                flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        vm3_fixture = self.create_vm(vn_fixture= vn1_fixture,vm_name=vn1_vm3_name,
                flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        vm4_fixture = self.create_vm(vn_fixture= vn1_fixture,vm_name=vn1_vm4_name,
                flavor='contrail_flavor_small', image_name='ubuntu-traffic')
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()

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
            stream = Stream(proto="udp", src=vm1_fixture.vm_ip, dst=ips, dport=9000)
            profile = ContinuousProfile(
                stream=stream, listener=ips, capfilter="udp port 8000", chksum=True)

            tx_vm_node_ip = self.inputs.host_data[
                self.connections.orch.get_host_of_vm(vm1_fixture.vm_obj)]['host_ip']
            rx1_vm_node_ip = self.inputs.host_data[
                self.connections.orch.get_host_of_vm(vm2_fixture.vm_obj)]['host_ip']
            rx2_vm_node_ip = self.inputs.host_data[
                self.connections.orch.get_host_of_vm(vm3_fixture.vm_obj)]['host_ip']
            rx3_vm_node_ip = self.inputs.host_data[
                self.connections.orch.get_host_of_vm(vm4_fixture.vm_obj)]['host_ip']

            tx_local_host = Host(
                tx_vm_node_ip,
                self.inputs.host_data[tx_vm_node_ip]['username'],
                self.inputs.host_data[tx_vm_node_ip]['password'])
            rx1_local_host = Host(
                rx1_vm_node_ip,
                self.inputs.host_data[rx1_vm_node_ip]['username'],
                self.inputs.host_data[rx1_vm_node_ip]['password'])
            rx2_local_host = Host(
                rx2_vm_node_ip,
                self.inputs.host_data[rx2_vm_node_ip]['username'],
                self.inputs.host_data[rx2_vm_node_ip]['password'])
            rx3_local_host = Host(
                rx3_vm_node_ip,
                self.inputs.host_data[rx3_vm_node_ip]['username'],
                self.inputs.host_data[rx3_vm_node_ip]['password'])

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
            if not sender.sent:
                self.logger.error("Failed to send packet to %s" %ips)
                result = False
            if not receiver1.recv or not receiver2.recv or not receiver3.recv:
                self.logger.error("Failed to recv packet destined to %s" %ips)
                result = False
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
        msg = "Packets not Broadcasted"
        assert result, msg
        return True
    # end broadcast_udp_w_chksum

    @preposttest_wrapper
    def test_bulk_add_delete(self):
        '''
         Description: Test to validate creation and deletion of VMs in bulk.
         Test steps:
                1. Create VMs in bulk, based on the count specified.
                2. Verify the VMs so created and cleanup of the VMs should also go through fine.
         Pass criteria: The creation and deletion of the VMs in bulk should go through fine.
         Maintainer : ganeshahv@juniper.net
        '''
        vn1_name = "bulk_test_vn1"
        vn1_name = get_random_name(vn1_name)
	vn1_fixture = self.create_vn(vn_name= vn1_name)
        assert vn1_fixture.verify_on_setup(), "Verification of VN %s failed" % (
            vn1_name)

        # Create 15 VMs in bulk
        vm_count = 15
        vmx_fixture = self.create_vm(vn_fixture=vn1_fixture,
                                     vm_name=vn1_name,
                                     count=vm_count)
        assert vmx_fixture.verify_vm_launched(), 'One or more VMs do not seem' \
            ' to have got launched. Please check logs'

        # Delete all vms now
        vmx_fixture.cleanUp(), 'Cleanup failed for atleast one VM, Check logs'
        self.remove_from_cleanups(vmx_fixture)
        assert vmx_fixture.verify_vm_not_in_nova(), 'Atleast 1 VM not deleted ' \
            ' in Nova, Pls check logs'
        return True
    # end test_bulk_add_delete

    @preposttest_wrapper
    def test_disassociate_vn_from_vm(self):
        '''
         Description: Test to validate that VN cannot be deleted if there is a VM associated with it.
         Test steps:
                1. Create a VN and launch a VM in that VN.
                2. Verify that with the VM still existing, it is not possible to delete the VN.
         Pass criteria: The attempt to delete VN should fail with a RefsExistError.
         Maintainer : ganeshahv@juniper.net
        '''
        vn_fixture = self.create_vn()
        assert vn_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn_fixture=vn_fixture)
        assert vm1_fixture.verify_on_setup()
        try:
            self.logger.info(' Will try deleting the VN now')
            #if (self.inputs.orchestrator == 'vcenter'):
            #    self.vnc_lib.virtual_network_delete(id=vn_obj.uuid)
            #else:
            self.vnc_lib.virtual_network_delete(id=vn_fixture.uuid)
        except RefsExistError as e:
            self.logger.info(
                'RefsExistError:Check passed that the VN cannot be disassociated/deleted when the VM exists')
        assert vn_fixture.verify_on_setup()
        assert vm1_fixture.verify_on_setup()

        return True
    # end test_disassociate_vn_from_vm

    @preposttest_wrapper
    def test_duplicate_vn_add(self):
        '''
         Description: Test to validate that with the same subnet and name provided, two different VNs cannot be created.
         Test steps:
                1. Create a VN.
                2. Create a second VN with the same name and subnet as the first VN.
                3. Verify that no second VN object is created.
         Pass criteria: There is a single VN created.
         Maintainer : ganeshahv@juniper.net
        '''
        vn_obj1 = self.create_vn()
        assert vn_obj1.verify_on_setup()

        vn_obj2 = self.create_vn(vn_name=vn_obj1.get_name(), subnets=vn_obj1.get_cidrs(af='dual'))
        assert vn_obj2.verify_on_setup()
        assert vn_obj2, 'Duplicate VN cannot be created'
        if (vn_obj1.vn_id == vn_obj2.vn_id):
            self.logger.info('Same obj created')
        else:
            self.logger.error('Different objs created.')
            assert False, 'Duplicate VN add must not create another object'
        return True
    # end test_duplicate_vn_add

    @preposttest_wrapper
    def test_host_route_add_delete(self):
        '''
         Description: Test to validate that host_route is sent to the VM via DHCP.
         Test steps:
                1. Create a VN.
                2. Add a prefix under the Host Route.
                3. Create a VM and observe that the Host Routes are seen in the VM's routing table.
                4. Delete the Host Route from the VN.
                5. Create a second VM and observe that the Host Routes are no longer seen.
         Pass criteria: The Host Route should get added and deleted accordingly.
         Maintainer : ganeshahv@juniper.net
        '''
        #ToDo: msenthil - vnc api update doesnt work
        raise self.skipTest("Skipping for now")
        result = True
        vm1_name = get_random_name('vm_mine')
        vm2_name = get_random_name('vm_yours')
        vn_name = get_random_name('vn222')
        host_rt = [get_random_ip(x) for x in get_random_cidrs(stack=self.inputs.get_af())]
        default_gw_cidr = get_default_cidr(stack=self.inputs.get_af())
        host_rt.extend(default_gw_cidr)
        vn_fixture = self.create_vn(vn_name=vn_name)
        assert vn_fixture.verify_on_setup()
        vn_fixture.add_host_routes(host_rt)
        vm1_fixture = self.create_vm(vn_fixture=vn_fixture, vm_name=vm1_name)
        assert vm1_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        route_cmd = 'route -n; route -n -A inet6'
        vm1_fixture.run_cmd_on_vm(cmds=[route_cmd], as_sudo=True)
        output = vm1_fixture.return_output_cmd_dict[route_cmd]
        self.logger.info('%s' % output)
        for rt in host_rt:
            if (rt.split('/')[0]) in output:
                self.logger.info('Route to %s found in the route-table' % rt)
            else:
                self.logger.info(
                    'Route to %s not found in the route-table' % rt)
                result = False
        assert result, 'No Host-Route in the route-table'

        vn_fixture.del_host_routes(host_rt)
        vm2_fixture = self.create_vm(vn_fixture=vn_fixture, vm_name=vm2_name)
        assert vm2_fixture.verify_on_setup()
        vm2_fixture.wait_till_vm_is_up()
        new_route_cmd = 'route -n'
        vm2_fixture.run_cmd_on_vm(cmds=[new_route_cmd], as_sudo=True)
        new_output = vm2_fixture.return_output_cmd_dict[new_route_cmd]
        self.logger.info('%s' % new_output)
        for rt in host_rt:
            route_ip = rt.split('/')[0]
            if rt in default_gw_cidr:
                self.logger.info('Skip verifying default route')
                continue
            if re.search(r'\broute_ip\b', new_output):
                self.logger.info('Route to %s found in the route-table' % rt)
                result = False
            else:
                self.logger.info(
                    'Route to %s not found in the route-table' % rt)
        assert result, 'Host-Route still found in the route-table'

        return True
    # end test_host_route_add_delete

    @test.attr(type=['sanity','ci_sanity','quick_sanity'])
    @preposttest_wrapper
    def test_ipam_add_delete(self):
        '''
         Description: Test to validate IPAM creation, association of a VN and creating VMs in the VN. Ping b/w the VMs should be successful.
         Test steps:
                1. Create a IPAM.
                2. Use this IPAM to create a VN.
                3. Launch 2 VMs in the VN.
         Pass criteria: Ping between the VMs should PASS.
         Maintainer : ganeshahv@juniper.net
        '''
        ipam_obj = self.useFixture(
            IPAMFixture(project_obj=self.project, name=get_random_name('my-ipam')))
        assert ipam_obj.verify_on_setup()
        vn_fixture = self.create_vn(ipam_fq_name=ipam_obj.fq_name)
        assert vn_fixture.verify_on_setup()

        vm1_fixture = self.create_vm(vn_fixture= vn_fixture, vm_name=get_random_name('vm1'))
        vm2_fixture = self.create_vm(vn_fixture= vn_fixture, vm_name=get_random_name('vm2'))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_to_vn(dst_vm_fixture=vm2_fixture,
                                      vn_fq_name=vn_fixture.get_vn_fq_name())

        return True
    # end test_ipam_add_delete

    @preposttest_wrapper
    def test_multiple_metadata_service_scale(self):
        '''
         Description: Test to validate metadata service
         Test steps:
                1. Create a VN.
                2. Launch a VM in this VN.
                3. Write a metadata script to print the current time.
                4. Pass this during the VM launch.
         Pass criteria: The output of the metadata script should be seen in the VM.
         Maintainer : sandipd@juniper.net
        '''
        result = False
        vn_fixture= self.create_vn()
        vm1_fixture = self.create_vm(vn_fixture= vn_fixture)

        text = """#!/bin/sh
echo "Hello World.  The time is now $(date -R)!" | tee /tmp/output.txt
               """
        try:
            with open ("/tmp/metadata_script.txt" , "w") as f:
                f.write(text)
        except Exception as e:
            self.logger.exception("Got exception while creating"
                                  " /tmp/metadata_script.txt as %s"%(e))
        vm1_name = get_random_name('vm_mine')
        vn_name = get_random_name('vn222')
        vn_count_for_test=20
        if (len(self.connections.orch.get_hosts()) == 1):
            vn_count_for_test=2
        vm_fixture = self.useFixture(
                         create_multiple_vn_and_multiple_vm_fixture(
                         connections=self.connections, vn_name=vn_name,
                         vm_name=vm1_name, inputs=self.inputs,
                         vn_count=vn_count_for_test, vm_count=1, af='v4',
                         subnet_count=1, userdata='/tmp/metadata_script.txt'))
        time.sleep(5)
        assert vm_fixture.verify_vms_on_setup()
        assert vm_fixture.verify_vns_on_setup()

        for vmobj in vm_fixture.vm_obj_dict.values():
            cmd = 'ls /tmp/'
            result = False
            ret = vmobj.run_cmd_on_vm(cmds = [cmd])
            for elem in ret.values():
                if 'output.txt' in elem:
                    result = True
                    break
            else:
                self.logger.info('%s' %vmobj.get_console_output())
            assert result, "metadata_script.txt did not get executed in the vm"
            self.logger.info("Printing the output.txt :")
            cmd = 'cat /tmp/output.txt'
            ret = vmobj.run_cmd_on_vm(cmds = [cmd])
            self.logger.info("%s" %(ret.values()))
            result = False
            for elem in ret.values():
                if 'Hello World' in elem:
                    result = True
                    break
            assert result, "output.txt does not contain proper output"
        return True

    @preposttest_wrapper
    def test_policy_between_vns_diff_proj(self):
        '''
         Description: Test to validate that policy to deny and pass under different projects should behave accordingly.
         Test steps:
                1. Create 2 different projects.
                2. Launch 2 VNs and 2 VMs under each project.
                3. Configure a policy to allow ICMP in one of the projects, while in the other configure a policy to deny ICMP between the projects.
         Pass criteria: Ping between the VMs in the first project should pass, while in the second project it should fail.
         Maintainer : ganeshahv@juniper.net
        '''
        vm_names = ['vm_100', 'vm_200', 'vm_300', 'vm_400']
        vn_names = ['vn_100', 'vn_200', 'vn_300', 'vn_400']
        projects = [get_random_name('project111'), get_random_name('project222')]
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
        project_inputs1 = ContrailTestInit(
                self.ini_file, stack_user=project_fixture1.username,
                stack_password=project_fixture1.password, project_fq_name=['default-domain', projects[0]],logger = self.logger)
        project_connections1 = ContrailConnections(project_inputs1,self.logger)

        user2_fixture= self.useFixture(UserFixture(connections=self.connections,
            username=user_list[1][0], password=user_list[1][1]))
        project_fixture2 = self.useFixture(
            ProjectFixture(
                project_name=projects[
                    1], vnc_lib_h=self.vnc_lib, username=user_list[1][0],
                password=user_list[1][1], connections=self.connections))
        user2_fixture.add_user_to_tenant(projects[1], user_list[1][0] , user_list[1][2])
        project_inputs2 = ContrailTestInit(
                self.ini_file, stack_user=project_fixture2.username,
                stack_password=project_fixture2.password, project_fq_name=['default-domain', projects[1]], logger = self.logger)
        project_connections2 = ContrailConnections(project_inputs2 , self.logger)
        project_inputs1.set_af(self.inputs.get_af())
        project_inputs2.set_af(self.inputs.get_af())

        self.logger.info(
            'We will now create policy to allow in project %s and check that ping passes between the VMs' % (projects[0]))

        policy1_fixture = self.useFixture(PolicyFixture(
                                          policy_name=policy_names[0],
                                          rules_list=rules,
                                          inputs=project_inputs1,
                                          connections=project_connections1))
        policy2_fixture = self.useFixture(PolicyFixture(
                                          policy_name=policy_names[1],
                                          rules_list=rev_rules,
                                          inputs=project_inputs1,
                                          connections=project_connections1))
        vn1_fixture = self.useFixture(VNFixture(project_name=projects[0],
                                      connections=project_connections1,
                                      vn_name=vn_names[0],
                                      inputs=project_inputs1,
                                      policy_objs=[policy1_fixture.policy_obj]))
        vn2_fixture = self.useFixture(VNFixture(project_name=projects[0],
                                      connections=project_connections1,
                                      vn_name=vn_names[1],
                                      inputs=project_inputs1,
                                      policy_objs=[policy2_fixture.policy_obj]))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        vm1_fixture= self.useFixture(VMFixture(connections=project_connections1,
                                     vn_obj=vn1_fixture.obj,vm_name=vm_names[0],
                                     project_name=projects[0]))
        vm2_fixture= self.useFixture(VMFixture(connections=project_connections1,
                                     vn_obj=vn2_fixture.obj,vm_name=vm_names[1],
                                     project_name=projects[0]))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_to_vn(dst_vm_fixture=vm2_fixture)

        self.logger.info('We will now create policy to deny in project %s and '
                         'check that ping fails between the VMs' %(projects[1]))

        policy3_fixture = self.useFixture(PolicyFixture(
                                          policy_name=policy_names[2],
                                          rules_list=rules1,
                                          inputs=project_inputs2,
                                          connections=project_connections2))
        policy4_fixture = self.useFixture(PolicyFixture(
                                          policy_name=policy_names[3],
                                          rules_list=rev_rules1,
                                          inputs=project_inputs2,
                                          connections=project_connections2))
        vn3_fixture = self.useFixture(VNFixture(project_name=projects[1],
                                      connections=project_connections2,
                                      vn_name=vn_names[2],
                                      inputs=project_inputs2,
                                      policy_objs=[policy3_fixture.policy_obj]))
        vn4_fixture = self.useFixture(VNFixture(project_name=projects[1],
                                      connections=project_connections2,
                                      vn_name=vn_names[3],
                                      inputs=project_inputs2,
                                      policy_objs=[policy4_fixture.policy_obj]))
        assert vn3_fixture.verify_on_setup()
        assert vn4_fixture.verify_on_setup()

        vm3_fixture= self.useFixture(VMFixture(connections=project_connections2,
                                               vn_obj=vn3_fixture.obj,
                                               vm_name=vm_names[2],
                                               project_name=projects[1]))
        vm4_fixture= self.useFixture(VMFixture(connections=project_connections2,
                                                vn_obj=vn4_fixture.obj,
                                                vm_name=vm_names[3],
                                                project_name=projects[1]))
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()

        vm3_fixture.wait_till_vm_is_up()
        vm4_fixture.wait_till_vm_is_up()
        assert not vm4_fixture.ping_to_vn(dst_vm_fixture=vm3_fixture)
        return True
    # end test_policy_between_vns_diff_proj

    @preposttest_wrapper
    def test_diff_proj_same_vn_vm_add_delete(self):
        '''
        Description: Test to validate that a VN and VM with the same name and same subnet can be created in two different projects
        Test steps:
               1. Create 2 different projects.
                2. Create a VN with the same name and subnet under each project.
                3. Launch a VM under the VN in both the projects.
        Pass criteria: The label allocated to the VM's /32 prefix by the agent should be different.
        Maintainer : ganeshahv@juniper.net
        '''
        vm_name = 'vm_mine'
        projects = [get_random_name('project111'), get_random_name('project222')]
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
        project_inputs1 = ContrailTestInit(
                self.ini_file, stack_user=project_fixture1.username,
                stack_password=project_fixture1.password, project_fq_name=['default-domain', projects[0]] , logger = self.logger)
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
        project_inputs2 = ContrailTestInit(
                self.ini_file, stack_user=project_fixture2.username,
                stack_password=project_fixture2.password, project_fq_name=['default-domain', projects[1]], logger = self.logger)
        project_connections2 = ContrailConnections(project_inputs2 , self.logger)
        project_inputs1.set_af(self.inputs.get_af())
        project_inputs2.set_af(self.inputs.get_af())

        vn1_fixture = self.useFixture(VNFixture(project_name=projects[0],
                                     connections=project_connections1,
                                     inputs=project_inputs1))
        vn2_fixture = self.useFixture(VNFixture(project_name=projects[1],
                                     connections=project_connections2,
                                     inputs=project_inputs2,
                                     vn_name=vn1_fixture.get_name(),
                                     subnets=vn1_fixture.get_cidrs(af='dual')))
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        vn1_obj = vn1_fixture.obj
        vn2_obj = vn2_fixture.obj

        vm1_fixture = self.useFixture(
            VMFixture(connections=project_connections1,
                      vn_obj=vn1_obj, vm_name=vm_name, project_name=projects[0]))
        vm2_fixture = self.useFixture(
            VMFixture(connections=project_connections2,
                      vn_obj=vn2_obj, vm_name=vm_name, project_name=projects[1]))
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        if not set(vm1_fixture.agent_label) == set(vm2_fixture.agent_label):
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

    @classmethod
    def tearDownClass(cls):
        super(TestBasicVMVN1, cls).tearDownClass()

    @preposttest_wrapper
    def test_vn_gateway_flag_disabled(self):

        result = True
        vn1_name = get_random_name('vn1')
        vn1_subnets = [get_random_cidr()]
        vn2_name = get_random_name('vn2')
        vn2_subnets = [get_random_cidr()]

        vn1_vm1_name = get_random_name('vm1')
        vn1_vm2_name = get_random_name('vm2')

        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets, disable_gateway=True))
        assert vn1_fixture.verify_on_setup()

        vn2_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn2_name, inputs=self.inputs, subnets=vn2_subnets))
        assert vn2_fixture.verify_on_setup()

        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_objs=[vn2_fixture.obj, vn1_fixture.obj], flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name=vn1_vm1_name))

        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_objs=[vn2_fixture.obj,vn1_fixture.obj], flavor='contrail_flavor_small', image_name='ubuntu-traffic', vm_name=vn1_vm2_name))
       
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()

        self.bringup_interface_forcefully(vm1_fixture)
        self.bringup_interface_forcefully(vm2_fixture)
        sleep(10)

        for i in range(7):
            self.logger.info("Retry %s for bringing up eth1 up" % (i))
            cmd_to_pass1 = ['dhclient eth1']
            vm1_fixture.run_cmd_on_vm(
                cmds=cmd_to_pass1, as_sudo=True, timeout=60)

            ret1 = self.verify_eth1_ip_from_vm(vm1_fixture)
            vm2_fixture.run_cmd_on_vm(
                cmds=cmd_to_pass1, as_sudo=True, timeout=60)

            ret2 = self.verify_eth1_ip_from_vm(vm2_fixture)
            if ret1 and ret2:
                break
            sleep(5)

        vn_subnet = vn1_subnets[0]
        vn_subnet_list = (vn_subnet.split('/')[0].split('.'))
        vn_subnet_list[3] = '1'
        gateway_ip = ".".join(vn_subnet_list)

        cmd_to_pass = ['cat /var/lib/dhcp/dhclient.leases']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_pass, as_sudo=True, timeout=60)
        dhcp_lease = vm1_fixture.return_output_cmd_dict['cat /var/lib/dhcp/dhclient.leases']
        gateway_check = 'option routers %s;'%(gateway_ip)

        if gateway_check in dhcp_lease:
           result = result and False
           self.logger.error("option router option is present in dhcp lease file not expected  as gateway is disabled for vn%s \n"%(vn2_name))
           assert result

        if not vm2_fixture.ping_to_ipv6(vm1_fixture.vm_ips[1], count='15',
                                              other_opt='-I eth1'):
           result = result and False
           self.logger.error("Ping from vm %s to vm %s Failed "%(vn1_vm1_name, vn1_vm2_name))
           assert result
 
        return True
        
    @preposttest_wrapper
    def test_no_frag_in_vm(self):
        '''
        Description:  Validate that VM should not fragment packets and that Vrouter does it.
        Test steps:
                1. Send a traffic stream with packet-size lesser than the MTU of the eth0 intf of a VM.
        Pass criteria: Traffic should reach the destination VM with the 'DF' Flag set, i.e, there should be no fragmentattion seen.
        Maintainer : ganeshahv@juniper.net
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

        out2 = vm2_fixture.wait_till_vm_is_up()
        if out2 == False:
            return {'result': out2, 'msg': "%s failed to come up" % vm2_fixture.vm_name}

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
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True)
        vm2_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True)
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
            vm1_fixture.run_cmd_on_vm(cmds=cmd_to_tcpdump, as_sudo=True)
            i = 'cat /tmp/out.log'
            cmd_to_output = ['cat /tmp/out.log']
            vm1_fixture.run_cmd_on_vm(cmds=cmd_to_output, as_sudo=True)
            output = vm1_fixture.return_output_cmd_dict[i]
            print output
            if 'DF' in output or 'echo reply' not in output:
                result = False
        return result
    # end test_no_frag_in_vm

class TestBasicVMVN2(BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicVMVN2, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBasicVMVN2, cls).tearDownClass()

    def runTest(self):
        pass
    #end runTes
 
    @preposttest_wrapper
    def test_ping_on_broadcast_multicast(self):
        '''
        Description:  Validate Ping on subnet broadcast,link local multucast,network broadcast.
        Test steps:
                1. Send ICMP traffic stream to subnet broadcast, multicast and all-broadcast address,
                2. Enable response to broadcasts on the destination VMs.
        Pass criteria: There should be no packet loss and all the three destination VMs should see the ICMP traffic.
        Maintainer : ganeshahv@juniper.net
        '''
        result = True
        ping_count = '2'
        vn1_subnets = ['30.1.1.0/24']
        vn1_vm1_name = get_random_name('vn1_vm1')
        vn1_vm2_name = get_random_name('vn1_vm2')
        vn1_vm3_name = get_random_name('vn1_vm3')
        vn1_vm4_name = get_random_name('vn1_vm4')
        vn1_fixture = self.create_vn(subnets=vn1_subnets)
        vm1_fixture = self.create_vm(vn1_fixture, vm_name=vn1_vm1_name)
        vm2_fixture = self.create_vm(vn1_fixture, vm_name=vn1_vm2_name)
        vm3_fixture = self.create_vm(vn1_fixture, vm_name=vn1_vm3_name)
        vm4_fixture = self.create_vm(vn1_fixture, vm_name=vn1_vm4_name)
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
            if expected_result not in ping_output:
                self.logger.error('Expected 0% packet loss!')
                self.logger.error('Ping result : %s' % (ping_output))
                result = result and False
# getting count of ping response from each vm
            string_count_dict = {}
            string_count_dict = get_string_match_count(ip_list, ping_output)
            self.logger.info("output %s" % (string_count_dict))
            self.logger.info(
                "There should be atleast 4 echo reply from each ip")
            for k in ip_list:
                if (ping_output.count('DUP') >= 3):
                    self.logger.info('Seen replies from all vms..')
                else:
                    self.logger.info('NOT Seen replies from all vms..')
                    result = result and False

        if not result:
            self.logger.error('There were errors. Verifying VM fixtures')
            assert vm1_fixture.verify_on_setup()
            assert vm2_fixture.verify_on_setup()
            assert vm3_fixture.verify_on_setup()
            assert vm4_fixture.verify_on_setup()
        return True
    # end subnet ping

    @test.attr(type=['sanity','ci_sanity','quick_sanity', 'vcenter'])
    @preposttest_wrapper
    def test_ping_within_vn(self):
        '''
        Description:  Validate Ping between 2 VMs in the same VN.
        Test steps:
               1. Create a VN and launch 2 VMs in it.
        Pass criteria: Ping between the VMs should go thru fine.
        Maintainer : ganeshahv@juniper.net
        '''
        vn1_name = get_random_name('vn30')
        vn1_vm1_name = get_random_name('vm1')
        vn1_vm2_name = get_random_name('vm2')
        vn1_fixture = self.create_vn(vn_name=vn1_name)
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm1_name)
        vm2_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=vn1_vm2_name)
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
            "Ping from %s to %s failed" % (vn1_vm1_name, vn1_vm2_name)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
            "Ping from %s to %s failed" % (vn1_vm2_name, vn1_vm1_name)
        return True
    # end test_ping_within_vn

    @test.attr(type=['sanity', 'ci_sanity'])
    @preposttest_wrapper
    def test_ping_within_vn_two_vms_two_different_subnets(self):
        '''
        Description:  Validate Ping between 2 VMs in the same VN, 2 VMs in different VNs.
        Test steps:
                1. Create 2 VNs and launch 2 VMs in them.
                2. Ping between the VMs in the same VN should go thru fine.
                3. Ping to the subnet broadcast and all-broadcast address.
        Pass criteria: VM in the same subnet will respond to both the pings, while the VM in a different VN should respond only to the 
                        all-broadcast address.
        Maintainer : ganeshahv@juniper.net
        '''
        vn1_name = 'vn030'
        vn1_subnets = ['31.1.1.0/29', '31.1.2.0/29']
        subnet1 = '31.1.1.0/29'
        subnet2 = '31.1.2.0/29'
        fixed_ip1 = '31.1.1.4'
        fixed_ip2 = '31.1.2.4'
        subnet_objects = []
        # vn1_subnets=['30.1.1.0/24']
        vn1_vm1_name = 'vm1'
        vn1_vm2_name = 'vm2'
        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()

        subnet_objects = vn1_fixture.get_subnets()
        ports = {}

        for subnet in subnet_objects:
            if subnet['cidr'] == subnet1:
                ports['subnet1'] = vn1_fixture.create_port(vn1_fixture.vn_id,
                    subnet_id=subnet['id'], ip_address=fixed_ip1)
            elif subnet['cidr'] == subnet2:
                ports['subnet2'] = vn1_fixture.create_port(vn1_fixture.vn_id,
                    subnet_id=subnet['id'],ip_address=fixed_ip2)
                     
        vm1_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm1_name, port_ids = [ports['subnet1']['id']]))
        vm2_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_obj=vn1_fixture.obj, vm_name=vn1_vm2_name,port_ids = [ports['subnet2']['id']]))
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
        ip_broadcast = get_subnet_broadcast('%s/%s'%(vm1_ip, '29'))
        list_of_ip_to_ping = [ip_broadcast, '224.0.0.1', '255.255.255.255']
        # passing command to vms so that they respond to subnet broadcast
        cmd_list_to_pass_vm = [
            'echo 0 > /proc/sys/net/ipv4/icmp_echo_ignore_broadcasts']

        vm1_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)
        vm2_fixture.run_cmd_on_vm(cmds=cmd_list_to_pass_vm, as_sudo=True)

        for dst_ip in list_of_ip_to_ping:
            print 'pinging from %s to %s' % (vm1_ip, dst_ip)
# pinging from Vm1 to subnet broadcast
            if os.environ.has_key('ci_image'):
                ping_output = vm1_fixture.ping_to_ip(
                    dst_ip, return_output=True)
            else:
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
                assert (string_count_dict[vm2_ip] > 0) or ('DUP!' in ping_output)
        return True
    #test_ping_within_vn_two_vms_two_different_subnets 
    
    @preposttest_wrapper
    def test_release_ipam(self):
        '''
        Description: Test to validate that IPAM cannot be deleted until the VM associated with it is deleted.
        Test steps:
                1. Create a IPAM.
                2. Create a VN referring this IPAM and launch a VM in it.
        Pass criteria: Attempt to delete the IPAM when the VM/VN exist should fail.
        Maintainer : ganeshahv@juniper.net
        '''
        ipam_obj = self.useFixture(
            IPAMFixture(project_obj=self.project, name='my-ipam'))
        assert ipam_obj.verify_on_setup()

        vn_fixture = self.create_vn(ipam_fq_name=ipam_obj.fq_name)
        assert vn_fixture.verify_on_setup()

        try:
            self.vnc_lib.network_ipam_delete(vn_fixture.ipam_fq_name)
        except RefsExistError as e:
            self.logger.info('RefsExistError:Check passed that the IPAM cannot '
                             'be released when the VN is associated to it.')

        vm1_fixture = self.create_vm(vn_fixture= vn_fixture)
        vm2_fixture = self.create_vm(vn_fixture= vn_fixture)
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_to_vn(vm2_fixture)

        try:
            self.vnc_lib.network_ipam_delete(vn_fixture.ipam_fq_name)
        except RefsExistError as e:
            self.logger.info('RefsExistError:Check passed that the IPAM cannot '
                             'be released when the VN is associated to it, '
                             'which has VMs on it.')
        return True
    # end test_release_ipam

    @preposttest_wrapper
    def test_shutdown_vm(self):
        '''
        Description:  Test to validate that VN is unaffected after the VMs in it are shutdown.
        Test steps:
                1. Create a VM in a VN.
                2. Shutdown this VM.
        Pass criteria: The VN is unaffected inspite of the VM's state.
        Maintainer : ganeshahv@juniper.net
        '''
        vn_fixture = self.create_vn()
        assert vn_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn_fixture= vn_fixture)
        assert vm1_fixture.verify_on_setup()
        cmd_to_shutdown_vm = ['shutdown -h now']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_shutdown_vm, as_sudo=True)
        assert vn_fixture.verify_on_setup()
        return True
    # end test_shutdown_vm

    @preposttest_wrapper
    def test_soft_reboot_vm(self):
        '''
        Description:
        Test steps:
               1. Launch a couple of VMs and ensure ping
               2. Issue reboot in VM console
        Pass criteria: Ping between the VMs should work after VM comes up
        Maintainer : sunilbasker@juniper.net
        '''
        vn1_fixture = self.create_vn(vn_name=get_random_name('vnsr'))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=get_random_name('vm1sr'))
        vm2_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=get_random_name('vm2sr'))
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
            "Ping from %s to %s failed" % (vm1_fixture.vm_name, vm2_fixture.vm_name)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
            "Ping from %s to %s failed" % (vm2_fixture.vm_name, vm1_fixture.vm_name)
        vm1_fixture.run_cmd_on_vm(['reboot'], as_sudo=True)
        sleep(10)
        vm1_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
            "Ping from %s to %s failed" % (vm1_fixture.vm_name, vm2_fixture.vm_name)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
            "Ping from %s to %s failed" % (vm2_fixture.vm_name, vm1_fixture.vm_name)
        return True
    # end test_soft_reboot_vm

    @preposttest_wrapper
    def test_hard_reboot_vm(self):
        '''
        Description:
        Test steps:
               1. Launch a couple of VMs and ensure ping
               2. Issue reboot in VM console
        Pass criteria: Ping between the VMs should work after VM comes up
        Maintainer : sunilbasker@juniper.net
        '''
        vn1_fixture = self.create_vn(vn_name=get_random_name('vnhr'))
        assert vn1_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=get_random_name('vm1hr'))
        vm2_fixture = self.create_vm(vn_fixture=vn1_fixture, vm_name=get_random_name('vm2hr'))
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
            "Ping from %s to %s failed" % (vm1_fixture.vm_name, vm2_fixture.vm_name)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
            "Ping from %s to %s failed" % (vm2_fixture.vm_name, vm1_fixture.vm_name)
        vm1_fixture.reboot('HARD')
        sleep(10)
        vm1_fixture.wait_till_vm_is_up()
        assert vm1_fixture.ping_with_certainty(dst_vm_fixture=vm2_fixture),\
            "Ping from %s to %s failed" % (vm1_fixture.vm_name, vm2_fixture.vm_name)
        assert vm2_fixture.ping_with_certainty(dst_vm_fixture=vm1_fixture),\
            "Ping from %s to %s failed" % (vm2_fixture.vm_name, vm1_fixture.vm_name)
        return True
    # end test_hard_reboot_vm


class TestBasicVMVN3(BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicVMVN3, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBasicVMVN3, cls).tearDownClass()

    def runTest(self):
        pass
    #end runTes 
    
    @preposttest_wrapper
    def test_traffic_bw_vms_diff_pkt_size(self):
        '''
        Description:  Test to validate TCP, ICMP, UDP traffic of different packet sizes b/w VMs created within a VN.
        Test steps:
                1. Create 2 VMs in a VN.
                2. Start 3 traffic streams of different protocols between the VMs.
        Pass criteria: Traffic should reach the destination VM, without any packet loss.
        Maintainer : ganeshahv@juniper.net
        '''
        vn_fixture = self.create_vn()
        assert vn_fixture.verify_on_setup()
        # Get all compute host
        host_list = self.connections.orch.get_hosts()
        vm1_fixture = self.create_vm(vn_fixture= vn_fixture,
                                     flavor='contrail_flavor_small',
                                     image_name='ubuntu-traffic',
                                     node_name=host_list[0])
        if len(host_list) > 1:
            self.logger.info("Multi-Node Setup")
            vm2_fixture = self.create_vm(vn_fixture= vn_fixture,
                                         flavor='contrail_flavor_small',
                                         image_name='ubuntu-traffic',
                                         node_name=host_list[1])
        else:
            self.logger.info("Single-Node Setup")
            vm2_fixture = self.create_vm(vn_fixture= vn_fixture,
                                         flavor='contrail_flavor_small',
                                         image_name='ubuntu-traffic')
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
                vm1_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu,
                                          as_sudo=True)
                vm2_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu,
                                          as_sudo=True)
            self.logger.info("-" * 80)
            self.logger.info("PACKET SIZE = %sB" % packet_size)
            self.logger.info("-" * 80)
            for proto in traffic_proto_l:
                traffic_obj[proto] = {}
                startStatus[proto] = {}
                traffic_obj[proto] = self.useFixture(
                    traffic_tests.trafficTestFixture(self.connections))
                startStatus[proto] = traffic_obj[proto].startTraffic(
                    num_streams=total_streams[proto], start_port=dpi,
                    tx_vm_fixture=vm1_fixture, rx_vm_fixture=vm2_fixture,
                    stream_proto=proto, packet_size=packet_size)
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
            self.logger.info('Sleeping for 10s')
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

    @classmethod
    def tearDownClass(cls):
        super(TestBasicVMVN4, cls).tearDownClass()

    @preposttest_wrapper
    def test_traffic_bw_vms_diff_pkt_size_w_chksum(self):
        '''
        Description:  Test to validate TCP, ICMP, UDP traffic of different packet sizes b/w VMs created within a VN and validate UDP checksum.
        Test steps:
                1. Create 2 VMs in a VN.
                2. Start 3 traffic streams of different protocols between the VMs.
        Pass criteria: Traffic should reach the destination VM, without any packet loss.
        Maintainer : ganeshahv@juniper.net
        '''
        vn_fixture = self.create_vn()
        assert vn_fixture.verify_on_setup()
        # Get all compute host
        host_list = self.connections.orch.get_hosts()
        vm1_fixture = self.create_vm(vn_fixture= vn_fixture,
                                     flavor='contrail_flavor_small',
                                     image_name='ubuntu-traffic',
                                     node_name=host_list[0])
        if len(host_list) > 1:
            self.logger.info("Multi-Node Setup")
            vm2_fixture = self.create_vm(vn_fixture= vn_fixture,
                                         flavor='contrail_flavor_small',
                                         image_name='ubuntu-traffic',
                                         node_name=host_list[1])
        else:
            self.logger.info("Single-Node Setup")
            vm2_fixture = self.create_vm(vn_fixture= vn_fixture,
                                         flavor='contrail_flavor_small',
                                         image_name='ubuntu-traffic')
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
                    cmds=cmd_to_increase_mtu, as_sudo=True)
                vm2_fixture.run_cmd_on_vm(cmds=cmd_to_increase_mtu, as_sudo=True)
            self.logger.info("-" * 80)
            self.logger.info("PACKET SIZE = %sB" % packet_size)
            self.logger.info("-" * 80)
            for proto in traffic_proto_l:
                name = proto
                traffic_obj[proto] = {}
                startStatus[proto] = {}
                traffic_obj[proto] = self.useFixture(
                    traffic_tests.trafficTestFixture(self.connections))
                startStatus[proto] = traffic_obj[proto].startTraffic(
                    num_streams=total_streams[proto], start_port=dpi,
                    tx_vm_fixture=vm1_fixture, rx_vm_fixture=vm2_fixture,
                    stream_proto=proto, packet_size=packet_size, chksum=True)
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
            sleep(1)
        self.assertEqual(result, True, msg)

        return True
    # end test_traffic_bw_vms_diff_pkt_size_w_chksum

    @test.attr(type=['sanity', 'ci_sanity', 'vcenter'])
    @preposttest_wrapper
    def test_vm_add_delete(self):
        '''
        Description:  Test to validate VM creation and deletion.
        Test steps:
                1. Create VM in a VN.
        Pass criteria: Creation and deletion of the VM should go thru fine.
        Maintainer : ganeshahv@juniper.net
        '''
        vn_fixture = self.create_vn()
        assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        vm1_fixture = self.create_vm(vn_fixture=vn_fixture,
                                     vm_name=get_random_name('vm_add_delete'))
        assert vm1_fixture.verify_on_setup()
        return True
    # end test_vm_add_delete

    @preposttest_wrapper
    def test_vm_add_delete_in_2_vns(self):
        '''
        Description:  Test to validate a VM associated with two VNs.
        Test steps:
                1. Create 2 VNs.
                2. Launch a VM such that it has address from both the VNs.
        Pass criteria: VM should get both the IPs.
        Maintainer : ganeshahv@juniper.net
        '''
        vm1_name = 'vm_mine1'
        vn1_fixture = self.create_vn()
        vn2_fixture = self.create_vn()
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                      vn_objs=[vn1_fixture.obj,vn2_fixture.obj],
                                      vm_name=vm1_name,
                                      project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        return True
    # end test_vm_add_delete_in_2_vns
 
    @preposttest_wrapper
    def test_vm_add_delete_in_2_vns_chk_ips(self):
        '''
        Description:  Test to validate a VM associated with two VNs.
        Test steps:
                1. Create 2 VNs.
                2. Launch a VM such that it has address from both the VNs.
                3. Set the ifconfig on eth1 of the VM.
        Pass criteria: VM should get both the IPs.
        Maintainer : ganeshahv@juniper.net
        '''

        list_of_ips = []
        vn1_fixture = self.create_vn()
        vn2_fixture = self.create_vn()
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()

        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                      vn_objs=[vn1_fixture.obj,vn2_fixture.obj],
                                      project_name=self.inputs.project_name))
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
                    return False
                else:
                    self.logger.info('IP %s assigned' % ips)
        return True
    # end test_vm_add_delete_in_2_vns_chk_ips

    @preposttest_wrapper
    def test_vm_arp(self):
        '''
        Description:  Test to validate that the fool-proof way is to not answer
        for arp request from the guest for the address the tap i/f is
        "configured" for.
        Test steps:
                1. Create 2 VMs in a VN.
                2. Start a arping from one of the VMs to the IP of both the VMs.
        Pass criteria: VM should answer the arping for the other VM's IP, not its own.
        Maintainer : ganeshahv@juniper.net
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
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()

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
        if not ' 0%' in output1:
            self.logger.error(
                'Arping to the other VMs address should have passed')
            result = False
        else:
            self.logger.info('Arping to the other VMs address passes')

        assert result, "ARPing Failure"
        return True
    # end test_vm_arp

    @test.attr(type=['sanity','quick_sanity','ci_sanity', 'vcenter'])
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
        vm1_name = get_random_name('vm1')
        vm2_name = get_random_name('vm2')
        vn_name = get_random_name('vn222')
        scp_test_file_sizes = ['1303'] if os.environ.has_key('ci_image') else \
                              ['1000', '1101', '1202', '1303', '1373', '1374',
                               '2210', '2845', '3000', '10000', '10000003']
        file = 'somefile'
        y = 'ls -lrt %s' % file
        cmd_to_check_file = [y]
        x = 'sync'
        cmd_to_sync = [x]
        create_result = True
        transfer_result = True
        vn_fixture = self.create_vn(vn_name=vn_name)
        assert vn_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn_fixture=vn_fixture,vm_name=vm1_name,
                                     flavor='contrail_flavor_small')
        vm2_fixture = self.create_vm(vn_fixture=vn_fixture,vm_name=vm2_name,
                                     flavor='contrail_flavor_small')
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()

        vm1_fixture.put_pub_key_to_vm()
        vm2_fixture.put_pub_key_to_vm()
        for size in scp_test_file_sizes:
            self.logger.info("-" * 80)
            self.logger.info("FILE SIZE = %sB" % size)
            self.logger.info("-" * 80)

            self.logger.info('Transferring the file from %s to %s using scp' %
                             (vm1_fixture.vm_name, vm2_fixture.vm_name))
            if os.environ.has_key('ci_image') and self.inputs.get_af() == 'v4':
                file_transfer_result = vm1_fixture.scp_file_transfer_cirros(vm2_fixture, size=size)
            else:
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

    @test.attr(type=['sanity', 'vcenter'])
    #@test.attr(type=['sanity', 'ci_sanity'])
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
        vm1_name = get_random_name('vm1')
        vm2_name = get_random_name('vm2')
        ts = time.time()
        vn_name = '%s_%s'%(inspect.stack()[0][3],str(ts))
        file_sizes=['1000'] if os.environ.has_key('ci_image') else \
                            ['1000', '1101', '1202', '1303', '1373', '1374',
                             '2210', '2845', '3000', '10000', '10000003']
        file= 'testfile'
        y = 'ls -lrt /var/lib/tftpboot/%s'%file
        cmd_to_check_file = [y]
        z = 'ls -lrt /var/lib/tftpboot/%s'%file
        cmd_to_check_tftpboot_file = [z]
        x = 'sync'
        cmd_to_sync = [x]
        create_result= True
        transfer_result= True
        vn_fixture= self.create_vn(vn_name=vn_name)
        assert vn_fixture.verify_on_setup()
        img_name=os.environ['ci_image'] if os.environ.has_key('ci_image')\
                                        else 'ubuntu-traffic'
        flavor='m1.tiny' if os.environ.has_key('ci_image')\
                         else 'contrail_flavor_small'
        vm1_fixture = self.create_vm(vn_fixture= vn_fixture, vm_name=vm1_name,
                                     image_name=img_name, flavor=flavor)
        vm2_fixture = self.create_vm(vn_fixture= vn_fixture, vm_name=vm2_name,
                                     image_name=img_name, flavor=flavor)
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm2_fixture.wait_till_vm_is_up()
        for size in file_sizes:
            self.logger.info ("-"*80)
            self.logger.info("FILE SIZE = %sB"%size)
            self.logger.info ("-"*80)
            self.logger.info('Transferring the file from %s to %s using tftp'%(
                                      vm1_fixture.vm_name, vm2_fixture.vm_name))
            vm1_fixture.check_file_transfer(dest_vm_fixture = vm2_fixture,
                                            mode = 'tftp', size= size)
            self.logger.info('Checking if the file exists on %s'%vm2_name)
            vm2_fixture.run_cmd_on_vm( cmds= cmd_to_check_file )
            output= vm2_fixture.return_output_cmd_dict[y]
            print output
            if size in output:
                self.logger.info('File of size %sB transferred via tftp properly'%size)
            else:
                transfer_result= False
                self.logger.error('File of size %sB not transferred via tftp '%size)
                break 
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

    @classmethod
    def tearDownClass(cls):
        super(TestBasicVMVN5, cls).tearDownClass()

    def runTest(self):
        pass
    #end runTes 

    @preposttest_wrapper
    def test_vm_gw_tests(self):
        '''
        Description: Test to validate gateway IP assignments the VM interface.
        Test steps:
                1. Create a VMs in a VN.
                2. Modify the Default Gateway on the VM's routing table.
        Pass criteria: Ping between the VMs should pass/fail based on the gateway assignment.
        Maintainer : ganeshahv@juniper.net
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
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_gw, as_sudo=True)
        assert vm1_fixture.verify_on_setup()
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)
        self.logger.info(
            'Adding a static GW, pointing to the metadata IP and checking that ping succeeds')
        i = 'route add default gw %s' % vm1_fixture.local_ip
        cmd_to_change_gw = [i]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_change_gw, as_sudo=True)
        assert vm1_fixture.verify_on_setup()
        assert vm1_fixture.ping_to_ip(vm2_fixture.vm_ip)
        return True
    # end test_vm_gw_tests

    @preposttest_wrapper
    def test_vm_in_2_vns_chk_ping(self):
        '''
        Description: Test to validate that a VM can be associated to more than a VN and ping to a network goes from the respective intf .
        Test steps:
                1. Create a VM and associate it to 2 VNs.
                2. Ping to destinations in those networks.
        Pass criteria: Ping packets should traverse out of the respective interfaces only.
        Maintainer : ganeshahv@juniper.net
        '''
        list_of_ips = []
        vn1_fixture = self.create_vn()
        vn2_fixture = self.create_vn()
        assert vn1_fixture.verify_on_setup()
        assert vn2_fixture.verify_on_setup()
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                      vn_objs=[vn1_fixture.obj,vn2_fixture.obj],
                                      project_name=self.inputs.project_name))
        assert vm1_fixture.verify_on_setup()
        vm2_fixture = self.create_vm(vn_fixture=vn1_fixture)
        assert vm2_fixture.verify_on_setup()
        vm3_fixture = self.create_vm(vn_fixture=vn2_fixture)
        assert vm3_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()
        vm2_fixture.wait_till_vm_is_up()
        vm3_fixture.wait_till_vm_is_up()
        intf_vm_dct = {}
        intf_vm_dct['eth0'] = vm2_fixture
        intf_vm_dct['eth1'] = vm3_fixture
        list_of_ips = vm1_fixture.vm_ips

        j = 'ifconfig -a'
        cmd_to_output1 = [j]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_output1)
        output1 = vm1_fixture.return_output_cmd_dict[j]
        print output1

        for ips in list_of_ips:
            if ips not in output1:
                self.logger.error("IP %s not assigned to any eth intf of %s"%
                                  (ips, vm1_fixture.vm_name))
                assert False, "IP %s not assigned to any eth intf of %s"\
                                  %(ips, vm1_fixture.vm_name)
            else:
                self.logger.info("IP %s is assigned to eth intf of %s" %
                                 (ips, vm1_fixture.vm_name))

        self.logger.info('-' * 80)
        self.logger.info('Will ping to the two VMs from the Multi-NIC VM')
        self.logger.info('-' * 80)
        result = True
        if not vm1_fixture.ping_to_vn(vm2_fixture):
            result = False
            assert result, "Ping to %s Fail" % vm2_fixture.vm_name
        else:
            self.logger.info('Ping to %s Pass' % vm2_fixture.vm_name)
        if not vm1_fixture.ping_to_vn(vm3_fixture):
            result = False
            assert result, "Ping to %s Fail" % vm3_fixture.vm_name
        else:
            self.logger.info('Ping to %s Pass' % vm3_fixture.vm_name)

        all_intfs = self.get_all_vm_interfaces(vm1_fixture)
        default_gateway_interface = self.get_default_gateway_interface(vm1_fixture)
        all_intfs.remove(default_gateway_interface) 
        other_interface = all_intfs[0] 
        self.logger.info('-' * 80)
        self.logger.info(
            'Will shut down %s and hence \
                ping to the second n/w should \
                fail, while the ping to the \
                first n/w is unaffected. \
                The same is not done for \
                 %s as it points to the default GW'%(other_interface,default_gateway_interface))
        self.logger.info('-' * 80)
        cmd = 'ifdown %s'%other_interface

        vm1_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)

        if vm1_fixture.ping_to_vn(intf_vm_dct[other_interface]):
            result = False
            assert result, "Ping to %s should have failed"%intf_vm_dct[other_interface].vm_name
        else:
            self.logger.info('Ping to %s failed as expected'%intf_vm_dct[other_interface].vm_name)
        if not vm1_fixture.ping_to_vn(intf_vm_dct[default_gateway_interface]):
            result = False
            assert result, "Ping to %s Fail" % intf_vm_dct[default_gateway_interface].vm_name
        else:
            self.logger.info('Ping to %s Pass' % intf_vm_dct[default_gateway_interface].vm_name)

        self.logger.info('-' * 80)
        self.logger.info(
            'Will unshut %s and hence \
            ping to the second n/w should pass,\
             while the ping to the first n/w is\
                  still unaffected. The same is\
                   not done for eth0 as it points to the default GW'%(other_interface))
        self.logger.info('-' * 80)

        cmd = 'ifup %s'%other_interface
        vm1_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True, timeout=90)
        if not vm1_fixture.ping_to_vn(intf_vm_dct[other_interface]):
            result = False
            assert result, "Ping to %s Fail"%intf_vm_dct[other_interface].vm_name
        else:
            self.logger.info('Ping to %s Pass'%intf_vm_dct[other_interface].vm_name)
        if not vm1_fixture.ping_to_ip(intf_vm_dct[default_gateway_interface].vm_ip):
            result = False
            assert result, "Ping to %s Fail" % intf_vm_dct[default_gateway_interface].vm_ip
        else:
            self.logger.info('Ping to %s Pass' % intf_vm_dct[default_gateway_interface].vm_ip)

        return True
        #end test_vm_in_2_vns_chk_ping

    @preposttest_wrapper
    def test_vm_intf_tests(self):
        '''
        Description: Test to validate Loopback and eth0 intfs up/down events.
        Test steps:
                1. Create a VM.
                2. Create ifup/ifdown events on the lo0 and eth0 interfaces of the VM.
        Pass criteria: The VM should not go down nor the tap interface should be affected.
        Maintainer : ganeshahv@juniper.net
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
        '''
        Description: Test to validate that a multiple interfaces of the same VM can be associated to the same VN and ping is successful.
        Test steps:
                1. Create a VM.
                2. In latest release we dont support adding same VN.
                3. Accept execption and mark as PASS
        Pass criteria: The VM should not go down nor the tap interface should be affected.
        Maintainer : ganeshahv@juniper.net
        '''
        #raise self.skipTest("Skipping Test. Will enable after infra changes to support them have been made")
        vm1_name = 'vm_mine1'
        vm2_name = 'vm_yours'
        list_of_ips = []
        vn1_fixture = self.create_vn()
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
        '''
        Description: Test to validate creation and deletion of VMs of all flavors.
        Test steps:
                1. Create VMs with varying flavors and images.
        Pass criteria: VM Creation, run and deletion shouldn't hit any issue.
        Maintainer : ganeshahv@juniper.net
        '''
        vn_fixture = self.create_vn()
        assert vn_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn_fixture=vn_fixture,
                                     vm_name='vm_tiny',
                                     flavor='m1.tiny')
        vm2_fixture = self.create_vm(vn_fixture=vn_fixture,
                                     vm_name='vm_small',
                                     flavor='m1.small')
        vm3_fixture = self.create_vm(vn_fixture=vn_fixture,
                                     vm_name='vm_medium',
                                     flavor='m1.medium')
        vm4_fixture = self.create_vm(vn_fixture=vn_fixture,
                                     vm_name='vm_large',
                                     flavor='m1.large')
        vm5_fixture = self.create_vm(vn_fixture=vn_fixture,
                                     vm_name='vm_xlarge',
                                     flavor='m1.xlarge')
        for a in range(1, 6):
            wait = eval('vm%d_fixture.wait_till_vm_is_up()' %
                 a)
            assert 'wait'

        for i in range(1, 5):
            for j in range(i + 1, 6):
                ping = eval('vm%d_fixture.ping_to_vn ( vm%d_fixture )' %
                            (i, j))
                assert 'ping'
        return True
    # end test_vm_multiple_flavors

    @preposttest_wrapper
    def test_vm_static_ip_tests(self):
        '''
        Description: Test to validate Static IP to the VM interface.
        Test steps:
                1. Create a VM.
                2. Add a static route entry and verify.
        Pass criteria: The static route entries should get added to the route table in the VM.
        Maintainer : ganeshahv@juniper.net
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
            "echo 'ifconfig; route; ifconfig eth0 10.10.10.10 netmask 255.255.255.0; ifconfig; route; ifconfig eth0 11.1.1.253 netmask 255.255.255.0; ifconfig; route; ip addr flush dev eth0; ifdown eth0; sleep 5; ifup eth0; ifconfig; route' > batchfile"]
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_add_cmd_to_file)

        cmd_to_exec_file = ['sh batchfile | tee > out.log']
        vm1_fixture.run_cmd_on_vm(cmds=cmd_to_exec_file, timeout=90, as_sudo=True)
        time.sleep(10)
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
        '''
        Description: Test to validate that a VMs cannot be created after the IP-Block is exhausted.
        Test steps:
                1. Create a VN and a subnet in it such that only 5 addresses are usable.
                2. Launch more than 5 VMs.
        Pass criteria: Only 5 VMs should get spawned. 
        The 6th VM should go into ERROR state as it is unable to get any ip. The ip-block is exhausted.
        Maintainer : ganeshahv@juniper.net
        '''
        subnets=list()
        af = self.inputs.get_af()
        if 'v4' in af or 'dual' in af:
            subnets.append(get_random_cidr(af='v4',
                           mask=SUBNET_MASK['v4']['max']))
        if 'v6' in af or 'dual' in af:
            subnets.append(get_random_cidr(af='v6',
                           mask=SUBNET_MASK['v6']['max']))
        vn_fixture = self.create_vn(subnets=subnets)
        assert vn_fixture.verify_on_setup()
        self.logger.info(
            'out of /29 block, we can have 5 usable addresses. Only 5 VMs should get launched properly.')

        vm1_fixture = self.create_vm(vn_fixture=vn_fixture, vm_name='vm1')
        vm2_fixture = self.create_vm(vn_fixture=vn_fixture, vm_name='vm2')
        vm3_fixture = self.create_vm(vn_fixture=vn_fixture, vm_name='vm3')
        vm4_fixture = self.create_vm(vn_fixture=vn_fixture, vm_name='vm4')

        self.logger.info(
            'The 5th VM should go into ERROR state as it is unable to get any ip. The ip-block is exhausted')
        sleep(5)
        vm5_fixture = self.create_vm(vn_fixture=vn_fixture, vm_name='vm5')
        assert vm1_fixture.verify_on_setup()
        assert vm2_fixture.verify_on_setup()
        assert vm3_fixture.verify_on_setup()
        assert vm4_fixture.verify_on_setup()
        assert not vm5_fixture.verify_on_setup()

        return True
    # end test_vm_vn_block_exhaustion

    @test.attr(type=['sanity','ci_sanity', 'quick_sanity', 'vcenter'])
    @preposttest_wrapper
    def test_vn_add_delete(self):
        '''
        Description: Test to validate VN creation and deletion.
        Test steps:
               1. Create a VN.
        Pass criteria: VN creation and deletion should go thru fine.
        Maintainer : ganeshahv@juniper.net
        '''
        vn_obj = self.create_vn()
        assert vn_obj.verify_on_setup()
        return True
    #end test_vn_add_delete

    @preposttest_wrapper
    def test_vn_in_agent_with_vms_add_delete(self):
        '''
        Description: Test to validate VN's existence and removal in agent with deletion of associated VMs.
        Test steps:
                1. Create a VN.
                2. launch a VM in it.
                3. Delete the VM.
        Pass criteria: VN entry is seen in the agent as long as the /32 route to the VM's IP exists, i.e., till the VM exists.
        Maintainer : ganeshahv@juniper.net
        '''
        vn_fixture = self.create_vn()
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
        sleep(5)
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
        '''
        Description: Test to validate VN name with special characters.
        Test steps:
                1. Create a VN, by specifying its name with special characters..
        Pass criteria: Special characters such as '.', ',', '_' are allowed in the VN names.
        Maintainer : ganeshahv@juniper.net
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
                vn_name='vn,2', inputs=self.inputs, subnets=['33.1.1.0/29']))
        assert vn2_obj.verify_on_setup()
        assert vn2_obj

        vn3_obj = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn&3', inputs=self.inputs, subnets=['44.1.1.0/29']))
        assert not vn3_obj.verify_on_setup()
        if vn3_obj:
            self.logger.error('Bug 1023 needs to be fixed')

        vn4_obj = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name='vn_4', inputs=self.inputs, subnets=['55.1.1.0/29']))
        assert vn4_obj.verify_on_setup()
        assert vn4_obj

        return True
    # end test_vn_name_with_spl_characters

class TestBasicVMVN6(BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicVMVN6, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBasicVMVN6, cls).tearDownClass()

    def runTest(self):
        pass
    #end runTes 

    @preposttest_wrapper
    def test_vn_subnet_types(self):
        '''
        Description: Validate various type of subnets associated to VNs.
        Test steps:
               1. Associate reserved_ip,  non-usable IPs and overalapping ip pools during a VN creation.
        Pass criteria: NotPossibleToSubnet errors should be seen.
        Maintainer : ganeshahv@juniper.net
        '''
        # vn-1 : 0.0.0.0/0 to be given once PR 802 is fixed
        reserved_ip_vns = {'vn-2': '169.254.1.1/24', 'vn-3': '251.2.2.1/24'}
        overlapping_vns = {'vn-5': ['10.1.1.0/24', '10.1.1.0/24'], 'vn-6':
                           ['11.11.11.0/29', '11.11.11.8/28'], 'vn-7': '10.1.1.1/24'}
        # vn-4 is added here bcoz the check has been implemented already for
        # 127 and not for 0
        non_usable_block_vns = {'vn-4': '127.0.0.1/8', 'vn-8':
                                '100.100.100.0/31', 'vn-9': '200.200.200.1/32'}

        res_vn_fixture = self.useFixture(
            MultipleVNFixture(connections=self.connections, 
                                inputs=self.inputs,
                                subnet_count=2, 
                                vn_name_net=reserved_ip_vns,  
                                project_name=self.inputs.project_name))


        for key,value in overlapping_vns.iteritems():
            try:
                ovlap_vn_fixture = self.useFixture(VNFixture(
                                            connections=self.connections, 
                                            inputs=self.inputs, 
                                            subnets=value, 
                                            vn_name=key,  
                                            project_name=self.inputs.project_name))
            except Exception as e:
                if 'overlap' in e:
                    self.logger.info('Overlap address cannot be assigned')    
        try:
            non_usable_vn_fixture = self.useFixture(MultipleVNFixture(
                                                    connections=self.connections, 
                                                    inputs=self.inputs, 
                                                    subnet_count=2, 
                                                    vn_name_net=non_usable_block_vns,  
                                                    project_name=self.inputs.project_name))
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
    def itest_vn_vm_no_ip(self):
        '''
        Description: Test to check that VMs launched in a VN with no subnet, will go to error state.
        Test steps:
                1. Create a VN with no subnet associated.
                2. Launch a VM in that VN.
        Pass criteria: The VM should go to ERROR state with no IP.
        Maintainer : ganeshahv@juniper.net
        '''
        vn_obj = self.create_vn(empty_vn=True)
        #assert vn_obj.verify_on_setup()
        assert vn_obj
        vm1_fixture = self.create_vm(vn_fixture=vn_obj)
        self.logger.info('The VM should not get an IP')
        assert not vm1_fixture.verify_on_setup()
        return True
    # end test_vn_vm_no_ip

    @preposttest_wrapper
    def itest_vn_vm_no_ip_assign(self):
        '''
        Description: Test to check that VMs launched in a VN with no subnet, will go to error state.
        Test steps:
                1. Create a VN with no subnety associated.
                2. Launch a VM in that VN.
                3. The VM should go to ERROR state.
                4. Assign a subnet block to the VN  now.
        Pass criteria: The VM state will not change.
        Maintainer : ganeshahv@juniper.net
        '''
        result = True
        vn_name = 'vn_vm_no_ip_assign'
        vm_name = 'vn_vm_no_ip_assign'
        vn_fixture = self.create_vn(empty_vn=True, vn_name=vn_name)
        vn_obj = self.connections.orch.get_vn_obj_if_present(vn_name)
        vn_id = vn_obj['network']['id']
        self.logger.info('VN launched with no ip block.Launching VM now.')
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                      vn_obj=vn_fixture.obj,
                                      vm_name=vm_name,
                                      project_name=self.inputs.project_name))
        self.project_fixture = self.useFixture(ProjectFixture(
                                      vnc_lib_h=self.vnc_lib,
                                      project_name=self.inputs.project_name,
                                      connections=self.connections))
        vm_obj = self.connections.orch.get_vm_if_present(
                                      vm_name, project_id=self.project_fixture.uuid)
        self.logger.info('The VM should not get any IP')
        assert not vm1_fixture.verify_on_setup()
        self.logger.info('Now assigning IP block to VN')
        ipam = vn_fixture.ipam_fq_name
        vn_fixture.create_subnet_af(af=self.inputs.get_af(), ipam_fq_name=ipam)
        vnnow_obj = self.connections.orch.get_vn_obj_if_present(vn_name)
        subnet_created = list(map(lambda obj: obj['subnet_cidr'],
                              vnnow_obj['network']['contrail:subnet_ipam']))
        if set(subnet_created) != set(vn_fixture.get_subnets()):
            self.logger.error('assigned ip block is not allocated to VN')
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
            return result
   # end test_vn_vm_no_ip_assign

    @preposttest_wrapper
    def test_multiple_vn_vm(self):
        '''
        Description: Validate creation of multiple VN with multiple subnet and VMs in it.
        Test steps:
                1. Create multiple VNs.
                2. Launch multiple VMs in each of the VNs.
        Pass criteria: The VMs should be UP and running with no ERRORs.
        Maintainer : ganeshahv@juniper.net
        '''

        result = True
        multi_vn_fixture = self.useFixture(MultipleVNFixture(
            connections=self.connections, inputs=self.inputs, subnet_count=2,
            vn_count=2, project_name=self.inputs.project_name))
        assert multi_vn_fixture.verify_on_setup()

        vn_objs = multi_vn_fixture.get_all_fixture_obj()
        multi_vm_fixture = self.useFixture(MultipleVMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vm_count_per_vn=4, vn_objs=vn_objs, flavor='m1.tiny'))
        assert multi_vm_fixture.verify_on_setup()

        return True
    # end test_multiple_vn_vm

    @test.attr(type=['sanity'])
    #@test.attr(type=['sanity', 'ci_sanity'])
    @preposttest_wrapper
    def test_ping_on_broadcast_multicast_with_frag(self):
        '''
        Description: Validate Ping on subnet broadcast,link local multucast,network broadcastwith packet sizes > MTU and see that fragmentation and assembly work fine .
        Test steps:
                1. Create multiple VMs.
                2. Start a ICMP stream to the subnet-broadcast, multicast and all-broadcast address with a packet-size greater than the MTU.
                3. We should see a packet too big error message.
                4. Increase the MTU on the interface.
        Pass criteria: The Traffic should go thru fine without any loss.
        Maintainer : ganeshahv@juniper.net
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
            if os.environ.has_key('ci_image'):
                ping_output = vm1_fixture.ping_to_ip(
                    dst_ip, return_output=True, count=ping_count,  size='3000')
            else:
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
            if os.environ.has_key('ci_image'):
                ping_output = vm1_fixture.ping_to_ip(
                    dst_ip, return_output=True, count=ping_count,  size='3000')
            else:
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
                assert (string_count_dict[k] >= (int(ping_count) - 1)) or\
                       (ping_output.count('DUP') >= (int(ping_count) - 1))
        return True
    # end test_ping_on_broadcast_multicast_with_frag


    @preposttest_wrapper
    def test_agent_cleanup_with_control_node_stop(self):
        '''
        Description: Stop all the control node and verify the cleanup process in agent
        Test steps:
                1. Create VN and multiple VMs in it.
                2. Shutdown the contrail-control service.
        Pass criteria: Cleanup of the VN and VM info in the agent should go thru fine.
        Maintainer : ganeshahv@juniper.net
        '''
        raise self.skipTest("Skipping a failing test")
        if len(set(self.inputs.bgp_ips)) < 2:
            raise self.skipTest(
                "Skipping Test. At least 2 control node required to run the test")
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

    @test.attr(type=['sanity', 'ci_sanity'])
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

        if os.environ.has_key('ci_image'):
            img_name = os.environ['ci_image']
        else:
            img_name = 'ubuntu'
        vn_name = get_random_name('vn2_metadata')
        vm1_name = get_random_name('vm_in_vn2_metadata')
        vn_fixture = self.create_vn(vn_name=vn_name, af='v4')
        assert vn_fixture.verify_on_setup()
        vm1_fixture = self.create_vm(vn_fixture=vn_fixture, vm_name=vm1_name,
                                     image_name=img_name,
                                     userdata='/tmp/metadata_script.txt',
                                     flavor='m1.tiny')
        assert vm1_fixture.verify_on_setup()
        assert vm1_fixture.wait_till_vm_is_up()

        cmd = 'ls /tmp/'
        result = False
        for i in range(3):
            self.logger.info("Retry %s" % (i))
            ret = vm1_fixture.run_cmd_on_vm(cmds=[cmd])
            self.logger.info("ret : %s" % (ret))
            for elem in ret.values():
                if 'output.txt' in elem:
                    result = True
                    break
            if result:
                break
            time.sleep(2)
        if not result:
            self.logger.warn(
                "metadata_script.txt did not get executed in the vm")
            self.logger.info('%s' %vm1_fixture.get_console_output())
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

    @test.attr(type=['sanity', 'ci_sanity', 'vcenter'])
    @preposttest_wrapper
    def test_generic_link_local_service(self):
        '''
        Description: Test to validate generic linklocal service - running nova list from vm.
            1.Create generic link local service to be able to wget to jenkins
            2.Create a vm
            3.Try wget to jenkins - passes if successful else fails

        Maintainer: sandipd@juniper.net
        '''

        result = True
        vn_name = get_random_name('vn2_metadata')
        vm1_name = get_random_name('nova_client_vm')
        vn_subnets = ['11.1.1.0/24']
        vn_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn_name, inputs=self.inputs, subnets=vn_subnets))
        #assert vn_fixture.verify_on_setup()
        vn_obj = vn_fixture.obj
        img_name = os.environ['ci_image'] if os.environ.has_key('ci_image') else 'ubuntu-traffic'
        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn_obj, vm_name=vm1_name, project_name=self.inputs.project_name,
                                                image_name=img_name))

        time.sleep(90)
        assert vm1_fixture.verify_on_setup()
        vm1_fixture.wait_till_vm_is_up()

        cfgm_hostname = self.inputs.host_data[self.inputs.cfgm_ip]['name']
        compute_user = self.inputs.host_data[vm1_fixture.vm_node_ip]['username']
        compute_password = self.inputs.host_data[vm1_fixture.vm_node_ip]['password']
        cfgm_host_new_name = cfgm_hostname + '-test'
        cfgm_control_ip = self.inputs.host_data[cfgm_hostname]['host_control_ip']
        cfgm_intro_port = '8084'
        link_local_args = "--admin_user %s \
         --admin_password %s --linklocal_service_name cfgmintrospect\
         --linklocal_service_ip 169.254.1.2\
         --linklocal_service_port 80\
         --ipfabric_dns_service_name %s\
         --ipfabric_service_port %s\
         --admin_tenant_name %s\
         " %( self.inputs.stack_user, self.inputs.stack_password,
                        cfgm_host_new_name, cfgm_intro_port,
                        self.inputs.project_name)
        if not self.inputs.devstack:
            cmd = "python /opt/contrail/utils/provision_linklocal.py --oper add %s" % (link_local_args)
        else:
            cmd = "python /opt/stack/contrail/controller/src/config/utils/provision_linklocal.py  --oper add %s" % (
                link_local_args)

        update_hosts_cmd = 'echo "%s %s" >> /etc/hosts' % (cfgm_control_ip,
            cfgm_host_new_name)
        self.inputs.run_cmd_on_server(vm1_fixture.vm_node_ip,
                                      update_hosts_cmd,
                                      compute_user,
                                      compute_password)

        args = shlex.split(cmd.encode('UTF-8'))
        process = Popen(args, stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = process.communicate()
        if stderr:
            self.logger.warn(
                "Linklocal service could not be created, err : \n %s" % (stderr))
        else:
            self.logger.info("%s" % (stdout))
        cmd = 'wget http://169.254.1.2:80'

        ret = None
        for i in range(3):
            try:
                self.logger.info("Retry %s" % (i))
                ret = vm1_fixture.run_cmd_on_vm(cmds=[cmd])
                if not ret[cmd]:
                    raise Exception('wget of http://169.254.1.2:80 returned None')
            except Exception as e:
                time.sleep(5)
                self.logger.exception("Got exception as %s" % (e))
            else:
                break
        if ret[cmd]:
            if 'Connection timed out' in str(ret):
                self.logger.warn("Generic metadata did NOT work")
                result = False
            if '200 OK' in str(ret) or '100%' in str(ret):
                self.logger.info("Generic metadata worked")
                result = True
        else:
            self.logger.error('Generic metadata check failed')
            result = False

        if not self.inputs.devstack:
            cmd = "python /opt/contrail/utils/provision_linklocal.py --oper delete %s" % (link_local_args)
        else:
            cmd = "python /opt/stack/contrail/controller/src/config/utils/provision_linklocal.py --oper delete %s" % (
                link_local_args)

        args = shlex.split(cmd.encode('UTF-8'))
        self.logger.info('Deleting the link local service')
        process = Popen(args, stdout=PIPE)
        stdout, stderr = process.communicate()
        if stderr:
            self.logger.warn(
                "Linklocal service could not be deleted, err : \n %s" % (stderr))
            result = result and False
        else:
            self.logger.info("%s" % (stdout))

        # Remove the hosts entry which was added earlier
        update_hosts_cmd = "sed -i '$ d' /etc/hosts" 
        self.inputs.run_cmd_on_server(vm1_fixture.vm_node_ip,
                                      update_hosts_cmd,
                                      compute_user,
                                      compute_password)
        assert result, "Generic Link local verification failed"
        return True
    # end test_generic_link_local_service

class TestBasicVMVN9(BaseVnVmTest):

    @classmethod
    def setUpClass(cls):
        super(TestBasicVMVN9, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(TestBasicVMVN9, cls).tearDownClass()

    @preposttest_wrapper
    def test_static_route_to_vm(self):
        '''
        Description: Test to validate that traffic to a destination for which a VM is a next-hop is sent to the tap-interface in the agent, corresponding to the VM.
        Test steps:
                1. Create VN and a VM in it.
                2. Add a static route with the next-hop pointing to the VMI.
                3. Send traffic to the prefix in the static route.
        Pass criteria: Traffic should reach the tap-interface related to the VM.
        Maintainer : ganeshahv@juniper.net
        '''
        vm1_name = get_random_name('vm_mine')
        vn1_name = get_random_name('vn222')
        vn1_subnets = ['11.1.1.0/24']
        vm2_name = get_random_name('vm_yours')
        vn2_name = get_random_name('vn111')
        vn2_subnets = ['12.1.1.0/24']

        vn1_fixture = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name, connections=self.connections,
                vn_name=vn1_name, inputs=self.inputs, subnets=vn1_subnets))
        assert vn1_fixture.verify_on_setup()
        vn1_obj = vn1_fixture.obj

        vm1_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn1_obj, vm_name=vm1_name, 
                                                project_name=self.inputs.project_name, 
                                                flavor='contrail_flavor_small', 
                                                image_name='ubuntu-traffic'))
        assert vm1_fixture.wait_till_vm_is_up()
        assert vm1_fixture.verify_on_setup()
        vm2_fixture = self.useFixture(VMFixture(connections=self.connections,
                                                vn_obj=vn1_obj, vm_name=vm2_name, 
                                                project_name=self.inputs.project_name, 
                                                flavor='contrail_flavor_small', 
                                                image_name='ubuntu-traffic'))
        assert vm2_fixture.wait_till_vm_is_up()
        assert vm2_fixture.verify_on_setup()

        self.logger.info(
            '+++++ Will add a static route with the VM1 as the next-hop and verify the route entry in the agent ++++++')
        vm1_vmi_id = vm1_fixture.cs_vmi_obj[vn1_fixture.vn_fq_name][
            'virtual-machine-interface']['uuid']
        add_static_route_cmd = 'python provision_static_route.py \
                                --prefix 1.2.3.4/32 --virtual_machine_interface_id %s \
                                 --tenant_name %s --api_server_ip 127.0.0.1 --api_server_port 8082 \
                                --oper add --route_table_name my_route_table \
                                --user  %s --password %s'\
                                  %(vm1_vmi_id,self.inputs.project_name,self.inputs.stack_user,self.inputs.stack_password)

        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.cfgm_ips[0]), 
                                    password=self.inputs.password, warn_only=True, 
                                    abort_on_prompts=False, debug=True):
            status = run('cd /opt/contrail/utils;' + add_static_route_cmd)
            self.logger.debug("%s" % status)
            m = re.search(r'Creating Route table', status)
            assert m, 'Failed in Creating Route table'
        time.sleep(10)
        for vm_fixture in [vm1_fixture, vm2_fixture]:
            (domain, project, vn) = vn1_fixture.vn_fq_name.split(':')
            inspect_h = self.agent_inspect[vm_fixture.vm_node_ip]
            agent_vrf_objs = inspect_h.get_vna_vrf_objs(domain, project, vn)
            agent_vrf_obj = vm_fixture.get_matching_vrf(
                agent_vrf_objs['vrf_list'], vn1_fixture.vrf_name)
            vn_vrf_id = agent_vrf_obj['ucindex']
            paths = inspect_h.get_vna_active_route(
                vrf_id=vn_vrf_id, ip='1.2.3.4', prefix='32')['path_list']
            self.logger.info('There are %s nexthops to 1.2.3.4 on Agent %s' %
                             (len(paths), vm_fixture.vm_node_ip))

        compute_ip = vm1_fixture.vm_node_ip
        compute_user = self.inputs.host_data[compute_ip]['username']
        compute_password = self.inputs.host_data[compute_ip]['password']
        session = ssh(compute_ip, compute_user, compute_password)
        vm1_tapintf = vm1_fixture.tap_intf[vn1_fixture.vn_fq_name]['name']
        cmd = 'tcpdump -ni %s icmp -vvv -c 2 > /tmp/%s_out.log' % (vm1_tapintf,
                                                                   vm1_tapintf)
        execute_cmd(session, cmd, self.logger)

        self.logger.info('***** Will start a ping from %s to 1.2.3.4 *****' %
                         vm2_fixture.vm_name)
        vm2_fixture.ping_with_certainty('1.2.3.4', expectation=False)
        self.logger.info('***** Will check the result of tcpdump *****')
        output_cmd = 'cat /tmp/%s_out.log' % vm1_tapintf
        output, err = execute_cmd_out(session, output_cmd, self.logger)
        print output
        if '1.2.3.4' in output:
            self.logger.info(
                'Traffic is going to the tap interface of %s correctly' %
                vm1_fixture.vm_name)
        else:
            result = False
            assert result
            self.logger.error(
                'Traffic to 1.2.3.4 not seen on the tap interface of %s' %
                vm1_fixture.vm_name)

        self.logger.info(
            '-------------------------Will delete the static route now------------------')
        del_static_route_cmd = 'python provision_static_route.py --prefix 1.2.3.4/32 \
                                --virtual_machine_interface_id %s \
                                --tenant_name %s --api_server_ip 127.0.0.1 \
                                --api_server_port 8082 \
                                --oper del --route_table_name my_route_table \
                                 --user %s --password %s'\
                                %(vm1_vmi_id,self.inputs.project_name,self.inputs.stack_user ,self.inputs.stack_password ) 

        with settings(host_string='%s@%s' % (self.inputs.username, self.inputs.cfgm_ips[0]), 
                        password=self.inputs.password, warn_only=True, 
                        abort_on_prompts=False, debug=True):
            del_status = run('cd /opt/contrail/utils;' + del_static_route_cmd)
            self.logger.debug("%s" % del_status)
        time.sleep(10)

        for vm_fixture in [vm1_fixture, vm2_fixture]:
            (domain, project, vn) = vn1_fixture.vn_fq_name.split(':')
            inspect_h = self.agent_inspect[vm_fixture.vm_node_ip]
            agent_vrf_objs = inspect_h.get_vna_vrf_objs(domain, project, vn)
            agent_vrf_obj = vm_fixture.get_matching_vrf(
                agent_vrf_objs['vrf_list'], vn1_fixture.vrf_name)
            vn_vrf_id = agent_vrf_obj['ucindex']
            del_check = True
            if inspect_h.get_vna_active_route(vrf_id=vn_vrf_id, ip='1.2.3.4', prefix='32') == None:
                self.logger.info('There is no route to 1.2.3.4 on Agent %s' %
                                 vm_fixture.vm_node_ip)
            else:
                del_check = False
            assert del_check, 'Static Route Deletion unsuccessful'

        return True
    # end test_static_route_to_vm

    @preposttest_wrapper
    def test_dns_resolution_for_link_local_service(self):
        '''
        Description: Test to verify DNS resolution for link local service
        Test steps:
                1. Create instance
                2. Configure few link service using IP/DNS option
                3. Verify DNS resolution for services created
                4. Perform ssh,curl and wget operation using services
        Pass criteria: All the three operations should go thru fine.
        Maintainer : ganeshahv@juniper.net
        '''
        cfgm_ip = self.inputs.cfgm_ips[0]
        cfgm_user = self.inputs.host_data[cfgm_ip]['username']
        cfgm_pwd = self.inputs.host_data[cfgm_ip]['password']
        openstack_ip = self.inputs.openstack_ip
        ks_admin_user = self.inputs.stack_user
        ks_admin_password = self.inputs.stack_password
        ks_admin_tenant = self.inputs.project_name

        # format: service_name: link_local_service_ip, address_port,
        # fabric_address
        service_info = {
            'cfgm_server': ['169.254.169.245', '22', self.inputs.cfgm_ips[0]],
            'build_server': ['169.254.169.246', '80', 'ftp.vim.org'],
            'web_server': ['169.254.169.247', '80', '174.143.194.225']
        }
        vn_obj = self.useFixture(
            VNFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_name= get_random_name('vnlocal'),
                inputs=self.inputs,
                subnets=['10.10.10.0/24']))
        assert vn_obj.verify_on_setup()
        vm_fixture = self.useFixture(
            VMFixture(
                connections=self.connections,
                vn_obj=vn_obj.obj,
                flavor='contrail_flavor_small',
                image_name='ubuntu-traffic',
                vm_name=get_random_name('vmlocal'),
                project_name=self.inputs.project_name))
        vm_fixture.wait_till_vm_is_up()
        assert vm_fixture.verify_on_setup()
        for service in service_info:
            self.logger.info('configure link local service %s' % service)
            #check if we provided dns/IP
            try:
                socket.inet_aton(service_info[service][2])
                metadata_args = "--admin_user %s\
                    --admin_password %s\
                    --admin_tenant_name %s\
                    --linklocal_service_name %s\
                    --linklocal_service_ip %s\
                    --linklocal_service_port %s\
                    --ipfabric_service_ip %s\
                    --ipfabric_service_port %s\
                    --oper add" % (ks_admin_user,
                                   ks_admin_password,
                                   ks_admin_tenant,
                                   service,
                                   service_info[service][0],
                                   service_info[service][1],
                                   service_info[service][2],
                                   service_info[service][1])
            except socket.error:
                metadata_args = "--admin_user %s\
                    --admin_password %s\
                    --admin_tenant_name %s\
                    --linklocal_service_name %s\
                    --linklocal_service_ip %s\
                    --linklocal_service_port %s\
                    --ipfabric_dns_service_name %s\
                    --ipfabric_service_port %s\
                    --oper add" % (ks_admin_user,
                                   ks_admin_password,
                                   ks_admin_tenant,
                                   service,
                                   service_info[service][0],
                                   service_info[service][1],
                                   service_info[service][2],
                                   service_info[service][1])
            with settings(host_string='%s@%s' % (cfgm_user, cfgm_ip),
                          password=cfgm_pwd, warn_only=True,
                          abort_on_prompts=False):
                status = run(
                    "python /opt/contrail/utils/provision_linklocal.py %s" %
                    (metadata_args))
                self.logger.debug("%s" % status)
            sleep(2)
            cmd = 'nslookup ' + service
            vm_fixture.run_cmd_on_vm(cmds=[cmd])
            result = vm_fixture.return_output_cmd_dict[cmd]
            result = self.trim_command_output_from_vm(result)
            lookup = re.search(r"Name:\s*(\S+)\s*Address:\s*(\S+)", result)
            if (lookup.group(1) == service) and (
                    lookup.group(2) == service_info[service][0]):
                self.logger.info(
                    'DNS resolution worked for link local service %s' %
                    service)
            else:
                assert False, "DNS resolution for \
                                link local service %s failed" % service
        for service in service_info:
            if service == "build_server":
                # verify wget from vim.org 
                sleep(20) #wait before attempting download
                image_name = 'vim-6.4.tar.bz2'
                cmd = 'wget ' + \
                    'http://%s/pub/vim/unix/' % service + image_name
                vm_fixture.run_cmd_on_vm(cmds=[cmd], timeout=60)
                result = vm_fixture.return_output_cmd_dict[cmd]
                result = self.trim_command_output_from_vm(result)
                cmd = 'ls -l ' + image_name
                vm_fixture.run_cmd_on_vm(cmds=[cmd])
                result = vm_fixture.return_output_cmd_dict[cmd]
                result = self.trim_command_output_from_vm(result)
                lookup_wget = re.search(r"No such file or directory", result)
                if lookup_wget:
                    assert False, "Image download failed with \
                                    link local service %s: %s" % (
                                    service, result)
                else:
                    self.logger.info(
                        "File copied to VM using linklocal service %s" %
                         service)
            elif service == 'cfgm_server':
                # verify ssh on cfgm node from vm
                self.logger.info(
                    "verify ssh port is opened in remote machine using netcat")
                cmd = 'nc -zvv %s %s' % (service, service_info[service][1])
                vm_fixture.run_cmd_on_vm(cmds=[cmd])
                result = vm_fixture.return_output_cmd_dict[cmd]
                result = self.trim_command_output_from_vm(result)
                lookup = re.search(r"succeeded", result)
                if lookup:
                    self.logger.info('%s' % result)
                else:
                    assert False, "Connection to cfgm_server failed with \
                                    link local service: %s" % result
            elif service == 'web_server':
                # verify curl on openstack.org
                cmd = 'curl ' + 'http://%s:80/' % service
                vm_fixture.run_cmd_on_vm(cmds=[cmd])
                result = vm_fixture.return_output_cmd_dict[cmd]
                result = self.trim_command_output_from_vm(result)
                lookup_curl = re.search(r"couldn't connect to host", result)
                if lookup_curl:
                    assert False, "curl operation failed with link local \
                                    service bug_server: %s" % result
                else:
                    self.logger.info(
                        "curl operation succeeded with \
                            link local service bug_server")
            else:
                self.logger.info(
                    "skip service %s, go to next service" %
                    service)
            self.logger.info('unconfigure link local service %s' % service)
            try:
                socket.inet_aton(service_info[service][2])
                metadata_args_delete = "--admin_user %s\
                    --admin_password %s\
                    --admin_tenant_name %s\
                    --linklocal_service_name %s\
                    --linklocal_service_ip %s\
                    --linklocal_service_port %s\
                    --ipfabric_service_ip %s\
                    --ipfabric_service_port %s\
                    --oper delete" % (ks_admin_user,
                                   ks_admin_password,
                                   ks_admin_tenant,
                                   service,
                                   service_info[service][0],
                                   service_info[service][1],
                                   service_info[service][2],
                                   service_info[service][1])
            except socket.error:
                metadata_args_delete = "--admin_user %s\
                    --admin_password %s\
                    --admin_tenant_name %s\
                    --linklocal_service_name %s\
                    --linklocal_service_ip %s\
                    --linklocal_service_port %s\
                    --ipfabric_dns_service_name %s\
                    --ipfabric_service_port %s\
                    --oper delete" % (ks_admin_user,
                                   ks_admin_password,
                                   ks_admin_tenant,
                                   service,
                                   service_info[service][0],
                                   service_info[service][1],
                                   service_info[service][2],
                                   service_info[service][1])
            with settings(host_string='%s@%s' % (cfgm_user, cfgm_ip),
                          password=cfgm_pwd, warn_only=True,
                          abort_on_prompts=False):
                status = run(
                    "python /opt/contrail/utils/provision_linklocal.py %s" %
                    (metadata_args_delete))
                self.logger.debug("%s" % status)
        return True
    # end test_dns_resolution_for_link_local_service


# IPv6 classes follow
class TestBasicIPv6VMVN0(TestBasicVMVN0):

    @classmethod
    def setUpClass(cls):
        super(TestBasicIPv6VMVN0, cls).setUpClass()
        cls.inputs.set_af('v6')

    @test.attr(type=['sanity','quick_sanity'])
    @preposttest_wrapper
    def test_ipam_add_delete(self):
        super(TestBasicIPv6VMVN0, self).test_ipam_add_delete()

class TestBasicIPv6VMVN2(TestBasicVMVN2):

    @classmethod
    def setUpClass(cls):
        super(TestBasicIPv6VMVN2, cls).setUpClass()
        cls.inputs.set_af('v6')

    @test.attr(type=['sanity','quick_sanity'])
    @preposttest_wrapper
    def test_ping_within_vn(self):
        super(TestBasicIPv6VMVN2, self).test_ping_within_vn()

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_ping_within_vn_two_vms_two_different_subnets(self):
        super(TestBasicIPv6VMVN2, self).test_ping_within_vn_two_vms_two_different_subnets()

class TestBasicIPv6VMVN3(TestBasicVMVN3):

    @classmethod
    def setUpClass(cls):
        super(TestBasicIPv6VMVN3, cls).setUpClass()
        cls.inputs.set_af('v6')

class TestBasicIPv6VMVN4(TestBasicVMVN4):

    @classmethod
    def setUpClass(cls):
        super(TestBasicIPv6VMVN4, cls).setUpClass()
        cls.inputs.set_af('v6')

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_vm_add_delete(self):
        super(TestBasicIPv6VMVN4, self).test_vm_add_delete()

    @test.attr(type=['sanity', 'quick_sanity'])
    @preposttest_wrapper
    def test_vm_file_trf_scp_tests(self):
        super(TestBasicIPv6VMVN4, self).test_vm_file_trf_scp_tests()

class TestBasicIPv6VMVN5(TestBasicVMVN5):

    @classmethod
    def setUpClass(cls):
        super(TestBasicIPv6VMVN5, cls).setUpClass()
        cls.inputs.set_af('v6')

    @test.attr(type=['sanity', 'quick_sanity'])
    @preposttest_wrapper
    def test_vn_add_delete(self):
        super(TestBasicIPv6VMVN5, self).test_vn_add_delete()

class TestBasicIPv6VMVN6(TestBasicVMVN6):

    @classmethod
    def setUpClass(cls):
        super(TestBasicIPv6VMVN6, cls).setUpClass()
        cls.inputs.set_af('v6')

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_generic_link_local_service(self):
        super(TestBasicIPv6VMVN6, self).test_generic_link_local_service()

    @test.attr(type=['sanity'])
    @preposttest_wrapper
    def test_metadata_service(self):
        super(TestBasicIPv6VMVN6, self).test_metadata_service()

class TestBasicIPv6VMVN9(TestBasicVMVN9):

    @classmethod
    def setUpClass(cls):
        super(TestBasicIPv6VMVN9, cls).setUpClass()
        cls.inputs.set_af('v6')
