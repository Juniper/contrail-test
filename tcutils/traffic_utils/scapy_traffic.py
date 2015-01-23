import os
import sys
from time import sleep
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))
from traffic.core.stream import Stream
from traffic.core.helpers import Host, Sender, Receiver
from traffic.core.profile import StandardProfile,\
    ContinuousProfile
from tcutils.util import get_random_name


def start_scapy(
        self,
        sender_vm,
        receiver_vm,
        proto,
        sport,
        dport,
        count=None,
        fip=None,
        recvr=True):

    if fip:
        stream = Stream(
            protocol="ip",
            sport=sport,
            dport=dport,
            proto=proto,
            src=sender_vm.vm_ip,
            dst=fip)
    else:
        stream = Stream(
            protocol="ip",
            sport=sport,
            dport=dport,
            proto=proto,
            src=sender_vm.vm_ip,
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
    random = get_random_name()
    send_name = 'send' + proto + '_' + random
    recv_name = 'recv' + proto + '_' + random
    sender = Sender(send_name,
                    profile, send_node, send_host, self.inputs.logger)
    receiver = Receiver(recv_name,
                        profile, recv_node, recv_host, self.inputs.logger)

    # start traffic
    if recvr:
        receiver.start()
    sender.start()

    return (sender, receiver)


def stop_scapy(self, sender, receiver, recvr=True):

    # stop traffic
    sender.stop()
    if recvr:
        receiver.stop()
    return (sender.sent, receiver.recv)
