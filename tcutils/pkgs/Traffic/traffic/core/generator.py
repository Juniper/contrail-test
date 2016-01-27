"""Module to send packets.
"""
import os
import socket
import signal
import traceback
from time import sleep
from optparse import OptionParser
from multiprocessing import Process, Event

from scapy.all import send, sr1, sendpfast
from scapy.packet import Raw
from scapy.layers.inet import Ether, IP, UDP, TCP, ICMP
from scapy.layers.inet6 import IPv6, ICMPv6EchoRequest

try:
    # Running from the source repo "test".
    from tcutils.pkgs.Traffic.traffic.core.profile import *
    from tcutils.pkgs.Traffic.traffic.core.tcpclient import *
    from tcutils.pkgs.Traffic.traffic.utils.logger import LOGGER, get_logger
    from tcutils.pkgs.Traffic.traffic.utils.globalvars import LOG_LEVEL
    from tcutils.pkgs.Traffic.traffic.utils.util import is_v6
except ImportError:
    # Distributed and installed as package
    from traffic.core.profile import *
    from traffic.core.tcpclient import *
    from traffic.utils.logger import LOGGER, get_logger
    from traffic.utils.globalvars import LOG_LEVEL
    from traffic.utils.util import is_v6

LOGGER = "%s.core.generator" % LOGGER
log = get_logger(name=LOGGER, level=LOG_LEVEL)
SRC_PORT = 8000


class CreatePkt(object):

    def __init__(self, profile):
        self.profile = profile
        self.stream = profile.stream
        self._str_port_to_int()
        log.debug("Stream: %s", self.stream.__dict__)
        log.debug("Stream L3: %s", self.stream.l3.__dict__)
        if self.stream.l4 is not None:
            log.debug("Stream L4: %s", self.stream.l4.__dict__)
        self.pkt = None
        self._create()
        if isinstance(self.profile, ContinuousSportRange):
            self.pkts = self._create_pkts()

    def _str_port_to_int(self):
        try:
            self.stream.l4.sport = int(self.stream.l4.sport)
        except AttributeError:
            if self.stream.get_l4_proto() in ['udp', 'tcp']:
                self.stream.l4.sport = SRC_PORT
        try:
            self.stream.l4.dport = int(self.stream.l4.dport)
        except AttributeError:
            pass

    def _create(self):
        l2_hdr = None
        # To incease rate, we need to send pkt at L2 usinf sendpfast
        if isinstance(self.profile, ContinuousSportRange):
            l2_hdr = self._l2_hdr()
        l3_hdr = self._l3_hdr()
        l4_hdr = self._l4_hdr()
        if self.stream.get_l4_proto() == 'icmpv6':
            self.profile.size = 0
        self.payload = self._payload()
        if l2_hdr:
            log.debug("L2 Header: %s", `l2_hdr`)
            self.pkt = l2_hdr
        if l3_hdr:
            log.debug("L3 Header: %s", `l3_hdr`)
            if not self.pkt:
                self.pkt = l3_hdr
            else:
                self.pkt = self.pkt / l3_hdr
        if l4_hdr:
            log.debug("L4 Header: %s", `l4_hdr`)
            self.pkt = self.pkt / l4_hdr
        if self.payload:
            log.debug("Payload: %s", self.payload)
            self.pkt = self.pkt / self.payload

    def _create_pkts(self):
        pkts = [self.pkt]
        for sport in range(self.profile.startport, self.profile.endport + 1):
            self.pkt = None
            self.stream.l4.__dict__.update({'sport': sport})
            self._create()
            pkts.append(self.pkt)

        return pkts

    def _l4_hdr(self):
        if self.stream.l4 is not None:
            l4_header = self.stream.l4.__dict__
        proto = self.stream.get_l4_proto()
        if proto == 'tcp':
            return TCP(**l4_header)
        elif proto == 'udp':
            return UDP(**l4_header)
        elif proto == 'icmp':
            return ICMP(**l4_header)
        elif proto == 'icmpv6':
            return ICMPv6EchoRequest()
        else:
            log.error("Unsupported L4 protocol %s."%proto)

    def _l3_hdr(self):
        l3_header = self.stream.l3.__dict__

        if not l3_header:
            return None
        if self.stream.protocol == 'ip':
            return IP(**l3_header)
        elif self.stream.protocol == 'ipv6':
            return IPv6(**l3_header)
        else:
            log.error("Unsupported L3 protocol.")

    def _l2_hdr(self):
        return Ether()

    def _payload(self):
        if self.profile.payload:
            return self.profile.payload
        if self.profile.size:
            return Raw(RandString(size=self.profile.size))
        else:
            return None


