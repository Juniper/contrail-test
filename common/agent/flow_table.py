from tcutils.util import *
import tabulate

class FlowTable :
    '''Represent flow table in kernel on a compute node

       Data is got from queries similar to below:
        http://nodek1:8085/Snh_NextKFlowReq?x=

        flow_table_entries : List got from agent introspect API 
                             get_vna_kflowresp()
    '''

    def __init__(self, flow_table_entries):
        self.items = flow_table_entries or []
        self.flow_count = len(self.items)
    # end __init__

    def get_as_table(self):
        ''' Dump the flow table
        '''
        return tabulate.tabulate(self.items, headers="keys")
    # end dump

#end FlowTable

class FlowEntry:
    '''
    Object to represent a flow entry as got from 
        http://nodek1:8085/Snh_KFlowReq?flow_idx=

    Arguments:
    flow_entry_items : Flow entry dict as got from agent introspect
    
    Ex flow_entry_items: {'index': '24', 'rflow': '43061', 'd_vrf_id': '1',
                          'proto': '6', 'insight': '0', 'bytes': '80',
                          'pkts': '2', 'vrf_id': '0', 'sip': '192.168.192.1',
                          'flags': ' ACTIVE | VRFT | SNAT | DNAT ',
                          'dport': '80', 'sport': '21372',
                          'dip': '169.254.0.3', 'action': 'NAT'}
    Later additions to above dict: tcp_flags, underlay_udp_port, drop_reason,
    source_nh_id, insight

    Flow flags can be one or more of ACTIVE, MIRROR, VRFT, SNAT, SPAT, DNAT,
    DPAT, LINK_LOCAL, EVICTED, EVICT_CANDIDATE, NEW_FLOW, MODIFIED,
    RFLOW_VALID, INVALID ( from flow_kstate.cc)

    action can be one of FORWARD, DROP, NAT, HOLD

    tcp_floags can be one or more of SYN, SYN_R, ESTB, ESTB_R, FIN, FIN_R,
    RST, HALF_CLOSE, DEAD, INVALID
    '''

    def __init__(self, flow_entry_items):
        self.items = flow_entry_items
        self._update_flow_attrs(self.items)
        self.overflow_indices = []

        if self.dest_vrf_id == "-1":
            self.dest_vrf_id = None

    # end __init__

    def _update_flow_attrs(self, flow_entry_items):
        self.index = flow_entry_items['index']
        self.r_flow_index = flow_entry_items['rflow']
        self.dest_vrf_id = flow_entry_items['d_vrf_id']
        self.proto = flow_entry_items['proto']
        self.insight = flow_entry_items['insight']
        self.bytes = flow_entry_items['bytes']
        self.packets = flow_entry_items['pkts']
        self.vrf_id = flow_entry_items['vrf_id']
        self.source_ip = flow_entry_items['sip']
        self.flags = flow_entry_items['flags']
        self.dest_port = flow_entry_items['dport']
        self.source_port = flow_entry_items['sport']
        self.dest_ip = flow_entry_items['dip']
        self.action = flow_entry_items['action']
        self.tcp_flags = flow_entry_items.get('tcp_flags')
        self.underlay_udp_port = flow_entry_items.get('underlay_udp_port')
        self.drop_reason = flow_entry_items.get('drop_reason')
        self.source_nh_id = flow_entry_items.get('nhid')
        self.insight = flow_entry_items.get('insight')
    # end _update_flow_attrs

    def is_flow_having_flag(self, flag):
        if flag in self.flags:
            return True
        else:
            return False
    # end is_flow_having_flag

    def is_flow_evicted(self):
        ''' Returns True/False
        '''
        return self.is_flow_having_flag('EVICTED')
    # end is_flow_evicted

    def is_nat_flow(self):
        return self.is_flow_having_flag('NAT')
    # end is_nat_flow

    def dump(self):
        return self.items
    # end dump


if __name__ == "__main__":
    from tcutils.agent.vna_introspect_utils import *
    agent_inspect = AgentInspect('10.204.216.222')
    flow_table = FlowTable(agent_inspect.get_vna_kflowresp())
    flow_table.dump()
