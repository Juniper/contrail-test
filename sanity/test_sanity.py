import sys
import time
import logging
import os
from contrail_setup import *
from contrail_testbase import *
import argparse


class Test_Sanity(ContrailTestBase):

    def __init__(self, args=''):
        self.parse_args(args)
        self.iniFile = self.args.ini_file
        self.build_id = self.args.build_id
        self.single_node = self.args.single_node

        ContrailTestBase.__init__(
            self, self.iniFile, self.build_id, self.single_node)
        self.node = ContrailSetup(self.username, self.password,
                                  self.provFile, self.single_node, self.key, self.logScenario)
        self.hostname = self.node.get_cfgm_hostname()
    # end __init__

    def parse_args(self, args):

        defaults = {
            'ini_file': 'params.ini',
            'single_node': None,
            'build_id': '0000',
        }
        parser = argparse.ArgumentParser()
        parser.set_defaults(**defaults)
        parser.add_argument('-i', "--ini_file", dest="ini_file",
                            help="Init file which has reference to setup and testcase details")
        parser.add_argument('-s', "--single_node", dest="single_node",
                            help="IP of the All-in-one Single node setup. No need to populate json file in this case ")
        parser.add_argument('-b', '--build_id', dest='build_id',
                            help="Build ID for which you are running the tests. Defaults to 0000")

        self.args = parser.parse_args()
    # end parse_args

    def test_process_state(self):
        result = 1
        compute_services = ['contrail-vrouter', 'openstack-nova-compute']
        control_services = ['contrail-control']
        control_services = ['contrail-control',
                            'contrail-dns', 'contrail-named']
        cfgm_services = ['openstack-cinder-api',
                         'openstack-cinder-scheduler', 'openstack-glance-api',
                         'openstack-glance-registry', 'openstack-keystone',
                         'openstack-nova-api',
                         'openstack-nova-scheduler', 'openstack-nova-cert',
                         'openstack-nova-consoleauth', 'openstack-nova-objectstore',
                         'contrail-api', 'contrail-schema']
        webui_services = ['contrail-webui', 'contrail-webui-middleware']
        collector_services = ['redis', 'contrail-collector',
                              'contrail-opserver', 'contrail-qe']
        for host in self.node.hostIPs:
            if host in self.node.computeIPs:
                for service in compute_services:
                    (state, active_str1, active_str2) = self.node.get_service_status(host,
                                                                                     service, self.username, self.password)
                    if ('enabled', 'active', 'running') == (state, active_str1, active_str2):
                        self.logger.info('On host %s,Service %s states are %s, %s, %s ..OK'
                                         % (host, service, state, active_str1, active_str2))
                    else:
                        result = result & 0
                        self.logger.error('On host %s,Service %s states are %s, %s, %s ..NOT OK!'
                                          % (host, service, state, active_str1, active_str2))
            if host in self.node.bgpIPs:
                for service in control_services:
                    (state, active_str1, active_str2) = self.node.get_service_status(host,
                                                                                     service, self.username, self.password)
                    if ('enabled', 'active', 'running') == (state, active_str1, active_str2):
                        self.logger.info('On host %s,Service %s states are %s, %s, %s ..OK'
                                         % (host, service, state, active_str1, active_str2))
                    else:
                        result = result & 0
                        self.logger.error('On host %s,Service %s states are %s, %s, %s ..NOT OK!'
                                          % (host, service, state, active_str1, active_str2))
            if host == self.node.cfgmIP:
                for service in cfgm_services:
                    (state, active_str1, active_str2) = self.node.get_service_status(host,
                                                                                     service, self.username, self.password)
                    if ('enabled', 'active', 'running') == (state, active_str1, active_str2):
                        self.logger.info('On host %s,Service %s states are %s, %s, %s ..OK'
                                         % (host, service, state, active_str1, active_str2))
                    else:
                        result = result & 0
                        self.logger.error('On host %s,Service %s states are %s, %s, %s ..NOT OK!'
                                          % (host, service, state, active_str1, active_str2))
            if host == self.node.collectorIP:
                for service in collector_services:
                    (state, active_str1, active_str2) = self.node.get_service_status(host,
                                                                                     service, self.username, self.password)
                    if ('enabled', 'active', 'running') == (state, active_str1, active_str2):
                        self.logger.info('On host %s,Service %s states are %s, %s, %s ..OK'
                                         % (host, service, state, active_str1, active_str2))
                    else:
                        result = result & 0
                        self.logger.error('On host %s,Service %s states are %s, %s, %s ..NOT OK!'
                                          % (host, service, state, active_str1, active_str2))
            if host == self.node.webuiIP:
                for service in webui_services:
                    (state, active_str1, active_str2) = self.node.get_service_status(host,
                                                                                     service, self.username, self.password)
                    if ('enabled', 'active', 'running') == (state, active_str1, active_str2):
                        self.logger.info('On host %s,Service %s states are %s, %s, %s ..OK'
                                         % (host, service, state, active_str1, active_str2))
                    else:
                        result = result & 0
                        self.logger.error('On host %s,Service %s states are %s, %s, %s ..NOT OK!'
                                          % (host, service, state, active_str1, active_str2))

        if result:
            self.logPass('All processes are running fine on all nodes')
        else:
            self.logFail('One or more process-states are not correct on nodes')
        return result
    # end test_process_state

    def test_create_delete_vn(self, vn_name, vn_subnet):
        result = 1
        self.logger.info('Starting test to create a Virtual Network ' +
                         vn_name + ' with subnet ' + vn_subnet)
        vn = self.node.create_vn(vn_name, vn_subnet)
        if vn is None:  # Incase of any exception
            return 0
        vn_name = vn['network']['name']
        vnUUID = vn['network']['id']
        if self.node.is_vn_in_quantum(vn) == 1:
            self.logger.info('VN ' + vn_name + ' with UUID ' +
                             vnUUID + ' is found in the Networks list..OK')
        else:
            self.logger.error('VN' + vn_name + ' with UUID ' +
                              vnUUID + ' is not found in the Networks List..Not OK')
            result = result & 0

        self.sleep(10)
        # Check for delete of the VN also
        if not self.node.delete_vn(vn_name):
            result = result & 0
            self.sleep(20)
        vn_in_quantum = self.node.is_vn_in_quantum(vn)
        if (vn_in_quantum == 0 or self.node.is_vn_in_bgp(vn_name) or self.node.is_vn_in_agent(vn_name)):
            self.logger.info('VN ' + vn_name + ' with UUID ' +
                             vnUUID + ' is deleted from the Networks list..OK')
        else:
            self.logger.error('VN' + vn_name + ' with UUID ' + vnUUID +
                              ' is still found in the Networks List..Not OK')
            result = result & 0
        if result:
            self.logPass('VN ' + vn_name + ' with Subnet ' +
                         vn_subnet + '  is created and deleted fine.OK')
        else:
            self.logFail('VN ' + vn_name + ' with Subnet ' +
                         vn_subnet + ' creation/deletion had problems!')

        return result
    # end test_create_delete_vn

    def test_create_delete_vm(self, vn_name, vn_subnet, count):
        result = 1
        vn = self.node.create_vn(vn_name, vn_subnet)
        self.sleep(10)
        if vn is None:
            return 0
        for i in range(0, count):
            vmName = self.node.get_compute_host().next() + '-vm' + repr(i)
            self.logger.info('')
            self.logger.info('Starting Test to create VM ' +
                             vmName + ' in VN ' + vn_name + ', Subnet ' + vn_subnet)
            vm = self.node.create_vm(vmName, vn_name)
