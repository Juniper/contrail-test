from traffic.core.stream import Stream
from traffic.core.helpers import Host, Sender, Receiver
from traffic.core.profile import StandardProfile,\
    ContinuousProfile
from tcutils.util import get_random_name
from base_traffic import *
sys.path.append(os.path.realpath('tcutils/pkgs/Traffic'))

class Scapy(BaseTraffic):

    def __init__(self):

        self.sender = None
        self.receiver = None
        self.sent = None
        self.recv = None

    def start(
            self,
            sender_vm,
            receiver_vm,
            proto,
            sport,
            dport,
            pkt_count=None,
            fip=None):

        self.sender_vm = sender_vm
        self.receiver_vm = receiver_vm
        self.proto = proto
        self.sport = sport
        self.dport = dport
        self.inputs = sender_vm.inputs
        self.logger = self.inputs.logger
        self.pkt_count = pkt_count
        self.fip = fip

        if self.fip:
            stream = Stream(
                protocol="ip",
                sport=self.sport,
                dport=self.dport,
                proto=self.proto,
                src=self.sender_vm.vm_ip,
                dst=self.fip)
        else:
            stream = Stream(
                protocol="ip",
                sport=self.sport,
                dport=self.dport,
                proto=self.proto,
                src=self.sender_vm.vm_ip,
                dst=self.receiver_vm.vm_ip)
        profile_kwargs = {'stream': stream}
        if self.fip:
            profile_kwargs.update({'listener': self.receiver_vm.vm_ip})
        if self.pkt_count:
            profile_kwargs.update({'count': self.pkt_count})
            profile = StandardProfile(**profile_kwargs)
        else:
            profile = ContinuousProfile(**profile_kwargs)

        # Set VM credentials
        send_node = Host(self.sender_vm.vm_node_ip,
                         self.sender_vm.inputs.host_data[self.sender_vm.vm_node_ip]['username'],
                         self.sender_vm.inputs.host_data[self.sender_vm.vm_node_ip]['password'])
        recv_node = Host(self.receiver_vm.vm_node_ip,
                         self.sender_vm.inputs.host_data[self.receiver_vm.vm_node_ip]['username'],
                         self.sender_vm.inputs.host_data[self.receiver_vm.vm_node_ip]['password'])
        send_host = Host(self.sender_vm.local_ip,
                         self.sender_vm.vm_username, self.sender_vm.vm_password)
        recv_host = Host(self.receiver_vm.local_ip,
                         self.receiver_vm.vm_username, self.receiver_vm.vm_password)

        # Create send, receive helpers
        random = get_random_name()
        send_name = 'send' + self.proto + '_' + random
        recv_name = 'recv' + self.proto + '_' + random
        sender = Sender(send_name,
                        profile, send_node, send_host, self.logger)
        receiver = Receiver(recv_name,
                            profile, recv_node, recv_host, self.logger)

        # start traffic
        receiver.start()
        sender.start()

        self.sender = sender
        self.receiver = receiver
        return True 


    def stop(self):

        # stop traffic
        self.sender.stop()
        self.receiver.stop()

        self.sent = self.sender.sent
        self.recv= self.receiver.recv

        return self.get_packet_count()

    def get_packet_count(self):

        self.logger.info("Sent : %s, Received: %s" % (self.sent, self.recv))
        return (self.sent, self.recv)

