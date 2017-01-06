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
from traffic.core.stream import Stream                                                                                                                                                                                                      
from traffic.core.profile import StandardProfile, ContinuousProfile, ContinuousSportRange
from traffic.core.helpers import Host, Sender, Receiver
from common.servicechain.config import ConfigSvcChain

class VerifySvcChain(ConfigSvcChain):

    def verify_si(self, si_fixture):
        return si_fixture.verify_on_setup()

    def verify_sis(self, si_fixtures):
        result = True
        for si_fix in si_fixtures:
            result = result and si_fix.verify_on_setup()
        return result

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
        assert si_fixture.verify_on_setup(), 'SI Verification failed'

        result, msg = self.validate_vn(left_vn_fq_name)
        assert result, msg
        right_vn = True if st_fixture.service_mode == 'in-network-nat' else False
        result, msg = self.validate_vn(right_vn_fq_name, right_vn=right_vn)
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
