# Need to import path to test/fixtures and test/scripts/
# Ex : export PYTHONPATH='$PATH:/root/test/fixtures/:/root/test/scripts/'
#
# To run tests, you can do 'python -m testtools.run tests'. To run specific tests,
# You can do 'python -m testtools.run -l tests'
# Set the env variable PARAMS_FILE to point to your ini file. Else it will try to pick params.ini in PWD
#
import time
import re
import socket
import unittest
import fixtures
import testtools
from common.contrail_test_init import ContrailTestInit
from vn_test import *
from vm_test import *
from common.connections import ContrailConnections
from multiple_vn_vm_test import *
from tcutils.wrappers import preposttest_wrapper
from common.servicechain.config import ConfigSvcChain
from common.servicechain.verify import VerifySvcChain
import threading
from subprocess import Popen, PIPE
import shlex
from netaddr import *


class AnalyticsTestPerformance(testtools.TestCase, ConfigSvcChain, VerifySvcChain):

    def setUp(self):
        super(AnalyticsTestPerformance, self).setUp()
        if 'PARAMS_FILE' in os.environ:
            self.ini_file = os.environ.get('PARAMS_FILE')
        else:
            self.ini_file = 'params.ini'
        self.inputs = self.useFixture(ContrailTestInit(self.ini_file))
        self.connections = ContrailConnections(self.inputs)
        self.quantum_h = self.connections.quantum_h
        self.nova_h = self.connections.nova_h
        self.vnc_lib = self.connections.vnc_lib
        self.logger = self.inputs.logger
        self.agent_inspect = self.connections.agent_inspect
        self.cn_inspect = self.connections.cn_inspect
        self.analytics_obj = self.connections.analytics_obj
        self.sender_list = []
        self.receiver_list = []

    def cleanUp(self):
        super(AnalyticsTestPerformance, self).cleanUp()

    def runTest(self):
        pass

    def provision_static_route(
        self, prefix='111.1.0.0/16', virtual_machine_id='',
        tenant_name=None, api_server_ip='127.0.0.1',
        api_server_port='8082', oper='add',
        virtual_machine_interface_ip='11.1.1.252', route_table_name='my_route_table',
            user='admin', password='contrail123'):

        if not tenant_name:
            tenant_name = self.inputs.stack_tenant
        cmd = "python /usr/share/contrail-utils/provision_static_route.py --prefix %s \
                --virtual_machine_id %s \
                --tenant_name %s  \
                --api_server_ip %s \
                --api_server_port %s\
                --oper %s \
                --virtual_machine_interface_ip %s \
                --user %s\
                --password %s\
                --route_table_name %s" % (prefix, virtual_machine_id, tenant_name, api_server_ip, api_server_port, oper,
                                          virtual_machine_interface_ip, user, password, route_table_name)
        args = shlex.split(cmd)
        process = Popen(args, stdout=PIPE)
        stdout, stderr = process.communicate()
        if stderr:
            self.logger.warn("Route could not be created , err : \n %s" %
                             (stderr))
        else:
            self.logger.info("%s" % (stdout))

    def start_traffic(self, vm, src_min_ip='', src_mx_ip='', dest_ip='', dest_min_port='', dest_max_port=''):

        self.logger.info("Sending traffic...")
        try:
            cmd = '~/pktgen_new.sh %s %s %s %s %s' % (src_min_ip,
                                                      src_mx_ip, dest_ip, dest_min_port, dest_max_port)
            vm.run_cmd_on_vm(cmds=[cmd])
        except Exception as e:
            self.logger.exception("Got exception at start_traffic as %s" % (e))

    def stop_traffic(self, vm):
        self.logger.info("Stopping traffic...")
        try:
            cmd = 'killall ~/pktgen_new.sh'
            vm.run_cmd_on_vm([cmd])
        except Exception as e:
            self.logger.exception("Got exception at stop_traffic as %s" % (e))

    def create_vms(self, vn_name=get_random_name('vn_analytics'), vm_name=get_random_name('vm-analytics'), vn_count=1, vm_count=1, flavor='contrail_flavor_small'):

        vm1_name = vm_name
        vn_name = vn_name
        vn_subnets = ['11.1.1.0/24']
        try:
            self.setup_fixture = self.useFixture(
                create_multiple_vn_and_multiple_vm_fixture(
                    connections=self.connections,
                    vn_name=vn_name, vm_name=vm1_name, inputs=self.inputs, project_name=self.inputs.project_name,
                    subnets=vn_subnets, vn_count=vn_count, vm_count=vm_count, subnet_count=1, image_name='ubuntu-traffic',
                    flavor='contrail_flavor_small'))
            time.sleep(20)
        except Exception as e:
            self.logger.exception("Got exception as %s" % (e))

        try:
            assert self.setup_fixture.verify_vms_on_setup()
            assert self.setup_fixture.verify_vns_on_setup()
        except Exception as e:
            self.logger.exception(
                "Got exception  in create_vms function as %s" % (e))

    def build_query(self, src_vn, dst_vn):

        self.query = '(' + 'sourcevn=' + src_vn + \
            ') AND (destvn=' + dst_vn + ')'

    def run_query(self):
        for ip in self.inputs.collector_ips:
            try:
                self.logger.info('setup_time= %s' % (self.start_time))
                # Quering flow sreies table
                self.logger.info(
                    "Verifying flowSeriesTable through opserver %s" % (ip))
                res1 = self.analytics_obj.ops_inspect[ip].post_query(
                    'FlowSeriesTable', start_time=self.start_time, end_time='now', select_fields=['sourcevn', 'sourceip', 'destvn', 'destip', 'sum(packets)', 'sport', 'dport', 'T=1'],
                    where_clause=self.query, sort=2, limit=5, sort_fields=['sum(packets)'])
                self.logger.info("result: %s" % (res1))
                assert res1
                self.logger.info("Top 5 flows %s" % (res1))
            except Exception as e:
                self.logger.exception("Got exception as %s" % (e))

    def get_ip_list_from_prefix(self, prefix):

        ip_list = []
        ip = IPNetwork(prefix)
        ip_netowrk = str(ip.network)
        ip_broadcast = str(ip.broadcast)
        ip_lst = list(ip)
        for ip_addr in ip_lst:
            if ((str(ip_addr) in ip_netowrk) or (str(ip_addr) in ip_broadcast)):
                continue
            ip_list.append(str(ip_addr))
        return ip_list

    def get_min_max_ip_from_prefix(self, prefix):

        ip_list = self.get_ip_list_from_prefix(prefix)
        min_ip = ip_list[0]
        max_ip = ip_list[-1]
        return [min_ip, max_ip]

    def create_svc_chains(self, st_name, si_prefix, max_inst,
                          left_vn_fixture=None, right_vn_fixture=None,
                          svc_mode='in-network'):

        self.action_list = []
        self.if_list = [['management', False], ['left', True], ['right', True]]

        svc_chain_info = self.config_svc_chain(
            left_vn_fixture=left_vn_fixture,
            right_vn_fixture=right_vn_fixture,
            service_mode=svc_mode,
            st_name=st_name,
            max_inst=max_inst)
        self.st_fixture = svc_chain_info['st_fixture']
        self.si_fixture = svc_chain_info['si_fixture']

    def create_policy(self, policy_name='policy_in_network', rules=[], src_vn_fixture=None, dest_vn_fixture=None):

        self.policy_fixture = self.config_policy(policy_name, rules)
        self.vn1_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture, src_vn_fixture)
        self.vn2_policy_fix = self.attach_policy_to_vn(
            self.policy_fixture, dest_vn_fixture)
        self.validate_vn(src_vn_fixture.vn_name)
        self.validate_vn(dest_vn_fixture.vn_name)

    def setup_vm(self, vn_count=2, vm_count=1):

        self.create_vms(vn_count=vn_count, vm_count=vm_count)

    def setup_service_instance(
        self, st_name='in_net_svc_template_1', si_prefix='in_net_svc_instance_',
            si_count=1, svc_scaling=False, max_inst=1, left_vn_fixture=None,
            right_vn_fixture=None, svc_mode='in-network'):

        self.create_svc_chains(
            st_name, si_prefix, max_inst,
            left_vn_fixture=left_vn_fixture,
            right_vn_fixture=right_vn_fixture, svc_mode=svc_mode)

    def setup_policy(self, policy_name='policy_in_network', policy_rules=[], src_vn_fixture=None, dest_vn_fixture=None):

        self.create_policy(
            policy_name=policy_name, rules=policy_rules, src_vn_fixture=src_vn_fixture,
            dest_vn_fixture=dest_vn_fixture)

    def restart_service(self, ip_list, service, command='restart'):

        for ip in ip_list:
            cmd = 'service %s %s' % (service, command)
            self.inputs.run_cmd_on_server(
                ip, cmd, username='root', password='c0ntrail123')

    def reboot_node(self, ip_list):

        for ip in ip_list:
            self.inputs.run_cmd_on_server(
                ip, 'reboot', username='root', password='c0ntrail123')

    def reboot_vm(self, vm, cmd):

        vm.run_cmd_on_vm([cmd])

    def triggers(self, preference='', ip=[], command='', service='', vm=None):
        '''
        preference : agent restart - to restart vrouter service
                     control restart
                     collector restart
                     agent stop
                     control stop
                     collector stop
                     agent start
                     control start
                     collector start
                     agent reboot
                     control reboot
                     collector reboot
                     vm reboot
        '''

        if not preference:
            if (ip and service):
                self.restart_service(ip, service)
            if vm:
                self.reboot_vm(vm)
            if ip:
                self.reboot_node(ip)
            return
        if (preference in 'agent restart') or (preference in 'control restart') or (preference in 'collector restart'):
            if (ip and service):
                self.restart_service(ip, service)
        if (preference in 'agent stop') or (preference in 'control stop') or (preference in 'collector stop'):
            if (ip and service):
                self.restart_service(ip, service)
        if (preference in 'agent start') or (preference in 'control start') or (preference in 'collector start'):
            if (ip and service):
                self.restart_service(ip, service)
        if (preference in 'agent reboot') or (preference in 'control reboot') or (preference in 'collector reboot'):
            if ip:
                self.reboot_node(ip)
        if (preference in 'vm reboot'):
            if vm:
                self.reboot_vm(vm, command)

    def verifications(self, verify='uve'):

        if 'uve' in verify:
            assert self.analytics_obj.verify_all_uves()
        if 'tables' in verify:
            start_time = self.analytics_obj.get_time_since_uptime(
                self.inputs.cfgm_ip)
            assert self.analytics_obj.verify_object_tables(
                start_time=start_time, skip_tables=[
                    'FlowSeriesTable', 'FlowRecordTable',
                    'ObjectQueryQid',
                    'ServiceChain', 'ObjectSITable', 'ObjectModuleInfo',
                    'StatTable.QueryPerfInfo.query_stats', 'StatTable.UveVirtualNetworkAgent.vn_stats',
                    'StatTable.AnalyticsCpuState.cpu_info'])
        if 'setup' in verify:
            assert self.setup_fixture.verify_vms_on_setup()
            assert self.setup_fixture.verify_vns_on_setup()

    @preposttest_wrapper
    def test_verify_analytics_scale(self):
        ''' Test to validate scale

        '''
        self.setup_vm()  # Creating vns/vm
        # Creating service instance
        left_vn_fix = self.setup_fixture.vn_obj_dict.values()[0]
        right_vn_fix = self.setup_fixture.vn_obj_dict.values()[1]
        left_vn_fq_name = self.setup_fixture.vn_obj_dict.values()[0].vn_fq_name
        right_vn_fq_name = self.setup_fixture.vn_obj_dict.values()[
            1].vn_fq_name
        self.setup_service_instance(
            left_vn_fixture=left_vn_fix, right_vn_fixture=right_vn_fix)

        # Sending traffic
        prefix = '111.1.0.0/16'
        vm_uuid = self.setup_fixture.vm_valuelist[0].vm_obj.id
        vm_ip = self.setup_fixture.vm_valuelist[0].vm_ip
        self.provision_static_route(
            prefix=prefix, virtual_machine_id=vm_uuid,
            virtual_machine_interface_ip=vm_ip, route_table_name='my_route_table',
            user='admin', password='contrail123')

        dest_min_port = 8000
        dest_max_port = 8005
        ips = self.get_min_max_ip_from_prefix(prefix)

        first_vm = self.setup_fixture.vm_valuelist[0]
        vm_list = self.setup_fixture.vm_valuelist[1:]
        self.tx_vm_node_ip = self.inputs.host_data[
            self.nova_h.get_nova_host_of_vm(first_vm.vm_obj)]['host_ip']
        self.start_time = self.analytics_obj.getstarttime(self.tx_vm_node_ip)
        traffic_threads = []
        for vm in vm_list:
            t = threading.Thread(
                target=self.start_traffic, args=(
                    first_vm, ips[0], ips[-1], vm.vm_ip,
                    dest_min_port, dest_max_port,))
            traffic_threads.append(t)
        for th in traffic_threads:
            time.sleep(1)
            th.start()
        time.sleep(60)
