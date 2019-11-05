from builtins import str
from builtins import range
import test_v1, time
from vn_test import VNFixture
from vm_test import VMFixture
from policy_test import PolicyFixture
from floating_ip import FloatingIPFixture
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from tcutils.util import *
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
    def __init__(self, client_vm_fixture, server_vm_fixture, server_data_ip, *args, **kwargs):
        super(IperfToHost, self).__init__(client_vm_fixture,
            server_vm_fixture, *args, **kwargs)
        self.server_vm_fixture.vm_ip = server_data_ip
        self.server_vm_fixture.run_cmd_on_vm = self.run_cmds_on_server

    def run_cmds_on_server(self, cmds=[], as_sudo=False, timeout=30, pty=None,
                      as_daemon=False, raw=False, warn_only=True, pidfile=None):
        self.logger.info("Excecuting cmds, %s, on server %s" %(cmds,
            self.server_vm_fixture.ip))
        if not pidfile and self.server_pid_file:
            pidfile = self.server_pid_file
        if not pty:
            pty = not as_daemon
        output=[]
        for cmd in cmds:
            output.append(run_cmd_on_server(cmd, self.server_vm_fixture.ip,
                self.server_vm_fixture.username,
                self.server_vm_fixture.password,
                as_daemon=as_daemon, pty=pty,
                as_sudo=as_sudo, pidfile=pidfile))
        self.logger.debug("command output is %s" %output)
        return output

    def stop_iperf_on_server(self):
        cmds = []
        cmds.append("kill -9 $(cat " + self.server_pid_file + ")")
        cmds.append("for ps in $(pgrep iperf); do kill -9 $ps; done")
        for cmd in cmds:
            output = run_cmd_on_server(cmd, self.server_vm_fixture.ip,
                self.server_vm_fixture.username,
                self.server_vm_fixture.password, as_sudo=True)
            self.logger.debug("command output is %s" %output)