#            self.sleep(60)
            self.node.wait_till_vm_up(vm)
            self.node.get_vm_detail(vm)
            if vm.status == 'ACTIVE':
                self.logger.info(
                    'VM ' + vmName + ' is correctly in ACTIVE state')
            else:
                self.logger.error(
                    'VM ' + vmName + ' is not in ACTIVE state. Current state : ' + vm.status)
                result = result & 0
#            import pdb; pdb.set_trace()
            console_output = vm.get_console_output()

            if result:
                vmIP = vm.addresses[vn_name][0]['addr']
                if ('Lease of ' + vmIP + ' obtained' in console_output):
                    self.logger.info('VM did get a DHCP IP of ' + vmIP)
                elif ('Sending discover' in console_output):
                    self.logger.error('VM did not seem to have got an IP')
                    result = result & 0
                else:
                    self.logger.error(
                        'Unable to figure out whether VM got an IP or not')
                    self.logger.debug(
                        'Console output for VM ' + vmName + ': ' + console_output)

            self.logger.info('Continuing to delete the VMs')
            vm.delete()
            self.sleep(30)
            if self.node.is_server_present(vmName=vmName):
                self.logger.error(
                    'VM ' + vmName + ' still seems to be present even after deleting!')
                self.logger.error('Current VM list' +
                                  str(self.node._nc.servers.list()))
                result = result & 0
            else:
                self.logger.info(
                    'Vm ' + vmName + ' is removed from nova list after deleting..OK')
        # end for

        # Check for delete of the VN also
        if not self.node.delete_vn(vn_name):
            result = result & 0
        self.sleep(10)
        vn_in_quantum = self.node.is_vn_in_quantum(vn)
        if (vn_in_quantum == 0 or self.node.is_vn_in_bgp(vn_name) or self.node.is_vn_in_agent(vn_name)):
            self.logger.info('VN ' + vn_name +
                             ' is deleted from the Networks list..OK')
        else:
            self.logger.error('VN' + vn_name +
                              '  is still found in the Networks List..Not OK')
            result = result & 0

        return result
    # end test_create_delete_vms

    def test_ping_between_vms(self, vn_name, vn_subnet, min_size=56, max_size=57, size_step=1):
        result = 1
        vnName = vn_name
        vnSubnet = vn_subnet
        vn = self.node.create_vn(vnName, vnSubnet)
        if vn is None:
            return 0
        self.sleep(10)
        vmList = []
        for i in range(0, 2):
            vmName = self.node.get_compute_host().next() + '-vm' + repr(i)
            self.logger.info('')
            self.logger.info('Starting to create VM ' + vmName +
                             ' in VN ' + vnName + ', Subnet ' + vnSubnet)
            vm = self.node.create_vm(vmName, vnName)
            vmList.append(vm)
