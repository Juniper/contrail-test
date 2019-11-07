"""TCP Client module built on top of scapy Automaton"""

from scapy.all import *
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

LOGGER = "%s.core.tcpclient" % LOGGER
log = get_logger(name=LOGGER, level=LOG_LEVEL)


class TCPClient(Automaton):

    """ Controlled TCP_client to send RST, which can be trrigered from the
         main thread"""

    def parse_args(self, gen, sport, *args, **kargs):
        log.debug("Parsing the args")
        self.gen = gen
        l3_hdr = self.gen.creater._l3_hdr()
        l4_hdr = self.gen.creater._l4_hdr()

        self.pkt = l3_hdr / l4_hdr
        self.pkt[TCP].flags = 0
        self.pkt[TCP].seq = random.randrange(0, 2 ** 32)

        self.src = self.gen.profile.stream.l3.src
        self.dst = self.gen.profile.stream.l3.dst
        self.sport = sport
        self.dport = self.gen.profile.stream.l4.dport
        self.swin = self.pkt[TCP].window
        self.dwin = 1
        self.rcvbuf = ""
        self.count = 0
        self.recv_count = 0
        bpf = "host %s  and host %s and port %i and port %i" % (self.src,
                                                                self.dst,
                                                                self.sport,
                                                                self.dport)
        log.debug("BPF: %s", bpf)

#        bpf=None
        Automaton.parse_args(self, filter=bpf, **kargs)

    def master_filter(self, pkt):
        log.debug("Master filter")
        return (((IP in pkt and
                  pkt[IP].src == self.dst and
                  pkt[IP].dst == self.src) or
                 (IPv6 in pkt and
                  pkt[IPv6].src == self.dst and
                  pkt[IPv6].dst == self.src)
                ) and TCP in pkt and
                pkt[TCP].sport == self.dport and
                pkt[TCP].dport == self.sport and
                # XXX: seq/ack 2^32 wrap up
                self.pkt[TCP].seq >= pkt[TCP].ack and
                ((self.pkt[TCP].ack == 0) or (self.pkt[TCP].ack <= pkt[TCP].seq <= self.pkt[TCP].ack + self.swin)))

    @ATMT.state(initial=1)
    def START(self):
        log.debug("state = START")
        pass

    @ATMT.state()
    def SYN_SENT(self):
        log.debug("state = SYN_SENT")
        pass

    @ATMT.state()
    def ESTABLISHED(self):
        log.debug("state = ESTABLISHED")
        pass

    @ATMT.state()
    def LAST_ACK(self):
        log.debug("state = LAST_ACK")
        pass

    @ATMT.state(final=1)
    def CLOSED(self):
        log.debug("state = CLOSED")
        pass

    @ATMT.condition(START)
    def connect(self):
        raise self.SYN_SENT()

    @ATMT.action(connect)
    def send_syn(self):
        log.info("Sending SYN")
        self.pkt[TCP].flags = "S"
        log.debug(`self.pkt`)
        self.send(self.pkt)
        self.pkt[TCP].seq += 1

    @ATMT.receive_condition(SYN_SENT)
    def synack_received(self, pkt):
        if pkt[TCP].flags & 0x3f == 0x12:
            raise self.ESTABLISHED().action_parameters(pkt)

    @ATMT.action(synack_received)
    def send_ack_of_synack(self, pkt):
        log.info("Received SYN ACK")
        self.pkt[TCP].ack = pkt[TCP].seq + 1
        self.pkt[TCP].flags = "A"
        log.info("Sending ACK for SYN ACK")
        log.debug(`self.pkt`)
        self.send(self.pkt)

    @ATMT.receive_condition(ESTABLISHED)
    def incoming_data_received(self, pkt):
        if not isinstance(pkt[TCP].payload, NoPayload) and not isinstance(pkt[TCP].payload, Padding):
            raise self.ESTABLISHED().action_parameters(pkt)

    @ATMT.action(incoming_data_received)
    def receive_data(self, pkt):
        log.debug("Received data in ESTABLISHED state.")
        data = str(pkt[TCP].payload)
        if data and self.pkt[TCP].ack == pkt[TCP].seq:
            self.pkt[TCP].ack += len(data)
            self.pkt[TCP].flags = "A"
            log.debug(`self.pkt`)
            self.send(self.pkt)
            self.rcvbuf += data
            if pkt[TCP].flags & 8 != 0:  # PUSH
                self.oi.tcp.send(self.rcvbuf)
                self.rcvbuf = ""

    @ATMT.ioevent(ESTABLISHED, name="tcp", as_supersocket="tcplink")
    def outgoing_data_received(self, fd):
        raise self.ESTABLISHED().action_parameters(fd.recv())

    @ATMT.action(outgoing_data_received)
    def send_data(self, d):
        log.debug("Got '%s' to send at  ESTABLISHED state.", d)
        if d == "STOP_STREAM":
            log.debug("Sending RST")
            # User requested to reset the TCP connection
            self.pkt[TCP].flags = "R"
            log.debug(`self.pkt`)
            self.send(self.pkt)
            return

        self.count += 1
        self.pkt[TCP].flags = "PA"
        log.debug(`self.pkt / d`)
        self.send(self.pkt / d)
        self.pkt[TCP].seq += len(d)
        self.gen.update_result("Sent=%s\nReceived=%s" %
                               (self.count, self.recv_count))

    @ATMT.receive_condition(ESTABLISHED)
    def reset_received(self, pkt):
        log.debug("Recevied RST")
        if pkt[TCP].flags & 4 != 0:
            raise self.CLOSED()

    @ATMT.receive_condition(ESTABLISHED)
    def fin_received(self, pkt):
        if pkt[TCP].flags & 0x1 == 1:
            raise self.LAST_ACK().action_parameters(pkt)

    @ATMT.action(fin_received)
    def send_finack(self, pkt):
        log.debug("Sending FIN ACK")
        self.pkt[TCP].flags = "FA"
        self.pkt[TCP].ack = pkt[TCP].seq + 1
        log.debug(`self.pkt`)
        self.send(self.pkt)
        self.pkt[TCP].seq += 1

    @ATMT.receive_condition(LAST_ACK)
    def ack_of_fin_received(self, pkt):
        log.debug("Sending ACK for FIN")
        if pkt[TCP].flags & 0x3f == 0x10:
            raise self.CLOSED()