class GeneratorBase(object):

    def __init__(self, name, profile):
        self.profile = profile
        self.creater = CreatePkt(self.profile)
        self.pkt = self.creater.pkt
        self.count = 0
        self.recv_count = 0
        self.resultsfile = "/tmp/%s.results" % name
        self.update_result("Sent=%s\nReceived=%s" %
                           (self.count, self.recv_count))

    def update_result(self, result):
        fd = open(self.resultsfile, 'w')
        fd.write(result)
        fd.flush()
        fd.close()
        os.system('sync')


class Generator(Process, GeneratorBase):

    def __init__(self, name, profile):
        Process.__init__(self)
        GeneratorBase.__init__(self, name, profile)
        self.stopit = Event()
        self.stopped = Event()

    def send_recv(self, pkt, timeout=2):
        # Should wait for the ICMP reply when sending ICMP request.
        # So using scapy's "sr1".
        log.debug("Sending: %s", `pkt`)
        proto = self.profile.stream.get_l4_proto()
        if proto == "icmp" or proto == "icmpv6":
            p = sr1(pkt, timeout=timeout)
            if p:
                log.debug("Received: %s", `pkt`)
                self.recv_count += 1
        else:
            send(pkt)
        self.count += 1
        self.update_result("Sent=%s\nReceived=%s" %
                           (self.count, self.recv_count))

    def _standard_traffic(self):
        for i in range(self.profile.count):
            self.send_recv(self.pkt)
        self.stopped.set()

    def _continuous_traffic(self):
        while not self.stopit.is_set():
            self.send_recv(self.pkt)
        self.stopped.set()

    def _burst_traffic(self):
        for i in range(self.profile.count):
            for j in range(self.profile.burst_count):
                self.send_recv(self.pkt)
                sleep(self.profile.burst_interval)
        self.stopped.set()

    def _continuous_sport_range_traffic(self):
        self.pkts = self.creater.pkts
        while not self.stopit.is_set():
            sendpfast(self.pkts, pps=self.profile.pps)
            self.count += len(self.pkts)
            self.update_result("Sent=%s\nReceived=%s" %
                               (self.count, self.recv_count))
            if self.stopit.is_set():
                break
        self.stopped.set()

    def _start(self):
        # Preserve the order of the if-elif, because the Profiles are
        # inherited from StandardProfile, So all the profiles will be
        # instance of StandardProfile
        if isinstance(self.profile, ContinuousSportRange):
            self._continuous_sport_range_traffic()
        elif isinstance(self.profile, ContinuousProfile):
            self._continuous_traffic()
        elif isinstance(self.profile, BurstProfile):
            self._burst_traffic()
        elif isinstance(self.profile, StandardProfile):
            self._standard_traffic()

    def run(self):
        try:
            self._start()
        except Exception, err:
            log.warn(traceback.format_exc())
        finally:
            log.info("Total packets sent: %s", self.count)
            log.info("Total packets received: %s", self.recv_count)
            self.update_result("Sent=%s\nReceived=%s" %
                               (self.count, self.recv_count))

    def stop(self):
        if not self.is_alive():
            return

        if (isinstance(self.profile, ContinuousProfile) or
                isinstance(self.profile, ContinuousSportRange)):
            self.stopit.set()

        while (self.is_alive() and not self.stopped.is_set()):
            continue
        if self.is_alive():
            self.terminate()