#            self.sleep(120)
            self.node.wait_till_vm_up(vm)
#            self.node.get_vm_detail(vm)
            if vm.status == 'ACTIVE':
                self.logger.info(
                    'VM ' + vmName + ' is correctly in ACTIVE state')
            else:
                self.logger.error(
                    'VM ' + vmName + ' is not in ACTIVE state. Current state : ' + vm.status)
                result = result & 0
            if result:
                console_output = vm.get_console_output()
                if len(vm.addresses[vnName]) > 0:
                    vmIP = vm.addresses[vnName][0]['addr']
                    if ('Lease of ' + vmIP + ' obtained' in console_output):
                        self.logger.info('VM did get a DHCP IP of ' + vmIP)
                    elif ('Sending discover' in console_output):
                        self.logger.error('VM did not seem to have got an IP')
                        result = result & 0
                    else:
                        self.logger.error(
                            'Unable to figure out whether VM got an IP or not')
                        self.logger.debug(
                            'Console output for VM ' + vmName + ': ' + console_output)
                else:
                    self.logger.error(
                        'VM did not seem to have got an IP at all')
                    result = result & 0
        # end for
        vm0 = vmList[0]
        vm1 = vmList[1]

        if result:
            for size in range(min_size, max_size, size_step):
                if self.node.ping_to_ip(vm0, vm1.addresses[vnName][0]['addr'], size=size, username=self.username, password=self.password):
                    self.logger.info('Ping test between VMs passed')
                else:
                    self.logger.error('Ping Test between VMs failed')
                    result = result & 0

        self.logger.info('Continuing to delete the VMs')
        vm0.delete()
        vm1.delete()
        self.sleep(50)
        for vm in vmList:
