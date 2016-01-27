import time
import test
from netaddr import *

from common.connections import ContrailConnections
from common import isolated_creds
from common import create_public_vn
from vn_test import VNFixture
from vm_test import VMFixture
from project_test import ProjectFixture
from policy_test import PolicyFixture
from port_fixture import PortFixture
from tcutils.util import get_random_name, retry, get_random_cidr
from fabric.context_managers import settings
from fabric.api import run
from fabric.operations import get, put
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
import ConfigParser
import re

contrail_api_conf = '/etc/contrail/contrail-api.conf'


class BaseNeutronTest(test.BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super(BaseNeutronTest, cls).setUpClass()
        cls.isolated_creds = isolated_creds.IsolatedCreds(
            cls.__name__,
            cls.inputs,
            ini_file=cls.ini_file,
            logger=cls.logger)
        cls.admin_connections = cls.isolated_creds.get_admin_connections()
        cls.isolated_creds.setUp()
        cls.project = cls.isolated_creds.create_tenant()
        cls.isolated_creds.create_and_attach_user_to_tenant()
        cls.inputs = cls.isolated_creds.get_inputs()
        cls.connections = cls.isolated_creds.get_conections()
        cls.admin_inputs = cls.isolated_creds.get_admin_inputs()
        cls.admin_connections = cls.isolated_creds.get_admin_connections()
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
        cls.api_s_inspect = cls.connections.api_server_inspect
        cls.public_vn_obj = create_public_vn.PublicVn(
            cls.__name__,
            cls.__name__,
            cls.inputs,
            ini_file=cls.ini_file,
            logger=cls.logger)
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.isolated_creds.delete_tenant()
        super(BaseNeutronTest, cls).tearDownClass()
    # end tearDownClass

    def create_vn(self, vn_name=None, vn_subnets=None, vxlan_id=None,
        enable_dhcp=True, cleanup=True):
        if not vn_name:
            vn_name = get_random_name('vn')
        if not vn_subnets:
            vn_subnets = [get_random_cidr()]
        vn_fixture = VNFixture(project_name=self.inputs.project_name,
                      connections=self.connections,
                      inputs=self.inputs,
                      vn_name=vn_name,
                      subnets=vn_subnets,
                      vxlan_id=vxlan_id,
                      enable_dhcp=enable_dhcp)
        vn_fixture.setUp()
        if cleanup:
            self.addCleanup(vn_fixture.cleanUp)

        return vn_fixture
    # end create_vn

    def create_vm(self, vn_fixture, vm_name=None, node_name=None,
                  flavor='contrail_flavor_small',
                  image_name='ubuntu-traffic',
                  port_ids=[]):
        if not vm_name:
            vm_name = 'vm-%s' % (get_random_name(vn_fixture.vn_name))
        return self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_obj=vn_fixture.obj,
                vm_name=vm_name,
                image_name=image_name,
                flavor=flavor,
                node_name=node_name,
                port_ids=port_ids))

    def create_router(self, router_name, tenant_id=None):
        obj = self.quantum_h.create_router(router_name, tenant_id)
        if obj:
            self.addCleanup(self.quantum_h.delete_router, obj['id'])
        return obj

    def delete_router(self, router_id=None):
        val = self.quantum_h.delete_router(router_id)

    def create_port(self, net_id, fixed_ips=[],
                    mac_address=None, no_security_group=False,
                    security_groups=[], extra_dhcp_opts=None):
        port_rsp = self.quantum_h.create_port(
            net_id,
            fixed_ips,
            mac_address,
            no_security_group,
            security_groups,
            extra_dhcp_opts)
        self.addCleanup(self.delete_port, port_rsp['id'], quiet=True)
        return port_rsp

    def delete_port(self, port_id, quiet=False):
        self._remove_from_cleanup(self.quantum_h.delete_port, (port_id))
        if quiet and not self.quantum_h.get_port(port_id):
            return
        self.quantum_h.delete_port(port_id)

    def update_port(self, port_id, port_dict):
        if not self.quantum_h.get_port(port_id):
            self.logger.error('Port with port_id %s not found' % port_id)
            return
        else:
            port_rsp = self.quantum_h.update_port(port_id, port_dict)
        return port_rsp

    def add_router_interface(self, router_id, subnet_id=None, port_id=None,
                             cleanup=True):
        if subnet_id:
            result = self.quantum_h.add_router_interface(
                router_id, subnet_id)
        elif port_id:
            result = self.quantum_h.add_router_interface(router_id,
                                                         port_id=port_id)

        if cleanup:
            self.addCleanup(self.delete_router_interface,
                            router_id, subnet_id, port_id)
        return result

    def delete_router_interface(self, router_id, subnet_id=None, port_id=None):
        self._remove_from_cleanup(self.delete_router_interface,
                                  (router_id, subnet_id, port_id))
        self.quantum_h.delete_router_interface(
            router_id, subnet_id, port_id)

    def add_vn_to_router(self, router_id, vn_fixture, cleanup=True):
        return self.add_router_interface(
            router_id,
            subnet_id=vn_fixture.vn_subnet_objs[0]['id'], cleanup=cleanup)

    def delete_vn_from_router(self, router_id, vn_fixture):
        return self.delete_router_interface(
            router_id,
            vn_fixture.vn_subnet_objs[0]['id'])

    def create_security_group(self, name, quantum_handle=None):
        q_h = None
        if quantum_handle:
            q_h = quantum_handle
        else:
            q_h = self.quantum_h
        obj = q_h.create_security_group(name)
        if obj:
            self.addCleanup(self.delete_security_group, obj['id'])
        return obj
    # end create_security_group

    def delete_security_group(self, sg_id, quantum_handle=None):
        q_h = None
        if quantum_handle:
            q_h = quantum_handle
        else:
            q_h = self.quantum_h
        q_h.delete_security_group(sg_id)

    def update_default_quota_list(
            self,
            subnet=-1,
            virtual_network=-1,
            floating_ip=-1,
            logical_router=-1,
            security_group_rule=-1,
            virtual_machine_interface=-1,
            security_group=-1):
        contrail_api_file_list = []

        # Copy the contrail-api.conf to /tmp/ and restore it later

        for cfgm_ip in self.inputs.cfgm_ips:
            api_file_name = get_random_name('contrail-api')
            contrail_api_file_list.append(api_file_name)
            issue_cmd = "cp " + contrail_api_conf + " /tmp/" + \
                api_file_name
            output = self.inputs.run_cmd_on_server(
                cfgm_ip,
                issue_cmd,
                self.inputs.host_data[cfgm_ip]['username'],
                self.inputs.host_data[cfgm_ip]['password'])

        self.addCleanup(
            self.restore_default_quota_list,
            contrail_api_file_list)

        # Fetch the contrail-api.conf from all config nodes to active cfgm's
        # /tmp/

        api_file_list = []
        api_file_list.append(contrail_api_conf)
        for cfgm_ip in self.inputs.cfgm_ips[1:]:
            with settings(
                    host_string='%s@%s' % (
                        self.inputs.host_data[cfgm_ip]['username'], cfgm_ip)):
                api_conf_file = get_random_name('contrail-api-remote')
                api_file_list.append('/tmp/' + api_conf_file)
                get(contrail_api_conf, '/tmp/' + api_conf_file)

        # Edit the contrail-api.conf files adding quota sections

        for api_conf in api_file_list:
            api_conf_h = open(api_conf, 'a')
            config = ConfigParser.ConfigParser()
            config.add_section('QUOTA')
            config.set('QUOTA', 'subnet', subnet)
            config.set('QUOTA', 'virtual_network', virtual_network)
            config.set('QUOTA', 'floating_ip', floating_ip)
            config.set('QUOTA', 'logical_router', logical_router)
            config.set('QUOTA', 'security_group', security_group)
            config.set('QUOTA', 'security_group_rule', security_group_rule)
            config.set(
                'QUOTA',
                'virtual_machine_interface',
                virtual_machine_interface)
            config.write(api_conf_h)
            api_conf_h.close()

        # Put back updated contrail-api.conf file to respective cfgm's remove
        # temp files

        count = 1
        for cfgm_ip in self.inputs.cfgm_ips[1:]:
            with settings(
                    host_string='%s@%s' % (
                        self.inputs.host_data[cfgm_ip]['username'], cfgm_ip)):
                put(api_file_list[count], contrail_api_conf)
                issue_cmd = "rm -rf " + api_file_list[count]
                output = self.inputs.run_cmd_on_server(
                    cfgm_ip,
                    issue_cmd,
                    self.inputs.host_data[cfgm_ip]['username'],
                    self.inputs.host_data[cfgm_ip]['password'])
                count = count + 1

        # Restart contrail-api service on all cfgm nodes

        for cfgm_ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('contrail-api', [cfgm_ip])

        time.sleep(30)

    # end update_default_quota_list

    def restore_default_quota_list(self, file_list=[]):
        # Restore default contrail-api.conf on respective cfgm nodes remove
        # temp files

        file_itr = iter(file_list)
        for cfgm_ip in self.inputs.cfgm_ips:
            api_conf_backup = next(file_itr)
            issue_cmd = "cp /tmp/" + api_conf_backup + \
                " " + contrail_api_conf + "; rm -rf /tmp/" + api_conf_backup
            output = self.inputs.run_cmd_on_server(
                cfgm_ip,
                issue_cmd,
                self.inputs.host_data[cfgm_ip]['username'],
                self.inputs.host_data[cfgm_ip]['password'])

        for cfgm_ip in self.inputs.cfgm_ips:
            self.inputs.restart_service('contrail-api', [cfgm_ip])

        time.sleep(30)

    # end restore_default_quota_list

    def create_external_network(self, connections, inputs):
        ext_vn_name = get_random_name('ext_vn')
        ext_subnets = [self.inputs.fip_pool]
        mx_rt = self.inputs.mx_rt
        ext_vn_fixture = self.useFixture(
            VNFixture(
                project_name=inputs.project_name,
                connections=connections,
                vn_name=ext_vn_name,
                inputs=inputs,
                subnets=ext_subnets,
                router_asn=self.inputs.router_asn,
                rt_number=mx_rt,
                router_external=True))
        assert ext_vn_fixture.verify_on_setup()
        return ext_vn_fixture

    # end create_external_network

    def allow_default_sg_to_allow_all_on_project(self, project_name):

        self.project_fixture = self.useFixture(
            ProjectFixture(
                vnc_lib_h=self.vnc_lib,
                project_name=self.inputs.project_name,
                connections=self.connections))
        self.logger.info(
            'Default SG to be edited for allow all on project: %s' %
            project_name)
        self.project_fixture.set_sec_group_for_allow_all(
            project_name, 'default')

    # end allow_default_sg_to_allow_all_on_project

    def verify_snat(self, vm_fixture, expectation=True, timeout=200):
        result = True
        self.logger.info("Ping to 8.8.8.8 from vm %s" % (vm_fixture.vm_name))
        if not vm_fixture.ping_with_certainty('8.8.8.8',
                                              expectation=expectation):
            self.logger.error("Ping to 8.8.8.8 from vm %s Failed" %
                              (vm_fixture.vm_name))
            result = result and False
        self.logger.info('Testing FTP...Copying VIM files to VM via FTP')
        run_cmd = "wget http://ftp.vim.org/pub/vim/unix/vim-7.3.tar.bz2"
        vm_fixture.run_cmd_on_vm(cmds=[run_cmd], timeout=timeout)
        output = vm_fixture.return_output_values_list[0]
        if not output or 'saved' not in output:
            self.logger.error("FTP failed from VM %s" %
                              (vm_fixture.vm_name))
            result = result and False
        else:
            self.logger.info("FTP successful from VM %s via FIP" %
                             (vm_fixture.vm_name))
        return result
    # end verify_snat

    def get_active_snat_node(self, vm_fixture, vn_fixture):
        (domain, project, vn) = vn_fixture.vn_fq_name.split(':')
        inspect_h = self.agent_inspect[vm_fixture.vm_node_ip]
        agent_vrf_objs = inspect_h.get_vna_vrf_objs(domain, project, vn)
        agent_vrf_obj = vm_fixture.get_matching_vrf(
            agent_vrf_objs['vrf_list'], vn_fixture.vrf_name)
        vn_vrf_id9 = agent_vrf_obj['ucindex']
        next_hops = inspect_h.get_vna_active_route(
            vrf_id=vn_vrf_id9, ip=vm_fixture.vm_ip, prefix='32')['path_list'][0]['nh']
        if next_hops['type'] == 'interface':
            return vm_fixture.vm_node_ip
        else:
            return next_hops['itf']
    # end get_active_snat_node

    def config_aap(self, port1, port2, ip, vsrx=False):
        self.logger.info('Configuring AAP on ports %s and %s' %
                         (port1['id'], port2['id']))
