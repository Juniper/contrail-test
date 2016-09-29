import test_v1
from common.connections import ContrailConnections
from tcutils.util import *
from tcutils.tcpdump_utils import *
from compute_node_test import ComputeNodeFixture
from vnc_api.vnc_api import *
from tcutils.traffic_utils.base_traffic import *
from tcutils.traffic_utils.hping_traffic import Hping3
from tcutils.traffic_utils.ping_traffic import Ping
from common.neutron.lbaasv2.base import BaseLBaaSTest
from contrailapi import ContrailVncApi
import random
from security_group import get_secgrp_id_from_name, SecurityGroupFixture

class BaseVrouterTest(BaseLBaaSTest):

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
        cls.vnc_h = ContrailVncApi(cls.vnc_lib, cls.logger)

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

                rt_fq_name = [self.inputs.domain_name,
                    self.inputs.project_name, route_table_name]
                self.addCleanup(vm_fixture.vnc_lib_h.interface_route_table_delete,
                                    fq_name=rt_fq_name)
                self.addCleanup(vm_fixture.provision_static_route,
                                    prefix=prefix,
                                    tenant_name=self.inputs.project_name,
                                    oper='del',
                                    virtual_machine_interface_id=vmi_id,
                                    route_table_name=route_table_name,
                                    user=self.inputs.stack_user,
                                    password=self.inputs.stack_password)

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
                             count=1, interval='u100', *args, **kwargs):
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
                         *args, **kwargs)
        hping_h.start(wait=False)
        (stats, hping_log) = hping_h.stop()
        self.logger.debug('Hping3 log : %s' % (hping_log))

        return (stats, hping_log)

    def send_nc_traffic(self, sender_vm_fix, dest_vm_fix, sport, dport,
            proto, size='100', ip=None, exp=True):
        '''
        Sends tcp/udp traffic using netcat, this method will work for IPv4 as well as IPv6
        Starts the netcat on both sender as well as receiver
        IPv6 will work only with ubuntu and ubuntu-traffic images,
            cirros does not support IPv6.
        '''
        nc_options = '-4' if (self.inputs.get_af() == 'v4') else '-6'
        nc_options = nc_options + ' -q 2'
        if proto == 'udp':
            nc_options = nc_options + ' -u'

        result = sender_vm_fix.nc_file_transfer(
            dest_vm_fix, local_port=sport, remote_port=dport,
            nc_options=nc_options, size=size, ip=ip, expectation=exp)

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
        sg_fixture = self.useFixture(SecurityGroupFixture(self.inputs,
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

    def verify_traffic_load_balance_si(self, sender_vm_fix, si_vm_list,
                                dest_vm_fix, dest_ip=None, flow_count=0):
        '''
        This method is similar to verify_traffic_load_balance for service chain case.
        tcpdump is done on left interface of the SIs and ping is used for traffic verification
        The method is written for transparent service chain
        '''
        try_count = len(si_vm_list) + 2
        packet_count = 1
        session = {}
        pcap = {}
        compute_node_ips = []
        compute_fixtures = []
        proto = 'icmp'
        errmsg = "Ping to right VM ip %s from left VM failed" % dest_ip
        dest_ip = dest_ip or dest_vm_fix.vm_ip

        if flow_count:
            #If flow is expected, then flow count should be minimum no. of try_count
            flow_count = try_count
        #Get all the VMs compute IPs
        compute_node_ips.append(sender_vm_fix.vm_node_ip)
        if dest_vm_fix.vm_node_ip not in compute_node_ips:
                compute_node_ips.append(dest_vm_fix.vm_node_ip)

        #Get the compute fixture for all the concerned computes
        for ip in compute_node_ips:
            compute_fixtures.append(self.compute_fixtures_dict[ip])

        #Send traffic multiple times to verify load distribution
        for i in xrange(try_count):
            result = True
            sport = random.randint(12000, 65000)

            #Clean all the old flows before starting the traffic
            for fixture in compute_fixtures:
                fixture.delete_all_flows()
            #Start the tcpdump on all the SI VMs
            for vm in si_vm_list:
                filters = '\'(%s and (host %s or host %s))\'' % (
                    proto, sender_vm_fix.vm_ip, dest_ip)
                session[vm], pcap[vm] = start_tcpdump_for_vm_intf(self, vm,
                    self.trans_left_vn_fixture.vn_fq_name, filters = filters)

            #Send the traffic
            for i in xrange(try_count):
                assert sender_vm_fix.ping_with_certainty(dest_ip), errmsg

            #Verify tcpdump count, all destinations should receive some packets
            for vm in si_vm_list:
                ret = verify_tcpdump_count(self, session[vm], pcap[vm])
                if not ret:
                    self.logger.error("Tcpdump verification on VM %s failed" %
                                        vm.vm_ip)
                    stop_tcpdump_for_vm_intf(self, session[vm], pcap[vm])
                delete_pcap(session[vm], pcap[vm])
                result = result and ret

            #Verify expected flow count, on all the computes
            for vm in [sender_vm_fix, dest_vm_fix]:
                compute_fix = self.compute_fixtures_dict[vm.vm_node_ip]
                self.verify_flow_on_compute(compute_fix, sender_vm_fix.vm_ip,
                    dest_ip, proto=proto, ff_exp=flow_count, rf_exp=flow_count)

            if result:
                self.logger.info("Traffic is distributed to all the ECMP routes"
                        " as expected")
                return result

        return result

    def verify_traffic_load_balance(self, sender_vm_fix,
                                dest_vm_fix_list, dest_ip, flow_count=0):
        '''
        Common method to be used to verify if load is distributed to
        all the VMs in dest_vm_fix_list and flow is not created on the computes
        Inputs-
            sender_vm_fix: sender VM fixture
            dest_vm_fix_list: list of destination VM fixtures
            dest_ip: IP where traffic needs to be sent
        Verifications:
            1. Traffic verification is done on all the VMs via tcpdump
            2. hping3 is used to send udp traffic, and verify if there is no traffic loss
            3. Verify no flow is created on all the computes, when policy is disabled
        '''
        try_count = len(dest_vm_fix_list) + 1
        packet_count = 1
        session = {}
        pcap = {}
        compute_node_ips = []
        compute_fixtures = []
        proto = 'udp'
        destport = '11000'

        #Get all the VMs compute IPs
        compute_node_ips.append(sender_vm_fix.vm_node_ip)
        for vm in dest_vm_fix_list:
            if vm.vm_node_ip not in compute_node_ips:
                compute_node_ips.append(vm.vm_node_ip)

        #Get the compute fixture for all the concerned computes
        for ip in compute_node_ips:
            compute_fixtures.append(self.compute_fixtures_dict[ip])

        #Send traffic multiple times to verify load distribution
        for i in xrange(try_count):
            result = True
            sport = random.randint(12000, 65000)

            #Start the tcpdump on all the destination VMs
            for vm in dest_vm_fix_list:
                filters = '\'(%s and src host %s and dst host %s and dst port %s)\'' % (
                    proto, sender_vm_fix.vm_ip, dest_ip, int(destport))
                session[vm], pcap[vm] = start_tcpdump_for_vm_intf(self, vm,
                                            vm.vn_fq_names[0], filters = filters)

            #Send the traffic without any receiver, dest VM will send icmp error
            nc_options = '-4' if (self.inputs.get_af() == 'v4') else '-6'
            nc_options = nc_options + ' -q 2 -u'
            for i in xrange(try_count):
                sender_vm_fix.nc_send_file_to_ip('icmp_error', dest_ip,
                    local_port=sport+i, remote_port=destport,
                    nc_options=nc_options)

            #Verify tcpdump count, all destinations should receive some packets
            for vm in dest_vm_fix_list:
                ret = verify_tcpdump_count(self, session[vm], pcap[vm])
                if not ret:
                    self.logger.error("Tcpdump verification on VM %s failed" %
                                        vm.vm_ip)
                    stop_tcpdump_for_vm_intf(self, session[vm], pcap[vm])
                delete_pcap(session[vm], pcap[vm])
                result = result and ret

            #Verify expected flow count, on all the computes
            for fixture in compute_fixtures:
                vrf_id = fixture.get_vrf_id(sender_vm_fix.vn_fq_names[0])
                for i in xrange(try_count):
                    self.verify_flow_on_compute(fixture, sender_vm_fix.vm_ip,
                        dest_ip, vrf_id, vrf_id, sport=sport+i, dport=destport,
                        proto=proto, ff_exp=flow_count, rf_exp=flow_count)

            if result:
                self.logger.info("Traffic is distributed to all the ECMP routes"
                        " as expected")
                return result

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
                               unidirectional_traffic=True):
        '''
        Verifies FAT flows on all the computes
        '''
        dst_compute_fix = self.compute_fixtures_dict[dst_vm_fix.vm_node_ip]
        vrf_id_dst = dst_compute_fix.get_vrf_id(dst_vm_fix.vn_fq_names[0])
        for fix in sender_vm_fix_list:
            src_compute_fix = self.compute_fixtures_dict[fix.vm_node_ip]
            vrf_id_src = src_compute_fix.get_vrf_id(fix.vn_fq_names[0])
            #For inter-Node traffic
            if (dst_vm_fix.vm_node_ip != fix.vm_node_ip):
                self.verify_fat_flow_on_compute(dst_compute_fix, fix.vm_ip,
                            dst_vm_fix.vm_ip, dest_port, proto, vrf_id_dst,
                            fat_flow_count=fat_flow_count)

                #Source compute should never have Fat flow for inter node traffic
                self.verify_fat_flow_on_compute(src_compute_fix, fix.vm_ip,
                            dst_vm_fix.vm_ip, dest_port, proto, vrf_id_src,
                            fat_flow_count=0)
            #For intra-Node traffic
            else:
                if unidirectional_traffic:
                    #Source compute should not have Fat flow for unidirectional traffic
                    self.verify_fat_flow_on_compute(src_compute_fix, fix.vm_ip,
                                dst_vm_fix.vm_ip, dest_port, proto, vrf_id_src,
                                fat_flow_count=0)

                else:
                    #Source compute should have Fat flow for bi-directional traffic
                    self.verify_fat_flow_on_compute(src_compute_fix, fix.vm_ip,
                                dst_vm_fix.vm_ip, dest_port, proto, vrf_id_src,
                                fat_flow_count=fat_flow_count)


        return True

    def verify_fat_flow_with_traffic(self, sender_vm_fix_list, dst_vm_fix,
                                       proto, dest_port, traffic=True,
                                       expected_flow_count=1, fat_flow_count=1):
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
        #Use 2 different source ports for each sender VM
        sport_list = [10000, 10001]
        dst_compute_fix = self.compute_fixtures_dict[dst_vm_fix.vm_node_ip]

        #Start the traffic from each of the VM in sender_vm_fix_list to dst_vm_fix
        if traffic:
            for fix in sender_vm_fix_list:
                for port in sport_list:
                    assert self.send_nc_traffic(fix, dst_vm_fix, port, dest_port,
                        proto)

        #Verify the flows on sender computes for each sender/receiver VMs and ports
        for fix in sender_vm_fix_list:
            for port in sport_list:
                compute_fix = self.compute_fixtures_dict[fix.vm_node_ip]
                (ff_count, rf_count) = compute_fix.get_flow_count(
                                            source_ip=fix.vm_ip,
                                            dest_ip=dst_vm_fix.vm_ip,
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
                                                source_ip=fix.vm_ip,
                                                dest_ip=dst_vm_fix.vm_ip,
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
                               proto, dest_port, fat_flow_count)

        self.logger.info("Fat flow verification passed for "
            "protocol %s and port %s" % (proto, dest_port))
        return True
