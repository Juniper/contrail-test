import re
import test_v1
from netaddr import *
from vnc_api.vnc_api import *
from vn_test import VNFixture
from vm_test import VMFixture
from policy_test import PolicyFixture
from ipam_test import IPAMFixture
from port_fixture import PortFixture
from project_test import ProjectFixture
from security_group import SecurityGroupFixture
from floating_ip import FloatingIPFixture
from interface_route_table_fixture import InterfaceRouteTableFixture
from tcutils.util import get_random_name, get_random_cidr, is_v6
from tcutils.contrail_status_check import ContrailStatusChecker

class _GenericTestBaseMethods():

    def sleep(self, value):
        self.logger.debug('Sleeping for %s seconds..' % (value))
        time.sleep(value)
    # end sleep

    def remove_from_cleanups(self, func_call, *args):
        for cleanup in self._cleanups:
            if func_call in cleanup and args == cleanup[1]:
                self._cleanups.remove(cleanup)
                return True
        return False

    def remove_method_from_cleanups(self, method):
        for cleanup in self._cleanups:
            if method == cleanup:
                self._cleanups.remove(cleanup)
                break
   # end remove_method_from_cleanups

    def set_global_asn(self, asn):
        existing_asn = self.vnc_lib_fixture.get_global_asn()
        ret = self.vnc_lib_fixture.set_global_asn(asn)
        self.addCleanup(self.vnc_lib_fixture.set_global_asn, existing_asn)
        return ret
    # end set_global_asn

    def perform_cleanup(self, obj, remove_cleanup=True):
        if getattr(obj, 'cleanUp', None):
            if remove_cleanup:
                self.remove_from_cleanups(obj.cleanUp)
            obj.cleanUp()
    # end perform_cleanup

    def alloc_ips(self, vn_fixture, count=1):
        ret_val = vn_fixture.alloc_ips(count=count)
        self.addCleanup(vn_fixture.free_ips, ret_val)
        return ret_val
    # end alloc_ips

    def stop_containers(self, node_ip, containers, wait=10):
        '''
        containers  : list of container names to be stopped
        node_ip     : Node on which containers need to be stopped
        wait        : Seconds to wait for stop before killing it
        '''
        for container in containers:
            self.logger.info('Stopping container %s on %s' %(container, node_ip))
            self.inputs.stop_container(node_ip, container)
        self.addCleanup(self.start_containers, node_ip, containers)
    # end stop_containers

    def start_containers(self, node_ip, containers):
        '''
        containers: list of container names to be started
        node_ip: Node on which containers need to be started
        '''
        self.remove_from_cleanups(self.start_containers,
            (self, node_ip, containers))
        for container in containers:
            self.logger.info('Starting container %s on %s' %(container, node_ip))
            self.inputs.start_container(node_ip, container)
        self.sleep(60)
        assert ContrailStatusChecker().wait_till_contrail_cluster_stable(
            nodes=[node_ip])[0]
    # end start_containers

    def add_knob_to_container(self, node_ip, container_name, level='DEFAULT', knob=None):
        ''' Add a configuration knob to container at specified level
            Args:
                node_ip         : Node on which containers need to be stopped
                container_name  : Name of the container
                level           : Hierarchy level where knob needs to be added
                knob            : Knob which needs to be added
            E.g: add_knob_to_container('10.204.217.127', 'control_control_1',
            'DEFAULT', 'mvpn_ipv4_enable=1')
        '''

        issue_cmd = 'docker cp %s:/entrypoint.sh .' % (container_name)
        username = self.inputs.host_data[node_ip]['username']
        password = self.inputs.host_data[node_ip]['password']

        self.logger.info('Running %s on %s' % (issue_cmd, node_ip))
        self.inputs.run_cmd_on_server(node_ip, issue_cmd, username, password, pty=True,
                                    as_sudo=True)

        just_knob = knob[:knob.find('=')] 
        issue_cmd = 'sed -i -e \'/'+just_knob+'/d\' entrypoint.sh'
        self.logger.info('Running %s on %s' % (issue_cmd, node_ip))
        self.inputs.run_cmd_on_server(node_ip, issue_cmd, username, password, pty=True,
                                    as_sudo=True)
        issue_cmd = 'grep -q -F \''+knob+'\' entrypoint.sh ||' + \
            'sed -i  \'/\['+level+'\]/a '+knob+'\' entrypoint.sh'
        self.logger.info('Running %s on %s' % (issue_cmd, node_ip))
        self.inputs.run_cmd_on_server(node_ip, issue_cmd, username, password, pty=True,
                                    as_sudo=True)

        issue_cmd = 'docker cp entrypoint.sh %s:/entrypoint.sh' % (container_name)
        self.logger.info('Running %s on %s' % (issue_cmd, node_ip))
        self.inputs.run_cmd_on_server(node_ip, issue_cmd, username, password, pty=True,
                                    as_sudo=True)

        issue_cmd = 'docker restart %s -t 60' % (container_name)
        self.logger.info('Running %s on %s' % (issue_cmd, node_ip))
        self.inputs.run_cmd_on_server(node_ip, issue_cmd, username, password, pty=True,
                                    as_sudo=True)

