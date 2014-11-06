"""Module for creating socket to receive packets.
"""
import errno
import socket
import signal
import traceback
from select import select
from multiprocessing import Process, Queue
from optparse import OptionParser

from scapy.data import *
from scapy.config import conf
from scapy.utils import PcapReader
from scapy.all import plist
from scapy.layers.inet import IP, TCP, UDP, ICMP

try:
    # Running from the source repo "test".
    from tcutils.pkgs.Traffic.traffic.core.profile import *
    from tcutils.pkgs.Traffic.traffic.utils.logger import LOGGER, get_logger
    from tcutils.pkgs.Traffic.traffic.utils.globalvars import LOG_LEVEL
except ImportError:
    # Distributed and installed as package
    from traffic.core.profile import *
    from traffic.utils.logger import LOGGER, get_logger
    from traffic.utils.globalvars import LOG_LEVEL


LOGGER = "%s.core.listener" % LOGGER
log = get_logger(name=LOGGER, level=LOG_LEVEL)

MTU = 65565


class CaptureBase(Process):

    def __init__(self, name, **kwargs):
        super(CaptureBase, self).__init__()
        self.kwargs = kwargs
        log.debug("Filter is: %s", self.kwargs['filter'])
        self.capture = True
        self.pcap = []
        self.filtered_pcap = []
        self.corrupted_pcap = []
        self.resultsfile = "/tmp/%s.results" % name

    @conf.commands.register
    def sniff(self, count=0, store=1, timeout=None, stopperTimeout=None, stopper=None, chksum=False, *arg, **karg):
        """Sniff packets
        sniff([count=0,] [store=1,] [stopper] + args) -> list of packets

          count: number of packets to capture. 0 means infinity
          store: wether to store sniffed packets or discard them
        timeout: stop sniffing after a given time (default: None)
        stopperTimeout: break the select to check the returned value of
        stopper: function returning true or false to stop the sniffing process
        """
        self.chksum = chksum
        c = 0  # Total packets

        L2socket = conf.L2listen
        self.sock = L2socket(type=ETH_P_ALL, *arg, **karg)

        if timeout is not None:
            stoptime = time.time() + timeout
        remain = None

        if stopperTimeout is not None:
            stopperStoptime = time.time() + stopperTimeout
        remainStopper = None
        last_pkt = None
        while self.capture:
            if timeout is not None:
                remain = stoptime - time.time()
                if remain <= 0:
                    break
                sel = select([self.sock], [], [], remain)
                if self.sock in sel[0]:
                    p = self.sock.recv(MTU)
            else:
                p = self.sock.recv(MTU)

            if p is None:
                continue
            if p == last_pkt:
                last_pkt = None
                # Sniff sniffs packet twice; workarund for it
                # When time permits, we should debug this
                log.debug("Duplicate, Skip counting this packet")
                continue
            last_pkt = p
            log.debug(`p`)
            # Discard the first ssh keepalive packet
            try:
                dport = p[TCP].dport
                sport = p[TCP].sport
                if dport == 22 or sport == 22:
                    log.debug("Discard the ssh keepalive packet")
                    continue
            except IndexError:
                pass
            if store:
                self.pcap.append(p)
            if self.count_tcp(p):
                c += 1
                log.debug("Total packets received: %s", c)
                self.update_result(c, len(self.corrupted_pcap))
                if count > 0 and c >= count:
                    break
                if stopper and stopper(p):
                    break
                continue

            if self.count_icmp(p):
                c += 1
                log.debug("Total packets received: %s", c)
                self.update_result(c, len(self.corrupted_pcap))
                if count > 0 and c >= count:
                    break
                if stopper and stopper(p):
                    break
                continue

            if self.count_udp(p):
                c += 1
                log.debug("Total packets received: %s", c)
                self.update_result(c, len(self.corrupted_pcap))
                if count > 0 and c >= count:
                    break
                if stopper and stopper(p):
                    break
                continue

    def checksum(self, p, proto):
        # Preserve the received checksum
        l3_chksum = p[IP].chksum
        l4_chksum = p[proto].chksum
        log.debug("Received L3 checksum: %s and L4 checksum: %s",
                  l3_chksum, l4_chksum)
        # delete the chksum field in the receicved packets
        del p[IP].chksum
        del p[proto].chksum
        # Calculate the chksum
        p = p.__class__(str(p))
        log.debug("Calculated L3 checksum: %s and L4 checksum: %s",
                  p[IP].chksum, p[proto].chksum)
        if (p[IP].chksum == l3_chksum and p[proto].chksum == l4_chksum):
            return True
        return False

    def count_tcp(self, p):
        try:
            if p[IP].proto == 6:
                log.debug("Protocol is TCP")
                if self.chksum and not self.checksum(p, TCP):
                    self.corrupted_pcap.append(p)
                if (not p[IP].frag == "MF" and p[TCP].flags == 24):
                    # count only TCP PUSH ACK packet.
                    log.debug("Packet is unfagmented and tcp flag is PUSH")
                    self.filtered_pcap.append(p)
                    return 1
        except IndexError:
            pass
        return 0

    def count_udp(self, p):
        try:
            if p[IP].proto == 17:
                log.debug("Protocol is UDP")
                if self.chksum and not self.checksum(p, UDP):
                    self.corrupted_pcap.append(p)
                if not p[IP].frag == "MF":
                    # count only unfragmented packet.
                    log.debug("Packet is unfagmented")
                    self.filtered_pcap.append(p)
                    return 1
        except IndexError:
            pass
        return 0

    def count_icmp(self, p):
        try:
            if p[ICMP].type == 8:
                # count only ICMP Echo Request
                log.debug("ICMP echo request")
                self.filtered_pcap.append(p)
                if self.chksum and not self.checksum(p, ICMP):
                    self.corrupted_pcap.append(p)
                return 1
        except IndexError:
            pass
        return 0

    def run(self):
        try:
            self.sniff(**self.kwargs)
        except socket.error as (code, msg):
            if code != errno.EINTR:
                raise
        except Exception, err:
            log.warn(traceback.format_exc())
        finally:
            self.sock.close()
            self.pcap = plist.PacketList(self.filtered_pcap, "Sniffed")
            log.debug("Total packets received: %s", len(self.pcap))
            self.update_result(len(self.pcap), len(self.corrupted_pcap))

    def update_result(self, recv, corrupt):
        result = "Received=%s\nCorrupted=%s" % (recv, corrupt)
        fd = open(self.resultsfile, 'w')
        fd.write(result)
        fd.flush()
        fd.close()

    def stop(self):
        self.capture = False
        self.terminate()
        self.sock.close()


