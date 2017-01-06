import os
from tcutils.util import get_random_cidr
from tcutils.util import get_random_name
from common.servicechain.verify import VerifySvcChain


class ConfigSvcMirror(VerifySvcChain):
    ''' Class for mirroring specific config routines
    '''

    def config_svc_mirroring(self, service_mode='transparent', *args, **kwargs):
        """Validate the service chaining datapath
           Test steps:
           1. Create the SI/ST in svc_mode specified.
           2. Create vn11/vm1, vn21/vm2
           3. Create the policy rule for ICMP/UDP and attach to vn's
           4. Send the traffic from vm1 to vm2 and verify if the packets gets mirrored to the analyzer
           5. If its a single analyzer only ICMP(5 pkts) will be sent else ICMP and UDP traffic will be sent.
           Pass criteria :
           count = sent
           single node : Pkts mirrored to the analyzer should be equal to 'count'
           multinode :Pkts mirrored to the analyzer should be equal to '2xcount'
        """
        ci = False
        if os.environ.get('ci_image'):
            ci = True
        create_svms = kwargs.get('create_svms', True)
        vn1_subnets = [get_random_cidr(af=self.inputs.get_af())]
        vn2_subnets = [get_random_cidr(af=self.inputs.get_af())]
        vn1_name = get_random_name('left')
        vn2_name = get_random_name('right')
        st_name = get_random_name("st1")
        action_list = []
        service_type = 'analyzer'
        si_prefix = get_random_name("mirror_si")
        policy_name = get_random_name("mirror_policy")
        vn1_fixture = self.config_vn(vn1_name, vn1_subnets)
        vn2_fixture = self.config_vn(vn2_name, vn2_subnets)

        ret_dict = self.verify_svc_chain(service_mode=service_mode,
                                         service_type=service_type,
                                         left_vn_fixture=vn1_fixture,
                                         right_vn_fixture=vn2_fixture,
                                         create_svms=create_svms)
        si_fixture = ret_dict['si_fixture']
        policy_fixture = ret_dict['policy_fixture']
        si_fq_name = si_fixture.fq_name_str
        rules = [{'direction': '<>',
                       'protocol': 'icmp',
                       'source_network': vn1_fixture.vn_fq_name,
                       'src_ports': [0, 65535],
                       'dest_network': vn2_fixture.vn_fq_name,
                       'dst_ports': [0, 65535],
                       'action_list': {'simple_action': 'pass',
                                       'mirror_to': {'analyzer_name': si_fq_name}}
                       },
                       {'direction': '<>',
                       'protocol': 'icmp6',
                       'source_network': vn1_fixture.vn_fq_name,
                       'src_ports': [0, 65535],
                       'dest_network': vn2_fixture.vn_fq_name,
                       'dst_ports': [0, 65535],
                       'action_list': {'simple_action': 'pass',
                                       'mirror_to': {'analyzer_name': si_fq_name}}
                       }]
        policy_fixture.update_policy_api(rules)
        ret_dict['policy_fixture'] = policy_fixture

        return ret_dict
    # end config_svc_mirroring
