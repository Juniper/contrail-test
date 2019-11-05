from __future__ import print_function
from common.neutron.base import BaseNeutronTest
from tcutils.util import get_random_name, retry
from tcutils.traffic_utils.base_traffic import BaseTraffic, SCAPY
from vnc_api.vnc_api import NoIdError, BadRequest
import re

class BaseDataPathEncryption(BaseNeutronTest):
    @classmethod
    def setUpClass(cls):
        super(BaseDataPathEncryption, cls).setUpClass()
        cls.project_name = cls.inputs.project_name
        cls.domain_name = cls.inputs.domain_name
        cls.vnc_h = cls.connections.orch.vnc_h
        cls.vr_ip_address = cls.get_vr_ip_addresses()
    # end setUpClass

    @classmethod
    def tearDownClass(cls):
        cls.disable_encryption()
        super(BaseDataPathEncryption, cls).tearDownClass()
    # end tearDownClass

    @classmethod
    def get_vr_ip_addresses(cls):
        vr_ip_address = dict()
        for compute_name in cls.inputs.compute_names:
            vr_obj = cls.vnc_h.read_virtual_router(compute_name)
            vr_ip_address[compute_name] = vr_obj.virtual_router_ip_address
        return vr_ip_address

    def is_test_applicable(self):
        if len(self.inputs.compute_names) < 2:
            return (False, 'Need atleast 2 compute nodes')
        if not self.inputs.is_dp_encryption_enabled:
            return (False, 'Datapath Encryption is not enabled')
        return (True, None)

    def _get_vr_ip_addresses(self, compute_names):
        vrouters = list()
        for compute_name in compute_names:
            vrouters.append(self.vr_ip_address[compute_name])
        return vrouters

    def enable_encryption(self, compute_names=None):
        compute_names = compute_names or self.inputs.compute_names
        self.add_vrouter_to_encryption(compute_names)

    def add_vrouter_to_encryption(self, compute_names):
        vrouters = self._get_vr_ip_addresses(compute_names)
        self.logger.info('Enabling vrouter encryption for computes %s'%vrouters)
        self.vnc_h.add_vrouter_to_encryption(vrouters)

    def delete_vrouter_from_encryption(self, compute_names):
        vrouters = self._get_vr_ip_addresses(compute_names)
        self.logger.info('Disabling vrouter encryption for computes %s'%vrouters)
        self.vnc_h.delete_vrouter_from_encryption(vrouters)

    @classmethod
    def disable_encryption(self):
        self.logger.info('Disabling vrouter encryption for all computes')
        self.vnc_h.disable_datapath_encryption()

    def validate_tunnels(self, vrouters=None, endpoints=None):
        vrouters = vrouters if vrouters is not None else self.inputs.compute_names
        endpoints = endpoints or list()
        for vrouter in vrouters:
            assert self.validate_established_tunnels(vrouter, endpoints)
            assert self.check_crypt_endpoint_on_agent(vrouter, endpoints)

    @retry(tries=6, delay=5)
    def validate_established_tunnels(self, vrouter, endpoints):
        node = self.inputs.get_host_ip(vrouter)
        self_ip = self.vr_ip_address[vrouter]
        exp_vrouters = set(self._get_vr_ip_addresses(endpoints)) - set([self_ip])
        cmd = 'strongswan status | grep ESTABLISHED'
        output = self.inputs.run_cmd_on_server(node, cmd, container='strongswan')
        pattern = 'ESTABLISHED.*%s\[.*\]...(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})'%(self_ip)
        curr_vrouters = re.findall(pattern, output)
        if not curr_vrouters and endpoints:
            self.logger.warn('No Established tunnels from %s'%vrouter)
            return False
        if exp_vrouters.symmetric_difference(set(curr_vrouters)):
            self.logger.warn('exp tunnels from %s to %s, got: %s'%(
                             self_ip, exp_vrouters, curr_vrouters))
            return False
        self.logger.info('Validated tunnels established from %s to %s'%(
                         vrouter, endpoints))
        return True

    @retry(tries=6, delay=5)
    def check_crypt_endpoint_on_agent(self, vrouter, endpoints):
        node = self.inputs.get_host_ip(vrouter)
        self_ip = self.vr_ip_address[vrouter]
        exp_vrouters = set(self._get_vr_ip_addresses(endpoints)) - set([self_ip])
        agent_h = self.connections.agent_inspect[node]
        nh_list = agent_h.get_nh_list(nh_type='tunnel')
        for nh in nh_list:
            if nh['dip'] in exp_vrouters:
               if nh['crypt_all_traffic'] != 'true':
                   self.logger.warn('crypt_all_traffic is not set for'
                                    ' %s from %s'%(nh['dip'], vrouter))
                   return False
               if nh['crypt_path_available'] != 'true':
                   self.logger.warn('crypt path not available for %s from %s'%(
                                    nh['dip'], vrouter))
                   return False
               if nh['crypt_interface'] != 'crypt0':
                   self.logger.warn('crypt intf is not crypt0 for nh %s in %s'%(
                                    nh['dip'], vrouter))
                   return False
            else:
               if nh['crypt_interface'] == 'crypt0':
                   self.logger.warn('crypt intf shouldnt be set for nh'
                       ' %s in %s'%(nh['dip'], vrouter))
                   return False
               if nh['crypt_path_available'] == 'true':
                   self.logger.warn('crypt path available shouldnt be set'
                      ' for %s from %s'%(nh['dip'], vrouter))
                   return False
               if nh['crypt_all_traffic'] == 'true':
                   self.logger.warn('crypt_all_traffic shouldnt be set for'
                                    ' %s from %s'%(nh['dip'], vrouter))
                   return False
        self.logger.info('Validated crypt endpoints on %s'%vrouter)
        return True

    def get_crypt_stats(self, source_vrouter, destination_vrouter):
        src_ip = self.vr_ip_address[source_vrouter]
        dst_ip = self.vr_ip_address[destination_vrouter]
        cmd1 = 'ip -s xfrm state list src %s dst %s'%(src_ip, dst_ip)
        cmd2 = 'ip -s xfrm state list src %s dst %s'%(dst_ip, src_ip)
        pattern = 'bytes\), (?P<pkts>\d+)\(packets'
        snode = self.inputs.get_host_ip(source_vrouter)
        dnode = self.inputs.get_host_ip(destination_vrouter)
        output1 = self.inputs.run_cmd_on_server(snode, cmd1, container='strongswan')
        output2 = self.inputs.run_cmd_on_server(dnode, cmd2, container='strongswan')
        match = re.search(pattern, output1, re.M)
        spkts = match.group('pkts') if match else None
        match = re.search(pattern, output2, re.M)
        dpkts = match.group('pkts') if match else None
        return (spkts, dpkts)

    def start_traffic(self, src_vm, dst_vm, proto, sport,
                      dport, src_vn_fqname=None, dst_vn_fqname=None,
                      af=None, fip_ip=None):
        traffic_obj = BaseTraffic.factory(tool=SCAPY, proto=proto)
        assert traffic_obj.start(src_vm, dst_vm, proto, sport,
                                 dport, sender_vn_fqname=src_vn_fqname,
                                 receiver_vn_fqname=dst_vn_fqname, af=af,
                                 interval=1, fip=fip_ip)
        return traffic_obj

    def poll_traffic(self, traffic_obj, interval=5, expectation=True):
        (initial_sent, initial_recv) = traffic_obj.poll()
        self.sleep(interval)
        (curr_sent, curr_recv) = traffic_obj.poll()
        assert (curr_sent - initial_sent) > 1, 'Seems the traffic is stopped in the sender'
        recv = curr_recv - initial_recv
        msg = 'recvd %s pkts which is not expected'%recv
        assert (recv and expectation) or not(recv or expectation), msg

    def stop_traffic(self, traffic_obj, expectation=True, validate=True):
        sent, recv = traffic_obj.stop()
        msg = "transferred between %s and %s, proto %s sport %s and dport %s"%(
               traffic_obj.src_ip, traffic_obj.dst_ip, traffic_obj.proto,
               traffic_obj.sport, traffic_obj.dport)
        if validate:
            if not expectation:
                assert sent or traffic_obj.proto == 'tcp', "Packets not %s"%msg
                assert not recv, "Packets %s"%msg
            else:
                assert sent and recv, "Packets not %s"%msg
                if recv*100/float(sent) < 95:
                    assert False, "Packets not %s"%msg
        return (sent, recv)

    def verify_ping(self, src_vm, dst_vm, af=None, expectation=True, size='56'):
        assert src_vm.ping_with_certainty(dst_vm_fixture=dst_vm, af=af,
                                          expectation=expectation, size=size)
        return True

    def verify_traffic(self, src_vm, dst_vm, proto, sport=0, dport=0,
                       src_vn_fqname=None, dst_vn_fqname=None, af=None,
                       fip_ip=None, expectation=True, size='56'):
        if proto == 'icmp':
            return self.verify_ping(src_vm, dst_vm, af, expectation, size=size)
        traffic_obj = self.start_traffic(src_vm, dst_vm, proto,
                                  sport, dport, src_vn_fqname=src_vn_fqname,
                                  dst_vn_fqname=dst_vn_fqname, af=af,
                                  fip_ip=fip_ip)
        return self.stop_traffic(traffic_obj, expectation)

    def verify_encrypt_traffic(self, src_vm, dst_vm, proto='icmp', encrypt=True, **kwargs):
        src_vrouter = self.inputs.get_node_name(src_vm.vm_node_ip)
        dst_vrouter = self.inputs.get_node_name(dst_vm.vm_node_ip)
        before_src, before_dst = self.get_crypt_stats(src_vrouter, dst_vrouter)
        self.verify_traffic(src_vm, dst_vm, proto, **kwargs)
        after_src, after_dst = self.get_crypt_stats(src_vrouter, dst_vrouter)
        print(before_src, before_dst, after_src, after_dst)
        if encrypt:
            assert (before_src != after_src) and (before_dst != after_dst)
        else:
            assert not (before_src or before_dst or after_src or after_dst)

    def verify_encrypt_traffic_bw_hosts(self, src_vrouter, dst_vrouter, dport,
                                        encrypt=True, expectation=True):
        cmd='python -mSimpleHTTPServer %s >& /tmp/ignore.ctest'%dport
        index_cmd = 'echo %s >& index.html'%dst_vrouter
        kill_cmd = 'pkill -f SimpleHTTPServer'
        curl_cmd = 'timeout 15 curl -i %s:%s'%(self.inputs.get_host_data_ip(dst_vrouter), dport)
        self.inputs.run_cmd_on_server(dst_vrouter, index_cmd)
        self.inputs.run_cmd_on_server(dst_vrouter, cmd, as_daemon=True)
        self.sleep(15)
        self.addCleanup(self.inputs.run_cmd_on_server, dst_vrouter, kill_cmd)
        before_src, before_dst = self.get_crypt_stats(src_vrouter, dst_vrouter)
        output = self.inputs.run_cmd_on_server(src_vrouter, curl_cmd)
        if "200 OK" in output and not expectation:
            assert False, 'Traffic should have been dropped'
        elif "200 OK" not in output and expectation:
            assert False, 'Traffic should have been allowed'
        after_src, after_dst = self.get_crypt_stats(src_vrouter, dst_vrouter)
        print(before_src, before_dst, after_src, after_dst)
        msg = 'non tunneled traffic shouldnt be encrypted'
        assert (before_src == after_src) and (before_dst == after_dst), msg