# end _GenericTestBaseMethods


class GenericTestBase(test_v1.BaseTestCase_v1, _GenericTestBaseMethods):

    @classmethod
    def setUpClass(cls):
        super(GenericTestBase, cls).setUpClass()
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
        cls.api_s_inspect = cls.connections.api_server_inspect
        cls.orch = cls.connections.orch
        try:
            address_family = cls.address_family or 'v4'
        except AttributeError:
            cls.address_family = 'v4'
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(GenericTestBase, cls).tearDownClass()
    # end tearDownClass


    def get_connections(self, username, password, project_fixture):
        return project_fixture.get_project_connections(username=username, password=password)

    @classmethod
    def create_only_project(cls, project_name=None, **kwargs):
        project_name = project_name or get_random_name('project')
        connections = kwargs.pop('connections', None) or cls.connections
        project_fixture = ProjectFixture(connections=connections,
                          project_name=project_name, **kwargs)
        project_fixture.setUp()
        return project_fixture

    def create_project(self, project_name=None, cleanup=True, **kwargs):
        project_fixture = self.create_only_project(project_name, **kwargs)
        if cleanup:
            self.addCleanup(project_fixture.cleanUp)
        return project_fixture

    def add_user_to_project(self, project_name=None, username=None, role='admin', **kwargs):
        connections = kwargs.get('connections') or self.connections
        username = username or self.inputs.stack_user
        project_name = project_name or self.inputs.project_name
        connections.auth.add_user_to_project(username, project_name, role)
        self.addCleanup(connections.auth.remove_user_from_project,
                        username, role, project_name)

    @classmethod
    def create_only_vn(cls, vn_name=None, vn_subnets=None, vxlan_id=None,
                   enable_dhcp=True, **kwargs):
        '''Classmethod to do only VN creation
        '''
        if not vn_name:
            vn_name = get_random_name('vn')
        project_name = kwargs.pop('project_name', None) or cls.connections.project_name
        connections = kwargs.pop('connections', None) or cls.connections
        vn_fixture = VNFixture(project_name=project_name,
                      connections=connections,
                      inputs=connections.inputs,
                      vn_name=vn_name,
                      subnets=vn_subnets,
                      vxlan_id=vxlan_id,
                      enable_dhcp=enable_dhcp,
                      **kwargs)
        vn_fixture.setUp()
        return vn_fixture
    # end create_only_vn

    def create_vn(self, vn_name=None, vn_subnets=None, vxlan_id=None,
        enable_dhcp=True, cleanup=True, **kwargs):
        vn_fixture = self.create_only_vn(vn_name=vn_name,
                                     vn_subnets=vn_subnets,
                                     vxlan_id=vxlan_id,
                                     enable_dhcp=enable_dhcp,
                                     **kwargs)
        if cleanup:
            self.addCleanup(vn_fixture.cleanUp)

        return vn_fixture
    # end create_vn

    @classmethod
    def create_only_vm(cls, vn_fixture=None, vm_name=None, node_name=None,
                  flavor='contrail_flavor_small',
                  image_name='ubuntu-traffic',
                  port_ids=[], **kwargs):
        vn_obj = None
        if vn_fixture:
            vn_obj = vn_fixture.obj
        project_name = kwargs.pop('project_name', None) or cls.connections.project_name
        connections = kwargs.pop('connections', None) or cls.connections
        vm_obj = VMFixture(
                    project_name=project_name,
                    connections=connections,
                    vn_obj=vn_obj,
                    vm_name=vm_name,
                    image_name=image_name,
                    flavor=flavor,
                    node_name=node_name,
                    port_ids=port_ids,
                    **kwargs)
        vm_obj.setUp()
        return vm_obj
    # end create_only_vm

    def create_vm(self, vn_fixture=None, vm_name=None, node_name=None,
                  flavor='contrail_flavor_small',
                  image_name='ubuntu-traffic',
                  port_ids=[], **kwargs):
        cleanup = kwargs.pop('cleanup', True)
        vm_fixture = self.create_only_vm(vn_fixture=vn_fixture,
                        vm_name=vm_name,
                        node_name=node_name,
                        flavor=flavor,
                        image_name=image_name,
                        port_ids=port_ids,
                        **kwargs)
        if cleanup:
            self.addCleanup(vm_fixture.cleanUp)
        return vm_fixture

    def create_router(self, router_name=None, connections=None):
        if not connections:
            neutron_handle = self.quantum_h
        else:
            neutron_handle = connections.quantum_h
        if not router_name:
            router_name = 'router-%s' % (get_random_name())
        obj = neutron_handle.create_router(router_name)
        if obj:
            self.addCleanup(neutron_handle.delete_router, obj['id'])
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
        self.remove_from_cleanups(self.quantum_h.delete_port, (port_id))
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
        self.remove_from_cleanups(self.delete_router_interface,
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

    def create_ipam(self, name=None, connections=None):
        connections = connections or self.connections
        name = name or get_random_name('ipam')
        return self.useFixture(IPAMFixture(name, connections))

    def create_floatingip_pool(self, floating_vn, name=None):
        fip_pool_name = name if name else get_random_name('fip')
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name,
                vn_id=floating_vn.vn_id))
        assert fip_fixture.verify_on_setup()
        return fip_fixture

    def create_interface_route_table(self, prefixes):
        intf_route_table_obj = self.vnc_h.create_route_table(
            prefixes = prefixes,
            parent_obj=self.project.project_obj)
        return intf_route_table_obj

    @classmethod
    def setup_only_policy_between_vns(cls, vn1_fixture, vn2_fixture, rules=[], **kwargs):
        connections = kwargs.get('connections') or cls.connections
        api = kwargs.get('api') or None
        policy_name = get_random_name('policy-allow-all')
        rules = rules or [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any',
                'source_network': vn1_fixture.vn_name,
                'dest_network': vn2_fixture.vn_name,
            },
        ]
        policy_fixture = PolicyFixture(
                policy_name=policy_name, rules_list=rules, inputs=connections.inputs,
                connections=connections, api=api)
        policy_fixture.setUp()

        vn1_fixture.bind_policies(
            [policy_fixture.policy_fq_name], vn1_fixture.vn_id, reset=False)
        vn2_fixture.bind_policies(
            [policy_fixture.policy_fq_name], vn2_fixture.vn_id, reset=False)
        return policy_fixture
    # end setup_only_policy_between_vns

    def setup_policy_between_vns(self, vn1_fixture, vn2_fixture,
                                 rules=[], cleanup=True, **kwargs):
        policy_fixture = self.setup_only_policy_between_vns(vn1_fixture,
                                            vn2_fixture, rules, **kwargs)
        if cleanup:
            self.addCleanup(policy_fixture.cleanUp)
            self.addCleanup(vn1_fixture.unbind_policies,
                        vn1_fixture.vn_id, [policy_fixture.policy_fq_name])
            self.addCleanup(vn2_fixture.unbind_policies,
                        vn2_fixture.vn_id, [policy_fixture.policy_fq_name])
        return policy_fixture
    # end setup_policy_between_vns

    def create_dhcp_server_vm(self,
                              vn1_fixture,
                              vn2_fixture,
                              vm_name=None,
                              node_name=None,
                              flavor='contrail_flavor_large',
                              image_name='ubuntu-dns-server',
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
        self.sleep(5)
        return vm_fixture

    # end create_dhcp_server_vm

    @classmethod
    def setup_only_vmi(cls, vn_id=None, fixed_ips=[],
                  mac_address=None,
                  security_groups=[],
                  extra_dhcp_opts=[],
                  **kwargs):
        if mac_address:
            mac_address = EUI(mac_address)
            mac_address.dialect = mac_unix
        port_fixture = PortFixture(
            vn_id=vn_id,
            mac_address=mac_address,
            fixed_ips=fixed_ips,
            security_groups=security_groups,
            extra_dhcp_opts=extra_dhcp_opts,
            connections=cls.connections,
            **kwargs
        )
        port_fixture.setUp()
        return port_fixture
    # end setup_only_vmi

    def setup_vmi(self, vn_id=None, fixed_ips=[],
                  mac_address=None,
                  security_groups=[],
                  extra_dhcp_opts=[],
                  **kwargs):
        cleanup = kwargs.pop('cleanup', True)
        port_fixture = self.setup_only_vmi(vn_id=vn_id,fixed_ips=fixed_ips,
                                           mac_address=mac_address,
                                           security_groups=security_groups,
                                           extra_dhcp_opts=extra_dhcp_opts,
                                           **kwargs)
        if cleanup:
            self.addCleanup(port_fixture.cleanUp)
        return port_fixture
    # end setup_vmi

    def setup_interface_route_table(
            self,
            obj=None,
            name=None,
            cleanup=True,
            **kwargs):
        '''
        Create interface route table and optionally add it to obj
        obj : Example : PortFixture instance
        '''
        name = name or get_random_name('irtb')
        intf_route_table = InterfaceRouteTableFixture(
            name=name,
            cleanup=cleanup,
            connections=self.connections,
            **kwargs)
        intf_route_table.setUp()
        if cleanup:
            self.sleep(1)
            self.addCleanup(intf_route_table.cleanUp)
        if obj:
            self.add_interface_route_table(obj,intf_route_table.obj, cleanup)
        return intf_route_table
    # end setup_interface_route_table

    def add_interface_route_table(self, obj, intf_route_table_obj,
        cleanup=True):
        ''' Calls add_interface_route_table on obj object
            intf_route_table_obj is InterfaceRouteTable instance
        '''
        obj.add_interface_route_table(intf_route_table_obj)
        if cleanup:
            self.addCleanup(obj.del_interface_route_table,
                            intf_route_table_obj.uuid)
    # end add_inteface_route_table

    def del_interface_route_table(self, obj, uuid):
        self.remove_from_cleanups(obj.del_interface_route_table, (uuid))
        obj.del_interface_route_table(uuid)
    # end del_interface_route_table

    def do_ping_test(self, fixture_obj, sip, dip, expectation=True):
        assert fixture_obj.ping_with_certainty(dip, expectation=expectation),\
            'Ping from %s to %s with expectation %s failed!' % (
                sip, dip, str(expectation))
        self.logger.info('Ping test from %s to %s with expectation %s passed' % (sip,
                          dip, str(expectation)))
    # end do_ping_test

    def apply_policy(self, policy_fixture, vn_fixtures=None):
        policy_fqname = policy_fixture.policy_fq_name
        for fixture in vn_fixtures:
            fixture.bind_policies([policy_fqname])
            self.addCleanup(fixture.unbind_policies, policy_fq_names=[policy_fqname])

    def create_policy(self, policy_name=None, rules=[], **kwargs):
        policy_name = policy_name or get_random_name('policy')
        policy_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=rules,
                inputs=self.inputs,
                connections=self.connections,
                **kwargs))
        return policy_fixture
    #end create_policy

    def _get_network_policy_rule(self, direction='<>', protocol='any',
                         action='pass', src_vn=None, dst_vn=None,
                         src_ports=(0, 65535), dst_ports=(0, 65535),
                         src_cidr=None, dst_cidr=None, src_policy=None,
                         dst_policy=None, action_list=None):
        rule = {'direction': direction,
                'protocol': protocol,
                'source_network': src_vn,
                'source_policy': src_policy,
                'source_subnet': src_cidr,
                'src_ports': src_ports,
                'dest_network': dst_vn,
                'dest_policy': dst_policy,
                'dest_subnet': dst_cidr,
                'dst_ports': dst_ports,
                'action_list': action_list or {},
                'simple_action': action
               }
        return rule

    def _get_secgrp_rule(self, direction='ingress', protocol='any',
                         dst_ports=(0, 65535), src_ports=(0, 65535),
                         cidr='0.0.0.0/0', dst_sg=None, af='IPv4'):
        if dst_sg:
            addr = {'security_group': dst_sg}
        else:
            subnet, mask = cidr.split('/')
            addr = {'subnet': {'ip_prefix': subnet, 'ip_prefix_len': int(mask)}}
        if direction == 'ingress':
            src_addr = addr
            dst_addr = {'security_group': 'local'}
        else:
            dst_addr = addr
            src_addr = {'security_group': 'local'}
        rule = {'direction': '>',
                'protocol': protocol,
                'dst_addresses': [dst_addr],
                'dst_ports': [{'start_port': dst_ports[0], 'end_port': dst_ports[1]}],
                'src_ports': [{'start_port': src_ports[0], 'end_port': src_ports[1]}],
                'src_addresses': [src_addr],
                'ethertype': af
               }
        return rule

    def create_security_group(self, name=None, rules=None, **kwargs):
        connections = kwargs.get('connections') or self.connections
        option = kwargs.get('option') or 'neutron'
        name = name or get_random_name('secgrp')
        secgrp_fixture = self.useFixture(SecurityGroupFixture(
            connections, secgrp_name=name,
            secgrp_entries=rules, option=option))
        return secgrp_fixture
    # end create_sg

    def get_default_sg(self, **kwargs):
        connections = kwargs.get('connections') or self.connections
        option = kwargs.get('option') or 'neutron'
        return self.useFixture(SecurityGroupFixture(connections,
                               secgrp_name='default', option=option))

    @classmethod
    def check_vms_booted(cls, vms_list, do_assert=True):
        '''
        If instances call this method, they may need to set do_assert to False
        so that the fixture cleanup routines automatically take care of deletion
        '''
        failed = False
        for vm_fixture in vms_list:
            if not vm_fixture.wait_till_vm_is_up():
                msg = 'VM %s has not booted' %(vm_fixture.vm_name)
                cls.logger.error(msg)
                failed = True
                break
        if failed and do_assert:
            for vm_fixture in vms_list:
                vm_fixture.cleanUp()
            assert False, 'One or more vm-boots failed. Check logs'
        if failed:
            return False
        return True
    # end check_vms_booted

    @classmethod
    def check_vms_active(cls, vms_list, do_assert=True):
        '''
        If instances call this method, they may need to set do_assert to False
        so that the fixture cleanup routines automatically take care of deletion
        '''
        failed = False
        for vm_fixture in vms_list:
            if not vm_fixture.wait_till_vm_is_active():
                msg = 'VM %s has not booted' %(vm_fixture.vm_name)
                cls.logger.error(msg)
                failed = True
                break
        if failed and do_assert:
            for vm_fixture in vms_list:
                vm_fixture.cleanUp()
            assert False, 'One or more vm-boots failed. Check logs'
        if failed:
            return False
        return True
    # end check_vms_active

    @classmethod
    def set_af(cls, family='v4'):
        cls.address_family = family

    @classmethod
    def get_af(cls):
        return cls.address_family

    @classmethod
    def safe_cleanup(cls, obj_name):
        '''
        Check if the fixture object exists and 'created' attribute
        is set in it. If so, call the cleanUp() of the fixture object
        '''
        obj = getattr(cls, obj_name, None)
        if obj and getattr(obj, 'created', False):
            return obj.cleanUp()
    # end cleanup
