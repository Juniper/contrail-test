"""Module holding various stream profiles.
"""

from cPickle import dumps, loads

try:
    # Running from the source repo "test".
    from tcutils.pkgs.Traffic.traffic.core.stream import *
    from tcutils.pkgs.Traffic.traffic.utils.logger import LOGGER, get_logger
    from tcutils.pkgs.Traffic.traffic.utils.globalvars import LOG_LEVEL
except ImportError:
    # Distributed and installed as package
    from traffic.core.stream import *
    from traffic.utils.logger import LOGGER, get_logger
    from traffic.utils.globalvars import LOG_LEVEL


LOGGER = "%s.core.listener" % LOGGER
log = get_logger(name=LOGGER, level=LOG_LEVEL)

ENCRYPT = [("\n", "#"), (" ", "@"), ("(", "{"), ("'", "}")]


def create(obj):
    """Creates the string representation of the profile object.
    Which can be passed as command line argument to the sendpkts/recvpkts
    scripts that are run in another machine(VM, Host).
    """
    objs = dumps(obj)
    for actual, encrypt in ENCRYPT:
        objs = objs.replace(actual, encrypt)
    return "\"%s\"" % objs


def load(objs):
    """Converts the string representation of the profile object to Object.
    Which will be used by the listener and generator modules in another
    Machine(VM , Host).
    """
    ENCRYPT.reverse()
    for actual, encrypt in ENCRYPT:
        objs = objs.replace(encrypt, actual)
    return loads(objs)


class StandardProfile(object):

    def __init__(
        self, stream, size=100, count=10, payload=None, capfilter=None,
            stopper=None, timeout=None, iface=None, listener=None, chksum=False):
        self.stream = stream
        # payload size in bytes
        self.size = size
        # Payload to tbe sent in the packets.
        self.payload = payload
        # Number of packets to send/send per burst.
        self.count = count
        # Tcp dump style filter to be applied when capturing the packets.
        # If filter is not given, the dfault filter will be framed automatically
        # using the source/destination IP and source/destination port attributes
        # of the stream.
        self.capfilter = capfilter
        # Stop packet capturing, once this stopper function returns true
        # This function will be applied on each received packets.
        self.stopper = stopper
        # Timeout usually goes with stopper.say the stopper function waiting for
        # a particular packet and its never received...timeout avoids dead
        # lock.
        self.timeout = timeout
        # Interface to capture packets, if None captures in all interface.
        self.iface = iface
        # Listener IP address; for tcp and udp receivers
        self.listener = listener
        # to verify checksum of the received packet.
        self.chksum = chksum

        # Number of bursts
        self.burst_count = None
        # Interval between burst in seconds
        self.burst_interval = None


class ContinuousProfile(StandardProfile):

    def __init__(
        self, stream, size=100, count=10, payload=None, capfilter=None,
        stopper=None, timeout=None, iface=None, listener=None,
            chksum=False):
        # count = 0; means send packets continuously
        super(ContinuousProfile, self).__init__(stream, size, count, payload,
                                                capfilter, stopper, timeout, iface, listener, chksum)


class BurstProfile(StandardProfile):

    def __init__(
        self, stream, size=100, count=10, payload=None, capfilter=None,
        stopper=None, timeout=None, burst_count=10, listener=None,
            chksum=False, burst_interval=10):
        super(BurstProfile, self).__init__(stream, size, count, payload,
                                           capfilter, stopper, timeout, iface, listener, chksum)
        # Number of bursts
        self.burst_count = burst_count
        # Interval between burst in seconds
        self.burst_interval = burst_interval


class ContinuousSportRange(StandardProfile):

    def __init__(self, stream, size=100, startport=8001, endport=8100,
                 payload=None, capfilter=None, stopper=None, timeout=None,
                 iface=None, listener=None, chksum=False, pps=500):
        super(
            ContinuousSportRange, self).__init__(stream, size=size, payload=payload,
                                                 capfilter=capfilter, stopper=stopper, timeout=timeout, iface=iface,
                                                 listener=listener, chksum=chksum)

        self.startport = startport
        self.endport = endport
        self.pps = pps