#
        # Analytics query to flow tables
        self.logger.info("start time= %s" % (self.start_time))
        self.build_query(left_vn_fix.vn_fq_name, right_vn_fix.vn_fq_name)
        self.run_query()
#        print 'Waiting...'

        # Triggers
        # restart agent with scenario up
        self.logger.info("Verifying agent restart")
        temp = self.inputs.compute_ips[:]
        self.inputs.compute_ips.remove(self.tx_vm_node_ip)
        self.triggers(preference='agent restart', ip=self.inputs.compute_ips,
                      command='restart', service='contrail-vrouter')
        time.sleep(20)
        self.verifications(verify='uve')
        self.inputs.compute_ips = temp[:]
        # switchover collector
        self.logger.info("Verifying collector start/stop")
        self.triggers(preference='collector stop', ip=[
                      self.inputs.collector_ips[0]], command='stop', service='supervisor-analytics')
        temp = self.inputs.collector_ips[:]
        self.inputs.collector_ips.remove(self.inputs.collector_ips[0])
        time.sleep(10)
        self.verifications(verify='uve')
        self.inputs.collector_ips = temp[:]
        self.triggers(preference='collector start', ip=[
                      self.inputs.collector_ips[0]], command='start', service='supervisor-analytics')
        time.sleep(10)
        # collector reboot
        self.logger.info("Verifying collector reboot")
        self.triggers(preference='collector reboot',
                      ip=[self.inputs.collector_ips[1]])
        temp = self.inputs.collector_ips[:]
        self.inputs.collector_ips.remove(self.inputs.collector_ips[1])
        time.sleep(10)
        self.verifications(verify='uve')
        self.inputs.collector_ips = temp[:]
        # reboot dest vm
        self.logger.info("Verifying vm reboot")
        for vm in vm_list:
            self.triggers(preference='vm reboot', command='reboot', vm=vm)
        time.sleep(20)
        # reboot dest compute
        self.logger.info("Verifying agent reboot")
        for vm in vm_list:
            dest_vm_node_list = []
            dest_vm_node_ip = self.inputs.host_data[
                self.nova_h.get_nova_host_of_vm(vm.vm_obj)]['host_ip']
            dest_vm_node_list.append(dest_vm_node_ip)
        self.triggers(preference='agent reboot', ip=dest_vm_node_list)
        time.sleep(20)
        # add new config-TO DO
        # modify policy rules without affecting live flows - TO DO
        # modify policy rules affecting live flows-TO DO
        # force continuous aging of flows- TO DO
        self.verifications(verify='uve')
        # Stopping traffic
        self.stop_traffic(first_vm)

        for th in traffic_threads:
            th.join()
        return True
# end AnalyticsTestPerformance


def main():
    obj = AnalyticsTestPerformance()
#    obj.get_ip_list_from_prefix('192.0.2.16/29')
    for ip in obj.get_ip_list_from_prefix('192.0.2.16/29'):
        print ip

if __name__ == "__main__":
    main()
