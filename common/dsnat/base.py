import test_v1, time
from vn_test import VNFixture
from vm_test import VMFixture
from policy_test import PolicyFixture
from floating_ip import FloatingIPFixture
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from tcutils.util import *
from contrailapi import ContrailVncApi
from common.base import GenericTestBase
from common.policy.config import ConfigPolicy, AttachPolicyFixture
from common.neutron.base import BaseNeutronTest
from vnc_api.vnc_api import *
from tcutils.traffic_utils.iperf3_traffic import Iperf3
from collections import OrderedDict
from compute_node_test import ComputeNodeFixture

class IperfToHost(Iperf3):
    '''
       Methods to run the iperf tests between the VM and the server
    '''
    def __init__(self, client_vm_fixture, server_vm_fixture, *args, **kwargs):
        super(IperfToHost, self).__init__(client_vm_fixture,
            server_vm_fixture, *args, **kwargs)
        self.server_vm_fixture.vm_ip = self.server_vm_fixture.ip
        self.server_vm_fixture.run_cmd_on_vm = self.run_cmd_on_server
        output = self.run_cmd_on_server(cmds=['yum -y install iperf3'],
            as_sudo=True, pty=False)
        print output

    def run_cmd_on_server(self, cmds=[], as_sudo=False, timeout=30, pty=None,
                      as_daemon=False, raw=False, warn_only=True, pidfile=None):
        self.logger.info("Excecuting cmds, %s, on server %s" %(cmds,
            self.server_vm_fixture.ip))
        if not pidfile and self.server_pid_file:
            pidfile = self.server_pid_file
        if not pty:
            pty = not as_daemon
        for cmd in cmds:
            output = run_cmd_on_server(cmd, self.server_vm_fixture.ip, 
                self.server_vm_fixture.username, 
                self.server_vm_fixture.password,
                as_daemon=as_daemon, pty=pty,
                as_sudo=as_sudo, pidfile=pidfile)
            self.logger.debug("command output is %s" %output)

    def stop_iperf_on_server(self):
        cmds = []
        cmds.append("kill -9 $(cat " + self.server_pid_file + ")")
        cmds.append("for ps in $(pgrep iperf); do kill -9 $ps; done")
        for cmd in cmds:
            output = run_cmd_on_server(cmd, self.server_vm_fixture.ip,
                self.server_vm_fixture.username,
                self.server_vm_fixture.password, as_sudo=True)
            self.logger.debug("command output is %s" %output)

