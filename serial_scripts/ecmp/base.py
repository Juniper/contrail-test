from vn_test import VNFixture
from vm_test import VMFixture
from vnc_api.vnc_api import *
import re
import test_v1
from common.connections import ContrailConnections
from common import isolated_creds
from fabric.api import run, hide, settings
from common.servicechain.verify import VerifySvcChain
from tcutils.tcpdump_utils import *
from common.neutron.base import BaseNeutronTest

class BaseECMPRestartTest(test_v1.BaseTestCase_v1):

    @classmethod
    def setUpClass(cls):
        super(BaseECMPRestartTest, cls).setUpClass()
        cls.quantum_h = cls.connections.quantum_h
        cls.nova_h = cls.connections.nova_h
        cls.vnc_lib = cls.connections.vnc_lib
        cls.agent_inspect = cls.connections.agent_inspect
        cls.cn_inspect = cls.connections.cn_inspect
        cls.analytics_obj = cls.connections.analytics_obj
        cls.config_vm_vn_handle = BaseNeutronTest()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        super(BaseECMPRestartTest, cls).tearDownClass()
    # end tearDownClass

    def remove_from_cleanups(self, fix):
        for cleanup in self._cleanups:
        #    if fix.cleanUp in cleanup:
            self._cleanups.remove(cleanup)
            # break
    # end remove_from_cleanups

    # Configure VMs, static table and attach table to relevant ports
    def config_2_vns_7_vms(self):
        '''
        # Create VNs and VMs, 2 left vms, 3 ecmp vms, 2 right vms
        self.vn1_name = "left-vn"
        vn1_net = ['1.1.1.0/24']
        self.vn1_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=self.vn1_name, inputs=self.inputs, subnets=vn1_net))
        self.vn2_name = "right-vn"
        vn2_net = ['2.2.2.0/24']
        self.vn2_fixture = self.useFixture(VNFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_name=self.vn2_name, inputs=self.inputs, subnets=vn2_net))
        left_vm_name = "left-vm"
        right_vm_name = "right-vm"
        self.left_vm_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=self.vn1_fixture.obj, vm_name=left_vm_name, node_name=None,
            image_name='ubuntu', flavor='m1.tiny'))

        self.right_vm_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=self.vn2_fixture.obj, vm_name=right_vm_name, node_name=None,
            image_name='ubuntu', flavor='m1.tiny'))
        '''
        self.left_vm_fixture.wait_till_vm_is_up()
        self.right_vm_fixture.wait_till_vm_is_up()

        vm1_name = 'ecmp_vm1'
        vm2_name = 'ecmp_vm2'
        vm3_name = 'left_vm2'
        vm4_name = 'right_vm2'
        vm5_name = 'ecmp_vm3'

        # ECMP vms should have legs in both VNs
        self.vm1_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_objs=[self.vn1_fixture.obj,
                     self.vn2_fixture.obj], vm_name=vm1_name, node_name=None,
            image_name='ubuntu', flavor='m1.tiny'))

        self.vm2_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_objs=[self.vn1_fixture.obj,
                     self.vn2_fixture.obj], vm_name=vm2_name, node_name=None,
            image_name='ubuntu', flavor='m1.tiny'))
        self.vm3_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=self.vn1_fixture.obj, vm_name=vm3_name, node_name=None,
            image_name='ubuntu', flavor='m1.tiny'))
        self.vm4_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_obj=self.vn2_fixture.obj, vm_name=vm4_name, node_name=None,
            image_name='ubuntu', flavor='m1.tiny'))
        self.vm5_fixture = self.useFixture(VMFixture(
            project_name=self.inputs.project_name, connections=self.connections,
            vn_objs=[self.vn1_fixture.obj,
                     self.vn2_fixture.obj], vm_name=vm5_name, node_name=None,
            image_name='ubuntu', flavor='m1.tiny'))

        # Are the VMs up?
        self.vm1_fixture.wait_till_vm_is_up()
        self.vm2_fixture.wait_till_vm_is_up()
        self.vm3_fixture.wait_till_vm_is_up()
        self.vm4_fixture.wait_till_vm_is_up()
        self.vm5_fixture.wait_till_vm_is_up()

        # Enable routing in the centre VMs, which will be in the ECMP paths
        cmd = 'echo 1 > /proc/sys/net/ipv4/ip_forward'
        self.vm1_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        self.vm2_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)
        self.vm5_fixture.run_cmd_on_vm(cmds=[cmd], as_sudo=True)

        # Create static tables and attach it to centre ECMP VM ports
        self.create_static_table(
            self.vn1_fixture,
            self.vn2_fixture,
            self.vm1_fixture,
            self.vm2_fixture,
            self.vm5_fixture)

    # Will update network hash on the vn_fixture
    def update_hash_on_network(self, ecmp_hash, vn_fixture):

        vn_config = self.vnc_lib.virtual_network_read(id=vn_fixture.uuid)
        vn_config.set_ecmp_hashing_include_fields(ecmp_hash)
        self.vnc_lib.virtual_network_update(vn_config)

    # Will update port hash on vm_fixture
    def update_hash_on_port(self, ecmp_hash, vm_fixture):
        id_entry = self.inputs.project_fq_name[0] + ':' + \
            self.inputs.project_fq_name[1] + ':' + self.vn1_name
        vm_uuid = str(vm_fixture.get_vmi_ids()[id_entry])
        vm_config = self.vnc_lib.virtual_machine_interface_read(id=vm_uuid)
        vm_config.set_ecmp_hashing_include_fields(ecmp_hash)
        self.vnc_lib.virtual_machine_interface_update(vm_config)

    # Will update global ECMP hash
    def config_all_hash(self, ecmp_hashing_include_fields):

        global_vrouter_id = self.vnc_lib.get_default_global_vrouter_config_id()
        global_config = self.vnc_lib.global_vrouter_config_read(
            id=global_vrouter_id)
        global_config.set_ecmp_hashing_include_fields(
            ecmp_hashing_include_fields)
        self.vnc_lib.global_vrouter_config_update(global_config)

    def initialize_hit_counters(self):

        self.available_ecmp_paths[self.current_tap[0]] = 0
        self.available_ecmp_paths[self.current_tap[1]] = 0
        self.available_ecmp_paths[self.current_tap[2]] = 0

    # Create static tables and attach it to passed port fixtures
    def create_static_table(
        self,
        src_vn_fix,
        dst_vn_fix,
        port1_fix,
        port2_fix,
            port3_fix):

        id_entry = self.inputs.project_fq_name[0] + ':' + \
            self.inputs.project_fq_name[1] + ':' + self.vn1_name

        vm_uuid1 = str(port1_fix.get_vmi_ids()[id_entry])
        vm_uuid2 = str(port2_fix.get_vmi_ids()[id_entry])
        vm_uuid3 = str(port3_fix.get_vmi_ids()[id_entry])
        for vm_uuid in [vm_uuid1, vm_uuid2, vm_uuid3]:
            add_static_route_cmd = 'python provision_static_route.py --prefix ' + str(dst_vn_fix.get_cidrs()[0]) + ' --virtual_machine_interface_id ' + vm_uuid + \
                ' --tenant_name ' + self.inputs.project_name + ' --api_server_ip 127.0.0.1 --api_server_port 8082 --oper add --route_table_name my_route_table' + vm_uuid + \
                ' --user ' + "admin" + ' --password ' + "contrail123"
            with settings(
                host_string='%s@%s' % (
                    self.inputs.username, self.inputs.cfgm_ips[0]),
                    password=self.inputs.password, warn_only=True, abort_on_prompts=False, debug=True):

                status = run('cd /opt/contrail/utils;' + add_static_route_cmd)
                self.logger.debug("%s" % status)
                m = re.search(r'Creating Route table', status)
                assert m, 'Failed in Creating Route table'
        id_entry = self.inputs.project_fq_name[0] + ':' + \
            self.inputs.project_fq_name[1] + ':' + self.vn2_name

        vm_uuid1 = str(port1_fix.get_vmi_ids()[id_entry])
        vm_uuid2 = str(port2_fix.get_vmi_ids()[id_entry])
        vm_uuid3 = str(port3_fix.get_vmi_ids()[id_entry])
        for vm_uuid in [vm_uuid1, vm_uuid2, vm_uuid3]:
            add_static_route_cmd = 'python provision_static_route.py --prefix ' + str(src_vn_fix.get_cidrs()[0]) + ' --virtual_machine_interface_id ' + vm_uuid + \
                ' --tenant_name ' + self.inputs.project_name + ' --api_server_ip 127.0.0.1 --api_server_port 8082 --oper add --route_table_name my_route_table' + vm_uuid + \
                ' --user ' + "admin" + ' --password ' + "contrail123"
            with settings(
                host_string='%s@%s' % (
                    self.inputs.username, self.inputs.cfgm_ips[0]),
                    password=self.inputs.password, warn_only=True, abort_on_prompts=False, debug=True):

                status = run('cd /opt/contrail/utils;' + add_static_route_cmd)
                self.logger.debug("%s" % status)
                m = re.search(r'Creating Route table', status)
                assert m, 'Failed in Creating Route table'

    def send_traffic_and_update_hit_count(
        self,
        sender,
        receiver,
        sport='8001',
        dport='9001',
        protocol='udp',
            count=2):

            self.check_all_ecmpinterfaces()
            self.verify_traffic(
                sender,
                receiver,
                protocol,
                sport=sport,
                dport=dport,
                count=count)
            current_ecmp_path = self.get_which_path_is_being_taken()
            self.available_ecmp_paths[current_ecmp_path] += 1

    # Get all ECMP paths, enable tcpdump on them
    def check_all_ecmpinterfaces(self):

        i = 0
        self.session = []
        self.pcap = []
        filters = '-nn'
        self.current_tap = []
        for vm in [self.vm1_fixture, self.vm2_fixture, self.vm5_fixture]:
            get_vm_op = vm.get_tap_intf_of_vm()
            for tap in get_vm_op:
                if self.vn1_name in tap['vn_name']:
                    tap_if_of_vm = tap['name']
            self.current_tap.append(tap_if_of_vm)
            vm_nodeip = vm.vm_node_ip
            compute_user = self.inputs.host_data[vm_nodeip]['username']
            compute_password = self.inputs.host_data[vm_nodeip]['password']
            self.session_item, self.pcap_item = start_tcpdump_for_intf(
                vm_nodeip, compute_user, compute_password, tap_if_of_vm, filters=filters)
            self.session.append(self.session_item)
            self.pcap.append(self.pcap_item)
            i = i + 1

    # Stop tcpdump on the interface and from tcpdump output, get which ecmp
    # path was taken
    def get_which_path_is_being_taken(self):

        i = 0
        correct_tap = ''
        for vm in [self.vm1_fixture, self.vm2_fixture, self.vm5_fixture]:
            cmd = 'tcpdump -r %s' % self.pcap[i]
            udp_op, err = execute_cmd_out(self.session[i], cmd, self.logger)
            receiving_int = re.search("IP (.+ > .+): UDP", udp_op)
            if receiving_int:
                correct_tap = self.current_tap[i]
            stop_tcpdump_for_vm_intf(self, self.session[i], self.pcap[i])
            i = i + 1
        return correct_tap

    def send_traffic_and_return_path_taken(
        self,
        sender,
        receiver,
        sport='8001',
        dport='9001',
        protocol='udp',
            count=2):

            self.check_all_ecmpinterfaces()
            self.verify_traffic(
                sender,
                receiver,
                protocol,
                sport=sport,
                dport=dport,
                count=count)
            path_taken = self.get_which_path_is_being_taken()
            return path_taken

    def ecmp_stats_with_hit_count_check(self):

        self.logger.info(
            "Hit count on first ecmp path : %s" %
            self.available_ecmp_paths[self.current_tap[0]])
        self.logger.info(
            "Hit count on second ecmp path : %s" %
            self.available_ecmp_paths[self.current_tap[1]])
        self.logger.info(
            "Hit count on third ecmp path : %s" %
            self.available_ecmp_paths[self.current_tap[2]])

        assert (self.available_ecmp_paths[self.current_tap[0]] + \
                self.available_ecmp_paths[self.current_tap[1]] + \
                self.available_ecmp_paths[self.current_tap[2]] == 60), \
                'Traffic not distributed correctly across ecmp paths'

    # From introspect output, get the route entry for ECMP route and check for
    # ECMP fields
    def verify_if_hash_changed(
        self,
        vn1_fixture,
        vn2_fixture,
        vm1_fixture,
        vm2_fixture,
            ecmp_hashing_include_fields):
        (domain, project, vn) = vn1_fixture.vn_fq_name.split(':')
        inspect_h = self.agent_inspect[vm1_fixture.vm_node_ip]
        agent_vrf_objs = inspect_h.get_vna_vrf_objs(domain, project, vn)
        agent_vrf_obj = vm1_fixture.get_matching_vrf(
            agent_vrf_objs['vrf_list'], vn1_fixture.vrf_name)
        vn_vrf_id = agent_vrf_obj['ucindex']
        next_hops = inspect_h.get_vna_active_route(
            vrf_id=vn_vrf_id, ip=str(vn2_fixture.get_cidrs()[0])[:-1][:-1][:-1], \
                                     prefix='24')['path_list'][0]['nh']['mc_list']

        if not next_hops:
            result = False
            assert result, 'Route not found in the Agent %s' % vm2_fixture.vm_node_ip
        else:
            self.logger.info(
                'Route found in the Agent %s' %
                vm2_fixture.vm_node_ip)
        if (len(next_hops) != 3):
            result = False
            assert result, 'Agent does not reflect the static route addition'
        else:
            self.logger.info('Agent reflects the static route addition')
        ecmp_field = inspect_h.get_vna_active_route(
            vrf_id=vn_vrf_id,
            ip=str(vn2_fixture.get_cidrs()[0])[:-1][:-1][:-1],
            prefix='24')['path_list'][0]['ecmp_hashing_fields']
        if not(ecmp_field == ecmp_hashing_include_fields):
            return False
        id_entry = self.inputs.project_fq_name[0] + ':' + \
            self.inputs.project_fq_name[1] + ':' + self.vn1_name
        vm_uuid1 = str(port1_fix.get_vmi_ids()[id_entry])
        vm_uuid2 = str(port2_fix.get_vmi_ids()[id_entry])
        vm_uuid3 = str(port3_fix.get_vmi_ids()[id_entry])

        for node in self.inputs.bgp_ips:
            route_entry = self.cn_inspect[
                node]._get_if_map_table_entry(vm_uuid1)