#            vmName=self.hostname+ '-'+ vmList[i].name
            vmName = vm.name
            if self.node.is_server_present(vmName=vmName):
                self.logger.error(
                    'VM ' + vmName + ' still seems to be present even after deleting!')
                self.logger.error('Current VM list' +
                                  str(self.node._nc.servers.list()))
                result = result & 0
            else:
                self.logger.info(
                    'Vm ' + vmName + ' is removed from nova list after deleting..OK')
        # end for
        if not self.node.delete_vn(vnName):
            result = result & 0

        return result
    # end test_ping_between_vms

    def test_floating_ip(self):
        result = 1
        fVNName = 'net22'
        fSubnet = '22.1.1.0/24'
        fVMName = self.node.get_compute_host().next() + '-net22Inst1'
        vnName = 'net19a'
        vnSubnet = '19.1.1.0/24'
        fip_pool_name = 'pub-fip-pool'

        vmName = self.node.get_compute_host().next() + '-net18Inst1'
        self.logger.info('Creating a VM in VN ' + vnName +
                         ' and another VM in floating-IP-VN ' + fVNName)
        if self.node.create_vn(fVNName, fSubnet) is None:
            return 0
        if self.node.create_vn(vnName, vnSubnet) is None:
            return 0
        vm = self.node.create_vm(vmName, vnName)
        fvm = self.node.create_vm(fVMName, fVNName)
        fVNid = self.node.get_vn_id(fVNName)
#        self.sleep(60)
        self.node.wait_till_vm_up(vm)
        self.node.wait_till_vm_up(fvm)
        self.node.get_vm_detail(fvm)
        self.node.get_vm_detail(vm)
        for tvm in [vm, fvm]:
            if tvm.status == 'ACTIVE':
                self.logger.info('VM ' + tvm.name +
                                 ' is correctly in ACTIVE state')
            else:
                self.logger.error(
                    'VM ' + tvm.name + ' is not in ACTIVE state. Current state : ' + tvm.status)
                result = result & 0

        fip_pool_obj = self.node.create_floatingip_pool(
            fip_pool_name=fip_pool_name, net_id=fVNid)
        fip_obj_list = self.node.create_floatingip(count=1)
        fip_id = fip_obj_list['floatingips'][0]['id']
        fip_resp = self.node.assoc_floatingip(fip_id, vm.id)
        if not fip_resp:
            self.logger.error(
                'Unable to associate floating IP with VM. Response : ' + str(fip_resp))
            result = result & 0
        else:
            self.logger.info('Associated Floating IP ' + fip_resp['floatingip']['floating_ip_address'] +
                             'with VM ' + vmName)

        self.sleep(10)
        if result:
            if self.node.ping_to_ip(vm, fvm.addresses[fVNName][0]['addr'], username=self.username, password=self.password):
                self.logger.info(
                    'VM is able to ping a IP in floating IP Network')
            else:
                self.logger.error(
                    'VM is not able to ping a IP in floating IP Network')
                result = result & 0

        self.node.disassoc_floatingip(fip_id)
        self.node.delete_floatingip(fip_obj_list)
        self.node.delete_floatingip_pool(fip_pool_obj.uuid)
        vm.delete()
        fvm.delete()
        # Workaround for Bug 437
        time.sleep(20)
        if not self.node.delete_vn(fVNName):
            self.logger.error(
                'Deleting vn %s failed.. Please check quantum logs ' % (fVNName))
            result = result & 0
        if not self.node.delete_vn(vnName):
            self.logger.error(
                'Deleting vn %s failed.. Please check quantum logs ' % (vnName))
            result = result & 0
        return result
    # end test_floating_ip

    def test_ping_between_vns_with_policy(self, vn1, vn2, policy_dict, rev_policy_dict):
        result = 1
        self.logger.info('Creating VNs : ' +
                         vn1['name'] + ' and ' + vn2['name'])
        source_vn = self.node.create_vn(vn1['name'], vn1['subnet'])
        if source_vn is None:
            return 0
        dest_vn = self.node.create_vn(vn2['name'], vn2['subnet'])
        if dest_vn is None:
            return 0
        self.sleep(30)

        self.logger.info('Creating and binding policies for : ' +
                         vn1['name'] + ' and ' + vn2['name'])
#        policy_dict['source_vn']=source_vn['network']['contrail:fq_name']
#        policy_dict['dest_vn']=dest_vn['network']['contrail:fq_name']
        resp = self.node.create_and_bind_policy(
            source_vn['network']['id'], policy_dict)
        if resp is None:
            return 0