#        port1_dict = {'allowed_address_pairs': [
#            {"ip_address": ip + '/32', "mac_address": port1['mac_address']}]}
#        port2_dict = {'allowed_address_pairs': [
#            {"ip_address": ip + '/32', "mac_address": port2['mac_address']}]}
        if vsrx:
            port1_dict = {'allowed_address_pairs': [
                {"ip_address": ip + '/32', "mac_address": '00:00:5e:00:01:01'}]}
            port2_dict = {'allowed_address_pairs': [
                {"ip_address": ip + '/32', "mac_address": '00:00:5e:00:01:01'}]}
        else:
            port1_dict = {'allowed_address_pairs': [
                {"ip_address": ip + '/32'}]}
            port2_dict = {'allowed_address_pairs': [
                {"ip_address": ip + '/32'}]}
        port1_rsp = self.update_port(port1['id'], port1_dict)
        port2_rsp = self.update_port(port2['id'], port2_dict)
        return True
    # end config_aap

    def config_vrrp_on_vsrx(self, vm_fix, vip, priority):
        cmdList = []
        cmdList.append('deactivate security nat source rule-set TestNat')
        cmdList.append(
            'deactivate interfaces ge-0/0/1 unit 0 family inet filter')
        cmdList.append('deactivate interfaces ge-0/0/1.0 family inet dhcp')
        cmdList.append('deactivate security policies')
        cmdList.append(
            'set security forwarding-options family inet6 mode packet-based')
        cmdList.append(
            'set security forwarding-options family mpls mode packet-based')
        cmdList.append(
            'set security forwarding-options family iso mode packet-based')
        vsrx_vrrp_config = ['set interfaces ge-0/0/1.0 family inet address ' + vm_fix.vm_ips[
            1] + '/' + '24 vrrp-group 1 priority ' + priority + ' virtual-address ' + vip + ' accept-data']
        cmdList = cmdList + vsrx_vrrp_config
        cmd_string = (';').join(cmdList)
        result = vm_fix.config_via_netconf(cmds=cmd_string)
        return result

    @retry(delay=5, tries=10)
    def config_vrrp(self, vm_fix, vip, priority):
        self.logger.info('Configuring VRRP on %s ' % vm_fix.vm_name)
        vrrp_cmd = 'nohup vrrpd -n -D -i eth0 -v 1 -a none -p %s -d 3 %s' % (
            priority, vip)
        vm_fix.run_cmd_on_vm(cmds=[vrrp_cmd], as_sudo=True)
        result = self.vrrp_chk(vm_fix)
        return result
    # end config_vrrp

    def vrrp_chk(self, vm):
        vrrp_chk_cmd = 'netstat -anp | grep vrrpd'
        vm.run_cmd_on_vm(cmds=[vrrp_chk_cmd], as_sudo=True)
        vrrp_op = vm.return_output_cmd_dict[vrrp_chk_cmd]
        if '/vrrpd' in vrrp_op:
            result = True
            self.logger.info('vrrpd running in %s' % vm.vm_name)
        else:
            result = False
            self.logger.error('vrrpd not running in %s' % vm.vm_name)
        return result
    # end vrrp_mas_chk

    @retry(delay=5, tries=10)
    def vrrp_mas_chk(self, vm, vn, ip, vsrx=False):
        self.logger.info(
            'Will verify who the VRRP master is and the corresponding route entries in the Agent')
        if vsrx:
            vrrp_mas_chk_cmd = 'show vrrp'
            result = vm.config_via_netconf(cmds=vrrp_mas_chk_cmd)
            if 'master' in result:
                self.logger.info(
                    '%s is selected as the VRRP Master' % vm.vm_name)
                result = True
            else:
                result = False
                self.logger.error('VRRP Master not selected')
        else:
            vrrp_mas_chk_cmd = 'ip -4 addr ls'
            vm.run_cmd_on_vm(cmds=[vrrp_mas_chk_cmd], as_sudo=True)
            output = vm.return_output_cmd_dict[vrrp_mas_chk_cmd]
            result = False
            if ip in output:
                self.logger.info(
                    '%s is selected as the VRRP Master' % vm.vm_name)
                result = True
            else:
                result = False
                self.logger.error('VRRP Master not selected')
        inspect_h = self.agent_inspect[vm.vm_node_ip]
        (domain, project, vnw) = vn.vn_fq_name.split(':')
        agent_vrf_objs = inspect_h.get_vna_vrf_objs(domain, project, vnw)
        agent_vrf_obj = vm.get_matching_vrf(
            agent_vrf_objs['vrf_list'], vn.vrf_name)
        vn1_vrf_id = agent_vrf_obj['ucindex']
        paths = inspect_h.get_vna_active_route(
            vrf_id=vn1_vrf_id, ip=ip, prefix='32')['path_list']
        for path in paths:
            if path['peer'] == 'LocalVmPort' and path['path_preference_data']['wait_for_traffic'] == 'false':
                result = True
                break
            else:
                result = False
        return result
    # end vrrp_mas_chk

    @retry(delay=5, tries=10)
    def verify_vrrp_action(self, src_vm, dst_vm, ip, vsrx=False):
        result = False
        self.logger.info('Will ping %s from %s and check if %s responds' % (
            ip, src_vm.vm_name, dst_vm.vm_name))
        compute_ip = dst_vm.vm_node_ip
        compute_user = self.inputs.host_data[compute_ip]['username']
        compute_password = self.inputs.host_data[compute_ip]['password']
        session = ssh(compute_ip, compute_user, compute_password)
        if vsrx:
            vm_tapintf = dst_vm.tap_intf[dst_vm.vn_fq_names[1]]['name']
        else:
            vm_tapintf = dst_vm.tap_intf[dst_vm.vn_fq_name]['name']
        cmd = 'tcpdump -nni %s -c 10 > /tmp/%s_out.log' % (
            vm_tapintf, vm_tapintf)
        execute_cmd(session, cmd, self.logger)
        assert src_vm.ping_with_certainty(ip), 'Ping to vIP failure'
        output_cmd = 'cat /tmp/%s_out.log' % vm_tapintf
        output, err = execute_cmd_out(session, output_cmd, self.logger)
        if ip in output:
            result = True
            self.logger.info(
                '%s is seen responding to ICMP Requests' % dst_vm.vm_name)
        else:
            self.logger.error('ICMP Requests not seen on the VRRP Master')
            result = False
        return result
    # end verify_vrrp_sction

    def _remove_from_cleanup(self, func_call, *args):
        for cleanup in self._cleanups:
            if func_call in cleanup and args == cleanup[1]:
                self._cleanups.remove(cleanup)
                return True
        return False

    def create_lb_pool(self, name, lb_method, protocol, subnet_id):
        lb_pool_resp = None
        lb_pool_resp = self.quantum_h.create_lb_pool(
            name, lb_method, protocol, subnet_id)
        if lb_pool_resp:
            self.addCleanup(self.verify_on_pool_delete, lb_pool_resp['id'])
            self.addCleanup(self.quantum_h.delete_lb_pool,
                            lb_pool_resp['id'])
        return lb_pool_resp
    # end create_lb_pool

    def verify_on_pool_delete(self, pool_id):
        result, msg = self.verify_pool_not_in_api_server(pool_id)
        assert result, msg

    @retry(delay=10, tries=10)
    def verify_pool_not_in_api_server(self, pool_id):
        pool = self.api_s_inspect.get_lb_pool(pool_id)
        if pool:
            self.logger.warn("pool with pool id %s still present in API"
                             " server even after pool delete.retrying..." % (pool_id))
            errmsg = "API server verification failed for pool with pool id %s" % (
                pool_id)
            return False, errmsg
        self.logger.debug(
            "pool with pool id %s not present in API server" % (pool_id))
        return True, None

    def create_lb_member(self, ip_address, protocol_port, pool_id):
        lb_member_resp = None
        lb_member_resp = self.quantum_h.create_lb_member(
            ip_address, protocol_port, pool_id)
        if lb_member_resp:
            self.addCleanup(self.verify_on_member_delete, lb_member_resp['id'])
            self.addCleanup(self.quantum_h.delete_lb_member,
                            lb_member_resp['id'])
        return lb_member_resp
    # end create_lb_member

    def verify_on_member_delete(self, member_id):
        result, msg = self.verify_member_not_in_api_server(member_id)
        assert result, msg

    @retry(delay=10, tries=10)
    def verify_member_not_in_api_server(self, member_id):
        member = self.api_s_inspect.get_lb_member(member_id)
        if member:
            self.logger.warn("member with member id %s still present in API"
                             " server even after member delete" % (member_id))
            errmsg = "API server verification failed for member with member id %s" % (
                member_id)
            assert False, errmsg
        self.logger.debug(
            "member with member id %s not present in API server" % (member_id))
        return True, None

    def create_health_monitor(self, delay, max_retries, probe_type, timeout):
        hm_resp = None
        hm_resp = self.quantum_h.create_health_monitor(
            delay, max_retries, probe_type, timeout)
        if hm_resp:
            self.addCleanup(self.verify_on_healthmonitor_delete, hm_resp['id'])
            self.addCleanup(self.quantum_h.delete_health_monitor,
                            hm_resp['id'])
        return hm_resp
    # end create_health_monitor

    def verify_on_healthmonitor_delete(self, healthmonitor_id):
        result, msg = self.verify_healthmonitor_not_in_api_server(
            healthmonitor_id)
        assert result, msg

    @retry(delay=10, tries=10)
    def verify_healthmonitor_not_in_api_server(self, healthmonitor_id):
        healthmonitor = self.api_s_inspect.get_lb_healthmonitor(
            healthmonitor_id)
        if healthmonitor:
            self.logger.warn("healthmonitor with id %s still present in API"
                             " server even after healthmonitor delete" % (healthmonitor_id))
            errmsg = "API server verification failed for healthmonitor with id %s" % (
                healthmonitor_id)
            assert False, errmsg
        self.logger.debug(
            "healthmonitor with id %s not present in API server" % (healthmonitor_id))
        return True, None

    def create_vip(self, name, protocol, protocol_port, subnet_id, pool_id):
        vip_resp = None
        vip_resp = self.quantum_h.create_vip(
            name, protocol, protocol_port, pool_id, subnet_id)
        if vip_resp:
            self.addCleanup(self.verify_on_vip_delete, pool_id, vip_resp['id'])
            self.addCleanup(self.quantum_h.delete_vip,
                            vip_resp['id'])
        return vip_resp
    # end create_vip

    def verify_on_vip_delete(self, pool_id, vip_id):
        result = True
        result, msg = self.verify_vip_delete(vip_id)
        assert result, msg
        for compute_ip in self.inputs.compute_ips:
            result, msg = self.verify_netns_delete(compute_ip, pool_id)
            assert result, msg
        for compute_ip in self.inputs.compute_ips:
            result, msg = self.verify_haproxy_kill(compute_ip, pool_id)
            assert result, msg
        result, msg = self.verify_vip_not_in_api_server(vip_id)
        assert result, msg
    # end verify_on_vip_delete

    @retry(delay=10, tries=10)
    def verify_vip_delete(self, vip_id):
        vip = self.quantum_h.show_vip(vip_id)
        if vip:
            errmsg = "vip %s still exists after delete" % vip_id
            self.logger.error(errmsg)
            return (False, errmsg)
        self.logger.debug("vip %s deleted successfully" % vip_id)
        return (True, None)
    # end verify_vip_delete

    @retry(delay=10, tries=10)
    def verify_netns_delete(self, compute_ip, pool_id):
        cmd = 'ip netns list | grep %s' % pool_id
        pool_obj = self.quantum_h.get_lb_pool(pool_id)
        out = self.inputs.run_cmd_on_server(
            compute_ip, cmd,
            self.inputs.host_data[compute_ip]['username'],
            self.inputs.host_data[compute_ip]['password'])
        if out:
            self.logger.warn("NET NS: %s still present for pool name: %s with UUID: %s"
                             " even after VIP delete in compute node %s"
                             % (out, pool_obj['name'], pool_id, compute_ip))
            errmsg = "NET NS still present after vip delete, failed in compute %s" % compute_ip
            return False, errmsg
        self.logger.debug("NET NS deleted successfully for pool name: %s with"
                          " UUID :%s in compute node %s" % (pool_obj['name'], pool_id, compute_ip))
        return True, None
    # end verify_netns_delete

    @retry(delay=10, tries=10)
    def verify_haproxy_kill(self, compute_ip, pool_id):
        cmd = 'ps -aux | grep loadbalancer | grep %s' % pool_id
        pool_obj = self.quantum_h.get_lb_pool(pool_id)
        pid = []
        out = self.inputs.run_cmd_on_server(
            compute_ip, cmd,
            self.inputs.host_data[compute_ip]['username'],
            self.inputs.host_data[compute_ip]['password'])
        output = out.split('\n')
        for out in output:
            match = re.search("nobody\s+(\d+)\s+", out)
            if match:
                pid.append(match.group(1))
        if pid:
            self.loger.warn("haproxy still running even after VIP delete for pool name: %s,"
                            " with UUID: %s in compute node %s" % (pool_obj['name'], pool_id, compute_ip))
            errmsg = "HAPROXY still running after VIP delete failed in compute node %s" % (
                compute_ip)
            return False, errmsg
        self.logger.debug("haproxy process got killed successfully with vip delete for pool"
                          " name: %s UUID :%s on compute %s" % (pool_obj['name'], pool_id, compute_ip))
        return True, None
    # end verify_haproxy_kill

    @retry(delay=10, tries=10)
    def verify_vip_not_in_api_server(self, vip_id):
        vip = self.api_s_inspect.get_lb_vip(vip_id)
        if vip:
            self.logger.warn("vip with vip id %s still present in API"
                             " server even after vip delete" % (vip_id))
            errmsg = "API server verification failed for vip with id %s" % (
                vip_id)
            return False, errmsg
        self.logger.debug(
            "vip with vip id %s not present in API server" % (vip_id))
        #msg = "vip with vip id %s not present in API server" % (vip_id)
        return True, None

    def associate_health_monitor(self, pool_id, hm_id):
        hm_resp = self.quantum_h.associate_health_monitor(
            pool_id, hm_id)
        if hm_resp:
            self.addCleanup(self.verify_on_disassociate_health_monitor,
                            pool_id, hm_id)
            self.addCleanup(self.quantum_h.disassociate_health_monitor,
                            pool_id, hm_id)
    # end associate_health_monitor

    def verify_on_disassociate_health_monitor(self, pool_id, hm_id):
        result, msg = self.verify_disassociate_health_monitor(pool_id, hm_id)
        assert result, msg
    # end verify_on_disassociate_health_monitor

    @retry(delay=10, tries=10)
    def verify_disassociate_health_monitor(self, pool_id, hm_id):
        pool = self.api_s_inspect.get_lb_pool(pool_id)
        try:
            healthmonitor_refs = pool[
                'loadbalancer-pool']['loadbalancer_healthmonitor_refs']
            for href in healthmonitor_refs:
                if href['uuid'] == healthmonitor_id:
                    self.logger.warn("healthmonitor with id %s associated with pool"
                                     "  %s" % (healthmonitor_id, pool['loadbalancer-pool']['name']))
                    errmsg = ("API server verification failed, health monitor %s still associated"
                              " with pool %s" % (healthmonitor_id, ool['loadbalancer-pool']['name']))
                    return False, errmsg
                else:
                    self.logger.debug("healthmonitor with id %s successfully disassociated with pool"
                                      "  %s" % (healthmonitor_id, pool['loadbalancer-pool']['name']))
                    return True, None
        except KeyError:
            self.logger.debug("healthmonitor refs not found in API server for pool %s"
                              % (pool['loadbalancer-pool']['name']))
            return True, None
    # end verify_disassociate_health_monitor

    def remove_method_from_cleanups(self, method):
        for cleanup in self._cleanups:
            if method == cleanup:
                self._cleanups.remove(cleanup)
                break
   # end remove_from_cleanups

    def extend_vn_to_physical_router(self, vn_fixture, phy_router_fixture):
        # Attach VN to router in Contrail API so that Device manager
        # can configure the device
        phy_router_fixture.add_virtual_network(vn_fixture.vn_id)
        self.addCleanup(self.delete_vn_from_physical_router, vn_fixture,
                        phy_router_fixture)
    # end extend_vn_to_physical_router

    def delete_vn_from_physical_router(self, vn_fixture, phy_router_fixture):
        # Disassociate VN from the physical router so that Device manager
        # can delete corresponding configs from the device
        phy_router_fixture.delete_virtual_network(vn_fixture.vn_id)
    # end delete_vn_from_physical_router

    def allow_all_traffic_between_vns(self, vn1_fixture, vn2_fixture):
        policy_name = get_random_name('policy-allow-all')
        rules = [
            {   
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any',
                'source_network': vn1_fixture.vn_name,
                'dest_network': vn2_fixture.vn_name,
            },
        ] 
        policy_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name, rules_list=rules, inputs=self.inputs,
                connections=self.connections))

        vn1_fixture.bind_policies(
            [policy_fixture.policy_fq_name], vn1_fixture.vn_id)
        self.addCleanup(vn1_fixture.unbind_policies,
                        vn1_fixture.vn_id, [policy_fixture.policy_fq_name])        

        vn2_fixture.bind_policies(
            [policy_fixture.policy_fq_name], vn2_fixture.vn_id)
        self.addCleanup(vn2_fixture.unbind_policies,
                        vn2_fixture.vn_id, [policy_fixture.policy_fq_name])        
    # end allow_all_traffic_between_vns

    def create_dhcp_server_vm(self,
                              vn1_fixture,
                              vn2_fixture,
                              vm_name=None,
                              node_name=None,
                              flavor='contrail_flavor_large',
                              image_name='ubuntu-dhcpdns-server',
                              port_ids=[]):
        if not vm_name:
            vm_name = get_random_name('dhcp-server')
        vm_fixture = self.useFixture(
            VMFixture(
                project_name=self.inputs.project_name,
                connections=self.connections,
                vn_objs=[vn1_fixture.obj, vn2_fixture.obj],
                vm_name=vm_name,
                image_name=image_name,
                flavor=flavor,
                node_name=node_name,
                port_ids=port_ids))
        assert vm_fixture.verify_on_setup(), (
            "DHCP Server VM Verification failed ")
        assert vm_fixture.wait_till_vm_is_up()
        vn2_fq_name = vn2_fixture.vn_fq_name
        vm_ip = vm_fixture.vm_ip_dict[vn2_fq_name][0]
        cmds = ['ifconfig eth1 up',
                'ifconfig eth1 %s netmask 255.255.255.0' % (vm_ip),
                'service isc-dhcp-server restart']
        vm_fixture.run_cmd_on_vm(cmds, as_sudo=True)
        time.sleep(5)
        return vm_fixture
        
    # end create_dhcp_server_vm

    def setup_vmi(self, vn_id, fixed_ips=[],
                  mac_address=None,
                  security_groups=[],
                  extra_dhcp_opts=[],
                  cleanup=True):
        if mac_address:
            mac_address = EUI(mac_address)
            mac_address.dialect = mac_unix
        port_fixture = PortFixture(
            vn_id,
            mac_address=mac_address,
            fixed_ips=fixed_ips,
            security_groups=security_groups,
            extra_dhcp_opts=extra_dhcp_opts,
            connections=self.connections,
        )
        port_fixture.setUp()
        if cleanup:
            self.addCleanup(port_fixture.cleanUp)
        return port_fixture
    # end setup_vmi

    def do_ping_test(self, fixture_obj, sip, dip, expectation=True): 
        assert fixture_obj.ping_with_certainty(dip, expectation=expectation),\
            'Ping from %s to %s with expectation %s failed!' % (
                sip, dip, str(expectation))
        self.logger.info('Ping test from %s to %s with expectation %s passed' % (sip,
                          dip, str(expectation)))
    # end do_ping_test