class BaseDSNAT(BaseNeutronTest, ConfigPolicy):

    @classmethod
    def setUpClass(cls):
        super(BaseDSNAT, cls).setUpClass()
        cls.project_name = cls.inputs.project_name
        cls.quantum_h= cls.connections.quantum_h
        cls.orch = cls.connections.orch
        cls.nova_h = cls.connections.nova_h
        cls.vnc_h = cls.orch.vnc_h
        cls.vnc_lib= cls.connections.vnc_lib
        cls.agent_inspect= cls.connections.agent_inspect
        cls.cn_inspect= cls.connections.cn_inspect
        cls.analytics_obj=cls.connections.analytics_obj
    #end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseDSNAT, cls).tearDownClass()
    # end tearDownClass

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
        self.vnc_h.delete_port_translation_pool(pp)
        return pp

    def create_vn_enable_fabric_snat(self):
        '''
           create a virtual network , enable SNAT and verify routing instance for SNAT flag
           return the VN object
        '''
        vn_name = get_random_name('dsnat_vn')
        vn_subnets = [get_random_cidr()]
        vn_fix = self.create_vn(vn_name, vn_subnets)
        self.vnc_h.set_fabric_snat(vn_fix.uuid)
        assert vn_fix.verify_routing_instance_snat()
        return vn_fix

    def set_vn_forwarding_mode(self, vn_fix, forwarding_mode="default"):
        vn_fix = self.vnc_h.virtual_network_read(id=vn_fix.uuid)
        vni_obj_properties = vn_fix.get_virtual_network_properties(
            ) or VirtualNetworkType()
        vni_obj_properties.set_forwarding_mode(forwarding_mode)
        vn_fix.set_virtual_network_properties(vni_obj_properties)
        self.vnc_h.virtual_network_update(vn_fix)

    @retry(delay=5, tries=5)
    def verify_port_allocation_in_agent(self, pp):
        '''
            function to verify the configured port pool
            has been allocated in the agent
        '''
        for compute in self.inputs.compute_ips:
            self.logger.info("Verify port pools allocated on compute node, %s" %compute)
            inspect_h = self.connections.agent_inspect[compute]
            port_config = inspect_h.get_vna_snat_port_config()
            configured_port = defaultdict()
            for port_pool in pp:
                protocol = '17' if port_pool.get_protocol() == 'udp' else '6'
                if protocol not in list(configured_port.keys()):
                    configured_port[protocol] = defaultdict()
                if 'port_list' not in list(configured_port[protocol].keys()):
                    configured_port[protocol]['port_list'] = []
                if port_pool.port_range and port_pool.port_range.start_port > 0:
                    start_port = port_pool.port_range.start_port
                    end_port = port_pool.port_range.end_port
                    configured_port[protocol]['port_list'] +=\
                      [str(port) for port in range(start_port, end_port+1)]
                if port_pool.port_count:
                    configured_port[protocol]['port_count'] = port_pool.port_count
            for protocol in list(configured_port.keys()):
                if ('port_list' in list(configured_port[protocol].keys()) and \
                    configured_port[protocol]['port_list'] != port_config[protocol]['bound_port_list']) or \
                    ('port_count' in list(configured_port[protocol].keys()) and \
                    int(configured_port[protocol]['port_count']) != len(port_config[protocol]['bound_port_list'])):
                    self.logger.error('Configured port pool isnt same as allocated ports, %s, on compute node, %s'
                        %(port_config[protocol]['bound_port_list'], compute))
                    return False
        self.logger.info('configured port pools got allocated on all the agent')
        return True

    def get_ip_fabric_vn_fixture(self):
        fabric_vn =  self.vnc_h.virtual_network_read(fq_name=['default-domain', 'default-project', 'ip-fabric'])
        fabric_vn = VNFixture(self.connections, uuid=fabric_vn.uuid)
        fabric_vn.read()
        return fabric_vn

    def detach_policy_from_vn(self, policy_fix, vn_fix):
        vn_obj = self.vnc_h.virtual_network_read(id=vn_fix.uuid)
        policy_obj = self.vnc_h.network_policy_read(id=policy_fix.get_id())
        vn_obj.del_network_policy(policy_obj)
        self.vnc_h.virtual_network_update(vn_obj)

    def create_policy_attach_to_vn(self, vn_fixture, rules):
        policy_name = get_random_name('test-dsnat')
        policy_fix = self.config_policy(policy_name, rules)
        return self.attach_policy_to_vn(policy_fix, vn_fixture)

    def run_iperf_between_vm_host(self, vm_fixture, server_ip, server_data_ip, **kwargs):
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
            self.iperf = IperfToHost(vm_fixture, server_fixture, server_data_ip, **params)
            self.addCleanup(self.iperf.stop_iperf_on_server)
        self.iperf.stop_iperf_on_server()
        self.iperf.start(wait=False)
        time.sleep(3)

    def get_nat_port_used_for_flow(self, vm_fix, proto, port, container='agent'):
        server_fixture = self.useFixture(ComputeNodeFixture(
                self.connections, vm_fix.vm_node_ip))
        flow_entry = server_fixture.get_flow_entry(dest_ip=vm_fix.vm_node_data_ip,
            proto=proto, source_port = port,all_flows=True)
        nat_port = []
        for flow in flow_entry:
            nat_port.append(int(flow[0].dest_port))
        return nat_port

    @retry(delay=5, tries=5)
    def verify_flow_with_port(self, client_vm_fix, dst_vm_fix, port_range, **traffic):
        server_ip = dst_vm_fix.vm_node_ip
        server_data_ip = dst_vm_fix.vm_node_data_ip
        self.run_iperf_between_vm_host(client_vm_fix, server_ip, server_data_ip, **traffic)
        if traffic['udp']:
            proto = '17'
        else:
            proto = '6'
        nat_port_used = self.get_nat_port_used_for_flow(client_vm_fix, proto, traffic['port'])
        self.iperf.stop_iperf_on_server()
        self.logger.info("Nat port being used for the flow is %s" %nat_port_used)
        if not nat_port_used or not [port for port in nat_port_used if port in port_range]:
            return False
        return True

    def get_vhost_vmi_obj(self, compute_node):
        fq_name = "default-global-system-config:"+compute_node+":vhost0"
        return self.vnc_h.virtual_machine_interface_read(fq_name_str=
            fq_name)

    def disable_policy_on_vhost0(self, compute_node, disable=True):
        self.logger.info('Disable vhost0 policy on the compute node, %s, set to %s'\
            %(compute_node, disable))
        vhost_vmi = self.get_vhost_vmi_obj(compute_node)
        self.vnc_h.disable_policy_on_vmi(vhost_vmi.uuid, disable)

    def configure_aap_for_port_list(self, vn, vm_list):
        vIP = get_an_ip(vn.vn_subnets[0]['cidr'], offset=10)
        for vm in vm_list:
            port = self.vnc_h.virtual_machine_interface_read(id=list(vm.vmi_ids.values())[0])
            mac_address = port.virtual_machine_interface_mac_addresses.mac_address[0]
            self.config_aap(
                port.uuid, vIP, mac=mac_address, aap_mode='active-active', contrail_api=True)
            output = vm.run_cmd_on_vm(
                ['sudo ifconfig eth0:10 ' + vIP + ' netmask 255.255.255.0'])
            self.check_master_in_agent(vm, vn, vIP, ecmp=True)
        return vIP
