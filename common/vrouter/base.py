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

class BaseVrouterTest(BaseNeutronTest):

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
        for i in xrange(count):
            vn_subnets = get_random_cidrs(self.inputs.get_af())
            vn_fixtures.append(self.create_vn(vn_subnets=vn_subnets, *args, **kwargs))

        return vn_fixtures

    def verify_vns(self, vn_fixtures):
        for vn_fixture in vn_fixtures:
            assert vn_fixture.verify_on_setup()

    def create_vms(self, vn_fixture, count=1, image_name='ubuntu', *args, **kwargs):
        vm_fixtures = []
        for i in xrange(count):
            vm_fixtures.append(self.create_vm(
                            vn_fixture,
                            image_name=image_name,
                            *args, **kwargs
                            ))

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
            assert vm_fixture.verify_on_setup()
        for vm_fixture in vm_fixtures:
            assert vm_fixture.wait_till_vm_is_up()

    def add_static_routes_on_vms(self,prefix, vm_fixtures, ip=None):
        if ip is None:
            #get a random IP from the prefix and configure it on the VMs
            ip = get_random_ip(prefix)
        for vm_fixture in vm_fixtures:
            #Disable duplicate address detection before adding static IP on VMs
            interface = vm_fixture.get_vm_interface_list(ip=vm_fixture.vm_ip)[0]
            cmd = 'sysctl net.ipv6.conf.%s.accept_dad=0' % (interface)
            vm_fixture.run_cmd_on_vm([cmd], as_sudo=True)
            vmi_ids = vm_fixture.get_vmi_ids().values()
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
            vmi_ids = vm.get_vmi_ids().values()
            self.disable_policy_on_vmis(vmi_ids, disable)

        return True

    def add_fat_flow_to_vmis(self, vmi_ids, fat_flow_config):
        '''vmi_ids: list of vmi ids
           fat_flow_config: dictionary of format {'proto':<string>,'port':<int>}
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

    def start_ping(self, src_vm, dst_vm=None, dst_ip=None, wait=False,
            *args, **kwargs):
        '''
        Starts ping from src_vm to dst_ip
        '''
        dst_ip = dst_ip or dst_vm.vm_ip

        ping_h = Ping(src_vm, dst_ip, *args, **kwargs)
        ping_h.start(wait=wait)

        return ping_h

    def stop_ping(self, ping_h):
        (stats, ping_log) = ping_h.stop()
        self.logger.debug('Ping log : %s' % (ping_log))

        return (stats, ping_log)

    def remove_sg_from_vms(self, vm_fix_list, sg_id=None):
        default_sg_id = get_secgrp_id_from_name(
                                self.connections,
                                ':'.join([self.inputs.domain_name,
                                        self.inputs.project_name,
                                        'default']))
        sg_id = sg_id or default_sg_id
        for vm in vm_fix_list:
            vm.remove_security_group(secgrp=sg_id)

    def add_sg_to_vms(self, vm_fix_list, sg_id=None):
        default_sg_id = get_secgrp_id_from_name(
                                self.connections,
                                ':'.join([self.inputs.domain_name,
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
            proto, ff_exp=0, rf_exp=0, exp=True):

        src_ip = src_vm_fix.vm_ip
        dst_ip = dst_vm_fix.vm_ip
        sport = 10000
        dport = 11000

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
                               dest_port, proto, vrf_id, fat_flow_count=1):
        '''
        Verifies Fat flow on specific compute node
        '''
        #Get Fat flow, with source port as ZERO
        (ff_count, rf_count) = compute_fixture.get_flow_count(
                                    source_ip=source_ip,
                                    dest_ip=dest_ip,
                                    source_port=0,
                                    dest_port=dest_port,
                                    proto=proto,
                                    vrf_id=vrf_id
                                    )
        if (ff_count != fat_flow_count) or (rf_count != fat_flow_count):
            str_log = 'FAILED'
        else:
            str_log = 'PASSED'
        self.logger.debug("Fat flow verification %s on node: %s for VMs - "
                            "Sender: %s, Receiver: %s, "
                            "Fat flow expected: %s, got:%s" % (
                            str_log,
                            compute_fixture.ip,
                            source_ip, dest_ip,
                            fat_flow_count, ff_count))

        assert ff_count == fat_flow_count, ('Fat flow count mismatch on '
            'compute, got:%s, exp:%s' % (ff_count, fat_flow_count))
        assert rf_count == fat_flow_count, ('Fat flow count mismatch on '
            'compute, got:%s, exp:%s' % (rf_count, fat_flow_count))

    def verify_fat_flow(self, sender_vm_fix_list, dst_vm_fix,
                               proto, dest_port,
                               fat_flow_count=1,
                               unidirectional_traffic=True, af=None):
        '''
        Verifies FAT flows on all the computes
        '''
        af = af or self.inputs.get_af()
        dst_compute_fix = self.compute_fixtures_dict[dst_vm_fix.vm_node_ip]
        vrf_id_dst = dst_compute_fix.get_vrf_id(dst_vm_fix.vn_fq_names[0])
        for fix in sender_vm_fix_list:
            src_compute_fix = self.compute_fixtures_dict[fix.vm_node_ip]
            vrf_id_src = src_compute_fix.get_vrf_id(fix.vn_fq_names[0])
            #For inter-Node traffic
            if (dst_vm_fix.vm_node_ip != fix.vm_node_ip):
                self.verify_fat_flow_on_compute(dst_compute_fix,
                    fix.get_vm_ips(af=af)[0], dst_vm_fix.get_vm_ips(af=af)[0],
                    dest_port, proto, vrf_id_dst, fat_flow_count=fat_flow_count)

                #Source compute should never have Fat flow for inter node traffic
                self.verify_fat_flow_on_compute(src_compute_fix,
                    fix.get_vm_ips(af=af)[0], dst_vm_fix.get_vm_ips(af=af)[0],
                    dest_port, proto, vrf_id_src, fat_flow_count=0)
            #For intra-Node traffic
            else:
                if unidirectional_traffic:
                    #Source compute should not have Fat flow for unidirectional traffic
                    self.verify_fat_flow_on_compute(src_compute_fix,
                        fix.get_vm_ips(af=af)[0],
                        dst_vm_fix.get_vm_ips(af=af)[0], dest_port, proto,
                        vrf_id_src, fat_flow_count=0)

                else:
                    #Source compute should have Fat flow for bi-directional traffic
                    self.verify_fat_flow_on_compute(src_compute_fix,
                        fix.get_vm_ips(af=af)[0],
                        dst_vm_fix.get_vm_ips(af=af)[0], dest_port, proto,
                        vrf_id_src, fat_flow_count=fat_flow_count)


        return True

    def verify_fat_flow_with_traffic(self, sender_vm_fix_list, dst_vm_fix,
                           proto, dest_port, traffic=True,
                           expected_flow_count=1, fat_flow_count=1, af=None):
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
        af = af or self.inputs.get_af()
        #Use 2 different source ports for each sender VM
        sport_list = [10000, 10001]
        dst_compute_fix = self.compute_fixtures_dict[dst_vm_fix.vm_node_ip]

        #Start the traffic from each of the VM in sender_vm_fix_list to dst_vm_fix
        if traffic:
            for fix in sender_vm_fix_list:
                for port in sport_list:
                    assert self.send_nc_traffic(fix, dst_vm_fix, port,
                        dest_port, proto, ip=dst_vm_fix.get_vm_ips(af=af)[0])

        #Verify the flows on sender computes for each sender/receiver VMs and ports
        for fix in sender_vm_fix_list:
            for port in sport_list:
                compute_fix = self.compute_fixtures_dict[fix.vm_node_ip]
                (ff_count, rf_count) = compute_fix.get_flow_count(
                                    source_ip=fix.get_vm_ips(af=af)[0],
                                    dest_ip=dst_vm_fix.get_vm_ips(af=af)[0],
                                    source_port=port,
                                    dest_port=dest_port,
                                    proto=proto,
                                    vrf_id=compute_fix.get_vrf_id(
                                              fix.vn_fq_names[0])
                                    )
                assert ff_count == expected_flow_count, ('Flows count mismatch on '
                    'sender compute, got:%s, expected:%s' % (
                    ff_count, expected_flow_count))
                assert rf_count == expected_flow_count, ('Flows count mismatch on '
                    'sender compute, got:%s, expected:%s' % (
                    rf_count, expected_flow_count))

                #For the case when sender and receiver are on different nodes
                if dst_vm_fix.vm_node_ip != fix.vm_node_ip:
                    #Flow with source and dest port should not be created on dest node, if Fat flow is expected
                    if fat_flow_count:
                        expected_count_dst = 0
                    else:
                        expected_count_dst = expected_flow_count
                    (ff_count, rf_count) = dst_compute_fix.get_flow_count(
                                    source_ip=fix.get_vm_ips(af=af)[0],
                                    dest_ip=dst_vm_fix.get_vm_ips(af=af)[0],
                                    source_port=port,
                                    dest_port=dest_port,
                                    proto=proto,
                                    vrf_id=dst_compute_fix.get_vrf_id(
                                              dst_vm_fix.vn_fq_names[0])
                                    )
                    assert ff_count == expected_count_dst, ('Flows count '
                        'mismatch on dest compute, got:%s, expected:%s' % (
                        ff_count, expected_count_dst))
                    assert rf_count == expected_count_dst, ('Flows count '
                        'mismatch on dest compute, got:%s, expected:%s' % (
                        rf_count, expected_count_dst))

        #FAT flow verification
        assert self.verify_fat_flow(sender_vm_fix_list, dst_vm_fix,
                               proto, dest_port, fat_flow_count, af=af)

        self.logger.info("Fat flow verification passed for "
            "protocol %s and port %s" % (proto, dest_port))
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
            tap_intf = vm_fixture.tap_intf.values()[0]['name']
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