#        rev_policy_dict['source_vn']=dest_vn['network']['contrail:fq_name']
#        rev_policy_dict['dest_vn']=source_vn['network']['contrail:fq_name']
        resp = self.node.create_and_bind_policy(
            dest_vn['network']['id'], rev_policy_dict)
        if resp is None:
            return 0

        self.logger.info('Creating VMs ' + vn1['vm_name'] +
                         ' and ' + vn2['vm_name'] + ' in each of the VNs')
        vm1 = self.node.create_vm(vn1['vm_name'], vn1['name'])
        vm2 = self.node.create_vm(vn2['vm_name'], vn2['name'])
#        self.sleep(150)
        self.node.wait_till_vm_up(vm1)
        self.node.wait_till_vm_up(vm2)
        self.node.get_vm_detail(vm1)
        self.node.get_vm_detail(vm2)
        for tvm in [vm1, vm2]:
            if tvm.status == 'ACTIVE':
                self.logger.info('VM ' + tvm.name +
                                 ' is correctly in ACTIVE state')
            else:
                self.logger.error(
                    'VM ' + tvm.name + ' is not in ACTIVE state. Current state : ' + tvm.status)
                result = result & 0

        if result:
            if self.node.ping_to_ip(vm1, vm2.addresses[vn2['name']][0]['addr'], username=self.username, password=self.password):
                self.logger.info(
                    'VM is able to ping a IP in a different VN using policy')
            else:
                self.logger.error(
                    'VM is not able to ping a IP in a different VN using policy')
                result = result & 0

        # Cleanup
        self.logger.info('Cleaning up VMs and VNs')
        vm1.delete()
        vm2.delete()
        self.sleep(30)
        self.node.delete_vn(vn1['name'])
        self.node.delete_vn(vn2['name'])
        self.node.delete_policy(policy_dict['name'])
        self.node.delete_policy(rev_policy_dict['name'])
        return result
    # end test_ping_between_vns_with_policy

    def test_junk(self):
        return 1
    # end

    def test_junk1(self):
        return 0
    # end

    def test_junk2(self):
        return 0
    # end

# end Test_Sanity

if __name__ == "__main__":
    x = Test_Sanity()
    x.runTest(x.test_process_state,
              test_id=1,
              description='Check all processes are running fine')
    x.runTest(x.test_create_delete_vn,
              test_id=2,
              description='Create and Delete Virtual Networks',
              vn_name='net19',
              vn_subnet='19.1.1.0/24')
    x.runTest(x.test_create_delete_vm,
              test_id=3,
              description='Create and Delete Virtual Machines',
              vn_name='net93',
              vn_subnet='39.1.1.0/24',
              count=1)
    x.runTest(x.test_ping_between_vms,
              test_id=4,
              description='Validate Ping between two Virtual Machines within a VN',
              vn_name='net22',
              vn_subnet='22.1.1.0/24')
    x.runTest(x.test_create_delete_vm,
              test_id=5,
              description='Create and Delete Multiple Virtual Machines',
              count=20,
              vn_name='net12',
              vn_subnet='12.1.1.0/24')
    x.runTest(x.test_floating_ip,
              test_id=6,
              description='Validate floating ip assignment to a VM')
    x.runTest(x.test_ping_between_vns_with_policy,
              test_id=7,
              description='Validate Ping between two VNs with policy assigned',
              vn1={'name': 'vn5', 'subnet': '19.1.1.0/24', 'vm_name':
                   x.node.get_compute_host().next() + '-vn1vm1'},
              vn2={'name': 'vn6', 'subnet': '20.1.1.0/24', 'vm_name':
                   x.node.get_compute_host().next() + '-vn2vm1'},
              policy_dict={
                  'name': 'policy4', 'source_vn': 'vn5', 'source_port': 'any', 'source_subnet': None,
                  'protocol': 'any', 'dest_vn': 'vn6', 'dest_port': 'any', 'dest_subnet': None, 'action': 'pass'},
              rev_policy_dict={
                  'name': 'rev_policy6', 'source_vn': 'vn6', 'source_port': 'any', 'source_subnet': None,
                  'protocol': 'any', 'dest_vn': 'vn5', 'dest_port': 'any', 'dest_subnet': None, 'action': 'pass'})
    x.runTest(x.test_process_state,
              test_id=8,
              description='Check all processes are running fine')
    x.runTest(x.test_ping_between_vms,
              test_id=9,
              description='Validate Ping between two Virtual Machines within a VN',
              min_size=64,
              max_size=1500,
              size_step=10)
    x.endTests()
