from builtins import str
from builtins import range
import test_v1
from common.connections import ContrailConnections
from tcutils.util import *
from tcutils.tcpdump_utils import *
from compute_node_test import ComputeNodeFixture
from vnc_api.vnc_api import *
from tcutils.traffic_utils.base_traffic import *
from tcutils.traffic_utils.hping_traffic import Hping3
from tcutils.traffic_utils.ping_traffic import Ping
from common.neutron.base import BaseNeutronTest
import random
from security_group import get_secgrp_id_from_name, SecurityGroupFixture
from tcutils.agent.vrouter_lib import *
from policy_test import PolicyFixture
from vn_policy_test import VN_Policy_Fixture
from port_fixture import PortFixture
import ipaddress
from common.servicechain.config import ConfigSvcChain
from common.servicechain.verify import VerifySvcChain
from svc_hc_fixture import HealthCheckFixture
from common.servicechain.mirror.verify import VerifySvcMirror

class BaseVrouterTest(BaseNeutronTest, VerifySvcMirror):

    @classmethod
    def setUpClass(cls):
        super(BaseVrouterTest, cls).setUpClass()
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib_fixture = cls.connections.vnc_lib_fixture
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
        cls.api_s_inspect = cls.connections.api_server_inspect
        cls.orch = cls.connections.orch
        cls.compute_ips = cls.inputs.compute_ips
        cls.compute_fixtures_dict = {}
        cls.logger = cls.connections.logger
        cls.vnc_h = cls.vnc_lib_fixture.vnc_h
        cls.ops_inspect = cls.connections.ops_inspects

        for ip in cls.compute_ips:
            cls.compute_fixtures_dict[ip] = ComputeNodeFixture(
                                        cls.connections,ip)
            cls.compute_fixtures_dict[ip].setUp()
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        for ip in cls.compute_ips:
            cls.compute_fixtures_dict[ip].cleanUp()
        super(BaseVrouterTest, cls).tearDownClass()
    # end tearDownClass

    def _create_resources(self, test_type='intra-node', no_of_client=1,
            no_of_server=1):
        '''
            test_type: can be intra-node or inter-node
        '''
        compute_hosts = self.orch.get_hosts()
        if (len(compute_hosts) < 2) and (test_type == 'inter-node'):
            raise self.skipTest("Skipping test case,\
                                    this test needs atleast 2 compute nodes")

        node_name1 = compute_hosts[0]
        node_ip1 = self.inputs.compute_info[node_name1]
        node_name2 = compute_hosts[0]
        node_ip2 = self.inputs.compute_info[node_name2]

        if test_type == 'inter-node':
            node_name2 = compute_hosts[1]
            node_ip2 = self.inputs.compute_info[node_name2]

        self.vn_fixtures = self.create_vns(count=2)
        self.verify_vns(self.vn_fixtures)
        self.vn1_fixture = self.vn_fixtures[0]
        self.vn2_fixture = self.vn_fixtures[1]
        self.client_fixtures = self.create_vms(vn_fixture=self.vn1_fixture,
            count=no_of_client, node_name=node_name1, image_name='ubuntu-traffic')
        self.server_fixtures = self.create_vms(vn_fixture=self.vn2_fixture,
            count=no_of_server, node_name=node_name2, image_name='ubuntu-traffic')
        self.client_fixture = self.client_fixtures[0]
        self.server_fixture = self.server_fixtures[0]

        policy_name = 'policy1'
        policy_rules = [
            {
                'direction': '<>', 'simple_action': 'pass',
                'protocol': 'any',
                'source_network': self.vn1_fixture.vn_name,
                'dest_network': self.vn2_fixture.vn_name,
            }
        ]
        self.policy_fixture = self.useFixture(
            PolicyFixture(
                policy_name=policy_name,
                rules_list=policy_rules,
                inputs=self.inputs,
                connections=self.connections,
                api=True))

        self.vn1_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.vn1_fixture.vn_name,
                policy_obj={self.vn1_fixture.vn_name : \
                           [self.policy_fixture.policy_obj]},
                vn_obj={self.vn1_fixture.vn_name : self.vn1_fixture},
                vn_policys=[policy_name],
                project_name=self.project.project_name))

        self.vn2_policy_fixture = self.useFixture(
            VN_Policy_Fixture(
                connections=self.connections,
                vn_name=self.vn2_fixture.vn_name,
                policy_obj={self.vn2_fixture.vn_name : \
                           [self.policy_fixture.policy_obj]},
                vn_obj={self.vn2_fixture.vn_name : self.vn2_fixture},
                vn_policys=[policy_name],
                project_name=self.project.project_name))

        self.verify_vms(self.client_fixtures + self.server_fixtures)

    #end _create_resources

    @retry(delay=2, tries=15)
    def get_vna_route_with_retry(self, agent_inspect, vrf_id, ip, prefix):
        '''
            Get vna route with retry
        '''
        route_list = agent_inspect.get_vna_route(vrf_id, ip, prefix)

        if not route_list:
            self.logger.warn("Route of IP %s not found in agent" % (ip))
            return (False, None)
        else:
            return (True, route_list)

    def get_random_ip_from_vn(self, vn_fixture):
        ips = []
        cidrs = vn_fixture.get_cidrs(af=self.inputs.get_af())
        for cidr in cidrs:
            ips.append(get_random_ip(cidr))

        return ips

    def create_vns(self, count=1, *args, **kwargs):
        vn_fixtures = []
        for i in range(count):
            if 'vn_subnets' not in list(kwargs.keys()):
                vn_subnets = get_random_cidrs(self.inputs.get_af())
                vn_fixtures.append(self.create_vn(vn_subnets=vn_subnets, *args, **kwargs))
            else:
                vn_fixtures.append(self.create_vn(*args, **kwargs))

        return vn_fixtures

    def verify_vns(self, vn_fixtures):
        for vn_fixture in vn_fixtures:
            assert vn_fixture.verify_on_setup()

    def create_vms(self, vn_fixture, count=1, image_name='ubuntu',
            fixed_ips_list=None, node_list=None, *args, **kwargs):
        vm_fixtures = []
        node_name = None
        host = False
        compute_hosts = self.orch.get_hosts()
        for i in range(count):
            if node_list:
                node_count = len(node_list)
                node_id  = i % node_count
                node_name = node_list[node_id]
                if 'node_name' not in list(kwargs.keys()):
                    kwargs['node_name'] = node_name
                    host = True
            fixed_ips=None
            if fixed_ips_list:
                fixed_ips=fixed_ips_list[i]
            vm_fixtures.append(self.create_vm(
                            vn_fixture,
                            image_name=image_name,
                            fixed_ips=fixed_ips,
                            *args, **kwargs
                            ))
            if host:
                del kwargs['node_name']

        return vm_fixtures

    def _remove_fixture_from_cleanup(self, fixture):
        for cleanup in self._cleanups:
            if hasattr(cleanup[0],'__self__') and fixture == cleanup[0].__self__:
                self._cleanups.remove(cleanup)
                return True
        return False

    def delete_vms(self, vm_fixtures):
        for vm_fixture in vm_fixtures:
            self._remove_fixture_from_cleanup(vm_fixture)
            vm_fixture.cleanUp()

    def verify_vms(self, vm_fixtures):
        for vm_fixture in vm_fixtures:
            assert vm_fixture.wait_till_vm_is_up()

    def add_static_routes_on_vms(self,prefix, vm_fixtures, ip=None):
        if ip is None:
            #get a random IP from the prefix and configure it on the VMs
            ip = get_random_ip(prefix)
        for vm_fixture in vm_fixtures:
            #Disable duplicate address detection before adding static IP on VMs
            interface = vm_fixture.get_vm_interface_list(ip=vm_fixture.vm_ip)[1][0]
            cmd = 'sysctl net.ipv6.conf.%s.accept_dad=0' % (interface)
            vm_fixture.run_cmd_on_vm([cmd], as_sudo=True)
            vmi_ids = list(vm_fixture.get_vmi_ids().values())
            for vmi_id in vmi_ids:
                route_table_name = get_random_name('my_route_table')
                vm_fixture.provision_static_route(
                                prefix=prefix,
                                tenant_name=self.inputs.project_name,
                                oper='add',
                                virtual_machine_interface_id=vmi_id,
                                route_table_name=route_table_name,
                                user=self.inputs.stack_user,
                                password=self.inputs.stack_password)
                assert vm_fixture.add_ip_on_vm(ip)

        return ip

    def disable_policy_on_vmis(self, vmi_ids, disable=True):
        '''vmi_ids: list of VMIs'''
        for vmi_id in vmi_ids:
            self.vnc_h.disable_policy_on_vmi(vmi_id, disable)

        return True

    def disable_policy_for_vms(self, vm_fixtures, disable=True):
        for vm in vm_fixtures:
            vmi_ids = list(vm.get_vmi_ids().values())
            self.disable_policy_on_vmis(vmi_ids, disable)

        return True

    def add_fat_flow_to_vmis(self, vmi_ids, fat_flow_config):
        '''vmi_ids: list of vmi ids
           fat_flow_config: dictionary of format {'proto':<string>,'port':<int>,
            'ignore_address': <string, source/destination>}
        '''
        for vmi_id in vmi_ids:
            self.vnc_h.add_fat_flow_to_vmi(vmi_id, fat_flow_config)

        return True

    def remove_fat_flow_on_vmis(self, vmi_ids, fat_flow_config):
        '''vmi_ids: list of vmi ids
           fat_flow_config: dictionary of format {'proto':<string>,'port':<int>}
        '''
        for vmi_id in vmi_ids:
            vmi_obj = self.vnc_h.remove_fat_flow_on_vmi(vmi_id, fat_flow_config)

        return True


    def get_cidr_mask_vmi_id(self, fix, ipv6=False):
        cidr, cidr6, mask, mask6, subnet_ipv4, subnet_ipv6 = None, None, None, None, None, None
        subnets =  fix.vn_subnets
        vn_subnets = fix.get_subnets()
        for subnet in vn_subnets:
             if subnet.get('ip_version') == 4:
                 subnet_ipv4_id = subnet.get('id')
             elif subnet.get('ip_version') == 6:
                 subnet_ipv6_id = subnet.get('id')
        for subnet in subnets:
            subnet1  = subnet.get('cidr').split('/')
            if subnet.get('ip_version') == '6':
                cidr6 = subnet1[0]
                mask6 = subnet1[1]
            else:
                cidr = subnet1[0]
                mask = subnet1[1]
        cidr_mask_ipv6 = None
        cidr_mask_ipv4 = (cidr, mask, subnet_ipv4_id)
        if ipv6:
            cidr_mask_ipv6 = (cidr6, mask6, subnet_ipv6_id)

        cidr_mask = { 'v4': cidr_mask_ipv4, 'v6': cidr_mask_ipv6 }
        return cidr_mask
    # end get_cidr_mask_vmi_id

    def fat_flow_with_prefix_aggr(self, prefix_length=29, prefix_length6=125,
        inter_node=False, inter_vn=False, dual=False, traffic_recvr=False,
        unidirectional_traffic=True, ignore_address=None,
        proto='udp', port=55, portv6=56, svc_chain=False, only_v6=False,
        af='v4', icmp_error=False, hc=None, vn_policy=True, policy_deny=False,
        svm_inter_node=False, resources=True, scale=False):
        '''
        Method to configure fat flow with prefix aggr with various options
        traffic_recvr : if enabled, traffic is also started from the server (bidirectional)
        dual : configures fat flow for both IPv4 and IPv6, use only_v6 flag to configure
        only for IPv6
        For aggrSrc/AggrDst: Match rule is reversed if traffic is from fabric to VM, or VM to faric
        i.e. AggrSrc is matched with dst ip, and AggrDst is match with src ip
        For VM to VM: Match rule is not swapped.
        AggrSrc/AggrDst rule are applied only for prefixes which are configured in the aggr fat flow config.
        i.e. Aggr Src 20.1.1.0 29 is configured, then fat flow gets created only when src ip belongs to 20.1.1.0
        '''

        afs = ['v4', 'v6'] if 'dual' in self.inputs.get_af() else [self.inputs.get_af()]
        if only_v6:
            afs = ['v6']

        if resources: # Need to create new fixture objs if resources flag is set
            # if not set, no need to create fresh resources, useful for config changes only
            self.vn_fixtures = None
            self.client1_fix = None
            self.client2_fix = None
            self.server_fixtures = None
            self.policy_fixture_vn1_vn2 = None
            self.svc_chain_info = None
            self.hc_fixture = None
            ff_on_si_vmis = None

        scale_src = scale

        if policy_deny:
            vn_policy = True

        fat_flow = True # Default is enabled, global flag to test the scenario without fat flow

        none_in_one = False # When each VM/SVM is on a different node,  applicable for no. of CNs > 2

        svm_inter_node = False

        compute_hosts = self.orch.get_hosts()
        if inter_node:  # Only for src and dst vm
            if len(compute_hosts) < 2:
                raise self.skipTest("Skipping test case,"
                                        "this test needs atleast 2 compute nodes")
        if dual:
            self.inputs.set_af('dual') # Configures fat flow for both IPv4 and IPv6
        vn_count = 1
        if inter_vn:
            vn_count = 2
        svm_inter_node = svm_inter_node # src vm and svm on same compute, if enabled svm on different compute
        server_compute = compute_hosts[0] # client vms always launched on host0
        if inter_node:
            server_compute = compute_hosts[1]
        svm_fix = False

        if svc_chain:
            svm_fix= True
            if not self.vn_fixtures:
                self.vn_fixtures = self.create_vns(count=vn_count)
            vn_fixtures = self.vn_fixtures
            inter_vn = True
            dual = False
            svm_node = compute_hosts[2]
            svm_node_remote = compute_hosts[2] #scenario 1
            if svm_inter_node:  # svm is inter wrt to src vm
                svm_node_remote = compute_hosts[1]  #scenario 2
            if none_in_one:
                svm_node = compute_hosts[2]
                svm_node_remote = compute_hosts[3]
        else:
            if vn_policy:
                if not self.vn_fixtures:
                    self.vn_fixtures = self.create_vns(count=vn_count)
                vn_fixtures = self.vn_fixtures
            else:
                if not self.vn_fixtures:
                    self.vn_fixtures = self.create_vns(count=vn_count, rt_number='10000')
                vn_fixtures = self.vn_fixtures

        self.verify_vns(vn_fixtures)
        src_vn_fixture = vn_fixtures[0]
        dst_vn_fixture = vn_fixtures[0]

        if len(vn_fixtures) > 1:
            dst_vn_fixture = vn_fixtures[1]
        cidr_mask_dict = self.get_cidr_mask_vmi_id(src_vn_fixture, ipv6=dual)
        cidr, mask, subnet_ipv4 = cidr_mask_dict.get('v4')

        if dual:
            cidr6, mask6, subnet_ipv6 = cidr_mask_dict.get('v6')
        if not self.client1_fix:
            self.client_fixtures = self.create_vms(vn_fixture= src_vn_fixture,count=1,
                                          node_name=compute_hosts[0])
            self.client1_fix = self.client_fixtures[0]
            assert self.client1_fix.wait_till_vm_is_up()

        if scale_src:
            node_list = [ compute_hosts[0], compute_hosts[2], compute_hosts[3] ]
            node_list = [ compute_hosts[0], compute_hosts[2], compute_hosts[3] ]
            self.scale_clients = self.create_vms(vn_fixture= src_vn_fixture,count=scale_src, node_list=node_list)
            for client in self.scale_clients:
                client.read()
                assert client.wait_till_vm_is_up()
        client1_fix = self.client1_fix
        client1_fix.read()
        calc_no_hosts = 2 ** (32 - prefix_length)
        client1_vm_ip = client1_fix.get_vm_ips(af='v4')[0]
        next_subnet_ip = str(ipaddress.IPv4Address
                             (str(client1_vm_ip)) + calc_no_hosts)
        next_subnet = str(ipaddress.IPv4Address(str(cidr)) + calc_no_hosts)
        fixed_ips = [{'subnet_id' : subnet_ipv4,'ip_address': next_subnet_ip}]
        fixed_ips = [{'subnet_id' : subnet_ipv4,'ip_address': next_subnet_ip}]

        if self.inputs.get_af() == 'dual':
             client1_vm_ipv6 = None
             if client1_fix.get_vm_ips(af='v6'):
                 client1_vm_ipv6 = client1_fix.get_vm_ips(af='v6')[0]

             calc_no_hosts = 2 ** (128 - prefix_length6)
             next_subnet_ipv6 = str(ipaddress.IPv6Address
                                    (str(client1_vm_ipv6)) + calc_no_hosts)
             next_subnetv6 = str(ipaddress.IPv6Address
                                 (str(cidr6)) + calc_no_hosts)
             fixed_ips.append({'subnet_id' : subnet_ipv6,'ip_address': next_subnet_ipv6})
        if not self.client2_fix:
            self.client2_fix = self.create_vm_using_fixed_ips(
                vn_fixture=src_vn_fixture, fixed_ips=fixed_ips,
                vm_name='client2_vm')
        client2_fix = self.client2_fix
        if not self.server_fixtures:
            self.server_fixtures = self.create_vms(vn_fixture= dst_vn_fixture,count=1,
                                        node_name=server_compute)
            for server in self.server_fixtures:
                assert server.wait_till_vm_is_up()

        server_fixtures = self.server_fixtures
        client_fixtures  = [client1_fix, client2_fix]
        client1_ip = client_fixtures[0].vm_ips[0]
        client2_ip = client_fixtures[1].vm_ips[0]
        for server in server_fixtures:
            server.read()
        server_ip = server_fixtures[0].vm_ips[0]
        if vn_policy:
            policy_name_vn1_vn2 = get_random_name("vn1_vn2_pass")
            vn1_name = vn_fixtures[0].vn_fq_name.split(':')[2]
            vn2_name = vn_fixtures[1].vn_fq_name.split(':')[2]
            rules = []
            if policy_deny:
                source_subnet1 = client1_ip + '/32'
                source_subnet2 = client2_ip + '/32'
                dst_subnet = server_ip + '/32'
                self.create_policy_rule(rules, src_subnet=source_subnet2, dst_subnet=dst_subnet, proto=proto, action='deny')
            if not self.policy_fixture_vn1_vn2:
                self.create_policy_rule(rules, src_vn=vn1_name, dst_vn=vn2_name, proto=proto)
                self.policy_fixture_vn1_vn2 = self.config_policy(policy_name_vn1_vn2, rules)
                policy_fixture_vn1_vn2 = self.policy_fixture_vn1_vn2
                if not svc_chain: # No need to configure explicit policy
                    vn1_v2_attach_to_vn1 = self.attach_policy_to_vn(
                        policy_fixture_vn1_vn2, vn_fixtures[0])
                    vn1_vn2_attach_to_vn2 = self.attach_policy_to_vn(
                        policy_fixture_vn1_vn2, vn_fixtures[1])

        expected_src_prefix_list  = { client_fixtures[0]: cidr, client_fixtures[1]: next_subnet}
        if scale_src:
            # rpf disabled required when multiple clients reachable over multiple tunnels, snh(0)
            # needs to be 0, else invalid source issue due to rpf check failure.
            self.vnc_lib_fixture.set_rpf_mode(vn_fixtures[1].vn_fq_name, 'disable')
            for client in self.scale_clients:
                expected_src_prefix_list[client] = cidr
        if not fat_flow:
            expected_src_prefix_list  = { client_fixtures[0]: client1_ip, client_fixtures[1]: client2_ip}
            if scale_src:
               for client in self.scale_clients:
                   expected_src_prefix_list[client] = client.vm_ips[0]

        ignore_address_left = 'src'
        ignore_address_right = 'dst'
        svm_fixture = None
        if svc_chain:
            # For svc_chain = { "svc_aggr": True, "ff_on_si_vmis": True, "svc_ignore_addr": True }
            svc_aggr = svc_chain.get('svc_aggr', True)
            svc_mode = svc_chain.get('svc_mode', 'in-network')
            # For enabling SrcAggr/DstAggr, without this basic fat flow config with ignore src
            ff_on_si_vmis = svc_chain.get('ff_on_si_vmis', {'left':False, 'right': False})
            # If enabled, fat flow configs on left vmi and right vmi
            svmi_config = svc_chain.get('svmi_config', {'left_vmi_config':'AggrDst', 'right_vmi_config': 'AggrSrc'})
            svc_ignore_addr = svc_chain.get('svc_ignore_addr', True) # For enabling ignore address config on svc VMIs
            scale = svc_chain.get('instances', 1)
            st_name = get_random_name("in_net_svc_template_1")
            si_prefix = get_random_name("in_net_svc_instance") + "_"
            policy_name = get_random_name("policy_in_network")
            server_compute = compute_hosts[1] # server vm is always launched on compute 1 when svc chain is enabled
            hosts = [svm_node]
            if scale == 2:
                hosts.append(svm_node_remote)
            if not self.svc_chain_info:
                self.svc_chain_info = self.config_svc_chain(
                    left_vn_fixture=src_vn_fixture,
                    right_vn_fixture=dst_vn_fixture,
                    service_mode=svc_mode,
                    left_vm_fixture=client1_fix,
                    right_vm_fixture=server_fixtures[0],
                    create_svms=True,
                    hosts=hosts, max_inst=scale)
            svc_chain_info = self.svc_chain_info
            st_fixture = svc_chain_info['st_fixture']
            si_fixture = svc_chain_info['si_fixture']
            flow_timeout = 100
            self.add_proto_based_flow_aging_time(proto, port, flow_timeout)
            if ff_on_si_vmis:
                left_vn_fq_name =  src_vn_fixture.vn_fq_name
                right_vn_fq_name = dst_vn_fixture.vn_fq_name

                cidr_mask_dict_left = self.get_cidr_mask_vmi_id(src_vn_fixture)
                cidr_left, mask_left, subnet_left = cidr_mask_dict_left.get('v4')

                cidr_mask_dict_right = self.get_cidr_mask_vmi_id(dst_vn_fixture)
                cidr_right, mask_right, subnet_right = cidr_mask_dict_right.get('v4')

                if hc:
                    http_url = 'local-ip'
                    hc_type = hc.get('hc_type', 'link-local')
                    if hc_type == 'end-to-end':
                        # Check for bug 1704716
                        http_url='ping://' + server_fixtures[0].vm_ip
                        # for ping use 'ping://', for http, use 'http://'(default)
                    if not self.hc_fixture:
                        hc_fixture = self.useFixture(HealthCheckFixture(connections=self.connections,
                            name=get_random_name(self.inputs.project_name),hc_type=hc_type, delay=3,
                            probe_type='PING', timeout=5, max_retries=2, http_url=http_url))
                    hc_fixture = self.hc_fixture
                    assert hc_fixture.verify_on_setup()
                    si_index = hc['si_index']
                    si_intf_type = hc['si_intf_type']
                    st_fixtures = [st_fixture]
                    si_fixtures = [si_fixture]
                    si_fixture = si_fixtures[si_index]
                    si_fixture.associate_hc(hc_fixture.uuid, si_intf_type)
                    self.addCleanup(si_fixture.disassociate_hc, hc_fixture.uuid)
                    assert si_fixture.verify_hc_in_agent()
                    assert si_fixture.verify_hc_is_active()
                    for i in range(len(st_fixtures)):
                        assert st_fixtures[i].verify_on_setup(), 'ST Verification failed'
                        assert si_fixtures[i].verify_on_setup(), 'SI Verification failed'

                if not svc_aggr:
                    cidr=None
                    mask=None
                    prefix_length=None
                    if not svc_ignore_addr:
                        ignore_address=None
                    cidr_left = None
                    mask_left = None
                    cidr_right = None
                    mask_right = None

                # default config is cidr_left on both left vmi and right vmi
                left_vmi_config = svmi_config['left_vmi_config']
                right_vmi_config = svmi_config['right_vmi_config']
                left_src = None
                right_src = None
                if left_vmi_config  == 'AggrDst':
                    left_src = False
                if right_vmi_config == 'AggrDst':
                    right_src = False
                if left_vmi_config == 'AggrSrc':
                    left_src = True
                if right_vmi_config == 'AggrSrc':
                    right_src = True

                fat_flow_cidr_on_left_vmi = None
                fat_flow_cidr_on_right_vmi = None
                if ff_on_si_vmis.get('left'):
                    fat_flow_cidr_on_left_vmi = cidr_left
                if ff_on_si_vmis.get('right'):
                    fat_flow_cidr_on_right_vmi = cidr_left
                svm_fixtures = svc_chain_info['svm_fixtures']
                svm_fixtures = svc_chain_info['svm_fixtures']
                for svm_fixture in svc_chain_info['svm_fixtures']:
                    # if max_instance > 1 configure the fat flow for both the instances
                    vmi_ids_dict = svm_fixture.get_vmi_ids()
                    left_vmi_id = vmi_ids_dict[left_vn_fq_name]
                    right_vmi_id = vmi_ids_dict[right_vn_fq_name]

                    clean_config = True
                    repeat = 1
                    for num in range(repeat):
                        if clean_config:
                            self.delete_fat_flow_from_vmi(vmi_ids=[left_vmi_id])
                            self.delete_fat_flow_from_vmi(vmi_ids=[right_vmi_id])

                        if fat_flow:
                            self.config_fat_flow_aggr_prefix(vmi=[left_vmi_id], proto=proto,
                                                             port=port, cidr=fat_flow_cidr_on_left_vmi, mask=mask_left,
                                                             prefix_length=prefix_length,
                                                             ignore_address=ignore_address_left, src=left_src)
                            self.config_fat_flow_aggr_prefix(vmi=[right_vmi_id], proto=proto,
                                                             port=port, cidr=fat_flow_cidr_on_right_vmi, mask=mask_left,
                                                             prefix_length=prefix_length,
                                                             ignore_address=ignore_address_right, src=right_src)
                        config_change = False
                        if config_change:
                            self.config_fat_flow_aggr_prefix(vmi=[left_vmi_id], proto=proto,
                                                             port=port, cidr=fat_flow_cidr_on_left_vmi, mask=mask_left,
                                                             prefix_length=prefix_length,
                                                             ignore_address=None, src=left_src)
                            self.config_fat_flow_aggr_prefix(vmi=[right_vmi_id], proto=proto,
                                                             port=port, cidr=fat_flow_cidr_on_right_vmi, mask=mask_left,
                                                             prefix_length=prefix_length,
                                                             ignore_address=None, src=right_src)
                            ignore_address = None
                # check health status again after configuring fat flow, bug 1704716
                if hc:
                    assert si_fixture.verify_hc_in_agent()
                    assert si_fixture.verify_hc_is_active()

        #Configure Fat flow on server VM
        server_vmi_id = list(server_fixtures[0].get_vmi_ids().values())
        ff_on_vmi = False
        if not only_v6 and ff_on_vmi or not ff_on_si_vmis:
            if fat_flow:
                for vmi_id in [ server_vmi_id ]:
                    self.config_fat_flow_aggr_prefix(vmi=vmi_id, proto=proto,
                                                     port=port, cidr=cidr, mask=mask,
                                                     prefix_length=prefix_length,
                                                     ignore_address=ignore_address)
        for af in afs:
            port = port
            if af == 'v6':
                port = portv6
                for vmi_id in [ server_vmi_id ]:
                    self.config_fat_flow_aggr_prefix(vmi=vmi_id,
                        proto=proto, port=port, cidr=cidr6, mask=mask6,
                        prefix_length=prefix_length6, ignore_address=ignore_address)
                expected_src_prefix_list  = { client_fixtures[0]: cidr6, client_fixtures[1]: next_subnetv6}
                if proto == 'icmp': port = 0
            scale_sessions = 1 # default
            if scale_src:
                client_fixtures.extend(self.scale_clients)
                #scale_sessions = 0 # number of sessions from a src
                scale_sessions = 3
            expected_flow_count = 1
            if svm_fix:
                ignore_address = ignore_address_left
                #expected_flow_count = 2 # For both left and right vmi
            for fix in server_fixtures:
                self.verify_fat_flow_with_traffic(client_fixtures,fix,
                                                    proto, port, af=af, expected_src_prefix_list=expected_src_prefix_list,
                                                    unidirectional_traffic=unidirectional_traffic,
                                                    ignore_address=ignore_address, icmp_error=icmp_error,
                                                    svm_fix=svm_fixture, expected_flow_count=expected_flow_count,
                                                    svc_chain=svc_chain, scale=scale_sessions)
            clean_config = True
            if fat_flow and ff_on_si_vmis and clean_config:
                for svm_fixture in svc_chain_info['svm_fixtures']:
                    # if max_instance > 1 configure the fat flow for both the instances
                    vmi_ids_dict = svm_fixture.get_vmi_ids()
                    left_vmi_id = vmi_ids_dict[left_vn_fq_name]
                    right_vmi_id = vmi_ids_dict[right_vn_fq_name]
                    self.delete_fat_flow_from_vmi(vmi_ids=[left_vmi_id])
                    self.delete_fat_flow_from_vmi(vmi_ids=[right_vmi_id])
    # end

    def fat_flow_config_on_svms(self, svm_fixtures, fat_flow=False):
        for svm_fixture in svm_fixtures:
            # if max_instance > 1 configure the fat flow for both the instances
            vmi_ids_dict = svm_fixture.get_vmi_ids()
            left_vmi_id = vmi_ids_dict[left_vn_fq_name]
            right_vmi_id = vmi_ids_dict[right_vn_fq_name]

            clean_config = True
            if clean_config:
                self.delete_fat_flow_from_vmi(vmi_ids=[left_vmi_id])
                self.delete_fat_flow_from_vmi(vmi_ids=[right_vmi_id])

            if fat_flow:
                self.config_fat_flow_aggr_prefix(vmi=[left_vmi_id], proto=proto,
                                                 port=port, cidr=fat_flow_cidr_on_left_vmi, mask=mask_left,
                                                 prefix_length=prefix_length,
                                                 ignore_address=ignore_address_left, src=left_src)
                self.config_fat_flow_aggr_prefix(vmi=[right_vmi_id], proto=proto,
                                                 port=port, cidr=fat_flow_cidr_on_right_vmi, mask=mask_left,
                                                 prefix_length=prefix_length,
                                                 ignore_address=ignore_address_right, src=right_src)

    def delete_fat_flow_from_vmi(self, vmi_ids):
        '''vmi_ids: list of vmi ids
           fat_flow_config: dictionary of format {'proto':<string>,'port':<int>,
            'ignore_address': <string, source/destination>}
        '''
        for vmi_id in vmi_ids:
            self.vnc_h.delete_all_fat_flow_config_from_vmi(vmi_id)

        return True

    def create_policy_rule(self, rules, src_vn=None, dst_vn=None,
                           src_subnet=None, dst_subnet=None, src_ports=[0, 65535],
                           dest_ports=[0, 65535], action='pass',
                           proto='icmp', direction='<>'):
        rule = {'direction': direction,
            'protocol': proto,
            'source_network': src_vn,
            'src_ports': src_ports,
            'dest_network': dst_vn,
            'source_subnet': src_subnet,
            'dest_subnet': dst_subnet,
            'dst_ports': dest_ports,
            'simple_action': action,
            'action_list': {'simple_action': action}
            }
        rules.append(rule)
    # end create_policy_rule


    def config_fat_flow_aggr_prefix(self, vmi, proto=None, port=None, cidr=None, mask=None,
                                    prefix_length=None, src=None, ignore_address=None):
        config_dict = {}
        if ignore_address == 'src':
            config_dict['ignore_address'] = 'source'
        elif ignore_address == 'dst':
            config_dict['ignore_address'] = 'destination'

        config_dict['port'] = port
        config_dict['proto'] = proto
        prefix_type = 'destination_prefix'
        length_type = 'destination_aggregate_prefix_length'
        if src:
            prefix_type = 'source_prefix'
            length_type = 'source_aggregate_prefix_length'
        config_dict[prefix_type] = [cidr, mask]
        config_dict[length_type] = prefix_length
        self.add_fat_flow_to_vmis(vmi, config_dict)
    # end config_fat_flow_aggr_prefix

    def create_vm_using_fixed_ips(self, vn_fixture,
            fixed_ips, vm_name='vm1', image_name='ubuntu'):
        port = self.useFixture(PortFixture(vn_fixture.uuid,
                                api_type = "contrail",
                                fixed_ips = fixed_ips,
                                connections=self.connections))
        fix = self.create_vm(vn_fixture, vm_name,
                                     image_name=image_name,
                                     port_ids=[port.uuid])
        assert fix.wait_till_vm_is_up()
        return fix
    # end create_vm_using_fixed_ips

    def add_fat_flow_to_vns(self, vn_fixtures, fat_flow_config):
        '''vn_fixtures: list of vn fixtures
           fat_flow_config: dictionary of format {'proto':<string>,'port':<int>,
            'ignore_address': <string, source/destination>}
        '''
        ignore_address = fat_flow_config.get('ignore_address', None)
        if ignore_address:
            proto_type = ProtocolType(protocol=fat_flow_config['proto'],
                port=fat_flow_config['port'], ignore_address=ignore_address)
        else:
            proto_type = ProtocolType(protocol=fat_flow_config['proto'],
                            port=fat_flow_config['port'])
        for vn in vn_fixtures:
            fat_config = vn.get_fat_flow_protocols()
            if fat_config:
                fat_config.fat_flow_protocol.append(proto_type)
            else:
                fat_config = FatFlowProtocols(fat_flow_protocol=[proto_type])
            vn.set_fat_flow_protocols(fat_config)

        return True

    def delete_fat_flow_from_vns(self, vn_fixtures):
        '''Removes all Fat flow config from VNs'''
        fat_config = FatFlowProtocols()
        for vn in vn_fixtures:
            vn.set_fat_flow_protocols(fat_config)

    def add_proto_based_flow_aging_time(self, proto, port=0, timeout=180):
        self.vnc_h.add_proto_based_flow_aging_time(proto, port, timeout)
        self.addCleanup(self.vnc_h.delete_proto_based_flow_aging_time,
                                proto, port, timeout)

        return True

    def delete_all_flows_on_vms_compute(self, vm_fixtures):
        '''
        Deletes all the flows on the compute node of the VMs
        '''
        for vm in vm_fixtures:
            self.compute_fixtures_dict[vm.vm_node_ip].delete_all_flows()

    def restart_agent_on_vms_compute(self, vm_fixtures):
        '''
        Restart agent on the compute node of the VMs
        '''
        for vm in vm_fixtures:
            self.compute_fixtures_dict[vm.vm_node_ip].restart_agent()

    def send_hping3_traffic(self, sender_vm_fix, dest_ip, srcport, destport,
                            count=1, interval='u100', stop=True, wait=False,
                            **kwargs):
        '''
        Sends unidirectional traffic from sender_vm_fix to dest_ip using hping3 util,
        where as destination will send icmp error if no process is running on port destport
        '''
        hping_h = Hping3(sender_vm_fix,
                         dest_ip,
                         destport=destport,
                         baseport=srcport,
                         count=count,
                         interval=interval,
                         **kwargs)
        hping_h.start(wait=wait)
        if stop:
            (stats, hping_log) = hping_h.stop()
            self.logger.debug('Hping3 log : %s' % (hping_log))
            return (stats, hping_log)
        elif wait:
            stats = hping_h.get_stats()
            return (stats, None)
        else:
            return (hping_h, None)

    def send_nc_traffic(self, sender_vm_fix, dest_vm_fix, sport, dport,
            proto, size='100', ip=None, exp=True, receiver=True):
        '''
        Sends tcp/udp traffic using netcat, this method will work for IPv4 as well as IPv6
        Starts the netcat on both sender and on receiver if receiver is True
        IPv6 will work only with ubuntu and ubuntu-traffic images,
            cirros does not support IPv6.
        '''
        af =  get_af_type(ip) if ip else self.inputs.get_af()
        nc_options = '-4' if (af == 'v4') else '-6'
        nc_options = nc_options + ' -q 2 -w 5'
        if proto == 'udp' or proto == 17:
            nc_options = nc_options + ' -u'

        result = sender_vm_fix.nc_file_transfer(
            dest_vm_fix, local_port=sport, remote_port=dport,
            nc_options=nc_options, size=size, ip=ip, expectation=exp,
            retry=True, receiver=receiver)
        return result

    def remove_sg_from_vms(self, vm_fix_list, sg_id=None):
        default_sg_id = get_secgrp_id_from_name(
                                self.connections,
                                ':'.join([self.connections.domain_name,
                                        self.inputs.project_name,
                                        'default']))
        sg_id = sg_id or default_sg_id
        for vm in vm_fix_list:
            vm.remove_security_group(secgrp=sg_id)

    def add_sg_to_vms(self, vm_fix_list, sg_id=None):
        default_sg_id = get_secgrp_id_from_name(
                                self.connections,
                                ':'.join([self.connections.domain_name,
                                        self.inputs.project_name,
                                        'default']))
        sg_id = sg_id or default_sg_id
        for vm in vm_fix_list:
            vm.add_security_group(secgrp=sg_id)

    def create_sg(self, name=None, entries=None):
        sg_fixture = self.useFixture(SecurityGroupFixture(
            self.connections, self.inputs.domain_name, self.inputs.project_name,
            secgrp_name=name, secgrp_entries=entries))

        return sg_fixture

    def verify_sg(self, sg_fixture):
        result, msg = sg_fixture.verify_on_setup()
        assert result, msg

    def verify_flow_action(self, compute_fix, action, src_ip=None, dst_ip=None,
            sport=None, dport=None, src_vrf=None, proto=None, exp=True):
        '''
        action can be one of FORWARD, DROP, NAT, HOLD
        '''
        (forward_flow, reverse_flow) = compute_fix.get_flow_entry(source_ip=src_ip, dest_ip=dst_ip,
            source_port=sport, dest_port=dport, proto=proto, vrf_id=src_vrf)

        if exp:
            assert (forward_flow.action == action), ("Flow Action expected: %s"
                ",got: %s" % (action, forward_flow.action))
        else:
            assert (forward_flow.action != action), ("Flow Action not expected: %s"
                ",got: %s" % (action, forward_flow.action))

    def verify_traffic_for_ecmp_si(self, sender_vm_fix, si_vm_list,
                dest_vm_fix, dest_ip=None, flow_count=0, si_left_vn_name=None):
        '''
        This method is similar to verify_traffic_for_ecmp for service chain case.
        tcpdump is done on left interface of the SIs and ping is used for traffic verification
        The method is written for transparent service chain
        '''
        session = {}
        pcap = {}
        compute_node_ips = []
        compute_fixtures = []
        proto = 'icmp' if (self.inputs.get_af() == 'v4') else 'icmp6'
        dest_ip = dest_ip or dest_vm_fix.vm_ip
        vm_fix_pcap_pid_files = {}
        errmsg = "Ping to right VM ip %s from left VM failed" % dest_ip

        #Get all the VMs compute IPs
        compute_node_ips.append(sender_vm_fix.vm_node_ip)
        if dest_vm_fix.vm_node_ip not in compute_node_ips:
                compute_node_ips.append(dest_vm_fix.vm_node_ip)

        #Get the compute fixture for all the concerned computes
        for ip in compute_node_ips:
            compute_fixtures.append(self.compute_fixtures_dict[ip])

        result = False

        #Start the tcpdump on all the SI VMs
        for vm in si_vm_list:
            filters = '\'(%s and (host %s or host %s))\'' % (
                proto, sender_vm_fix.vm_ip, dest_ip)
            if not self.inputs.pcap_on_vm:
                session[vm], pcap[vm] = start_tcpdump_for_vm_intf(self, vm,
                    si_left_vn_name, filters = filters)
            else:
                vm_fix_pcap_pid_files[vm] = start_tcpdump_for_vm_intf(
                    None, [vm], None, filters=filters, pcap_on_vm=True, vm_intf='eth1', svm=True)

        #wait till ping passes without any loss
        assert sender_vm_fix.ping_with_certainty(dest_ip), errmsg

        #Clean all the old flows before starting the traffic
        for fixture in compute_fixtures:
            fixture.delete_all_flows()

        assert sender_vm_fix.ping_to_ip(dest_ip), errmsg

        #Verify tcpdump count, any one SI should receive the packets
        for vm in si_vm_list:
            if not self.inputs.pcap_on_vm:
                ret = verify_tcpdump_count(self, session[vm], pcap[vm])
            else:
                ret = verify_tcpdump_count(self, None, 'eth1', vm_fix_pcap_pid_files=vm_fix_pcap_pid_files[vm], svm=True)
            if ret:
                self.logger.error("Tcpdump verification on SI %s passed" %
                                    vm.vm_ip)
                result = ret
                break

        if not self.inputs.pcap_on_vm:
            for vm in si_vm_list:
                stop_tcpdump_for_vm_intf(self, session[vm], pcap[vm])
                delete_pcap(session[vm], pcap[vm])

        #Verify expected flow count, on all the computes
        for vm in [sender_vm_fix, dest_vm_fix]:
            compute_fix = self.compute_fixtures_dict[vm.vm_node_ip]
            self.verify_flow_on_compute(compute_fix, sender_vm_fix.vm_ip,
                dest_ip, proto=proto, ff_exp=flow_count, rf_exp=flow_count)

        if result:
            self.logger.info("Traffic verification for ECMP passed")
        else:
            self.logger.info("Traffic verification for ECMP failed")

        return result

    def verify_ecmp_routes_si(self, sender_vm_fix, dest_vm_fix):
        '''
        Verify ECMP routes in agent for service chain case
        '''
        result = False
        if self.inputs.get_af() == 'v6':
            prefix_len = 128
        else:
            prefix_len = 32

        #Verify ECMP routes
        vrf_id = sender_vm_fix.agent_vrf_id[sender_vm_fix.vn_fq_name]
        route_list = self.get_vna_route_with_retry(
            self.agent_inspect[sender_vm_fix.vm_node_ip], vrf_id,
            dest_vm_fix.vm_ip, prefix_len)[1]

        if not route_list:
            self.logger.error("Route itself could not be found in agent for IP %s, test failed"
                % (dest_vm_fix.vm_ip))
            return False

        for route in route_list['routes']:
            for path in route['path_list']:
                if 'ECMP Composite sub nh count:' in path['nh']['type']:
                    self.logger.info("ECMP routes found in agent %s, for "
                        "IP %s" % (sender_vm_fix.vm_node_ip, sender_vm_fix.vm_ip))
                    result = True
                    break

        return result

    def verify_ecmp_routes(self, vm_fix_list, prefix):
        '''
        Verify ECMP routes in agent and tap interface of each of the VM in ecmp routes.
        more validations can be added here
        Inputs args:
            vm_fix_list: list of VM's whose vrfs need to be validated for ecmp routes
            prefix: prefix for which routes need to be validated
        '''

        prefix_split = prefix.split('/')
        tap_itf_list = []
        result = False

        #Get expected tap interfaces in ecmp routes
        for vm in vm_fix_list:
            tap_itf_list.append(vm.tap_intf[vm.vn_fq_name]['name'])

        for vm in vm_fix_list:
            vrf_id = vm.agent_vrf_id[vm.vn_fq_name]
            route_list = self.get_vna_route_with_retry(
                self.agent_inspect[vm.vm_node_ip], vrf_id,
                prefix_split[0], prefix_split[1])[1]

            if not route_list:
                self.logger.error("Route itself could not be found in agent for IP %s, test failed"
                    % (prefix_split[0]))
                return False

            for route in route_list['routes']:
                for path in route['path_list']:
                    if 'ECMP Composite sub nh count:' in path['nh']['type']:
                        self.logger.info("ECMP routes found in agent %s, for "
                            "prefix %s" % (vm.vm_node_ip, prefix))
                        if 'mc_list' in path['nh']:
                            for item in path['nh']['mc_list']:
                                if ('itf' in item) and (item['itf'] in tap_itf_list):
                                    self.logger.info("Tap interface %s found in "
                                        "ecmp routes in agent %s" % (item['itf'],
                                        vm.vm_node_ip))
                                    tap_itf_list.remove(item['itf'])
                        result = True
                        break

        if result:
            if not tap_itf_list:
                return result
            else:
                self.logger.error("Tap interface %s not found in any agent" % (
                    tap_itf_list))
                return False
        else:
            self.logger.error("ECMP routes not found in any agent")
            return False


    def verify_traffic_for_ecmp(self, sender_vm_fix,
                                dest_vm_fix_list, dest_ip, flow_count=0):
        '''
        Common method to be used to verify if traffic goes through fine for ECMP
        routes and flow is not created on the computes
        Inputs-
            sender_vm_fix: sender VM fixture
            dest_vm_fix_list: list of destination VM fixtures
            dest_ip: IP where traffic needs to be sent
        Verifications:
            1. Traffic verification is done on all the VMs via tcpdump
            2. nc is used to send udp traffic
            3. Verify no flow is created on all the computes, when policy is disabled
        '''
        session = {}
        pcap = {}
        proto = 'udp'
        destport = '11000'
        result = False
        sport = random.randint(12000, 65000)

        af =  get_af_type(dest_ip)
        sender_vm_ip = sender_vm_fix.get_vm_ips(af=af)[0]
        vm_fix_pcap_pid_files = {}
        src_compute_fix = self.compute_fixtures_dict[sender_vm_fix.vm_node_ip]
        src_vrf_id = src_compute_fix.get_vrf_id(sender_vm_fix.vn_fq_names[0])
        #Start the tcpdump on all the destination VMs
        for vm in dest_vm_fix_list:
            filters = '\'(%s and src host %s and dst host %s and dst port %s)\'' % (
                proto, sender_vm_ip, dest_ip, int(destport))
            if not self.inputs.pcap_on_vm:
                session[vm], pcap[vm] = start_tcpdump_for_vm_intf(self, vm,
                                            vm.vn_fq_names[0], filters = filters)
            else:
                vm_fix_pcap_pid_files[vm] = start_tcpdump_for_vm_intf(
                    None, [vm], None, filters=filters, pcap_on_vm=True)

        #Send the traffic without any receiver, dest VM will send icmp error
        nc_options = '-4' if (af == 'v4') else '-6'
        nc_options = nc_options + ' -q 2 -u'
        sender_vm_fix.nc_send_file_to_ip('icmp_error', dest_ip,
            local_port=sport, remote_port=destport,
            nc_options=nc_options)

        #Verify tcpdump count, any one destination should receive the packet
        for vm in dest_vm_fix_list:
            if not self.inputs.pcap_on_vm:
                ret = verify_tcpdump_count(self, session[vm], pcap[vm])
            else:
                ret = verify_tcpdump_count(self, None, None, vm_fix_pcap_pid_files=vm_fix_pcap_pid_files[vm])
            if ret:
                self.logger.info("Tcpdump verification on VM %s passed" %
                                    vm.get_vm_ips(af=af)[0])
                result = ret
                #Verify flow on the dest VM compute where traffic is received
                dst_compute_fix = self.compute_fixtures_dict[vm.vm_node_ip]
                dst_vrf = dst_compute_fix.get_vrf_id(vm.vn_fq_names[0])
                src_vrf = dst_compute_fix.get_vrf_id(sender_vm_fix.vn_fq_names[0])
                dst_vrf_on_src = src_compute_fix.get_vrf_id(vm.vn_fq_names[0])
                self.verify_flow_on_compute(dst_compute_fix,
                    sender_vm_ip,
                    dest_ip, src_vrf, dst_vrf, sport=sport, dport=destport,
                    proto=proto, ff_exp=flow_count, rf_exp=flow_count)

                break
        for vm in dest_vm_fix_list:
            if not self.inputs.pcap_on_vm:
                stop_tcpdump_for_vm_intf(self, session[vm], pcap[vm])
                delete_pcap(session[vm], pcap[vm])

        #Verify expected flow count on sender compute
        self.verify_flow_on_compute(src_compute_fix, sender_vm_ip,
            dest_ip, src_vrf_id, dst_vrf_on_src, sport=sport, dport=destport,
            proto=proto, ff_exp=flow_count, rf_exp=flow_count)

        if result:
            self.logger.info("Traffic verification for ECMP passed")
        else:
            self.logger.info("Traffic verification for ECMP failed")

        return result

    def send_traffic_verify_flow_dst_compute(self, src_vm_fix, dst_vm_fix,
            proto, sport=10000, dport=11000, ff_exp=0, rf_exp=0, exp=True):

        src_ip = src_vm_fix.vm_ip
        dst_ip = dst_vm_fix.vm_ip

        assert self.send_nc_traffic(src_vm_fix, dst_vm_fix, sport, dport,
            proto, exp=exp)

        compute_fix = self.compute_fixtures_dict[dst_vm_fix.vm_node_ip]
        dst_vrf = compute_fix.get_vrf_id(dst_vm_fix.vn_fq_names[0])
        src_vrf = compute_fix.get_vrf_id(src_vm_fix.vn_fq_names[0]) or dst_vrf

        self.verify_flow_on_compute(compute_fix, src_ip,
            dst_ip, src_vrf, dst_vrf, sport=sport, dport=dport, proto=proto,
            ff_exp=ff_exp, rf_exp=rf_exp)

    def verify_flow_on_compute(self, compute_fixture, source_ip, dest_ip,
            src_vrf=None, dst_vrf=None, sport=None, dport=None, proto=None,
            ff_exp=1, rf_exp=1):
        '''
        Verifies flow on specific compute node
        '''
        (ff_count, rf_count) = compute_fixture.get_flow_count(
                                    source_ip=source_ip,
                                    dest_ip=dest_ip,
                                    source_port=sport,
                                    dest_port=dport,
                                    proto=proto,
                                    vrf_id=src_vrf
                                    )
        if src_vrf != dst_vrf:
            (rf_count, ff_count2) = compute_fixture.get_flow_count(
                                        source_ip=dest_ip,
                                        dest_ip=source_ip,
                                        source_port=dport,
                                        dest_port=sport,
                                        proto=proto,
                                        vrf_id=dst_vrf
                                        )
        if (ff_count != ff_exp) or (rf_count != rf_exp):
            str_log = 'FAILED'
        else:
            str_log = 'PASSED'
        self.logger.debug("Flow verification %s on node: %s for VMs - "
            "Sender: %s, Receiver: %s, Flow count expected: %s %s, "
            "got: %s %s" % (str_log, compute_fixture.ip, source_ip, dest_ip,
            ff_exp, rf_exp, ff_count, rf_count))
        assert ff_count == ff_exp, ('Flow count mismatch on '
            'compute, please check logs..')
        assert rf_count == rf_exp, ('Flow count mismatch on '
            'compute, please check logs..')

    def verify_fat_flow_on_compute(self, compute_fixture, source_ip, dest_ip,
                               dest_port, proto, vrf_id, fat_flow_count=1,
                               sport=0):
        '''
        Verifies Fat flow on specific compute node
        '''
        #Get Fat flow, with source port as ZERO
        (ff_count, rf_count) = compute_fixture.get_flow_count(
                                    source_ip=source_ip,
                                    dest_ip=dest_ip,
                                    source_port=sport,
                                    dest_port=dest_port,
                                    proto=proto,
                                    vrf_id=vrf_id
                                    )
        if (ff_count != fat_flow_count) or (rf_count != fat_flow_count):
            str_log = 'FAILED'
        else:
            str_log = 'PASSED'
        self.logger.info("Fat flow verification %s on node: %s for - "
                            "SIP: %s, DIP: %s, sport: %s, dport: %s, "
                            "vrf-id: %s "
                            "Fat flow expected: %s, got: %s" % (
                            str_log,
                            compute_fixture.ip,
                            source_ip, dest_ip, sport, dest_port, vrf_id,
                            fat_flow_count, ff_count))
        assert ff_count == fat_flow_count, ('Fat flow count mismatch on '
            'compute, got:%s, exp:%s' % (ff_count, fat_flow_count))
        assert rf_count == fat_flow_count, ('Fat flow count mismatch on '
            'compute, got:%s, exp:%s' % (rf_count, fat_flow_count))

    def verify_fat_flow(self, sender_vm_fix_list, dst_vm_fix,
                               proto, dest_port,
                               fat_flow_count=1,
                               unidirectional_traffic=True, af=None,
                               expected_src_prefix_list=None, expected_dst_prefix_list=None,
                               ignore_address=None, icmp_error=False, svm_fix=None, svc_chain=None):
        '''
        Verifies FAT flows on all the computes
        '''
        ff_count = fat_flow_count
        af = af or self.inputs.get_af()
        if svm_fix: # For SVM, ff verification should happen on the CN where SVM is launched
            verify_for_left_vmi=True
            verify_for_right_vmi=True
        dst_compute_fix = self.compute_fixtures_dict[dst_vm_fix.vm_node_ip]
        vrf_id_dst = dst_compute_fix.get_vrf_id(dst_vm_fix.vn_fq_names[0])
        if svm_fix:
            dst_compute_fix = self.compute_fixtures_dict[svm_fix.vm_node_ip]
            vrf_id_dst = None # Ignore vrf_id for SVMI
        for fix in sender_vm_fix_list:
            fat_flow_count = ff_count
            src_compute_fix = self.compute_fixtures_dict[fix.vm_node_ip]
            vrf_id_src = src_compute_fix.get_vrf_id(fix.vn_fq_names[0])
            if svm_fix:
                vrf_id_src = None
                if proto == 'icmp': dest_port = None
                fat_flow_count = 2
            #For inter-Node traffic
            if expected_src_prefix_list:
                src_ip = expected_src_prefix_list[fix]
            else:
                src_ip = fix.get_vm_ips(af=af)[0]
            if expected_dst_prefix_list:
                dst_ip = expected_dst_prefix_list[fix]
                dest_port = dest_port
            else:
                dst_ip = dst_vm_fix.get_vm_ips(af=af)[0]
            if ignore_address == 'src':
                dst_ip = '0.0.0.0' if self.inputs.get_af() == 'v4' else '::'
            if ignore_address == 'dst':
                src_ip = '0.0.0.0' if self.inputs.get_af() == 'v4' else '::'
            ff_fix = dst_vm_fix # Where ff verification happens
            if svm_fix:
                svm_compute_fix = self.compute_fixtures_dict[svm_fix.vm_node_ip]
                ff_fix = svm_fix
                # when fat flow configured on both left and right svmi
                if svc_chain['ff_on_si_vmis']['left'] and svc_chain['ff_on_si_vmis']['right']:
                    fat_flow_count = 2 * fat_flow_count # for left svmi, and right svmi
            if (ff_fix.vm_node_ip != fix.vm_node_ip):
                ff_compute_fix = dst_compute_fix # default compute fix is dst_compute_fix
                # In the case when svm and dst vm are on different node
                # the verification should happen on the svm's compute node, not dest's compute node
                # i.e. src and dst on the same compute node, but svm on different compute node.
                if svm_fix and fix.vm_node_ip == dst_vm_fix.vm_node_ip:
                # when both src and dst VMs are on the same compute, but svm on different compute
                    ff_compute_fix = svm_compute_fix
                    fat_flow_count = 2
                        # when svm is on different compute, 2 pairs of fat flows to be created
                self.verify_fat_flow_on_compute(ff_compute_fix,
                    src_ip, dst_ip,
                    dest_port, proto, vrf_id_dst, fat_flow_count=fat_flow_count)

                #Source compute should never have Fat flow for inter node traffic
                fat_flow_count=0
                self.verify_fat_flow_on_compute(src_compute_fix,
                    src_ip, dst_ip,
                    dest_port, proto, vrf_id_src, fat_flow_count=fat_flow_count)
            #For intra-Node traffic
            else:
                if proto in  ['icmp', 'icmp6'] and svm_fix:
                    fat_flow_count = 2 # one for left vmi, other for right vmi, src and svm both on same node
                    unidirectional_traffic = False
                if unidirectional_traffic:
                    #Source compute should not have Fat flow for unidirectional traffic
                    fat_flow_count = 0
                    if icmp_error or proto in ['icmp', 'icmp6']:  fat_flow_count=1
                    if svm_fix:
                        fat_flow_count = 1 # One fat flow expected for right vmi
                        # when AggrSrc( + Ignore Dst) with src prefix is configured on right vmi
                        # fat flow should not get created if AggrSrc with dest prefix is configured
                    self.verify_fat_flow_on_compute(src_compute_fix,
                        src_ip,
                        dst_ip, dest_port, proto,
                        vrf_id_src, fat_flow_count=fat_flow_count)

                else:
                    ##Source compute should have Fat flow for bi-directional traffic
                    self.verify_fat_flow_on_compute(src_compute_fix,
                        src_ip,
                        dst_ip, dest_port, proto,
                        vrf_id_src, fat_flow_count=fat_flow_count)

        return True

    def verify_fat_flow_with_traffic(self, sender_vm_fix_list, dst_vm_fix,
            proto, dest_port=None, traffic=True,
            expected_flow_count=1, fat_flow_count=1, af=None,
            fat_flow_config=None, sport_list=None, dport_list=None,
            expected_src_prefix_list=None, expected_dst_prefix_list=None,
            unidirectional_traffic=True, traffic_recvr=False,
            ignore_address=None, icmp_error=False, svm_fix=None, svc_chain=None, scale=1):
        '''
        Common method to be used for Fat and non-Fat flow verifications:
            1. Use 2 different source ports from each sender VM to send traffic
            2. verify non-Fat flow on sender computes
            3. verify Fat flow on destination compute
            4. if sender and destination VMs are on same node, no Fat flow will be created
            Optional Inputs:
                traffic: True if has to send the traffic
                expected_flow_count: expected non-Fat flow count
                fat_flow_count: expected Fat flow count
        '''
        receiver = True
        af = af or self.inputs.get_af()
        #Use 2 different source ports for each sender VM
        if proto == 'tcp':
            unidirectional_traffic = False
        sport_list = sport_list or [10000, 10001]
        sport_list = [10000]
        if af == 'v6':
            sport_list = [20000, 20001]
        dport_list = dport_list or [dest_port]
        fat_flow_dport = dest_port or 0
        dst_compute_fix = self.compute_fixtures_dict[dst_vm_fix.vm_node_ip]
        if fat_flow_config:
            #mask both source and dest port in the flow
            if fat_flow_config['port'] == 0:
                fat_flow_dport = 0
        if proto == 'icmp':
            traffic = False
            for fix in sender_vm_fix_list:
                for i in range(scale):
                    ping_h = self.start_ping(fix, dst_ip=dst_vm_fix.get_vm_ips(af=af)[0])
                dport_list = [0]
                if af == 'v6':
                    dport_list = [129]  # For icmp6 port=129
                    proto = 'icmp6'
                for sp in sport_list: # random port for icmp, so pass None
                    index_of_sp = sport_list.index(sp)
                    sport_list[index_of_sp] = 0
        #Start the traffic from each of the VM in sender_vm_fix_list to dst_vm_fix
        if traffic_recvr:
            traffic = False
        if traffic:
            for fix in sender_vm_fix_list:
                for sport in sport_list:
                    for dport in dport_list:
                        #if af == 'v6':
                        if icmp_error:
                            receiver = False
                        assert self.send_nc_traffic(fix, dst_vm_fix, sport,
                            dport, proto, ip=dst_vm_fix.get_vm_ips(af=af)[0], receiver=receiver)
        if traffic_recvr: # For Intra node only, only fat flow expected on Intra compute node
            for fix in sender_vm_fix_list:
                for sport in sport_list:
                    for dport in dport_list:
                        #if af == 'v6':
                        assert self.send_nc_traffic(dst_vm_fix, fix, dport,
                            sport, proto, ip=fix.get_vm_ips(af=af)[0])
        #Verify the non-Fat flows on sender computes for each sender/receiver VMs and ports
        dest_ip=dst_vm_fix.get_vm_ips(af=af)[0]
        #dest_port = dport
        for fix in sender_vm_fix_list:
            source_ip=fix.get_vm_ips(af=af)[0]
            for sport in sport_list:
                source_port = sport
                if source_port == 0:
                    source_port = None
                for dport in dport_list:
                    dest_port = dport
                    compute_fix = self.compute_fixtures_dict[fix.vm_node_ip]
                    vrf_id = compute_fix.get_vrf_id(fix.vn_fq_names[0])
                    if svm_fix:
                        vrf_id = None # vrf_id not applicable for SVMI
                        if dst_vm_fix.vm_node_ip == fix.vm_node_ip: # when src vm and dest vm are on the same node
                        # and svc_chain enabled, the node to have multiple normal flows for each vrf.
                            expected_flow_count = 2
                    (ff_count, rf_count) = compute_fix.get_flow_count(
                                        source_ip=source_ip,
                                        dest_ip=dest_ip,
                                        source_port=source_port,
                                        dest_port=dest_port,
                                        proto=proto,
                                        vrf_id=vrf_id)
                    if proto == 'tcp' or traffic_recvr:
                        expected_flow_count = 0
                    assert ff_count == expected_flow_count, ('Flows count mismatch on '
                        'sender compute, got:%s, expected:%s' % (
                        ff_count, expected_flow_count))
                    assert rf_count == expected_flow_count, ('Flows count mismatch on '
                        'sender compute, got:%s, expected:%s' % (
                        rf_count, expected_flow_count))

                    #For the case when sender and receiver are on different nodes
                    if dst_vm_fix.vm_node_ip != fix.vm_node_ip:
                        #Flow with source and dest port should not be created on dest node, if Fat flow is expected
                        if fat_flow_count and not svm_fix:
                            expected_count_dst = 0
                        else:
                            expected_count_dst = expected_flow_count
                        if proto == 'tcp': # Due to eviction
                            expected_flow_count = 0
                        vrf_id = dst_compute_fix.get_vrf_id(dst_vm_fix.vn_fq_names[0])
                        if svm_fix:
                            vrf_id = None # Ignore vrf_id if svm_fix is set
                            if proto == 'icmp' : # Normal flow expected when dst is on different CN
                                sport=None
                                dport=None
                        (ff_count, rf_count) = dst_compute_fix.get_flow_count(
                                        source_ip=fix.get_vm_ips(af=af)[0],
                                        dest_ip=dst_vm_fix.get_vm_ips(af=af)[0],
                                        source_port=sport,
                                        dest_port=dport,
                                        proto=proto,
                                        vrf_id=vrf_id)
                        assert ff_count == expected_count_dst, ('Flows count '
                            'mismatch on dest compute, got:%s, expected:%s' % (
                            ff_count, expected_count_dst))
                        assert rf_count == expected_count_dst, ('Flows count '
                            'mismatch on dest compute, got:%s, expected:%s' % (
                            rf_count, expected_count_dst))
        #FAT flow verification
        if svm_fix: # For SVM, ff verification should happen on the CN where SVM is launched
            verify_for_left_vmi=True
            verify_for_right_vmi=True
        assert self.verify_fat_flow(sender_vm_fix_list, dst_vm_fix,
                               proto, fat_flow_dport, fat_flow_count, af=af,
                               expected_src_prefix_list=expected_src_prefix_list,
                               expected_dst_prefix_list=expected_dst_prefix_list,
                               unidirectional_traffic=unidirectional_traffic,
                               ignore_address=ignore_address, icmp_error=icmp_error,
                               svm_fix=svm_fix, svc_chain=svc_chain)
        self.logger.info("Fat flow verification passed for "
            "protocol %s and port %s" % (proto, fat_flow_dport))
        return True
    # end verify_fat_flow_with_traffic

    def verify_fat_flow_with_ignore_addrs(self, sender_vm_fix_list,
            dst_vm_fix_list, fat_flow_config, traffic=True,
            fat_flow_count=1, af=None, icmp_error=False, fat_config_on='server',
            sport=10000, dport=53):
        '''
        Common method to be used for Fat flow verification with ignore addrs
        '''
        af = af or self.inputs.get_af()
        #Use 2 different source ports for each sender VM
        port1 = dport
        port2 = sport
        dport_list = [port1, port1+1]
        sport_list = [port2, port2+1]
        fat_flow_dport = dport_list[0]
        fat_flow_sport = 0
        fat_flow_sip = None
        fat_flow_dip = None
        proto = fat_flow_config['proto']
        ignore_address = fat_flow_config.get('ignore_address')

        if fat_flow_config['port'] == 0:
            #mask both source and dest port in the flow
            fat_flow_dport = 0
            fat_flow_sport = 0
        else:
            if fat_config_on == 'server':
                dport_list = [port1]
                #mask only source port
                fat_flow_sport = 0
                fat_flow_dport = dport_list[0]
            elif fat_config_on == 'client':
                sport_list = [port2]
                #mask only dst port
                fat_flow_dport = 0
                fat_flow_sport = sport_list[0]
            else:
                fat_flow_sport = 0
                fat_flow_dport = 0
                dport_list = [port1]
                fat_flow_dport = dport_list[0]

        #mask source IP
        if ignore_address == 'source':
            if fat_config_on == 'server':
                #use 1 client and multiple server VMs
                sender_vm_fix_list = [sender_vm_fix_list[0]]
                fat_flow_dip = '0.0.0.0' if af == 'v4' else '::'
                fat_flow_sip = sender_vm_fix_list[0].get_vm_ips(af=af)[0]
            elif fat_config_on == 'client' or fat_config_on == 'all':
                #use multiple clients and 1 server VM
                dst_vm_fix_list = [dst_vm_fix_list[0]]
                fat_flow_sip = '0.0.0.0' if af == 'v4' else '::'
                fat_flow_dip = dst_vm_fix_list[0].get_vm_ips(af=af)[0]
        #mask dest IP
        elif ignore_address == 'destination':
            if fat_config_on == 'server':
                #use multiple clients and 1 server VM
                dst_vm_fix_list = [dst_vm_fix_list[0]]
                fat_flow_sip = '0.0.0.0' if af == 'v4' else '::'
                fat_flow_dip = dst_vm_fix_list[0].get_vm_ips(af=af)[0]
                #Disable rpf
                self.vnc_lib_fixture.set_rpf_mode(
                    dst_vm_fix_list[0].vn_fq_names[0], 'disable')
            elif fat_config_on == 'client' or fat_config_on == 'all':
                #use 1 client and multiple server VMs
                sender_vm_fix_list = [sender_vm_fix_list[0]]
                fat_flow_dip = '0.0.0.0' if af == 'v4' else '::'
                fat_flow_sip = sender_vm_fix_list[0].get_vm_ips(af=af)[0]
                #Disable rpf
                self.vnc_lib_fixture.set_rpf_mode(
                    sender_vm_fix_list[0].vn_fq_names[0], 'disable')
        elif ignore_address == None:
            if fat_config_on == 'server':
                #use multiple clients and 1 server VM
                dst_vm_fix_list = [dst_vm_fix_list[0]]
            elif fat_config_on == 'client' or fat_config_on == 'all':
                #use 1 client and multiple server VMs
                sender_vm_fix_list = [sender_vm_fix_list[0]]

        #For intra-node traffic
        if dst_vm_fix_list[0].vm_node_ip == sender_vm_fix_list[0].vm_node_ip:
            compute_fix = self.compute_fixtures_dict[sender_vm_fix_list[0].vm_node_ip]
            vrf_id = None
        #For inter-node traffic
        else:
            if fat_config_on == 'server':
                compute_fix = self.compute_fixtures_dict[dst_vm_fix_list[0].vm_node_ip]
                vrf_id = compute_fix.get_vrf_id(dst_vm_fix_list[0].vn_fq_names[0])
            elif fat_config_on == 'client':
                compute_fix = self.compute_fixtures_dict[sender_vm_fix_list[0].vm_node_ip]
                vrf_id = compute_fix.get_vrf_id(sender_vm_fix_list[0].vn_fq_names[0])

        #Start the traffic
        if traffic:
            for svm in sender_vm_fix_list:
                for dvm in dst_vm_fix_list:
                    for sport in sport_list:
                        for dport in dport_list:
                            assert self.send_nc_traffic(svm, dvm, sport,
                                dport, proto, ip=dvm.get_vm_ips(af=af)[0],
                                receiver=(not icmp_error))

        #FAT flow verification
        if ignore_address == 'destination':
            self.verify_fat_flow_on_compute(compute_fix,
                fat_flow_sip, fat_flow_dip,
                fat_flow_dport, proto,
                vrf_id, fat_flow_count=fat_flow_count,
                sport=fat_flow_sport)
            if fat_config_on == 'server':
                #Enable back rpf
                self.vnc_lib_fixture.set_rpf_mode(
                    dst_vm_fix_list[0].vn_fq_names[0], 'enable')
            elif fat_config_on == 'client' or fat_config_on == 'all':
                #Enable back rpf
                self.vnc_lib_fixture.set_rpf_mode(
                    sender_vm_fix_list[0].vn_fq_names[0], 'enable')
        elif ignore_address == 'source':
            self.verify_fat_flow_on_compute(compute_fix,
                fat_flow_sip, fat_flow_dip,
                fat_flow_dport, proto,
                vrf_id, fat_flow_count=2*fat_flow_count,
                sport=fat_flow_sport)
        elif ignore_address == None and fat_flow_config['port'] == 0:
            for svm in sender_vm_fix_list:
                for dvm in dst_vm_fix_list:
                    self.verify_fat_flow_on_compute(compute_fix,
                        svm.get_vm_ips(af=af)[0],
                        dvm.get_vm_ips(af=af)[0], fat_flow_dport, proto,
                        vrf_id, fat_flow_count=fat_flow_count,
                        sport=fat_flow_sport)

        #Verify NO hold flows
        action = 'HOLD'
        self.verify_flow_action(compute_fix, action,
            src_vrf=vrf_id, exp=False)
        return True

    def get_vrouter_route(self, prefix, vn_fixture=None, vrf_id=None,
                          inspect_h=None, node_ip=None):
        ''' prefix is in the form of ip/mask
        '''
        if not (vn_fixture or vrf_id):
            self.logger.debug('get_vrouter_route required atleast one of '
                              'VN Fixture or vrf id')
            return None
        if not (inspect_h or node_ip):
            self.logger.debug('get_vrouter_route needs one of inspect_h '
                              ' or node_ip')
            return None

        #vrf_id = vrf_id or vn_fixture.get_vrf_id(node_ip, refresh=True)
        inspect_h = inspect_h or self.agent_inspect_h[node_ip]
        vrf_id = vrf_id or inspect_h.get_vna_vrf_id(vn_fixture.vn_fq_name)[0]
        (prefix_ip, mask) = prefix.split('/')
        route = inspect_h.get_vrouter_route_table(vrf_id, prefix=prefix_ip,
                                                  prefix_len=mask,
                                                  get_nh_details=True)
        if len(route) > 0:
            return route[0]
    # end get_vrouter_route

    def get_vrouter_route_table(self, node_ip, vn_fixture=None, vrf_id=None):
        if not (vn_fixture or vrf_id):
            self.logger.debug('get_vrouter_route_table required atleast one of'
                              ' VN Fixture or vrf id')
            return None
        if not vrf_id:
            vrf_id = vn_fixture.get_vrf_id(node_ip)
        inspect_h = self.agent_inspect_h[node_ip]
        routes = inspect_h.get_vrouter_route_table(vrf_id)
        return routes
    # end get_vrouter_route_table

    def get_vrouter_route_table_size(self, *args, **kwargs):
        routes = self.get_vrouter_route_table(*args, **kwargs)
        self.logger.debug('Route table size : %s' % (len(routes)))
        return len(routes)
    # end get_vrouter_route_table_size

    @retry(delay=1, tries=5)
    def validate_prefix_is_of_vm_in_vrouter(self, inspect_h, prefix,
                                            vm_fixture, vn_fixture=None):
        '''
        '''
        vrf_id = None
        if not vn_fixture:
            vrf_id = inspect_h.get_vna_vrf_id(vm_fixture.vn_fq_names[0])[0]
        route = self.get_vrouter_route(prefix,
                                       vn_fixture=vn_fixture, vrf_id=vrf_id, inspect_h=inspect_h)
        if not route:
            self.logger.debug('No route seen in vrouter for %s' % (prefix))
            return False
        return self.validate_route_is_of_vm_in_vrouter(
            inspect_h,
            route,
            vm_fixture,
            vn_fixture)
    # end validate_prefix_is_of_vm_in_vrouter

    @retry(delay=3, tries=3)
    def validate_route_is_of_vm_in_vrouter(self, inspect_h, route, vm_fixture,
                                           vn_fixture=None):
        '''Validation is in vrouter
            Recommended to do verify_on_setup() on vm_fixture before calling
            this method
        '''
        result = False
        vm_intf = None
        # Get the VM tap interface to be validated
        vm_tap_intfs = vm_fixture.get_tap_intf_of_vm()
        if not vn_fixture:
            vm_intf = vm_fixture.get_tap_intf_of_vm()[0]
        else:
            for vm_tap_intf in vm_tap_intfs:
                if vm_tap_intf['vn_name'] == vn_fixture.vn_fq_name:
                    vm_intf = vm_tap_intf.copy()
            if not vm_intf:
                self.logger.debug('VM %s did not have any intf in VN %s' % (
                    vm_fixture.vm_name, vn_fixture.vn_name))
                return False

        if not (vm_intf and vm_fixture.vm_node_ip):
            self.logger.warn('Cannot check routes without enough VM details')
            return False

        tunnel_ip = self.inputs.host_data[vm_fixture.get_host_of_vm()][
            'host_control_ip']
        result = validate_route_in_vrouter(route, inspect_h, vm_intf['name'],
                                           tunnel_ip, vm_intf['label'], self.logger)
        return result
    # end validate_route_is_of_vm_in_vrouter

    def count_nh_label_in_route_table(self, node_ip, vn_fixture, nh_id, label):
        '''
        Count the number of times nh_id,label is a nh in vrouter's route table
        '''
        route_table = self.get_vrouter_route_table(node_ip,
                                                   vn_fixture=vn_fixture)
        count = 0
        for rt in route_table:
            if rt['nh_id'] == str(nh_id) and rt['label'] == str(label):
                count += 1
        return count
    # end count_nh_label_in_route_table

    @retry(delay=2, tries=5)
    def validate_discard_route(self, prefix, vn_fixture, node_ip):
        '''
        Validate that route for prefix in vrf of a VN is  pointing to a discard
        route on compute node node_ip
        '''
        route = self.get_vrouter_route(prefix,
                                       vn_fixture=vn_fixture,
                                       node_ip=node_ip)
        if not route:
            self.logger.warn('No vrouter route for prefix %s found' % (prefix))
            return False
        if not (route['label'] == '0' and route['nh_id'] == '1'):
            self.logger.warn('Discard route not set for prefix %s' % (prefix))
            self.logger.debug('Route seen is %s' % (route))
            return False
        self.logger.info('Route for prefix %s is validated to be discard'
                         ' route' %(prefix))
        return True
    # end validate_discard_route

    def is_flow_pointing_to_vm(self, flow_entry, compute_fixture, vm_fixture,
                               vn_fixture=None, vm_ip=None):
        '''
        flow_entry : Instance of FlowEntry class
        vm_ip      : If there is more than one ip on the VM

        Returns True if nh is that of the vm_fixture
        '''
        vrf_id = flow_entry.vrf_id
        flow_dest_ip = '%s/32' % (flow_entry.dest_ip)
        if not vn_fixture:
            tap_intf = list(vm_fixture.tap_intf.values())[0]['name']
            vn_fq_name = vm_fixture.vn_fq_names[0]
        else:
            tap_intf = vm_fixture.tap_intf[vn_fixture.vn_fq_name]['name']
            vn_fq_name = vn_fixture.vn_fq_name

        if not vm_ip:
            vm_ip = vm_fixture.vm_ip
        agent_inspect_h = compute_fixture.agent_inspect_h
        route = self.get_vrouter_route(flow_dest_ip,
                                       vrf_id=vrf_id,
                                       inspect_h=agent_inspect_h)
        if not route:
            self.logger.warn('Route for IP %s in vrf %s not found' % (
                flow_dest_ip, vrf_id))
            return False
        result = self.validate_route_is_of_vm_in_vrouter(agent_inspect_h,
                                                route,
                                                vm_fixture)

        if not result:
            self.logger.error('Route %s as seen from flow is not that of VM '
                ' %s' % (route, vm_fixture.vm_ip))
            return False

        self.logger.info('On %s, flow is pointing to the VM %s as expected' % (
                          compute_fixture.ip, vm_ip))
        return True
    # end is_flow_pointing_to_vm
