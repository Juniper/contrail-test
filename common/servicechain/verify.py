import os
import sys
from time import sleep

import fixtures
import testtools                                                                                                                                                                                                                            
import unittest                                                                                                                                                                                                                           
import types                                                                                                                                                                                                                                
import time
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))                                                                                                                                                                                  
from tcutils.util import retry
from traffic.core.stream import Stream                                                                                                                                                                                                      
from traffic.core.profile import StandardProfile, ContinuousProfile, ContinuousSportRange
from traffic.core.helpers import Host, Sender, Receiver

class VerifySvcChain(fixtures.TestWithFixtures):

    def verify_si(self, si_fixtures):
        for si_fix in si_fixtures:
            si_fix.verify_on_setup()

    @retry(delay=5, tries=6)
    def validate_vn(self, vn_name, domain_name='default-domain',
                    project_name='admin'):
        ri_fq_name = [domain_name, project_name, vn_name, vn_name]
        ri_obj = self.vnc_lib.routing_instance_read(fq_name=ri_fq_name)
        errmsg = "RI object not found for RI: %s" % ri_fq_name
        if not ri_obj:
            self.logger.warn(errmsg)
            return False, errmsg

        vmi_refs = ri_obj.get_virtual_machine_interface_back_refs()
        errmsg = "VMI refs is none for RI %s" % ri_fq_name
        if not vmi_refs:
            self.logger.warn(errmsg)
            return False, errmsg

        ri_refs = ri_obj.get_routing_instance_refs()
        errmsg = "RI refs is none for RI %s" % ri_fq_name
        if not ri_refs:
            self.logger.warn(errmsg)
            return False, errmsg

        return True, "VN valdation passed."

    def verify_traffic(self, sender_vm, receiver_vm, proto, sport, dport, count=None, fip=None):
        # Create stream and profile
        if fip:
            stream = Stream(
                protocol="ip", sport=sport, dport=dport, proto=proto, src=sender_vm.vm_ip,
                dst=fip)
        else:
            stream = Stream(
                protocol="ip", sport=sport, dport=dport, proto=proto, src=sender_vm.vm_ip,
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
