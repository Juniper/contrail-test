
import logging
import fixtures
import dpkt

from tcutils.tcpdump_utils import *
from tcutils.util import retry
from time import sleep
from tcutils.commands import ssh, execute_cmd, execute_cmd_out
from compute_node_test import ComputeNodeFixture
from common import log_orig as contrail_logging

class TrafficAnalyzer:
    '''
    This class is used to capture traffic using tcpdump and analyze qos
    related fields of captured packets.
    Following are main utilities which are part of this class:
    1. Capturing packet on user defined fields or payload and storing the 
       captured packets in .pcap.
    2. Analyzing the .pcap file and verifying the qos fields of packets
       are as expected or not.
    3. Analyzing the .pcap file and verifying the encapsulation of packets
       recieved.
    '''
    def __init__(self, interface = None, compute_node_fixture=None,
                username = None, password = None, vlan = None, \
                src_ip = None, dest_ip = None, src_port = None, \
                dest_port = None, protocol=None, logger = None, \
                encap_type = None):
        
        self.compute_node_fixture = compute_node_fixture
        self.interface = interface or compute_node_fixture.agent_physical_interface
        self.node_ip = compute_node_fixture.ip
        self.username = username
        self.password = password
        self.vlan = vlan
        self.src_ip = src_ip
        self.dest_ip = dest_ip
        self.src_port = src_port
        self.dest_port = dest_port
        self.protocol = protocol
        self.encap_type = encap_type
        self.session = None
        self.pcap = None
        self.logger = logger or contrail_logging.getLogger(__name__)

    def packet_capture_start(self, traffic_between_diff_networks = False,
                             capture_on_payload = False,\
                             signature_string = None, offset = None,
                             bytes_to_match = None, min_length = 50,
                             max_length = 200):
        '''
        This procedure capture packets based on following fields:
        1. If capture_on_payload is True, it puts a filter on signature
           mentioned by the user starting from the offset specified
        2. If capture_on_payload is False, it check for encapsulation.
           If Encap is VxLAN or MPLSoUDP, it captures packets based on the
           user inputs of vlan, protocol, ips, ports etc.
        3. If encap is MPLSoGRE, it captures packets based on the source ip
           and destination ip of internal header. User should specify 
           "traffic_between_diff_networks" flag to get the correct results
           This flag is applicable only in case encap is MPLSoGRE and networks
           corresponds to internal source and destination IP networks
        Note: 
        Use bytes_to_match as multiple of 4
        All arguments of this functions are only required when user want to
        capture traffic on basis of payload.
        '''
        if capture_on_payload and not signature_string:
            self.logger.error("No signature string mentioned to capture packets")
            return False
        elif capture_on_payload and signature_string:
            if not offset or not bytes_to_match:
                self.logger.error("Please specify offset to match"
                                  " and bytes to be matched and try again")
                return False
            filter = []
            for i in range(0,bytes_to_match,4):
                filter.append("ether[%d:4]==0x%s" \
                                    % (offset,signature_string[2*i:2*i+8]))
                offset = offset+4
            filter.append(("greater %d") % min_length)
            filter.append(("not greater %d") % max_length)
            filter_pattern = ["and"] * (len(filter)*2-1)
            filter_pattern[0::2] = filter
            filter_string = " ".join(filter_pattern)
        if (self.encap_type == None or self.encap_type =="MPLSoUDP"\
        or self.encap_type=="VxLAN") and capture_on_payload == False:
            filter = []
            if self.vlan:
                filter.append("vlan %s" % self.vlan)
            if self.protocol:
                filter.append(self.protocol)
            if self.src_ip:
                filter.append("src host %s" % self.src_ip)
            if self.dest_ip:
                filter.append("dst host %s" % self.dest_ip )
            if self.src_port:
                filter.append("src port %s" % self.src_port)
            if self.dest_port:
                filter.append("dst port %s" % self.dest_port)
            filter_pattern = ["and"] * (len(filter)*2-1)
            filter_pattern[0::2] = filter
            self.logger.debug("The filter pattern is %s" % filter_pattern)
            filter_string = " ".join(filter_pattern)
        elif self.encap_type == "MPLSoGRE" and capture_on_payload == False:
            src_ip = '0x{:02x}{:02x}{:02x}{:02x}'.format(*map(int,\
                                        self.src_ip.split('.')))
            dest_ip = '0x{:02x}{:02x}{:02x}{:02x}'.format(*map(int,\
                                        self.dest_ip.split('.')))
            # Below 'if' check is to distinguish packets within the same network
            # and different  networks
            # Packet between different networks don't carry L2 header and thus 
            # there is a 14 byte difference
            if traffic_between_diff_networks:
                filter_string="proto gre and (ip[40:4]= %s and ip[44:4]= %s)"\
                                    % (src_ip,dest_ip)
            else:
                filter_string="proto gre and (ip[54:4]= %s and ip[58:4]= %s)"\
                                    % (src_ip,dest_ip)
        filter_string = '\'(%s)\'' % filter_string
        self.logger.debug("The filter string is %s" % filter_string)
        if not self.interface and not self.username and\
        not self.node_ip and not self.password:
            self.logger.error("At least one of interface, IP,"
                              " username or password not specified")
            return (self.session, self.pcap)
        # Intf to capture will be parent intf in the case of tagged intfs
        if '.' in self.interface:
            capture_intf = self.interface.split('.')[0]
        else:
            capture_intf = self.interface
        self.session, self.pcap = start_tcpdump_for_intf(self.node_ip,\
                self.username, self.password, capture_intf, \
                filters='-vvxx %s' % filter_string,
                logger=self.logger)
        return (self.session, self.pcap)
    
    def packet_capture_stop(self):
        '''
        Closes the tcpdump session.
        Recommended is to use this function always after "packet_capture_start"
        and "verify_packets".
        '''
        try:
            return stop_tcpdump_for_intf(self.session, self.pcap,
                                         logger=self.logger)
        except e:
            self.info.error("Failed to stop tcpdump. Possibly,"
                            " session does not exist")
    
    def _check_underlay_interface_is_tagged(self):
        ''' Returns True if self.interface is compute nodes' phy intf
            and it is tagged
        '''
        cn_intf = self.compute_node_fixture.agent_physical_interface
        if self.interface == cn_intf and '.' not in cn_intf:
            self.logger.debug('Interface %s does not seem to be a '
                'tagged intf. Skipping dot1p check' % (cn_intf))
            return False
        return True
    # end _check_underlay_interface_is_tagged
    
    def verify_packets(self, packet_type, pcap_path_with_file_name,
                       expected_count =None, dot1p = None, dscp = None, 
                       mpls_exp = None):
        '''
        This function parses tcpdump file.
        It verifies that field in packet in pcap file are same as expected by user or not.
        "packet_type" is mandatory and can be set to any string containing "exp", "dot1p",
        "dscp" or any or all of them.
        Verification done for following values:
            1. DSCP field
            2. VLAN Priority code point
            3. MPLS EXP bits
        This function can also be used to parse any .pcap present on any node
        even if the start capture was not done by 'TestQosTraffic' object.
        '''
        if self.session == None:
            if not self.username and not self.node_ip and not self.password:
                self.logger.error("Either of IP, username or password not"
                                  " specified")
                self.logger.error("Cannot open ssh session to the node")
                return False
            else:
                self.session = ssh(self.node_ip, self.username,\
                                       self.password)
            cmd = "ls -al %s" % pcap_path_with_file_name
            out, err = execute_cmd_out(self.session, cmd)
            if out:
                self.pcap = out.split('\n')[0].split()[-1]
            elif err:
                self.logger.error("%s" % err)
                return False
        if expected_count:
            result = verify_tcpdump_count(self, self.session, self.pcap,
                                          expected_count, exact_match=False)
            if not result:
                return result
        file_transfer = self.compute_node_fixture.file_transfer(
                            "get", self.pcap, self.pcap.split('/')[-1])
        if not file_transfer:
            self.logger.error("Unable to transfer file to local system")
            return False
        file_name = self.pcap.split('/')[-1]
        if self.encap_type:
            if not self.verify_encap_type(self.encap_type, file_name):
                return False
        f = open(file_name, 'r')
        pcap = dpkt.pcap.Reader(f)
        count = 0
        for ts,buff in pcap:
            ether = dpkt.ethernet.Ethernet(buff)
            self.logger.debug("Verifying for packet number %d" % count)
            count = count+1
            if "dot1p" in packet_type and\
            self._check_underlay_interface_is_tagged():
                if isinstance(dot1p,int):
                    string = ''
                    try:
                        priority = ether.vlan_tags[0].pri
                    except AttributeError, e:
                        self.logger.error(e)
                        return False
                    if priority == dot1p:
                        self.logger.debug("Validated dot1p marking of %s" 
                                          % (dot1p))
                    else:
                        self.logger.error("Mismatch between actual and"
                                          " expected PCP")
                        self.logger.error("Expected PCP : %s, Actual PCP :%s"\
                                          % (dot1p,priority))
                        return False
                else:
                    self.logger.error("dot1p to be compared not mentioned")
                    return False
            if "dscp" in packet_type:
                if isinstance(dscp,int):
                    ip = ether.data
                    try:
                        actual_dscp = int(bin(ip.tos >> 2), 2)
                    except AttributeError, e:
                        self.logger.error(e)
                        return False
                    if dscp == actual_dscp:
                        self.logger.debug("Validated DSCP marking of %s" % 
                                          (dscp))
                    else:
                        self.logger.error("Mismatch between actual and"
                                          " expected DSCP")
                        self.logger.error("Expected DSCP: %s, Actual DSCP:%s"\
                                          % (dscp,actual_dscp))
                        return False
                else:
                    self.logger.error("dscp to be compared not mentioned")
                    return False
            if "exp" in packet_type:
                if isinstance(mpls_exp,int):
                    try:
                        if self.encap_type == "MPLSoUDP" or not self.encap_type:
                            actual_mpls_exp = int((ether.ip.data.data)\
                                                  .encode("hex")[5:6], 16) >> 1
                        elif self.encap_type == "MPLSoGRE":
                            actual_mpls_exp = int(ether.ip.data.\
                                                  encode("hex")[13:14],16) >> 1
                        elif self.encap_type == "VxLAN":
                            self.logger.error("VxLAN encapslation does "
                                              "not have exp")
                            self.logger.error("Correct the 'packet_type' "
                                              "or 'encap_type'")
                            return False
                    except AttributeError, e:
                        self.logger.error(e)
                        return False
                    if mpls_exp == actual_mpls_exp:
                        self.logger.debug("Validated EXP marking of %s" 
                                          % (mpls_exp))
                    else:
                        self.logger.error("Mismatch between actual and"
                                          " expected EXP")
                        self.logger.error("Expected EXP : %s ,Actual EXP :%s"\
                                          % (mpls_exp,actual_mpls_exp))
                        return False
                else:
                    self.logger.error("Mpls exp to be compared not mentioned")
                    return False
        self.logger.info('Packet QoS marking validation passed')
        return True
    # end verify_packets

    def verify_encap_type(self, expected_encap, file_name):
        f = open(file_name, 'r')
        pcap = dpkt.pcap.Reader(f)
        for ts,buff in pcap:
            ether = dpkt.ethernet.Ethernet(buff)
            try:
                if ether.ip.data.encode("hex")[0:8] == '00008847':
                    actual_encap = 'MPLSoGRE'
                    break
            except AttributeError, e:
                self.logger.debug(e)
                self.logger.debug("Packet different from GRE encap")  
            if ether.ip.data.data.encode("hex")[0:8] == '08000000':
                actual_encap = 'VxLAN'
            elif ether.ip.data.data.encode("hex")[0:8] != '08000000'\
                and ether.ip.data.sport:
                actual_encap = 'MPLSoUDP'
            else:
                actual_encap = None
                self.logger.error("Unable to find the encapsulation type")
                return False
            break
        if actual_encap == expected_encap:
            self.logger.debug("Encapsulation same as expected")
            return True
        else:
            self.logger.error("Encapsulation mismatch")
            self.logger.error("Expected encapsulation: %s" % expected_encap)
            self.logger.error("Actual encapsulation: %s" % actual_encap)
            return False
        