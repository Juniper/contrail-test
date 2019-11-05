from __future__ import print_function
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
    def validate_route_deletion(self, vn_fq_name, si, dst_vm, src, intf_type='left', protocol=None, left_ri_ecmp=False):
        '''
        1]. Get a list of all RIs associted with the VN.
        2]. On the compute node housing the SI, get all the VRFs.
        3]. See if any one of the RIs match the VRF on the node.
        4]. Get the paths in that VRF and the next-hop to the destination.
        5]. The src is required because for Transparent SIs, the left and right VNs
            are different from those in the Service Chain.
        '''
        vn1 = self.connections.vnc_lib_fixture.virtual_network_read(
            fq_name=vn_fq_name.split(':'))
        ri_list = []
        itf_list = []
        itf_nh = None
        for ris in vn1.get_routing_instances():
            ri_fqn = (":").join(ris['to'])
            ri_list.append(ri_fqn)
        # Don't check route deletion in right vm's ri if intf_type is set to 'right'
        if intf_type == 'right':
            right_ri = '%s:%s' % (vn_fq_name, vn_fq_name.split(':')[2])
            ri_list.remove(right_ri)
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

            active_controller = None
            inspect_h1 = self.agent_inspect[svm_node_ip]
            agent_xmpp_status = inspect_h1.get_vna_xmpp_connection_status()
            for entry in agent_xmpp_status:
                if entry['cfg_controller'] == 'Yes':
                    active_controller = entry['controller_ip']
                    new_controller = self.inputs.host_data[
                        active_controller]['host_ip']
                    self.logger.info('Active control node is %s' % new_controller)
            ri_0 = ri_list[0]
            left_ri = False
            ri_list_new = []
            if left_ri_ecmp:  #This flag to check if more than 1 svc chains exist
                # Routes should be present in svc chain 1, removed from svc chain 0
                ri_list = ri_list[0:3]  # Routes removed from svc chain 0
                ri_list_new = ri_list[3::]  # Routes should be present in svc chain 1
            for ri in ri_list:
                if 'left' in ri:
                    left_ri = '%s:%s' % (vn_fq_name, vn_fq_name.split(':')[2])
                dst_vm_ip = True
                count = 0
                while dst_vm_ip:
                    dst_vm_ip = self.cn_inspect[new_controller].get_cn_route_table_entry(
                            ri_name=ri, prefix=dst_vm.vm_ip + '/' + net, protocol=protocol)
                    self.sleep(4)
                    count = count + 1
                    if count > 20:
                        break
                    if ri == left_ri and left_ri_ecmp: # left vn's ri to have more than 1 routes to dest
                        if len(dst_vm_ip) == left_ri_ecmp - 1:
                            self.logger.info('Multi Svc chains, 1 route deleted via svc0, Route %s exists via svc1 is %s routes %s' % (
                                dst_vm.vm_ip, left_ri_ecmp-1, dst_vm_ip))
                            dst_vm_ip = False
                    import pprint; pprint.pprint(dst_vm_ip); print("Route is \n\n")
                result = True
                if dst_vm_ip:
                    self.logger.error(
                        'Route to %s found in the Active Control-Node %s ri %s \n' %
                        (dst_vm.vm_ip, new_controller, ri))
                    result = False
                    assert result, 'Route to %s still found in the Active Control-Node ri %s %s \n' %(dst_vm.vm_ip, new_controller, ri)
                else:
                    self.logger.info('Route to %s not found in the Active Control-Node ri %s %s' %(dst_vm.vm_ip, new_controller, ri))
            if ri_list_new:
                for ri in ri_list_new:
                    dst_vm_ip = self.cn_inspect[new_controller].get_cn_route_table_entry(
                            ri_name=ri, prefix=dst_vm.vm_ip + '/' + net)
                    if dst_vm_ip:
                        self.logger.info(
                            'SVC 1 Route to %s found in the Active Control-Node %s ri %s' %
                            (dst_vm.vm_ip, new_controller, ri))
                    else:
                        result = False
                        assert result, 'Svc 1 Route to %s not found in the Active Control-Node ri %s %s' %(dst_vm.vm_ip, new_controller, ri)

            paths = inspect_h1.get_vna_active_route(
                vrf_id=vrf_id, ip=dst_vm.vm_ip, prefix=net)
            errmsg = "Route to %s seen in %s" % (dst_vm.vm_ip, vn_fq_name)
            if paths:
                if protocol == 'ServiceChain':
                    self.logger.info("Path present in the agent %s" % (paths))
                else:
                    self.logger.warn(errmsg)
                    return False, errmsg
            else:
                self.logger.info("Route deletion from %s verified" % (ri_list))
        return True, "Route deletion verified"

    @retry(delay=5, tries=25)
    def validate_svc_action(self, vn_fq_name, si, dst_vm, src, check_si_as_nh=True, check_rt_in_control=False, protocol=None, left_ri_ecmp=False):
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
        vrf_match_list = []
        itf_nh = None
        for ris in vn1.get_routing_instances():
            ri_fqn = (":").join(ris['to'])
            ri_list.append(ri_fqn)
        vrf_id = None
        for svm in si.svm_list:
            svm_node_ip = self.inputs.host_data[svm.vm_node_ip]['host_ip']
            svm_node_name = self.inputs.host_data[svm.vm_node_ip]['name']
            inspect_h1 = self.connections.agent_inspect[svm_node_ip]
            vrf_match_list = [vn_fq_name, si.si_name]
            for vrf_list in inspect_h1.get_vna_vrf_list()['VRFs']:
                if all(x in vrf_list['name'] for x in vrf_match_list):
                    vrf_id = vrf_list['ucindex']
                    break
            errmsg = "RI not created for the SVC"
            if not vrf_id:
                self.logger.warn(errmsg)
                return False, errmsg
            net = '32'
            if self.inputs.get_af() == 'v6':
                net = '128'
            if check_rt_in_control:
                active_controller = None
                inspect_h1 = self.agent_inspect[svm_node_ip]
                agent_xmpp_status = inspect_h1.get_vna_xmpp_connection_status()
                for entry in agent_xmpp_status:
                    if entry['cfg_controller'] == 'Yes':
                        active_controller = entry['controller_ip']
                        new_controller = self.inputs.host_data[
                            active_controller]['host_ip']
                        self.logger.info('Active control node is %s' % new_controller)
                ri_0 = ri_list[0]
                left_ri = False
                if 'left' in ri_list:
                    left_ri = '%s:%s' % (vn_fq_name, vn_fq_name.split(':')[2])
                if si.svc_template.service_template_properties.service_mode == 'transparent':
                    if not inspect_h1.get_vna_tap_interface({'vn':vn_fq_name}):
                        ri_list.remove(vn_fq_name + ':' + vn1.name)

                for ri in ri_list:
                    dst_vm_ip = self.cn_inspect[new_controller].get_cn_route_table_entry(
                            ri_name=ri, prefix=dst_vm.vm_ip + '/' + net)
                    if ri == left_ri and left_ri_ecmp:
                        if left_ri_ecmp != len(dst_cm_ip):
                            self.logger.error('Number of routes exepcted %s' % len(left_ri_ecmp))
                            assert False
                        self.logger.info('Number of routes found %s, routes are %s' % len(left_ri_ecmp, dst_vm_ip))
                    result = True
                    if dst_vm_ip:
                        self.logger.info(
                            'Route to %s found in the Active Control-Node %s ri %s' %
                            (dst_vm.vm_ip, new_controller, ri))
                    else:
                        result = False
                        assert result, 'Route to %s not found in the Active Control-Node ri %s %s' %(dst_vm.vm_ip, new_controller, ri)

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
            if check_si_as_nh:
                if svm.get_tap_intf_of_vmi(svm_vmi_id)['name'] != itf_nh and svm.get_tap_intf_of_vmi(svm_vmi_id)['name'] not in itf_list:
                    self.logger.warn(errmsg)
                    return False, errmsg
                self.logger.info('Route to %s seen in VRF:%s on %s, and SI %s is seen as the NH' % (
                    dst_vm.vm_ip, vrf_id, svm_node_name, si.si_name))
            else:
                self.logger.info('Route to %s seen in VRF:%s on %s, SI as the NH check not required' % (
                    dst_vm.vm_ip, vrf_id, svm_node_name))
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
        evpn = ret_dict.get('evpn')

        assert st_fixture.verify_on_setup(), 'ST Verification failed'
        # SVM would have been up in config_svc_chain() itself
        # So no need to wait for vms to be up
        assert si_fixture.verify_on_setup(wait_for_vms=False), \
            ('SI Verification failed')

        if not evpn:
            result, msg = self.validate_vn(left_vn_fq_name)
            assert result, msg
            right_vn = True if st_fixture.service_mode == 'in-network-nat' else False
            result, msg = self.validate_vn(right_vn_fq_name, right_vn=right_vn)
            assert result, msg
        else:
            left_lr_child_vn_fq_name = ret_dict.get('left_lr_child_vn_fixture').vn_fq_name
            result, msg = self.validate_vn(left_lr_child_vn_fq_name,
                                           right_vn=True)
            assert result, msg
            right_lr_child_vn_fq_name = ret_dict.get('right_lr_child_vn_fixture').vn_fq_name
            result, msg = self.validate_vn(right_lr_child_vn_fq_name,
                                           right_vn=True)
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
        svm_fixtures = si_fixture.svm_list
        for svm in svm_fixtures:
            svm_name = svm.vm_name
            host = self.inputs.host_data[svm.vm_node_ip]
            #tapintf = self.get_svm_tapintf(svm_name)
            tapintf = list(svm.tap_intf.values())[0]['name']
            session = ssh(host['host_ip'], host['username'], host['password'])
            pcap_vm = self.inputs.pcap_on_vm
            pcap = self.start_tcpdump(session, tapintf, pcap_on_vm=pcap_vm)
            sessions.update({svm_name: (session, pcap)})

        if self.inputs.pcap_on_vm:
            conn_list = []
            svm_list = si_fixture._svm_list
            vm_fix_pcap_pid_files = self.start_tcpdump(None, tap_intf='eth0', vm_fixtures=svm_list, pcap_on_vm=True)
            conn_list.append(vm_fix_pcap_pid_files)
            conn_list.append(sessions)
            return conn_list

        return sessions
