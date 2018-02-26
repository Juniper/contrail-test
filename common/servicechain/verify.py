import os
import sys
from time import sleep

import fixtures
import testtools                                                                                                                                                                                                                            
import unittest                                                                                                                                                                                                                           
import types                                                                                                                                                                                                                                
import time
trafficdir = os.path.join(os.path.dirname(__file__), '../../tcutils/pkgs/Traffic')
sys.path.append(trafficdir)
from tcutils.util import retry
from tcutils.commands import ssh
from traffic.core.stream import Stream                                                                                                                                                                                                      
from traffic.core.profile import StandardProfile, ContinuousProfile, ContinuousSportRange
from traffic.core.helpers import Host, Sender, Receiver
from common.servicechain.config import ConfigSvcChain

class VerifySvcChain(ConfigSvcChain):

    def verify_si(self, si_fixture, wait_for_vms=True):
        return si_fixture.verify_on_setup(wait_for_vms=wait_for_vms)

    def verify_sis(self, si_fixtures, wait_for_vms=True):
        result = True
        for si_fix in si_fixtures:
            result = result and si_fix.verify_on_setup(wait_for_vms=wait_for_vms)
        return result

    @retry(delay=5, tries=25)
    def validate_svc_action(self, vn_fq_name, si, dst_vm, src):
        '''
        1]. Get a list of all RIs associted with the VN.
        2]. On the compute node housing the SI, get all the VRFs.
        3]. See if any one of the RIs match the VRF on the node.
        4]. Get the paths in that VRF and the next-hop to the destination.  
        5]. The src is required because for Transparent SIs, the left and right VNs 
            are different from those in the Service Chain.
        '''
        if si.svc_template.get_service_template_properties().service_type == 'analyzer':
            return True, "Skip this check for Analyser"
        vn1 = self.connections.vnc_lib_fixture.virtual_network_read(
            fq_name=vn_fq_name.split(':'))
        ri_list = []
        itf_list = []
        itf_nh = None
        for ris in vn1.get_routing_instances():
            ri_fqn = (":").join(ris['to'])
            ri_list.append(ri_fqn)
        vrf_id = None
        for svm in si.svm_list:
            svm_node_ip = self.inputs.host_data[svm.vm_node_ip]['host_ip']
            svm_node_name = self.inputs.host_data[svm.vm_node_ip]['name']
            inspect_h1 = self.connections.agent_inspect[svm_node_ip]
            for vrf_list in inspect_h1.get_vna_vrf_list()['VRFs']:
                if vrf_list['name'] in ri_list:
                    vrf_id = vrf_list['ucindex']
                    break
            errmsg = "RI not created for the SVC"
            if not vrf_id:
                self.logger.warn(errmsg)
                return False, errmsg
            net = '32'
            if self.inputs.get_af() == 'v6':
                net = '128'
            paths = inspect_h1.get_vna_active_route(
                vrf_id=vrf_id, ip=dst_vm.vm_ip, prefix=net)
            errmsg = "Route to %s not seen in %s" % (dst_vm.vm_ip, vn_fq_name)
            if not paths:
                self.logger.warn(errmsg)
                return False, errmsg
            next_hops = paths['path_list'][0]['nh']
            if 'ECMP' in next_hops['type']:
                for entry in next_hops['mc_list']:
                    if entry['type'] == 'Interface' or entry['type'] == 'Vlan':
                        itf_list.append(entry['itf'])
            elif next_hops['type'] == 'interface' or next_hops['type'] == 'vlan':
                itf_nh = next_hops['itf']
            else:
                itf_nh = None
            errmsg = "SI is not seen as NH to reach %s from %s" % (
                dst_vm.vm_ip, vn_fq_name)
            if src == 'left':
                si_vn = si.left_vn_fq_name
            elif src == 'right':
                si_vn = si.right_vn_fq_name
            svm_vmi_id = svm.get_vmi_ids()[si_vn]
            if svm.get_tap_intf_of_vmi(svm_vmi_id)['name'] != itf_nh and svm.get_tap_intf_of_vmi(svm_vmi_id)['name'] not in itf_list:
                self.logger.warn(errmsg)
                return False, errmsg
            self.logger.info('Route to %s seen in VRF:%s on %s, and SI %s is seen as the NH' % (
                dst_vm.vm_ip, vrf_id, svm_node_name, si.si_name))
        return True, "Route-leak and NH change verified"
    # end validate_svc_action

    @retry(delay=5, tries=15)
    def validate_vn(self, vn_fq_name, right_vn=False):
        '''
        vn_fq_name : VN fq_name_str
        '''
        ri_fq_name = vn_fq_name.split(':')
        ri_fq_name.append(ri_fq_name[-1])
        ri_obj = self.connections.vnc_lib_fixture.routing_instance_read(fq_name=ri_fq_name)
        errmsg = "RI object not found for RI: %s" % ri_fq_name
        if not ri_obj:
            self.logger.warn(errmsg)
            return False, errmsg

        vmi_refs = ri_obj.get_virtual_machine_interface_back_refs()
        errmsg = "VMI refs is none for RI %s" % ri_fq_name
        if not vmi_refs:
            self.logger.warn(errmsg)
            return False, errmsg
        if right_vn == False:
            ri_refs = ri_obj.get_routing_instance_refs()
            errmsg = "RI refs is none for RI %s" % ri_fq_name
            if not ri_refs:
                self.logger.warn(errmsg)
                return False, errmsg

        self.logger.info('VMI and/or RI refs are present for VN %s' % (vn_fq_name))
        return True, "VN valdation passed."

    def verify_traffic(self, sender_vm, receiver_vm, proto, sport, dport, count=None, fip=None):
        # Create stream and profile
        if fip:
            stream = Stream(
                sport=sport, dport=dport, proto=proto, src=sender_vm.vm_ip,
                dst=fip)
        else:
            stream = Stream(
                sport=sport, dport=dport, proto=proto, src=sender_vm.vm_ip,
                dst=receiver_vm.vm_ip)
        profile_kwargs = {'stream': stream}
        if fip:
            profile_kwargs.update({'listener': receiver_vm.vm_ip})
        if count:
            profile_kwargs.update({'count': count})
            profile = StandardProfile(**profile_kwargs)
        else:
            profile = ContinuousProfile(**profile_kwargs)

        # Set VM credentials
        send_node = Host(sender_vm.vm_node_ip,
                      self.inputs.host_data[sender_vm.vm_node_ip]['username'],
                      self.inputs.host_data[sender_vm.vm_node_ip]['password'])
        recv_node = Host(receiver_vm.vm_node_ip,
                      self.inputs.host_data[receiver_vm.vm_node_ip]['username'],
                      self.inputs.host_data[receiver_vm.vm_node_ip]['password'])
        send_host = Host(sender_vm.local_ip,
                         sender_vm.vm_username, sender_vm.vm_password)
        recv_host = Host(receiver_vm.local_ip,
                         receiver_vm.vm_username, receiver_vm.vm_password)

        # Create send, receive helpers
        sender = Sender("send%s" %
                        proto, profile, send_node, send_host, self.inputs.logger)
        receiver = Receiver("recv%s" %
                            proto, profile, recv_node, recv_host, self.inputs.logger)

        # start traffic
        receiver.start()
        sender.start()
        sleep(5)

        # stop traffic
        sender.stop()
        receiver.stop()
        self.logger.debug("Sent: %s; Received: %s", sender.sent, receiver.recv)
        return (sender.sent, receiver.recv)

    def verify_svc_chain(self, *args, **kwargs):
        svc_chain_info = kwargs.get('svc_chain_info')
        ret_dict = svc_chain_info or self.config_svc_chain(*args, **kwargs)
        proto = kwargs.get('proto', 'any')
        left_vn_fq_name = ret_dict.get('left_vn_fixture').vn_fq_name
        right_vn_fq_name = ret_dict.get('right_vn_fixture').vn_fq_name
        left_vm_fixture = ret_dict.get('left_vm_fixture')
        right_vm_fixture = ret_dict.get('right_vm_fixture')
        st_fixture = ret_dict.get('st_fixture')
        si_fixture = ret_dict.get('si_fixture')

        assert st_fixture.verify_on_setup(), 'ST Verification failed'
        # SVM would have been up in config_svc_chain() itself
        # So no need to wait for vms to be up
        assert si_fixture.verify_on_setup(wait_for_vms=False), \
            ('SI Verification failed')

        result, msg = self.validate_vn(left_vn_fq_name)
        assert result, msg
        right_vn = True if st_fixture.service_mode == 'in-network-nat' else False
        result, msg = self.validate_vn(right_vn_fq_name, right_vn=right_vn)
        assert result, msg

        result, msg = self.validate_svc_action(
            left_vn_fq_name, si_fixture, right_vm_fixture, src='left')
        assert result, msg
        if st_fixture.service_mode != 'in-network-nat':
            result, msg = self.validate_svc_action(
                right_vn_fq_name, si_fixture, left_vm_fixture, src='right')
            assert result, msg
        if proto not in ['any', 'icmp']:
            self.logger.info('Will skip Ping test')
        else:
            # Ping from left VM to right VM
            errmsg = "Ping to Right VM %s from Left VM failed" % right_vm_fixture.vm_ip
            assert left_vm_fixture.ping_with_certainty(
                right_vm_fixture.vm_ip, count='3'), errmsg
        return ret_dict
    # end verify_svc_chain

    def tcpdump_on_all_analyzer(self, si_fixture):
        sessions = {}
        svms = self.get_svms_in_si(si_fixture)
        svm_fixtures = si_fixture.svm_list
        for svm in svm_fixtures:
            svm_name = svm.vm_name
            host = self.inputs.host_data[svm.vm_node_ip]
            #tapintf = self.get_svm_tapintf(svm_name)
            tapintf = svm.tap_intf.values()[0]['name']
            session = ssh(host['host_ip'], host['username'], host['password'])
            pcap = self.start_tcpdump(session, tapintf)
            sessions.update({svm_name: (session, pcap)})

        if self.inputs.pcap_on_vm:
            conn_list = []
            svm_list = si_fixture._svm_list
            vm_fix_pcap_pid_files = self.start_tcpdump(None, tap_intf='eth0', vm_fixtures=svm_list, pcap_on_vm=True)
            conn_list.append(vm_fix_pcap_pid_files)
            conn_list.append(sessions)
            return conn_list

        return sessions