class BaseDSNAT(BaseNeutronTest):

    @classmethod
    def setUpClass(cls):
        super(BaseDSNAT, cls).setUpClass()
        cls.project_name = cls.inputs.project_name
        cls.quantum_h= cls.connections.quantum_h
        cls.orch = cls.connections.orch
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseDSNAT, cls).tearDownClass()
    # end tearDownClass

    def is_test_applicable(self):
        self.logger.info("Executing the function %s", self._testMethodName)
        basic_tc = ['test_dsnat_global_config', 'test_dsnat_basic',\
                 'test_dsnat_with_floating_ip', 'test_dsnat_through_floatingvn']
        if self._testMethodName not in basic_tc:
            if len(self.inputs.compute_ips) < 2:
                return (False, 'Required minimum two compute nodes')
        return (True, None)

    def define_port_translation_pool(self, **kwargs):
        protocol = kwargs.get('protocol', None)
        port_count = kwargs.get('port_count', '')
        start_port = kwargs.get('start_port', 0)
        end_port = kwargs.get('end_port', 0)
        pp = self.vnc_h.port_translation_pool(protocol, port_count, start_port, end_port)
        return pp
        
    def configure_port_translation_pool(self, **kwargs):
        pp = self.define_port_translation_pool(**kwargs)
        self.vnc_h.set_port_translation_pool([pp])
        return pp

    def add_port_translation_pool(self, **kwargs):
        pp = self.define_port_translation_pool(**kwargs)
        self.vnc_h.insert_port_translation_pool(pp)
        return pp

    def delete_port_translation_pool(self, **kwargs):
        pp = self.define_port_translation_pool(**kwargs)
        assert self.vnc_h.delete_port_translation_pool(pp), (
            "failed to delete pool %s", pp)
        return pp

    def create_vn_enable_fabric_snat(self):
        '''
           create a virtual network , enable SNAT and verify routing instance for SNAT flag
           return the VN object
        '''
        vn_name = get_random_name('dsnat_vn')
        vn_subnets = [get_random_cidr()]
        vn_fix = self.create_vn(vn_name, vn_subnets)
        assert vn_fix.verify_on_setup()
        self.vnc_h.set_fabric_snat(vn_fix.uuid)
        assert self.verify_routing_instance_snat(vn_fix)
        return vn_fix

    def set_vn_forwarding_mode(self, vn_fix, forwarding_mode="default"):
        vn_fix = self.vnc_h.virtual_network_read(id=vn_fix.uuid)
        vni_obj_properties = vn_fix.get_virtual_network_properties(
            ) or VirtualNetworkType()
        vni_obj_properties.set_forwarding_mode(forwarding_mode)
        vn_fix.set_virtual_network_properties(vni_obj_properties)
        self.vnc_h.virtual_network_update(vn_fix)

    def verify_port_translation_pool(self, expected_pp=None):
        actual_pps = self.vnc_h.get_port_translation_pools()
        if expected_pp == actual_pps:
            self.logger.info("Port Translation pool is empty as expected")
            return True
        else:
            for actual_pp in actual_pps.port_translation_pool if actual_pps else []:
                self.logger.info('Verifies that configured port translation pool %s,\
                    is same as actual %s' %(expected_pp, actual_pp))
                return expected_pp == actual_pp
        return False

    def get_ip_fabric_vn_fixture(self):
        fabric_vn =  self.vnc_h.virtual_network_read(fq_name=['default-domain', 'default-project', 'ip-fabric'])
        fabric_vn.vn_fq_name = fabric_vn.get_fq_name_str()
        fabric_vn.vn_name = fabric_vn.name
        fabric_vn.policy_objs = []
        return fabric_vn

    def verify_routing_instance_snat(self, vn_fix):
        '''
            Verify the routing instance fabric SNAT flag is same as its virtual network flag
        '''       
        for ri in vn_fix.api_s_routing_instance['routing_instances']:
            ri_obj = self.vnc_h.routing_instance_read(id=ri['routing-instance']['uuid'])
            if ri_obj.routing_instance_fabric_snat != self.vnc_h.get_fabric_snat(vn_fix.uuid):
                self.logger.error("Fabric SNAT has not been set in the routing instance ")
                return False
        return True
            
    def verify_fabric_ip_as_floating_ip(self, vm_fix, vn_fq_name):
        '''
            Function to verify the fabric IP associated to the VMI of the VM , with SNAT enabled
        '''
        vm_fix.refresh_agent_vmi_objects()
        for fip in vm_fix.tap_intf[vn_fq_name]['fip_list']:
            if fip['ip_addr'] == vm_fix.vm_node_ip:
                return True
        self.logger.error("With SNAT enabled for the VN %s,\
            fabric ip is not assigned as FIP ip to the VMI", vn_fq_name)
        return False

    def create_floatingip(self, floating_vn):
        fip_pool_name = get_random_name('dsnat_fip')
        fip_fixture = self.useFixture(
            FloatingIPFixture(
                project_name=self.inputs.project_name,
                inputs=self.inputs,
                connections=self.connections,
                pool_name=fip_pool_name,
                vn_id=floating_vn.vn_id))
        assert fip_fixture.verify_on_setup()
        return fip_fixture

    def config_policy(self, policy_name, rules):
        """Configures policy."""
        use_vnc_api = getattr(self, 'use_vnc_api', None)
        # create policy
        policy_fix = self.useFixture(PolicyFixture(
            policy_name=policy_name, rules_list=rules,
            inputs=self.inputs, connections=self.connections,
            api=use_vnc_api))
        return policy_fix

    def attach_policy_to_vn(self, policy_fix, vn_fix, policy_type=None):
        policy_attach_fix = self.useFixture(AttachPolicyFixture(
            self.inputs, self.connections, vn_fix, policy_fix, policy_type))
        return policy_attach_fix

    def detach_policy_from_vn(self, policy_fix, vn_fix):
        vn_obj = self.vnc_h.virtual_network_read(id=vn_fix.uuid)
        policy_obj = self.vnc_h.network_policy_read(id=policy_fix.get_id())
        vn_obj.del_network_policy(policy_obj)
        self.vnc_h.virtual_network_update(vn_obj)

    def create_policy_attach_to_vn(self, vn_fixture, rules):
        policy_name = get_random_name('test-dsnat')
        policy_fix = self.config_policy(policy_name, rules)
        return self.attach_policy_to_vn(policy_fix, vn_fixture)

    def create_interface_route_table(self, prefixes):
        intf_route_table_obj = self.vnc_h.create_route_table(
            prefixes = prefixes,
            parent_obj=self.project.project_obj)
        return intf_route_table_obj

    def run_iperf_between_vm_host(self, vm_fixture, server_ip, **kwargs):
        params = OrderedDict()
        params["port"] = kwargs.get('port', 4203)
        params["udp"] = kwargs.get('udp', True)
        if params["udp"] == True:
            params["length"] = kwargs.get('length', 65507)
        else:
            params["length"] = kwargs.get('length', 1048576)
        params["time"] = kwargs.get('time', 10)
        server_fixture = self.useFixture(ComputeNodeFixture(
                self.connections, server_ip))
        if not self.iperf:
            self.iperf = IperfToHost(vm_fixture, server_fixture, **params)
        self.iperf.stop_iperf_on_server()
        self.iperf.start(wait=False)
        time.sleep(3)

    def get_nat_port_used_for_flow(self, compute_node_ip, proto, port, container='agent'):
        server_fixture = self.useFixture(ComputeNodeFixture(
                self.connections, compute_node_ip))
        flow_entry = server_fixture.get_flow_entry(dest_ip=compute_node_ip,
            proto=proto, source_port = port,all_flows=True)
        nat_port = []
        for flow in flow_entry:
            nat_port.append(int(flow[0].dest_port))
        return nat_port
      
    @retry(delay=5, tries=5)
    def verify_flow_with_port(self, client_vm_fix, server_ip, port_range, **traffic):
        self.run_iperf_between_vm_host(client_vm_fix, server_ip, **traffic)
        if traffic['udp']:
            proto = '17'
        else:
            proto = '6'
        nat_port_used = self.get_nat_port_used_for_flow(client_vm_fix.vm_node_ip, proto, traffic['port'])
        self.iperf.stop_iperf_on_server()
        self.logger.info("Nat port being used for the flow is %s" %nat_port_used)
        if not nat_port_used or not [port for port in nat_port_used if port in port_range]:
            return False
        return True
