"""Module to create traffic stream.

It just parses the arguments given by the user and fills up the approprite
protocol header. 

This needs to be extended for new protocol streams with new protocol.
"""

import sys
import inspect
import random

try:
    # Running from the source repo "test".
    from tcutils.pkgs.Traffic.traffic.utils.logger import LOGGER, get_logger
    from tcutils.pkgs.Traffic.traffic.utils.globalvars import LOG_LEVEL
    from tcutils.pkgs.Traffic.traffic.utils.util import is_v6, is_v4
except ImportError:
    # Distributed and installed as package
    from traffic.utils.logger import LOGGER, get_logger
    from traffic.utils.globalvars import LOG_LEVEL
    from traffic.utils.util import is_v6, is_v4


LOGGER = "%s.core.listener" % LOGGER
log = get_logger(name=LOGGER, level=LOG_LEVEL)


def help(header="all"):
    """lists the keywords of fields available in currenlty implemented 
    protocols.
    This is a helper method to the users to get the list of fields,
    before creating a stream.

       Usage:
       import stream
       stream.help()
       stream.help("IPHeader")
    """
    clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
    if not header == "all":
        clsmembers = filter(lambda x: x[0] == header, clsmembers)
    for clsname, clsmember in clsmembers:
        clsobj = clsmember()
        clsattrs = dir(clsobj)
        if "fields" in clsattrs:
            print clsname, ": ", clsobj.fields
        if "options" in clsattrs:
            print clsname, ": ", clsobj.options


class Stream(object):

    def __init__(self, **kwargs):
        if not kwargs:
            # Just for getting Help.
            return
        self.all_fields = kwargs

        try:
            self.protocol = self.all_fields['protocol']
        except KeyError:
            self.protocol = "ip"  # Defualt L3 protocol.
            dst = self.all_fields['dst']
            if is_v6(dst):
                self.protocol = "ipv6"
        try:
            proto = self.all_fields['proto']
        except KeyError, err:
            print err, "Must specify proto."
        if 'dst' in self.all_fields.keys():
            self.all_fields['dst'] = str(self.all_fields['dst'])

        self.l2 = self._eth_header()
        if self.protocol == 'ip':
            self.l3 = self._ip_header()
        elif self.protocol == 'ipv6':
            self.l3 = self._ip6_header()
        if proto == 'tcp':
            self.l4 = self._tcp_header()
        elif proto == 'udp':
            self.l4 = self._udp_header()
        elif proto == 'icmp':
            self.l4 = self._icmp_header()

    def _eth_header(self):
        return {}

    def _ip_header(self):
        return IPHeader(**self.all_fields).get_header()

    def _ip6_header(self):
        return IP6Header(**self.all_fields).get_header()

    def _tcp_header(self):
        return TCPHeader(**self.all_fields).get_header()

    def _udp_header(self):
        return UDPHeader(**self.all_fields).get_header()

    def _icmp_header(self):
        if self.protocol == 'ipv6':
            return None
        return ICMPHeader(**self.all_fields).get_header()

    def get_l4_proto(self):
        return getattr(self.l3, 'proto', None) or \
               getattr(self.l3, 'nh', None).lower()


class Header(object):

    def __init__(self, fields={}):
        for key, val in fields.items():
            self.__setattr__(key, val)


class AnyHeader(object):

    def __init__(self, **kwargs):
        self.all_fields = kwargs
        try:
            self.all_fields.update({'sport': int(self.all_fields['sport'])})
            self.all_fields.update({'dport': int(self.all_fields['dport'])})
            self.all_fields.update({'inter': int(self.all_fields['inter'])})
        except KeyError:
            pass

    def create_header(self, fields):
        header = {}
        for field in fields:
            if field in self.all_fields.keys():
                if field == "iplen":  # UDP also has len
                    field = "len"
                if field == "ipflags":  # TCP also has flags
                    field = "flags"
                header.update({field: self.all_fields[field]})

        return header


class TCPHeader(AnyHeader):

    def __init__(self, **kwargs):
        super(TCPHeader, self).__init__(**kwargs)
        # Set got from "fields_desc" attribute of protocol headers in scapy.
        self.fields = ("sport", "dport", "seq", "ack", "dataofs", "reserved",
                       "flags", "window", "chksum", "urgptr")
        self.options = ("EOL", "NOP", "MSS", "WScale", "SAckOK", "SAck",
                        "Timestamp", "AltChkSum", "AltChkSumOpt")

    def get_header(self):
        header = self.create_header(self.fields)
        options = self.create_header(self.options)

        if options:
            header.update({'options': options})

        return Header(header)


class UDPHeader(AnyHeader):

    def __init__(self, **kwargs):
        super(UDPHeader, self).__init__(**kwargs)
        # Set got from "fields_desc" attribute of protocol headers in scapy.
        self.fields = ("sport", "dport", "len", "chksum")

    def get_header(self):
        header = self.create_header(self.fields)

        return Header(header)


class ICMPHeader(AnyHeader):

    def __init__(self, **kwargs):
        super(ICMPHeader, self).__init__(**kwargs)
        # Set got from "fields_desc" attribute of protocol headers in scapy.
        self.fields = ("type", "code", "chksum", "id", "seq", "ts_ori", "ts_rx"
                       "ts_tx", "gw", "ptr", "reserved", "addr_mask")

    def get_header(self):
        header = self.create_header(self.fields)
        header['id'] = random.randint(0, 32767)

        return Header(header)


class IPHeader(AnyHeader):

    def __init__(self, **kwargs):
        super(IPHeader, self).__init__(**kwargs)
        # Set got from "fields_desc" attribute of protocol headers in scapy.
        self.fields = ("version", "ihl", "tos", "iplen", "id", "ipflags",
                       "frag", "ttl", "proto", "ipchksum", "src", "dst",
                       "options")

    def get_header(self):
        header = self.create_header(self.fields)

        return Header(header)


class IP6Header(AnyHeader):

    def __init__(self, **kwargs):
        super(IP6Header, self).__init__(**kwargs)
        # Set got from "fields_desc" attribute of protocol headers in scapy.
        self.fields = ("version", "tc", "fl", "iplen", "nh", "proto",
                       "hlim", "ttl", "src", "dst")

    def get_header(self):
        header = self.create_header(self.fields)
        hdr_obj = Header(header)
        if hasattr(hdr_obj, 'proto'):
            hdr_obj.nh = hdr_obj.proto.upper()
            if 'ICMP' in hdr_obj.nh:
                hdr_obj.nh = 'ICMPv6'
            del hdr_obj.proto
        if hasattr(hdr_obj, 'ttl'):
            hdr_obj.hlim = hdr_obj.ttl
            del hdr_obj.ttl
        return hdr_obj