class TCPGenerator(GeneratorBase):

    def __init__(self, name, profile):
        super(TCPGenerator, self).__init__(name, profile)
        self.stopit = False
        self.stopped = False

    def start(self):
        sport = self.profile.stream.l4.sport
        self.client = TCPClient(self, sport, debug=5)
        table = 'ip6tables' if is_v6(self.profile.stream.l3.src) else 'iptables'
        # Kernal will send RST packet during TCP hand shake before the scapy
        # sends ACK, So drop RST packets sent by Kernal
        os.system(
            '%s -A OUTPUT -p tcp --tcp-flags RST RST -s %s -j DROP' %
            (table, self.profile.stream.l3.src))
        # DO TCP Three way Hand Shake
        self.client.runbg()
        if isinstance(self.profile, ContinuousSportRange):
            self.clients = self.start_clients()
        self._start()

    def start_clients(self):
        clients = []
        for sport in range(self.profile.startport, self.profile.endport + 1):
            client = TCPClient(self, sport, debug=5)
            self.client.runbg()
            clients.append(client)
        return clients

    def _start(self):
        # Preserve the order of the if-elif, because the Profiles are
        # inherited from StandardProfile, So all the profiles will be
        # instance of StandardProfile
        if isinstance(self.profile, ContinuousSportRange):
            data = self.creater.payload
            while not self.stopit:
                for tcpclient in self.clients:
                    tcpclient.io.tcp.send(data)
            self.stopped = True
            return
        elif isinstance(self.profile, ContinuousProfile):
            data = self.creater.payload
            while not self.stopit:
                self.client.io.tcp.send(data)
            self.stopped = True
            return
        elif isinstance(self.profile, BurstProfile):
            for i in range(self.profile.count):
                for j in range(self.profile.burst_count):
                    data = self.creater.payload
                    self.client.io.tcp.send(data)
                sleep(self.profile.burst_interval)
        elif isinstance(self.profile, StandardProfile):
            for i in range(self.profile.count):
                data = self.creater.payload
                self.client.io.tcp.send(data)
            burst = self.profile.burst_count or 1

        while True:
            try:
                with open(self.resultsfile, 'r') as rfile:
                    sent = re.search("(Sent)=([0-9]+)", rfile.read())
                    if sent:
                        sent = int(sent.group(2))
                    if sent == (self.profile.count * burst):
                        break
            except IOError:
                continue
        self.stopped = True

    def stop(self):
        if (isinstance(self.profile, ContinuousProfile) or
                isinstance(self.profile, ContinuousSportRange)):
            self.stopit = True

        if not self.stopped:
            return
        # Trriger the TCPClient to RESET the connection.
        self.client.io.tcp.send("STOP_STREAM")
        self.client.stop()


class PktGenerator(object):

    def __init__(self, params):
        self.params = params
        self.profile = load(params.profile)
        log.debug("Profile: %s", self.profile.__dict__)

    def handler(self, signum, frame):
        self.generator.stop()

    def start(self):
        # Set the signal handler
        signal.signal(signal.SIGTERM, self.handler)
        if self.profile.stream.get_l4_proto() == 'tcp':
            self.generator = TCPGenerator(self.params.name, self.profile)
            self.generator.start()
        else:
            self.generator = Generator(self.params.name, self.profile)
            self.generator.daemon = True
            self.generator.start()
            self.generator.join()


class GenArgParser(object):

    def parse(self):
        parser = OptionParser()
        parser.add_option("-n", "--name",
                          dest="name",
                          help="Name for this traffic profile.")
        parser.add_option("-p", "--profile",
                          dest="profile",
                          help="Stream profile to be used for sending traffic.")
        parser.add_option("-S", "--stop",
                          dest="stop",
                          action="store_true",
                          default=False,
                          help="Stop this traffic Generator.")
        parser.add_option("-P", "--poll",
                          dest="poll",
                          action="store_true",
                          default=False,
                          help="Poll for packets sent/recv at traffic Generator.")
        opts, args = parser.parse_args()
        return opts
