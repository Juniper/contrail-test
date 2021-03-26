from __future__ import absolute_import
from tcutils.wrappers import preposttest_wrapper
import os
import time
import test
from vn_test import *
from vm_test import *
from tcutils.util import *
from vcenter import *
from common.contrail_test_init import *
from common.base import *
from common.device_connection import NetconfConnection
from jnpr.junos.utils.start_shell import StartShell
from jnpr.junos import Device
from tcutils.util import retry


class TestNHLimit(GenericTestBase):
    vn_fixtures = []
    vm_fixtures = []

    @retry(delay=10, tries=40)
    def verify_nh_indexes(self, compute, Range):
        '''
        Description: Number of nexthop indexes are verified on vrouter agent side
        '''
        cmd = "contrail-tools nh --list | grep Id | wc -l"
        nh_indexes = run_cmd_on_server(
            cmd, compute, username='root', password='c0ntrail123')
        if Range[0] <= int(nh_indexes) <= Range[1]:
            self.logger.debug("nh_indexes are populated and in range")
        else:
            assert False, "nh_indexes are not in range"

    def set_nh_limit(self, nh_limit, compute, agent_mode=None, mpls_limit=None, modify=False):
        '''
        Description: Next Hop limit and mpls limit is set on vrouter agent side on specified compute node based on the values of nhlimit and mpls limit passed as arguements.
        ''' 
        if modify == True:
            if agent_mode == 'dpdk':
                if mpls_limit is not None:
                    nh_mpls_limit_cmd = '''sed -i '/# base command/ a DPDK_COMMAND_ADDITIONAL_ARGS="--vr_nexthops= --vr_mpls_labels="' entrypoint.sh'''
                    updated_cmd = nh_mpls_limit_cmd[:71] + nh_limit + \
                        nh_mpls_limit_cmd[71:89] + \
                        mpls_limit + nh_mpls_limit_cmd[89:]
                else:
                    nh_limit_cmd = '''sed -i '/# base command/ a DPDK_COMMAND_ADDITIONAL_ARGS="--vr_nexthops="' entrypoint.sh'''
                    updated_cmd = nh_limit_cmd[:71] + \
                        nh_limit + nh_limit_cmd[71:]
                cmds = ['docker cp vrouter_vrouter-agent-dpdk_1:/entrypoint.sh .',
                        'cp entrypoint.sh entrypoint_backup.sh', updated_cmd]
                for cmd in cmds:
                    run_cmd_on_server(
                        cmd, compute, username='root', password='c0ntrail123')

            else:
                if mpls_limit is not None:
                    nh_mpls_limit_cmd = '''sed -i '/VROUTER_GATEWAY/ a VROUTER_MODULE_OPTIONS="vr_nexthops= vr_mpls_labels="' /etc/contrail/common_vrouter.env'''
                    updated_cmd = nh_mpls_limit_cmd[:64] + nh_limit + \
                        nh_mpls_limit_cmd[64:80] + \
                        mpls_limit + nh_mpls_limit_cmd[80:]
                else:
                    nh_limit_cmd = '''sed -i '/VROUTER_GATEWAY/ a VROUTER_MODULE_OPTIONS="vr_nexthops="' /etc/contrail/common_vrouter.env'''
                    updated_cmd = nh_limit_cmd[:64] + \
                        nh_limit + nh_limit_cmd[64:]
                agent_file_backup_cmd = "cp /etc/contrail/common_vrouter.env /etc/contrail/common_vrouter_backup.env"
                cmds = [agent_file_backup_cmd, updated_cmd]
                for cmd in cmds:
                    run_cmd_on_server(
                        cmd, compute, username='root', password='c0ntrail123')

        if agent_mode == 'dpdk':
            cmds = ['docker cp entrypoint.sh vrouter_vrouter-agent-dpdk_1:/entrypoint.sh',
                    'docker stop vrouter_vrouter-agent-dpdk_1', 'docker start vrouter_vrouter-agent-dpdk_1']
        else:
            cmds = ['docker stop vrouter_vrouter-agent_1', 'ifdown vhost0',
                    'cd /etc/contrail/vrouter/; docker-compose down; docker-compose up -d']
        for cmd in cmds:
            run_cmd_on_server(cmd, compute, username='root',
                              password='c0ntrail123')
        self.verify_nh_limit(compute, nh_limit, mpls_limit)

    @retry(delay=3, tries=7)
    def verify_nh_limit(self, compute, nh_limit, mpls_limit=None):
        '''
        Description: Nh limit set on vrouter agent side is checked and verified comparing with nhlimit value passed as argument. This is called whenever new nh_limit is set.
        '''
        verify_nh_limit_cmd = "contrail-tools vrouter --info | awk '{print $3}' | awk 'NR==6'"
        nh_limit_set = run_cmd_on_server(
            verify_nh_limit_cmd, compute, username='root', password='c0ntrail123')
        if nh_limit_set == nh_limit:
            self.logger.debug(
                'Desired nh_limit %s is set on agent side' % nh_limit_set)
        else:
            assert False, "Proper nh_limit is not set"
            self.logger.debug('nhlimit set is %s' % nh_limit_set)
        if mpls_limit is not None:
            verify_mpls_limit_cmd = "contrail-tools vrouter --info | awk '{print $4}' | awk 'NR==7'"
            mpls_limit_set = run_cmd_on_server(
                verify_mpls_limit_cmd, compute, username='root', password='c0ntrail123')
            if mpls_limit_set == mpls_limit:
                self.logger.debug(
                    'Desired mpls_limit %s is set on agent side' % mpls_limit_set)
            else:
                assert False, "Proper mpls_limit is not set"
                self.logger.debug('mplslimit set is %s' % mpls_limit_set)

    def reset_nh_limit(self, compute, agent_mode=None):
        '''
        Description: Default nh limit and mpls limit are set on agent side.
        '''
        nh_limit = '524288'
        mpls_limit = '5120'
        if agent_mode == 'dpdk':
            cmds = ['mv -f entrypoint_backup.sh entrypoint.sh']
        else:
            cmds = [
                'mv -f /etc/contrail/common_vrouter_backup.env /etc/contrail/common_vrouter.env']
        for cmd in cmds:
            run_cmd_on_server(cmd, compute, username='root',
                              password='c0ntrail123')
        self.set_nh_limit(nh_limit=nh_limit, compute=compute,
                          agent_mode=agent_mode, mpls_limit=mpls_limit)
        self.logger.debug("nh_limit has been reset")

    def add_routes_using_rtgen_mx_side(self, logicalsystem, table, subnet, count):
        '''
        Description: Routes are pumped on mx side referring to logical system and routing table, using rtgen tool.
                     Count takes integer value of number of routes.
        '''
        rtgen_cmd = 'rtgen --op add --logical-system --table --prefix --count --next-hop-type reject'
        index_words = ['--logical-system', '--table', '--prefix', '--count']
        substring_list = []
        for i in range(len(index_words)):
            substring_list.append(rtgen_cmd.find(
                index_words[i]) + len(index_words[i]))
        updated_rtgen_cmd = rtgen_cmd[:substring_list[0] + 1] + logicalsystem + rtgen_cmd[substring_list[0]:substring_list[1] + 1] + table + \
            rtgen_cmd[substring_list[1]:substring_list[2] + 1] + subnet + \
            rtgen_cmd[substring_list[2]:substring_list[3] + 1] + \
            count + rtgen_cmd[substring_list[3]:]
        mx_params = list(self.inputs.physical_routers_data.values())[0]
        dev = Device(
            host=mx_params['mgmt_ip'], user=mx_params['ssh_username'], password=mx_params['ssh_password'])
        ss = StartShell(dev)
        ss.open()
        updated_rtgen_cmd_result = ss.run(updated_rtgen_cmd)
        self.logger.debug('routes are added')
        ss.close()

    def remove_routes_mx_side(self, logicalsystem):
        '''
        Description: Route entries from routing table are removed by deactivating the logical system and is activated back.
        '''
        deactivate_cmd = 'deactivate logical-systems ' + logicalsystem
        activate_cmd = 'activate logical-systems ' + logicalsystem
        cmds = [[deactivate_cmd], [activate_cmd]]
        mx_params = list(self.inputs.physical_routers_data.values())[0]
        nhLS_netconf = NetconfConnection(mx_params['mgmt_ip'])
        nhLS_netconf.connect()
        for i in range(len(cmds)):
            nhLS_netconf.config(stmts=cmds[i], timeout=120)
        nhLS_netconf.disconnect()

    def create_vmvn_for_nhlimittest(self, compute, vn_count):
        for i in range(vn_count):
            vn_fixture = self.create_vn()
            for i in range(0,5):
                while True:
                    try:    
                        assert vn_fixture.verify_on_setup()
                    except AttributeError:
                        self.logger.debug("agent introspect might be down only at this moment")
                        continue
                    break
            self.vn_fixtures.append(vn_fixture)
            vm_fixture = self.create_vm(
                vn_fixture=vn_fixture, node_name=compute)
            assert vm_fixture.wait_till_vm_is_up()
            assert vm_fixture.verify_on_setup()
            self.vm_fixtures.append(vm_fixture)
        for i in range(len(self.vn_fixtures)):
            for j in range(0,10):
                while True:
                    try:
                        self.vn_fixtures[i].add_route_target(router_asn=64512, route_target_number=190)
                    except vnc_api.exceptions.NoIdError:
                        continue
                    break
        vn1_name = self.vn_fixtures[0].vn_fq_name
        vn2_name = self.vn_fixtures[1].vn_fq_name
        rule1 = self._get_network_policy_rule(
            src_vn=vn1_name, dst_vn=vn2_name, action='pass')
        rule2 = self._get_network_policy_rule(
            src_vn=vn2_name, dst_vn=vn1_name, action='pass')
        vn12_pol = self.create_policy(rules=[rule1, rule2])
        self.apply_policy(vn12_pol, [self.vn_fixtures[0], self.vn_fixtures[1]])

    def get_compute(self, agent_mode=None):
        dpdk_computes = []
        kernel_computes = []
        for host in self.inputs.compute_ips:
            if self.inputs.host_data[host]['roles'].get('vrouter').get('AGENT_MODE') == 'dpdk':
                dpdk_computes.append(self.inputs.host_data[host]['name'])
            else:
                kernel_computes.append(self.inputs.host_data[host]['name'])
        if agent_mode == 'dpdk':
            return dpdk_computes[0]
        else:
            return kernel_computes[0]

    def get_prefix_count(self, nh_limit, vn_count):
        return str(int(int(nh_limit)/vn_count))

    def ping_after_nh_index(self):
        assert self.vm_fixtures[0].ping_with_certainty(
            self.vm_fixtures[1].vm_ip)
