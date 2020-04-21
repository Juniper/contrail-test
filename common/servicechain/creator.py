from builtins import range
from builtins import object
import copy
import pprint
import itertools

from common.servicechain.config import *


class ServiceChainCreator(object):

    def __init__(self, tc):
        '''
            tc : test class instance
        '''
        self.tc = tc

    def build(self, data, evpn=False):
        '''
        Sample data :
        data = {
            'left_vm': {
                'host': 'nodei1',
            },
            'right_vm': {
                'host': 'nodei2',
            },
            'policy' : [
                {
                    'proto': 'any',
                    'services' : [
                        {'service_mode' : 'transparent',
                         'si_count' : 1,
                         'hosts' : ['nodei3', 'nodei2']
                        },
                        {'service_mode' : 'in-network',
                         'si_count' : 2,
                         'hosts' : ['nodei1', 'nodei2']
                        }
                    ]
                }
            ]
        }
        '''

        si_inputs = []
        if data.get('scenario_valid') is False:
            self.tc.logger.info('Scenario in %s not valid..skipping' % (data))
            return None
        # Create left and right VNs, VMs
        left_vn_fixture = self.tc.create_vn(get_random_name('left'))
        right_vn_fixture = self.tc.create_vn(get_random_name('right'))

        if evpn:
            (left_lr_intvn_fixture,
             right_lr_intvn_fixture) = self.tc.setup_evpn_service_chain(
                left_vn_fixture, right_vn_fixture)

        left_vm_fixture = self.tc.create_vm(vn_fixture=left_vn_fixture,
                                            node_name=data.get('left_vm', {}).get('host'))
        right_vm_fixture = self.tc.create_vm(vn_fixture=right_vn_fixture,
                                             node_name=data.get('right_vm', {}).get('host'))
        assert left_vm_fixture.wait_till_vm_is_up()
        assert right_vm_fixture.wait_till_vm_is_up()

        for elem in data['policy'][0]['services']:
            si_input = {}
            si_count = elem.get('si_count', 1)
            service_type = elem.get('service_type', 'firewall')
            service_mode = elem.get('service_type', 'transparent')
            si_input['service_mode'] = service_mode
            si_input['max_inst'] = si_count
            si_input['svc_img_name'] = elem.get('svc_img_name',
                                                SVC_TYPE_PROPS[service_type][service_mode])
            hosts = elem.get('hosts', [])
            si_input['hosts'] = hosts[:si_count]
            si_inputs.append(si_input)

        if evpn:
            svc_chain_info = self.tc.config_multi_inline_svc(
                si_inputs,
                proto=data['policy'][0].get('proto', 'any'),
                left_vn_fixture=left_lr_intvn_fixture,
                right_vn_fixture=right_lr_intvn_fixture,
                left_vm_fixture=left_vm_fixture,
                right_vm_fixture=right_vm_fixture,
                left_lr_child_vn_fixture=left_vn_fixture,
                right_lr_child_vn_fixture=right_vn_fixture,
                create_svms=True, evpn=evpn)
        else:
            svc_chain_info = self.tc.config_multi_inline_svc(
                si_inputs,
                proto=data['policy'][0].get('proto', 'any'),
                left_vn_fixture=left_vn_fixture,
                right_vn_fixture=right_vn_fixture,
                left_vm_fixture=left_vm_fixture,
                right_vm_fixture=right_vm_fixture,
                create_svms=True)
        return svc_chain_info

    def _remove_in_nat_in_middle(self, stages_combo):
        for item in stages_combo:
            if not item:
                continue
            svc_mode_order = [x['service_mode'] for x in item if x is not None]
            if len(svc_mode_order) > 1 and 'in-network-nat' in svc_mode_order[:-1]:
                stages_combo.remove(item)
        return stages_combo

    def _remove_duplicate_modes(self, stages_combo):
        indices = []
        for item in stages_combo:
            if not item:
                continue
            item1 = list(item)
            svc_modes = [x['service_mode'] for x in item1 if x is not None]
            if len(svc_modes) > len(set(svc_modes)):
                indices.append(stages_combo.index(item))

        new_list = []
        for i in range(len(stages_combo)):
            if i not in indices:
                new_list.append(stages_combo[i])
        return new_list
    # end _remove_duplicate_modes

    def get_next_combo(self, left_vm_nodes=[], right_vm_nodes=[],
                       si_vm_nodes=[], si_modes=[], max_sis=3,
                       max_stages=3):

        gbase = {
            'left_vm': {
            },
            'right_vm': {
            },
            'policy': [{}]
        }
        for l_item in left_vm_nodes:
            base = copy.deepcopy(gbase)
            base['left_vm']['host'] = l_item
            for r_item in right_vm_nodes:
                base['right_vm']['host'] = r_item
                stages = []
                for mode in si_modes:
                    for si_count in range(1, max_sis + 1):
                        stage_hosts_combo = list(
                            itertools.combinations(si_vm_nodes, si_count))
                        for stage_hosts in stage_hosts_combo:
                            stage = {}
                            stage['service_mode'] = mode
                            stage['si_count'] = si_count
                            stage['hosts'] = list(stage_hosts)
                            stages.append(stage)
                stages_combo = list(itertools.chain.from_iterable(
                    itertools.combinations(stages, r) for r in range(max_stages + 1)))
                self._remove_in_nat_in_middle(stages_combo)
                stages_combo = self._remove_duplicate_modes(stages_combo)
                stages_combo = list(
                    k for k, _ in itertools.groupby(stages_combo))
                for stage_combo in stages_combo:
                    if not stage_combo:
                        continue
                    base['policy'][0]['services'] = list(stage_combo)
                    yield(base)
    # end get_next_combo
