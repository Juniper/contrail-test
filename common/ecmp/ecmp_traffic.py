from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from common.servicechain.verify import VerifySvcChain
from tcutils.tcpdump_utils import *
DPORT=9000
SPORT=8000

class ECMPTraffic(VerifySvcChain):
    def verify_traffic_flow(self, src_vm, dst_vm_list, si_fix, src_vn,
                            src_ip=None, dst_ip=None, ecmp_hash=None,
                            flow_count=3):
        src_ip = src_vm.vm_ip
        if dst_ip == None:
            dst_ip = dst_vm_list[0].vm_ip
        traffic_objs = self.start_multiple_streams(src_vm, dst_vm_list,
            src_ip=src_ip, dst_ip=dst_ip, flow_count=flow_count)
        self.verify_flow_thru_si(si_fix, src_vn, ecmp_hash, flow_count)
        self.verify_flow_records(src_vm, src_ip, dst_ip, flow_count)
        self.stop_multiple_streams(traffic_objs)
        return True

    def start_multiple_streams(self, src_vm, dst_vm_list, src_ip=None,
                             dst_ip=None, flow_count=3):
        traffic_objs = list()
        src_ip = src_ip or src_vm.vm_ip
        if dst_ip is None:
            dst_ip = dst_vm_list[0].vm_ip
        self.logger.info("-" * 80)
        self.logger.info('Starting Traffic from %s to %s' %(src_ip, dst_ip))
        self.logger.info("-" * 80)
        for dst_vm in dst_vm_list:
            for index in range(flow_count):
                traffic_objs.append(self.start_traffic(src_vm,
                    dst_vm, 'udp', SPORT, DPORT+index, fip_ip=dst_ip))
        return traffic_objs
    # end start_multiple_flows

    def stop_multiple_streams(self, traffic_objs):
        self.logger.info('Stopping Traffic now')
        for trafic_obj in traffic_objs:
            assert self.stop_traffic(traffic_obj)
        return True
    # end stop_traffic

    def scapy_start_traffic(self, src_vm, dst_vm_list, stream_list, src_ip=None, dst_ip=None):

        self.logger.info("-" * 80)
        self.logger.info('Starting Traffic from %s to %s' %
                         (src_ip, dst_ip))
        self.logger.info("-" * 80)
        profile = {}
        sender = {}
        receiver = {}
        tx_vm_node_ip = src_vm.vm_node_ip
        tx_local_host = Host(
            tx_vm_node_ip,
            self.inputs.host_data[tx_vm_node_ip]['username'],
            self.inputs.host_data[tx_vm_node_ip]['password'])
        send_host = Host(src_vm.local_ip, src_vm.vm_username,
                         src_vm.vm_password)
        rx_vm_node_ip = {}
        rx_local_host = {}
        recv_host = {}

        for dst_vm in dst_vm_list:
            rx_vm_node_ip[dst_vm] = dst_vm.vm_node_ip
            rx_local_host[dst_vm] = Host(
                rx_vm_node_ip[dst_vm],
                self.inputs.host_data[rx_vm_node_ip[dst_vm]]['username'],
                self.inputs.host_data[rx_vm_node_ip[dst_vm]]['password'])
            recv_host[dst_vm] = Host(dst_vm.local_ip, dst_vm.vm_username,
                                     dst_vm.vm_password)
        count = 0
        for stream in stream_list:
            profile[stream] = {}
            sender[stream] = {}
            receiver[stream] = {}
            for dst_vm in dst_vm_list:
                count = count + 1
                x = datetime.now().microsecond
                send_filename = "sendudp_" + str(x) + "_" + "%s" % count
                recv_filename = "recvudp_" + str(x) + "_" + "%s" % count
                profile[stream][dst_vm] = ContinuousProfile(
                    stream=stream, listener=dst_vm.vm_ip, chksum=True)
                sender[stream][dst_vm] = Sender(
                    send_filename, profile[stream][dst_vm], tx_local_host, send_host, self.inputs.logger)
                receiver[stream][dst_vm] = Receiver(
                    recv_filename, profile[stream][dst_vm], rx_local_host[dst_vm], recv_host[dst_vm], self.inputs.logger)
                receiver[stream][dst_vm].start()
                sender[stream][dst_vm].start()
        return sender, receiver
        # end scapy_start_traffic

    def verify_flow_thru_si(self, si_fix, src_vn=None, ecmp_hash=None, flow_count=3):
        self.logger.debug('Will start a tcpdump on the left interfaces '
            'of the SI to find out which flow is entering which SI')
        flowcount = 0
        result = True
        flow_pattern = {}
        svms = self.get_svms_in_si(si_fix)
        svms = sorted(set(svms))
        svm_list = si_fix.svm_list
        svm_index = 0
        vm_fix_pcap_pid_files = []

        # Capturing packets based upon source port
        src_port = str(SPORT)
        filters = '\'(src port %s)\'' % (src_port)
        if None in svms:
            svms.remove(None)
        for svm_fixture in svm_list:
            svm = svm_fixture.vm_obj
            if svm.status == 'ACTIVE':
                host_name = svm_fixture.get_host_of_vm()
                host = self.inputs.host_data[host_name]
                if src_vn is not None:
                    tapintf = self.connections.orch.get_vm_tap_interface(
                        svm_fixture.tap_intf[src_vn.vn_fq_name])
                else:
                    tapintf = self.connections.orch.get_vm_tap_interface(
                        svm_fixture.tap_intf[si_fix.left_vn_fq_name])
                    filters = ''
                if self.inputs.pcap_on_vm:
                    tcpdump_files = start_tcpdump_for_vm_intf(None,
                        [svm_list[svm_index]], None, filters=filters,
                        pcap_on_vm=True, vm_intf='eth1', svm=True)
                    svm_index = svm_index + 1
                    vm_fix_pcap_pid_files.append(tcpdump_files)
                else:
                    session = ssh(
                        host['host_ip'], host['username'], host['password'])
                    cmd = 'sudo tcpdump -nni %s %s -c 20 > /tmp/%s_out.log' % (
                        tapintf, filters, tapintf)
                    execute_cmd(session, cmd, self.logger)
            else:
                self.logger.info('%s is not in ACTIVE state' % svm.name)
        sleep(5)

        self.logger.info('%%%%% Will check the result of tcpdump %%%%%')
        svm_index = 0
        for svm_fixture in svm_list:
            svm = svm_fixture.vm_obj
            if svm.status == 'ACTIVE':
                svm_name = svm.name
                host_name = svm_fixture.get_host_of_vm()
                host = self.inputs.host_data[host_name]
                if src_vn is not None:
                    tapintf = self.connections.orch.get_vm_tap_interface(
                        svm_fixture.tap_intf[src_vn.vn_fq_name])
                else:
                    direction = 'left'
                    tapintf = self.connections.orch.get_vm_tap_interface(
                        svm_fixture.tap_intf[si_fix.left_vn_fq_name])
                if not self.inputs.pcap_on_vm:
                    session = ssh(
                        host['host_ip'], host['username'], host['password'])
                    output_cmd = 'cat /tmp/%s_out.log' % tapintf
                    out, err = execute_cmd_out(session, output_cmd, self.logger)
                else:
                    out, pkt_count = stop_tcpdump_for_vm_intf(
                        None, None, None, vm_fix_pcap_pid_files=vm_fix_pcap_pid_files[svm_index], svm=True)
                    svm_index = svm_index + 1
                    out = out[0]
                for i in range(0, flow_count):
                    dport = str(DPORT+i)
                    if dport in out:
                        flowcount = flowcount + 1
                        self.logger.info(
                            'Flow with dport %s seen flowing inside %s' % (dport,svm_name))
                        flow_pattern[dport] = svm_name
            else:
                self.logger.info('%s is not in ACTIVE state' % svm.name)
        if flowcount > 0:
            self.logger.info(
                'Flows are distributed across the Service Instances as :')
            self.logger.info('%s' % flow_pattern)
        else:
            result = False

        if ecmp_hash and ecmp_hash != 'default':
            # count the number of hash fields set
            hash_var_count = sum(ecmp_hash.values())

            # Incase, only one hash field is set, all flows should go through
            # single service instance. One exception here is destination_port.
            # Destination port varies for traffic streams.So, for destination
            # port, traffic will get load balanced even if ecmp hash is
            # configured "destination_port" alone.
            if hash_var_count == 1 and (not 'destination_port' in ecmp_hash):
                flow_pattern_ref = flow_pattern[str(DPORT)]
                if all(flow_pattern_ref  == item for item in flow_pattern.values()):
                    self.logger.info(
                        'Flows are flowing through Single Service Instance: %s, as per config hash: %s' % (flow_pattern_ref, ecmp_hash))
                    self.logger.info('%s' % flow_pattern)
                else:
                    self.logger.error(
                        'Flows are flowing through multiple Service Instances:%s, where as it should not as per config hash:%s' % (flow_pattern, ecmp_hash))
                    assert result, 'Config hash is not working for: %s' % ( ecmp_hash)
            # Incase, multiple ecmp hash fields are configured or default ecmp
            # hash is present or only 'destionation_port' is configured in
            # ecmp_hash
            else:
                flow_pattern_ref = flow_pattern[str(DPORT)]
                if all(flow_pattern_ref  == item for item in flow_pattern.values()):
                    result = False
                    self.logger.error(
                        'Flows are flowing through Single Service Instance:%s, where as it should not as per config hash:%s' % (flow_pattern_ref, ecmp_hash))
                    #assert result, 'Config hash is not working fine.'
                else:
                    self.logger.info(
                        'Flows are flowing through multiple Service Instances:%s, as per config hash: %s' % (flow_pattern, ecmp_hash))
                    self.logger.info('%s' % flow_pattern)
        else:
            assert result, 'No Flow distribution seen'

        # end verify_flow_thru_si

    def verify_flow_records(self, src_vm, src_ip=None, dst_ip=None, flow_count=3, protocol='17', traffic_objs=None):
        self.logger.info('Checking Flow records')
        vn_fq_name = src_vm.vn_fq_name
        items_list = src_vm.tap_intf[vn_fq_name].items()
        for items, values in items_list:
            if items == 'flow_key_idx':
                nh_id = values
        self.logger.debug('Flow Index of the src_vm is %s' % nh_id)
        inspect_h = self.agent_inspect[src_vm.vm_node_ip]

        proto_map = {'udp': '17', 'tcp': '6', 'icmp': '1'}
        flow_result = True
        if traffic_objs:
            for stream in traffic_objs:
                src_ip = stream.src_ip
                dst_ip = stream.dst_ip
                src_port = unicode(stream.sport)
                dest_port = unicode(stream.dport)
                protocol = proto_map.get(stream.proto) or str(stream.proto)
                flow_rec = inspect_h.get_vna_fetchflowrecord(nh=nh_id,
                    sip=src_ip, dip=dst_ip, sport=src_port, dport=dest_port,
                    protocol=protocol)
                if flow_rec is None:
                    flow_result = False
        else:
            for i in range(0, flow_count):
                src_port = unicode(SPORT)
                dest_port = unicode(DPORT+i)
                flow_rec = inspect_h.get_vna_fetchflowrecord(nh=nh_id,
                    sip=src_ip, dip=dst_ip, sport=src_port, dport=dest_port,
                    protocol=protocol)
                if flow_rec is None:
                    flow_result = False
        if flow_result:
            self.logger.info('Flow between %s and %s seen' % (dst_ip, src_ip))
        else:
            assert flow_result, 'Flow between %s and %s not seen' % ( dst_ip, src_ip)
        return True
        # end verify_flow_records