class ListenerBase(Process):

    def __init__(self, sock):
        super(ListenerBase, self).__init__()
        self.sock = sock
        self.listen = True

    def run(self):
        try:
            while self.listen:
                pkt = self.sock.recv(MTU)
        except socket.error as (code, msg):
            if code != errno.EINTR:
                raise

    def stop(self):
        self.listen = False
        self.terminate()
        self.sock.close()


class UDPListener(ListenerBase):

    def __init__(self, ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((ip, int(port)))
        super(UDPListener, self).__init__(sock)


class TCPListener(ListenerBase):

    def __init__(self, ip, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((ip, int(port)))
        sock.listen(1)
        super(TCPListener, self).__init__(sock)

    def run(self):
        while self.listen:
            conn, address = self.sock.accept()
            # self.sock.recv(MTU)


class PktListener(object):

    def __init__(self, params):
        self.profile_name = params.name
        self.profile = load(params.profile)
        self.stream = self.profile.stream
        log.debug("Profile: %s", self.profile.__dict__)
        log.debug("Stream: %s", self.stream.__dict__)
        log.debug("Stream L3: %s", self.stream.l3.__dict__)
        log.debug("Stream L4: %s", self.stream.l4.__dict__)
        self.create_listener()
        self.create_sniffer()
        self.pcap = 0

    def _join(self, *args):
        return " ".join(args)

    def _make_filter(self):
        capfilter = ''
        if hasattr(self.stream.l3, 'proto'):
            capfilter = self._join(capfilter, self.stream.l3.proto)

        if hasattr(self.stream.l4, 'dport'):
            capfilter = self._join(
                capfilter, "port", str(self.stream.l4.dport))

        return capfilter

    def create_listener(self):
        if self.profile.listener:
            listen_at = self.profile.listener
        else:
            listen_at = self.stream.l3.dst

        self.listener = None
        if self.stream.l3.proto == 'tcp':
            self.listener = TCPListener(listen_at, self.stream.l4.dport)
        elif self.stream.l3.proto == 'udp':
            self.listener = UDPListener(listen_at, self.stream.l4.dport)
        if self.listener:
            self.listener.daemon = 1

    def _standard_traffic(self):
        count = self.profile.count
        return count

    def _burst_traffic(self):
        count = self.profile.burst_count * self.profile.count
        return count

    def _continuous_traffic(self):
        pass

    def create_sniffer(self):
        kwargs = {}
        if not self.profile.iface:
            kwargs.update({'iface': self.profile.iface})
        if not self.profile.capfilter:
            capfilter = self._make_filter()
        else:
            capfilter = self.profile.capfilter
        kwargs.update({'filter': capfilter})

        if (isinstance(self.profile, ContinuousProfile) or
                isinstance(self.profile, ContinuousSportRange)):
            self._continuous_traffic()
        elif isinstance(self.profile, BurstProfile):
            kwargs.update({'count': self._burst_traffic()})
        elif isinstance(self.profile, StandardProfile):
            kwargs.update({'count': self._standard_traffic()})

        if self.profile.stopper:
            kwargs.update({'stopper': self.profile.stopper})
        if self.profile.timeout:
            kwargs.update({'timeout': self.profile.timeout})
        if self.profile.chksum:
            kwargs.update({'chksum': self.profile.chksum})

        self.sniffer = CaptureBase(self.profile_name, **kwargs)
        self.sniffer.daemon = 1

    def start(self):
        # Set the signal handler
        signal.signal(signal.SIGTERM, self.handler)
        try:
            if self.listener:
                self.listener.start()
            self.sniffer.start()
            self.sniffer.join()
        except Exception, err:
            log.warn(traceback.format_exc())
        finally:
            self.stop()

    def stop(self):
        try:
            self.sniffer.stop()
            if self.listener:
                self.listener.stop()
        except:
            pass
        finally:
            self.pcap = len(self.sniffer.pcap)

    def handler(self, signum, frame):
        self.stop()


class ListenerArgParser(object):

    def parse(self):
        parser = OptionParser()
        parser.add_option("-n", "--name",
                          dest="name",
                          help="Name for this traffic profile.")
        parser.add_option("-p", "--profile",
                          dest="profile",
                          help="Traffic profile to be used to receive packets.")
        parser.add_option("-S", "--stop",
                          dest="stop",
                          action="store_true",
                          default=False,
                          help="Stop this traffic listener.")
        parser.add_option("-P", "--poll",
                          dest="poll",
                          action="store_true",
                          default=False,
                          help="poll for packets recieved at traffic listener.")

        opts, args = parser.parse_args()
        return opts
